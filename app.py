# app.py
from __future__ import annotations

from dataclasses import asdict
from html import escape
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import streamlit as st
import yaml

from mmf.config import load_config
from mmf.validator import validate_metric_pack
from mmf.scoring import score_pack
from mmf.suggestions import deterministic_suggestions

APP_TITLE = "Measurement Maturity Framework — YAML Auditor"
FOOTER_TEXT = "Deterministic checks. No silent edits. Schema-valid ≠ decision-ready. Treat suggestions as a checklist, not a verdict."


# -----------------------------
# Mermaid integration (safe)
# -----------------------------


def _try_get_strategy_mermaid_builder() -> Optional[Callable[[Dict[str, Any]], str]]:
    """Return the Mermaid strategy builder when available."""
    try:
        from mmf.mermaid import build_strategy_mermaid  # type: ignore

        if callable(build_strategy_mermaid):
            return build_strategy_mermaid
    except Exception:
        return None
    return None


def _try_get_mermaid_renderer() -> Optional[Callable[..., None]]:
    """Return the Streamlit Mermaid renderer when available."""
    try:
        from mmf.streamlit_mermaid import render_mermaid  # type: ignore

        if callable(render_mermaid):
            return render_mermaid
    except Exception:
        return None
    return None


# -----------------------------
# YAML helpers
# -----------------------------


