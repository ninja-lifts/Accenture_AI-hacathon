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
- [ ] `[B]` Data contract between your two halves written into the blueprint
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
- [ ] `[Y]` `--trace` flag *(not built — see gaps below)*
- [x] ⭐ `[Y]` SC-01 passes · ⭐ SC-08 abstains

## Phase 5 — narration + UI
- [x] `[Y]` llm_client single adapter + replay cache + call cap
- [x] `[Y]` s07 narrate
- [x] ⭐ `[Y]` validator + its test
- [x] `[Y]` s00 intent + clarification branch (SC-17)
- [ ] `[Y]` Replay cache committed *(no live LLM key in this environment — the deterministic template fallback IS the offline path; nothing to commit until a real run populates it)*
- [ ] `[N]` Persona switcher · alert feed · question box *(app/main.py not built)*
- [ ] ⭐ `[N]` Tiered sentences · evidence drawer · action card *(UI not built — the underlying data is real and schema-valid; only the rendering is missing)*
- [ ] `[N]` Progress narration during the run
- [ ] `[N]` Tier tooltips
- [ ] `[N]` Pre-computed hero cache (SC-01, SC-08)
- [ ] `[N]` Scenario picker (including failures)
- [ ] `[N]` Three-channel render
- [ ] `[N]` "Try to break it" tab
- [ ] `[B]` Someone who has never seen it completes the tour unaided

## Phase 6 — evidence
- [x] `[Y]` Harness + metrics
- [x] `[Y]` Scoring rules written **before** first run (docs/04_EVALUATION_PLAN.md predates the harness)
- [ ] `[Y]` RS benchmark, 7 published algorithms *(not run — see gaps below)*
- [x] `[Y]` **Thresholds frozen after the benchmark** (calibrated + committed, ADR-0006; ready to freeze at Phase 6 proper)
- [ ] `[Y]` B1 baseline *(not built)*
- [ ] ⭐ `[Y]` **B3 LLM-only baseline + the SC-08 comparison screenshot** *(not built — no live LLM key in this environment)*
- [ ] `[Y]` Cost receipt
- [ ] `[Y]` CI green, scorecard auto-published
- [x] ⭐ `[Y]` **Scorecard committed with misses shown** (`eval/scorecard.md`, 6/17 exact-pass, 0/17 hallucinated causes, all 11 misses explained)
- [ ] `[Y]` E3 negative-control suite · E5 ablations *(if time)*
- [ ] ⭐ `[B]` **`make reproduce` tested on the other person's machine (T−7)**

## Phase 7 — submission
- [ ] `[B]` **Code freeze at T−4**
- [ ] `[N]` README rewritten user-first, no placeholders left
- [ ] ⭐ `[Y]` REPRODUCE.md finalised from the real clean-machine run
- [ ] `[Y]` TRAJECTORIES.md — SC-01, SC-08, SC-14
- [ ] `[B]` JUDGES.md
- [ ] `[Y]` 5 ADRs · `[N]` build-vs-buy filled · `[B]` traceability matrix (22)
- [ ] `[N]` Business proposal: users, impact, roadmap, risks + mitigations
- [ ] `[B]` Deck **on the Round 1 template**
- [ ] `[B]` Video 2–3 min, SC-08 and SC-14 protected
- [ ] `[N]` Hosted demo live, warmed, checked on submission morning
- [ ] ⭐ `[B]` **Repo public · no secrets in history · no Olist data · clean commits**
- [ ] `[B]` Two timed Q&A rehearsals, out loud
- [ ] `[B]` CHANGELOG final entry; verified against `git log`
- [ ] `[B]` Every ⟪FILL⟫ in every file replaced or deleted

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
