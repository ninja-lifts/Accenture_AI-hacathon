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
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine import config
from engine import telemetry

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


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


def _call_live_anthropic(settings: config.Settings, system: str, user: str, meta: dict[str, Any]) -> LLMResult:
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
    data = _urlopen_with_retry(req)
    text = "".join(block.get("text", "") for block in data.get("content", []))
    usage = data.get("usage", {})
    tokens_in = usage.get("input_tokens", 0)
    tokens_out = usage.get("output_tokens", 0)
    cost = telemetry.estimate_cost(tokens_in, tokens_out, settings.llm_model)
    return LLMResult(text=text, tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost, from_cache=False)


def _call_live_openai_compatible(settings: config.Settings, system: str, user: str, meta: dict[str, Any]) -> LLMResult:
    """Groq (and anything else that speaks the OpenAI chat-completions shape)
    over the same dependency-free urllib path as the Anthropic adapter -
    still no new pinned dependency, just a second, equally minimal HTTP call."""
    endpoint = settings.llm_endpoint or "https://api.groq.com/openai/v1/chat/completions"
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
    data = _urlopen_with_retry(req)
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    tokens_in = usage.get("prompt_tokens", 0)
    tokens_out = usage.get("completion_tokens", 0)
    cost = telemetry.estimate_cost(tokens_in, tokens_out, settings.llm_model)
    return LLMResult(text=text, tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost, from_cache=False)


def _urlopen_with_retry(req: urllib.request.Request, max_attempts: int = 5) -> dict[str, Any]:
    """Groq's free tier rate-limits by requests/minute; a 17-scenario baseline
    run comfortably exceeds that in a tight loop. Retry on 429 with backoff
    (honouring Retry-After when the server sends one) rather than failing the
    whole run partway through."""
    import time

    for attempt in range(max_attempts):
        try:
            # A reasoning model generating against a large real payload (the
            # full findings object, ~10KB+) can take well over 60s - 60s was
            # tuned against small test prompts, not the actual production
            # payload size. 150s gives real generations room without making
            # a genuinely stuck request hang forever.
            with urllib.request.urlopen(req, timeout=150) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == max_attempts - 1:
                raise
            wait = float(e.headers.get("Retry-After", 0)) or (2**attempt) * 2
            time.sleep(wait)
    raise RuntimeError("unreachable")


_LIVE_ADAPTERS = {
    "anthropic": _call_live_anthropic,
    "groq": _call_live_openai_compatible,
}


def _call_live(settings: config.Settings, system: str, user: str, meta: dict[str, Any]) -> LLMResult:
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
    return adapter(settings, system, user, meta)


def complete(
    prompt_id: str,
    payload: dict[str, Any],
    *,
    json_mode: bool = True,
    ctx: dict[str, Any] | None = None,
) -> LLMResult:
    """Render prompts/{prompt_id}.md with payload, call the provider (or the
    replay cache), return the result.

    Raises LLMCallCapExceeded if this would be the 3rd call within the run
    tracked by `ctx` (pass the pipeline context so the cap is enforced across
    Stage 00 and Stage 07, not just within one call site). Raises
    LLMCacheMiss when replay mode has no cached entry - callers must catch
    this and use a deterministic fallback; it is never appropriate to let it
    crash the run.
    """
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

    if use_live:
        result = _call_live(settings, system, user, meta)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {"text": result.text, "tokens_in": result.tokens_in, "tokens_out": result.tokens_out},
                indent=2,
            ),
            encoding="utf-8",
        )
    elif cache_path.exists():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        result = LLMResult(
            text=cached["text"],
            tokens_in=cached.get("tokens_in", 0),
            tokens_out=cached.get("tokens_out", 0),
            cost_usd=0.0,
            from_cache=True,
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
