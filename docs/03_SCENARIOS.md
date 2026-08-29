# Scenarios SC-01 … SC-17

The machine-readable ground truth is `data/injection_manifest.yaml` — **that file
is authoritative**. This one is the human index: what each scenario is *for*, and
which are load-bearing.

| ID | Scenario | Branch | Difficulty | Proves |
|---|---|---|---|---|
| SC-01 | South × Audio revenue drop; courier SLA, promo decoy | answer | core | The hero. Localization + evidence + a demoted rival cause |
| SC-02 | Festival calendar shift | **no alert** | core | Noise vs signal — the pass condition is silence |
| SC-03 | Planned promo in the registry | **no alert** | core | "We noticed and it's expected" ≠ "we didn't notice" |
| SC-04 | Payment provider outage | answer | core | The easy case. Baselines get it too — keep it |
| SC-05 | Mix shift, volume and price flat | answer | core | Decomposition. A drill-down finds nothing here |
| SC-06 | App release regression, staged rollout | answer | hard | Dose-response — the strongest falsification evidence |
| SC-07 | Two co-equal causes | answer | hard | Ranked drivers + an honest unexplained residual |
| **SC-08** | **Real movement, no cause planted** | **abstention** | adversarial | **The most important scenario in the submission** |
| SC-09 | Definition drift (ETL change) | answer | hard | The metric moved, the business didn't |
| SC-10 | New category, five weeks of history | answer | hard | Declared degradation — tier capped at HYPOTHESIS |
| SC-11 | Slow erosion over six weeks | answer | hard | No single day trips a threshold |
| SC-12 | Spillover contaminates the controls | answer | hard | Honest inconclusive > confident wrong |
| SC-13 | Three personas, one movement | answer | adversarial | Entitlements are real, not a UI filter |
| **SC-14** | **Malicious ticket, retrieved and inert** | answer | adversarial | **Injection defence you can watch** |
| SC-15 | Localizes to a 4-order cell | answer | adversarial | Small-cell suppression; deliberately less useful |
| SC-16 | Partner feed 40 hours stale | answer | adversarial | Freshness is the finding |
| SC-17 | "Why are sales down in the south?" | **clarification** | adversarial | Asks rather than guesses |

## The three that carry the submission

**SC-08** is the demo. Real, material movement; nothing planted; decoy documents
in the corpus to bait a retrieval-only system. It must abstain, list what it
ruled out, and refer onward. Pair it with baseline B3 on the same slide.

**SC-14** is the security proof. The malicious ticket is genuinely relevant and
*is* retrieved — hiding it would be the weaker demo. Flagged, quoted, inert.

**SC-01** is everything working at once, and it mirrors the Round 1 brief's own
example down to the number.

## Coverage against the brief

| Objective | Scenarios |
|---|---|
| Separate signal from noise | SC-02, SC-03, SC-11 |
| Localize the change | SC-01, SC-05, SC-12, SC-15 |
| Use unstructured evidence | SC-01, SC-04, SC-06, SC-07, SC-14 |
| Move from correlation to action | SC-01, SC-06, SC-12 |
| **Clarify or abstain** | **SC-08 (abstain) + SC-17 (clarify)** |
| Security and access | SC-13, SC-14, SC-15 |
| Data quality and drift | SC-09, SC-16 |
| Graceful degradation | SC-10, SC-12, SC-16 |

Objective 5 says "requests clarification **or** abstains." SC-08 covers one half;
without SC-17 the other half is unevidenced. That is why SC-17 exists.

## Adding a scenario

Allowed, any time. Append to the manifest, commit with a message saying why, and
add a changelog entry. **Changing an existing scenario's ground truth after the
engine has produced output for it is not allowed** — mark it
`notes: RETIRED - <reason>` and leave it in the file. A retired scenario visible
in git history reads as honesty; a silently edited one reads as fraud.
