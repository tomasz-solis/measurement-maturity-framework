# mmf/validator.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import sqlparse
    SQLPARSE_AVAILABLE = True
except ImportError:
    SQLPARSE_AVAILABLE = False


# -------------------------
# Public data structures
# -------------------------

@dataclass
class ValidationIssue:
    severity: str          # ERROR | WARNING | INFO
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
                    severity="ERROR",
                    code="pack_not_mapping",
                    message="Top-level YAML must be a mapping (object).",
                    path="/",
                    human_location="pack",
                )
            ],
        )

    # Check schema version (informational)
    pack_def = pack.get("pack", {})
    if isinstance(pack_def, dict):
        schema_version = pack_def.get("schema_version")
        if not schema_version:
            issues.append(
                _info(
                    "missing_schema_version",
                    "Consider adding 'schema_version' to pack metadata for future compatibility tracking.",
                    "/pack/schema_version",
                    "pack.schema_version",
                )
            )
        elif schema_version != "1.0":
            issues.append(
                _warning(
                    "unknown_schema_version",
                    f"Schema version '{schema_version}' is not recognized. Current supported version: 1.0",
                    "/pack/schema_version",
                    "pack.schema_version",
                )
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
        # Skip non-dict metrics
        if not isinstance(m, dict):
            issues.append(
                _error(
                    "metric_not_dict",
                    f"Metric at index {idx} is not a dictionary. Expected a metric object.",
                    f"/metrics/{idx}",
                    f"metrics[{idx}]",
                )
            )
            continue

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
        else:
            # Validate SQL syntax if sqlparse is available
            if SQLPARSE_AVAILABLE:
                sql_fields = []
                if has_value_sql:
                    sql_fields.append(("value", sql.get("value")))
                if has_ratio_sql:
                    sql_fields.append(("numerator", sql.get("numerator")))
                    sql_fields.append(("denominator", sql.get("denominator")))

                for field_name, sql_text in sql_fields:
                    if sql_text and not _validate_sql_syntax(sql_text):
                        issues.append(
                            _warning(
                                "metric_sql_syntax_error",
                                f"SQL syntax appears invalid in '{field_name}'. "
                                "This is a basic check - verify the query works in your database.",
                                f"/metrics/{idx}/sql/{field_name}",
                                f"{mid}.sql.{field_name}",
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

    has_errors = any(i.severity == "ERROR" for i in issues)

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
        severity="ERROR",
        code=code,
        message=message,
        path=path,
        human_location=human,
    )


def _warning(code: str, message: str, path: str, human: str) -> ValidationIssue:
    return ValidationIssue(
        severity="WARNING",
        code=code,
        message=message,
        path=path,
        human_location=human,
    )


def _info(code: str, message: str, path: str, human: str) -> ValidationIssue:
    return ValidationIssue(
        severity="INFO",
        code=code,
        message=message,
        path=path,
        human_location=human,
    )


def _validate_sql_syntax(sql_text: str) -> bool:
    """
    Basic SQL syntax validation using sqlparse.
    Returns True if SQL appears valid, False if syntax errors detected.

    Note: This is a basic check. It does not validate:
    - Table/column existence
    - Database-specific syntax
    - Query correctness
    """
    if not SQLPARSE_AVAILABLE or not sql_text or not sql_text.strip():
        return True  # Assume valid if we can't validate

    try:
        # Parse the SQL
        parsed = sqlparse.parse(sql_text)

        # If parsing returns nothing, it's likely invalid
        if not parsed:
            return False

        # Check for basic structure - should have at least one statement
        for statement in parsed:
            if statement.get_type() is None:
                # Unknown statement type might indicate syntax error
                return False

        return True
    except Exception:
        # If parsing raises an exception, assume syntax error
        return False
