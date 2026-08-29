# Business Proposal

**Status note, read this first:** the sections below that depend on real
customer conversations (market sizing, willingness to pay, competitive
positioning against named incumbents) are marked explicitly where they are
informed judgement rather than research. We would rather flag an assumption
than dress an estimate up as a finding — the same standard the rest of this
repo holds itself to (see `eval/scorecard.md`, `CHANGELOG.md`). Every
technical claim below is pulled from a committed file, not asserted.

---

## 1. The user

**Primary: the category/functional manager who owns a KPI on a monthly
business review** — in the prototype, "Priya," Audio category lead at a
mid-size electronics retailer (`README.md`). She does not write SQL, does not
have an analytics degree, and is accountable for a number that moves before
she knows why.

**Secondary: the analyst who currently does the investigation by hand.**
GlassBox does not remove this role — it removes the three-to-four-day
mechanical part (pull the numbers, slice by every dimension, read forty
tickets) so the analyst's time goes to the last 20%: judgement calls the
system correctly declines to make (SC-08, SC-12).

**Tertiary: Finance/Ops leadership**, who receive the action object and the
audit trail, not the investigation.

**Explicitly not the buyer, at least not first: the data platform team.**
Adoption cost sits with them (writing semantic contracts), but the person who
feels the pain and requests the tool is the KPI owner, not the platform team —
this shapes the go-to-market motion in §4.

---

## 2. The problem, sized honestly

**What we can state as fact, from the prototype itself:**
- The manual investigation this replaces (pull numbers → slice dimensions →
  ask other teams → read support tickets → produce a written answer) is a
  real, described workflow, not a hypothetical (`README.md`'s Priya scenario).
- GlassBox runs the same seven-stage investigation end to end in **under 30
  seconds** measured (`eval/cost_receipt.md`: p50 latency ~424-880ms *per
  pipeline stage set*, full harness across 17 scenarios in ~26s total,
  meaning each individual investigation completes in low single-digit
  seconds to tens of seconds depending on retrieval cold-start — see the
  receipt for the real breakdown), at **$0 marginal cost in replay mode**
  and a small, bounded live-mode cost (2 LLM calls per run, hard-capped).

**What we cannot state as fact, and are not going to invent:** how many
investigations a month a "mid-size retailer" actually runs, what an analyst-
day actually costs a specific customer, or what this is worth to them in
rupees. Those numbers need a discovery call with 3-5 real prospective
customers, not a benchmark run. **This is the single highest-value non-
engineering task for the next phase of this project**, and it is a gap we are
naming, not filling with a plausible-sounding placeholder — see
`README.md`'s equivalent note on the same question.

**What we can argue directionally, and would defend in Q&A:** any
organization running weekly/monthly KPI reviews across more than a handful of
segments has this bottleneck, because the bottleneck is structural (the
translation from "what changed" to "why" is inherently manual today, not a
tooling gap any current dashboard closes) — see `docs/05_DATA_STRATEGY.md`
§2 for the evidence that this is a genuine market gap, not just a
positioning claim (no public dataset even pairs the four things — KPIs,
customer text, anomaly labels, cause labels — needed to build or evaluate a
system like this, which is itself evidence nobody has solved it cleanly yet).

---

## 3. What GlassBox actually is, in procurement terms

Not a chatbot over a warehouse. Not an agent. A **governed, deterministic
investigation pipeline** with two narrow, capped LLM touchpoints, sitting
behind a semantic contract layer that doubles as the access-control layer.

The reason this framing matters commercially: it is the difference between
"another AI pilot that needs a security review nobody has time for" and "a
tool where the access control is provably the same as the warehouse's own
row-level security, because it's compiled from the same contract." See
`docs/06_SECURITY_TRUST.md` and the entitlements demonstration in
`JUDGES.md`'s 15-minute path (a real, run-not-simulated `entitlements_hash`
diff between personas).

**Deployment model:** ships to the customer's data, never the reverse — runs
inside the customer's own cloud tenant, reads their warehouse through a
read-only service account, calls the model through a private endpoint in
their own subscription (`README.md` §Trust and deployment). This is a
deliberate, load-bearing constraint on the product, not an aspiration: it is
what makes "can I trust this with my data" answerable in one sentence instead
of a security questionnaire.

---

## 4. Phased roadmap

**Phase 0 (this submission).** Engine, evaluation harness, and evidence real
and reproducible for 5 semantic contracts and 17 pre-registered scenarios.
UI thin but functional (`app/main.py`). B1 baseline run; B3 baseline run live
against a real model (`eval/baseline_scorecard.md`) — not simulated.

