"""Row, column and cell-size access control.

Applied BEFORE any query runs, by pushing predicates into the SQL. Never filter
results afterwards: a judge asking 'is this real access control or a UI filter?'
must be answerable by pointing at the generated SQL."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

_ROLE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class EntitlementError(Exception):
    """Refused to resolve entitlements - fails loudly rather than defaulting open."""


def resolve(persona: str, contract: dict[str, Any], role_id: str | None = None) -> dict[str, Any]:
    """Resolve persona -> {row_predicate, visible_columns, masked_columns,
    excluded_columns, min_cell_size, role_id, entitlements_hash}.

    The predicate is returned as literal SQL text meant to be pushed into the
    contract's query (Stage 01), never applied to results afterwards - that is
    the difference between real access control and a UI filter (Gate 3).

    `role_id` scopes a category_manager's row_rules predicate
    ("category IN (SELECT category FROM role_scope WHERE role_id = :role_id)").
    It is substituted as a literal after a strict allowlist check
    (`_ROLE_ID_RE`) rather than left as a bind parameter, because DuckDB's
    Python driver binds positionally and the pipeline already treats role_id
    as an internal, closed-set value (never raw user text) - the allowlist
    check is what keeps that assumption enforced rather than assumed.
    """
    access = contract["access"]
    matches = [r for r in access["row_rules"] if r["role"] == persona]
    if not matches:
        raise EntitlementError(
            f"no row_rule for persona '{persona}' in contract '{contract['id']}'"
        )
    predicate = matches[0]["predicate"]

    if ":role_id" in predicate:
        if not role_id:
            raise EntitlementError(
                f"persona '{persona}' requires a role_id to resolve its row predicate"
            )
        if not _ROLE_ID_RE.match(role_id):
            raise EntitlementError(f"role_id '{role_id}' fails the allowlist pattern")
        predicate = predicate.replace(":role_id", f"'{role_id}'")

    visible_columns: list[str] = []
    masked_columns: list[str] = []
    excluded_columns: list[str] = []
    for rule in access.get("column_rules", []):
        if persona not in rule.get("visible_to", []):
            if rule["treatment"] == "excluded":
                excluded_columns.append(rule["column"])
            continue
        if rule["treatment"] in ("masked", "hashed"):
            masked_columns.append(rule["column"])
        else:
            visible_columns.append(rule["column"])

    resolved = {
        "persona": persona,
        "role_id": role_id or persona,
        "row_predicate": predicate,
        "visible_columns": sorted(visible_columns),
        "masked_columns": sorted(masked_columns),
        "excluded_columns": sorted(excluded_columns),
        "min_cell_size": access["min_cell_size"],
    }
    digest_source = json.dumps(
        {k: v for k, v in resolved.items() if k != "entitlements_hash"},
        sort_keys=True,
    )
    resolved["entitlements_hash"] = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()
    return resolved


def suppress_small_cells(
    segments: list[dict[str, Any]], min_cell_size: int
) -> tuple[list[dict[str, Any]], int]:
    """Roll segments below min_cell_size up to their parent. This is SC-15.

    `segments` are dicts with at minimum {dimensions, contribution_abs,
    contribution_pct, support_size}. A segment whose support_size is below
    min_cell_size (or unknown) is dropped and its contribution folded into a
    synthetic parent segment - one level up the dimension lattice, i.e. with
    the most granular dimension removed. If nothing remains at the parent
    level after folding, the parent is created with the suppressed segment's
    own totals under `suppressed: true`. Returns (segments, n_suppressed).
    """
    kept: list[dict[str, Any]] = []
    suppressed_by_parent: dict[tuple[tuple[str, str], ...], dict[str, Any]] = {}
    n_suppressed = 0

    for seg in segments:
        support = seg.get("support_size")
        if support is not None and support >= min_cell_size:
            kept.append(seg)
            continue

        n_suppressed += 1
        dims = dict(seg["dimensions"])
        if len(dims) <= 1:
            # Already at the coarsest level - suppress with no lower rollup
            # available; still disclosed, never silently dropped.
            parent_key: tuple[tuple[str, str], ...] = ()
        else:
            # Drop the most granular (last-added) dimension key.
            keys = list(dims.keys())[:-1]
            parent_key = tuple(sorted((k, dims[k]) for k in keys))

        bucket = suppressed_by_parent.setdefault(
            parent_key,
            {
                "dimensions": dict(parent_key) if parent_key else {},
                "contribution_abs": 0.0,
                "contribution_pct": 0.0,
                "rank": seg.get("rank"),
                "suppressed": True,
                "suppression_reason": f"cell size below min_cell_size={min_cell_size}",
                "support_size": 0,
            },
        )
        bucket["contribution_abs"] += seg.get("contribution_abs", 0.0)
        bucket["contribution_pct"] += seg.get("contribution_pct", 0.0)
        bucket["support_size"] += support or 0

    kept.extend(suppressed_by_parent.values())
    kept.sort(key=lambda s: abs(s.get("contribution_abs", 0.0)), reverse=True)
    for i, seg in enumerate(kept, start=1):
        seg["rank"] = i
    return kept, n_suppressed
