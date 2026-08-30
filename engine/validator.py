"""The number validator. The single hardest guarantee in the system.

Extracts every numeral from generated narration and asserts each one is present
in (or a declared rounding of) the findings object. Failure regenerates once,
then falls back to a template render.

NEVER weaken this to make a demo pass. If narration keeps failing validation,
the prompt is wrong, not the validator. `findings.telemetry.validator_retries`
is deliberately surfaced - a non-zero count is the guard working, and saying so
out loud scores better than hiding it."""

from __future__ import annotations

import re
from typing import Any

# A numeral, optionally comma-grouped (western OR Indian: both "120,000" and
# "1,20,000" strip to the same digits), optionally decimal, optionally
# followed by a magnitude word or percent sign. The lookbehind excludes
# digits that are really part of an id like "TCK-4417" or "SC-01" - those are
# preceded by <letter><hyphen>, which no genuine numeral in prose is.
_NUM_RE = re.compile(
    r"(?<![\w.])(?<![A-Za-z]-)(-?\d[\d,]*\.?\d*)\s*(%|crore|lakh|million|mn\b|m\b|k\b)?",
    re.IGNORECASE,
)
_MULTIPLIERS = {
    "k": 1_000.0, "lakh": 100_000.0, "crore": 10_000_000.0,
    "m": 1_000_000.0, "mn": 1_000_000.0, "million": 1_000_000.0,
}


def extract_numerals(text: str) -> list[float]:
    """Locale-aware. Handles 8.2%, Rs 3.1 crore, 1,20,000, 12k.

    A '%' suffix does not scale the numeral - "8.2%" extracts as 8.2, matching
    how delta_pct is stored in the findings object (a percentage point value,
    not a 0-1 fraction).
    """
    values: list[float] = []
    for raw, suffix in _NUM_RE.findall(text):
        digits = raw.replace(",", "")
        if digits in ("", "-"):
            continue
        try:
            value = float(digits)
        except ValueError:
            continue
        multiplier = _MULTIPLIERS.get(suffix.lower()) if suffix else None
        if multiplier:
            value *= multiplier
        values.append(value)
    return values


