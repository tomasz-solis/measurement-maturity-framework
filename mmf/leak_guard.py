"""Location-aware leak guard for committed public packs.

The vertical validator flags an ``internal_references`` leak as a warning while
reviewing a single pack. This module enforces the stronger, location-aware rule
used in CI (PRD FR12): any pack committed under the public ``examples/`` tree
must be a public sample with no private data. A private pack is perfectly valid
locally; it just must never be committed to the public repo.

The check logic lives here (importable, testable); ``scripts/check_public_packs.py``
is the thin CLI that CI runs.
"""

from __future__ import annotations

import glob
from typing import Any, Dict, List, Mapping

import yaml

DEFAULT_GLOBS = ["examples/**/*.yaml", "examples/**/*.yml"]


def scan_pack(pack: Mapping[str, Any]) -> List[str]:
    """Return a list of leak problems for one parsed pack (empty if clean)."""
    problems: List[str] = []
    _meta = pack.get("pack")
    meta: Dict[str, Any] = _meta if isinstance(_meta, dict) else {}
    visibility = meta.get("visibility")

    if visibility == "private":
        problems.append(
            "visibility is 'private' (private packs must not be committed to the public repo)"
        )

    refs = pack.get("internal_references")
    if isinstance(refs, dict):
        non_null = sorted(k for k, v in refs.items() if v is not None)
        if non_null:
            problems.append(
                "internal_references has non-null values: " + ", ".join(non_null)
            )
    return problems


def scan_file(path: str) -> List[str]:
    """Parse a YAML file and scan it; parse failures are reported as problems."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception as exc:  # noqa: BLE001 - surface any parse error as a problem
        return [f"could not parse: {exc}"]
    if not isinstance(data, dict):
        return []
    return scan_pack(data)


def scan_paths(globs: List[str]) -> Dict[str, List[str]]:
    """Scan every file matching the globs; return {path: problems} for offenders."""
    violations: Dict[str, List[str]] = {}
    for pattern in globs:
        for path in sorted(glob.glob(pattern, recursive=True)):
            problems = scan_file(path)
            if problems:
                violations[path] = problems
    return violations
