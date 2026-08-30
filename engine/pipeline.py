"""The orchestrator. Reads like the architecture diagram, top to bottom.

Deliberately a straight line, not an agent loop. Stages are pure functions
over a growing context; any stage may declare a tier cap or route to the
gate. This is what makes a run replayable, testable and explainable - and it
is the design decision to defend in Q&A, not apologise for.

Two entry scopes:
  - `investigate=False` (default for trigger='alert_sweep'): the full,
    autonomous alert path - Stage 02's dual materiality gate decides whether
    this even becomes a findings object, or a lightweight alert-feed row
    (SC-02 silence, SC-03 "explained - planned"). Never schema-validated,
    because it never claims to be a finished analysis.
  - `investigate=True`: the movement is already worth investigating (a typed
    question, a category manager's own scoped view, a scenario replay) - the
    materiality gate is skipped and the run always proceeds to a full,
    schema-valid findings object.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import duckdb
import ulid

from engine import audit, config, contracts as contracts_mod, gate, kpi_graph, tiers
from engine.stages import s00_intent, s01_define, s02_detect, s03_localize, s04_decompose, s05_retrieve, s06_falsify, s07_narrate

_CACHE: dict[str, Any] = {}


def _setup(settings) -> dict[str, Any]:
    if "contracts" in _CACHE:
        return _CACHE
    all_contracts = contracts_mod.load_all("contracts")
    catalogue = contracts_mod.build_catalogue(all_contracts)
    graph = kpi_graph.compile_graph(all_contracts)
    con = duckdb.connect(settings.duckdb_path, read_only=False)
    # DuckDB's default multi-threaded aggregation can sum the same rows in a
    # different order across process launches, producing float results that
    # agree to ~10 significant digits but not bit-for-bit (e.g.
    # -3499600.0126327574 vs ...593). Invisible at the 2-decimal precision
    # the scorecard reports, but it broke the replay cache: two runs of "the
    # same" scenario hashed to two different cache keys. Single-threaded
    # execution makes the reduction order - and therefore the exact float -
    # reproducible run to run, which is what "make reproduce" actually
    # promises. Meridian is small enough (~1.2M orders) that this costs
    # negligible wall-clock time.
    con.execute("PRAGMA threads=1")
    _CACHE.update({"contracts": all_contracts, "catalogue": catalogue, "graph": graph, "con": con})
    return _CACHE


def _code_version() -> str:
    try:
        return subprocess.run(
            ["git", "describe", "--always", "--dirty"], capture_output=True, text=True, timeout=5, cwd=Path(__file__).parent
        ).stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


_TRACE_KEYS = {
    "s00_intent": ["route", "kpi_id", "segment", "window", "clarification"],
    "s01_define": ["data_quality_failure", "data_quality_reason", "sources", "entitlement", "series"],
    "s02_detect": ["history_periods_ok", "movement"],
    "s03_localize": ["localization"],
    "s04_decompose": ["decomposition"],
    "s05_retrieve": ["evidence", "sources"],
    "s06_falsify": ["candidates", "rejected_hypotheses"],
}


def _snapshot(ctx: dict[str, Any], stage: str) -> None:
    """Record what a stage actually put on the context, for --trace. Reads
    ctx after the stage already ran; never influences pipeline behaviour -
    deleting this function changes no findings output, only whether a trace
    is available to inspect one."""
    if ctx.get("_trace") is None:
        return
    keys = _TRACE_KEYS.get(stage, [])
    snapshot = {}
    for k in keys:
        if k not in ctx:
            continue
        v = ctx[k]
        if k == "evidence" and isinstance(v, list):
            snapshot[k] = [
                {kk: e.get(kk) for kk in ("document_id", "source", "retrieval_score", "flagged_injection")}
                for e in v
            ]
        elif k == "series":
            # A DataFrame isn't JSON-serialisable and a full history dump
            # would dwarf everything else in the trace - the row count is
            # the number a reader of a trace actually wants here.
            snapshot[k] = {"row_count": int(len(v))} if v is not None else None
        else:
            snapshot[k] = v
    ctx["_trace"].append({"stage": stage, "ctx": snapshot})


def _default_window(today: dt.date) -> dict[str, str]:
    last_sunday = today - dt.timedelta(days=today.weekday() + 1)
    focal_end = last_sunday
    focal_start = focal_end - dt.timedelta(days=6)
    cmp_end = focal_start - dt.timedelta(days=1)
    cmp_start = cmp_end - dt.timedelta(days=6)
    return {
        "focal_start": focal_start.isoformat(), "focal_end": focal_end.isoformat(),
        "comparison_start": cmp_start.isoformat(), "comparison_end": cmp_end.isoformat(),
        "grain": "day",
    }


def run(
    *,
    trigger: str,
    persona: str,
    question: str | None = None,
    kpi: str | None = None,
    segment: dict[str, Any] | None = None,
    window: dict[str, Any] | None = None,
    role_id: str | None = None,
    today: dt.date | None = None,
    investigate: bool = False,
    trace: bool = False,
    scenario_id: str | None = None,
) -> dict[str, Any] | tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute the pipeline. Returns either a findings object (schema-valid)
    or, for an alert_sweep that does not escalate, a small alert-feed row
    dict with `kind: 'no_alert'` - the latter is intentionally NOT validated
    against findings.schema.json, because it never became one (see module
    docstring).

    trace=True changes the return to (result, trace_log): a list of
    {"stage": str, "ctx": {...}} snapshots, one per stage that actually ran,
    for `python -m eval.trace`. Every existing caller passes trace=False (the
    default) and gets the exact same single-value return as before - this is
    additive, not a behaviour change.

    scenario_id is optional and purely cosmetic: engine/llm_client.py uses it
    (falling back to the generated run_id) to label live-call progress lines,
    so a batch run's stderr says which scenario a hung or slow call belongs
    to instead of just a stage name. Never read by scoring or schema
    validation - additive, like trace."""
    settings = config.load()
    env = _setup(settings)
    today = today or dt.date.today()

    ctx: dict[str, Any] = {
        "settings": settings,
        "con": env["con"],
        "contracts": env["contracts"],
        "catalogue": env["catalogue"],
        "graph": env["graph"],
        "run_id": str(ulid.new()),
        "scenario_id": scenario_id,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "trigger": trigger,
        "raw_question": question,
        "persona": persona,
        "role_id": role_id,
        "kpi_id": kpi,
        "segment": segment or {},
        "window": window,
        "today": today,
        "degradations": [],
        "route": None,
        "data_quality_failure": False,
        "telemetry": {"stage_timings_ms": {}, "llm_calls": 0, "tokens_in": 0, "tokens_out": 0,
                       "estimated_cost_usd": 0.0, "rows_scanned": 0, "validator_retries": 0},
        "security": {"cells_suppressed": 0, "documents_withheld": 0, "redactions_applied": 0, "injection_flags": []},
        "_trace": [] if trace else None,
    }

    def _done(result: dict[str, Any]) -> Any:
        return (result, ctx["_trace"]) if trace else result

    s00_intent.run(ctx)
    _snapshot(ctx, "s00_intent")

    if ctx["route"] == "clarification":
        findings = _assemble_clarification(ctx)
        audit.write(findings)
        return _done(findings)

    if ctx["kpi_id"] is None:
        raise ValueError("kpi is required (directly, or resolved by Stage 00 from a question)")
    ctx["window"] = ctx["window"] or _default_window(today)

    s01_define.run(ctx)
    _snapshot(ctx, "s01_define")
    s02_detect.run(ctx)
    _snapshot(ctx, "s02_detect")

    if trigger == "alert_sweep" and not investigate:
        mat = ctx["movement"]["materiality"]
        escalate = mat["statistically_surprising"] and mat["materially_large"] and not mat["suppressed_by_registry"]
        if not escalate:
            return _done({
                "kind": "no_alert",
                "kpi": ctx["kpi_id"],
                "segment": ctx["segment"],
                "window": ctx["window"],
                "movement": ctx["movement"],
                "explained_planned": mat["suppressed_by_registry"],
                "registry_entry_id": mat["registry_entry_id"],
            })

    s03_localize.run(ctx)
    _snapshot(ctx, "s03_localize")
    s04_decompose.run(ctx)
    _snapshot(ctx, "s04_decompose")
    s05_retrieve.run(ctx)
    _snapshot(ctx, "s05_retrieve")
    s06_falsify.run(ctx)
    _snapshot(ctx, "s06_falsify")

    branch = gate.decide(ctx)
    ctx["branch"] = branch

    if branch == "abstention":
        findings = _assemble_abstention(ctx)
    else:
        findings = _assemble_answer(ctx)
    if ctx["_trace"] is not None:
        ctx["_trace"].append({"stage": "s07_narrate", "ctx": {"branch": branch, "outcome": findings["outcome"]}})

    audit.write(findings)
    return _done(findings)


