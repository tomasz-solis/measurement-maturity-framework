# mmf/suggestions.py
"""Deterministic suggestions for improving metric packs."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping, Set, Tuple

from .config import ScoringConfig, load_config
from .scoring import ScoreResult, MetricScore

logger = logging.getLogger(__name__)


def deterministic_suggestions(
    pack: Mapping[str, Any], score_result: ScoreResult
) -> Dict[str, List[Dict[str, str]]]:
    """Return rules-based suggestions grouped by metric.

    Each item includes a severity, a priority, and a short action message.
    Priority uses a simple scale: 1 = do first, 2 = do next, 3 = nice to have.
    """
    logger.debug(
        "Generating suggestions for %d scored metric(s)",
        len(score_result.metric_scores),
    )
    config = load_config()
    metrics = pack.get("metrics", []) or []
    metrics_by_id: Dict[str, Dict[str, Any]] = {}
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        metric_id = metric.get("id")
        if isinstance(metric_id, str) and metric_id:
            metrics_by_id[metric_id] = metric

    score_by_id: Dict[str, MetricScore] = {
        ms.metric_id: ms for ms in score_result.metric_scores if ms.metric_id
    }

    out: Dict[str, List[Dict[str, str]]] = {}

    for mid, m in metrics_by_id.items():
        ms = score_by_id.get(mid)
        if not ms:
            continue

        items: List[Dict[str, str]] = []

        # --- What's good ---
        items.extend(_good_signals(m, ms, config))

        # --- What to do next (based on scoring gaps) ---
        tier = (m.get("tier") or "").upper()
        items.extend(_gap_actions(list(ms.gaps), tier))

        # Tier note, only when it adds value
        if tier == "V0" and ms.score >= 70:
            items.append(
                {
                    "severity": "info",
                    "priority": "3",
                    "message": (
                        "This is a solid V0. When the definition settles, do a V1 pass "
                        "and add SQL plus a small test set."
                    ),
                }
            )

        out[mid] = _dedupe(items)

    # Remove empty groups
    return {k: v for k, v in out.items() if v}


def _good_signals(
    metric: Dict[str, Any], ms: MetricScore, config: ScoringConfig
) -> List[Dict[str, str]]:
    """Return positive signals that do not contradict known maturity gaps."""
    good: List[Dict[str, str]] = []
    gaps = set(ms.gaps)
    status = (metric.get("status") or "").strip().lower()

    if metric.get("name") and metric.get("id"):
        good.append({"severity": "good", "message": "ID and name are set."})
    if metric.get("description"):
        good.append(
            {
                "severity": "good",
                "message": "Description is present.",
            }
        )
    if metric.get("unit"):
        good.append({"severity": "good", "message": "Unit is set."})
    if metric.get("grain"):
        good.append(
            {
                "severity": "good",
                "message": "Grain is set.",
            }
        )
    if status and status != "deprecated":
        good.append(
            {
                "severity": "good",
                "message": f"Status is set to '{metric.get('status')}'.",
            }
        )

    if (
        ms.score >= config.thresholds["decision_ready"]
        and "deprecated_status" not in gaps
    ):
        good.append(
            {
                "severity": "good",
                "message": "This metric is in good shape for its current tier.",
            }
        )

    return good


def _gap_actions(gaps: List[str], tier: str) -> List[Dict[str, str]]:
    """Generate prioritized suggestions based on gaps and tier.

    Priority depends on tier:
    - V0: stabilize the definition first (description, owner)
    - V1+: focus on reproducibility (SQL, tests, dependencies)
    """
    actions: List[Dict[str, str]] = []
    is_v0 = tier == "V0"

    if "missing_description" in gaps:
        actions.append(
            {
                "severity": "warning",
                "priority": "1" if is_v0 else "2",
                "message": "Add a short 'description' so someone new can tell what this metric means.",
            }
        )

    if "missing_accountable" in gaps:
        actions.append(
            {
                "severity": "warning",
                "priority": "1",
                "message": "Add 'accountable' or 'responsible' so it is clear who owns this metric.",
            }
        )

    if "missing_sql" in gaps:
        if is_v0:
            actions.append(
                {
                    "severity": "warning",
                    "priority": "2",
                    "message": (
                        "Add SQL once the proxy settles. Even a simple first query is "
                        "better than leaving the logic implicit."
                    ),
                }
            )
        else:
            actions.append(
                {
                    "severity": "warning",
                    "priority": "1",
                    "message": (
                        "Add SQL (`value` or `numerator` + `denominator`). Without it, "
                        "someone else cannot reproduce the metric."
                    ),
                }
            )

    if "missing_sql_temporary" in gaps:
        actions.append(
            {
                "severity": "warning",
                "priority": "2",
                "message": (
                    "SQL is deferred while this proxy settles. Put a date on the V1 pass "
                    "so it does not stay temporary."
                ),
            }
        )

    if "missing_sql_structural" in gaps:
        actions.append(
            {
                "severity": "critical",
                "priority": "1",
                "message": (
                    "This metric lives outside a query engine. Move it into SQL or "
                    "another reviewable pipeline before people rely on it."
                ),
            }
        )

    if "missing_tests" in gaps:
        actions.append(
            {
                "severity": "warning",
                "priority": "1" if not is_v0 else "2",
                "message": "Add 1 or 2 basic tests such as `not_null`, `freshness`, or `range`.",
            }
        )

    if "deprecated_status" in gaps:
        actions.append(
            {
                "severity": "critical",
                "priority": "1",
                "message": "This metric is deprecated. Remove it from active packs or name the replacement.",
            }
        )

    if "missing_grain" in gaps:
        actions.append(
            {
                "severity": "info",
                "priority": "2",
                "message": "Add 'grain' so readers know what one row represents.",
            }
        )

    if "missing_unit" in gaps:
        actions.append(
            {
                "severity": "info",
                "priority": "2",
                "message": "Add 'unit' so readers know how to read the value.",
            }
        )

    if "missing_dependencies" in gaps:
        actions.append(
            {
                "severity": "info",
                "priority": "3",
                "message": "Add 'requires' so the upstream tables or events are visible.",
            }
        )

    return actions


def _dedupe(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Remove duplicate suggestion items while preserving order."""
    seen: Set[Tuple[str, str]] = set()
    out: List[Dict[str, str]] = []
    for it in items:
        sev = (it.get("severity") or "").strip()
        msg = (it.get("message") or "").strip()
        key = (sev, msg)
        if not sev or not msg:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out
