"""
Tests for mmf/config.py - scoring configuration and validation
"""

import pytest

from mmf.config import ScoringConfig, load_config


class TestConfigDefaults:
    """Test default configuration values"""

    def test_default_config_loads(self):
        """Default config should load without errors"""
        config = load_config()

        assert config.base_score == 100
        assert isinstance(config.deductions, dict)
        assert isinstance(config.thresholds, dict)
        assert config.pack_floor_weight == 0.3

    def test_default_deductions_present(self):
        """Default config should have all expected deductions"""
        config = ScoringConfig()

        assert "v0_tier" in config.deductions
        assert "missing_accountable" in config.deductions
        assert "missing_sql" in config.deductions
        assert "missing_tests" in config.deductions
        assert "missing_description" in config.deductions
        assert "missing_grain" in config.deductions
        assert "missing_unit" in config.deductions

    def test_default_thresholds_present(self):
        """Default config should have all required thresholds"""
        config = ScoringConfig()

        assert "decision_ready" in config.thresholds
        assert "usable_with_caution" in config.thresholds
        assert "early_fragile" in config.thresholds

    def test_default_thresholds_ordered_correctly(self):
        """Thresholds should be in descending order"""
        config = ScoringConfig()

        assert (
            config.thresholds["decision_ready"]
            > config.thresholds["usable_with_caution"]
        )
        assert (
            config.thresholds["usable_with_caution"]
            > config.thresholds["early_fragile"]
        )


class TestConfigValidation:
    """Test configuration validation logic"""

    def test_invalid_base_score_raises(self):
        """Base score outside 0-100 should raise ValueError"""
        with pytest.raises(
            ValueError, match="base_score must be an integer between 0 and 100"
        ):
            ScoringConfig(base_score=150)

        with pytest.raises(
            ValueError, match="base_score must be an integer between 0 and 100"
        ):
            ScoringConfig(base_score=-10)

    def test_negative_deduction_raises(self):
        """Negative deduction values should raise ValueError"""
        with pytest.raises(ValueError, match="must be a non-negative number"):
            ScoringConfig(deductions={"v0_tier": -5})

    def test_deduction_exceeds_base_raises(self):
        """Deduction > base_score should raise ValueError"""
        with pytest.raises(ValueError, match="cannot exceed base_score"):
            ScoringConfig(base_score=100, deductions={"v0_tier": 150})

    def test_non_dict_deductions_raises(self):
        """Deductions must be a dictionary"""
        with pytest.raises(ValueError, match="deductions must be a dictionary"):
            ScoringConfig(deductions="not a dict")

    def test_non_dict_thresholds_raises(self):
        """Thresholds must be a dictionary"""
        with pytest.raises(ValueError, match="thresholds must be a dictionary"):
            ScoringConfig(thresholds=[80, 60, 40])

    def test_missing_required_threshold_raises(self):
        """Missing required threshold keys should raise ValueError"""
        with pytest.raises(
            ValueError, match="Missing required threshold: decision_ready"
        ):
            ScoringConfig(thresholds={"usable_with_caution": 60, "early_fragile": 40})

    def test_threshold_out_of_range_raises(self):
        """Threshold values outside 0-100 should raise ValueError"""
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            ScoringConfig(
                thresholds={
                    "decision_ready": 150,
                    "usable_with_caution": 60,
                    "early_fragile": 40,
                }
            )

    def test_wrong_threshold_order_raises(self):
        """Thresholds not in descending order should raise ValueError"""
        with pytest.raises(ValueError, match="Thresholds must be ordered"):
            ScoringConfig(
                thresholds={
                    "decision_ready": 60,  # Should be highest
                    "usable_with_caution": 80,  # Wrong order
                    "early_fragile": 40,
                }
            )

    def test_valid_custom_config_works(self):
        """Valid custom configuration should not raise"""
        config = ScoringConfig(
            base_score=100,
            deductions={"v0_tier": 15, "missing_sql": 10},
            thresholds={
                "decision_ready": 90,
                "usable_with_caution": 70,
                "early_fragile": 50,
            },
            pack_floor_weight=0.4,
        )

        assert config.base_score == 100
        assert config.deductions["v0_tier"] == 15
        assert config.thresholds["decision_ready"] == 90
        assert config.pack_floor_weight == 0.4

    def test_invalid_pack_floor_weight_raises(self):
        """Pack floor weight must stay within the 0-1 range."""
        with pytest.raises(
            ValueError, match="pack_floor_weight must be a number between 0 and 1"
        ):
            ScoringConfig(pack_floor_weight=1.2)

        with pytest.raises(
            ValueError, match="pack_floor_weight must be a number between 0 and 1"
        ):
            ScoringConfig(pack_floor_weight=-0.1)


