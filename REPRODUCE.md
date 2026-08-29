<!-- Finalise at Phase 7, AFTER the T−7 clean-machine test. Replace every ⟪FILL⟫
     with what you actually observed. Times and outputs invented from memory are
     the fastest way to lose a reproducibility mark, because the judge finds out
     within ninety seconds. -->

# Reproduce our results

Assumes you have never seen this project and are starting from a clean machine.
**No API key is required.** Model responses are served from a committed replay
cache; the UI states when it is replaying.

---

## 0. Requirements

| | |
|---|---|
| OS | Linux, macOS, or Windows (WSL2 recommended) |
| Python | **3.11** (3.12 works; 3.10 and below will not — we use `X \| Y` type syntax) |
| Disk | ⟪FILL: ~N MB⟫ |
| RAM | ⟪FILL: peak observed⟫ |
| Network | Only for `pip install`. Everything after runs offline. |
| Time | ⟪FILL: total wall clock⟫ |
| Cost | **$0.00** — replay mode makes no API calls |

---

## 1. Clone and install — ⟪FILL: ~N min⟫

```bash
git clone ⟪FILL: repo URL⟫
cd glassbox
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
make setup                         # pip install -r requirements.txt
```

The first `sentence-transformers` import downloads a small model (~⟪FILL⟫ MB) on
first use. That is the only network access after install.

**Verify:**
```bash
python -c "import duckdb, pandas, statsmodels, networkx; print('ok')"
```

---

## 2. Generate the dataset — ⟪FILL: ~N min⟫

```bash
make data
```

Builds Meridian Electronics from the committed seed: ⟪FILL⟫ months of orders,
sessions, marketing spend and delivery events, plus ⟪FILL⟫ support tickets, CRM
notes and field reports — with the 17 scenarios planted per
`data/injection_manifest.yaml`.

**Deterministic.** The same seed gives byte-identical output.

**Expected:**
```
⟪FILL: paste the actual tail of the output, including the file hashes⟫
```

**Verify:**
```bash
python -c "import duckdb; print(duckdb.connect('data/generated/meridian.duckdb').sql('select count(*) from fact_orders'))"
# ⟪FILL: expected count⟫
```

---

## 3. Run the evaluation — ⟪FILL: ~N min⟫

```bash
make eval
```

Runs all 17 scenarios through the real pipeline and scores against ground truth.
Writes `eval/scorecard.md`.

**Expected — this should match the committed `eval/scorecard.md` exactly:**
```
⟪FILL: paste the real summary block⟫
```

If your numbers differ, something is wrong — **tell us**, that is a bug, not
expected variance. The pipeline is deterministic in replay mode.

---

## 4. Run the baselines — ⟪FILL: ~N min⟫

```bash
make baseline
```

- **B1** naive drill-down — largest single-dimension segment + most recent
  matching ticket
- **B3** single LLM prompt — same aggregates, same retrieved documents, one call

Writes `eval/baseline_scorecard.md`.

> B3 needs a live model to regenerate. **Its responses are committed to the replay
> cache**, so this runs offline and reproduces our exact published comparison. To
> re-run it live: set `GLASSBOX_REPLAY=0` and the four `GLASSBOX_LLM_*` variables
> in `.env` (see `.env.example`). Approximate live cost: ⟪FILL: $ for 17 runs⟫.

**The row that matters** — SC-08, where no cause was planted:
```
⟪FILL: paste the two outputs side by side⟫
```

---

## 5. The external benchmark — optional, ⟪FILL: ~N min⟫

```bash
make fetch-rs      # clones RiskLoc (MIT); not committed here for licence hygiene
python -m eval.harness --benchmark rs --out eval/rs_benchmark.md
```

135 real anomaly cases from a video-delivery system, with operator-assigned
causes, against seven published algorithms. This is the answer to "your primary
dataset is synthetic."

---

## 6. The app — ⟪FILL: ~N sec to first paint⟫

```bash
make app        # → http://localhost:8501
```

**A four-minute tour:**
1. Persona: **Category Manager**. Click **Net Revenue −8.2%** *(SC-01)*.
2. Watch the stages tick. Read the answer — note the tier on each sentence.
3. Open the evidence drawer. Four cited tickets. Note the **rejected** rival cause.
4. Scenario picker → **SC-08**. It declines. That is the pass condition.
5. Scenario picker → **SC-14**. Open the evidence drawer: the flagged malicious
   ticket is there, quoted, and did nothing.
6. Switch persona to **CFO** and re-run SC-01. Different scope, different
   documents, different `entitlements_hash` in the footer.

---

## 7. Tests

```bash
make test
```

Three of these must never be weakened — see their docstrings:
`test_gate_invariant`, `test_tiers_monotone`,
`test_validator_blocks_invented_numbers`.

---

## 8. One command

```bash
make reproduce     # setup → data → eval → test   ·  ⟪FILL: total time⟫
```

---

## 9. Troubleshooting

<!-- Fill this from the failures you ACTUALLY hit during the T−7 clean-machine
     test. A troubleshooting table nobody could have written from imagination is
     the clearest possible signal that the reproduction path was really walked.
     If you hit nothing, you did not test on a clean enough machine. -->

| Symptom | Cause | Fix |
|---|---|---|
| `SyntaxError` on `str \| None` | Python ≤ 3.10 | Use 3.11+ |
| ⟪FILL⟫ | ⟪FILL⟫ | ⟪FILL⟫ |
| ⟪FILL⟫ | ⟪FILL⟫ | ⟪FILL⟫ |

---

## 10. Runtime and cost summary

| Step | Time | Cost |
|---|---|---|
| Install | ⟪FILL⟫ | $0 |
| Generate data | ⟪FILL⟫ | $0 |
| Evaluate (17 scenarios) | ⟪FILL⟫ | $0 (replay) |
| Baselines | ⟪FILL⟫ | $0 (replay) / ⟪FILL⟫ live |
| Tests | ⟪FILL⟫ | $0 |
| **`make reproduce`** | **⟪FILL⟫** | **$0** |

Per-run cost in live mode, measured across all scenarios:
[`eval/cost_receipt.md`](eval/cost_receipt.md).
