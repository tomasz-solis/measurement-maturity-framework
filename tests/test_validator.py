"""Tests for mmf.validator module."""
import pytest
import yaml
from pathlib import Path

from mmf.validator import validate_metric_pack, ValidationIssue, ValidationResult


# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(filename: str) -> dict:
    """Load a YAML fixture file."""
    with open(FIXTURES_DIR / filename) as f:
        return yaml.safe_load(f)


class TestValidatorBasic:
    """Basic validation tests."""

    def test_minimal_pack_validates(self):
        """A minimal but complete pack should validate successfully."""
        pack = load_fixture("minimal_pack.yaml")
        result = validate_metric_pack(pack)

        assert result.ok is True
        assert isinstance(result.issues, list)
        # May have INFO issues but no ERRORS
        errors = [i for i in result.issues if i.severity == "ERROR"]
        assert len(errors) == 0

    def test_empty_pack_validates(self):
        """Pack with no metrics should validate (edge case)."""
        pack = load_fixture("empty_pack.yaml")
        result = validate_metric_pack(pack)

        # Empty pack is technically valid
        assert result.ok is True

    def test_invalid_pack_fails(self):
        """Pack missing 'metrics' field should fail validation."""
        pack = load_fixture("invalid_pack.yaml")
        result = validate_metric_pack(pack)

        assert result.ok is False
        errors = [i for i in result.issues if i.severity == "ERROR"]
        assert len(errors) > 0
        assert any("metrics" in i.message.lower() for i in errors)

    def test_non_dict_pack_fails(self):
        """Non-dictionary input should fail validation."""
        result = validate_metric_pack("not a dict")

        assert result.ok is False
        assert len(result.issues) == 1
        assert result.issues[0].severity == "ERROR"
        assert "mapping" in result.issues[0].message.lower()


class TestMetricValidation:
    """Tests for individual metric validation."""

    def test_missing_metric_id(self):
        """Metric without ID should produce error."""
        pack = {
            "metrics": [
                {"name": "Test Metric"}  # Missing 'id'
            ]
        }
        result = validate_metric_pack(pack)

        assert result.ok is False
        errors = [i for i in result.issues if i.severity == "ERROR"]
        assert any("id" in i.message.lower() for i in errors)

    def test_missing_metric_name(self):
        """Metric without name should produce error."""
        pack = {
            "metrics": [
                {"id": "test_metric"}  # Missing 'name'
            ]
        }
        result = validate_metric_pack(pack)

        assert result.ok is False
        errors = [i for i in result.issues if i.severity == "ERROR"]
        assert any("name" in i.message.lower() for i in errors)

    def test_duplicate_metric_ids(self):
        """Duplicate metric IDs should produce error."""
        pack = {
            "metrics": [
                {"id": "duplicate", "name": "Metric 1"},
                {"id": "duplicate", "name": "Metric 2"},
            ]
        }
        result = validate_metric_pack(pack)

        assert result.ok is False
        errors = [i for i in result.issues if i.severity == "ERROR"]
        assert any("duplicate" in i.message.lower() for i in errors)

    def test_missing_accountable_warns(self):
        """Missing 'accountable' field should produce warning."""
        pack = {
            "metrics": [
                {"id": "test", "name": "Test"}  # Missing 'accountable'
            ]
        }
        result = validate_metric_pack(pack)

        # Should pass but with warnings
        assert result.ok is True
        warnings = [i for i in result.issues if i.severity == "WARNING"]
        assert any("accountable" in i.message.lower() for i in warnings)

    def test_missing_sql_warns(self):
        """Missing SQL should produce warning."""
        pack = {
            "metrics": [
                {"id": "test", "name": "Test"}  # No SQL
            ]
        }
        result = validate_metric_pack(pack)

        warnings = [i for i in result.issues if i.severity == "WARNING"]
        assert any("sql" in i.message.lower() for i in warnings)

    def test_missing_tests_warns(self):
        """Missing tests should produce warning."""
        pack = {
            "metrics": [
                {"id": "test", "name": "Test"}  # No tests
            ]
        }
        result = validate_metric_pack(pack)

        warnings = [i for i in result.issues if i.severity == "WARNING"]
        assert any("tests" in i.message.lower() for i in warnings)