# ============================================================== assembly ===


def _base_findings(ctx: dict[str, Any]) -> dict[str, Any]:
    contract = ctx["contracts"][ctx["kpi_id"]]
    entitlements_hash = ctx.get("entitlement", {}).get("entitlements_hash", "n/a")
    return {
        "schema_version": "1.0.0",
        "run_id": ctx["run_id"],
        "created_at": ctx["created_at"],
        "request": {
            "trigger": ctx["trigger"],
            "raw_question": ctx["raw_question"],
            "principal": {
                "persona": ctx["persona"],
                "role_id": ctx.get("role_id") or ctx["persona"],
                "entitlements_hash": entitlements_hash,
            },
        },
        "kpi": {
            "id": contract["id"], "contract_version": contract["version"],
            "display_name": contract["display_name"], "unit": contract.get("unit") or "count",
        },
        "window": ctx["window"],
        "provenance": {
            "sources": ctx.get("sources", []),
            "code_version": _code_version(),
            "contracts_used": [contract["id"]],
            "replay_mode": ctx["settings"].replay_mode or not ctx["settings"].llm_api_key,
        },
        "telemetry": {
            "stage_timings_ms": ctx["telemetry"]["stage_timings_ms"],
            "total_ms": sum(ctx["telemetry"]["stage_timings_ms"].values()),
            "llm_calls": ctx.get("_llm_call_count", 0),
            "tokens_in": ctx.get("_llm_tokens_in", 0),
            "tokens_out": ctx.get("_llm_tokens_out", 0),
            "estimated_cost_usd": ctx.get("_llm_cost_usd", 0.0),
            "rows_scanned": int(len(ctx["series"])) if "series" in ctx else 0,
            "validator_retries": ctx["telemetry"].get("validator_retries", 0),
        },
        "security": ctx["security"],
    }


