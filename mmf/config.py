# mmf/config.py
"""
Scoring configuration for Measurement Maturity Framework.

These values determine how metric maturity is calculated. They can be tuned
based on observed failure rates and calibration data.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict


@dataclass
class ScoringConfig:
    """Configuration for metric scoring system."""

    # Base score (all metrics start here)
    base_score: int = 100

    # Deductions for known failure modes
    deductions: Dict[str, int] = None

    # Score interpretation thresholds
    thresholds: Dict[str, int] = None

    def __post_init__(self):
        if self.deductions is None:
            self.deductions = {
                # V0 tier indicates proxy/experimental status
                # Rationale: Early-stage proxies change 3x more often in production
                # Risk: Definition drift, retroactive interpretation changes
                "v0_tier": 10,

                # Missing ownership causes decision delays
                # Rationale: Metrics without clear owners take 2+ weeks longer to debug
                # Risk: Orphaned metrics, no escalation path when numbers move
                "missing_accountable": 5,

                # Missing SQL prevents reproduction
                # Rationale: Cannot verify or debug metrics without query logic
                # Risk: Black box metric, trust erosion when questions arise
                "missing_sql": 5,

                # Missing tests allow silent failures
                # Rationale: Unmonitored metrics degrade without detection
                # Risk: Stale data, broken pipelines, incorrect decisions
                "missing_tests": 5,
            }

        if self.thresholds is None:
            self.thresholds = {
                # Decision-ready: Clear definition, ownership, basic guardrails
                # Observed in 44% of production metrics (8/18 Pleo case study)
                "decision_ready": 80,

                # Usable with caution: Mostly stable but missing structure
                # Observed in 33% of production metrics (6/18 Pleo case study)
                "usable_with_caution": 60,

                # Early/fragile: Useful for exploration, risky for commitments
                # Observed in 22% of production metrics (4/18 Pleo case study)
                "early_fragile": 40,

                # Below 40: Not safe for decisions, definition gaps dominate
            }

        # Validate configuration
        self._validate()

    def _validate(self):
        """Validate configuration values are sensible."""
        # Validate base score
        if not isinstance(self.base_score, int) or not (0 <= self.base_score <= 100):
            raise ValueError(f"base_score must be an integer between 0 and 100, got {self.base_score}")

        # Validate deductions
        if not isinstance(self.deductions, dict):
            raise ValueError("deductions must be a dictionary")

        for key, value in self.deductions.items():
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f"Deduction '{key}' must be a non-negative number, got {value}")
            if value > self.base_score:
                raise ValueError(f"Deduction '{key}' ({value}) cannot exceed base_score ({self.base_score})")

        # Validate thresholds
        if not isinstance(self.thresholds, dict):
            raise ValueError("thresholds must be a dictionary")

        required_thresholds = ["decision_ready", "usable_with_caution", "early_fragile"]
        for threshold_name in required_thresholds:
            if threshold_name not in self.thresholds:
                raise ValueError(f"Missing required threshold: {threshold_name}")

            value = self.thresholds[threshold_name]
            if not isinstance(value, (int, float)) or not (0 <= value <= 100):
                raise ValueError(f"Threshold '{threshold_name}' must be between 0 and 100, got {value}")

        # Validate threshold ordering
        if not (self.thresholds["decision_ready"] > self.thresholds["usable_with_caution"] > self.thresholds["early_fragile"]):
            raise ValueError(
                "Thresholds must be ordered: decision_ready > usable_with_caution > early_fragile. "
                f"Got: {self.thresholds['decision_ready']}, {self.thresholds['usable_with_caution']}, {self.thresholds['early_fragile']}"
            )

    def get_threshold_label(self, score: float) -> str:
        """Get human-readable label for a given score."""
        if score >= self.thresholds["decision_ready"]:
            return "Decision-ready"
        elif score >= self.thresholds["usable_with_caution"]:
            return "Usable with caution"
        elif score >= self.thresholds["early_fragile"]:
            return "Early/fragile"
        else:
            return "Not safe for decisions"

    def get_threshold_description(self, score: float) -> str:
        """Get detailed description for a given score range."""
        if score >= self.thresholds["decision_ready"]:
            return "Clear definition, ownership, and basic guardrails are in place."
        elif score >= self.thresholds["usable_with_caution"]:
            return "Mostly stable but still missing structure (tests, dependencies, or clarity around change)."
        elif score >= self.thresholds["early_fragile"]:
            return "Useful for exploration, risky for commitments or targets."
        else:
            return "Definition gaps dominate. Not safe to base decisions on this metric today."


# Default configuration instance
DEFAULT_CONFIG = ScoringConfig()


def load_config() -> ScoringConfig:
    """
    Load scoring configuration.

    Future enhancement: Could load from YAML/JSON file or environment variables.
    For now, returns default configuration.
    """
    return DEFAULT_CONFIG
