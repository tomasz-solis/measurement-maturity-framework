#!/usr/bin/env python
"""CI guard: fail if any committed public pack leaks private data.

Scans the public ``examples/`` tree and exits non-zero if any pack is marked
``visibility: private`` or carries non-null ``internal_references`` (PRD FR12).
Run from the repo root: ``python scripts/check_public_packs.py``.
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional

# Allow running as a plain script (no install) by making the repo root importable.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from mmf.leak_guard import DEFAULT_GLOBS, scan_paths  # noqa: E402


def main(argv: Optional[List[str]] = None) -> int:
    globs = argv if argv else DEFAULT_GLOBS
    violations = scan_paths(globs)
    if violations:
        print("Public-pack leak guard FAILED:")
        for path in sorted(violations):
            for problem in violations[path]:
                print(f"  {path}: {problem}")
        print(
            "\nThese files must not be committed to the public repo. "
            "Set visibility to public_sample and clear internal_references, "
            "or move the pack to a git-ignored private location."
        )
        return 1
    print("Public-pack leak guard passed: no private data in committed packs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or None))
