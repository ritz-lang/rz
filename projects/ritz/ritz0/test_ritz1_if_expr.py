"""Regression tests for AGAST #1613: ritz1 must parse and lower a block-form
`if`/`else` used as a value.

    let n: i32 = if x < 0
        1
    else
        0

docs/LANGUAGE_SPEC.md §6.1 documents `if` as an expression and ritz0 accepts
it, but ritz1's grammar only had `if_stmt`, so `let_stmt` (which takes `expr
NEWLINE` or `match_expr_rhs`) refused it and the enclosing fn died with
`cannot parse item`.

The fix adds `if_expr_rhs` (IF expr block ELSE block, ending in DEDENT like
`match_expr_rhs`) to let / var / return, and an EXPR_IF node that lowers
through the match-value machinery: each arm is a wildcard MatchArm built by
match_arm_set_block, and the merge is one phi typed exactly as a match's.
A nested `if`/`else` that ends an arm (including an `else if` chain) is that
arm's value.

Not covered: the inline `if c then a else b` form (ritz1 has no `then`
token, AGAST #1753) — see RITZ1_CANNOT_PARSE in
test_ritz1_implicit_narrowing.py.  The narrowing parity cases for the block
form are the if_block_* entries there.

ritz0 is the oracle. Every program exits 42 on success.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# Build product, not a tracked file (see test_ritz1_ptr_arith_chain.py).
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date so we never assert against a stale grammar."""
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        ["make", "-C", "ritz1", "ritz1"],
        cwd=RITZ_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if proc.returncode != 0 or not RITZ1_BIN.exists():
        pytest.fail(
            "could not build ritz1 for the if-expression tests:\n"
            f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )


