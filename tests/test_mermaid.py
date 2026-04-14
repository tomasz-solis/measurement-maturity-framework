"""Tests for mmf.mermaid module — strategy tree diagram generation."""

from mmf.mermaid import (
    build_strategy_mermaid,
    _esc,
    _strip_numeric_prefix,
    _metric_name,
    _goal_labels_from_impact_graph,
    _goal_to_goal_edges,
)


class TestBuildStrategyMermaid:
    """Tests for the main diagram builder."""

    def test_empty_pack_produces_valid_mermaid(self):
        """Pack with no strategy data should still produce valid mermaid syntax."""
        pack = {"metrics": []}
        result = build_strategy_mermaid(pack)

        assert result.startswith("flowchart TB")
        assert "subgraph Context" in result

    def test_minimal_strategy_board(self):
        """Pack with basic strategy_board should render goals and success node."""
        pack = {
            "metrics": [],
            "strategy_board": {
                "title": "TEAM SUCCESS",
                "success_node_id": "success",
                "company_goals_box": {
                    "title": "Company Goals",
                    "goals": [{"id": "revenue"}, {"id": "retention"}],
                },
                "levers": [],
            },
        }
        result = build_strategy_mermaid(pack)

        assert "TEAM SUCCESS" in result
        assert "revenue" in result
        assert "retention" in result

    def test_levers_and_pillars_render(self):
        """Levers with pillars should produce subgraphs and nodes."""
        pack = {
            "metrics": [
                {"id": "m1", "name": "Metric One"},
            ],
            "strategy_board": {
                "title": "SUCCESS",
                "success_node_id": "success",
                "company_goals_box": {"goals": []},
                "levers": [
                    {
                        "id": "growth_lever",
                        "title": "Growth",
                        "style": "growth",
                        "pillars": [
                            {
                                "id": "p1",
                                "label": "Adoption",
                                "kpi_metric_id": "m1",
                                "accountable": "Growth Team",
                            }
                        ],
                    },
                    {
                        "id": "trust_lever",
                        "title": "Trust",
                        "style": "trust",
                        "pillars": [
                            {
                                "id": "p2",
                                "label": "Reliability",
                            }
                        ],
                    },
                ],
            },
        }
        result = build_strategy_mermaid(pack)

        assert 'subgraph Growth["Growth"]' in result
        assert 'subgraph Trust["Trust"]' in result
        assert "Metric One" in result  # KPI metric name resolved
        assert "Growth Team" in result
        assert "p1 --> success" in result
        assert "p2 --> success" in result
        # Growth styling applied
        assert "class p1 kpi_growth" in result
        assert "class p2 kpi_trust" in result

    def test_impact_graph_edges(self):
        """Impact graph edges should connect success to goals."""
        pack = {
            "metrics": [],
            "strategy_board": {
                "title": "SUCCESS",
                "success_node_id": "success",
                "company_goals_box": {
                    "goals": [{"id": "arr"}],
                },
                "levers": [],
            },
            "impact_graph": {
                "nodes": [{"id": "arr", "type": "goal", "label": "Total ARR"}],
                "edges": [{"from": "success", "to": "arr"}],
            },
        }
        result = build_strategy_mermaid(pack)

        assert "success == Impacts ==> arr" in result
        assert "Total ARR" in result

    def test_goal_to_goal_edges_render(self):
        """Goal-to-goal edges from impact_graph should use dotted arrows."""
        pack = {
            "metrics": [],
            "strategy_board": {
                "title": "S",
                "success_node_id": "s",
                "company_goals_box": {
                    "goals": [{"id": "a"}, {"id": "b"}],
                },
                "levers": [],
            },
            "impact_graph": {
                "nodes": [
                    {"id": "a", "type": "goal", "label": "A"},
                    {"id": "b", "type": "goal", "label": "B"},
                ],
                "edges": [{"from": "a", "to": "b"}],
            },
        }
        result = build_strategy_mermaid(pack)

        assert "a -.-> b" in result

    def test_supporting_metrics_shown(self):
        """Pillars with supporting_metric_ids should list those metric names."""
        pack = {
            "metrics": [
                {"id": "main", "name": "Main KPI"},
                {"id": "support1", "name": "Support Metric"},
            ],
            "strategy_board": {
                "title": "S",
                "success_node_id": "s",
                "company_goals_box": {"goals": []},
                "levers": [
                    {
                        "style": "growth",
                        "pillars": [
                            {
                                "id": "p1",
                                "label": "Pillar",
                                "kpi_metric_id": "main",
                                "supporting_metric_ids": ["support1"],
                            }
                        ],
                    }
                ],
            },
        }
        result = build_strategy_mermaid(pack)

        assert "Support Metric" in result

    def test_multiple_growth_levers_get_unique_subgraph_ids(self):
        """Growth levers should render as distinct Mermaid subgraphs."""
        pack = {
            "metrics": [],
            "strategy_board": {
                "title": "S",
                "success_node_id": "s",
                "company_goals_box": {"goals": []},
                "levers": [
                    {
                        "style": "growth",
                        "title": "Acquisition",
                        "pillars": [{"id": "p1", "label": "Acquire"}],
                    },
                    {
                        "style": "growth",
                        "title": "Activation",
                        "pillars": [{"id": "p2", "label": "Activate"}],
                    },
                ],
            },
        }
        result = build_strategy_mermaid(pack)

        assert 'subgraph Growth["Acquisition"]' in result
        assert 'subgraph Growth2["Activation"]' in result
        assert "style Growth2" in result

    def test_pillar_numbering_is_deterministic(self):
        """Pillars should be numbered in order across levers."""
        pack = {
            "metrics": [],
            "strategy_board": {
                "title": "S",
                "success_node_id": "s",
                "company_goals_box": {"goals": []},
                "levers": [
                    {
                        "style": "growth",
                        "pillars": [
                            {"id": "p1", "label": "First"},
                            {"id": "p2", "label": "Second"},
                        ],
                    },
                    {
                        "style": "trust",
                        "pillars": [
                            {"id": "p3", "label": "Third"},
                        ],
                    },
                ],
            },
        }
        result = build_strategy_mermaid(pack)

        assert "1. First" in result
        assert "2. Second" in result
        assert "3. Third" in result


