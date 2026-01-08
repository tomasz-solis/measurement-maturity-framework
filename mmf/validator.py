# mmf/validator.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# -------------------------
# Public data structures
# -------------------------

@dataclass
class ValidationIssue:
    severity: str          # ❌ ERROR | ⚠️ WARNING | ℹ️ INFO
    code: str
    message: str
    path: str              # raw JSON pointer
    human_location: str    # metric_id.field (or pack.field)


@dataclass
class ValidationResult:
    ok: bool
    pack: Dict[str, Any]
    issues: List[ValidationIssue] = field(default_factory=list)


# -------------------------
# Validator entry point
# -------------------------

def validate_metric_pack(pack: Dict[str, Any]) -> ValidationResult:
    issues: List[ValidationIssue] = []

    # ---- Pack-level checks ----
    if not isinstance(pack, dict):
        return ValidationResult(
            ok=False,
            pack=pack,
            issues=[
                ValidationIssue(
                    severity="❌ ERROR",
                    code="pack_not_mapping",
                    message="Top-level YAML must be a mapping (object).",
                    path="/",
                    human_location="pack",
                )
            ],
        )

    metrics = pack.get("metrics")
    if not isinstance(metrics, list):
        issues.append(
            _error(
                "missing_metrics",
                "Pack must define a list of metrics.",
                "/metrics",
                "pack.metrics",
            )
        )
        return ValidationResult(ok=False, pack=pack, issues=issues)

    # Check duplicate metric IDs
    seen_ids = set()
    for idx, m in enumerate(metrics):
        mid = m.get("id")
        if not mid:
            issues.append(
                _error(
                    "missing_metric_id",
                    "Metric is missing required field 'id'.",
                    f"/metrics/{idx}/id",
                    f"metrics[{idx}].id",
                )
            )
            continue
        if mid in seen_ids:
            issues.append(
                _error(
                    "duplicate_metric_id",
                    f"Duplicate metric id '{mid}'. Metric IDs must be unique.",
                    f"/metrics/{idx}/id",
                    f"{mid}.id",
                )
            )
        seen_ids.add(mid)

    # ---- Metric-level checks ----
    for idx, metric in enumerate(metrics):
        if not isinstance(metric, dict):
            continue

        mid = metric.get("id", f"metrics[{idx}]")

        # Required core fields
        if not metric.get("name"):
            issues.append(
                _error(
                    "missing_metric_name",
                    "Metric is missing required field 'name'.",
                    f"/metrics/{idx}/name",
                    f"{mid}.name",
                )
            )

        # Accountable (not blocking at V0)
        if not metric.get("accountable"):
            issues.append(
                _warning(
                    "missing_metric_accountable",
                    "No accountable team or role defined. "
                    "Add 'accountable' to clarify ownership and escalation.",
                    f"/metrics/{idx}/accountable",
                    f"{mid}.accountable",
                )
            )

        # Add warning when ai flag exists
        if isinstance(metric, dict) and "ai" in metric:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    code="ai_flag_present",
                    message=(
                        "AI draft flag is set. Review the AI-generated content and "
                        "remove the 'ai' field before treating this metric as ready."
                    ),
                    path=f"/metrics/{idx}/ai",
                    human_location=f"{mid}.ai",
                )
            )

        # SQL (optional at V0)
        sql = metric.get("sql") or {}
        has_value_sql = bool(sql.get("value"))
        has_ratio_sql = bool(sql.get("numerator")) and bool(sql.get("denominator"))

        if not (has_value_sql or has_ratio_sql):
            issues.append(
                _warning(
                    "metric_sql_missing",
                    "No SQL defined. This is fine for early proxies; "
                    "add SQL once the definition stabilizes.",
                    f"/metrics/{idx}",
                    f"{mid}.sql",
                )
            )

        # Tests (optional early)
        if not metric.get("tests"):
            issues.append(
                _warning(
                    "metric_tests_missing",
                    "No tests defined. Optional early on; "
                    "add basic checks once teams start relying on the metric.",
                    f"/metrics/{idx}/tests",
                    f"{mid}.tests",
                )
            )

        # Requires (purely informational)
        if not metric.get("requires"):
            issues.append(
                _info(
                    "metric_requires_missing",
                    "No upstream dependencies listed. Optional, but helps debugging later.",
                    f"/metrics/{idx}/requires",
                    f"{mid}.requires",
                )
            )

    has_errors = any(i.severity == "❌ ERROR" for i in issues)

    return ValidationResult(
        ok=not has_errors,
        pack=pack,
        issues=issues,
    )


# -------------------------
# Helpers
# -------------------------

def _error(code: str, message: str, path: str, human: str) -> ValidationIssue:
    return ValidationIssue(
        severity="❌ ERROR",
        code=code,
        message=message,
        path=path,
        human_location=human,
    )


def _warning(code: str, message: str, path: str, human: str) -> ValidationIssue:
    return ValidationIssue(
        severity="⚠️ WARNING",
        code=code,
        message=message,
        path=path,
        human_location=human,
    )


def _info(code: str, message: str, path: str, human: str) -> ValidationIssue:
    return ValidationIssue(
        severity="ℹ️ INFO",
        code=code,
        message=message,
        path=path,
        human_location=human,
    )
