# ADR-0004 — Synthetic data as the primary benchmark

**Status:** accepted

## Context
Evaluating the full pipeline needs KPIs, unstructured text, and labelled root
causes together. No public dataset has all three (see `docs/05_DATA_STRATEGY.md`
for the four-way partition demonstrating why).

## Decision
Generate Meridian with planted causes, pre-register the ground truth by
committing `data/injection_manifest.yaml` before any engine code, and validate
externally on RiskLoc's RS set — 135 real anomalies with operator-assigned causes
and seven published baselines.

## Consequences
**Good.** Ground truth for every stage, including negative controls, which is the
only way to measure abstention at all. Fully reproducible from a seed.

**Bad.** Synthetic data is as hard as we made it, and we chose the difficulty.
Mitigated by the five honesty rules (ramps, spillover, contaminated pre-period,
confounded rival, unmarked negative controls) and by the external benchmark.

**Non-negotiable.** Ground truth is frozen at its commit. A scenario that turns
out to be ill-posed is retired in place, never edited.
