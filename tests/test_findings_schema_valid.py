"""Every findings object the pipeline produces must validate against the
frozen schemas/findings.schema.json - schemas/ is rule 1 in PROJECT_RULES.md, and
"the pipeline emits schema-valid findings" is Gate 4's other half (the first
half, exactly-one-branch, is tests/test_gate_invariant.py).

Runs the real 17-scenario manifest through the real pipeline via
eval.harness (the same code path the committed scorecard used), so this
test and the scorecard can never silently drift apart."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml

from eval.harness import run_scenario

_SCHEMA = json.loads(
    (Path(__file__).resolve().parent.parent / "schemas" / "findings.schema.json").read_text(encoding="utf-8")
)
_VALIDATOR = jsonschema.Draft202012Validator(_SCHEMA, format_checker=jsonschema.FormatChecker())
_MANIFEST = yaml.safe_load(
    (Path(__file__).resolve().parent.parent / "data" / "injection_manifest.yaml").read_text(encoding="utf-8")
)


def test_all_scenarios_produce_schema_valid_or_no_alert_output():
    checked = 0
    for scenario in _MANIFEST["scenarios"]:
        if scenario.get("notes", "").strip().upper().startswith("RETIRED"):
            continue
        result = run_scenario(scenario)
        if result.get("kind") == "no_alert":
            # An alert-sweep scenario that correctly did not escalate never
            # became a findings object - nothing to validate against a
            # schema for an object it never claimed to produce.
            assert scenario["expected_branch"] == "no_alert", (
                f"{scenario['id']}: produced no_alert but manifest expects "
                f"{scenario['expected_branch']}"
            )
            continue
        errors = list(_VALIDATOR.iter_errors(result))
        assert not errors, (
            f"{scenario['id']}: findings object fails schemas/findings.schema.json:\n"
            + "\n".join(f"  {'/'.join(str(p) for p in e.path)}: {e.message}" for e in errors)
        )
        # The hard invariant from Gate 4/the gate itself, re-checked here at
        # the schema level rather than the branch level.
        outcome = result["outcome"]
        populated = [k for k in ("answer", "abstention", "clarification") if outcome[k] is not None]
        assert len(populated) == 1
        checked += 1

    assert checked >= 10, "expected most of the 17 scenarios to reach a schema-checkable findings object"
