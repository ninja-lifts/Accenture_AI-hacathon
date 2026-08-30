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

## 022 — A third provider adapter, added under duress: Groq's account-level rate limit forced Gemini, which surfaced three more real quirks
**Date:** 2026-08-30 · **Phase:** 6 · **Commit:** `0d48e68`

- **Evidence:** Three different Groq keys 429'd on the very first live call
  each, in a tight window - not a per-key exhaustion pattern, an
  account-level (or IP-level) one that swapping keys can't route around.
  Rather than wait on an unknown reset window, added Gemini as a third
  provider (Google AI Studio's `generateContent` REST API) - proving the
  vendor-neutral design a second time, the same way entry 008 added Groq
  alongside Anthropic. Every one of the three quirks below was found by
  actually calling the real endpoint, not anticipated in advance.
- **Problem, one:** the configured model (`gemini-2.0-flash`) is no longer
  available - the API's own 404 named the replacement
  (`gemini-3.6-flash`). **Two:** that model thinks by default with no
  documented way to turn it off - `generationConfig.thinkingConfig:
  {thinkingBudget: 0}` is rejected outright with a 400 - and a trivial
  one-word prompt still spent 90 tokens on `thoughtsTokenCount` before the
  visible answer; under a normal `max_output_tokens` budget the entire
  allowance goes to thinking and the visible response comes back empty
  (`finishReason: MAX_TOKENS`, `content: {}`) - the identical failure shape
  Groq's `gpt-oss-120b` has (entry 008/009). **Three:** even with
  `responseMimeType: "application/json"` set, a real narrate-shaped call
  returned the JSON wrapped in a markdown code fence with prose *after* it
  ("Let's count sentences: exactly 7 sentences in the `sentences` array.") -
  `json.loads` would have failed on that verbatim, indistinguishable from a
  genuine parse failure. **Four, found only after fixing three:** the
  now-parseable response used `tier_from: "answer.localization[0]"`, not
  the `drivers[0]` convention `prompts/narrate.md`'s worked example shows -
  a reasonable pointer into the same findings object, just not the one
  exact string entry 020's scope-check regex matched, which meant that
  specific safety net silently would not have engaged for a Gemini
  response making the same misattribution mistake it exists to catch.
- **Decision:** Fix all four for real, not route around them.
  `_call_live_gemini` budgets generously (`max(declared*3, declared+2000)`,
  same formula as Groq's reasoning-model bump - a matching failure mode
  gets the matching fix) since disabling thinking isn't available.
  JSON-fence unwrapping is scoped narrowly to the Gemini adapter itself
  (strip a leading fence, take the first complete JSON value via
  `json.JSONDecoder.raw_decode` - which naturally ignores anything trailing
  it, no need to locate a closing fence) and falls back to the original
  text unchanged if it doesn't apply, so a genuinely broken response still
  goes through `s07_narrate.py`'s existing, already-tested
  retry/raise-loudly path rather than a new one. The `tier_from` fix is
  the opposite of narrow on purpose: broadened
  `engine/validator.py`'s pattern from `drivers[N]` alone to
  `(?:answer\.)?(?:drivers|localization|decomposition)\[N\]`, since the
  underlying misattribution risk is the same regardless of which per-segment
  array a model's pointer happens to name, or whether it prefixes `answer.` -
  general to the *shape* of a reasonable pointer, not to one provider's
  specific string.
- **Change:** `engine/llm_client.py` - `_call_live_gemini` (new adapter,
  registered in `_LIVE_ADAPTERS`), `_clean_gemini_json_text` (fence-stripping,
  provider-scoped). `engine/validator.py` - `_DRIVER_TIER_FROM_RE` renamed
  `_SEGMENT_TIER_FROM_RE`, broadened pattern, docstrings updated. New test:
  `test_localization_pointer_tier_from_also_rejects_unscoped_headline_numbers`.
  `.env` (not committed - gitignored): `GLASSBOX_LLM_PROVIDER=gemini`,
  `GLASSBOX_LLM_MODEL=gemini-3.6-flash`.
- **Result:** `pytest` 13/13. Verified end to end against SC-01's real
  outcome_draft (bypassing `complete()`'s cache so the existing good Groq
  capture wasn't overwritten): clean, valid JSON; headline stated the
  unscoped category movement; the localization-sourced sentence correctly
  used South's own Rs 27.24 lakh / 77.8% - not the headline's Rs 35 lakh /
  23.5% - despite using the `answer.localization[0]` pointer convention the
  original entry-020 regex would have missed. `tokens_in=4883
  tokens_out=113 cost=$0.01634` (Gemini's own thinking tokens aren't
  separately billed-reported here - `candidatesTokenCount` only, matching
  what the API itself calls the visible-output count). One live regression
  cost real money to find and fix (~$0.05 across the Gemini probes in this
  entry) - disclosed, not hidden, per this file's own rules.

## 023 — Gemini's thinking-token budget needed a flat floor, not just a multiplier
**Date:** 2026-08-30 · **Phase:** 6 · **Commit:** `58e8f4c`

- **Evidence:** Running SC-04 live (not the trivial one-word test entry 022
  was verified against): the response truncated mid-string -
  `"text": "wide Audio downturn hypothesis..."` with no closing quote, no
  closing braces. `tokens_out=111` against a 2,900-token
  `maxOutputTokens` budget (`max(900*3, 900+2000)`, entry 022's formula).
- **Problem:** Thinking-token consumption is not proportional to the
  declared output size the way the multiplier formula assumed. A trivial
  "reply with one word" prompt spent 90 thinking tokens; a real,
  moderately-complex narrate prompt spent roughly 2,700-2,800 of the same
  2,900-token budget, leaving 111 tokens for the actual answer and cutting
  it off mid-generation - genuinely incomplete JSON, a different failure
  from the fenced-wrapper case entry 022's `_clean_gemini_json_text`
  handles. Both retry attempts (the first live, the second via `force_live`)
  hit this identically, exhausting the retry budget and correctly raising
  `RuntimeError` rather than silently falling back to the template - the
  entry 013/014 guard working exactly as designed, on a failure mode from a
  provider that did not exist when it was written. Side effect: the
  truncated response got cached (writes are unconditional on any live
  response, valid or not), and a later `pytest` run in replay mode
  correctly refused to silently accept the corrupted cached text as a valid
  narration - not a new bug, the schema-validation test doing its job on
  cache content this session's own experimentation had corrupted.
- **Decision:** Raise the budget with a large flat floor
  (`max(declared*3, declared+2000, 8000)`) rather than a bigger multiplier
  alone, since thinking cost does not scale simply with the declared output
  size. Deleted the one corrupted cache entry rather than leave it for a
  future run to trip over.
- **Change:** `engine/llm_client.py::_call_live_gemini` - budget floor
  raised to 8,000 tokens; docstring records the real measured ratio.
- **Result:** `pytest` 13/13 after deleting the corrupted entry. Re-ran
  SC-04 live: complete, valid JSON, correct branch (`answer`), `tokens_in=3933
  tokens_out=628`. `pass=False` on localization precision only (same benign
  miss category as SC-05/SC-10/SC-11/SC-14/SC-16 throughout this project's
  history) - not a validator or parsing failure.

## 024 — The only two stages that ever make an LLM call were the only two never timed
**Date:** 2026-08-30 · **Phase:** 6 · **Commit:** `e67f8ab`

- **Evidence:** The live batch's own `eval/cost_receipt.md` reported
  `latency p50/p95 = 1,078ms/1,927ms`. The same batch's raw harness logs
  show real per-call elapsed times of 25,000-91,000ms. A forty-to-fifty-fold
  discrepancy, not a rounding difference.
- **Problem:** `telemetry.total_ms` is `sum(stage_timings_ms.values())`,
  nothing else. `engine/stages/s01_define.py` through `s06_falsify.py` - six
  of eight stages - wrap their `run()` body in
  `engine/telemetry.py::stage()`. `s00_intent.py` and `s07_narrate.py` - the
  *only two stages in the whole pipeline that ever call
  `llm_client.complete()`* - never did, for the project's entire history.
  Invisible in replay mode, where a cache read is near-instant regardless of
  whether it's timed, which is exactly why nobody had caught it before this
  session ran the pipeline live and actually looked at real per-call timing
  against what the receipt claimed.
- **Decision:** Wrap both. `s00_intent.py`'s existing early return for a
  non-`user_question` trigger stays outside the wrap (most scenarios never
  touch this stage at all; recording a near-zero entry for all of them
  would be a different, unrequested behaviour change). `s07_narrate.py`
  wraps unconditionally, matching the six baseline stages, since it runs
  for every branch regardless of whether an LLM call happens.
- **Change:** `engine/stages/s00_intent.py`, `engine/stages/s07_narrate.py`
  (both wrapped), `engine/telemetry.py::stage()` (docstring records why this
  matters for every future stage). `eval/cost_receipt.md` - a correction
  appended under the already-generated live numbers, not a rewrite of them
  (this file's own rule: never edit an old entry to look better).
- **Result:** `pytest` 13/13. Verified structurally in replay mode:
  `07_narrate` now appears in `stage_timings_ms` with a realistic 3.5ms for
  a cache-hit read - not conflated with `05_retrieve`'s 18.7s
  first-process embedding-model load, which had been the only other large
  number in the same breakdown. A future live run's cost receipt will
  report genuine end-to-end latency; this session's already-recorded one
  carries the real number as a correction instead (entry 025).

## 025 — First full live recording: 15 scored scenarios, two providers, one Groq quota wall
**Date:** 2026-08-30 · **Phase:** 6 · **Commit:** `8e650ce`

- **Evidence:** Three different Groq API keys 429'd on the first live call
  each (entry 022) - consistent with an account-level free-tier quota
  (`openai/gpt-oss-120b`: 8K TPM confirmed empirically and matching Groq's
  published limit, but also 200K tokens/day, shared across keys on the same
  account) rather than a per-key one. Recording the full batch meant
  finishing on Gemini rather than waiting on an unknown reset window.
- **Problem:** Nothing left to fix by this point - entries 022-024 already
  closed the real gaps (JSON fencing, thinking-token budget, latency
  timing). This entry is the actual deliverable those existed to produce:
  a genuine, complete, live-recorded run of the 15 non-retired scenarios.
- **Decision:** Record what's real rather than force single-provider
  purity. 12 of 19 total live calls this session are Groq-sourced (from
  before the quota wall), 7 are Gemini-sourced (after) - the replay cache
  is keyed by `(prompt_id, prompt_version, payload_hash)`, not by provider,
  and a captured response is real evidence regardless of which real
  provider produced it. Scenarios already validly cached from Groq
  (SC-01, SC-06, SC-08, SC-09, SC-13) were not re-called on Gemini just for
  uniformity - that would spend real quota to replace a real capture with
  another real capture, for no evidentiary gain.
- **Change:** `eval/replay_cache/narrate/` (18 entries) and
  `eval/replay_cache/intent_parse/` (1 entry, SC-17) committed.
  `eval/scorecard.md`, `eval/cost_receipt.md` regenerated from the real run.
- **Result:** **7/15 pass, 0/15 hallucinated causes** - the headline number
  holds under real live narration, not just replay-mode template rendering.
  All 8 misses are imprecise-localization or conservative-abstention, the
  same benign categories this project has shown throughout; nothing new or
  concerning surfaced by finally going live end to end. 19 real calls
  total this session: 71,341 input + 21,688 output tokens. Real dollar
  cost: **$0** (both providers' free tiers - genuinely, not a rounding of
  something small). Illustrative cost per `engine/telemetry.py`'s
  placeholder rate (not a provider invoice - see that file's own docstring):
  $0.5393 combined. Next: B3 baseline, live.

## 026 — A fourth provider, added the same day: OpenAI, when Gemini's rate limit didn't clear on retry
**Date:** 2026-08-30 · **Phase:** 6 · **Commit:** `1428e61`

- **Evidence:** B3 (no caching, no per-scenario error recovery - entry 018's
  known gap) hit a Gemini 429 on its third call (SC-03), exhausted 5 retry
  attempts, and crashed the whole batch. A wait and a full retry from
  scratch 429'd again, this time immediately on the *first* call
  (SC-01) - worse than before, not better. Google's rate-limit docs don't
  publish exact per-model free-tier numbers for a preview model like
  `gemini-3.6-flash`; they're visible only on the account's own AI Studio
  dashboard, which wasn't available to check from here.
- **Problem:** Two providers' free tiers were now both blocking completion
  of the same task for different reasons (Groq: an account-level quota;
  Gemini: a rate limit that didn't visibly reset within a reasonable wait).
  Continuing to guess at wait durations against undocumented limits wasn't
  a productive use of either the session's time or its budget of real
  calls.
- **Decision:** Add OpenAI as a fourth provider rather than keep waiting.
  No new adapter function needed - OpenAI's Chat Completions API is what
  Groq's adapter already imitates (Rule 6's "provider is config, not code"
  claim, now demonstrated a third time). Verified the real narrate-shaped
  path before running anything at scale, the same discipline applied to
  Gemini: real SC-01 payload, `_call_live` called directly so the existing
  good capture wasn't touched.
- **Change:** `engine/llm_client.py` - `_OPENAI_COMPATIBLE_ENDPOINTS` (a
  provider-aware default instead of the hardcoded Groq URL),
  `"openai": _call_live_openai_compatible` registered in `_LIVE_ADAPTERS`.
- **Result:** Clean on the first real test: valid JSON with no markdown
  fencing, `reasoning_tokens: 0` (not a thinking model, unlike Gemini - no
  budget-floor workaround needed), 5.8s latency (vs Gemini's 25-91s), and
  it followed `prompts/narrate.md`'s `tier_from` convention exactly
  (`drivers[0]`, `decomposition`) rather than Gemini's structurally-valid
  but divergent `answer.localization[0]` (entry 022). One honest caveat for
  the record: unlike Groq/Gemini's free tiers, OpenAI bills real money, and
  `engine/telemetry.py`'s cost estimate is still the generic illustrative
  rate, not `gpt-4o-mini`'s actual price - the first provider this project
  has used where the receipt's "cost" column is not incidentally accurate.

## 027 — First complete live B3 baseline: 14/15 scenarios, zero errors, the SC-08 comparison landed for real
**Date:** 2026-08-30 · **Phase:** 6 · **Commit:** `9f9bce4`

- **Evidence:** Ran `--baseline` against all 15 non-retired scenarios via
  OpenAI. Zero 429s, zero retries, zero crashes - the cleanest of the three
  providers tried this session, on the one baseline run that has no
  per-scenario error recovery to fall back on if a single call fails.
- **Problem:** None - this entry is the deliverable entries 008 (which
  first added a live B3 run, on Groq) and 026 existed to produce: a
  genuine, complete, live B3 comparison against the current engine and
  manifest, not a partial or simulated one.
- **Decision:** Record the real run rather than wait for single-provider
  purity across every artefact this session touched (entry 025 already
  established this precedent for the main scorecard).
- **Change:** `eval/baseline_scorecard.md` regenerated from the live run.
- **Result:** **The comparison this project's pitch depends on, landed with
  a real model, today's manifest, today's engine.** On SC-08 (a real,
  material movement with nothing planted - the negative control), B3
  confidently invents a specific cause: *"issues with product returns due
  to packaging problems and a shift in the app's order composition...
  I am reasonably confident in this assessment."* GlassBox's own SC-08 row
  (`eval/scorecard.md`) abstains. 2/15 scenarios where B3 asserted a cause
  on an unplanted movement without hedging (SC-02, SC-08). B1: 2/15 exact
  segment match, 3/15 scenarios asserting a cause on an unplanted movement.
  Both baselines now real for the current live-recorded scorecard, not
  carried over from an earlier engine/manifest state.

## 028 — Three disclosed-but-deferred bugs from the live recording session, fixed
**Date:** 2026-08-30 · **Phase:** 6 · **Commit:** `2b1a602`

- **Evidence:** All three were found and explicitly deferred during entries
  022-027 rather than fixed mid-task. (1) B3's Gemini run crashed entirely
  on a single scenario's 429 (entry 026), losing two already-real answers.
  (2) A truncated Gemini response got cached before its budget fix landed
  (entry 023), and a `pytest` run in replay mode correctly refused to treat
  the corrupted text as valid - the right behaviour, but only by luck of a
  test happening to cover that exact cache entry. (3)
  `eval/metrics.py::rca_top1` was noted as dead code while auditing what's
  actually a scoring key (entry 019).
- **Problem:** (1) `eval/baselines/run_all.py::main()` has no per-scenario
  error recovery, unlike `eval/harness.py`'s main loop - a live-call
  failure anywhere in the batch loses every result before it, not just the
  one scenario that failed. (2) `engine/llm_client.py::complete()` writes
  a live response to cache unconditionally; nothing stops a response that
  doesn't even parse as JSON from being persisted as if it were a usable
  capture, ready to poison a *future* run via the resumable-cache path
  (entry 018) rather than just failing loudly once. (3) A function keyed on
  `true_cause_id` sitting in `eval/metrics.py`'s public surface implies
  root-cause-id scoring happens somewhere it doesn't, which is exactly the
  kind of mismatch between what a file claims and what it does this
  project's entire changelog exists to catch.
- **Decision:** Fix all three for real now rather than continue deferring
  them past the session that found them. (1) Wrap the per-scenario body in
  `try/except`, matching the main harness's existing pattern exactly - a
  failure becomes an `ERROR: ...` row, the batch continues. (2) Use the
  `json_mode` parameter `complete()` already had but never read: when true
  (every current prompt's default), a response that fails `json.loads` is
  still returned to the caller normally - its own retry/error handling is
  unaffected - but is not written to `eval/replay_cache/`. (3) Delete
  `rca_top1()`; keep the metric name documented in the module docstring,
  pointing at where it's actually computed (`eval/harness.py`'s inline
  `true_segment` check - there is nothing a `true_cause_id`-keyed function
  could check, since the engine never sees the generator's internal cause
  ids by design).
- **Change:** `eval/baselines/run_all.py` (try/except per scenario, error
  count in the totals line). `engine/llm_client.py::complete()`
  (`json_mode`-gated cache write; docstring). `eval/metrics.py` (`rca_top1`
  removed, docstring updated). `tests/test_llm_client_force_live.py` -
  existing fixtures switched from plain strings to valid JSON (fix 2 would
  otherwise have silently stopped caching the test's own fake responses -
  caught by running the suite, not anticipated), new test asserting an
  unparseable response is returned to the caller but never written to disk.
- **Result:** `pytest` 14/14. Replay-mode `eval/scorecard.md` regenerated
  and diffed against the committed live version: byte-identical except the
  header commit hash - none of these three fixes touch scoring or the
  offline path, confirmed rather than assumed.

## 029 — Judge-facing docs drifted from reality again, same class of gap entry 011 already fixed once
**Date:** 2026-08-30 · **Phase:** 7 · **Commit:** `1bc3339`, `f22c4e7`

- **Evidence:** Checking `CHECKLIST.md`'s open items against what this
  session actually did (per the task at hand: "build it completely") found
  a list of unticked-but-now-true and ticked-but-now-stale rows: the replay
  cache row still said "not currently populated" after entries 019-028
  populated it; the cost-receipt row still said "honestly $0.00, no live
  key configured" after entry 025 recorded a genuine live run; the B3 row
  still named Groq/`gpt-oss-120b` after entries 026-027 moved to
  OpenAI/`gpt-4o-mini`. Grepping README/JUDGES/REPRODUCE/TRAJECTORIES/the
  pitch script/the business proposal for the same patterns found the
  identical drift spread across every judge-facing doc - the exact failure
  mode entry 011 diagnosed and fixed once already ("nothing enforces that
  judge-facing prose docs track the code/eval state they describe"),
  recurring for the same structural reason: these files aren't part of the
  CHANGELOG/CHECKLIST loop that stays current as a matter of process.
  Separately, verifying `make reproduce` actually runs on this machine
  found `make` itself is not installed (confirmed: `which make` empty, no
  WSL) - a real gap in the literal promise `Makefile`'s own first line
  makes ("if it breaks, the submission breaks") - though a compatible
  `mingw32-make.exe` turned out to already be on `PATH` from an unrelated
  MinGW install.
- **Problem:** A judge who reads `eval/scorecard.md` and then `README.md`
  would see two different pass counts (7/15 vs a stale 7/17) and two
  different B3 providers. `JUDGES.md`'s and `TRAJECTORIES.md`'s biggest
  single claims - "the default clone runs the template narrator, not the
  live one" - described a real, honestly-disclosed gap that this session's
  own work (entries 019-028) had already closed, making an honest
  disclosure into a stale, now-inaccurate one if left alone.
- **Decision:** Fix the specific stale passages, the same discipline entry
  011 used - not a wholesale rewrite, and not silently correcting numbers
  without saying what changed and why (`JUDGES.md`'s rewritten section
  keeps the old gap's history rather than deleting it, since a judge who
  remembers the earlier version deserves to see it was real and got fixed,
  not memory-holed). `make baseline` gets the same `GLASSBOX_REPLAY=1`
  force `make eval` already had (entry 018) - the same billing-surprise
  risk, just not caught until auditing every judge-facing claim against
  current reality surfaced it. `mingw32-make` is documented as a fallback,
  not treated as a full fix - most judges on Windows won't have MinGW
  installed either, so the manual per-target commands remain the primary
  documented path.
- **Change:** `Makefile` (`baseline` forces replay; new `baseline-live`
  target). `CHECKLIST.md`, `JUDGES.md`, `README.md`, `REPRODUCE.md`,
  `TRAJECTORIES.md`, `docs/07_DEMO_AND_PITCH.md`,
  `docs/09_BUSINESS_PROPOSAL.md` - scorecard numbers, B3 provider/quotes,
  provider-adapter count, replay-cache status, and the `--trace`-flag /
  empty-cache claims that predated entries 012 and 019-028.
- **Result:** `pytest` 14/14 (docs-only changes don't touch code paths, but
  the Makefile fix does - reran to confirm regardless). Every number now
  quoted in a judge-facing doc was re-verified against a currently
  committed file before being written, not copied forward from an earlier
  pass or reconstructed from memory - `eval/baseline_scorecard.md`'s exact
  current SC-08 quote was re-read and pasted verbatim into README.md and
  JUDGES.md, not paraphrased from the old Groq version.

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
