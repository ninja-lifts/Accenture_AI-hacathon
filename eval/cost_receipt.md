# Cost receipt

```
Runs measured: 15      Mode: replay

tokens in  (mean / p95)   0  /  0
tokens out (mean / p95)   0  /  0
USD per run (mean)        0.0000
latency p50 / p95 (ms)    424  /  797
rows scanned (mean)       29531
LLM calls per run (max observed / cap)   0 / 2

Replay mode cost: $0.00 (15/15 runs served from replay/template fallback, not a live model call)
```

Most prototypes cannot answer "what does one of these cost to run?" Being able to is a small, memorable signal of production thinking.

**Note on this run:** no live LLM key was configured, so every run above used the deterministic template narrator (engine/stages/s07_narrate.py's fallback path) rather than a live model call - `llm_calls` is 0 for all of them and this receipt is a true $0.00, not a rounded one. Re-run with GLASSBOX_REPLAY=0 and a real key to get live token/cost numbers; the harness and this receipt need no changes to do so.
