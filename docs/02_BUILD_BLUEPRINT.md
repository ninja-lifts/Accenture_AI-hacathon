# Build Blueprint — architecture, stage specs, module map

The buildable specification. `docs/01_MASTER_BUILD_FLOW.md` says *when*; this
says *what*.

---

## 1. The shape of the system

```
                    ╔═══════════════ INPUT ═══════════════╗
                    ║  alert sweep    OR    typed question ║
                    ║  identity + entitlements resolved    ║
                    ║  5 semantic contracts → KPI graph    ║
                    ║  3 structured sources (freshness     ║
                    ║  declared) + redacted doc index      ║
                    ╚══════════════════╤═══════════════════╝
                                       │
   ┌───────────────────────────────────▼───────────────────────────────────┐
   │  00  INTENT      ◆ LLM #1   text → {kpi, segment, window}             │
   │                             contract-validated · asks, never guesses  │
   │  01  DEFINE      ● contract SQL + entitlement predicates → series     │
   │  02  DETECT      ● seasonal baseline · dual materiality · registry    │
   │  03  LOCALIZE    ● multi-dim attribution · small-cell suppression     │
   │  04  DECOMPOSE   ● price / volume / mix along KPI graph edges         │
   │  05  RETRIEVE    ● BM25 + embeddings · entitlement + window filtered  │
   │  06  FALSIFY     ● diff-in-diff · placebo · controls · dose-response  │
   │  ──────────────────── GATE ────────────────────                       │
   │       answer          │        abstain        │       clarify         │
   │  07  NARRATE     ◆ LLM #2   persona prose · number-validated          │
   └───────────────────────────────────┬───────────────────────────────────┘
                                       │
                    ╔══════════════════▼═══════════════════╗
                    ║  ONE findings object                 ║
                    ║  exactly one branch populated        ║
                    ║  → persona × channel renders         ║
                    ║  → evidence drawer · re-run · fresh  ║
                    ║  → action object · audit · telemetry ║
                    ╚══════════════════════════════════════╝

   ● deterministic (5 of 7)          ◆ the only two LLM touchpoints
```

**Read the diagram as the argument.** The model is at the edges: it turns
language into a query, and a finished result into language. Everything that
decides *what is true* is in the middle, and the middle is arithmetic.

---

## 2. Stage specifications

### Stage 00 — Intent *(LLM #1, typed questions only)*
**In:** raw question, contract catalogue, today's date.
**Out:** `{kpi, segment, window}` **or** a clarification **or** out-of-scope.
**Constraint:** may only emit values present in the catalogue. Anything unmapped
is reported, never silently dropped.
**Why it exists:** Objective 5 asks for a system that "requests clarification or
abstains." Nothing in an alert-driven flow is ever ambiguous, so without a
question box, half that objective is unevidenced. *(SC-17.)*

### Stage 01 — Define
**In:** contract, principal, window. **Out:** series + per-source freshness.
Executes the contract's SQL with the entitlement predicate pushed in. A mismatch
between contract and warehouse is a **data-quality failure**, not a silent
coercion — it routes to abstention with `reason_code=data_quality_failure`.

### Stage 02 — Detect
**In:** series, contract detection block, context registry.
**Out:** movement + materiality verdict.
- Seasonal baseline: STL residual control chart, with day-of-week, month and a
  festival calendar. *(SC-02 lives or dies here.)*
- **Dual materiality:** a movement alerts only if it is **both** statistically
  surprising (`min_z`) **and** financially large (`min_abs_impact`). Either test
  alone produces the 200-alerts-a-day failure mode.
- Registry suppression: planned promos, price changes and releases mark the
  movement "explained — planned" and stop escalation without hiding it. *(SC-03.)*
- Cumulative-residual run rule for slow erosion no single day would trip. *(SC-11.)*
- Below `min_history_periods` → declare a tier cap of HYPOTHESIS. *(SC-10.)*

### Stage 03 — Localize
**In:** movement, dimension lattice. **Out:** ranked segments.
Search the lattice for the smallest cell set explaining most of the movement,
then apply small-cell suppression. **This is the only stage with published
baselines**, which makes it the only place an apples-to-apples external
comparison is possible — and the reason the results table is split in two.
*(SC-15 for suppression; SC-12 for the spillover case.)*

### Stage 04 — Decompose
**In:** localized movement, KPI graph. **Out:** price / volume / mix / new / churn.
Walk the graph edges rather than a hard-coded list. **Components must sum to the
movement** — assert it; a decomposition that does not close is a bug, and every
number here is VERIFIED by construction because it is recomputed from source.
*(SC-05: volume flat, price flat, mix moved — the case a drill-down cannot see.)*

### Stage 05 — Retrieve
**In:** segment, window, principal. **Out:** ranked evidence with citations.
Hybrid BM25 + embeddings over the redacted index. Two filters applied **before**
scoring, not after:
1. **Entitlement** — documents the principal may not read never enter the pool.
2. **Window** — a ticket from three months ago is not evidence for last week,
   however well it matches. *(This filter is what defeats the SC-08 decoys. Get
   it wrong and your abstention scenario silently starts answering.)*

