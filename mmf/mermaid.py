"""Mermaid diagram generation for strategy boards."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Set, Tuple


def build_strategy_mermaid(pack: Mapping[str, Any]) -> str:
    """Build a Mermaid flowchart for the pack's strategy board.

    The diagram has four sections rendered top-to-bottom:
      1. Company goals subgraph (context box)
      2. Team success node
      3. Lever/pillar subgraphs (growth and trust lanes)
      4. Connections and styling

    Requires the pack to contain a ``strategy_board`` key.
    ``impact_graph`` is optional but improves goal label resolution and
    edge direction.
    """
    sb = pack.get("strategy_board") or {}
    ig = pack.get("impact_graph") or {}
    metrics_by_id: Dict[str, Dict[str, Any]] = {}
    for metric in pack.get("metrics", []) or []:
        if not isinstance(metric, dict):
            continue
        metric_id = metric.get("id")
        if isinstance(metric_id, str) and metric_id:
            metrics_by_id[metric_id] = metric

    lines: List[str] = ["flowchart TB"]
    lines.extend(_render_goals_subgraph(sb, ig))
    lines.extend(_render_success_node(sb))

    lever_result = _render_levers_subgraph(sb, ig, metrics_by_id)
    lines.extend(lever_result["lines"])

    lines.extend(
        _render_connections(
            ig=ig,
            success_id=lever_result["success_id"],
            goal_ids=lever_result["goal_ids"],
            pillar_ids=lever_result["growth_nodes"] + lever_result["trust_nodes"],
        )
    )
    lines.extend(
        _render_styles(
            goal_ids=lever_result["goal_ids"],
            growth_nodes=lever_result["growth_nodes"],
            trust_nodes=lever_result["trust_nodes"],
            growth_groups=lever_result["growth_groups"],
            trust_groups=lever_result["trust_groups"],
        )
    )

    return "\n".join(lines)


def build_vertical_strategy_mermaid(pack: Mapping[str, Any]) -> str:
    """Build a Mermaid flowchart for a v2 vertical pack's strategy.

    Ladders bottom-up: primary/supporting metrics -> OKRs -> the vertical ->
    vertical outcomes -> company goals. Returns "" when there is nothing to draw
    (an L0/L1 pack without strategy or OKRs).
    """
    _strategy = pack.get("strategy")
    strategy: Dict[str, Any] = _strategy if isinstance(_strategy, dict) else {}
    goals = [
        g
        for g in (strategy.get("company_goals") or [])
        if isinstance(g, dict) and g.get("id")
    ]
    outcomes = [
        o
        for o in (strategy.get("vertical_outcomes") or [])
        if isinstance(o, dict) and o.get("id")
    ]
    okrs = [o for o in (pack.get("okrs") or []) if isinstance(o, dict) and o.get("id")]
    metrics_by_id: Dict[str, Any] = {
        str(m.get("id")): m
        for m in (pack.get("metrics") or [])
        if isinstance(m, dict) and m.get("id")
    }

    if not (goals or outcomes or okrs):
        return ""

    _vertical = pack.get("vertical")
    vertical: Dict[str, Any] = _vertical if isinstance(_vertical, dict) else {}
    _meta = pack.get("pack")
    meta: Dict[str, Any] = _meta if isinstance(_meta, dict) else {}
    vname = vertical.get("name") or meta.get("name") or "Vertical"
    vnode = "v_node"

    lines: List[str] = ["flowchart BT"]

    if goals:
        lines.append('  subgraph Goals["Company Goals"]')
        lines.append("    direction LR")
        for g in goals:
            lines.append(f'    g_{_safe(g["id"])}["{_esc(g.get("name") or g["id"])}"]')
        lines += ["  end", ""]

    for o in outcomes:
        lines.append(f'  o_{_safe(o["id"])}(["{_esc(o.get("name") or o["id"])}"])')
    if outcomes:
        lines.append("")

    lines += [f'  {vnode}["{_esc(vname)}"]', ""]

    for okr in okrs:
        lines.append(
            f'  k_{_safe(okr["id"])}["{_esc(okr.get("objective") or okr["id"])}"]'
        )
    if okrs:
        lines.append("")

    rendered_metrics: List[str] = []
    metric_edges: List[Tuple[str, str]] = []
    for okr in okrs:
        linked: List[str] = []
        for kr in okr.get("key_results") or []:
            if isinstance(kr, dict):
                linked += list(kr.get("linked_metrics") or [])
        for m_id, metric in metrics_by_id.items():
            if okr["id"] in (metric.get("linked_okrs") or []):
                linked.append(m_id)
        for m_id in dict.fromkeys(linked):
            if m_id not in metrics_by_id:
                continue
            if m_id not in rendered_metrics:
                name = metrics_by_id[m_id].get("name") or m_id
                lines.append(f'  m_{_safe(m_id)}["{_esc(name)}"]')
                rendered_metrics.append(m_id)
            metric_edges.append((f"m_{_safe(m_id)}", f"k_{_safe(okr['id'])}"))
    if rendered_metrics:
        lines.append("")

    lines.append("  %% --- CONNECTIONS ---")
    for src, dst in metric_edges:
        lines.append(f"  {src} --> {dst}")
    for okr in okrs:
        lines.append(f"  k_{_safe(okr['id'])} --> {vnode}")
    for o in outcomes:
        lines.append(f"  {vnode} --> o_{_safe(o['id'])}")
    goal_id_set = {g["id"] for g in goals}
    for o in outcomes:
        for gid in o.get("linked_company_goals") or []:
            if gid in goal_id_set:
                lines.append(f"  o_{_safe(o['id'])} == ladders ==> g_{_safe(gid)}")
    lines.append("")

    lines.append("  classDef metric fill:#eef2ff,stroke:#4f6dff,color:#10131a")
    lines.append("  classDef okr fill:#e6f7f1,stroke:#1ecf9b,color:#10131a")
    lines.append("  classDef outcome fill:#fff7e6,stroke:#d18a1f,color:#10131a")
    if rendered_metrics:
        lines.append(
            "  class " + ",".join(f"m_{_safe(m)}" for m in rendered_metrics) + " metric"
        )
    if okrs:
        lines.append(
            "  class " + ",".join(f"k_{_safe(o['id'])}" for o in okrs) + " okr"
        )
    if outcomes:
        lines.append(
            "  class " + ",".join(f"o_{_safe(o['id'])}" for o in outcomes) + " outcome"
        )
    lines.append(f"  style {vnode} fill:#0d1015,stroke:#0d1015,color:#ffffff")
    for g in goals:
        lines.append(
            f"  style g_{_safe(g['id'])} fill:#e0e0e0,stroke:#9e9e9e,color:#616161"
        )

    return "\n".join(lines)


def _safe(text: str) -> str:
    """Sanitise an id into a Mermaid-safe node id fragment."""
    return re.sub(r"[^0-9A-Za-z_]", "_", str(text))


# -------------------------
# Section renderers
# -------------------------


def _render_goals_subgraph(sb: Dict[str, Any], ig: Dict[str, Any]) -> List[str]:
    """Render the company goals context subgraph.

    Pulls goal IDs and labels from ``strategy_board.company_goals_box``.
    Goal-to-goal edges come from ``impact_graph`` when available, with a
    fallback to any ``links`` defined on the goals box directly.
    """
    goals_box = sb.get("company_goals_box") or {}
    context_title = goals_box.get("title") or "Company Goals"
    goals = goals_box.get("goals") or []
    goal_links_fallback = goals_box.get("links") or []

    goal_labels = _goal_labels_from_impact_graph(ig)
    goal_ids = [g.get("id") for g in goals if g.get("id")]

    lines: List[str] = [
        "  %% --- TOP LEVEL: COMPANY GOALS ---",
        f'  subgraph Context["{_esc(context_title)}"]',
        "    direction TB",
    ]

    for gid in goal_ids:
        label = goal_labels.get(gid) or gid
        lines.append(f'    {gid}["{_esc(label)}"]')

    # Prefer impact_graph goal-to-goal edges (correct causal direction)
    goal_edges = _goal_to_goal_edges(ig, set(goal_ids))
    if goal_edges:
        for frm, to in goal_edges:
            lines.append(f"    {frm} -.-> {to}")
    else:
        for link in goal_links_fallback:
            frm = link.get("from")
            to = link.get("to")
            if frm and to and frm in goal_ids and to in goal_ids:
                lines.append(f"    {frm} -.-> {to}")

    lines += ["  end", ""]
    return lines


def _render_success_node(sb: Dict[str, Any]) -> List[str]:
    """Render the team success node that sits between levers and company goals."""
    success_id = sb.get("success_node_id") or "success"
    success_title = sb.get("title") or "SUCCESS"
    subtitle = sb.get("subtitle") or ""

    label = _esc(success_title)
    if subtitle:
        label += f"<br/>{_esc(subtitle)}"

    return [
        "  %% --- THE GROUP GOAL ---",
        f'  {success_id}["{label}"]',
        "",
    ]


def _render_levers_subgraph(
    sb: Dict[str, Any],
    ig: Dict[str, Any],
    metrics_by_id: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Render all lever/pillar subgraphs and return node tracking data.

    Returns a dict with:
      - ``lines``: rendered Mermaid lines
      - ``success_id``: the team success node ID
      - ``goal_ids``: list of company goal IDs (for connection rendering)
      - ``growth_nodes`` / ``trust_nodes``: pillar node IDs by lane
      - ``growth_groups`` / ``trust_groups``: subgraph names by lane
    """
    levers = sb.get("levers") or []
    success_id = sb.get("success_node_id") or "success"

    goals_box = sb.get("company_goals_box") or {}
    goal_ids = [g.get("id") for g in (goals_box.get("goals") or []) if g.get("id")]

    # Assign stable 1-based numbers to pillars across all levers
    pillar_number = _build_pillar_numbers(levers)

    lines: List[str] = []
    growth_nodes: List[str] = []
    trust_nodes: List[str] = []
    growth_groups: List[str] = []
    trust_groups: List[str] = []
    growth_count = 0
    trust_count = 0

    for lever in levers:
        is_growth = (lever.get("style") or "").lower() == "growth"

        if is_growth:
            growth_count += 1
            group = "Growth" if growth_count == 1 else f"Growth{growth_count}"
            growth_groups.append(group)
        else:
            trust_count += 1
            group = "Trust" if trust_count == 1 else f"Trust{trust_count}"
            trust_groups.append(group)

        title = lever.get("title") or lever.get("id") or group
        lines.append(f'  subgraph {group}["{_esc(title)}"]')
        lines.append("    direction LR")

        for p in lever.get("pillars", []) or []:
            if not isinstance(p, dict):
                continue
            pid = p.get("id")
            if not pid:
                continue

            card = _build_pillar_card(p, pid, pillar_number, metrics_by_id)
            lines.append(f'    {pid}["{card}"]')

            if is_growth:
                growth_nodes.append(pid)
            else:
                trust_nodes.append(pid)

        lines += ["  end", ""]

    return {
        "lines": lines,
        "success_id": success_id,
        "goal_ids": goal_ids,
        "growth_nodes": growth_nodes,
        "trust_nodes": trust_nodes,
        "growth_groups": growth_groups,
        "trust_groups": trust_groups,
    }


