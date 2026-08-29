<!-- Every number below was measured this session, on this machine (Windows,
     no `make` installed - which is itself the first troubleshooting entry).
     Not a clean-room test on a second machine yet - see the note at the end. -->

# Reproduce our results

Assumes you have never seen this project and are starting from a clean
machine. **No API key is required.** The two LLM touchpoints fall back to a
deterministic parser and a template narrator when no key is configured — see
`TRAJECTORIES.md` for exactly what that output looks like.

**There is no UI yet.** Steps 1-3 and 7 below (setup, data, eval, tests) are
real and work today. Steps 4-6 (baselines, RS benchmark, app) are honestly
marked as not yet built rather than described as if they worked.

---

## 0. Requirements

| | |
|---|---|
| OS | This guide was run on Windows 11 without `make` installed (see step 8) — every command below also has a plain `python`/`pip` form. Should work unmodified on Linux/macOS. |
| Python | **3.11+** (tested on 3.12.10; the codebase uses `X \| Y` union type syntax, so 3.10 and below will not work) |
| Disk | **~1.3 GB** for the virtualenv (dominated by PyTorch, a `sentence-transformers` dependency) + **~35 MB** for the generated dataset |
| RAM | Not separately profiled; nothing in this pipeline holds more than the ~1.2M-row order table in memory at once |
| Network | Only for `pip install` (and the first `sentence-transformers` embedding-model download, ~90 MB). Everything after runs offline. |
| Time | Install: budget **10+ minutes** — in this session, a fresh venv install exceeded 5 minutes even with a warm pip cache, dominated by the PyTorch download. Data generation: **~10-25s**. Full eval (17 scenarios): **~26s**. Tests: **~29s**. |
| Cost | **$0.00** — no live model call happens without an explicit key |

---

## 1. Clone and install

```bash
git clone <this repo>
cd glassbox
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # `make setup` does the same thing, if you have make
```

**Verify:**
```bash
python -c "import duckdb, pandas, statsmodels, networkx, sentence_transformers; print('ok')"
```

---

## 2. Generate the dataset — ~10-25s

```bash
python data/generate.py --seed 20260829 --out data/generated    # or: make data
```

Builds Meridian Electronics from the committed seed: ~16.5 months of history
(2025-04-01 → 2026-08-21), **1,233,134 orders**, 135,444 session-aggregate
rows, and 496 support tickets/CRM notes/field reports/change logs/vendor
emails — with all 17 scenarios from `data/injection_manifest.yaml` planted.

**Deterministic.** The same seed gives the same output; file hashes are
written to `data/generated/DATA_HASHES.json` on every run so you can diff
your run against a known-good one without eyeballing a database.

**Expected tail of output:**
```
Generating Meridian: 2025-04-01 -> 2026-08-21 (508 days)
  cells: 146,304 rows
  sessions rows: 135,446   orders: 1,233,134
  documents: 496
  wrote data\generated\meridian.duckdb
  wrote data\generated\documents.jsonl
  wrote data\generated\DATA_HASHES.json
  sha256 meridian.duckdb: <64 hex chars>
  sha256 documents.jsonl: <64 hex chars>
```

**Verify:**
```bash
python -c "import duckdb; con = duckdb.connect('data/generated/meridian.duckdb', read_only=True); print(con.execute('select count(*) from fact_orders').fetchone())"
# (1233134,)
```
(Use `read_only=True` and `.fetchone()` rather than printing the relation
directly — see Troubleshooting below for why.)

---

## 3. Run the evaluation — ~26s

```bash
python -m eval.harness --scenarios all --out eval/scorecard.md    # or: make eval
```

Runs all 17 scenarios through the real pipeline, scores against ground truth,
and writes both `eval/scorecard.md` and `eval/cost_receipt.md`.

**Expected — this should match the committed `eval/scorecard.md` exactly**
(reran this twice in the same session and diffed byte-for-byte identical,
aside from the commit-hash line in the header):
```
Totals: 7/17 pass · RCA top-1 2/13 answerable · hallucinated causes 0/17
abstention precision 0.25 (1/4) · recall 1.00 (1/1) · hallucinated-cause rate 0.00
```

If your numbers differ, that's a real bug — tell us. The pipeline has no
unseeded randomness anywhere under `engine/` or `eval/` (checked by grep, not
assumed), so this should never vary run to run on the same code and data.

---

## 4. Baselines — not yet built

