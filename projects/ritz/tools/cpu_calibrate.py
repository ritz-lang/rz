#!/usr/bin/env python3
"""How many CPU-seconds a fixed workload costs on this host (AGAST #3897).

    cpu_calibrate.py --out PATH [--jobs N] [--rounds R] [--scratch DIR]
    cpu_calibrate.py --out PATH --factor F
    cpu_calibrate.py --runs N [--jobs N] [--rounds R] [--budget TOML]

cost_meter's CPU-seconds are not portable: at ef9a7e2b the same ritz0 suite
measured 1,454.5 CPU-s on toffee and 2,347 on omegalisk (1.6x).  One cap in
tools/test_budget.toml then meant ~40% headroom on one gate host and ~2% on
the other.  So the ritz0 step runs this first, and check_test_budget.py
divides every CPU figure by the host's factor:

    factor = this workload's CPU-s here / [calibration] reference_cpu_s

reference_cpu_s is the same workload's CPU-s on the host the caps were set on,
so a normalised figure reads as "CPU-s on that host".

The workload is shaped like a ritz0 test, but uses nothing from the tree:

* a Python child that parses, compiles and runs generated source, and counts
  its tokens (the compiler's share of the suite);
* clang compiling a generated LLVM IR module and linking it -nostdlib (the
  link's share);
* running the linked binary many times (fork/exec, the run's share).

Nothing from the tree on purpose.  A workload of ritz0 compiles would slow
down with the compiler, and a compiler twice as slow would leave the
normalised suite figure where it was: the budget would stop seeing what it
exists to see.  Only the host moves this figure: its CPU, kernel, Python and
clang, and how loaded it is right now.

`--jobs` copies run at once, one per xdist worker the suite will have (the
step's `-n auto --maxprocesses "${PYTEST_J:-8}"`): two busy hyperthreads on one core spend
more CPU-s on the same work, and the suite pays that too.  `--rounds` repeats
it after one uncounted warm-up; the figure is the median round's CPU-s per
copy.  Out: {"cpu_s", "jobs",
"rounds", "samples"} as JSON, and one line for the log.  A few seconds wall.

A few seconds just before a ~20-minute suite is a reading of how busy the box
is right now, too: skronk (normally ~1.67) read 1.054 and 1.072 under load and
failed two gates whose tests all passed (AGAST #4172).  So a host can fix its
factor instead, as host.env's RZ_CPU_FACTOR:

* `--factor F` writes {"factor": F, "fixed": true} and times nothing;
  check_test_budget.py takes F as it stands.  The gate passes it when the
  host has one.
* `--runs N` is how to find F, once, on an idle box: N whole calibrations,
  each over the budget's reference_cpu_s, and their median, printed as the
  RZ_CPU_FACTOR= line to copy into host.env.

`--scratch DIR` is where the copies work; with none it is $TMPDIR (or /tmp).
The workload EXECs the linked binary, so the dir must be on a filesystem
mounted exec: where /tmp is `noexec` (bangerang was) the default died with
`Permission denied` (exit 126), which reads as a broken tool (AGAST #4431).
So the candidates are probed -- `--scratch`, then $TMPDIR, then
$XDG_CACHE_HOME/ritz/exec-tmp (~/.cache/ritz/exec-tmp) -- and the first that
can write and run a file is used, with a line saying why it moved on.  Gates
are unaffected: run-gate.sh gives each gate its own exec-capable TMPDIR.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

import exec_tmpdir  # AGAST #3704: the one exec-capable-dir probe

DEFAULT_BUDGET = Path(__file__).resolve().parent / "test_budget.toml"

# main.yml's `--maxprocesses "${PYTEST_J:-8}"`: 8 unless the gate sets
# PYTEST_J (run-gate.sh does, from host.env's RZ_GATE_JOBS; AGAST #4971).
MAX_PROCESSES = 8


def max_processes() -> int:
    """The suite's --maxprocesses: $PYTEST_J if a whole number >= 1, else 8."""
    raw = os.environ.get("PYTEST_J", "")
    return int(raw) if raw.isdigit() and int(raw) >= 1 else MAX_PROCESSES

# Runs of the linked binary per copy: a process start each, as each test's
# run step is.
EXECS = 60

