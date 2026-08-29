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


def _call_live(settings: config.Settings, system: str, user: str, meta: dict[str, Any]) -> LLMResult:
    """Minimal, dependency-free HTTP call. requirements.txt intentionally pins
    no provider SDK (replay mode - the default - needs none), so this speaks
    the Anthropic Messages API directly over urllib rather than adding a new
    pinned dependency for a path that is off by default."""
    if settings.llm_provider != "anthropic":
        raise NotImplementedError(
            f"live calls implemented for provider='anthropic' only; "
            f"got '{settings.llm_provider}'. Add an adapter or run in replay mode."
        )
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
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = "".join(block.get("text", "") for block in data.get("content", []))
    usage = data.get("usage", {})
    tokens_in = usage.get("input_tokens", 0)
    tokens_out = usage.get("output_tokens", 0)
    cost = telemetry.estimate_cost(tokens_in, tokens_out, settings.llm_model)
    return LLMResult(text=text, tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost, from_cache=False)


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
