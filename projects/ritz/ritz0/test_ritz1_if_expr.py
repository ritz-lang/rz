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

The inline_* programs cover the single-line `if c then a else b` form
(AGAST #1753): primary_expr's `IF expr THEN expr ELSE expr`, lowered through
the same EXPR_IF / expr_if path by expr_if_inline.  The narrowing parity
cases for both forms live in test_ritz1_implicit_narrowing.py.

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

# --- inline `if c then a else b` (AGAST #1753) ----------------------------------

# #1753's repro (tier4 36_timeout:207 / 39_time:162), taken both ways.
INLINE_REPRO = """\
fn clamp(a: i32) -> i32
    let m: i32 = if a < 255 then a else 255 as i32
    return m

fn main() -> i32
    if clamp(300) != 255
        return 1
    clamp(42)
"""

# No annotation: the slot takes its type from the phi.
INLINE_UNTYPED = """\
fn f(c: i64) -> i64
    let n = if c == 1 then 40 else 7
    n + 2

fn main() -> i32
    if f(0) != 9
        return 1
    f(1) as i32
"""

# `return if ...`, and an inline if as a call argument and an operand.
INLINE_POSITIONS = """\
fn twice(x: i32) -> i32
    x * 2

fn f(c: i32) -> i32
    return if c > 0 then 20 else 1

fn main() -> i32
    let a: i32 = twice(if f(1) == 20 then 10 else 0)
    let b: i64 = (a as i64) + (if a == 20 then 22 else 0)
    if f(0) != 1
        return 1
    b as i32
"""

# Both arms take a whole expression, as in ritz0: `else 2 + 40` is 42, and
# `else if` chains right-nest.
INLINE_ARM_EXTENT = """\
fn classify(x: i32) -> i32
    if x < 0 then 1 else if x == 0 then 2 else 3

fn main() -> i32
    let c: i32 = 0
    let n: i32 = if c == 1 then 1 else 2 + 40
    let r: i32 = classify(0 - 5) * 100 + classify(0) * 10 + classify(9)
    if r != 123
        return 1
    n
"""

# Nested inline ifs as the then-arm, in a loop.
INLINE_NESTED_LOOP = """\
fn main() -> i32
    var total: i32 = 0
    for i in 0..10
        let d: i32 = if i % 2 == 0 then if i < 3 then 6 else 2 else 0
        total = total + d
    total + 24
"""

PROGRAMS = {
    "inline_repro": INLINE_REPRO,
    "inline_untyped": INLINE_UNTYPED,
    "inline_positions": INLINE_POSITIONS,
    "inline_arm_extent": INLINE_ARM_EXTENT,
    "inline_nested_loop": INLINE_NESTED_LOOP,
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
    # Inline form with no `else` (AGAST #1753).
    "inline_no_else": """\
fn f(c: i32) -> i32
    let n: i32 = if c == 1 then 1
    n

fn main() -> i32
    f(1)
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
