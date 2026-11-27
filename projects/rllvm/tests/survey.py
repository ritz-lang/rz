"""rllvm's cutover survey (../razm/DESIGN.md "Cutover", "Coverage before the
switch").

    python3 survey.py DIR [--profile PROFILE] [-j N]
    ./rz test rllvm --survey DIR [--profile PROFILE]

Runs rllvm on every `.ll` under DIR (recursively), the IR a `--debug` build
keeps under build/. It builds nothing. Each file gets one line:

    accepted  REL
    rejected  REL:LINE  CONSTRUCT     rllvm exit 2: outside the subset
    failed    REL  STATUS: DETAIL     exit 1, a signal or a timeout

then the rejected constructs, most files first, and one summary line:

    survey DIR (PROFILE): N files: A accepted, R rejected, F failed

PROFILE picks rllvm's flags, the same argv the corpus gives clang and rllvm
(corpus.PROFILE_FLAGS): hosted, shim, small-pic, kernel or large. A `.ll`
does not record the flags it was built with, so the caller names them.

Exit 0 when every file was accepted or rejected: a rejection is a survey
result, and the pipeline sends that file to clang. Exit 1 when any file
failed (DESIGN: a build failure with no fallback), when DIR holds no `.ll`,
or on a usage error.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus import PROFILE_FLAGS, TOOL_TIMEOUT

PKG = Path(__file__).resolve().parent.parent

EXIT_UNSUPPORTED = 2

# `rllvm: FILE:LINE: unsupported: WHAT`, or `rllvm: FILE: unsupported: WHAT`
# when no line applies (a --target triple).
_UNSUPPORTED = re.compile(r"^rllvm: .*?(?::(\d+))?: unsupported: (.*)$")


@dataclass(frozen=True)
class Outcome:
    path: Path
    verdict: str        # accepted | rejected | failed
    line: int = 0       # rejected: the line rllvm named, 0 if none
    detail: str = ""    # rejected: the construct; failed: status and stderr


def default_rllvm() -> str:
    """$RLLVM, else this package's debug build (as conftest.py finds it)."""
    return os.environ.get("RLLVM") or str(PKG / "build" / "debug" / "rllvm")


def find_ll(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.ll") if p.is_file())


def classify(path: Path, returncode: int, stderr: str) -> Outcome:
    """One rllvm run's verdict from its exit status and stderr."""
    if returncode == 0:
        return Outcome(path, "accepted")
    if returncode == EXIT_UNSUPPORTED:
        for text in stderr.splitlines():
            m = _UNSUPPORTED.match(text)
            if m:
                return Outcome(path, "rejected", int(m.group(1) or 0), m.group(2))
        return Outcome(path, "failed", 0,
                       f"exit 2 without an 'unsupported:' line: {_first(stderr)}")
    if returncode < 0:
        return Outcome(path, "failed", 0, f"killed by signal {-returncode}")
    return Outcome(path, "failed", 0, f"exit {returncode}: {_first(stderr)}")


def _first(stderr: str) -> str:
    lines = stderr.strip().splitlines()
    return lines[0] if lines else "(no stderr)"


def run_one(rllvm: str, flags: list[str], path: Path, out_dir: Path, n: int) -> Outcome:
    obj = out_dir / f"{n}.o"
    try:
        p = subprocess.run([rllvm, *flags, str(path), "-o", str(obj)],
                           capture_output=True, text=True, timeout=TOOL_TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        return Outcome(path, "failed", 0, f"timed out after {TOOL_TIMEOUT}s")
    finally:
        obj.unlink(missing_ok=True)
    return classify(path, p.returncode, p.stderr)


def survey(root: Path, profile: str, rllvm: str, jobs: int) -> list[Outcome]:
    files = find_ll(root)
    flags = PROFILE_FLAGS[profile]
    with tempfile.TemporaryDirectory(prefix="rllvm-survey-") as tmp, \
            ThreadPoolExecutor(max_workers=jobs) as pool:
        return list(pool.map(lambda nf: run_one(rllvm, flags, nf[1], Path(tmp), nf[0]),
                             enumerate(files)))


def report(root: Path, profile: str, outcomes: list[Outcome], out) -> int:
    """Print the per-file lines, the construct tally and the summary; return
    the exit status."""
    counts = {"accepted": 0, "rejected": 0, "failed": 0}
    by_construct: dict[str, list[str]] = defaultdict(list)
    for o in outcomes:
        rel = o.path.relative_to(root).as_posix()
        counts[o.verdict] += 1
        if o.verdict == "accepted":
            print(f"accepted  {rel}", file=out)
        elif o.verdict == "rejected":
            where = f"{rel}:{o.line}" if o.line else rel
            print(f"rejected  {where}  {o.detail}", file=out)
            by_construct[o.detail].append(rel)
        else:
            print(f"failed    {rel}  {o.detail}", file=out)
    if by_construct:
        print("rejected constructs:", file=out)
        for what, rels in sorted(by_construct.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            print(f"  {len(rels):4}  {what}", file=out)
    print(f"survey {root} ({profile}): {len(outcomes)} files: "
          f"{counts['accepted']} accepted, {counts['rejected']} rejected, "
          f"{counts['failed']} failed", file=out)
    return 1 if counts["failed"] or not outcomes else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="survey", description=__doc__.split("\n\n")[0])
    ap.add_argument("dir", type=Path, help="tree of .ll files, e.g. a --debug build/")
    ap.add_argument("--profile", choices=sorted(PROFILE_FLAGS), default="hosted",
                    help="rllvm's flags for every file (default: hosted)")
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 1)
    args = ap.parse_args(argv)
    if not args.dir.is_dir():
        print(f"survey: {args.dir}: not a directory", file=sys.stderr)
        return 1
    rllvm = default_rllvm()
    if not os.access(rllvm, os.X_OK):
        print(f"survey: rllvm is not built at {rllvm}: run ./rz build rllvm first",
              file=sys.stderr)
        return 1
    root = args.dir.resolve()
    outcomes = survey(root, args.profile, rllvm, max(1, args.jobs))
    if not outcomes:
        print(f"survey: {args.dir}: no .ll files", file=sys.stderr)
    return report(root, args.profile, outcomes, sys.stdout)


if __name__ == "__main__":
    sys.exit(main())