# The compiler-shaped part: parse, compile, exec, call, count tokens.
PY_WORKLOAD = r'''
import ast, re
N = 400
src = "\n".join(
    f"def f{i}(a, b):\n"
    f"    x = a * {i} + b\n"
    f"    if x % 3 == 0:\n"
    f"        return [x, a, b, '{i}']\n"
    f"    return {{'k{i}': x, 'v': (a, b)}}\n"
    for i in range(N))
total = 0
for _ in range(8):
    tree = ast.parse(src)
    names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    code = compile(tree, "<reference>", "exec")
    ns = {}
    exec(code, ns)
    counts = {}
    for tok in re.findall(r"\w+|[^\w\s]", src):
        counts[tok] = counts.get(tok, 0) + 1
    for i, name in enumerate(names):
        total += len(ns[name](i, 7))
    total += len(counts)
print(total)
'''

IR_FUNCS = 800


def reference_ir() -> str:
    """A fixed LLVM IR module with its own _start: no runtime, no libc."""
    out = []
    for i in range(IR_FUNCS):
        out.append(f"""define i64 @f{i}(i64 %a, i64 %b) {{
entry:
  %m = mul i64 %a, {i + 3}
  %s = add i64 %m, %b
  %c = icmp sgt i64 %s, {i * 7}
  br i1 %c, label %hi, label %lo
hi:
  %x = sdiv i64 %s, 3
  br label %done
lo:
  %y = shl i64 %s, 2
  br label %done
done:
  %r = phi i64 [ %x, %hi ], [ %y, %lo ]
  ret i64 %r
}}
""")
    calls = []
    prev = "0"
    for i in range(IR_FUNCS):
        calls.append(f"  %v{i} = call i64 @f{i}(i64 {prev}, i64 {i})")
        prev = f"%v{i}"
    out.append("define void @_start() {\nentry:\n" + "\n".join(calls) + "\n"
               '  call void asm sideeffect "mov $$60, %eax\\0Axor %edi, %edi\\0Asyscall",'
               ' "~{eax},~{edi},~{rcx},~{r11},~{memory}"()\n'
               "  unreachable\n}\n")
    return "\n".join(out)


def scratch_candidates(scratch: Path | None = None) -> list[Path]:
    """Where a copy may work, best first: `--scratch`, $TMPDIR, then the cache
    fallback exec_tmpdir already uses for the gate (AGAST #4431)."""
    candidates = [] if scratch is None else [Path(scratch)]
    candidates.append(Path(tempfile.gettempdir()))
    candidates.append(exec_tmpdir.default_fallback())
    out, seen = [], set()
    for c in candidates:
        key = os.path.abspath(c)
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def resolve_scratch(scratch: Path | None = None,
                    probe_fn: Callable[[str], str | None] | None = None,
                    out: TextIO = sys.stderr) -> Path:
    """The first scratch candidate that can create and EXEC a file (AGAST #4431).

    A noexec mount makes the linked binary exit 126, which reads as a broken
    tool, so probe each candidate and use the first that runs.  Missing dirs
    are created (the fallback usually does not exist yet).  Raises
    exec_tmpdir.SetupError naming every candidate when none can run a file.
    """
    probe = exec_tmpdir.probe if probe_fn is None else probe_fn
    candidates = scratch_candidates(scratch)
    failed: list[str] = []
    for n, d in enumerate(candidates):
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            failed.append(f"{d}: cannot create it: {e}")
            continue
        why = probe(str(d))
        if why is None:
            if n:
                print(f"# scratch {candidates[0]} can't run binaries "
                      f"({failed[0]}); using {d}", file=out, flush=True)
            return d
        failed.append(f"{d}: {why}")
    raise exec_tmpdir.SetupError(
        "no scratch dir can run binaries: " + "; ".join(failed))


def default_jobs() -> int:
    """The suite's worker count: xdist's own `-n auto`, capped at max_processes().

    xdist's hook, not a copy of it: physical cores when psutil is installed,
    the affinity mask's CPUs when not, $PYTEST_XDIST_AUTO_NUM_WORKERS over both.
    """
    from types import SimpleNamespace

    from xdist.plugin import pytest_xdist_auto_num_workers
    config = SimpleNamespace(option=SimpleNamespace(numprocesses="auto"))
    return max(1, min(int(pytest_xdist_auto_num_workers(config)), max_processes()))


def _children_cpu() -> float:
    t = os.times()
    return t.children_user + t.children_system


def _run(cmd, cwd) -> None:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=300, check=False)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} exited {r.returncode}: "
                           f"{r.stderr.decode(errors='replace')[-2000:]}")


def _one_copy(work: Path, ir: str) -> None:
    _run([sys.executable, "-I", "-c", PY_WORKLOAD], work)
    (work / "ref.ll").write_text(ir)
    _run(["clang", "-w", "-O0", "-c", "ref.ll", "-o", "ref.o"], work)
    _run(["clang", "ref.o", "-o", "ref", "-nostdlib"], work)
    for _ in range(EXECS):
        _run([str(work / "ref")], work)


