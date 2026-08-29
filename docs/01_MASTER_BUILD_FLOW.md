# Master Build Flow — one sequence, top to bottom

**This file is the plan.** `CLAUDE.md` points here; every session starts by
reading the current phase. Eight phases, each ending in a **gate** with an
explicit pass condition. Do not enter a phase before the previous gate is green.

---

## Set your anchor before you do anything else

Everything below is **T-minus**. Fill this in once, here, and commit it:

```
T−0  (submission deadline)  =  ____________   ← set this
T−0  time of day / timezone =  ____________
Submission mechanics        =  repo link + demo video + deck  (confirm page limits,
                               video length, whether the pitch is live)
```

**Default assumption used throughout: a 21-day build.** If your real window is
shorter, do not compress everything proportionally — apply the compression ladder
in §9 *at the start*, decide what you are not building, and write it down. A
scope decision made on day one is a plan; the same decision made at T−2 is a
disaster.

**Owners:** `[Y]` Yuvraj — engine, data, evaluation. `[N]` Nikhil — retrieval,
UI, business proposal. `[B]` both.

---

## Phase 0 — Repo, freeze, and the pre-registration commit
**T−21 · ~2 hours · `[B]`**

The shortest phase and the one with the most permanent consequences.

- [ ] `[B]` Create the repo (private for now), clone locally
- [ ] `[B]` Drop in this starter kit: `CLAUDE.md`, `docs/`, `schemas/`,
      `contracts/`, `prompts/`, `engine/`, `eval/`, `app/`, `tests/`,
      `Makefile`, `requirements.txt`, `.gitignore`, `.env.example`, `LICENSE`
- [ ] `[Y]` `python -m venv .venv` → activate → `make setup`
- [ ] `[B]` Fill in the T-minus anchor above
- [ ] `[B]` Read `docs/00_SUBMISSION_STRATEGY.md` once, together, out loud if
      that is what it takes. It is the only doc that explains *why* the rest is
      shaped this way.
- [ ] `[Y]` **Commit `data/injection_manifest.yaml` now, before any engine code.**
      Commit message: `data: freeze injection manifest (pre-registration)`
- [ ] `[Y]` Record that commit hash in `README.md` and in `CHANGELOG.md` entry 001
- [ ] `[B]` Agree the data contract between your halves: the exact column names
      the generator emits and the exact document-record shape retrieval consumes.
      **Write it in `docs/02_BUILD_BLUEPRINT.md` §Module map.** This one
      conversation is what stops you blocking each other for three weeks.

> ### GATE 0
> `git log` shows the manifest commit **before** any file under `engine/` exists.
> Both of you can state, without looking, what the three output branches are.
> `CHANGELOG.md` has its first entry.
>
> *Why this gate is first: it is the only thing in the entire build that cannot
> be done later. Everything else can be rescued; this cannot.*

---

## Phase 1 — Meridian: the data and the planted truth
**T−20 → T−18 · ~2 days · `[Y]` lead, `[N]` on documents**

- [ ] `[Y]` `data/generate.py`: orders, sessions, marketing spend, delivery
      events, returns. Seeded. 12 months of history to 2026-08-21.
- [ ] `[Y]` Realistic baseline behaviour first — day-of-week, month, a festival
      calendar, and a slow organic trend. **Get the boring part right before
      planting anything**; a detector tuned on unrealistic noise is worthless.
- [ ] `[Y]` Plant every scenario from the manifest, obeying the four honesty
      rules: **ramps not steps**, **partial spillover**, **contaminated
      pre-period**, **one confounded rival cause** (SC-01).
- [ ] `[N]` Generate ~490 documents: support tickets, CRM notes, field reports,
      change-log entries, vendor emails. Mixed quality — typos, half-sentences,
      duplicates, and irrelevant chatter. **Clean, well-written tickets make
      retrieval look better than it is.**
- [ ] `[N]` Plant the manifest's evidence documents, plus decoys: documents that
      match a query's keywords but sit outside the movement window (this is the
      SC-08 bait).
- [ ] `[N]` Write `TCK-6666`, the injection document (SC-14).
- [ ] `[Y]` `make data` builds `meridian.duckdb`; record file hashes in the
      manifest header.
