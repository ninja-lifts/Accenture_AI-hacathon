"""The KPI dependency graph - our knowledge graph, compiled not authored.

Every contract's drivers[].depends_on block is an edge. Compiling them yields a
machine-readable graph of how the business metrics relate. It is validated for
cycles at startup, rendered once for the deck, and used at runtime to order the
issue tree so decomposition follows real lineage instead of a hard-coded list."""

from __future__ import annotations

from typing import Any


def compile_graph(contracts: dict[str, Any]) -> Any:
    """TODO(Phase 2): networkx DiGraph. Raise on cycles - loudly, at startup."""
    raise NotImplementedError


def issue_tree(graph: Any, kpi_id: str) -> list[str]:
    """TODO(Phase 2): ordered descendants of kpi_id - the order Stage 04 walks."""
    raise NotImplementedError


def render_png(graph: Any, out_path: str) -> None:
    """TODO(Phase 2): one static render for the deck and the README."""
    raise NotImplementedError
