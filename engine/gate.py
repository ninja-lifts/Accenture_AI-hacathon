"""The answer / abstain / clarify gate. The most important 100 lines here.

The invariant: exactly one branch is populated. Never a hedged blend. The
product's whole claim to trustworthiness is that it can decline, so the decline
path must be as engineered as the answer path."""

from __future__ import annotations

from typing import Any

EVIDENCE_FLOOR = 2          # cited docs required before a driver may be EVIDENCED
MIN_DRIVER_TIER = "TESTED"  # weakest tier permitted on the answer branch


def decide(findings_draft: dict[str, Any]) -> str:
    """TODO(Phase 4): -> 'answer' | 'abstention' | 'clarification'.

    Abstain when: no candidate clears the evidence floor; evidence contradicts
    every candidate; history below contract minimum; a data-quality check
    failed; or the movement localises only to a suppressed cell.
    """
    raise NotImplementedError
