"""Stage 02 - Detect.

Seasonal baseline (STL / seasonal-naive with a festival calendar), residual
control chart, dual materiality test, and suppression of movements already
explained by the context registry (planned promos, price changes, releases).
Answers the brief's 'meaningful change vs normal noise' question directly."""

from __future__ import annotations

from typing import Any


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    """Pure function over the pipeline context. Returns the updated context.

    May append to ctx['degradations'] to declare a tier cap. May set
    ctx['route'] to send the run to the gate early.

    TODO: see docs/01_MASTER_BUILD_FLOW.md for the phase this belongs to.
    """
    raise NotImplementedError
