"""Build the weight calibration notebook.

Assembles analysis/weight_calibration.ipynb from the saved calibration
artefacts. Run after calibration_results.json and figures/ are generated.
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK_PATH = REPO_ROOT / "analysis" / "weight_calibration.ipynb"


def md(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(text)


def code(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(source)


def build() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = []

    nb.cells.append(md(
        "# Weight Calibration\n"
        "\n"
        "**Measurement Maturity Framework — fitting deduction weights against human judgment**\n"
        "\n"
        "The Bayesian robustness notebook showed that MMF's rule-based weights are\n"
        "stable under weight uncertainty — within a plausible range, the weights\n"
        "don't strongly affect pack rankings. That's a *necessary* condition for\n"
        "the framework to be trustworthy. This notebook tests a *sufficient* one:\n"
        "are the specific weights actually close to what a human analyst would\n"
        "choose if they ranked packs by decision-readiness and the weights were\n"
        "fit to match?\n"
        "\n"
        "The short answer: **mostly yes, with three specific revisions.** MMF\n"
        "agrees with a consensus human ranking at ρ = 0.95. A ridge-regressed\n"
        "weight configuration bumps that to ρ = 0.99, and the fitted weights\n"
        "reveal three substantive MMF corrections: `missing_sql` doubled,\n"
        "`missing_owner` up 50%, `tier_v0` halved.\n"
        "\n"
        "## Scope, caveats, and what this is not\n"
        "\n"
        "This is a calibration **attempt**, not a definitive calibration. A\n"
        "real calibration would use at least three independent human raters,\n"
        "ideally drawn from different professional backgrounds. This one has:\n"
        "\n"
        "- **One human rater** (the project author), who ranked the 27 synthetic\n"
        "  packs twice, a few minutes apart, with different gap-categorisation\n"
        "  models between the two attempts.\n"
        "- **One LLM rater** (Claude), which ranked the same 27 packs using\n"
        "  documented first-principles weights deliberately chosen to differ\n"
        "  from MMF's. The LLM ranking was recorded before the human\n"
        "  finalised theirs.\n"
        "- **A consensus** built by averaging the three ranks.\n"
        "\n"
        "The honest limitations that come with this setup:\n"
        "\n"
        "1. **The author is not independent of the framework.** They built MMF.\n"
        "   Their intuition about decision-readiness is informed by the same\n"
        "   reasoning that produced MMF's weights.\n"
        "2. **The LLM rater shares methodological homogeneity with the author.**\n"
        "   Both reason about metric quality in roughly the same idiom; that\n"
        "   pushes their rankings toward agreement independent of whether either\n"
        "   is correct.\n"
        "3. **Rankers were not fully blinded to each other.** The LLM's ranking\n"
        "   output was visible in the session before the human finalised theirs.\n"
        "   This was an unavoidable setup limitation.\n"
        "4. **n = 27**. Ridge regression with 7 features on 27 packs is\n"
        "   susceptible to overfitting. The fitted weights should be read as a\n"
        "   directional signal about weight revisions, not as a definitive\n"
        "   replacement configuration.\n"
        "5. **Synthetic packs, not real ones.** The packs were generated\n"
        "   parametrically by `analysis/generate_synthetic_packs.py`. Real packs\n"
        "   might show different weight dynamics.\n"
        "\n"
        "What this notebook *does* support: a defensible directional argument\n"
        "that MMF's `missing_sql` is underweighted, `tier_v0` is overweighted,\n"
        "and the overall weight structure is broadly sensible.\n"
        "\n"
        "What it does not support: a replacement weight configuration that\n"
        "should be shipped without further validation."
    ))

    nb.cells.append(code(
        "# Setup\n"
        "import json\n"
        "import sys\n"
        "from pathlib import Path\n"
        "\n"
        "import matplotlib.pyplot as plt\n"
        "import numpy as np\n"
        "import pandas as pd\n"
        "from scipy.stats import kendalltau, spearmanr\n"
        "\n"
        "REPO_ROOT = Path.cwd().parent if Path.cwd().name == 'analysis' else Path.cwd()\n"
        "sys.path.insert(0, str(REPO_ROOT))\n"
        "\n"
        "CALIB = REPO_ROOT / 'analysis' / 'calibration'\n"
        "FIG = CALIB / 'figures'\n"
        "print(f'Calibration artefacts: {CALIB}')"
    ))

    # ---------------------------------------------------------------------
    # Test-retest
    # ---------------------------------------------------------------------

    nb.cells.append(md(
        "## Test-retest reliability of the human rater\n"
        "\n"
        "Before any calibration, a question that's rarely asked in calibration\n"
        "studies (because most use a single pass): **how stable is the human\n"
        "rater's ranking?** If the same person ranked the same 27 packs twice,\n"
        "how much would the rankings agree?\n"
        "\n"
        "The rater here did exactly that. Between the first and second\n"
        "attempt, they explicitly re-categorised their own mental model of\n"
        "gap severity (in the first attempt V0 was critical, in the second it\n"
        "was medium; description moved the opposite way). Despite that model\n"
        "change, the rank agreement between attempts is:\n"
        "\n"
        "- Spearman ρ = 0.974\n"
        "- Kendall τ = 0.892\n"
        "\n"
        "This matters for interpreting everything else in this notebook. If\n"
        "test-retest reliability had been low (say τ < 0.75), any calibration\n"
        "built on the human ranking would be building on noise. At τ = 0.89,\n"
        "the rater is stable enough for the calibration to mean something —\n"
        "even though their own reasoning about *why* certain packs scored as\n"
        "they did changed between attempts."
    ))

    nb.cells.append(code(
        "from IPython.display import Image, display\n"
        "display(Image(str(FIG / 'test_retest.png')))\n"
        "\n"
        "v1 = pd.read_csv(CALIB / '_user_ranking.csv', decimal=',')[['pack_id', 'your_rank']].rename(columns={'your_rank': 'v1'})\n"
        "v2 = pd.read_csv(CALIB / '_user_ranking_v2.csv').rename(columns={'user_rank_v2': 'v2'})\n"
        "merged = v1.merge(v2, on='pack_id')\n"
        "rho, _ = spearmanr(merged['v1'], merged['v2'])\n"
        "tau, _ = kendalltau(merged['v1'], merged['v2'])\n"
        "print(f'Test-retest: Spearman={rho:.4f}, Kendall={tau:.4f}')\n"
        "\n"
        "merged['shift'] = (merged['v1'] - merged['v2']).abs()\n"
        "print('\\nLargest shifts between attempts:')\n"
        "print(merged.nlargest(5, 'shift')[['pack_id', 'v1', 'v2', 'shift']].to_string(index=False))"
    ))

    nb.cells.append(md(
        "The five biggest re-ranks are substantively interesting. `prod_ready_02`\n"
        "moved from rank 3 to rank 8 because its missing descriptions became a\n"
        "bigger concern in the rater's second model. `edge_all_v0_but_documented`\n"
        "moved from rank 10 to rank 5 because V0 was demoted from critical to\n"
        "medium. These are principled reassessments, not noise — and the high\n"
        "overall agreement tells us that across most packs, the underlying\n"
        "ordering held steady.\n"
        "\n"
        "The average of the two attempts is used as the human consensus in the\n"
        "rest of this analysis."
    ))

    # ---------------------------------------------------------------------
    # Three-way ranking comparison
    # ---------------------------------------------------------------------

    nb.cells.append(md(
        "## Three-way ranking agreement\n"
        "\n"
        "With the human consensus (mean of two attempts), the LLM ranking, and\n"
        "MMF's rule-based scores, we can measure pairwise agreement."
    ))

    nb.cells.append(code(
        "df = pd.read_csv(CALIB / 'all_rankings_merged.csv')\n"
        "\n"
        "pairs = [\n"
        "    ('user_consensus', 'claude_rank', 'User vs Claude'),\n"
        "    ('user_consensus', 'mmf_rank', 'User vs MMF'),\n"
        "    ('claude_rank', 'mmf_rank', 'Claude vs MMF'),\n"
        "]\n"
        "print(f'{\"pair\":<24} {\"Spearman\":>10} {\"Kendall\":>10}')\n"
        "print('-' * 48)\n"
        "for a, b, label in pairs:\n"
        "    rho, _ = spearmanr(df[a], df[b])\n"
        "    tau, _ = kendalltau(df[a], df[b])\n"
        "    print(f'{label:<24} {rho:>10.4f} {tau:>10.4f}')\n"
        "\n"
        "display(Image(str(FIG / 'three_way_ranks.png')))"
    ))

    nb.cells.append(md(
        "Three observations worth naming:\n"
        "\n"
        "1. **User-Claude agreement (τ=0.92) is higher than either-vs-MMF\n"
        "   (τ≈0.82-0.84).** This suggests the two human-ish rankers share some\n"
        "   intuition that MMF's weights don't fully capture.\n"
        "2. **MMF still performs well** — a Spearman ρ of 0.94-0.95 against human\n"
        "   judgment is a good baseline, especially for a rule-based scorer with\n"
        "   asserted weights.\n"
        "3. **The disagreements are concentrated.** Most rankings track closely;\n"
        "   a small number of packs account for most of the rank difference.\n"
        "   Those packs are the ones that tell us what to fix."
    ))

    # ---------------------------------------------------------------------
    # Fitted weights
    # ---------------------------------------------------------------------

    nb.cells.append(md(
        "## Fitted weights\n"
        "\n"
        "To derive weights that best explain consensus human ranking, we fit a\n"
        "ridge regression (positive=True to force non-negative weights) with\n"
        "gap counts per metric as features and the mean rank as the target.\n"
        "Ridge regularisation (α=1.0) dampens the tendency of small-n fits to\n"
        "produce extreme coefficients.\n"
        "\n"
        "The resulting weights, scaled so the largest fitted weight equals MMF's\n"
        "largest (10):"
    ))

    nb.cells.append(code(
        "display(Image(str(FIG / 'fitted_weights.png')))\n"
        "\n"
        "results = json.loads((CALIB / 'calibration_results.json').read_text())\n"
        "mmf = results['mmf_baseline_weights']\n"
        "fit = results['fitted_weights']\n"
        "comparison = pd.DataFrame({\n"
        "    'gap': list(mmf.keys()),\n"
        "    'mmf': list(mmf.values()),\n"
        "    'fitted': [fit[k] for k in mmf],\n"
        "})\n"
        "comparison['delta'] = comparison['fitted'] - comparison['mmf']\n"
        "print(comparison.to_string(index=False))"
    ))

    nb.cells.append(md(
        "### What the fitted weights say\n"
        "\n"
        "**`missing_sql` doubles (5 → 10).** Both rankers independently penalised\n"
        "missing SQL more than MMF does. Absence of SQL means the metric cannot\n"
        "be independently reproduced or audited, and the two human-ish rankers\n"
        "treated that as nearly as severe as any single gap could be.\n"
        "\n"
        "**`missing_owner` up 50% (5 → 7.5).** No accountable team means no one\n"
        "to answer questions when the metric drifts. Both rankers weighted this\n"
        "above MMF's default.\n"
        "\n"
        "**`tier_v0` halved (10 → 5.4).** The largest correction. MMF treats V0\n"
        "as the most severe single gap; the calibration suggests it should be\n"
        "mid-weight. Interpretation: V0 is a *signal* that a metric is a\n"
        "temporary proxy, and when the proxy is otherwise well-documented (SQL,\n"
        "owner, tests), the V0 tag should not dominate the score.\n"
        "\n"
        "**`missing_grain` doubles (2 → 3.9).** Knowing what one row represents\n"
        "is structurally important — the human rater explicitly called this out\n"
        "as a medium-severity gap in their second ranking.\n"
        "\n"
        "**`missing_description`, `missing_tests`, `missing_unit` are roughly\n"
        "unchanged or slightly revised downward.** MMF's weights for these are\n"
        "broadly correct.\n"
        "\n"
        "### How much does this improve predictive power?\n"
        "\n"
        "Under MMF's default weights, the pack ranking agrees with the consensus\n"
        "human ranking at Spearman ρ = 0.953. Under fitted weights, that rises\n"
        "to ρ = 0.993 — an improvement of about 0.04 in correlation, which\n"
        "corresponds to roughly twice as few rank inversions.\n"
        "\n"
        "This should be read carefully. The fitted weights will always agree\n"
        "with the consensus better than MMF's weights, because the fit is\n"
        "optimising for exactly that agreement on exactly this data. The real\n"
        "question is whether the weight revisions would generalise to a larger\n"
        "or more diverse corpus. With only 27 packs, that question cannot be\n"
        "answered here."
    ))

    # ---------------------------------------------------------------------
    # Recommendations
    # ---------------------------------------------------------------------

    nb.cells.append(md(
        "## Recommendations for MMF — and what was actually shipped\n"
        "\n"
        "Three fitted weight changes survive the caveats above and are the\n"
        "directional findings worth recording. Below each finding is the\n"
        "actual disposition — shipped, held, or held with a structural\n"
        "alternative — so this notebook does not overclaim influence on\n"
        "the live framework.\n"
        "\n"
        "### Finding 1 — `missing_sql` is underweighted\n"
        "\n"
        "**Recommendation:** Increase `missing_sql` from -5 to -8 or -10.\n"
        "Both the human rater (across two attempts) and the LLM rater placed\n"
        "SQL absence as the most severe single gap. It also aligns with an\n"
        "independent design critique in\n"
        "[SCORING_METHODOLOGY.md](../SCORING_METHODOLOGY.md) that\n"
        "`missing_sql` is too coarse when it fires for structurally\n"
        "unreviewable implementations.\n"
        "\n"
        "**Disposition: structural change shipped; magnitude change held.**\n"
        "The framework now splits the gap into\n"
        "`missing_sql_temporary` (-3) and `missing_sql_structural` (-12),\n"
        "selected by an optional `implementation_type` field on each metric.\n"
        "This addresses the structural form of the critique without relying\n"
        "on a small-n magnitude fit. The magnitude revision to the default\n"
        "`missing_sql` (bumping from -5 to -8) has intentionally not been\n"
        "shipped.\n"
        "\n"
        "### Finding 2 — `tier_v0` is overweighted\n"
        "\n"
        "**Recommendation:** Reduce `tier_v0` from -10 to -5 or -6. A V0 tag\n"
        "is useful information, not a severe defect. Over-penalising it makes\n"
        "V0 tagging painful and discourages the honest declaration of metric\n"
        "instability that the framework is trying to encourage.\n"
        "\n"
        "**Disposition: held.** Shipping this revision would require re-running\n"
        "the robustness analysis, updating 27 synthetic pack scores, updating\n"
        "case study expected scores, and updating regression tests — all for\n"
        "a change justified by two rankers on synthetic data. Not a defensible\n"
        "trade when the notebook itself cautions against shipping without\n"
        "more rigour.\n"
        "\n"
        "### Finding 3 — `missing_owner` is slightly underweighted\n"
        "\n"
        "**Recommendation:** Increase `missing_owner` from -5 to -7.\n"
        "Ownership gaps are process failures that compound over time; the\n"
        "fit supports treating them as slightly more severe than MMF does.\n"
        "\n"
        "**Disposition: held.** Same reasoning as Finding 2.\n"
        "\n"
        "The remaining fitted revisions (grain up, tests slightly down) are\n"
        "within the noise of a single-rater small-n calibration and are not\n"
        "defensible recommendations.\n"
        "\n"
        "### What this calibration cannot tell us\n"
        "\n"
        "- Whether the improved weights generalise beyond the 27 synthetic packs\n"
        "- Whether a more diverse rater pool would produce different weights\n"
        "- Whether there are interaction terms (e.g. 'V0 with no owner' should\n"
        "  be more than the sum of its parts) that a linear model can't capture\n"
        "- Whether the weights should vary by metric tier (V0 vs V1 vs V2+)\n"
        "\n"
        "Each of these is future work that would require either more raters,\n"
        "more packs, or more sophisticated model structure."
    ))

    # ---------------------------------------------------------------------
    # Reproducibility
    # ---------------------------------------------------------------------

    nb.cells.append(md(
        "## Reproducibility\n"
        "\n"
        "All artefacts are saved in `analysis/calibration/`:\n"
        "\n"
        "- `_user_ranking.csv` — human rater's first attempt\n"
        "- `_user_ranking_v2.csv` — human rater's second attempt\n"
        "- `_claude_ranking.csv` — LLM ranker's ranking\n"
        "- `_mmf_reference_scores.csv` — MMF scores (not shown to rankers)\n"
        "- `all_rankings_merged.csv` — all rankings joined per pack\n"
        "- `calibration_results.json` — fitted weights and summary statistics\n"
        "- `figures/` — PNG outputs used in this notebook\n"
        "\n"
        "The notebook itself is regenerated from `analysis/build_calibration_notebook.py`;\n"
        "figures are regenerated from `analysis/build_calibration_figures.py`.\n"
        "Both scripts consume the CSVs above and are deterministic given those\n"
        "inputs."
    ))

    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10+"},
    }
    return nb


def main() -> None:
    nb = build()
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with NOTEBOOK_PATH.open("w") as f:
        nbf.write(nb, f)
    print(f"Wrote {NOTEBOOK_PATH}")


if __name__ == "__main__":
    main()
