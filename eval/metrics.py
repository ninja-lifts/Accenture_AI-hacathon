"""Metric definitions. Written once, used by the harness and quoted in the README.

Localization (Stage 03) - comparable to published baselines:
    f1_localization      set-F1 between predicted and true cell set
    exact_match          predicted cell set == true cell set

Root cause (whole pipeline) - our contribution, no published baseline:
    rca_top1             true cause is the highest-ranked driver - computed
                          inline in eval/harness.py::score_scenario as an
                          exact true_segment match on the top driver, not by
                          a function here: the engine never sees the
                          generator's internal cause ids (by design), so
                          there is nothing a true_cause_id-keyed function in
                          this module could actually check
    rca_hit_at_2         true cause is in the top 2 drivers

Retrieval (Stage 05):
    evidence_recall_at_5 share of manifest evidence docs in the top 5

Trust behaviour - the metrics that make this a trust product:
    abstention_precision of runs that abstained, share that SHOULD have
    abstention_recall    of runs that should abstain, share that did
    hallucinated_cause_rate   runs asserting a cause where none was planted.
                              TARGET: 0. This is the headline number.

Cost / latency:
    p50_latency_ms, p95_latency_ms, usd_per_run

TODO(Phase 6).
"""

from __future__ import annotations

from typing import Any


def localization_set(findings: dict[str, Any]) -> set[tuple[str, str]]:
    """The predicted cell set as a set of (dim, value) pairs, from the
    top-ranked, non-suppressed localization entry - or, if the top entry IS
    suppressed, from its rolled-up parent (SC-15: scored at the disclosed
    granularity, never penalised for suppressing correctly)."""
    if findings.get("kind") == "no_alert" or findings["outcome"]["branch"] != "answer":
        return set()
    loc = findings["outcome"]["answer"]["localization"]
    if not loc:
        return set()
    top = next((s for s in loc if not s["suppressed"]), loc[0])
    return {(k, v) for k, v in top["dimensions"].items()}


def f1_localization(predicted: set[tuple[str, str]], true_segment: dict[str, Any] | None) -> float:
    true_set = {(k, v) for k, v in (true_segment or {}).items() if v is not None}
    if not true_set and not predicted:
        return 1.0
    if not true_set or not predicted:
        return 0.0
    tp = len(predicted & true_set)
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(true_set) if true_set else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def exact_match(predicted: set[tuple[str, str]], true_segment: dict[str, Any] | None) -> bool:
    true_set = {(k, v) for k, v in (true_segment or {}).items() if v is not None}
    return predicted == true_set


def rca_hit_at_2(findings: dict[str, Any], true_segment: dict[str, Any] | None) -> bool:
    if findings.get("kind") == "no_alert" or findings["outcome"]["branch"] != "answer":
        return False
    true_set = {(k, v) for k, v in (true_segment or {}).items() if v is not None}
    if not true_set:
        return False
    loc = findings["outcome"]["answer"]["localization"]
    for seg in loc[:2]:
        if {(k, v) for k, v in seg["dimensions"].items()} & true_set:
            return True
    return False


def evidence_recall_at_5(findings: dict[str, Any], true_evidence_ids: list[str]) -> float | None:
    if not true_evidence_ids:
        return None
    if findings.get("kind") == "no_alert" or findings["outcome"]["branch"] not in ("answer",):
        cited: list[str] = []
    else:
        cited = []
        for d in findings["outcome"]["answer"]["drivers"]:
            cited.extend(e["document_id"] for e in d.get("evidence", []))
    top5 = set(cited[:5])
    hit = len(top5 & set(true_evidence_ids))
    return hit / len(true_evidence_ids)


def hallucinated_cause(findings: dict[str, Any], planted: bool) -> bool:
    """True if the run asserted a cause (answer branch, tier >= CORRELATED)
    on a scenario where ground_truth.planted == false. This is the number
    the whole submission is judged on; target 0."""
    if planted:
        return False
    if findings.get("kind") == "no_alert":
        return False
    branch = findings["outcome"]["branch"]
    if branch != "answer":
        return False
    weak_tiers = {"HYPOTHESIS", "UNKNOWN"}
    for d in findings["outcome"]["answer"]["drivers"]:
        if d["tier"] not in weak_tiers:
            return True
    return False
