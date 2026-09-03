# Definition of Done

Tick as you go. **Commit this file daily** — its own git history becomes evidence
that the process was real.

Legend: `[Y]` Yuvraj · `[N]` Nikhil · `[B]` both · ⭐ never cut

---

## Phase 0 — freeze
- [x] `[B]` Repo created, kit committed
- [ ] `[B]` T-minus anchor filled in `docs/01_MASTER_BUILD_FLOW.md` *(deferred — no deadline set yet)*
- [ ] `[B]` Submission mechanics confirmed (deadline, page limits, video length,
      is the pitch live?)
- [x] ⭐ `[Y]` **Injection manifest committed before any engine code**
- [x] `[Y]` That commit hash recorded in README + CHANGELOG 001
- [x] `[B]` Data contract between your two halves written into the blueprint (`docs/02_BUILD_BLUEPRINT.md` §4 — `metric_row`/`document`/`evidence_ref` shapes; spot-checked this session against `schemas/findings.schema.json`'s `evidenceRef` def and `engine/stages/s05_retrieve.py`'s actual field construction, both match exactly)
- [ ] `[B]` `docs/00_SUBMISSION_STRATEGY.md` read by both of you

## Phase 1 — data
- [x] `[Y]` Generator: orders, sessions, spend, delivery, returns
- [x] `[Y]` Realistic seasonality *before* any planting
- [x] `[Y]` 17 scenarios planted — ramps, spillover, contaminated pre-period,
      one confounded rival
- [x] `[N]` ~490 documents, scruffy, with out-of-window decoys
- [x] `[N]` TCK-6666 (the injection document)
- [x] `[Y]` `make data` reproducible from seed; hashes recorded (`data/generated/DATA_HASHES.json`)
- [x] `[Y]` Planted effects are **not** obvious by eye (calibrated against measured noise, see ADR-0006)

## Phase 2 — contracts
- [x] `[Y]` Five contracts complete and validating
- [x] `[Y]` KPI graph compiles, cycle-checked, renders to `assets/` (SVG, not PNG — no plotting dep; see kpi_graph.py)
- [x] `[Y]` Catalogue built for intent parsing
- [x] `[N]` Context registry
- [x] `[Y]` A deliberately broken contract stops the app with a clear error (`ContractError`)

## Phase 3 — trust
- [x] `[Y]` Entitlements resolve to SQL predicates (verified by diffing SQL)
- [x] `[Y]` Small-cell suppression
- [x] `[N]` PII redaction at index time
- [x] `[N]` Injection flagging — flag and keep
- [x] `[Y]` Audit log writing
- [x] `[N]` Document index built (BM25 + embeddings, graceful degrade to BM25-only)

## Phase 4 — engine
- [x] `[Y]` s01 define · s02 detect · s03 localize · s04 decompose
- [x] `[N]` s05 retrieve — **window filter before scoring**
- [x] `[Y]` s06 falsify — diff-in-diff, placebo, controls, dose-response
- [x] ⭐ `[Y]` tiers.py + monotonicity test
- [x] ⭐ `[Y]` gate.py + invariant test
- [x] `[Y]` pipeline emits schema-valid findings
- [x] `[Y]` `--trace` flag (`python -m eval.trace SC-01`, writes `eval/traces/SC-01.md`) — `pipeline.run(..., trace=True)` is additive, every existing caller's return shape is unchanged; tested across all four branch types (answer, abstention, no_alert, clarification)
- [x] ⭐ `[Y]` SC-01 passes · ⭐ SC-08 abstains

## Phase 5 — narration + UI
- [x] `[Y]` llm_client single adapter + replay cache + call cap
- [x] `[Y]` s07 narrate
- [x] ⭐ `[Y]` validator + its test
- [x] `[Y]` s00 intent + clarification branch (SC-17)
- [x] `[Y]` Replay cache committed — **populated for real** (CHANGELOG 019-028). 18 narrate + 1 intent_parse entries, all genuine captures: 12 from Groq before its account-level quota blocked further calls, 7 from Gemini (with two real Gemini-specific bugs found and fixed: a thinking-token budget floor and JSON code-fence unwrapping) after. `eval/scorecard.md` is now the live-recorded scorecard, not the replay-only one; diffed byte-identical against a fresh `GLASSBOX_REPLAY=1` regeneration except the header commit hash, proving replay reproduces live exactly.
- [x] `[N]` Persona switcher · alert feed(-equivalent) · question box (`app/main.py` — sidebar persona override + scenario picker; functionally verified via headless `AppTest` across all 17 scenarios × 3 personas, zero exceptions — not yet browser-verified, see gaps below)
- [x] ⭐ `[N]` Tiered sentences · evidence drawer · action card (`app/main.py::render_findings`)
- [ ] `[N]` Progress narration during the run
- [ ] `[N]` Tier tooltips *(tier badges have a hover title with the gloss; not a dedicated tooltip UI)*
- [ ] `[N]` Pre-computed hero cache (SC-01, SC-08)
- [x] `[N]` Scenario picker (including failures) — sidebar dropdown over all 17
- [ ] `[N]` Three-channel render
- [ ] `[N]` "Try to break it" tab
- [ ] `[B]` Someone who has never seen it completes the tour unaided — **not yet done. The app is functionally verified (headless `AppTest` run across all 17 scenarios and 3 personas, zero exceptions) and now also visually verified: 11 real screenshots in `screenshots/` cover the home screen, SC-01's headline/evidence/rejected-cause views, SC-08's abstention, and SC-14's flagged injection — the earlier Chrome-tool-won't-connect gap is closed. What's still open is a blind user completing the tour with no prior exposure to the app.**