### Stage 06 — Falsify
**In:** candidate causes, evidence, series. **Out:** tests with verdicts.
The stage that separates explanation from correlation. Per candidate:
- **Difference-in-differences** against control segments
- **Placebo timing** — run the same test on a date where nothing happened. If it
  "finds" an effect, the method is broken for this data. *This is the test a
  causal-inference-literate judge looks for and almost never sees.*
- **Unaffected control segments** — and check they really are unaffected (SC-12)
- **Dose-response** where magnitude varies (SC-06's rollout curve is the best
  falsification evidence in the suite)
- **Pre-period contamination check**

Survivors → TESTED. Failures → `rejected_hypotheses` **with the test that killed
them**, never dropped. That field is the difference between an explanation and an
assertion; if it is ever empty on a real answer, something is wrong.

### The gate
```
if intent ambiguous                          → clarification
elif data-quality failure                    → abstention (data_quality_failure)
elif only localization is a suppressed cell  → abstention (segment_too_small)
elif no candidate clears the evidence floor  → abstention (no_candidate...)
elif evidence contradicts every candidate    → abstention (evidence_contradicts)
elif history below contract minimum          → answer, capped at HYPOTHESIS
else                                         → answer
```
**Exactly one branch.** Never a hedged blend. `tests/test_gate_invariant.py`
proves it and must never be weakened.

### Stage 07 — Narrate *(LLM #2)*
**In:** the completed findings object + persona. **Out:** prose.
Sees no raw data. Cannot introduce a number, a cause or a tier. Output passes
`engine/validator.py`: every numeral must already exist in the findings object.
Failure → regenerate once → fall back to a template render. `validator_retries`
is surfaced in telemetry on purpose.

---

## 3. The tier ladder

| Tier | Means | Assigned when |
|---|---|---|
| `VERIFIED` | Arithmetic, not judgement | Recomputed from source (all of Stage 04) |
| `EVIDENCED` | We can show you the documents | ≥ `EVIDENCE_FLOOR` cited docs inside the window |
| `TESTED` | We tried to disprove it and failed | Survived ≥1 falsification test |
| `CORRELATED` | Moves together; not established as cause | Statistical association only |
| `HYPOTHESIS` | A lead, not a finding | Plausible mechanism, no support |
| `UNKNOWN` | We will not grade this | Refused |

Two properties matter more than the exact thresholds:
- the mapping is a **lookup table a judge can read in 30 seconds**
- it is **monotone**: removing evidence can never raise a tier
  (`tests/test_tiers_monotone.py`)

**Declared degradations** cap tiers from upstream: sparse history → HYPOTHESIS;
no clean pre-period → CORRELATED; suppressed cell → UNKNOWN. Degradation is
always announced in the UI, never silent. Silent degradation is the failure mode
that makes a trust product untrustworthy.

---

## 4. Module map and the interface between you two

The one thing to agree on **day one**, because it is the only place your two
halves touch.

### `[Y]` owns: `data/generate.py`, `engine/` stages 01–04, 06, tiers, gate, validator, pipeline, `eval/`
### `[N]` owns: documents, `engine/redaction.py`, stage 05, `app/`, business proposal
### `[B]`: contracts, schemas, docs, deck, video

**The contract between the halves — write the real column names in here at
Phase 0 and do not change them without telling the other person:**

```python
# What the generator emits (Y → N)
metric_row  = {ts, region, category, channel, payment_method, value, support_size}
document    = {document_id, source, title, body, published_at,
               entities: {region?, category?, channel?, sku?},
               visibility_roles: [str]}

# What retrieval returns (N → Y)
evidence_ref = {document_id, source, snippet, retrieval_score,
                published_at, entitlement_ok, flagged_injection}
```

`evidence_ref` matches `$defs/evidenceRef` in the findings schema exactly. If
those two ever drift, the schema wins.

---

## 5. Deliberate non-features

Written here so they are decisions, not omissions — and so the answer is ready in
Q&A. Long form in `docs/adr/`.

| Not built | The answer to give, verbatim |
|---|---|
| Agent loop / tools | "A trust product needs a control flow that is identical every run. An agent that plans its own path can't be audited, replayed, or unit-tested. We made the pipeline fixed and the model narrow on purpose." |
| Vector database | "490 documents. We measured it — in-memory hybrid retrieval beats the recall we'd get from adding an operational dependency. We'd add one at about a million documents." |
| Fine-tuning | "Nothing is trained. Statistical baselines are fit per KPI on history; the model is used as-is behind a private endpoint. Fine-tuning would mean moving customer data out, which contradicts the whole deployment story." |
| Real SSO | "The persona switcher is disclosed as a simulation. The entitlement logic behind it is real — it changes the SQL, not the view." |
| Kafka / streaming | "Replay clock in the prototype, CDC → stream → warehouse on one slide for production. We didn't think a message broker was what you were assessing." |
| BI tool embed | "Days of brittle integration for a screenshot. We showed the Slack and email renders instead — same point about meeting users where they are." |
