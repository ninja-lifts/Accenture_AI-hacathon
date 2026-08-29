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


def test_extract_numerals_handles_locale_formats():
    assert extract_numerals("8.2%") == [8.2]
    assert extract_numerals("Rs 3.1 crore") == [31000000.0]
    assert extract_numerals("1,20,000") == [120000.0]
    assert extract_numerals("12k") == [12000.0]
    assert extract_numerals("see TCK-4417 and SC-01") == []