def _render_connections(
    ig: Dict[str, Any],
    success_id: str,
    goal_ids: List[str],
    pillar_ids: List[str],
) -> List[str]:
    """Render edges: pillars → success, and success → company goals."""
    lines: List[str] = ["  %% --- CONNECTIONS ---"]

    for pid in pillar_ids:
        lines.append(f"  {pid} --> {success_id}")

    for e in ig.get("edges", []) or []:
        if e.get("from") == success_id and e.get("to") in goal_ids:
            lines.append(f'  {success_id} == Impacts ==> {e.get("to")}')

    lines.append("")
    return lines


def _render_styles(
    goal_ids: List[str],
    growth_nodes: List[str],
    trust_nodes: List[str],
    growth_groups: List[str],
    trust_groups: List[str],
) -> List[str]:
    """Render all classDef, class, and style declarations."""
    lines: List[str] = [
        "  %% --- STYLING ---",
        "  classDef kpi_growth fill:#e1f5fe,stroke:#0277bd,stroke-width:2px,color:#000",
        "  classDef kpi_trust fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#000",
    ]

    if growth_nodes:
        lines.append(f"  class {','.join(growth_nodes)} kpi_growth")
    if trust_nodes:
        lines.append(f"  class {','.join(trust_nodes)} kpi_trust")

    for group in growth_groups:
        lines.append(
            f"  style {group} fill:#ffffff,stroke:#0288d1,"
            "stroke-width:1px,stroke-dasharray: 5 5,color:#01579b"
        )
    for group in trust_groups:
        lines.append(
            f"  style {group} fill:#ffffff,stroke:#fbc02d,"
            "stroke-width:1px,stroke-dasharray: 5 5,color:#f57f17"
        )

    lines.append(
        "  style Context fill:#f5f5f5,stroke:#bdbdbd,"
        "stroke-width:1px,color:#757575,stroke-dasharray: 5 5"
    )

    for gid in goal_ids:
        lines.append(
            f"  style {gid} fill:#e0e0e0,stroke:#9e9e9e,"
            "color:#616161,stroke-width:2px,stroke-dasharray: 5 5"
        )

    return lines


