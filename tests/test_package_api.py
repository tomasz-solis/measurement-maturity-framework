"""Tests for the public mmf package API."""

import mmf


class TestPackageApi:
    """Keep the root package exports stable for library users."""

    def test_core_helpers_are_available_from_package_root(self):
        """The package root should expose the core validator, scorer, and config API."""
        assert callable(mmf.validate_metric_pack)
        assert callable(mmf.score_pack)
        assert callable(mmf.deterministic_suggestions)
        assert callable(mmf.load_config)
        assert mmf.ValidationResult.__name__ == "ValidationResult"
        assert mmf.ValidationIssue.__name__ == "ValidationIssue"
        assert mmf.ScoreResult.__name__ == "ScoreResult"
        assert mmf.MetricScore.__name__ == "MetricScore"
        assert mmf.ScoringConfig.__name__ == "ScoringConfig"
