# Data Strategy — what we use, why, and what does not exist

---

## 1. The short version

| Role | Dataset | Why |
|---|---|---|
| **Primary** | **Meridian** (synthetic, ours) | The only way to get ground truth for the *whole* pipeline: KPIs + text evidence + known causes + negative controls |
| **External benchmark** | **RiskLoc `data/RS/`** — 135 real anomalies, operator-assigned causes | Real data, real causes, 7 published algorithms, one command. The answer to "your data is synthetic." |
| **Secondary benchmark** | **PSqueeze simulation sets** (Zenodo 8153849, CC BY 4.0) | Additional localization coverage, unencrypted |
| **Optional narrative** | Olist Brazilian e-commerce | Realism colour only. **Never committed** — CC BY-NC-SA |

**Do not use the Squeeze Zenodo record (8153367).** Six of its seven files are
encrypted (`encrypted_B0.tgz` … `encrypted_D.tgz`) with no password published in
the README, the repo or the open issues. The PSqueeze record publishes the same
simulation data unencrypted under CC BY 4.0. Going to the wrong record costs a
day and possibly the whole benchmark.

---

## 2. Why the ideal dataset does not exist — and why that is an argument *for* GlassBox

The dataset we would want contains all four of: **business KPIs + support or
customer text + anomaly labels + explicit root-cause labels.** It does not exist
publicly. That is not a failure of searching; it is structural, and everything
available partitions into four groups, none with all four properties:

| Group | Has | Missing |
|---|---|---|
| KPI-localization benchmarks (Squeeze, RiskLoc, Adtributor-lineage) | Metrics, anomaly labels, cause labels | **No text at all** — dimensions are anonymised `a,b,c,d` |
| AIOps multimodal (LEMMA-RCA and similar) | Metrics + logs + traces, injected faults | Machine logs, service-level causes — not business causes, not customer language |
| Real commercial data (Olist and similar) | Real KPIs, real customer text | **No labels** — nobody recorded why anything moved |
| LLM analytics benchmarks (InsightBench and similar) | Business framing, questions | Free-text insights scored by an LLM judge — not objective ground truth |

Adtributor itself, twelve years on, ran on proprietary Microsoft data and
released nothing; the public benchmarks in its lineage are still anonymised
cubes. **The absence is the market gap.** The reason nobody has built a system
that localizes *and* retrieves evidence *and* falsifies is partly that nobody
could evaluate one.

Say this in the pitch, in one sentence, and it converts your most obvious
weakness — "you made up your data" — into your thesis: *"we had to build the
evaluation because the field never had one."*

---

## 3. Licensing — a public repo makes this a real constraint

| Dataset | Licence | Consequence |
|---|---|---|
| Meridian | Ours, MIT | Ship the generator, not the data |
| RiskLoc | MIT (repo) | `make fetch-rs` clones it; attribute |
| PSqueeze | CC BY 4.0 | Downloadable, attribute |
| Olist | **CC BY-NC-SA** | **Never commit.** Non-commercial *and* share-alike, in a public MIT repo, at a competition run by a consultancy where you are pitching a product. Download script only. |
| LEMMA-RCA | CC BY-NC | Same treatment if used at all |

One pre-emptive line in the proposal closes this: *"Prototype evaluation uses
non-commercial research datasets under their licences; the production system runs
entirely on customer-owned data, so no dataset licence transfers to a
deployment."* Volunteering it is worth more than being asked.

---

## 4. Making synthetic data honest

Synthetic data is only worth something if it is hard. Five rules, all enforced in
`data/generate.py` and visible in the manifest:

1. **Ramps, not steps.** A clean step change is trivially detectable and makes a
   difference-in-differences test unfalsifiable.
2. **Partial spillover.** Effects bleed into neighbouring segments, so "control"
   segments are not pristine. Without this you *construct* the parallel-trends
   assumption the test is supposed to check, and the test can never fail — which
   is exactly the circularity a causal-inference-literate judge will probe.
3. **A contaminated pre-period.** Unrelated small movements before the focal
   window, so the baseline is not artificially clean.
4. **A confounded rival cause.** SC-01's national promo ends in the same week.
   The engine must demote it via the control-segment test, not pick it.
5. **Unmarked negative controls.** SC-08's movement carries no signal
   distinguishing it from a caused one. Nothing in the data lets the engine
   shortcut to "this is the abstention case."

**And documents must be scruffy.** Typos, half-sentences, duplicates,
irrelevant chatter, and decoys that match query keywords but sit outside the
window. Clean well-written tickets make retrieval look far better than it is, and
the SC-08 result depends entirely on decoys being present.

---

## 5. On the Olist controlled-intervention idea

The tempting plan — take a state × category × window, apply a degradation, add
text evidence, and test whether the engine finds it — **is circular as usually
stated.** If you apply a clean multiplicative shift to one segment, leave the
others untouched, and then test with difference-in-differences against those
untouched segments, you have constructed the assumption the test requires. It
cannot fail. A "100% accuracy" result from that design is worth nothing and a
sharp judge will say so.

If you do it at all, it needs the four modifications above (ramp, spillover,
contaminated pre-period, confounded rival) plus three controls: a **placebo
timing** control, an **unaffected-metric** control, and an **unexplainable
movement** control.

**Recommendation: skip it.** Meridian already gives you controlled ground truth
with those properties, and RS gives you real data with real causes. Olist adds a
licence problem and a methodological argument in exchange for realism you can get
by naming Meridian's segments after real retail geography. If you have spare time
at T−6, spend it on E3 and E5 in the evaluation plan instead.
