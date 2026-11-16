"""AGAST #3471 (LARB R56): ritz1 and ritz1_selfhosted refuse a closure or
lambda written as an expression, located at the `|` (or `||`) or `fn` that
opens it, in ritz0's words (#3470, test_closures_refused.py):

    main.ritz:2:29: error: closures aren't supported: write a named fn and pass it by name (§5.5)

ritz1 already failed these at the parse, but with "unexpected '|'" /
"unexpected 'fn'" at whatever token the backtracking parser gave up on.  The
rows are ritz0's REFUSED, plus a multi-param `|x: i32, y|`.  `|` / `||` as
operators and `fn(..)` as a type stay accepted.
"""

import os
import subprocess
from pathlib import Path

import pytest
from test_closures_refused import MSG, REFUSED

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ1S = ["ritz1", "ritz1_selfhosted"]

# One more shape than ritz0's rows: several params, one typed.
ROWS = dict(
    REFUSED,
    pipe_two_params=("fn main() -> i32\n    let f = |x: i32, y| x + y\n    0\n", 2, 13),
)


def _compile(compiler, tmp_path, src):
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    (tmp_path / "main.ritz").write_text(src)
    ll = tmp_path / "main.ll"
    env = dict(
        os.environ, RITZ_PATH=str(RITZ_ROOT), RITZ_CACHE_DIR=str(tmp_path / "cas")
    )
    proc = subprocess.run(
        [str(binary), "main.ritz", "-o", str(ll)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return proc, ll


@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(ROWS))
def test_closure_expression_is_a_located_error(tmp_path, compiler, name):
    src, line, column = ROWS[name]
    proc, ll = _compile(compiler, tmp_path, src)
    assert proc.returncode != 0, proc.stderr
    assert not ll.exists()
    errors = [l for l in proc.stderr.splitlines() if ": error: " in l]
    assert errors == [f"main.ritz:{line}:{column}: error: {MSG}"], proc.stderr


# Each closure in a file is reported once, where it is written, however often
# the backtracking parser re-reads it.
@pytest.mark.parametrize("compiler", RITZ1S)
def test_each_closure_is_reported_once(tmp_path, compiler):
    src = (
        "fn apply(f: fn(i32) -> i32, x: i32) -> i32\n"
        "    f(x)\n"
        "\n"
        "fn main() -> i32\n"
        "    let a = apply(|x| x * 2, 1)\n"
        "    let b = apply(fn(x: i32) -> i32 x, 2)\n"
        "    a + b\n"
    )
    proc, ll = _compile(compiler, tmp_path, src)
    assert proc.returncode != 0, proc.stderr
    assert not ll.exists()
    errors = [l for l in proc.stderr.splitlines() if ": error: " in l]
    assert errors == [
        f"main.ritz:5:19: error: {MSG}",
        f"main.ritz:6:19: error: {MSG}",
    ], proc.stderr


# The alternative to a closure, and the `|` / `||` operators, still compile.
@pytest.mark.parametrize("compiler", RITZ1S)
def test_named_fn_by_name_and_or_operators_still_compile(tmp_path, compiler):
    src = (
        "fn double(x: i32) -> i32\n"
        "    x * 2\n"
        "\n"
        "fn apply(f: fn(i32) -> i32, x: i32) -> i32\n"
        "    f(x)\n"
        "\n"
        "fn main() -> i32\n"
        "    let a: i32 = apply(double, 1) | 4\n"
        "    let b: bool = a == 6 || a == 7\n"
        "    if b then 0 else 1\n"
    )
    proc, ll = _compile(compiler, tmp_path, src)
    assert proc.returncode == 0, proc.stderr
    assert ll.exists()
