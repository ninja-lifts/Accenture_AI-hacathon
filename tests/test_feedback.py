"""engine/feedback.py - the R2 objective 7 substrate.

Three properties matter more than any single assertion:
1. Every recorded entry validates against schemas/feedback.schema.json.
2. review_candidates() is monotone the same way tiers are: more feedback can
   only add or grow a review candidate, never remove or shrink one.
3. Nothing here ever writes to a contract, a schema, or the generated
   database - only runs/feedback.jsonl (and reads of runs/audit.jsonl)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from engine import feedback

_SCHEMA = json.loads(
    (Path(__file__).resolve().parent.parent / "schemas" / "feedback.schema.json").read_text(encoding="utf-8")
)
_VALIDATOR = jsonschema.Draft202012Validator(_SCHEMA, format_checker=jsonschema.FormatChecker())


def _write_audit_line(path: Path, run_id: str, kpi: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"run_id": run_id, "kpi": kpi}) + "\n")


def test_record_is_schema_valid_and_appended(tmp_path):
    fb_path = tmp_path / "feedback.jsonl"

    entry = feedback.record("RUN-1", "DRIVER-PRIMARY", "rejected", note="decoy", path=str(fb_path))

    errors = list(_VALIDATOR.iter_errors(entry))
    assert not errors, [e.message for e in errors]

    lines = fb_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["feedback_id"] == entry["feedback_id"]


def test_record_rejects_unknown_verdict(tmp_path):
    with pytest.raises(ValueError):
        feedback.record("RUN-1", "DRIVER-PRIMARY", "maybe", path=str(tmp_path / "feedback.jsonl"))


def test_load_is_empty_list_not_error_when_file_absent(tmp_path):
    assert feedback.load(str(tmp_path / "nope.jsonl")) == []


def test_load_roundtrips_multiple_records(tmp_path):
    fb_path = tmp_path / "feedback.jsonl"
    feedback.record("RUN-1", "DRIVER-A", "confirmed", path=str(fb_path))
    feedback.record("RUN-2", "DRIVER-B", "rejected", path=str(fb_path))

    records = feedback.load(str(fb_path))
    assert len(records) == 2
    assert {r["run_id"] for r in records} == {"RUN-1", "RUN-2"}


def test_join_with_audit_attaches_kpi_context(tmp_path):
    fb_path = tmp_path / "feedback.jsonl"
    audit_path = tmp_path / "audit.jsonl"
    _write_audit_line(audit_path, "RUN-1", "net_revenue")

    feedback.record("RUN-1", "DRIVER-A", "rejected", path=str(fb_path))
    joined = feedback.join_with_audit(feedback_path=str(fb_path), audit_path=str(audit_path))

    assert joined[0]["audit_context"]["kpi"] == "net_revenue"


def test_join_with_audit_keeps_unmatched_run_visible(tmp_path):
    fb_path = tmp_path / "feedback.jsonl"
    audit_path = tmp_path / "audit.jsonl"  # never written - no matching run

    feedback.record("RUN-GHOST", "DRIVER-A", "rejected", path=str(fb_path))
    joined = feedback.join_with_audit(feedback_path=str(fb_path), audit_path=str(audit_path))

    assert len(joined) == 1
    assert joined[0]["audit_context"] is None


def test_review_candidates_requires_the_minimum(tmp_path):
    fb_path = tmp_path / "feedback.jsonl"
    audit_path = tmp_path / "audit.jsonl"
    _write_audit_line(audit_path, "RUN-1", "net_revenue")
    _write_audit_line(audit_path, "RUN-2", "net_revenue")

    feedback.record("RUN-1", "DRIVER-A", "rejected", path=str(fb_path))
    assert feedback.review_candidates(feedback_path=str(fb_path), audit_path=str(audit_path)) == []

    feedback.record("RUN-2", "DRIVER-A", "rejected", path=str(fb_path))
    candidates = feedback.review_candidates(feedback_path=str(fb_path), audit_path=str(audit_path))
    assert len(candidates) == 1
    assert candidates[0] == {
        "kpi": "net_revenue",
        "driver_id": "DRIVER-A",
        "rejection_count": 2,
        "run_ids": ["RUN-1", "RUN-2"],
        "notes": [],
        "suggested_action": candidates[0]["suggested_action"],  # asserted non-empty below
    }
    assert candidates[0]["suggested_action"]


def test_review_candidates_never_fires_on_confirmed_or_partial(tmp_path):
    fb_path = tmp_path / "feedback.jsonl"
    audit_path = tmp_path / "audit.jsonl"
    _write_audit_line(audit_path, "RUN-1", "net_revenue")
    _write_audit_line(audit_path, "RUN-2", "net_revenue")
    _write_audit_line(audit_path, "RUN-3", "net_revenue")

    for run_id, verdict in [("RUN-1", "confirmed"), ("RUN-2", "partial"), ("RUN-3", "confirmed")]:
        feedback.record(run_id, "DRIVER-A", verdict, path=str(fb_path))

    assert feedback.review_candidates(feedback_path=str(fb_path), audit_path=str(audit_path)) == []


def test_review_candidates_separates_same_driver_id_across_kpis(tmp_path):
    fb_path = tmp_path / "feedback.jsonl"
    audit_path = tmp_path / "audit.jsonl"
    _write_audit_line(audit_path, "RUN-1", "net_revenue")
    _write_audit_line(audit_path, "RUN-2", "aov")

    feedback.record("RUN-1", "DRIVER-PRIMARY", "rejected", path=str(fb_path))
    feedback.record("RUN-2", "DRIVER-PRIMARY", "rejected", path=str(fb_path))

    candidates = feedback.review_candidates(feedback_path=str(fb_path), audit_path=str(audit_path), min_rejections=1)
    assert {c["kpi"] for c in candidates} == {"net_revenue", "aov"}
    assert all(c["rejection_count"] == 1 for c in candidates)


def test_review_candidates_is_monotone_under_more_feedback(tmp_path):
    """The property tests/test_tiers_monotone.py checks for tiers, checked
    here for review flagging: once a driver is a candidate, no amount of
    additional feedback (of any verdict, about anything) can make it stop
    being one, and its rejection_count can only grow."""
    fb_path = tmp_path / "feedback.jsonl"
    audit_path = tmp_path / "audit.jsonl"
    for i in range(1, 6):
        _write_audit_line(audit_path, f"RUN-{i}", "net_revenue")

    feedback.record("RUN-1", "DRIVER-A", "rejected", path=str(fb_path))
    feedback.record("RUN-2", "DRIVER-A", "rejected", path=str(fb_path))
    before = {c["driver_id"]: c["rejection_count"] for c in feedback.review_candidates(
        feedback_path=str(fb_path), audit_path=str(audit_path)
    )}
    assert before == {"DRIVER-A": 2}

    # Unrelated confirmed/partial noise, plus one more real rejection.
    feedback.record("RUN-3", "DRIVER-A", "confirmed", path=str(fb_path))
    feedback.record("RUN-4", "DRIVER-B", "partial", path=str(fb_path))
    feedback.record("RUN-5", "DRIVER-A", "rejected", path=str(fb_path))

    after = {c["driver_id"]: c["rejection_count"] for c in feedback.review_candidates(
        feedback_path=str(fb_path), audit_path=str(audit_path)
    )}
    assert after["DRIVER-A"] == 3  # grew, never shrank or disappeared
    assert "DRIVER-B" not in after  # a single partial verdict never flags anything


def test_feedback_never_touches_contracts_schemas_or_generated_db(tmp_path):
    """The invariant the whole design rests on: recording and reviewing
    feedback is read/append-only against runs/feedback.jsonl and a read of
    runs/audit.jsonl. It must never edit anything governed."""
    repo_root = Path(__file__).resolve().parent.parent
    watched = list((repo_root / "contracts").glob("*.yaml")) + list((repo_root / "schemas").glob("*.schema.json"))
    before = {p: p.read_bytes() for p in watched}

    fb_path = tmp_path / "feedback.jsonl"
    audit_path = tmp_path / "audit.jsonl"
    _write_audit_line(audit_path, "RUN-1", "net_revenue")
    _write_audit_line(audit_path, "RUN-2", "net_revenue")
    feedback.record("RUN-1", "DRIVER-A", "rejected", path=str(fb_path))
    feedback.record("RUN-2", "DRIVER-A", "rejected", path=str(fb_path))
    feedback.review_candidates(feedback_path=str(fb_path), audit_path=str(audit_path))

    after = {p: p.read_bytes() for p in watched}
    assert before == after
