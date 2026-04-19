# mmf/config.py
"""Scoring configuration for the Measurement Maturity Framework."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict


def _default_deductions() -> Dict[str, int]:
    """Return the default deduction values for metric scoring.

    Larger deductions cover missing ownership, SQL, or tests. Smaller ones
    cover metadata that affects interpretation. ``implementation_type`` can
    refine the missing-SQL penalty into a temporary or structural version.
    """
    return {
        "v0_tier": 10,
        "missing_accountable": 5,
        "missing_sql": 5,
        "missing_sql_temporary": 3,
        "missing_sql_structural": 12,
        "missing_tests": 5,
        # Softer deductions: structural completeness, not safety-critical.
        # These penalise metrics that are harder to interpret or maintain,
        # without blocking a pack that is otherwise well-defined.
        "missing_description": 3,
        "missing_grain": 2,
        "missing_unit": 2,
    }


def _default_thresholds() -> Dict[str, int]:
    """Return the default score thresholds."""
    return {
        "decision_ready": 80,
        "usable_with_caution": 60,
        "early_fragile": 40,
    }


@dataclass
class ScoringConfig:
    """Configuration for metric scoring system."""

    base_score: int = 100
    deductions: Dict[str, int] = field(default_factory=_default_deductions)
    thresholds: Dict[str, int] = field(default_factory=_default_thresholds)
    pack_floor_weight: float = 0.3

    def __post_init__(self) -> None:
        """Validate the configuration after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate configuration values are sensible."""
        if not isinstance(self.base_score, int) or not (0 <= self.base_score <= 100):
            raise ValueError(
                f"base_score must be an integer between 0 and 100, got {self.base_score}"
            )

        if not isinstance(self.deductions, dict):
            raise ValueError("deductions must be a dictionary")

        for key, value in self.deductions.items():
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError(
                    f"Deduction '{key}' must be a non-negative number, got {value}"
                )
            if value > self.base_score:
                raise ValueError(
                    f"Deduction '{key}' ({value}) cannot exceed base_score ({self.base_score})"
                )

        if not isinstance(self.thresholds, dict):
            raise ValueError("thresholds must be a dictionary")

        required_thresholds = ["decision_ready", "usable_with_caution", "early_fragile"]
        for threshold_name in required_thresholds:
            if threshold_name not in self.thresholds:
                raise ValueError(f"Missing required threshold: {threshold_name}")

            value = self.thresholds[threshold_name]
            if not isinstance(value, (int, float)) or not (0 <= value <= 100):
                raise ValueError(
                    f"Threshold '{threshold_name}' must be between 0 and 100, got {value}"
                )

        if not (
            self.thresholds["decision_ready"]
            > self.thresholds["usable_with_caution"]
            > self.thresholds["early_fragile"]
        ):
            raise ValueError(
                "Thresholds must be ordered: decision_ready > usable_with_caution > early_fragile. "
                f"Got: {self.thresholds['decision_ready']}, "
                f"{self.thresholds['usable_with_caution']}, {self.thresholds['early_fragile']}"
            )

        if not isinstance(self.pack_floor_weight, (int, float)) or not (
            0 <= self.pack_floor_weight <= 1
        ):
            raise ValueError(
                "pack_floor_weight must be a number between 0 and 1, "
                f"got {self.pack_floor_weight}"
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


# Default configuration instance used as a template for fresh config objects.
DEFAULT_CONFIG = ScoringConfig()


def load_config() -> ScoringConfig:
    """Load scoring configuration as a fresh object.

    Returning a copy avoids hidden global state if callers mutate deductions
    or thresholds at runtime.
    """
    return ScoringConfig(
        base_score=DEFAULT_CONFIG.base_score,
        deductions=DEFAULT_CONFIG.deductions.copy(),
        thresholds=DEFAULT_CONFIG.thresholds.copy(),
        pack_floor_weight=DEFAULT_CONFIG.pack_floor_weight,
    )
