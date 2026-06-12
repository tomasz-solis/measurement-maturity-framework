"""Layer 2 — vertical measurement readiness scoring.

Decision-centric: readiness is built bottom-up from whether each key decision
is backed by trusted, owned, instrumented, guardrailed metrics, then rolled up
into eight ordinal dimension bands and an overall band. There is no metric-count
term anywhere in this module (PRD principle P1).

See docs/V2_SCORING_METHODOLOGY.md for the full specification; this code is the
source of truth if the two disagree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .config import ScoringConfig
from .measurement_debt import (
    DebtItem,
    RISK_BEARING_TYPES,
    build_debt,
    graph_linkage,
    severity_rank,
)
from .scoring import score_pack

# A metric must be "decision-ready" (>= 80) to gate a decision — a deliberately
# higher bar than the 60 "usable" cutoff.
TRUSTED_THRESHOLD = 80.0

READY = "READY"
USABLE = "USABLE_WITH_CAUTION"
NOT_READY = "NOT_READY"

STRONG, PARTIAL, WEAK, NOT_ASSESSED = "Strong", "Partial", "Weak", "Not assessed"

# Best -> worst.
BAND_ORDER = [
    "Decision-ready",
    "Usable with caution",
    "Fragile",
    "Not ready for recurring decisions",
]

# Per-dimension cap applied to the overall band when a dimension is Weak.
_DIMENSION_CAP = {
    "Decision coverage & linkage": "Fragile",
    "Metric definition quality": "Fragile",
    "Instrumentation readiness": "Fragile",
    "Portfolio role clarity": "Usable with caution",
    "Guardrail coverage": "Usable with caution",
    "Operating rhythm": "Usable with caution",
    "Ownership clarity": "Usable with caution",
    "Strategy / OKR linkage": "Usable with caution",
}


@dataclass
class DecisionReadiness:
    """Readiness of a single decision."""

    id: str
    question: str
    status: str  # READY | USABLE_WITH_CAUTION | NOT_READY
    reasons: List[str] = field(default_factory=list)


@dataclass
class Dimension:
    """One scored dimension and the evidence behind its band."""

    name: str
    band: str  # Strong | Partial | Weak | Not assessed
    driver: str


@dataclass
class VerticalScore:
    """Full Layer-2 result for one vertical pack."""

    decisions_ready: int
    decisions_total: int
    fraction: Optional[float]
    overall_band: str
    decision_readiness: List[DecisionReadiness]
    dimensions: List[Dimension]
    debt: List[DebtItem]
    l1_pack_score: float

    def dimension(self, name: str) -> Optional[Dimension]:
        """Return the named dimension, or None."""
        for d in self.dimensions:
            if d.name == name:
                return d
        return None


def _worse(a: str, b: str) -> str:
    """Return the worse (lower-ranked) of two overall bands."""
    return a if BAND_ORDER.index(a) >= BAND_ORDER.index(b) else b


def _owned(metric: Mapping[str, Any]) -> bool:
    return bool(metric.get("accountable") or metric.get("responsible"))


def _is_risk(decision: Mapping[str, Any]) -> bool:
    return (decision.get("decision_type") or "").lower() in RISK_BEARING_TYPES


def _fraction_band(ready: int, total: int) -> Optional[str]:
    if total == 0:
        return None
    r = ready / total
    if r >= 1.0:
        return "Decision-ready"
    if r >= 0.5:
        return "Usable with caution"
    if r > 0:
        return "Fragile"
    return "Not ready for recurring decisions"


def _decision_status(
    decision: Mapping[str, Any],
    metrics_by_id: Mapping[str, Any],
    l1_scores: Mapping[str, float],
    debt: List[DebtItem],
    rhythm_weak: bool,
) -> DecisionReadiness:
    required = decision.get("required_metrics") or []
    guardrails = decision.get("guardrails") or []
    reasons: List[str] = []

    missing_ref = [m for m in (required + guardrails) if m not in metrics_by_id]
    untrusted = [
        m
        for m in required
        if m in metrics_by_id
        and (l1_scores.get(m, 0.0) < TRUSTED_THRESHOLD or not _owned(metrics_by_id[m]))
    ]
    blocking = [
        d.id
        for d in debt
        if severity_rank(d.severity) <= 1  # critical or high
        and set(d.affected_metrics) & set(required)
    ]
    missing_guard = _is_risk(decision) and not guardrails

    if missing_ref:
        reasons.append(f"references undefined metric(s): {', '.join(missing_ref)}")
    if untrusted:
        reasons.append(
            f"required metric(s) not decision-ready or unowned: {', '.join(untrusted)}"
        )
    if blocking:
        reasons.append(f"blocked by high-severity debt: {', '.join(blocking)}")

    if missing_ref or untrusted or blocking:
        status = NOT_READY
    elif missing_guard:
        status = USABLE
        reasons.append("risk-bearing decision has no guardrail")
    elif guardrails and rhythm_weak:
        status = USABLE
        reasons.append("guardrails exist but are not part of a clear review rhythm")
    else:
        status = READY

    return DecisionReadiness(
        id=decision.get("id", "unknown"),
        question=decision.get("question", ""),
        status=status,
        reasons=reasons,
    )


def _operating_rhythm_band(pack: Mapping[str, Any]) -> Dimension:
    om = pack.get("operating_model")
    if not isinstance(om, dict):
        return Dimension(
            "Operating rhythm", NOT_ASSESSED, "No operating_model provided."
        )
    has_cadence = bool(om.get("review_cadence"))
    has_evidence = bool(om.get("decision_log_exists")) or bool(om.get("last_reviewed"))
    if has_cadence and has_evidence:
        band, driver = STRONG, "Review cadence plus a decision log or recent review."
    elif has_cadence:
        band, driver = (
            PARTIAL,
            "A review cadence exists but there is little evidence it runs.",
        )
    else:
        band, driver = WEAK, "No review cadence and no evidence of recurring review."
    return Dimension("Operating rhythm", band, driver)


def score_vertical(
    pack: Mapping[str, Any],
    config: Optional[ScoringConfig] = None,
) -> VerticalScore:
    """Compute Layer-2 vertical readiness for a v2 pack."""
    metrics = [m for m in (pack.get("metrics") or []) if isinstance(m, dict)]
    metrics_by_id: Dict[str, Any] = {m.get("id", ""): m for m in metrics}

    l1 = score_pack(pack, config)
    l1_scores = {ms.metric_id: ms.score for ms in l1.metric_scores}

    debt = build_debt(pack, l1_scores)

    rhythm = _operating_rhythm_band(pack)
    rhythm_weak = rhythm.band == WEAK

    decisions = [d for d in (pack.get("decisions") or []) if isinstance(d, dict)]
    readiness = [
        _decision_status(d, metrics_by_id, l1_scores, debt, rhythm_weak)
        for d in decisions
    ]
    ready_count = sum(1 for r in readiness if r.status == READY)
    total = len(readiness)
    fraction = (ready_count / total) if total else None

    dimensions = _score_dimensions(
        pack, metrics, l1, l1_scores, readiness, rhythm, debt
    )

    overall = _overall_band(ready_count, total, dimensions)

    return VerticalScore(
        decisions_ready=ready_count,
        decisions_total=total,
        fraction=fraction,
        overall_band=overall,
        decision_readiness=readiness,
        dimensions=dimensions,
        debt=debt,
        l1_pack_score=l1.pack_score,
    )


def _score_dimensions(
    pack: Mapping[str, Any],
    metrics: Sequence[Mapping[str, Any]],
    l1: Any,
    l1_scores: Mapping[str, float],
    readiness: List[DecisionReadiness],
    rhythm: Dimension,
    debt: List[DebtItem],
) -> List[Dimension]:
    decisions = [d for d in (pack.get("decisions") or []) if isinstance(d, dict)]
    metric_ids = {m.get("id") for m in metrics}
    linkage = graph_linkage(pack)
    dims: List[Dimension] = []

    # 1. Decision coverage & linkage
    if not decisions:
        dims.append(
            Dimension(
                "Decision coverage & linkage", NOT_ASSESSED, "No decisions defined."
            )
        )
    else:
        any_missing = any(
            mid not in metric_ids
            for d in decisions
            for mid in (d.get("required_metrics") or []) + (d.get("guardrails") or [])
        )
        ready = sum(1 for r in readiness if r.status == READY)
        r = ready / len(decisions)
        if any_missing:
            band, driver = WEAK, "A decision references an undefined metric."
        elif r >= 0.8:
            band, driver = (
                STRONG,
                f"{ready}/{len(decisions)} decisions are decision-ready.",
            )
        elif r >= 0.5:
            band, driver = (
                PARTIAL,
                f"{ready}/{len(decisions)} decisions are decision-ready.",
            )
        else:
            band, driver = (
                WEAK,
                f"Only {ready}/{len(decisions)} decisions are decision-ready.",
            )
        dims.append(Dimension("Decision coverage & linkage", band, driver))

    # 2. Metric definition quality (rollup of Layer 1)
    ps = l1.pack_score
    if ps >= 80:
        band, driver = STRONG, f"Layer-1 pack score {ps:.0f}."
    elif ps >= 60:
        band, driver = PARTIAL, f"Layer-1 pack score {ps:.0f}."
    else:
        band, driver = WEAK, f"Layer-1 pack score {ps:.0f}."
    dims.append(Dimension("Metric definition quality", band, driver))

    # 3. Portfolio role clarity
    if metrics and not any(m.get("role") for m in metrics):
        dims.append(
            Dimension(
                "Portfolio role clarity", NOT_ASSESSED, "No roles set on any metric."
            )
        )
    elif not metrics:
        dims.append(Dimension("Portfolio role clarity", NOT_ASSESSED, "No metrics."))
    else:
        with_role = [m for m in metrics if m.get("role")]
        orphans = [
            m.get("id", "")
            for m in metrics
            if not linkage.get(m.get("id", ""), {}).get("decision")
            and not linkage.get(m.get("id", ""), {}).get("okr")
        ]
        has_primary = any((m.get("role") or "") == "primary_metric" for m in metrics)
        role_frac = len(with_role) / len(metrics)
        orphan_frac = len(orphans) / len(metrics)
        if role_frac == 1.0 and not orphans and has_primary:
            band, driver = (
                STRONG,
                "Every metric has a role; none are orphaned; a primary is identifiable.",
            )
        elif role_frac >= 0.8 and orphan_frac <= 0.2:
            band, driver = PARTIAL, "Most metrics have clear roles and links."
        else:
            unrole = [m.get("id") for m in metrics if not m.get("role")]
            bits = []
            if unrole:
                bits.append(f"{len(unrole)} metric(s) have no role")
            if orphans:
                bits.append(
                    f"{len(orphans)} metric(s) are not linked to a decision or OKR"
                )
            band, driver = WEAK, "; ".join(bits) + "."
        dims.append(Dimension("Portfolio role clarity", band, driver))

    # 4. Guardrail coverage
    risk = [d for d in decisions if _is_risk(d)]
    if not risk:
        dims.append(
            Dimension("Guardrail coverage", NOT_ASSESSED, "No risk-bearing decisions.")
        )
    else:
        covered = sum(1 for d in risk if d.get("guardrails"))
        frac = covered / len(risk)
        if frac == 1.0:
            band, driver = STRONG, "All risk-bearing decisions have a guardrail."
        elif frac >= 0.5:
            band, driver = (
                PARTIAL,
                f"{covered}/{len(risk)} risk-bearing decisions have a guardrail.",
            )
        else:
            band, driver = (
                WEAK,
                f"Only {covered}/{len(risk)} risk-bearing decisions have a guardrail.",
            )
        dims.append(Dimension("Guardrail coverage", band, driver))

    # 5. Instrumentation readiness
    instr = [i for i in (pack.get("instrumentation") or []) if isinstance(i, dict)]
    any_depends = any(m.get("depends_on") for m in metrics)
    if not instr and not any_depends:
        dims.append(
            Dimension(
                "Instrumentation readiness",
                NOT_ASSESSED,
                "No instrumentation declared.",
            )
        )
    else:
        statuses = [(i.get("status") or "").lower() for i in instr]
        blocking_instr = any(
            d.type == "instrumentation"
            and severity_rank(d.severity) <= 1
            and any(mid in metric_ids for mid in d.affected_metrics)
            for d in debt
        )
        if "missing" in statuses or blocking_instr:
            band, driver = (
                WEAK,
                "Instrumentation is missing or blocked for a metric in use.",
            )
        elif "partial" in statuses:
            band, driver = PARTIAL, "Some instrumentation is only partially in place."
        else:
            band, driver = STRONG, "Declared instrumentation is complete."
        dims.append(Dimension("Instrumentation readiness", band, driver))

    # 6. Ownership clarity
    owned_metrics = sum(1 for m in metrics if _owned(m))
    owned_decisions = sum(1 for d in decisions if d.get("owner"))
    denom = len(metrics) + len(decisions)
    if denom == 0:
        dims.append(Dimension("Ownership clarity", NOT_ASSESSED, "Nothing to own yet."))
    else:
        frac = (owned_metrics + owned_decisions) / denom
        if frac == 1.0:
            band, driver = STRONG, "Every metric and decision has an owner."
        elif frac >= 0.8:
            band, driver = PARTIAL, "Most metrics and decisions have owners."
        else:
            band, driver = WEAK, "Several metrics or decisions have no owner."
        dims.append(Dimension("Ownership clarity", band, driver))

    # 7. Operating rhythm (computed earlier)
    dims.append(rhythm)

    # 8. Strategy / OKR linkage
    okrs = [o for o in (pack.get("okrs") or []) if isinstance(o, dict)]
    if not okrs:
        dims.append(
            Dimension("Strategy / OKR linkage", NOT_ASSESSED, "No OKRs defined.")
        )
    else:
        prim_supp = [
            m
            for m in metrics
            if (m.get("role") or "") in {"primary_metric", "supporting_metric"}
        ]
        okr_metric_ids = {
            mid
            for o in okrs
            for kr in (o.get("key_results") or [])
            if isinstance(kr, dict)
            for mid in (kr.get("linked_metrics") or [])
        }
        linked = [
            m
            for m in prim_supp
            if m.get("linked_okrs") or m.get("id") in okr_metric_ids
        ]
        krs = [
            kr
            for o in okrs
            for kr in (o.get("key_results") or [])
            if isinstance(kr, dict)
        ]
        resolved_krs = [
            kr
            for kr in krs
            if any(mid in metric_ids for mid in (kr.get("linked_metrics") or []))
        ]
        link_frac = (len(linked) / len(prim_supp)) if prim_supp else 1.0
        kr_frac = (len(resolved_krs) / len(krs)) if krs else 1.0
        if link_frac >= 0.8 and kr_frac >= 0.8:
            band, driver = STRONG, "Outcome metrics and key results are well connected."
        elif link_frac >= 0.5 or kr_frac >= 0.5:
            band, driver = PARTIAL, "Strategy linkage is partial."
        else:
            band, driver = (
                WEAK,
                "Few outcome metrics or key results connect to each other.",
            )
        dims.append(Dimension("Strategy / OKR linkage", band, driver))

    return dims


def _overall_band(
    ready: int,
    total: int,
    dimensions: List[Dimension],
) -> str:
    fb = _fraction_band(ready, total)
    if fb is None:
        return "Not assessed (no decisions defined)"
    band = fb
    for dim in dimensions:
        if dim.band == WEAK and dim.name in _DIMENSION_CAP:
            band = _worse(band, _DIMENSION_CAP[dim.name])
    return band
