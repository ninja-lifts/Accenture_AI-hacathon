"""Load, validate and compile semantic contracts.

A contract that fails schema validation is a startup error. Never degrade to a
partial catalogue - a metric with a broken definition is worse than a missing
one."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


class ContractError(Exception):
    """A contract failed validation. This is a startup error, never a degrade."""


def _schema_path() -> Path:
    return Path(__file__).resolve().parent.parent / "schemas" / "contract.schema.json"


def load_all(path: str = "contracts") -> dict[str, dict[str, Any]]:
    """Parse every YAML in `path`, validate against
    schemas/contract.schema.json, return {contract_id: contract}.

    Fails loudly: a broken contract stops the app rather than shrinking the
    catalogue silently (rule 1 in CLAUDE.md - schemas/ is frozen and a
    contract that violates it is a bug in the contract, not a case to handle).
    """
    schema = json.loads(_schema_path().read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    contracts: dict[str, dict[str, Any]] = {}
    contract_dir = Path(path)
    for file in sorted(contract_dir.glob("*.yaml")):
        with file.open(encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
        errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
        if errors:
            messages = "\n".join(
                f"  - {'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
                for e in errors
            )
            raise ContractError(
                f"{file}: fails schemas/contract.schema.json:\n{messages}"
            )
        contract_id = doc["id"]
        if contract_id in contracts:
            raise ContractError(
                f"{file}: duplicate contract id '{contract_id}' "
                f"(already defined in another file)"
            )
        contracts[contract_id] = doc

    if not contracts:
        raise ContractError(f"no contracts found under {contract_dir!s}")
    return contracts


def build_catalogue(contracts: dict[str, Any]) -> dict[str, Any]:
    """The vocabulary handed to intent parsing: kpis, dimensions, synonyms.

    Stage 00 may only emit values that appear here. Observed dimension values
    are added separately at runtime (from the warehouse) by the caller, since
    the catalogue itself only knows the contract-declared vocabulary.
    """
    kpis = []
    for kpi_id, c in sorted(contracts.items()):
        dims = []
        for d in c.get("dimensions", []):
            dims.append(
                {
                    "name": d["name"],
                    "column": d["column"],
                    "searchable": d["searchable"],
                    "synonyms": list(d.get("synonyms", [])),
                }
            )
        kpis.append(
            {
                "id": kpi_id,
                "display_name": c["display_name"],
                "unit": c.get("unit"),
                "plain_english": c["definition"]["plain_english"],
                "dimensions": dims,
                "default_grain": c["grain"],
            }
        )
    return {"kpis": kpis}
