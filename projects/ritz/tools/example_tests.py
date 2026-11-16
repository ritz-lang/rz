#!/usr/bin/env python3
"""Run every examples/**/test/*.ritz [[test]] suite with ritz0, with a floor.

AGAST #3729. rz.toml excludes projects/ritz/examples from `rz test --all`,
and scripts/regression.sh builds each example's src/ and runs its test.sh
but never its test/*.ritz. So nothing ran them: #1561 found three suites
(67, 69, 72_raii) that had failed to compile for months, and two test/ dirs
(73_heap, 74_autodrop) had no ritz.toml, so build.py never discovered them.

What this does, per example package that has test files (build.py's
discover_test_files, the single owner of discovery):

  build.py test <pkg> --unit-plan   build the package (integration tests
                                    fork/exec its binary)
  build.py test <pkg> --unit-file F one per test file

These are the units `rz test --all -j N` schedules (AGAST #1809), run here
on a pool of -j workers. test.sh is NOT run: regression.sh already runs it
three times over.

Verdict (judge()):
  * a file that did not pass and is not in KNOWN_FAILING fails the gate;
  * a KNOWN_FAILING file that passes fails the gate (strict xpass), as does
    an entry for a file that no longer exists, so an excuse cannot outlive
    its failure;
  * the floor: every test/*.ritz on disk, found by a plain walk that does not
    use package discovery, must have run. A test/ dir build.py cannot see
    is red, not silently skipped.

Exit 0 only if there are no problems.

Usage:  python3 tools/example_tests.py [-j N]      (from projects/ritz)
        make example-tests
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RITZ_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = RITZ_ROOT / "examples"
BUILD_PY = RITZ_ROOT / "build.py"

# Example test files that fail today, each citing the AGAST ticket that
# tracks the failure. Keys are relative to examples/. Every entry must cite
# #NNNN and name a file on disk (tools/test_example_tests.py); one that
# starts passing fails the gate until it is removed here.
KNOWN_FAILING: dict[str, str] = {}


def test_files_on_disk(examples: Path) -> set[str]:
    """Every <dir>/test/*.ritz under `examples`, outside build/ trees.

    Deliberately a plain walk, not build.py discovery: it is the floor the
    discovered set is checked against.
    """
    return {
        f.relative_to(examples).as_posix()
        for f in examples.glob("**/test/*.ritz")
        if "build" not in f.relative_to(examples).parts
    }


def judge(disk: set[str], ran: dict[str, str], known: dict[str, str]) -> list[str]:
    """Problems with a run; [] means green.

    `ran` maps a file (relative to examples/) to its status: build.py's
    run_test_file statuses ("pass", "fail", "error", "empty", "timeout"), or
    "build-failed" when its package did not build and it never ran.
    """
    problems = []
    for f in sorted(disk - ran.keys()):
        problems.append(
            f"{f}: on disk but did not run (no package "
            f"discovers it: missing ritz.toml?)"
        )
    for f, status in sorted(ran.items()):
        if status != "pass" and f not in known:
            problems.append(f"{f}: {status}")
        elif status == "pass" and f in known:
            problems.append(
                f"{f}: passes, so its KNOWN_FAILING entry "
                f"({known[f]}) is stale: remove it"
            )
    for f in sorted(known.keys() - disk):
        problems.append(f"{f}: KNOWN_FAILING entry ({known[f]}) is stale: no such file")
    return problems


def _packages_with_tests() -> list[tuple[Path, list[Path]]]:
    # build.py by path, not `import build`: that name is also a PyPI
    # distribution (test_tools_requirements.py would read it as one).
    import importlib.util

    sys.path.insert(0, str(RITZ_ROOT))  # build.py's own sibling imports
    spec = importlib.util.spec_from_file_location("ritz_buildpy_3729", BUILD_PY)
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)

    out = []
    for pkg_dir, config in build.find_all_packages(EXAMPLES):
        files = build.discover_test_files(pkg_dir, config)
        if files:
            out.append((pkg_dir, files))
    return sorted(out)


def _run(cmd: list[str], cwd: Path, env: dict) -> str:
    r = subprocess.run(
        cmd, cwd=cwd, env=env, capture_output=True, text=True, check=False
    )
    return r.stdout + r.stderr


def _test_package(
    pkg_dir: Path, files: list[Path], env: dict, tmp: Path
) -> tuple[str, dict[str, str]]:
    """Build one package, run each of its test files. (log, {file: status})"""
    rel = lambda f: f.resolve().relative_to(EXAMPLES).as_posix()
    base = [sys.executable, str(BUILD_PY), "test", str(pkg_dir)]
    key = pkg_dir.relative_to(EXAMPLES).as_posix().replace("/", "__")
    plan_path = tmp / f"{key}.plan.json"
    log = _run(base + ["--unit-plan", str(plan_path)], RITZ_ROOT, env)
    plan = json.loads(plan_path.read_text()) if plan_path.exists() else {}
    if not plan.get("built"):
        return log, {rel(f): "build-failed" for f in files}
    statuses = {}
    for f in plan["files"]:
        res = tmp / f"{key}.{Path(f).name}.json"
        log += _run(
            base + ["--unit-file", f, "--unit-result", str(res)], RITZ_ROOT, env
        )
        status = json.loads(res.read_text())["status"] if res.exists() else "error"
        statuses[rel(Path(f))] = status
    return log, statuses


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-j", "--jobs", type=int, default=min(os.cpu_count() or 1, 8))
    args = ap.parse_args(argv)

    env = os.environ.copy()
    # Without it every example fails with "Cannot find module: ritzlib.*".
    env["RITZ_PATH"] = os.pathsep.join(
        p for p in (str(RITZ_ROOT), env.get("RITZ_PATH", "")) if p
    )

    t0 = time.monotonic()
    packages = _packages_with_tests()
    ran: dict[str, str] = {}
    with (
        tempfile.TemporaryDirectory(prefix="example-tests-") as td,
        ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool,
    ):
        futures = [
            pool.submit(_test_package, p, fs, env, Path(td)) for p, fs in packages
        ]
        for (pkg_dir, _), fut in zip(packages, futures):
            log, statuses = fut.result()
            print(f"--- {pkg_dir.relative_to(EXAMPLES).as_posix()}")
            print(log.rstrip())
            ran.update(statuses)

    disk = test_files_on_disk(EXAMPLES)
    problems = judge(disk, ran, KNOWN_FAILING)
    passed = sum(1 for s in ran.values() if s == "pass")
    excused = sorted(f for f, s in ran.items() if s != "pass" and f in KNOWN_FAILING)
    print()
    print(
        f"Example [[test]] files: {len(disk)} on disk, {len(ran)} ran "
        f"({len(packages)} packages), {passed} passed, "
        f"{len(excused)} known-failing, {time.monotonic() - t0:.0f}s"
    )
    for f in excused:
        print(f"  known-failing {f}: {ran[f]} ({KNOWN_FAILING[f]})")
    if problems:
        print(f"FAIL: {len(problems)} problem(s):")
        for p in problems:
            print(f"  ✗ {p}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
