# Project Rules

Read this first, every session. Then read `docs/01_MASTER_BUILD_FLOW.md`, which
is the single source of truth for what to build and in what order.

---

## What this project is

**GlassBox** — an explainable KPI root-cause engine. A dashboard says "net
revenue fell 8.2%." GlassBox says *why*, cites the evidence, grades its own
confidence, recommends an action — and refuses to answer when the data does not
support one.

Built for Round 2 of the Accenture Innovation Challenge 2026, Track 3
(BusinessIntelligence.ai). Team of two. Deliverables: a working prototype, a
business proposal, a pitch, and a public repo with a demo video and README.

**The architecture in one paragraph.** A seven-stage deterministic pipeline
(define → detect → localize → decompose → retrieve → falsify → narrate), with an
eighth intent-parsing stage in front of typed questions. Five of the seven stages
are statistics and arithmetic. The LLM is called **exactly twice**: once to parse
a question into a structured query using only vocabulary from the semantic
contracts, and once to write the narration from a completed findings object,
under a validator that rejects any number the statistical layer did not compute.
Every claim carries a rule-assigned confidence tier. The output is one findings
object with exactly one of three branches: **answer, abstain, or clarify** —
never a blend.

---

## The ten hard rules

These exist because a coding assistant's natural instinct is to helpfully fix
exactly the things this methodology requires stay fixed. If following a rule
seems to block progress, **stop and ask** — do not route around it.

1. **`schemas/` is frozen.** `findings.schema.json`, `contract.schema.json` and
   `injection_manifest.schema.json` are contracts, not suggestions. Never add,
   rename or relax a field to make code pass. If a schema genuinely needs to
   change, stop, explain why, and wait for a human decision.

2. **`data/injection_manifest.yaml` is frozen ground truth.** It is committed
   before any engine code reads it, and that commit hash is our pre-registration
   proof. You may fix a generator *bug*; you may add a new scenario. You may
   **never** change an existing scenario's `ground_truth` after the engine has
   produced output for it. If a scenario is ill-posed, mark it
   `notes: RETIRED - <reason>` and leave it in place.

3. **Thresholds freeze after the benchmark.** Detection thresholds, the evidence
   floor and tier cut-offs are set once, on the RS benchmark, before the scenario
   suite is scored. After that they are frozen. Tuning a threshold because a
   scenario failed is how a benchmark becomes meaningless.

4. **No secrets, ever.** Not in code, not in config, not in a commit, not in a
   notebook output, not in a test fixture. Git history is permanent — a key
   committed once is a key that leaked. `.env` is gitignored; keep it that way.

5. **No Olist data in the repo.** CC BY-NC-SA, and this repo is public and MIT.
   Ship a download script with attribution. Same for any other externally
   licensed dataset — `data/external/` is gitignored on purpose.

6. **All LLM calls go through `engine/llm_client.py`.** One file. No provider
   name, model id, endpoint or key anywhere else in the codebase. Prompts live in
   `prompts/*.md`, not as string literals.

7. **Never weaken `engine/validator.py`.** If narration keeps failing number
   validation, the prompt is wrong — fix the prompt. `validator_retries` is
   surfaced in telemetry deliberately; a non-zero count is the guard working.

8. **No LLM in stages 01–06.** Those stages are statistics and arithmetic. If a
   stage seems to need a model, the stage is wrongly specified — stop and ask.
   The hard cap of two calls is encoded in `findings.schema.json`.

9. **No new dependencies without asking.** `requirements.txt` is pinned. Every
   addition is one more thing that can fail on a judge's laptop at 11pm. In
   particular: **no vector database** (490 documents fit in memory — that is a
   measured decision, recorded in `docs/adr/`), **no agent framework**, **no
   orchestration library**.

