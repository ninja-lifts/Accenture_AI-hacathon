"""Removing evidence must never raise a tier.

Property test over generated support objects. Cheap to write, and it is the
proof that tiers are rules rather than vibes.
"""

from __future__ import annotations

import itertools
import random

from engine.tiers import TIER_ORDER, assign

_SUPPORT_FLAGS = ["verified", "correlated", "hypothesis"]
_EVIDENCE_COUNTS = [0, 1, 2, 3]
_TEST_RESULT_SETS = [[], ["survived"], ["failed"], ["survived", "failed"]]
_DEGRADATION_SETS = [[], ["sparse_history"], ["no_clean_pre_period"], ["suppressed_cell"]]


def _support(flags: set[str], evidence_count: int, test_results: list[str]) -> dict:
    return {
        **{f: (f in flags) for f in _SUPPORT_FLAGS},
        "evidence_ids": [f"E{i}" for i in range(evidence_count)],
        "test_results": test_results,
    }


def test_tier_monotonicity():
    for evidence_count, test_results, degradations in itertools.product(
        _EVIDENCE_COUNTS, _TEST_RESULT_SETS, _DEGRADATION_SETS
    ):
        for r in range(len(_SUPPORT_FLAGS) + 1):
            for flags in itertools.combinations(_SUPPORT_FLAGS, r):
                full = _support(set(flags), evidence_count, test_results)
                full_tier = assign("driver", full, degradations)

                # Removing ANY one piece of evidence must never raise the tier.
                if evidence_count > 0:
                    less = _support(set(flags), evidence_count - 1, test_results)
                    assert TIER_ORDER.index(assign("driver", less, degradations)) <= TIER_ORDER.index(full_tier)
                if test_results:
                    less = _support(set(flags), evidence_count, test_results[:-1])
                    assert TIER_ORDER.index(assign("driver", less, degradations)) <= TIER_ORDER.index(full_tier)
                for f in flags:
                    less = _support(set(flags) - {f}, evidence_count, test_results)
                    assert TIER_ORDER.index(assign("driver", less, degradations)) <= TIER_ORDER.index(full_tier)


def test_degradation_never_raises_tier():
    rng = random.Random(20260829)
    for _ in range(200):
        flags = set(rng.sample(_SUPPORT_FLAGS, k=rng.randint(0, len(_SUPPORT_FLAGS))))
        support = _support(flags, rng.choice(_EVIDENCE_COUNTS), rng.choice(_TEST_RESULT_SETS))
        undegraded = assign("driver", support, [])
        for degradations in _DEGRADATION_SETS[1:]:
            degraded = assign("driver", support, degradations)
            assert TIER_ORDER.index(degraded) <= TIER_ORDER.index(undegraded)
