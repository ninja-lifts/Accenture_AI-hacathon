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

**Correction (CHANGELOG.md, filed after this receipt was generated):** the `latency p50/p95` line above is wrong, and known to be wrong - not rounded, not approximate, structurally excluded from what it claims to measure. `engine/stages/s00_intent.py` and `s07_narrate.py`, the only two stages that ever make an LLM call, were the only two of eight stages never wrapped in `engine/telemetry.py::stage()` - `total_ms` is `sum(stage_timings_ms.values())` and nothing else, so every live call's wait time was silently absent from it, for this project's entire history. Real per-call latency for this run, computed from the raw harness logs instead: **p50 ≈ 36,000ms, p95 ≈ 91,000ms** - not 1,078/1,927. Both stages are now wrapped; a fresh live run's receipt will report this correctly. Left the numbers above unedited rather than silently rewritten, per this file's own sibling `CHANGELOG.md`'s rule: append a correction, don't edit an old entry to look better.
