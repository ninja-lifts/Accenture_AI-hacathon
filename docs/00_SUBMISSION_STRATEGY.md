# Submission Strategy — reading the borrowed rubric against GlassBox

**Status:** advisory. Read once before Phase 0, once again at T−10, once at T−4.
**Audience:** you two, not judges. Nothing here ships.

---

## 0. First, a warning about the rubric you handed me

You gave me an evaluation rubric from a *different* hackathon — an agent-building
competition. It is a good rubric and there is real value in it. But it is not
your rubric, and one of its six criteria is actively dangerous to you:

> **Agent solution & engineering — 30% — "Uses agents purposefully… which design
> choices helped the agent solve the problem?"**

GlassBox is **deliberately not agentic**. Five of seven stages are plain
statistics. The model gets no tools, no loop, no autonomy, and is called exactly
twice. That is not a shortcut — it is the entire product thesis. A trust product
for finance cannot have a non-deterministic control flow, because a CFO cannot
audit a trajectory that differs every run.

If you optimise toward that 30% line, you will bolt a ReAct loop onto a system
whose value proposition is that it does not have one, and you will lose your
Accenture submission to win a rubric you are not being judged against.

**So: use this rubric as a source of *evidence practices*, not architecture.**
Five of its six criteria translate cleanly and make you meaningfully stronger.
One does not translate, and the correct response is to translate it into
*run trajectories* — which we can and should ship — and then say plainly in the
README why the system is a pipeline and not an agent. See §C-3.

| Borrowed criterion | Translates to GlassBox? | What we take from it |
|---|---|---|
| Problem & user value (15%) | Yes, directly | Named user + bottleneck at the top of the README |
| Agent solution & engineering (30%) | **Partly — do not copy** | Prompts as artefacts, run traces, an explicit "why not an agent" answer |
| End-to-end quality (20%) | Yes | `make reproduce` completing cleanly; hosted demo |
| Measured improvement (15%) | **Yes — biggest gap** | Fair baselines + a live changelog tying each iteration to evidence |
| Reproducibility (15%) | Yes | REPRODUCE.md from a clean environment |
| Hot take / insights (5%) | Yes, and cheap | One honest failure-mode section |

Your actual Round 2 brief asks for a business proposal, a working prototype, a
pitch, and a public repo with a demo video and README. Where the two conflict,
**Accenture wins**. Where the borrowed rubric adds something Accenture does not
forbid — and evidence practices always are — take it.

---

## A. What is already strong — keep, do not touch

These came out of the R1 concept and the planning work. They are the submission's
spine. Nothing below should be redesigned to satisfy anything in this document.

1. **The deterministic-first architecture.** Five of seven stages are statistics
   and arithmetic; the LLM sits at the two boundaries. This is a defensible,
   unusual, correct design for a trust product, and it is the answer to the
   single most common judge objection in 2026 ("isn't this just a wrapper?").

2. **The confidence tier ladder** (VERIFIED / EVIDENCED / TESTED / CORRELATED /
   HYPOTHESIS / UNKNOWN), assigned by rule and attached to *every sentence*.
   No blending. Most competing prototypes produce one undifferentiated
   paragraph; you produce a graded one.

3. **The abstention branch.** A system that refuses to answer is rare, and in a
   competition about trustworthy AI it is the thing judges remember. SC-08 is
   your best 40 seconds.

4. **Falsification, not just correlation.** Difference-in-differences, placebo
   timing, control segments, dose-response. This is graduate-level rigour in a
   student prototype and it directly answers the R1 brief's own question about
   moving from correlation to action.

5. **The semantic contract as one governed artefact.** Definition + lineage +
   access rules + drivers + vocabulary in one YAML. It is simultaneously the
   semantic layer, the access-control layer, the disambiguation vocabulary and
   the KPI graph. That economy is genuinely elegant and worth one slide by itself.

6. **The number validator.** The LLM cannot emit a number the statistical layer
   did not compute. One sentence, and it kills the hallucination question.

7. **"GlassBox ships to the data, never the reverse."** The in-tenant deployment
   answer to "who hands their private data to an AI agent?" is correct,
   commercially literate, and the strongest thing you can say to an Accenture
   audience specifically.

8. **Ground truth you control.** Because you plant the causes, you can report
   accuracy honestly. Almost no student prototype can put a real number on
   "how often is it right?"

**Preserve all eight verbatim.** Everything in §C is a layer *around* these, not
a change *to* them.

---

## B. Submission gaps