- [ ] `[Y]` Sanity notebook or script: plot each KPI, eyeball that the planted
      effects are visible but not cartoonish.

> ### GATE 1
> `make data` from a clean checkout produces a byte-identical dataset from the
> committed seed. A human looking at a plot of `net_revenue` for the South cannot
> immediately point at SC-01 — if the planted effect is obvious to the naked eye,
> it is too strong and the benchmark is trivial. **Turn it down until it is
> genuinely hard, then leave it alone forever.**

---

## Phase 2 — Contracts and the KPI graph
**T−18 → T−16 · ~1.5 days · `[Y]`**

- [ ] `[Y]` Complete the four stub contracts against `net_revenue.yaml`
- [ ] `[Y]` `engine/contracts.py` — load, validate against the schema, fail loudly
- [ ] `[Y]` `engine/kpi_graph.py` — compile `drivers[].depends_on` into a DiGraph,
      detect cycles at startup, expose `issue_tree()`
- [ ] `[Y]` `render_png()` → `assets/kpi_graph.png` for the deck and README
- [ ] `[Y]` `build_catalogue()` — the vocabulary intent parsing is limited to
- [ ] `[N]` Context registry: a small YAML of planned interventions (promos,
      price changes, releases) that Stage 02 consults to suppress escalation

> ### GATE 2
> All five contracts validate. The graph renders. A deliberately broken contract
> (delete a required field) stops the app with a clear error rather than
> degrading. **The "knowledge graph / ontology" line in the brief is now answered
> by an artefact rather than a claim** — and you did not build a graph database
> to do it.

---

## Phase 3 — The trust layer
**T−16 → T−14 · ~1.5 days · `[Y]` entitlements, `[N]` redaction/index**

Deliberately *before* the engine. If access control is retrofitted, it ends up as
a UI filter, and a judge will catch that in one question.

- [ ] `[Y]` `engine/entitlements.py` — resolve persona → row predicate, column
      treatment, `min_cell_size`, `entitlements_hash`
- [ ] `[Y]` Predicates are pushed **into the SQL**. Verify by logging generated
      SQL for two personas and diffing it.
- [ ] `[Y]` `suppress_small_cells()` (SC-15)
- [ ] `[N]` `engine/redaction.py` — PII masking at index time
- [ ] `[N]` Injection flagging: flag and **keep**, never silently drop (SC-14)
- [ ] `[Y]` `engine/audit.py` — append-only JSONL, one line per run
- [ ] `[N]` Build the document index (BM25 + embeddings, in memory)

> ### GATE 3
> Two personas, same question, provably different SQL and different
> `entitlements_hash`. A document containing an injection string is indexed,
> flagged, and still retrievable. The audit log has entries. **Say out loud to
> each other: "is this real access control, or a filter?" If anyone hesitates,
> it is a filter — fix it now, not in week three.**

---

## Phase 4 — The engine
**T−15 → T−9 · ~5 days · `[Y]` lead, `[N]` on Stage 05**

The largest phase. Build the stages in order; each one runnable and testable on
its own before the next.

- [ ] `[Y]` `s01_define` — contract SQL + entitlement predicates → series
- [ ] `[Y]` `s02_detect` — seasonal baseline, residual control chart, dual
      materiality, registry suppression *(SC-02, SC-03, SC-11 depend on this)*
- [ ] `[Y]` `s03_localize` — multi-dimensional attribution + small-cell
      suppression *(this is the stage with external baselines — see Phase 6)*
- [ ] `[Y]` `s04_decompose` — price / volume / mix along graph edges;
      **assert the components sum to the movement** *(SC-05)*
- [ ] `[N]` `s05_retrieve` — hybrid BM25 + embeddings, entitlement-filtered,
      **window-filtered before scoring** *(the SC-08 decoys defeat you otherwise)*
- [ ] `[Y]` `s06_falsify` — difference-in-differences, placebo timing, control
      segments, dose-response, pre-period contamination check
- [ ] `[Y]` `engine/tiers.py` — the rule table; `tests/test_tiers_monotone.py`
- [ ] `[Y]` `engine/gate.py` — answer / abstain / clarify;
      `tests/test_gate_invariant.py`
- [ ] `[Y]` `engine/pipeline.py` — orchestrate; emit a schema-valid findings object
- [ ] `[Y]` `--trace` flag emitting a readable markdown trace *(feeds
      `TRAJECTORIES.md`; build it now, it costs an hour here and a day later)*

