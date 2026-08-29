"""Stage 00 - Intent parsing (LLM touchpoint #1).

Only runs for typed questions. Maps free text to {kpi, segment, window}
using ONLY the compiled contract vocabulary, and routes to the clarification
branch when the mapping is ambiguous rather than guessing. This is what turns
'requests clarification or abstains' from a claim into a demonstrable behaviour."""

from __future__ import annotations

from typing import Any


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    """Pure function over the pipeline context. Returns the updated context.

    May append to ctx['degradations'] to declare a tier cap. May set
    ctx['route'] to send the run to the gate early.

    TODO: see docs/01_MASTER_BUILD_FLOW.md for the phase this belongs to.
    """
    raise NotImplementedError
