# Demo, Pitch and Q&A

---

## 1. The 3-minute video *(what goes in the repo)*

The submission checklist specifies 2–3 minutes. Two moments are protected — cut
anything else before them.

| Time | Scene | The line |
|---|---|---|
| 0:00–0:20 | A dashboard showing −8.2%. A person staring at it. | "Every dashboard can tell you *what* changed. None of them tell you *why*. That translation takes an analyst three to four days — and the decision gets made on day two." |
| 0:20–0:45 | Alert feed → click "Net Revenue −8.2%" → stages ticking | "GlassBox does the investigation. Seven stages. Five of them are statistics, not AI." |
| 0:45–1:25 | The answer: tiered sentences, evidence drawer open, cited tickets, a demoted rival cause | "Every sentence is graded. This one is TESTED — we tried to disprove it. This one is only CORRELATED, and it says so. And here is what we ruled out: a national promo ended the same week, but it ended everywhere, and only the South moved." |
| 1:25–2:05 | **SC-08.** Switch scenario. The engine declines. Long pause. | "This movement is real. We planted no cause. Watch. — *It doesn't answer.* It lists what it ruled out and tells you who to ask. **Here is the same model, given the same data, in a single prompt.** It invents a cause, with high confidence." |
| 2:05–2:30 | **SC-14.** Evidence drawer with the flagged malicious ticket | "A support ticket tries to hijack it. It gets retrieved, quoted as evidence, flagged — and ignored." |
| 2:30–2:50 | The scorecard, misses visible | "Seventeen pre-registered scenarios, ground truth committed twelve days before the engine existed. Thirteen pass. Here are the four that don't, and why." |
| 2:50–3:00 | `make reproduce` scrolling | "Clone it and run it. No API key needed." |

**Keep a 7-minute cut for the live pitch.** Same spine, room to breathe on the
architecture and the business case.

Recording hygiene: close every other window and tab, use a clean browser profile,
run locally (**never off the free-tier host**), and check the terminal prompt and
window titles are clean before you hit record.

---

## 2. Pitch structure

Open on the R1 brief's own three questions. The judges wrote them; answering each
by name with a demo scene is free alignment that no other team will think to do.

1. **The 8% question** — the problem, in a person's voice, 45 seconds
2. **"How do you separate meaningful change from noise?"** → dual materiality +
   the festival scenario where *nothing happens*
3. **"How do you get from correlation to something a leader can act on?"** →
   falsification + the tier ladder + the action object
4. **"What do you do when the data is genuinely ambiguous?"** → **SC-08.** Stop
   talking. Let the silence sit.
5. **How it is built** — the seven stages, the two LLM touchpoints, the contract
6. **Does it work?** — scorecard, RS benchmark, the B3 comparison
7. **Can you trust it with your data?** — in-tenant, phased access, injection demo
8. **The business case** — user, saving, phased roadmap, risks
9. **Ask** — what you would build next, and what you would need

Appendix: traceability matrix (22 items), KPI graph, cost receipt, R1→R2 tracker.

Use the **Round 1 template** (AIC Talent-Brand PPT template) — same visual
identity as the R1 deck. It was an instruction, and it is the kind of instruction
that gets checked.

---

## 3. Q&A bank

Rehearse these out loud, twice, timed, taking turns as the hostile judge. Reading
them silently does not work — the failure mode is knowing the answer and taking
forty seconds to find it.

**"Your main dataset is synthetic. Why should I believe any of it?"**
Two answers. One: no public dataset pairs business KPIs with customer text *and*
labelled causes — here is the four-way partition showing why that gap is
structural. Two: which is why we also benchmark on RS — 135 real anomalies with
operator-assigned causes, against seven published algorithms. The synthetic set
measures the whole pipeline; the real set keeps us honest about the part that can
be compared.

**"Most of this is statistics, not AI."**
Yes. Five of seven stages. That is the design, not a shortcut. The parts that
decide what is true are deterministic; the model turns language into a query and
a result into language. It is why we can promise the system cannot invent a number.

**"Why isn't this just one prompt?"**
We built that — baseline B3, same model, same data. It matches us on the easy
scenarios and fails the hard ones confidently. On SC-08 it invents a cause. The
table is in the appendix.

**"Why not an agent?"**
A trust product needs a control flow that is identical every run. An agent that
plans its own path can't be replayed, unit-tested or audited, and a CFO cannot
sign off on a trajectory that differs each time. We traded flexibility for
auditability deliberately. *(ADR-0003.)*

**"Would this survive a real warehouse — 400 metrics, no contracts?"**
The contract is the adoption cost and we should not pretend otherwise. Phase 1 is
five metrics, not four hundred — the five that appear in the monthly review.
Writing one takes an afternoon with the metric's owner, and most enterprises
already have half of it in a dbt or semantic layer. It is a delivery motion, which
is where a partner like Accenture actually adds value.

**"What's your accuracy?"**
Point at the scorecard, including the misses, and give the hallucinated-cause
rate. Never quote a number that is not in a committed file.

**"What breaks it?"**
A confounder that moves with the true cause across every control segment. SC-12
is that case — the tests come back inconclusive and the tier caps at CORRELATED
rather than TESTED. It degrades honestly instead of guessing, but it does degrade.

**"Who built what?"**
`git log` is public. Answer truthfully and specifically.

**"Did you use AI tools to build this?"**
Yes — nearly every serious team did, and judges know it. If the rules require a
disclosure line, it is in the README. What matters is that we can defend every
design decision and every line, which is what the Q&A is testing.

---

## 4. The three sentences to have word-perfect

Under pressure you will fall back on whatever you have said most often. Make it
these.

> **On the product:** "Every dashboard tells you what changed. GlassBox tells you
> why, shows you the evidence, and tells you how much to trust it."

> **On the architecture:** "Five of the seven stages never touch a language model.
> The model turns a question into a query and a result into a sentence — it never
> decides what's true."

> **On the abstention:** "The hard part wasn't finding causes. It was building
> something that would stay quiet when there wasn't one."
