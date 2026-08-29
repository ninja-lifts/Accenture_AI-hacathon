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
