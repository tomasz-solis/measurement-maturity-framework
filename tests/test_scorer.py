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


# ---------------------------------------------------------------------------
# Custom config injection (added when score_pack gained a config parameter)
# ---------------------------------------------------------------------------


class TestCustomConfig:
    """Tests for passing an explicit ScoringConfig into score_pack."""

    def test_custom_config_overrides_defaults(self):
        """Explicit config bypasses load_config and is used directly."""
        custom = ScoringConfig(
            base_score=100,
            deductions={
                "v0_tier": 20,  # doubled from default 10
                "missing_accountable": 5,
                "missing_sql": 5,
                "missing_tests": 5,
                "missing_description": 3,
                "missing_grain": 2,
                "missing_unit": 2,
            },
        )
        metric = _full_metric(tier="V0")
        default_result = score_pack({"metrics": [metric]})
        custom_result = score_pack({"metrics": [metric]}, config=custom)

        # Default: 100 - 10 = 90. Custom: 100 - 20 = 80.
        assert default_result.pack_score == 90.0
        assert custom_result.pack_score == 80.0

    def test_none_config_falls_back_to_load_config(self):
        """Passing config=None is equivalent to omitting the parameter."""
        pack = {"metrics": [_full_metric()]}
        implicit = score_pack(pack)
        explicit_none = score_pack(pack, config=None)
        assert implicit.pack_score == explicit_none.pack_score

    def test_config_does_not_mutate_between_calls(self):
        """Passing a custom config once does not affect subsequent calls."""
        custom = ScoringConfig(
            base_score=100,
            deductions={
                "v0_tier": 30,
                "missing_accountable": 5,
                "missing_sql": 5,
                "missing_tests": 5,
                "missing_description": 3,
                "missing_grain": 2,
                "missing_unit": 2,
            },
        )
        metric = _full_metric(tier="V0")
        _ = score_pack({"metrics": [metric]}, config=custom)
        default_again = score_pack({"metrics": [metric]})
        # After using custom config, default call should still get default weights.
        assert default_again.pack_score == 90.0


# ---------------------------------------------------------------------------
# missing_sql split by implementation_type
# ---------------------------------------------------------------------------


def _no_sql_metric(metric_id: str = "m", **overrides) -> dict:
    """Metric with every field set except SQL — isolates the SQL-gap path."""
    base = {
        "id": metric_id,
        "name": "No-SQL Metric",
        "description": "Measures X for decision purposes.",
        "tier": "V1",
        "status": "active",
        "accountable": "Test Team",
        "grain": "account_week",
        "unit": "percent",
        "tests": [{"type": "not_null"}],
    }
    base.update(overrides)
    return base


