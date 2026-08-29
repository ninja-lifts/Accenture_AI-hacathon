"""Append-only audit record. One line per run, written before the response is
returned to the user.

Records who asked, what was computed, what was withheld, which documents were
cited, which were flagged, and the code version. In the prototype this is a
JSONL file; in production it is a table with retention. The demo line that
lands: 'everything you just tried is in the audit log.'"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write(findings: dict[str, Any], path: str = "runs/audit.jsonl") -> None:
    """Append one canonical JSON line. Never rewrite history.

    The audit record is a projection of the findings object, not a copy: who
    asked, what was computed, what was withheld, which documents were cited or
    flagged, and the code version - enough to answer "what did this run see
    and do" without re-serialising the whole (potentially large) object.
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    outcome = findings["outcome"]
    branch = outcome["branch"]
    driver_ids: list[str] = []
    evidence_ids: list[str] = []
    if branch == "answer" and outcome["answer"]:
        for d in outcome["answer"]["drivers"]:
            driver_ids.append(d["driver_id"])
            evidence_ids.extend(e["document_id"] for e in d.get("evidence", []))

    record = {
        "run_id": findings["run_id"],
        "created_at": findings["created_at"],
        "code_version": findings["provenance"]["code_version"],
        "principal": findings["request"]["principal"],
        "trigger": findings["request"]["trigger"],
        "raw_question": findings["request"].get("raw_question"),
        "kpi": findings["kpi"]["id"],
        "window": findings["window"],
        "outcome_branch": branch,
        "driver_ids": driver_ids,
        "evidence_cited": sorted(set(evidence_ids)),
        "security": findings["security"],
        "telemetry": {
            "total_ms": findings["telemetry"]["total_ms"],
            "llm_calls": findings["telemetry"]["llm_calls"],
            "estimated_cost_usd": findings["telemetry"]["estimated_cost_usd"],
        },
        "replay_mode": findings["provenance"]["replay_mode"],
    }

    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
