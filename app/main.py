"""Streamlit UI. Deliberately thin - roughly 20% of the effort.

The webpage is the window; the engine is the prototype. Anything that looks
like analysis happening in this file is a bug - every number rendered here is
read straight off a findings object the pipeline already computed and the
schema already validated.

Two screens, one page:
    Sidebar   - persona switcher, scenario picker (SC-01..SC-17, including
                the ones that don't pass), a raw question box
    Main      - the findings view: tiered narrative, evidence drawer with
                injection-flag warnings, action card, decomposition,
                rejected hypotheses, telemetry footer, and a REPLAYING /
                LIVE banner - silent replay would be dishonest.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import streamlit as st
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import config, pipeline  # noqa: E402
from eval.harness import SCENARIO_RUN_CONFIG  # noqa: E402

TODAY = dt.date(2026, 8, 22)
TIER_COLOR = {
    "VERIFIED": "#1a7f37", "EVIDENCED": "#2b6cb0", "TESTED": "#6b46c1",
    "CORRELATED": "#b7791f", "HYPOTHESIS": "#c05621", "UNKNOWN": "#718096",
}
TIER_GLOSS = {
    "VERIFIED": "Recomputed from source. Arithmetic, not judgement.",
    "EVIDENCED": "Supported by specific documents we can show you.",
    "TESTED": "We tried to disprove this and failed.",
    "CORRELATED": "Moves together with the metric. Not established as a cause.",
    "HYPOTHESIS": "A plausible lead with no support yet.",
    "UNKNOWN": "We are not willing to grade this.",
}


@st.cache_data(show_spinner=False)
def load_manifest() -> list[dict]:
    manifest = yaml.safe_load(Path("data/injection_manifest.yaml").read_text(encoding="utf-8"))
    return manifest["scenarios"]


def clear_replay_cache(cache_dir: Path) -> int:
    """Delete cached LLM responses only. Scoped to cache_dir's own
    narrate/intent_parse subfolders - structurally cannot reach data/,
    which lives under a separate directory this function never opens."""
    removed = 0
    for sub in ("narrate", "intent_parse"):
        subdir = cache_dir / sub
        if not subdir.is_dir():
            continue
        for f in subdir.glob("*.json"):
            f.unlink()
            removed += 1
    return removed


def tier_badge(tier: str) -> str:
    color = TIER_COLOR.get(tier, "#718096")
    gloss = TIER_GLOSS.get(tier, "")
    return (
        f'<span title="{gloss}" style="background:{color};color:white;'
        f'padding:2px 8px;border-radius:10px;font-size:0.75em;font-weight:600;">{tier}</span>'
    )


def run_scenario_in_app(scenario_id: str, persona_override: str | None) -> dict:
    scenarios = {s["id"]: s for s in load_manifest()}
    scenario = scenarios[scenario_id]
    config = dict(SCENARIO_RUN_CONFIG[scenario_id])
    if persona_override:
        config["persona"] = persona_override
        if persona_override != "category_manager":
            config.pop("role_id", None)
        elif "role_id" not in config:
            config["role_id"] = "cm_audio"
    if config.get("trigger") != "user_question":
        fw = scenario["focal_window"]
        start = dt.date.fromisoformat(fw["start"])
        end = dt.date.fromisoformat(fw["end"])
        span = (end - start).days + 1
        cmp_end = start - dt.timedelta(days=1)
        cmp_start = cmp_end - dt.timedelta(days=span - 1)
        config["window"] = {
            "focal_start": start.isoformat(), "focal_end": end.isoformat(),
            "comparison_start": cmp_start.isoformat(), "comparison_end": cmp_end.isoformat(), "grain": "day",
        }
    return pipeline.run(today=TODAY, scenario_id=scenario_id, **config)


def render_evidence(evidence: list[dict]) -> None:
    for e in evidence:
        flag = " ⚠️ **flagged: possible prompt injection**" if e.get("flagged_injection") else ""
        with st.expander(f"{e['document_id']} · {e['source']} · score {e['retrieval_score']:.2f}{flag}"):
            st.write(e["snippet"])
            st.caption(f"Published {e['published_at']}")
            if e.get("flagged_injection"):
                st.warning(
                    "This document matched an injection pattern. It is shown here as ordinary "
                    "cited evidence - the narrator was instructed to treat its text as inert, "
                    "never as an instruction."
                )


def render_findings(findings: dict) -> None:
    replay = findings.get("provenance", {}).get("replay_mode")
    if findings.get("kind") == "no_alert":
        st.info("**No alert.** The materiality/registry gate did not escalate this to a full investigation.")
        mv = findings["movement"]
        st.metric("Movement", f"{mv['delta_pct']:.1f}%", delta=f"{mv['delta_abs']:,.0f}")
        st.json(mv["materiality"])
        return

    if replay is not None:
        st.caption("🔁 REPLAYING a committed model response (no live key configured)" if replay
                   else "🟢 LIVE model call")

    branch = findings["outcome"]["branch"]

    if branch == "clarification":
        clar = findings["outcome"]["clarification"]
        st.warning(f"**{clar['question']}**")
        for opt in clar["options"]:
            st.button(opt["label"], key=opt["label"], disabled=True)
        st.caption(f"Ambiguity type: {clar['ambiguity_type']} · vocabulary source: {', '.join(clar['vocabulary_source'])}")
        return

    if branch == "abstention":
        ab = findings["outcome"]["abstention"]
        st.error(f"**Abstained** — {ab['reason_code']}")
        st.markdown(ab["statement"])
        if ab["ruled_out"]:
            st.markdown("**Ruled out:**")
            for r in ab["ruled_out"]:
                st.markdown(f"- {r['statement']} — *{r['detail']}* (`{r['rejected_by']}`)")
        st.markdown(f"**Referred to {ab['referral']['team']}:** {ab['referral']['why']}")
        return

    ans = findings["outcome"]["answer"]
    st.markdown(f"### {ans['headline']['text']} {tier_badge(ans['headline']['tier'])}", unsafe_allow_html=True)

    st.markdown("**Narrative**")
    for s in ans["narrative"]:
        st.markdown(f"{tier_badge(s['tier'])} &nbsp; {s['text']}", unsafe_allow_html=True)

    if ans["localization"]:
        st.markdown("**Localization**")
        st.dataframe(
            [
                {"dimensions": str(seg["dimensions"]), "contribution_abs": seg["contribution_abs"],
                 "contribution_pct": seg["contribution_pct"], "suppressed": seg["suppressed"]}
                for seg in ans["localization"]
            ],
            hide_index=True,
        )

    if ans["decomposition"]:
        st.markdown("**Decomposition** *(VERIFIED — recomputed from source, closes exactly)*")
        st.bar_chart({d["component"]: d["contribution_abs"] for d in ans["decomposition"]})

    if ans["rejected_hypotheses"]:
        st.markdown("**Rejected hypotheses**")
        for r in ans["rejected_hypotheses"]:
            st.markdown(f"- ~~{r['statement']}~~ — *{r['detail']}* (`{r['rejected_by']}`)")

    st.markdown("**Evidence**")
    all_evidence = {e["document_id"]: e for d in ans["drivers"] for e in d.get("evidence", [])}
    render_evidence(list(all_evidence.values()))

    action = ans["action"]
    with st.container(border=True):
        st.markdown(f"**Action** — {action['recommendation']}")
        st.caption(
            f"Lever: `{action['lever']}` · Owner: {action['owner']} · "
            f"Confidence: {action['confidence']} · Review in {action['monitoring']['check_after_days']} days"
        )

    with st.expander("Telemetry & security"):
        st.json(findings["telemetry"])
        st.json(findings["security"])
        st.caption(f"entitlements_hash: {findings['request']['principal']['entitlements_hash']}")

        sources = findings.get("provenance", {}).get("sources", [])
        if sources:
            st.markdown("**Sources**")
            for src in sources:
                flags = src.get("quality_flags") or []
                flag_text = f" ⚠️ {', '.join(flags)}" if flags else ""
                st.caption(f"`{src['source_id']}` · as of {src['as_of']} · {src['row_count']:,} rows{flag_text}")


def main() -> None:
    st.set_page_config(page_title="GlassBox", page_icon="🔍", layout="wide")
    st.title("GlassBox")
    st.caption("Every dashboard tells you *what* changed. This tells you *why* — and says \"I don't know\" when the data doesn't support an answer.")

    scenarios = load_manifest()

    with st.sidebar:
        st.header("Scenario picker")
        st.caption("Includes the ones that don't pass — see eval/scorecard.md for why.")
        options = {f"{s['id']} — {s['title'][:40]}": s["id"] for s in scenarios}
        label = st.selectbox("Scenario", list(options.keys()))
        scenario_id = options[label]
        scenario = next(s for s in scenarios if s["id"] == scenario_id)
        st.caption(f"Difficulty: {scenario['difficulty']} · Expected: {scenario['expected_branch']}")

        st.header("Persona")
        persona = st.radio(
            "View as", ["(scenario default)", "cfo", "category_manager", "analyst"],
            help="Switching persona re-runs the pipeline with a different entitlement predicate — a genuinely different SQL query, not a UI filter.",
        )
        persona_override = None if persona == "(scenario default)" else persona

        run = st.button("Run", type="primary")

        st.divider()
        st.header("Cache")
        settings = config.load()
        live_ready = (not settings.replay_mode) and bool(settings.llm_api_key)
        if live_ready:
            st.caption(f"Live key configured ({settings.llm_provider}). Safe to clear.")
            confirm_clear = st.checkbox("I understand this deletes cached responses")
            if st.button("🗑️ Clear cache", disabled=not confirm_clear):
                removed = clear_replay_cache(Path(settings.replay_cache))
                st.success(f"Cleared {removed} cached response(s) — the next Run calls the live model fresh.")
        else:
            st.button("🗑️ Clear cache", disabled=True)
            st.caption(
                "Disabled: no live key configured (`GLASSBOX_REPLAY=0` + "
                "`GLASSBOX_LLM_API_KEY`). Clearing without one would leave "
                "scenarios with nothing to replay and no way to regenerate. "
                "Only ever clears `eval/replay_cache/` — never the dataset."
            )

    if not run:
        st.info("Pick a scenario in the sidebar and click **Run**. Offline by default — no API key needed; responses come from the committed replay cache, and the app says so above the result.")
        return

    with st.spinner("Running the seven-stage pipeline…"):
        try:
            findings = run_scenario_in_app(scenario_id, persona_override)
        except Exception as exc:  # noqa: BLE001 - show the error in the UI rather than a stack trace
            st.exception(exc)
            return

    render_findings(findings)


if __name__ == "__main__":
    main()
