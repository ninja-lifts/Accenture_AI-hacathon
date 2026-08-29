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


def assign(claim_kind: str, support: dict[str, Any], degradations: list[str]) -> str:
    """TODO(Phase 4): table lookup. `degradations` are declared caps from
    upstream stages (sparse history caps at HYPOTHESIS, no clean pre-period
    caps at CORRELATED, suppressed cell caps at UNKNOWN)."""
    raise NotImplementedError
