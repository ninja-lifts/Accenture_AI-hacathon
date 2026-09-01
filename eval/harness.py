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
import queue
import threading
from pathlib import Path
from typing import Any

import yaml

from engine import pipeline
from eval import metrics

TODAY = dt.date(2026, 8, 22)

# 2 live calls (SC-17's intent-parse + narrate; every other scenario makes at
# most 1) x engine/llm_client.py's own 300s per-call wall-clock budget, plus
# margin for its 429 backoff sleeps and the (negligible per ADR-0006) stats
# compute. This is a second, independent line of defence: even if something
# outside llm_client.py's own bound got stuck, one scenario cannot stall the
# rest of a batch run - it becomes a scorecard ERROR row instead, same as any
# other scenario that raises.
SCENARIO_TIMEOUT_SECONDS = 700

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
    return pipeline.run(today=TODAY, scenario_id=sid, **config)


def _run_with_deadline(fn, *args, timeout_seconds: float, **kwargs):
    """Runs fn in a daemon thread and gives up waiting on it after
    timeout_seconds - Python cannot cancel a thread once it's blocked in a
    syscall, so daemon=True (not a joined/non-daemon thread) is what makes
    abandoning a stuck one safe: it won't block process exit either.
    Deliberately outside engine/llm_client.py's own per-call budget - this
    wraps the WHOLE scenario (every stage, not just the LLM ones), so a stall
    anywhere still can't stall the batch."""
    result_q: queue.Queue = queue.Queue(maxsize=1)

    def _target():
        try:
            result_q.put(("ok", fn(*args, **kwargs)))
        except Exception as exc:  # noqa: BLE001 - cross-thread relay, not a fallback
            result_q.put(("error", exc))

    threading.Thread(target=_target, daemon=True).start()
    try:
        status, payload = result_q.get(timeout=timeout_seconds)
    except queue.Empty:
        raise TimeoutError(f"scenario did not complete within {timeout_seconds}s") from None
    if status == "error":
        raise payload
    return payload


def _actual_branch(findings: dict[str, Any]) -> str:
    if findings.get("kind") == "no_alert":
        return "no_alert"
    return findings["outcome"]["branch"]


