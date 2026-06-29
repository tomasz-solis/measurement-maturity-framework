"""HTML/CSS layout helpers for the MMF Streamlit app.

All functions here produce HTML or inject CSS. None of them depend on
Streamlit session state or uploaded data - they only take plain Python
arguments and call st.markdown / st.write.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

_THEME_CSS_PATH = Path(__file__).parent / "theme.css"
_THEME_TOKENS_PATH = Path(__file__).parent / "theme-tokens.css"


def inject_theme_css() -> None:
    """Inject the shared design tokens, then the main app theme from theme.css."""
    try:
        tokens = _THEME_TOKENS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        tokens = ""  # Degrade gracefully if the file is missing
    try:
        css = _THEME_CSS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        css = ""  # Degrade gracefully if the file is missing

    st.markdown(f"<style>\n{tokens}\n{css}\n</style>", unsafe_allow_html=True)


def render_hero(title: str, subtitle: str, pills: List[str]) -> None:
    """Render the main page hero section with an optional row of pill badges."""
    pill_markup = []
    for index, pill in enumerate(pills):
        accent_class = " mmf-pill--accent" if index == 0 else ""
        pill_markup.append(
            f'<span class="mmf-pill{accent_class}">{escape(str(pill))}</span>'
        )

    st.markdown(
        f"""
        <section class="mmf-hero">
          <div class="mmf-kicker">Measurement Maturity Framework</div>
          <h1>{escape(title)}</h1>
          <p>{escape(subtitle)}</p>
          <div class="mmf-pill-row">{''.join(pill_markup)}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(label: str, title: str, description: str) -> None:
    """Render a section header with an editorial signal label."""
    st.markdown(
        f"""
        <div class="mmf-section-head">
          <div class="label">{escape(label)}</div>
          <h2>{escape(title)}</h2>
          <p>{escape(description)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_card_html(
    eyebrow: str,
    value: str,
    body: str,
    *,
    tone: str = "accent",
    dark: bool = False,
) -> str:
    """Return the HTML string for a single summary stat card.

    Cards are assembled into a row with ``render_stat_card_row``.
    """
    classes = ["mmf-grid-card", f"mmf-tone-{tone}"]
    if dark:
        classes.append("mmf-grid-card--dark")

    return (
        f'<div class="{" ".join(classes)}">'
        f'<div class="eyebrow">{escape(eyebrow)}</div>'
        f'<div class="value">{escape(value)}</div>'
        f'<div class="body">{escape(body)}</div>'
        "</div>"
    )


def render_stat_card_row(cards: List[str], columns: Optional[int] = None) -> None:
    """Render a horizontal row of stat card HTML strings."""
    card_columns = columns or len(cards) or 1
    st.markdown(
        (
            f'<div class="mmf-card-row mmf-cols-{card_columns}">'
            f'{"".join(cards)}'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def threshold_band_html(
    t_ready: float,
    t_caution: float,
    t_early: float,
    pack_label: str,
) -> str:
    """Return the threshold band markup for the scoring section.

    The active band is highlighted based on ``pack_label``.
    """
    thresholds = [
        (
            "Decision-ready",
            f"{int(t_ready)}-100",
            "Clear definition, ownership, and basic guardrails are in place.",
        ),
        (
            "Usable with caution",
            f"{int(t_caution)}-{int(t_ready - 1)}",
            "Useful, but still carrying enough structural risk to review closely.",
        ),
        (
            "Early/fragile",
            f"{int(t_early)}-{int(t_caution - 1)}",
            "Useful for exploration, but still too fragile for strong commitments.",
        ),
        (
            "Not safe for decisions",
            f"0-{int(t_early - 1)}",
            "Definition gaps dominate. Fix the basics before relying on it.",
        ),
    ]

    parts = ['<div class="mmf-threshold-band">']
    for label, range_label, description in thresholds:
        active_class = " is-active" if label == pack_label else ""
        parts.append(
            f'<div class="mmf-threshold{active_class}">'
            f"<strong>{escape(label)}</strong>"
            f"<span>{escape(range_label)} · {escape(description)}</span>"
            "</div>"
        )
    parts.append("</div>")
    return "".join(parts)


def heatmap_table_html(
    column_headers: List[str],
    rows: List[Tuple[str, List[Tuple[str, str]]]],
) -> str:
    """Return an HTML heatmap table.

    ``column_headers`` are the column labels (e.g. vertical names). Each row is
    ``(row_label, cells)`` where each cell is ``(text, tone)`` and ``tone`` is one
    of ``good`` | ``watch`` | ``risk`` | ``none`` (green / amber / red / grey).
    Verticals are columns and dimensions are rows, so the table reads top to
    bottom and stays narrow.
    """
    valid_tones = {"good", "watch", "risk", "none"}
    head = "".join(f"<th>{escape(str(h))}</th>" for h in column_headers)
    thead = f'<thead><tr><th class="mmf-hm-corner"></th>{head}</tr></thead>'

    body_rows: List[str] = []
    for label, cells in rows:
        tds = []
        for text, tone in cells:
            cls = tone if tone in valid_tones else "none"
            tds.append(f'<td class="mmf-hm-{cls}">{escape(str(text))}</td>')
        body_rows.append(f"<tr><th>{escape(str(label))}</th>{''.join(tds)}</tr>")
    tbody = f"<tbody>{''.join(body_rows)}</tbody>"

    return (
        '<div class="mmf-heatmap-wrap">'
        f'<table class="mmf-heatmap">{thead}{tbody}</table>'
        "</div>"
    )


def data_table_html(rows: List[Dict[str, Any]]) -> str:
    """Return a light, card-styled HTML table matching the app design.

    ``rows`` is a list of dicts; the first row's keys become the column headers
    (in order). A cell value may be a plain value, or a ``(text, tone)`` tuple to
    render a coloured status chip, where ``tone`` is one of
    ``good`` | ``watch`` | ``alarm`` | ``risk`` | ``accent`` | ``none``.

    Using one builder for every table keeps all tables visually consistent and
    high-contrast (dark text on a light surface), unlike the default grid.
    """
    if not rows:
        return (
            '<div class="mmf-table-wrap"><table class="mmf-table">'
            "<tbody><tr><td>No rows.</td></tr></tbody></table></div>"
        )

    valid_tones = {"good", "watch", "alarm", "risk", "accent", "none"}
    headers = list(rows[0].keys())
    head = "".join(f"<th>{escape(str(h))}</th>" for h in headers)
    thead = f"<thead><tr>{head}</tr></thead>"

    body_rows: List[str] = []
    for row in rows:
        cells = []
        for header in headers:
            value = row.get(header, "")
            if isinstance(value, tuple) and len(value) == 2:
                text, tone = value
                cls = tone if tone in valid_tones else "none"
                cells.append(
                    f'<td><span class="mmf-tag mmf-tag-{cls}">'
                    f"{escape(str(text))}</span></td>"
                )
            else:
                cells.append(f"<td>{escape(str(value))}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    tbody = f"<tbody>{''.join(body_rows)}</tbody>"

    return (
        '<div class="mmf-table-wrap">'
        f'<table class="mmf-table">{thead}{tbody}</table>'
        "</div>"
    )


def render_empty_state_cards() -> None:
    """Render the three explainer cards shown before any pack is uploaded."""
    st.markdown(
        """
        <div class="mmf-empty-grid">
          <div class="mmf-empty-card">
            <div class="index">Signal 01</div>
            <h3>Check the structure first</h3>
            <p>Review ownership, definitions, SQL shape, and tests before the pack
               turns into a dashboard dependency.</p>
          </div>
          <div class="mmf-empty-card">
            <div class="index">Signal 02</div>
            <h3>Score decision risk, not performance</h3>
            <p>The framework measures how safe a metric is to use, not whether the
               business is doing well.</p>
          </div>
          <div class="mmf-empty-card">
            <div class="index">Signal 03</div>
            <h3>See the strategy path</h3>
            <p>Map how local metrics roll up into levers and business goals so
               weak links stay visible.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer(footer_text: str) -> None:
    """Render the page footer note."""
    st.markdown(
        f'<p class="mmf-footer">{escape(footer_text)}</p>', unsafe_allow_html=True
    )
