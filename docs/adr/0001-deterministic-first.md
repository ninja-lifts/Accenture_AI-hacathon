# ADR-0001 — Deterministic-first pipeline

**Status:** accepted

## Context
A KPI root-cause system can be built as one LLM call over a data dump, as an
agent with database tools, or as a fixed statistical pipeline with the model at
the edges. The first two are faster to build and demo well.

## Decision
A fixed seven-stage pipeline. Five stages are statistics and arithmetic. The
model is called exactly twice — intent parsing in, narration out — and a hard cap
of 2 is encoded in `findings.schema.json`.

## Consequences
**Good.** Every number is traceable to a computation. Runs are replayable and
unit-testable. The model cannot invent a cause because it never chooses one. We
can state a hallucinated-cause rate and defend it.

**Bad.** Less flexible: a question outside the contract catalogue gets a
clarification or a refusal rather than a best effort. Adding a KPI means writing
a contract, which is real adoption cost.

**We accept this** because the product's claim is trustworthiness, and a
trustworthy system that answers 80% of questions beats a fluent one that answers
100% with unknown reliability.
