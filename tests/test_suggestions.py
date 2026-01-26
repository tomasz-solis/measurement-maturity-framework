"""
Tests for mmf/suggestions.py - deterministic suggestion generation
"""
from dataclasses import dataclass
from typing import List, Optional

import pytest

from mmf.suggestions import deterministic_suggestions


@dataclass
class MockMetricScore:
    """Mock MetricScore for testing"""
    metric_id: str
    score: float
    gaps: List[str]
    tier: Optional[str] = None
    status: Optional[str] = None
    why: str = ""


@dataclass
class MockScoreResult:
    """Mock ScoreResult for testing"""
    pack_score: float
    metric_scores: List[MockMetricScore]
    avg_metric_score: float = 0.0


class TestDeterministicSuggestions:
    """Test suggestions are generated correctly based on scores and gaps"""

    def test_empty_pack_returns_empty_suggestions(self):
        """Empty metric pack should return no suggestions"""
        pack = {"metrics": []}
        score_result = MockScoreResult(pack_score=100, metric_scores=[])

        result = deterministic_suggestions(pack, score_result)

        assert result == {}

    def test_high_score_metric_gets_good_signals(self):
        """Metric with score >=80 should get positive feedback"""
        pack = {
            "metrics": [
                {
                    "id": "test_metric",
                    "name": "Test Metric",
                    "tier": "V1",
                    "description": "A test metric",
                }
            ]
        }
        score_result = MockScoreResult(
            pack_score=90,
            metric_scores=[
                MockMetricScore(metric_id="test_metric", score=90, gaps=[])
            ]
        )

        result = deterministic_suggestions(pack, score_result)

        assert "test_metric" in result
        suggestions = result["test_metric"]
        # Should have at least one "good" signal
        good_messages = [s for s in suggestions if s.get("severity") == "good"]
        assert len(good_messages) > 0

    def test_missing_sql_generates_gap_action(self):
        """Missing SQL should generate actionable suggestion"""
        pack = {
            "metrics": [
                {
                    "id": "no_sql_metric",
                    "name": "No SQL Metric",
                    "tier": "V0",
                }
            ]
        }
        score_result = MockScoreResult(
            pack_score=75,
            metric_scores=[
                MockMetricScore(
                    metric_id="no_sql_metric",
                    score=75,
                    gaps=["missing_sql"]
                )
            ]
        )

        result = deterministic_suggestions(pack, score_result)

        assert "no_sql_metric" in result
        suggestions = result["no_sql_metric"]

        # Should have suggestion about SQL
        sql_suggestions = [s for s in suggestions if "SQL" in s.get("message", "")]
        assert len(sql_suggestions) > 0

    def test_missing_tests_generates_gap_action(self):
        """Missing tests should generate actionable suggestion"""
        pack = {
            "metrics": [
                {
                    "id": "no_tests_metric",
                    "name": "No Tests Metric",
                    "tier": "V0",
                }
            ]
        }
        score_result = MockScoreResult(
            pack_score=75,
            metric_scores=[
                MockMetricScore(
                    metric_id="no_tests_metric",
                    score=75,
                    gaps=["missing_tests"]
                )
            ]
        )

        result = deterministic_suggestions(pack, score_result)

        assert "no_tests_metric" in result
        suggestions = result["no_tests_metric"]

        # Should have suggestion about tests
        test_suggestions = [s for s in suggestions if "test" in s.get("message", "").lower()]
        assert len(test_suggestions) > 0

    def test_missing_accountable_generates_gap_action(self):
        """Missing accountable should generate actionable suggestion"""
        pack = {
            "metrics": [
                {
                    "id": "no_owner_metric",
                    "name": "No Owner Metric",
                }
            ]
        }
        score_result = MockScoreResult(
            pack_score=70,
            metric_scores=[
                MockMetricScore(
                    metric_id="no_owner_metric",
                    score=70,
                    gaps=["missing_accountable"]
                )
            ]
        )

        result = deterministic_suggestions(pack, score_result)

        assert "no_owner_metric" in result
        suggestions = result["no_owner_metric"]

        # Should have suggestion about ownership
        owner_suggestions = [s for s in suggestions if any(word in s.get("message", "").lower()
                                                          for word in ["accountable", "owner", "responsible"])]
        assert len(owner_suggestions) > 0

    def test_v0_tier_with_good_score_suggests_upgrade(self):
        """V0 metric with score >=70 should suggest considering V1"""
        pack = {
            "metrics": [
                {
                    "id": "v0_metric",
                    "name": "V0 Metric",
                    "tier": "V0",
                    "sql": {"value": "SELECT 1"},
                    "tests": [{"type": "not_null", "field": "value"}],
                }
            ]
        }
        score_result = MockScoreResult(
            pack_score=80,
            metric_scores=[
                MockMetricScore(metric_id="v0_metric", score=80, gaps=[], tier="V0")
            ]
        )

        result = deterministic_suggestions(pack, score_result)

        assert "v0_metric" in result
        suggestions = result["v0_metric"]

        # Should have info about V1 upgrade path
        v1_suggestions = [s for s in suggestions if "V1" in s.get("message", "")]
        assert len(v1_suggestions) > 0
        assert v1_suggestions[0].get("severity") == "info"

    def test_multiple_gaps_generate_multiple_actions(self):
        """Multiple gaps should generate multiple actionable suggestions"""
        pack = {
            "metrics": [
                {
                    "id": "many_gaps_metric",
                    "name": "Many Gaps Metric",
                }
            ]
        }
        score_result = MockScoreResult(
            pack_score=60,
            metric_scores=[
                MockMetricScore(
                    metric_id="many_gaps_metric",
                    score=60,
                    gaps=["missing_sql", "missing_tests", "missing_accountable"]
                )
            ]
        )

        result = deterministic_suggestions(pack, score_result)

        assert "many_gaps_metric" in result
        suggestions = result["many_gaps_metric"]

        # Should have at least 3 suggestions (one per gap)
        assert len(suggestions) >= 3

    def test_metric_without_score_is_skipped(self):
        """Metric that has no score should not appear in suggestions"""
        pack = {
            "metrics": [
                {"id": "metric_with_score", "name": "Scored"},
                {"id": "metric_without_score", "name": "Not Scored"},
            ]
        }
        score_result = MockScoreResult(
            pack_score=75,
            metric_scores=[
                MockMetricScore(metric_id="metric_with_score", score=75, gaps=[])
            ]
        )

        result = deterministic_suggestions(pack, score_result)

        assert "metric_with_score" in result
        assert "metric_without_score" not in result

    def test_suggestions_have_required_fields(self):
        """All suggestions should have severity and message"""
        pack = {
            "metrics": [
                {
                    "id": "test_metric",
                    "name": "Test Metric",
                    "tier": "V0",
                }
            ]
        }
        score_result = MockScoreResult(
            pack_score=70,
            metric_scores=[
                MockMetricScore(metric_id="test_metric", score=70, gaps=["missing_sql"])
            ]
        )

        result = deterministic_suggestions(pack, score_result)

        suggestions = result["test_metric"]
        for suggestion in suggestions:
            assert "severity" in suggestion
            assert "message" in suggestion
            assert suggestion["severity"] in ["good", "info", "warning", "critical"]
            assert len(suggestion["message"]) > 0


