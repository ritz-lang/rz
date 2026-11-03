"""AGAST #1642: byte-exact output of ritzlib printers that ritzlib/tests can't reach.

#1642 turned ritzlib's hand-rolled prints/eprints/print_int chains into single
print/eprint interpolations.  Output must stay byte-identical, on the same fd,
with the same exit status.  ritzlib/tests/test_{argspec,args,env}_output.ritz
pin most of it under ritz0; this file covers the two things they can't:

* (ritzlib/testing.ritz's assertion helpers were pinned here until AGAST
  #1869 deleted the module: `assert` itself now prints both operands; see
  ritz0/test/test_assert_operands.ritz.)
* ritzlib/args.ritz is compiled by ritz1 for every example that imports it, so
  its converted printers are also built with `--compiler ritz1` and both
  binaries must print the same pinned bytes.  The cases are the ones in
  ritzlib/tests/test_args_output.ritz (read from that file, so they can't
  drift apart).  argspec and os/env are not here: ritz1 cannot compile either
  module yet (scripts/regression-known-failures-ritz1.txt; env_must's block
  match arm, #1454).

AGAST #1684 did the same to timer, iovec, lang/tokens and elf.  ritz1
compiles all four, so the timer/iovec/tokens cases from
ritzlib/tests/test_{timer,iovec,tokens}_output.ritz are built with both
compilers below.  elf is ritz0 only: its golden finds `pub fn test_*` symbols
in the [[test]] harness binary, which a package build doesn't reproduce.
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
# ritzlib/args.ritz (ritz0 and ritz1)
# ---------------------------------------------------------------------------


def _args_program() -> str:
    """test_args_output.ritz's case functions, driven by argv[1] instead of fork."""
    src = (RITZ_ROOT / "ritzlib" / "tests" / "test_args_output.ritz").read_text()
    cases = src[src.index("fn setup(") : src.index("fn run_body(")]
    return (
        "import ritzlib.sys\nimport ritzlib.io\nimport ritzlib.args\n\n"
        + cases
        + """fn main(argc: i32, argv: **u8) -> i32
    let which: u8 = *(*(argv + 1))
    if which == '1'
        return case_long_errors()
    if which == '2'
        return case_short_errors()
    if which == '3'
        return case_positional_errors()
    case_help()
"""
    )


# case -> (exit status, stdout, stderr).
ARGS_CASES = {
    "1": (
        4,
        b"",
        b"prog: unknown option '--bogus'\n"
        b"prog: option '--verbose' doesn't accept a value\n"
        b"prog: unknown option '--bogus'\n"
        b"prog: option '--count' requires a value\n",
    ),
    # #1683: the option char goes to stderr with the rest of the message.
    "2": (2, b"", b"prog: unknown option '-z'\nprog: option '-n' requires a value\n"),
    "3": (
        2,
        b"",
        b"prog: missing required argument 'FILE'\nprog: too many arguments\n",
    ),
    "4": (
        0,
        b"Usage: prog [OPTIONS] FILE...\n\nDoes things\n\nOptions:\n"
        b"  -v, --verbose\n        Say more\n"
        b"  -q\n        Quiet\n"
        b"  -n, --count=NUM\n        How many (default: 10)\n"
        b"      --name=S\n        Who\n"
        b"  -x\n        Short value (default: 3)\n"
        b"\nArguments:\n  FILE\n        Input files\n"
        b"Usage: bare [OPTIONS] [ARG...]\n\nArguments:\n  ARG\n        An arg\n",
        b"",
    ),
}


@pytest.fixture(scope="module", params=["ritz0", "ritz1"])
def agold(request, tmp_path_factory) -> Path:
    if request.param == "ritz1":
        request.getfixturevalue("ritz1_bin")
    pkg = tmp_path_factory.mktemp(f"agold_{request.param}")
    return _build(pkg, "agold", _args_program(), request.param)


@pytest.mark.parametrize("case", sorted(ARGS_CASES))
def test_args_output_is_byte_exact(agold, case):
    want_rc, want_out, want_err = ARGS_CASES[case]
    _check(
        agold,
        [case],
        {},
        want_rc,
        want_out,
        want_err,
        f"args case {case} ({agold.parent})",
    )


# ---------------------------------------------------------------------------
# ritzlib/timer.ritz, iovec.ritz, lang/tokens.ritz (ritz0 and ritz1, #1684)
# ---------------------------------------------------------------------------


def _golden_body(name: str, start: str, prefix: str) -> str:
    """ritzlib/tests/test_<name>_output.ritz from `start` up to its first
    [[test]], with `run_body` renamed `<prefix>_body`."""
    src = (RITZ_ROOT / "ritzlib" / "tests" / f"test_{name}_output.ritz").read_text()
    body = src[src.index(start) : src.index("[[test]]")]
    return body.replace("fn run_body(", f"fn {prefix}_body(")


def _printers_program() -> str:
    """The goldens' case functions, driven by argv[1] instead of fork."""
    return (
        "import ritzlib.sys\nimport ritzlib.io\nimport ritzlib.strview\n"
        "import ritzlib.timer\nimport ritzlib.iovec\nimport ritzlib.lang.tokens\n\n"
        + _golden_body("timer", "fn show(", "timer")
        + _golden_body("iovec", "fn case_empty(", "iovec")
        + _golden_body("tokens", "fn run_body(", "tokens")
        + """fn main(argc: i32, argv: **u8) -> i32
    let which: u8 = *(*(argv + 1))
    if which == '1'
        return timer_body(1)
    if which == '2'
        return timer_body(2)
    if which == '3'
        return iovec_body(1)
    if which == '4'
        return iovec_body(2)
    tokens_body(1)
"""
    )


# ritz0 sizes a plain "..." literal by code points, so "µs" prints as "µ"
# (#1694); ritz1 sizes it by bytes.  When #1694 is fixed, both are "µs".
MICRO = {"ritz0": "µ", "ritz1": "µs"}


def _printers_cases(compiler: str) -> dict:
    """case -> stdout (every case exits 0 with empty stderr)."""
    us = MICRO[compiler]
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
        "5": b"3:7 kind=5 'ident'\n10:200 kind=2 'foo'\n1:1 kind=0\n",
    }


@pytest.fixture(scope="module", params=["ritz0", "ritz1"])
def pgold(request, tmp_path_factory):
    if request.param == "ritz1":
        request.getfixturevalue("ritz1_bin")
    pkg = tmp_path_factory.mktemp(f"pgold_{request.param}")
    return request.param, _build(pkg, "pgold", _printers_program(), request.param)


@pytest.mark.parametrize("case", ["1", "2", "3", "4", "5"])
def test_printers_output_is_byte_exact(pgold, case):
    compiler, exe = pgold
    want_out = _printers_cases(compiler)[case]
    _check(exe, [case], {}, 0, want_out, b"", f"printers case {case} ({compiler})")
