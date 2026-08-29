<!-- ===================================================================== -->
<!-- TEMPLATE. Rewrite at Phase 7 with real numbers.                       -->
<!-- Every ⟪FILL⟫ must be replaced or deleted before the repo goes public. -->
<!-- Never leave a placeholder in a public repo — it is the single most    -->
<!-- visible sign of a submission finished at 3am.                         -->
<!-- ===================================================================== -->

# GlassBox

**Every dashboard tells you *what* changed. GlassBox tells you *why*, shows you
the evidence, and tells you how much to trust it — and says "I don't know" when
the data doesn't support an answer.**

⟪FILL: **[▶ Try it live](URL)** — no install, no API key⟫ · [5-minute evaluation guide](JUDGES.md) · [Reproduce our results](REPRODUCE.md) · [Run traces](TRAJECTORIES.md) · [Improvement changelog](CHANGELOG.md)

---

## The person this is for

Priya runs the Audio category at a mid-size electronics retailer. On Tuesday
morning her dashboard shows net revenue in the South down 8.2% — about ₹3.1
crore. The dashboard tells her *that*. It cannot tell her *why*.

So she files a request. An analyst pulls the numbers, slices by region and
channel, finds nothing conclusive, asks the supply-chain team, waits, reads
forty support tickets, and comes back on **Friday** with: *"it looks like
delivery times slipped in three southern hubs."*

The decision was made on Wednesday.

**This is the bottleneck.** Not the dashboard — dashboards are good at what they
do. The translation from *what changed* to *why, and what to do* is manual, it
takes three to four analyst-days, and it finishes after the window in which it
mattered. At a mid-size retailer that is ⟪FILL: N⟫ investigations a month and
⟪FILL: N⟫ analyst-days a year, and the real cost is not the salary — it is the
decisions made without the answer.

**What GlassBox changes:** the same investigation, run automatically, in under a
minute, with every claim graded and every source cited. Priya opens Tuesday's
alert and reads a two-paragraph answer with four cited tickets, a rival cause
that was tested and rejected, and a recommended action with an owner.

And when the data genuinely doesn't contain an answer, it says so — which is the
part that took the longest to build.

⟪FILL: screenshot of the findings view — tiered sentences, evidence drawer open⟫

---

## How it works

Seven stages. **Five of them never touch a language model.**

```
question or alert
   ↓
00 INTENT     ◆ text → {kpi, segment, window}, from contract vocabulary only
01 DEFINE     ● the metric's governed definition → SQL → series
02 DETECT     ● seasonal baseline · is this signal or noise?
03 LOCALIZE   ● which segment actually moved
04 DECOMPOSE  ● price vs volume vs mix
05 RETRIEVE   ● tickets, CRM notes, field reports — who already noticed
06 FALSIFY    ● try to disprove each candidate cause
   ↓ gate:  answer  |  abstain  |  clarify
07 NARRATE    ◆ write it, with every number validated against the computation

● deterministic     ◆ the only two model calls
```

The model turns a question into a query, and a finished result into a sentence.
**It never decides what is true.** Every number in the output is re-extracted and
matched against the computed findings before it reaches a human; unmatched output
is regenerated, then falls back to a template.

Every sentence carries a confidence tier:

| | |
|---|---|
| `VERIFIED` | Recomputed from source. Arithmetic, not judgement. |
| `EVIDENCED` | Supported by specific documents we can show you. |
| `TESTED` | We tried to disprove this and failed. |
| `CORRELATED` | Moves together with the metric. Not established as a cause. |
| `HYPOTHESIS` | A plausible lead with no support yet. |
| `UNKNOWN` | We are not willing to grade this. |

Tiers are assigned by a rule table, never by the model. Removing evidence can
never raise one — that property is unit-tested.

---

## Does it work?

⟪FILL from `eval/scorecard.md` — never retype numbers, quote the committed file⟫

**17 pre-registered scenarios** on data where we planted the causes, so we know
the right answers:

| | GlassBox | B1 naive drill-down | B3 single LLM prompt |
|---|---|---|---|
| Scenarios passed | ⟪ /17⟫ | ⟪ /17⟫ | ⟪ /17⟫ |
| Root cause, top-1 | ⟪ ⟫ | ⟪ ⟫ | ⟪ ⟫ |
| Localization F1 | ⟪ ⟫ | ⟪ ⟫ | — |
| **Hallucinated causes** | ⟪ ⟫ | ⟪ ⟫ | ⟪ ⟫ |

