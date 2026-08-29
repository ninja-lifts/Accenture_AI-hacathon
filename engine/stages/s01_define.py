"""Stage 01 - Define.

Resolve the contract, apply entitlement predicates, execute the contract SQL,
return the full history (not just the focal window - Stage 02 needs prior
periods to fit a baseline) with declared freshness per source. A mismatch
between the contract's declared source and what the warehouse actually has is
a data-quality failure, not a silent coercion."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pandas as pd

from engine import entitlements
from engine.telemetry import stage

# Which fact table each contract's declared source_id maps to, and how stale
# it is allowed to be treated as "live" for freshness reporting. In a real
# warehouse this would be metadata Stage 01 reads off the source system; here
# it is declared once because Meridian has no live ingestion clock.
_SOURCE_FRESHNESS_OVERRIDE = {
    # channel-scoped freshness lag, populated by data/generate.py for SC-16.
    "fact_orders": {"Partner": 40 * 3600},
}


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    contract = ctx["contracts"][ctx["kpi_id"]]
    ctx["contract"] = contract

    with stage("01_define", ctx["telemetry"]):
        entitlement = entitlements.resolve(ctx["persona"], contract, ctx.get("role_id"))
        ctx["entitlement"] = entitlement

        segment = ctx.get("segment") or {}
        segment_predicate = " AND ".join(
            f"{col} = '{val}'" for col, val in segment.items() if val is not None
        ) or "TRUE"

        sql = (
            f"SELECT * FROM ({contract['definition']['sql']}) t "
            f"WHERE ({entitlement['row_predicate']}) AND ({segment_predicate}) "
            f"ORDER BY ts"
        )
        try:
            series = ctx["con"].execute(sql).df()
        except Exception as exc:  # noqa: BLE001 - a broken contract/warehouse mismatch
            ctx["data_quality_failure"] = True
            ctx["data_quality_reason"] = f"contract SQL failed against the warehouse: {exc}"
            ctx["series"] = pd.DataFrame(columns=["ts", "region", "category", "channel", "value", "support_size"])
            ctx["sources"] = []
            return ctx

        if "ts" in series.columns:
            series["ts"] = pd.to_datetime(series["ts"]).dt.date

        ctx["series"] = series
        # An empty series is not itself a data-quality failure - it might
        # simply be a category that has not launched yet (SC-10) or a window
        # with genuinely no activity. Stage 02 turns "too little history" into
        # a declared HYPOTHESIS-capped answer, not an abstention; only an
        # actual SQL/warehouse exception (the except branch above) counts as
        # data_quality_failure.
        ctx.setdefault("data_quality_failure", False)

        sources = []
        for src in contract.get("sources", []):
            row_count = int(len(series))
            freshness = src["expected_freshness_seconds"]
            quality_flags: list[str] = []
            channel_override = _SOURCE_FRESHNESS_OVERRIDE.get(src["table"].split(".")[-1], {})
            observed_channel = segment.get("channel")
            if observed_channel in channel_override:
                freshness = channel_override[observed_channel]
                quality_flags.append("stale_source")
            sources.append(
                {
                    "source_id": src["source_id"],
                    "as_of": _as_of(ctx),
                    "freshness_seconds": int(freshness),
                    "row_count": row_count,
                    "quality_flags": quality_flags,
                }
            )
        ctx["sources"] = sources

    return ctx


def _as_of(ctx: dict[str, Any]) -> str:
    today = ctx.get("today") or dt.date.today()
    return dt.datetime.combine(today, dt.time(6, 0)).isoformat() + "Z"
