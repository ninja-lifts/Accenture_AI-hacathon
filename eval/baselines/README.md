# Baselines

A measured improvement means nothing without a fair baseline. We run three, and
they answer three different objections.

## B1 - Naive heuristic ("what a dashboard drill-down does")
Rank single-dimension segments by absolute contribution, take the largest, and
report the most recent ticket mentioning that segment as the cause.

*Answers:* "isn't this just a drill-down with extra steps?"
This is the honest strawman - and it is what the user does today, so beating it
is the actual product claim, not a formality.

## B2 - Published localization algorithms (external, real data)
Adtributor, R-Adtributor, Squeeze, RiskLoc, HotSpot and the other implementations
that ship with the RiskLoc repo, run on `data/RS/` (135 real labelled anomalies).

*Answers:* "your benchmark is your own synthetic data, so of course you win."
Same data, same metric, published algorithms, one command.

**Scope honestly.** These baselines evaluate **Stage 03 only**. None of them
does retrieval, falsification or abstention - there is nothing to compare on
those, because nobody published a method that does them. Report Stage 03 in one
table and the trust behaviours in a separate one. Merging them into a single
"GlassBox vs the world" table would put our least novel component on stage and
invite the one question we cannot answer well.

## B3 - LLM-only ("just ask a model")
The same window's aggregates and the same retrieved documents, handed to one
model in a single prompt: "what caused this movement and how confident are you?"
No pipeline, no tiers, no falsification.

*Answers:* the question every judge in 2026 is thinking - "why isn't this one
prompt?"

**This is the most valuable baseline in the submission.** It is cheap to build
(one file, reuses the existing retrieval output), and it is the one that
produces the killer row: on **SC-08, where no cause is planted**, B3 confidently
invents one and GlassBox abstains. Put that side by side and the architecture
argument is made by the evidence rather than by us.

Run it on every scenario, not just the flattering ones. Where B3 matches us,
say so - a baseline that never wins looks rigged, and "the single prompt gets
the easy cases right and the hard ones confidently wrong" is a sharper story
than "we win everywhere".
