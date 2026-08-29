"""Stage 07 - Narrate (LLM touchpoint #2).

Sees no raw data - only the completed outcome object built by
engine/pipeline.py (movement, drivers with their tiers already assigned,
rejected hypotheses, the action). Turns it into persona-appropriate prose.
Every numeral in the output must already exist in that object;
engine/validator.py enforces it, and a failure regenerates once, then falls
back to the template renderer below - which, being built directly from the
same object, cannot introduce an unaccounted number by construction."""

from __future__ import annotations

import json
from typing import Any

from engine import llm_client, validator


def _template_answer(outcome_draft: dict[str, Any], persona: str) -> dict[str, Any]:
    ans = outcome_draft["answer"]
    kpi_name = outcome_draft["_kpi_display_name"]
    window = outcome_draft["_window"]
    headline_text = (
        f"{kpi_name} moved {ans['headline_delta_pct']:.1f}% "
        f"({ans['headline_delta_abs']:,.0f}) in the window to {window['focal_end']}."
    )
    sentences = [{"text": headline_text, "tier_from": "headline"}]

    for i, d in enumerate(ans["drivers"]):
        verb = "moved with" if d["tier"] in ("CORRELATED", "HYPOTHESIS") else "was driven by"
        share = f" (~{d['share_of_movement_pct']:.0f}% of the movement)" if d.get("share_of_movement_pct") is not None else ""
        sentences.append({"text": f"The movement {verb}: {d['statement']}{share}.", "tier_from": f"drivers[{i}]"})

    if ans.get("rejected_hypotheses"):
        r = ans["rejected_hypotheses"][0]
        sentences.append({"text": f"Ruled out: {r['statement']} ({r['detail']}).", "tier_from": "rejected_hypotheses[0]"})

    if ans.get("decomposition"):
        parts = ", ".join(f"{c['component']} {c['contribution_pct']:.0f}%" for c in ans["decomposition"])
        sentences.append({"text": f"Decomposition: {parts}.", "tier_from": "decomposition"})

    action = ans["action"]
    sentences.append(
        {
            "text": f"Recommended: {action['recommendation']} (owner: {action['owner']}).",
            "tier_from": "action",
        }
    )

    return {"headline": headline_text, "sentences": sentences}


def _template_abstention(outcome_draft: dict[str, Any], persona: str) -> dict[str, Any]:
    ab = outcome_draft["abstention"]
    headline_text = ab["statement"]
    sentences = [{"text": headline_text, "tier_from": "abstention"}]
    for i, r in enumerate(ab["ruled_out"]):
        sentences.append({"text": f"Ruled out: {r['statement']} ({r['detail']}).", "tier_from": f"ruled_out[{i}]"})
    sentences.append(
        {
            "text": f"Referred to {ab['referral']['team']}: {ab['referral']['why']}",
            "tier_from": "referral",
        }
    )
    return {"headline": headline_text, "sentences": sentences}


def _template_clarification(outcome_draft: dict[str, Any], persona: str) -> dict[str, Any]:
    clar = outcome_draft["clarification"]
    return {"headline": clar["question"], "sentences": [{"text": clar["question"], "tier_from": "clarification"}]}


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    branch = ctx["branch"]
    outcome_draft = ctx["outcome_draft"]
    persona = ctx["persona"]

    template_fn = {
        "answer": _template_answer,
        "abstention": _template_abstention,
        "clarification": _template_clarification,
    }[branch]

    narration = None
    if branch in ("answer", "abstention"):
        payload = {"FINDINGS": outcome_draft, "PERSONA": persona}
        for attempt in range(ctx["settings"].max_validator_retries):
            try:
                result = llm_client.complete("narrate", payload, ctx=ctx)
                candidate = json.loads(result.text)
                ok, unaccounted = validator.validate(candidate, outcome_draft)
                ctx["telemetry"].setdefault("validator_retries", 0)
                if ok:
                    narration = candidate
                    break
                ctx["telemetry"]["validator_retries"] += 1
            except (llm_client.LLMCacheMiss, llm_client.LLMCallCapExceeded, ValueError, KeyError):
                break

    if narration is None:
        narration = template_fn(outcome_draft, persona)

    ctx["narration"] = narration
    return ctx
