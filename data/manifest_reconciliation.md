# Manifest reconciliation — declared vs. actually planted magnitude

**Date:** 2026-08-30 · **Status:** disclosure, not a repair. `data/generate.py`
is unchanged. No `magnitude_pct` value in `data/injection_manifest.yaml` is
changed. See "Why this is not a pre-registration violation" below.

## What this is

`data/injection_manifest.yaml` is frozen ground truth, committed before any
engine code existed (Rule 2, `CLAUDE.md`). Each scenario declares a
`ground_truth.magnitude_pct` alongside `true_segment`, `true_cause_id`, etc.
While investigating an internal contradiction in a live SC-01 narration
(2026-08-30 session), the movement the engine actually measured for SC-01
(-18% to -23.5%, depending on scope) turned out not to be close to the
manifest's declared `-8.2%`. That prompted checking all 17.

## Methodology

Independent of the engine: raw DuckDB queries against
`data/generated/meridian.duckdb` (seed `20260829`, matching
`data/generated/DATA_HASHES.json`), mirroring each `contracts/*.yaml`
`definition.sql` by hand, aggregated over the scenario's declared
`focal_window` vs. an equal-length comparison window immediately before it
(the same convention `eval/harness.py::_window_for` uses). This does **not**
call `engine/pipeline.py` or any engine stage - it is a second, independent
measurement, not a re-run of the code path that produced the scorecard.

Sanity check: SC-01's raw focal/comparison values from this method
(₹60,92,237.07 / ₹74,27,372.38) matched `DRIVER-PRIMARY`'s own DiD test
values in the engine's real findings object to the cent. The methodology is
sound and directly comparable to what the engine itself measures.

## Full table

| id | kpi | declared% | measured% | diff(pp) | note |
|---|---|---:|---:|---:|---|
| SC-01 | net_revenue | -8.2 | -18.0 | -9.8 | matches engine's own DiD exactly |
| SC-02 | net_revenue | -14.0 | -30.6 | -16.6 | not planted (`ground_truth.planted: false`) - manifest note describes this as a *year-on-year* figure; this WoW measurement is not the same yardstick, not treated as a clean mismatch |
| SC-03 | aov | -9.5 | -11.0 | -1.5 | close |
| SC-04 | conversion_rate | -22.0 | -18.5 | +3.5 | `fact_sessions` has no `payment_method` column; measured `channel=Web` only (diluted by non-UPI Web traffic). Sanity-checked via raw order counts: UPI orders on Web fell 587→152 (-74%) over the same two windows while every other payment method stayed flat - the plant is real and correctly targeted; -18.5% is a reasonable diluted proxy for a segment this schema can't isolate directly |
| SC-05 | net_revenue | -5.1 | -4.9 | +0.2 | well calibrated |
| SC-06 | conversion_rate | -6.4 | -2.7 | +3.7 | measured ~42% of declared |
| SC-07 | net_revenue | -6.8 | -0.1 | +6.7 | measured is essentially zero - **RETIRED, see below** |
| SC-08 | net_revenue | -7.3 | -11.8 | -4.5 | not planted (negative control / pure aggregate noise by design). Also disagrees with `CHANGELOG.md` entry 003's own "-9.7%" claim for the same scenario - three different numbers now on record for one deliberately-unexplained dip. Not scored on magnitude either way |
| SC-09 | net_revenue | +4.9 | +1.2 | -3.7 | right direction, ~25% of declared |
| SC-10 | net_revenue | -18.0 | -7.0 | +11.0 | measured ~39% of declared |
| SC-11 | conversion_rate | -4.2 | -2.6 | +1.6 | scenario is explicitly about *gradual six-week decay*, scored via cumulative residual, not a point-in-time comparison; a WoW-style measurement isn't the right yardstick for this one by the scenario's own design - flagged, not claimed as a clean mismatch |
| SC-12 | net_revenue | -11.0 | -5.5 | +5.5 | measured ~50% of declared |
| SC-13 | net_revenue | -8.2 | -18.0 | -9.8 | same cause/segment/window as SC-01 (run under a different persona), same result |
| SC-14 | net_revenue | -3.9 | -12.7 | -8.8 | measured **3.3x** the declared magnitude - over-planted, not under |
| SC-15 | net_revenue | -2.1 | +12.0 | +14.1 | **wrong sign** at the declared (2-dimension) segment - **RETIRED, see below** |
| SC-16 | net_revenue | -12.0 | -41.4 | -29.4 | measured **3.5x** the declared magnitude |
| SC-17 | — | n/a | n/a | n/a | clarification scenario, no magnitude claimed |

Of the 14 `planted: true` scenarios, only SC-03 and SC-05 land close to their
declared magnitude. The rest diverge by 1.6x-3.5x, in both directions, and
one (SC-15) flips sign entirely.

## SC-15 — three-way analysis

