# ADR-0006 — Detection materiality thresholds calibrated against Meridian, not guessed

**Status:** accepted (pre-freeze; re-confirmed at Phase 6 per `docs/01_MASTER_BUILD_FLOW.md`)

## Context
`detection.materiality.{min_abs_impact,min_z}` in each contract is the dual
threshold that keeps the alert feed at single digits instead of 200 rows
nobody reads. The starter kit shipped `net_revenue`'s as an illustrative
`min_abs_impact: 2,500,000` INR; the other four contracts shipped `0`
(unset). Neither was measured against real data, because at Phase 0 no data
existed yet.

Once Meridian was generated (`data/generate.py`, seed `20260829`), the actual
numbers didn't support the illustrative value: national weekly `net_revenue`
is ~INR 20 crore with ~2% residual noise (~INR 40 lakh std) once dow/month/
festival_calendar seasonality is removed - so `min_z=2.5` alone already
requires an ~INR 1 crore national swing. A single-segment scenario like
SC-01 (South x Audio) moves the national total by only ~INR 3-5 lakh, because
one region-category cell is a small share of the whole business - exactly as
it should be. `min_abs_impact: 2,500,000` would have made SC-01 nationally
undetectable at any believable segment concentration, and the only way to
"fix" that honestly would have been to distort the region/category revenue
mix into something implausible, not to leave the threshold alone.

## Decision
Threshold values are calibrated against the committed dataset, then frozen
(rule 3, `CLAUDE.md`):
- `min_z` stays the primary, scale-independent "is this surprising" gate.
- `min_abs_impact` becomes a much smaller, scale-independent floor - "not
  worth an analyst's time below this regardless of statistical surprise" -
  rather than a national-only bar. It is set once the actual segment-scale
  and national-scale movements in Meridian are known (see the calibration
  queries this ADR's commit is paired with), comfortably below every
  `expected_branch: answer` scenario's real measured impact and comfortably
  above ordinary week-to-week noise at that same scope.

Final values: `net_revenue` 250,000 INR / z 2.5 · `aov` 100 INR / z 2.5 ·
`conversion_rate` 0.003 / z 2.0 · `delivery_sla` 0.03 / z 2.5 ·
`orders` 50 orders / z 2.5.

## Consequences
**Good.** Thresholds are evidence-based rather than aesthetic, and the
calibration method (measure the noise floor, measure each scenario's real
effect, set floors between them) is exactly what Phase 6 asks the team to do
anyway with the RS benchmark - this ADR is that same discipline applied one
phase early, because Phase 1-2 needed a working detector before Phase 6.

**Bad.** `min_abs_impact` no longer maps to "material at national scale" the
way the illustrative starter value implied. That is a feature, not a
regression: Stage 02 Detect runs on whatever series Stage 01 Define scoped
(national for an alert sweep, segment-scoped for a category manager or a
direct question), and one flat national-only floor would have made every
non-national investigation in the product unreachable by construction.

**Note for Q&A.** If asked "why isn't the threshold a round number like
Rs 25 lakh" - because a round number chosen before the data existed is a
guess, and a guess that happens to break the hero scenario is worse than an
odd number that was actually measured.
