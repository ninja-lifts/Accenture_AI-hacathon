"""Runs the baselines against the same 17 scenarios GlassBox is scored on and
writes eval/baseline_scorecard.md in the shape docs/04_EVALUATION_PLAN.md §3
specifies.

B1 (naive drill-down) is real - see b1_naive.py, no external dependency.

B3 (single LLM prompt) only runs live - when GLASSBOX_REPLAY=0 and a real
GLASSBOX_LLM_API_KEY are configured - because the whole point of the
comparison is showing what an actual model says when asked in one shot.
Without a live key it is rendered as "NOT RUN", never a plausible-sounding
invented transcript - that would be exactly the kind of fabricated baseline
this project's own rules (and CLAUDE.md rule 6/7) exist to prevent, in the
one place fabrication would do the most damage: the SC-08 comparison.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine import config, contracts as contracts_mod, entitlements, llm_client, pipeline as pipeline_mod
from eval.baselines.b1_naive import run_b1
from eval.harness import SCENARIO_RUN_CONFIG, run_scenario

B3_SYSTEM_PROMPT = (
    "You are a business analyst. You are given a KPI's movement (observed vs "
    "expected, over a window) and a set of retrieved evidence document ids "
    "that were found relevant to it. Answer in 2-4 sentences: what caused "
    "this movement, and how confident are you? If you are not sure, say so - "
    "but give your best guess rather than declining, the way a single-prompt "
    "assistant would if pressed for an answer in one turn."
)


def build_b3_payload(scenario: dict[str, Any]) -> dict[str, Any]:
    """What a live B3 call actually sends: the same window aggregates and the
    same retrieved documents GlassBox saw for this scenario - fetched by
    calling define/detect/localize/retrieve directly, independent of whether
    GlassBox's own gate went on to answer or abstain, so an abstention
    doesn't quietly starve B3 of the evidence GlassBox actually retrieved."""
    import datetime as dt

    from engine.stages import s01_define, s02_detect, s03_localize, s05_retrieve

    settings = config.load()
    env = pipeline_mod._setup(settings)
    run_config = dict(SCENARIO_RUN_CONFIG[scenario["id"]])
    if run_config.get("trigger") == "user_question":
        # SC-17: nothing to hand B3 - the whole point is the question is
        # ambiguous before any data is even touched.
        return {
            "kpi": None, "window": None, "movement": None,
            "retrieved_evidence_ids": [],
            "note": "clarification scenario - no KPI/window resolved yet",
            "prompt": B3_SYSTEM_PROMPT,
        }
    run_config["window"] = pipeline_mod._default_window(dt.date(2026, 8, 22))
    fw = scenario["focal_window"]
    start = dt.date.fromisoformat(fw["start"])
    end = dt.date.fromisoformat(fw["end"])
    span = (end - start).days + 1
    cmp_end = start - dt.timedelta(days=1)
    cmp_start = cmp_end - dt.timedelta(days=span - 1)
    run_config["window"] = {
        "focal_start": start.isoformat(), "focal_end": end.isoformat(),
        "comparison_start": cmp_start.isoformat(), "comparison_end": cmp_end.isoformat(), "grain": "day",
    }

    ctx: dict[str, Any] = {
        "settings": settings, "con": env["con"], "contracts": env["contracts"],
        "catalogue": env["catalogue"], "graph": env["graph"],
        "trigger": run_config["trigger"], "raw_question": None,
        "persona": run_config["persona"], "role_id": run_config.get("role_id"),
        "kpi_id": run_config["kpi"], "segment": run_config.get("segment") or {},
        "window": run_config["window"], "today": dt.date(2026, 8, 22),
        "degradations": [], "route": None, "data_quality_failure": False,
        "telemetry": {"stage_timings_ms": {}},
        "security": {"cells_suppressed": 0, "documents_withheld": 0, "redactions_applied": 0, "injection_flags": []},
    }
    s01_define.run(ctx)
    s02_detect.run(ctx)
    s03_localize.run(ctx)
    s05_retrieve.run(ctx)

    return {
        "kpi": ctx["kpi_id"],
        "window": ctx["window"],
        "movement": ctx["movement"],
        "localization": ctx.get("localization", [])[:3],
        "retrieved_evidence_ids": [e["document_id"] for e in ctx.get("evidence", [])],
        "retrieved_evidence_snippets": [
            {"document_id": e["document_id"], "snippet": e["snippet"][:200]} for e in ctx.get("evidence", [])[:5]
        ],
        "prompt": B3_SYSTEM_PROMPT,
    }


def run_b3(scenario: dict[str, Any], payload: dict[str, Any], settings) -> str:
    """Returns the model's answer text, or a clear NOT_RUN marker - never an
    invented stand-in. Live only: needs GLASSBOX_REPLAY=0 and a real key."""
    if settings.replay_mode or not settings.llm_api_key:
        return "NOT RUN (replay mode / no live key configured)"
    if payload.get("kpi") is None:
        return "N/A (clarification scenario - no data to hand a single prompt)"
    from engine.llm_client import _call_live

    user = json.dumps(payload, default=str, indent=2)
    result = _call_live(
        settings, B3_SYSTEM_PROMPT, user, {"temperature": 0.2, "max_output_tokens": 1200}, f"{scenario['id']}/b3"
    )
    return result.text.strip()


