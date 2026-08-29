# Replay cache

Committed model responses, keyed by `(prompt_id, prompt_version, sha256(payload))`.

This is what makes the whole system runnable offline, with no API key, and what
makes the published evaluation exactly reproducible on a judge's machine.

- Regenerate: `GLASSBOX_REPLAY=0` with the `GLASSBOX_LLM_*` variables set, then
  re-run the harness. Commit the diff.
- Never hand-edit a cached response. If one is wrong, regenerate it and say so in
  the changelog.
- The UI displays when it is replaying. Silent replay would be dishonest.
