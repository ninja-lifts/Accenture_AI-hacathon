"""The KPI dependency graph - our knowledge graph, compiled not authored.

Every contract's drivers[].depends_on block is an edge. Compiling them yields a
machine-readable graph of how the business metrics relate. It is validated for
cycles at startup, rendered once for the deck, and used at runtime to order the
issue tree so decomposition follows real lineage instead of a hard-coded list."""

from __future__ import annotations

from typing import Any

import networkx as nx


class KpiGraphError(Exception):
    """The compiled graph is invalid - a startup error, never a silent skip."""


def compile_graph(contracts: dict[str, Any]) -> nx.DiGraph:
    """Compile every contract's drivers[].depends_on into a DiGraph.

    An edge kpi -> dependency means "kpi depends on dependency" - e.g.
    net_revenue -> orders, never the reverse. A dependency that is not itself
    a governed contract (e.g. `sessions`, `unit_price`) becomes a leaf node
    with kind="external": it is real vocabulary in the business, just not (yet)
    a metric with its own contract, detection rules or access policy.

    Raises KpiGraphError on a cycle. Cycles are a startup error, not a
    runtime surprise - Stage 04 walks this graph assuming it terminates.
    """
    graph = nx.DiGraph()
    for kpi_id, c in contracts.items():
        graph.add_node(kpi_id, kind="contract", display_name=c["display_name"])

    for kpi_id, c in contracts.items():
        for driver in c.get("drivers", []):
            for dep in driver.get("depends_on", []):
                if dep not in graph:
                    graph.add_node(dep, kind="external", display_name=dep)
                graph.add_edge(
                    kpi_id,
                    dep,
                    driver=driver["name"],
                    relation=driver["relation"],
                    levers=list(driver.get("levers", [])),
                )

    if not nx.is_directed_acyclic_graph(graph):
        cycles = list(nx.simple_cycles(graph))
        raise KpiGraphError(f"KPI graph has cycles: {cycles}")

    return graph


def issue_tree(graph: nx.DiGraph, kpi_id: str) -> list[str]:
    """Ordered descendants of kpi_id - the order Stage 04 walks the graph.

    Breadth-first from kpi_id so a direct driver is always visited before the
    things it in turn depends on, matching how a decomposition should be
    read: closest cause first.
    """
    if kpi_id not in graph:
        raise KpiGraphError(f"unknown kpi_id '{kpi_id}' - not in the compiled graph")
    return [n for _, n in nx.bfs_edges(graph, kpi_id)]


def render_png(graph: nx.DiGraph, out_path: str) -> None:
    """One static render for the deck and the README.

    Hand-built SVG rather than matplotlib: requirements.txt does not pin a
    plotting library (CLAUDE.md rule 9 - no new dependency without asking),
    and networkx's own layout (spring_layout) needs nothing beyond numpy,
    which is already pinned. `out_path` is honoured verbatim; callers should
    pass an `.svg` path - scalable and just as usable in a deck or README as
    a raster image, at zero dependency cost.
    """
    from pathlib import Path

    width, height, pad = 900, 600, 60
    pos = nx.spring_layout(graph, seed=20260829, k=1.1)
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    x_lo, x_hi = min(xs), max(xs)
    y_lo, y_hi = min(ys), max(ys)

    def scale(p: tuple[float, float]) -> tuple[float, float]:
        x, y = p
        sx = pad + (x - x_lo) / (x_hi - x_lo or 1) * (width - 2 * pad)
        sy = pad + (y - y_lo) / (y_hi - y_lo or 1) * (height - 2 * pad)
        return sx, sy

    coords = {n: scale(p) for n, p in pos.items()}

    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica,Arial,sans-serif">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#4a5568"/></marker></defs>',
        f'<text x="{pad}" y="24" font-size="14" fill="#1a202c">'
        "GlassBox KPI graph (compiled from contracts/*.yaml drivers)</text>",
    ]

    for u, v, d in graph.edges(data=True):
        x1, y1 = coords[u]
        x2, y2 = coords[v]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            'stroke="#4a5568" stroke-width="1.5" marker-end="url(#arrow)"/>'
        )
        parts.append(
            f'<text x="{mx:.1f}" y="{my:.1f}" font-size="9" fill="#718096">'
            f"{esc(d['driver'])}</text>"
        )

    for n, (x, y) in coords.items():
        kind = graph.nodes[n].get("kind", "external")
        fill = "#2b6cb0" if kind == "contract" else "#a0aec0"
        r = 34 if kind == "contract" else 24
        label = graph.nodes[n].get("display_name", n)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"/>')
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="9" fill="white" '
            'text-anchor="middle" dominant-baseline="middle">'
            f"{esc(label)}</text>"
        )

    parts.append("</svg>")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts), encoding="utf-8")
