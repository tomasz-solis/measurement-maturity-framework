"""Streamlit rendering components for pack analysis results.

These functions translate scored/validated pack data into Streamlit UI.
They depend on Streamlit but not on session state — all inputs are
explicit arguments.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import streamlit as st


def severity_rank(sev: str) -> int:
    """Return a sort key for issue severity — lower means higher priority."""
    return {"ERROR": 0, "WARNING": 1, "INFO": 2}.get((sev or "").upper(), 9)


def score_signal(score: float, config: Any) -> Tuple[str, str]:
    """Return the threshold label and visual tone string for a pack score."""
    label = config.get_threshold_label(score)
    if label == "Decision-ready":
        return label, "good"
    if label == "Usable with caution":
        return label, "watch"
    return label, "risk"


def validation_signal(issues: List[Any]) -> Tuple[str, str, str]:
    """Summarise validation status as (label, detail, tone).

    Tone is one of: 'good', 'watch', 'risk'.
    """
    error_count = sum(
        1
        for i in issues
        if getattr(i, "severity", getattr(i, "level", "")).lower() == "error"
    )
    warning_count = sum(
        1
        for i in issues
        if getattr(i, "severity", getattr(i, "level", "")).lower() == "warning"
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
            f"{warning_count} warning(s) still worth fixing.",
            "watch",
        )
    return "Schema clean", "No structural issues found in this pass.", "good"


def issue_counts(issues: List[Any]) -> Dict[str, int]:
    """Count validation issues by severity."""
    counts = {"error": 0, "warning": 0, "info": 0}
    for issue in issues:
        sev = getattr(issue, "severity", getattr(issue, "level", "")).lower()
        if sev in counts:
            counts[sev] += 1
    return counts


def suggestion_group_icon(items: List[Dict[str, str]]) -> str:
    """Return an icon character summarising a metric's suggestion state."""
    severities = {(item.get("severity") or "").lower() for item in items}
    if "critical" in severities or "warning" in severities:
        return "⚠"
    if "info" in severities:
        return "ℹ"
    return "✓"


def render_sidebar_intro() -> None:
    """Render the branded sidebar header and description."""
    st.markdown(
        """
        <div class="mmf-sidebar-brand">
          <div class="kicker">Measurement Maturity</div>
          <h2>Metric Pack Review</h2>
          <p>Upload a pack, grab an example, and review the structure before a
             number starts steering decisions.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
