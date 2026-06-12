"""Deterministic exports for v1 and v2 results.

Produces the artifacts named in PRD FR10:

- validation results -> JSON
- metric readiness -> CSV
- vertical score -> CSV
- one-page brief -> Markdown

Plus the cross-vertical comparison matrix and shared-gaps summary as CSV.

All outputs are pure strings and deterministic (fixed column order, ``\\n``
line terminator, stable JSON key order), so the same input always yields the
same bytes. ``write_text`` writes UTF-8 with ``\\n`` newlines so exports are
portable across platforms (NFR3) and never hit Windows' cp1252 limits.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from typing import Any, Dict, List, Mapping, Optional

from .brief import build_brief
from .cross_vertical import CrossVerticalView
from .scoring import ScoreResult
from .validator import ValidationResult
from .vertical_scoring import VerticalScore


def _csv(header: List[str], rows: List[List[str]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buf.getvalue()


def validation_to_json(result: ValidationResult) -> str:
    """Serialise validation issues to indented JSON."""
    payload = {
        "ok": result.ok,
        "issue_count": len(result.issues),
        "issues": [asdict(issue) for issue in result.issues],
    }
    return json.dumps(payload, indent=2, ensure_ascii=True)


def metric_readiness_to_csv(
    score: ScoreResult,
    pack: Optional[Mapping[str, Any]] = None,
) -> str:
    """Metric-level readiness table. Role/owner/links filled in when ``pack`` is given."""
    meta: Dict[str, Mapping[str, Any]] = {}
    if pack:
        for m in pack.get("metrics") or []:
            if isinstance(m, dict):
                meta[m.get("id", "")] = m

    header = [
        "id",
        "name",
        "role",
        "tier",
        "status",
        "owner",
        "linked_okrs",
        "linked_decisions",
        "score",
        "gaps",
    ]
    rows: List[List[str]] = []
    for ms in score.metric_scores:
        m = meta.get(ms.metric_id, {})
        owner = m.get("accountable") or m.get("responsible") or ""
        rows.append(
            [
                ms.metric_id,
                ms.name,
                str(m.get("role") or ""),
                ms.tier or "",
                ms.status,
                str(owner),
                ";".join(m.get("linked_okrs") or []),
                ";".join(m.get("linked_decisions") or []),
                f"{ms.score:.0f}",
                ";".join(ms.gaps),
            ]
        )
    return _csv(header, rows)


def vertical_score_to_csv(score: VerticalScore) -> str:
    """Vertical readiness as a flat table: overall row plus one row per dimension."""
    header = ["name", "band", "driver"]
    if score.decisions_total:
        decision_detail = f"{score.decisions_ready} of {score.decisions_total} decisions decision-ready"
    else:
        decision_detail = "no decisions defined"
    rows: List[List[str]] = [["(overall)", score.overall_band, decision_detail]]
    rows += [[d.name, d.band, d.driver] for d in score.dimensions]
    return _csv(header, rows)


def cross_vertical_matrix_to_csv(view: CrossVerticalView) -> str:
    """The cross-vertical band matrix: one row per vertical, one column per dimension."""
    header = ["vertical", "overall_band", "decisions_ready", "decisions_total"]
    header += list(view.dimension_names)
    rows: List[List[str]] = []
    for summary in view.summaries:
        row = [
            summary.name,
            summary.overall_band,
            str(summary.decisions_ready),
            str(summary.decisions_total),
        ]
        row += [summary.dimensions.get(dim, "") for dim in view.dimension_names]
        rows.append(row)
    return _csv(header, rows)


def cross_vertical_shared_gaps_to_csv(view: CrossVerticalView) -> str:
    """The shared-gaps summary: dimensions weak/partial across multiple verticals."""
    header = ["dimension", "weak_in", "partial_in", "verticals_weak"]
    rows = [
        [gap.dimension, str(gap.weak), str(gap.partial), ";".join(gap.verticals_weak)]
        for gap in view.shared_gaps
    ]
    return _csv(header, rows)


def brief_to_markdown(
    pack: Mapping[str, Any],
    score: Optional[VerticalScore] = None,
) -> str:
    """The one-page brief as Markdown (thin wrapper over ``build_brief``)."""
    return build_brief(pack, score)


def export_all(
    pack: Mapping[str, Any],
    validation: ValidationResult,
    score: ScoreResult,
    vertical_score: VerticalScore,
) -> Dict[str, str]:
    """Return all FR10 artifacts keyed by suggested filename."""
    return {
        "validation.json": validation_to_json(validation),
        "metric_readiness.csv": metric_readiness_to_csv(score, pack),
        "vertical_score.csv": vertical_score_to_csv(vertical_score),
        "brief.md": brief_to_markdown(pack, vertical_score),
    }


def write_text(path: str, text: str) -> None:
    """Write text as UTF-8 with ``\\n`` newlines (portable, deterministic)."""
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
