# app.py
"""Entry point for the Measurement Maturity Framework Streamlit app."""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional

import streamlit as st
import yaml  # type: ignore[import-untyped]

from mmf.config import load_config
from mmf.streamlit_compat import render_download_button
from mmf.validator import validate_metric_pack
from mmf.scoring import score_pack
from mmf.suggestions import deterministic_suggestions
from mmf.schema import is_v2_pack
from mmf.vertical_validator import validate_vertical_pack
from mmf.vertical_scoring import score_vertical
from mmf.decision_map import build_decision_map
from mmf.brief import build_brief
from mmf.cross_vertical import compare_verticals
from mmf.exports import (
    cross_vertical_matrix_to_csv,
    cross_vertical_shared_gaps_to_csv,
    export_all,
)
from mmf.ui import (
    inject_theme_css,
    data_table_html,
    heatmap_table_html,
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
    load_sidebar_examples,
    render_sidebar_examples,
)

APP_TITLE = "Measurement Maturity Framework | Metric Pack Auditor"
FOOTER_TEXT = (
    "Rules-based checks. No silent edits. "
    "Schema-valid does not mean decision-ready. Use the suggestions as a checklist, not a verdict."
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
        "Check the structure first. Scoring still runs when issues exist, but this section "
        "tells you how much trust to place in the input.",
    )

    if validation.ok:
        st.success(
            "Schema checks passed. That does not mean the pack is ready to use without review."
        )
    else:
        st.error(
            "Schema errors found. Fix these first. Scoring still runs, but the results may be misleading."
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
                return "ERROR"
            if s == "warning":
                return "WARNING"
            if s == "info":
                return "INFO"
            return sev

        rows = []
        for i in issues_sorted:
            sev = getattr(i, "severity", getattr(i, "level", "")) or ""
            rows.append(
                {
                    "Location": getattr(i, "human_location", "")
                    or getattr(i, "path", ""),
                    "Severity": (_icon(sev), _SEV_TONE.get(sev.upper(), "none")),
                    "Code": getattr(i, "code", ""),
                    "Message": getattr(i, "message", ""),
                }
            )
        st.markdown(data_table_html(rows), unsafe_allow_html=True)
    else:
        st.caption("No issues found.")

    _render_why_it_matters(issues)

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
        "This score is about metric safety, not business performance. The pack score "
        "blends the average metric quality with the weakest metric in the set.",
    )

    pack_score = score_result.pack_score
    if pack_score >= t_ready:
        pack_label = "Decision-ready"
    elif pack_score >= t_caution:
        pack_label = "Usable with caution"
    elif pack_score >= t_early:
        pack_label = "Early/fragile"
    else:
        pack_label = "Not safe for decisions"

    col_a, col_b, col_c = st.columns(3)
    col_a.metric(
        "Pack Score",
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

    metric_rows = [
        {
            "Metric": ms.name,
            "Signal": _score_signal(ms.score),
            "Score": int(ms.score),
            "Status": ms.status,
            "Tier": ms.tier or " - ",
            "ID": ms.metric_id,
            "Why": ms.why,
        }
        for ms in score_result.metric_scores
    ]
    st.markdown(data_table_html(metric_rows), unsafe_allow_html=True)


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
        "Suggestions stay rules-based too. They are grouped by metric so the next step "
        "is easy to see.",
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
        title = f"{suggestion_group_icon(items)} {name_by_id.get(mid, mid)} - {mid}"
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
        "An optional view of how the pack rolls up into levers and business outcomes. "
        "It helps show where one weak metric can distort the bigger picture.",
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
# Page sections (v2 vertical + cross-vertical)
# ---------------------------------------------------------------------------


def _band_tone(band: str) -> str:
    """Map a vertical readiness band to a stat-card tone."""
    b = (band or "").lower()
    if b.startswith("decision-ready"):
        return "good"
    if b.startswith("usable"):
        return "watch"
    if b.startswith("fragile"):
        return "alarm"
    return "risk"


# Band -> heatmap/chip tone (green / amber / red / grey).
_DIM_TONE = {
    "Strong": "good",
    "Partial": "watch",
    "Weak": "risk",
    "Not assessed": "none",
}
_OVERALL_TONE = {
    "Decision-ready": "good",
    "Usable with caution": "watch",
    "Fragile": "alarm",
    "Not ready for recurring decisions": "risk",
}

# Severity -> chip tone, shared by validation tables.
_SEV_TONE = {"ERROR": "risk", "WARNING": "watch", "INFO": "accent", "CRITICAL": "risk"}

# Plain-English "why this check matters" for the validation panel. Codes not
# listed fall back to the issue's own message.
_WHY_IT_MATTERS = {
    "metric_sql_missing": (
        "Without source-controlled SQL, the number cannot be reproduced, "
        "audited, or handed to another team."
    ),
    "metric_tests_missing": (
        "With no checks, a broken metric surfaces in a board deck instead of a "
        "pipeline alert."
    ),
    "metric_requires_missing": (
        "Upstream dependencies are not listed, so tracing a break later takes "
        "longer."
    ),
    "missing_metric_accountable": (
        "With no owner, the metric drifts and no one is responsible when it breaks."
    ),
    "metric_sql_syntax_error": (
        "The query may not run as written - verify it in the warehouse before "
        "relying on it."
    ),
    "missing_schema_version": (
        "Without a schema version, future compatibility is harder to track."
    ),
    "unknown_schema_version": (
        "The declared schema version is not recognised by this build."
    ),
    "duplicate_metric_id": (
        "Duplicate ids make references ambiguous and risk double-counting."
    ),
    "missing_metric_name": (
        "A metric with no name is hard to reference, review, or discuss."
    ),
    "metric_missing_role": (
        "Without a role, it is unclear whether this is a primary, supporting, "
        "diagnostic, or guardrail metric."
    ),
    "broken_required_metric_reference": (
        "A decision points at a metric that does not exist, so it cannot "
        "actually be supported."
    ),
    "broken_guardrail_reference": (
        "A guardrail points at a metric that does not exist, so the safety check "
        "is not real."
    ),
    "broken_okr_reference": (
        "A metric links to an OKR that does not exist, so strategy linkage is "
        "broken."
    ),
    "broken_decision_reference": ("A metric links to a decision that does not exist."),
    "broken_kr_metric_reference": (
        "A key result points at a metric that does not exist."
    ),
    "unlinked_okr": (
        "This OKR has no key result that resolves to a defined metric, so it is "
        "not measured yet."
    ),
    "missing_vertical_owner": (
        "With no vertical owner, measurement decisions lack a clear accountable "
        "person."
    ),
    "internal_reference_in_public_sample": (
        "A public sample is carrying private links - clear them before committing."
    ),
}


def _decisions_tone(ready: int, total: int) -> str:
    """Tone for the 'decisions ready' heatmap row."""
    if total == 0:
        return "none"
    if ready == total:
        return "good"
    if ready == 0:
        return "risk"
    return "watch"


def _debt_tone(severity: str) -> str:
    """Map a debt severity to a chip tone."""
    s = (severity or "").lower()
    if s in {"critical", "high"}:
        return "risk"
    if s == "medium":
        return "alarm"
    return "watch"


def _score_signal(score: float) -> tuple:
    """Return a (label, tone) chip for a metric readiness score."""
    if score >= 80:
        return "Good", "good"
    if score >= 60:
        return "Watch", "watch"
    if score >= 40:
        return "Fragile", "alarm"
    return "Risk", "risk"


def _render_why_it_matters(issues: list) -> None:
    """Render an exec-friendly 'why these checks matter' panel (no raw JSON)."""
    if not issues:
        return
    first_msg: Dict[str, str] = {}
    codes: list = []
    for issue in issues:
        code = getattr(issue, "code", "")
        if code and code not in first_msg:
            first_msg[code] = getattr(issue, "message", "")
            codes.append(code)
    if not codes:
        return
    rows = [
        {
            "Check": code.replace("_", " ").title(),
            "Why it matters": _WHY_IT_MATTERS.get(code, first_msg.get(code, "")),
        }
        for code in codes
    ]
    with st.expander("Why these checks matter", expanded=False):
        st.markdown(data_table_html(rows), unsafe_allow_html=True)


def _render_export_buttons(
    pack: Dict[str, Any],
    validation: Any,
    score_result: Any,
    vertical_score: Any,
) -> None:
    """Render sidebar download buttons for the four FR10 export artifacts."""
    st.markdown("---")
    st.subheader("Exports")
    bundle = export_all(pack, validation, score_result, vertical_score)
    mimes = {
        "validation.json": "application/json",
        "metric_readiness.csv": "text/csv",
        "vertical_score.csv": "text/csv",
        "brief.md": "text/markdown",
    }
    for file_name, content in bundle.items():
        render_download_button(
            label=f"Download {file_name}",
            data=content.encode("utf-8"),
            file_name=file_name,
            mime=mimes.get(file_name, "text/plain"),
            key=f"export_{file_name}",
        )


def _load_bundled_v2_examples() -> list:
    """Load bundled example packs that use the v2 schema, as (name, pack) pairs."""
    out = []
    for example in load_sidebar_examples():
        try:
            data = yaml.safe_load(example.content.decode("utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and is_v2_pack(data):
            out.append((example.file_name, data))
    return out


def _render_v2_strategy(pack: Dict[str, Any]) -> None:
    """Render the v2 strategy tree (Mermaid) for a vertical pack."""
    try:
        from mmf.mermaid import build_vertical_strategy_mermaid

        code = build_vertical_strategy_mermaid(pack)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully in the UI
        st.warning(f"Could not build strategy tree: {exc}")
        return

    if not code.strip():
        st.caption("No strategy or OKRs defined in this pack yet.")
        return

    render_mermaid_fn = _try_get_mermaid_renderer()
    if render_mermaid_fn:
        try:
            render_mermaid_fn(code, height=620)
            return
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Could not render diagram in Streamlit: {exc}")
    st.code(code, language="mermaid")


def _render_v2_pack(pack: Dict[str, Any]) -> None:
    """Render the v2 vertical-readiness view for a single vertical pack."""
    validation = validate_vertical_pack(pack)
    issues = list(validation.issues or [])
    vertical_score = score_vertical(pack)
    score_result = score_pack(pack)
    decision_views = build_decision_map(pack, vertical_score)
    brief_md = build_brief(pack, vertical_score)

    vertical = pack.get("vertical") or {}
    if not isinstance(vertical, dict):
        vertical = {}
    pack_meta = pack.get("pack") or {}
    if not isinstance(pack_meta, dict):
        pack_meta = {}

    name = str(vertical.get("name") or pack_meta.get("name") or "Untitled Vertical")
    band = vertical_score.overall_band
    tone = _band_tone(band)
    if vertical_score.decisions_total:
        frac = f"{vertical_score.decisions_ready}/{vertical_score.decisions_total}"
    else:
        frac = " - "

    with st.sidebar:
        _render_export_buttons(pack, validation, score_result, vertical_score)

    render_hero(
        name,
        "Vertical measurement readiness: which key decisions are backed by trusted, "
        "owned, instrumented metrics - and where the gaps are.",
        [
            band,
            f"{frac} decisions ready",
            f"Schema {pack_meta.get('schema_version', '2.0')}",
        ],
    )

    errors = sum(1 for i in issues if i.severity == "ERROR")
    warnings = sum(1 for i in issues if i.severity == "WARNING")
    render_stat_card_row(
        [
            stat_card_html(
                "Readiness", band, "Decision-centric overall band.", tone=tone
            ),
            stat_card_html(
                "Decisions Ready",
                frac,
                "Key decisions backed by trusted, owned metrics.",
                tone=tone,
            ),
            stat_card_html(
                "Measurement Debt",
                str(len(vertical_score.debt)),
                "Gaps derived from the graph, plus any authored items.",
                tone="watch" if vertical_score.debt else "good",
            ),
            stat_card_html(
                "Validation",
                "Clean" if validation.ok else "Errors",
                f"{errors} error(s), {warnings} warning(s).",
                tone="good" if validation.ok else "risk",
            ),
        ],
        columns=2,
    )

    # --- Vertical overview ---
    st.markdown("---")
    render_section_header(
        "Signal 01",
        "Vertical Overview",
        "What this product area is and who owns its measurement.",
    )
    st.markdown(f"**{name}** - {vertical.get('description', '')}")
    st.caption(
        f"Owner: {vertical.get('owner', ' - ')} | "
        f"Lifecycle: {vertical.get('lifecycle_stage', ' - ')}"
    )

    # --- Vertical readiness scorecard ---
    st.markdown("---")
    render_section_header(
        "Signal 02",
        "Vertical Readiness",
        "Decision-ready fraction plus a dimension profile. Bands, not a "
        "falsely-precise number. Absent sections are 'not assessed', not zero.",
    )
    dim_rows = [
        {
            "Dimension": d.name,
            "Status": (d.band, _DIM_TONE.get(d.band, "none")),
            "Why": d.driver,
        }
        for d in vertical_score.dimensions
    ]
    st.markdown(data_table_html(dim_rows), unsafe_allow_html=True)

    # --- Decision map ---
    st.markdown("---")
    render_section_header(
        "Signal 03",
        "Decision Map",
        "Each recurring decision and whether its measurement can support it.",
    )
    if not decision_views:
        st.caption("No decisions defined in this pack.")
    for dv in decision_views:
        title = f"[{dv.readiness}] {dv.question or dv.id}"
        with st.expander(title, expanded=False):
            st.caption(
                f"Owner: {dv.owner or ' - '} | Cadence: {dv.cadence or ' - '} | "
                f"Type: {dv.decision_type or ' - '}"
            )
            if dv.required_metrics:
                st.markdown("**Required metrics:** " + ", ".join(dv.required_metrics))
            if dv.guardrails:
                st.markdown("**Guardrails:** " + ", ".join(dv.guardrails))
            if dv.missing_metrics:
                st.warning(
                    "Missing metric reference(s): " + ", ".join(dv.missing_metrics)
                )
            for reason in dv.reasons:
                st.markdown(f"- {reason}")
            if dv.next_step:
                st.info(dv.next_step)

    # --- Measurement debt ---
    st.markdown("---")
    render_section_header(
        "Signal 04",
        "Measurement Debt",
        "Derived from the graph (plus any authored items), sorted by severity.",
    )
    if vertical_score.debt:
        debt_rows = [
            {
                "Severity": (item.severity, _debt_tone(item.severity)),
                "Type": item.type,
                "Source": item.source,
                "Description": item.description,
                "Recommended fix": item.recommended_fix,
            }
            for item in vertical_score.debt
        ]
        st.markdown(data_table_html(debt_rows), unsafe_allow_html=True)
    else:
        st.success("No measurement debt detected from the structure.")

    # --- Metric readiness (Layer 1) ---
    st.markdown("---")
    render_section_header(
        "Signal 05",
        "Metric Readiness",
        "The v1 structural score for each metric, reused unchanged.",
    )
    metric_rows = [
        {
            "Metric": ms.name,
            "Signal": _score_signal(ms.score),
            "Score": int(ms.score),
            "Tier": ms.tier or " - ",
            "Status": ms.status,
            "ID": ms.metric_id,
            "Why": ms.why,
        }
        for ms in score_result.metric_scores
    ]
    st.markdown(data_table_html(metric_rows), unsafe_allow_html=True)

    # --- Validation ---
    st.markdown("---")
    render_section_header(
        "Signal 06",
        "Validation",
        "Structural and cross-reference checks. Warnings do not block scoring.",
    )
    if validation.ok:
        st.success("No structural errors. Review warnings below.")
    else:
        st.error("Structural errors found. Fix these first.")
    if issues:
        issue_rows = [
            {
                "Location": getattr(i, "human_location", "") or getattr(i, "path", ""),
                "Severity": (
                    i.severity,
                    _SEV_TONE.get((i.severity or "").upper(), "none"),
                ),
                "Code": i.code,
                "Message": i.message,
            }
            for i in issues
        ]
        st.markdown(data_table_html(issue_rows), unsafe_allow_html=True)
    else:
        st.caption("No issues found.")
    _render_why_it_matters(issues)

    # --- Strategy tree ---
    st.markdown("---")
    render_section_header(
        "Signal 07",
        "Strategy Tree",
        "How primary metrics ladder up through OKRs to vertical outcomes and "
        "company goals.",
    )
    _render_v2_strategy(pack)

    # --- One-page brief ---
    st.markdown("---")
    render_section_header(
        "Signal 08",
        "One-Page Brief",
        "Deterministic Markdown you can paste into a planning doc.",
    )
    st.markdown(brief_md)
    render_download_button(
        label="Download brief.md",
        data=brief_md.encode("utf-8"),
        file_name="brief.md",
        mime="text/markdown",
        key="brief_download_section",
    )


def _render_cross_vertical(uploaded_list: Any, include_samples: bool) -> None:
    """Render the cross-vertical comparison (pattern view, never a ranking)."""
    render_section_header(
        "Cross-vertical",
        "Compare Verticals",
        "Patterns across verticals - shared gaps and where to focus enablement. "
        "This is a comparison of patterns, not a single-number ranking.",
    )

    packs = []
    for uploaded in uploaded_list or []:
        try:
            data = _load_yaml_bytes(uploaded.getvalue())
        except Exception as exc:
            st.warning(f"Skipped {uploaded.name}: {exc}")
            continue
        if is_v2_pack(data):
            packs.append((uploaded.name, data))
        else:
            st.warning(f"Skipped {uploaded.name}: not a v2 vertical pack.")

    if include_samples:
        packs.extend(_load_bundled_v2_examples())

    if len(packs) < 2:
        st.info(
            "Add at least two v2 vertical packs (or include the bundled samples) "
            "to compare."
        )
        return

    view = compare_verticals(packs)

    # Verticals as columns, dimensions as rows: reads top-to-bottom, no
    # horizontal scrolling, and colour-coded as a heatmap.
    column_headers = [summary.name for summary in view.summaries]
    heat_rows = [
        (
            "Overall readiness",
            [
                (s.overall_band, _OVERALL_TONE.get(s.overall_band, "none"))
                for s in view.summaries
            ],
        ),
        (
            "Decisions ready",
            [
                (
                    f"{s.decisions_ready}/{s.decisions_total}",
                    _decisions_tone(s.decisions_ready, s.decisions_total),
                )
                for s in view.summaries
            ],
        ),
    ]
    for dim in view.dimension_names:
        heat_rows.append(
            (
                dim,
                [
                    (
                        s.dimensions.get(dim, " - "),
                        _DIM_TONE.get(s.dimensions.get(dim, ""), "none"),
                    )
                    for s in view.summaries
                ],
            )
        )
    st.markdown(heatmap_table_html(column_headers, heat_rows), unsafe_allow_html=True)
    st.caption("Green = strong, amber = partial, red = weak, grey = not assessed.")
    render_download_button(
        label="Download cross_vertical_matrix.csv",
        data=cross_vertical_matrix_to_csv(view).encode("utf-8"),
        file_name="cross_vertical_matrix.csv",
        mime="text/csv",
        key="cv_matrix_download",
    )

    st.markdown("---")
    render_section_header(
        "Focus",
        "Shared Gaps",
        "Dimensions that are weak across multiple verticals - the enablement "
        "priorities a cross-vertical owner can act on.",
    )
    if view.shared_gaps:
        gap_rows = [
            {
                "Dimension": gap.dimension,
                "Weak in": gap.weak,
                "Partial in": gap.partial,
                "Verticals (weak)": ", ".join(gap.verticals_weak) or " - ",
            }
            for gap in view.shared_gaps
        ]
        st.markdown(data_table_html(gap_rows), unsafe_allow_html=True)
        render_download_button(
            label="Download shared_gaps.csv",
            data=cross_vertical_shared_gaps_to_csv(view).encode("utf-8"),
            file_name="shared_gaps.csv",
            mime="text/csv",
            key="cv_gaps_download",
        )
    else:
        st.caption("No shared gaps across the selected verticals.")
    st.caption("This view compares patterns, not a single-number ranking of verticals.")


def _render_v1_pack(pack: Dict[str, Any]) -> None:
    """Render the original v1 metric-pack review for a single pack."""
    validation = validate_metric_pack(pack)
    normalized_pack = validation.pack
    issues = list(validation.issues or [])
    score_result = score_pack(normalized_pack)
    grouped = deterministic_suggestions(normalized_pack, score_result)
    config = load_config()
    t_ready = config.thresholds["decision_ready"]
    t_caution = config.thresholds["usable_with_caution"]
    t_early = config.thresholds["early_fragile"]

    pack_meta = pack.get("pack") or {}
    if not isinstance(pack_meta, dict):
        pack_meta = {}

    metrics = normalized_pack.get("metrics", []) or []
    metric_count = len(metrics) if isinstance(metrics, list) else 0
    pack_name = str(pack_meta.get("name", "Untitled Metric Pack"))
    pack_id = str(pack_meta.get("id", " - "))
    pack_version = str(pack_meta.get("version", " - "))
    schema_version = str(pack_meta.get("schema_version", "1.0"))
    score_lbl, score_tone = score_signal(score_result.pack_score, config)
    val_label, val_detail, val_tone = validation_signal(issues)

    render_hero(
        pack_name,
        "One review pass across structure, decision risk, and strategy. "
        "The weakest metric stays visible so it does not get hidden by stronger ones.",
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
        columns=2,
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Render the Streamlit app."""
    st.set_page_config(
        page_title=APP_TITLE, layout="wide", initial_sidebar_state="expanded"
    )
    inject_theme_css()

    sidebar_examples = load_sidebar_examples()

    uploaded = None
    multi_uploads: Any = []
    include_samples = True
    with st.sidebar:
        render_sidebar_intro()
        st.header("Inputs")
        mode = st.radio(
            "Mode",
            ["Review a pack", "Compare verticals"],
            index=0,
            help="Review one pack (v1 or v2), or compare several v2 verticals.",
        )
        if mode == "Review a pack":
            uploaded = st.file_uploader(
                "Upload a metric-pack YAML", type=["yaml", "yml"]
            )
            render_sidebar_examples(sidebar_examples)
        else:
            multi_uploads = (
                st.file_uploader(
                    "Upload vertical packs",
                    type=["yaml", "yml"],
                    accept_multiple_files=True,
                )
                or []
            )
            include_samples = st.checkbox("Include bundled v2 sample packs", value=True)

    if mode == "Compare verticals":
        _render_cross_vertical(multi_uploads, include_samples)
        render_footer(FOOTER_TEXT)
        return

    if not uploaded:
        render_hero(
            "Review metric packs before they steer decisions.",
            "A quick pass for teams that want clearer metrics and fewer surprises once "
            "a KPI shows up in a dashboard or target.",
            ["Rules-based review", "No silent edits", "Optional strategy tree"],
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

    if is_v2_pack(pack):
        _render_v2_pack(pack)
    else:
        _render_v1_pack(pack)
    render_footer(FOOTER_TEXT)


if __name__ == "__main__":
    main()