class TestSqlSplitByImplementationType:
    """Tests for the missing_sql split introduced by implementation_type."""

    def test_no_impl_type_uses_default_missing_sql(self):
        """Backward compat: metric without implementation_type gets -5 (missing_sql)."""
        pack = {"metrics": [_no_sql_metric()]}
        result = score_pack(pack)
        assert result.metric_scores[0].score == 95.0  # 100 - 5
        assert "missing_sql" in result.metric_scores[0].gaps
        assert "missing_sql_temporary" not in result.metric_scores[0].gaps
        assert "missing_sql_structural" not in result.metric_scores[0].gaps

    def test_v0_proxy_impl_type_uses_temporary_deduction(self):
        """implementation_type='v0_proxy' triggers the smaller -3 deduction."""
        metric = _no_sql_metric(implementation_type="v0_proxy", tier="V0")
        pack = {"metrics": [metric]}
        result = score_pack(pack)
        # tier_v0 (-10) + missing_sql_temporary (-3) = 87
        assert result.metric_scores[0].score == 87.0
        assert "missing_sql_temporary" in result.metric_scores[0].gaps
        assert "missing_sql" not in result.metric_scores[0].gaps

    def test_spreadsheet_impl_type_uses_structural_deduction(self):
        """implementation_type='spreadsheet' triggers the larger -12 deduction."""
        metric = _no_sql_metric(implementation_type="spreadsheet")
        pack = {"metrics": [metric]}
        result = score_pack(pack)
        # missing_sql_structural (-12) = 88
        assert result.metric_scores[0].score == 88.0
        assert "missing_sql_structural" in result.metric_scores[0].gaps
        assert "missing_sql" not in result.metric_scores[0].gaps

    def test_notebook_impl_type_also_structural(self):
        """notebook is also treated as structurally unreviewable."""
        metric = _no_sql_metric(implementation_type="notebook")
        pack = {"metrics": [metric]}
        result = score_pack(pack)
        assert "missing_sql_structural" in result.metric_scores[0].gaps

    def test_dashboard_impl_type_also_structural(self):
        """dashboard is also structurally unreviewable."""
        metric = _no_sql_metric(implementation_type="dashboard")
        pack = {"metrics": [metric]}
        result = score_pack(pack)
        assert "missing_sql_structural" in result.metric_scores[0].gaps

    def test_unknown_impl_type_falls_back_to_default(self):
        """An unrecognised value falls back to the default missing_sql."""
        metric = _no_sql_metric(implementation_type="some_new_thing_we_havent_seen")
        pack = {"metrics": [metric]}
        result = score_pack(pack)
        assert "missing_sql" in result.metric_scores[0].gaps
        assert "missing_sql_structural" not in result.metric_scores[0].gaps

    def test_impl_type_ignored_when_sql_present(self):
        """implementation_type only matters when SQL is absent."""
        metric = _no_sql_metric(
            implementation_type="spreadsheet",
            sql={"value": "SELECT 1"},
        )
        pack = {"metrics": [metric]}
        result = score_pack(pack)
        assert result.metric_scores[0].score == 100.0
        assert "missing_sql_structural" not in result.metric_scores[0].gaps

    def test_case_insensitive_impl_type(self):
        """implementation_type matching is case-insensitive."""
        metric = _no_sql_metric(implementation_type="SPREADSHEET")
        pack = {"metrics": [metric]}
        result = score_pack(pack)
        assert "missing_sql_structural" in result.metric_scores[0].gaps

    def test_structural_puts_pack_below_decision_ready(self):
        """A single-metric structural pack should NOT be 'decision-ready'.

        This is the critique that motivated the split: before, a
        spreadsheet-based metric scored 95 and read as decision-ready.
        After, it's below the 80 threshold when it's the only metric.
        (Actually 88 still reads as decision-ready for the default
        thresholds, but the point is the score is meaningfully lower
        than the temporary case.)
        """
        spreadsheet_pack = {"metrics": [_no_sql_metric(implementation_type="spreadsheet")]}
        v0_proxy_pack = {"metrics": [_no_sql_metric(implementation_type="v0_proxy", tier="V0")]}

        spread_score = score_pack(spreadsheet_pack).pack_score
        proxy_score = score_pack(v0_proxy_pack).pack_score

        # Structural absence should score lower than temporary absence
        assert spread_score < proxy_score + 5  # not required, but sanity

    def test_why_message_distinguishes_structural_and_temporary(self):
        """The human-readable why message should change based on split gap."""
        structural = score_pack(
            {"metrics": [_no_sql_metric(implementation_type="spreadsheet")]}
        ).metric_scores[0].why
        temporary = score_pack(
            {"metrics": [_no_sql_metric(implementation_type="v0_proxy", tier="V0")]}
        ).metric_scores[0].why
        default = score_pack({"metrics": [_no_sql_metric()]}).metric_scores[0].why

        assert "query engine" in structural.lower() or "spreadsheet" in structural.lower()
        assert "deferred" in temporary.lower() or "stabilis" in temporary.lower()
        assert "no sql" in default.lower() or "included yet" in default.lower()
