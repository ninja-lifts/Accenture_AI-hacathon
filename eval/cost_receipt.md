# Cost receipt

```
Runs measured: 13      Mode: replay

tokens in  (mean / p95)   2620  /  4924
tokens out (mean / p95)   1123  /  1898
USD per run (mean)        0.0000
latency p50 / p95 (ms)    542  /  980
rows scanned (mean)       32279
LLM calls per run (max observed / cap)   1 / 2

Replay mode cost: $0.00 (13/13 runs served from replay/template fallback, not a live model call)
```

Most prototypes cannot answer "what does one of these cost to run?" Being able to is a small, memorable signal of production thinking.

**Note on this run:** replay mode throughout (no live key configured this run), but 10/13 run(s) matched a populated entry in eval/replay_cache/ and read a previously-captured model response instead of falling back to the template narrator - that is where the nonzero token/latency numbers above come from. USD cost is still $0.00 because a cache read makes no API call; those tokens were paid for once, when the cache entry was originally recorded live.
