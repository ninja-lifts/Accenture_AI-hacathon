# Definition of Done

Tick as you go. **Commit this file daily** — its own git history becomes evidence
that the process was real.

Legend: `[Y]` Yuvraj · `[N]` Nikhil · `[B]` both · ⭐ never cut

---

## Phase 0 — freeze
- [ ] `[B]` Repo created, kit committed
- [ ] `[B]` T-minus anchor filled in `docs/01_MASTER_BUILD_FLOW.md`
- [ ] `[B]` Submission mechanics confirmed (deadline, page limits, video length,
      is the pitch live?)
- [ ] ⭐ `[Y]` **Injection manifest committed before any engine code**
- [ ] `[Y]` That commit hash recorded in README + CHANGELOG 001
- [ ] `[B]` Data contract between your two halves written into the blueprint
- [ ] `[B]` `docs/00_SUBMISSION_STRATEGY.md` read by both of you

## Phase 1 — data
- [ ] `[Y]` Generator: orders, sessions, spend, delivery, returns
- [ ] `[Y]` Realistic seasonality *before* any planting
- [ ] `[Y]` 17 scenarios planted — ramps, spillover, contaminated pre-period,
      one confounded rival
- [ ] `[N]` ~490 documents, scruffy, with out-of-window decoys
- [ ] `[N]` TCK-6666 (the injection document)
- [ ] `[Y]` `make data` reproducible from seed; hashes recorded
- [ ] `[Y]` Planted effects are **not** obvious by eye

## Phase 2 — contracts
- [ ] `[Y]` Five contracts complete and validating
- [ ] `[Y]` KPI graph compiles, cycle-checked, renders to `assets/`
- [ ] `[Y]` Catalogue built for intent parsing
- [ ] `[N]` Context registry
- [ ] `[Y]` A deliberately broken contract stops the app with a clear error

## Phase 3 — trust
- [ ] `[Y]` Entitlements resolve to SQL predicates (verified by diffing SQL)
- [ ] `[Y]` Small-cell suppression
- [ ] `[N]` PII redaction at index time
- [ ] `[N]` Injection flagging — flag and keep
- [ ] `[Y]` Audit log writing
- [ ] `[N]` Document index built

## Phase 4 — engine
- [ ] `[Y]` s01 define · s02 detect · s03 localize · s04 decompose
- [ ] `[N]` s05 retrieve — **window filter before scoring**
- [ ] `[Y]` s06 falsify — diff-in-diff, placebo, controls, dose-response
- [ ] ⭐ `[Y]` tiers.py + monotonicity test
- [ ] ⭐ `[Y]` gate.py + invariant test
- [ ] `[Y]` pipeline emits schema-valid findings
- [ ] `[Y]` `--trace` flag
- [ ] ⭐ `[Y]` SC-01 passes · ⭐ SC-08 abstains

## Phase 5 — narration + UI
- [ ] `[Y]` llm_client single adapter + replay cache + call cap
- [ ] `[Y]` s07 narrate
- [ ] ⭐ `[Y]` validator + its test
- [ ] `[Y]` s00 intent + clarification branch (SC-17)
- [ ] `[Y]` Replay cache committed
- [ ] `[N]` Persona switcher · alert feed · question box
- [ ] ⭐ `[N]` Tiered sentences · evidence drawer · action card
- [ ] `[N]` Progress narration during the run
- [ ] `[N]` Tier tooltips
- [ ] `[N]` Pre-computed hero cache (SC-01, SC-08)
- [ ] `[N]` Scenario picker (including failures)
- [ ] `[N]` Three-channel render
- [ ] `[N]` "Try to break it" tab
- [ ] `[B]` Someone who has never seen it completes the tour unaided

## Phase 6 — evidence
- [ ] `[Y]` Harness + metrics
- [ ] `[Y]` Scoring rules written **before** first run
- [ ] `[Y]` RS benchmark, 7 published algorithms
- [ ] `[Y]` **Thresholds frozen after the benchmark**
- [ ] `[Y]` B1 baseline
- [ ] ⭐ `[Y]` **B3 LLM-only baseline + the SC-08 comparison screenshot**
- [ ] `[Y]` Cost receipt
- [ ] `[Y]` CI green, scorecard auto-published
- [ ] ⭐ `[Y]` **Scorecard committed with misses shown**
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
