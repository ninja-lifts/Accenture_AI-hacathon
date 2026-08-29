"""Per-run timings, token counts and cost. Rendered as a footer on every answer.

Cost transparency is cheap to build and disproportionately credible: most
prototypes cannot answer 'what does one of these cost to run?'"""

from __future__ import annotations

from typing import Any
import contextlib


@contextlib.contextmanager
def stage(name: str, sink: dict[str, Any]):
    """TODO(Phase 4): time a stage into sink['stage_timings_ms'][name]."""
    raise NotImplementedError


def estimate_cost(tokens_in: int, tokens_out: int, model: str) -> float:
    """TODO(Phase 4): read rates from config; return USD. Zero in replay mode."""
    raise NotImplementedError
