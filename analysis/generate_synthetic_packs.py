"""Generate synthetic metric packs spanning the realistic quality space.

Packs are generated parametrically from a small set of templates so the
distribution of gaps can be documented and reproduced. Each pack is written
as a standalone YAML file that round-trips through the existing validator,
scorer, and suggestions pipeline without modification.

The generator is seeded for reproducibility. See
tests/fixtures/synthetic_packs/README.md for the resulting distribution.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml


@dataclass
class PackProfile:
    """A pack-level quality profile driving metric generation."""

    name: str
    n_metrics: int
    p_v0: float           # fraction of metrics at V0 tier
    p_missing_owner: float
    p_missing_sql: float
    p_missing_tests: float
    p_missing_desc: float
    p_missing_grain: float
    p_missing_unit: float


PROFILES: List[PackProfile] = [
    # Production-ready: rare gaps, mostly V1
    PackProfile("prod_ready_01", 5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    PackProfile("prod_ready_02", 6, 0.0, 0.0, 0.0, 0.17, 0.17, 0.0, 0.0),
    PackProfile("prod_ready_03", 4, 0.25, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    PackProfile("prod_ready_04", 5, 0.2, 0.0, 0.2, 0.0, 0.0, 0.0, 0.0),
    PackProfile("prod_ready_05", 7, 0.14, 0.0, 0.0, 0.14, 0.0, 0.14, 0.0),

    # Mixed: V0 proxies alongside V1, scattered gaps
    PackProfile("mixed_01", 6, 0.33, 0.17, 0.33, 0.33, 0.17, 0.17, 0.17),
    PackProfile("mixed_02", 5, 0.4, 0.2, 0.4, 0.4, 0.2, 0.2, 0.2),
    PackProfile("mixed_03", 8, 0.25, 0.125, 0.25, 0.375, 0.125, 0.25, 0.25),
    PackProfile("mixed_04", 4, 0.5, 0.25, 0.25, 0.5, 0.25, 0.25, 0.25),
    PackProfile("mixed_05", 6, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.17),
    PackProfile("mixed_06", 5, 0.4, 0.2, 0.6, 0.4, 0.4, 0.2, 0.2),
    PackProfile("mixed_07", 7, 0.29, 0.14, 0.43, 0.29, 0.29, 0.29, 0.14),
    PackProfile("mixed_08", 5, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4),
    PackProfile("mixed_09", 6, 0.5, 0.17, 0.33, 0.5, 0.33, 0.33, 0.33),
    PackProfile("mixed_10", 8, 0.25, 0.25, 0.5, 0.5, 0.25, 0.25, 0.25),

    # Early-stage: V0-heavy, most gaps present
    PackProfile("early_01", 4, 0.75, 0.5, 0.75, 0.75, 0.5, 0.5, 0.5),
    PackProfile("early_02", 5, 1.0, 0.6, 0.8, 0.8, 0.6, 0.6, 0.6),
    PackProfile("early_03", 3, 1.0, 0.67, 1.0, 1.0, 0.67, 0.67, 0.67),
    PackProfile("early_04", 4, 0.75, 0.75, 0.75, 1.0, 0.75, 0.75, 0.75),
    PackProfile("early_05", 5, 1.0, 0.8, 1.0, 1.0, 0.8, 0.8, 0.8),

    # Edge cases: specific shapes we want to probe
    PackProfile("edge_single_perfect", 1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    PackProfile("edge_single_worst", 1, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
    PackProfile("edge_one_bad_in_strong_pack", 6, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17),
    PackProfile("edge_all_v0_but_documented", 5, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    PackProfile("edge_v1_but_no_sql", 5, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0),
    PackProfile("edge_v1_but_no_tests", 5, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0),
    PackProfile("edge_everything_missing_except_ids", 5, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
]


def _bernoulli(p: float, rng: random.Random) -> bool:
    """Draw a single Bernoulli(p) sample."""
    return rng.random() < p


def _generate_metric(
    idx: int,
    profile: PackProfile,
    rng: random.Random,
) -> Dict[str, Any]:
    """Generate a single metric conforming to the pack profile's gap probabilities."""
    metric: Dict[str, Any] = {
        "id": f"{profile.name}_m{idx}",
        "name": f"Metric {idx} ({profile.name})",
        "status": "active",
    }

    metric["tier"] = "V0" if _bernoulli(profile.p_v0, rng) else "V1"

    if not _bernoulli(profile.p_missing_owner, rng):
        metric["accountable"] = rng.choice(["Growth Team", "Product Team", "Platform Team"])

    if not _bernoulli(profile.p_missing_sql, rng):
        metric["sql"] = {"value": f"SELECT COUNT(*) FROM events_{idx}"}

    if not _bernoulli(profile.p_missing_tests, rng):
        metric["tests"] = [{"type": "not_null"}]

    if not _bernoulli(profile.p_missing_desc, rng):
        metric["description"] = f"Synthetic metric {idx} for calibration."

    if not _bernoulli(profile.p_missing_grain, rng):
        metric["grain"] = rng.choice(["account_day", "user_week", "event"])

    if not _bernoulli(profile.p_missing_unit, rng):
        metric["unit"] = rng.choice(["count", "percent", "ratio"])

    return metric


def generate_pack(profile: PackProfile, seed: int) -> Dict[str, Any]:
    """Generate a full pack YAML structure for the given profile and seed."""
    rng = random.Random(seed)
    metrics = [_generate_metric(i, profile, rng) for i in range(1, profile.n_metrics + 1)]
    return {
        "pack": {
            "id": profile.name,
            "name": f"Synthetic — {profile.name}",
            "version": "0.1.0",
            "schema_version": "1.0",
        },
        "metrics": metrics,
    }


def write_all(output_dir: Path, base_seed: int = 42) -> List[Path]:
    """Generate all synthetic packs and write them to the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    for i, profile in enumerate(PROFILES):
        pack = generate_pack(profile, seed=base_seed + i)
        path = output_dir / f"{profile.name}.yaml"
        with path.open("w") as f:
            yaml.safe_dump(pack, f, sort_keys=False)
        paths.append(path)
    return paths


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    out = repo_root / "tests" / "fixtures" / "synthetic_packs"
    paths = write_all(out)
    print(f"Wrote {len(paths)} synthetic packs to {out}")
