"""Session-wide test safety net. Tests must never make a live LLM call - not
because a passing suite should be free (it should), but because one already
did: a plain `pytest` run inherited .env's GLASSBOX_REPLAY=0, went live for
~12 minutes and hit a real Groq 429 (see CHANGELOG.md). That inheritance is
the bug this file exists to make impossible, twice over:

1. GLASSBOX_REPLAY is forced to "1" here, at MODULE import time, before
   pytest collects a single test module. This has to happen this early
   because engine/config.py's Settings dataclass reads os.environ as
   CLASS-LEVEL FIELD DEFAULTS, evaluated once when the class body executes
   (i.e. on first import of engine.config) - not per Settings()
   instantiation. Setting the env var from inside a fixture would be too
   late if anything had already imported engine.config by then; conftest.py
   is guaranteed to be imported before test modules in the same directory,
   which is what makes doing it here, at module scope, actually reliable.
2. engine.llm_client._call_live is patched to raise loudly if anything ever
   calls it during a test run - a backstop independent of (1), so that if
   some future import-order change ever meant GLASSBOX_REPLAY wasn't forced
   in time, the suite still stops the network call before it happens
   instead of silently going live again.
"""

from __future__ import annotations

import os

os.environ["GLASSBOX_REPLAY"] = "1"

import pytest  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def _forbid_live_llm_calls():
    from engine import llm_client

    def _blocked(*_args, **_kwargs):
        raise AssertionError(
            "a test tried to make a live LLM call via engine.llm_client._call_live. "
            "Tests must never reach the network - GLASSBOX_REPLAY is forced to '1' at "
            "tests/conftest.py import time; if this fired, something bypassed that."
        )

    original = llm_client._call_live
    llm_client._call_live = _blocked
    try:
        yield
    finally:
        llm_client._call_live = original
