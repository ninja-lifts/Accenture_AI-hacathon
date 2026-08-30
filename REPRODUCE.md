<!-- Every number below was measured this session, on this machine (Windows,
     no `make` installed - which is itself the first troubleshooting entry).
     Not a clean-room test on a second machine yet - see the note at the end. -->

# Reproduce our results

Assumes you have never seen this project and are starting from a clean
machine. **No API key is required.** `eval/replay_cache/` now holds real,
live-recorded responses for every scored scenario (`CHANGELOG.md` entries
019-028) - a fresh clone with no key configured resumes those exact real
narrations, not a template. Only a scenario with no cached entry at all
falls back to the deterministic parser / template narrator; see
`TRAJECTORIES.md` for what that fallback output looks like.

Steps 1-4 and 6-7 below (setup, data, eval, baselines, app, tests) are real
and work today. Step 5 (the external RS benchmark) is honestly marked as not
yet run rather than described as if it were.

---

## 0. Requirements

| | |
|---|---|
| OS | This guide was run on Windows 11 without `make` installed (see step 8) — every command below also has a plain `python`/`pip` form. Should work unmodified on Linux/macOS. |
| Python | **3.11+** (tested on 3.12.10; the codebase uses `X \| Y` union type syntax, so 3.10 and below will not work) |
| Disk | **~1.3 GB** for the virtualenv (dominated by PyTorch, a `sentence-transformers` dependency) + **~35 MB** for the generated dataset |
| RAM | Not separately profiled; nothing in this pipeline holds more than the ~1.2M-row order table in memory at once |
| Network | Only for `pip install` (and the first `sentence-transformers` embedding-model download, ~90 MB). Everything after runs offline. |
| Time | Install: budget **10+ minutes** — in this session, a fresh venv install exceeded 5 minutes even with a warm pip cache, dominated by the PyTorch download. Data generation: **~10-25s**. Full eval (15 scored + 2 retired): **~26s**. Tests: **~40s** (14 tests). |
| Cost | **$0.00** in replay mode (`make eval`/`make reproduce` force this — never a billed call, even with a key configured). The committed scorecard was produced by a real live run once, though — see step 3. |

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
GLASSBOX_REPLAY=1 python -m eval.harness --scenarios all --out eval/scorecard.md    # or: make eval
```

`GLASSBOX_REPLAY=1` is forced here on purpose (`make eval` forces it too, in
the recipe itself) - this command can never trigger a billed call, even if
you have a live key configured in `.env`. Runs all 17 scenarios (15 scored,
2 retired - see below) through the real pipeline, scores against ground
truth, and writes both `eval/scorecard.md` and `eval/cost_receipt.md`.

**SC-07 and SC-15 are retired**, in place, per `CLAUDE.md`'s rule for an
ill-posed scenario - both stay in the manifest with their `ground_truth`
unedited; only their `notes` field says why. Full reasoning:
`data/manifest_reconciliation.md`. They show as their own `RETIRED` row in
the scorecard and are excluded from every total, not silently dropped.

**Expected — this should match the committed `eval/scorecard.md` exactly**
(reran this in replay mode and diffed byte-for-byte identical against the
live-recorded version committed to the repo, aside from the commit-hash line
in the header - this is the actual proof that replay reproduces a real live
run, not just a claim):
```
Totals: 7/15 pass · RCA top-1 2/11 answerable · hallucinated causes 0/15
abstention precision 0.33 (1/3) · recall 1.00 (1/1) · hallucinated-cause rate 0.00
```

If your numbers differ, that's a real bug — tell us. The pipeline has no
unseeded randomness anywhere under `engine/` or `eval/` (checked by grep, not
assumed), so this should never vary run to run on the same code and data.

**The committed scorecard is now a live-recorded run, not a replay-only
one.** `eval/replay_cache/` holds 19 real captures (12 Groq, 7 Gemini -
`CHANGELOG.md` entries 019-028) from an actual end-to-end live run; a fresh
clone without any key configured resumes every one of them from that cache
via the exact code path shown above, so the numbers above are what you
should see regardless of whether you have a key.

---

## 4. Baselines — ~28s (no key), longer with a live key

```bash
GLASSBOX_REPLAY=1 python -m eval.harness --baseline --out eval/baseline_scorecard.md    # or: make baseline
```

`GLASSBOX_REPLAY=1` is forced here too, same reasoning as step 3 - `make
baseline` forces it in the recipe. Runs B1 (naive drill-down — real,
deterministic, no LLM) and B3 (single-LLM-prompt) across the 15 non-retired
scenarios and writes `eval/baseline_scorecard.md`. Without a live key
configured, B3's rows honestly read `NOT RUN (replay mode / no live key
configured)` rather than faking a response — regenerating this way
overwrites the real live B3 transcript currently committed (OpenAI,
`gpt-4o-mini`, 14/15 scenarios - Groq's account-level quota and then
Gemini's rate limit both blocked completion before OpenAI cleanly finished
it; `CHANGELOG.md` entries 026-027) with that honest placeholder, so if you
want to keep the real quotes, copy the file first. B3 has no replay cache
(`eval/baselines/run_all.py::run_b3` calls the provider directly, bypassing
`engine/llm_client.py::complete()`'s cache) - `make baseline-live` with a
real key makes a fresh call for every scenario every time, not resumable.

**Expected — B1 totals should match exactly:**
```
B1 totals: 2/15 exact segment match · 3/15 scenarios where B1 named a cause on an unplanted movement
```

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

## 6. The app — cold start under 2s

```bash
streamlit run app/main.py    # or: make app
```

Opens a browser tab at `localhost:8501`: a sidebar scenario picker
(SC-01..SC-17, including the ones that don't pass) and persona switcher, a
main panel with the tiered narrative, evidence drawer, decomposition chart
and action card. Offline by default, same as everything else — responses
come from the committed replay cache and the app says so above the result
(a 🔁 REPLAYING / 🟢 LIVE banner; silent replay would be dishonest).

**Important:** DuckDB only allows one writer at a time. Don't run the app
and `make eval`/`make reproduce`/`pytest` against the same
`data/generated/meridian.duckdb` concurrently — the second process fails
with `IOException: File is already open`. Stop the app (or the other
process) first.

**Verified without a browser**, since screenshotting one wasn't available in
this environment: Streamlit's `AppTest` harness drove `app/main.py`
end-to-end — selected each of the 17 scenarios, clicked Run, and switched
all three persona overrides — and every run completed with zero exceptions,
covering every branch the UI renders (no_alert, answer, abstention,
clarification). That's real functional verification; nobody has confirmed
the layout looks right in an actual browser yet.

---

## 7. Tests — ~29s

```bash
pytest -q    # or: make test
```

14 tests. Four must never be weakened — see their docstrings:
`test_gate_invariant`, `test_tiers_monotone`,
`test_validator_blocks_invented_numbers`, and `test_findings_schema_valid`
(validates every scenario's output against the frozen
`schemas/findings.schema.json`). The other ten (`test_llm_client_force_live.py`,
plus additions to `test_validator_blocks_invented_numbers.py`) are
regression tests added while fixing real bugs found during this session's
live run — see `CHANGELOG.md` entries 020-028.

---

## 8. One command — if you have `make`

```bash
make reproduce     # setup → data → eval → test
```

**This machine doesn't have plain `make` installed** (confirmed: `which
make` returns nothing on this Windows box, no WSL) — but it does have
`mingw32-make.exe` on PATH (from an unrelated MinGW install), which reads
this `Makefile` correctly (`mingw32-make.exe -n test` prints `pytest -q` as
expected). If your Windows machine has MinGW/MSYS installed for some other
reason, try `mingw32-make` before assuming you need the manual form below.
If you have neither, run steps 1, 2, 3 and 7 above directly — that's the
entire content of the `reproduce` target; nothing else happens inside it.

---

## 9. Troubleshooting

Real failures hit while writing this guide, not invented ones:

| Symptom | Cause | Fix |
|---|---|---|
| `SyntaxError` on `str \| None` | Python ≤ 3.10 | Use 3.11+ |
| `make: command not found` | No `make` on this machine (plain Windows, no WSL) | Try `mingw32-make` if you have MinGW/MSYS installed (see step 8); otherwise use the `python -m ...` form of each target shown above — every target is one line |
| A live-mode run makes a real call when you only ran `make eval`/`make baseline` | Wasn't possible before this session's fix - `eval`/`baseline` used to have no opinion on `GLASSBOX_REPLAY` and would inherit whatever `.env` said | `make eval` and `make baseline` now force `GLASSBOX_REPLAY=1` in the recipe itself; live runs require the explicit `make eval-live` / `make baseline-live` targets, which print the provider/model and an approximate call count before starting |
| `duckdb.duckdb.ConnectionException: Connection has already been closed` | Another process still holds the DuckDB file open (e.g. a previous script that didn't close its connection, or a concurrent `du`/backup process scanning the file) | Close other processes touching `data/generated/meridian.duckdb`, or open with `read_only=True` |
| `duckdb.duckdb.IOException: File is already open in <path> (PID ...)` | DuckDB allows exactly one writer. Hit this directly this session: `pytest` failed because a `streamlit run app/main.py` left running in the background from an earlier step still held the file open | Stop the other process (the PID is in the error message) before running `pytest`, `eval.harness`, or another app instance |
| `UnicodeEncodeError: 'charmap' codec can't encode characters` when printing a DuckDB relation directly in a Windows terminal | DuckDB's pretty-printed table repr uses box-drawing Unicode characters the default Windows `cp1252` console encoding can't render | Call `.fetchone()` / `.fetchall()` and print the plain Python value instead of printing the relation object |
| `pip install` takes much longer than expected | `sentence-transformers` pulls in PyTorch, which is large (~600MB-1GB depending on platform) | Expected — budget 10+ minutes on a fresh install, more on a slow connection |
| Embedding-based retrieval silently falls back to BM25-only | No network access to download the `all-MiniLM-L6-v2` model on first use | Expected degradation, not a bug — `engine/stages/s05_retrieve.py` catches this and continues with BM25 alone, same as it would with `sentence-transformers` uninstalled |

