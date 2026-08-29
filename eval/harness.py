"""Scenario harness. Runs every scenario in the injection manifest through the
real pipeline and scores the output against ground truth.

Runs in CI on every push. The scorecard it emits is committed, misses
included - a scorecard that only ever shows wins is not evidence, it is
marketing.

Usage:
    python -m eval.harness --scenarios all --out eval/scorecard.md
    python -m eval.harness --scenarios SC-01,SC-08 --verbose
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from typing import Any

import yaml

from engine import pipeline
from eval import metrics

TODAY = dt.date(2026, 8, 22)

# How a real user/alert naturally encounters each scenario - persona, kpi and
# (where relevant) a pre-scoped segment. This is a run-time QUERY CONTEXT
# choice, not ground truth: it never touches data/injection_manifest.yaml and
# carries none of the true_segment/true_cause_id fields the engine is scored
# against. SC-02/03/08 deliberately run as a blind national alert sweep
# (investigate=False) because that IS the behaviour under test for them.
SCENARIO_RUN_CONFIG: dict[str, dict[str, Any]] = {
    "SC-01": dict(trigger="alert_sweep", persona="category_manager", role_id="cm_audio", kpi="net_revenue", investigate=True),
    "SC-02": dict(trigger="alert_sweep", persona="cfo", kpi="net_revenue", investigate=False),
    "SC-03": dict(trigger="alert_sweep", persona="cfo", kpi="aov", investigate=False),
    "SC-04": dict(trigger="alert_sweep", persona="analyst", kpi="conversion_rate", segment={"channel": "Web"}, investigate=True),
    "SC-05": dict(trigger="alert_sweep", persona="analyst", kpi="net_revenue", segment={"channel": "App"}, investigate=True),
    "SC-06": dict(trigger="alert_sweep", persona="analyst", kpi="conversion_rate", segment={"channel": "App"}, investigate=True),
    "SC-07": dict(trigger="alert_sweep", persona="analyst", kpi="net_revenue", segment={"region": "West"}, investigate=True),
    "SC-08": dict(trigger="alert_sweep", persona="cfo", kpi="net_revenue", investigate=False),
    "SC-09": dict(trigger="alert_sweep", persona="cfo", kpi="net_revenue", investigate=True),
    "SC-10": dict(trigger="alert_sweep", persona="analyst", kpi="net_revenue", segment={"category": "Smart Home"}, investigate=True),
    "SC-11": dict(trigger="alert_sweep", persona="analyst", kpi="conversion_rate", segment={"region": "North", "channel": "Web"}, investigate=True),
    "SC-12": dict(trigger="alert_sweep", persona="analyst", kpi="net_revenue", segment={"region": "East", "category": "Large Appliances"}, investigate=True),
    "SC-13": dict(trigger="alert_sweep", persona="category_manager", role_id="cm_audio", kpi="net_revenue", investigate=True),
    "SC-14": dict(trigger="alert_sweep", persona="analyst", kpi="net_revenue", segment={"region": "West", "channel": "App"}, investigate=True),
    "SC-15": dict(trigger="alert_sweep", persona="analyst", kpi="net_revenue", segment={"region": "North-East", "category": "Large Appliances"}, investigate=True),
    "SC-16": dict(trigger="alert_sweep", persona="analyst", kpi="net_revenue", segment={"channel": "Partner"}, investigate=True),
    "SC-17": dict(trigger="user_question", persona="cfo", question="why are sales down in the south?"),
}


def _window_for(scenario: dict[str, Any]) -> dict[str, str]:
    fw = scenario["focal_window"]
    start = dt.date.fromisoformat(fw["start"])
    end = dt.date.fromisoformat(fw["end"])
    span = (end - start).days + 1
    cmp_end = start - dt.timedelta(days=1)
    cmp_start = cmp_end - dt.timedelta(days=span - 1)
    return {
        "focal_start": start.isoformat(), "focal_end": end.isoformat(),
        "comparison_start": cmp_start.isoformat(), "comparison_end": cmp_end.isoformat(), "grain": "day",
    }


def run_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    sid = scenario["id"]
    config = dict(SCENARIO_RUN_CONFIG[sid])
    if config.get("trigger") != "user_question":
        config["window"] = _window_for(scenario)
    return pipeline.run(today=TODAY, **config)


def _actual_branch(findings: dict[str, Any]) -> str:
    if findings.get("kind") == "no_alert":
        return "no_alert"
    return findings["outcome"]["branch"]


def score_scenario(scenario: dict[str, Any], findings: dict[str, Any]) -> dict[str, Any]:
    gt = scenario["ground_truth"]
    expected_branch = scenario["expected_branch"]
    actual_branch = _actual_branch(findings)
    branch_pass = actual_branch == expected_branch

    predicted_set = metrics.localization_set(findings)
    f1 = metrics.f1_localization(predicted_set, gt.get("true_segment"))
    exact = metrics.exact_match(predicted_set, gt.get("true_segment"))
    hit2 = metrics.rca_hit_at_2(findings, gt.get("true_segment"))
    top1 = bool(gt.get("true_segment")) and exact and actual_branch == "answer"
    recall5 = metrics.evidence_recall_at_5(findings, gt.get("evidence_document_ids") or [])
    hallucinated = metrics.hallucinated_cause(findings, gt.get("planted", False))

    tier = None
    if actual_branch == "answer" and findings["outcome"]["answer"]["drivers"]:
        tier = findings["outcome"]["answer"]["drivers"][0]["tier"]

    overall_pass = branch_pass and (not gt.get("planted") or top1 or expected_branch != "answer")

    return {
        "id": scenario["id"], "expected_branch": expected_branch, "actual_branch": actual_branch,
        "branch_pass": branch_pass, "f1_localization": f1, "exact_match": exact, "rca_top1": top1,
        "rca_hit_at_2": hit2, "evidence_recall_at_5": recall5, "hallucinated_cause": hallucinated,
        "tier": tier, "pass": overall_pass, "planted": gt.get("planted", False),
        "difficulty": scenario["difficulty"], "title": scenario["title"],
    }


def _fmt(x):
    if x is None:
        return "-"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, float):
        return f"{x:.2f}"
    return str(x)


def render_scorecard(rows: list[dict[str, Any]]) -> str:
    import subprocess

    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip() or "uncommitted"
    except Exception:  # noqa: BLE001
        commit = "unknown"
    today = dt.date.today().isoformat()

    lines = [f"## Scorecard — {commit} — {today}", ""]
    lines.append("### Q2: end-to-end root cause, 17 scenarios")
    lines.append("| ID | Difficulty | Expected | Got | Localization F1 | RCA top-1 | Tier | Pass |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['difficulty']} | {r['expected_branch']} | {r['actual_branch']} | "
            f"{_fmt(r['f1_localization'])} | {_fmt(r['rca_top1'])} | {_fmt(r['tier'])} | {_fmt(r['pass'])} |"
        )
    n_pass = sum(1 for r in rows if r["pass"])
    answerable = [r for r in rows if r["expected_branch"] == "answer"]
    top1_hits = sum(1 for r in answerable if r["rca_top1"])
    hallucinated = sum(1 for r in rows if r["hallucinated_cause"])
    lines.append("")
    lines.append(
        f"Totals: {n_pass}/{len(rows)} pass · RCA top-1 {top1_hits}/{len(answerable)} answerable · "
        f"hallucinated causes {hallucinated}/{len(rows)}"
    )
    lines.append("")

    lines.append("### Q3: trust behaviour")
    abstain_rows = [r for r in rows if r["expected_branch"] == "abstention"]
    should_abstain_and_did = sum(1 for r in abstain_rows if r["actual_branch"] == "abstention")
    did_abstain = [r for r in rows if r["actual_branch"] == "abstention"]
    should_have = sum(1 for r in did_abstain if r["expected_branch"] == "abstention")
    precision = should_have / len(did_abstain) if did_abstain else float("nan")
    recall = should_abstain_and_did / len(abstain_rows) if abstain_rows else float("nan")
    lines.append(
        f"abstention precision {precision:.2f} ({should_have}/{len(did_abstain)}) · "
        f"recall {recall:.2f} ({should_abstain_and_did}/{len(abstain_rows)}) · "
        f"hallucinated-cause rate {hallucinated/len(rows):.2f}"
    )
    lines.append("")

    lines.append("### Misses")
    misses = [r for r in rows if not r["pass"]]
    if not misses:
        lines.append("None.")
    else:
        for r in misses:
            lines.append(f"{r['id']} — expected {r['expected_branch']}, got {r['actual_branch']}. {r['title']}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", default="all")
    parser.add_argument("--out", default="eval/scorecard.md")
    parser.add_argument("--baseline", action="store_true",
                        help="Run the baselines instead of GlassBox (see eval/baselines/).")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    manifest = yaml.safe_load(Path("data/injection_manifest.yaml").read_text(encoding="utf-8"))
    scenarios = manifest["scenarios"]
    if args.scenarios != "all":
        wanted = set(args.scenarios.split(","))
        scenarios = [s for s in scenarios if s["id"] in wanted]

    if args.baseline:
        from eval.baselines import run_all as run_baselines

        run_baselines.main(scenarios, args.out, verbose=args.verbose)
        return

    rows = []
    for scenario in scenarios:
        if scenario.get("notes", "").strip().upper().startswith("RETIRED"):
            continue
        try:
            findings = run_scenario(scenario)
            row = score_scenario(scenario, findings)
        except Exception as exc:  # noqa: BLE001 - a scenario failing to run is itself a scoring result
            row = {
                "id": scenario["id"], "expected_branch": scenario["expected_branch"], "actual_branch": "ERROR",
                "branch_pass": False, "f1_localization": 0.0, "exact_match": False, "rca_top1": False,
                "rca_hit_at_2": False, "evidence_recall_at_5": None, "hallucinated_cause": False,
                "tier": None, "pass": False, "planted": scenario["ground_truth"].get("planted", False),
                "difficulty": scenario["difficulty"], "title": f"{scenario['title']} [ERROR: {exc}]",
            }
        rows.append(row)
        if args.verbose:
            print(f"{row['id']}: expected={row['expected_branch']} got={row['actual_branch']} pass={row['pass']}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_scorecard(rows), encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
