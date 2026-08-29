"""Stage 05 - Retrieve.

Hybrid BM25 + embedding retrieval over the redacted document index,
filtered by the principal's entitlements and by the movement's time window.
Documents outside the window are excluded before scoring - a ticket from three
months ago is not evidence for last week, however well it matches."""

from __future__ import annotations

from typing import Any


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    """Pure function over the pipeline context. Returns the updated context.

    May append to ctx['degradations'] to declare a tier cap. May set
    ctx['route'] to send the run to the gate early.

    TODO: see docs/01_MASTER_BUILD_FLOW.md for the phase this belongs to.
    """
    raise NotImplementedError
