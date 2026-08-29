"""Streamlit UI. Deliberately thin - roughly 20% of the effort.

The webpage is the window; the engine is the prototype. Anything that looks like
analysis happening in this file is a bug.

Screens:
    1. Persona switcher (CFO / Category Manager / Analyst) - disclosed, not hidden
    2. Ranked alert feed + question box
    3. Run view with live stage narration
    4. Findings: tiered narrative, evidence drawer, action card, telemetry footer
    5. Scenario picker (SC-01..SC-17) so a judge replays anything, including misses
    6. "Try to break it" tab - type your own injection, request data your role
       cannot see, then see the audit log entry it produced

TODO(Phase 5).
"""

from __future__ import annotations


def main() -> None:
    raise NotImplementedError("Phase 5")


if __name__ == "__main__":
    main()