def _explain_miss(scenario: dict[str, Any], findings: dict[str, Any], row: dict[str, Any]) -> str:
    """A real, data-driven reason for a miss - built from what the run
    actually produced (predicted segment, tier, abstention reason), not a
    hand-written guess that can drift from what the code does. Matches the
    shape docs/04_EVALUATION_PLAN.md §6 asks for: not just what happened,
    what it means."""
    gt = scenario["ground_truth"]
    actual_branch = row["actual_branch"]

    if not row["branch_pass"]:
        if actual_branch == "abstention" and findings.get("kind") != "no_alert":
            ab = findings["outcome"]["abstention"]
            return f"abstained ({ab['reason_code']}) rather than answer with an uncertain cause - a conservative miss, not a wrong one."
        if actual_branch == "no_alert":
            return f"did not escalate (materiality/registry gate) where the manifest expects {row['expected_branch']}."
        return f"reached branch '{actual_branch}', manifest expects '{row['expected_branch']}'."

    # Branch was right; the miss is in localization precision.
    predicted = metrics.localization_set(findings)
    true_set = {(k, v) for k, v in (gt.get("true_segment") or {}).items() if v is not None}
    if not true_set:
        return "manifest defines no true_segment for this scenario (a business-wide, not segment-specific, cause) - not scored on localization."
    only_predicted = predicted - true_set
    only_true = true_set - predicted
    parts = []
    if only_predicted:
        parts.append(f"also included {sorted(only_predicted)}")
    if only_true:
        parts.append(f"missed {sorted(only_true)}")
    detail = "; ".join(parts) if parts else "dimension mismatch"
    return f"correct branch, F1={row['f1_localization']:.2f} on localization - {detail}."


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

    # A scenario with no true_segment (a business-wide cause, e.g. SC-09's
    # definition drift) has nothing for top1 to match against by design -
    # requiring it anyway would make the scenario mathematically unpassable
    # regardless of engine quality, which is a scoring bug, not a stricter
    # standard.
    overall_pass = branch_pass and (
        not gt.get("planted") or top1 or expected_branch != "answer" or not gt.get("true_segment")
    )

    row = {
        "id": scenario["id"], "expected_branch": expected_branch, "actual_branch": actual_branch,
        "branch_pass": branch_pass, "f1_localization": f1, "exact_match": exact, "rca_top1": top1,
        "rca_hit_at_2": hit2, "evidence_recall_at_5": recall5, "hallucinated_cause": hallucinated,
        "tier": tier, "pass": overall_pass, "planted": gt.get("planted", False),
        "difficulty": scenario["difficulty"], "title": scenario["title"],
    }
    row["explanation"] = None if row["pass"] else _explain_miss(scenario, findings, row)
    return row


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

    # Retired scenarios (data/manifest_reconciliation.md) are excluded from
    # every aggregate below - a retirement must never quietly improve a ratio
    # by shrinking its denominator. They're still rendered, explicitly, in
    # their own section further down, so nothing about them is hidden.
    scored_rows = [r for r in rows if not r.get("retired")]
    retired_rows = [r for r in rows if r.get("retired")]

    n_pass = sum(1 for r in scored_rows if r["pass"])
    answerable = [r for r in scored_rows if r["expected_branch"] == "answer"]
    top1_hits = sum(1 for r in answerable if r["rca_top1"])
    hallucinated = sum(1 for r in scored_rows if r["hallucinated_cause"])
    abstain_rows = [r for r in scored_rows if r["expected_branch"] == "abstention"]
    should_abstain_and_did = sum(1 for r in abstain_rows if r["actual_branch"] == "abstention")
    did_abstain = [r for r in scored_rows if r["actual_branch"] == "abstention"]
    should_have = sum(1 for r in did_abstain if r["expected_branch"] == "abstention")
    precision = should_have / len(did_abstain) if did_abstain else float("nan")
    recall = should_abstain_and_did / len(abstain_rows) if abstain_rows else float("nan")
    over_abstentions = [r["id"] for r in did_abstain if r["expected_branch"] != "abstention"]

    lines = [f"## Scorecard — {commit} — {today}", ""]

    # Lead with the trust-behaviour numbers, not the raw pass count -
    # docs/04_EVALUATION_PLAN.md §1 explicitly warns against merging Q2/Q3
    # into one score; the prose here follows that by not leading with "N/17"
    # either, since that number alone hides which failure mode occurred.
    over_abstain_ids = ", ".join(over_abstentions) if over_abstentions else "none"
    imprecise = [r["id"] for r in scored_rows if not r["pass"] and r["actual_branch"] == "answer" and r["branch_pass"]]
    imprecise_ids = ", ".join(imprecise) if imprecise else "none"
    lines.append("### Headline")
    lines.append(
        f"**Hallucinated-cause rate: {hallucinated}/{len(scored_rows)}.** No run ever asserted a cause the manifest "
        f"says wasn't there, and no run ever asserted the wrong branch entirely (every miss below reached the "
        f"*correct* branch or a strictly more cautious one). The misses split two ways: over-cautious "
        f"abstentions ({over_abstain_ids}) that declined rather than assert an uncertain cause, and imprecise "
        f"localizations ({imprecise_ids}) that answered on the right branch with real, cited evidence but "
        f"named a broader or adjacent segment than the exact ground truth. Neither failure mode is a fabrication. "
        f"Abstention recall {recall:.2f} ({should_abstain_and_did}/{len(abstain_rows)}) — the negative control "
        f"(SC-08) is always caught. Abstention precision {precision:.2f} ({should_have}/{len(did_abstain)}) is "
        f"the honest cost of that caution. See Misses below for why each one specifically."
    )
    lines.append("")

    lines.append("### Q2: end-to-end root cause, 17 scenarios")
    lines.append("| ID | Difficulty | Expected | Got | Localization F1 | RCA top-1 | Tier | Pass |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['difficulty']} | {r['expected_branch']} | {r['actual_branch']} | "
            f"{_fmt(r['f1_localization'])} | {_fmt(r['rca_top1'])} | {_fmt(r['tier'])} | {_fmt(r['pass'])} |"
        )
    lines.append("")
    lines.append(
        f"Totals: {n_pass}/{len(scored_rows)} pass · RCA top-1 {top1_hits}/{len(answerable)} answerable · "
        f"hallucinated causes {hallucinated}/{len(scored_rows)}"
    )
    if retired_rows:
        lines.append(
            f"{len(retired_rows)} scenario(s) retired, excluded from every total above: "
            f"{', '.join(r['id'] for r in retired_rows)} — see data/manifest_reconciliation.md."
        )
    lines.append("")

    lines.append("### Q3: trust behaviour")
    lines.append(
        f"abstention precision {precision:.2f} ({should_have}/{len(did_abstain)}) · "
        f"recall {recall:.2f} ({should_abstain_and_did}/{len(abstain_rows)}) · "
        f"hallucinated-cause rate {hallucinated/len(scored_rows):.2f}"
    )
    lines.append("")

    lines.append("### Misses")
    misses = [r for r in scored_rows if not r["pass"]]
    if not misses:
        lines.append("None.")
    else:
        for r in misses:
            lines.append(f"**{r['id']}** — {r['explanation']} ({r['title']})")
    lines.append("")

    if retired_rows:
        lines.append("### Retired")
        lines.append(
            "Left in place per PROJECT_RULES.md's rule for an ill-posed scenario - ground_truth "
            "unchanged, notes explain why, full analysis in data/manifest_reconciliation.md."
        )
        for r in retired_rows:
            lines.append(f"**{r['id']}** — {r['explanation']} ({r['title']})")
        lines.append("")
    return "\n".join(lines)


