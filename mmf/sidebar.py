"""Sidebar logic: file discovery, template loading, and download buttons.

These helpers are separated from the main render loop so the sidebar
setup can be tested and reasoned about independently.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st
import yaml  # type: ignore[import-untyped]

from .streamlit_compat import render_download_button


def repo_root() -> Path:
    """Return the repository root directory for template and example lookup.

    app.py lives at the repo root, so its parent is the anchor.
    sidebar.py lives in ``mmf/``, so we walk up one level from that
    package directory to reach the repository root.
    """
    return Path(__file__).resolve().parent.parent


def read_text_if_exists(path: Path) -> Optional[str]:
    """Read a UTF-8 text file and return its contents, or None if absent."""
    try:
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8")
    except Exception:
        return None
    return None


def find_first_yaml_in_dir(dir_path: Path) -> Optional[Path]:
    """Return the first YAML file found in a directory, sorted alphabetically."""
    if not dir_path.exists() or not dir_path.is_dir():
        return None
    candidates = sorted(list(dir_path.glob("*.yaml")) + list(dir_path.glob("*.yml")))
    return candidates[0] if candidates else None


def default_metric_template_yaml() -> str:
    """Return a built-in metric template when the repo template file is missing."""
    template: Dict[str, Any] = {
        "id": "my_metric_id",
        "name": "My metric name",
        "description": "One sentence on what this measures and why it matters.",
        "tier": "V0",
        "status": "active",
        "responsible": "Team / role",
        "unit": "count",
        "grain": "one row per ...",
        "requires": [],
        "sql": {},
        "tests": [],
    }
    return yaml.safe_dump(
        template,
        sort_keys=False,
        allow_unicode=True,
        width=100,
        default_flow_style=False,
    )


def load_sidebar_downloads() -> Dict[str, Optional[str]]:
    """Load downloadable templates and the preferred example pack.

    Returns a dict with keys:
      - metric_template: YAML string for the single-metric template
      - pack_template: YAML string for the full pack template (may be None)
      - example_pack: YAML string for the example pack (may be None)
      - example_pack_filename: filename for the example pack download
    """
    root = repo_root()

    template_path = root / "templates" / "metric_template.yaml"
    metric_template = (
        read_text_if_exists(template_path) or default_metric_template_yaml()
    )

    pack_template_path = root / "templates" / "metric_pack_template.yaml"
    pack_template = read_text_if_exists(pack_template_path)

    examples_dir = root / "examples"
    preferred = examples_dir / "generic_product_metric_pack.yaml"
    example_path = (
        preferred if preferred.exists() else find_first_yaml_in_dir(examples_dir)
    )
    example_pack = read_text_if_exists(example_path) if example_path else None

    return {
        "metric_template": metric_template,
        "pack_template": pack_template,
        "example_pack": example_pack,
        "example_pack_filename": example_path.name if example_path else None,
    }


def render_sidebar_downloads(dl: Dict[str, Optional[str]]) -> None:
    """Render the static download buttons (templates, example pack)."""
    st.markdown("---")
    st.subheader("Downloads")

    render_download_button(
        label="Download metric template (YAML)",
        data=(dl["metric_template"] or "").encode("utf-8"),
        file_name="metric_template.yaml",
        mime="text/yaml",
    )

    pack_template = dl.get("pack_template")
    if pack_template:
        render_download_button(
            label="Download pack template (YAML)",
            data=pack_template.encode("utf-8"),
            file_name="metric_pack_template.yaml",
            mime="text/yaml",
        )
    else:
        st.caption(
            "No pack template found in ./templates "
            "(add templates/metric_pack_template.yaml to enable this download)."
        )

    example_pack = dl.get("example_pack")
    if example_pack:
        render_download_button(
            label="Download example pack (YAML)",
            data=example_pack.encode("utf-8"),
            file_name=dl["example_pack_filename"] or "example_metric_pack.yaml",
            mime="text/yaml",
        )
    else:
        st.caption(
            "No example pack found in ./examples " "(add one to enable this download)."
        )

    st.markdown("---")
    st.markdown(
        (
            '<p class="mmf-sidebar-tip">'
            "Tip: keep IDs stable. It makes trends and governance easier later."
            "</p>"
        ),
        unsafe_allow_html=True,
    )


def render_normalized_download(normalized_yaml_text: str) -> None:
    """Render the post-upload normalized YAML download button."""
    render_download_button(
        label="Download normalized YAML",
        data=normalized_yaml_text.encode("utf-8"),
        file_name="normalized_metric_pack.yaml",
        mime="text/yaml",
    )
