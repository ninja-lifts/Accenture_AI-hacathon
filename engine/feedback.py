"""Analyst and business-user feedback capture - the substrate for R2
objective 7 ("mechanism to learn from analyst and business-user feedback").

This does not wire a feedback loop into the live pipeline, and it never will
by itself. What it adds: a durable, auditable record of a human confirming,
rejecting or partially confirming a specific driver from a specific run
(runs/feedback.jsonl, append-only, mirroring engine/audit.py exactly), plus a
read-only aggregation that surfaces *candidates* for a governed change - a
tightened detection threshold, a new context-registry entry, the same
mechanism engine/stages/s02_detect.py already uses for SC-03's planned
promotions - for a human to review and commit through the same reviewed,
git-tracked process every other change to a contract goes through in this
repo.

It never edits a contract, the generated database, or retrains the narration
model on its own. Doing any of those automatically would be exactly the kind
of silent drift the tier system (engine/tiers.py) and PROJECT_RULES.md rule 3
("thresholds freeze after the benchmark... tuning a threshold because a
scenario failed is how a benchmark becomes meaningless") both exist to
prevent. A human closes the loop; this module only makes sure the human has
something real to review instead of institutional memory."""

from __future__ import annotations

import datetime as dt
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import ulid

VERDICTS = ("confirmed", "rejected", "partial")

__all__ = ["VERDICTS", "record", "load", "join_with_audit", "review_candidates"]


def record(
    run_id: str,
    driver_id: str,
    verdict: str,
    note: str = "",
    reviewer: dict[str, Any] | None = None,
    path: str = "runs/feedback.jsonl",
) -> dict[str, Any]:
    """Append one feedback record. Never mutates a contract, the generated
    database, or any prior feedback record - append-only, like the audit
    log this is designed to sit next to.

    `run_id` should be a real run_id from runs/audit.jsonl and `driver_id` a
    driver_id from that run's findings object, but neither is cross-checked
    here - feedback can legitimately be recorded before the audit line is in
    front of the reviewer. join_with_audit() does that cross-check when it
    is actually needed, for building a review summary.
    """
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {VERDICTS}, got {verdict!r}")

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "feedback_id": str(ulid.new()),
        "created_at": dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "run_id": run_id,
        "driver_id": driver_id,
        "verdict": verdict,
        "note": note,
        "reviewer": reviewer or {},
    }
    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def load(path: str = "runs/feedback.jsonl") -> list[dict[str, Any]]:
    """Read every feedback record. Empty list, not an error, if the file
    does not exist yet - a fresh clone has received no feedback."""
    p = Path(path)
    if not p.exists():
        return []
    records = []
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def join_with_audit(
    records: list[dict[str, Any]] | None = None,
    feedback_path: str = "runs/feedback.jsonl",
    audit_path: str = "runs/audit.jsonl",
) -> list[dict[str, Any]]:
    """Attach each feedback record's run-level context (kpi, window,
    principal, outcome_branch, ...) from the audit log line it references,
    by run_id. A feedback record whose run_id has no matching audit line (a
    bad id, or an audit log that predates this feature) keeps
    `audit_context: None` rather than being silently dropped - a broken
    reference is itself something a reviewer should see.
    """
    if records is None:
        records = load(feedback_path)

    audit_by_run: dict[str, dict[str, Any]] = {}
    audit_file = Path(audit_path)
    if audit_file.exists():
        with audit_file.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    audit_by_run[rec["run_id"]] = rec

    return [{**fb, "audit_context": audit_by_run.get(fb["run_id"])} for fb in records]


def review_candidates(
    records: list[dict[str, Any]] | None = None,
    feedback_path: str = "runs/feedback.jsonl",
    audit_path: str = "runs/audit.jsonl",
    min_rejections: int = 2,
) -> list[dict[str, Any]]:
    """Surface drivers with enough independent rejections to be worth a
    human reviewing for a governed change - never applies one itself.

    Grouped by (kpi, driver_id) rather than driver_id alone: driver_id is
    only unique within a single run's own findings object, so the same
    driver_id string can legitimately name an unrelated driver under a
    different KPI's pipeline output.

    Monotone by construction: a driver's rejection_count can only grow as
    more feedback is recorded, so a driver already flagged can never become
    unflagged by later feedback - the same property
    tests/test_tiers_monotone.py checks for confidence tiers,
    checked here for review flagging in tests/test_feedback.py.
    """
    joined = join_with_audit(records, feedback_path, audit_path)

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for fb in joined:
        if fb["verdict"] != "rejected":
            continue
        ctx = fb.get("audit_context") or {}
        kpi = ctx.get("kpi", "unknown")
        groups[(kpi, fb["driver_id"])].append(fb)

    candidates = []
    for (kpi, driver_id), entries in sorted(groups.items()):
        if len(entries) < min_rejections:
            continue
        candidates.append(
            {
                "kpi": kpi,
                "driver_id": driver_id,
                "rejection_count": len(entries),
                "run_ids": sorted({e["run_id"] for e in entries}),
                "notes": [e["note"] for e in entries if e.get("note")],
                "suggested_action": (
                    f"{len(entries)} independent rejections of driver '{driver_id}' on "
                    f"'{kpi}'. Review the cited runs; if these are recurring false "
                    f"positives from the same known cause, consider a context-registry "
                    f"entry (the mechanism SC-03 already uses) or a tightened "
                    f"detection.materiality threshold in contracts/{kpi}.yaml. Neither "
                    f"is applied automatically - PROJECT_RULES.md rule 3 freezes "
                    f"thresholds outside a reviewed, committed change."
                ),
            }
        )
    return candidates


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("record", help="record one analyst/business-user verdict on a driver")
    rec.add_argument("run_id", help="a run_id from runs/audit.jsonl")
    rec.add_argument("driver_id", help="a driver_id from that run's findings object")
    rec.add_argument("verdict", choices=VERDICTS)
    rec.add_argument("--note", default="")
    rec.add_argument("--reviewer-role", default="analyst")
    rec.add_argument("--reviewer-id", default="")

    sub.add_parser("review", help="print drivers with enough rejected feedback to warrant a human review")

    args = parser.parse_args()

    if args.command == "record":
        entry = record(
            args.run_id,
            args.driver_id,
            args.verdict,
            note=args.note,
            reviewer={"role": args.reviewer_role, "id": args.reviewer_id},
        )
        print(f"recorded {entry['feedback_id']} ({entry['verdict']} on {entry['driver_id']} / {entry['run_id']})")
    elif args.command == "review":
        candidates = review_candidates()
        if not candidates:
            print("no driver has enough rejected feedback to flag for review yet.")
            return
        for c in candidates:
            print(f"[{c['kpi']}] {c['driver_id']} - {c['rejection_count']} rejections across {len(c['run_ids'])} runs")
            print(f"  {c['suggested_action']}")


if __name__ == "__main__":
    main()
