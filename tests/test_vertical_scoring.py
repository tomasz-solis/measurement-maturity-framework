"""Discriminant-validity tests for Layer-2 vertical scoring.

These assert that the three public sample packs rank in their intended order and
that each pack's designed weakness shows up where it should. This is the primary
validity mechanism described in docs/V2_SCORING_METHODOLOGY.md: it tests that the
score *discriminates* between systems that should differ and *attributes* the
weakness correctly, deterministically, with no rater pool required.

If a rules change breaks an assertion here, fix either the rule or the pack on
purpose; never silently re-baseline.
"""

from __future__ import annotations

import os

import yaml

from mmf.vertical_scoring import (
    BAND_ORDER,
    NOT_ASSESSED,
    STRONG,
    WEAK,
    score_vertical,
)

EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples")


def _load(name):
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


ONBOARDING = "onboarding_measurement_ready.yaml"
COLLABORATION = "collaboration_portfolio_design.yaml"
SEARCH = "search_decision_gap.yaml"


def _score(name):
    return score_vertical(_load(name))


# --- Assertion 1: strict band ordering ----------------------------------------


def test_overall_bands_match_design():
    assert _score(ONBOARDING).overall_band == "Decision-ready"
    assert _score(COLLABORATION).overall_band == "Usable with caution"
    assert _score(SEARCH).overall_band == "Fragile"


def test_band_ordering_is_strict():
    bands = [
        _score(ONBOARDING).overall_band,
        _score(COLLABORATION).overall_band,
        _score(SEARCH).overall_band,
    ]
    ranks = [BAND_ORDER.index(b) for b in bands]
    assert ranks == sorted(ranks)
    assert len(set(ranks)) == 3  # genuinely separated, not tied


def test_decision_ready_counts():
    assert (_score(ONBOARDING).decisions_ready, _score(ONBOARDING).decisions_total) == (
        2,
        2,
    )
    assert (
        _score(COLLABORATION).decisions_ready,
        _score(COLLABORATION).decisions_total,
    ) == (2, 2)
    assert (_score(SEARCH).decisions_ready, _score(SEARCH).decisions_total) == (1, 2)


# --- Assertion 2: designed weakness is attributed correctly -------------------


def test_onboarding_has_no_weak_dimension():
    assert [d.name for d in _score(ONBOARDING).dimensions if d.band == WEAK] == []


def test_collaboration_weakness_is_role_clarity():
    s = _score(COLLABORATION)
    assert s.dimension("Portfolio role clarity").band == WEAK


def test_search_weakness_is_decision_coverage():
    s = _score(SEARCH)
    assert s.dimension("Decision coverage & linkage").band == WEAK


# --- Assertion 3: strength preserved (good metrics != ready system) -----------


def test_all_packs_have_strong_definition_quality():
    for name in (ONBOARDING, COLLABORATION, SEARCH):
        assert _score(name).dimension("Metric definition quality").band == STRONG


# --- Assertion 4: signature debt surfaces on top ------------------------------


def test_collaboration_signature_debt():
    top_ids = [d.id for d in _score(COLLABORATION).debt[:3]]
    assert "orphan_comment_volume" in top_ids
    assert "orphan_mentions_per_user" in top_ids


def test_search_signature_debt_is_top():
    debt = _score(SEARCH).debt
    assert debt, "search pack should derive debt"
    assert (
        debt[0].id
        == "missing_metric_ship_search_ranking_change_query_understanding_score"
    )
    assert debt[0].severity == "high"


# --- Spot checks on the underlying rules --------------------------------------


def test_missing_reference_makes_decision_not_ready():
    s = _score(SEARCH)
    ship = next(r for r in s.decision_readiness if r.id == "ship_search_ranking_change")
    assert ship.status == "NOT_READY"


def test_orphan_detection():
    from mmf.measurement_debt import graph_linkage

    link = graph_linkage(_load(COLLABORATION))
    assert not link["comment_volume"]["decision"] and not link["comment_volume"]["okr"]
    assert link["active_collaborators"]["decision"]


def test_absent_section_is_not_assessed_not_zero():
    # A pack with metrics only should not be punished on decision dimensions.
    minimal = {
        "pack": {
            "id": "p",
            "name": "P",
            "schema_version": "2.0",
            "visibility": "public_sample",
        },
        "metrics": [
            {
                "id": "m1",
                "name": "M1",
                "role": "primary_metric",
                "tier": "V1",
                "accountable": "Team",
                "description": "x",
                "unit": "percent",
                "grain": "account",
                "sql": {"value": "SELECT 1"},
                "tests": [{"type": "not_null"}],
            }
        ],
    }
    s = score_vertical(minimal)
    assert s.dimension("Decision coverage & linkage").band == NOT_ASSESSED
    assert s.dimension("Operating rhythm").band == NOT_ASSESSED
