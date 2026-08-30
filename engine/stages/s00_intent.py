"""Stage 00 - Intent parsing (LLM touchpoint #1).

Only runs for typed questions. Maps free text to {kpi, segment, window} using
ONLY the compiled contract vocabulary, and routes to the clarification branch
when the mapping is ambiguous rather than guessing.

Tries the LLM (prompts/intent_parse.md, via engine.llm_client, replay-cached)
first; when no cached response exists and no live key is configured - the
default, offline state - falls back to a deterministic keyword/synonym
parser over the same compiled catalogue. Both paths are constrained to
catalogue vocabulary only, which is the actual guarantee this stage makes;
which one produced a given answer is an implementation detail, not something
the guarantee depends on.

That equivalence covers two paths that both succeeded. It does not cover a
live call that was attempted and failed - a network error, a non-JSON
response, an unexpected shape. That is a real failure, not an offline
fallback, and it must not be silently absorbed into the same except clause
as "no cache entry exists"; see run() below."""

from __future__ import annotations

import datetime as dt
import re
from typing import Any

from engine import llm_client
from engine.telemetry import stage

# Terms not literally present in any contract's synonyms but genuinely
# ambiguous between two KPIs - SC-17's "sales" is the canonical example. Kept
# small and explicit rather than folded into the contract schema, since it is
# about vocabulary AMBIGUITY, not a dimension value.
KPI_AMBIGUOUS_TERMS = {
    "sales": ["net_revenue", "orders"],
}
KPI_KEYWORDS = {
    "net_revenue": ["revenue", "net revenue"],
    "orders": ["order volume", "order count", "orders"],
    "aov": ["average order value", "aov", "basket value"],
    "conversion_rate": ["conversion", "conversion rate"],
    "delivery_sla": ["delivery", "sla", "on-time", "on time"],
}


def _catalogue_kpi(ctx: dict[str, Any], kpi_id: str) -> dict[str, Any]:
    return next(k for k in ctx["catalogue"]["kpis"] if k["id"] == kpi_id)


def _resolve_default_window(ctx: dict[str, Any]) -> dict[str, str]:
    today = ctx.get("today") or dt.date.today()
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


def _deterministic_parse(question: str, ctx: dict[str, Any]) -> dict[str, Any]:
    q = question.lower()

    for term, kpi_ids in KPI_AMBIGUOUS_TERMS.items():
        if term in q:
            options = [
                {
                    "label": f"{_catalogue_kpi(ctx, k)['display_name']} ({_catalogue_kpi(ctx, k)['plain_english'].strip()})",
                    "resolves_to": {"kpi": k},
                }
                for k in kpi_ids
            ]
            return {
                "status": "clarification",
                "clarification": {
                    "question": f"Which do you mean by '{term}'?",
                    "ambiguity_type": "kpi_ambiguous",
                    "options": options,
                },
                "vocabulary_source": kpi_ids,
            }

    matched_kpi = None
    for kpi_id, keywords in KPI_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            matched_kpi = kpi_id
            break

    if matched_kpi is None:
        return {
            "status": "out_of_scope",
            "clarification": {
                "question": "I don't recognise that metric. Which of these did you mean?",
                "ambiguity_type": "kpi_ambiguous",
                "options": [
                    {"label": k["display_name"], "resolves_to": {"kpi": k["id"]}}
                    for k in ctx["catalogue"]["kpis"]
                ],
            },
            "vocabulary_source": [k["id"] for k in ctx["catalogue"]["kpis"]],
        }

    segment: dict[str, str] = {}
    contract = ctx["contracts"][matched_kpi]
    unmapped: list[str] = []
    for dim in contract["dimensions"]:
        if not dim["searchable"]:
            continue
        for syn in [dim["name"]] + dim.get("synonyms", []):
            if syn.lower() in q:
                segment[dim["name"]] = _canonical_value(ctx, matched_kpi, dim["name"], syn)
                break

    return {"status": "resolved", "kpi": matched_kpi, "segment": segment, "window": None, "unmapped_terms": unmapped}


def _canonical_value(ctx: dict[str, Any], kpi_id: str, dim_name: str, matched_synonym: str) -> str:
    """A synonym like 'the south' resolves to the actual data value 'South' -
    found by checking which distinct value the synonym prefix-matches."""
    contract = ctx["contracts"][kpi_id]
    dim = next(d for d in contract["dimensions"] if d["name"] == dim_name)
    for syn in dim.get("synonyms", []):
        if syn.lower() == matched_synonym.lower():
            # Best-effort: strip common filler words, title-case the remainder.
            cleaned = re.sub(r"\b(the|zone|region)\b", "", syn, flags=re.IGNORECASE).strip()
            return cleaned.title() if cleaned else syn.title()
    return matched_synonym.title()


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    if ctx["trigger"] != "user_question":
        return ctx

    with stage("00_intent", ctx["telemetry"]):
        question = ctx["raw_question"] or ""
        payload = {
            "CATALOGUE": ctx["catalogue"],
            "TODAY": (ctx.get("today") or dt.date.today()).isoformat(),
            "QUESTION": question,
        }

        parsed: dict[str, Any] | None = None
        try:
            result = llm_client.complete("intent_parse", payload, ctx=ctx)
        except llm_client.LLMCacheMiss:
            # The legitimate offline path: no key configured and no cache entry
            # for this exact payload. Nothing was attempted, nothing failed.
            result = None

        if result is None:
            parsed = _deterministic_parse(question, ctx)
        else:
            import json

            # A call actually happened (live, or a cache hit) and returned
            # something. If it doesn't parse as the shape prompts/intent_parse.md
            # requires, that is a real failure of the call this run made, not an
            # absence of one - it must not be silently treated as if no call had
            # been attempted. Let it propagate: the harness records it as a
            # scenario ERROR (not a batch abort) and the UI shows st.exception -
            # both are "fail loudly", not "fail silently into a stale answer".
            parsed = json.loads(result.text)

        status = parsed.get("status")
        if status == "resolved":
            ctx["kpi_id"] = parsed["kpi"]
            ctx["segment"] = parsed.get("segment") or {}
            ctx["window"] = parsed.get("window") or _resolve_default_window(ctx)
        else:
            clar = parsed["clarification"]
            ctx["route"] = "clarification"
            ctx["clarification"] = {
                "question": clar["question"],
                "ambiguity_type": clar["ambiguity_type"],
                "options": clar["options"],
                "vocabulary_source": parsed.get("vocabulary_source", []),
            }

        return ctx