10. **Clean commit history.** Descriptive messages in the imperative mood. No
    co-author trailers, no assistant branding, no "🤖 generated with" lines, no
    references to which tools were used, in commits, comments, docstrings,
    notebook outputs or documentation. The repo is a professional artefact. *(If
    the competition rules require an AI-assistance disclosure, that is a single
    honest line in the README — a rules question, separate from repo hygiene.)*

---

## How to work

**One phase per session.** Read the phase in `docs/01_MASTER_BUILD_FLOW.md`, do
the unchecked items, stop at the gate. Do not run ahead into the next phase
because the current one went quickly — the gates exist so a human reviews the
diff while it is still small.

**At the end of every phase, before saying you are done:**
1. `make test` and `make eval` — both must pass or the failure must be reported
2. Tick the completed items in `CHECKLIST.md`
3. **Add a `CHANGELOG.md` entry** in the required five-part shape:
   *evidence → problem discovered → decision → change → result.* This is not
   documentation housekeeping; it is 15% of how this project is assessed, and it
   is only credible if written live. An entry saying "we tried X, it made recall
   worse, we reverted" is worth more than a clean one.
4. Summarise the diff in three lines and stop.

**When something is ambiguous,** ask rather than assume — especially about
anything the ten rules cover. Being blocked for ten minutes is much cheaper than
a silently changed threshold.

**When you disagree with the plan,** say so. The build flow was written before
the code existed and it is allowed to be wrong. Say what you would do instead and
why, then wait. Do not implement the alternative unilaterally.

---

## Where things live

```
PROJECT_RULES.md          this file
README.md          judge-facing. Rewrite at Phase 7, not before.
CHANGELOG.md       the improvement log — append at every phase gate
CHECKLIST.md       definition of done; tick and commit daily
REPRODUCE.md       clean-environment reproduction guide
TRAJECTORIES.md    committed run traces (SC-01, SC-08, SC-14)
JUDGES.md          the five-minute evaluation path

docs/00_SUBMISSION_STRATEGY.md   why the submission is shaped this way (advisory)
docs/01_MASTER_BUILD_FLOW.md     ← THE PLAN. Phases 0–7 with gates.
docs/02_BUILD_BLUEPRINT.md       architecture, stage specs, module map
docs/03_SCENARIOS.md             SC-01…SC-17 in prose
docs/04_EVALUATION_PLAN.md       baselines, metrics, scoring rules
docs/05_DATA_STRATEGY.md         datasets, licensing, why synthetic is primary
docs/06_SECURITY_TRUST.md        the in-tenant deployment argument
docs/07_DEMO_AND_PITCH.md        video script, pitch structure, Q&A bank
docs/08_BUILD_VS_BUY.md          native / configured / custom / integrated
docs/adr/                        architecture decision records

schemas/     frozen JSON Schemas
contracts/   semantic contracts (net_revenue.yaml is the reference)
prompts/     the two prompts, versioned
engine/      the pipeline — stages/ is one file per stage
app/         Streamlit UI (thin — ~20% of the work)
data/        generator + the frozen injection manifest
eval/        harness, metrics, baselines, scorecards
tests/       three of these must never be weakened (see their docstrings)
```

---

## Things that are true and easy to forget

- **The webpage is not the project.** The engine is. If a session spends its time
  on UI polish while a stage is stubbed, it went wrong.
- **Abstention is a feature, not a bug.** SC-08 refusing to answer is a *passing*
  test. Never "fix" it.
- **Failing scenarios stay in the scorecard.** We publish misses. Do not filter
  the scorecard to look better; the honesty is the point and a judge who spots
  the filtering discounts everything else.
- **Not an agent, on purpose.** No loop, no tools, no planner, no multi-agent
  anything. A trust product needs a control flow that is identical every run.
  This is a decision to defend, not apologise for — see `docs/adr/`.
- **The judges have our Round 1 deck.** Three commitments in it (live semantic
  layer, context registry, analyst-verdict loop) are effectively a contract.
- **Two people, limited time.** When behind, cut in the order written in the
  build flow's compression ladder — never by silently shipping something
  half-built.
