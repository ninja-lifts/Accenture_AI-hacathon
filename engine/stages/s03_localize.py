"""Stage 03 - Localize.

Multi-dimensional attribution: find the smallest cell set that explains
most of the movement. Ripple/GPS-style search over the dimension lattice, then
small-cell suppression. This is the ONLY stage with published baselines to
compare against (Adtributor, Squeeze, RiskLoc) - see docs/04_EVALUATION_PLAN.md."""

from __future__ import annotations

from typing import Any


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    """Pure function over the pipeline context. Returns the updated context.

    May append to ctx['degradations'] to declare a tier cap. May set
    ctx['route'] to send the run to the gate early.

    TODO: see docs/01_MASTER_BUILD_FLOW.md for the phase this belongs to.
    """
    raise NotImplementedError