class TestHelpers:
    """Tests for mermaid helper functions."""

    def test_esc_quotes(self):
        """Quotes should be escaped to HTML entities."""
        assert _esc('He said "hello"') == "He said &quot;hello&quot;"

    def test_esc_angle_brackets(self):
        """Angle brackets should be stripped (not allowed in mermaid v10+)."""
        assert _esc("<b>bold</b>") == "bbold/b"

    def test_esc_passthrough(self):
        """Normal text should pass through unchanged."""
        assert _esc("simple text") == "simple text"

    def test_strip_numeric_prefix(self):
        """Numeric prefixes like '1. ' should be stripped."""
        assert _strip_numeric_prefix("1. Adoption") == "Adoption"
        assert _strip_numeric_prefix("  2. Growth") == "Growth"
        assert _strip_numeric_prefix("No prefix") == "No prefix"
        assert _strip_numeric_prefix("") == ""

    def test_metric_name_found(self):
        """Should return metric name when ID exists."""
        metrics = {"m1": {"name": "My Metric"}}
        assert _metric_name(metrics, "m1") == "My Metric"

    def test_metric_name_fallback(self):
        """Should fall back to metric_id when not found."""
        metrics = {}
        assert _metric_name(metrics, "unknown_id") == "unknown_id"

    def test_metric_name_empty(self):
        """Empty metric_id should return empty string."""
        assert _metric_name({}, "") == ""

    def test_goal_labels_from_impact_graph(self):
        """Should extract goal labels from impact graph nodes."""
        ig = {
            "nodes": [
                {"id": "g1", "type": "goal", "label": "Revenue"},
                {"id": "g2", "type": "goal", "label": "Retention"},
                {"id": "m1", "type": "metric", "label": "Not a goal"},
            ]
        }
        result = _goal_labels_from_impact_graph(ig)

        assert result == {"g1": "Revenue", "g2": "Retention"}

    def test_goal_labels_empty(self):
        """Empty impact graph should return empty dict."""
        assert _goal_labels_from_impact_graph({}) == {}

    def test_goal_to_goal_edges(self):
        """Should return only edges where both from and to are goals."""
        ig = {
            "edges": [
                {"from": "g1", "to": "g2"},
                {"from": "g1", "to": "m1"},  # m1 not a goal
            ]
        }
        result = _goal_to_goal_edges(ig, {"g1", "g2"})

        assert result == [("g1", "g2")]

    def test_goal_to_goal_edges_empty(self):
        """No edges should return empty list."""
        assert _goal_to_goal_edges({}, set()) == []
