"""Generate calibration figures from saved rankings and weights."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

CALIB = REPO_ROOT / "analysis" / "calibration"
OUT = CALIB / "figures"
OUT.mkdir(exist_ok=True, parents=True)


def plot_test_retest() -> None:
    """Scatter of the user's first vs second ranking."""
    v1 = pd.read_csv(CALIB / "_user_ranking.csv", decimal=",")[["pack_id", "your_rank"]].rename(
        columns={"your_rank": "v1"}
    )
    v2 = pd.read_csv(CALIB / "_user_ranking_v2.csv").rename(columns={"user_rank_v2": "v2"})
    merged = v1.merge(v2, on="pack_id")

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(merged["v1"], merged["v2"], color="#0277bd", alpha=0.7, s=50)
    ax.plot([1, 27], [1, 27], "--", color="gray", alpha=0.5, label="y = x")

    # Annotate the biggest shifts
    merged["shift"] = (merged["v1"] - merged["v2"]).abs()
    for _, row in merged.nlargest(4, "shift").iterrows():
        ax.annotate(
            row["pack_id"],
            (row["v1"], row["v2"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
            color="#d32f2f",
        )

    ax.set_xlabel("First ranking attempt")
    ax.set_ylabel("Second ranking attempt")
    ax.set_title("Human rater test-retest reliability\n(ρ = 0.974, τ = 0.892)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "test_retest.png", dpi=120)
    plt.close(fig)


def plot_three_way_ranks() -> None:
    """Scatter matrix of user-consensus, Claude, and MMF rankings."""
    df = pd.read_csv(CALIB / "all_rankings_merged.csv")

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    pairs = [
        ("user_consensus", "claude_rank", "Claude", axes[0]),
        ("user_consensus", "mmf_rank", "MMF", axes[1]),
        ("claude_rank", "mmf_rank", "MMF", axes[2]),
    ]
    for xcol, ycol, ylabel, ax in pairs:
        xname = xcol.replace("_", " ").title()
        ax.scatter(df[xcol], df[ycol], color="#0277bd", alpha=0.7, s=40)
        ax.plot([1, 27], [1, 27], "--", color="gray", alpha=0.5)
        ax.set_xlabel(xname)
        ax.set_ylabel(ylabel)
        ax.set_xlim(0, 28)
        ax.set_ylim(0, 28)
        ax.grid(alpha=0.3)

    axes[0].set_title("User vs Claude (ρ=0.98)")
    axes[1].set_title("User vs MMF (ρ=0.95)")
    axes[2].set_title("Claude vs MMF (ρ=0.95)")

    fig.suptitle("Rank agreement across three rankers", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT / "three_way_ranks.png", dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_fitted_weights() -> None:
    """Bar chart of MMF baseline vs fitted weights."""
    results = json.loads((CALIB / "calibration_results.json").read_text())
    fitted = results["fitted_weights"]
    mmf = results["mmf_baseline_weights"]

    gaps = list(mmf.keys())
    mmf_vals = [mmf[g] for g in gaps]
    fit_vals = [fitted[g] for g in gaps]

    x = np.arange(len(gaps))
    width = 0.38

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - width / 2, mmf_vals, width, label="MMF default", color="#90caf9")
    ax.bar(x + width / 2, fit_vals, width, label="Fitted (ridge)", color="#0277bd")

    ax.set_xticks(x)
    ax.set_xticklabels([g.replace("_", "\n") for g in gaps])
    ax.set_ylabel("Weight (scale: max fitted = 10)")
    ax.set_title("Fitted weights from consensus human ranking vs MMF defaults")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")

    for i, (m, f) in enumerate(zip(mmf_vals, fit_vals)):
        diff = f - m
        if abs(diff) > 0.5:
            color = "#d32f2f" if diff > 0 else "#1976d2"
            ax.annotate(
                f"{diff:+.1f}",
                (i + width / 2, max(m, f) + 0.3),
                ha="center",
                fontsize=9,
                color=color,
                weight="bold",
            )

    fig.tight_layout()
    fig.savefig(OUT / "fitted_weights.png", dpi=120)
    plt.close(fig)


def main() -> None:
    plot_test_retest()
    plot_three_way_ranks()
    plot_fitted_weights()
    print(f"Wrote figures to {OUT}")


if __name__ == "__main__":
    main()
