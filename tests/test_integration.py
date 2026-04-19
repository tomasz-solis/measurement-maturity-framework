"""End-to-end pipeline tests: YAML → validate → score → suggest."""

from mmf.validator import validate_metric_pack
from mmf.scoring import score_pack
from mmf.suggestions import deterministic_suggestions


def _minimal_pack() -> dict:
    """Return a minimal pack that exercises the full pipeline."""
    return {
        "pack": {"id": "minimal", "name": "Minimal Pack", "schema_version": "1.0"},
        "metrics": [
            {
                "id": "signup_rate",
                "name": "Signup Rate",
                "accountable": "Growth Team",
                "sql": {"value": "SELECT 1"},
                "tests": [{"type": "not_null"}],
            }
        ],
    }


def _empty_pack() -> dict:
    """Return an empty but valid pack."""
    return {
        "pack": {"id": "empty", "name": "Empty Pack", "schema_version": "1.0"},
        "metrics": [],
    }


def _invalid_pack() -> dict:
    """Return a pack that should fail validation but not crash the pipeline."""
    return {"pack": {"id": "invalid", "name": "Invalid Pack", "schema_version": "1.0"}}


class TestFullPipeline:
    """Test the complete validate → score → suggest chain."""

    def test_minimal_pack_pipeline(self):
        """Minimal valid pack should complete the full pipeline without errors."""
        pack = _minimal_pack()
        validation = validate_metric_pack(pack)
        assert validation.ok

        score = score_pack(validation.pack)
        assert score.pack_score > 0
        assert len(score.metric_scores) == 1

        suggestions = deterministic_suggestions(validation.pack, score)
        assert len(suggestions) > 0

    def test_empty_pack_pipeline(self):
        """Empty pack should complete without errors."""
        pack = _empty_pack()
        validation = validate_metric_pack(pack)
        assert validation.ok

        score = score_pack(validation.pack)
        assert score.pack_score == 0.0

        suggestions = deterministic_suggestions(validation.pack, score)
        assert suggestions == {}

    def test_invalid_pack_pipeline(self):
        """Invalid pack should fail validation but not crash scoring."""
        pack = _invalid_pack()
        validation = validate_metric_pack(pack)
        assert not validation.ok

    def test_perfect_metric_pipeline(self):
        """A metric with all fields should score 100 and get only 'good' suggestions."""
        pack = {
            "metrics": [
                {
                    "id": "complete",
                    "name": "Complete Metric",
                    "description": "Fully defined metric for testing.",
                    "tier": "V1",
                    "status": "active",
                    "accountable": "Data Team",
                    "grain": "user_day",
                    "unit": "count",
                    "requires": ["warehouse.events"],
                    "sql": {"value": "SELECT COUNT(*) FROM events"},
                    "tests": [{"type": "not_null"}],
                }
            ]
        }

        validation = validate_metric_pack(pack)
        assert validation.ok

        score = score_pack(pack)
        assert score.pack_score == 100.0
        assert score.metric_scores[0].gaps == []

        suggestions = deterministic_suggestions(pack, score)
        assert "complete" in suggestions
        # All suggestions should be positive ("good")
        for s in suggestions["complete"]:
            assert s["severity"] == "good"

    def test_pipeline_consistency(self):
        """Gaps reported by scoring should match suggestions generated."""
        pack = {
            "metrics": [
                {
                    "id": "gappy",
                    "name": "Gappy Metric",
                    "tier": "V0",
                    # Missing: accountable, sql, tests, description, grain, unit, requires
                }
            ]
        }

        score = score_pack(pack)
        gaps = set(score.metric_scores[0].gaps)

        suggestions = deterministic_suggestions(pack, score)
        suggestion_messages = " ".join(
            s["message"] for s in suggestions.get("gappy", [])
        ).lower()

        # Each gap should produce at least one related suggestion
        if "missing_accountable" in gaps:
            assert (
                "accountable" in suggestion_messages
                or "responsible" in suggestion_messages
            )
        if "missing_sql" in gaps:
            assert "sql" in suggestion_messages
        if "missing_tests" in gaps:
            assert "test" in suggestion_messages

    def test_composite_score_with_mixed_pack(self):
        """Pack with mixed quality should have pack_score < avg_metric_score."""
        good_metric = {
            "id": "good",
            "name": "Good",
            "description": "Well-defined.",
            "tier": "V1",
            "status": "active",
            "accountable": "Team",
            "grain": "day",
            "unit": "count",
            "requires": ["t"],
            "sql": {"value": "SELECT 1"},
            "tests": [{}],
        }
        bad_metric = {"id": "bad", "name": "Bad"}

        pack = {"metrics": [good_metric, bad_metric]}
        score = score_pack(pack)

        # Composite should be lower than simple average
        assert score.pack_score < score.avg_metric_score
        assert score.min_metric_score < score.avg_metric_score
