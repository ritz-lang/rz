#!/usr/bin/env python3
"""Run ritz1's unit suites: every ritz1/test/*.ritz, as `[[test]]` files.

    python3 tools/ritz1_unit.py [--dir DIR] [-j N]

`make ritz1-unit` runs this, and it is a step of CI's bootstrap job, so the
gate runs it (AGAST #1556).  The files test ritz1/src modules directly
(lexer_nfa.ritz, ...) by importing them: RITZ_PATH gets ritz1/src, so
`import lexer_nfa` resolves as it does when ritz1 is built.

Each file runs through `build.py test <ritz1> --unit-file`, the same per-file
unit `rz test` uses.  That classifies a file that runs zero tests as a
failure ("empty"), and so does this runner when it finds zero FILES: a
suite that cannot fail is not a suite, and ritz1/test/ held 23 files with no
[[test]] fn, built by nothing, until #1556.

ritz0 builds the test binaries.  ritz1 compiling these same modules is
covered by the bootstrap (ritz1 builds ritz1_selfhosted from them).

Exit 0 only if at least one file ran and every file passed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RITZ_ROOT = Path(__file__).resolve().parent.parent  # projects/ritz
RITZ1 = RITZ_ROOT / "ritz1"
TEST_DIR = RITZ1 / "test"
SRC_DIR = RITZ1 / "src"
BUILD_PY = RITZ_ROOT / "build.py"

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import exec_tmpdir  # noqa: E402  (AGAST #3704)


def discover(test_dir: Path) -> list[Path]:
    """The suite's files: test_dir/*.ritz, sorted.  Not recursive."""
    return sorted(test_dir.glob("*.ritz"))


def run_file(tfile: Path, scratch: Path) -> dict:
    """One file through build.py's --unit-file; its outcome dict.

    The child's own lines (✓ / ✗ and the failures) go to our stdout.  An
    outcome that never got written (a crash before build.py wrote it) is an
    error, never a pass.
    """
    result = scratch / f"{tfile.stem}.json"
    env = os.environ.copy()
    env["RITZ_PATH"] = ":".join(
        p for p in [str(SRC_DIR), env.get("RITZ_PATH", "")] if p
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILD_PY),
            "test",
            str(RITZ1),
            "--unit-file",
            str(tfile),
            "--unit-result",
            str(result),
        ],
        cwd=RITZ_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stdout.write(proc.stdout)
    sys.stdout.write(proc.stderr)
    try:
        return json.loads(result.read_text())
    except (OSError, ValueError):
        return {"status": "error", "passed": 0, "failed": 0}


def verdict(files: list[Path], outcomes: list[dict]) -> tuple[int, str]:
    """(exit code, summary line) for a run of `files`."""
    if not files:
        return 1, (
            "✗ ritz1-unit: found 0 test files: a gate that runs no "
            "tests cannot fail (AGAST #1556)"
        )
    tests = sum(o["passed"] for o in outcomes)
    bad = [f.name for f, o in zip(files, outcomes) if o["status"] != "pass"]
    if bad:
        return 1, (
            f"✗ ritz1-unit: {len(bad)} of {len(files)} files did not "
            f"pass: {', '.join(bad)}"
        )
    if tests == 0:  # unreachable while build.py fails empty files; kept honest
        return 1, "✗ ritz1-unit: 0 tests ran"
    return 0, f"✓ ritz1-unit: {len(files)} files, {tests} tests passed"


def main(argv: list[str] | None = None, run=run_file) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--dir",
        type=Path,
        default=TEST_DIR,
        help="directory of test files (default: ritz1/test)",
    )
    ap.add_argument("-j", type=int, default=4, help="files run at once")
    args = ap.parse_args(argv)

    # The suites build binaries under the temp dir and run them: a noexec
    # /tmp is the host's fault, not a red suite (#3704).
    try:
        exec_tmpdir.ensure_exec_tmpdir(out=sys.stdout)
    except exec_tmpdir.SetupError as e:
        print(f"SETUP ERROR: {e}")
        return exec_tmpdir.EXIT_SETUP

    files = discover(args.dir)
    print(f"=== ritz1 unit suites: {len(files)} file(s) in {args.dir} ===")
    with (
        tempfile.TemporaryDirectory(prefix="ritz1-unit-") as scratch,
        ThreadPoolExecutor(max_workers=max(1, args.j)) as pool,
    ):
        outcomes = list(pool.map(lambda f: run(f, Path(scratch)), files))
    code, line = verdict(files, outcomes)
    print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