Ordered by what a judge would notice first. Nothing here is architectural — that
is the point.

### B1. No baseline. *(Borrowed rubric weights this 15%; your brief implies it.)*
You can currently say "the engine found the right cause 9 of 11 times." A judge's
immediate question is **"compared to what?"** Without a baseline, 9/11 is a number
without a denominator of meaning. This is the largest single gap in the
submission and it is cheap to close.

### B2. The changelog does not exist and cannot be faked later.
"Evidence → problem discovered → decision → change → result" is only credible if
the git history agrees with it. Written at T−2 from memory, it reads as fiction
and a judge who diffs it against `git log` will know. Written live, one entry per
phase gate, it is the most persuasive document in the repo. **This is the only
item on this list with a hard deadline of "starting now."**

### B3. The README does not yet name a user or a bottleneck.
Currently the story is a technology story. The first 200 words a judge reads
should be: who this person is, what their Tuesday looks like, what it costs, and
what changes. Everything technical comes after.

### B4. No run traces.
You have a beautiful pipeline and no artefact showing one run end to end —
inputs, each stage's computation, the exact prompt sent, the exact response, the
validator's verdict, the retry, the tier assignment, the gate decision. This is
the honest translation of "agent trajectories," it is *more* legible than an
agent trace because it is deterministic, and it costs a `--trace` flag plus two
committed markdown files.

### B5. Reproducibility is claimed, not tested.
`make reproduce` will work on the machine that wrote it. It fails on a clean
environment for reasons you will not predict (a missing system library, a locale
issue with number parsing, a model download at first run, a Python version).
Untested reproducibility is worse than no claim, because the failure happens in
front of the judge.

### B6. No stated failure mode.
Every serious system has one. Volunteering yours reads as confidence; being
caught not knowing it reads as inexperience. It is 5% of the borrowed rubric and
roughly 200 words of work.

### B7. Prompts are not first-class.
They are the two places the model touches your system. If they live as string
literals inside Python, a judge cannot assess the part of your system they most
want to assess.

### B8. The "why not an agent?" answer is not written down.
You will be asked. Every team will be asked in 2026. Having the answer in the
README — architectural, confident, with the trade-off named — converts your
biggest apparent weakness into your clearest design decision.

---

## C. Recommended final improvements

Each carries: what, why judges care, impact, effort, verdict. **Effort assumes
two people.** Ordered by impact-per-hour, which is the order you should build in.

---

### C-1 — The LLM-only baseline (B3) ⭐ highest value in this document
**What.** One file, `eval/baselines/llm_only.py`. Hand a single model the same
window aggregates and the same retrieved documents in one prompt: *"What caused
this movement, and how confident are you?"* No pipeline, no tiers, no
falsification. Run it across all 17 scenarios. Publish both scorecards.

**Why it matters.** It answers the question every judge is silently asking —
*"why isn't this one prompt?"* — with evidence instead of assertion. And it
produces the single best slide in your deck: on **SC-08, where no cause exists**,
the one-prompt baseline confidently invents one and GlassBox abstains. Same
inputs, same model, opposite behaviour. That is the entire architecture argument
made in one screenshot.

**Impact:** very high. **Effort:** ~4 hours (reuses Stage 05 output).
**Verdict: ESSENTIAL.**

> Report where it *beats or matches* you too — SC-04 probably. A baseline that
> never wins looks rigged. "The single prompt gets the easy cases right and the
> hard cases confidently wrong" is a sharper and more honest finding than "we win
> everywhere."

---

### C-2 — The live Improvement Changelog
**What.** `CHANGELOG.md` at the repo root, one entry per phase gate, in a fixed
five-part shape: **evidence → problem discovered → decision → change → result**,
each entry naming the commit and the scorecard delta.

**Why.** It converts three weeks of invisible work into assessable work, and it
demonstrates the thing hackathon judges most want and most rarely see: that you
*iterated on evidence* rather than building once and demoing. It also protects
you — an entry saying "we tried X, it made recall worse, we reverted" is worth
more than a clean history.

**Impact:** high. **Effort:** 10 minutes per gate, ~2 hours total across the
build — *if written live.* Unfakeable afterwards.
**Verdict: ESSENTIAL, and it starts at Phase 0, not at the end.**

---

### C-3 — Run traces (the honest translation of "agent trajectories")
**What.** A `--trace` flag on the pipeline that emits a readable markdown trace,
plus **three** committed traces in `TRAJECTORIES.md`:
- **SC-01** — the full happy path, all seven stages, both LLM calls verbatim
- **SC-08** — the abstention path, showing *why* the gate declined
- **SC-14** — the injection path, showing the malicious snippet arriving as
  evidence and being treated as inert

