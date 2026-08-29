"""Confidence tier assignment. Pure rules, no model, no heuristic fudge.

The ladder, strongest first:
  VERIFIED    recomputed from source arithmetic
  EVIDENCED   supported by >= N cited documents inside the movement window
  TESTED      survived a falsification test
  CORRELATED  statistical association only
  HYPOTHESIS  plausible mechanism, no support
  UNKNOWN     refuse to grade

Two properties matter more than the exact thresholds:
  - the mapping is a lookup table a judge can read in 30 seconds
  - it is monotone: removing evidence can never raise a tier
tests/test_tiers.py asserts monotonicity over generated inputs."""

from __future__ import annotations

from typing import Any

TIER_ORDER = ["UNKNOWN", "HYPOTHESIS", "CORRELATED", "TESTED", "EVIDENCED", "VERIFIED"]

# Minimum cited documents, inside the movement window, before a claim may be
# EVIDENCED. Shared with engine/gate.py's "no candidate clears the evidence
# floor" abstention check - one number, defined once.
EVIDENCE_FLOOR = 2

# Caps a degradation declared upstream may impose. Applying the tightest one
# present in `degradations` is what makes degradation announce itself instead
# of silently producing a confident-looking answer built on weak ground.
_DEGRADATION_CAPS = {
    "sparse_history": "HYPOTHESIS",
    "no_clean_pre_period": "CORRELATED",
    "suppressed_cell": "UNKNOWN",
}


def assign(claim_kind: str, support: dict[str, Any], degradations: list[str]) -> str:
    """Rule-table tier assignment. Pure lookup, no model, no fudge factor.

    `support` describes what backs the claim:
      verified        bool  - recomputed from source arithmetic (Stage 04)
      evidence_ids    list  - cited document ids inside the movement window
      test_results    list  - falsification test outcomes ("survived"/"failed"/"inconclusive")
      correlated      bool  - statistical association observed (detect/localize)
      hypothesis      bool  - a plausible mechanism was proposed, nothing more

    `degradations` are declared caps from upstream stages: sparse history
    caps at HYPOTHESIS, no clean pre-period caps at CORRELATED, a suppressed
    cell caps at UNKNOWN. The result is the BEST tier the support earns,
    capped by the TIGHTEST applicable degradation - which is what makes this
    monotone: taking evidence away can only remove an earned tier or tighten
    a cap, never raise the result (tests/test_tiers_monotone.py).
    """
    earned = ["UNKNOWN"]
    if support.get("verified"):
        earned.append("VERIFIED")
    if len(support.get("evidence_ids", []) or []) >= EVIDENCE_FLOOR:
        earned.append("EVIDENCED")
    if any(t == "survived" for t in support.get("test_results", []) or []):
        earned.append("TESTED")
    if support.get("correlated"):
        earned.append("CORRELATED")
    if support.get("hypothesis"):
        earned.append("HYPOTHESIS")

    tier = max(earned, key=TIER_ORDER.index)

    applicable_caps = [_DEGRADATION_CAPS[d] for d in degradations if d in _DEGRADATION_CAPS]
    if applicable_caps:
        tightest_cap = min(applicable_caps, key=TIER_ORDER.index)
        if TIER_ORDER.index(tier) > TIER_ORDER.index(tightest_cap):
            tier = tightest_cap

    return tier
