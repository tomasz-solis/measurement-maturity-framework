"""Schema-version detection and routing.

This is the single source of truth for deciding whether a pack is handled by
the v1 metric-readiness path or the v2 vertical-readiness path. See
docs/V2_SCHEMA.md ("Version routing").
"""

from __future__ import annotations

from typing import Any, Mapping

V1_SCHEMA = "1.0"
V2_SCHEMA = "2.0"


def detect_schema_version(pack: Mapping[str, Any]) -> str:
    """Return the declared ``pack.schema_version`` as a string, or "" if absent."""
    if not isinstance(pack, dict):
        return ""
    meta = pack.get("pack")
    if isinstance(meta, dict):
        version = meta.get("schema_version")
        if version:
            return str(version)
    return ""


def is_v2_pack(pack: Mapping[str, Any]) -> bool:
    """True when the pack opts into the v2 vertical schema."""
    return detect_schema_version(pack) == V2_SCHEMA


def is_known_schema(pack: Mapping[str, Any]) -> bool:
    """True when the declared schema version is one this build understands."""
    return detect_schema_version(pack) in {V1_SCHEMA, V2_SCHEMA}
