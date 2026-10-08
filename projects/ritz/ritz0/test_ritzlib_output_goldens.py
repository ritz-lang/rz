"""AGAST #1642: byte-exact output of ritzlib printers that ritzlib/tests can't reach.

#1642 turned ritzlib's hand-rolled prints/eprints/print_int chains into single
print/eprint interpolations.  Output must stay byte-identical, on the same fd,
with the same exit status.  ritzlib/tests/test_{argspec,args,env}_output.ritz
pin most of it under ritz0; this file covers the two things they can't:

* ritzlib/testing.ritz defines its own `main` (calling the program's
  `__init_tests`), so it cannot be linked into a `[[test]]` harness.  It is
  built here as a package, one case per process via $TGOLD_CASE.  ritz0 only:
  ritz1 cannot parse the module's `asm` block.
* ritzlib/args.ritz is compiled by ritz1 for every example that imports it, so
  its converted printers are also built with `--compiler ritz1` and both
  binaries must print the same pinned bytes.  The cases are the ones in
  ritzlib/tests/test_args_output.ritz (read from that file, so they can't
  drift apart).  argspec and os/env are not here: ritz1 cannot compile either
  module yet (scripts/regression-known-failures-ritz1.txt; env_must's block
  match arm, #1454).
"""

import os
import subprocess
from pathlib import Path

import pytest

from test_ritz1_builtin_struct_shadow import RITZ_ROOT
from test_ritz1_builtin_struct_shadow import ritz1_bin  # noqa: F401


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
# ritzlib/testing.ritz (ritz0)
# ---------------------------------------------------------------------------

TESTING_PROGRAM = """\
import ritzlib.sys
import ritzlib.strview
import ritzlib.os.env
import ritzlib.testing

fn t_ok() -> i32
    0

fn t_bad() -> i32
    1

# ritzlib.testing's main calls this; the case comes from $TGOLD_CASE.
fn __init_tests()
    let case = env_get_or("TGOLD_CASE", "0")
    let which: u8 = strview_get(@case, 0)
    if which == '1'
        assert_msg(0, "boom")
    else if which == '2'
        assert_eq_i64(5, -7, "i64 differ")
    else if which == '3'
        assert_eq_i64(4294967297, 4294967298, "truncated")
    else if which == '4'
        assert_eq_i32(-3, 4, "i32 differ")
    else if which == '5'
        assert_not_null(null, "want ptr")
    else if which == '6'
        assert_null(c"x", "want null")
    else if which == '8'
        register_test("t_ok", t_ok as *u8)
        register_test("t_bad", t_bad as *u8)
        register_test("t_ok2", t_ok as *u8)
    else if which == '9'
        var i: i32 = 0
        while i <= 1024
            register_test("t", t_ok as *u8)
            i += 1
    return
"""

# case -> (exit status, stdout, stderr)
TESTING_CASES = {
    "0": (0, b"No tests registered.\n", b""),
    "1": (1, b"", b"Assertion failed: boom\n"),
    "2": (1, b"", b"Assertion failed: i64 differ\n  expected: -7\n  actual:   5\n"),
    # assert_eq_i64 reports both sides truncated to i32: 2^32 + 1 shows as 1,
    # 2^32 + 2 as 2.
    "3": (1, b"", b"Assertion failed: truncated\n  expected: 2\n  actual:   1\n"),
    "4": (1, b"", b"Assertion failed: i32 differ\n  expected: 4\n  actual:   -3\n"),
    "5": (1, b"", b"Assertion failed (null pointer): want ptr\n"),
    "6": (1, b"", b"Assertion failed (expected null): want null\n"),
    "8": (
        1,
        b"Running 3 tests:\n  [OK] t_ok\n  [FAIL] t_bad\n  [OK] t_ok2\n"
        b"\n2 passed, 1 failed\n",
        b"",
    ),
    "9": (1, b"", b"Error: Too many tests registered\n"),
}


@pytest.fixture(scope="module")
def tgold(tmp_path_factory) -> Path:
    return _build(tmp_path_factory.mktemp("tgold"), "tgold", TESTING_PROGRAM, "ritz0")


@pytest.mark.parametrize("case", sorted(TESTING_CASES))
def test_testing_output_is_byte_exact(tgold, case):
    want_rc, want_out, want_err = TESTING_CASES[case]
    _check(
        tgold,
        [],
        {"TGOLD_CASE": case},
        want_rc,
        want_out,
        want_err,
        f"testing case {case}",
    )


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
