# Build vs Buy

The brief asks for this table explicitly. Fill the status column as you go.

| Component | Approach | Choice | Why |
|---|---|---|---|
| Storage / query | **Native** | DuckDB embedded | Zero provisioning, nothing to be down during judging. Swaps to Snowflake/Databricks behind one adapter file |
| Dataframes / stats | **Native** | pandas, numpy, scipy, statsmodels | Standard, boring, correct |
| Seasonality | **Custom** | dow x month x festival_calendar decomposition, per-KPI parameters in the contract | Same idea as STL (learn seasonality from history, hold it against the focal window) without statsmodels.STL's 2-full-cycle data requirement — Meridian has ~16 months, not 24+. Reasoning in `engine/stages/s02_detect.py`'s docstring |
| Attribution search | **Custom** | Ours | This is the differentiated part. Benchmarked against 7 published algorithms |
| Falsification | **Custom** | Ours | Nothing off the shelf does this for business KPIs |
| Confidence tiers | **Custom** | Ours | The product. Rule-assigned, never learned |
| Lexical retrieval | **Native** | rank-bm25 | 490 docs. In-memory |
| Semantic retrieval | **Native** | sentence-transformers, local | No embedding data leaves the tenant |
| Vector store | **Deliberately none** | In-memory | Measured: no recall gain at this scale, one less operational dependency |
| Language model | **Externally integrated** | One private-endpoint call ×2, behind `engine/llm_client.py` | Vendor-neutral by construction. Provider is config |
| Prompt management | **Custom** | Versioned `prompts/*.md` | Prompts are artefacts, not string literals |
| Number validation | **Custom** | Ours | The guarantee nothing off the shelf provides |
| Access control | **Custom** | Contract-driven predicates pushed into SQL | The contract *is* the access layer — no second system to drift |
| PII redaction | **Custom** | Pattern + entity masking at index time | Runs before indexing, so unredacted text is never stored |
| Audit | **Native** | Append-only JSONL → Postgres in production | Append-only is the requirement; the storage is not interesting |
| UI | **Native** | Streamlit | The webpage is ~20% of the marks. React would be a bad trade |
| Delivery channels | **Configured** | Three renders of one findings object | Same object, three surfaces — not three implementations |
| Evaluation | **Custom** | Pre-registered harness in CI | Nothing off the shelf evaluates abstention |
| Hosting | **Native** | Streamlit Community Cloud (free) | Judges click; no key required in replay mode |

**The pattern is the point, and it is worth saying out loud in the pitch:**
everything commodity is bought; everything at the trust boundary is ours. That
one sentence is the differentiation argument in miniature — and this table is the
evidence for it.
