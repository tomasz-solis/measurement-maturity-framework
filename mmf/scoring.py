"""Scoring logic for metric packs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

from .config import ScoringConfig, load_config

logger = logging.getLogger(__name__)


@dataclass
class MetricScore:
    """Score details for a single metric."""

    metric_id: str
    name: str
    tier: Optional[str]
    status: str
    score: float
    why: str
    gaps: List[str]


@dataclass
class ScoreResult:
    """Aggregate scoring output for a metric pack."""

    pack_score: float
    avg_metric_score: float
    min_metric_score: float
    metric_scores: List[MetricScore]


def score_pack(
    pack: Mapping[str, Any],
    config: Optional[ScoringConfig] = None,
) -> ScoreResult:
    """Score a metric pack and return both pack-level and metric-level results.

    Parameters
    ----------
    pack
        The metric pack to score.
    config
        Optional scoring configuration. Defaults to ``load_config()``.
        Pass an explicit config when running robustness analyses or
        calibration studies that need to vary deductions independently.
    """
    metrics = pack.get("metrics", [])
    logger.debug(
        "Scoring pack with %d metric(s)",
        len(metrics) if isinstance(metrics, list) else 0,
    )

    if config is None:
        config = load_config()
    metric_scores: List[MetricScore] = []

    for metric in metrics:
        if isinstance(metric, dict):
            metric_scores.append(_score_metric(metric, config))

    avg_score = (
        (sum(m.score for m in metric_scores) / len(metric_scores))
        if metric_scores
        else 0.0
    )
    min_score = min((m.score for m in metric_scores), default=0.0)
    pack_score = (
        1 - config.pack_floor_weight
    ) * avg_score + config.pack_floor_weight * min_score

    return ScoreResult(
        pack_score=round(pack_score, 2),
        avg_metric_score=round(avg_score, 2),
        min_metric_score=round(min_score, 2),
        metric_scores=metric_scores,
    )


def _score_metric(metric: Dict[str, Any], config: ScoringConfig) -> MetricScore:
    """Score a single metric definition."""

    base = config.base_score
    gaps: List[str] = []

    tier = metric.get("tier")
    status = metric.get("status") or "active"

    deductions = config.deductions

    # Tier stability — V0 proxies carry instability risk on top of any other gaps
    if (tier or "").upper() == "V0":
        base -= deductions["v0_tier"]
        gaps.append("tier_v0")

    # Ownership — no accountable team means slower debugging and weaker follow-up
    has_owner = metric.get("accountable") or metric.get("responsible")
    if not has_owner:
        base -= deductions["missing_accountable"]
        gaps.append("missing_accountable")

    # SQL — without query logic the metric can't be reproduced or inspected.
    # When the metric declares implementation_type, we refine the deduction:
    # spreadsheet/notebook/dashboard/other signal structural unreviewability
    # (larger deduction); v0_proxy signals the SQL is just not written yet
    # (smaller deduction). Without implementation_type, the default
    # missing_sql applies — this keeps older packs backward-compatible.
    sql = metric.get("sql") or {}
    has_value_sql = bool(sql.get("value"))
    has_ratio_sql = bool(sql.get("numerator")) and bool(sql.get("denominator"))
    if not (has_value_sql or has_ratio_sql):
        impl_type = (metric.get("implementation_type") or "").strip().lower()
        if impl_type in {"spreadsheet", "notebook", "dashboard", "other"}:
            base -= deductions.get(
                "missing_sql_structural",
                deductions["missing_sql"],
            )
            gaps.append("missing_sql_structural")
        elif impl_type == "v0_proxy":
            base -= deductions.get(
                "missing_sql_temporary",
                deductions["missing_sql"],
            )
            gaps.append("missing_sql_temporary")
        else:
            base -= deductions["missing_sql"]
            gaps.append("missing_sql")

    # Tests — without basic checks, silent breakage goes undetected
    if not metric.get("tests"):
        base -= deductions["missing_tests"]
        gaps.append("missing_tests")

    # Description — intent should be readable without opening the SQL
    if not metric.get("description"):
        base -= deductions.get("missing_description", 0)
        gaps.append("missing_description")

    # Grain — what one row of the output represents
    if not metric.get("grain"):
        base -= deductions.get("missing_grain", 0)
        gaps.append("missing_grain")

    # Unit — how to interpret the value (count, percent, currency, etc.)
    if not metric.get("unit"):
        base -= deductions.get("missing_unit", 0)
        gaps.append("missing_unit")

    score = max(0, min(100, base))
    why = _build_why(score=score, gaps=gaps)

    return MetricScore(
        metric_id=metric.get("id", "unknown"),
        name=metric.get("name", "Unnamed metric"),
        tier=tier,
        status=status,
        score=float(score),
        why=why,
        gaps=gaps,
    )


def _build_why(score: float, gaps: List[str]) -> str:
    """Build a short human-readable explanation for a metric score."""

    if score >= 95 and not gaps:
        return "Well-defined and production-ready."

    # Safety gaps first (higher deduction), then completeness gaps
    critical_parts: List[str] = []
    if "tier_v0" in gaps:
        critical_parts.append("it's a V0 proxy")
    if "missing_accountable" in gaps:
        critical_parts.append("no accountable team is listed")
    if "missing_sql_structural" in gaps:
        critical_parts.append(
            "the implementation is outside a query engine "
            "(spreadsheet, notebook, or dashboard)"
        )
    elif "missing_sql_temporary" in gaps:
        critical_parts.append("SQL is deferred while the proxy settles")
    elif "missing_sql" in gaps:
        critical_parts.append("no SQL is included yet")
    if "missing_tests" in gaps:
        critical_parts.append("no tests are defined")

    completeness_parts: List[str] = []
    if "missing_description" in gaps:
        completeness_parts.append("no description is set")
    if "missing_grain" in gaps:
        completeness_parts.append("grain is unspecified")
    if "missing_unit" in gaps:
        completeness_parts.append("unit is missing")

    all_parts = critical_parts + completeness_parts

    if not all_parts:
        return "Minor maturity gaps."

    # Short, readable, not judgemental
    return "Good start, but " + ", ".join(all_parts) + "."
