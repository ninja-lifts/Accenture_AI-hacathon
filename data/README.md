# Data

Three things live here, and it matters that they are separate.

## 1. Meridian - synthetic, generated, ours

`generate.py` builds the fictional electronics retailer: orders, sessions,
marketing spend, delivery events, and ~490 support tickets / CRM notes / field
reports. Seeded, so the same seed produces a byte-identical dataset.

It is committed as a **generator plus a manifest**, not as data files. A judge
runs `make data` and gets exactly what we had.

**Why synthetic is the right choice here, and how to say it:** we need ground
truth. No public dataset pairs business KPIs with support text *and* labelled
root causes (see `docs/05_DATA_STRATEGY.md` for the evidence that this gap is
structural, not a failure of searching). Generating it is the only way to
measure whether the engine finds the *right* cause rather than *a* cause. We
then check that argument against real labelled data - see below - so the
synthetic set is never the only evidence.

## 2. The injection manifest - the ground truth

`injection_manifest.yaml` declares what was planted where, and what the correct
answer is for every scenario. Validated against
`schemas/injection_manifest.schema.json`.

**It is committed before any engine code reads it.** That commit hash is the
pre-registration proof, and it is quoted in the README. Editing ground truth
after seeing results is the one thing that would make every number in this
submission meaningless.

## 3. External datasets - never committed

| Dataset | Use | Licence | In repo? |
|---|---|---|---|
| RiskLoc `data/RS/` | 135 real labelled anomalies with operator-assigned causes; our external benchmark for Stage 03 | MIT (repo) | No - `make fetch-rs` clones it |
| PSqueeze simulation sets | Additional localization benchmark, unencrypted mirror of the Squeeze data | CC BY 4.0 | No - `make fetch-psqueeze` |
| Olist Brazilian e-commerce | Optional realism narrative | CC BY-NC-**SA** | **No, and never** - non-commercial + share-alike, and this repo is public and MIT |

`make fetch-*` downloads with attribution into `data/external/`, which is
gitignored. If the download fails, the harness runs the synthetic suite and
reports the external benchmark as `NOT RUN` - it never silently substitutes.
