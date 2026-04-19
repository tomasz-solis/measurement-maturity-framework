"""Tests for the Bayesian robustness layer.

These tests check mathematical properties rather than exact numeric
output. Exact output checks belong in regression tests; these tests
document the behavioural contract.
"""

from __future__ import annotations

import yaml
from pathlib import Path

import pytest

from mmf.bayesian_scoring import (
    score_pack_bayesian,
    _beta_params_for_weight,
    SCALE,
    CONCENTRATION,
)
from mmf.config import ScoringConfig

FIXTURES = Path(__file__).parent / "fixtures" / "synthetic_packs"


def _load_pack(name: str) -> dict:
    """Load a synthetic pack by name."""
    with (FIXTURES / f"{name}.yaml").open() as f:
        return yaml.safe_load(f)


def _average_ranks(values: list[float]) -> list[float]:
    """Return average ranks for a list of values, handling ties."""
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    position = 0

    while position < len(indexed):
        end = position + 1
        while end < len(indexed) and indexed[end][1] == indexed[position][1]:
            end += 1

        avg_rank = (position + 1 + end) / 2.0
        for original_index, _ in indexed[position:end]:
            ranks[original_index] = avg_rank

        position = end

    return ranks


def _spearman_rank_correlation(xs: list[float], ys: list[float]) -> float:
    """Return Spearman's rho without relying on SciPy."""
    if len(xs) != len(ys):
        raise ValueError("Spearman inputs must have the same length.")
    if len(xs) < 2:
        raise ValueError("Spearman correlation requires at least two values.")

    rank_x = _average_ranks(xs)
    rank_y = _average_ranks(ys)
    mean_x = sum(rank_x) / len(rank_x)
    mean_y = sum(rank_y) / len(rank_y)

    covariance = sum(
        (x - mean_x) * (y - mean_y) for x, y in zip(rank_x, rank_y, strict=True)
    )
    std_x = sum((x - mean_x) ** 2 for x in rank_x) ** 0.5
    std_y = sum((y - mean_y) ** 2 for y in rank_y) ** 0.5

    if std_x == 0 or std_y == 0:
        return 0.0

    return covariance / (std_x * std_y)


# ---------------------------------------------------------------------------
# Prior specification
# ---------------------------------------------------------------------------


class TestBetaPriors:
    """Tests for the Beta prior construction."""

    def test_beta_mean_matches_rule_based_weight(self):
        """Prior mean on the weight scale equals the rule-based weight."""
        for weight in [2, 3, 5, 10]:
            alpha, beta = _beta_params_for_weight(weight)
            beta_mean = alpha / (alpha + beta)
            expected = weight / SCALE
            assert abs(beta_mean - expected) < 1e-9

    def test_concentration_is_fixed(self):
        """Total concentration (alpha + beta) matches the module constant."""
        for weight in [2, 3, 5, 10]:
            alpha, beta = _beta_params_for_weight(weight)
            assert abs((alpha + beta) - CONCENTRATION) < 1e-9

    def test_zero_weight_is_clamped(self):
        """A zero weight clamps to a small positive alpha to keep Beta valid."""
        alpha, beta = _beta_params_for_weight(0.0)
        assert alpha > 0
        assert beta > 0


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------


class TestReproducibility:
    """Same seed produces identical posteriors."""

    def test_same_seed_identical_output(self):
        pack = _load_pack("mixed_05")
        r1 = score_pack_bayesian(pack, n_samples=500, seed=7)
        r2 = score_pack_bayesian(pack, n_samples=500, seed=7)
        assert r1.point_estimate == r2.point_estimate
        assert r1.ci_lower == r2.ci_lower
        assert r1.ci_upper == r2.ci_upper
        assert r1.std == r2.std

    def test_different_seeds_different_output(self):
        pack = _load_pack("mixed_05")
        r1 = score_pack_bayesian(pack, n_samples=500, seed=7)
        r2 = score_pack_bayesian(pack, n_samples=500, seed=8)
        assert r1.point_estimate != r2.point_estimate


# ---------------------------------------------------------------------------
# Convergence
# ---------------------------------------------------------------------------


class TestConvergence:
    """Monte Carlo error shrinks as n_samples increases."""

    def test_ci_bounds_stabilise_with_more_samples(self):
        pack = _load_pack("early_02")

        # Take three seeds at each sample size and check variance shrinks
        def ci_spread(n):
            widths = []
            for seed in [1, 2, 3]:
                r = score_pack_bayesian(pack, n_samples=n, seed=seed)
                widths.append(r.ci_upper - r.ci_lower)
            return max(widths) - min(widths)

        spread_small = ci_spread(300)
        spread_large = ci_spread(3000)
        # Spread across seeds should shrink with more samples.
        assert spread_large < spread_small


# ---------------------------------------------------------------------------
# Monotonicity and structural properties
# ---------------------------------------------------------------------------


