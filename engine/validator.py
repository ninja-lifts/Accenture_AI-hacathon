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
    r"(?<![\w.])(?<![A-Za-z]-)(-?\d[\d,]*\.?\d*)\s*(%|crore|lakh|k\b)?",
    re.IGNORECASE,
)
_MULTIPLIERS = {"k": 1_000.0, "lakh": 100_000.0, "crore": 10_000_000.0}


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


def _narration_text_fields(narration: dict[str, Any]) -> list[str]:
    fields: list[str] = []
    headline = narration.get("headline")
    if isinstance(headline, str):
        fields.append(headline)
    for s in narration.get("sentences", []) or []:
        if isinstance(s, dict) and isinstance(s.get("text"), str):
            fields.append(s["text"])
        elif isinstance(s, str):
            fields.append(s)
    return fields


def validate(narration: dict[str, Any], findings: dict[str, Any]) -> tuple[bool, list[str]]:
    """-> (ok, unaccounted_numerals).

    `findings` is the completed findings-draft the narrator was given as
    context; every numeral it produced must trace back to a numeral already
    present somewhere in that object (or a declared rounding of one - see
    `_accounted_for`). This also catches the adversarial case: a plausible
    arithmetic *combination* of two real numbers (e.g. summing two real
    percentages into a new one) is rejected, because the combined value was
    never itself a number in the findings object.
    """
    allowed: set[float] = set()
    _collect_findings_numbers(findings, allowed)

    unaccounted: list[str] = []
    for text in _narration_text_fields(narration):
        for n in extract_numerals(text):
            if not _accounted_for(n, allowed):
                unaccounted.append(f"{n!r} in: {text[:120]!r}")

    return (len(unaccounted) == 0, unaccounted)
