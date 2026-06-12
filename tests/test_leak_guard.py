"""Tests for the public-pack leak guard (PRD FR12)."""

from __future__ import annotations

import os

from mmf.leak_guard import DEFAULT_GLOBS, scan_pack, scan_paths

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))


def test_clean_public_sample_has_no_problems():
    pack = {
        "pack": {"id": "p", "visibility": "public_sample"},
        "internal_references": {"dashboard_url": None, "dbt_model": None},
    }
    assert scan_pack(pack) == []


def test_private_visibility_is_flagged():
    problems = scan_pack({"pack": {"id": "p", "visibility": "private"}})
    assert any("private" in p for p in problems)


def test_non_null_internal_reference_is_flagged():
    pack = {
        "pack": {"id": "p", "visibility": "public_sample"},
        "internal_references": {
            "dashboard_url": "https://internal/dash",
            "dbt_model": None,
        },
    }
    problems = scan_pack(pack)
    assert any("internal_references" in p and "dashboard_url" in p for p in problems)


def test_shipped_examples_pass_the_guard():
    # Our own committed sample packs must never trip the guard.
    globs = [os.path.join(REPO_ROOT, g) for g in DEFAULT_GLOBS]
    violations = scan_paths(globs)
    assert violations == {}, f"committed packs leak private data: {violations}"
