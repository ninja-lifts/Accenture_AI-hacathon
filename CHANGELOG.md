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

## 007 — An independent audit found gaps the build session didn't: no schema
## test, SC-09 unpassable by construction, a fabricated baseline quote
**Date:** 2026-08-29 · **Phase:** 6→7 · **Commit:** (this session, pre-freeze)

- **Evidence:** A second pass over the repo, done deliberately as an
  adversarial audit rather than a continuation of the build, found: (1)
  Gate 4's "schema-valid findings" claim was only ever checked by hand in a
  terminal, never as a committed test; (2) `score_scenario`'s pass condition
  required an exact `true_segment` match for every planted `answer`
  scenario, but SC-09 has no `true_segment` by design (a business-wide
  definition-drift cause) — making it mathematically unpassable regardless
  of engine quality; (3) README.md's SC-08 section quoted an invented
  single-prompt B3 response ("Revenue fell 7.3%, primarily driven by...") as
  if it were real recorded output, left over from the starter template and
  never replaced.
- **Problem:** (1) and (2) are real correctness/methodology gaps. (3) is the
  most serious: fabricated evidence, sitting in the one section of the repo
  built specifically to demonstrate the product does *not* fabricate.
- **Decision:** Fix all three for real rather than patch around them: add
  the missing test, fix the scoring bug (not lower the bar — the bug made a
  legitimately-answered scenario score as a miss for a reason unrelated to
  the engine), and replace the fabricated quote with GlassBox's actual
  measured SC-08 output plus an honest "B3 not yet run" statement.
- **Change:** `tests/test_findings_schema_valid.py` (new), `eval/harness.py`
  (`score_scenario`'s pass criterion), `README.md`, `JUDGES.md` (also fixed:
  a stale claim that SC-12 "degrades to CORRELATED" when it actually
  abstains in the current build), `REPRODUCE.md` (real measured numbers in
  place of template placeholders), `TRAJECTORIES.md` (written from real
  captured runs, replacing 100% template content).
- **Result:** 7/17 exact pass (was 6 — the SC-09 fix, not new tuning). Zero
  fabricated content remaining in judge-facing docs, verified by grepping
  for the removed quote and re-reading every `⟪FILL⟫` site.

## 008 — Groq adapter added; B1 and B3 baselines run for real
**Date:** 2026-08-29 · **Phase:** 6 · **Commit:** (this session, pre-freeze)

- **Evidence:** `engine/llm_client.py` only implemented an Anthropic
  adapter; no live key was available for it. A Groq key was.
- **Problem:** Without a live model call, B3 (the highest-value baseline —
  same data, one prompt, no pipeline) could only ever be "not yet run,"
  and the SC-08 comparison — arguably the single strongest piece of
  evidence available — stayed hypothetical.
