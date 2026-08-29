# GlassBox

**Every dashboard tells you *what* changed. GlassBox tells you *why*, shows you
the evidence, and tells you how much to trust it — and says "I don't know" when
the data doesn't support an answer.**

**No live demo yet — the UI (`app/main.py`) isn't built. Everything below is
verifiable directly in this repo: real code, a real committed dataset, and a
scorecard you can regenerate yourself with no API key.**
[5-minute evaluation guide](JUDGES.md) · [Reproduce our results](REPRODUCE.md) · [Run traces](TRAJECTORIES.md) · [Improvement changelog](CHANGELOG.md)

---

## The person this is for

Priya runs the Audio category at a mid-size electronics retailer. On Tuesday
morning her dashboard shows net revenue in her category down sharply in the
South — a real run of this system, on the committed dataset, measures it at
-23.5% (-₹34,99,600) against the prior week ([full trace](TRAJECTORIES.md#1-sc-01--the-hero-all-seven-stages)).
The dashboard tells her *that*. It cannot tell her *why*.

So she files a request. An analyst pulls the numbers, slices by region and
channel, finds nothing conclusive, asks the supply-chain team, waits, reads
forty support tickets, and comes back days later with: *"it looks like
delivery times slipped in southern hubs."*

**This is the bottleneck.** Not the dashboard — dashboards are good at what they
do. The translation from *what changed* to *why, and what to do* is manual and
it finishes well after the window in which it mattered. (We don't have primary
research on exactly how many investigations a month this costs a retailer like
Priya's employer — that number needs a real customer conversation, not an
invented statistic, so we're not printing one here.)

**What GlassBox changes:** the same investigation, run automatically, with
every claim graded and every source cited. On the run above, GlassBox found
the same underlying cause — a South-hub courier capacity cut — cited four
support tickets and a field report, and *also* found and correctly rejected a
second, genuinely plausible cause (a national promotion that ended the same
week): it survived its own significance test at the national level but failed
when checked against South specifically, because the promotion ended
everywhere and South's drop was larger than that alone explains.
[See the full seven-stage trace.](TRAJECTORIES.md#1-sc-01--the-hero-all-seven-stages)

And when the data genuinely doesn't contain an answer, it says so — which is
the part that took the longest to build. [See SC-08.](TRAJECTORIES.md#2-sc-08--the-abstention-path)

*(No screenshot yet — there's no UI to screenshot. The trace above is the real
output, in the format the engine actually produces it.)*

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

Quoted from the committed [`eval/scorecard.md`](eval/scorecard.md) — regenerate
it yourself with `python -m eval.harness --scenarios all --out eval/scorecard.md`,
no API key needed, and it will reproduce these numbers exactly (deterministic,
verified by rerunning it twice in the same session and diffing byte-for-byte):

**17 pre-registered scenarios** on data where we planted the causes, so we know
the right answers:

| | GlassBox |
|---|---|
| Exact-match scenarios passed | 7 / 17 |
| Root cause, top-1 (of scenarios with a segment to match) | 2 / 13 |
| **Hallucinated causes** | **0 / 17** |
| Abstention recall (caught the negative control) | 1.00 (1/1) |
| Abstention precision | 0.25 (1/4) |

*B1 (naive drill-down) and B3 (single-LLM-prompt) baseline columns are not in
this table because they haven't been run yet — B1's harness isn't built, and
B3 specifically needs a live model call to be honest evidence, which this
build environment doesn't have configured. See `eval/baselines/README.md` and
`CHECKLIST.md` for status; we would rather leave the columns out than invent
what they'd show.*

The 10 non-exact scenarios split two ways, neither of which is a fabrication:
3 abstain conservatively where an answer was possible (the system declining
rather than guess), and 7 answer correctly on the right branch, with real
cited evidence, but name a broader or adjacent segment than the exact ground
truth. `eval/scorecard.md`'s Misses section has the specific reason for each.

**On real data:** the RS benchmark (135 real anomalies against seven
published localization algorithms) is planned but has not been run —
`eval/rs_benchmark.md` says so honestly rather than showing invented numbers.

**The ground truth was frozen before the engine existed.** Commit
`c908ef9bd569befc754c8b28d1db99b4ba590f52` is the repo's first commit and
contains `data/injection_manifest.yaml`, before any file under `engine/`
exists. Check it: `git log --follow data/injection_manifest.yaml`.

**The scorecard includes our failures**, with an explanation for each. Some of
them are the system behaving correctly under a hard case; we say which.

### The result we care about most

On **SC-08**, a real run against the committed dataset finds a real, material
-13.3% drop (z = -8.06 — statistically unambiguous) and **no planted cause**.
The corpus is salted with plausible-sounding decoys. GlassBox investigates,
finds nothing that survives a falsification test, and says so:

> *"Net Revenue moved -13.3% in the window to 2026-07-26, but no cause could
> be established that clears the evidence floor."* Ruled out: a Web-channel
> localization that failed its own control-segment check. Referred to
> Analytics, with the specific reason recorded. **Zero causes asserted.**

The obvious next step — the same data and retrieved documents through a
single LLM prompt, to see whether it invents a cause where we don't — is
exactly what a B3 baseline would show, and we don't have a live model call
available in this build environment to run it honestly. We are naming that
gap here rather than writing you a plausible-sounding transcript of what we
expect it would say; see `TRAJECTORIES.md`'s §2 for the full real trace and
`JUDGES.md` for how to run this yourself.

---

## Trust and deployment

**GlassBox ships to the data, never the reverse.** In production it runs inside
the customer's own cloud tenant, reads their warehouse through a read-only
service account, and reaches the model through a private endpoint in their own
subscription. Five of seven stages never touch a model; the model sees a
minimised, redacted findings object and snippets of documents the asking user was
already entitled to read.

Demonstrated in the prototype, not just claimed — no UI picker yet, so these
are traced directly rather than clicked:

- **Prompt injection** — a malicious support ticket is retrieved, quoted as
  evidence, flagged, and ignored. Found doing this in two different scenarios,
  one of them unplanned. *([SC-14 trace](TRAJECTORIES.md#3-sc-14--a-hostile-document))*
- **Small-cell suppression** — a movement localizing below the minimum cell
  size is rolled up to a disclosable level so no individual is inferable
  *(SC-15; `engine/entitlements.py::suppress_small_cells`)*
- **Role-based access** — different personas produce a different SQL predicate
  and a different `entitlements_hash` for the same question — shown directly,
  no UI needed, in [`JUDGES.md`'s 15-minute path](JUDGES.md)
- **Audit log** — every run: who asked, what was computed, what was withheld
  (`engine/audit.py`, append-only JSONL)

Details in [`docs/06_SECURITY_TRUST.md`](docs/06_SECURITY_TRUST.md).

---

## Run it

```bash
git clone <this repo> && cd glassbox
make reproduce        # setup → generate data → run 17 scenarios → tests
```

`make app` is listed in the Makefile but not runnable yet — `app/main.py` is
unbuilt. Everything else above works today. No `make` on your machine
(Windows without WSL, for instance)? The four steps are just:

```bash
pip install -r requirements.txt
python data/generate.py --seed 20260829 --out data/generated
python -m eval.harness --scenarios all --out eval/scorecard.md
pytest -q
```

Works fully offline, no API key required by default
(`GLASSBOX_REPLAY=1` in `.env.example`): the two LLM touchpoints fall back to
a deterministic parser and a template narrator respectively, and every
findings object still validates against the schema and passes the number
validator either way — see `TRAJECTORIES.md` for exactly what that fallback
output looks like. Full guide, expected outputs and troubleshooting:
[REPRODUCE.md](REPRODUCE.md).

**Model used in live mode: Claude (Anthropic), via `engine/llm_client.py`.**
It's the only provider adapter currently implemented there — swapping
providers is meant to be a config change, but only one adapter has actually
been written and exercised.

---

## What's in here

```
engine/       the pipeline — one file per stage
contracts/    semantic contracts: definition + lineage + access + drivers
prompts/      both prompts, versioned — the only two model calls
data/         generator + the frozen injection manifest (ground truth)
eval/         harness, metrics, baselines, committed scorecards
app/          Streamlit UI (not yet built — engine and evidence come first)
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
segments is suggestive, not proof. The tiers are honest about this — `EVIDENCED`
and `TESTED`-equivalent mean "survived our falsification attempts", not
"proven" — but a confounder that moves with the true cause across every
control segment will defeat it. **SC-12 is that scenario** (spillover
contaminates the would-be control segments) — in the current build it
abstains rather than force an answer with degraded confidence, which is a
stricter response than we originally designed for and not the one we'd
ultimately want, but it is still the system declining to overclaim rather
than guessing. `eval/scorecard.md`'s Misses section has the exact reason.
That's the ceiling of what this method can claim, stated as it actually
behaves today, not as we intended it to.

---

**Team Vantage.** MIT licensed (see [`LICENSE`](LICENSE)). External benchmark
datasets used under their own licences where applicable: RiskLoc (MIT),
PSqueeze (CC BY 4.0) — see [`data/README.md`](data/README.md). No Olist or
other CC BY-NC-SA data is committed to this repo, by design
(see `docs/05_DATA_STRATEGY.md` §3).

*If the competition rules require an AI-assistance disclosure, that line
belongs here — we haven't added one because we don't know this competition's
specific rules and it isn't ours to word unilaterally. Flagging it rather
than skipping it silently.*