> ### GATE 4
> The pipeline produces a schema-valid findings object for SC-01 **and** SC-08,
> with no LLM involved yet (template narration is fine). SC-08 abstains. The
> three protected tests pass.
>
> **This is the real halfway point of the project.** If you are past T−9 and this
> gate is not green, go to §9 and cut something today.

---

## Phase 5 — Narration and the interface
**T−10 → T−6 · ~3.5 days · `[N]` lead UI, `[Y]` on narration**

- [ ] `[Y]` `engine/llm_client.py` — single adapter, replay cache, call cap
- [ ] `[Y]` `s07_narrate` using `prompts/narrate.md`
- [ ] `[Y]` `engine/validator.py` + `tests/test_validator_blocks_invented_numbers.py`
- [ ] `[Y]` `s00_intent` using `prompts/intent_parse.md` → clarification branch
      *(SC-17)*
- [ ] `[Y]` Record the replay cache and **commit it** — this is what makes the
      whole system runnable offline with no key
- [ ] `[N]` Streamlit: persona switcher, alert feed, question box
- [ ] `[N]` Findings view: tiered sentences, evidence drawer, action card,
      freshness banner, telemetry footer
- [ ] `[N]` **Progress narration during the run** — stages ticking by live
      ("Localizing… ✓ · 37 tickets matched…"). A 45-second wait with a spinner
      feels broken; the same wait narrated feels like work being done. Cheapest
      UX win available.
- [ ] `[N]` **Tier tooltips** — one plain-English line per tier, on hover. Never
      make a judge guess what EVIDENCED means.
- [ ] `[N]` **Pre-computed hero cache** — SC-01 and SC-08 load instantly from
      cache; everything else computes live. Protects the demo from a cold start.
- [ ] `[N]` Scenario picker SC-01…SC-17, **including the ones you fail**
- [ ] `[N]` Three-channel render (workspace card / chat message / email digest)
      side by side — answers the brief's "delivery channels" clause in half a day
- [ ] `[N]` "Try to break it" tab

> ### GATE 5
> A judge who has never seen the project can, unaided: pick a persona, click an
> alert, watch it run, read a tiered answer, open the evidence, and switch to
> SC-08 and see it decline. Watch someone actually do this — a friend, a
> flatmate, anyone. Where they hesitate is your UI bug.

---

## Phase 6 — Evaluation and evidence
**T−12 → T−5 · runs alongside Phases 4–5 · `[Y]`**

Start this *during* Phase 4, not after. Evidence built at the end is always thin.

- [ ] `[Y]` `eval/harness.py` — run all 17 scenarios, score against ground truth
- [ ] `[Y]` `eval/metrics.py` — localization F1, RCA top-1, evidence recall@5,
      **abstention precision/recall**, **hallucinated-cause rate (target 0)**
- [ ] `[Y]` Scoring rules written down **before** running: how a suppressed cell
      scores (SC-15), how a partially-correct multi-cause answer scores (SC-07),
      what counts as a hallucinated cause
- [ ] `[Y]` `make fetch-rs` → run the seven published algorithms on the 135 real
      labelled anomalies → `eval/rs_benchmark.md`
- [ ] `[Y]` **Freeze thresholds here**, on the benchmark, before scoring scenarios
- [ ] `[Y]` **B1** naive drill-down baseline
- [ ] `[Y]` **B3** LLM-only single-prompt baseline ← *the highest-value four hours
      in the project; see `docs/04_EVALUATION_PLAN.md` §3*
- [ ] `[Y]` `eval/cost_receipt.md` — tokens, USD/run, p50/p95 latency
- [ ] `[Y]` CI running the harness and publishing the scorecard on every push
- [ ] `[Y]` Two separate result tables: **Stage 03 vs published baselines**, and
      **trust behaviours (no baseline exists)**. Never merge them.

> ### GATE 6
> `eval/scorecard.md` and `eval/baseline_scorecard.md` are committed and current,
> **with misses shown**. The SC-08 comparison — B3 invents a cause, GlassBox
> abstains — exists as a screenshot for the deck.
>
> Thresholds have not moved since the benchmark run. Check `git log` on the
> config; if they moved, say so in the changelog rather than hiding it.

