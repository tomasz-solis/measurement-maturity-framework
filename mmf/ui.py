"""Compatibility layer for UI helpers used by the Streamlit app.

The UI code was split into smaller modules, but the app still imports
symbols from ``mmf.ui``. This module keeps that import path stable while
re-exporting the public helpers from their new homes.
"""

from __future__ import annotations

from .components import (
    issue_counts,
    render_sidebar_intro,
    score_signal,
    severity_rank,
    suggestion_group_icon,
    validation_signal,
)
from .layout import (
    inject_theme_css,
    render_empty_state_cards,
    render_footer,
    render_hero,
    render_section_header,
    render_stat_card_row,
    stat_card_html,
    threshold_band_html,
)
from .sidebar import (
    load_sidebar_examples,
    load_sidebar_downloads,
    render_normalized_download,
    render_sidebar_examples,
    render_sidebar_downloads,
)

__all__ = [
    "inject_theme_css",
    "issue_counts",
    "load_sidebar_examples",
    "load_sidebar_downloads",
    "render_empty_state_cards",
    "render_footer",
    "render_hero",
    "render_normalized_download",
    "render_section_header",
    "render_sidebar_examples",
    "render_sidebar_downloads",
    "render_sidebar_intro",
    "render_stat_card_row",
    "score_signal",
    "severity_rank",
    "stat_card_html",
    "suggestion_group_icon",
    "threshold_band_html",
    "validation_signal",
]
