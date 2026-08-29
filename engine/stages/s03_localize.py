"""Stage 03 - Localize.

Search the dimension lattice for the smallest cell set explaining most of the
movement, then apply small-cell suppression. Attribution assumes each segment
would otherwise have moved in proportion to the whole (the same assumption
Adtributor and its lineage make): a segment's expected value is its own
comparison-period actual, scaled by the aggregate's fitted growth factor from
Stage 02, so a 1-way partition's contributions sum exactly to
movement.delta_abs by construction. A 2-way search over the strongest 1-way
candidates is what finds a combination (e.g. South x Audio) that concentrates
more of the movement than either dimension alone - the case a single-dimension
drill-down (baseline B1) cannot see."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pandas as pd

from engine.entitlements import suppress_small_cells
from engine.stages.s02_detect import _AVG_KPIS
from engine.telemetry import stage

DIMENSIONS = ["region", "category", "channel"]
TOP_K_PER_DIM = 3
MAX_SEGMENTS_RETURNED = 8
MIN_CONCENTRATION_RATIO = 1.8


def _agg(df: pd.DataFrame, by: list[str], kpi_id: str) -> pd.DataFrame:
    if not by:
        support = float(df["support_size"].sum())
        if kpi_id in _AVG_KPIS:
            value = float((df["value"] * df["support_size"]).sum() / support) if support else 0.0
        else:
            value = float(df["value"].sum())
        return pd.DataFrame({"value": [value], "support_size": [support]})
    if kpi_id in _AVG_KPIS:
        w = df.assign(_w=df["value"] * df["support_size"])
        g = w.groupby(by).agg(_w=("_w", "sum"), support_size=("support_size", "sum"))
        g["value"] = g["_w"] / g["support_size"].replace(0, float("nan"))
        return g.drop(columns="_w").reset_index()
    return df.groupby(by).agg(value=("value", "sum"), support_size=("support_size", "sum")).reset_index()


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    with stage("03_localize", ctx["telemetry"]):
        series = ctx["series"]
        kpi_id = ctx["kpi_id"]
        window = ctx["window"]
        focal_start = dt.date.fromisoformat(window["focal_start"])
        focal_end = dt.date.fromisoformat(window["focal_end"])
        span = (focal_end - focal_start).days + 1
        cmp_start = focal_start - dt.timedelta(days=span)
        cmp_end = focal_start - dt.timedelta(days=1)

        given_segment = {k: v for k, v in (ctx.get("segment") or {}).items() if v is not None}
        # A dimension can already be pinned to a single value without being
        # in ctx['segment'] - most commonly a category_manager's row_predicate
        # restricting the series to one category before Stage 03 ever runs.
        # Treat that the same as an explicitly given segment: it is not
        # something to search, it is already the scope.
        for dim in DIMENSIONS:
            if dim in given_segment or dim not in series.columns or series.empty:
                continue
            uniques = series[dim].dropna().unique()
            if len(uniques) == 1:
                given_segment[dim] = uniques[0]
        free_dims = [d for d in DIMENSIONS if d not in given_segment and d in series.columns]

        if series.empty or not free_dims:
            # The scope is already as narrow as it can go (every dimension is
            # pinned, e.g. the harness handed us the exact segment already) -
            # localization is confirmatory, not a search.
            seg = {
                "dimensions": dict(given_segment),
                "contribution_abs": ctx["movement"]["delta_abs"],
                "contribution_pct": ctx["movement"]["delta_pct"],
                "rank": 1,
                "suppressed": False,
                "suppression_reason": None,
                "support_size": int(series["support_size"].sum()) if not series.empty else None,
            }
            segs, n_sup = suppress_small_cells([seg], ctx["entitlement"]["min_cell_size"])
            ctx["localization"] = segs
            ctx["security"]["cells_suppressed"] += n_sup
            return ctx

        focal = series[series["ts"].between(focal_start, focal_end)]
        cmp = series[series["ts"].between(cmp_start, cmp_end)]

        growth_factor = (
            ctx["movement"]["expected"] / ctx["movement"]["observed"]
            if kpi_id in _AVG_KPIS
            else (
                ctx["movement"]["expected"] / (cmp["value"].sum() or 1.0)
                if not cmp.empty
                else 1.0
            )
        )

        candidates: list[dict[str, Any]] = []

        def contribution(sub_focal: pd.DataFrame, sub_cmp: pd.DataFrame, dims: dict[str, str]) -> dict[str, Any]:
            actual_focal = _agg(sub_focal, [], kpi_id)["value"].iloc[0] if not sub_focal.empty else 0.0
            actual_cmp = _agg(sub_cmp, [], kpi_id)["value"].iloc[0] if not sub_cmp.empty else 0.0
            if kpi_id in _AVG_KPIS:
                expected = actual_cmp  # ratio KPIs: "expected" is proportional shift already in growth_factor via mean level, not multiplied twice
            else:
                expected = actual_cmp * growth_factor
            contribution_abs = actual_focal - expected
            support = int(sub_focal["support_size"].sum()) if not sub_focal.empty else 0
            return {
                "dimensions": dims,
                "contribution_abs": float(contribution_abs),
                "support_size": support,
            }

        # Only trust a dimension's ranking if its top value actually
        # DOMINATES the others - a movement spread roughly evenly across
        # every value of a dimension (SC-09's definition drift, which
        # touches the whole business, not one region) must not be reported
        # as "localized" just because Poisson noise makes one value the
        # nominal top by a hair. Concentration = top / median(rest).
        concentrated_dims = []
        one_way: dict[str, list[dict[str, Any]]] = {}
        for dim in free_dims:
            values = sorted(series[dim].dropna().unique().tolist())
            rows = []
            for val in values:
                sub_focal = focal[focal[dim] == val]
                sub_cmp = cmp[cmp[dim] == val]
                rows.append(contribution(sub_focal, sub_cmp, {**given_segment, dim: val}))
            rows.sort(key=lambda r: abs(r["contribution_abs"]), reverse=True)
            one_way[dim] = rows
            rest = [abs(r["contribution_abs"]) for r in rows[1:]]
            rest_median = sorted(rest)[len(rest) // 2] if rest else 0.0
            top_abs = abs(rows[0]["contribution_abs"]) if rows else 0.0
            if top_abs >= MIN_CONCENTRATION_RATIO * max(rest_median, 1e-9):
                concentrated_dims.append(dim)
                candidates.extend(rows[:TOP_K_PER_DIM])

        if len(concentrated_dims) >= 2:
            for i, dim_a in enumerate(concentrated_dims):
                for dim_b in concentrated_dims[i + 1 :]:
                    top_a = [r["dimensions"][dim_a] for r in one_way[dim_a][:TOP_K_PER_DIM]]
                    top_b = [r["dimensions"][dim_b] for r in one_way[dim_b][:TOP_K_PER_DIM]]
                    for va in top_a:
                        for vb in top_b:
                            sub_focal = focal[(focal[dim_a] == va) & (focal[dim_b] == vb)]
                            sub_cmp = cmp[(cmp[dim_a] == va) & (cmp[dim_b] == vb)]
                            candidates.append(
                                contribution(sub_focal, sub_cmp, {**given_segment, dim_a: va, dim_b: vb})
                            )

        if not concentrated_dims:
            # Nothing concentrates in any single free dimension - the honest
            # localization is "broad-based, not attributable to one segment",
            # not whichever noisy cell happened to rank first.
            candidates = [contribution(focal, cmp, dict(given_segment))]

        candidates.sort(key=lambda r: abs(r["contribution_abs"]), reverse=True)
        deduped: list[dict[str, Any]] = []
        seen = set()
        for c in candidates:
            key = tuple(sorted(c["dimensions"].items()))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(c)

        total_delta = ctx["movement"]["delta_abs"] or 1.0
        segments = []
        for i, c in enumerate(deduped[:MAX_SEGMENTS_RETURNED], start=1):
            segments.append(
                {
                    "dimensions": c["dimensions"],
                    "contribution_abs": c["contribution_abs"],
                    "contribution_pct": c["contribution_abs"] / total_delta * 100.0,
                    "rank": i,
                    "suppressed": False,
                    "suppression_reason": None,
                    "support_size": c["support_size"],
                }
            )

        segments, n_suppressed = suppress_small_cells(segments, ctx["entitlement"]["min_cell_size"])
        ctx["localization"] = segments
        ctx["security"]["cells_suppressed"] += n_suppressed

    return ctx
