# app.py
"""Entry point for the Measurement Maturity Framework Streamlit app."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Dict, Mapping, Optional

import streamlit as st
import yaml  # type: ignore[import-untyped]

from mmf.config import load_config
from mmf.streamlit_compat import render_dataframe
from mmf.validator import validate_metric_pack
from mmf.scoring import score_pack
from mmf.suggestions import deterministic_suggestions
from mmf.ui import (
    inject_theme_css,
    render_hero,
    render_section_header,
    stat_card_html,
    render_stat_card_row,
    threshold_band_html,
    render_empty_state_cards,
    render_footer,
    severity_rank,
    score_signal,
    validation_signal,
    issue_counts,
    suggestion_group_icon,
    render_sidebar_intro,
    load_sidebar_downloads,
    render_sidebar_downloads,
    render_normalized_download,
)

APP_TITLE = "Measurement Maturity Framework — YAML Auditor"
FOOTER_TEXT = (
    "Deterministic checks. No silent edits. "
    "Schema-valid ≠ decision-ready. Treat suggestions as a checklist, not a verdict."
)
MAX_UPLOAD_BYTES = 1_000_000  # 1 MB


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------


def _load_yaml_bytes(raw: bytes) -> Dict[str, Any]:
    """Parse raw YAML bytes and return a dict, raising ValueError on bad input."""
    data = yaml.safe_load(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Top-level YAML must be a mapping (object).")
    return data


def _dump_yaml_text(obj: Any) -> str:
    """Serialise a Python object to stable, readable YAML."""
    return yaml.safe_dump(
        obj,
        sort_keys=False,
        allow_unicode=True,
        width=100,
        default_flow_style=False,
    )


# ---------------------------------------------------------------------------
# Optional dependency wrappers (Mermaid)
# ---------------------------------------------------------------------------


def _try_get_strategy_mermaid_builder() -> Optional[Callable[[Mapping[str, Any]], str]]:
    """Return the Mermaid strategy builder when available, else None."""
    try:
        from mmf.mermaid import build_strategy_mermaid  # type: ignore

        if callable(build_strategy_mermaid):
            return build_strategy_mermaid
    except Exception:
        pass
    return None


def _try_get_mermaid_renderer() -> Optional[Callable[..., None]]:
    """Return the Streamlit Mermaid renderer when available, else None."""
    try:
        from mmf.streamlit_mermaid import render_mermaid  # type: ignore

        if callable(render_mermaid):
            return render_mermaid
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Page sections
# ---------------------------------------------------------------------------


def _render_validation_section(
    validation: Any,
    issues: list,
    grouped: Dict[str, list],
) -> tuple[int, int]:
    """Render the validation results: status banner, stat cards, and issue table."""
    render_section_header(
        "Signal 01",
        "Validation",
        "Structural checks first. Scoring still runs when issues exist, but this section "
        "tells you how much trust to place in the inputs.",
    )

    if validation.ok:
        st.success(
            "Schema checks passed (this does not mean the pack is decision-ready)."
        )
    else:
        st.error(
            "Schema errors found. Fix these first — scoring still runs, but results may be misleading."
        )

    counts = issue_counts(issues)
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

    render_stat_card_row(
        [
            stat_card_html(
                "Errors",
                str(counts["error"]),
                "Blocking issues that can distort scoring or meaning.",
                tone="risk",
            ),
            stat_card_html(
                "Warnings",
                str(counts["warning"]),
                "Gaps that weaken decision confidence.",
                tone="watch",
            ),
            stat_card_html(
                "Info",
                str(counts["info"]),
                "Optional cleanups and future-proofing notes.",
                tone="accent",
            ),
        ],
        columns=3,
    )

    issues_sorted = sorted(
        issues,
        key=lambda i: (
            severity_rank(getattr(i, "severity", getattr(i, "level", ""))),
            getattr(i, "code", ""),
        ),
    )

    if issues_sorted:

        def _icon(sev: str) -> str:
            s = sev.lower()
            if s == "error":
                return "🔴 ERROR"
            if s == "warning":
                return "🟡 WARNING"
            if s == "info":
                return "🔵 INFO"
            return sev

        rows = [
            {
                "Location": getattr(i, "human_location", "") or getattr(i, "path", ""),
                "Severity": _icon(getattr(i, "severity", getattr(i, "level", ""))),
                "Code": getattr(i, "code", ""),
                "Message": getattr(i, "message", ""),
            }
            for i in issues_sorted
        ]
        render_dataframe(rows, hide_index=True)
    else:
        st.caption("No issues found.")

    with st.expander("Technical details", expanded=False):
        st.json([asdict(i) if hasattr(i, "__dict__") else i for i in issues])

    return metrics_needing_attention, metrics_showing_strength


def _render_scoring_section(
    score_result: Any,
    config: Any,
    t_ready: float,
    t_caution: float,
    t_early: float,
) -> None:
    """Render the scoring section: summary metrics, threshold band, per-metric table."""
    render_section_header(
        "Signal 02",
        "Scoring",
        "This score reflects decision safety, not business performance. The pack score "
        "blends the average metric quality with the weakest metric in the set.",
    )

    pack_score = score_result.pack_score
    if pack_score >= t_ready:
        pack_icon, pack_label = "🟢", "Decision-ready"
    elif pack_score >= t_caution:
        pack_icon, pack_label = "🟡", "Usable with caution"
    elif pack_score >= t_early:
        pack_icon, pack_label = "🟠", "Early/fragile"
    else:
        pack_icon, pack_label = "🔴", "Not safe for decisions"

    col_a, col_b, col_c = st.columns(3)
    col_a.metric(
        f"{pack_icon} Pack Score",
        f"{pack_score:.2f}",
        help=(
            f"{pack_label} "
            f"({t_ready}+ = decision-ready, "
            f"{t_caution}-{int(t_ready - 1)} = caution, "
            f"{t_early}-{int(t_caution - 1)} = early/fragile, "
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
        help="Simple average across all metric scores before the floor is applied.",
    )

    st.markdown(
        threshold_band_html(
            t_ready=t_ready, t_caution=t_caution, t_early=t_early, pack_label=pack_label
        ),
        unsafe_allow_html=True,
    )

    def _score_label(score: float) -> str:
        if score >= t_ready:
            return "🟢 Good"
        if score >= t_caution:
            return "🟡 Watch"
        if score >= t_early:
            return "🟠 Fragile"
        return "🔴 Risk"

    metric_rows = [
        {
            "Metric": ms.name,
            "Signal": _score_label(ms.score),
            "Score": int(ms.score),
            "Status": ms.status,
            "Tier": ms.tier or "—",
            "ID": ms.metric_id,
            "Why": ms.why,
        }
        for ms in score_result.metric_scores
    ]
    render_dataframe(metric_rows, hide_index=True)


def _render_suggestions_section(
    grouped: Dict[str, list],
    metrics: list,
    metric_count: int,
    metrics_needing_attention: int,
    metrics_showing_strength: int,
) -> None:
    """Render the deterministic suggestions section, grouped by metric."""
    render_section_header(
        "Signal 03",
        "Suggestions",
        "The framework stays deterministic here too. Suggestions are grouped by metric "
        "so the next move is obvious instead of buried in a long checklist.",
    )

    render_stat_card_row(
        [
            stat_card_html(
                "Needs Attention",
                str(metrics_needing_attention),
                "Metrics with at least one warning, info, or critical follow-up.",
                tone="watch" if metrics_needing_attention else "good",
            ),
            stat_card_html(
                "Total Metrics",
                str(metric_count),
                "The full scope of the reviewed pack.",
                tone="accent",
            ),
            stat_card_html(
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
        return

    name_by_id = {m.get("id"): m.get("name") for m in metrics if isinstance(m, dict)}
    ordered_groups = sorted(
        grouped.items(),
        key=lambda pair: (
            (
                0
                if any(
                    (item.get("severity") or "").lower() != "good" for item in pair[1]
                )
                else 1
            ),
            name_by_id.get(pair[0], pair[0] or ""),
        ),
    )

    for mid, items in ordered_groups:
        title = f"{suggestion_group_icon(items)} {name_by_id.get(mid, mid)} — {mid}"
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


def _render_strategy_section(normalized_pack: Mapping[str, Any]) -> None:
    """Render the optional Mermaid strategy tree section."""
    render_section_header(
        "Signal 04",
        "Strategy Tree",
        "A visual check for how the pack rolls up into levers and business outcomes. "
        "It helps spot where one weak metric can distort the bigger story.",
    )

    build_strategy = _try_get_strategy_mermaid_builder()
    render_mermaid_fn = _try_get_mermaid_renderer()

    if not build_strategy:
        st.warning("Strategy tree renderer is not available in this build.")
        return

    try:
        mermaid_code = build_strategy(normalized_pack)
    except Exception as e:
        st.warning(f"Could not build strategy tree: {e}")
        return

    if not mermaid_code.strip():
        return

    if render_mermaid_fn:
        try:
            render_mermaid_fn(mermaid_code, height=760)
        except Exception as e:
            st.warning(f"Could not render diagram in Streamlit: {e}")
            st.code(mermaid_code, language="mermaid")
    else:
        st.code(mermaid_code, language="mermaid")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Render the Streamlit app."""
    st.set_page_config(
        page_title=APP_TITLE, layout="wide", initial_sidebar_state="expanded"
    )
    inject_theme_css()

    dl = load_sidebar_downloads()

    with st.sidebar:
        render_sidebar_intro()
        st.header("Inputs")
        uploaded = st.file_uploader("Upload a metric-pack YAML", type=["yaml", "yml"])
        render_sidebar_downloads(dl)

    if not uploaded:
        render_hero(
            "Audit metric packs before they shape decisions.",
            "Structured review for teams that want clearer metrics, calmer governance, "
            "and fewer surprises once a KPI makes it into a dashboard or target.",
            ["Deterministic review", "No silent edits", "Strategy tree included"],
        )
        render_empty_state_cards()
        render_footer(FOOTER_TEXT)
        return

    # --- Parse ---
    raw_bytes = uploaded.getvalue()
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

    # --- Pipeline ---
    validation = validate_metric_pack(pack)
    normalized_pack = validation.pack
    issues = list(validation.issues or [])
    score_result = score_pack(normalized_pack)
    grouped = deterministic_suggestions(normalized_pack, score_result)
    config = load_config()
    t_ready = config.thresholds["decision_ready"]
    t_caution = config.thresholds["usable_with_caution"]
    t_early = config.thresholds["early_fragile"]

    with st.sidebar:
        render_normalized_download(_dump_yaml_text(normalized_pack))

    pack_meta = pack.get("pack") or {}
    if not isinstance(pack_meta, dict):
        pack_meta = {}

    metrics = normalized_pack.get("metrics", []) or []
    metric_count = len(metrics) if isinstance(metrics, list) else 0
    pack_name = str(pack_meta.get("name", "Untitled Metric Pack"))
    pack_id = str(pack_meta.get("id", "—"))
    pack_version = str(pack_meta.get("version", "—"))
    schema_version = str(pack_meta.get("schema_version", "1.0"))
    score_lbl, score_tone = score_signal(score_result.pack_score, config)
    val_label, val_detail, val_tone = validation_signal(issues)

    render_hero(
        pack_name,
        "A compact review pass across structure, decision risk, and strategy shape. "
        "The weakest metric still matters, so the page keeps it visible throughout.",
        [
            f"{metric_count} metric(s)",
            f"Version {pack_version}",
            f"Schema {schema_version}",
            score_lbl,
        ],
    )

    render_stat_card_row(
        [
            stat_card_html(
                "Pack ID",
                pack_id,
                f"Version {pack_version} · Schema {schema_version}",
                tone="accent",
                dark=True,
            ),
            stat_card_html("Validation", val_label, val_detail, tone=val_tone),
            stat_card_html(
                "Pack Score",
                f"{score_result.pack_score:.2f}",
                f"{score_lbl}. Average metric score: {score_result.avg_metric_score:.2f}.",
                tone=score_tone,
            ),
            stat_card_html(
                "Weakest Metric",
                f"{score_result.min_metric_score:.0f}",
                f"{metric_count} metric(s) reviewed in this pass.",
                tone="watch" if score_result.min_metric_score >= t_caution else "risk",
            ),
        ],
        columns=4,
    )

    st.markdown("---")
    metrics_needing, metrics_strong = _render_validation_section(
        validation, issues, grouped
    )
    st.markdown("---")
    _render_scoring_section(score_result, config, t_ready, t_caution, t_early)
    st.markdown("---")
    _render_suggestions_section(
        grouped, metrics, metric_count, metrics_needing, metrics_strong
    )
    st.markdown("---")
    _render_strategy_section(normalized_pack)
    render_footer(FOOTER_TEXT)


if __name__ == "__main__":
    main()
