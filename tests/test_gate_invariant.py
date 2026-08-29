"""The one test that must never be deleted.

Exactly one outcome branch is populated on every run. If this test is weakened
to make a demo pass, the product no longer means anything.
"""

from __future__ import annotations

import datetime as dt

from engine import pipeline

_TODAY = dt.date(2026, 8, 22)

_CASES = [
    dict(
        trigger="alert_sweep", persona="category_manager", role_id="cm_audio", kpi="net_revenue",
        window={"focal_start": "2026-08-08", "focal_end": "2026-08-14",
                "comparison_start": "2026-08-01", "comparison_end": "2026-08-07", "grain": "day"},
        investigate=True,
    ),
    dict(
        trigger="alert_sweep", persona="cfo", kpi="net_revenue",
        window={"focal_start": "2026-07-20", "focal_end": "2026-07-26",
                "comparison_start": "2026-07-13", "comparison_end": "2026-07-19", "grain": "day"},
        investigate=False,
    ),
    dict(trigger="user_question", persona="cfo", question="why are sales down in the south?"),
]


def _branches_populated(findings: dict) -> list[str]:
    outcome = findings["outcome"]
    return [k for k in ("answer", "abstention", "clarification") if outcome[k] is not None]


def test_exactly_one_branch_populated():
    for case in _CASES:
        findings = pipeline.run(today=_TODAY, **case)
        if findings.get("kind") == "no_alert":
            continue
        populated = _branches_populated(findings)
        assert len(populated) == 1, f"{case}: expected exactly one branch, got {populated}"
        assert findings["outcome"]["branch"] in populated
