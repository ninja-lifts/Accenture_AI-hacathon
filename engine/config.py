"""Configuration. Everything environment-specific lives here and nowhere else.

No model name, endpoint, key or provider string may appear anywhere else in the
codebase. That is what makes the LLM swappable and the repo vendor-neutral."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # --- data ---
    data_dir: str = os.getenv("GLASSBOX_DATA_DIR", "data/generated")
    duckdb_path: str = os.getenv("GLASSBOX_DUCKDB", "data/generated/meridian.duckdb")

    # --- llm (single adapter reads these; nothing else does) ---
    llm_provider: str = os.getenv("GLASSBOX_LLM_PROVIDER", "replay")
    llm_model: str = os.getenv("GLASSBOX_LLM_MODEL", "")
    llm_endpoint: str = os.getenv("GLASSBOX_LLM_ENDPOINT", "")
    llm_api_key: str = os.getenv("GLASSBOX_LLM_API_KEY", "")

    # --- replay ---
    replay_cache: str = os.getenv("GLASSBOX_REPLAY_CACHE", "eval/replay_cache")
    # Default TRUE on purpose: a fresh clone runs offline with no key.
    replay_mode: bool = os.getenv("GLASSBOX_REPLAY", "1") == "1"

    # --- guards ---
    max_llm_calls_per_run: int = 2
    max_validator_retries: int = 2


def load() -> Settings:
    """TODO(Phase 0): read .env if present, return frozen Settings."""
    raise NotImplementedError