Each shows: stage input → computation → output → tier cap declared → gate
decision, with the exact prompt, the exact response, the validator verdict, and
any retry.

**Why.** It makes the system inspectable without cloning it, and it is where you
place the "why not an agent?" answer — in context, next to the trace that proves
the flow is the same every time.

> **Do not add:** an agent loop, tool-calling, a planner, or a multi-agent
> orchestration layer to make the traces look more "agentic." That would trade
> your actual differentiator for a rubric you are not being marked against.
> A deterministic trace is a *better* artefact than an agent trajectory: it is
> replayable, diffable and identical on the judge's machine.

**Impact:** high. **Effort:** ~half a day (the pipeline context object already
holds most of it). **Verdict: ESSENTIAL.**

---

### C-4 — README rewritten user-first
**What.** Restructure so the first screen is: **who** (Priya, category manager at
a mid-size retailer), **the bottleneck** (Tuesday's dashboard says −8%; the
answer arrives Friday, after the decision), **why it costs money**, **what
GlassBox changes**, and **one screenshot**. Architecture, benchmarks and setup
follow. Then: two ways in — the live link, or `make reproduce`.

**Why.** Judges are reading twenty repos. The first 200 words decide whether the
rest gets read carefully or skimmed. And "problem & user value" is a scored line
on both rubrics.

**Impact:** high. **Effort:** ~3 hours. **Verdict: ESSENTIAL.**

---

### C-5 — REPRODUCE.md, tested on a machine that has never seen this project
**What.** Exact commands from a clean OS; Python version; dependency install;
data generation; baseline run; system run; evaluation run; expected output with
a sample of the actual expected numbers; runtime per step; cost (≈ $0 in replay
mode, and say so); and a **troubleshooting table** of the three failures you
actually hit.

**Why.** "Gives another person a clear path… from a clean environment" is 15% of
the borrowed rubric and implicitly most of your prototype mark. The
troubleshooting table is the tell that you actually ran it — nobody writes one
from imagination.

**Impact:** high. **Effort:** ~3 hours writing, plus one hour of real testing at
T−7 on a machine you have not developed on (a friend's laptop, a fresh VM, or a
GitHub Codespace). **Verdict: ESSENTIAL — and schedule the test, do not assume it.**

---

### C-6 — Prompts as versioned repo artefacts
**What.** `prompts/intent_parse.md` and `prompts/narrate.md` with version
headers, plus a short `prompts/README.md` stating that exactly two LLM calls
exist and what constrains each. *(Already scaffolded in this kit.)*

**Why.** It is the part of an LLM system a judge most wants to read and most
often cannot find.

**Impact:** medium-high. **Effort:** already done — keep them in sync as you
build. **Verdict: ESSENTIAL (maintenance only).**

---

### C-7 — The hot take / failure mode section
**What.** Close the README with 200 honest words. The strongest available take,
and it is genuinely yours:

> **The failure mode of analytics AI is fluency, not accuracy.** A model asked
> why revenue fell will always produce a fluent, plausible, well-structured
> answer — including when the data contains no answer at all. Fluency is
> indistinguishable from correctness at reading speed, which is exactly when a
> business decision gets made. So we built the system to be *capable of
> declining*, and then measured how often it declines when it should. Our
> hardest engineering problem was not finding causes. It was building something
> that would stay quiet.

Then state your real limitation: causal claims rest on quasi-experimental tests
over observational data. Difference-in-differences with contaminated controls is
suggestive, not proof. GlassBox's tiers are honest *about* that — TESTED means
"survived our falsification attempts," not "proven" — but a determined
confounder still defeats it, and SC-12 is the scenario where you can see it
happen.

**Impact:** medium-high, disproportionate to effort. **Effort:** 1 hour.
**Verdict: ESSENTIAL.**

---

### C-8 — JUDGES.md, a five-minute evaluation path
**What.** One page: *if you have 5 minutes, do these four things.* Click the live
link → run SC-01 → run SC-08 and watch it decline → open the scorecard. If you
have 30 minutes: `make reproduce`, then here is the trace to read.

**Why.** Judges are time-poor. Directing their attention is free points; you
choose which four things they see, and they will thank you for it.

**Impact:** medium-high. **Effort:** 1 hour. **Verdict: ESSENTIAL.**

