"""The orchestrator. Reads like the architecture diagram, top to bottom.

Deliberately a straight line, not an agent loop. Stages are pure functions over
a growing context; any stage may declare a tier cap or route to the gate. This
is what makes a run replayable, testable and explainable - and it is the design
decision to defend in Q&A, not apologise for."""

from __future__ import annotations

from typing import Any


def run(
    *,
    trigger: str,
    persona: str,
    question: str | None = None,
    kpi: str | None = None,
    window: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute the pipeline and return one findings object validated against
    schemas/findings.schema.json.

    Stage order (see docs/02_BUILD_BLUEPRINT.md):
        00 intent      (LLM #1, only when trigger == 'user_question')
        01 define      contract -> SQL -> series
        02 detect      seasonal baseline, dual materiality, registry suppression
        03 localize    multi-dimensional attribution + small-cell suppression
        04 decompose   price / volume / mix along the KPI graph
        05 retrieve    BM25 + embeddings over the redacted document index
        06 falsify     difference-in-differences, placebo timing, controls
        --- gate ---   answer | abstention | clarification
        07 narrate     (LLM #2, number-validated)

    TODO(Phase 4).
    """
    raise NotImplementedError