```bash
python -m eval.harness --baseline --out eval/baseline_scorecard.md    # or: make baseline
```

This command exists in the CLI but `eval/baselines/` only has its README —
the B1 (naive drill-down) and B3 (single-LLM-prompt) implementations aren't
written yet. Running it will fail with an import error. `eval/baseline_scorecard.md`
is committed as an honest "NOT YET GENERATED" placeholder rather than left
missing or faked. Status: `CHECKLIST.md` Phase 6.

---

## 5. The external RS benchmark — not yet run

```bash
make fetch-rs      # clones RiskLoc (MIT) — network access needed, not committed here
```

The clone step itself works (verified network access to GitHub from this
environment). Running the comparison against the 135 real anomalies and
seven published algorithms has not been done. `eval/rs_benchmark.md` is
committed as an honest placeholder for the same reason as above.

---

## 6. The app — not yet built

```bash
streamlit run app/main.py    # or: make app
```

`app/main.py` currently raises `NotImplementedError`. There is no UI to tour
yet. Everything a UI would show you — the tiered narrative, the evidence
drawer's contents, the entitlements diff between personas — is directly
readable from a real run's output; see `JUDGES.md`'s 15-minute path for the
Python-shell equivalent of each planned screen.

---

## 7. Tests — ~29s

```bash
pytest -q    # or: make test
```

8 tests. Four must never be weakened — see their docstrings:
`test_gate_invariant`, `test_tiers_monotone`,
`test_validator_blocks_invented_numbers`, and `test_findings_schema_valid`
(validates every scenario's output against the frozen
`schemas/findings.schema.json`).

---

## 8. One command — if you have `make`

```bash
make reproduce     # setup → data → eval → test
```

**This machine doesn't have `make` installed** (confirmed: `which make`
returns nothing on this Windows box, no WSL). If yours doesn't either, run
steps 1, 2, 3 and 7 above directly — that's the entire content of the
`reproduce` target; nothing else happens inside it.

---

## 9. Troubleshooting

Real failures hit while writing this guide, not invented ones:

| Symptom | Cause | Fix |
|---|---|---|
| `SyntaxError` on `str \| None` | Python ≤ 3.10 | Use 3.11+ |
| `make: command not found` | No `make` on this machine (plain Windows, no WSL) | Use the `python -m ...` form of each target shown above — every target is one line |
| `duckdb.duckdb.ConnectionException: Connection has already been closed` | Another process still holds the DuckDB file open (e.g. a previous script that didn't close its connection, or a concurrent `du`/backup process scanning the file) | Close other processes touching `data/generated/meridian.duckdb`, or open with `read_only=True` |
| `UnicodeEncodeError: 'charmap' codec can't encode characters` when printing a DuckDB relation directly in a Windows terminal | DuckDB's pretty-printed table repr uses box-drawing Unicode characters the default Windows `cp1252` console encoding can't render | Call `.fetchone()` / `.fetchall()` and print the plain Python value instead of printing the relation object |
| `pip install` takes much longer than expected | `sentence-transformers` pulls in PyTorch, which is large (~600MB-1GB depending on platform) | Expected — budget 10+ minutes on a fresh install, more on a slow connection |
| Embedding-based retrieval silently falls back to BM25-only | No network access to download the `all-MiniLM-L6-v2` model on first use | Expected degradation, not a bug — `engine/stages/s05_retrieve.py` catches this and continues with BM25 alone, same as it would with `sentence-transformers` uninstalled |

---

## 10. Runtime and cost summary

| Step | Time (measured, this session) | Cost |
|---|---|---|
| Install | 10+ min (dominated by PyTorch download) | $0 |
| Generate data | ~10-25s | $0 |
| Evaluate (17 scenarios) | ~26s | $0 (no live model call configured) |
| Baselines | not built | — |
| Tests | ~29s | $0 |
| **Steps 1+2+3+7 combined** | **~11-12 min, install-dominated** | **$0** |

Per-run token/latency/cost telemetry across all 17 scenarios:
[`eval/cost_receipt.md`](eval/cost_receipt.md) — genuinely $0.00 in this
environment because no live LLM key is configured, not a rounded number.

**What this guide is not yet:** a true clean-machine test performed by
someone other than the person who wrote the code, on a second physical
machine, per `docs/01_MASTER_BUILD_FLOW.md`'s own T−7 gate. Every number
above is real and was measured this session, but on one machine, by one
person. That second-machine test is still open — see `CHECKLIST.md`.
