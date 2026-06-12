"""Cross-vertical comparison.

Compares several vertical packs by *pattern*, never by a single-number ranking
(PRD §13, principle G6). The output is a band matrix plus a "shared gaps"
summary: which dimensions are weak across many verticals. This is the
enablement-prioritization signal a cross-vertical measurement owner needs -- it
deliberately does not produce a "best/worst vertical" leaderboard.

Intended for private, local use over multiple packs; the public app uses it only
to compare the bundled sample packs as a demonstration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .vertical_scoring import PARTIAL, WEAK, score_vertical


@dataclass
class VerticalSummary:
    """One vertical's headline result for the comparison matrix."""

    id: str
    name: str
    overall_band: str
    decisions_ready: int
    decisions_total: int
    dimensions: Dict[str, str] = field(default_factory=dict)


@dataclass
class SharedGap:
    """A dimension that is weak/partial across one or more verticals."""

    dimension: str
    weak: int
    partial: int
    verticals_weak: List[str] = field(default_factory=list)


@dataclass
class CrossVerticalView:
    """Pattern comparison across verticals. No single-number ranking by design."""

    summaries: List[VerticalSummary]
    dimension_names: List[str]
    shared_gaps: List[SharedGap]
    shared_debt_types: List[Tuple[str, int]]


def _name_and_id(pack: Mapping[str, Any], fallback: str) -> Tuple[str, str]:
    _vertical = pack.get("vertical")
    vertical: Dict[str, Any] = _vertical if isinstance(_vertical, dict) else {}
    _meta = pack.get("pack")
    meta: Dict[str, Any] = _meta if isinstance(_meta, dict) else {}
    name = vertical.get("name") or meta.get("name") or fallback
    vid = vertical.get("id") or meta.get("id") or fallback
    return str(name), str(vid)


def compare_verticals(
    named_packs: Sequence[Tuple[str, Mapping[str, Any]]],
) -> CrossVerticalView:
    """Compare several (label, pack) pairs into a pattern view.

    Verticals keep their input order; gaps and debt types are sorted by
    prevalence with a stable tie-break, so the output is deterministic.
    """
    scored = [(label, pack, score_vertical(pack)) for label, pack in named_packs]

    summaries: List[VerticalSummary] = []
    for label, pack, result in scored:
        name, vid = _name_and_id(pack, label)
        summaries.append(
            VerticalSummary(
                id=vid,
                name=name,
                overall_band=result.overall_band,
                decisions_ready=result.decisions_ready,
                decisions_total=result.decisions_total,
                dimensions={d.name: d.band for d in result.dimensions},
            )
        )

    dimension_names = [d.name for d in scored[0][2].dimensions] if scored else []

    shared_gaps: List[SharedGap] = []
    for dim in dimension_names:
        weak_in = [s.name for s in summaries if s.dimensions.get(dim) == WEAK]
        partial = sum(1 for s in summaries if s.dimensions.get(dim) == PARTIAL)
        if weak_in or partial:
            shared_gaps.append(SharedGap(dim, len(weak_in), partial, weak_in))
    shared_gaps.sort(key=lambda g: (-g.weak, -g.partial, g.dimension))

    debt_counts: Dict[str, int] = {}
    for _label, _pack, result in scored:
        for debt_type in {item.type for item in result.debt}:
            debt_counts[debt_type] = debt_counts.get(debt_type, 0) + 1
    shared_debt_types = sorted(debt_counts.items(), key=lambda kv: (-kv[1], kv[0]))

    return CrossVerticalView(
        summaries=summaries,
        dimension_names=dimension_names,
        shared_gaps=shared_gaps,
        shared_debt_types=shared_debt_types,
    )
