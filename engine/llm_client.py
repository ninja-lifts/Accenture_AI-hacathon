"""The single LLM boundary. Exactly one file in this repo may call a model.

Vendor-neutral by construction: the provider, model id and endpoint come from
config, prompts come from prompts/*.md, and callers pass a prompt id plus a
payload. Swapping providers is a config change, not a code change.

Also the replay layer: in replay mode, responses are read from the committed
cache keyed by (prompt_id, prompt_version, sha256(payload)). This is what lets
a judge run the whole system offline with no API key, and what makes the
evaluation deterministic."""

from __future__ import annotations

import hashlib
import json
import queue
import random
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine import config
from engine import telemetry

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# A hung live call is not hypothetical here - the first live run of this
# session hung for 19+ minutes with the process alive and no exception ever
# raised (see CHANGELOG.md). Root cause: urllib.request.urlopen(timeout=N)
# is a per-socket-operation timeout, not a wall-clock deadline on the whole
# request - resp.read() re-arms it on every successful recv(), so a
# connection that trickles bytes in slowly enough never trips it, however
# long the total transfer takes. These constants and _urlopen_with_retry
# below exist specifically to make that structurally impossible.
_SOCKET_TIMEOUT_SECONDS = 60  # catches a genuinely dead connect/recv fast
_MAX_ATTEMPTS = 5
_MAX_TOTAL_SECONDS = 300  # hard wall-clock ceiling across ALL attempts of one logical call
_INTER_CALL_DELAY_SECONDS = 3  # defensive pacing; 429 backoff below is the second line of defence


class LLMCallCapExceeded(Exception):
    """A run tried to make a third LLM call. The architecture has exactly two
    touchpoints (schemas/findings.schema.json telemetry.llm_calls.maximum=2) -
    this is a bug, not a case to handle gracefully."""


class LLMCacheMiss(Exception):
    """Replay mode (or no configured key) and no cached response exists for
    this exact (prompt_id, prompt_version, payload). Callers are expected to
    fall back to a deterministic renderer (Stage 00's rule-based parser,
    Stage 07's template narration) rather than fail the whole run - the
    product's own promise is that it runs offline with no key."""

    def __init__(self, prompt_id: str, key: str):
        super().__init__(
            f"no replay-cache entry for prompt_id='{prompt_id}' key='{key}'. "
            f"Populate eval/replay_cache/{prompt_id}/{key}.json by running once "
            f"in live mode, or handle LLMCacheMiss with a deterministic fallback."
        )
        self.prompt_id = prompt_id
        self.key = key


@dataclass
class LLMResult:
    text: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    from_cache: bool


def _load_prompt(prompt_id: str) -> tuple[dict[str, Any], str]:
    """Split prompts/{prompt_id}.md into (frontmatter, body). Frontmatter is
    the '---'-delimited YAML header (prompt_id, version, temperature, ...);
    the body is everything after it, sent to the model as the system turn."""
    import yaml

    path = _PROMPTS_DIR / f"{prompt_id}.md"
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        raise ValueError(f"{path}: missing '---' frontmatter header")
    _, fm, body = raw.split("---", 2)
    meta = yaml.safe_load(fm)
    return meta, body.strip()


def _render_user_turn(payload: dict[str, Any]) -> str:
    sections = []
    for k, v in payload.items():
        sections.append(f"{k.upper()}:\n{json.dumps(v, indent=2, default=str, ensure_ascii=False)}")
    return "\n\n".join(sections)


def cache_key(prompt_id: str, prompt_version: str, payload: dict[str, Any]) -> str:
    """Stable hash. Payload is canonically serialised (sorted keys) so the
    cache does not miss on dict ordering - a miss there would mean the
    'offline' demo quietly needs a live key."""
    canonical = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    digest = hashlib.sha256(f"{prompt_id}:{prompt_version}:{canonical}".encode("utf-8")).hexdigest()
    return digest[:32]


def _cache_path(settings: config.Settings, prompt_id: str, key: str) -> Path:
    return Path(settings.replay_cache) / prompt_id / f"{key}.json"


