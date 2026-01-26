from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


def build_strategy_mermaid(pack: Dict[str, Any]) -> str:
    sb = pack.get("strategy_board") or {}
    ig = pack.get("impact_graph") or {}
    metrics_by_id = {
        m.get("id"): m for m in pack.get("metrics", []) if isinstance(m, dict)
    }

    lines: List[str] = []
    lines.append("flowchart TB")

    # -------------------------
    # Company Goals (Context)
    # -------------------------
    goals_box = sb.get("company_goals_box") or {}
    context_title = goals_box.get("title") or "Company Goals"
    goals = goals_box.get("goals") or []
    goal_links_fallback = goals_box.get("links") or []

    goal_labels = _goal_labels_from_impact_graph(ig)
    goal_ids = [g.get("id") for g in goals if g.get("id")]

    lines.append("  %% --- TOP LEVEL: COMPANY GOALS ---")
    lines.append(f'  subgraph Context["{_esc(context_title)}"]')
    lines.append("    direction TB")

    for gid in goal_ids:
        label = goal_labels.get(gid) or gid
        lines.append(f'    {gid}["{_esc(label)}"]')

    # Prefer impact_graph goal-to-goal edges (correct causal direction)
    goal_edges = _goal_to_goal_edges(ig, set(goal_ids))
    if goal_edges:
        for frm, to in goal_edges:
            lines.append(f"    {frm} -.-> {to}")
    else:
        # Fallback only if impact_graph doesn't provide goal relationships
        for link in goal_links_fallback:
            frm = link.get("from")
            to = link.get("to")
            if frm and to and frm in goal_ids and to in goal_ids:
                lines.append(f"    {frm} -.-> {to}")

    lines.append("  end")
    lines.append("")

    # -------------------------
    # Success node
    # -------------------------
    success_id = sb.get("success_node_id") or "success"
    success_title = sb.get("title") or "SUCCESS"
    subtitle = sb.get("subtitle") or ""

    group_label = f"{_esc(success_title)}"
    if subtitle:
        group_label += f"<br/>{_esc(subtitle)}"

    lines.append("  %% --- THE GROUP GOAL ---")
    lines.append(f'  {success_id}["{group_label}"]')
    lines.append("")

    # -------------------------
    # Levers / Pillars (board layout)
    # -------------------------
    levers = sb.get("levers") or []

    # Flatten pillars in lever order to generate clean numbering
    ordered_pillars: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for lever in levers:
        for p in lever.get("pillars", []) or []:
            if isinstance(p, dict):
                ordered_pillars.append((lever, p))

    pillar_number: Dict[str, int] = {}
    for idx, (_, p) in enumerate(ordered_pillars, start=1):
        pid = p.get("id")
        if pid:
            pillar_number[pid] = idx

    growth_nodes: List[str] = []
    trust_nodes: List[str] = []

    for lever in levers:
        lever_style = (lever.get("style") or "").lower()  # "growth" | "trust"
        is_growth = lever_style == "growth"
        subgraph_name = "Growth" if is_growth else "Trust"
        title = lever.get("title") or lever.get("id") or subgraph_name

        lines.append(f'  subgraph {subgraph_name}["{_esc(title)}"]')
        lines.append("    direction LR")

        for p in lever.get("pillars", []) or []:
            if not isinstance(p, dict):
                continue

            pid = p.get("id")
            if not pid:
                continue

            # Clean label: strip any numeric prefix from YAML label, then re-number deterministically
            raw_label = p.get("label") or pid
            clean = _strip_numeric_prefix(str(raw_label))

            num = pillar_number.get(pid)
            label = f"{num}. {clean}" if num is not None else clean

            # Pillar KPI
            kpi_metric_id = p.get("kpi_metric_id") or ""
            kpi_name = _metric_name(metrics_by_id, kpi_metric_id)  # type: ignore[arg-type]

            # Acc label (preferred keys)
            accountable = (
                p.get("accountable") or p.get("responsible") or p.get("owner") or ""
            )

            # Optional: supporting metrics (if present)
            supporting_ids: List[str] = []
            for key in (
                "supporting_metric_ids",
                "supporting_metrics",
                "supporting_kpi_metric_ids",
            ):
                v = p.get(key)
                if isinstance(v, list):
                    supporting_ids.extend([str(x) for x in v if x])
                elif isinstance(v, str) and v.strip():
                    supporting_ids.append(v.strip())

            supporting_names = []
            for sid in supporting_ids:
                supporting_names.append(_metric_name(metrics_by_id, sid))  # type: ignore[arg-type]
            supporting_names = [s for s in supporting_names if s]

            parts = [f"{_esc(label)}"]
            if kpi_name:
                parts.append(f"KPI: {_esc(kpi_name)}")
            if supporting_names:
                parts.append(f"Supporting: {_esc(', '.join(supporting_names))}")
            if accountable:
                parts.append(f"Accountable: {_esc(accountable)}")

            card = "<br/>".join(parts)
            lines.append(f'    {pid}["{card}"]')

            if is_growth:
                growth_nodes.append(pid)
            else:
                trust_nodes.append(pid)

        lines.append("  end")
        lines.append("")

    # -------------------------
    # Connections
    # -------------------------
    lines.append("  %% --- CONNECTIONS ---")
    for pid in growth_nodes + trust_nodes:
        lines.append(f"  {pid} --> {success_id}")

    # Success -> goals (labelled "Impacts") via impact_graph edges
    for e in ig.get("edges", []) or []:
        if e.get("from") == success_id and e.get("to") in goal_ids:
            lines.append(f'  {success_id} == Impacts ==> {e.get("to")}')

    lines.append("")

    # -------------------------
    # Styling
    # -------------------------
    lines.append("  %% --- STYLING ---")
    lines.append(
        "  classDef kpi_growth fill:#e1f5fe,stroke:#0277bd,stroke-width:2px,color:#000"
    )
    lines.append(
        "  classDef kpi_trust fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#000"
    )

    if growth_nodes:
        lines.append(f"  class {','.join(growth_nodes)} kpi_growth")
    if trust_nodes:
        lines.append(f"  class {','.join(trust_nodes)} kpi_trust")

    lines.append(
        "  style Growth fill:#ffffff,stroke:#0288d1,stroke-width:1px,stroke-dasharray: 5 5,color:#01579b"
    )
    lines.append(
        "  style Trust fill:#ffffff,stroke:#fbc02d,stroke-width:1px,stroke-dasharray: 5 5,color:#f57f17"
    )
    lines.append(
        "  style Context fill:#f5f5f5,stroke:#bdbdbd,stroke-width:1px,color:#757575,stroke-dasharray: 5 5"
    )

    # Style goal nodes as dashed grey cards
    for gid in goal_ids:
        lines.append(
            f"  style {gid} fill:#e0e0e0,stroke:#9e9e9e,color:#616161,stroke-width:2px,stroke-dasharray: 5 5"
        )

    return "\n".join(lines)


# -------------------------
# Helpers
# -------------------------


def _metric_name(metrics_by_id: Dict[str, Dict[str, Any]], metric_id: str) -> str:
    if not metric_id:
        return ""
    m = metrics_by_id.get(metric_id) or {}
    return (m.get("name") or metric_id).strip()


def _goal_labels_from_impact_graph(impact_graph: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for n in impact_graph.get("nodes", []) or []:
        if n.get("type") == "goal" and n.get("id"):
            out[n["id"]] = n.get("label") or n["id"]
    return out


def _goal_to_goal_edges(
    impact_graph: Dict[str, Any], goal_ids: set[str]
) -> List[Tuple[str, str]]:
    edges = []
    for e in impact_graph.get("edges", []) or []:
        frm = e.get("from")
        to = e.get("to")
        if frm in goal_ids and to in goal_ids:
            edges.append((frm, to))
    return edges


_NUM_PREFIX = re.compile(r"^\s*\d+\.\s*")


def _strip_numeric_prefix(label: str) -> str:
    return _NUM_PREFIX.sub("", label).strip()


def _esc(text: str) -> str:
    # Escape quotes and remove angle brackets (HTML tags not allowed in v10+)
    return str(text).replace('"', "&quot;").replace("<", "").replace(">", "")