class TestSuggestionSeverityLevels:
    """Test that suggestions use appropriate severity levels"""

    def test_good_severity_for_high_scores(self):
        """High-scoring metrics should get 'good' severity"""
        pack = {
            "metrics": [
                {"id": "excellent_metric", "name": "Excellent", "tier": "V1"}
            ]
        }
        score_result = MockScoreResult(
            pack_score=95,
            metric_scores=[
                MockMetricScore(metric_id="excellent_metric", score=95, gaps=[])
            ]
        )

        result = deterministic_suggestions(pack, score_result)

        good_suggestions = [s for s in result["excellent_metric"] if s["severity"] == "good"]
        assert len(good_suggestions) > 0

    def test_info_severity_for_optional_improvements(self):
        """Optional improvements should use 'info' severity"""
        pack = {
            "metrics": [
                {"id": "v0_ready", "name": "V0 Ready", "tier": "V0"}
            ]
        }
        score_result = MockScoreResult(
            pack_score=75,
            metric_scores=[
                MockMetricScore(metric_id="v0_ready", score=75, gaps=[], tier="V0")
            ]
        )

        result = deterministic_suggestions(pack, score_result)

        info_suggestions = [s for s in result["v0_ready"] if s["severity"] == "info"]
        assert len(info_suggestions) > 0


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_none_metrics_handled_gracefully(self):
        """Pack with metrics: None should not crash"""
        pack = {"metrics": None}
        score_result = MockScoreResult(pack_score=0, metric_scores=[])

        result = deterministic_suggestions(pack, score_result)

        assert result == {}

    def test_metric_without_id_is_skipped(self):
        """Metrics without IDs should be skipped"""
        pack = {
            "metrics": [
                {"name": "No ID Metric"},
                {"id": "valid_metric", "name": "Valid"},
            ]
        }
        score_result = MockScoreResult(
            pack_score=75,
            metric_scores=[
                MockMetricScore(metric_id="valid_metric", score=75, gaps=[])
            ]
        )

        result = deterministic_suggestions(pack, score_result)

        assert "valid_metric" in result
        assert len(result) == 1  # Only valid_metric

    def test_empty_gaps_list_handled(self):
        """Empty gaps list should not crash"""
        pack = {
            "metrics": [
                {"id": "perfect_metric", "name": "Perfect"}
            ]
        }
        score_result = MockScoreResult(
            pack_score=100,
            metric_scores=[
                MockMetricScore(metric_id="perfect_metric", score=100, gaps=[])
            ]
        )

        result = deterministic_suggestions(pack, score_result)

        assert "perfect_metric" in result
        # Should still have at least one suggestion (good signal)
        assert len(result["perfect_metric"]) > 0

    def test_unknown_gap_types_handled_gracefully(self):
        """Unknown gap types should not crash the system"""
        pack = {
            "metrics": [
                {"id": "unknown_gap", "name": "Unknown Gap"}
            ]
        }
        score_result = MockScoreResult(
            pack_score=70,
            metric_scores=[
                MockMetricScore(
                    metric_id="unknown_gap",
                    score=70,
                    gaps=["missing_sql", "unknown_gap_type", "another_unknown"]
                )
            ]
        )

        result = deterministic_suggestions(pack, score_result)

        # Should not crash, should handle known gaps at minimum
        assert "unknown_gap" in result
        sql_suggestions = [s for s in result["unknown_gap"] if "SQL" in s.get("message", "")]
        assert len(sql_suggestions) > 0
