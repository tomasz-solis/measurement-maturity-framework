"""Tests for mmf.scoring module."""

from mmf.scoring import score_pack
from mmf.config import ScoringConfig


class TestBasicScoring:
    """Basic scoring functionality tests."""

    def test_perfect_metric_scores_high(self):
        """A metric with all fields should score high."""
        pack = {
            "metrics": [
                {
                    "id": "perfect_metric",
                    "name": "Perfect Metric",
                    "tier": "V1",
                    "accountable": "Test Team",
                    "sql": {"value": "SELECT 1"},
                    "tests": [{"type": "not_null"}],
                }
            ]
        }
        result = score_pack(pack)

        assert result.pack_score == 100.0
        assert len(result.metric_scores) == 1
        assert result.metric_scores[0].score == 100.0
        assert len(result.metric_scores[0].gaps) == 0

    def test_minimal_metric_scores_lower(self):
        """A metric with only required fields should score lower."""
        pack = {
            "metrics": [
                {
                    "id": "minimal",
                    "name": "Minimal Metric",
                    # Missing: accountable, sql, tests, tier
                }
            ]
        }
        result = score_pack(pack)

        # Should lose points for missing accountable (-5), sql (-5), tests (-5) = 85
        assert result.pack_score == 85.0
        assert len(result.metric_scores[0].gaps) == 3

    def test_v0_tier_deduction(self):
        """V0 tier should deduct points."""
        config = ScoringConfig()

        pack_v0 = {
            "metrics": [
                {
                    "id": "v0_metric",
                    "name": "V0 Metric",
                    "tier": "V0",
                    "accountable": "Team",
                    "sql": {"value": "SELECT 1"},
                    "tests": [{}],
                }
            ]
        }
        pack_v1 = {
            "metrics": [
                {
                    "id": "v1_metric",
                    "name": "V1 Metric",
                    "tier": "V1",
                    "accountable": "Team",
                    "sql": {"value": "SELECT 1"},
                    "tests": [{}],
                }
            ]
        }

        result_v0 = score_pack(pack_v0)
        result_v1 = score_pack(pack_v1)

        # V0 should score lower
        assert (
            result_v0.pack_score == result_v1.pack_score - config.deductions["v0_tier"]
        )
        assert "tier_v0" in result_v0.metric_scores[0].gaps


class TestSQLScoring:
    """Tests for SQL-related scoring."""

    def test_value_sql_counts(self):
        """Metric with 'value' SQL should not lose points."""
        pack = {
            "metrics": [
                {
                    "id": "test",
                    "name": "Test",
                    "sql": {"value": "SELECT COUNT(*) FROM table"},
                    "accountable": "Team",
                    "tests": [{}],
                }
            ]
        }
        result = score_pack(pack)

        assert "missing_sql" not in result.metric_scores[0].gaps
        assert result.pack_score == 100.0

    def test_ratio_sql_counts(self):
        """Metric with numerator/denominator SQL should not lose points."""
        pack = {
            "metrics": [
                {
                    "id": "test",
                    "name": "Test",
                    "sql": {
                        "numerator": "SELECT COUNT(*) FROM success",
                        "denominator": "SELECT COUNT(*) FROM total",
                    },
                    "accountable": "Team",
                    "tests": [{}],
                }
            ]
        }
        result = score_pack(pack)

        assert "missing_sql" not in result.metric_scores[0].gaps
        assert result.pack_score == 100.0

    def test_partial_ratio_sql_deducts(self):
        """Metric with only numerator should deduct points."""
        pack = {
            "metrics": [
                {
                    "id": "test",
                    "name": "Test",
                    "sql": {"numerator": "SELECT COUNT(*) FROM success"},
                    "accountable": "Team",
                    "tests": [{}],
                }
            ]
        }
        result = score_pack(pack)

        assert "missing_sql" in result.metric_scores[0].gaps

    def test_empty_sql_dict_deducts(self):
        """Metric with empty SQL dict should deduct points."""
        pack = {
            "metrics": [
                {
                    "id": "test",
                    "name": "Test",
                    "sql": {},
                    "accountable": "Team",
                    "tests": [{}],
                }
            ]
        }
        result = score_pack(pack)

        assert "missing_sql" in result.metric_scores[0].gaps


