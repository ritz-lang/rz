"""AGAST #1642: byte-exact output of ritzlib printers that ritzlib/tests can't reach.

#1642 turned ritzlib's hand-rolled prints/eprints/print_int chains into single
print/eprint interpolations.  Output must stay byte-identical, on the same fd,
with the same exit status.  ritzlib/tests/test_{argspec,env}_output.ritz
pin most of it under ritz0; this file covers what they can't.

(ritzlib/testing.ritz's assertion helpers were pinned here until AGAST #1869
deleted the module: `assert` itself now prints both operands; see
ritz0/test/test_assert_operands.ritz.  The deprecated ritzlib/args.ritz
printers were pinned here under both compilers until AGAST #4046 deleted the
module.)

AGAST #1684 did the same to timer, iovec, lang/tokens and elf.  ritz1
compiles all four, so the timer/iovec cases from
ritzlib/tests/test_{timer,iovec}_output.ritz are built with both
compilers below.  elf is ritz0 only: its golden finds `pub fn test_*`
symbols in the [[test]] harness binary, which a package build doesn't
reproduce.  lang/tokens' case went with that dead module (#3721).
"""

import os
import subprocess
from pathlib import Path

import pytest

from test_ritz1_builtin_struct_shadow import RITZ_ROOT

# xdist_group("tree") (AGAST #1804): build.py without --no-cache reads and writes the
# shared projects/ritz/.ritz-cache{,-ritz1}.  Tests in the group
# run on one xdist worker, one at a time; see conftest.py.
# Every test compiles and runs programs, so the module is integration (AGAST #1805).
pytestmark = [pytest.mark.xdist_group("tree"), pytest.mark.integration]


def _manifest(name: str) -> str:
    return (
        f'[package]\nname = "{name}"\nversion = "0.1.0"\n\n'
        f'[[bin]]\nname = "{name}"\npath = "src/main.ritz"\n'
    )


def _build(pkg: Path, name: str, program: str, compiler: str) -> Path:
    """Write a one-binary package under `pkg`, build it, return the binary."""
    (pkg / "src").mkdir(parents=True, exist_ok=True)
    (pkg / "ritz.toml").write_text(_manifest(name))
    (pkg / "src" / "main.ritz").write_text(program)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        [
            "python3",
            str(RITZ_ROOT / "build.py"),
            "build",
            str(pkg),
            "--compiler",
            compiler,
        ],
        cwd=pkg,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    exe = pkg / "build" / "debug" / name
    assert proc.returncode == 0 and exe.exists(), (
        f"build.py --compiler {compiler} failed:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"
    )
    return exe


def _check(exe: Path, args, env_extra, want_rc, want_out, want_err, label):
    env = dict(os.environ, **env_extra)
    run = subprocess.run([str(exe), *args], env=env, capture_output=True, timeout=60)
    assert run.stdout == want_out, f"{label} stdout: {run.stdout!r}"
    assert run.stderr == want_err, f"{label} stderr: {run.stderr!r}"
    assert run.returncode == want_rc, f"{label} exit {run.returncode}"


# ---------------------------------------------------------------------------
# ritzlib/timer.ritz, iovec.ritz (ritz0 and ritz1, #1684)
# ---------------------------------------------------------------------------


def _golden_body(name: str, start: str, prefix: str) -> str:
    """ritzlib/tests/test_<name>_output.ritz from `start` up to its first
    [[test]], with `run_body` renamed `<prefix>_body`."""
    src = (RITZ_ROOT / "ritzlib" / "tests" / f"test_{name}_output.ritz").read_text()
    body = src[src.index(start) : src.index("[[test]]")]
    return body.replace("fn run_body(", f"fn {prefix}_body(")


def _printers_program() -> str:
    """The goldens' case functions, driven by args[1] instead of fork."""
    return (
        "import ritzlib.sys\nimport ritzlib.io\nimport ritzlib.strview\n"
        "import ritzlib.timer\nimport ritzlib.iovec\n\n"
        + _golden_body("timer", "fn show(", "timer")
        + _golden_body("iovec", "fn case_empty(", "iovec")
        + """pub fn main(args: Span<StrView>) -> i32
    let which: u8 = args[1].ptr[0]
    if which == '1'
        return timer_body(1)
    if which == '2'
        return timer_body(2)
    if which == '3'
        return iovec_body(1)
    iovec_body(2)
"""
    )


def _printers_cases(compiler: str) -> dict:
    """case -> stdout (every case exits 0 with empty stderr)."""
    # Both compilers size "...µs" by its UTF-8 bytes (#1694).
    us = "µs"
    return {
        "1": (
            f"0ns\n999ns\n-5ns\n1.0{us}\n1.9{us}\n999.9{us}\n"
            "1.0ms\n2.3ms\n1.0s\n12.3s\n"
        ).encode(),
        "2": (
            "Stopwatch: total=5ms, count=0, avg=N/A\n"
            f"Stopwatch: total=7ms, count=3, avg=2500{us}"
        ).encode(),
        "3": b"IoVecBuilder: 0 iovecs, 0 pool bytes, 0 total bytes\n",
        "4": b"IoVecBuilder: 4 iovecs, 16 pool bytes, 22 total bytes\n"
        b"  [0] len=4\n  [1] len=11\n  [2] len=5\n  [3] len=2\n",
    }


@pytest.fixture(scope="module", params=["ritz0", "ritz1"])
def pgold(request, tmp_path_factory):
    if request.param == "ritz1":
        request.getfixturevalue("ritz1_bin")
    pkg = tmp_path_factory.mktemp(f"pgold_{request.param}")
    return request.param, _build(pkg, "pgold", _printers_program(), request.param)


@pytest.mark.parametrize("case", ["1", "2", "3", "4"])
def test_printers_output_is_byte_exact(pgold, case):
    compiler, exe = pgold
    want_out = _printers_cases(compiler)[case]
    _check(exe, [case], {}, 0, want_out, b"", f"printers case {case} ({compiler})")
