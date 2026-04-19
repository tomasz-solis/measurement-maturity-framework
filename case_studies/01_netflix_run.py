"""Case 1 — Netflix view redefinition (2019-2020).

Runs MMF against two reconstructed versions of the same metric:
  a) What Netflix likely had (V1, stable SQL, all checks present)
  b) What a paranoid analyst expecting redefinition would write (V0)

The gap between the two scores is the framework's signal value for
this kind of failure mode.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from mmf.scoring import score_pack  # noqa: E402


def run_and_report(yaml_path: Path, label: str) -> None:
    """Score a pack and print the result with context."""
    with yaml_path.open() as f:
        pack = yaml.safe_load(f)
    result = score_pack(pack)
    print(f"=== {label} ===")
    print(f"Pack score: {result.pack_score}")
    for ms in result.metric_scores:
        print(f"  {ms.metric_id}: {ms.score} — {ms.why}")
        if ms.gaps:
            print(f"    gaps: {ms.gaps}")
    print()


if __name__ == "__main__":
    base = Path(__file__).parent
    run_and_report(base / "01_netflix_actual.yaml", "Version A — What Netflix likely had (V1)")
    run_and_report(base / "01_netflix_cautious.yaml", "Version B — With V0 tagging (proactive caution)")
