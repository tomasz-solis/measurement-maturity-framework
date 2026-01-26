# mmf/scoring.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .config import load_config


@dataclass
class MetricScore:
    metric_id: str
    name: str
    tier: Optional[str]
    status: str
    score: float
    why: str
    gaps: List[str]


@dataclass
class ScoreResult:
    pack_score: float
    avg_metric_score: float
    metric_scores: List[MetricScore]


def score_pack(pack: Dict[str, Any], issues: Optional[List[Any]] = None) -> ScoreResult:
    metrics = pack.get("metrics", [])
    metric_scores: List[MetricScore] = []

    for metric in metrics:
        if isinstance(metric, dict):
            metric_scores.append(_score_metric(metric))

    avg_score = (
        (sum(m.score for m in metric_scores) / len(metric_scores))
        if metric_scores
        else 0.0
    )

    return ScoreResult(
        pack_score=round(avg_score, 2),
        avg_metric_score=round(avg_score, 2),
        metric_scores=metric_scores,
    )


def _score_metric(metric: Dict[str, Any]) -> MetricScore:
    config = load_config()
    base = config.base_score
    gaps: List[str] = []

    tier = metric.get("tier")
    status = metric.get("status", "active")

    # Tier expectations
    deductions = config.deductions  # type: ignore[union-attr]
    if (tier or "").upper() == "V0":
        base -= deductions["v0_tier"]  # type: ignore[index]
        gaps.append("tier_v0")

    # Accountable
    if not metric.get("accountable"):
        base -= deductions["missing_accountable"]  # type: ignore[index]
        gaps.append("missing_accountable")

    # SQL
    sql = metric.get("sql") or {}
    has_value_sql = bool(sql.get("value"))
    has_ratio_sql = bool(sql.get("numerator")) and bool(sql.get("denominator"))
    if not (has_value_sql or has_ratio_sql):
        base -= deductions["missing_sql"]  # type: ignore[index]
        gaps.append("missing_sql")

    # Tests
    if not metric.get("tests"):
        base -= deductions["missing_tests"]  # type: ignore[index]
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
