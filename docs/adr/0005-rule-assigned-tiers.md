# ADR-0005 — Confidence tiers assigned by rule, not by model

**Status:** accepted

## Context
Every claim carries a confidence tier. It could be assigned by the model (natural,
flexible, one prompt) or by a rule table over the evidence actually present.

## Decision
A rule table in `engine/tiers.py`. The model never sees, chooses or influences a
tier; it receives them already attached and is forbidden from describing a
CORRELATED driver in causal language.

## Consequences
**Good.** Tiers mean the same thing every time. Monotonicity is testable and
tested — removing evidence can never raise a tier. A judge can read the whole
mapping in thirty seconds.

**Bad.** Coarser than a human analyst's judgement. Edge cases sit at a tier that
feels slightly wrong.

**We accept this** because a confidence score produced by the same system that
produced the claim is not a confidence score. Coarse and honest beats fine-grained
and circular.
