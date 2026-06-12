"""Tests for the one-page measurement-readiness brief."""

from __future__ import annotations

import os

import yaml

from mmf.brief import build_brief

EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples")


def _load(name):
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_brief_has_expected_structure():
    md = build_brief(_load("onboarding_measurement_ready.yaml"))
    assert md.startswith("# Measurement Readiness Brief: Onboarding")
    for heading in (
        "## Summary",
        "## Strengths",
        "## Risks",
        "## Recommended next actions",
    ):
        assert heading in md
    assert "Decision-ready" in md
    assert "2 of 2 key decisions are decision-ready." in md


def test_brief_surfaces_the_designed_gap():
    md = build_brief(_load("search_decision_gap.yaml"))
    assert "Fragile" in md
    assert "Decision coverage & linkage" in md
    # The signature debt's recommended fix should appear as a next action.
    assert "query-understanding" in md.lower() or "query_understanding" in md.lower()


def test_brief_is_deterministic():
    pack = _load("collaboration_portfolio_design.yaml")
    assert build_brief(pack) == build_brief(pack)


def test_healthy_brief_lists_strengths_and_minimal_risk():
    md = build_brief(_load("onboarding_measurement_ready.yaml"))
    strengths_idx = md.index("## Strengths")
    risks_idx = md.index("## Risks")
    # Strengths section lists the strong dimensions.
    assert "Metric definition quality" in md[strengths_idx:risks_idx]
    # No weak dimension, so risks are minimal.
    assert "No material risks detected." in md