def _build_runtime_start() -> None:
    proc = subprocess.run(
        ["make", "-C", "runtime", RITZ_START.name],
        cwd=RITZ_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0 or not RITZ_START.exists():
        pytest.fail(
            f"could not build the runtime start object {RITZ_START}:\n"
            f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
        )


@pytest.fixture(scope="module")
def ritz1_bin() -> Path:
    _build_ritz1()
    _build_runtime_start()
    return RITZ1_BIN


# --- programs -----------------------------------------------------------------

# #1613's repro, both ways round so a constant-folded arm can't pass it.
REPRO = """\
fn sign(x: i32) -> i32
    let n: i32 = if x < 0
        1
    else
        0
    n

fn main() -> i32
    sign(0 - 3) * 40 + sign(3) + 2
"""

# No annotation: the slot takes its type from the phi.
UNTYPED_LET = """\
fn f(c: i64) -> i64
    let n = if c == 1
        40
    else
        7
    n + 2

fn main() -> i32
    if f(0) != 9
        return 1
    f(1) as i32
"""

# `var`, then reassigned, so the slot really is mutable.
VAR_FORM = """\
fn main() -> i32
    let c: i32 = 5
    var n: i32 = if c > 3
        40
    else
        0
    n = n + 2
    n
"""

# `return if ...` in a non-tail position, with statements after it.
RETURN_VALUE = """\
fn f(flag: i32, v: i32) -> i32
    if flag == 1
        return if v > 10
            42
        else
            1
    let w: i32 = v + 1
    w

fn main() -> i32
    if f(1, 3) != 1
        return 1
    if f(0, 41) != 42
        return 2
    f(1, 20)
"""

# A nested if/else as the then-arm's value, and another inside the else arm.
NESTED = """\
fn g(a: i32, b: i32) -> i32
    let n: i32 = if a > 0
        if b > 0
            1
        else
            2
    else
        if b > 0
            3
        else
            4
    n

fn main() -> i32
    let r: i32 = g(1, 1) * 1000 + g(1, 0) * 100 + g(0, 1) * 10 + g(0, 0)
    if r != 1234
        return 1
    42
"""

# `else if` chain: the else arm is a single if_stmt.
ELSE_IF_CHAIN = """\
fn classify(x: i32) -> i32
    return if x < 0
        1
    else if x == 0
        2
    else
        3

fn main() -> i32
    let r: i32 = classify(0 - 5) * 100 + classify(0) * 10 + classify(9)
    if r != 123
        return 1
    42
"""

# Arms with leading statements; their locals don't leak past the arm.
BLOCK_ARMS = """\
fn f(c: i32) -> i64
    let n: i64 = if c == 1
        let a: i32 = 40
        let b: i32 = a + 1
        b + 1
    else
        let a: i32 = 3
        a
    n

fn main() -> i32
    if f(0) != 3
        return 1
    f(1) as i32
"""

# A bool condition (an i1 register, not an i64 to compare with 0).
BOOL_COND = """\
fn f(c: bool) -> i32
    let n: i32 = if c
        42
    else
        1
    n

fn main() -> i32
    if f(false) != 1
        return 1
    f(true)
"""

# StrView-valued arms: the phi must be a %StrView, not i64.
STRVIEW = """\
import ritzlib.strview

fn pick(c: i32) -> StrView
    let s = if c == 1
        "Seven"
    else
        "(none)"
    s

fn main() -> i32
    let a = pick(1)
    if a.len != 5 or *a.ptr != 83
        return 1
    let b: StrView = pick(0)
    if b.len != 6 or *b.ptr != 40
        return 2
    42
"""

# An if-expression in a loop body, evaluated many times.
IN_LOOP = """\
fn main() -> i32
    var total: i32 = 0
    for i in 0..10
        let d: i32 = if i % 2 == 0
            8
        else
            0
        total = total + d
    total + 2
"""

# An if-expression in a generic fn: monomorph must clone the arms (and
# substitute T inside them).  `return if` rather than `let r: T = if`: a
# `let r: T` local in a generic fn is broken on its own (AGAST #1751).
GENERIC = """\
fn pick<T>(c: i32, a: T, b: T) -> T
    return if c == 1
        a
    else
        b

fn main() -> i32
    let x: i32 = pick<i32>(1, 42, 7)
    let y: i64 = pick<i64>(0, 1, 9)
    if y != 9
        return 1
    x
"""

# An arm that leaves via `return` has no value and needs none.  ritz1-only:
# ritz0 binds 0 here instead of 2 (AGAST #1752), so it cannot be the oracle.
DIVERGING = """\
fn f(c: i32) -> i32
    let n: i64 = if c != 0
        2
    else
        return 40
    n as i32

fn main() -> i32
    f(0) + f(1)
"""

# A generic instantiation reached ONLY from inside an if arm: monomorph's
# collector must walk the arms or `ident$i64` is never specialised.
GENERIC_CALL_IN_ARM = """\
fn ident<T>(v: T) -> T
    v

fn main() -> i32
    let c: i32 = 1
    let n: i64 = if c == 1
        ident<i64>(21)
    else
        0
    (n * 2) as i32
"""

PROGRAMS = {
    "generic_call_in_arm": GENERIC_CALL_IN_ARM,
    "repro": REPRO,
    "untyped_let": UNTYPED_LET,
    "var_form": VAR_FORM,
    "return_value": RETURN_VALUE,
    "nested": NESTED,
    "else_if_chain": ELSE_IF_CHAIN,
    "block_arms": BLOCK_ARMS,
    "bool_cond": BOOL_COND,
    "strview": STRVIEW,
    "in_loop": IN_LOOP,
    "generic": GENERIC,
}

RITZ1_ONLY = {
    "diverging": DIVERGING,
}

# An if-expression with no `else` has no value; both compilers reject it.
MALFORMED = {
    "no_else": """\
fn f(c: i32) -> i32
    let n: i32 = if c == 1
        1
    n

fn main() -> i32
    f(1)
""",
    # The arm's value is a nested `if` with no `else`.
    "nested_no_else": """\
fn f(c: i32, d: i32) -> i32
    let n: i32 = if c == 1
        if d == 1
            1
    else
        2
    n

fn main() -> i32
    f(1, 1)
""",
    "return_no_else": """\
fn f(c: i32) -> i32
    return if c == 1
        1

fn main() -> i32
    f(1)
""",
}


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    src = work / "main.ritz"
    src.write_text(program)
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)]
    comp = subprocess.run(
        cmd, cwd=work, env=env, capture_output=True, text=True, timeout=300
    )
    return comp, ll, work


def _run(compiler: str, tmp_path: Path, name: str):
    """Compile PROGRAMS[name] with `compiler`, link and run it; return the process."""
    program = PROGRAMS[name] if name in PROGRAMS else RITZ1_ONLY[name]
    comp, ll, work = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = work / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=work, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)


def _check(proc, name: str) -> None:
    assert proc.returncode == 42, f"{name}: exit {proc.returncode}, stdout={proc.stdout!r}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    _check(_run("ritz0", tmp_path, name), name)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_if_expr(ritz1_bin, tmp_path, name):
    """AGAST #1613. Before the fix these died with `cannot parse item`."""
    _check(_run("ritz1", tmp_path, name), name)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ1_ONLY))
def test_ritz1_if_expr_beyond_ritz0(ritz1_bin, tmp_path, name):
    """Shapes ritz0 gets wrong; each names its ritz0 ticket above."""
    _check(_run("ritz1", tmp_path, name), name)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_ritz0_rejects_if_expr_without_else(tmp_path, name):
    comp, ll, _ = _compile("ritz0", tmp_path, name, MALFORMED[name])
    assert comp.returncode != 0, f"ritz0 accepted {name!r}: the oracle moved"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_ritz1_rejects_if_expr_without_else(ritz1_bin, tmp_path, name):
    comp, ll, _ = _compile("ritz1", tmp_path, name, MALFORMED[name])
    assert comp.returncode != 0, (
        f"ritz1 accepted if-expression without else {name!r}:\n{comp.stdout[-1000:]}"
    )
    assert not ll.exists(), f"ritz1 wrote an artifact for malformed {name!r}"
