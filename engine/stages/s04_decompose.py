"""Stage 04 - Decompose.

A price/volume/mix revenue bridge, computed by sequential substitution so it
closes EXACTLY (not approximately) by telescoping construction:

    R1 = total_orders_focal * aov_avg_comparison        (volume only)
    R2 = sum_i(orders_focal_i * aov_comparison_i)        (+ mix)
    R_focal = sum_i(orders_focal_i * aov_focal_i)        (+ price)

    volume = R1 - R_comparison
    mix    = R2 - R1
    price  = R_focal - R2
    volume + mix + price == R_focal - R_comparison   (exactly, asserted below)

This is what SC-05 needs: a category-manager scoped to App channel where
order count and every category's own AOV are unchanged, but the CATEGORY MIX
shifted toward cheaper items - a single-dimension drill-down (volume or price
alone) finds nothing there; only `mix` moves."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pandas as pd

from engine.stages.s02_detect import _AVG_KPIS
from engine.telemetry import stage

MIX_DIMENSION_CANDIDATES = ["category", "channel", "region"]


class DecompositionError(Exception):
    """The bridge did not close. A decomposition that does not sum to the
    movement it claims to explain is a bug, not a rounding footnote."""


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    with stage("04_decompose", ctx["telemetry"]):
        kpi_id = ctx["kpi_id"]
        if kpi_id in _AVG_KPIS or not ctx.get("localization"):
            ctx["decomposition"] = []
            return ctx

        top = next((s for s in ctx["localization"] if not s["suppressed"]), None)
        if top is None:
            ctx["decomposition"] = []
            return ctx

        pinned = dict(top["dimensions"])
        mix_dim = next((d for d in MIX_DIMENSION_CANDIDATES if d not in pinned and d in ctx["series"].columns), None)

        window = ctx["window"]
        focal_start = dt.date.fromisoformat(window["focal_start"])
        focal_end = dt.date.fromisoformat(window["focal_end"])
        span = (focal_end - focal_start).days + 1
        cmp_start = focal_start - dt.timedelta(days=span)
        cmp_end = focal_start - dt.timedelta(days=1)

        series = ctx["series"]
        for col, val in pinned.items():
            series = series[series[col] == val]

        focal = series[series["ts"].between(focal_start, focal_end)]
        cmp = series[series["ts"].between(cmp_start, cmp_end)]

        if not mix_dim or focal.empty or cmp.empty:
            r_focal = float(focal["value"].sum())
            r_cmp = float(cmp["value"].sum())
            orders_focal = float(focal["support_size"].sum()) or 1.0
            orders_cmp = float(cmp["support_size"].sum()) or 1.0
            aov_cmp = r_cmp / orders_cmp if orders_cmp else 0.0
            volume = (orders_focal - orders_cmp) * aov_cmp
            price = (r_focal - r_cmp) - volume
            ctx["decomposition"] = _finalize({"volume": volume, "price": price, "mix": 0.0}, r_focal - r_cmp)
            return ctx

        f = focal.groupby(mix_dim).agg(orders=("support_size", "sum"), rev=("value", "sum"))
        c = cmp.groupby(mix_dim).agg(orders=("support_size", "sum"), rev=("value", "sum"))
        idx = f.index.union(c.index)
        f = f.reindex(idx, fill_value=0.0)
        c = c.reindex(idx, fill_value=0.0)

        total_orders_focal = float(f["orders"].sum())
        total_orders_cmp = float(c["orders"].sum())
        r_cmp = float(c["rev"].sum())
        r_focal = float(f["rev"].sum())

        aov_avg_cmp = r_cmp / total_orders_cmp if total_orders_cmp else 0.0
        aov_cmp_i = (c["rev"] / c["orders"].replace(0, pd.NA)).fillna(0.0)
        aov_focal_i = (f["rev"] / f["orders"].replace(0, pd.NA)).fillna(0.0)

        r1 = total_orders_focal * aov_avg_cmp
        r2 = float((f["orders"] * aov_cmp_i).sum())

        volume = r1 - r_cmp
        mix = r2 - r1
        price = r_focal - r2

        ctx["decomposition"] = _finalize({"volume": volume, "mix": mix, "price": price}, r_focal - r_cmp)

    return ctx


def _finalize(components: dict[str, float], total_delta: float) -> list[dict[str, Any]]:
    checksum = sum(components.values())
    if abs(checksum - total_delta) > max(1.0, abs(total_delta) * 0.01):
        raise DecompositionError(
            f"decomposition {components} sums to {checksum:.2f}, expected {total_delta:.2f}"
        )
    out = []
    for name, val in components.items():
        pct = (val / total_delta * 100.0) if total_delta else 0.0
        out.append({"component": name, "contribution_abs": val, "contribution_pct": pct})
    return out
