"""The single LLM boundary. Exactly one file in this repo may call a model.

Vendor-neutral by construction: the provider, model id and endpoint come from
config, prompts come from prompts/*.md, and callers pass a prompt id plus a
payload. Swapping providers is a config change, not a code change.

Also the replay layer: in replay mode, responses are read from the committed
cache keyed by (prompt_id, prompt_version, sha256(payload)). This is what lets
a judge run the whole system offline with no API key, and what makes the
evaluation deterministic."""

from __future__ import annotations

from typing import Any


class LLMResult:
    text: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    from_cache: bool


def complete(prompt_id: str, payload: dict[str, Any], *, json_mode: bool = True) -> LLMResult:
    """Render prompts/{prompt_id}.md with payload, call the provider (or replay
    cache), return the result. Raises if called more than
    Settings.max_llm_calls_per_run times within one run context.

    TODO(Phase 4).
    """
    raise NotImplementedError


def cache_key(prompt_id: str, prompt_version: str, payload: dict[str, Any]) -> str:
    """TODO(Phase 4): stable hash. Payload must be canonically serialised or the
    cache misses on dict ordering and your 'offline' demo quietly needs a key."""
    raise NotImplementedError
