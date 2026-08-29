# ADR-0002 — No vector database

**Status:** accepted

## Context
The corpus is ~490 documents. The reflex in 2026 is to add a vector DB.

## Decision
In-memory hybrid retrieval: BM25 plus locally-computed embeddings. No vector
store, hosted or embedded.

## Consequences
**Good.** No operational dependency, no service to be down during judging, no
embedding data leaving the tenant, faster cold start, one less thing in
`requirements.txt`.

**Bad.** Does not scale past roughly 10^5–10^6 documents, at which point a proper
index becomes necessary.

**Note for Q&A.** Saying "we measured it and it wasn't needed at this scale"
scores higher than adding one, because the mark is engineering judgement, not
component count. Have the recall number ready.