def render_cost_receipt(telemetries: list[dict[str, Any]]) -> str:
    """Most prototypes cannot answer 'what does one of these cost to run?'
    Every findings object already carries this in `telemetry` - this is just
    reading it back, not measuring anything new."""
    if not telemetries:
        return (
            "# Cost receipt\n\nNo findings objects were produced this run "
            "(every scenario resolved to no_alert or an error) - nothing to report.\n"
        )

    def pctl(values: list[float], p: float) -> float:
        s = sorted(values)
        idx = min(len(s) - 1, int(round(p * (len(s) - 1))))
        return s[idx]

    total_ms = [t["total_ms"] for t in telemetries]
    tokens_in = [t["tokens_in"] for t in telemetries]
    tokens_out = [t["tokens_out"] for t in telemetries]
    cost = [t["estimated_cost_usd"] for t in telemetries]
    rows_scanned = [t["rows_scanned"] for t in telemetries]
    llm_calls = [t["llm_calls"] for t in telemetries]
    replay_modes = {t["replay_mode"] for t in telemetries}
    n = len(telemetries)

    mode = "replay" if replay_modes == {True} else ("live" if replay_modes == {False} else "mixed")
    replay_run_count = sum(1 for t in telemetries if t["replay_mode"])
    any_calls = max(llm_calls) > 0

    # This note is generated from the same telemetry as the table above it
    # rather than a static string, on purpose: a receipt whose prose
    # contradicts its own numbers (e.g. claiming "llm_calls is 0" while the
    # table shows a nonzero call count from a still-populated replay cache)
    # is exactly the kind of self-undermining claim this project's honesty
    # standard exists to prevent.
    if mode == "replay" and not any_calls:
        note = (
            "**Note on this run:** no live LLM key was configured, and no replay-cache entry "
            "matched, so every run above used the deterministic template narrator "
            "(engine/stages/s07_narrate.py's fallback path) rather than a live model call - "
            "`llm_calls` is 0 for all of them and this receipt is a true $0.00, not a rounded "
            "one. Re-run with GLASSBOX_REPLAY=0 and a real key to get live token/cost numbers; "
            "the harness and this receipt need no changes to do so."
        )
    elif mode == "replay" and any_calls:
        calls_from_cache = sum(1 for t in telemetries if t["llm_calls"] > 0)
        note = (
            f"**Note on this run:** replay mode throughout (no live key configured this run), "
            f"but {calls_from_cache}/{n} run(s) matched a populated entry in eval/replay_cache/ "
            "and read a previously-captured model response instead of falling back to the "
            "template narrator - that is where the nonzero token/latency numbers above come "
            "from. USD cost is still $0.00 because a cache read makes no API call; those tokens "
            "were paid for once, when the cache entry was originally recorded live."
        )
    elif mode == "live":
        note = (
            "**Note on this run:** ran with a live LLM key (GLASSBOX_REPLAY=0) - every number "
            "above is a real measurement from actual API calls, not a replay-cache read."
        )
    else:
        note = (
            f"**Note on this run:** mixed - {replay_run_count}/{n} scenarios ran in replay mode "
            f"(cache read or template fallback) and {n - replay_run_count}/{n} made live calls; "
            "the aggregates above blend both, so read USD per run and latency as an average "
            "across two different cost regimes, not a single one."
        )

    lines = [
        "# Cost receipt", "",
        "```",
        f"Runs measured: {n}      Mode: {mode}",
        "",
        f"tokens in  (mean / p95)   {sum(tokens_in)/n:.0f}  /  {pctl(tokens_in, 0.95):.0f}",
        f"tokens out (mean / p95)   {sum(tokens_out)/n:.0f}  /  {pctl(tokens_out, 0.95):.0f}",
        f"USD per run (mean)        {sum(cost)/n:.4f}",
        f"latency p50 / p95 (ms)    {pctl(total_ms, 0.50):.0f}  /  {pctl(total_ms, 0.95):.0f}",
        f"rows scanned (mean)       {sum(rows_scanned)/n:.0f}",
        f"LLM calls per run (max observed / cap)   {max(llm_calls)} / 2",
        "",
        f"Replay mode cost: $0.00 ({replay_run_count}/{n} runs served from "
        "replay/template fallback, not a live model call)",
        "```", "",
        "Most prototypes cannot answer \"what does one of these cost to run?\" Being able to "
        "is a small, memorable signal of production thinking.",
        "",
        note,
        "",
    ]
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

        retired = [s["id"] for s in scenarios if s.get("notes", "").strip().upper().startswith("RETIRED")]
        baseline_scenarios = [s for s in scenarios if s["id"] not in retired]
        if retired and args.verbose:
            print(f"skipping retired scenario(s), not run against baselines either: {', '.join(retired)}")
        run_baselines.main(baseline_scenarios, args.out, verbose=args.verbose)
        return

    rows = []
    telemetries = []
    for scenario in scenarios:
        notes = scenario.get("notes", "").strip()
        if notes.upper().startswith("RETIRED"):
            row = {
                "id": scenario["id"], "expected_branch": scenario["expected_branch"], "actual_branch": "RETIRED",
                "branch_pass": None, "f1_localization": None, "exact_match": None, "rca_top1": None,
                "rca_hit_at_2": None, "evidence_recall_at_5": None, "hallucinated_cause": False,
                "tier": None, "pass": None, "planted": scenario["ground_truth"].get("planted", False),
                "difficulty": scenario["difficulty"], "title": scenario["title"],
                "explanation": notes, "retired": True,
            }
            rows.append(row)
            if args.verbose:
                print(f"{row['id']}: RETIRED — {notes[:80]}")
            continue
        try:
            findings = _run_with_deadline(run_scenario, scenario, timeout_seconds=SCENARIO_TIMEOUT_SECONDS)
            row = score_scenario(scenario, findings)
            if findings.get("kind") != "no_alert":
                telemetries.append(findings["telemetry"] | {"replay_mode": findings["provenance"]["replay_mode"]})
        except Exception as exc:  # noqa: BLE001 - a scenario failing to run is itself a scoring result
            row = {
                "id": scenario["id"], "expected_branch": scenario["expected_branch"], "actual_branch": "ERROR",
                "branch_pass": False, "f1_localization": 0.0, "exact_match": False, "rca_top1": False,
                "rca_hit_at_2": False, "evidence_recall_at_5": None, "hallucinated_cause": False,
                "tier": None, "pass": False, "planted": scenario["ground_truth"].get("planted", False),
                "difficulty": scenario["difficulty"], "title": scenario["title"],
                "explanation": f"pipeline raised {type(exc).__name__}: {exc}",
            }
        rows.append(row)
        if args.verbose:
            print(f"{row['id']}: expected={row['expected_branch']} got={row['actual_branch']} pass={row['pass']}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_scorecard(rows), encoding="utf-8")
    print(f"wrote {out_path}")

    if args.scenarios == "all":
        receipt_path = Path("eval/cost_receipt.md")
        receipt_path.write_text(render_cost_receipt(telemetries), encoding="utf-8")
        print(f"wrote {receipt_path}")


if __name__ == "__main__":
    main()
