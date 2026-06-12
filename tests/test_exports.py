"""Tests for deterministic exports (PRD FR10)."""

from __future__ import annotations

import csv
import io
import json
import os

import yaml

from mmf.exports import (
    export_all,
    metric_readiness_to_csv,
    validation_to_json,
    vertical_score_to_csv,
)
from mmf.scoring import score_pack
from mmf.validator import validate_metric_pack
from mmf.vertical_scoring import score_vertical

EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples")


def _load(name):
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


PACK = "search_decision_gap.yaml"


def test_validation_json_is_valid_json():
    res = validate_metric_pack(_load(PACK))
    payload = json.loads(validation_to_json(res))
    assert "ok" in payload and "issues" in payload
    assert payload["issue_count"] == len(payload["issues"])


def test_metric_readiness_csv_has_row_per_metric():
    pack = _load(PACK)
    csv_text = metric_readiness_to_csv(score_pack(pack), pack)
    rows = list(csv.reader(io.StringIO(csv_text)))
    header, data = rows[0], rows[1:]
    assert header[0] == "id" and "role" in header and "linked_decisions" in header
    assert len(data) == len([m for m in pack["metrics"] if isinstance(m, dict)])
    # Role column is populated from the pack (v2 enrichment).
    assert any(r[header.index("role")] for r in data)


def test_vertical_csv_has_overall_and_dimensions():
    pack = _load(PACK)
    csv_text = vertical_score_to_csv(score_vertical(pack))
    rows = list(csv.reader(io.StringIO(csv_text)))
    names = [r[0] for r in rows]
    assert "(overall)" in names
    assert "Decision coverage & linkage" in names
    # The overall row carries the band.
    overall = next(r for r in rows if r[0] == "(overall)")
    assert overall[1] == "Fragile"


def test_export_all_returns_four_artifacts():
    pack = _load(PACK)
    bundle = export_all(
        pack,
        validate_metric_pack(pack),
        score_pack(pack),
        score_vertical(pack),
    )
    assert set(bundle) == {
        "validation.json",
        "metric_readiness.csv",
        "vertical_score.csv",
        "brief.md",
    }
    assert bundle["brief.md"].startswith("# Measurement Readiness Brief:")


def test_exports_are_deterministic():
    pack = _load(PACK)
    a = export_all(
        pack, validate_metric_pack(pack), score_pack(pack), score_vertical(pack)
    )
    b = export_all(
        pack, validate_metric_pack(pack), score_pack(pack), score_vertical(pack)
    )
    assert a == b


def test_exports_use_lf_newlines_only():
    # Portable, deterministic line endings (no platform CRLF leakage).
    pack = _load(PACK)
    csv_text = vertical_score_to_csv(score_vertical(pack))
    assert "\r" not in csv_text


def test_cross_vertical_matrix_csv():
    from mmf.cross_vertical import compare_verticals
    from mmf.exports import cross_vertical_matrix_to_csv

    names = [
        "onboarding_measurement_ready.yaml",
        "collaboration_portfolio_design.yaml",
        "search_decision_gap.yaml",
        "reporting_operating_gap.yaml",
    ]
    view = compare_verticals([(n, _load(n)) for n in names])
    rows = list(csv.reader(io.StringIO(cross_vertical_matrix_to_csv(view))))
    header, data = rows[0], rows[1:]
    assert header[:4] == [
        "vertical",
        "overall_band",
        "decisions_ready",
        "decisions_total",
    ]
    assert "Operating rhythm" in header
    assert len(data) == 4  # one row per vertical


def test_cross_vertical_shared_gaps_csv():
    from mmf.cross_vertical import compare_verticals
    from mmf.exports import cross_vertical_shared_gaps_to_csv

    names = [
        "search_decision_gap.yaml",
        "reporting_operating_gap.yaml",
    ]
    view = compare_verticals([(n, _load(n)) for n in names])
    rows = list(csv.reader(io.StringIO(cross_vertical_shared_gaps_to_csv(view))))
    header, data = rows[0], rows[1:]
    assert header == ["dimension", "weak_in", "partial_in", "verticals_weak"]
    # Operating rhythm is weak in both verticals here.
    op = next(r for r in data if r[0] == "Operating rhythm")
    assert op[1] == "2"
