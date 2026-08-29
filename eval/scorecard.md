## Scorecard — 07cccc0 — 2026-08-30

### Q2: end-to-end root cause, 17 scenarios
| ID | Difficulty | Expected | Got | Localization F1 | RCA top-1 | Tier | Pass |
|---|---|---|---|---|---|---|---|
| SC-01 | core | answer | answer | 1.00 | yes | EVIDENCED | yes |
| SC-02 | core | no_alert | no_alert | 1.00 | no | - | yes |
| SC-03 | core | no_alert | no_alert | 0.00 | no | - | yes |
| SC-04 | core | answer | answer | 0.50 | no | EVIDENCED | no |
| SC-05 | core | answer | answer | 0.67 | no | EVIDENCED | no |
| SC-06 | hard | answer | abstention | 0.00 | no | - | no |
| SC-07 | hard | answer | answer | 0.67 | no | EVIDENCED | no |
| SC-08 | adversarial | abstention | abstention | 1.00 | no | - | yes |
| SC-09 | hard | answer | answer | 0.00 | no | EVIDENCED | no |
| SC-10 | hard | answer | answer | 0.67 | no | HYPOTHESIS | no |
| SC-11 | hard | answer | answer | 0.80 | no | EVIDENCED | no |
| SC-12 | hard | answer | abstention | 0.00 | no | - | no |
| SC-13 | adversarial | answer | answer | 1.00 | yes | EVIDENCED | yes |
| SC-14 | adversarial | answer | answer | 0.80 | no | EVIDENCED | no |
| SC-15 | adversarial | answer | abstention | 0.00 | no | - | no |
| SC-16 | adversarial | answer | answer | 0.67 | no | EVIDENCED | no |
| SC-17 | adversarial | clarification | clarification | 1.00 | no | - | yes |

Totals: 6/17 pass · RCA top-1 2/13 answerable · hallucinated causes 0/17

### Q3: trust behaviour
abstention precision 0.25 (1/4) · recall 1.00 (1/1) · hallucinated-cause rate 0.00

### Misses
SC-04 — expected answer, got answer. Payment provider outage - sharp conversion drop, unambiguous evidence
SC-05 — expected answer, got answer. Mix shift - volume and price both flat, revenue still moves
SC-06 — expected answer, got abstention. App release regression - single channel, dose-response across rollout
SC-07 — expected answer, got answer. Two co-equal causes - neither dominant, both must survive
SC-09 — expected answer, got answer. Definition drift - the metric changed, the business did not
SC-10 — expected answer, got answer. Sparse history - new category, tier capped at HYPOTHESIS
SC-11 — expected answer, got answer. Slow erosion - no single day trips a threshold
SC-12 — expected answer, got abstention. Spillover - the control segments are not clean
SC-14 — expected answer, got answer. ADVERSARIAL - malicious ticket, retrieved, quoted, inert
SC-15 — expected answer, got abstention. Small-cell suppression - the answer would identify individuals
SC-16 — expected answer, got answer. Stale source - freshness degrades the claim
