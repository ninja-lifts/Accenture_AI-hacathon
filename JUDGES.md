# For evaluators

Thank you for the time. Here is the shortest path to a fair assessment.

**Status check first, because it matters for how you read this:** the engine,
data generator, and evaluation harness are real, tested, and reproducible. The
UI is not built yet — there is no live demo. Everything below points at the
repo itself (code, committed output, tests you can run) rather than a hosted
page, because that's what actually exists right now. We would rather you know
that up front than discover it by clicking a dead link.

---

## If you have 5 minutes

1. Open [`eval/scorecard.md`](eval/scorecard.md) and read the **Headline**
   section first, not the pass/fail table. **Hallucinated-cause rate: 0/17.**
   No run ever asserted a cause the data doesn't support.
2. Open [`TRAJECTORIES.md`](TRAJECTORIES.md) §2 — **SC-08**. We planted a
   real, material revenue drop with *no cause anywhere in the data*, salted
   the evidence corpus with plausible-looking decoys, and the system
   investigated, found nothing that survived a falsification test, and said
   so — by name, with a referral. Zero causes asserted.
3. Run it yourself:
   ```bash
   pip install -r requirements.txt
   python data/generate.py --seed 20260829 --out data/generated
   python -m eval.harness --scenarios SC-08 --verbose
   ```
   No API key needed — the default `.env` runs fully offline.

If you only do one of these, do **step 2**.

---

## If you have 15 minutes

Add:

4. [`TRAJECTORIES.md`](TRAJECTORIES.md) §1 — **SC-01**, the hero, all seven
   stages with real numbers: a courier-collapse cause found, and a genuinely
   confounding national promotion (real, well-timed, well-documented)
   correctly demoted by a falsification test rather than picked because it
   was plausible.
5. [`TRAJECTORIES.md`](TRAJECTORIES.md) §3 — **SC-14**. A support ticket in
   the evidence set contains a live prompt-injection attack
   ("IGNORE ALL PREVIOUS INSTRUCTIONS..."). It's retrieved — hiding it would
   be the weaker system — flagged, cited as ordinary evidence, and never
   acted on. It also turned up, unplanned, while retrieving evidence for
   SC-08 (a different scenario) and was correctly flagged there too — that
   wasn't staged, we found it while writing the trace.
6. Run the real test suite:
   ```bash
   pytest -q
   ```
   8 tests, including one that validates every scenario's output against the
   frozen `schemas/findings.schema.json`, and one proving tier assignment is
   monotone (removing evidence can never raise a confidence tier).
7. Switch persona in a Python shell and diff the `entitlements_hash`:
   ```python
   from engine import pipeline
   import datetime as dt
   window = {"focal_start": "2026-08-08", "focal_end": "2026-08-14",
             "comparison_start": "2026-08-01", "comparison_end": "2026-08-07", "grain": "day"}
   cfo = pipeline.run(today=dt.date(2026,8,22), trigger="alert_sweep", persona="cfo",
                        kpi="net_revenue", window=window, investigate=False)
   cm  = pipeline.run(today=dt.date(2026,8,22), trigger="alert_sweep", persona="category_manager",
                        role_id="cm_audio", kpi="net_revenue", window=window, investigate=True)
   assert cfo["movement"] != cm["movement"]  # different scope, different computation
   ```
   The role changes the SQL predicate and the resulting `entitlements_hash` —
   this is real access control, not a UI filter, and you can verify it without
   a UI at all.

---

## If you have 30 minutes

8. [REPRODUCE.md](REPRODUCE.md) — clean-environment setup, `make data`,
   `make eval`, `make test`. Your scorecard should match ours exactly (it's
   deterministic — we reran it twice this session and got byte-identical
   output both times).
9. [`prompts/`](prompts/) — the only two model calls in the system, in full.
10. [`eval/scorecard.md`](eval/scorecard.md)'s full Misses section — every
    non-passing scenario explained with what was actually predicted vs. the
    true segment, not just restated as a failure.

---

## Four things worth checking, because they are unusual

