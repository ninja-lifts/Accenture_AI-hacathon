# For evaluators

Thank you for the time. Here is the shortest path to a fair assessment.

**Status check first, because it matters for how you read this:** the engine,
data generator, and evaluation harness are real, tested, and reproducible. A
minimal UI exists (`app/main.py` — `make app`) and is verified to run every
scenario without error, but no one has clicked through it in a browser yet,
so we can't vouch for the visual polish, only the logic. There is no hosted
page — everything below points at the repo itself (code, committed output,
tests you can run) rather than a link, because that's what actually exists
right now. We would rather you know that up front than discover it by
clicking a dead link.

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

4. [`eval/baseline_scorecard.md`](eval/baseline_scorecard.md) — two real,
   run-not-invented baselines. B1 (naive drill-down) asserts a confident
   cause on **all 3** of the scenarios where none was planted. B3
   (single-LLM-prompt, live via Groq's `openai/gpt-oss-120b`) does the same
   on the 2 of those 3 it was actually sent a prompt for, fluently, at
   "70-80% confidence," citing a real ticket number that is a planted decoy.
   GlassBox's rate on the same three: zero.
5. [`TRAJECTORIES.md`](TRAJECTORIES.md) §1 — **SC-01**, the hero, all seven
   stages with real numbers: a courier-collapse cause found, and a genuinely
   confounding national promotion (real, well-timed, well-documented)
   correctly demoted by a falsification test rather than picked because it
   was plausible.
6. [`TRAJECTORIES.md`](TRAJECTORIES.md) §3 — **SC-14**. A support ticket in
   the evidence set contains a live prompt-injection attack
   ("IGNORE ALL PREVIOUS INSTRUCTIONS..."). It's retrieved — hiding it would
   be the weaker system — flagged, cited as ordinary evidence, and never
   acted on. It also turned up, unplanned, while retrieving evidence for
   SC-08 (a different scenario) and was correctly flagged there too — that
   wasn't staged, we found it while writing the trace.
7. Run the real test suite:
   ```bash
   pytest -q
   ```
   8 tests, including one that validates every scenario's output against the
   frozen `schemas/findings.schema.json`, and one proving tier assignment is
   monotone (removing evidence can never raise a confidence tier).
8. Switch persona in a Python shell and diff the `entitlements_hash`:
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
   a UI at all. Or skip the Python shell:
   `python -m eval.trace SC-01` writes `eval/traces/SC-01.md`, a full
   stage-by-stage dump (including the entitlement predicate and hash) read
   straight off the pipeline's own context, for any of the 17 scenarios.

---

## If you have 30 minutes

9. [REPRODUCE.md](REPRODUCE.md) — clean-environment setup and real,
   measured timings (no `make` on the machine we built this on either — every
   step has a plain `python`/`pip` equivalent). Your scorecard should match
   ours exactly (it's deterministic — we reran it twice this session and got
   byte-identical output both times).
10. [`prompts/`](prompts/) — the only two model calls in the system, in full.
11. [`eval/scorecard.md`](eval/scorecard.md)'s full Misses section — every
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

**The changelog agrees with the history.** [`CHANGELOG.md`](CHANGELOG.md) — 10
entries, each naming what evidence prompted a change and what the change was,
including several real bugs found only by running the scenarios (or a live
model) after the engine was believed finished — a validator gap on `M`/million
suffixes, a tier-resolver crash on a model-authored pointer, a cross-process
floating-point non-determinism bug in DuckDB's default aggregation.

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

- **The UI exists but hasn't been eyeballed by a human.** `app/main.py`
  (`make app`) runs every one of the 17 scenarios and all three persona
  overrides with zero exceptions under Streamlit's headless `AppTest`
  harness — that's real functional verification, not a claim — but nobody
  has opened it in an actual browser to check the layout looks right. Engine
  and evidence came first on purpose; this is the ~20% we'd finish next.
- **Both baselines have been run live, not simulated.**
  [`eval/baseline_scorecard.md`](eval/baseline_scorecard.md) is real: B1
  (naive drill-down) asserts a cause on **3 of 3** scenarios where none was
  planted (SC-02, SC-08, SC-17), because it has no concept of declining. B3
  (same retrieved data, one LLM prompt, no pipeline, live via Groq's
  `openai/gpt-oss-120b`) does the same on 2 of those 3 — the one it wasn't
  sent a prompt for, SC-17, has no single question to hand it in the first
  place. GlassBox's rate on those same three: 0/3. On SC-08 specifically, B3
  produces a fluent, ~70-80%-confident cause citing a real ticket number
  (TCK-6666) that is a planted decoy — see `TRAJECTORIES.md`'s §2 for the
  full transcript.
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
- **The default clone runs the template narrator, not the live one, and
  that's a real gap worth naming precisely.** Live narration quality *has*
  been demonstrated — we ran it this session (Groq,
  `openai/gpt-oss-120b`) and it produced natural, correctly-validated prose,
  e.g. *"Net revenue fell 23.5% (Rs 34,99,600) in the week to 14 Aug... The
  primary driver is a localized movement in the Audio category within the
  South region..."* (`TRAJECTORIES.md`'s §1). But a determinism bug fix
  (single-threaded DuckDB, `PRAGMA threads=1` — see CHANGELOG) invalidated
  the replay-cache keys computed during that testing, and repopulating them
  hit unresolved hangs against the live API. So `eval/replay_cache/narrate/`
  is currently empty, and a fresh clone gets the template fallback instead —
  legible but mechanical, e.g. `"driven by: Movement localized to
  {'category': 'Audio', 'region': 'South'}"`. Every number is validated
  against the findings object either way.
- **The semantic contract is real adoption cost.** Five metrics is an
  afternoon each with their owners. Four hundred is a programme, and we would
  not pretend otherwise.

---

## Questions we are ready for

[`docs/07_DEMO_AND_PITCH.md#3-qa-bank`](docs/07_DEMO_AND_PITCH.md) — but ask
us anything. If we cannot defend a file in this repo, we should not have
shipped it.
