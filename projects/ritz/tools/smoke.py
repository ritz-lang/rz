#!/usr/bin/env python3
"""`make smoke`: say "fully broken" in under two minutes (AGAST #1803).

Design: projects/larb/review/4/fast-iteration.md §4.  Before this, nothing in
the gate exercised ritz1 until ~26 minutes in: a ritz1 that built but compiled
nothing was first reported at the end of the ritz0 pytest run, and a miscompile
of the basics at regression Stage 3.  This runs first — in run-gate.sh and as
the first step of main.yml's bootstrap job — and stops at the first failure.

Steps, cheapest and most-likely-broken first:

  0. timeout --signal=KILL                the run budgets regression.sh relies
                                          on are enforced (#2745; SETUP ERROR)
  1. check-no-s-strings, regen-check      banned syntax, generator drift
  2. pytest -m smoke  (ritz0/, serial)    broken ritz0 front end / tooling
  3. build ritz1 (incremental, -j)        ritz1 does not build
  4. canary matrix, ritz0 + ritz1         ritz1 builds but compiles nothing,
     over tools/smoke_canaries.txt        or miscompiles the basics
  5. ritz1 compiles tokens_gen.ritz and   self-hosting totally broken
     `clang -c` accepts the .ll

Each step prints its wall time against its budget.  A step over budget is
reported, not failed: on a contended host the time is not the commit's fault.

The canary list is short by design, so it gets the #1371 treatment: every
listed canary must still be discovered on disk, and the list must not shrink
below CANARY_FLOOR.  A canary renamed away fails smoke instead of quietly
dropping out of it.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TextIO

HERE = Path(__file__).resolve().parent
RITZ_ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import run_regression_matrix as matrix  # noqa: E402

CANARY_FILE = HERE / "smoke_canaries.txt"
# Lowering the floor is a deliberate act: edit it here, in review.
CANARY_FLOOR = 8
SELF_COMPILE_SRC = RITZ_ROOT / "ritz1" / "src" / "tokens_gen.ritz"
RITZ1_BIN = Path(matrix.RITZ1)
# Lines of a failing step's captured output to show.
FAIL_TAIL = 60
# "This machine lacks a working tool", not "this commit is broken" -- the same
# code as ci_local.EXIT_SETUP and build.py's (AGAST #2141).
EXIT_SETUP = 3


# --------------------------------------------------------------------------
# Canary list
# --------------------------------------------------------------------------

def load_canaries(path: Path = CANARY_FILE) -> list[str]:
    """Test-file stems from the canary list; `#` starts a comment."""
    out = []
    for line in Path(path).read_text().splitlines():
        name = line.split("#", 1)[0].strip()
        if name:
            out.append(name)
    return out


def canary_problems(canaries: list[str], discovered: list[str],
                    floor: int = CANARY_FLOOR) -> list[str]:
    """Reasons the canary list cannot be trusted (empty = OK)."""
    probs = []
    seen = set()
    found = set(discovered)
    for c in canaries:
        if c in seen:
            probs.append(f"{c}: listed twice in {CANARY_FILE.name}")
        seen.add(c)
        if c in matrix.NOT_TESTS:
            probs.append(f"{c}: is in run_regression_matrix.NOT_TESTS, so the matrix "
                         f"never runs it — pick a test file")
        elif c not in found:
            probs.append(f"{c}: listed in {CANARY_FILE.name} but not discovered in "
                         f"{matrix.TEST_DIR} — renamed or deleted? update the list")
    if len(seen) < floor:
        probs.append(f"{len(seen)} canaries is below the floor of {floor} "
                     f"(CANARY_FLOOR in tools/smoke.py)")
    return probs


def canary_regex(canaries: list[str]) -> str:
    """An anchored --tests regex that selects exactly these file stems."""
    return "^(" + "|".join(re.escape(c) for c in canaries) + ")$"


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

@dataclass
class Step:
    name: str
    budget: int  # seconds, uncontended
    run: Callable[[], int]


def run_steps(steps: list[Step], out: TextIO = sys.stdout) -> int:
    """Run steps in order, stop at the first failure, print per-step seconds."""
    rows: list[tuple[str, int, float | None, str]] = []
    rc = 0
    t_all = time.monotonic()
    for i, step in enumerate(steps, 1):
        if rc != 0:
            rows.append((step.name, step.budget, None, "not run"))
            continue
        print(f"[smoke {i}/{len(steps)}] {step.name} ...", file=out, flush=True)
        t0 = time.monotonic()
        try:
            step_rc = step.run()
        except Exception as e:  # a crashing step is a failing step
            print(f"  {step.name} raised {type(e).__name__}: {e}", file=out)
            step_rc = 1
        dt = time.monotonic() - t0
        status = "ok" if step_rc == 0 else f"FAIL (exit {step_rc})"
        if step_rc != 0:
            rc = step_rc if isinstance(step_rc, int) and step_rc > 0 else 1
        elif dt > step.budget:
            status = "ok, over budget"
        rows.append((step.name, step.budget, dt, status))
    total = time.monotonic() - t_all

    print("\n=== smoke: per-step seconds ===", file=out)
    for name, budget, dt, status in rows:
        secs = "     -" if dt is None else f"{dt:6.1f} s"
        print(f"  {name:22s} {secs}  (budget {budget:3d} s)  {status}", file=out)
    print(f"  {'total':22s} {total:6.1f} s", file=out)
    if rc == 0:
        print(f"✓ smoke passed in {total:.1f} s", file=out)
    else:
        failed = next(n for n, _, _, s in rows if s.startswith("FAIL"))
        print(f"💥 smoke FAILED at '{failed}' after {total:.1f} s", file=out)
    return rc


def _env() -> dict:
    return dict(os.environ, RITZ_PATH=str(RITZ_ROOT))


def _run(cmd: list[str], cwd: Path = RITZ_ROOT, out: TextIO = sys.stdout,
         timeout: int = 600, quiet: bool = True) -> int:
    """Run cmd; when quiet, show its output only if it fails."""
    if not quiet:
        return subprocess.run(cmd, cwd=cwd, env=_env(), timeout=timeout).returncode
    proc = subprocess.run(cmd, cwd=cwd, env=_env(), timeout=timeout,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        lines = proc.stdout.splitlines()
        print(f"  $ {' '.join(cmd)}  (exit {proc.returncode})", file=out)
        for line in lines[-FAIL_TAIL:]:
            print(f"  | {line}", file=out)
    return proc.returncode


def _make(*targets: str, cwd: Path = RITZ_ROOT) -> list[str]:
    return ["make", "--no-print-directory", "-C", str(cwd), *targets]


# --------------------------------------------------------------------------
# Steps
# --------------------------------------------------------------------------

def timeout_kill_probe(limit: float = 1.0, sleep: float = 3.0,
                       out: TextIO = sys.stdout,
                       env: dict | None = None) -> int:
    """`timeout --signal=KILL` really kills at its limit (AGAST #2745).

    regression.sh wraps every example run (and each example's test.sh) in
    `timeout --signal=KILL <budget>`.  uutils 0.2.x (Ubuntu's
    coreutils-from-uutils) ignores the limit with --signal=KILL and runs the
    command to completion, so on such a host no run budget exists and one
    hanging example hangs the whole gate.  That is the machine's fault, not the
    commit's: report it as a SETUP ERROR (exit EXIT_SETUP), naming the fix.

    `env` overrides os.environ (tests put a fake `timeout` on PATH).
    """
    run_env = dict(os.environ, **(env or {}))
    path = run_env.get("PATH", "")
    exe = shutil.which("timeout", path=path) or "timeout"
    cmd = [exe, "--signal=KILL", f"{limit:g}s", "sleep", f"{sleep:g}"]
    # Killed at `limit`, or ran to `sleep`: split the difference so a
    # contended host's scheduling jitter cannot flip the verdict.
    deadline = (limit + sleep) / 2
    t0 = time.monotonic()
    try:
        rc = subprocess.run(cmd, check=False, env=run_env, timeout=sleep + 30,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).returncode
        why = None
    except FileNotFoundError:
        rc, why = None, f"no `timeout` on PATH ({path})"
    dt = time.monotonic() - t0
    if why is None and dt >= deadline:
        why = (f"`{' '.join(cmd)}` ran {dt:.1f} s: the {limit:g} s limit "
               f"was not enforced")
    elif why is None and rc not in (124, 137, -signal.SIGKILL):
        # GNU exits 137, or (without --foreground) KILLs its own process group
        # and so dies by SIGKILL itself, which Python reports as -9 (#2775);
        # uutils >= 0.8 exits 124. The overrun check above is the real test.
        why = (f"`{' '.join(cmd)}` exited {rc} after {dt:.1f} s, "
               f"not 124/137/-{int(signal.SIGKILL)}")
    if why is None:
        return 0
    print(f"  ⚠ SETUP ERROR: {why}.", file=out)
    print("    regression.sh's per-example run budgets use `timeout --signal=KILL`;"
          " without it a hanging example hangs the gate.", file=out)
    print("    Fix: `sudo apt install coreutils-from-gnu` (GNU timeout), or a newer"
          " uutils (0.8.0 enforces it). Not a regression.", file=out)
    return EXIT_SETUP


def pytest_smoke(out: TextIO = sys.stdout) -> int:
    # Serial on purpose: under xdist the controller builds ritz1 before any
    # worker starts (ritz0/conftest.py item 4) — step 3's job, not this one's.
    # -p no:cacheprovider: smoke must not leave .pytest_cache state behind.
    # --disable-plugin-autoload: none of a venv's other plugins (AGAST #2793).
    return _run([sys.executable, "-m", "pytest", "-q", "-m", "smoke",
                 "--disable-plugin-autoload",
                 "-p", "no:cacheprovider", "-o", "addopts="],
                cwd=RITZ_ROOT / "ritz0", out=out, timeout=600)


def build_ritz1(out: TextIO = sys.stdout) -> int:
    # The Makefile's `ritz1` target carries the repo's -j rule (AGAST #1802).
    rc = _run(_make("ritz1"), out=out, timeout=900)
    if rc != 0:
        return rc
    # The matrix links every test against this start object; it is a build
    # product, so a fresh worktree does not have it.
    runtime_o = Path(matrix.RUNTIME_O)
    return _run(_make(runtime_o.name, cwd=runtime_o.parent), out=out, timeout=300)


def canary_matrix(out: TextIO = sys.stdout) -> int:
    canaries = load_canaries()
    probs = canary_problems(canaries, matrix.discover_test_files())
    if probs:
        print("  canary list self-check FAILED:", file=out)
        for p in probs:
            print(f"    ✗ {p}", file=out)
        return 1
    print(f"  {len(canaries)} canaries x ritz0, ritz1", file=out)
    return _run([sys.executable, str(HERE / "run_regression_matrix.py"),
                 "--compiler", "ritz0,ritz1", "--tests", canary_regex(canaries)],
                out=out, timeout=600)


def self_compile(ritz1: Path = RITZ1_BIN, src: Path = SELF_COMPILE_SRC,
                 out: TextIO = sys.stdout) -> int:
    """ritz1 compiles one of its own modules to IR that clang accepts."""
    with tempfile.TemporaryDirectory(prefix="smoke_selfcompile_") as tmp:
        ll = Path(tmp) / (src.stem + ".ll")
        rc = _run([str(ritz1), str(src), "-o", str(ll)], out=out, timeout=120)
        if rc != 0:
            return rc
        if not ll.is_file() or not re.search(r"^define ", ll.read_text(), re.M):
            print(f"  {ritz1.name} exited 0 but {ll.name} defines no function", file=out)
            return 1
        return _run(["clang", "-c", str(ll), "-o", str(ll.with_suffix(".o"))],
                    out=out, timeout=120)


def build_steps(out: TextIO = sys.stdout) -> list[Step]:
    return [
        # First: a broken timeout makes every later run budget meaningless.
        Step("timeout --signal=KILL", 2, lambda: timeout_kill_probe(out=out)),
        Step("check-no-s-strings", 2, lambda: _run(_make("check-no-s-strings"), out=out)),
        Step("regen-check", 3, lambda: _run(_make("regen-check"), out=out)),
        Step("pytest -m smoke", 45, lambda: pytest_smoke(out)),
        Step("build ritz1", 30, lambda: build_ritz1(out)),
        Step("canary matrix", 20, lambda: canary_matrix(out)),
        Step("ritz1 self-compile", 10, lambda: self_compile(out=out)),
    ]


def main() -> int:
    return run_steps(build_steps())


if __name__ == "__main__":
    sys.exit(main())
