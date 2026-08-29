# ADR-0003 — Not an agent

**Status:** accepted

## Context
The dominant 2026 pattern is an agent with tools and a planning loop. Some
evaluation rubrics explicitly reward "purposeful use of agents." Ours is a fixed
pipeline where the model has no tools and no loop.

## Decision
Keep the fixed pipeline. Do not add an agent loop, tool-calling, a planner, or
multi-agent orchestration — including to satisfy a rubric.

## Consequences
**Good.** The control flow is identical on every run, which is what makes it
auditable, replayable, diffable and testable. A CFO can be shown the same
trajectory twice. The evaluation harness is meaningful because the system is
deterministic between the two model calls.

**Bad.** Cannot handle a novel question shape by improvising. Extending the
system means writing a stage, not a tool.

**We accept this** because auditability is the product. An agent that plans its
own path cannot be signed off by a risk function, and a system whose reasoning
differs run to run cannot be benchmarked. Where a rubric rewards agentic design,
the correct response is to explain the trade-off, not to adopt the pattern —
the explanation is itself the engineering judgement being assessed.
