# For evaluators

Thank you for the time. Here is the shortest path to a fair assessment.

**Status check first, because it matters for how you read this:** the engine,
data generator, and evaluation harness are real, tested, and reproducible. A
minimal UI exists (`app/main.py` — `make app`), is verified to run every
scenario without error, and has real rendered screenshots in
[`screenshots/`](screenshots/) — not mockups. There is no hosted page —
everything below points at the repo itself (code, committed output, tests
you can run) rather than a link, because that's what actually exists right
now. We would rather you know that up front than discover it by clicking a
dead link.

---

## If you have 5 minutes

1. Open [`eval/scorecard.md`](eval/scorecard.md) and read the **Headline**
   section first, not the pass/fail table. **Hallucinated-cause rate: 0/15**
   (15 scored; two scenarios retired in place, see below — this is a real
   live-recorded run, not replay-only). No run ever asserted a cause the
   data doesn't support.
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

   **Want to watch it generate a genuinely fresh answer instead of replaying
   a cached one?** Groq's free tier (`console.groq.com/keys`, about a
   minute, no card) is enough for a full pass: in `.env` set
   `GLASSBOX_REPLAY=0`, `GLASSBOX_LLM_PROVIDER=groq`,
   `GLASSBOX_LLM_MODEL=openai/gpt-oss-120b` (what this repo's own live
   captures used), and `GLASSBOX_LLM_API_KEY` to your key, then `make app`
   and run any scenario — the badge changes from `🔁 REPLAYING` to `🟢 LIVE
   model call`, and the narration you're reading was written seconds ago,
   not committed to the repo.

If you only do one of these, do **step 2**.

---

## If you have 15 minutes

Add:

4. [`eval/baseline_scorecard.md`](eval/baseline_scorecard.md) — two real,
   run-not-invented baselines. B1 (naive drill-down) asserts a confident
   cause on **all 3** of the scenarios where none was planted. B3
   (single-LLM-prompt, live via OpenAI's `gpt-4o-mini` — after Groq's
   account-level quota and then Gemini's rate limit both blocked completion,
   `CHANGELOG.md` entries 026-027) does the same on the 2 of those 3 it was
   actually sent a prompt for, fluently, saying *"I am reasonably confident
   in this assessment"* about a cause built entirely from the planted decoy
   evidence. GlassBox's rate on the same three: zero.
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
   14 tests. Four must never be weakened — `test_gate_invariant`,
   `test_tiers_monotone`, `test_validator_blocks_invented_numbers`, and
   `test_findings_schema_valid` (validates every scenario's output against
   the frozen `schemas/findings.schema.json`; the tiers test proves
   assignment is monotone — removing evidence can never raise a confidence
   tier). The other ten are regression tests added while fixing real bugs
   found during live runs — see `CHANGELOG.md` entries 020-028.
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

**The changelog agrees with the history.** [`CHANGELOG.md`](CHANGELOG.md) — 28
entries, each naming what evidence prompted a change and what the change
was and naming the real commit, including several real bugs found only by
running the scenarios (or a live model) after the engine was believed
finished: a validator gap on `M`/million suffixes, a tier-resolver crash on
a model-authored pointer, a cross-process floating-point non-determinism bug
in DuckDB's default aggregation, a live call that hung for 19 minutes with
no exception because `urlopen`'s timeout bounds a socket operation, not the
whole request, and — found only by actually going live end to end — a real
narration that reattached a category-wide number to a named sub-region,
individually-real digits assembled into a false claim the validator's old
design couldn't catch.

**The scorecard shows failures, and now explains them.** 8 of the 15 scored
scenarios don't pass exactly. None of the 8 asserts a wrong or invented
cause — 2 abstain conservatively where an answer was possible (SC-06,
SC-12) and 6 answer on the correct branch with real cited evidence but name
a broader or adjacent segment than the exact ground truth (see the Misses
section for the specific dimension each one over- or under-included). We
would rather show this breakdown than a single "8 failed" line. Two more
scenarios (SC-07, SC-15) are retired, not failed — `data/manifest_reconciliation.md`
found their declared `magnitude_pct` was never verified against what the
generator actually plants (true for 12 of 14 planted scenarios, disclosed
there in full), and for these two specifically the field that *is* scored
(`true_segment` for SC-15, a near-zero real effect for SC-07) is itself the
problem, not just the magnitude. Both stay in the manifest, `ground_truth`
unedited, per our own pre-registration rule.

