#!/usr/bin/env python3
"""Hold the ritz0 suite's test count to its cap before a gate (AGAST #4904).

    check_suite_count.py [--ritz0 DIR] [--budget tools/test_budget.toml]

Collects the ritz0 suite (`pytest --collect-only`, the gate's own selection:
no path, no marker, no autoloaded plugin) and holds the count to the budget's
`[suite] tests` cap, failing with check_test_budget.py's own line.  The gate
checks the same cap on its cost report, but only after the whole ~25k-test
suite has run: on 2026-11-27 #4899 (26,817) and #4885 (26,806) each turned a
train red after a ~25 min gate on the count alone.  The count is exact, so
collecting it is enough.

~10-20 s on huburght (load ~11), so it runs in `make train-precheck`
(train.sh precheck), not in every room's smoke.

Exit 0 when the count fits, 1 over the cap, 2 when collection fails (a file
that does not import hides its tests, so its count would read low).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import check_test_budget as ctb

RITZ0 = TOOLS.parent / "ritz0"

_SUMMARY = re.compile(r"^=*\s*(\d+) tests? collected\b", re.MULTILINE)


def collect_argv() -> list[str]:
    """pytest's arguments: main.yml's ritz0 step, collecting instead of running.

    -o tmp_path_retention_policy=failed as every tools/ pytest
    (test_pytest_tmp_retention.py); -p xdist as the gate loads it (its hooks
    are in the conftest); no -n, so nothing builds ritz1 (that happens in
    xdist's configure_node or a fixture).
    """
    return [
        "-m",
        "pytest",
        "-o",
        "tmp_path_retention_policy=failed",
        "--collect-only",
        "-q",
        "--disable-plugin-autoload",
        "-p",
        "xdist",
        "-p",
        "no:cacheprovider",
    ]


def parse_count(out: str) -> int | None:
    """The N in pytest's `N tests collected` summary, if it printed one."""
    m = _SUMMARY.findall(out)
    return int(m[-1]) if m else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ritz0", type=Path, default=RITZ0)
    ap.add_argument("--budget", type=Path, default=ctb.DEFAULT_BUDGET)
    a = ap.parse_args(argv)
    budget = ctb.load_budget(a.budget)
    t0 = time.monotonic()
    proc = subprocess.run(
        [sys.executable, *collect_argv()],
        cwd=a.ritz0,
        capture_output=True,
        text=True,
        check=False,
    )
    took = time.monotonic() - t0
    count = parse_count(proc.stdout)
    if proc.returncode != 0 or count is None:
        print(
            f"suite count: collection failed (pytest exit {proc.returncode}) in {a.ritz0}:"
        )
        print(proc.stdout[-3000:] + proc.stderr[-2000:])
        return 2
    cap = budget["suite"].get("tests")
    if (e := ctb.count_breach(count, budget)) is not None:
        print(
            f"test budget: 1 breach(es), collected in {took:.1f} s ({a.budget.name}):"
        )
        print(f"  {e}")
        return 1
    print(f"suite count: ok, {count} tests (cap {cap}), collected in {took:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
