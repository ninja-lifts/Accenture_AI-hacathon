# Cost receipt

```
Runs measured: 13      Mode: live

tokens in  (mean / p95)   4217  /  8306
tokens out (mean / p95)   931  /  1330
USD per run (mean)        0.0140
latency p50 / p95 (ms)    1078  /  1927
rows scanned (mean)       32279
LLM calls per run (max observed / cap)   2 / 2

Replay mode cost: $0.00 (0/13 runs served from replay/template fallback, not a live model call)
```

Most prototypes cannot answer "what does one of these cost to run?" Being able to is a small, memorable signal of production thinking.

**Note on this run:** ran with a live LLM key (GLASSBOX_REPLAY=0) - every number above is a real measurement from actual API calls, not a replay-cache read.
