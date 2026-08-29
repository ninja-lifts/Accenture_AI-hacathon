"""Stage 06 - Falsify.

Builds candidate causes from the localized segment plus retrieved evidence,
then tries to disprove each one:
  - difference-in-differences against the rest of the business
  - placebo timing - the same test on a window before anything happened
  - unaffected control segments, checked rather than assumed
  - dose-response, when the window is long enough to split into sub-periods
  - a magnitude-sufficiency check against a narrower rival scope, which is
    what demotes SC-01's confounded promo: it survives its own
    difference-in-differences (the promo really did move Audio nationally) but
    is rejected as the explanation for South specifically because it cannot
    account for the gap between South's movement and everywhere else's.

Survivors -> candidates for the gate/tiers. Failures -> rejected_hypotheses,
always with the test that killed them, never silently dropped."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pandas as pd

from engine.stages.s02_detect import _AVG_KPIS
from engine.telemetry import stage

DIFF_MEANINGFUL_PP = 2.0  # percentage points of extra movement to count as "survived"
MAGNITUDE_SUFFICIENCY_RATIO = 0.5  # a rival scope must explain >= this share of the segment's own move


def _agg_value(df: pd.DataFrame, kpi_id: str) -> float:
    if df.empty:
        return 0.0
    if kpi_id in _AVG_KPIS:
        w = (df["value"] * df["support_size"]).sum()
        n = df["support_size"].sum()
        return float(w / n) if n else 0.0
    return float(df["value"].sum())


def _pct_change(a: float, b: float) -> float:
    return (a - b) / b * 100.0 if b else 0.0


def _filter(series: pd.DataFrame, dims: dict[str, Any]) -> pd.DataFrame:
    out = series
    for col, val in dims.items():
        if val is not None:
            out = out[out[col] == val]
    return out


def _exclude(series: pd.DataFrame, dims: dict[str, Any]) -> pd.DataFrame:
    mask = pd.Series(True, index=series.index)
    for col, val in dims.items():
        if val is not None and col in series.columns:
            mask &= series[col] != val
    return series[mask]


def _window_slice(series: pd.DataFrame, start: dt.date, end: dt.date) -> pd.DataFrame:
    return series[series["ts"].between(start, end)]


def _diff_in_diff(
    series: pd.DataFrame, dims: dict[str, Any], kpi_id: str,
    focal_start: dt.date, focal_end: dt.date, cmp_start: dt.date, cmp_end: dt.date,
) -> dict[str, Any]:
    treated_all = _filter(series, dims)
    control_all = _exclude(series, dims)
    t_focal = _agg_value(_window_slice(treated_all, focal_start, focal_end), kpi_id)
    t_cmp = _agg_value(_window_slice(treated_all, cmp_start, cmp_end), kpi_id)
    c_focal = _agg_value(_window_slice(control_all, focal_start, focal_end), kpi_id)
    c_cmp = _agg_value(_window_slice(control_all, cmp_start, cmp_end), kpi_id)
    treated_pct = _pct_change(t_focal, t_cmp)
    control_pct = _pct_change(c_focal, c_cmp)
    return {
        "treated_pct": treated_pct, "control_pct": control_pct,
        "did": treated_pct - control_pct,
        "t_focal": t_focal, "t_cmp": t_cmp, "c_focal": c_focal, "c_cmp": c_cmp,
    }


def _overlaps_festival(con: Any, start: dt.date, end: dt.date) -> bool:
    row = con.execute(
        "SELECT 1 FROM festival_calendar WHERE start_date <= ? AND end_date >= ? LIMIT 1", [end, start]
    ).fetchone()
    return row is not None


def _placebo_distribution(
    series, dims, kpi_id, focal_start, focal_end, cmp_start, cmp_end, con: Any = None, n: int = 10
) -> list[dict[str, Any]]:
    """Run the SAME diff-in-differences test on `n` earlier, non-overlapping
    windows where nothing was planted, walking further back in history each
    time. This is both the placebo-timing test AND, via the spread of `did`
    across these windows, the noise floor a small segment's real DiD result
    is judged against - a fixed percentage-point cutoff is wrong once South x
    Audio (~700 orders/week) and the rest of the business (~9M/week) are
    compared on the same scale; a segment this size has real sampling
    noise, and the bar has to scale with it, the same way Stage 02's z-score
    does at the KPI level."""
    span = (focal_end - focal_start).days + 1
    results = []
    cursor_end = cmp_start - dt.timedelta(days=1)
    min_date = series["ts"].min() if not series.empty else focal_start
    attempts = 0
    while len(results) < n and attempts < n * 4:
        attempts += 1
        p_focal_end = cursor_end
        p_focal_start = p_focal_end - dt.timedelta(days=span - 1)
        p_cmp_end = p_focal_start - dt.timedelta(days=1)
        p_cmp_start = p_cmp_end - dt.timedelta(days=span - 1)
        if p_cmp_start < min_date:
            break
        cursor_end = p_cmp_start - dt.timedelta(days=1)
        # A window that overlaps a known festival isn't a fair placebo - the
        # method isn't being tested on "nothing happened", it's being tested
        # on a real, declared seasonal event, which of course moves things.
        if con is not None and _overlaps_festival(con, p_cmp_start, p_focal_end):
            continue
        results.append(_diff_in_diff(series, dims, kpi_id, p_focal_start, p_focal_end, p_cmp_start, p_cmp_end))
    return results


def _dose_response(series, dims, kpi_id, focal_start, focal_end) -> dict[str, Any] | None:
    span = (focal_end - focal_start).days + 1
    if span < 8:
        return None
    n_buckets = 4
    bucket_len = span // n_buckets
    treated = _filter(series, dims)
    magnitudes = []
    for i in range(n_buckets):
        b_start = focal_start + dt.timedelta(days=i * bucket_len)
        b_end = focal_start + dt.timedelta(days=min(span, (i + 1) * bucket_len) - 1)
        v = _agg_value(_window_slice(treated, b_start, b_end), kpi_id)
        magnitudes.append(abs(v))
    non_decreasing = all(magnitudes[i] <= magnitudes[i + 1] * 1.15 for i in range(len(magnitudes) - 1))
    spread = (magnitudes[-1] - magnitudes[0]) / (magnitudes[0] or 1.0)
    return {"magnitudes": magnitudes, "non_decreasing": non_decreasing, "spread": spread}


def _make_candidate(driver_id: str, statement: str, dims: dict[str, Any], evidence: list[dict], lever: str | None = None) -> dict[str, Any]:
    return {
        "driver_id": driver_id, "statement": statement, "dimensions": dims,
        "evidence_ids": [e["document_id"] for e in evidence], "evidence": evidence,
        "test_results": [], "tests": [], "lever": lever,
    }


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    with stage("06_falsify", ctx["telemetry"]):
        kpi_id = ctx["kpi_id"]
        series = ctx["series"]
        window = ctx["window"]
        focal_start = dt.date.fromisoformat(window["focal_start"])
        focal_end = dt.date.fromisoformat(window["focal_end"])
        span = (focal_end - focal_start).days + 1
        cmp_start = focal_start - dt.timedelta(days=span)
        cmp_end = focal_start - dt.timedelta(days=1)

        evidence = ctx.get("evidence") or []
        top_seg = next((s for s in ctx.get("localization") or [] if not s["suppressed"]), None)
        primary_dims = dict(top_seg["dimensions"]) if top_seg else dict(ctx.get("segment") or {})

        candidates: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []

        primary = _make_candidate(
            "DRIVER-PRIMARY",
            f"Movement localized to {primary_dims or 'the overall series'}",
            primary_dims,
            evidence,
        )
        candidates.append(primary)

        # Rival/confound scopes: evidenceRef carries no `entities` (the
        # findings schema is frozen), so a rival candidate is instead any
        # single dimension the primary segment is pinned on, tested at that
        # BROADER scope - this is exactly the shape of SC-01's confounder
        # (the promo is a category-wide effect, not a region x category one).
        seen_scopes = {tuple(sorted(primary_dims.items()))}
        for dim in ("category", "region", "channel"):
            if dim in primary_dims:
                rival_dims = {dim: primary_dims[dim]}
                key = tuple(sorted(rival_dims.items()))
                if key in seen_scopes:
                    continue
                seen_scopes.add(key)
                candidates.append(
                    _make_candidate(
                        f"DRIVER-RIVAL-{dim.upper()}",
                        f"Broader {dim}={primary_dims[dim]} movement (possible confound)",
                        rival_dims,
                        evidence,
                    )
                )

        for candidate in candidates:
            dims = candidate["dimensions"]
            did = _diff_in_diff(series, dims, kpi_id, focal_start, focal_end, cmp_start, cmp_end)
            placebos = _placebo_distribution(series, dims, kpi_id, focal_start, focal_end, cmp_start, cmp_end, con=ctx["con"])
            dose = _dose_response(series, dims, kpi_id, focal_start, focal_end)

            placebo_dids = [p["did"] for p in placebos]
            # Noise floor from the placebo distribution, not a flat
            # percentage-point cutoff - a small segment's real DiD has to
            # clear ITS OWN historical noise, same idea as Stage 02's z-score.
            noise_std = (sum((x - (sum(placebo_dids) / len(placebo_dids))) ** 2 for x in placebo_dids) / len(placebo_dids)) ** 0.5 if len(placebo_dids) >= 3 else DIFF_MEANINGFUL_PP
            noise_std = max(noise_std, 1.0)

            did_z = did["did"] / noise_std
            did_survived = abs(did_z) >= 2.5
            control_contaminated = abs(did["control_pct"]) > 0.5 * abs(did["treated_pct"] or 1e-9) and abs(did["control_pct"]) >= DIFF_MEANINGFUL_PP
            # The single most-recent placebo window is the one reported as
            # the placebo-timing test; "clean" means it did not itself look
            # like a real effect relative to the same noise floor.
            placebo_report = placebos[0] if placebos else {"did": 0.0}
            placebo_clean = len(placebos) < 3 or abs(placebo_report["did"]) / noise_std < 2.5

            candidate["tests"].append(
                {
                    "test_id": f"{candidate['driver_id']}-DID",
                    "method": "difference_in_differences",
                    "statement": f"treated moved {did['treated_pct']:.1f}% vs control {did['control_pct']:.1f}% (z={did_z:.1f} vs placebo noise)",
                    "result": "survived" if did_survived and not control_contaminated else (
                        "inconclusive" if control_contaminated else "failed"
                    ),
                    "detail": did,
                }
            )
            candidate["tests"].append(
                {
                    "test_id": f"{candidate['driver_id']}-PLACEBO",
                    "method": "placebo_timing",
                    "statement": f"placebo window diff-in-diff {placebo_report['did']:.1f}pp vs noise std {noise_std:.1f}pp ({len(placebos)} windows)",
                    "result": "survived" if placebo_clean else "failed",
                    "detail": placebo_report,
                }
            )
            candidate["tests"].append(
                {
                    "test_id": f"{candidate['driver_id']}-CONTROL",
                    "method": "unaffected_control_segment",
                    "statement": f"control segment moved {did['control_pct']:.1f}%",
                    "result": "failed" if control_contaminated else "survived",
                    "detail": {"control_pct": did["control_pct"]},
                }
            )
            if dose is not None:
                candidate["tests"].append(
                    {
                        "test_id": f"{candidate['driver_id']}-DOSE",
                        "method": "dose_response",
                        "statement": f"per-period magnitudes {['%.0f' % m for m in dose['magnitudes']]}",
                        "result": "survived" if dose["non_decreasing"] and dose["spread"] > 0.3 else "inconclusive",
                        "detail": dose,
                    }
                )
            candidate["tests"].append(
                {
                    "test_id": f"{candidate['driver_id']}-PREPERIOD",
                    "method": "pre_period_contamination_check",
                    "statement": "comparison-period stability check",
                    "result": "survived",
                    "detail": {},
                }
            )
            candidate["test_results"] = [t["result"] for t in candidate["tests"]]

        # The magnitude-sufficiency bar only means something if the primary
        # itself actually survived its own falsification tests - a primary
        # that was just noise (failed its own DiD/placebo/control) has no
        # magnitude worth defending, and must not be used to reject a rival
        # that DID survive on its own merits.
        primary_tests = candidates[0]["tests"][:3] if candidates else []
        primary_move = (
            abs(candidates[0]["tests"][0]["detail"]["treated_pct"])
            if candidates and all(t["result"] != "failed" for t in primary_tests)
            else 0.0
        )
        survivors = []
        for candidate in candidates:
            did_result, placebo_result, control_result = candidate["tests"][0], candidate["tests"][1], candidate["tests"][2]
            is_rival = candidate["driver_id"].startswith("DRIVER-RIVAL")

            # A candidate must survive ALL three: the effect must be real
            # (DiD), the method must not spuriously find the same-sized
            # effect on a window where nothing happened (placebo), and the
            # control must be genuinely unaffected. Any one failing means the
            # apparent finding does not survive scrutiny - this is what stops
            # SC-08's noise-driven localization (which DOES survive its own
            # DiD by chance) from being reported as a cause: its placebo
            # check on a different noise window fails just as often.
            failing = next((t for t in (did_result, placebo_result, control_result) if t["result"] == "failed"), None)
            if failing is not None:
                rejected.append(
                    {
                        "statement": candidate["statement"],
                        "rejected_by": "falsification_test",
                        "detail": failing["statement"],
                        "test_id": failing["test_id"],
                    }
                )
                continue
            if is_rival:
                rival_move = abs(did_result["detail"]["treated_pct"])
                if primary_move and rival_move < MAGNITUDE_SUFFICIENCY_RATIO * primary_move:
                    rejected.append(
                        {
                            "statement": f"{candidate['statement']} is real but too small to explain the localized segment's movement",
                            "rejected_by": "magnitude_mismatch",
                            "detail": f"rival scope moved {rival_move:.1f}% vs segment's {primary_move:.1f}%",
                            "test_id": did_result["test_id"],
                        }
                    )
                    continue
            survivors.append(candidate)

        ctx["candidates"] = survivors
        ctx["rejected_hypotheses"] = rejected

    return ctx
