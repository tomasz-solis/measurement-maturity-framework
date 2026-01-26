# app.py
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import streamlit as st
import yaml

from mmf.validator import validate_metric_pack
from mmf.scoring import score_pack
from mmf.suggestions import deterministic_suggestions



APP_TITLE = "Measurement Maturity Framework — YAML Auditor"
FOOTER_TEXT = "Deterministic checks. No silent edits. Schema-valid ≠ decision-ready. Treat suggestions as a checklist, not a verdict."


# -----------------------------
# Mermaid integration (safe)
# -----------------------------

def _try_get_strategy_mermaid_builder() -> Optional[Callable[[Dict[str, Any]], str]]:
    """
    Returns build_strategy_mermaid(pack) if present, otherwise None.
    Never raises.
    """
    try:
        from mmf.mermaid import build_strategy_mermaid  # type: ignore
        if callable(build_strategy_mermaid):
            return build_strategy_mermaid
    except Exception:
        return None
    return None


def _try_get_mermaid_renderer() -> Optional[Callable[..., None]]:
    """
    Returns render_mermaid(code, height=...) if present, otherwise None.
    Never raises.
    """
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
    data = yaml.safe_load(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Top-level YAML must be a mapping (object).")
    return data


def _dump_yaml_text(obj: Any) -> str:
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
    # app.py is expected to live in repo root (or close enough).
    # We treat its parent as the root for template/examples lookup.
    return Path(__file__).resolve().parent


def _read_text_if_exists(path: Path) -> Optional[str]:
    try:
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8")
    except Exception:
        return None
    return None


def _find_first_yaml_in_dir(dir_path: Path) -> Optional[Path]:
    if not dir_path.exists() or not dir_path.is_dir():
        return None

    candidates = sorted(list(dir_path.glob("*.yaml")) + list(dir_path.glob("*.yml")))
    return candidates[0] if candidates else None


def _default_metric_template_yaml() -> str:
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
    root = _repo_root()

    # Metric template: prefer repo file if present, else fallback.
    template_path = root / "templates" / "metric_template.yaml"
    metric_template = _read_text_if_exists(template_path) or _default_metric_template_yaml()

    pack_template_path = root / "templates" / "metric_pack_template.yaml"
    pack_template = _read_text_if_exists(pack_template_path)

    # Example pack: pick first YAML in examples/
    examples_dir = root / "examples"
    example_path = _find_first_yaml_in_dir(examples_dir)
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
    sev = (sev or "").upper()
    return {"ERROR": 0, "WARNING": 1, "INFO": 2}.get(sev, 9)


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")

    st.title(APP_TITLE)
    st.caption("Upload a metric-pack YAML to validate it, score it, and generate deterministic suggestions.")

    dl = _sidebar_downloads_base()

    # --- Sidebar: inputs + downloads that don't depend on upload ---
    with st.sidebar:
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
            width='stretch',
        )

        if dl.get("pack_template"):
            st.download_button(
                label="Download pack template (YAML)",
                data=dl["pack_template"].encode("utf-8"),
                file_name="metric_pack_template.yaml",
                mime="text/yaml",
                use_container_width=True,
            )
        else:
            st.caption("No pack template found in ./templates (add template/metric_pack_template.yaml to enable this download).")

        # Example pack
        if dl["example_pack"]:
            st.download_button(
                label="Download example pack (YAML)",
                data=dl["example_pack"].encode("utf-8"),
                file_name=dl["example_pack_filename"] or "example_metric_pack.yaml",
                mime="text/yaml",
                width='stretch',
            )
        else:
            st.caption("No example pack found in ./examples (add one to enable this download).")

        st.markdown("---")
        st.caption("Tip: keep IDs stable. It makes trends and governance easier later.")

    if not uploaded:
        st.info("Upload a YAML file to begin.")
        st.markdown("---")
        st.caption(FOOTER_TEXT)
        return

    # --- Parse YAML ---
    raw_bytes = uploaded.getvalue()
    try:
        pack = _load_yaml_bytes(raw_bytes)
    except Exception as e:
        st.error(f"Could not parse YAML: {e}")
        st.stop()

    # Pack header
    pack_meta = pack.get("pack") or {}
    if isinstance(pack_meta, dict):
        cols = st.columns(3)
        cols[0].metric("Pack", pack_meta.get("name", "—"))
        cols[1].metric("ID", pack_meta.get("id", "—"))
        cols[2].metric("Version", pack_meta.get("version", "—"))

    st.markdown("---")

    # 1) Validate (and normalize)
    validation = validate_metric_pack(pack)
    normalized_pack = validation.pack
    issues = list(validation.issues or [])

    # --- Sidebar: normalized download (depends on upload) ---
    normalized_yaml_text = _dump_yaml_text(normalized_pack)
    with st.sidebar:
        st.download_button(
            label="Download normalized YAML",
            data=normalized_yaml_text.encode("utf-8"),
            file_name="normalized_metric_pack.yaml",
            mime="text/yaml",
            width='stretch',
        )

    # Validation UI
    st.subheader("Validation")
    if validation.ok:
        st.success("Schema checks passed (this does not mean the pack is decision-ready).")
    else:
        st.error("Schema errors found. Fix these first — scoring still runs, but results may be misleading.")

    issues_sorted = sorted(
        issues,
        key=lambda i: (_severity_rank(getattr(i, "severity", getattr(i, "level", ""))), getattr(i, "code", "")),
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
                    "Location": getattr(i, "human_location", "") or getattr(i, "path", ""),
                    "Severity": _severity_icon(getattr(i, "severity", getattr(i, "level", ""))),
                    "Code": getattr(i, "code", ""),
                    "Message": getattr(i, "message", ""),
                }
            )
        st.dataframe(rows, width='stretch', hide_index=True)
    else:
        st.caption("No issues found.")

    with st.expander("Technical details", expanded=False):
        st.json([asdict(i) if hasattr(i, "__dict__") else i for i in issues])

    st.markdown("---")

    # 2) Scoring
    st.subheader("Scoring")
    score_result = score_pack(normalized_pack, issues=issues)

    # Pack-level score with icon
    pack_score = score_result.pack_score
    if pack_score >= 80:
        pack_icon = "🟢"
        pack_label = "Decision-ready"
    elif pack_score >= 55:
        pack_icon = "🟡"
        pack_label = "Use with caution"
    else:
        pack_icon = "🔴"
        pack_label = "Not decision-ready"

    col_a, col_b = st.columns(2)
    col_a.metric(f"{pack_icon} Pack Score", f"{pack_score:.2f}", help=f"{pack_label} (80+ = decision-ready, 55-79 = caution, <55 = risky)")

    # Threshold explanation
    st.caption("**Score thresholds:** 80-100 = decision-ready | 55-79 = usable with caution | 0-54 = early/fragile")

    # Metric-level scores with icons
    def _score_label(score: float) -> str:
        if score >= 80:
            return "🟢 Good"
        if score >= 55:
            return "🟡 Watch"
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
    st.dataframe(metric_rows, width='stretch', hide_index=True)

    st.markdown("---")

    # 3) Suggestions
    st.subheader("Suggestions")
    grouped = deterministic_suggestions(normalized_pack, score_result)

    if not grouped:
        st.caption("No suggestions.")
    else:
        metrics = normalized_pack.get("metrics", []) or []
        name_by_id = {m.get("id"): m.get("name") for m in metrics if isinstance(m, dict)}

        for mid, items in grouped.items():
            title = f"{name_by_id.get(mid, mid)} — {mid}"
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
    st.subheader("Strategy tree")
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

    st.markdown("---")
    st.caption(FOOTER_TEXT)


if __name__ == "__main__":
    main()