---

## 10. Runtime and cost summary

| Step | Time (measured, this session) | Cost |
|---|---|---|
| Install | 10+ min (dominated by PyTorch download) | $0 |
| Generate data | ~10-25s | $0 |
| Evaluate (15 scored + 2 retired) | ~26s in replay mode (resuming a real live-recorded run) | $0 |
| Baselines (15 scored, no key) | ~28s | $0 |
| App cold start | under 2s to first healthy response | $0 |
| Tests | ~40s (14 tests) | $0 |
| **Steps 1+2+3+7 combined** | **~11-12 min, install-dominated** | **$0** |

Per-run token/latency/cost telemetry: [`eval/cost_receipt.md`](eval/cost_receipt.md)
is now generated from a genuine live run (`Mode: live`, real nonzero
tokens - 12 real Groq calls, 7 real Gemini calls this session,
`CHANGELOG.md` entry 025) rather than the offline/no-key case. It's still
$0.00, but because both providers used have a free tier, not because no key
was configured - reproducing it yourself in replay mode (as above) will
also show $0.00, for the offline reason this note used to describe. The
receipt also carries an appended correction for a real latency-measurement
bug found this session (entry 024): the two stages that make LLM calls were
never wrapped in the pipeline's own timing code, so every previously
reported latency number silently excluded live-call wait time.

**What this guide is not yet:** a true clean-machine test performed by
someone other than the person who wrote the code, on a second physical
machine, per `docs/01_MASTER_BUILD_FLOW.md`'s own T−7 gate. Every number
above is real and was measured this session, but on one machine, by one
person. That second-machine test is still open — see `CHECKLIST.md`.