## Phase 6 — evidence
- [x] `[Y]` Harness + metrics
- [x] `[Y]` Scoring rules written **before** first run (docs/04_EVALUATION_PLAN.md predates the harness)
- [ ] `[Y]` RS benchmark, 7 published algorithms *(not run — see gaps below)*
- [x] `[Y]` **Thresholds frozen after the benchmark** (calibrated + committed, ADR-0006; ready to freeze at Phase 6 proper)
- [x] `[Y]` B1 baseline (`eval/baselines/b1_naive.py` + `run_all.py`, real, run: 2/15 exact match, asserts a cause on 3/3 unplanted scenarios vs GlassBox's 0/3)
- [x] ⭐ `[Y]` **B3 LLM-only baseline + the SC-08 comparison** — run live (`gpt-4o-mini` via OpenAI, after Groq's quota and Gemini's rate limit both blocked completion - CHANGELOG 026-027), not simulated: on SC-08 specifically, invented a specific cause with "I am reasonably confident in this assessment." 2/3 unplanted scenarios hallucinated a cause; GlassBox 0/3. Real quotes in `eval/baseline_scorecard.md`. *(Screenshot itself not taken — the quote is the evidence; a screenshot would just be a picture of the same text.)*
- [x] `[Y]` Cost receipt (`eval/cost_receipt.md`, generated from real live telemetry - `Mode: live`, real nonzero tokens, real $0.00 because both providers used were free-tier, not because no key was configured. Carries a correction for a real latency-measurement bug found this session - CHANGELOG 024.)
- [ ] `[Y]` CI green, scorecard auto-published
- [x] ⭐ `[Y]` **Scorecard committed with misses shown** (`eval/scorecard.md`, live-recorded: 7/15 exact-pass, 0/15 hallucinated causes, all 8 misses explained. SC-07 and SC-15 retired in place - `data/manifest_reconciliation.md` - not cut, not hidden: `magnitude_pct` was never verified against generated output for 12 of 14 planted scenarios, and these two specifically have a wrong scoring key, not just a wrong magnitude.)
- [ ] `[Y]` E3 negative-control suite · E5 ablations *(if time)*
- [ ] ⭐ `[B]` **`make reproduce` tested on the other person's machine (T−7)**

## Phase 7 — submission
- [ ] `[B]` **Code freeze at T−4** *(no deadline set yet — see Phase 0)*
- [x] `[N]` README rewritten user-first, no placeholders left *(real numbers throughout; a fabricated B3 transcript from the starter template was found and removed — see CHANGELOG)*
- [x] ⭐ `[Y]` REPRODUCE.md finalised — real measurements from this session (not yet a second-machine clean-room run, noted explicitly in the file)
- [x] `[Y]` TRAJECTORIES.md — SC-01, SC-08, SC-14, all real captured output
- [x] `[B]` JUDGES.md — placeholders filled, SC-12/UI mismatches corrected to match actual behavior
- [x] `[Y]` 5 ADRs *(0001-0005 pre-existing; ADR-0006 added this session)* · `[N]` build-vs-buy filled (one factual correction: seasonality is a custom dow×month×festival decomposition, not literal statsmodels.STL — see the table) · `[ ]` traceability matrix (22) not built
- [x] `[N]` Business proposal (`docs/09_BUSINESS_PROPOSAL.md`) — users, impact, roadmap, risks + mitigations; market-sizing numbers explicitly flagged as needing real customer discovery, not invented
- [x] `[B]` Deck — content-complete, published as an artifact (not literally the Round 1 PPT template file, which wasn't available to build against); every number/quote pulled from committed files
- [x] `[B]` Video **script** updated with real numbers/quotes (`docs/07_DEMO_AND_PITCH.md`) — **not recorded**, that step needs a person, a screen and a voice
- [ ] `[N]` Hosted demo live, warmed, checked on submission morning
- [ ] ⭐ `[B]` **Repo public · no secrets in history · no Olist data · clean commits** *(secrets-scanned clean this session; repo not yet made public — that's your call, not mine to make unilaterally)*
- [ ] `[B]` Two timed Q&A rehearsals, out loud
- [x] `[B]` CHANGELOG entries verified against `git log` this session
- [x] `[B]` Every ⟪FILL⟫ placeholder in README/JUDGES/REPRODUCE/TRAJECTORIES resolved

---

## The scope gate — T−10

Count green scenarios. **Under 13/17 → cut today**, in this order:

1. "Try to break it" tab → 2. Third persona → 3. Docker →
4. Three-channel live render (screenshot instead) → 5. SC-11, SC-12 →
6. SC-03, SC-09 (mark NOT IMPLEMENTED in the scorecard) → 7. Hosted demo →
8. B1 baseline

Record every cut in `CHANGELOG.md`.

**Green count at T−10: ______ / 17.   Cut: ______________________**

---

## Never cut — final check
- [ ] ⭐ SC-08 abstention works
- [ ] ⭐ `make reproduce` works from a clean clone
- [ ] ⭐ Scorecard committed, misses included
- [ ] ⭐ Tiers on every sentence
- [ ] ⭐ Number validator active and untouched
- [ ] ⭐ CHANGELOG written live, agreeing with `git log`
