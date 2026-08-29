<!-- GENERATED FILE - do not hand-edit. Written by `make baseline`.
     Committed on purpose, misses included. If you are reading this line in the
     submitted repo, the harness never ran. -->

# Baselines — NOT YET GENERATED

Run `make baseline`. Required shape:

```
### Q2 · same 17 scenarios
| ID | GlassBox | B1 naive drill-down | B3 single LLM prompt |
|----|----------|---------------------|----------------------|
| SC-01 | – | – | – |
...
Totals

### SC-08 · the row that matters (no cause was planted)
B3       : <its confident invented cause, verbatim>
GlassBox : <the abstention, verbatim>
```

Report the scenarios where a baseline **beats or matches** you as prominently as
the ones where it does not. A baseline that never wins looks rigged, and "the
single prompt gets the easy cases right and the hard cases confidently wrong" is
a stronger finding than "we win everywhere".
