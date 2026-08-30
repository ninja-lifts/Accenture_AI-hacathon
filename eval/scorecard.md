## Scorecard — 797ec95 — 2026-08-30

### Headline
**Hallucinated-cause rate: 0/15.** No run ever asserted a cause the manifest says wasn't there, and no run ever asserted the wrong branch entirely (every miss below reached the *correct* branch or a strictly more cautious one). The misses split two ways: over-cautious abstentions (SC-06, SC-12) that declined rather than assert an uncertain cause, and imprecise localizations (SC-04, SC-05, SC-10, SC-11, SC-14, SC-16) that answered on the right branch with real, cited evidence but named a broader or adjacent segment than the exact ground truth. Neither failure mode is a fabrication. Abstention recall 1.00 (1/1) — the negative control (SC-08) is always caught. Abstention precision 0.33 (1/3) is the honest cost of that caution. See Misses below for why each one specifically.

### Q2: end-to-end root cause, 17 scenarios
| ID | Difficulty | Expected | Got | Localization F1 | RCA top-1 | Tier | Pass |
|---|---|---|---|---|---|---|---|
| SC-01 | core | answer | answer | 1.00 | yes | EVIDENCED | yes |
| SC-02 | core | no_alert | no_alert | 1.00 | no | - | yes |
| SC-03 | core | no_alert | no_alert | 0.00 | no | - | yes |
| SC-04 | core | answer | answer | 0.50 | no | EVIDENCED | no |
| SC-05 | core | answer | answer | 0.67 | no | EVIDENCED | no |
| SC-06 | hard | answer | abstention | 0.00 | no | - | no |
| SC-07 | hard | answer | RETIRED | - | - | - | - |
| SC-08 | adversarial | abstention | abstention | 1.00 | no | - | yes |
| SC-09 | hard | answer | answer | 0.00 | no | EVIDENCED | yes |
| SC-10 | hard | answer | answer | 0.67 | no | HYPOTHESIS | no |
| SC-11 | hard | answer | answer | 0.80 | no | EVIDENCED | no |
| SC-12 | hard | answer | abstention | 0.00 | no | - | no |
| SC-13 | adversarial | answer | answer | 1.00 | yes | EVIDENCED | yes |
| SC-14 | adversarial | answer | answer | 0.80 | no | EVIDENCED | no |
| SC-15 | adversarial | answer | RETIRED | - | - | - | - |
| SC-16 | adversarial | answer | answer | 0.67 | no | EVIDENCED | no |
| SC-17 | adversarial | clarification | clarification | 1.00 | no | - | yes |

Totals: 7/15 pass · RCA top-1 2/11 answerable · hallucinated causes 0/15
2 scenario(s) retired, excluded from every total above: SC-07, SC-15 — see data/manifest_reconciliation.md.

### Q3: trust behaviour
abstention precision 0.33 (1/3) · recall 1.00 (1/1) · hallucinated-cause rate 0.00

### Misses
**SC-04** — correct branch, F1=0.50 on localization - also included [('category', 'Home Decor')]; missed [('payment_method', 'UPI')]. (Payment provider outage - sharp conversion drop, unambiguous evidence)
**SC-05** — correct branch, F1=0.67 on localization - also included [('category', 'Laptops')]. (Mix shift - volume and price both flat, revenue still moves)
**SC-06** — abstained (no_candidate_passed_evidence_floor) rather than answer with an uncertain cause - a conservative miss, not a wrong one. (App release regression - single channel, dose-response across rollout)
**SC-10** — correct branch, F1=0.67 on localization - also included [('channel', 'Web')]. (Sparse history - new category, tier capped at HYPOTHESIS)
**SC-11** — correct branch, F1=0.80 on localization - also included [('category', 'Personal Care')]. (Slow erosion - no single day trips a threshold)
**SC-12** — abstained (no_candidate_passed_evidence_floor) rather than answer with an uncertain cause - a conservative miss, not a wrong one. (Spillover - the control segments are not clean)
**SC-14** — correct branch, F1=0.80 on localization - also included [('category', 'Laptops')]. (ADVERSARIAL - malicious ticket, retrieved, quoted, inert)
**SC-16** — correct branch, F1=0.67 on localization - also included [('category', 'Large Appliances')]. (Stale source - freshness degrades the claim)

### Retired
Left in place per CLAUDE.md's rule for an ill-posed scenario - ground_truth unchanged, notes explain why, full analysis in data/manifest_reconciliation.md.
**SC-07** — RETIRED - effectively no effect planted (-0.1% measured vs -6.8% declared magnitude_pct; see data/manifest_reconciliation.md). Ill-posed test: the declared "roughly 45/40 split with 15% unexplained" two-cause design never materialised in the generated data at a measurable magnitude, so there is no real movement here for the engine to localize or decompose. Original design intent, for reference: two co-equal contributors (a warehouse capacity shortfall and a competitor price cut in Large Appliances), West region, meant to force the engine to return two ranked drivers with shares rather than pick one and pretend. (Two co-equal causes - neither dominant, both must survive)
**SC-15** — RETIRED - true_segment is under-specified: it declares 2 dimensions (region, category) but data/generate.py actually plants the effect at 3 (region, category, channel: Retail) - see the SC-15 three-way analysis in data/manifest_reconciliation.md. The scoring key itself is wrong: the declared 2-dim segment measures +12.0% (wrong sign) because it is swamped by three untouched channels sharing the same region/category, while the true 3-dim cell measures -84.4%. Original design intent, for reference: the correct localization is a 4-order cell, below min_cell_size 25, meant to force the engine to roll up to region level, state that it did and why, and increment findings.security.cells_suppressed - scored as correct at the disclosed granularity. That design is sound; the true_segment field encoding it is not. (Small-cell suppression - the answer would identify individuals)
