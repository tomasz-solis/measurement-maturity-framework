"""Tests for mmf.scoring module."""

from mmf.scoring import score_pack
from mmf.config import ScoringConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _full_metric(metric_id: str = "m", **overrides) -> dict:
    """Return a fully-defined metric that scores 100 under the current model."""
    base = {
        "id": metric_id,
        "name": "Full Metric",
        "description": "Measures X so that we can track Y.",
        "tier": "V1",
        "status": "active",
        "accountable": "Test Team",
        "grain": "account_week",
        "unit": "percent",
        "sql": {"value": "SELECT 1"},
        "tests": [{"type": "not_null"}],
    }
    base.update(overrides)
    return base


def _config() -> ScoringConfig:
    return ScoringConfig()


# ---------------------------------------------------------------------------
# Basic scoring
# ---------------------------------------------------------------------------


class TestBasicScoring:
    """Basic scoring functionality tests."""

    def test_perfect_metric_scores_100(self):
        """A metric with all expected fields should score 100."""
        result = score_pack({"metrics": [_full_metric()]})

        assert result.pack_score == 100.0
        assert len(result.metric_scores) == 1
        assert result.metric_scores[0].score == 100.0
        assert result.metric_scores[0].gaps == []

    def test_minimal_metric_scores_lower(self):
        """A metric with only id and name loses points for every missing field."""
        # Missing: accountable (-5), sql (-5), tests (-5),
        #          description (-3), grain (-2), unit (-2) = 78
        pack = {"metrics": [{"id": "minimal", "name": "Minimal Metric"}]}
        result = score_pack(pack)

        config = _config()
        expected = (
            config.base_score
            - config.deductions["missing_accountable"]
            - config.deductions["missing_sql"]
            - config.deductions["missing_tests"]
            - config.deductions.get("missing_description", 0)
            - config.deductions.get("missing_grain", 0)
            - config.deductions.get("missing_unit", 0)
        )
        assert result.pack_score == float(expected)
        assert len(result.metric_scores[0].gaps) == 6

    def test_v0_tier_deduction(self):
        """V0 tier should deduct points relative to the same metric at V1."""
        pack_v0 = {"metrics": [_full_metric("v0", tier="V0")]}
        pack_v1 = {"metrics": [_full_metric("v1", tier="V1")]}

        result_v0 = score_pack(pack_v0)
        result_v1 = score_pack(pack_v1)

        config = _config()
        assert (
            result_v0.pack_score == result_v1.pack_score - config.deductions["v0_tier"]
        )
        assert "tier_v0" in result_v0.metric_scores[0].gaps

    def test_responsible_field_prevents_deduction(self):
        """'responsible' should work the same as 'accountable' for scoring."""
        metric = _full_metric(accountable=None, responsible="Growth Team")
        result = score_pack({"metrics": [metric]})

        assert "missing_accountable" not in result.metric_scores[0].gaps
        assert result.pack_score == 100.0


# ---------------------------------------------------------------------------
# SQL scoring
# ---------------------------------------------------------------------------


class TestSQLScoring:
    """Tests for SQL-related scoring."""

    def test_value_sql_counts(self):
        """Metric with 'value' SQL should not lose SQL points."""
        metric = _full_metric(sql={"value": "SELECT COUNT(*) FROM table"})
        result = score_pack({"metrics": [metric]})

        assert "missing_sql" not in result.metric_scores[0].gaps
        assert result.pack_score == 100.0

    def test_ratio_sql_counts(self):
        """Metric with numerator/denominator SQL should not lose SQL points."""
        metric = _full_metric(
            sql={
                "numerator": "SELECT COUNT(*) FROM success",
                "denominator": "SELECT COUNT(*) FROM total",
            }
        )
        result = score_pack({"metrics": [metric]})

        assert "missing_sql" not in result.metric_scores[0].gaps
        assert result.pack_score == 100.0

    def test_partial_ratio_sql_deducts(self):
        """Metric with only numerator (no denominator) should lose SQL points."""
        metric = _full_metric(sql={"numerator": "SELECT COUNT(*) FROM success"})
        result = score_pack({"metrics": [metric]})

        assert "missing_sql" in result.metric_scores[0].gaps

    def test_empty_sql_dict_deducts(self):
        """Metric with an empty SQL dict should lose SQL points."""
        metric = _full_metric(sql={})
        result = score_pack({"metrics": [metric]})

        assert "missing_sql" in result.metric_scores[0].gaps


# ---------------------------------------------------------------------------
# Pack-level scoring
# ---------------------------------------------------------------------------


class TestPackScoring:
    """Tests for pack-level scoring."""

    def test_empty_pack_scores_zero(self):
        """Empty pack should score 0."""
        result = score_pack({"metrics": []})

        assert result.pack_score == 0.0
        assert result.avg_metric_score == 0.0
        assert result.min_metric_score == 0.0
        assert len(result.metric_scores) == 0

    def test_pack_score_reflects_floor_weight(self):
        """pack_score blends average and minimum per the floor-weight formula."""
        # m1 is fully defined (100). m2 has only id and name.
        config = _config()
        m2_score = float(
            config.base_score
            - config.deductions["missing_accountable"]
            - config.deductions["missing_sql"]
            - config.deductions["missing_tests"]
            - config.deductions.get("missing_description", 0)
            - config.deductions.get("missing_grain", 0)
            - config.deductions.get("missing_unit", 0)
        )

        pack = {"metrics": [_full_metric("m1"), {"id": "m2", "name": "M2"}]}
        result = score_pack(pack)

        expected_avg = round((100.0 + m2_score) / 2, 10)
        expected_min = m2_score
        expected_pack = round(
            (1 - config.pack_floor_weight) * expected_avg
            + config.pack_floor_weight * expected_min,
            2,
        )

        assert result.pack_score == expected_pack
        assert result.min_metric_score == expected_min
        assert result.pack_score < result.avg_metric_score

    def test_custom_floor_weight_1_equals_weakest_metric(self, monkeypatch):
        """With floor_weight=1.0, the pack score equals the weakest metric score."""
        custom_config = ScoringConfig(pack_floor_weight=1.0)
        monkeypatch.setattr("mmf.scoring.load_config", lambda: custom_config)

        pack = {"metrics": [_full_metric("strong"), {"id": "weak", "name": "Weak"}]}
        result = score_pack(pack)

        assert result.pack_score == result.min_metric_score
        assert result.avg_metric_score > result.min_metric_score

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
        assert result.metric_scores[0].score < result.metric_scores[1].score


