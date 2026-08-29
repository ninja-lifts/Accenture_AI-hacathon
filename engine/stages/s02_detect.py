"""Stage 02 - Detect.

Seasonal baseline, dual materiality, registry suppression. The contract
declares `method: stl_residual_control`; this implements it as an explicit
day-of-week x month x festival_calendar multiplicative decomposition rather
than calling statsmodels.tsa.seasonal.STL directly, because STL wants at
least two full seasonal cycles (104 weeks) to be numerically stable and
Meridian's history is ~16 months - a leave-one-out dow/month/festival
decomposition is the same idea (learn seasonality from history, hold it
against the focal window) without that data requirement, and degrades the
same way STL would: fewer prior occurrences of a month means a noisier, not
wrong, month_factor estimate."""

from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np
import pandas as pd

from engine.telemetry import stage

_AVG_KPIS = {"aov", "conversion_rate", "delivery_sla"}
TREND_WINDOW_DAYS = 45
MIN_TREND_PERIODS = 10


def _aggregate_daily(series: pd.DataFrame, kpi_id: str) -> pd.Series:
    if series.empty:
        return pd.Series(dtype=float)
    if kpi_id in _AVG_KPIS:
        weighted = series.assign(_w=series["value"] * series["support_size"])
        g = weighted.groupby("ts").agg(_w=("_w", "sum"), _n=("support_size", "sum"))
        return (g["_w"] / g["_n"].replace(0, np.nan)).fillna(0.0)
    return series.groupby("ts")["value"].sum()


def _festival_factor(con: Any, d: dt.date) -> float:
    row = con.execute(
        "SELECT uplift FROM festival_calendar WHERE ? BETWEEN start_date AND end_date LIMIT 1",
        [d],
    ).fetchone()
    return 1.0 + row[0] if row else 1.0


def _fit_seasonality(history: pd.Series, con: Any) -> tuple[dict[int, float], dict[int, float], pd.Series]:
    """Returns (dow_factor, month_factor, trend) fit on `history` (a daily
    Series indexed by date, strictly before the focal window)."""
    idx = pd.to_datetime(history.index)
    trend = history.rolling(TREND_WINDOW_DAYS, min_periods=MIN_TREND_PERIODS).mean()
    trend = trend.bfill().ffill()
    trend = trend.replace(0, np.nan).fillna(history.mean() or 1.0)

    detrended = (history / trend).replace([np.inf, -np.inf], np.nan).fillna(1.0)

    dow = pd.Series(idx.dayofweek, index=history.index)
    dow_factor_raw = detrended.groupby(dow).mean()
    dow_factor_raw = dow_factor_raw / (dow_factor_raw.mean() or 1.0)
    dow_factor = {int(k): float(v) for k, v in dow_factor_raw.items()}

    dow_adjusted = detrended / dow.map(dow_factor).replace(0, np.nan).fillna(1.0).to_numpy()
    month = pd.Series(idx.month, index=history.index)
    month_factor_raw = pd.Series(dow_adjusted.to_numpy(), index=history.index).groupby(month).mean()
    month_factor_raw = month_factor_raw / (month_factor_raw.mean() or 1.0)
    month_factor = {int(k): float(v) for k, v in month_factor_raw.items()}

    return dow_factor, month_factor, trend


def _expected_series(
    dates: list[dt.date],
    trend_level: float,
    dow_factor: dict[int, float],
    month_factor: dict[int, float],
    con: Any,
) -> pd.Series:
    values = [
        trend_level
        * dow_factor.get(d.weekday(), 1.0)
        * month_factor.get(d.month, 1.0)
        * _festival_factor(con, d)
        for d in dates
    ]
    return pd.Series(values, index=dates)


