"""Metric definitions. Written once, used by the harness and quoted in the README.

Localization (Stage 03) - comparable to published baselines:
    f1_localization      set-F1 between predicted and true cell set
    exact_match          predicted cell set == true cell set

Root cause (whole pipeline) - our contribution, no published baseline:
    rca_top1             true cause is the highest-ranked driver
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
