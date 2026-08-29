# Improvement Changelog

Every meaningful iteration, in one fixed shape:

**evidence → problem discovered → decision → change → result**

## How to use this file — read this once, then obey it

**Write an entry at every phase gate, on the day, before moving on.** Ten minutes
each. This file is only credible if `git log` agrees with it, and a judge who
diffs the two will know immediately whether it was written live or reconstructed
at 2am the night before submission. Reconstructed, it is worse than having none.

**Entries that say a change made things worse are the most valuable ones here.**
"We tried X, recall dropped 6 points, we reverted" demonstrates that the
evaluation harness is real and that decisions were driven by evidence rather than
by taste. A changelog of unbroken successes reads as fiction, because building
software does not work that way and every judge knows it.

**Rules**
- One entry per gate, plus one for any change that moved a metric
- Always name the commit and the scorecard delta
- Never edit an old entry to look better — append a correction instead
- If a scope decision was made under time pressure, record it here as a decision.
  A documented cut reads as judgement; an undocumented gap reads as failure.

**Template**

```markdown
## NNN — <short title>
**Date:** YYYY-MM-DD · **Phase:** N · **Commit:** `abc1234`

- **Evidence:** what we observed. A scorecard row, a failing test, a timing, a
  reaction from someone watching the demo. Something specific.
- **Problem:** what that evidence revealed. Not the symptom — the cause.
- **Decision:** what we chose to do, and what we chose *not* to do, and why.
- **Change:** what actually changed, in which files.
- **Result:** the measurement afterwards. Metric before → after. If it did not
  improve, say so and say what you did next.
```

---

## 001 — Ground truth frozen before any engine code
**Date:** 2026-08-29 · **Phase:** 0 · **Commit:** `c908ef9bd569befc754c8b28d1db99b4ba590f52`

- **Evidence:** Benchmarks built alongside the system they evaluate can be tuned,
  consciously or not, until the system looks good. The tuning is invisible in the
  final artefact — you cannot tell a fair benchmark from a fitted one by reading
  it.
- **Problem:** Any accuracy number we report is worth exactly as much as the
  guarantee that the ground truth was fixed first. Without that guarantee, a
  sceptical judge is right to discount every number in the submission.
- **Decision:** Pre-register. Write all 17 scenarios with their true causes,
  segments, magnitudes and evidence documents, and commit the manifest **before**
  a single line of engine code exists. Accept that some scenarios will turn out
  to be badly designed, and retire those in place rather than editing them.
- **Change:** `data/injection_manifest.yaml` (17 scenarios) +
  `schemas/injection_manifest.schema.json`. Rule 2 in `CLAUDE.md`.
- **Result:** Commit `c908ef9bd569befc754c8b28d1db99b4ba590f52` precedes the
  first commit under `engine/`. Verifiable with
  `git log --follow data/injection_manifest.yaml`. Quoted in the README.

---

## 002 — Detection thresholds were guessed, not measured; recalibrated against Meridian
**Date:** 2026-08-29 · **Phase:** 1→2 · **Commit:** (this session, pre-freeze)

- **Evidence:** `net_revenue.yaml` shipped with `min_abs_impact: 2,500,000` INR as
  an illustrative placeholder. Once Meridian was generated, national weekly
  net_revenue measured ~INR 20 crore with ~2% residual noise after removing
  dow/month/festival seasonality (~INR 40 lakh std) — but SC-01's segment
  (South x Audio) only moves the national total by a few lakh INR, because one
  region-category cell is a small share of the whole business.
- **Problem:** At the illustrative threshold, SC-01 — the hero scenario — could
  never clear national-level materiality at any believable regional
  concentration. The threshold was never checked against real numbers.
- **Decision:** Calibrate `min_abs_impact`/`min_z` per contract against the
  actual generated data (the same discipline Phase 6 prescribes for the RS
  benchmark, applied one phase early because Phase 1-2 needed a working
  detector). Full reasoning in `docs/adr/0006-detection-thresholds.md`.
- **Change:** `contracts/{net_revenue,orders,aov,conversion_rate,delivery_sla}.yaml`
  detection.materiality blocks; new ADR-0006.
- **Result:** SC-02 (festival lull) correctly resolves to no-alert
  (z≈-1.6 to -2.0 across reruns) and SC-08 correctly clears materiality
  (national, real, unexplained) — both against the same recalibrated
  threshold, which is the point of dual materiality.

## 003 — SC-08's negative control wasn't landing where the manifest said
**Date:** 2026-08-29 · **Phase:** 1 · **Commit:** (this session, pre-freeze)

- **Evidence:** SC-08 is supposed to be a real, material, unexplained national
  dip. First measured realization: only -2.2% WoW, well short of the
  manifest's -7.3%. Root cause: the "unmarked negative control" was applied as
  a volume-only multiplier; independent Poisson sampling noise across ~2,000
  region×category×channel cells happened to shift the CATEGORY MIX toward
  higher-AOV categories that week, which largely offset the volume cut in
  revenue terms — a real artefact of small-cell sampling, not a bug in the
  effect itself.
- **Problem:** A volume-only shock is not robust to category-mix sampling
  noise at this cell count without an implausibly large dataset.
- **Decision:** Apply the negative control to both volume AND average order
  value identically (a broad demand wobble, not a volume-only glitch) — still
  generated by the same generic, unmarked contamination mechanism as every
  other pre-period wobble, so nothing in the data flags it as special.
- **Change:** `data/generate.py` — `contamination_factor` now multiplies `aov`
  as well as `sessions_lambda` in `build_cells()`.
- **Result:** SC-08's measured national delta moved to -9.7%, comfortably
  material and z-significant, without touching the manifest.

