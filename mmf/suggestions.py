# mmf/suggestions.py
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple


def deterministic_suggestions(pack: Dict[str, Any], score_result: Any) -> Dict[str, List[Dict[str, str]]]:
    """
    Deterministic, rules-based suggestions grouped per metric.

    Output:
      {
        "metric_id": [
           {"severity": "good|info|warning|critical", "message": "..."},
           ...
        ]
      }
    """
    metrics = pack.get("metrics", []) or []
    metrics_by_id = {m.get("id"): m for m in metrics if isinstance(m, dict) and m.get("id")}

    metric_scores = getattr(score_result, "metric_scores", []) or []
    score_by_id = {getattr(ms, "metric_id", None): ms for ms in metric_scores if getattr(ms, "metric_id", None)}

    out: Dict[str, List[Dict[str, str]]] = {}

    for mid, m in metrics_by_id.items():
        ms = score_by_id.get(mid)
        if not ms:
            continue

        items: List[Dict[str, str]] = []

        # --- What’s good ---
        items.extend(_good_signals(m, ms))

        # --- What to do next (based on scoring gaps) ---
        gaps = list(getattr(ms, "gaps", []) or [])
        items.extend(_gap_actions(m, gaps))

        # Tier note, only when it adds value (no spam)
        tier = (m.get("tier") or "").upper()
        if tier == "V0" and ms.score >= 70:
            items.append(
                {
                    "severity": "info",
                    "message": "V0 is fine for early rollout. Once the definition stabilizes, consider a V1 pass (SQL + basic tests).",
                }
            )

        out[mid] = _dedupe(items)

    # Remove empty groups
    return {k: v for k, v in out.items() if v}


def _good_signals(metric: Dict[str, Any], ms: Any) -> List[Dict[str, str]]:
    good: List[Dict[str, str]] = []

    # Lightweight, reusable signals
    if metric.get("name") and metric.get("id"):
        good.append({"severity": "good", "message": "Clear identity (id + name)."})
    if metric.get("description"):
        good.append({"severity": "good", "message": "Description is present (people can understand the intent)."})
    if metric.get("unit"):
        good.append({"severity": "good", "message": "Unit is specified."})
    if metric.get("grain"):
        good.append({"severity": "good", "message": "Grain is specified (what one row represents)."})
    if metric.get("status"):
        good.append({"severity": "good", "message": f"Status is set to '{metric.get('status')}'."})

    # If the score is high, call it out once
    if getattr(ms, "score", 0) >= 85:
        good.append({"severity": "good", "message": "Overall maturity is strong for the current tier."})

    return good


def _gap_actions(metric: Dict[str, Any], gaps: List[str]) -> List[Dict[str, str]]:
    actions: List[Dict[str, str]] = []

    tier = (metric.get("tier") or "").upper()

    if "missing_accountable" in gaps:
        actions.append(
            {
                "severity": "warning",
                "message": "Add 'accountable' (team/role). This makes ownership and escalation explicit.",
            }
        )

    if "missing_sql" in gaps:
        if tier == "V0":
            actions.append(
                {
                    "severity": "warning",
                    "message": "Add SQL when the proxy stabilizes. Start with a simple query and document assumptions in comments.",
                }
            )
        else:
            actions.append(
                {
                    "severity": "warning",
                    "message": "Add SQL (value.sql or numerator/denominator). Without it, the metric can’t be reproduced.",
                }
            )

    if "missing_tests" in gaps:
        actions.append(
            {
                "severity": "warning",
                "message": "Add 1–2 basic tests (null rate, expected range, freshness). Keep them cheap and practical.",
            }
        )

    # Validator currently treats requires as INFO; we keep it low priority here too
    if not metric.get("requires"):
        actions.append(
            {
                "severity": "info",
                "message": "Optional: add 'requires' to list upstream tables/events. Helps debugging and impact analysis later.",
            }
        )

    return actions


def _dedupe(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
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
        out.append({"severity": sev, "message": msg})
    return out