class TestThresholdLabels:
    """Test threshold label methods"""

    def test_get_threshold_label_decision_ready(self):
        """Score >= 80 should return Decision-ready"""
        config = ScoringConfig()

        assert config.get_threshold_label(100) == "Decision-ready"
        assert config.get_threshold_label(80) == "Decision-ready"

    def test_get_threshold_label_usable_with_caution(self):
        """Score 60-79 should return Usable with caution"""
        config = ScoringConfig()

        assert config.get_threshold_label(79) == "Usable with caution"
        assert config.get_threshold_label(60) == "Usable with caution"

    def test_get_threshold_label_early_fragile(self):
        """Score 40-59 should return Early/fragile"""
        config = ScoringConfig()

        assert config.get_threshold_label(59) == "Early/fragile"
        assert config.get_threshold_label(40) == "Early/fragile"

    def test_get_threshold_label_not_safe(self):
        """Score < 40 should return Not safe for decisions"""
        config = ScoringConfig()

        assert config.get_threshold_label(39) == "Not safe for decisions"
        assert config.get_threshold_label(0) == "Not safe for decisions"

    def test_get_threshold_description(self):
        """Threshold descriptions should be helpful"""
        config = ScoringConfig()

        desc_high = config.get_threshold_description(90)
        assert len(desc_high) > 20
        assert "definition" in desc_high.lower() or "guardrail" in desc_high.lower()

        desc_low = config.get_threshold_description(30)
        assert len(desc_low) > 20
        assert "gap" in desc_low.lower() or "risk" in desc_low.lower()


class TestConfigImmutability:
    """Test that config validation doesn't modify values"""

    def test_validation_preserves_values(self):
        """Validation should not modify config values"""
        original_deductions = {"v0_tier": 10, "missing_sql": 5}
        original_thresholds = {
            "decision_ready": 80,
            "usable_with_caution": 60,
            "early_fragile": 40,
        }

        config = ScoringConfig(
            deductions=original_deductions.copy(), thresholds=original_thresholds.copy()
        )

        assert config.deductions == original_deductions
        assert config.thresholds == original_thresholds

    def test_load_config_returns_independent_objects(self):
        """load_config should not hand out shared mutable state."""
        first = load_config()
        second = load_config()

        first.thresholds["decision_ready"] = 95

        assert second.thresholds["decision_ready"] == 80


class TestEdgeCases:
    """Test edge cases in configuration"""

    def test_minimum_valid_config(self):
        """Minimum valid config should work with proper ordering"""
        config = ScoringConfig(
            base_score=100,
            deductions={},
            thresholds={
                "decision_ready": 80,
                "usable_with_caution": 60,
                "early_fragile": 40,
            },
        )

        assert config.base_score == 100
        assert len(config.deductions) == 0

    def test_empty_deductions_valid(self):
        """Empty deductions dictionary should be valid"""
        config = ScoringConfig(
            deductions={},
            thresholds={
                "decision_ready": 80,
                "usable_with_caution": 60,
                "early_fragile": 40,
            },
        )

        assert config.deductions == {}

    def test_float_deductions_accepted(self):
        """Float deduction values should be accepted"""
        config = ScoringConfig(
            deductions={"v0_tier": 10.5, "missing_sql": 5.5},
            thresholds={
                "decision_ready": 80,
                "usable_with_caution": 60,
                "early_fragile": 40,
            },
        )

        assert config.deductions["v0_tier"] == 10.5
