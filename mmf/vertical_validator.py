"""Validation for v2 vertical measurement packs.

Reuses the v1 metric-level checks (names, ownership, SQL, tests, duplicate ids)
via ``validate_metric_pack`` and adds vertical-level structure: the vertical
block, cross-reference integrity, metric roles, OKR linkage, and a public-sample
leak signal. Issues use the same ``ValidationIssue`` shape as v1, so the app can
render them with no changes.

Validation is non-blocking, exactly as in v1: errors mean "not clean", but
scoring still runs. Broken cross-references are warnings (the gap is also
surfaced as debt and drives decision readiness), not hard errors — so a pack
that documents a real gap stays structurally valid.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, cast

from .validator import (
    ValidatedPack,
    ValidationIssue,
    ValidationResult,
    validate_metric_pack,
)

# v1-only codes that do not apply to a v2 pack (it uses depends_on, not requires,
# and the v2 schema version is handled by the router, not flagged as unknown).
_DROP_V1_CODES = {
    "metric_requires_missing",
    "missing_schema_version",
    "unknown_schema_version",
}


def _issue(
    severity: str, code: str, message: str, path: str, human: str
) -> ValidationIssue:
    return ValidationIssue(
        severity=severity, code=code, message=message, path=path, human_location=human
    )


def _error(code, message, path, human):
    return _issue("ERROR", code, message, path, human)


def _warning(code, message, path, human):
    return _issue("WARNING", code, message, path, human)


def _info(code, message, path, human):
    return _issue("INFO", code, message, path, human)


def _ids(items: Iterable[Any]) -> set:
    out = set()
    for it in items or []:
        if isinstance(it, dict) and it.get("id"):
            out.add(it.get("id"))
    return out


def _check_duplicates(items, collection, issues):
    seen = set()
    for idx, it in enumerate(items or []):
        if not isinstance(it, dict):
            continue
        cid = it.get("id")
        if not cid:
            continue
        if cid in seen:
            issues.append(
                _error(
                    f"duplicate_{collection}_id",
                    f"Duplicate {collection} id '{cid}'. Ids must be unique.",
                    f"/{collection}/{idx}/id",
                    f"{cid}.id",
                )
            )
        seen.add(cid)


def validate_vertical_pack(pack: Dict[str, Any]) -> ValidationResult:
    """Validate a v2 vertical pack and return issues without mutating input."""
    base = validate_metric_pack(pack)
    issues: List[ValidationIssue] = [
        i for i in base.issues if i.code not in _DROP_V1_CODES
    ]

    if not isinstance(pack, dict):
        return base  # already an ERROR result from the base validator

    metrics = pack.get("metrics")
    metrics_list = metrics if isinstance(metrics, list) else []
    metric_ids = _ids(metrics_list)
    decisions = [d for d in (pack.get("decisions") or []) if isinstance(d, dict)]
    decision_ids = _ids(decisions)
    okrs = [o for o in (pack.get("okrs") or []) if isinstance(o, dict)]
    okr_ids = _ids(okrs)
    instrumentation = [
        i for i in (pack.get("instrumentation") or []) if isinstance(i, dict)
    ]
    instrumentation_ids = _ids(instrumentation)
    _strategy = pack.get("strategy")
    strategy: Dict[str, Any] = _strategy if isinstance(_strategy, dict) else {}
    company_goal_ids = _ids(strategy.get("company_goals") or [])

    # ---- Vertical block ----
    vertical = pack.get("vertical")
    if not isinstance(vertical, dict):
        issues.append(
            _warning(
                "missing_vertical",
                "No 'vertical' block. A v2 pack normally describes one product area.",
                "/vertical",
                "vertical",
            )
        )
    else:
        if not vertical.get("id"):
            issues.append(
                _error(
                    "missing_vertical_id",
                    "Vertical is missing 'id'.",
                    "/vertical/id",
                    "vertical.id",
                )
            )
        if not vertical.get("name"):
            issues.append(
                _error(
                    "missing_vertical_name",
                    "Vertical is missing 'name'.",
                    "/vertical/name",
                    "vertical.name",
                )
            )
        if not vertical.get("owner"):
            issues.append(
                _warning(
                    "missing_vertical_owner",
                    "Vertical has no 'owner'.",
                    "/vertical/owner",
                    "vertical.owner",
                )
            )

    # ---- Duplicate ids across v2 collections ----
    _check_duplicates(decisions, "decision", issues)
    _check_duplicates(okrs, "okr", issues)
    _check_duplicates(instrumentation, "instrumentation", issues)

    # ---- Metric-level v2 checks (role + cross-refs) ----
    for idx, m in enumerate(metrics_list):
        if not isinstance(m, dict):
            continue
        mid = m.get("id", f"metrics[{idx}]")
        if not m.get("role"):
            issues.append(
                _warning(
                    "metric_missing_role",
                    "No role set. Classify as primary, supporting, diagnostic, guardrail, input, or output.",
                    f"/metrics/{idx}/role",
                    f"{mid}.role",
                )
            )
        _check_refs(
            m.get("linked_okrs"),
            okr_ids,
            "broken_okr_reference",
            f"{mid}.linked_okrs",
            issues,
        )
        _check_refs(
            m.get("linked_decisions"),
            decision_ids,
            "broken_decision_reference",
            f"{mid}.linked_decisions",
            issues,
        )
        if instrumentation:  # only enforce depends_on when instrumentation is declared
            _check_refs(
                m.get("depends_on"),
                instrumentation_ids,
                "broken_instrumentation_reference",
                f"{mid}.depends_on",
                issues,
            )

    # ---- Decision cross-refs ----
    for d in decisions:
        did = d.get("id", "decision")
        _check_refs(
            d.get("required_metrics"),
            metric_ids,
            "broken_required_metric_reference",
            f"{did}.required_metrics",
            issues,
        )
        _check_refs(
            d.get("guardrails"),
            metric_ids,
            "broken_guardrail_reference",
            f"{did}.guardrails",
            issues,
        )

    # ---- OKR cross-refs + unlinked-OKR info ----
    for o in okrs:
        oid = o.get("id", "okr")
        krs = [kr for kr in (o.get("key_results") or []) if isinstance(kr, dict)]
        resolvable = False
        for kr in krs:
            linked = kr.get("linked_metrics") or []
            _check_refs(
                linked,
                metric_ids,
                "broken_kr_metric_reference",
                f"{kr.get('id', oid)}.linked_metrics",
                issues,
            )
            if any(mid in metric_ids for mid in linked):
                resolvable = True
        if krs and not resolvable:
            issues.append(
                _info(
                    "unlinked_okr",
                    f"OKR '{oid}' has no key result that resolves to a defined metric.",
                    f"/okrs/{oid}",
                    f"{oid}",
                )
            )

    # ---- Strategy outcome -> company goal refs ----
    for vo in strategy.get("vertical_outcomes") or []:
        if isinstance(vo, dict):
            _check_refs(
                vo.get("linked_company_goals"),
                company_goal_ids,
                "broken_company_goal_reference",
                f"{vo.get('id', 'outcome')}.linked_company_goals",
                issues,
            )

    # ---- Measurement-debt refs ----
    for item in pack.get("measurement_debt") or []:
        if isinstance(item, dict):
            iid = item.get("id", "debt")
            _check_refs(
                item.get("affected_metrics"),
                metric_ids,
                "broken_debt_metric_reference",
                f"{iid}.affected_metrics",
                issues,
            )
            _check_refs(
                item.get("affected_decisions"),
                decision_ids,
                "broken_debt_decision_reference",
                f"{iid}.affected_decisions",
                issues,
            )

    # ---- Public-sample leak signal (complements the CI guard) ----
    _pack_meta = pack.get("pack")
    pack_meta: Dict[str, Any] = _pack_meta if isinstance(_pack_meta, dict) else {}
    visibility = pack_meta.get("visibility")
    if visibility and visibility not in {"public_sample", "private"}:
        issues.append(
            _warning(
                "invalid_visibility",
                f"Unknown visibility '{visibility}'. Use public_sample or private.",
                "/pack/visibility",
                "pack.visibility",
            )
        )
    refs = pack.get("internal_references")
    if (
        visibility == "public_sample"
        and isinstance(refs, dict)
        and any(v is not None for v in refs.values())
    ):
        issues.append(
            _warning(
                "internal_reference_in_public_sample",
                "A public_sample pack has non-null internal_references. Clear them before committing.",
                "/internal_references",
                "internal_references",
            )
        )

    ok = not any(i.severity == "ERROR" for i in issues)
    return ValidationResult(ok=ok, pack=cast(ValidatedPack, base.pack), issues=issues)


def _check_refs(refs, valid_ids, code, human, issues):
    """Flag any id in ``refs`` that is not present in ``valid_ids`` (warning)."""
    for r in refs or []:
        if r not in valid_ids:
            issues.append(
                _warning(
                    code,
                    f"Reference '{r}' does not resolve to a defined id.",
                    f"/{human}",
                    human,
                )
            )
