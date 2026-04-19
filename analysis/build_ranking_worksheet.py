"""Generate a blind ranking worksheet for calibration.

Produces a CSV showing each synthetic pack's structural content (metric
count, gap counts per metric, tier distribution) WITHOUT showing the
MMF pack score. The rater reads the contents and assigns a rank from 1
(most decision-ready) to 27 (least decision-ready).

Output: analysis/calibration/blind_ranking_worksheet.csv
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from mmf.scoring import score_pack  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "synthetic_packs"
OUTPUT_DIR = REPO_ROOT / "analysis" / "calibration"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def _describe_metric(metric: dict) -> dict:
    """Return a structural description of a single metric — no MMF score."""
    sql = metric.get("sql") or {}
    has_value_sql = bool(sql.get("value"))
    has_ratio_sql = bool(sql.get("numerator")) and bool(sql.get("denominator"))
    return {
        "tier": (metric.get("tier") or "?").upper(),
        "has_owner": bool(metric.get("accountable") or metric.get("responsible")),
        "has_sql": has_value_sql or has_ratio_sql,
        "has_tests": bool(metric.get("tests")),
        "has_description": bool(metric.get("description")),
        "has_grain": bool(metric.get("grain")),
        "has_unit": bool(metric.get("unit")),
    }


def _summarise_pack(pack: dict) -> dict:
    """Summarise a pack's structural contents without MMF scoring."""
    metrics = pack.get("metrics") or []
    descriptions = [_describe_metric(m) for m in metrics if isinstance(m, dict)]
    n = len(descriptions)

    tier_counts = Counter(d["tier"] for d in descriptions)
    gaps = Counter()
    for d in descriptions:
        if d["tier"] == "V0":
            gaps["tier_v0"] += 1
        if not d["has_owner"]:
            gaps["missing_owner"] += 1
        if not d["has_sql"]:
            gaps["missing_sql"] += 1
        if not d["has_tests"]:
            gaps["missing_tests"] += 1
        if not d["has_description"]:
            gaps["missing_description"] += 1
        if not d["has_grain"]:
            gaps["missing_grain"] += 1
        if not d["has_unit"]:
            gaps["missing_unit"] += 1

    total_gaps = sum(gaps.values())

    return {
        "n_metrics": n,
        "tier_mix": ", ".join(f"{t}:{c}" for t, c in sorted(tier_counts.items())),
        "v0_count": tier_counts.get("V0", 0),
        "missing_owner": gaps.get("missing_owner", 0),
        "missing_sql": gaps.get("missing_sql", 0),
        "missing_tests": gaps.get("missing_tests", 0),
        "missing_description": gaps.get("missing_description", 0),
        "missing_grain": gaps.get("missing_grain", 0),
        "missing_unit": gaps.get("missing_unit", 0),
        "total_gaps": total_gaps,
    }


def build_worksheet() -> pd.DataFrame:
    """Build the full worksheet frame, one row per pack."""
    rows = []
    for path in sorted(FIXTURES.glob("*.yaml")):
        with path.open() as f:
            pack = yaml.safe_load(f)
        summary = _summarise_pack(pack)
        rows.append({"pack_id": path.stem, **summary, "your_rank": ""})

    df = pd.DataFrame(rows)

    # Shuffle deterministically so the rater doesn't see packs in name order
    # (which would leak the "prod_ready / mixed / early / edge" structure).
    df = df.sample(frac=1, random_state=17).reset_index(drop=True)
    df.insert(0, "presentation_order", df.index + 1)
    return df


def mmf_reference_scores() -> pd.DataFrame:
    """Regenerate MMF scores for later calibration use.

    NOT part of the worksheet shown to the rater.
    """
    rows = []
    for path in sorted(FIXTURES.glob("*.yaml")):
        with path.open() as f:
            pack = yaml.safe_load(f)
        rows.append({
            "pack_id": path.stem,
            "mmf_score": score_pack(pack).pack_score,
        })
    return pd.DataFrame(rows)


def main() -> None:
    worksheet = build_worksheet()
    worksheet_path = OUTPUT_DIR / "blind_ranking_worksheet.csv"
    worksheet.to_csv(worksheet_path, index=False)
    print(f"Wrote worksheet: {worksheet_path}")
    print(f"  {len(worksheet)} packs, randomised presentation order")
    print("  MMF scores are NOT in the worksheet")
    print()

    ref = mmf_reference_scores()
    ref_path = OUTPUT_DIR / "_mmf_reference_scores.csv"
    ref.to_csv(ref_path, index=False)
    print(f"Wrote MMF reference (not for rater): {ref_path}")


if __name__ == "__main__":
    main()