# ---------------------------------------------------------------------------
# Behavioral contract tests (replaces structural hasattr checks)
# ---------------------------------------------------------------------------


class TestScoringContract:
    """Behavioral tests for scoring arithmetic and gap accumulation."""

    def test_gap_accumulation_is_monotone(self):
        """Each additional gap should decrease the metric score by its deduction."""
        config = _config()
        base = config.base_score

        def score(**kwargs) -> float:
            return (
                score_pack({"metrics": [{"id": "m", "name": "M", **kwargs}]})
                .metric_scores[0]
                .score
            )

        full = score(
            description="D",
            grain="user_day",
            unit="count",
            accountable="T",
            sql={"value": "SELECT 1"},
            tests=[{}],
        )
        no_tests = score(
            description="D",
            grain="user_day",
            unit="count",
            accountable="T",
            sql={"value": "SELECT 1"},
        )
        no_sql = score(
            description="D",
            grain="user_day",
            unit="count",
            accountable="T",
            tests=[{}],
        )
        no_owner = score(
            description="D",
            grain="user_day",
            unit="count",
            sql={"value": "SELECT 1"},
            tests=[{}],
        )
        no_desc = score(
            grain="user_day",
            unit="count",
            accountable="T",
            sql={"value": "SELECT 1"},
            tests=[{}],
        )

        assert full == base
        assert no_tests == base - config.deductions["missing_tests"]
        assert no_sql == base - config.deductions["missing_sql"]
        assert no_owner == base - config.deductions["missing_accountable"]
        assert no_desc == base - config.deductions.get("missing_description", 0)

    def test_score_is_clamped_to_zero_minimum(self):
        """Score should never go below 0, even with many deductions."""
        result = score_pack(
            {"metrics": [{"id": "worst", "name": "Worst", "tier": "V0"}]}
        )
        assert result.metric_scores[0].score >= 0

    def test_score_never_exceeds_100(self):
        """A fully-defined metric should not exceed 100."""
        result = score_pack({"metrics": [_full_metric()]})
        assert result.metric_scores[0].score <= 100.0

    def test_missing_id_defaults_to_unknown(self):
        """Missing metric ID should default to 'unknown'."""
        result = score_pack({"metrics": [{"name": "No ID"}]})
        assert result.metric_scores[0].metric_id == "unknown"

    def test_missing_name_defaults(self):
        """Missing metric name should default gracefully."""
        result = score_pack({"metrics": [{"id": "no_name"}]})
        assert result.metric_scores[0].name == "Unnamed metric"

    def test_missing_status_defaults_to_active(self):
        """Missing status should default to 'active'."""
        result = score_pack({"metrics": [{"id": "t", "name": "T"}]})
        assert result.metric_scores[0].status == "active"

    def test_null_status_defaults_to_active(self):
        """Null status should also normalise to 'active'."""
        result = score_pack({"metrics": [{"id": "t", "name": "T", "status": None}]})
        assert result.metric_scores[0].status == "active"

    def test_case_insensitive_tier_v0(self):
        """V0 tier detection should be case-insensitive."""
        config = _config()
        for tier_value in ["V0", "v0"]:
            metric = _full_metric("t", tier=tier_value)
            result = score_pack({"metrics": [metric]})
            assert "tier_v0" in result.metric_scores[0].gaps
            assert result.metric_scores[0].score == 100.0 - config.deductions["v0_tier"]


# ---------------------------------------------------------------------------
# Score explanation (_build_why)
# ---------------------------------------------------------------------------


class TestScoreWhy:
    """Tests for score explanation generation."""

    def test_fully_defined_metric_gets_positive_why(self):
        """A metric with no gaps should get a production-ready message."""
        result = score_pack({"metrics": [_full_metric()]})
        why = result.metric_scores[0].why.lower()

        assert "production-ready" in why or "well-defined" in why

    def test_gaps_appear_in_why(self):
        """Each gap type should surface in the why explanation."""
        result = score_pack({"metrics": [{"id": "gappy", "name": "Gappy"}]})
        why = result.metric_scores[0].why.lower()

        # Missing accountable, sql, tests, description, grain, unit
        assert any(
            word in why
            for word in ["accountable", "sql", "tests", "description", "grain", "unit"]
        )

    def test_v0_why_mentions_proxy(self):
        """V0 tier gap should appear in the why message."""
        metric = _full_metric(tier="V0")
        result = score_pack({"metrics": [metric]})
        assert (
            "v0" in result.metric_scores[0].why.lower()
            or "proxy" in result.metric_scores[0].why.lower()
        )
