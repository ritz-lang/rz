#!/usr/bin/env python3
"""likely_tests.py -- the ritz0 test files most likely to fail a gate.

AGAST #3456 (LARB review/5 tooling F4).  `ci_local.py` runs these files
BEFORE the rest of the gate and leaves them out of the full pytest step, so a
likely failure shows within four minutes of gate start instead of 9-11
minutes in.  A green gate runs every test once, as before.

The rule: the ritz0 test modules changed by the last COMMITS commits that
touched projects/ritz/ritz0, newest first, at most MAX_FILES, leaving out the
serial ones (below).  Reachable from HEAD, so the gated commit's own tests
lead, then a merge train's batch, then what landed on main lately.

Why recency and not the diff alone.  Replayed against the 20 gates of
Nov 12-16 whose ritz0 pytest step failed:

    test files the gated commit touched           0 / 20 caught
    + files that failed in earlier gates (top 30) 9 / 20
    this rule (80 commits, 60 files)             15 / 20, all within 240 s

A room's commit breaks a NEIGHBOUR's test, rarely its own (which it ran),
and the neighbours most at risk are the tests main gained lately: they pin
behaviour of code that is still moving.  The failure history adds nothing
over that and would need state shared between gates; this needs only git.

"Within 240 s" is gate start + 63 s (median start of ci-local) + the ritz1
build + xdist start-up + the CPU-seconds of the files ahead of the failing
one at the gates' 2.85 CPU-s per wall second.  The selection's median is
~300 CPU-s (~100 s wall), its largest ~530; more files bought no catch that
lands in time.

Serial files are left out: an `xdist_group` or `slow` file runs on one
worker, one test at a time, so in a pre-pass it would be the tail the other
workers wait on.  The full step schedules those first (ritz0/conftest.py).

    python3 tools/likely_tests.py             # print the selection
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RITZ0 = "projects/ritz/ritz0"
COMMITS = 80
MAX_FILES = 60
_SERIAL = re.compile(r"xdist_group|mark\.slow\b")


def _is_test_module(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return name.startswith("test_") and name.endswith(".py")


def select(root: Path, commits: int = COMMITS, max_files: int = MAX_FILES) -> list[str]:
    """Test files (relative to RITZ0) changed by the last `commits` commits
    that touched RITZ0, newest first, each once, that still exist and are not
    serial."""
    root = Path(root)
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "log", f"-n{commits}", "--no-merges",
             "--name-only", "--format=", "HEAD", "--", RITZ0],
            capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    prefix = RITZ0 + "/"
    seen: set[str] = set()
    picked: list[str] = []
    for path in out.splitlines():
        if not path.startswith(prefix):
            continue
        rel = path[len(prefix):]
        if rel in seen or not _is_test_module(rel):
            continue
        seen.add(rel)
        f = root / path
        if not f.is_file():  # deleted or renamed since
            continue
        if _SERIAL.search(f.read_text(errors="replace")):
            continue
        picked.append(rel)
        if len(picked) >= max_files:
            break
    return picked


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    for f in select(root):
        print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
