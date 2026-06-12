"""Tests for v2 vertical-pack validation."""

from __future__ import annotations

import copy
import os

import yaml

from mmf.vertical_validator import validate_vertical_pack

EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples")


def _load(name):
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _codes(result):
    return {i.code for i in result.issues}


def test_healthy_pack_validates_clean():
    res = validate_vertical_pack(_load("onboarding_measurement_ready.yaml"))
    assert res.ok
    # No broken references and no missing roles in a healthy pack.
    assert not any(c.startswith("broken_") for c in _codes(res))
    assert "metric_missing_role" not in _codes(res)


def test_missing_role_is_flagged():
    res = validate_vertical_pack(_load("collaboration_portfolio_design.yaml"))
    assert res.ok  # missing role is a warning, not an error
    assert "metric_missing_role" in _codes(res)


def test_dangling_required_metric_is_flagged_but_not_blocking():
    res = validate_vertical_pack(_load("search_decision_gap.yaml"))
    # The undefined query_understanding_score reference is detected...
    assert "broken_required_metric_reference" in _codes(res)
    # ...but it is a warning: the pack is still structurally valid.
    assert res.ok


def test_missing_vertical_id_is_error():
    pack = _load("onboarding_measurement_ready.yaml")
    del pack["vertical"]["id"]
    res = validate_vertical_pack(pack)
    assert not res.ok
    assert "missing_vertical_id" in _codes(res)


def test_duplicate_decision_id_is_error():
    pack = _load("onboarding_measurement_ready.yaml")
    dup = copy.deepcopy(pack["decisions"][0])
    pack["decisions"].append(dup)
    res = validate_vertical_pack(pack)
    assert not res.ok
    assert "duplicate_decision_id" in _codes(res)


def test_internal_reference_leak_in_public_sample_is_flagged():
    pack = _load("onboarding_measurement_ready.yaml")
    pack["internal_references"]["dashboard_url"] = "https://example.internal/dash"
    res = validate_vertical_pack(pack)
    assert "internal_reference_in_public_sample" in _codes(res)


def test_v1_only_noise_is_suppressed():
    # v2 packs should not be told to add `requires` or warned about schema "2.0".
    res = validate_vertical_pack(_load("onboarding_measurement_ready.yaml"))
    assert "metric_requires_missing" not in _codes(res)
    assert "unknown_schema_version" not in _codes(res)
