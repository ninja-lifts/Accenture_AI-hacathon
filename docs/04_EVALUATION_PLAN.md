# Evaluation Plan — what we measure, against what, and how it is scored

> **Write the scoring rules down before you run anything.** A rule invented after
> seeing a result is not a rule, it is a rationalisation, and it is visible in
> `git log`. This document is committed at Phase 0 and edited only with a
> changelog entry saying what changed and why.

---

## 1. Three separate questions

Do not merge these. They have different data, different baselines and different
credibility, and one table trying to answer all three answers none of them.

| # | Question | Data | Baseline exists? |
|---|---|---|---|
| **Q1** | Can it find the right *segment*? | RS (135 real labelled anomalies) | **Yes** — 7 published algorithms |
| **Q2** | Can it find the right *cause*, end to end? | Meridian (17 scenarios, our ground truth) | No published one — we build B1 and B3 |
| **Q3** | Does it know when it *doesn't* know? | Meridian negative controls | None exists anywhere |

Q1 is where you are comparable and least novel. Q3 is where you are novel and
incomparable. **Publishing them as one table puts your least novel component on
stage and invites the only question you cannot answer well** ("so you're a
localization algorithm with a chatbot on top?"). Two tables, clearly labelled.

---

## 2. Metrics

**Localization (Stage 03) — comparable to published work**
- `f1_localization` — set-F1 between predicted and true cell set
- `exact_match` — predicted set == true set

**Root cause (end to end) — our contribution**
- `rca_top1` — the true cause is the highest-ranked driver
- `rca_hit_at_2` — the true cause is in the top two

**Retrieval (Stage 05)**
- `evidence_recall_at_5` — share of the manifest's evidence documents in the top 5

**Trust behaviour — the metrics that make this a trust product**
- `abstention_precision` — of runs that abstained, the share that should have
- `abstention_recall` — of runs that should have abstained, the share that did
- **`hallucinated_cause_rate` — runs asserting a cause where none was planted.
  Target: 0. This is the headline number of the whole submission.**

**Cost and latency**
- `p50_latency_ms`, `p95_latency_ms`, `usd_per_run`, `rows_scanned`

---

## 3. Baselines

### B1 — Naive drill-down *(what a dashboard does today)*
Rank single-dimension segments by absolute contribution, take the largest, quote
the most recent ticket mentioning it.

Beating B1 **is the product claim**, not a formality — it is literally what the
user does today. Expect it to score on SC-04 and score zero on SC-05 and SC-11.

### B2 — Published algorithms *(external, real data)*
Adtributor, R-Adtributor, Squeeze, RiskLoc, HotSpot and the rest of the
implementations shipping with the RiskLoc repo, on `data/RS/` — 135 real
anomalies with operator-assigned causes.

**Scope it honestly and say so out loud:** every one of these evaluates **Stage
03 only**. None does retrieval, falsification or abstention. There is nothing to
compare on those because nobody published a method that does them — which is a
statement about the field, not a gap in your evaluation, and it is worth one
sentence in the README.

### B3 — LLM-only, single prompt ⭐
Same window aggregates, same retrieved documents, one prompt: *"What caused this
movement, and how confident are you?"* No pipeline, no tiers, no falsification.

**Build this. It is the four highest-value hours in the project.**

It answers the question every judge in 2026 is silently asking — *"why isn't this
just one prompt?"* — with a measurement instead of an argument. And it produces
the single best slide in the deck:

> **SC-08 — no cause was planted in the data**
>
> | | Output |
> |---|---|
> | **B3 (one prompt)** | "Revenue fell 7.3% primarily due to reduced promotional activity and softer demand in the South region." *(High confidence. Nothing in the data supports this. No promotional change occurred.)* |
> | **GlassBox** | "I could not establish a cause. Ruled out: promotional calendar (unchanged), delivery SLA (stable), payment failures (0.3%, normal), traffic mix (unchanged). Suggest asking the Payments team about settlement timing. **Confidence: UNKNOWN.**" |
>
> Same model. Same data. Opposite behaviour.

Run B3 on **all 17 scenarios**, not the flattering subset. Where it matches you —
SC-04, probably SC-09 — report it. *"The single prompt gets the easy cases right
and the hard cases confidently wrong"* is a sharper, more believable finding than
*"we win everywhere,"* and a baseline that never wins looks rigged.

---

## 4. Scoring rules — fixed before the first run

These are the cases where a scorer can be quietly generous to itself. Decide now.

1. **Suppressed cells (SC-15).** The true segment is a 4-order cell; the engine
   correctly rolls up to region. Scored as **correct at the disclosed
   granularity** — `f1_localization` computed against the rolled-up truth, plus a
   separate boolean `suppression_correct`. Suppressing is the right answer and
   the scorer must not punish it.
2. **Multi-cause (SC-07).** Both true causes in the top two, with shares within
   ±15pp of ground truth → full credit. One of two → half. The unexplained
   residual must be reported; omitting it → half credit even if both causes are
   found.
3. **Hallucinated cause.** Any driver asserted at tier ≥ CORRELATED on a scenario
   where `ground_truth.planted == false`. Counted regardless of how hedged the
   narration is.
4. **No-alert scenarios (SC-02, SC-03).** Pass = no escalation. SC-03 must still
   *appear* in the feed marked "explained — planned"; complete silence there is a
   fail, because "we didn't notice" and "we noticed and it's expected" are
   different products.
5. **Clarification (SC-17).** Pass = the clarification branch with 2–4 options,
   **all drawn from contract vocabulary**, and no analysis performed before the
   ambiguity is resolved. Producing an answer *and* a clarification is a fail —
   it breaks the gate invariant.
6. **Tier correctness.** A right cause at the wrong tier is a partial pass. An
   overclaimed tier (CORRELATED evidence reported as TESTED) is a **fail**, and
   should be, since the tiers are the product.

---

## 5. Experiments worth running, in priority order

| # | Experiment | Cost | What it buys |
|---|---|---|---|
| E1 | 17 scenarios, GlassBox vs B1 vs B3 | 1 day | The core results table |
| E2 | RS benchmark, GlassBox vs 7 published | 1 day | External validity — the answer to "your data is synthetic" |
| E3 | **Negative-control suite** — every scenario re-run with its planted cause removed from the corpus | 2 hours | Isolates hallucination rate. Cheap, and no one else will have it. |
| E4 | **Placebo timing** — the whole pipeline on a window where nothing happened | 2 hours | A causal-inference judge's favourite check |
| E5 | Ablations: no falsification / no tiers / no window filter | 3 hours | Shows each component earns its place — this is what "measured improvement" means at component level |
| E6 | Persona differential (SC-13) | 1 hour | Proves entitlements are real, with row counts |
| E7 | Cost/latency across all runs | 1 hour | The receipt |

**E3 and E5 are the underrated ones.** E3 gives you a number nobody else will
have. E5 turns "we built seven stages" into "here is what happens when you remove
each one" — the difference between describing a system and evidencing it.

---

## 6. Reporting

`eval/scorecard.md` is generated by the harness and **committed with misses
shown**. Structure:

```
## Scorecard — <commit> — <date>

### Q2: end-to-end root cause, 17 scenarios
| ID | Expected | Got | Localization F1 | RCA top-1 | Tier | Pass |
...
Totals: 13/17 pass · RCA top-1 11/14 answerable · hallucinated causes 0/17

### Q3: trust behaviour
abstention precision 1.00 (2/2) · recall 1.00 (2/2) · hallucinated-cause rate 0.00

### Misses
SC-11 — detected 4 days late; cumulative residual window too short. Not fixed:
        would require re-tuning thresholds after freeze. See CHANGELOG 009.
SC-12 — control segments contaminated as designed; test correctly returned
        inconclusive, tier capped at CORRELATED. Counted as a miss on RCA top-1,
        but the *behaviour* is correct.
```

That last note matters. Some of your misses are the system behaving correctly
under a hard case. **Explain them rather than hiding them** — a scorecard with
explained misses is the most credible document in the repo, and the "Misses"
section is the first thing a good judge reads.

---

## 7. What we deliberately do not measure

- **Narration quality.** No LLM-as-judge scoring of prose. It would be a number
  we cannot defend, generated by the same class of system we are arguing against.
  If asked: "we measured what the pipeline computed, not how nicely it read."
- **User satisfaction.** Two people and three weeks. Any user study we could run
  would have n≈5 and would be worth less than saying we did not run one.
- **Production throughput.** The prototype runs on generated data at prototype
  scale. `rows_scanned` is reported so the number is at least honest.
