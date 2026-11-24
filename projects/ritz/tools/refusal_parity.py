#!/usr/bin/env python3
"""ritz1 refuses what ritz0 refuses in the ritz0-only tests (AGAST #4669).

Self-hosting goal 3 is "ritz1 rejects everything ritz0 rejects".  583 of
ritz0/tests' files run ritz1 beside ritz0; the rest never do, and survey
#4631 found every goal-3 gap in them.  This is the differential for those
files, run as part of main.yml's "ritz0 unit tests" step:

1. The step's pytest runs with RITZ_REFUSAL_CAPTURE=<dir>, so
   ritz0/harness/refusal_capture.py records, for each test in a file that
   never names ritz1, every program ritz0's CLI refused and every source
   the test lexed in-process (see that module).
2. `refusal_parity.py replay <dir>` compiles each recorded program with
   ritz0's CLI (`src -o x.ll`) and with ritz1 the same way.  For each one
   ritz0 refuses, ritz1 must refuse it too, with its first located
   diagnostic's file and line (`<file>.ritz:LINE`) among its own
   diagnostics: ritz1 may also report an error ritz0 stopped before.  Both
   compilers see the same file, cwd and RITZ_PATH, and plain arguments:
   a refusal only a ritz0 flag produces (--test, a lint switch) is not
   ritz1's to reproduce, and is counted, not judged.

A test id (`tests/test_x.py::name[param]`) fails when any of its programs
does.  Failures are excused only by known-failures/<agast>.toml entries with
`gate = "refusal"`, `compiler = "ritz1"`, `unit = <test id>`, under the one
rule in tools/known_failures.py: an excused test that now passes fails the
step (strict xpass), so the list only shrinks; a test that did not run this
time (the likely-first split, a filtered run) is neither.

Why inside the pytest step rather than its own: the replay needs that step's
capture, so it must be skipped exactly when that step is (ci_local
--diff-base) and see exactly the tests that step ran (ci_local's likely-first
pre-pass runs the step's command on a few files, then the rest: each run
captures and replays its own tests, so every test is judged once).  `make
unit` does not capture, so it pays nothing.

Cost: the capture is a copy per refusal; the replay is ~1,000 compiles per
compiler (ritz0 forked from a preloaded forkserver, ~40 ms; ritz1 ~10 ms),
in parallel.  The step prints its wall time.

Exit: 0 green; 1 a failure no entry excuses, or an entry that now passes, or
a capture with no marker (the hook did not run: never a silent green);
2 bad usage or a malformed known-failures list.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
RITZ_ROOT = TOOLS.parent
RITZ0_DIR = RITZ_ROOT / "ritz0"
sys.path.insert(0, str(TOOLS))
import known_failures  # noqa: E402

GATE = "refusal"
COMPILER = "ritz1"
RITZ1 = RITZ_ROOT / "ritz1" / "build" / "ritz1"
MARKER = "capture-on"
# First located diagnostic: `<anything>.ritz:LINE:COL`.
LOCATED = re.compile(r"([^\s:'\"`]+\.ritz):(\d+):(\d+)")
CRASH = "Traceback (most recent call last)"
TIMEOUT = 120


@dataclass(frozen=True)
class Program:
    """One file to compile: where it is and what RITZ_PATH it saw."""
    path: Path               # the .ritz source, inside the capture dir
    ritz_path: str | None    # None: unset
    alone: bool = False      # an in-process source: its directory holds
                             # every other one, so copy only the file


@dataclass
class Verdict:
    rc: int | None
    output: str

    @property
    def refused(self) -> bool:
        return self.rc is not None and self.rc != 0

    @property
    def crashed(self) -> bool:
        return self.rc is None or self.rc < 0 or CRASH in self.output

    @property
    def at(self) -> tuple[str, int] | None:
        """The first located diagnostic's (file name, line)."""
        m = LOCATED.search(self.output)
        return (Path(m.group(1)).name, int(m.group(2))) if m else None

    @property
    def located(self) -> set[tuple[str, int]]:
        """Every (file name, line) a diagnostic names."""
        return {(Path(f).name, int(line)) for f, line, _ in LOCATED.findall(self.output)}


@dataclass
class Capture:
    ran: set[str] = field(default_factory=set)            # ritz0-only tests that ran
    programs: dict[str, list[Program]] = field(default_factory=dict)  # test -> programs
    skipped: list[str] = field(default_factory=list)      # records with no program