`true_segment: { region: "North-East", category: "Large Appliances" }` in the
manifest declares **two** dimensions. `data/generate.py::plant_scenarios`
actually injects at **three**:
```python
tiny_cell = (region == "North-East") & (category == "Large Appliances") & (channel == "Retail")
apply_effect(cells, tiny_cell, w0, w1, "step", -0.88, "sessions_lambda")
```
Three independent measurements:

| Scope | Measured % | Orders (cmp → focal) |
|---|---:|---|
| Manifest's declared 2-dim segment (region×category, all channels) | **+12.0%** (wrong sign) | swamped by unrelated Web/App/Partner volume in the same region×category |
| True 3-dim injected cell (region×category×channel=Retail) | **-84.4%** | 21 → 3 |
| Manifest's declared `magnitude_pct` | -2.1% | — |

The plant is real and large (-84.4% at the cell it actually targets - the
-0.88 `sessions_lambda` multiplier applied almost exactly: 21 × 0.12 ≈ 2.5,
observed 3). But the manifest's own `true_segment` is under-specified
relative to what was planted, and neither reading of the data (the declared
2-dim rollup, or the true 3-dim cell) is close to the declared `-2.1%`. The
scenario's own notes correctly anticipate scoring at the disclosed (rolled-up,
suppressed) granularity - but that rolled-up view is dominated by noise from
three other channels that were never touched, which is a property of the
scenario design, not something a smarter engine could localize its way out of.

## Root cause

`magnitude_pct` was a design target, chosen when each scenario was written,
and never verified against the generator's actual output once
`data/generate.py` existed - the same pattern `docs/adr/0006-detection-thresholds.md`
already documents for detection thresholds ("An illustrative placeholder...
never checked against real numbers"). Every scenario's plant is coded as a
raw multiplicative shock to an upstream rate (`conversion_rate`,
`sessions_lambda`, `on_time_rate`, `return_rate`, `aov`), and nothing checks
that the chosen multiplier reproduces the declared `magnitude_pct` once it
runs through Poisson sampling and aggregation into a KPI.

## What is actually a scoring key (verified against the code, not asserted)

Grepping `eval/metrics.py` and `eval/harness.py`:

- **`true_segment`** - read directly (`f1_localization`, `exact_match`,
  `rca_hit_at_2`, and the inline `top1` check in
  `eval/harness.py::score_scenario`). Genuinely scored.
- **`expected_branch`** - read directly (`branch_pass`). Genuinely scored.
- **`evidence_document_ids`** - read directly
  (`metrics.evidence_recall_at_5`). Genuinely scored.
- **`true_cause_id`** - a correction to make here, not just a confirmation:
  `eval/metrics.py::rca_top1(findings, true_cause_id)` exists and is
  documented ("true cause is the highest-ranked driver") but **is never
  called anywhere in `eval/harness.py`**. The `"rca_top1"` column actually
  reported in the scorecard is a differently-named inline check
  (`bool(true_segment) and exact_match and branch == "answer"`) that never
  reads `true_cause_id` at all. `rca_top1()` itself, if it were called,
  would contribute nothing beyond a not-applicable/applicable gate - its own
  docstring says top-1 is judged by segment match "since we don't have the
  generator's internal cause ids inside the findings object." This is dead
  code, not a hidden scoring dependency - worth fixing at some point, but not
  something this magnitude discrepancy touches, and out of scope for this
  disclosure.
- **`magnitude_pct`** - grepped `eval/`, `engine/`, `app/`, `tests/`: zero
  matches outside the manifest itself. It is not read by any scoring code,
  anywhere.

## Why this is not a pre-registration violation

Rule 2 (`CLAUDE.md`) exists to prevent tuning ground truth after seeing what
the engine says about it. Nothing here does that: `data/generate.py` is
unchanged, every `magnitude_pct` value is unchanged, and the two fields nobody
disputes are actually scored - `true_segment` and `expected_branch` - are
untouched for every scenario, including the two retired below (a `RETIRED`
note does not remove a scenario or alter its `ground_truth` block; both stay
in the file, in place, per Rule 2's own instruction for an ill-posed scenario).
The pre-registration of what this benchmark actually measures is intact. What
this document discloses is narrower and less convenient: a field that was
never a scoring key turns out to have also never been verified against the
data it was meant to describe.

## Disposition

- **SC-07** and **SC-15** marked `RETIRED` in `data/injection_manifest.yaml`
  (notes field only - see that file for the exact reasons). Both scenarios,
  and their full `ground_truth` blocks, remain in the file unedited.
- The other 12 `planted: true` mismatches (SC-01/13, SC-04, SC-06, SC-09,
  SC-10, SC-12, SC-14, SC-16) are disclosed above but not retired -
  `true_segment` and `expected_branch`, the fields actually scored, are not
  in question for any of them, and the magnitude gap alone does not make a
  scenario unpassable or ill-posed the way SC-07's near-zero effect or
  SC-15's wrong scoring key do.
- SC-02 and SC-08 (`planted: false`) are noted for completeness; their
  `magnitude_pct` describes an observed, not injected, movement and was
  never claimed to be a precision target the way a planted scenario's is.