**On real data:** segment localization against seven published algorithms
(Adtributor, Squeeze, RiskLoc and others) on 135 real anomalies with
operator-assigned causes → [`eval/rs_benchmark.md`](eval/rs_benchmark.md).

**The ground truth was frozen before the engine existed.** Commit
`c908ef9bd569befc754c8b28d1db99b4ba590f52` contains `data/injection_manifest.yaml`
and predates the first commit under `engine/`. Check it:
`git log --follow data/injection_manifest.yaml`.

**The scorecard includes our failures**, with an explanation for each. Some of
them are the system behaving correctly under a hard case; we say which.

### The result we care about most

On **SC-08**, the data contains a real, material 7.3% drop and **no planted
cause**. Same model, same data, one prompt versus our pipeline:

> **Single prompt:** *"Revenue fell 7.3%, primarily driven by reduced promotional
> activity and softer demand across the South region."* — confident, fluent, and
> entirely invented. No promotional change occurred.
>
> **GlassBox:** *"I could not establish a cause. Ruled out: promotional calendar
> (unchanged), delivery SLA (stable), payment failures (0.3%, within normal
> range), traffic mix (unchanged). Suggest asking the Payments team about
> settlement timing."* — **Confidence: UNKNOWN.**

---

## Trust and deployment

**GlassBox ships to the data, never the reverse.** In production it runs inside
the customer's own cloud tenant, reads their warehouse through a read-only
service account, and reaches the model through a private endpoint in their own
subscription. Five of seven stages never touch a model; the model sees a
minimised, redacted findings object and snippets of documents the asking user was
already entitled to read.

Demonstrated in the prototype, not just claimed:

- **Prompt injection** — a malicious support ticket is retrieved, quoted as
  evidence, flagged, and ignored *(SC-14 — try it in the picker)*
- **Small-cell suppression** — a movement localizing to four orders is rolled up
  so no individual is inferable *(SC-15)*
- **Role-based access** — three personas, the same movement, different SQL,
  different answers *(SC-13)*
- **Audit log** — every run: who asked, what was computed, what was withheld

Details in [`docs/06_SECURITY_TRUST.md`](docs/06_SECURITY_TRUST.md).

---

## Run it

```bash
git clone ⟪FILL: repo URL⟫ && cd glassbox
make reproduce        # setup → generate data → run 17 scenarios → tests
make app              # the UI at localhost:8501
```

Works offline. No API key: model responses are served from a committed replay
cache, and the UI says when it is replaying. Full guide, expected outputs,
runtimes and troubleshooting: [REPRODUCE.md](REPRODUCE.md).

⟪FILL: Model used in live mode: NAME. Justification: ... (required by the
submission checklist — name the provider you actually ran, truthfully)⟫

---

## What's in here

```
engine/       the pipeline — one file per stage
contracts/    semantic contracts: definition + lineage + access + drivers
prompts/      both prompts, versioned — the only two model calls
data/         generator + the frozen injection manifest (ground truth)
eval/         harness, metrics, baselines, committed scorecards
app/          Streamlit UI (deliberately thin — the engine is the product)
docs/         architecture, evaluation plan, data strategy, ADRs
```

---

## Our hot take

**The failure mode of analytics AI is fluency, not accuracy.**

A model asked why revenue fell will always produce a fluent, plausible,
well-structured answer — including when the data contains no answer at all. And
fluency is indistinguishable from correctness at reading speed, which is exactly
the speed at which a business decision gets made. The dangerous output is not the
one that is obviously wrong. It is the one that is confidently, articulately
wrong about a number someone is about to act on.

So we built the system to be *capable of declining*, and then measured how often
it declines when it should. Our hardest engineering problem was not finding
causes. It was building something that would stay quiet.

**And our honest limitation:** GlassBox's causal claims rest on quasi-experimental
tests over observational data. Difference-in-differences against imperfect control
segments is suggestive, not proof. The tiers are honest about this — `TESTED`
means "survived our falsification attempts", not "proven" — but a confounder that
moves with the true cause across every control segment will defeat it. **SC-12 is
that scenario, it is in the picker, and you can watch the tier degrade from
TESTED to CORRELATED rather than the system guessing.** That degradation is the
system working. It is also the ceiling of what this method can claim.

---

⟪FILL: team, licence line, dataset attributions (RiskLoc MIT · PSqueeze CC BY 4.0),
and — if the competition rules require it — the AI-assistance disclosure line⟫