def main(scenarios: list[dict[str, Any]], out_path: str, *, verbose: bool = False) -> None:
    settings = config.load()
    env = pipeline_mod._setup(settings)
    con = env["con"]
    all_contracts = env["contracts"]
    b3_live = (not settings.replay_mode) and bool(settings.llm_api_key)

    rows = []
    for scenario in scenarios:
        gt = scenario["ground_truth"]
        try:
            b1 = run_b1(scenario, con, all_contracts, settings)
            true_seg = {(k, v) for k, v in (gt.get("true_segment") or {}).items() if v is not None}
            b1_seg = {(k, v) for k, v in b1["segment"].items()}
            b1_correct = bool(true_seg) and b1_seg == true_seg
            b1_hallucinated = (not gt.get("planted", False)) and b1["cause_statement"] is not None

            b3_payload = build_b3_payload(scenario)
            b3_text = run_b3(scenario, b3_payload, settings)
            b3_answered = not b3_text.startswith(("NOT RUN", "N/A"))
            b3_hallucinated = (
                b3_live and b3_answered and (not gt.get("planted", False))
                and not any(p in b3_text.lower() for p in ("cannot determine", "no clear cause", "insufficient", "unable to establish", "not enough evidence"))
            )
        except Exception as exc:  # noqa: BLE001 - a scenario failing (a live-call
            # rate limit or timeout, most likely) must not cost every scenario
            # already answered before it. eval/harness.py's main loop has always
            # caught this per-scenario; this loop didn't, and a single Gemini
            # 429 crashed a batch that had already recorded two real answers.
            b1 = {"segment": {}, "cause_statement": None}
            b1_correct = False
            b1_hallucinated = False
            b3_text = f"ERROR: {type(exc).__name__}: {exc}"
            b3_hallucinated = False

        rows.append(
            {
                "id": scenario["id"], "title": scenario["title"],
                "b1_segment": b1["segment"], "b1_cause": b1["cause_statement"],
                "b1_correct": b1_correct, "b1_hallucinated": b1_hallucinated,
                "b3_text": b3_text, "b3_hallucinated": b3_hallucinated,
                "planted": gt.get("planted", False),
            }
        )
        if verbose:
            # Windows consoles default to cp1252, which can't render every
            # character a model might produce (em dashes, curly quotes,
            # rupee signs) - encode defensively rather than crash mid-run.
            def _safe(s: str) -> str:
                return s.encode("ascii", errors="replace").decode("ascii")

            print(_safe(f"{scenario['id']}: B1 -> {b1['segment']} | {b1['cause_statement']}"))
            print(_safe(f"{scenario['id']}: B3 -> {b3_text[:120]}"))

    lines = [
        "<!-- GENERATED by eval/baselines/run_all.py. B1 is always real. -->",
        (f"<!-- B3 was run LIVE this time (model={settings.llm_model!r}, provider={settings.llm_provider!r}). -->" if b3_live
         else "<!-- B3 was NOT run this time - replay mode / no live key. See the module docstring. -->"),
        "",
        "# Baselines",
        "",
        f"### Q2 - {len(scenarios)} scenarios (RETIRED scenarios excluded - see data/manifest_reconciliation.md)",
        "| ID | GlassBox (see eval/scorecard.md) | B1 naive drill-down | B3 single LLM prompt |",
        "|----|----|----|----|",
    ]
    for r in rows:
        b1_cell = f"{r['b1_segment']} / {r['b1_cause'] or 'no matching document'}"
        b3_cell = r["b3_text"].replace("\n", " ")[:150] + ("…" if len(r["b3_text"]) > 150 else "")
        lines.append(f"| {r['id']} | see scorecard | {b1_cell} | {b3_cell} |")
    n_b1_correct = sum(1 for r in rows if r["b1_correct"])
    n_b1_hallucinated = sum(1 for r in rows if r["b1_hallucinated"])
    n_b3_hallucinated = sum(1 for r in rows if r["b3_hallucinated"])
    lines += [
        "",
        f"B1 totals: {n_b1_correct}/{len(rows)} exact segment match · "
        f"{n_b1_hallucinated}/{len(rows)} scenarios where B1 named a cause on an unplanted movement",
    ]
    n_b3_errored = sum(1 for r in rows if r["b3_text"].startswith("ERROR:"))
    if b3_live:
        lines.append(
            f"B3 totals: run live on {sum(1 for r in rows if not r['b3_text'].startswith(('NOT RUN', 'N/A', 'ERROR:')))}/{len(rows)} scenarios · "
            f"{n_b3_hallucinated} scenarios where B3 asserted a cause on an unplanted movement without hedging "
            f"(heuristic keyword check on its own text - read the full row, this count is not authoritative)"
            + (f" · {n_b3_errored} errored (see row text)" if n_b3_errored else "")
        )
    lines += [
        "",
        "### SC-08 - the row that matters (no cause was planted)",
    ]
    sc08 = next((r for r in rows if r["id"] == "SC-08"), None)
    if sc08:
        lines.append(f"B1       : {sc08['b1_segment']} / {sc08['b1_cause'] or 'no matching document'}")
        lines.append(f"B3       : {sc08['b3_text']}")
    lines.append("GlassBox : see eval/scorecard.md's SC-08 row and TRAJECTORIES.md §2 for the real abstention.")
    lines.append("")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")
