"""The answer / abstain / clarify gate. The most important 100 lines here.

The invariant: exactly one branch is populated. Never a hedged blend. The
product's whole claim to trustworthiness is that it can decline, so the decline
path must be as engineered as the answer path."""

from __future__ import annotations

from typing import Any

from engine.tiers import EVIDENCE_FLOOR

__all__ = ["EVIDENCE_FLOOR", "decide"]


def decide(ctx: dict[str, Any]) -> str:
    """-> 'answer' | 'abstention' | 'clarification'.

    Implements the gate exactly as specified in
    docs/02_BUILD_BLUEPRINT.md#the-gate:

        if intent ambiguous                          -> clarification
        elif data-quality failure                     -> abstention (data_quality_failure)
        elif only localization is a suppressed cell    -> abstention (segment_too_small_to_disclose)
        elif no candidate clears the evidence floor    -> abstention (no_candidate_passed_evidence_floor)
        elif evidence contradicts every candidate      -> abstention (evidence_contradicts_all_candidates)
        elif history below contract minimum            -> answer, capped at HYPOTHESIS
        else                                            -> answer

    Reads (never mutates) `ctx`:
        route                str|None   'clarification' set by Stage 00
        data_quality_failure bool
        localization          list[dict]  segments with a 'suppressed' flag
        candidates             list[dict]  candidate drivers; each has
                                            'evidence_ids', 'test_results'
        history_periods_ok    bool

    Writes ctx['gate_reason'] with the abstention reason_code (or None for
    answer/clarification) so the caller (engine/pipeline.py) can assemble the
    right outcome payload without re-deriving this logic. The branch itself
    is the return value - the one thing this function may never do is
    populate more than one outcome, which is why it returns a single string
    rather than a partially-filled object (tests/test_gate_invariant.py).
    """
    ctx["gate_reason"] = None

    if ctx.get("route") == "clarification":
        return "clarification"

    if ctx.get("data_quality_failure"):
        ctx["gate_reason"] = "data_quality_failure"
        return "abstention"

    localization = ctx.get("localization") or []
    unsuppressed = [s for s in localization if not s.get("suppressed")]
    if localization and not unsuppressed:
        ctx["gate_reason"] = "segment_too_small_to_disclose"
        return "abstention"

    candidates = ctx.get("candidates") or []
    cleared_evidence_floor = [
        c for c in candidates if len(c.get("evidence_ids") or []) >= EVIDENCE_FLOOR
    ]
    if not cleared_evidence_floor:
        ctx["gate_reason"] = "no_candidate_passed_evidence_floor"
        return "abstention"

    contradicted = [
        c
        for c in cleared_evidence_floor
        if c.get("test_results") and all(t == "failed" for t in c["test_results"])
    ]
    if len(contradicted) == len(cleared_evidence_floor):
        ctx["gate_reason"] = "evidence_contradicts_all_candidates"
        return "abstention"

    if ctx.get("history_periods_ok") is False:
        ctx.setdefault("degradations", [])
        if "sparse_history" not in ctx["degradations"]:
            ctx["degradations"].append("sparse_history")

    return "answer"
