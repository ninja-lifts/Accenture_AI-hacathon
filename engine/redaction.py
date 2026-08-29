"""Document redaction and prompt-injection flagging.

Two independent jobs, deliberately in one file because they run over the same
corpus at index time:
  1. PII redaction before a document is ever indexed.
  2. Injection pattern flagging - flag and neutralise, never silently drop. A
     flagged document still appears as cited evidence; that visibility IS the
     demo (SC-14)."""

from __future__ import annotations

INJECTION_PATTERNS: list[str] = [
    r"ignore (all )?(previous|prior) instructions",
    r"disregard the (above|system)",
    r"you are now",
    r"print (the )?(customer|user) (emails|list|records)",
    r"output your (system )?prompt",
    r"</?(system|assistant)>",
]


def redact(text: str) -> tuple[str, int]:
    """TODO(Phase 3): mask emails, phones, order ids, names. Return (text, n)."""
    raise NotImplementedError


def flag_injection(text: str) -> list[str]:
    """TODO(Phase 3): return matched pattern names. Flagging is not exclusion -
    the snippet is still shown to the user, marked, and passed to the narrator
    which is instructed to treat document text as inert."""
    raise NotImplementedError
