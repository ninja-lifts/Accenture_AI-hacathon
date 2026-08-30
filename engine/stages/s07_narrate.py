"""Stage 07 - Narrate (LLM touchpoint #2).

Sees no raw data - only the completed outcome object built by
engine/pipeline.py (movement, drivers with their tiers already assigned,
rejected hypotheses, the action). Turns it into persona-appropriate prose.
Every numeral in the output must already exist in that object;
engine/validator.py enforces it, and a rejection regenerates (bounded by
settings.max_validator_retries), then falls back to the template renderer
below - which, being built directly from the same object, cannot introduce
an unaccounted number by construction.

Two different things can exhaust that retry budget: the validator correctly
rejecting bad numbers (expected, telemetried via validator_retries, not an
error), and a live call returning something that doesn't parse at all (a
real failure). The first still falls back to the template silently, by
design. The second raises instead of falling back - see run() - because a
silently-rendered template is indistinguishable from a working live call to
anyone reading the output, and this stage's provenance is exactly what the
project promises never to misrepresent."""

from __future__ import annotations

import json
from typing import Any

from engine import llm_client, validator
from engine.telemetry import stage


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


def _trim_for_narration(outcome_draft: dict[str, Any]) -> dict[str, Any]:
    """A lighter payload for the narrate LLM call only - never mutates or
    replaces outcome_draft itself, which is what the schema-validated
    findings object, the UI, and evidence-recall scoring
    (eval/metrics.py::evidence_recall_at_5 reads drivers[].evidence directly)
    are built from. Two cuts, measured against a real captured SC-01 payload
    (CHANGELOG.md entry 020): Stage 05 attaches the SAME retrieved evidence
    pool to every candidate driver, so a scenario with 2 drivers sent the
    identical 6 documents/snippets twice (34% of the object, pure
    duplication) - deduplicated here into one pool, drivers keep only the
    ids they cite. localization's lower-ranked rows (3rd-8th) are dropped -
    prompts/narrate.md never references localization at all, and the
    unused rows are also unnecessary surface for a number to get attached to
    the wrong segment. Together this roughly halves the payload without
    removing any content the prompt actually asks for."""
    ans = outcome_draft.get("answer")
    if not isinstance(ans, dict):
        return outcome_draft

    evidence_pool: dict[str, dict[str, Any]] = {}
    trimmed_drivers = []
    for d in ans.get("drivers") or []:
        d2 = dict(d)
        ids = []
        for e in d.get("evidence") or []:
            doc_id = e.get("document_id")
            if doc_id and doc_id not in evidence_pool:
                evidence_pool[doc_id] = e
            ids.append(doc_id)
        d2["evidence_ids"] = ids
        d2.pop("evidence", None)
        trimmed_drivers.append(d2)

    trimmed_ans = dict(ans)
    trimmed_ans["drivers"] = trimmed_drivers
    trimmed_ans["evidence_pool"] = list(evidence_pool.values())
    trimmed_ans["localization"] = [s for s in (ans.get("localization") or []) if not s.get("suppressed")][:2]

    trimmed = dict(outcome_draft)
    trimmed["answer"] = trimmed_ans
    return trimmed


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    with stage("07_narrate", ctx["telemetry"]):
        branch = ctx["branch"]
        outcome_draft = ctx["outcome_draft"]
        persona = ctx["persona"]

        template_fn = {
            "answer": _template_answer,
            "abstention": _template_abstention,
            "clarification": _template_clarification,
        }[branch]

        narration = None
        live_attempt_failed = False
        if branch in ("answer", "abstention"):
            payload = {"FINDINGS": _trim_for_narration(outcome_draft), "PERSONA": persona}
            ctx["telemetry"].setdefault("validator_retries", 0)
            for attempt in range(ctx["settings"].max_validator_retries):
                try:
                    # force_live on retries: prompts/narrate.md runs at
                    # temperature 0.2 specifically so a rejected attempt has a
                    # real chance at a different result - the payload is
                    # identical across attempts (same outcome_draft/persona), so
                    # without this every attempt after the first would just
                    # replay attempt 1's cached (already-rejected) text via the
                    # resumable-cache path. See engine/llm_client.py::complete's
                    # own docstring and CHANGELOG.md entry 020.
                    result = llm_client.complete("narrate", payload, ctx=ctx, force_live=(attempt > 0))
                except llm_client.LLMCacheMiss:
                    # The legitimate offline path: no key, no cache entry for
                    # this exact payload. Nothing was attempted this call.
                    break
                try:
                    candidate = json.loads(result.text)
                    ok, unaccounted = validator.validate(candidate, outcome_draft)
                except (ValueError, KeyError):
                    # The call succeeded but the response doesn't parse as
                    # prompts/narrate.md's contract - a real failure of a call
                    # this run actually made. Counted against the same retry
                    # budget as a validator rejection (a transient bad
                    # generation shouldn't abort the whole run on the first
                    # attempt), but tracked separately so that if every attempt
                    # fails this way, it is raised rather than silently
                    # rendered as an unlabeled template.
                    ok = False
                    live_attempt_failed = True
                if ok:
                    narration = candidate
                    break
                ctx["telemetry"]["validator_retries"] += 1

            if narration is None and live_attempt_failed:
                raise RuntimeError(
                    f"prompts/narrate.md produced {ctx['settings'].max_validator_retries} "
                    "consecutive unparseable/invalid live responses this run - falling back "
                    "to the template would silently hide a real live-call failure behind "
                    "output that looks like the normal offline path. Check the provider/"
                    "model configuration, or retry."
                )

        if narration is None:
            narration = template_fn(outcome_draft, persona)

        ctx["narration"] = narration
        return ctx