def _collect_findings_numbers(obj: Any, out: set[float]) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.add(float(obj))
    elif isinstance(obj, str):
        # Some findings fields are themselves descriptive text (e.g. a
        # falsification test's or rejected hypothesis's `detail`, e.g.
        # "treated moved -9.2% vs control 0.0% (z=-2.4 ...)") - a numeral the
        # narrator faithfully quotes FROM that text is not invented, so it
        # must be in `allowed` too, not just literal JSON number values.
        out.update(extract_numerals(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_findings_numbers(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect_findings_numbers(v, out)


def _accounted_for(n: float, allowed: set[float], *, rel_tol: float = 0.02, abs_tol: float = 0.05) -> bool:
    """True if n is one of `allowed`, or a declared rounding of one of them.
    Compared on absolute value: prose states magnitude ("fell 8.2%") while the
    findings field is often signed (delta_pct = -8.2) - that sign difference
    is not an invented number, so it must not fail validation."""
    an = abs(n)
    for a in allowed:
        aa = abs(a)
        tol = max(abs_tol, rel_tol * aa)
        if abs(an - aa) <= tol:
            return True
    return False


def _narration_sentences(narration: dict[str, Any]) -> list[tuple[str, str | None]]:
    """(text, tier_from) pairs. `headline` has no tier_from of its own - it is
    the one field allowed to state the run's unscoped movement, by
    construction, so it is never subject to the segment-naming restriction
    below."""
    out: list[tuple[str, str | None]] = []
    headline = narration.get("headline")
    if isinstance(headline, str):
        out.append((headline, None))
    for s in narration.get("sentences", []) or []:
        if isinstance(s, dict) and isinstance(s.get("text"), str):
            out.append((s["text"], s.get("tier_from")))
        elif isinstance(s, str):
            out.append((s, None))
    return out


_DRIVER_TIER_FROM_RE = re.compile(r"^drivers\[(\d+)\]")


def _dimension_values(findings: dict[str, Any]) -> set[str]:
    """Every dimension VALUE named across localization[] - segment names like
    "South" or "Web" that a driver-sourced sentence might claim to describe."""
    values: set[str] = set()
    ans = findings.get("answer")
    if not isinstance(ans, dict):
        return values
    for seg in ans.get("localization") or []:
        for v in (seg.get("dimensions") or {}).values():
            if isinstance(v, str):
                values.add(v)
    return values


def _names_a_segment(text: str, dimension_values: set[str]) -> bool:
    lowered = text.lower()
    return any(re.search(rf"\b{re.escape(v.lower())}\b", lowered) for v in dimension_values)


def _headline_numbers(findings: dict[str, Any]) -> set[float]:
    ans = findings.get("answer")
    if not isinstance(ans, dict):
        return set()
    out: set[float] = set()
    for key in ("headline_delta_pct", "headline_delta_abs"):
        v = ans.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out.add(float(v))
    return out


def _exclude_by_magnitude(
    pool: set[float], to_exclude: set[float], *, rel_tol: float = 0.02, abs_tol: float = 0.05
) -> set[float]:
    """pool minus anything within `_accounted_for`'s own tolerance of an
    excluded value's magnitude - not a literal set difference. A plain
    `pool - to_exclude` misses e.g. `answer.action.expected_impact.value`
    being the same magnitude as `headline_delta_abs` but stored positive
    where the headline is signed negative: two distinct floats to a set,
    same number to a reader, and `_accounted_for` itself is already
    sign-blind (see its own docstring) - this exclusion has to match that or
    it silently fails to close the loophole it exists for."""
    excluded_abs = {abs(v) for v in to_exclude}
    out: set[float] = set()
    for v in pool:
        av = abs(v)
        if any(abs(av - ea) <= max(abs_tol, rel_tol * ea) for ea in excluded_abs):
            continue
        out.add(v)
    return out


def validate(narration: dict[str, Any], findings: dict[str, Any]) -> tuple[bool, list[str]]:
    """-> (ok, unaccounted_numerals).

    `findings` is the completed findings-draft the narrator was given as
    context; every numeral it produced must trace back to a numeral already
    present somewhere in that object (or a declared rounding of one - see
    `_accounted_for`). This also catches the adversarial case: a plausible
    arithmetic *combination* of two real numbers (e.g. summing two real
    percentages into a new one) is rejected, because the combined value was
    never itself a number in the findings object.

    Per-sentence scoping (CHANGELOG.md entry 020): the global `allowed` pool
    above catches invented numbers, but not a REAL number reattached to the
    wrong claim - a live SC-01 narration once said "Net revenue dropped 23.5%
    (Rs 35 lakh) in the South region" when 23.5%/Rs 35L is the category-wide
    headline, not South's own number (South's own contribution is a
    different, smaller figure, elsewhere in `answer.localization`). Every
    digit was real, so the global check passed it. A sentence whose
    `tier_from` is `drivers[N]` and which names a specific segment (matched
    against `answer.localization[].dimensions` values) may not use the
    unscoped `headline_delta_pct`/`headline_delta_abs` - it must reach for
    that segment's own numbers instead. `headline` itself is exempt (see
    `_narration_sentences`): it is the one field meant to state the unscoped
    movement.
    """
    allowed: set[float] = set()
    _collect_findings_numbers(findings, allowed)
    headline_numbers = _headline_numbers(findings)
    dimension_values = _dimension_values(findings)

    unaccounted: list[str] = []
    for text, tier_from in _narration_sentences(narration):
        sentence_allowed = allowed
        if tier_from and _DRIVER_TIER_FROM_RE.match(tier_from) and _names_a_segment(text, dimension_values):
            sentence_allowed = _exclude_by_magnitude(allowed, headline_numbers)
        for n in extract_numerals(text):
            if not _accounted_for(n, sentence_allowed):
                unaccounted.append(f"{n!r} in: {text[:120]!r}")

    return (len(unaccounted) == 0, unaccounted)
