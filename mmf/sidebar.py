"""Sidebar logic: example discovery and download buttons.

These helpers are separated from the main render loop so the sidebar
setup can be tested and reasoned about independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import streamlit as st

from .streamlit_compat import render_download_button


@dataclass(frozen=True)
class SidebarExample:
    """Represent one example pack that can be downloaded from the sidebar."""

    label: str
    file_name: str
    content: bytes
    description: str


_EXAMPLE_METADATA: dict[str, tuple[str, str]] = {
    "generic_product_metric_pack.yaml": (
        "Generic product example",
        "A full reference pack spanning adoption, engagement, outcome, reliability, and support.",
    ),
    "mixed_maturity_pack.yaml": (
        "Mixed maturity example",
        "Shows how one weaker V0 metric can drag a mostly strong pack downward.",
    ),
    "spreadsheet_pipeline_pack.yaml": (
        "Spreadsheet pipeline example",
        "Highlights the structural SQL gap for metrics that still depend on spreadsheet pipelines.",
    ),
}
_PREFERRED_EXAMPLE_ORDER = tuple(_EXAMPLE_METADATA)


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


def _example_sort_key(path: Path) -> tuple[int, str]:
    """Return a stable sort key that keeps the most useful examples first."""
    try:
        return (_PREFERRED_EXAMPLE_ORDER.index(path.name), path.name)
    except ValueError:
        return (len(_PREFERRED_EXAMPLE_ORDER), path.name)


def _example_label_and_description(file_name: str) -> tuple[str, str]:
    """Return sidebar copy for a known example pack, with a safe fallback."""
    if file_name in _EXAMPLE_METADATA:
        return _EXAMPLE_METADATA[file_name]

    stem = file_name.rsplit(".", 1)[0].replace("_", " ").strip()
    label = stem.title() or file_name
    description = "Example pack from ./examples."
    return label, description


def load_sidebar_examples() -> list[SidebarExample]:
    """Load the example packs that should be exposed in the sidebar."""
    root = repo_root()
    examples_dir = root / "examples"
    if not examples_dir.exists() or not examples_dir.is_dir():
        return []

    example_paths = sorted(
        [*examples_dir.glob("*.yaml"), *examples_dir.glob("*.yml")],
        key=_example_sort_key,
    )

    examples: list[SidebarExample] = []
    for path in example_paths:
        text = read_text_if_exists(path)
        if text is None:
            continue

        label, description = _example_label_and_description(path.name)
        examples.append(
            SidebarExample(
                label=label,
                file_name=path.name,
                content=text.encode("utf-8"),
                description=description,
            )
        )

    return examples


def render_sidebar_examples(examples: Sequence[SidebarExample]) -> None:
    """Render the sidebar section that exposes downloadable example packs."""
    st.markdown("---")
    st.subheader("Example Packs")

    if not examples:
        st.markdown(
            (
                '<p class="mmf-sidebar-note">'
                "No example packs found in ./examples "
                "(add one there to expose it in the app)."
                "</p>"
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            (
                '<p class="mmf-sidebar-note">'
                "Download one of the repo examples, then upload it here or adapt it locally."
                "</p>"
            ),
            unsafe_allow_html=True,
        )
        for example in examples:
            render_download_button(
                label=f"Download {example.label}",
                data=example.content,
                file_name=example.file_name,
                mime="text/yaml",
            )
            st.markdown(
                f'<p class="mmf-sidebar-example-copy">{example.description}</p>',
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown(
        (
            '<p class="mmf-sidebar-tip">'
            "Tip: keep IDs stable. It makes change tracking much easier later."
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


def load_sidebar_downloads() -> list[SidebarExample]:
    """Backward-compatible alias for loading sidebar examples."""
    return load_sidebar_examples()


def render_sidebar_downloads(examples: Sequence[SidebarExample]) -> None:
    """Backward-compatible alias for rendering sidebar examples."""
    render_sidebar_examples(examples)
