"""HTML/CSS layout helpers for the MMF Streamlit app.

All functions here produce HTML or inject CSS. None of them depend on
Streamlit session state or uploaded data — they only take plain Python
arguments and call st.markdown / st.write.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import List, Optional

import streamlit as st

_THEME_CSS_PATH = Path(__file__).parent / "theme.css"


def inject_theme_css() -> None:
    """Inject the main app theme from theme.css into the Streamlit page."""
    try:
        css = _THEME_CSS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        css = ""  # Degrade gracefully if the file is missing

    st.markdown(f"<style>\n{css}\n</style>", unsafe_allow_html=True)


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
            f'<div class="mmf-card-row" style="--mmf-card-cols: {card_columns};">'
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
            "Clear definition, ownership, and guardrails are in place.",
        ),
        (
            "Usable with caution",
            f"{int(t_caution)}-{int(t_ready - 1)}",
            "Useful, but still carrying enough structural risk to review closely.",
        ),
        (
            "Early/fragile",
            f"{int(t_early)}-{int(t_caution - 1)}",
            "Helpful for exploration, but still too fragile for strong commitments.",
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


def render_empty_state_cards() -> None:
    """Render the three explainer cards shown before any pack is uploaded."""
    st.markdown(
        """
        <div class="mmf-empty-grid">
          <div class="mmf-empty-card">
            <div class="index">Signal 01</div>
            <h3>Validate the structure first</h3>
            <p>Check ownership, definitions, SQL shape, and tests before the pack
               becomes a dashboard dependency.</p>
          </div>
          <div class="mmf-empty-card">
            <div class="index">Signal 02</div>
            <h3>Score decision risk, not performance</h3>
            <p>The framework measures how safe a metric is to use, not whether the
               business is doing well.</p>
          </div>
          <div class="mmf-empty-card">
            <div class="index">Signal 03</div>
            <h3>See the strategy chain</h3>
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