class TestStructuralProperties:
    """Posterior behaves sensibly as pack quality varies."""

    def test_perfect_pack_has_zero_uncertainty(self):
        """If there are no gaps, sampled weights are never applied — CI is a point."""
        pack = _load_pack("prod_ready_01")  # all metrics score 100
        r = score_pack_bayesian(pack, n_samples=500, seed=42)
        assert r.std == pytest.approx(0.0, abs=1e-9)
        assert r.ci_lower == r.ci_upper == r.point_estimate == 100.0

    def test_weaker_pack_has_wider_ci(self):
        """Packs with more gaps should have wider posterior CIs."""
        r_strong = score_pack_bayesian(
            _load_pack("prod_ready_03"), n_samples=1000, seed=42
        )
        r_weak = score_pack_bayesian(_load_pack("early_02"), n_samples=1000, seed=42)
        strong_width = r_strong.ci_upper - r_strong.ci_lower
        weak_width = r_weak.ci_upper - r_weak.ci_lower
        assert weak_width > strong_width

    def test_posterior_mean_tracks_rule_based(self):
        """Posterior mean should stay within ~2 points of rule-based across packs.

        Wider drift would indicate the priors are biased, not just uncertain.
        """
        drifts = []
        for name in [
            "prod_ready_02",
            "mixed_03",
            "mixed_07",
            "early_02",
            "edge_single_worst",
        ]:
            r = score_pack_bayesian(_load_pack(name), n_samples=3000, seed=42)
            drifts.append(abs(r.point_estimate - r.rule_based_score))
        assert max(drifts) < 2.0

    def test_ci_contains_rule_based_score(self):
        """90% CI should contain the rule-based score for typical packs."""
        misses = 0
        for name in [
            "prod_ready_02",
            "prod_ready_03",
            "mixed_01",
            "mixed_03",
            "mixed_05",
            "mixed_07",
            "early_01",
            "early_02",
            "edge_single_worst",
        ]:
            r = score_pack_bayesian(_load_pack(name), n_samples=2000, seed=42)
            if not (r.ci_lower <= r.rule_based_score <= r.ci_upper):
                misses += 1
        # Across 9 packs, we expect at most 1 to miss the 90% CI just from
        # the bound being symmetric around a slightly asymmetric posterior.
        assert misses <= 1

    def test_rank_preservation_vs_rule_based(self):
        """Bayesian posterior means should rank packs similarly to rule-based scores.

        If ranks diverge wildly, the Bayesian layer is measuring something
        different from the rule-based scorer — which defeats the purpose.
        """
        names = [
            "prod_ready_01",
            "prod_ready_03",
            "prod_ready_05",
            "mixed_01",
            "mixed_03",
            "mixed_05",
            "mixed_07",
            "mixed_10",
            "early_01",
            "early_02",
            "early_05",
            "edge_single_worst",
        ]
        rb = []
        bayes = []
        for n in names:
            r = score_pack_bayesian(_load_pack(n), n_samples=1000, seed=42)
            rb.append(r.rule_based_score)
            bayes.append(r.point_estimate)

        rho = _spearman_rank_correlation(rb, bayes)
        # Rankings should be near-identical.
        assert rho > 0.95


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge-case packs that stress the sampling logic."""

    def test_single_metric_perfect(self):
        pack = _load_pack("edge_single_perfect")
        r = score_pack_bayesian(pack, n_samples=500, seed=42)
        assert r.point_estimate == 100.0
        assert r.std == 0.0
        assert len(r.metric_scores) == 1

    def test_single_metric_worst(self):
        pack = _load_pack("edge_single_worst")
        r = score_pack_bayesian(pack, n_samples=1000, seed=42)
        # Rule-based floor for single-metric max gaps is 68 (100 - 32)
        assert abs(r.rule_based_score - 68.0) < 1e-6
        # Posterior mean close to rule-based
        assert abs(r.point_estimate - 68.0) < 2.0
        # Non-zero uncertainty
        assert r.std > 2.0

    def test_empty_pack(self):
        """A pack with no metrics scores zero with zero uncertainty."""
        r = score_pack_bayesian({"metrics": []}, n_samples=200, seed=42)
        assert r.point_estimate == 0.0
        assert r.std == 0.0
        assert r.metric_scores == []

    def test_custom_config_respected(self):
        """A custom ScoringConfig is used instead of defaults."""
        custom = ScoringConfig(
            base_score=100,
            deductions={
                "v0_tier": 20,  # doubled
                "missing_accountable": 5,
                "missing_sql": 5,
                "missing_tests": 5,
                "missing_description": 3,
                "missing_grain": 2,
                "missing_unit": 2,
            },
        )
        pack = _load_pack("early_02")
        r_default = score_pack_bayesian(pack, n_samples=500, seed=42)
        r_custom = score_pack_bayesian(pack, n_samples=500, seed=42, config=custom)
        # Custom penalises V0 harder → lower point estimate for V0-heavy packs
        assert r_custom.point_estimate < r_default.point_estimate

    def test_ci_level_affects_bounds(self):
        """Wider CI level → wider bounds."""
        pack = _load_pack("mixed_05")
        r90 = score_pack_bayesian(pack, n_samples=2000, seed=42, ci_level=0.90)
        r50 = score_pack_bayesian(pack, n_samples=2000, seed=42, ci_level=0.50)
        width90 = r90.ci_upper - r90.ci_lower
        width50 = r50.ci_upper - r50.ci_lower
        assert width90 > width50


# ---------------------------------------------------------------------------
# Regression (hard-coded values)
# ---------------------------------------------------------------------------


class TestRegression:
    """Hard-coded expected values. If any of these fail, investigate before updating."""

    def test_edge_single_worst_posterior_regression(self):
        """Posterior mean and CI for edge_single_worst are stable.

        Hard-coded values are for seed=42, n_samples=2000, ci_level=0.90.
        If priors, scale, or concentration change, update these and
        confirm intentional.
        """
        pack = _load_pack("edge_single_worst")
        r = score_pack_bayesian(pack, n_samples=2000, seed=42, ci_level=0.90)
        # Stored as loose ranges — tighter than any plausible bug.
        assert 66.5 < r.point_estimate < 69.5
        assert 58.0 < r.ci_lower < 62.0
        assert 74.0 < r.ci_upper < 79.0
        assert 3.5 < r.std < 5.5