def load_capture(d: Path) -> Capture:
    """Read every records-*.jsonl under `d`."""
    cap = Capture()
    for f in sorted(d.glob("records-*.jsonl")):
        for line in f.read_text().splitlines():
            rec = json.loads(line)
            test = rec["test"]
            if rec["kind"] == "ran":
                cap.ran.add(test)
                continue
            cap.ran.add(test)
            if "skip" in rec:
                cap.skipped.append(f"{test}: {rec['skip']}")
                continue
            if rec["kind"] == "cli":
                root = d / rec["dir"]
                parts = []
                for c in rec.get("ritz_path") or []:
                    if c == "@RITZ_ROOT":
                        parts.append(str(RITZ_ROOT))
                    elif c.startswith("@DIR/"):
                        parts.append(str((root / c[5:]).resolve()))
                prog = Program(root / rec["source"], ":".join(parts) or None)
            else:
                # In-process sources import ritzlib, if anything: resolve it.
                prog = Program(d / rec["source"], str(RITZ_ROOT), alone=True)
            progs = cap.programs.setdefault(test, [])
            if prog not in progs:
                progs.append(prog)
    return cap


def _env(prog: Program, cache: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if k not in ("RITZ_PATH", "RITZ_REFUSAL_CAPTURE", "PYTEST_CURRENT_TEST")}
    if prog.ritz_path is not None:
        env["RITZ_PATH"] = prog.ritz_path
    # Never a shared or stale incremental cache: a hit prints "Skipped
    # (unchanged)" and exits 0, which would read as an acceptance.
    env["RITZ_CACHE_DIR"] = str(cache)
    return env


def private_copy(prog: Program, where: Path) -> Program:
    """`prog` in a directory of its own: a compile writes beside its source
    (interface and cache files) and reads its directory's other modules, so
    two compiles sharing one -- 900 in-process sources do, and ritz0 before
    ritz1 on a CLI capture -- made verdicts flaky (seen: ritz0 refusing a
    program it compiles alone)."""
    if prog.alone:
        where.mkdir(parents=True)
        shutil.copy2(prog.path, where / prog.path.name)
        return Program(where / prog.path.name, prog.ritz_path, True)
    shutil.copytree(prog.path.parent, where, symlinks=True)
    remap = prog.ritz_path
    if remap:
        old = str(prog.path.parent.resolve())
        remap = ":".join(str(where) + c[len(old):] if c == old or c.startswith(old + "/")
                         else c for c in remap.split(":"))
    return Program(where / prog.path.name, remap)