# -------------------------
# Private helpers
# -------------------------


def _build_pillar_numbers(levers: List[Dict[str, Any]]) -> Dict[str, int]:
    """Assign stable 1-based numbers to pillars in lever order."""
    numbers: Dict[str, int] = {}
    idx = 1
    for lever in levers:
        for p in lever.get("pillars", []) or []:
            if isinstance(p, dict) and p.get("id"):
                numbers[p["id"]] = idx
                idx += 1
    return numbers


def _build_pillar_card(
    p: Dict[str, Any],
    pid: str,
    pillar_number: Dict[str, int],
    metrics_by_id: Dict[str, Dict[str, Any]],
) -> str:
    """Build the display card text for a single pillar node.

    Format:
      <number>. <label>
      KPI: <name>          (if kpi_metric_id is set)
      Supporting: <names>  (if supporting metric IDs are set)
      Accountable: <team>  (if accountable/responsible/owner is set)
    """
    raw_label = p.get("label") or pid
    clean = _strip_numeric_prefix(str(raw_label))
    num = pillar_number.get(pid)
    label = f"{num}. {clean}" if num is not None else clean

    kpi_id = p.get("kpi_metric_id") or ""
    kpi_name = _metric_name(metrics_by_id, kpi_id)

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

    supporting_names = [
        name for sid in supporting_ids if (name := _metric_name(metrics_by_id, sid))
    ]

    accountable = p.get("accountable") or p.get("responsible") or p.get("owner") or ""

    parts = [_esc(label)]
    if kpi_name:
        parts.append(f"KPI: {_esc(kpi_name)}")
    if supporting_names:
        parts.append(f"Supporting: {_esc(', '.join(supporting_names))}")
    if accountable:
        parts.append(f"Accountable: {_esc(accountable)}")

    return "<br/>".join(parts)


