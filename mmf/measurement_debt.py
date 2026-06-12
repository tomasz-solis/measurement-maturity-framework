"""Measurement debt for v2 vertical packs.

Most debt is *derived* from the pack's graph (PRD principle P2): orphaned
metrics, decisions that reference undefined metrics, missing guardrails,
incomplete instrumentation, and so on. Authored debt (the optional
``measurement_debt`` block) is merged in for problems the graph cannot see.

Authored debt is additive to the debt list only; it is never turned into a
separate scoring dimension (see docs/V2_SCORING_METHODOLOGY.md), so disclosing
a known problem does not, by itself, lower a vertical's dimension bands (P4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping

# Ordered worst -> best. Used for sorting and for "blocking" checks.
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

RISK_BEARING_TYPES = {
    "rollout",
    "launch",
    "ranking_change",
    "pricing_change",
    "default_change",
    "deprecation",
}


@dataclass
class DebtItem:
    """A single measurement-debt entry, derived or authored."""

    id: str
    type: str
    severity: str
    description: str
    affected_metrics: List[str] = field(default_factory=list)
    affected_decisions: List[str] = field(default_factory=list)
    recommended_fix: str = ""
    source: str = "derived"  # derived | authored


def severity_rank(severity: str) -> int:
    """Return a sortable rank for a severity (lower = more severe)."""
    return SEVERITY_ORDER.get((severity or "").lower(), 99)


def _is_owned(metric: Mapping[str, Any]) -> bool:
    return bool(metric.get("accountable") or metric.get("responsible"))


def _has_sql(metric: Mapping[str, Any]) -> bool:
    sql = metric.get("sql") or {}
    if not isinstance(sql, dict):
        return False
    has_value = bool(sql.get("value"))
    has_ratio = bool(sql.get("numerator")) and bool(sql.get("denominator"))
    return has_value or has_ratio


def graph_linkage(pack: Mapping[str, Any]) -> Dict[str, Dict[str, bool]]:
    """Return, per metric id, whether it is linked to a decision and/or an OKR.

    A metric counts as decision-linked if it appears in any decision's
    ``required_metrics``/``guardrails`` or names a resolvable decision in its
    own ``linked_decisions``. OKR-linked is the analogous check across
    ``okrs`` and the metric's ``linked_okrs``.
    """
    metrics = [m for m in (pack.get("metrics") or []) if isinstance(m, dict)]

    decisions = [d for d in (pack.get("decisions") or []) if isinstance(d, dict)]
    decision_ids = {d.get("id") for d in decisions}
    dec_referenced: set = set()
    for d in decisions:
        for mid in (d.get("required_metrics") or []) + (d.get("guardrails") or []):
            dec_referenced.add(mid)

    okr_metric_ids: set = set()
    for okr in pack.get("okrs") or []:
        if not isinstance(okr, dict):
            continue
        for kr in okr.get("key_results") or []:
            if isinstance(kr, dict):
                okr_metric_ids.update(kr.get("linked_metrics") or [])

    linkage: Dict[str, Dict[str, bool]] = {}
    for m in metrics:
        mid = m.get("id", "")
        decision_linked = mid in dec_referenced or any(
            d in decision_ids for d in (m.get("linked_decisions") or [])
        )
        okr_linked = bool(m.get("linked_okrs")) or mid in okr_metric_ids
        linkage[mid] = {"decision": decision_linked, "okr": okr_linked}
    return linkage


def derive_debt(
    pack: Mapping[str, Any],
    l1_scores: Mapping[str, float],
) -> List[DebtItem]:
    """Derive debt items from the pack graph (no authored input read here)."""
    items: List[DebtItem] = []
    metrics = [m for m in (pack.get("metrics") or []) if isinstance(m, dict)]
    metrics_by_id = {m.get("id", ""): m for m in metrics}
    linkage = graph_linkage(pack)

    # --- Metric-level derived debt ---
    for m in metrics:
        mid = m.get("id", "")
        link = linkage.get(mid, {"decision": False, "okr": False})
        if not link["decision"] and not link["okr"]:
            items.append(
                DebtItem(
                    id=f"orphan_{mid}",
                    type="decision_linkage",
                    severity="medium",
                    description=f"Metric '{mid}' is not linked to any decision or OKR.",
                    affected_metrics=[mid],
                    recommended_fix="Assign a role and map it to a decision or an explicit diagnostic use.",
                )
            )
        elif link["okr"] and not link["decision"]:
            items.append(
                DebtItem(
                    id=f"okr_only_{mid}",
                    type="decision_linkage",
                    severity="low",
                    description=f"Metric '{mid}' is linked to an OKR but to no recurring decision.",
                    affected_metrics=[mid],
                    recommended_fix="Map it to a recurring decision or mark it diagnostic.",
                )
            )
        if not _has_sql(m):
            items.append(
                DebtItem(
                    id=f"missing_sql_{mid}",
                    type="definition",
                    severity="medium",
                    description=f"Metric '{mid}' has no source-controlled SQL definition.",
                    affected_metrics=[mid],
                    recommended_fix="Add query logic so the metric can be reproduced and reviewed.",
                )
            )
        if not m.get("tests"):
            items.append(
                DebtItem(
                    id=f"missing_tests_{mid}",
                    type="testing",
                    severity="low",
                    description=f"Metric '{mid}' has no tests.",
                    affected_metrics=[mid],
                    recommended_fix="Add basic checks (not_null, range) before teams rely on it.",
                )
            )
        if not _is_owned(m):
            items.append(
                DebtItem(
                    id=f"missing_owner_{mid}",
                    type="ownership",
                    severity="medium",
                    description=f"Metric '{mid}' has no accountable or responsible owner.",
                    affected_metrics=[mid],
                    recommended_fix="Name an accountable team or role.",
                )
            )

    # --- Decision-level derived debt ---
    for d in pack.get("decisions") or []:
        if not isinstance(d, dict):
            continue
        did = d.get("id", "")
        for mid in (d.get("required_metrics") or []) + (d.get("guardrails") or []):
            if mid not in metrics_by_id:
                items.append(
                    DebtItem(
                        id=f"missing_metric_{did}_{mid}",
                        type="decision_linkage",
                        severity="high",
                        description=(
                            f"Decision '{did}' references metric '{mid}', "
                            "which is not defined in the pack."
                        ),
                        affected_decisions=[did],
                        recommended_fix=f"Define '{mid}' or remove the reference.",
                    )
                )
        is_risk = (d.get("decision_type") or "").lower() in RISK_BEARING_TYPES
        if is_risk and not (d.get("guardrails") or []):
            items.append(
                DebtItem(
                    id=f"no_guardrail_{did}",
                    type="operating_rhythm",
                    severity="medium",
                    description=(
                        f"Risk-bearing decision '{did}' has no guardrail metric."
                    ),
                    affected_decisions=[did],
                    recommended_fix="Add a guardrail that protects against harmful optimization.",
                )
            )

    # --- Instrumentation derived debt ---
    for instr in pack.get("instrumentation") or []:
        if not isinstance(instr, dict):
            continue
        status = (instr.get("status") or "").lower()
        if status and status != "complete":
            items.append(
                DebtItem(
                    id=f"instrumentation_{instr.get('id')}",
                    type="instrumentation",
                    severity="high" if status == "missing" else "medium",
                    description=(f"Instrumentation '{instr.get('id')}' is {status}."),
                    recommended_fix="Complete instrumentation before relying on dependent metrics.",
                )
            )

    # --- Strategy-linkage derived debt ---
    for okr in pack.get("okrs") or []:
        if not isinstance(okr, dict):
            continue
        for kr in okr.get("key_results") or []:
            if not isinstance(kr, dict):
                continue
            resolvable = [
                mid for mid in (kr.get("linked_metrics") or []) if mid in metrics_by_id
            ]
            if not resolvable:
                items.append(
                    DebtItem(
                        id=f"okr_kr_{kr.get('id')}",
                        type="strategy_linkage",
                        severity="low",
                        description=(
                            f"Key result '{kr.get('id')}' has no resolvable metric."
                        ),
                        recommended_fix="Link the key result to a defined metric.",
                    )
                )

    return items


def _authored_debt(pack: Mapping[str, Any]) -> List[DebtItem]:
    items: List[DebtItem] = []
    for entry in pack.get("measurement_debt") or []:
        if not isinstance(entry, dict):
            continue
        items.append(
            DebtItem(
                id=entry.get("id", "authored"),
                type=entry.get("type", "definition"),
                severity=entry.get("severity", "medium"),
                description=entry.get("description", ""),
                affected_metrics=list(entry.get("affected_metrics") or []),
                affected_decisions=list(entry.get("affected_decisions") or []),
                recommended_fix=entry.get("recommended_fix", ""),
                source="authored",
            )
        )
    return items


def build_debt(
    pack: Mapping[str, Any],
    l1_scores: Mapping[str, float],
) -> List[DebtItem]:
    """Return derived + authored debt, sorted by (severity, type, id).

    The sort is a total order, so the top-N is deterministic (PRD P6).
    """
    items = derive_debt(pack, l1_scores) + _authored_debt(pack)
    items.sort(key=lambda d: (severity_rank(d.severity), d.type, d.id))
    return items
