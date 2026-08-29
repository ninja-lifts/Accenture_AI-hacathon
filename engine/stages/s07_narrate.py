"""Stage 07 - Narrate (LLM touchpoint #2).

Renders a completed, tiered findings object into persona-appropriate
prose. Sees no raw data. Cannot introduce a number, a cause or a tier. Output
passes through engine/validator.py before it reaches a human."""

from __future__ import annotations

from typing import Any


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    """Pure function over the pipeline context. Returns the updated context.

    May append to ctx['degradations'] to declare a tier cap. May set
    ctx['route'] to send the run to the gate early.

    TODO: see docs/01_MASTER_BUILD_FLOW.md for the phase this belongs to.
    """
    raise NotImplementedError
