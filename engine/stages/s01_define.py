"""Stage 01 - Define.

Resolve the contract, apply entitlement predicates, execute the contract
SQL, return the series with declared freshness per source. If the contract and
the warehouse disagree, that is a data-quality failure, not a silent coercion."""

from __future__ import annotations

from typing import Any


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    """Pure function over the pipeline context. Returns the updated context.

    May append to ctx['degradations'] to declare a tier cap. May set
    ctx['route'] to send the run to the gate early.

    TODO: see docs/01_MASTER_BUILD_FLOW.md for the phase this belongs to.
    """
    raise NotImplementedError