def _assemble_clarification(ctx: dict[str, Any]) -> dict[str, Any]:
    contract_ids = ctx["clarification"].get("vocabulary_source") or []
    kpi_id = contract_ids[0] if contract_ids else next(iter(ctx["contracts"]))
    ctx["kpi_id"] = kpi_id
    ctx["window"] = ctx.get("window") or _default_window(ctx["today"])
    ctx["entitlement"] = {"entitlements_hash": "n/a"}
    ctx["sources"] = []
    ctx["security"] = ctx["security"]

    base = _base_findings(ctx)
    base["movement"] = None
    base["outcome"] = {
        "branch": "clarification",
        "answer": None,
        "abstention": None,
        "clarification": ctx["clarification"],
    }
    return base


def _driver_tier(driver: dict[str, Any], degradations: list[str]) -> str:
    support = {
        "evidence_ids": driver.get("evidence_ids") or [],
        "test_results": driver.get("test_results") or [],
        "correlated": True,
        "hypothesis": True,
    }
    return tiers.assign("driver", support, degradations)


def _build_action(ctx: dict[str, Any], top_driver: dict[str, Any], top_tier: str) -> dict[str, Any]:
    contract = ctx["contracts"][ctx["kpi_id"]]
    lever = None
    for d in contract.get("drivers", []):
        if d.get("levers"):
            lever = d["levers"][0]
            break
    lever = lever or "operational_review"
    movement = ctx["movement"]
    kpi_name = contract["display_name"]
    return {
        "driver_id": top_driver["driver_id"],
        "lever": lever,
        "recommendation": f"Investigate and address: {top_driver['statement']}",
        "expected_impact": {"metric": ctx["kpi_id"], "value": abs(movement["delta_abs"]), "basis": "recovered_gap"},
        "owner": contract["owner"],
        "confidence": top_tier,
        "monitoring": {
            "metric": ctx["kpi_id"], "check_after_days": 14,
            "success_threshold": f"{kpi_name} recovers to within 2% of the expected baseline",
        },
    }


def _assemble_answer(ctx: dict[str, Any]) -> dict[str, Any]:
    contract = ctx["contracts"][ctx["kpi_id"]]
    degradations = ctx.get("degradations", [])
    candidates = ctx.get("candidates", [])

    drivers = []
    for c in candidates:
        tier = _driver_tier(c, degradations)
        drivers.append(
            {
                "driver_id": c["driver_id"], "statement": c["statement"], "tier": tier,
                "share_of_movement_pct": None, "evidence": c.get("evidence", []), "tests": c.get("tests", []),
            }
        )
    if not drivers:
        drivers.append(
            {
                "driver_id": "DRIVER-UNEXPLAINED", "statement": "No specific cause could be isolated from the available evidence.",
                "tier": "HYPOTHESIS", "share_of_movement_pct": None, "evidence": [], "tests": [],
            }
        )
    top_tier = max(drivers, key=lambda d: tiers.TIER_ORDER.index(d["tier"]))["tier"]
    top_driver = next(d for d in drivers if d["tier"] == top_tier)

    outcome_draft = {
        "_kpi_display_name": contract["display_name"],
        "_window": ctx["window"],
        "answer": {
            "headline_delta_pct": ctx["movement"]["delta_pct"],
            "headline_delta_abs": ctx["movement"]["delta_abs"],
            "headline_tier": "VERIFIED",
            "localization": ctx.get("localization", []),
            "decomposition": ctx.get("decomposition", []),
            "drivers": drivers,
            "rejected_hypotheses": ctx.get("rejected_hypotheses", []),
            "action": _build_action(ctx, {"driver_id": top_driver["driver_id"], "statement": top_driver["statement"]}, top_tier),
        },
    }
    ctx["outcome_draft"] = outcome_draft
    ctx["branch"] = "answer"
    s07_narrate.run(ctx)

    narrative = []
    for s in ctx["narration"]["sentences"][1:]:
        tier = _resolve_tier(s["tier_from"], drivers, top_tier)
        numbers = _numerals_in(s["text"])
        narrative.append({"text": s["text"], "tier": tier, "support": {"numbers": numbers, "evidence_ids": [], "test_ids": []}})

    headline = {
        "text": ctx["narration"]["headline"], "tier": "VERIFIED",
        "support": {"numbers": [ctx["movement"]["delta_pct"], ctx["movement"]["delta_abs"]], "evidence_ids": [], "test_ids": []},
    }

    base = _base_findings(ctx)
    base["movement"] = ctx["movement"]
    base["outcome"] = {
        "branch": "answer",
        "answer": {
            "headline": headline,
            "narrative": narrative,
            "localization": outcome_draft["answer"]["localization"],
            "decomposition": outcome_draft["answer"]["decomposition"],
            "drivers": drivers,
            "rejected_hypotheses": outcome_draft["answer"]["rejected_hypotheses"],
            "action": outcome_draft["answer"]["action"],
        },
        "abstention": None,
        "clarification": None,
    }
    return base