def _metric_name(metrics_by_id: Dict[str, Dict[str, Any]], metric_id: str) -> str:
    """Resolve a metric ID to a display name, returning the ID if not found."""
    if not metric_id:
        return ""
    m = metrics_by_id.get(metric_id) or {}
    return (m.get("name") or metric_id).strip()


def _goal_labels_from_impact_graph(impact_graph: Dict[str, Any]) -> Dict[str, str]:
    """Extract goal ID → label mapping from impact graph nodes."""
    out: Dict[str, str] = {}
    for node in impact_graph.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        goal_id = node.get("id")
        if node.get("type") == "goal" and isinstance(goal_id, str) and goal_id:
            out[goal_id] = str(node.get("label") or goal_id)
    return out


def _goal_to_goal_edges(
    impact_graph: Dict[str, Any], goal_ids: Set[str]
) -> List[Tuple[str, str]]:
    """Return impact-graph edges where both endpoints are goal nodes."""
    return [
        (e["from"], e["to"])
        for e in (impact_graph.get("edges", []) or [])
        if e.get("from") in goal_ids and e.get("to") in goal_ids
    ]


_NUM_PREFIX = re.compile(r"^\s*\d+\.\s*")


def _strip_numeric_prefix(label: str) -> str:
    """Remove numeric list prefixes before deterministic re-numbering."""
    return _NUM_PREFIX.sub("", label).strip()


def _esc(text: str) -> str:
    """Escape text for Mermaid labels - removes angle brackets, escapes quotes."""
    return str(text).replace('"', "&quot;").replace("<", "").replace(">", "")
