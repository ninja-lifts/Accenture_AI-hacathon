# For evaluators

Thank you for the time. Here is the shortest path to a fair assessment.

---

## If you have 5 minutes

1. **⟪FILL: [Open the live demo](URL)⟫** — no install, no key.
2. Persona **Category Manager** → click **Net Revenue −8.2%**. Read the answer.
   *Look at the confidence tier on each sentence, and at the cause we tested and
   rejected.*
3. Scenario picker → **SC-08**. We planted no cause in this data.
   **It refuses to answer** and tells you who to ask instead.
4. Open [`eval/scorecard.md`](eval/scorecard.md). ⟪FILL: N⟫ of 17 scenarios pass.
   The failures are listed, with an explanation for each.

If you only do one of these, do **step 3**.

---

## If you have 15 minutes

Add:

5. Scenario picker → **SC-14**. A support ticket in the evidence drawer contains a
   prompt-injection attack. It is retrieved, quoted, flagged — and ignored.
6. Switch persona to **CFO**, re-run SC-01. Different scope, different cited
   documents, different `entitlements_hash` in the footer. The role changes the
   SQL, not the view.
7. [`eval/baseline_scorecard.md`](eval/baseline_scorecard.md) — the same model,
   the same data, in one prompt. Compare the SC-08 rows.
8. The **"try to break it"** tab. Type your own injection, or ask for data your
   persona cannot see. Everything you try appears in the audit log.

---

## If you have 30 minutes

9. [REPRODUCE.md](REPRODUCE.md) → `make reproduce`. Runs offline, no key,
   ⟪FILL: N⟫ minutes. Your scorecard should match ours exactly.
10. [TRAJECTORIES.md](TRAJECTORIES.md) — three complete runs, every stage, both
    prompts and both responses verbatim, the validator verdict, the gate decision.
11. [`prompts/`](prompts/) — the only two model calls in the system.

---

## Four things worth checking, because they are unusual

**The ground truth was frozen before the engine existed.**
```bash
git log --follow data/injection_manifest.yaml
```
Commit ⟪FILL: hash⟫ predates the first commit under `engine/`. Our accuracy
numbers are pre-registered, not fitted.

**The changelog agrees with the history.**
[`CHANGELOG.md`](CHANGELOG.md) — ⟪FILL: N⟫ entries, each naming a commit and a
scorecard delta, including changes that made things worse and were reverted.
`git log` will corroborate it.

**The scorecard shows failures.** We publish misses with explanations. Some are
the system behaving correctly under a hard case — SC-12 returns "inconclusive"
and caps its confidence rather than guessing — and we say which is which.

**Five of seven stages never touch a language model.** The model turns a question
into a query and a result into a sentence. Every numeral it writes is
re-extracted and matched against the computed findings before you see it.

---

## What we would push on, if we were you

We would rather name these than have you find them.

- **The primary dataset is synthetic.** It has to be — no public dataset pairs
  business KPIs with customer text *and* labelled causes
  ([why](docs/05_DATA_STRATEGY.md#2-why-the-ideal-dataset-does-not-exist)). We
  offset it with a real-data benchmark:
  [`eval/rs_benchmark.md`](eval/rs_benchmark.md), 135 real anomalies with
  operator-assigned causes, against seven published algorithms.
- **Causal claims are quasi-experimental.** `TESTED` means "survived our
  falsification attempts", not "proven". A confounder moving with the true cause
  across every control segment defeats it — SC-12 is that case, and it is in the
  picker.
- **The UI is a prototype.** Streamlit, deliberately. The engine is ~80% of the
  work and all of the differentiation.
- **The semantic contract is real adoption cost.** Five metrics is an afternoon
  each with their owners. Four hundred is a programme, and we would not pretend
  otherwise.

---

## Questions we are ready for

[`docs/07_DEMO_AND_PITCH.md#3-qa-bank`](docs/07_DEMO_AND_PITCH.md) — but ask us
anything. If we cannot defend a file in this repo, we should not have shipped it.
