"""Bayesian robustness analysis for measurement-maturity-framework.

This script runs the full Bayesian analysis end-to-end and saves outputs
that feed directly into analysis/bayesian_robustness.ipynb. Running this
file regenerates the notebook-ready figures and tables.

Outputs
-------
analysis/outputs/synthetic_summary.csv
    Per-pack summary: rule-based, posterior mean, CI bounds, std.
analysis/outputs/rank_correlation.txt
    Spearman rho and Kendall tau between rule-based and posterior rankings.
analysis/outputs/divergence_table.csv
    Packs where |posterior_mean - rule_based| is largest.
analysis/outputs/posterior_distributions.png
    Small-multiples of posterior densities for selected packs.
analysis/outputs/ci_width_vs_gap_count.png
    CI width as a function of total gap count.
analysis/outputs/rule_based_vs_posterior_scatter.png
    Scatter of rule-based vs posterior mean scores.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from scipy.stats import kendalltau, spearmanr

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mmf.bayesian_scoring import score_pack_bayesian  # noqa: E402
from mmf.scoring import score_pack  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "synthetic_packs"
OUTPUTS = REPO_ROOT / "analysis" / "outputs"
OUTPUTS.mkdir(exist_ok=True, parents=True)

N_SAMPLES = 3000
SEED = 42
CI_LEVEL = 0.90


def _count_gaps(pack: dict) -> int:
    """Return the total number of gaps across all metrics in the pack."""
    total = 0
    for m in pack.get("metrics", []):
        score = score_pack({"metrics": [m]}).metric_scores[0]
        total += len(score.gaps)
    return total


def build_summary() -> pd.DataFrame:
    """Score every synthetic pack under both methods and return a summary frame."""
    rows = []
    for path in sorted(FIXTURES.glob("*.yaml")):
        with path.open() as f:
            pack = yaml.safe_load(f)
        r = score_pack_bayesian(pack, n_samples=N_SAMPLES, seed=SEED, ci_level=CI_LEVEL)
        rows.append(
            {
                "pack": path.stem,
                "n_metrics": len(pack.get("metrics", [])),
                "total_gaps": _count_gaps(pack),
                "rule_based": r.rule_based_score,
                "posterior_mean": r.point_estimate,
                "ci_lower": r.ci_lower,
                "ci_upper": r.ci_upper,
                "ci_width": r.ci_upper - r.ci_lower,
                "std": r.std,
                "divergence": r.point_estimate - r.rule_based_score,
            }
        )
    return pd.DataFrame(rows).sort_values("rule_based", ascending=False).reset_index(drop=True)


def rank_correlation(summary: pd.DataFrame) -> dict:
    """Compute rank agreement between rule-based and posterior mean scores."""
    rho, p_rho = spearmanr(summary["rule_based"], summary["posterior_mean"])
    tau, p_tau = kendalltau(summary["rule_based"], summary["posterior_mean"])
    return {"spearman_rho": rho, "spearman_p": p_rho, "kendall_tau": tau, "kendall_p": p_tau}


def plot_scatter(summary: pd.DataFrame, out_path: Path) -> None:
    """Scatter of rule-based vs posterior-mean scores with CI bars."""
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.errorbar(
        summary["rule_based"],
        summary["posterior_mean"],
        yerr=[
            summary["posterior_mean"] - summary["ci_lower"],
            summary["ci_upper"] - summary["posterior_mean"],
        ],
        fmt="o",
        capsize=3,
        alpha=0.7,
        color="#0277bd",
        ecolor="#90caf9",
    )
    lims = [summary["rule_based"].min() - 3, 102]
    ax.plot(lims, lims, "--", color="gray", alpha=0.5, label="y = x")
    ax.set_xlabel("Rule-based score")
    ax.set_ylabel("Bayesian posterior mean (with 90% CI)")
    ax.set_title("Rule-based vs Bayesian posterior across synthetic packs")
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_ci_width_vs_gaps(summary: pd.DataFrame, out_path: Path) -> None:
    """CI width as a function of total gap count in the pack."""
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(summary["total_gaps"], summary["ci_width"], color="#0277bd", alpha=0.7)
    ax.set_xlabel("Total gaps across all metrics in pack")
    ax.set_ylabel("90% CI width (score points)")
    ax.set_title("Score uncertainty grows with gap count")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_posterior_distributions(
    selected_packs: list[str],
    out_path: Path,
) -> None:
    """Small multiples showing posterior densities for selected packs."""
    fig, axes = plt.subplots(1, len(selected_packs), figsize=(4 * len(selected_packs), 4), sharey=True)
    if len(selected_packs) == 1:
        axes = [axes]
    for ax, name in zip(axes, selected_packs):
        with (FIXTURES / f"{name}.yaml").open() as f:
            pack = yaml.safe_load(f)
        # Draw raw samples by running many small batches — reuse seeded sampler
        # For density plotting we need the raw draws, so call the lower-level
        # machinery directly.
        from mmf.bayesian_scoring import _sample_weights, _score_pack_with_weights
        from mmf.config import load_config

        config = load_config()
        rng = np.random.default_rng(SEED)
        samples = _sample_weights(config, N_SAMPLES, rng)
        draws = np.empty(N_SAMPLES)
        for i in range(N_SAMPLES):
            w = {k: samples[k][i] for k in samples}
            draws[i] = _score_pack_with_weights(pack, config, w).pack_score

        rule_based = score_pack(pack).pack_score
        ax.hist(draws, bins=40, color="#0277bd", alpha=0.6, density=True)
        ax.axvline(rule_based, color="red", linestyle="--", label=f"rule-based = {rule_based:.1f}")
        ax.axvline(np.mean(draws), color="black", linestyle="-", alpha=0.6, label=f"posterior mean = {np.mean(draws):.1f}")
        ax.set_title(name, fontsize=10)
        ax.set_xlabel("Pack score")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Posterior density")
    fig.suptitle("Posterior pack-score distributions across the quality spectrum", y=1.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    """Run the full analysis and save all outputs."""
    print(f"Running Bayesian robustness analysis on {len(list(FIXTURES.glob('*.yaml')))} synthetic packs")
    print(f"  n_samples={N_SAMPLES}, seed={SEED}, ci_level={CI_LEVEL}")
    print()

    summary = build_summary()
    summary.to_csv(OUTPUTS / "synthetic_summary.csv", index=False)
    print(f"Wrote {OUTPUTS / 'synthetic_summary.csv'}")

    corr = rank_correlation(summary)
    with (OUTPUTS / "rank_correlation.txt").open("w") as f:
        f.write(
            f"Spearman rho = {corr['spearman_rho']:.4f} (p = {corr['spearman_p']:.2e})\n"
            f"Kendall tau  = {corr['kendall_tau']:.4f} (p = {corr['kendall_p']:.2e})\n"
        )
    print(f"Spearman rho = {corr['spearman_rho']:.4f}")
    print(f"Kendall tau  = {corr['kendall_tau']:.4f}")
    print()

    # Top 5 divergences
    div = summary.reindex(
        summary["divergence"].abs().sort_values(ascending=False).index
    ).head(5)
    div.to_csv(OUTPUTS / "divergence_table.csv", index=False)
    print("Top 5 divergences (|posterior - rule_based|):")
    print(div[["pack", "rule_based", "posterior_mean", "divergence", "ci_width"]].to_string(index=False))
    print()

    plot_scatter(summary, OUTPUTS / "rule_based_vs_posterior_scatter.png")
    plot_ci_width_vs_gaps(summary, OUTPUTS / "ci_width_vs_gap_count.png")
    plot_posterior_distributions(
        ["prod_ready_03", "mixed_05", "early_02", "edge_single_worst"],
        OUTPUTS / "posterior_distributions.png",
    )
    print(f"Wrote figures to {OUTPUTS}")


if __name__ == "__main__":
    main()
