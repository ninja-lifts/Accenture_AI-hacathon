"""Narration containing a number absent from the findings object must be rejected.

Includes the adversarial case: a number that is a plausible arithmetic
combination of two real ones.
"""

from __future__ import annotations

from engine.validator import extract_numerals, validate

FINDINGS = {
    "answer": {
        "headline_delta_pct": -8.2,
        "headline_delta_abs": -3100000,
        "drivers": [{"driver_id": "D1", "share_of_movement_pct": 62}],
    }
}


def test_valid_narration_passes():
    narration = {
        "headline": "Net revenue fell 8.2% (Rs 3,100,000) in the week.",
        "sentences": [{"text": "The primary driver explains about 62% of the movement.", "tier_from": "drivers[0]"}],
    }
    ok, unaccounted = validate(narration, FINDINGS)
    assert ok, unaccounted


def test_invented_number_rejected():
    narration = {
        "headline": "Net revenue fell 8.2%.",
        "sentences": [{"text": "This is expected to cost the business Rs 9,400,000 this quarter.", "tier_from": "drivers[0]"}],
    }
    ok, unaccounted = validate(narration, FINDINGS)
    assert not ok
    assert unaccounted


def test_plausible_arithmetic_combination_rejected():
    """9,400,000 is not in FINDINGS anywhere, but LOOKS like it could be
    derived (e.g. 3,100,000 * 3-ish, or some other combination the model
    might invent). The validator must reject it precisely because it is not
    itself a number that was ever computed - being plausible is not enough."""
    combined = 3100000 + 62 * 10000  # a number that "looks" derived, isn't real
    narration = {
        "headline": f"Net revenue fell 8.2%, a total impact of Rs {combined:,}.",
        "sentences": [{"text": "See headline.", "tier_from": "headline"}],
    }
    ok, unaccounted = validate(narration, FINDINGS)
    assert not ok
    assert unaccounted


LOCALIZED_FINDINGS = {
    "answer": {
        "headline_delta_pct": -23.5,
        "headline_delta_abs": -3499600,
        "localization": [
            {
                "dimensions": {"category": "Audio", "region": "South"},
                "contribution_abs": -2724103,
                "contribution_pct": 77.8,
            }
        ],
        "drivers": [{"driver_id": "DRIVER-PRIMARY", "share_of_movement_pct": None}],
    }
}


def test_driver_sentence_naming_a_segment_rejects_unscoped_headline_numbers():
    """The exact failure mode from a live SC-01 run (CHANGELOG.md entry 020):
    a drivers[0] sentence names "South" but cites the category-wide headline
    numbers (23.5%, Rs 35 lakh) instead of South's own localization
    contribution (77.8%, Rs 27.24 lakh). Every digit is individually real -
    both numbers are the object's real headline_delta_pct/_abs - so the old
    global-pool check passed this. It must not anymore."""
    narration = {
        "headline": "Net revenue fell 23.5% (Rs 35 lakh) in the week.",
        "sentences": [
            {
                "text": "Net revenue dropped 23.5% (Rs 35 lakh) in the South region for the Audio category.",
                "tier_from": "drivers[0]",
            }
        ],
    }
    ok, unaccounted = validate(narration, LOCALIZED_FINDINGS)
    assert not ok, "a drivers[N] sentence naming South must not be allowed to cite the unscoped headline numbers"
    assert unaccounted


def test_driver_sentence_naming_a_segment_with_its_own_numbers_passes():
    """Same sentence shape as above, but correctly scoped: South's own
    localization numbers instead of the category-wide headline's. Confirms
    the fix rejects the wrong pairing without also rejecting the right one."""
    narration = {
        "headline": "Net revenue fell 23.5% (Rs 35 lakh) in the week.",
        "sentences": [
            {
                "text": "The South region, within Audio, accounts for 77.8% of that decline (Rs 27.24 lakh).",
                "tier_from": "drivers[0]",
            }
        ],
    }
    ok, unaccounted = validate(narration, LOCALIZED_FINDINGS)
    assert ok, unaccounted


def test_headline_field_itself_is_exempt_from_segment_scoping():
    """`headline` has no tier_from - it is the one field meant to state the
    unscoped movement, so naming a segment there does not trigger the
    drivers[N] restriction (there is nothing to exempt it FROM narrowing to,
    unlike a drivers[N] sentence which has the segment's own numbers to use
    instead)."""
    narration = {"headline": "Net revenue fell 23.5% (Rs 35 lakh), concentrated in the South.", "sentences": []}
    ok, unaccounted = validate(narration, LOCALIZED_FINDINGS)
    assert ok, unaccounted


def test_extract_numerals_handles_locale_formats():
    assert extract_numerals("8.2%") == [8.2]
    assert extract_numerals("Rs 3.1 crore") == [31000000.0]
    assert extract_numerals("1,20,000") == [120000.0]
    assert extract_numerals("12k") == [12000.0]
    assert extract_numerals("see TCK-4417 and SC-01") == []
