"""Decision-centered view of a v2 vertical pack.

Turns the decision-readiness results plus the debt graph into per-decision rows
suitable for the app's Decision Map section and the one-page brief.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional

from .measurement_debt import DebtItem
from .vertical_scoring import NOT_READY, READY, USABLE, VerticalScore

_READABLE_STATUS = {
    READY: "Decision-ready",
    USABLE: "Usable with caution",
    NOT_READY: "Not ready",
}

_NEXT_STEP = {
    READY: "No blocking measurement gap. Keep guardrails in the review rhythm.",
    USABLE: "Close the noted gap before treating this as a hard decision gate.",
    NOT_READY: "Resolve the blocking metric or debt before using this decision.",
}


@dataclass
class DecisionView:
    """A single decision enriched for display."""

    id: str
    question: str
    owner: Optional[str]
    cadence: Optional[str]
    decision_type: Optional[str]
    required_metrics: List[str]
    guardrails: List[str]
    missing_metrics: List[str]
    readiness: str  # human-readable
    related_debt: List[DebtItem] = field(default_factory=list)
    next_step: str = ""
    reasons: List[str] = field(default_factory=list)


def build_decision_map(
    pack: Mapping[str, Any],
    score: VerticalScore,
) -> List[DecisionView]:
    """Build per-decision views from a scored vertical."""
    metric_ids = {
        m.get("id") for m in (pack.get("metrics") or []) if isinstance(m, dict)
    }
    name_by_id = {
        m.get("id"): m.get("name", m.get("id"))
        for m in (pack.get("metrics") or [])
        if isinstance(m, dict)
    }
    readiness_by_id = {r.id: r for r in score.decision_readiness}

    views: List[DecisionView] = []
    for d in pack.get("decisions") or []:
        if not isinstance(d, dict):
            continue
        did = d.get("id", "")
        required = d.get("required_metrics") or []
        guardrails = d.get("guardrails") or []
        missing = [m for m in (required + guardrails) if m not in metric_ids]
        r = readiness_by_id.get(did)
        status_key = r.status if r else NOT_READY
        related = [
            item
            for item in score.debt
            if did in item.affected_decisions
            or set(item.affected_metrics) & set(required + guardrails)
        ]
        views.append(
            DecisionView(
                id=did,
                question=d.get("question", ""),
                owner=d.get("owner"),
                cadence=d.get("cadence"),
                decision_type=d.get("decision_type"),
                required_metrics=[name_by_id.get(m, m) for m in required],
                guardrails=[name_by_id.get(m, m) for m in guardrails],
                missing_metrics=missing,
                readiness=_READABLE_STATUS.get(status_key, status_key),
                related_debt=related,
                next_step=_NEXT_STEP.get(status_key, ""),
                reasons=r.reasons if r else [],
            )
        )
    return views
