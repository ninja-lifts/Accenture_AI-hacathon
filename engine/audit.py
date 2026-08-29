"""Append-only audit record. One line per run, written before the response is
returned to the user.

Records who asked, what was computed, what was withheld, which documents were
cited, which were flagged, and the code version. In the prototype this is a
JSONL file; in production it is a table with retention. The demo line that
lands: 'everything you just tried is in the audit log.'"""

from __future__ import annotations

from typing import Any


def write(findings: dict[str, Any], path: str = "runs/audit.jsonl") -> None:
    """TODO(Phase 3): append one canonical JSON line. Never rewrite history."""
    raise NotImplementedError