def _assemble_abstention(ctx: dict[str, Any]) -> dict[str, Any]:
    contract = ctx["contracts"][ctx["kpi_id"]]
    reason = ctx.get("gate_reason") or "no_candidate_passed_evidence_floor"
    kpi_name = contract["display_name"]
    movement = ctx["movement"]

    ruled_out = ctx.get("rejected_hypotheses", [])
    for c in ctx.get("candidates", []):
        for t in c.get("tests", []):
            if t["result"] == "failed":
                ruled_out.append(
                    {"statement": c["statement"], "rejected_by": "falsification_test", "detail": t["statement"], "test_id": t["test_id"]}
                )

    statement = (
        f"{kpi_name} moved {movement['delta_pct']:.1f}% in the window to {ctx['window']['focal_end']}, "
        f"but no cause could be established that clears the evidence floor."
    )
    referral = {"team": "Analytics", "why": "Movement is real and material; needs a human investigation with broader context."}

    outcome_draft = {
        "_kpi_display_name": kpi_name,
        "_window": ctx["window"],
        "abstention": {
            "reason_code": reason, "statement": statement, "ruled_out": ruled_out,
            "what_would_resolve_it": ["Additional evidence documents inside the movement window", "A wider evidence floor review"],
            "referral": referral,
        },
    }
    ctx["outcome_draft"] = outcome_draft
    ctx["branch"] = "abstention"
    s07_narrate.run(ctx)

    # outcome.abstention carries plain strings, not tiered claims (the schema
    # has no tier field here - abstention IS the tier, in effect: UNKNOWN).
    # The narrator's job is to turn the templated statement into persona-
    # appropriate prose; join headline + sentences into one statement (the
    # schema gives abstention a single string field, not a sentence array)
    # so the ruled-out and referral content the narrator was explicitly
    # instructed to include (narrate.md rule 5) doesn't get silently dropped
    # down to just the headline. Every numeral in all of it is already
    # validated against outcome_draft.
    narration = ctx["narration"]
    statement_parts = [narration["headline"]] + [s["text"] for s in narration.get("sentences", [])[1:]]
    outcome_draft["abstention"]["statement"] = " ".join(statement_parts)

    base = _base_findings(ctx)
    base["movement"] = movement
    base["outcome"] = {
        "branch": "abstention",
        "answer": None,
        "abstention": outcome_draft["abstention"],
        "clarification": None,
    }
    return base


_DRIVER_INDEX_RE = re.compile(r"^drivers\[(\d+)\]")


def _resolve_tier(tier_from: str, drivers: list[dict[str, Any]], top_tier: str) -> str:
    """`tier_from` is model-authored (narrate.md asks for pointers like
    'drivers[0]'), so it is untrusted input, not a value the pipeline
    controls the exact shape of - a live model may reasonably write
    'drivers[0].tests[0]' or similar to point at a specific test rather than
    the driver as a whole. Only the leading 'drivers[N]' is meaningful for
    tier lookup; anything else after it is ignored rather than rejected."""
    m = _DRIVER_INDEX_RE.match(tier_from)
    if m:
        idx = int(m.group(1))
        if 0 <= idx < len(drivers):
            return drivers[idx]["tier"]
    return top_tier


def _numerals_in(text: str) -> list[float]:
    from engine.validator import extract_numerals

    return extract_numerals(text)
