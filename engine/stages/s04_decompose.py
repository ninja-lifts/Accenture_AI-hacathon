"""Stage 04 - Decompose.

Price / volume / mix arithmetic along the KPI graph edges. Every number
here is VERIFIED by construction because it is recomputed from source, and the
components must sum to the movement - an identity check, asserted in tests."""

from __future__ import annotations

from typing import Any


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    """Pure function over the pipeline context. Returns the updated context.

    May append to ctx['degradations'] to declare a tier cap. May set
    ctx['route'] to send the run to the gate early.

    TODO: see docs/01_MASTER_BUILD_FLOW.md for the phase this belongs to.
    """
    raise NotImplementedError
