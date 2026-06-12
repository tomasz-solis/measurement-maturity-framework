"""Tests for the v2 vertical strategy-tree Mermaid builder."""

from __future__ import annotations

from mmf.mermaid import build_vertical_strategy_mermaid

PACK = {
    "vertical": {"id": "v", "name": "Demo Vertical"},
    "strategy": {
        "company_goals": [{"id": "retention", "name": "Retention"}],
        "vertical_outcomes": [
            {
                "id": "faster",
                "name": "Faster value",
                "linked_company_goals": ["retention"],
            }
        ],
    },
    "okrs": [
        {
            "id": "okr1",
            "objective": "Improve activation",
            "key_results": [{"id": "kr1", "linked_metrics": ["activation_rate"]}],
        }
    ],
    "metrics": [
        {
            "id": "activation_rate",
            "name": "Activation Rate",
            "role": "primary_metric",
            "linked_okrs": ["okr1"],
        }
    ],
}


def test_builds_full_ladder():
    code = build_vertical_strategy_mermaid(PACK)
    assert code.startswith("flowchart")
    # All four layers are labelled.
    for label in (
        "Activation Rate",
        "Improve activation",
        "Faster value",
        "Retention",
        "Demo Vertical",
    ):
        assert label in code
    # The ladder edges connect metric -> okr -> vertical -> outcome -> goal.
    assert "m_activation_rate --> k_okr1" in code
    assert "k_okr1 --> v_node" in code
    assert "v_node --> o_faster" in code
    assert "o_faster == ladders ==> g_retention" in code


def test_empty_when_no_strategy_or_okrs():
    assert (
        build_vertical_strategy_mermaid({"metrics": [{"id": "m", "name": "M"}]}) == ""
    )