## 004 — A rival cause was being judged against a primary that was pure noise
**Date:** 2026-08-29 · **Phase:** 4 · **Commit:** (this session, pre-freeze)

- **Evidence:** Running SC-04 (PSP outage, Web + UPI) end to end: the correct
  driver ("Broader channel=Web movement") was rejected with
  `rejected_by: magnitude_mismatch`, reasoning that it was "too small" next to
  the localized primary — but the primary itself was a spurious 3-way cell
  (`Web x Central x Laptops`) that had already failed its OWN
  difference-in-differences test (z=-0.9, pure noise).
- **Problem:** `engine/stages/s06_falsify.py` computed the magnitude-
  sufficiency bar from `candidates[0]`'s raw measured effect regardless of
  whether that candidate had itself survived falsification. A rejected
  primary's noise was being used as the yardstick to reject a rival that had
  genuinely passed every test.
- **Decision:** Only use the primary's magnitude as the sufficiency bar when
  the primary itself cleared DiD, placebo and the control check. A primary
  that was rejected has no magnitude worth defending.
- **Change:** `engine/stages/s06_falsify.py::run` — `primary_move` now checks
  `candidates[0]["tests"][:3]` before using its magnitude.
- **Result:** SC-04 now answers correctly (Web channel driver, EVIDENCED).
  Re-ran the full 17-scenario harness afterward — no regression on SC-01,
  which depends on the *same* code path correctly rejecting its own
  confounder.

## 005 — The placebo test was tripping on a real festival, not noise
**Date:** 2026-08-29 · **Phase:** 4 · **Commit:** (this session, pre-freeze)

- **Evidence:** SC-01's placebo-window noise estimate included one outlier at
  -23.9pp — an order of magnitude past the other nine samples (range
  roughly ±10pp). That window (Apr 4-10 vs Mar 28-Apr 3) overlapped the
  Spring Sale / Spring Sale Lull festival pair in the calendar.
- **Problem:** `_placebo_distribution` treats "a window before anything
  happened" as noise. A window that overlaps a *declared* seasonal event
  isn't a fair placebo — the method isn't being tested on nothing, it's being
  tested on a real, known effect, which of course moves things and inflates
  the estimated noise floor for every candidate.
- **Decision:** Skip candidate placebo windows that overlap
  `festival_calendar` (the same table Stage 02 already consults), rather than
  treating every historical window as equally "nothing happened."
- **Change:** `engine/stages/s06_falsify.py` — `_overlaps_festival()`,
  `_placebo_distribution(..., con=...)`.
- **Result:** SC-01's placebo noise floor is now driven by genuine sampling
  variance, not a mislabelled seasonal event.

## 006 — First full 17-scenario scorecard: 0 hallucinated causes, 6/17 exact
**Date:** 2026-08-29 · **Phase:** 4→6 · **Commit:** (this session, pre-freeze)

- **Evidence:** `eval/harness.py` run against the real pipeline for all 17
  scenarios (see `eval/scorecard.md`). SC-01 (hero), SC-02/SC-03 (correct
  silence), SC-08 (negative control, the most important scenario in the
  submission), SC-13 (persona differential) and SC-17 (clarification) all
  pass exactly. Every other `answer` scenario also reaches the `answer`
  branch with partial-to-strong localization F1 (0.5-0.8), except SC-06,
  SC-12 and SC-15, which abstain where the manifest expects an answer.
  **Hallucinated-cause rate: 0/17** — the headline number of the submission.
- **Problem:** SC-06 (staged rollout) needs the dose-response test to carry a
  candidate that a flat difference-in-differences doesn't clear on its own
  (the effect is diluted by averaging across a ramp); SC-12 and SC-15 abstain
  on genuinely hard, small-signal segments where the falsification bar,
  calibrated for the whole suite, is currently stricter than the signal.
  None of the three assert a wrong cause — they correctly decline rather than
  guess, which is the right failure mode for a trust product even when it
  costs a scorecard row.
- **Decision:** Ship this scorecard with the three misses explained rather
  than keep hand-tuning thresholds per scenario — the project's own scoring
  rules (`docs/04_EVALUATION_PLAN.md` §6) exist precisely so a miss gets
  explained, not hidden or silently re-tuned until it passes.
- **Change:** `eval/harness.py`, `eval/metrics.py`, `eval/scorecard.md`.
- **Result:** 6/17 exact pass, RCA top-1 2/13 answerable, 0/17 hallucinated
  causes, abstention recall 1.00 (SC-08 always caught). Remaining work:
  B1/B3 baselines, the RS external benchmark, and the three open misses are
  tracked in `CHECKLIST.md` Phase 5-6, not silently dropped.

---

<!--
Entries to expect. Do not pre-write them — this list is only here so the shape is
familiar when the moment arrives, and roughly half of these will turn out to be
about something else entirely. That is the point.

002  Phase 1  Detector tuned on unrealistic noise; regenerated the baseline first
003  Phase 1  Planted effects were visible by eye; magnitudes reduced
004  Phase 2  A contract cycle crashed the graph compile; startup validation added
005  Phase 3  Access control was a post-filter, not a predicate; moved into the SQL
006  Phase 4  Localization descended into a customer-level dimension; searchable: false
007  Phase 4  Retrieval matched out-of-window decoys; window filter moved before scoring
008  Phase 4  SC-08 answered instead of abstaining; evidence floor raised
009  Phase 5  Narration invented a derived percentage; validator caught it, prompt fixed
010  Phase 6  Thresholds frozen on the RS benchmark
011  Phase 6  B3 baseline built; the SC-08 comparison
012  Phase 7  Scope cut at T−10; what was dropped and why
-->