---

### C-9 — Hosted demo link
**What.** Streamlit Community Cloud, replay mode, no API key required. README
line one: *"Try it live — no install."*

**Why.** Most judges will never clone your repo. They click, watch, and skim.

**Impact:** high **if it works**, negative if it is slow, asleep or broken.
**Effort:** ~2 hours including the cold-start check.
**Verdict: ESSENTIAL — but only after the never-cut list is green.** A hosted
demo of a half-built engine is worse than no link. And **never demo live off the
free tier** during the pitch — run locally, use the link only as the judges'
self-service path.

---

### C-10 — Scenario picker + "try to break it" tab
**What.** A dropdown of SC-01…SC-17 so a judge replays anything themselves,
*including the scenarios you fail*; and a tab where they can type their own
prompt-injection or request data their persona cannot see — ending with
*"everything you just tried is in the audit log."*

**Why.** Interactivity converts a demo into an experiment the judge runs. Letting
them see your misses is counter-intuitively the strongest credibility move in the
build: it says the scorecard is real.

**Impact:** medium-high. **Effort:** ~half a day (mostly UI).
**Verdict: STRONGLY RECOMMENDED — first thing to cut if you are behind.**

---

### C-11 — Traceability matrix as an appendix slide
**What.** The 22-item Round 2 objective checklist, each mapped to a specific
artefact, screen or scenario, with a status column.

**Why.** Turns a subjective impression into a list where you score full marks,
and it is unique to the Accenture brief (the borrowed rubric has nothing like it).

**Impact:** medium-high **for your actual competition**. **Effort:** 2 hours.
**Verdict: ESSENTIAL — this one comes from your real brief, not the borrowed one.**

---

### C-12 — Cost and latency receipt
**What.** A committed `eval/cost_receipt.md`: tokens, USD per run, p50/p95
latency, rows scanned. Rendered as a footer in the UI too.

**Why.** Almost no prototype can answer "what does one of these cost to run?"
Being able to is a small, memorable signal of production thinking — and it is one
of Track 3's explicit prototype expectations.

**Impact:** medium. **Effort:** 2 hours (telemetry already in the findings schema).
**Verdict: RECOMMENDED.**

---

### C-13 — ADRs (architecture decision records)
**What.** Five short records: why deterministic-first; why no vector DB; why no
agent loop; why synthetic primary data; why tiers are rule-assigned.

**Why.** Judges assessing "engineering" want to see decisions with trade-offs,
not just outcomes. Each is ~150 words and doubles as Q&A prep.

**Impact:** medium. **Effort:** 2 hours. **Verdict: RECOMMENDED.**

---

### C-14 — R1 → R2 promise tracker
**What.** A short table: the three commitments your Round 1 deck made (live
semantic layer, context registry, analyst-verdict loop) → where each is now, with
a link.

**Why.** The judges have your R1 deck. Those commitments are a contract. Hitting
all three *and naming them in the pitch* is free credibility that no other team
can copy, because they did not make your promises.

**Impact:** medium. **Effort:** 1 hour. **Verdict: RECOMMENDED.**

---

### Do NOT add these

Each of these is a plausible-sounding improvement that costs days and returns
nothing, or actively damages the submission. If you find yourself building one,
stop.

| Do not add | Why not |
|---|---|
| **An agent loop / tool-calling / multi-agent orchestration** | Contradicts the product thesis. A trust system needs a replayable control flow. The borrowed rubric's 30% line does not apply to you. Write the *reason* down instead — it scores better than the feature would. |
| **A vector database** (Pinecone, Weaviate, Chroma-as-a-service) | 490 documents fit in memory. Saying "we measured it; a vector DB would add an operational dependency and no measurable recall" scores *higher* than adding one. Engineering judgement is the mark, not component count. |
| **Real SSO / OAuth** | Days of work for a login screen. The disclosed persona switcher demonstrates the same access-control story and is honest about being a simulation. |
| **Kafka / a real streaming layer** | The replay clock plus a declared production path on one slide gets the full mark. Nobody is scoring your broker. |
| **A Tableau / Power BI / Looker embed** | Days of brittle integration for a screenshot. Show the Slack/email/workspace render instead — it makes the same "meets users where they are" point in half a day. |
| **A second or third LLM touchpoint** | Every additional call weakens "five of seven stages never touch a model," which is your headline. The cap of 2 is in the findings schema on purpose. |
| **More scenarios beyond 17** | 17 is already more than any judge will inspect. Depth of evidence per scenario beats breadth. |
| **A fine-tuned model** | Weeks of work, unreproducible for a judge, and it undermines "no data leaves the tenant." Say plainly: nothing is trained; baselines are fit per-KPI, the model is used as-is. |
| **A React frontend** | The webpage is ~20% of the marks. Streamlit is the correct trade, and rewriting it late is how teams lose their last week. |
| **Retrofitting the changelog at T−2** | Worse than having none. `git log` disagrees with it and the disagreement is visible. |

