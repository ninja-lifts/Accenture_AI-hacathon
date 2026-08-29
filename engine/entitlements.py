"""Row, column and cell-size access control.

Applied BEFORE any query runs, by pushing predicates into the SQL. Never filter
results afterwards: a judge asking 'is this real access control or a UI filter?'
must be answerable by pointing at the generated SQL."""

from __future__ import annotations

from typing import Any


def resolve(persona: str, contract: dict[str, Any]) -> dict[str, Any]:
    """TODO(Phase 3): -> {row_predicate, visible_columns, masked_columns,
    min_cell_size, entitlements_hash}."""
    raise NotImplementedError


def suppress_small_cells(segments: list[dict], min_cell_size: int) -> tuple[list[dict], int]:
    """TODO(Phase 3): roll segments below min_cell_size up to their parent.
    Returns (segments, n_suppressed). This is SC-15."""
    raise NotImplementedError
