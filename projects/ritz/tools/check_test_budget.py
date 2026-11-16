#!/usr/bin/env python3
"""Hold the ritz0 suite to its time budget (AGAST #3453, LARB review/5 F1).

    check_test_budget.py COST_REPORT [--budget tools/test_budget.toml]

COST_REPORT is what `pytest --cost-report=PATH` writes (ritz0/cost_meter.py):
CPU-seconds per test file.  The budget file sets

    [suite]  cpu_s          cap on the whole suite's CPU-seconds
             tests          cap on the number of tests (exact; never scaled):
                            each one costs the xdist controller time to
                            collect, dispatch and report, however cheap
    [file]   default_cpu_s  cap on any one file
    [file.override."<file>"]  cpu_s, ticket
                            a higher cap for one file, naming the ticket that
                            pays it down; it fails once the file is gone

Exit 1 with one line per breach, 0 when everything fits.  Every limit is
multiplied by $RITZ_TEST_BUDGET_SCALE (default 1) for a slower machine.

Why CPU-seconds: see ritz0/cost_meter.py.  Why a budget at all: the suite
went from 2,898 tests / 134 s to 39,054 / 372 s in three weeks, and nothing
said no.  A file over budget is fixed by sizing its matrix to the rule and
batching it (docs/TESTING.md, "What a ritz0 pytest case costs"), not by
raising the number.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from pathlib import Path

DEFAULT_BUDGET = Path(__file__).resolve().parent / "test_budget.toml"


def load_budget(path: Path) -> dict:
    b = tomllib.loads(Path(path).read_text())
    b.setdefault("file", {}).setdefault("override", {})
    return b


def check(report: dict, budget: dict, scale: float = 1.0) -> list[str]:
    """Every breach of `budget` in `report`, as one line each."""
    errs = []
    files = report["files"]
    default = float(budget["file"]["default_cpu_s"]) * scale
    overrides = budget["file"].get("override", {})

    for name, o in sorted(overrides.items()):
        if not o.get("ticket"):
            errs.append(f"{name}: override has no ticket; name the ticket that "
                        f"brings it under {default:.1f} s")
        if name not in files:
            errs.append(f"{name}: override for a file the suite no longer runs; "
                        f"remove it from the budget")

    for name, v in sorted(files.items()):
        cpu = float(v["cpu_s"])
        o = overrides.get(name)
        limit = float(o["cpu_s"]) * scale if o else default
        if cpu > limit:
            why = f" (override, #{o['ticket']})" if o else ""
            errs.append(f"{name}: {cpu:.1f} CPU-s over its budget of {limit:.1f}{why}, "
                        f"{v['tests']} tests")

    total = sum(float(v["cpu_s"]) for v in files.values())
    cap = float(budget["suite"]["cpu_s"]) * scale
    if total > cap:
        errs.append(f"suite: {total:.1f} CPU-s over its cap of {cap:.1f}")

    # Not scaled: every machine runs the same number of tests.
    max_tests = budget["suite"].get("tests")
    count = sum(int(v["tests"]) for v in files.values())
    if max_tests is not None and count > int(max_tests):
        errs.append(f"suite: {count} tests over its cap of {int(max_tests)}; "
                    f"collapse a matrix into table rows before adding cases")
    return errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("report", type=Path)
    ap.add_argument("--budget", type=Path, default=DEFAULT_BUDGET)
    a = ap.parse_args(argv)
    scale = float(os.environ.get("RITZ_TEST_BUDGET_SCALE", "1") or 1)
    report = json.loads(a.report.read_text())
    errs = check(report, load_budget(a.budget), scale)
    total = sum(float(v["cpu_s"]) for v in report["files"].values())
    if errs:
        print(f"test budget: {len(errs)} breach(es) ({a.budget.name}, scale {scale:g}):")
        for e in errs:
            print(f"  {e}")
        print("Size the matrix to the rule and batch it: docs/TESTING.md, "
              "\"What a ritz0 pytest case costs\".")
        return 1
    print(f"test budget: ok, {total:.1f} CPU-s across {len(report['files'])} files "
          f"({a.budget.name}, scale {scale:g})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
