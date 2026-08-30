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
    """Time a stage into sink['stage_timings_ms'][name].

    Every stage must call this - `total_ms` (and therefore every latency
    number this project ever reports) is `sum(stage_timings_ms.values())`,
    nothing more. engine/stages/s00_intent.py and s07_narrate.py went
    without it for the whole project's history (CHANGELOG.md): invisible in
    replay mode, where a cache read is near-instant regardless, but it meant
    every reported latency silently excluded the two stages that make live
    LLM calls - the ones actually slow enough to matter. Found by running
    live end to end and comparing the receipt's own numbers (~1s) against
    real per-call elapsed time in the logs (25-91s)."""
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
