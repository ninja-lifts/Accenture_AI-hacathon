"""Document redaction and prompt-injection flagging.

Two independent jobs, deliberately in one file because they run over the same
corpus at index time:
  1. PII redaction before a document is ever indexed.
  2. Injection pattern flagging - flag and neutralise, never silently drop. A
     flagged document still appears as cited evidence; that visibility IS the
     demo (SC-14)."""

from __future__ import annotations

import re

INJECTION_PATTERNS: list[str] = [
    r"ignore (all )?(previous|prior) instructions",
    r"disregard the (above|system)",
    r"you are now",
    r"print (the )?(customer|user) (emails|list|records)",
    r"output your (system )?prompt",
    r"</?(system|assistant)>",
]

_COMPILED_INJECTION = [(p, re.compile(p, re.IGNORECASE)) for p in INJECTION_PATTERNS]

# PII patterns. Deliberately conservative (over-mask rather than leak) - a
# false-positive mask costs a slightly odd sentence; a false-negative leaks a
# real identifier into an index we then hand to a model.
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[-\s]?)?\d{10}(?!\d)")
_ORDER_ID_RE = re.compile(r"\b(ORD|TCK|CRM|FLD|CHG|REG)-\d{3,6}\b")


def redact(text: str) -> tuple[str, int]:
    """Mask emails, phone numbers and raw order/ticket ids. Return (text, n).

    Order/ticket ids (TCK-4417 etc.) are masked here because the *document*
    text may reference a customer's own order id inline in a sentence, which
    is itself a weak identifier; document_id and evidence_ref.document_id -
    the ids the pipeline cites as evidence - are separate fields, not part of
    this free text, so masking here does not break citation.
    """
    n = 0

    def _sub(pattern: re.Pattern[str], token: str, s: str) -> str:
        nonlocal n
        s, count = pattern.subn(token, s)
        n += count
        return s

    text = _sub(_EMAIL_RE, "[EMAIL_REDACTED]", text)
    text = _sub(_PHONE_RE, "[PHONE_REDACTED]", text)
    text = _sub(_ORDER_ID_RE, "[ID_REDACTED]", text)
    return text, n


def flag_injection(text: str) -> list[str]:
    """Return matched pattern names. Flagging is not exclusion - the snippet
    is still shown to the user, marked, and passed to the narrator which is
    instructed to treat document text as inert (SC-14)."""
    return [pattern for pattern, rx in _COMPILED_INJECTION if rx.search(text)]