def _window_dates(start: dt.date, end: dt.date) -> list[dt.date]:
    return [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    with stage("02_detect", ctx["telemetry"]):
        contract = ctx["contract"]
        kpi_id = ctx["kpi_id"]
        det = contract["detection"]
        con = ctx["con"]

        window = ctx["window"]
        focal_start = dt.date.fromisoformat(window["focal_start"])
        focal_end = dt.date.fromisoformat(window["focal_end"])
        window_days = (focal_end - focal_start).days + 1

        # daily is indexed by plain datetime.date (s01_define normalises
        # ts to .date), so history/focal splits are simple date comparisons.
        daily = _aggregate_daily(ctx["series"], kpi_id)
        history = daily[daily.index < focal_start] if not daily.empty else daily

        n_history_days = (focal_start - history.index.min()).days if len(history) else 0
        ctx["history_periods_ok"] = n_history_days >= det["min_history_periods"]

        if len(history) < MIN_TREND_PERIODS:
            # Not enough history to fit anything - report the raw window mean
            # as both observed and expected (no surprise claimed) and let the
            # sparse-history degradation (Stage gate) cap the tier.
            focal_dates = _window_dates(focal_start, focal_end)
            observed_series = daily.reindex(focal_dates, fill_value=0.0)
            observed = float(observed_series.sum()) if kpi_id not in _AVG_KPIS else float(observed_series.mean())
            ctx["movement"] = _movement_payload(observed, observed, observed, observed, None, det, False)
            return ctx

        dow_factor, month_factor, trend = _fit_seasonality(history, con)
        trend_level = float(trend.iloc[-1])

        focal_dates = _window_dates(focal_start, focal_end)
        expected_daily = _expected_series(focal_dates, trend_level, dow_factor, month_factor, con)
        observed_daily = daily.reindex(focal_dates, fill_value=0.0)

        agg = "mean" if kpi_id in _AVG_KPIS else "sum"
        observed = float(getattr(observed_daily, agg)())
        expected = float(getattr(expected_daily, agg)())

        # z-score: compare this window's residual to the residual of many
        # prior same-length rolling windows, using the SAME fitted model -
        # this is what makes the z scale-free across a 2-day PSP outage and a
        # 6-week erosion window without hand-tuning per scenario.
        resid_fracs = []
        stride = max(1, window_days // 2) if window_days > 3 else 1
        cursor_end = focal_start - dt.timedelta(days=1)
        for _ in range(24):
            cursor_start = cursor_end - dt.timedelta(days=window_days - 1)
            if cursor_start < history.index.min() if len(history) else True:
                break
            wdates = _window_dates(cursor_start, cursor_end)
            w_obs = daily.reindex(wdates, fill_value=0.0)
            w_exp = _expected_series(wdates, trend_level, dow_factor, month_factor, con)
            o = float(getattr(w_obs, agg)())
            e = float(getattr(w_exp, agg)())
            if e:
                resid_fracs.append((o - e) / e)
            cursor_end = cursor_end - dt.timedelta(days=stride)

        resid_std = float(np.std(resid_fracs)) if len(resid_fracs) >= 4 else 0.0
        resid_std = max(resid_std, 1e-6)
        z = ((observed - expected) / expected) / resid_std if expected else 0.0

        ctx["movement"] = _movement_payload(observed, expected, observed, observed, z, det, True)

        registry_hit = _check_registry(con, kpi_id, ctx.get("segment") or {}, focal_start, focal_end)
        if registry_hit:
            ctx["movement"]["materiality"]["suppressed_by_registry"] = True
            ctx["movement"]["materiality"]["registry_entry_id"] = registry_hit

    return ctx


def _movement_payload(observed, expected, lo, hi, z, det, has_model) -> dict[str, Any]:
    delta_abs = observed - expected
    delta_pct = (delta_abs / expected * 100.0) if expected else 0.0
    materiality = {
        "statistically_surprising": bool(has_model and z is not None and abs(z) >= det["materiality"]["min_z"]),
        "materially_large": bool(abs(delta_abs) >= det["materiality"]["min_abs_impact"]),
        "suppressed_by_registry": False,
        "registry_entry_id": None,
    }
    return {
        "observed": observed,
        "expected": expected,
        "expected_lo": expected * 0.95,
        "expected_hi": expected * 1.05,
        "delta_abs": delta_abs,
        "delta_pct": delta_pct,
        "z_score": z,
        "materiality": materiality,
    }


def _check_registry(con: Any, kpi_id: str, segment: dict[str, Any], start: dt.date, end: dt.date) -> str | None:
    rows = con.execute(
        "SELECT registry_entry_id, region, category, channel, window_start, window_end "
        "FROM context_registry WHERE kpi = ?",
        [kpi_id],
    ).fetchall()
    for entry_id, region, category, channel, w_start, w_end in rows:
        if isinstance(w_start, str):
            w_start = dt.date.fromisoformat(w_start)
        if isinstance(w_end, str):
            w_end = dt.date.fromisoformat(w_end)
        if not (w_start <= end and w_end >= start):
            continue
        for dim, val in (("region", region), ("category", category), ("channel", channel)):
            seg_val = segment.get(dim)
            if val is not None and seg_val is not None and val != seg_val:
                break
        else:
            return entry_id
    return None