class TestPackScoring:
    """Tests for pack-level scoring."""

    def test_empty_pack_scores_zero(self):
        """Empty pack should score 0."""
        pack = {"metrics": []}
        result = score_pack(pack)

        assert result.pack_score == 0.0
        assert result.avg_metric_score == 0.0
        assert len(result.metric_scores) == 0

    def test_pack_score_is_average(self):
        """Pack score should be average of metric scores."""
        pack = {
            "metrics": [
                # Perfect metric: 100
                {
                    "id": "m1",
                    "name": "M1",
                    "accountable": "T",
                    "sql": {"value": "1"},
                    "tests": [{}],
                },
                # Missing all: 85
                {"id": "m2", "name": "M2"},
            ]
        }
        result = score_pack(pack)

        expected_avg = (100.0 + 85.0) / 2
        assert result.pack_score == expected_avg
        assert result.avg_metric_score == expected_avg

    def test_multiple_metrics_scored_independently(self):
        """Each metric should be scored independently."""
        pack = {
            "metrics": [
                {"id": "m1", "name": "M1", "tier": "V0"},
                {"id": "m2", "name": "M2", "tier": "V1"},
            ]
        }
        result = score_pack(pack)

        assert len(result.metric_scores) == 2
        # V0 should score lower than V1
        assert result.metric_scores[0].score < result.metric_scores[1].score


class TestScoreResult:
    """Tests for ScoreResult dataclass."""

    def test_score_result_contains_all_fields(self):
        """ScoreResult should have all expected fields."""
        pack = {"metrics": [{"id": "test", "name": "Test"}]}
        result = score_pack(pack)

        assert hasattr(result, "pack_score")
        assert hasattr(result, "avg_metric_score")
        assert hasattr(result, "metric_scores")
        assert isinstance(result.metric_scores, list)

    def test_metric_score_contains_all_fields(self):
        """MetricScore should have all expected fields."""
        pack = {"metrics": [{"id": "test", "name": "Test Metric", "status": "active"}]}
        result = score_pack(pack)
        ms = result.metric_scores[0]

        assert ms.metric_id == "test"
        assert ms.name == "Test Metric"
        assert ms.status == "active"
        assert isinstance(ms.score, float)
        assert isinstance(ms.why, str)
        assert isinstance(ms.gaps, list)


class TestScoreWhy:
    """Tests for score explanation generation."""

    def test_perfect_score_gets_positive_why(self):
        """Perfect score should get positive message."""
        pack = {
            "metrics": [
                {
                    "id": "perfect",
                    "name": "Perfect",
                    "accountable": "Team",
                    "sql": {"value": "SELECT 1"},
                    "tests": [{}],
                }
            ]
        }
        result = score_pack(pack)

        assert (
            "production-ready" in result.metric_scores[0].why.lower()
            or "well-defined" in result.metric_scores[0].why.lower()
        )

    def test_gaps_appear_in_why(self):
        """Gaps should be mentioned in why message."""
        pack = {
            "metrics": [
                {
                    "id": "gappy",
                    "name": "Gappy Metric",
                    # Missing: accountable, sql, tests
                }
            ]
        }
        result = score_pack(pack)
        why = result.metric_scores[0].why.lower()

        # Should mention missing elements
        assert "accountable" in why or "sql" in why or "tests" in why


class TestEdgeCases:
    """Tests for edge cases in scoring."""

    def test_score_never_below_zero(self):
        """Score should never go below 0."""
        # This shouldn't be possible with current deductions, but test anyway
        pack = {
            "metrics": [
                {
                    "id": "worst",
                    "name": "Worst Metric",
                    "tier": "V0",
                    "ai": True,
                    # Missing accountable, sql, tests
                }
            ]
        }
        result = score_pack(pack)

        assert result.metric_scores[0].score >= 0

    def test_score_never_above_100(self):
        """Score should never exceed 100."""
        pack = {
            "metrics": [
                {
                    "id": "best",
                    "name": "Best Metric",
                    "accountable": "Team",
                    "sql": {"value": "SELECT 1"},
                    "tests": [{}],
                }
            ]
        }
        result = score_pack(pack)

        assert result.metric_scores[0].score <= 100

    def test_missing_metric_id_handled(self):
        """Missing metric ID should default to 'unknown'."""
        pack = {"metrics": [{"name": "No ID Metric"}]}
        result = score_pack(pack)

        assert result.metric_scores[0].metric_id == "unknown"

    def test_missing_metric_name_handled(self):
        """Missing metric name should default."""
        pack = {"metrics": [{"id": "no_name"}]}
        result = score_pack(pack)

        assert result.metric_scores[0].name == "Unnamed metric"

    def test_missing_status_defaults_to_active(self):
        """Missing status should default to 'active'."""
        pack = {"metrics": [{"id": "test", "name": "Test"}]}
        result = score_pack(pack)

        assert result.metric_scores[0].status == "active"

    def test_case_insensitive_tier_v0(self):
        """V0 tier should be case-insensitive."""
        for tier_value in ["V0", "v0", "V0"]:
            pack = {
                "metrics": [
                    {
                        "id": "test",
                        "name": "Test",
                        "tier": tier_value,
                        "accountable": "Team",
                        "sql": {"value": "1"},
                        "tests": [{}],
                    }
                ]
            }
            result = score_pack(pack)

            assert "tier_v0" in result.metric_scores[0].gaps
            assert result.metric_scores[0].score == 90.0  # 100 - 10 for V0