---

## D. Final submission architecture

How the pieces fit. Six artefacts, one job each, no overlap.

```
                        ┌──────────────────────────┐
                        │   JUDGE ARRIVES HERE     │
                        │        README.md         │
                        │  user → bottleneck →     │
                        │  what changes → 1 shot   │
                        │  → 2 doors + hot take    │
                        └────────────┬─────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
      ┌───────▼───────┐     ┌────────▼────────┐    ┌────────▼────────┐
      │  5-MIN PATH   │     │   30-MIN PATH   │    │  SKEPTIC PATH   │
      │  JUDGES.md    │     │  REPRODUCE.md   │    │ TRAJECTORIES.md │
      │               │     │                 │    │                 │
      │ hosted link   │     │ clean env →     │    │ SC-01 full run  │
      │ SC-01 demo    │     │ make reproduce  │    │ SC-08 declining │
      │ SC-08 decline │     │ → scorecard     │    │ SC-14 injection │
      │ scorecard     │     │ → runtime/cost  │    │ + why not agent │
      └───────┬───────┘     └────────┬────────┘    └────────┬────────┘
              │                      │                      │
              └──────────────────────┼──────────────────────┘
                                     │
                        ┌────────────▼─────────────┐
                        │      THE EVIDENCE        │
                        ├──────────────────────────┤
                        │ eval/scorecard.md        │  GlassBox, 17 scenarios
                        │ eval/baseline_scorecard  │  B1 naive / B2 published / B3 one-prompt
                        │ eval/rs_benchmark.md     │  135 real anomalies, 7 published algos
                        │ eval/cost_receipt.md     │  tokens, USD, p50/p95
                        │ CHANGELOG.md             │  evidence→problem→decision→change→result
                        │ CI: .github/workflows    │  the history of our own results
                        └────────────┬─────────────┘
                                     │
                        ┌────────────▼─────────────┐
                        │       THE SYSTEM         │
                        │  contracts/ prompts/     │
                        │  engine/ app/ tests/     │
                        │  data/generate.py +      │
                        │  injection_manifest.yaml │
                        │  (committed FIRST)       │
                        └──────────────────────────┘
```

**Two rules that keep this coherent:**

1. **Every claim points at an artefact.** No sentence in the README, the deck or
   the video asserts a capability that does not have a file, a screen or a
   scenario behind it. When you cannot point, delete the claim — a deleted claim
   costs nothing; an unbacked one costs the judge's trust in *all* your claims.

2. **One number, one home.** Accuracy lives in the scorecard. Cost lives in the
   receipt. Latency lives in telemetry. The README quotes them; it does not
   restate them independently, or they will drift and a judge will find the
   inconsistency.

**How the deck and the video attach:** the video is the 3-minute cut (SC-01,
SC-08, SC-14, scorecard). The deck's opening is structured around the three
"think about" questions the R1 brief asked — noise vs signal, correlation to
action, genuine ambiguity — each answered with a demo scene rather than a bullet.
The traceability matrix is the appendix.

---

## E. Final judge perspective

*Written as a Round 2 judge opening this submission cold, having already seen
eleven others that morning.*