- **Decision:** Add a second provider adapter (`_call_live_openai_compatible`,
  Groq's OpenAI-compatible chat-completions API) behind the same
  `engine/llm_client.py` boundary, proving the "provider is config, not
  code" claim with a second working example rather than just the one
  adapter it shipped with. Build B1 for real (no external dependency,
  should have existed already). Run B3 live rather than fake it.
- **Change:** `engine/llm_client.py` (Groq adapter, 429 retry-with-backoff,
  a discovered Cloudflare-vs-default-urllib-User-Agent 403 fixed with a
  browser UA string), `eval/baselines/b1_naive.py` (new), `eval/baselines/run_all.py`
  (new; B3's prompt payload is built from real retrieval calls, independent
  of whether GlassBox's own gate went on to answer or abstain, so an
  abstention doesn't quietly starve B3 of evidence GlassBox actually saw).
- **Result:** B1: 2/17 exact segment match, asserts a cause on **3/3**
  scenarios where none was planted. B3 (live, `openai/gpt-oss-120b` via
  Groq): run on 16/17, asserts a cause without hedging on 2/3. On SC-08
  specifically, B3 produced a fluent, 70-80%-confident, fabricated cause
  citing a real document from a *different* scenario (TCK-6666) — quoted
  verbatim in `eval/baseline_scorecard.md`, not paraphrased. GlassBox's rate
  on the same three scenarios: 0/3.

## 009 — Live narration surfaced two real validator gaps and one thin prompt
**Date:** 2026-08-29 · **Phase:** 5 · **Commit:** (this session, pre-freeze)

- **Evidence:** First live run of `s07_narrate` (via Groq) failed
  validation twice, then fell back to the template — not a crash, but a
  silent quality regression nobody would have noticed without checking
  `telemetry.validator_retries`.
- **Problem:** Two real gaps in `engine/validator.py`, both confirmed by
  inspecting the actual rejected output: (1) `extract_numerals` didn't
  recognise "M"/"million" as a magnitude suffix, so "≈-1.29M" extracted as
  the unaccounted numeral `1.29`; (2) `_collect_findings_numbers` only
  walked literal JSON number values, so a numeral the model faithfully
  quoted *from a string field* (e.g. `rejected_hypotheses[].detail`:
  "treated moved -9.2% vs control 0.0%") was never in the allowed set,
  because that number only exists inside a text field, not as a JSON
  number. Separately: `openai/gpt-oss-120b` is a reasoning model that
  spends part of its token budget on an internal `reasoning` field before
  the visible answer — under-budgeted `max_output_tokens` produced an
  empty final generation, which Groq's JSON-mode validator rejects with a
  400 rather than returning partial content. And once validation passed,
  the model quoted every number unrounded ("-23.51725190215333%"),
  technically valid but unreadable.
- **Decision:** Fix the validator gaps for real (they'd misfire against any
  provider's output, not just Groq's) rather than route around them.
  Give reasoning-style models a generous token ceiling rather than the
  prompt's declared budget. Tighten `prompts/narrate.md` to require
  human-scale rounding, since the validator already accepts a rounded
  figure as a match within ~2% - rounding was never a validation risk, the
  prompt just didn't ask for it.
- **Change:** `engine/validator.py` (`_MULTIPLIERS`, string-aware
  `_collect_findings_numbers`), `engine/llm_client.py` (reasoning-model
  token bump), `prompts/narrate.md` (v1.0.0 → v1.1.0, rounding rule),
  `engine/pipeline.py` (`_assemble_abstention` was also only keeping the
  narrator's headline and silently dropping the ruled-out/referral
  sentences it was instructed to write — now joins the full narration).
- **Result:** SC-01 and SC-08 narrate live on the first attempt, 0 validator
  retries, real natural-language output captured and quoted in this
  changelog and `TRAJECTORIES.md`. *(That specific cache entry did not
  survive to be committed — the determinism fix in entry 010's companion
  change invalidated its key, and this session couldn't reliably
  regenerate it afterward against a live API that started hanging for
  unexplained periods. The quotes are real; the offline-replay artifact
  of them is not currently in the repo. See `CHECKLIST.md`.)*

## 010 — `pytest` failed after a live batch run populated more of the replay cache: `_resolve_tier` couldn't parse a model-authored pointer it hadn't seen
**Date:** 2026-08-29 · **Phase:** 5 · **Commit:** (this session, pre-freeze)

- **Evidence:** Ran the harness live across more scenarios to broaden replay-
  cache coverage beyond SC-01/SC-08 (interrupted partway by rate limits, but
  it had already cached ~11 more real responses). `pytest` immediately
  after: `ValueError: invalid literal for int() with base 10: '0].tests[0'`
  in `engine/pipeline.py::_resolve_tier`, triggered by a cached SC-11
  response.
- **Problem:** `_resolve_tier` assumed every `tier_from` string a narrator
  writes exactly matches `drivers[N]` and nothing else, then did
  `int(tier_from[len("drivers["):-1])` on it - a live model is free to write
  a more specific pointer like `drivers[0].tests[0]` (reasonably, since it's
  pointing at a specific test's result, not just the driver), and the exact-
  match assumption crashed the whole pipeline run on perfectly sensible
  model output. `tier_from` is untrusted, model-authored input; the code was
  treating it as a value the pipeline controls the shape of.
- **Decision:** Parse only the meaningful leading `drivers[N]` prefix with a
  regex and ignore anything after it, rather than require an exact match.
- **Change:** `engine/pipeline.py::_resolve_tier`.
- **Result:** `pytest` green again (8/8), including against the now-broader
  live replay cache. Found by running the actual test suite against real
  model output, not by anticipating the failure mode in advance - exactly
  why this project treats "run it for real" as part of the process, not a
  formality after the code is believed finished.

---

## 011 — A deep post-submission-readiness audit found the docs had drifted from the code, and the cost receipt could contradict itself
**Date:** 2026-08-30 · **Phase:** 7 · **Commit:** (this session, pre-freeze)

- **Evidence:** Re-ran `make eval`/`make baseline` in a clean shell (no key)
  and diffed against the committed files to check the reproducibility claim
  was still true. `eval/scorecard.md` matched byte-for-byte except the
  commit-hash header — good. But `eval/cost_receipt.md`'s table showed
  `LLM calls per run (max observed / cap) 1 / 2` with real nonzero token and
  latency numbers, while the prose directly below it unconditionally read
  "no live LLM key was configured... `llm_calls` is 0 for all of them" -
  the file contradicted itself. Separately, grepping README.md and
  JUDGES.md against the actual repo state found both still saying
  "the UI isn't built," "B3 hasn't been run," and "only one provider
  adapter is implemented" - all three false as of commit `9ca7502`
  (Groq adapter, live B3 run, and `app/main.py` all landed last session,
  but the judge-facing docs were never updated to match).
- **Problem:** two different kinds of drift. (1) `render_cost_receipt` in
  `eval/harness.py` had a hardcoded prose string written for the common
  no-key case, never made conditional on the actual telemetry - true only
  by accident once the replay cache was empty, and silently false the
  moment any run's `llm_calls` count is nonzero (a populated cache, or a
  live key). (2) Nothing enforces that judge-facing prose docs track the
  code/eval state they describe - CHECKLIST/CHANGELOG were kept current
  through this project's process, but README.md and JUDGES.md are prose
  written once and not part of that loop, so they went stale the moment
  real work outpaced them.
- **Decision:** Fix (1) as a real bug - a receipt whose numbers and prose
  disagree is exactly the kind of self-undermining claim this project
  exists to avoid, and it isn't a scored metric so nothing in the "don't
  tune to improve scores" rule is in tension with fixing it. Fix (2) by
  rewriting the specific stale passages (not a wholesale rewrite) with
  facts re-verified against the current repo, not memory. Also used
  Streamlit's `AppTest` harness to actually exercise `app/main.py` -
  select each scenario, click Run, switch every persona - since the Chrome
  browser tool still won't connect (three failed attempts across two
  sessions) and "syntax-checked only" was a real, named gap.
- **Change:** `eval/harness.py::render_cost_receipt` (note text now
  branches on `mode` and whether any run made a call, instead of a static
  string); `README.md` (UI status, the B3/SC-08 comparison, provider
  adapter count, `make app` status, file tree); `JUDGES.md` (status banner,
  the "what we'd push on" section, changelog entry count); `REPRODUCE.md`
  (baselines and app sections rewritten from "not yet built" to real,
  measured steps, plus a new troubleshooting row for the DuckDB
  single-writer lock hit directly this session when a backgrounded
  `streamlit run` held the file open during `pytest`); `CHECKLIST.md`
  (Phase 5 rows updated to cite the `AppTest` verification).
- **Result:** `eval/cost_receipt.md` regenerated clean (0 calls, table and
  prose agree) - `pytest` still 8/8, `eval/scorecard.md` still byte-identical
  to the pre-audit version except the header. `AppTest` result: all 17
  scenarios and all 3 persona overrides run through the real UI with zero
  exceptions - real functional verification, though the visual layout is
  still unconfirmed in an actual browser. No engine, contract, or manifest
  file touched.

---

## 012 — Built the `--trace` flag the master build flow scoped but the build session skipped
**Date:** 2026-08-30 · **Phase:** 4 · **Commit:** (this session, pre-freeze)

- **Evidence:** `docs/01_MASTER_BUILD_FLOW.md` line 163 specs a `--trace` flag
  "feeds TRAJECTORIES.md; build it now, it costs an hour here and a day
  later" - never built. `TRAJECTORIES.md` itself admits its SC-01/SC-08/
  SC-14 sections were captured by hand, "instrumenting the stage functions
  directly in a Python shell," which is exactly the manual process the flag
  was meant to replace.
- **Problem:** no way to inspect a scenario's real stage-by-stage output
  without either reading `eval/scorecard.md`'s final row or writing a
  one-off Python shell session per scenario, as `JUDGES.md`'s 15-minute path
  currently asks a judge to do for the persona/entitlements check.
- **Decision:** add it as a strictly additive capability rather than change
  `pipeline.run`'s existing contract - a `trace: bool = False` parameter
  that, only when explicitly set, switches the return from `findings` to
  `(findings, trace_log)`. Every existing call site (the harness, the app,
  all three protected tests) passes no `trace` argument and is provably
  unaffected: reran the full suite and diffed a regenerated
  `eval/scorecard.md` against the pre-change version - byte-identical.
- **Change:** `engine/pipeline.py` (`_snapshot`/`_TRACE_KEYS`, the `trace`
  parameter, a snapshot call after each stage); new `eval/trace.py`
  (`python -m eval.trace SC-01` writes `eval/traces/SC-01.md`).
- **Result:** generated real traces for one scenario of each branch type
  (SC-01 answer, SC-08 abstention, SC-02 no_alert, SC-17 clarification) -
  all four ran clean. SC-01's trace surfaces the entitlement predicate and
  `entitlements_hash` Stage 01 actually computed
  (`category IN (SELECT category FROM role_scope WHERE role_id = 'cm_audio')`),
  the same access-control evidence `JUDGES.md` item 8 asks a judge to
  reproduce by hand - now one command. `pytest` 8/8, scorecard unchanged.

---

## 013 — Stage 00 absorbed a live intent-parse failure into the same fallback path as "no key configured"
**Date:** 2026-08-30 · **Phase:** 5 · **Commit:** `465bebb`

- **Evidence:** `engine/stages/s00_intent.py::run()` wrapped both
  `llm_client.complete("intent_parse", ...)` and the subsequent
  `json.loads(result.text)` in one `try` block, catching
  `(LLMCacheMiss, LLMCallCapExceeded, ValueError, KeyError)` together and
  falling back to `_deterministic_parse` on any of them.
- **Problem:** `LLMCacheMiss` means nothing was attempted - the documented
  offline path. A `ValueError`/`KeyError` from `json.loads` means a call
  actually ran and came back malformed or the wrong shape - a real failure of
  a call this run made. Collapsing both into one except clause meant a broken
  live call and "no key configured" were indistinguishable to the rest of
  the pipeline. `engine/llm_client.py`'s own `LLMCallCapExceeded` docstring
  already says "this is a bug, not a case to handle gracefully," yet it sat
  in the same catch.
- **Decision:** Split the try blocks. Only `LLMCacheMiss` triggers the
  deterministic fallback. A parse failure on an actual result now propagates
  - the harness records it as a scenario `ERROR` (not a silent lower-fidelity
  answer), and the UI surfaces it via `st.exception` rather than rendering
  something that looks like the normal offline path.
- **Change:** `engine/stages/s00_intent.py::run()` - separated the
  `LLMCacheMiss` catch from the `json.loads` parse step; module docstring
  states the distinction explicitly.
- **Result:** `pytest` 8/8, unchanged - the offline/replay path (the only
  path this session's replay-cache runs exercise) is byte-identical. No live
  scenario in this repo has yet hit a genuine intent-parse failure, so this
  closes a gap in defensive coverage rather than fixing an observed
  misfire - the guard is now in place for when a live run does hit it.

## 014 — A failed live narration call could render a template behind a LIVE provenance banner
**Date:** 2026-08-30 · **Phase:** 5 · **Commit:** `465bebb`

- **Evidence:** The same pattern, one layer deeper: `engine/stages/s07_narrate.py`'s
  retry loop caught `(LLMCacheMiss, LLMCallCapExceeded, ValueError, KeyError)`
  around both `llm_client.complete("narrate", ...)` and the
  `json.loads`/`validator.validate` step that follows it, and simply
  `break`-ed out on any of them. If every retry attempt returned text that
  failed to parse at all - a live-call failure, not a validator rejection -
  the loop still exited quietly with `narration = None`, which then rendered
  `template_fn(outcome_draft, persona)`.
- **Problem:** `provenance.replay_mode` is computed independently of what
  Stage 07 actually managed to do -
  `ctx["settings"].replay_mode or not ctx["settings"].llm_api_key` in
  `engine/pipeline.py::_base_findings` - so a run with a live key configured
  that attempted a live call and failed to parse it on every retry still
  reports `replay_mode: False`. `app/main.py::render_findings` reads exactly
  that field to show "🟢 LIVE model call". The result: a live call that
  failed silently would still display a LIVE provenance banner over template
  prose - indistinguishable from a working live call to anyone reading the
  output, which is exactly what this project's provenance guarantee exists
  to prevent. This is the strongest of the two fixes in this pair, because it
  is a defect in the specific claim ("this is a live answer") the whole
  submission is built to never misrepresent.
- **Decision:** Track whether any retry attempt failed to parse
  (`live_attempt_failed`), separately from an ordinary validator rejection
  (which still falls back to the template silently, by design - `Rule 7`,
  `validator_retries` is the guard working, not a defect). Raise instead of
  falling back only when the retry budget is exhausted by real parse
  failures.
- **Change:** `engine/stages/s07_narrate.py::run()` - split the
  `LLMCacheMiss` catch from the parse/validate step, added
  `live_attempt_failed` tracking, raises `RuntimeError` naming the exhausted
  retry count when every attempt was a live parse failure rather than a
  validator rejection. Module docstring states the distinction.
- **Result:** `pytest` 8/8, unchanged - the validator-rejection fallback path
  (exercised by the existing schema/validator tests) still falls back to the
  template exactly as before. Only the previously-unguarded live-parse-
  failure path changed behaviour, from a silent template render to a raised,
  loud error.

## 015 — provenance had no entry at all for the document corpus, so a BM25-only degradation had nowhere honest to surface
**Date:** 2026-08-30 · **Phase:** 5 · **Commit:** `681456c`

- **Evidence:** `engine/stages/s05_retrieve.py` already degraded to BM25-only
  retrieval when the embedding model couldn't load, and already printed a
  loud stderr warning saying so - but `ctx["sources"]` (the list that becomes
  `findings.provenance.sources`) is only ever populated by
  `s01_define.py::run()`, once per contract source (`fact_orders`,
  `dim_product`). Stage 05 never appended anything for the document index
  itself, so there was no source entry to attach a quality flag to - the
  stderr print was the *only* place this was recorded anywhere.
- **Problem:** `findings.schema.json`'s `provenance.sources[].quality_flags`
  was the right home for this (checked: a plain array of string, already
  used by `s01_define.py` for `stale_source`), but using it required a
  source entry to exist first. Without one, "this run degraded to
  BM25-only" was invisible to the schema-valid findings object a judge or
  the UI actually reads - visible only to whoever happened to be watching
  stderr.
- **Decision:** Append a `document_index` source entry to `ctx["sources"]`
  every run (not only on degradation), carrying
  `embeddings_unavailable_bm25_only` in `quality_flags` when the embedding
  model didn't load. No schema change - the field already existed. Kept the
  stderr print (checked before the UI even starts, e.g. a headless run).
  Separately narrowed `_load_index`'s `except Exception` to
  `except (ImportError, OSError)` - covers package-missing and no-network,
  since connection/timeout/TLS/missing-local-cache errors all subclass
  `OSError` in Python 3. Deliberately left uncaught: `RuntimeError` and
  library-internal errors from a corrupted cache or version mismatch - those
  aren't "no network," and telling them apart further would mean importing
  `huggingface_hub`/`torch` exception types `requirements.txt` doesn't pin
  (Rule 9). Letting those propagate is the honest choice given what's safely
  knowable here without that dependency.
- **Change:** `engine/stages/s05_retrieve.py::run()` (new source entry),
  `_load_index` (narrowed except clause, docstring); `engine/pipeline.py`
  (`_TRACE_KEYS["s05_retrieve"]` now includes `sources`, so `--trace` shows
  it too); `app/main.py::render_findings` (new "Sources" list in the
  Telemetry & security expander - `source_id`, `as_of`, `row_count`, any
  `quality_flags` with a ⚠️ marker; nothing read `provenance.sources` at all
  before this).
- **Result:** `pytest` 8/8 (schema-validation test included - the new source
  entry validates against the frozen schema unchanged). Verified with
  Streamlit's `AppTest` harness: ran SC-01 through the real UI, no
  exception, `document_index` rendered alongside `fact_orders`/`dim_product`
  with 496 rows and (on this machine, where the embedding model loads fine)
  an empty `quality_flags`. `eval/scorecard.md` unchanged except the header
  commit hash; `eval/cost_receipt.md`'s latency line moved with normal
  wall-clock noise (tokens/cost still 0/0 in replay mode, byte-identical).

## 016 — First live run hung indefinitely; no wall-clock read timeout on the provider call
**Date:** 2026-08-30 · **Phase:** 6 · **Commit:** `0d46a85`

- **Evidence:** The first live run of the full 17-scenario harness (real
  Groq key, `GLASSBOX_REPLAY=0`) hung: the process stayed alive
  (confirmed via `ps`, PID present, not crashed), but no new replay-cache
  entry was written for 19+ minutes - well past the old retry logic's
  worst-case bound of ~13.5 minutes (5 attempts x 150s timeout + 429
  backoff), and no exception was ever raised.
- **Problem:** `_urlopen_with_retry` called
  `urllib.request.urlopen(req, timeout=150)` and then `resp.read()` on the
  same socket. That `timeout` is a *per-socket-operation* timeout, not a
  wall-clock deadline on the whole request - `resp.read()` re-arms it on
  every successful `recv()`, so a connection trickling bytes in slower than
  150s apart never trips it, however long the *total* transfer takes. The
  retry loop's `except urllib.error.HTTPError` only catches a completed
  response with a 4xx/5xx status; a raw socket stall doesn't raise that at
  all, so it wasn't retried either - it just hung. (Checked and ruled out
  as contributing causes: no `stream` flag is set in either provider's
  request body, and grepping `engine/` found nothing blocking on stdin -
  see the diagnosis reported in-session before any code changed.)
- **Decision:** No single `urlopen(timeout=N)` value fixes a
  per-operation-timeout problem - the fix has to add an actual wall-clock
  deadline urllib doesn't provide natively, without a new dependency
  (Rule 9 rules out swapping to `requests`, which does support a
  connect/read timeout tuple natively). Chose a daemon-thread +
  `queue.Queue.get(timeout=...)` pattern over
  `concurrent.futures.ThreadPoolExecutor` specifically because the
  executor's context-manager exit calls `shutdown(wait=True)`, which
  blocks until the thread actually finishes - the identical hang, one
  level up. A bare daemon thread can be safely abandoned on timeout (it
  won't block process exit) even though nothing in Python can cancel a
  thread already blocked in a C-level `recv()`.
- **Change:** `engine/llm_client.py` - `_do_single_attempt` runs each
  provider request in a daemon thread; `_urlopen_with_retry` awaits it
  against a hard `_MAX_TOTAL_SECONDS=300` wall-clock budget shared across
  all `_MAX_ATTEMPTS=5` attempts (not just `_SOCKET_TIMEOUT_SECONDS=60` per
  operation), with jittered backoff on 429/`OSError`/`URLError`, and raises
  `TimeoutError` on exhaustion - never silently degrades. Both adapters and
  `_call_live` take a `label` (scenario id + stage) threaded through
  `complete()` (new `ctx["scenario_id"]`, set via a new optional
  `pipeline.run(scenario_id=...)` kwarg - additive, like `trace` in entry
  012) and B3's direct `_call_live` call, printed to stderr on every
  attempt/success/failure/retry. `_call_live` adds a 3s delay after every
  live call - the one point `complete()` and B3 both go through - as a
  first line of defence against a rate-limit burst, ahead of the existing
  429 backoff. `eval/harness.py` adds an independent, defence-in-depth
  `_run_with_deadline()` (same daemon-thread pattern) wrapping each
  scenario's run in a `SCENARIO_TIMEOUT_SECONDS=700` outer deadline - a
  stall anywhere, not just inside `llm_client.py`'s own bound, now becomes
  an ordinary scenario `ERROR` row through the harness's existing exception
  handling rather than stalling the batch.
- **Result:** `pytest` 8/8 - but only once forced to `GLASSBOX_REPLAY=1`
  explicitly. A plain `pytest` run picked up `.env`'s now-live
  configuration and actually went live for ~12 minutes, hitting a real
  Groq 429 (`Retry-After` around 300s) on two tests - not a code
  regression (the same 8 pass under replay), but a real, unplanned cost
  from a genuine gap: the test suite doesn't force replay mode itself, it
  inherits whatever `GLASSBOX_REPLAY` the environment has. Noted here
  rather than fixed unilaterally, since it's a test-harness scoping
  question outside what was asked. The two failures are themselves
  evidence the fix works: `TimeoutError` raised loudly after exhausting
  the wall-clock budget, in a scenario where the old code would have hung
  the same way it did during the run this entry is about.

## 017 — Tests inherited live mode from .env and made 12 minutes of billed calls; tests now force replay unconditionally
**Date:** 2026-08-30 · **Phase:** 6 · **Commit:** `20ab098`

- **Evidence:** Immediately after committing the hang fix (entry 016), ran a
  plain `pytest -q` with no env override to check for regressions. `.env`
  (created this session to run the live harness) had `GLASSBOX_REPLAY=0` and
  a real key. The run took 711s instead of the usual ~30-60s and failed 2 of
  8 tests with a live `TimeoutError` wrapping `HTTPError: 429 Too Many
  Requests` (`Retry-After` ~300s) from a real narrate call `pytest` had no
  business making.
- **Problem:** `engine/config.py`'s `Settings` dataclass reads
  `GLASSBOX_REPLAY` as a *class-level field default* via `os.getenv(...)`,
  evaluated once when the class body executes (i.e. on first import of
  `engine.config`) - `config.load()` is just `Settings()`, it doesn't
  re-read the environment per call. Nothing in the test suite ever set or
  forced `GLASSBOX_REPLAY` itself; it silently inherited whatever `.env`/the
  ambient shell had. That was invisible for the entire session up to this
  point, because `.env` didn't exist yet - the moment it was created with a
  live key, every subsequent `pytest` invocation silently went live too,
  including ones run purely to check for code regressions after a change.
- **Decision:** Tests must be hermetic regardless of what a developer's or
  judge's `.env` happens to contain - a suite whose behaviour (and cost)
  depends on ambient secrets isn't trustworthy. Force `GLASSBOX_REPLAY=1` at
  `tests/conftest.py` MODULE level, not inside a fixture - it has to run
  before `engine.config` is first imported anywhere in the process, since
  its field defaults are computed at import time; a fixture body runs too
  late if anything already imported `engine.config` by then. Backstop that
  with a session-scoped autouse fixture monkeypatching
  `engine.llm_client._call_live` to raise `AssertionError` if ever called -
  independent of the env-var-timing fix, so an import-order surprise stops
  the network call rather than silently going live again.
- **Change:** new `tests/conftest.py`.
- **Result:** `pytest` 8/8 in 27s with `.env` still live-configured
  (`GLASSBOX_REPLAY=0`, real key, unchanged) - confirmed by re-running with
  no env override after adding the fixture; the same conditions took 711s
  and failed 2 tests on a real 429 before this fix.

## 018 — Two more guards against a repeat: a forced-replay Makefile default, and a resumable replay cache
**Date:** 2026-08-30 · **Phase:** 6 · **Commit:** `20ab098`

- **Evidence:** Same incident as entry 017, two more angles on it. (1)
  `make eval`/`make reproduce` had no opinion on `GLASSBOX_REPLAY` at all -
  exactly the same inheritance bug as the test suite, except `make
  reproduce` is the literal command `README.md` promises a judge. (2)
  Restarting the live harness after swapping API keys (session-internal, not
  committed - the first key hit a rate limit) began *overwriting* the 10
  already-captured real responses from the first, interrupted run with fresh
  live calls, because `complete()` unconditionally called live whenever
  `use_live` was true, regardless of whether a cache entry for that exact
  payload already existed.
- **Problem:** (1) is entry 017's bug, one layer up - a judge running the
  promised command should never depend on what happens to be in their
  environment. (2) means a real interruption partway through a batch (a 429,
  the hang this whole thread of entries is about, anything) doesn't just
  delay the run - re-running it re-bills every call already made, not just
  the ones still outstanding.
- **Decision:** (1) `make eval` (and therefore `make reproduce`, which
  depends on it) now forces `GLASSBOX_REPLAY=1` in the recipe itself,
  overriding any ambient/`.env` value. A live run gets an explicit, separate
  `make eval-live` target that overrides to `GLASSBOX_REPLAY=0` (also
  regardless of ambient state) and prints the configured provider/model and
  an approximate call count before it starts. (2) `complete()` now checks
  the cache *before* deciding whether to go live - live mode becomes "call
  live for anything not yet captured," not "always call live and overwrite
  what's there." Replay-cache writes were already incremental (verified
  earlier this session: a killed live process left the 10 responses it had
  already made intact on disk, written per-response, not batched at the end)
  - this closes the other half of resumability, skipping calls already on
  disk instead of only not losing the ones that complete.
- **Change:** `Makefile` (`eval` forces `GLASSBOX_REPLAY=1`; new
  `eval-live` target with a provider/model/call-count warning);
  `engine/llm_client.py::complete()` (cache-exists check moved before the
  live/replay branch; a stderr line notes a resumed call). **Known related
  gap, left alone because it wasn't part of what was asked:** `make
  baseline` (B3) has neither a forced-replay default nor any caching at all
  - `eval/baselines/run_all.py::run_b3` calls `_call_live` directly, bypassing
  `complete()` (and its cache) entirely, so every `--baseline` run calls live
  unconditionally and uncached regardless of what already exists.
- **Result:** `pytest` 8/8 (unaffected - replay mode already skipped the
  live branch entirely, so checking the cache first is a no-op there).
  Resumability against a genuine already-cached live payload is verified
  structurally and by code review here, not yet exercised against a real
  duplicate live call - the live SC-01/17-scenario runs immediately
  following this entry are the real-world check, and will be reported
  honestly either way.

## 019 — `magnitude_pct` was a design target, never verified against the data it was meant to describe - true for 12 of 14 planted scenarios
**Date:** 2026-08-30 · **Phase:** 6 · **Commit:** `357ba41`

- **Evidence:** A live SC-01 narration surfaced an internal contradiction (a
  category-wide headline number narrated as if it were South-region-specific
  - full account in entry 020, the fix that came out of the same
  investigation). Chasing the numbers down: the engine's own DiD-measured
  SC-01 movement is -18% to -23.5% depending on scope, nowhere near the
  manifest's declared `magnitude_pct: -8.2`. That prompted checking all 17.
  An independent script - raw DuckDB queries against
  `data/generated/meridian.duckdb`, mirroring each `contracts/*.yaml` SQL by
  hand, deliberately never calling `engine/pipeline.py` - measured every
  scenario's actual movement and compared it to what the manifest declares.
  Sanity-checked against the engine's own numbers for SC-01 first: matched
  to the cent. Full table, methodology and a three-way SC-15 analysis are in
  the new `data/manifest_reconciliation.md` - not reproduced here in full,
  since the point of a changelog entry is to point at the artefact, not
  duplicate it.
- **Problem:** Of the 14 `planted: true` scenarios, only SC-03 and SC-05
  land close to their declared `magnitude_pct`. The rest diverge 1.6x-3.5x
  in both directions. Two are worse than a magnitude miss: **SC-07**
  measures -0.1% against a declared -6.8% - the two-cause effect it's
  supposed to test essentially never materialised in the generated data.
  **SC-15** measures the *wrong sign* (+12.0% against a declared -2.1%) at
  its declared 2-dimension `true_segment` - because `data/generate.py`
  actually plants the effect at 3 dimensions (`region, category,
  channel: Retail`; true 3-dim cell: -84.4%, plant confirmed real and
  correctly targeted) and the manifest's `true_segment` field never encoded
  the third one. Root cause, common to all of it: every plant is coded as a
  raw multiplicative shock to an upstream rate (`conversion_rate`,
  `sessions_lambda`, `on_time_rate`, `return_rate`, `aov`), chosen when each
  scenario was designed, and nothing ever verified the chosen multiplier
  reproduces the declared `magnitude_pct` once it runs through Poisson
  sampling and aggregation - the same pattern `docs/adr/0006-detection-thresholds.md`
  already documents for detection thresholds, recurring in a part of the
  codebase nobody re-checked the second time.
- **Decision:** Disclose, do not repair. Two things make this safe rather
  than a pre-registration violation (Rule 2): first, `magnitude_pct` is not
  a scoring key - grepped `eval/`, `engine/`, `app/`, `tests/`, zero matches
  outside the manifest itself; `eval/harness.py::score_scenario` reads
  `true_segment`, `expected_branch` and `evidence_document_ids`, and none of
  those are in question for 12 of the 14 mismatches. (A related, smaller
  finding surfaced while verifying this: `eval/metrics.py::rca_top1(findings,
  true_cause_id)` is defined but never called anywhere - `harness.py`
  computes its own inline top-1 check from `true_segment` instead, so
  `true_cause_id` is currently dead weight in scoring too. Not fixed here -
  out of scope for this disclosure, noted in `data/manifest_reconciliation.md`
  for whoever picks it up next.) Second, `data/generate.py` and every
  `magnitude_pct` value are unchanged - regenerating the data to match the
  manifest after seeing engine output is the one thing pre-registration
  exists to prevent, and this entry does the opposite: it publishes the
  mismatch against the frozen file rather than quietly closing the gap.
  SC-07 and SC-15 are the two exceptions, marked `RETIRED` in their `notes`
  field only (Rule 2's own prescribed mechanism for an ill-posed scenario) -
  not because their magnitude is off, but because SC-07's effect is
  essentially absent and SC-15's `true_segment` (the field that *is* scored)
  is itself wrong. The other 12 mismatches are disclosed but not retired:
  their scored fields aren't in question, only an unscored one.
- **Change:** new `data/manifest_reconciliation.md` (full table, SC-15
  three-way breakdown, scoring-key audit). `data/injection_manifest.yaml` -
  SC-07 and SC-15's `notes` fields only, replaced with `RETIRED - <reason>`
  plus the original design intent for reference; `ground_truth` blocks for
  both, and every other scenario, byte-identical. `eval/harness.py` - a
  `RETIRED` scenario now gets its own row (`actual_branch: "RETIRED"`,
  everything else `None`) instead of being silently skipped from the loop
  entirely; `render_scorecard` computes every aggregate (pass count,
  hallucination rate, abstention precision/recall, RCA top-1) from
  `scored_rows` (retired excluded) rather than all `rows`, so a retirement
  can never quietly improve a ratio by shrinking its denominator, and a new
  `### Retired` section names them and why, every time.
- **Result:** `pytest` 8/8 - `tests/test_findings_schema_valid.py` already
  had a `RETIRED`-skip check written in from the start (never previously
  exercised, since nothing was retired until now) and needed no change.
  Scorecard: **7/17 → 7/15**, hallucinated-cause rate **0/17 → 0/15**,
  abstention precision **0.25 (1/4) → 0.33 (1/3)** - all because SC-07/SC-15
  are excluded from every denominator, not because anything else changed;
  every other row's numbers are byte-identical to the pre-retirement
  scorecard. Verified the new `### Retired` section renders correctly and
  both scenarios' full `ground_truth` blocks are still present and unedited
  in the manifest.

## 020 — A real number can be reattached to the wrong claim; the validator, and the prompt's own worked example, both let it through
**Date:** 2026-08-30 · **Phase:** 5 · **Commit:** `21f6b3f`

- **Evidence:** A live SC-01 narration (first genuine live run, `openai/gpt-oss-120b`
  via Groq): headline said "Net revenue... fell 23.5% (Rs 35 lakh) in the
  South region for the Audio category," then the next sentence said a
  volume shortfall "represents 96.7% of the total gap." Both cannot be true
  of the same quantity - South's real share of the category-wide movement
  is Rs 27.24 lakh (77.8%), not Rs 35 lakh, and "96.7% of the total gap" is
  only true relative to a *third*, smaller number (South's own DiD-measured
  decline, Rs 13.35 lakh) that the sentence never named. Every individual
  digit was real and traced back to the findings object -
  `engine/validator.py::validate` pools every number in the whole object
  into one flat set and only checks presence, so it passed. Root cause
  traced one layer further: `prompts/narrate.md`'s own worked example used
  `-8.2% / Rs 3.1 crore, "in the South"` - the *manifest's declared* SC-01
  magnitude (entry 019), never anything the engine computes - modelling the
  exact misattribution the model went on to produce.
- **Problem:** Two distinct gaps, not one. (1) No mechanism catches a real
  number reattached to the wrong scope - `answer.localization[]` (a
  segment's share of the headline) and `answer.decomposition[]` (that
  segment's own separately-measured decline) can legitimately both contain
  a number that's "about the same segment," and nothing enforced that a
  sentence naming a segment uses that segment's own figures rather than the
  unscoped `headline_delta_pct`/`_abs`. (2) The prompt's only worked example
  taught the failure mode it was meant to prevent.
- **Decision:** Two validator changes plus a prompt fix, not a validator
  rewrite. **Per-sentence scoping:** a sentence whose `tier_from` matches
  `drivers[N]` and whose text names a segment (keyword-matched against
  `answer.localization[].dimensions` values - cheap, no NLU) may not draw on
  the unscoped headline numbers; everything else is unaffected, including
  the `headline` field itself, which is the one place meant to state the
  run's unscoped movement and so is exempt by construction. Caught in
  testing against the real object, not the minimal unit fixture: a plain
  `allowed - headline_numbers` set difference missed
  `answer.action.expected_impact.value`, which independently carries the
  same magnitude as `headline_delta_abs` but stored positive where the
  headline is signed negative - two distinct floats to a set, one number to
  a reader. Fixed with a magnitude/tolerance-aware exclusion
  (`_exclude_by_magnitude`) matching `_accounted_for`'s own sign-blind
  comparison, not a literal set difference. **Prompt rule 8:** any
  "X, representing Y% of Z" construction must name what Z *refers to* in
  the same clause - deliberately not "must state Z's value": the ambiguous
  denominator in the observed bug (South's own Rs 13.35 lakh decline) isn't
  itself a number anywhere in the findings object, only derivable by
  subtracting two others, so requiring it be *stated* would force the model
  to invent exactly the kind of number the validator exists to reject.
  Naming the *scope* in words removes the ambiguity without that trap.
  **Worked example replaced** with one built from SC-01's real findings
  object, correctly scoped, verified against the real (fixed) validator
  before committing it (see Change).
- **Change:** `engine/validator.py` - `_narration_sentences` (replaces
  `_narration_text_fields`, now carries `tier_from`), `_dimension_values`,
  `_names_a_segment`, `_headline_numbers`, `_exclude_by_magnitude`,
  `validate()` applies the per-sentence exclusion. `prompts/narrate.md` -
  new hard rule 8; worked example replaced. `engine/stages/s07_narrate.py` -
  new `_trim_for_narration()`: evidence deduplicated across drivers into one
  shared pool (Stage 05 attaches the *same* retrieved documents to every
  candidate driver - SC-01's two drivers sent the identical 6
  documents/snippets twice, 34% of the object, pure duplication) and
  `localization` trimmed to the top 2 non-suppressed rows (never referenced
  by the prompt at all). Applied only to the narrate LLM payload -
  `outcome_draft` itself, the schema-validated findings object, and
  `eval/metrics.py::evidence_recall_at_5`'s scoring input are all untouched,
  full detail. New tests in
  `tests/test_validator_blocks_invented_numbers.py`: the exact broken SC-01
  sentence now rejected, the correctly-scoped equivalent still passes, the
  headline field's exemption is explicit and tested.
- **Result:** `pytest` 12/12. Measured against the real SC-01 payload: 15,374
  → 9,934 chars (-35.4%). Re-ran SC-01 live (verbatim narration and the
  `force_live` regression this surfaced - see entry 021): **0 validator
  retries**, passed on the first attempt, `tokens_in=4094 tokens_out=1173
  cost=$0.02988` (down from the pre-trim probe's `tokens_in=4924
  tokens_out=1652 cost=$0.03955`). Headline stated the unscoped category
  movement with no segment named; the localization-sourced sentence named
  "the South segment's own decline" as its denominator in words, no
  fabricated number; zero internal contradiction. `schemas/findings.schema.json`
  validation: 0 errors.

## 021 — A resumable cache silently defeated the narrate retry loop's whole reason to exist
**Date:** 2026-08-30 · **Phase:** 5 · **Commit:** `21f6b3f`

- **Evidence:** Re-running SC-01 live to verify entry 020's fix (first
  attempt, under the new trimmed payload): `validator_retries=2`, final
  output was the *template* fallback, not a live narration - despite the
  log showing a live call genuinely succeeding on the first attempt. The
  narration text was literally `_template_answer`'s boilerplate
  ("The movement was driven by: <driver statement>"), not model prose.
- **Problem:** `engine/stages/s07_narrate.py`'s retry loop calls
  `llm_client.complete("narrate", payload, ctx=ctx)` with the *identical*
  `payload` on every attempt (same `outcome_draft`/persona - nothing in the
  loop changes it). `prompts/narrate.md` runs at `temperature: 0.2`
  specifically so a validator-rejected attempt has a real chance at a
  different result on retry - but entry 018's resumable-cache change
  (`complete()` checks the cache *before* deciding whether to go live) means
  an identical payload hashes to an identical cache key, so attempt 2
  "resumed" attempt 1's own just-written, already-rejected response instead
  of sampling again. Every attempt after the first was validating the exact
  same text against itself. A real regression, introduced by a fix built for
  a different purpose (batch-level resumability across separate runs) that
  never considered within-run retries of an intentionally-stochastic call.
- **Decision:** Give the caller a way to say "this exact retry needs a
  genuinely fresh sample, not the cache" - `complete()` gains
  `force_live: bool = False`, skipping the cache-hit branch only when both
  `force_live` and live mode are true (a no-op in replay/offline mode, so
  the offline/deterministic guarantee is untouched). `s07_narrate.py` passes
  `force_live=(attempt > 0)` - the first attempt still checks the cache
  (preserving batch resumability for a fresh scenario), every retry after it
  bypasses the cache entirely and overwrites the stale entry with whatever
  comes back, so a later resumed run picks up the response that ultimately
  passed validation, not the one that failed.
- **Change:** `engine/llm_client.py::complete()` (`force_live` parameter,
  `skip_cache_read` gate); `engine/stages/s07_narrate.py` (retry loop passes
  it); new `tests/test_llm_client_force_live.py` - asserts a second call
  with an identical payload resumes from cache by default, `force_live=True`
  forces a fresh live sample instead, and that fresh sample becomes what a
  later call resumes from (the overwrite, not just a bypass).
- **Result:** `pytest` 12/12. Deleted the one stale cache entry the broken
  run had written and re-ran SC-01 live: `validator_retries=0`, a genuine
  live narration on the first attempt (entry 020's Result). Found and fixed
  entirely by re-running the real thing live, immediately after landing a
  change meant to help - exactly the discipline `CLAUDE.md` asks this
  project to keep applying to itself, not just to the model's output.

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