---

## Phase 7 — Submission
**T−4 → T−0 · `[B]` · CODE FREEZE AT T−4**

Nothing new gets built in this phase. This is not a suggestion — every team that
loses its last week loses it by building one more feature at T−2.

- [ ] `[B]` **T−4: code freeze.** Only bug fixes with a failing test attached.
- [ ] `[N]` README rewritten user-first: person → bottleneck → cost → what
      changes → screenshot → two doors → hot take → failure mode
- [ ] `[Y]` `REPRODUCE.md` finalised **after** the T−7 clean-machine test
- [ ] `[Y]` `TRAJECTORIES.md` — SC-01, SC-08, SC-14 traces + "why not an agent"
- [ ] `[B]` `JUDGES.md` — the five-minute path
- [ ] `[Y]` ADRs (5) · `[N]` build-vs-buy table · `[B]` traceability matrix (22)
- [ ] `[N]` Business proposal: users, impact, phased roadmap, risks + mitigations
- [ ] `[B]` Deck **on the Round 1 template**, opening structured around the R1
      brief's three "think about" questions
- [ ] `[B]` Demo video, 2–3 min, timestamped. SC-08 and SC-14 are protected —
      cut anything else first.
- [ ] `[N]` Hosted demo deployed, warmed, checked the morning of submission
- [ ] `[B]` Repo → public. Final scan: no secrets in history, no Olist data, no
      tooling residue in commits or comments.
- [ ] `[B]` Two Q&A rehearsals against `docs/07_DEMO_AND_PITCH.md` — out loud,
      timed, taking turns being the hostile judge
- [ ] `[B]` `CHANGELOG.md` final entry; verify it agrees with `git log`

> ### GATE 7 — submit
> Every never-cut item green. `make reproduce` verified on a machine that never
> built this project. Both of you can defend every file.

---

## 8. The five improvements, and where they live

Carried in from the review, each pinned to a phase so none becomes a "later":

| Improvement | Phase | Why |
|---|---|---|
| Progress narration during the run | 5 | Turns the 45-second bottleneck into visible work |
| Plain-language tier tooltips | 5 | Tiers are the product; jargon must land in zero seconds |
| Pre-computed hero cache (SC-01, SC-08) | 5 | Removes cold-start risk from the two moments that matter |
| **Scope gate at T−10** | 4→5 boundary | Counted, pre-agreed cut order — decided early, not discovered late |
| **Cross-machine `make reproduce` test at T−7** | 6 | Reproducibility is a claim until someone else runs it |

---

## 9. The compression ladder

When you are behind, cut **in this order**, and cut *early*. Record every cut in
`CHANGELOG.md` — a documented scope decision reads as judgement; an undocumented
gap reads as failure.

**At T−10, count your green scenarios.** Under 13 of 17 → start cutting today.

1. The "try to break it" tab *(keep the injection scenario itself)*
2. The third persona (Analyst) — ship CFO + Category Manager
3. Docker
4. The three-channel render → one screenshot instead of live rendering
5. SC-11 (slow erosion) and SC-12 (spillover) — the two most expensive scenarios
6. SC-03, SC-09 — keep them in the manifest, mark `NOT IMPLEMENTED` in the
   scorecard *(an honest gap beats a quiet one)*
7. The hosted demo *(README then leads with `make reproduce`)*
8. B1 baseline *(keep B3 — it is worth more than B1 and B2 combined for you)*

### Never cut — in priority order
1. **SC-08 abstention.** The most memorable 40 seconds of the submission.
2. **`make reproduce` working from a clean clone.**
3. **The committed scorecard, with misses.**
4. **Tiers on every sentence.**
5. **The number validator.**
6. **`CHANGELOG.md` written live.**

Four of those six are nearly free. That is not an accident — the cheapest things
here are the most credible, which is why they are never the things to cut.

---

## 10. Session rhythm

One phase per session. Read the phase → do the unchecked items → `make test` and
`make eval` → tick `CHECKLIST.md` → **write the changelog entry** → summarise the
diff in three lines → stop.

Review the diff yourself before committing. Say "no" to any change to a frozen
thing you do not fully understand. And run `make eval` with your own hands at
least once a week — in Q&A the judges test *you*, not your tooling.
