"""Load, validate and compile semantic contracts.

A contract that fails schema validation is a startup error. Never degrade to a
partial catalogue - a metric with a broken definition is worse than a missing
one."""

from __future__ import annotations

from typing import Any


def load_all(path: str = "contracts") -> dict[str, dict[str, Any]]:
    """TODO(Phase 2): parse every YAML, validate against
    schemas/contract.schema.json, return {contract_id: contract}."""
    raise NotImplementedError


def build_catalogue(contracts: dict[str, Any]) -> dict[str, Any]:
    """TODO(Phase 2): the vocabulary handed to intent parsing - kpis, dimensions,
    observed dimension values, synonyms. The parser may emit nothing outside it."""
    raise NotImplementedError