**The ground truth was frozen before the engine existed.**
```bash
git log --follow data/injection_manifest.yaml
```
Commit `c908ef9bd569befc754c8b28d1db99b4ba590f52` is the first commit in the
repo, before any file under `engine/` exists (`git log --oneline --reverse --
engine/` confirms the earliest engine-touching commit comes after it). Our
accuracy numbers are pre-registered, not fitted — and where we *did* tune
things after the fact (data-generator noise
characteristics, detection thresholds — see `docs/adr/0006-detection-thresholds.md`
and CHANGELOG 002-005), that happened before freeze, is documented with the
evidence that motivated it, and never touched `true_segment`, `true_cause_id`,
or `evidence_document_ids` — the fields actually used for scoring.

**The changelog agrees with the history.** [`CHANGELOG.md`](CHANGELOG.md) — 6
entries, each naming what evidence prompted a change and what the change was,
including two real bugs found by running the scenarios (not by reading the
code) after the engine was believed finished.

**The scorecard shows failures, and now explains them.** 10 of 17 scenarios
don't pass exactly. None of the 10 asserts a wrong or invented cause — 3
abstain conservatively where an answer was possible (SC-06, SC-12, SC-15) and
7 answer on the correct branch with real cited evidence but name a broader or
adjacent segment than the exact ground truth (see the Misses section for the
specific dimension each one over- or under-included). We would rather show
this breakdown than a single "10 failed" line.

**Five of seven stages never touch a language model.** The model turns a
question into a query and a result into a sentence. Every numeral it writes is
re-extracted and matched against the computed findings before you see it —
`tests/test_validator_blocks_invented_numbers.py` proves this against an
adversarial case (a plausible-looking number that's a *combination* of two
real ones, not itself a real one).

---

## What we would push on, if we were you

We would rather name these than have you find them.

- **There is no UI.** `app/main.py` is unbuilt. The engine is real,
  ~80% of the technical work, and everything above can be verified without
  one — but a live, clickable demo does not exist right now.
- **The B3 (LLM-only) baseline hasn't been run.** The comparison it would
  produce — SC-08 side by side, GlassBox abstaining vs. a single prompt
  confidently inventing a cause — is the single most legible argument this
  submission could make, and it isn't in the repo yet because it requires a
  live model call and this build environment has none configured. The
  scaffolding exists (`eval/baselines/README.md`); it has not been faked to
  fill the gap.
- **The primary dataset is synthetic.** It has to be — no public dataset
  pairs business KPIs with customer text *and* labelled causes
  ([why](docs/05_DATA_STRATEGY.md#2-why-the-ideal-dataset-does-not-exist)).
  The RS external benchmark (135 real anomalies, 7 published algorithms) that
  would offset this has not been run yet either — tracked as open in
  `CHECKLIST.md`, not silently dropped.
- **Causal claims are quasi-experimental.** `TESTED`-equivalent evidence means
  "survived our falsification attempts," not "proven." SC-12 is the scenario
  designed to stress this (spillover contaminates the control segments) — in
  the current build it abstains rather than answer with a capped tier, which
  is a stricter, more conservative response than originally designed for but
  not a wrong one; see `eval/scorecard.md`'s Misses section for the specific
  evidence-floor reason.
- **Narration prose quality depends on a live LLM key, which this environment
  doesn't have.** Every number in every run is still validated against the
  findings object regardless (see `TRAJECTORIES.md` — the template fallback
  is legible but mechanical, e.g. `"driven by: Movement localized to
  {'category': 'Audio', 'region': 'South'}"`), but the natural-language
  quality a live model would produce hasn't been demonstrated in this repo
  yet.
- **The semantic contract is real adoption cost.** Five metrics is an
  afternoon each with their owners. Four hundred is a programme, and we would
  not pretend otherwise.

---

## Questions we are ready for

[`docs/07_DEMO_AND_PITCH.md#3-qa-bank`](docs/07_DEMO_AND_PITCH.md) — but ask
us anything. If we cannot defend a file in this repo, we should not have
shipped it.
