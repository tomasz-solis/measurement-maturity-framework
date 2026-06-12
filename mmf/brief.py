"""One-page measurement-readiness brief (Markdown).

Deterministic, template slot-filled from the structured score, decision map, and
top debt (PRD principle P6) — no generated narrative, no model calls. The same
pack always produces the same brief, suitable for pasting into a planning doc.
"""

from __future__ import annotations

from typing import Any, List, Mapping, Optional

from .vertical_scoring import STRONG, WEAK, VerticalScore, score_vertical


def _vertical_name(pack: Mapping[str, Any]) -> str:
    vertical = pack.get("vertical")
    if isinstance(vertical, dict) and vertical.get("name"):
        return str(vertical["name"])
    meta = pack.get("pack")
    if isinstance(meta, dict) and meta.get("name"):
        return str(meta["name"])
    return "Untitled Vertical"


def _summary(name: str, score: VerticalScore) -> str:
    weak = [d.name for d in score.dimensions if d.band == WEAK]
    if score.decisions_total:
        decision_bit = (
            f"{score.decisions_ready} of {score.decisions_total} key decisions are "
            "backed by trusted, owned metrics"
        )
    else:
        decision_bit = "no recurring decisions are documented yet"
    if weak:
        weak_bit = f" The main gaps are in {_join(weak)}."
    else:
        weak_bit = " No dimension is rated weak."
    return f"{name} is rated **{score.overall_band}**: {decision_bit}.{weak_bit}"


def _strengths(score: VerticalScore) -> List[str]:
    out = [f"{d.name} - {d.driver}" for d in score.dimensions if d.band == STRONG]
    if not score.debt:
        out.append("No measurement debt detected from the structure.")
    return out


def _risks(score: VerticalScore) -> List[str]:
    out = [f"{d.name} - {d.driver}" for d in score.dimensions if d.band == WEAK]
    for item in score.debt[:3]:
        label = item.type.replace("_", " ")
        out.append(f"{item.severity.title()} {label}: {item.description}")
    return out


def _next_actions(score: VerticalScore) -> List[str]:
    actions: List[str] = []
    seen = set()
    for item in score.debt[:3]:
        fix = (item.recommended_fix or "").strip()
        if fix and fix not in seen:
            actions.append(fix)
            seen.add(fix)
    # If debt did not supply enough concrete fixes, add weak-dimension prompts.
    for d in score.dimensions:
        if d.band == WEAK and len(actions) < 3:
            prompt = f"Address {d.name.lower()}: {d.driver}"
            if prompt not in seen:
                actions.append(prompt)
                seen.add(prompt)
    return actions


def _join(items: List[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f" and {items[-1]}"


def _bullets(items: List[str], empty: str) -> List[str]:
    return [f"- {x}" for x in items] if items else [f"- {empty}"]


def build_brief(
    pack: Mapping[str, Any],
    score: Optional[VerticalScore] = None,
) -> str:
    """Return a Markdown one-page brief for a v2 vertical pack."""
    if score is None:
        score = score_vertical(pack)

    name = _vertical_name(pack)
    lines: List[str] = [f"# Measurement Readiness Brief: {name}", ""]

    lines.append(f"Readiness: **{score.overall_band}**")
    if score.decisions_total:
        lines.append(
            f"Decision support: {score.decisions_ready} of "
            f"{score.decisions_total} key decisions are decision-ready."
        )
    lines += ["", "## Summary", _summary(name, score), ""]

    lines.append("## Strengths")
    lines += _bullets(_strengths(score), "None identified yet.")
    lines.append("")

    lines.append("## Risks")
    lines += _bullets(_risks(score), "No material risks detected.")
    lines.append("")

    lines.append("## Recommended next actions")
    actions = _next_actions(score)
    if actions:
        lines += [f"{i}. {a}" for i, a in enumerate(actions, 1)]
    else:
        lines.append("1. Maintain the current review rhythm and re-check next cycle.")

    return "\n".join(lines).rstrip() + "\n"
