"""Per-run timings, token counts and cost. Rendered as a footer on every answer.

Cost transparency is cheap to build and disproportionately credible: most
prototypes cannot answer 'what does one of these cost to run?'"""

from __future__ import annotations

import time
from typing import Any
import contextlib

# USD per 1K tokens, in/out. Illustrative rates for the cost receipt - not a
# claim about any specific provider's live pricing. Zero whenever the run was
# served from the replay cache, since no live call happened.
_RATES_PER_1K: dict[str, tuple[float, float]] = {
    "default": (0.003, 0.015),
}


@contextlib.contextmanager
def stage(name: str, sink: dict[str, Any]):
    """Time a stage into sink['stage_timings_ms'][name]."""
    sink.setdefault("stage_timings_ms", {})
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        sink["stage_timings_ms"][name] = sink["stage_timings_ms"].get(name, 0.0) + elapsed_ms


def estimate_cost(tokens_in: int, tokens_out: int, model: str) -> float:
    """Read rates from config; return USD. Zero in replay mode (callers pass
    tokens_in=tokens_out=0 for a cache hit, which naturally yields 0.0)."""
    rate_in, rate_out = _RATES_PER_1K.get(model, _RATES_PER_1K["default"])
    return round(tokens_in / 1000.0 * rate_in + tokens_out / 1000.0 * rate_out, 6)