def _call_live_anthropic(settings: config.Settings, system: str, user: str, meta: dict[str, Any], label: str = "?") -> LLMResult:
    endpoint = settings.llm_endpoint or "https://api.anthropic.com/v1/messages"
    body = json.dumps(
        {
            "model": settings.llm_model,
            "max_tokens": meta.get("max_output_tokens", 1024),
            "temperature": meta.get("temperature", 0),
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "content-type": "application/json",
            "x-api-key": settings.llm_api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    data = _urlopen_with_retry(req, label)
    text = "".join(block.get("text", "") for block in data.get("content", []))
    usage = data.get("usage", {})
    tokens_in = usage.get("input_tokens", 0)
    tokens_out = usage.get("output_tokens", 0)
    cost = telemetry.estimate_cost(tokens_in, tokens_out, settings.llm_model)
    return LLMResult(text=text, tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost, from_cache=False)


_OPENAI_COMPATIBLE_ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
}


def _call_live_openai_compatible(settings: config.Settings, system: str, user: str, meta: dict[str, Any], label: str = "?") -> LLMResult:
    """Groq and OpenAI itself (and anything else that speaks the OpenAI
    chat-completions shape) over the same dependency-free urllib path as the
    Anthropic adapter - still no new pinned dependency, just the same
    minimal HTTP call against a different default endpoint per provider."""
    endpoint = settings.llm_endpoint or _OPENAI_COMPATIBLE_ENDPOINTS.get(
        settings.llm_provider, _OPENAI_COMPATIBLE_ENDPOINTS["groq"]
    )
    max_tokens = meta.get("max_output_tokens", 1024)
    if "gpt-oss" in settings.llm_model or "reasoning" in settings.llm_model:
        # Reasoning-style models spend part of max_tokens on an internal
        # "reasoning" field before the final answer - the prompt's declared
        # budget assumes a non-reasoning model. Under-budgeting here doesn't
        # truncate gracefully: Groq's JSON-mode validator rejects an empty
        # final generation with a 400 rather than returning partial content,
        # so this has to be generous rather than exact.
        max_tokens = max(max_tokens * 3, max_tokens + 2000)
    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "temperature": meta.get("temperature", 0),
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if meta.get("output_format") == "json":
        payload["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {settings.llm_api_key}",
            # Groq's edge (Cloudflare) returns a bare 403 to urllib's default
            # User-Agent ("Python-urllib/3.x") - it reads as a bot signature,
            # not an auth problem. A normal browser UA clears it; found this
            # empirically, not documented anywhere obvious.
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
        method="POST",
    )
    data = _urlopen_with_retry(req, label)
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    tokens_in = usage.get("prompt_tokens", 0)
    tokens_out = usage.get("completion_tokens", 0)
    cost = telemetry.estimate_cost(tokens_in, tokens_out, settings.llm_model)
    return LLMResult(text=text, tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost, from_cache=False)


def _call_live_gemini(settings: config.Settings, system: str, user: str, meta: dict[str, Any], label: str = "?") -> LLMResult:
    """Google AI Studio / Gemini's generateContent REST API, over the same
    dependency-free urllib path as the other two adapters. Shaped differently
    from the OpenAI-compatible one in three ways worth flagging: the model id
    is part of the URL path, not the JSON body; the system prompt is its own
    top-level `systemInstruction` field, not a `role: system` message; and
    the API key is a `?key=` query parameter, not an Authorization header -
    all per Google's documented REST shape, not inferred.

    Confirmed empirically (see CHANGELOG.md), not assumed: this model thinks
    by default and there is no supported way to turn it off -
    `thinkingConfig: {thinkingBudget: 0}` is rejected outright with a 400.
    Thinking-token consumption scales with prompt complexity far more than
    the trivial-prompt test suggested: a one-word reply spent 90 tokens on
    `thoughtsTokenCount`, but a real SC-04 narrate call spent roughly
    2,700-2,800 of a 2,900-token budget on thinking, leaving only 111 for
    the visible answer and truncating it mid-string - genuinely incomplete
    JSON, not the fenced-wrapper case `_clean_gemini_json_text` handles.
    Same failure shape as Groq's reasoning models either way: budget
    generously rather than exactly, with a large flat floor rather than a
    multiplier alone, since thinking cost is not simply proportional to the
    declared output size."""
    model = settings.llm_model or "gemini-3.6-flash"
    endpoint = settings.llm_endpoint or (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    )
    declared_max = meta.get("max_output_tokens", 1024)
    generation_config: dict[str, Any] = {
        "temperature": meta.get("temperature", 0),
        "maxOutputTokens": max(declared_max * 3, declared_max + 2000, 8000),
    }
    if meta.get("output_format") == "json":
        generation_config["responseMimeType"] = "application/json"
    payload: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": generation_config,
    }
    req = urllib.request.Request(
        f"{endpoint}?key={settings.llm_api_key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    data = _urlopen_with_retry(req, label)
    candidates = data.get("candidates") or []
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    text = _clean_gemini_json_text("".join(p.get("text", "") for p in parts))
    usage = data.get("usageMetadata", {})
    tokens_in = usage.get("promptTokenCount", 0)
    tokens_out = usage.get("candidatesTokenCount", 0)
    cost = telemetry.estimate_cost(tokens_in, tokens_out, settings.llm_model)
    return LLMResult(text=text, tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost, from_cache=False)


def _clean_gemini_json_text(text: str) -> str:
    """Gemini's JSON mode can still wrap the payload in a markdown code
    fence with commentary after it, even with responseMimeType set to
    application/json - observed empirically on a real narrate-shaped call
    (see CHANGELOG.md), not assumed. Strips a leading fence if present, then
    takes the first complete JSON value via json.JSONDecoder.raw_decode,
    which stops at the end of that value and simply ignores anything
    trailing it - no need to locate or strip a closing fence separately.
    Falls back to the original text unchanged if this doesn't apply or
    still doesn't parse: s07_narrate.py's own json.loads/validator retry
    path already handles a genuinely unparseable response correctly (retry,
    then raise loudly) - this only needs to fix the case that IS valid JSON
    once unwrapped, not invent a second error-handling path for the case
    that isn't."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return text
    first_newline = stripped.find("\n")
    body = stripped[first_newline + 1:] if first_newline != -1 else stripped
    try:
        obj, _end = json.JSONDecoder().raw_decode(body.strip())
    except ValueError:
        return text
    return json.dumps(obj)


def _do_single_attempt(req: urllib.request.Request, result_q: "queue.Queue[tuple[str, Any]]") -> None:
    """Runs in its own daemon thread so the waiter in _urlopen_with_retry can
    give up on a wall-clock deadline even though nothing in urllib can be
    cancelled once it's blocked in a syscall. Relays success AND failure
    through the queue rather than letting an exception surface only in this
    thread - the caller is the one that decides what a failure means."""
    try:
        with urllib.request.urlopen(req, timeout=_SOCKET_TIMEOUT_SECONDS) as resp:
            result_q.put(("ok", json.loads(resp.read().decode("utf-8"))))
    except Exception as exc:  # noqa: BLE001 - cross-thread relay, not a fallback; the
        # real handling happens where this lands in _urlopen_with_retry below.
        result_q.put(("error", exc))


def _urlopen_with_retry(req: urllib.request.Request, label: str) -> dict[str, Any]:
    """Groq's free tier rate-limits by requests/minute; a 17-scenario batch
    comfortably exceeds that in a tight loop, so 429s are retried with
    backoff (honouring Retry-After when the server sends one).

    Every attempt runs in a daemon thread and is awaited with
    queue.Queue.get(timeout=...) against a hard _MAX_TOTAL_SECONDS wall-clock
    budget shared across all attempts - not just urlopen's own
    _SOCKET_TIMEOUT_SECONDS, which only bounds a single blocking recv() and
    does nothing for a connection that keeps trickling bytes in just under
    that ceiling forever (see the module-level comment; this is exactly the
    failure mode that produced a 19-minute hang with no exception raised).
    The thread is a daemon specifically so abandoning a truly stuck one on
    deadline doesn't also block process exit - Python cannot cancel a thread
    blocked in a C-level recv(), so "stop waiting on it" is the only lever
    available, and daemon=True is what makes that safe to do.

    Raises (never silently degrades) once _MAX_ATTEMPTS or
    _MAX_TOTAL_SECONDS is exhausted, whichever comes first."""
    start = time.monotonic()
    deadline = start + _MAX_TOTAL_SECONDS
    last_exc: BaseException | None = None

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        print(f"[llm] {label} attempt {attempt}/{_MAX_ATTEMPTS} starting, "
              f"elapsed={time.monotonic() - start:.0f}s budget_left={remaining:.0f}s", file=sys.stderr)

        result_q: queue.Queue = queue.Queue(maxsize=1)
        threading.Thread(target=_do_single_attempt, args=(req, result_q), daemon=True).start()
        try:
            status, payload = result_q.get(timeout=remaining)
        except queue.Empty:
            elapsed = time.monotonic() - start
            print(f"[llm] {label} attempt {attempt} did not finish within the "
                  f"{_MAX_TOTAL_SECONDS}s total budget (elapsed={elapsed:.0f}s) - giving up on "
                  "it; the thread is a daemon and won't block process exit.", file=sys.stderr)
            last_exc = TimeoutError(
                f"{label}: attempt {attempt} exceeded the {_MAX_TOTAL_SECONDS}s total wall-clock "
                f"budget without completing (socket timeout is {_SOCKET_TIMEOUT_SECONDS}s per "
                "operation, so this is bytes trickling in under that ceiling, not a dead socket)"
            )
            break  # this attempt consumed the whole remaining budget by definition; no point looping

        if status == "ok":
            print(f"[llm] {label} attempt {attempt} succeeded, elapsed={time.monotonic() - start:.0f}s",
                  file=sys.stderr)
            return payload

        exc = payload
        last_exc = exc
        retryable = (isinstance(exc, urllib.error.HTTPError) and exc.code == 429) or isinstance(
            exc, (urllib.error.URLError, OSError)
        )
        if not retryable:
            # A real HTTP error that isn't rate-limiting, a JSON decode error, an
            # unexpected response shape - retrying won't fix any of those. Raise
            # loudly now rather than burn the rest of the budget pretending it might.
            raise exc

        remaining = deadline - time.monotonic()
        if remaining <= 0 or attempt == _MAX_ATTEMPTS:
            break
        if isinstance(exc, urllib.error.HTTPError):
            wait = float(exc.headers.get("Retry-After", 0)) or (2**attempt)
        else:
            wait = 2**attempt
        wait = min(wait + random.uniform(0, 1), remaining)
        print(f"[llm] {label} attempt {attempt} failed ({type(exc).__name__}: {exc}), "
              f"retrying in {wait:.0f}s", file=sys.stderr)
        time.sleep(wait)

    elapsed = time.monotonic() - start
    raise TimeoutError(
        f"{label}: exhausted after {elapsed:.0f}s against a {_MAX_TOTAL_SECONDS}s total wall-clock "
        f"budget ({_MAX_ATTEMPTS} attempts max) - last error: {type(last_exc).__name__}: {last_exc}"
    ) from last_exc


_LIVE_ADAPTERS = {
    "anthropic": _call_live_anthropic,
    "groq": _call_live_openai_compatible,
    "gemini": _call_live_gemini,
    "openai": _call_live_openai_compatible,
}


def _call_live(settings: config.Settings, system: str, user: str, meta: dict[str, Any], label: str = "?") -> LLMResult:
    """Minimal, dependency-free HTTP calls. requirements.txt intentionally
    pins no provider SDK (replay mode - the default - needs none), so every
    adapter here speaks its provider's REST API directly over urllib rather
    than adding a pinned dependency for a path that is off by default."""
    adapter = _LIVE_ADAPTERS.get(settings.llm_provider)
    if adapter is None:
        raise NotImplementedError(
            f"live calls implemented for providers {sorted(_LIVE_ADAPTERS)}; "
            f"got '{settings.llm_provider}'. Add an adapter or run in replay mode."
        )
    result = adapter(settings, system, user, meta, label)
    # Serial by construction (no caller here is threaded or async - Rule 9), so
    # this simply spaces consecutive live calls apart: eval/baselines/run_all.py
    # calls this directly for B3, bypassing complete() entirely, so the delay
    # lives here rather than in complete() - the one point every live call
    # actually shares. A 17-scenario harness run plus a B3 baseline run back to
    # back is ~30+ calls in a tight loop against Groq's free-tier rate limit;
    # this is the first line of defence, the 429 backoff above is the second.
    time.sleep(_INTER_CALL_DELAY_SECONDS)
    return result


def complete(
    prompt_id: str,
    payload: dict[str, Any],
    *,
    json_mode: bool = True,
    ctx: dict[str, Any] | None = None,
    force_live: bool = False,
) -> LLMResult:
    """Render prompts/{prompt_id}.md with payload, call the provider (or the
    replay cache), return the result.

    Raises LLMCallCapExceeded if this would be the 3rd call within the run
    tracked by `ctx` (pass the pipeline context so the cap is enforced across
    Stage 00 and Stage 07, not just within one call site). Raises
    LLMCacheMiss when there's no cached entry AND live calls aren't available
    (replay mode, or no key) - callers must catch this and use a
    deterministic fallback; it is never appropriate to let it crash the run.

    A cache hit is checked FIRST, before deciding whether to go live - live
    mode means "call live for anything not yet captured," not "always call
    live and overwrite what's already there." This is what makes a live batch
    resumable: a run interrupted by a rate limit (a real Groq 429 with
    Retry-After: 300s cost us a partial batch once - see CHANGELOG.md) can be
    re-run and picks up exactly where it left off, at no extra cost, instead
    of re-billing every call made before the interruption.

    force_live=True skips that cache-hit check (still a no-op in replay mode,
    since the branch below only takes effect when use_live is also true) -
    for a caller that retries the SAME payload on purpose and needs a
    genuinely fresh sample each time, not the first attempt's cached text
    played back again. engine/stages/s07_narrate.py's retry loop is exactly
    this case: prompts/narrate.md runs at temperature 0.2 specifically so a
    validator-rejected attempt has a real chance of a different result next
    try, but the payload (outcome_draft/persona) is identical across
    attempts, so it hashes to the same cache key - resumability found this
    the hard way, deterministically replaying attempt 1's failed response for
    every subsequent attempt and burning the whole retry budget on one
    generation. Real regression, caught by re-running SC-01 live after this
    file's own resumability change landed - see CHANGELOG.md entry 020."""
    settings = config.load()

    if ctx is not None:
        calls_so_far = ctx.get("_llm_call_count", 0)
        if calls_so_far >= settings.max_llm_calls_per_run:
            raise LLMCallCapExceeded(
                f"prompt_id='{prompt_id}' would be call #{calls_so_far + 1}; "
                f"cap is {settings.max_llm_calls_per_run}"
            )

    meta, system = _load_prompt(prompt_id)
    version = str(meta.get("version", "0.0.0"))
    user = _render_user_turn(payload)
    key = cache_key(prompt_id, version, payload)
    cache_path = _cache_path(settings, prompt_id, key)

    use_live = (not settings.replay_mode) and bool(settings.llm_api_key)
    skip_cache_read = force_live and use_live

    if skip_cache_read:
        print(f"[llm] {prompt_id}/{key[:12]} force_live - ignoring any cached entry, calling live for a fresh sample",
              file=sys.stderr)

    if cache_path.exists() and not skip_cache_read:
        if use_live:
            print(f"[llm] {prompt_id}/{key[:12]} resumed from {cache_path} - no live call made",
                  file=sys.stderr)
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        result = LLMResult(
            text=cached["text"],
            tokens_in=cached.get("tokens_in", 0),
            tokens_out=cached.get("tokens_out", 0),
            cost_usd=0.0,
            from_cache=True,
        )
    elif use_live:
        label = f"{(ctx or {}).get('scenario_id') or (ctx or {}).get('run_id', '-')}/{prompt_id}"
        result = _call_live(settings, system, user, meta, label)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {"text": result.text, "tokens_in": result.tokens_in, "tokens_out": result.tokens_out},
                indent=2,
            ),
            encoding="utf-8",
        )
    else:
        raise LLMCacheMiss(prompt_id, key)

    if ctx is not None:
        ctx["_llm_call_count"] = ctx.get("_llm_call_count", 0) + 1
        ctx.setdefault("_llm_tokens_in", 0)
        ctx.setdefault("_llm_tokens_out", 0)
        ctx.setdefault("_llm_cost_usd", 0.0)
        ctx["_llm_tokens_in"] += result.tokens_in
        ctx["_llm_tokens_out"] += result.tokens_out
        ctx["_llm_cost_usd"] += result.cost_usd

    return result
