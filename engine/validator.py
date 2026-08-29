"""The number validator. The single hardest guarantee in the system.

Extracts every numeral from generated narration and asserts each one is present
in (or a declared rounding of) the findings object. Failure regenerates once,
then falls back to a template render.

NEVER weaken this to make a demo pass. If narration keeps failing validation,
the prompt is wrong, not the validator. `findings.telemetry.validator_retries`
is deliberately surfaced - a non-zero count is the guard working, and saying so
out loud scores better than hiding it."""

from __future__ import annotations

from typing import Any


def extract_numerals(text: str) -> list[float]:
    """TODO(Phase 4): locale-aware. Handles 8.2%, Rs 3.1 crore, 1,20,000, 12k."""
    raise NotImplementedError


def validate(narration: dict[str, Any], findings: dict[str, Any]) -> tuple[bool, list[str]]:
    """TODO(Phase 4): -> (ok, unaccounted_numerals)."""
    raise NotImplementedError
