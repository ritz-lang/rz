#!/usr/bin/env python3
"""Hold the ritz0 suite to its time budget (AGAST #3453, LARB review/5 F1).

    check_test_budget.py COST_REPORT [--budget tools/test_budget.toml]
                         [--calibration CPU_CALIBRATION]

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

Exit 1 with one line per breach, 0 when everything fits, 2 when the
calibration named is missing.  Every limit is multiplied by
$RITZ_TEST_BUDGET_SCALE (default 1) for a slower machine.

CPU-seconds are not the same number on every host (AGAST #3897: the same suite
measured 1,454.5 on toffee, 2,347 on omegalisk).  CPU_CALIBRATION is what
tools/cpu_calibrate.py wrote on this host just before the suite: a fixed
workload's CPU-s.  Over the budget's

    [calibration] reference_cpu_s   that workload's CPU-s on the host the
                                    caps were set on

it is the host's factor, and every CPU figure is divided by it before it meets
a cap.  The budget line prints the raw figure, the factor and the normalised
one.  Without --calibration the factor is 1 and the line says "uncalibrated".

A host with a fixed factor (host.env's RZ_CPU_FACTOR, AGAST #4172) has
cpu_calibrate.py --factor write {"factor": F, "fixed": true} instead; F is the
factor as it stands, and the line says "fixed" rather than "measured".

RITZ_TEST_BUDGET_PARTIAL=1 says the report covers a subset of the suite (the
gate's likely-failures-first pass, AGAST #3456): only the per-file checks
apply.  The full step's report folds that subset back in, and is checked whole.

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


def host_factor(budget: dict, calibration: Path | None) -> float:
    """This host's CPU-s over the reference host's, for the same workload."""
    if calibration is None:
        return 1.0
    cal = json.loads(Path(calibration).read_text())
    if cal.get("fixed"):
        return float(cal["factor"])
    return float(cal["cpu_s"]) / float(budget["calibration"]["reference_cpu_s"])


def factor_is_fixed(calibration: Path | None) -> bool:
    """Was the factor set by the host (RZ_CPU_FACTOR), not measured?"""
    return calibration is not None and bool(
        json.loads(Path(calibration).read_text()).get("fixed"))


def check(report: dict, budget: dict, scale: float = 1.0,
          partial: bool = False, factor: float = 1.0) -> list[str]:
    """Every breach of `budget` in `report`, as one line each.

    `partial`: the report is a subset of the suite, so the suite caps and
    "this override's file is gone" cannot be judged from it.
    `factor`: the host's calibration (host_factor); CPU figures are divided
    by it before they meet a cap.
    """
    errs = []
    files = report["files"]
    default = float(budget["file"]["default_cpu_s"]) * scale
    overrides = budget["file"].get("override", {})

    for name, o in sorted(overrides.items()):
        if not o.get("ticket"):
            errs.append(f"{name}: override has no ticket; name the ticket that "
                        f"brings it under {default:.1f} s")
        if name not in files and not partial:
            errs.append(f"{name}: override for a file the suite no longer runs; "
                        f"remove it from the budget")

    for name, v in sorted(files.items()):
        cpu = float(v["cpu_s"]) / factor
        o = overrides.get(name)
        limit = float(o["cpu_s"]) * scale if o else default
        if cpu > limit:
            why = f" (override, #{o['ticket']})" if o else ""
            errs.append(f"{name}: {cpu:.1f} CPU-s over its budget of {limit:.1f}{why}, "
                        f"{v['tests']} tests")

    if partial:
        return errs

    raw = sum(float(v["cpu_s"]) for v in files.values())
    total = raw / factor
    cap = float(budget["suite"]["cpu_s"]) * scale
    if total > cap:
        errs.append(f"suite: {raw:.1f} CPU-s raw / factor {factor:.3f} = "
                    f"{total:.1f} normalised, over its cap of {cap:.1f}")

    count = sum(int(v["tests"]) for v in files.values())
    if (e := count_breach(count, budget)) is not None:
        errs.append(e)
    return errs


def count_breach(count: int, budget: dict) -> str | None:
    """The `[suite] tests` breach line for `count` tests, or None.

    Not scaled: every machine runs the same number of tests.  Shared with
    tools/check_suite_count.py, which checks a collected count before a gate
    (AGAST #4904), so both fail with this one message.
    """
    max_tests = budget["suite"].get("tests")
    if max_tests is not None and count > int(max_tests):
        return (f"suite: {count} tests over its cap of {int(max_tests)}; "
                f"collapse a matrix into table rows before adding cases")
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("report", type=Path)
    ap.add_argument("--budget", type=Path, default=DEFAULT_BUDGET)
    ap.add_argument("--calibration", type=Path, default=None,
                    help="tools/cpu_calibrate.py's report for this host (AGAST #3897)")
    a = ap.parse_args(argv)
    scale = float(os.environ.get("RITZ_TEST_BUDGET_SCALE", "1") or 1)
    partial = os.environ.get("RITZ_TEST_BUDGET_PARTIAL", "") not in ("", "0")
    report = json.loads(a.report.read_text())
    budget = load_budget(a.budget)
    if a.calibration is not None and not a.calibration.is_file():
        print(f"test budget: no calibration at {a.calibration}: "
              f"tools/cpu_calibrate.py did not run on this host")
        return 2
    factor = host_factor(budget, a.calibration)
    errs = check(report, budget, scale, partial=partial, factor=factor)
    scope = ", partial: per-file checks only" if partial else ""
    raw = sum(float(v["cpu_s"]) for v in report["files"].values())
    how = "fixed" if factor_is_fixed(a.calibration) else "measured"
    cal = (f"factor {factor:.3f} {how}" if a.calibration is not None
           else "factor 1, uncalibrated")
    cap = float(budget["suite"]["cpu_s"]) * scale
    figures = (f"{raw:.1f} CPU-s raw, {cal}, {raw / factor:.1f} normalised "
               f"(cap {cap:.1f})")
    if errs:
        print(f"test budget: {len(errs)} breach(es), {figures} "
              f"({a.budget.name}, scale {scale:g}{scope}):")
        for e in errs:
            print(f"  {e}")
        print("Size the matrix to the rule and batch it: docs/TESTING.md, "
              "\"What a ritz0 pytest case costs\".")
        return 1
    print(f"test budget: ok, {figures} across {len(report['files'])} files "
          f"({a.budget.name}, scale {scale:g}{scope})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
