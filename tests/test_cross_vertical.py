"""Tests for the cross-vertical comparison view."""

from __future__ import annotations

import os

import yaml

from mmf.cross_vertical import compare_verticals

EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples")

V2_PACKS = [
    "onboarding_measurement_ready.yaml",
    "collaboration_portfolio_design.yaml",
    "search_decision_gap.yaml",
    "reporting_operating_gap.yaml",
]


def _named_packs():
    out = []
    for name in V2_PACKS:
        with open(os.path.join(EXAMPLES, name), encoding="utf-8") as fh:
            out.append((name, yaml.safe_load(fh)))
    return out


def test_summaries_cover_all_packs_with_bands():
    view = compare_verticals(_named_packs())
    assert len(view.summaries) == 4
    # Every vertical reports a band (a pattern signal), not a numeric score.
    assert all(s.overall_band for s in view.summaries)
    assert {s.name for s in view.summaries} == {
        "Onboarding",
        "Team Collaboration",
        "Search & Discovery",
        "Reporting & Insights",
    }


def test_eight_dimensions_present():
    view = compare_verticals(_named_packs())
    assert len(view.dimension_names) == 8
    assert "Operating rhythm" in view.dimension_names


def test_operating_rhythm_is_the_top_shared_gap():
    view = compare_verticals(_named_packs())
    top = view.shared_gaps[0]
    assert top.dimension == "Operating rhythm"
    assert top.weak == 2
    assert set(top.verticals_weak) == {"Search & Discovery", "Reporting & Insights"}


def test_no_single_number_leaderboard():
    # The view exposes bands and counts, never a 0-100 per-vertical score.
    view = compare_verticals(_named_packs())
    for summary in view.summaries:
        assert not hasattr(summary, "score")
        assert isinstance(summary.overall_band, str)


def test_is_deterministic():
    packs = _named_packs()
    a = compare_verticals(packs)
    b = compare_verticals(packs)
    assert [g.dimension for g in a.shared_gaps] == [g.dimension for g in b.shared_gaps]
    assert a.shared_debt_types == b.shared_debt_types