class TestSchemaVersioning:
    """Tests for schema version checking."""

    def test_missing_schema_version_info(self):
        """Missing schema_version should produce INFO message."""
        pack = {
            "pack": {"id": "test", "name": "Test"},
            "metrics": []
        }
        result = validate_metric_pack(pack)

        infos = [i for i in result.issues if i.severity == "INFO"]
        assert any("schema_version" in i.message.lower() for i in infos)

    def test_valid_schema_version_no_warning(self):
        """Valid schema_version should not produce warning."""
        pack = {
            "pack": {"id": "test", "name": "Test", "schema_version": "1.0"},
            "metrics": []
        }
        result = validate_metric_pack(pack)

        schema_warnings = [i for i in result.issues
                          if "schema_version" in i.message.lower()
                          and i.severity == "WARNING"]
        assert len(schema_warnings) == 0

    def test_unknown_schema_version_warns(self):
        """Unknown schema_version should produce warning."""
        pack = {
            "pack": {"id": "test", "name": "Test", "schema_version": "99.0"},
            "metrics": []
        }
        result = validate_metric_pack(pack)

        warnings = [i for i in result.issues if i.severity == "WARNING"]
        assert any("schema version" in i.message.lower() and "not recognized" in i.message.lower()
                  for i in warnings)


class TestSQLValidation:
    """Tests for SQL field validation."""

    def test_value_sql_valid(self):
        """Metric with 'value' SQL should not warn about missing SQL."""
        pack = {
            "metrics": [
                {
                    "id": "test",
                    "name": "Test",
                    "sql": {"value": "SELECT COUNT(*) FROM table"}
                }
            ]
        }
        result = validate_metric_pack(pack)

        sql_warnings = [i for i in result.issues
                       if "sql" in i.message.lower()
                       and i.severity == "WARNING"]
        assert len(sql_warnings) == 0

    def test_ratio_sql_valid(self):
        """Metric with numerator/denominator SQL should not warn."""
        pack = {
            "metrics": [
                {
                    "id": "test",
                    "name": "Test",
                    "sql": {
                        "numerator": "SELECT COUNT(*) FROM success",
                        "denominator": "SELECT COUNT(*) FROM total"
                    }
                }
            ]
        }
        result = validate_metric_pack(pack)

        sql_warnings = [i for i in result.issues
                       if "sql" in i.message.lower()
                       and i.severity == "WARNING"]
        assert len(sql_warnings) == 0

    def test_partial_ratio_sql_warns(self):
        """Metric with only numerator should warn about missing SQL."""
        pack = {
            "metrics": [
                {
                    "id": "test",
                    "name": "Test",
                    "sql": {"numerator": "SELECT COUNT(*) FROM success"}
                    # Missing denominator
                }
            ]
        }
        result = validate_metric_pack(pack)

        sql_warnings = [i for i in result.issues
                       if "sql" in i.message.lower()
                       and i.severity == "WARNING"]
        assert len(sql_warnings) > 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_metric_not_dict(self):
        """Non-dict metric should be skipped gracefully."""
        pack = {
            "metrics": [
                "not a dict",
                {"id": "valid", "name": "Valid Metric"}
            ]
        }
        result = validate_metric_pack(pack)

        # Should validate the valid metric
        assert len(result.issues) > 0  # Will have warnings for missing fields on valid metric

    def test_very_long_metric_list(self):
        """Large number of metrics should not crash."""
        pack = {
            "metrics": [
                {"id": f"metric_{i}", "name": f"Metric {i}"}
                for i in range(1000)
            ]
        }
        result = validate_metric_pack(pack)

        # Should complete without error
        assert result is not None
        assert isinstance(result.issues, list)

    def test_unicode_in_names(self):
        """Unicode characters should be handled correctly."""
        pack = {
            "metrics": [
                {"id": "test", "name": "Test Metric 测试 🚀"}
            ]
        }
        result = validate_metric_pack(pack)

        # Should not crash
        assert result is not None

    def test_empty_strings(self):
        """Empty strings for required fields should fail."""
        pack = {
            "metrics": [
                {"id": "", "name": ""}
            ]
        }
        result = validate_metric_pack(pack)

        # Empty ID is treated as missing
        errors = [i for i in result.issues if i.severity == "ERROR"]
        assert len(errors) > 0