def measure(jobs: int, rounds: int, scratch: Path | None = None) -> dict:
    """{"cpu_s": median round's CPU-s per copy, "jobs", "rounds", "samples"}."""
    work = resolve_scratch(scratch)
    ir = reference_ir()
    samples = []
    # Round 0 is a warm-up and is not counted: it pays for cold page cache
    # (python, clang) and a CPU still ramping its clock, and on toffee it read
    # up to 25% over the rounds after it.
    for n in range(rounds + 1):
        dirs = [Path(tempfile.mkdtemp(prefix="cpu-cal-", dir=work)) for _ in range(jobs)]
        errors: list[BaseException] = []

        def copy(d: Path) -> None:
            try:
                _one_copy(d, ir)
            except BaseException as e:  # reported below, after every copy ends
                errors.append(e)

        start = _children_cpu()
        threads = [threading.Thread(target=copy, args=(d,)) for d in dirs]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        used = _children_cpu() - start
        for d in dirs:
            shutil.rmtree(d, ignore_errors=True)
        if errors:
            raise errors[0]
        if n:
            samples.append(round(used / jobs, 4))
    return {"cpu_s": round(summarise(samples), 4), "jobs": jobs, "rounds": rounds,
            "samples": samples}


def summarise(samples: list[float]) -> float:
    """The median: one round hit by a burst of load does not move it."""
    return statistics.median(samples)


def positive_factor(v: str) -> float:
    """argparse type for --factor: a finite number > 0, as host-env.sh checks."""
    try:
        f = float(v)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {v!r}") from None
    if not math.isfinite(f) or f <= 0:
        raise argparse.ArgumentTypeError(f"must be a finite number > 0: {v!r}")
    return f


def host_factor_runs(runs: int, jobs: int, rounds: int, scratch: Path | None,
                     budget: Path) -> tuple[list[float], float]:
    """`runs` whole calibrations as factors over the budget's reference, and
    their median: the value for host.env's RZ_CPU_FACTOR."""
    ref = float(tomllib.loads(budget.read_text())["calibration"]["reference_cpu_s"])
    factors = [round(measure(jobs, rounds, scratch)["cpu_s"] / ref, 4)
               for _ in range(runs)]
    return factors, summarise(factors)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--jobs", type=int, default=None,
                    help="copies at once (default: the suite's xdist worker count)")
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--scratch", type=Path, default=None,
                    help="where the copies work (default: $TMPDIR, probed for "
                         "exec; else ~/.cache/ritz/exec-tmp)")
    ap.add_argument("--factor", type=positive_factor, default=None,
                    help="this host's fixed factor (host.env's RZ_CPU_FACTOR, "
                         "AGAST #4172): written as is, nothing is timed")
    ap.add_argument("--runs", type=int, default=None,
                    help="measure the factor N times and print the median, "
                         "for host.env's RZ_CPU_FACTOR (run on an idle box)")
    ap.add_argument("--budget", type=Path, default=DEFAULT_BUDGET,
                    help="test_budget.toml, for --runs' reference_cpu_s")
    a = ap.parse_args(argv)
    if a.runs is not None:
        if a.runs < 1 or a.factor is not None:
            ap.error("--runs takes N >= 1 and no --factor")
        try:
            work = resolve_scratch(a.scratch)
        except exec_tmpdir.SetupError as e:
            print(f"SETUP ERROR: {e}", file=sys.stderr)
            return exec_tmpdir.EXIT_SETUP
        factors, med = host_factor_runs(a.runs, a.jobs or default_jobs(), a.rounds,
                                        work, a.budget)
        print(f"cpu factor: {' '.join(f'{f:.3f}' for f in factors)}, "
              f"median of {a.runs} runs")
        print(f"RZ_CPU_FACTOR={med:.3f}")
        return 0
    if a.out is None:
        ap.error("--out is required (unless --runs)")
    if a.factor is not None:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps({"factor": a.factor, "fixed": True}) + "\n")
        print(f"cpu calibration: fixed factor {a.factor:.3f} (RZ_CPU_FACTOR), "
              f"not measured -> {a.out}")
        return 0
    try:
        work = resolve_scratch(a.scratch)
    except exec_tmpdir.SetupError as e:
        print(f"SETUP ERROR: {e}", file=sys.stderr)
        return exec_tmpdir.EXIT_SETUP
    r = measure(a.jobs or default_jobs(), a.rounds, work)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(r) + "\n")
    print(f"cpu calibration: {r['cpu_s']:.3f} CPU-s per copy, {r['jobs']} at once, "
          f"median of {r['rounds']} {r['samples']} -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