**Phase 1 — design partner (1 customer, 5 metrics, 90 days).** The five
metrics that already appear in that customer's own monthly business review,
not a generic starter set — this is deliberate: writing a contract is an
afternoon with the metric's *owner* (`JUDGES.md`), and picking metrics
nobody actually reviews wastes that afternoon on a metric nobody will ever
ask "why did this move." Success criteria agreed with the partner up front,
not retrofitted: hallucinated-cause rate on their real data (target: what we
measured here, 0), and a comparison against however they currently do this
investigation (their own B1-equivalent), not against our own baseline.

**Phase 2 — vertical expansion (3-5 customers, same vertical).** Electronics/
general retail first, because Meridian is modeled on it and the contract
templates transfer directly. Contracts stay bespoke per customer (the
adoption cost is real, see §5), but the *stages* — detect, localize,
decompose, retrieve, falsify — do not change per customer; only the
contracts and the document corpus do.

**Phase 3 — platform.** Self-service contract authoring (a governed metric
still needs an owner and a review, but the YAML-writing itself doesn't need
us in the room), a real vector/hybrid index once corpus size crosses the
point where in-memory retrieval stops winning on recall (`docs/adr/0002`
names the measured threshold reasoning, ~10^5-10^6 documents), and the
persona set expanding past CFO/Category Manager/Analyst as real customers
tell us which roles actually use it.

**What is explicitly NOT on this roadmap, and why:** an agent framework
(ADR-0003 — the control-flow-must-be-identical-every-run argument is a
product requirement, not a current limitation to grow out of), a general-
purpose "ask anything about the business" chatbot (the contract-scoped
vocabulary and the clarify-rather-than-guess behavior are the trust
mechanism; a general chatbot on the same warehouse would need to rebuild it
from scratch), and fine-tuning (customer data never needs to leave the
tenant to make this work — training on it would contradict the whole
deployment story, per `docs/02_BUILD_BLUEPRINT.md`'s deliberate-non-features
table).

---

## 5. Risks and mitigations

| Risk | Real, or hypothetical? | Mitigation |
|---|---|---|
| **Contract authoring cost blocks adoption** | Real — five metrics is an afternoon each; 400 is a programme (`JUDGES.md`) | Phase 1 deliberately scopes to 5 metrics with a design partner, not a big-bang rollout. Most enterprises already have half a contract in an existing dbt/semantic layer to draw from. |
| **Synthetic-primary-dataset objection undermines evaluation credibility** | Real, and named rather than hidden | RS external benchmark (135 real anomalies, 7 published algorithms) exists as a planned mitigation but has not been run yet in this build — tracked openly in `CHECKLIST.md`, not glossed over. |
| **A confounder survives every control-segment test and produces an overconfident answer** | Real — this is SC-12's designed failure mode | The system's actual behavior on this exact case, measured: it abstains rather than force an answer (`eval/scorecard.md`'s SC-12 row). The tier ladder and falsification stage exist specifically so this degrades honestly instead of silently. |
| **LLM provider dependency / vendor lock-in** | Partially mitigated by design, not yet proven | `engine/llm_client.py` is the single boundary; provider is config, not code. This session added a second working adapter (Groq, alongside the original Anthropic one) without touching any other file — real evidence the vendor-neutral design works, not just an architecture diagram claiming it does. |
| **A live-mode cost surprise at scale** | Low, and measured | Two LLM calls per run, hard-capped in the schema (`telemetry.llm_calls.maximum: 2`) and enforced in code (`LLMCallCapExceeded`). `eval/cost_receipt.md` reports real per-run token/cost telemetry every time the harness runs, not on request. |
| **Market size / willingness to pay unvalidated** | Real, explicitly not hidden | Named in §2 above as the top open item. No number is asserted for it here. |
| **"Just use one LLM prompt" competitive pressure** | Real — this is the most common objection this category of product faces | `eval/baseline_scorecard.md`'s B3 baseline is not hypothetical; it was run live against a real model this session. On SC-08 specifically it produced a fluent, 70-80%-confident, fabricated cause — quoted verbatim in that file, not paraphrased. |

---

## 6. The pitch in one paragraph

A KPI moves. Today, finding out why costs three to four analyst-days and
finishes after the decision window closes, or it costs one AI prompt and
produces a confident, unverifiable, sometimes fabricated paragraph.
GlassBox is neither: five of seven stages are arithmetic and statistics with
no model in the loop, the two touchpoints that do use one are capped and
number-validated, and — measured, not claimed — it produces zero
hallucinated causes across 17 pre-registered scenarios while a real, live
run of the obvious one-prompt alternative invents one on the scenario
designed to test exactly that. The hard engineering problem was not finding
causes. It was building something that stays quiet when there isn't one.
