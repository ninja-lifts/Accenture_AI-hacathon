"""Stage 06 - Falsify.

The stage that separates this from a correlation engine. For each
candidate cause: difference-in-differences against control segments, a
placebo-timing test, a dose-response check where magnitude is available, and a
pre-period contamination check. Candidates that survive are TESTED; candidates
that fail are recorded in rejected_hypotheses rather than dropped."""

from __future__ import annotations

from typing import Any


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    """Pure function over the pipeline context. Returns the updated context.

    May append to ctx['degradations'] to declare a tier cap. May set
    ctx['route'] to send the run to the gate early.

    TODO: see docs/01_MASTER_BUILD_FLOW.md for the phase this belongs to.
    """
    raise NotImplementedError