def compile_ritz0(prog: Program, out: Path) -> Verdict:
    sys.path.insert(0, str(RITZ0_DIR / "harness"))
    import ritz0_inproc
    try:
        cp = ritz0_inproc.run_ritz0([prog.path.name, "-o", str(out)],
                                    cwd=prog.path.parent,
                                    env=_env(prog, out.with_suffix(".cache")),
                                    timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return Verdict(None, "ritz0 timed out")
    return Verdict(cp.returncode, cp.stdout + cp.stderr)


def compile_ritz1(ritz1: Path, prog: Program, out: Path) -> Verdict:
    try:
        cp = subprocess.run([str(ritz1), prog.path.name, "-o", str(out)],
                            cwd=prog.path.parent,
                            env=_env(prog, out.with_suffix(".cache")),
                            capture_output=True, text=True, errors="replace",
                            timeout=TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        return Verdict(None, "ritz1 timed out")
    return Verdict(cp.returncode, cp.stdout + cp.stderr)


def judge(v0: Verdict, v1: Verdict) -> str | None:
    """Why ritz1's answer fails ritz0's refusal, or None.  `v0` refused."""
    if v1.crashed:
        return f"ritz1 crashed (exit {v1.rc}): {v1.output.strip()[-200:]}"
    if not v1.refused:
        return "ritz1 ACCEPTED it; ritz0 refuses it"
    a0 = v0.at
    if a0 is None:
        return None  # ritz0 names no position: the verdict is all there is
    if a0 in v1.located:
        # ritz1 reports ritz0's line; it may report others first (a second
        # error ritz0 stops before, or the same ones in another order).
        return None
    a1 = v1.at
    if a1 is None:
        return (f"ritz1 refused with no located diagnostic; ritz0 at "
                f"{a0[0]}:{a0[1]}: {v1.output.strip()[:160]}")
    return f"ritz1 refused at {a1[0]}:{a1[1]}, ritz0 at {a0[0]}:{a0[1]}"


def _first_line(text: str) -> str:
    for line in text.splitlines():
        if LOCATED.search(line):
            return line.strip()[:200]
    return (text.strip().splitlines() or [""])[0][:200]


def replay(cap: Capture, ritz1: Path, jobs: int) -> tuple[dict[str, str], dict[str, int]]:
    """({test: "pass" | why it fails}, counts)."""
    progs = sorted({p for ps in cap.programs.values() for p in ps},
                   key=lambda p: str(p.path))
    scratch = Path(tempfile.mkdtemp(prefix="refusal-parity-"))
    try:
        def one(i_prog):
            i, prog = i_prog
            here = scratch / str(i)
            v0 = compile_ritz0(private_copy(prog, here / "r0"), here / "r0.ll")
            if not v0.refused or v0.crashed:
                return prog, v0, None
            # A refusal must repeat: run_ritz0's forkserver reports exit 255
            # when it can't read a child's status, ~1 compile in 2,000 under
            # load (seen: "Compiled x.ritz" with exit 255).  Not repeated:
            # not ritz0's answer, so not judged.
            again = compile_ritz0(private_copy(prog, here / "r0b"), here / "r0b.ll")
            if not again.refused:
                return prog, Verdict(0, f"not repeated: {v0.output}"), None
            v1 = compile_ritz1(ritz1, private_copy(prog, here / "r1"), here / "r1.ll")
            return prog, v0, v1
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            done = {p: (v0, v1) for p, v0, v1 in pool.map(one, enumerate(progs))}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    counts = {"programs": len(progs), "ritz0_refused": 0, "ritz0_crashed": 0,
              "ritz1_disagrees": 0, "not_repeated": 0}
    for v0, v1 in done.values():
        if v0.output.startswith("not repeated: "):
            counts["not_repeated"] += 1
        elif v0.crashed:
            counts["ritz0_crashed"] += 1
        elif v0.refused:
            counts["ritz0_refused"] += 1
            if judge(v0, v1):
                counts["ritz1_disagrees"] += 1
    results: dict[str, str] = {test: "pass" for test in cap.ran}
    for test, ps in cap.programs.items():
        whys = []
        for p in ps:
            v0, v1 = done[p]
            if v1 is None:
                continue
            why = judge(v0, v1)
            if why:
                whys.append(f"{why}\n      ritz0: {_first_line(v0.output)}"
                            f"\n      file:  {p.path}")
        if whys:
            results[test] = "\n    ".join(whys)
    return results, counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    rp = sub.add_parser("replay", help="judge a capture directory")
    rp.add_argument("capture", type=Path)
    rp.add_argument("--ritz1", type=Path,
                    default=Path(os.environ.get("RITZ_REFUSAL_PARITY_RITZ1") or RITZ1))
    rp.add_argument("-j", "--jobs", type=int, default=min(8, os.cpu_count() or 1))
    args = ap.parse_args(argv)

    start = time.monotonic()
    if not (args.capture / MARKER).is_file():
        print(f"refusal parity: {args.capture} has no {MARKER} marker: the "
              f"pytest run did not capture (RITZ_REFUSAL_CAPTURE unset, or "
              f"ritz0/conftest.py's hook gone).  Nothing was judged.")
        return 1
    if not args.ritz1.is_file():
        print(f"refusal parity: no ritz1 at {args.ritz1} (make ritz1-bootstrap)")
        return 1
    try:
        excused = known_failures.known(GATE, COMPILER)
    except known_failures.KnownFailuresError as e:
        print(f"refusal parity: {e}")
        return 2
    cap = load_capture(args.capture)
    results, counts = replay(cap, args.ritz1, max(1, args.jobs))
    out = known_failures.outcome(excused, results)

    for test, key in sorted(out.known.items()):
        print(f"KNOWN  {test}  ({excused[key]})")
    for test in sorted(out.hard):
        print(f"FAIL   {test}\n    {results[test]}")
    for key in sorted(out.xpass):
        print(f"XPASS  {key}: ritz1 now agrees with ritz0; drop its "
              f"`refusal` entry ({excused[key]})")
    wall = time.monotonic() - start
    print(f"refusal parity: {len(results)} ritz0-only test(s) ran, "
          f"{counts['programs']} program(s), ritz0 refused {counts['ritz0_refused']} "
          f"(crashed on {counts['ritz0_crashed']}, {counts['not_repeated']} not "
          f"repeated), ritz1 disagreed on "
          f"{counts['ritz1_disagrees']}; {len(out.hard)} failing, "
          f"{len(out.known)} known, {len(out.xpass)} xpass "
          f"[{len(cap.skipped)} record(s) with no program] in {wall:.1f}s")
    if not out.ok:
        print("refusal parity: FAILED.  A ritz0-only test feeds ritz0 a program "
              "it refuses and ritz1 does not refuse it the same way: fix ritz1, "
              "or cite the open ticket in known-failures/<agast>.toml "
              "(gate = \"refusal\", compiler = \"ritz1\", unit = the test id).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