def _load_yaml_bytes(raw: bytes) -> Dict[str, Any]:
    """Load raw YAML bytes into a dictionary."""
    data = yaml.safe_load(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Top-level YAML must be a mapping (object).")
    return data


def _dump_yaml_text(obj: Any) -> str:
    """Dump a Python object to readable YAML."""
    # Stable, readable output (no key sorting)
    return yaml.safe_dump(
        obj,
        sort_keys=False,
        allow_unicode=True,
        width=100,
        default_flow_style=False,
    )


# -----------------------------
# Repo file discovery (template / examples)
# -----------------------------


def _repo_root() -> Path:
    """Return the repository root used for local file discovery."""
    # app.py is expected to live in repo root (or close enough).
    # We treat its parent as the root for template/examples lookup.
    return Path(__file__).resolve().parent


def _read_text_if_exists(path: Path) -> Optional[str]:
    """Read a UTF-8 text file when it exists, else return None."""
    try:
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8")
    except Exception:
        return None
    return None


def _find_first_yaml_in_dir(dir_path: Path) -> Optional[Path]:
    """Return the first YAML file in a directory, if any exist."""
    if not dir_path.exists() or not dir_path.is_dir():
        return None

    candidates = sorted(list(dir_path.glob("*.yaml")) + list(dir_path.glob("*.yml")))
    return candidates[0] if candidates else None


def _default_metric_template_yaml() -> str:
    """Return a built-in metric template when the repo template is missing."""
    # Minimal Option B template: enough to run scoring + suggestions, SQL/tests optional at V0.
    template = {
        "id": "my_metric_id",
        "name": "My metric name",
        "description": "One sentence on what this measures and why it matters.",
        "tier": "V0",  # V0 | V1 | V2 (your convention)
        "status": "active",  # active | draft | deprecated
        "responsible": "Team / role",
        "unit": "count",  # e.g. count | percent | currency | hours
        "grain": "one row per ...",  # e.g. user-day, account-week
        "requires": [
            # Optional: upstream tables/events
            # "warehouse.schema.table",
        ],
        "sql": {
            # Optional at V0. Add once stable.
            # Either provide "value" OR numerator+denominator.
            # "value": "SELECT ...",
            # "numerator": "SELECT ...",
            # "denominator": "SELECT ...",
        },
        "tests": [
            # Optional early. Add once teams rely on it.
            # {"type": "not_null", "field": "value"},
            # {"type": "range", "field": "value", "min": 0, "max": 100},
        ],
    }
    return _dump_yaml_text(template)


def _sidebar_downloads_base() -> Dict[str, Optional[str]]:
    """Load downloadable templates and the preferred example pack from the repo."""
    root = _repo_root()

    # Metric template: prefer repo file if present, else fallback.
    template_path = root / "templates" / "metric_template.yaml"
    metric_template = (
        _read_text_if_exists(template_path) or _default_metric_template_yaml()
    )

    pack_template_path = root / "templates" / "metric_pack_template.yaml"
    pack_template = _read_text_if_exists(pack_template_path)

    # Example pack: prefer the generic sample, else fall back to the first YAML file.
    examples_dir = root / "examples"
    preferred_example_path = examples_dir / "generic_product_metric_pack.yaml"
    example_path = (
        preferred_example_path
        if preferred_example_path.exists()
        else _find_first_yaml_in_dir(examples_dir)
    )
    example_pack = _read_text_if_exists(example_path) if example_path else None

    return {
        "metric_template": metric_template,
        "pack_template": pack_template,
        "example_pack": example_pack,
        "example_pack_filename": example_path.name if example_path else None,
    }


# -----------------------------
# Small UI helpers
# -----------------------------


def _severity_rank(sev: str) -> int:
    """Rank issue severities for stable sorting."""
    sev = (sev or "").upper()
    return {"ERROR": 0, "WARNING": 1, "INFO": 2}.get(sev, 9)


def _inject_theme_css() -> None:
    """Inject the main app theme."""
    st.markdown(
        """
        <style>
        :root {
          --mmf-bg: #eff2f7;
          --mmf-surface: rgba(255, 255, 255, 0.78);
          --mmf-surface-strong: #0d1015;
          --mmf-ink: #10131a;
          --mmf-muted: #646c79;
          --mmf-line: rgba(16, 19, 26, 0.08);
          --mmf-blue: #4f6dff;
          --mmf-mint: #1ecf9b;
          --mmf-amber: #d18a1f;
          --mmf-red: #dd5b52;
        }

        [data-testid="stAppViewContainer"] {
          background:
            radial-gradient(circle at 0% 0%, rgba(79, 109, 255, 0.14), transparent 28%),
            radial-gradient(circle at 100% 12%, rgba(30, 207, 155, 0.10), transparent 24%),
            linear-gradient(180deg, #f7f8fb 0%, var(--mmf-bg) 100%);
          color: var(--mmf-ink);
        }

        [data-testid="stHeader"] {
          background: transparent;
        }

        [data-testid="stToolbar"] {
          right: 1rem;
        }

        [data-testid="stMainBlockContainer"] {
          max-width: 1260px;
          padding-top: 2rem;
          padding-bottom: 4rem;
        }

        [data-testid="stSidebar"] {
          background:
            radial-gradient(circle at top left, rgba(79, 109, 255, 0.22), transparent 30%),
            linear-gradient(180deg, #0d1015 0%, #171b22 100%);
          border-right: 1px solid rgba(255, 255, 255, 0.08);
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li,
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong {
          color: rgba(248, 250, 255, 0.96);
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stCaption {
          color: rgba(233, 236, 244, 0.74) !important;
        }

        [data-testid="stSidebar"] [data-testid="stFileUploader"] {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.12);
          border-radius: 24px;
          padding: 0.6rem;
        }

        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
          background: linear-gradient(
            180deg,
            rgba(255, 255, 255, 0.10) 0%,
            rgba(255, 255, 255, 0.05) 100%
          ) !important;
          border: 1px dashed rgba(255, 255, 255, 0.18) !important;
          border-radius: 22px !important;
        }

        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {
          color: rgba(243, 247, 255, 0.84) !important;
        }

        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
          background: rgba(255, 255, 255, 0.10) !important;
          color: #f8fbff !important;
          border: 1px solid rgba(255, 255, 255, 0.16) !important;
          border-radius: 999px !important;
        }

        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] span,
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] small {
          color: rgba(230, 235, 245, 0.66) !important;
        }

        [data-testid="stSidebar"] .stDownloadButton > button {
          background: rgba(255, 255, 255, 0.08);
          color: #f8fbff;
          border: 1px solid rgba(255, 255, 255, 0.12);
          border-radius: 999px;
          min-height: 3rem;
          font-weight: 650;
          transition: transform 0.15s ease, background 0.15s ease, border-color 0.15s ease;
        }

        [data-testid="stSidebar"] .stDownloadButton > button:hover {
          transform: translateY(-1px);
          background: rgba(255, 255, 255, 0.14);
          border-color: rgba(255, 255, 255, 0.18);
        }

        .mmf-sidebar-brand {
          padding: 0.5rem 0 1.1rem;
          margin-bottom: 0.6rem;
        }

        .mmf-sidebar-brand .kicker {
          font-size: 0.74rem;
          text-transform: uppercase;
          letter-spacing: 0.2em;
          color: rgba(240, 244, 255, 0.6);
          margin-bottom: 0.45rem;
          font-weight: 700;
        }

        .mmf-sidebar-brand h2 {
          margin: 0;
          font-size: 1.45rem;
          line-height: 1.02;
          letter-spacing: -0.04em;
          font-family: "Avenir Next", "Helvetica Neue", sans-serif;
        }

        .mmf-sidebar-brand p {
          margin: 0.7rem 0 0;
          color: rgba(237, 241, 249, 0.72);
          line-height: 1.55;
          font-size: 0.94rem;
        }

        .mmf-hero {
          position: relative;
          overflow: hidden;
          border-radius: 36px;
          padding: 2rem 2.2rem;
          margin-bottom: 1.25rem;
          background:
            radial-gradient(circle at 15% 15%, rgba(92, 123, 255, 0.32), transparent 34%),
            radial-gradient(circle at 85% 0%, rgba(30, 207, 155, 0.16), transparent 28%),
            linear-gradient(135deg, #0d1015 0%, #171c24 52%, #0d1015 100%);
          border: 1px solid rgba(255, 255, 255, 0.08);
          box-shadow: 0 30px 80px rgba(12, 16, 24, 0.22);
          color: #f8fbff;
        }

        .mmf-hero::after {
          content: "";
          position: absolute;
          inset: auto -8% -35% auto;
          width: 240px;
          height: 240px;
          background: radial-gradient(circle, rgba(255, 255, 255, 0.14) 0%, rgba(255, 255, 255, 0) 70%);
          pointer-events: none;
        }

        .mmf-kicker {
          font-size: 0.76rem;
          letter-spacing: 0.22em;
          text-transform: uppercase;
          color: rgba(244, 247, 255, 0.62);
          margin-bottom: 0.7rem;
          font-weight: 700;
        }

        .mmf-hero h1 {
          font-family: "Avenir Next", "Helvetica Neue", sans-serif;
          font-size: clamp(2.1rem, 3.8vw, 4rem);
          line-height: 0.95;
          letter-spacing: -0.05em;
          margin: 0 0 0.8rem;
        }

        .mmf-hero p {
          max-width: 46rem;
          font-size: 1rem;
          line-height: 1.6;
          color: rgba(242, 245, 252, 0.76);
          margin: 0 0 1.2rem;
        }

        .mmf-pill-row {
          display: flex;
          flex-wrap: wrap;
          gap: 0.65rem;
        }

        .mmf-pill {
          display: inline-flex;
          align-items: center;
          gap: 0.45rem;
          padding: 0.56rem 0.9rem;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.09);
          border: 1px solid rgba(255, 255, 255, 0.08);
          font-size: 0.82rem;
          font-weight: 650;
          color: #f8fbff;
          backdrop-filter: blur(10px);
        }

        .mmf-pill--accent {
          background: linear-gradient(135deg, rgba(79, 109, 255, 0.26), rgba(30, 207, 155, 0.2));
        }

        .mmf-grid-card {
          background: var(--mmf-surface);
          border: 1px solid var(--mmf-line);
          border-radius: 28px;
          padding: 1.15rem 1.2rem;
          box-shadow: 0 12px 35px rgba(15, 18, 26, 0.06);
          backdrop-filter: blur(10px);
          min-height: 148px;
          height: 100%;
          display: flex;
          flex-direction: column;
        }

        .mmf-grid-card--dark {
          background: linear-gradient(180deg, #10141b 0%, #181d26 100%);
          color: #f7f9ff;
          border: 1px solid rgba(255, 255, 255, 0.08);
          box-shadow: 0 18px 45px rgba(13, 17, 24, 0.18);
        }

        .mmf-grid-card .eyebrow,
        .mmf-grid-card--dark .eyebrow {
          font-size: 0.74rem;
          text-transform: uppercase;
          letter-spacing: 0.18em;
          color: rgba(92, 100, 116, 0.72);
          margin-bottom: 0.65rem;
          font-weight: 700;
          min-height: 1.05rem;
        }

        .mmf-grid-card--dark .eyebrow {
          color: rgba(240, 244, 255, 0.56);
        }

        .mmf-grid-card .value {
          font-size: 1.9rem;
          line-height: 1;
          letter-spacing: -0.04em;
          font-weight: 700;
          margin-bottom: 0.55rem;
          font-family: "Avenir Next", "Helvetica Neue", sans-serif;
          min-height: 2rem;
          font-variant-numeric: tabular-nums;
        }

        .mmf-grid-card .body {
          color: #5d6574;
          font-size: 0.95rem;
          line-height: 1.5;
          margin-top: auto;
        }

        .mmf-grid-card--dark .body {
          color: rgba(238, 242, 252, 0.74);
        }

        .mmf-tone-good .value {
          color: #14b47a;
        }

        .mmf-tone-watch .value {
          color: var(--mmf-amber);
        }

        .mmf-tone-risk .value {
          color: var(--mmf-red);
        }

        .mmf-tone-accent .value {
          color: var(--mmf-blue);
        }

        .mmf-section-head {
          margin: 1.2rem 0 0.85rem;
        }

        .mmf-section-head .label {
          font-size: 0.76rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.18em;
          color: #6a7281;
          margin-bottom: 0.45rem;
        }

        .mmf-section-head h2 {
          margin: 0;
          font-size: 1.7rem;
          letter-spacing: -0.04em;
          font-family: "Avenir Next", "Helvetica Neue", sans-serif;
        }

        .mmf-section-head p {
          margin: 0.4rem 0 0;
          color: #626a78;
          max-width: 46rem;
          line-height: 1.6;
        }

        .mmf-card-row {
          display: grid;
          grid-template-columns: repeat(var(--mmf-card-cols, 3), minmax(0, 1fr));
          gap: 1rem;
          align-items: stretch;
          margin: 0 0 0.25rem;
        }

        .mmf-threshold-band {
          display: flex;
          gap: 0.75rem;
          flex-wrap: wrap;
          margin: 0.8rem 0 1rem;
        }

        .mmf-threshold {
          flex: 1 1 220px;
          padding: 0.95rem 1rem;
          border-radius: 22px;
          background: rgba(255, 255, 255, 0.74);
          border: 1px solid rgba(16, 19, 26, 0.07);
          box-shadow: 0 10px 30px rgba(15, 18, 26, 0.05);
        }

        .mmf-threshold strong {
          display: block;
          font-size: 0.95rem;
          margin-bottom: 0.2rem;
        }

        .mmf-threshold span {
          color: #636b79;
          font-size: 0.84rem;
        }

        .mmf-threshold.is-active {
          background: linear-gradient(135deg, rgba(79, 109, 255, 0.16), rgba(30, 207, 155, 0.08));
          border-color: rgba(79, 109, 255, 0.25);
        }

        .mmf-empty-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 1rem;
          margin-top: 1rem;
        }

        .mmf-empty-card {
          background: rgba(255, 255, 255, 0.76);
          border: 1px solid rgba(16, 19, 26, 0.08);
          border-radius: 24px;
          padding: 1.2rem;
          min-height: 190px;
          box-shadow: 0 12px 30px rgba(15, 18, 26, 0.05);
        }

        .mmf-empty-card h3 {
          margin: 0.25rem 0 0.5rem;
          font-size: 1.05rem;
        }

        .mmf-empty-card p {
          margin: 0;
          color: #616877;
          line-height: 1.55;
        }

        .mmf-empty-card .index {
          font-size: 0.8rem;
          letter-spacing: 0.18em;
          text-transform: uppercase;
          color: #73819a;
          font-weight: 700;
        }

        [data-testid="stMetric"] {
          background: rgba(255, 255, 255, 0.78);
          border: 1px solid rgba(16, 19, 26, 0.08);
          padding: 1rem 1.15rem;
          border-radius: 26px;
          box-shadow: 0 12px 35px rgba(15, 18, 26, 0.05);
        }

        [data-testid="stMetricLabel"] {
          color: #6a7180;
          text-transform: uppercase;
          letter-spacing: 0.16em;
          font-size: 0.72rem;
          font-weight: 700;
        }

        [data-testid="stMetricValue"] {
          font-family: "Avenir Next", "Helvetica Neue", sans-serif;
          letter-spacing: -0.04em;
          font-size: 2rem;
          color: #10131a;
        }

        .stAlert {
          border-radius: 22px;
          border: 1px solid rgba(16, 19, 26, 0.08);
          box-shadow: 0 10px 28px rgba(15, 18, 26, 0.05);
        }

        [data-testid="stExpander"] {
          background: rgba(255, 255, 255, 0.72);
          border: 1px solid rgba(16, 19, 26, 0.08);
          border-radius: 24px;
          overflow: hidden;
          box-shadow: 0 12px 35px rgba(15, 18, 26, 0.05);
        }

        [data-testid="stExpander"] details summary p {
          font-weight: 650;
          color: #12151d;
        }

        [data-testid="stDataFrame"] {
          border-radius: 26px;
          overflow: hidden;
          border: 1px solid rgba(16, 19, 26, 0.08);
          box-shadow: 0 14px 34px rgba(15, 18, 26, 0.06);
          background: rgba(255, 255, 255, 0.8);
        }

        .stCodeBlock,
        [data-testid="stCode"] {
          border-radius: 24px;
          border: 1px solid rgba(16, 19, 26, 0.08);
          overflow: hidden;
        }

        hr {
          border-color: rgba(16, 19, 26, 0.08);
          margin: 1.3rem 0;
        }

        .mmf-footer {
          color: #6a7281;
          font-size: 0.87rem;
          margin-top: 0.6rem;
        }

        @media (max-width: 900px) {
          .mmf-hero {
            padding: 1.5rem 1.35rem;
            border-radius: 30px;
          }

          .mmf-empty-grid {
            grid-template-columns: 1fr;
          }

          .mmf-card-row {
            grid-template-columns: 1fr;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar_intro() -> None:
    """Render the branded sidebar introduction."""
    st.markdown(
        """
        <div class="mmf-sidebar-brand">
          <div class="kicker">Measurement Maturity</div>
          <h2>Decision Design Layer</h2>
          <p>Upload a metric pack, pull down templates, and tighten the review loop before a number starts steering decisions.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _score_signal(score: float, config: Any) -> tuple[str, str]:
    """Return the score label and matching visual tone."""
    label = config.get_threshold_label(score)
    if label == "Decision-ready":
        return label, "good"
    if label == "Usable with caution":
        return label, "watch"
    return label, "risk"


def _validation_signal(issues: list[Any]) -> tuple[str, str, str]:
    """Summarize validation status for the top-level overview."""
    error_count = sum(
        1
        for issue in issues
        if getattr(issue, "severity", getattr(issue, "level", "")).lower() == "error"
    )
    warning_count = sum(
        1
        for issue in issues
        if getattr(issue, "severity", getattr(issue, "level", "")).lower() == "warning"
    )

    if error_count:
        return (
            "Errors present",
            f"{error_count} blocking issue(s) to resolve first.",
            "risk",
        )
    if warning_count:
        return (
            "Warnings present",
            f"{warning_count} structural risk(s) still visible.",
            "watch",
        )
    return "Schema clean", "No structural issues found in this pass.", "good"


def _issue_counts(issues: list[Any]) -> Dict[str, int]:
    """Count issues by severity."""
    counts = {"error": 0, "warning": 0, "info": 0}
    for issue in issues:
        severity = getattr(issue, "severity", getattr(issue, "level", "")).lower()
        if severity in counts:
            counts[severity] += 1
    return counts


def _render_hero(title: str, subtitle: str, pills: list[str]) -> None:
    """Render the main page hero."""
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


def _section_header(label: str, title: str, description: str) -> None:
    """Render a section header with an editorial label."""
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


def _stat_card_html(
    eyebrow: str,
    value: str,
    body: str,
    *,
    tone: str = "accent",
    dark: bool = False,
) -> str:
    """Build the HTML for a summary stat card."""
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


def _render_stat_card_row(cards: list[str], columns: Optional[int] = None) -> None:
    """Render a row of stat cards with consistent alignment."""
    card_columns = columns or len(cards) or 1
    st.markdown(
        (
            f'<div class="mmf-card-row" style="--mmf-card-cols: {card_columns};">'
            f'{"".join(cards)}'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_empty_state_cards() -> None:
    """Render the pre-upload explainer cards."""
    st.markdown(
        """
        <div class="mmf-empty-grid">
          <div class="mmf-empty-card">
            <div class="index">Signal 01</div>
            <h3>Validate the structure first</h3>
            <p>Check ownership, definitions, SQL shape, and tests before the pack becomes a dashboard dependency.</p>
          </div>
          <div class="mmf-empty-card">
            <div class="index">Signal 02</div>
            <h3>Score decision risk, not performance</h3>
            <p>The framework measures how safe a metric is to use, not whether the business is doing well.</p>
          </div>
          <div class="mmf-empty-card">
            <div class="index">Signal 03</div>
            <h3>See the strategy chain</h3>
            <p>Map how local metrics roll up into levers and business goals so weak links stay visible.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _threshold_band_html(
    t_ready: float,
    t_caution: float,
    t_early: float,
    pack_label: str,
) -> str:
    """Build the threshold band markup for the scoring section."""
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


def _suggestion_group_icon(items: list[Dict[str, str]]) -> str:
    """Return an icon for a metric's suggestion state."""
    severities = {(item.get("severity") or "").lower() for item in items}
    if "critical" in severities or "warning" in severities:
        return "⚠"
    if "info" in severities:
        return "ℹ"
    return "✓"


def _render_footer() -> None:
    """Render the footer note."""
    st.markdown(
        f'<p class="mmf-footer">{escape(FOOTER_TEXT)}</p>',
        unsafe_allow_html=True,
    )


def main() -> None:
    """Render the Streamlit app."""
    st.set_page_config(
        page_title=APP_TITLE,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_theme_css()

    dl = _sidebar_downloads_base()

    # --- Sidebar: inputs + downloads that don't depend on upload ---
    with st.sidebar:
        _render_sidebar_intro()
        st.header("Inputs")
        uploaded = st.file_uploader("Upload a metric-pack YAML", type=["yaml", "yml"])

        st.markdown("---")
        st.subheader("Downloads")

        # Metric template
        st.download_button(
            label="Download metric template (YAML)",
            data=(dl["metric_template"] or "").encode("utf-8"),
            file_name="metric_template.yaml",
            mime="text/yaml",
            width="stretch",
        )

        if dl.get("pack_template"):
            st.download_button(
                label="Download pack template (YAML)",
                data=dl["pack_template"].encode("utf-8"),
                file_name="metric_pack_template.yaml",
                mime="text/yaml",
                width="stretch",
            )
        else:
            st.caption(
                "No pack template found in ./templates (add template/metric_pack_template.yaml to enable this download)."
            )

        # Example pack
        if dl["example_pack"]:
            st.download_button(
                label="Download example pack (YAML)",
                data=dl["example_pack"].encode("utf-8"),
                file_name=dl["example_pack_filename"] or "example_metric_pack.yaml",
                mime="text/yaml",
                width="stretch",
            )
        else:
            st.caption(
                "No example pack found in ./examples (add one to enable this download)."
            )

        st.markdown("---")
        st.caption("Tip: keep IDs stable. It makes trends and governance easier later.")

    if not uploaded:
        _render_hero(
            "Audit metric packs before they shape decisions.",
            "Structured review for teams that want clearer metrics, calmer governance, and fewer surprises once a KPI makes it into a dashboard or target.",
            ["Deterministic review", "No silent edits", "Strategy tree included"],
        )
        _render_empty_state_cards()
        _render_footer()
        return

    # --- Parse YAML ---
    raw_bytes = uploaded.getvalue()

    MAX_UPLOAD_BYTES = 1_000_000  # 1 MB
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        st.error(
            f"File too large ({len(raw_bytes):,} bytes). Maximum is {MAX_UPLOAD_BYTES:,} bytes."
        )
        st.stop()

    try:
        pack = _load_yaml_bytes(raw_bytes)
    except Exception as e:
        st.error(f"Could not parse YAML: {e}")
        st.stop()

    # 1) Validate (and normalize)
    validation = validate_metric_pack(pack)
    normalized_pack = validation.pack
    issues = list(validation.issues or [])
    score_result = score_pack(normalized_pack)
    grouped = deterministic_suggestions(normalized_pack, score_result)
    config = load_config()
    t_ready = config.thresholds["decision_ready"]
    t_caution = config.thresholds["usable_with_caution"]
    t_early = config.thresholds["early_fragile"]

    # --- Sidebar: normalized download (depends on upload) ---
    normalized_yaml_text = _dump_yaml_text(normalized_pack)
    with st.sidebar:
        st.download_button(
            label="Download normalized YAML",
            data=normalized_yaml_text.encode("utf-8"),
            file_name="normalized_metric_pack.yaml",
            mime="text/yaml",
            width="stretch",
        )

    pack_meta = pack.get("pack") or {}
    if not isinstance(pack_meta, dict):
        pack_meta = {}

    metrics = normalized_pack.get("metrics", []) or []
    metric_count = len(metrics) if isinstance(metrics, list) else 0
    pack_name = str(pack_meta.get("name", "Untitled Metric Pack"))
    pack_id = str(pack_meta.get("id", "—"))
    pack_version = str(pack_meta.get("version", "—"))
    schema_version = str(pack_meta.get("schema_version", "1.0"))
    score_label, score_tone = _score_signal(score_result.pack_score, config)
    validation_label, validation_detail, validation_tone = _validation_signal(issues)

    _render_hero(
        pack_name,
        "A compact review pass across structure, decision risk, and strategy shape. The weakest metric still matters, so the page keeps it visible throughout.",
        [
            f"{metric_count} metric(s)",
            f"Version {pack_version}",
            f"Schema {schema_version}",
            score_label,
        ],
    )

    _render_stat_card_row(
        [
            _stat_card_html(
                "Pack ID",
                pack_id,
                f"Version {pack_version} · Schema {schema_version}",
                tone="accent",
                dark=True,
            ),
            _stat_card_html(
                "Validation",
                validation_label,
                validation_detail,
                tone=validation_tone,
            ),
            _stat_card_html(
                "Pack Score",
                f"{score_result.pack_score:.2f}",
                f"{score_label}. Average metric score: {score_result.avg_metric_score:.2f}.",
                tone=score_tone,
            ),
            _stat_card_html(
                "Weakest Metric",
                f"{score_result.min_metric_score:.0f}",
                f"{metric_count} metric(s) reviewed in this pass.",
                tone="watch" if score_result.min_metric_score >= t_caution else "risk",
            ),
        ],
        columns=4,
    )

    # Validation UI
    _section_header(
        "Signal 01",
        "Validation",
        "Structural checks first. Scoring still runs when issues exist, but this section tells you how much trust to place in the inputs.",
    )
    if validation.ok:
        st.success(
            "Schema checks passed (this does not mean the pack is decision-ready)."
        )
    else:
        st.error(
            "Schema errors found. Fix these first — scoring still runs, but results may be misleading."
        )

    issue_counts = _issue_counts(issues)
    metrics_needing_attention = sum(
        1
        for items in grouped.values()
        if any((item.get("severity") or "").lower() != "good" for item in items)
    )
    metrics_showing_strength = sum(
        1
        for items in grouped.values()
        if items
        and all((item.get("severity") or "").lower() == "good" for item in items)
    )
    _render_stat_card_row(
        [
            _stat_card_html(
                "Errors",
                str(issue_counts["error"]),
                "Blocking issues that can distort scoring or meaning.",
                tone="risk",
            ),
            _stat_card_html(
                "Warnings",
                str(issue_counts["warning"]),
                "Gaps that weaken decision confidence.",
                tone="watch",
            ),
            _stat_card_html(
                "Info",
                str(issue_counts["info"]),
                "Optional cleanups and future-proofing notes.",
                tone="accent",
            ),
        ],
        columns=3,
    )

    issues_sorted = sorted(
        issues,
        key=lambda i: (
            _severity_rank(getattr(i, "severity", getattr(i, "level", ""))),
            getattr(i, "code", ""),
        ),
    )

    if issues_sorted:

        def _severity_icon(severity: str) -> str:
            sev_lower = severity.lower()
            if sev_lower == "error":
                return "🔴 ERROR"
            elif sev_lower == "warning":
                return "🟡 WARNING"
            elif sev_lower == "info":
                return "🔵 INFO"
            return severity

        rows = []
        for i in issues_sorted:
            rows.append(
                {
                    "Location": getattr(i, "human_location", "")
                    or getattr(i, "path", ""),
                    "Severity": _severity_icon(
                        getattr(i, "severity", getattr(i, "level", ""))
                    ),
                    "Code": getattr(i, "code", ""),
                    "Message": getattr(i, "message", ""),
                }
            )
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.caption("No issues found.")

    with st.expander("Technical details", expanded=False):
        st.json([asdict(i) if hasattr(i, "__dict__") else i for i in issues])

    st.markdown("---")

    # 2) Scoring
    _section_header(
        "Signal 02",
        "Scoring",
        "This score reflects decision safety, not business performance. The pack score blends the average metric quality with the weakest metric in the set.",
    )

    pack_score = score_result.pack_score
    if pack_score >= t_ready:
        pack_icon = "🟢"
        pack_label = "Decision-ready"
    elif pack_score >= t_caution:
        pack_icon = "🟡"
        pack_label = "Usable with caution"
    elif pack_score >= t_early:
        pack_icon = "🟠"
        pack_label = "Early/fragile"
    else:
        pack_icon = "🔴"
        pack_label = "Not safe for decisions"

    col_a, col_b, col_c = st.columns(3)
    col_a.metric(
        f"{pack_icon} Pack Score",
        f"{pack_score:.2f}",
        help=(
            f"{pack_label} "
            f"({t_ready}+ = decision-ready, "
            f"{t_caution}-{t_ready - 1} = caution, "
            f"{t_early}-{t_caution - 1} = early/fragile, "
            f"<{t_early} = not safe)"
        ),
    )
    col_b.metric(
        "Weakest Metric",
        f"{score_result.min_metric_score:.0f}",
        help="Lowest individual metric score. The pack score is pulled toward this value.",
    )
    col_c.metric(
        "Average Metric",
        f"{score_result.avg_metric_score:.2f}",
        help="Simple average across all metric scores before the weakest-metric floor is applied.",
    )
    st.markdown(
        _threshold_band_html(
            t_ready=t_ready,
            t_caution=t_caution,
            t_early=t_early,
            pack_label=pack_label,
        ),
        unsafe_allow_html=True,
    )

    # Metric-level scores with icons
    def _score_label(score: float) -> str:
        if score >= t_ready:
            return "🟢 Good"
        if score >= t_caution:
            return "🟡 Watch"
        if score >= t_early:
            return "🟠 Fragile"
        return "🔴 Risk"

    metric_rows = []
    for ms in score_result.metric_scores:
        metric_rows.append(
            {
                "Metric": ms.name,
                "Signal": _score_label(ms.score),
                "Score": int(ms.score),
                "Status": ms.status,
                "Tier": ms.tier or "—",
                "ID": ms.metric_id,
                "Why": ms.why,
            }
        )
    st.dataframe(metric_rows, width="stretch", hide_index=True)

    st.markdown("---")

    # 3) Suggestions
    _section_header(
        "Signal 03",
        "Suggestions",
        "The framework stays deterministic here too. Suggestions are grouped by metric so the next move is obvious instead of buried in a long checklist.",
    )

    _render_stat_card_row(
        [
            _stat_card_html(
                "Needs Attention",
                str(metrics_needing_attention),
                "Metrics with at least one warning, info, or critical follow-up.",
                tone="watch" if metrics_needing_attention else "good",
            ),
            _stat_card_html(
                "Total Metrics",
                str(metric_count),
                "The full scope of the reviewed pack.",
                tone="accent",
            ),
            _stat_card_html(
                "Strong Signals",
                str(metrics_showing_strength),
                "Metrics showing only positive signals in this pass.",
                tone="good",
            ),
        ],
        columns=3,
    )

    if not grouped:
        st.caption("No suggestions.")
    else:
        name_by_id = {
            m.get("id"): m.get("name") for m in metrics if isinstance(m, dict)
        }

        ordered_groups = sorted(
            grouped.items(),
            key=lambda pair: (
                (
                    0
                    if any(
                        (item.get("severity") or "").lower() != "good"
                        for item in pair[1]
                    )
                    else 1
                ),
                name_by_id.get(pair[0], pair[0] or ""),
            ),
        )

        for mid, items in ordered_groups:
            title = (
                f"{_suggestion_group_icon(items)} {name_by_id.get(mid, mid)} — {mid}"
            )
            with st.expander(title, expanded=False):
                for it in items:
                    sev = (it.get("severity") or "").lower()
                    msg = it.get("message") or ""
                    if sev == "good":
                        st.success(msg)
                    elif sev in ("warning", "critical"):
                        st.warning(msg)
                    else:
                        st.info(msg)

    st.markdown("---")

    # 4) Strategy tree (safe)
    _section_header(
        "Signal 04",
        "Strategy Tree",
        "A visual check for how the pack rolls up into levers and business outcomes. It helps spot where one weak metric can distort the bigger story.",
    )
    build_strategy = _try_get_strategy_mermaid_builder()
    render_mermaid = _try_get_mermaid_renderer()

    if not build_strategy:
        st.warning("Strategy tree renderer is not available in this build.")
    else:
        try:
            mermaid_code = build_strategy(normalized_pack)
        except Exception as e:
            st.warning(f"Could not build strategy tree: {e}")
            mermaid_code = ""

        if mermaid_code.strip():
            if render_mermaid:
                try:
                    render_mermaid(mermaid_code, height=760)
                except Exception as e:
                    st.warning(f"Could not render diagram in Streamlit: {e}")
                    st.code(mermaid_code, language="mermaid")
            else:
                st.code(mermaid_code, language="mermaid")

    _render_footer()


if __name__ == "__main__":
    main()
