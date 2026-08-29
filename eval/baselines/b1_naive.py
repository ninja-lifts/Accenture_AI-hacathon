"""B1 - naive drill-down. "What a dashboard does today."

Rank single-dimension segments by absolute contribution to the movement
(comparison-window actual vs focal-window actual, no seasonal adjustment, no
growth-factor correction, no 2-way search, no falsification), take the
largest, and report the most recent document mentioning that segment's value
as the cause - no relevance ranking, no entitlement filter, no window filter
before scoring.

This is deliberately weaker than engine/stages/s03_localize.py. That's the
point: beating this baseline is the actual product claim, not a formality -
it's what a category manager does by hand in a spreadsheet today.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from engine import config, contracts as contracts_mod

DIMENSIONS = ["region", "category", "channel"]


def _load_documents(settings) -> list[dict[str, Any]]:
    path = Path(settings.data_dir) / "documents.jsonl"
    docs = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            docs.append(json.loads(line))
    return docs


def _window_for(scenario: dict[str, Any]) -> tuple[dt.date, dt.date, dt.date, dt.date]:
    fw = scenario["focal_window"]
    start = dt.date.fromisoformat(fw["start"])
    end = dt.date.fromisoformat(fw["end"])
    span = (end - start).days + 1
    cmp_end = start - dt.timedelta(days=1)
    cmp_start = cmp_end - dt.timedelta(days=span - 1)
    return start, end, cmp_start, cmp_end


def run_b1(scenario: dict[str, Any], con, all_contracts: dict[str, Any], settings) -> dict[str, Any]:
    """Returns a small, GlassBox-shaped-enough result: {segment, cause_statement,
    cited_document_id, delta_abs}. Not a findings object - B1 makes no tiered
    claims, has no gate, and cannot abstain, which is itself the point: a
    naive drill-down always produces *an* answer."""
    kpi_id = scenario["kpi"]
    contract = all_contracts[kpi_id]
    focal_start, focal_end, cmp_start, cmp_end = _window_for(scenario)

    sql = f"SELECT * FROM ({contract['definition']['sql']}) t"
    series = con.execute(sql).df()
    if "ts" in series.columns:
        import pandas as pd

        series["ts"] = pd.to_datetime(series["ts"]).dt.date

    focal = series[series["ts"].between(focal_start, focal_end)]
    cmp = series[series["ts"].between(cmp_start, cmp_end)]

    best = None
    for dim in DIMENSIONS:
        if dim not in series.columns:
            continue
        for val in series[dim].dropna().unique():
            f = focal[focal[dim] == val]["value"].sum()
            c = cmp[cmp[dim] == val]["value"].sum()
            delta = float(f - c)
            if best is None or abs(delta) > abs(best["delta_abs"]):
                best = {"dimensions": {dim: val}, "delta_abs": delta}

    if best is None:
        return {"segment": {}, "cause_statement": None, "cited_document_id": None, "delta_abs": 0.0}

    seg_value = next(iter(best["dimensions"].values()))
    docs = _load_documents(settings)
    matches = [
        d for d in docs
        if str(seg_value).lower() in (d["title"] + " " + d["body"]).lower()
        and dt.datetime.fromisoformat(d["published_at"].replace("Z", "+00:00")).date() <= focal_end
    ]
    matches.sort(key=lambda d: d["published_at"], reverse=True)
    most_recent = matches[0] if matches else None

    return {
        "segment": best["dimensions"],
        "cause_statement": most_recent["title"] if most_recent else None,
        "cited_document_id": most_recent["document_id"] if most_recent else None,
        "delta_abs": best["delta_abs"],
    }