> Another BI-copilot. That is the fourth today — I will give it ninety seconds.
>
> …The README opens with a person, not an architecture. Fine, that is one thing
> the others did not do.
>
> There is a live link. It works. I click "Net Revenue −8.2%" and it does what
> the last three did — but each sentence has a confidence label, and one says
> CORRELATED where I would have expected the team to overclaim. Interesting.
>
> There is a scenario dropdown. I pick one at random — SC-08 — and the system
> **refuses to answer**. It lists four things it ruled out and tells me to ask
> the Payments team. I go back and re-read: the movement is real, the cause was
> never planted. They built a case where their own product looks like it failed,
> and put it in the picker.
>
> Now I want to know whether that is engineering or luck. The scorecard is
> committed, with misses. There is a baseline table: the same model given the
> same data in one prompt invents a cause for SC-08 with high confidence. That
> is the argument, and they made it with a measurement instead of a claim.
>
> The changelog has eleven entries, each naming a commit and a scorecard delta,
> including one that says a change made retrieval worse and was reverted. I check
> `git log` against it. It agrees.
>
> The injection manifest was committed twelve days before the engine code. So the
> ground truth was fixed before the results existed. Almost nobody does that.
>
> **What I would push on in Q&A:**
> - "Your primary dataset is synthetic. Why should I believe any of it?"
>   *(They must answer instantly: the RS benchmark on 135 real labelled anomalies
>   is exactly this objection's answer — and the reason the ideal public dataset
>   does not exist is documented, not asserted.)*
> - "You call this an AI system but most of it is statistics." *(Say yes,
>   proudly, and give the number: five of seven stages. That is the design.)*
> - "Would this survive a real warehouse with 400 metrics and no contracts?"
>   *(The honest answer is that the contract is the adoption cost, and phase 1 is
>   five metrics, not four hundred. Do not oversell here — the honest answer is
>   the better one, and a consultant judge will respect the delivery framing.)*
> - "Who on the team wrote what?" *(git log is public. Make sure it is true.)*
>
> **Where it would lose marks:** the UI is plainly a Streamlit prototype; the
> business case rests on estimated analyst-hours rather than a customer; and the
> causal claims are quasi-experimental, which the team says out loud — I would
> rather they said it than that I found it.
>
> **Verdict:** the only submission today where I believed the numbers, because it
> was the only one that showed me a case where it lost.

That last line is the whole strategy. **Optimise for being believed, not for
looking perfect.** A perfect-looking demo from a student team invites suspicion;
a demo with a visible, measured, explained failure invites trust — and trust is
the literal subject of your product, so demonstrating it in the *submission
itself* is thematically coherent in a way judges notice even when they cannot
name why.

---

## F. Final checklist

Full version lives in `CHECKLIST.md` (tick it there, commit it daily, so its own
git history becomes evidence of process). Summary:

### Never cut — if these are not green, nothing else matters
- [ ] All 7 stages run end to end on generated data, no hard-coding
- [ ] Change a date, re-run, real numbers come out
- [ ] SC-01 works (the hero scenario)
- [ ] SC-08 works (the abstention — protect this above all)
- [ ] Tiers on every sentence, assigned by rule
- [ ] `make reproduce` completes from a clean clone
- [ ] Scorecard committed, misses included
- [ ] Injection manifest committed before engine code

### Evidence
- [ ] `eval/scorecard.md` — 17 scenarios, current
- [ ] `eval/baseline_scorecard.md` — B1, B2, B3
- [ ] `eval/rs_benchmark.md` — external, real, published algorithms
- [ ] `eval/cost_receipt.md`
- [ ] `CHANGELOG.md` — ≥8 entries, written live, agreeing with `git log`
- [ ] CI green, scorecard auto-published

### Documentation
- [ ] README — user-first, screenshot, two doors, hot take, failure mode
- [ ] REPRODUCE.md — **tested on a machine that never built this**
- [ ] TRAJECTORIES.md — SC-01, SC-08, SC-14 + "why not an agent"
- [ ] JUDGES.md — the 5-minute path
- [ ] `prompts/` — both prompts, versioned, in sync with the code
- [ ] ADRs — 5
- [ ] Traceability matrix — 22 items, each pointing at an artefact
- [ ] R1 → R2 promise tracker — all three commitments named

### Submission mechanics
- [ ] Public GitHub repo, MIT, no secrets anywhere in history
- [ ] No Olist data committed, ever (CC BY-NC-SA)
- [ ] Demo video, 2–3 minutes, timestamped, SC-08 and SC-14 protected
- [ ] Deck on the **Round 1 template** (AIC Talent-Brand PPT template)
- [ ] Business proposal: users, impact, phased roadmap, risks + mitigations
- [ ] Hosted demo link live and awake, checked the morning of submission
- [ ] Both of you can defend every file in Q&A

### The three things that must happen on a schedule, not when convenient
- [ ] **Phase 0:** commit the injection manifest *before* any engine code
- [ ] **T−10:** count green scenarios; if under 13/17, cut in the pre-agreed order
- [ ] **T−7:** test `make reproduce` on the other person's machine

---

*One last thing. The temptation in the final week is to add. Almost every
improvement in this document is a way of making what you already have legible,
not a way of making it bigger. If you are choosing between one more feature and
one more piece of evidence, the evidence wins every time — it is what a judge can
actually check.*
