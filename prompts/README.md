# Prompts

Both prompts live here as versioned files, not as string literals buried in
Python. That is deliberate: a judge assessing an LLM system will look for the
prompts, and "they are in the repo, versioned, with a changelog" is a better
answer than pasting them in Q&A.

GlassBox makes exactly **two** LLM calls per run. There is no third. If you
find yourself adding one, the architecture has drifted - stop and re-read
`docs/02_BUILD_BLUEPRINT.md`.

| File | Stage | What it is allowed to do | What guards it |
|---|---|---|---|
| `intent_parse.md` | 00 Intent | Map free text to `{kpi, segment, window}` drawn ONLY from contract vocabulary | Output validated against the compiled contracts; anything unmapped becomes a clarification, never a guess |
| `narrate.md` | 07 Narrate | Turn a finished findings object into persona-appropriate prose | `engine/validator.py` - every numeral in the output must already exist in the findings object, or the generation is rejected and retried |

Everything between those two stages is deterministic Python. The model never
sees raw customer rows, never chooses a root cause, never assigns a confidence
tier, and never has tools.

## Changing a prompt

Prompt edits are code changes. Bump the version header, run `make eval`, and
add a `CHANGELOG.md` entry with the before/after scorecard. A prompt change
that moves a metric is exactly the kind of evidence the changelog exists for.