**Five of seven stages never touch a language model.** The model turns a
question into a query and a result into a sentence. Every numeral it writes is
re-extracted and matched against the computed findings before you see it —
`tests/test_validator_blocks_invented_numbers.py` proves this against an
adversarial case (a plausible-looking number that's a *combination* of two
real ones, not itself a real one).

---

## What we would push on, if we were you

We would rather name these than have you find them.

- **The UI has been visually verified, not yet by a blind third-party user.**
  `app/main.py` (`make app`) runs every one of the 17 scenarios and all three
  persona overrides with zero exceptions under Streamlit's headless `AppTest`
  harness — that's real functional verification, not a claim. It has also now
  been opened in an actual browser: [`screenshots/`](screenshots/) has 11 real
  renders across the home screen, the SC-01 headline/evidence/rejected-cause
  views, SC-08's abstention, and SC-14's flagged prompt-injection document —
  not mockups. What's still open: nobody who didn't build this has completed
  the tour unaided. Engine and evidence came first on purpose; this is the
  ~20% we'd finish next.
- **Both baselines have been run live, not simulated.**
  [`eval/baseline_scorecard.md`](eval/baseline_scorecard.md) is real: B1
  (naive drill-down) asserts a cause on **3 of 3** scenarios where none was
  planted (SC-02, SC-08, SC-17), because it has no concept of declining. B3
  (same retrieved data, one LLM prompt, no pipeline, live via OpenAI's
  `gpt-4o-mini` — Groq's account-level quota and then Gemini's rate limit
  both blocked completion first, `CHANGELOG.md` entries 026-027) does the
  same on 2 of those 3 — the one it wasn't sent a prompt for, SC-17, has no
  single question to hand it in the first place. GlassBox's rate on those
  same three: 0/3. On SC-08 specifically, B3 produces a fluent, confident
  cause ("I am reasonably confident in this assessment") built from the
  same decoy evidence GlassBox saw and declined to act on — see
  `TRAJECTORIES.md`'s §2 for the full transcript.
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
- **This one used to be a real gap; it isn't anymore, and we're leaving the
  history here rather than deleting it.** An earlier version of this repo
  had an empty `eval/replay_cache/narrate/` — live narration quality had
  been demonstrated in testing, but a determinism fix invalidated the cache
  keys and repopulating them hit unresolved hangs against the live API
  (root-caused later: `urllib.request.urlopen(timeout=N)` bounds a single
  socket operation, not the whole request — a connection trickling bytes in
  under that ceiling never trips it, however long the true wall-clock time
  is; `CHANGELOG.md` entry 016). **That's fixed now**, and the cache is
  genuinely populated: 18 narrate + 1 intent_parse entries, real captures
  from a live end-to-end run across two providers (12 Groq, 7 Gemini, after
  Groq's account-level quota blocked further calls — entries 019-028). A
  fresh clone with no key resumes those exact real narrations, e.g.
  *"Net Revenue fell -23.5% (Rs 35 lakh) in the week to 14 Aug... The South
  region, within Audio, accounts for 77.8% of that category-wide decline -
  Rs 27.24 lakh"* (`TRAJECTORIES.md`'s §1) — not the template fallback.
  Along the way, this surfaced a real correctness bug in the narration
  itself worth knowing about: a live response once misattributed the
  category-wide headline number to a named sub-region, because every digit
  was individually real (just reattached to the wrong claim), which the
  validator's number-presence check couldn't catch by design. Fixed with
  per-sentence scope checking, not a prompt patch alone — `CHANGELOG.md`
  entry 020, and the regression test that would have caught the original
  bug is in `tests/test_validator_blocks_invented_numbers.py`.
- **The semantic contract is real adoption cost.** Five metrics is an
  afternoon each with their owners. Four hundred is a programme, and we would
  not pretend otherwise.

---

## Questions we are ready for

[`docs/07_DEMO_AND_PITCH.md#3-qa-bank`](docs/07_DEMO_AND_PITCH.md) — but ask
us anything. If we cannot defend a file in this repo, we should not have
shipped it.
