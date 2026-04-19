"""Bayesian robustness layer for metric-pack scoring.

The rule-based scorer in mmf.scoring treats deduction weights as fixed
integers (e.g. -10 for V0 tier, -5 for missing SQL). Those weights encode
judgment about typical gap severity. This module treats them as random
variables and reports the posterior distribution of pack scores.

Why this matters
----------------
Every weight in mmf.config is asserted, not derived. A reviewer can
reasonably ask "why -10 for V0 and not -5 or -15?" This module makes
that question quantitative by sampling weights from priors centred on
the asserted values and reporting the induced uncertainty in the pack
score. A small-n calibration study
(analysis/weight_calibration.ipynb) produces directional evidence that
some current weights could be revised, but the rankings remain stable
under the Beta priors documented below, which is the robustness
property this module measures.

Prior specification
-------------------
Each deduction weight w_k is treated as a draw from a scaled Beta:

    w_k ~ Beta(alpha_k, beta_k) * SCALE

where SCALE = 20 and Beta parameters are set so that:
    - the prior mean equals rule_based_weight / SCALE
    - the total concentration alpha_k + beta_k = CONCENTRATION = 20

A concentration of 20 gives a 90% prior CI that is roughly
asserted_weight ± 3 points. Wide enough to express genuine uncertainty,
tight enough to keep samples in a plausible range.

SCALE = 20 lets the largest current weight (10, for V0 tier) sit at the
prior mean of 0.5 on the Beta scale, so the prior is symmetric and the
weight can move up or down. If SCALE were closer to the max weight, the
prior would truncate plausible upward moves.

Limits
------
This is weight-robustness analysis, not calibration. The priors encode
uncertainty about weights; they do not encode any empirical signal from
audited packs. A separate, small-n calibration study against human
ranking lives in analysis/weight_calibration.ipynb — its findings are
held as directional pending a larger rater pool, and its recommended
weight revisions have intentionally not been shipped as new defaults.

Dependencies
------------
This module depends on numpy, which is an analysis-path requirement
(see requirements-dev.txt). The rest of the mmf package has no
numerical dependency. Importing mmf.bayesian_scoring without numpy
installed will raise ImportError; install dev requirements to use
this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Any

import numpy as np

from .config import ScoringConfig, load_config
from .scoring import ScoreResult, score_pack


# Prior configuration. Separated from ScoringConfig deliberately — rule-based
# weights and Bayesian priors evolve independently.
SCALE = 20.0
CONCENTRATION = 20.0


@dataclass
class BayesianMetricScore:
    """Posterior summary for a single metric."""

    metric_id: str
    name: str
    tier: str | None
    status: str
    point_estimate: float  # posterior mean
    ci_lower: float
    ci_upper: float
    std: float
    gaps: List[str]


@dataclass
class BayesianScoreResult:
    """Posterior summary for a full pack."""

    point_estimate: float
    ci_lower: float
    ci_upper: float
    std: float
    rule_based_score: float  # for reference / divergence tracking
    metric_scores: List[BayesianMetricScore]
    n_samples: int
    ci_level: float


def _beta_params_for_weight(weight: float) -> tuple[float, float]:
    """Return (alpha, beta) for a Beta prior centred on weight / SCALE.

    The total concentration is fixed at CONCENTRATION so every deduction
    has comparable prior width in proportional terms.
    """
    mean = weight / SCALE
    # Clamp to (0, 1) with a small margin so Beta params stay positive.
    mean = min(max(mean, 1e-6), 1.0 - 1e-6)
    alpha = mean * CONCENTRATION
    beta = (1.0 - mean) * CONCENTRATION
    return alpha, beta


def _sample_weights(
    base_config: ScoringConfig,
    n_samples: int,
    rng: np.random.Generator,
) -> Dict[str, np.ndarray]:
    """Draw n_samples weight vectors, one entry per deduction key.

    Returns a dict mapping deduction_key -> array of shape (n_samples,).
    """
    sampled: Dict[str, np.ndarray] = {}
    for key, weight in base_config.deductions.items():
        alpha, beta = _beta_params_for_weight(float(weight))
        draws = rng.beta(alpha, beta, size=n_samples) * SCALE
        sampled[key] = draws
    return sampled


def _score_pack_with_weights(
    pack: Mapping[str, Any],
    base_config: ScoringConfig,
    weight_sample: Dict[str, float],
) -> ScoreResult:
    """Score the pack using one sampled weight vector.

    Builds a fresh ScoringConfig for each sample so that mutation of
    shared state is impossible. This is the hot path, so we keep
    allocations minimal: only a new deductions dict per sample.
    """
    sampled_config = ScoringConfig(
        base_score=base_config.base_score,
        deductions={k: float(v) for k, v in weight_sample.items()},
        thresholds=dict(base_config.thresholds),
        pack_floor_weight=base_config.pack_floor_weight,
    )
    return score_pack(pack, config=sampled_config)


def score_pack_bayesian(
    pack: Mapping[str, Any],
    n_samples: int = 2000,
    ci_level: float = 0.90,
    seed: int = 42,
    config: ScoringConfig | None = None,
) -> BayesianScoreResult:
    """Return posterior summary of pack score under Beta-prior weights.

    Parameters
    ----------
    pack
        The metric pack to score.
    n_samples
        Number of weight draws. 2000 is enough for stable 90% CI bounds
        on pack scores; diminishing returns above 5000.
    ci_level
        Credible interval width. 0.90 by default so the bounds are
        narrower than a 95% CI without being misleadingly tight.
    seed
        RNG seed for reproducibility.
    config
        Base scoring config. Defaults to load_config() output.

    Returns
    -------
    BayesianScoreResult with pack-level posterior summary, per-metric
    posterior summaries, and the rule-based score for reference.
    """
    if config is None:
        config = load_config()

    rng = np.random.default_rng(seed)
    weight_samples = _sample_weights(config, n_samples, rng)

    # Pack-level posterior
    pack_scores = np.empty(n_samples)
    # Per-metric posteriors: we need the metric list in stable order.
    metrics_in_pack = [m for m in (pack.get("metrics") or []) if isinstance(m, dict)]
    metric_score_draws: Dict[str, np.ndarray] = {
        m.get("id", f"unknown_{i}"): np.empty(n_samples)
        for i, m in enumerate(metrics_in_pack)
    }
    # Also keep metric_id -> dataclass fields that don't vary across samples
    metric_meta: Dict[str, Dict[str, Any]] = {}

    for i in range(n_samples):
        w = {k: weight_samples[k][i] for k in weight_samples}
        result = _score_pack_with_weights(pack, config, w)
        pack_scores[i] = result.pack_score
        for ms in result.metric_scores:
            if ms.metric_id in metric_score_draws:
                metric_score_draws[ms.metric_id][i] = ms.score
            if ms.metric_id not in metric_meta:
                metric_meta[ms.metric_id] = {
                    "name": ms.name,
                    "tier": ms.tier,
                    "status": ms.status,
                    "gaps": ms.gaps,
                }

    alpha = (1 - ci_level) / 2
    q_lo = alpha
    q_hi = 1 - alpha

    rule_based = score_pack(pack, config=config).pack_score

    metric_results = []
    for mid, draws in metric_score_draws.items():
        meta = metric_meta.get(mid, {})
        metric_results.append(
            BayesianMetricScore(
                metric_id=mid,
                name=meta.get("name", "Unnamed metric"),
                tier=meta.get("tier"),
                status=meta.get("status", "active"),
                point_estimate=float(np.mean(draws)),
                ci_lower=float(np.quantile(draws, q_lo)),
                ci_upper=float(np.quantile(draws, q_hi)),
                std=float(np.std(draws)),
                gaps=meta.get("gaps", []),
            )
        )

    return BayesianScoreResult(
        point_estimate=float(np.mean(pack_scores)),
        ci_lower=float(np.quantile(pack_scores, q_lo)),
        ci_upper=float(np.quantile(pack_scores, q_hi)),
        std=float(np.std(pack_scores)),
        rule_based_score=rule_based,
        metric_scores=metric_results,
        n_samples=n_samples,
        ci_level=ci_level,
    )
