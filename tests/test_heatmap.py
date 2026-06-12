"""Tests for the cross-vertical heatmap HTML builder."""

from __future__ import annotations

from mmf.layout import data_table_html, heatmap_table_html


def test_structure_headers_and_tone_classes():
    html = heatmap_table_html(
        ["Onboarding", "Search"],
        [
            ("Overall readiness", [("Decision-ready", "good"), ("Fragile", "risk")]),
            ("Operating rhythm", [("Strong", "good"), ("Weak", "risk")]),
        ],
    )
    assert 'class="mmf-heatmap"' in html
    # Verticals are the columns.
    assert "<th>Onboarding</th>" in html and "<th>Search</th>" in html
    # Dimensions are the rows.
    assert "<th>Operating rhythm</th>" in html
    # Tones map to colour classes.
    assert "mmf-hm-good" in html and "mmf-hm-risk" in html


def test_escapes_text_and_defaults_unknown_tone():
    html = heatmap_table_html(["<x>"], [("row&", [("v", "bogus")])])
    assert "&lt;x&gt;" in html  # header escaped
    assert "row&amp;" in html  # row label escaped
    assert "mmf-hm-none" in html  # unknown tone falls back to grey


def test_is_deterministic():
    args = (
        ["A", "B"],
        [("Overall readiness", [("Decision-ready", "good"), ("Fragile", "risk")])],
    )
    assert heatmap_table_html(*args) == heatmap_table_html(*args)


def test_data_table_plain_and_chip_cells():
    html = data_table_html(
        [
            {"Metric": "Activation", "Signal": ("Good", "good")},
            {"Metric": "Latency", "Signal": ("Risk", "risk")},
        ]
    )
    assert 'class="mmf-table"' in html
    assert "<th>Metric</th>" in html and "<th>Signal</th>" in html
    assert "mmf-tag mmf-tag-good" in html and "mmf-tag-risk" in html
    assert "Activation" in html


def test_data_table_escapes_and_defaults_unknown_tone():
    html = data_table_html([{"A": "<b>", "S": ("x", "bogus")}])
    assert "&lt;b&gt;" in html
    assert "mmf-tag-none" in html  # unknown tone falls back to grey


def test_data_table_empty():
    assert "No rows." in data_table_html([])
