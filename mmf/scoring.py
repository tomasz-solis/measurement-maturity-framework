"""Scoring logic for metric packs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .config import ScoringConfig, load_config


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


def score_pack(pack: Dict[str, Any]) -> ScoreResult:
    """Score a metric pack and return both pack-level and metric-level results."""

    config = load_config()
    metrics = pack.get("metrics", [])
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

    # Tier expectations
    deductions = config.deductions
    if (tier or "").upper() == "V0":
        base -= deductions["v0_tier"]
        gaps.append("tier_v0")

    # Accountable / responsible
    has_owner = metric.get("accountable") or metric.get("responsible")
    if not has_owner:
        base -= deductions["missing_accountable"]
        gaps.append("missing_accountable")

    # SQL
    sql = metric.get("sql") or {}
    has_value_sql = bool(sql.get("value"))
    has_ratio_sql = bool(sql.get("numerator")) and bool(sql.get("denominator"))
    if not (has_value_sql or has_ratio_sql):
        base -= deductions["missing_sql"]
        gaps.append("missing_sql")

    # Tests
    if not metric.get("tests"):
        base -= deductions["missing_tests"]
        gaps.append("missing_tests")

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

    parts: List[str] = []

    if "tier_v0" in gaps:
        parts.append("it’s a V0 proxy")
    if "missing_accountable" in gaps:
        parts.append("no accountable team is listed")
    if "missing_sql" in gaps:
        parts.append("no SQL is included yet")
    if "missing_tests" in gaps:
        parts.append("no tests are defined")

    if not parts:
        return "Minor maturity gaps."

    # Short, readable, not judgemental
    return "Good start, but " + ", ".join(parts) + "."
