"""AGAST #1681: ritz1 types an untyped `var q = p` from a by-value struct param.

THE DEFECT

emit_var_decl (ritz1/src/emitter_stmt.ritz) narrows an unannotated local's
type from its initializer (call, method, struct lit, member, try, cast,
addr-of), but had no EXPR_IDENT case. `var parsed = p` with `p: ParsedArgs`
kept the parser default TYPE_I64, so the slot was `alloca i64` and the
`%ParsedArgs` load was stored into it; clang rejected the IR ("'%.4' defined
with type '%ParsedArgs' but expected 'i64'"). This blocked
examples/tier2_stdlib/77_args (`run(spec, p)` does `var parsed = p`).

THE FIX

An EXPR_IDENT initializer naming a struct-typed local (by-value param or
`let`) gives the new local that struct type, so it gets an `alloca %S` slot
and is registered for `.field` access.

Oracle: ritz0 builds and runs every program with the same exit code.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run, ritz1_bin  # noqa: F401

# `var q = p` from a by-value param, then a field read.
VAR_FROM_PARAM = """\
struct Pair
    a: i64
    b: i64

fn sum(p: Pair) -> i64
    var q = p
    return q.a + q.b

pub fn main() -> i32
    let p = Pair { a: 40, b: 2 }
    return sum(p) as i32
"""

# `let` spelling, with a nested-struct field read through the copy.
LET_NESTED = """\
struct Inner
    x: i64
    y: i64

struct Outer
    tag: i64
    inner: Inner
    tail: i64

fn total(o: Outer) -> i64
    let q = o
    return q.tag + q.inner.x * 10 + q.inner.y * 100 + q.tail * 1000

pub fn main() -> i32
    let i = Inner { x: 2, y: 3 }
    let o = Outer { tag: 1, inner: i, tail: 0 }
    if total(o) != 321
        return 1
    return 42
"""

# argspec's `run` shape: copy the param, pass `@q` on, then mutate through
# `@&q` and read the mutation back through the copy.
REF_AND_MUT = """\
struct Inner
    x: i64
    y: i64

struct Box
    n: i64
    inner: Inner

fn peek(b: @Box) -> i64
    return b.n + b.inner.x + b.inner.y

fn bump(b: @&Box)
    b.n = b.n + 100
    b.inner.y = b.inner.y + 1000

fn run(p: Box) -> i64
    var parsed = p
    let before = peek(@parsed)
    bump(@&parsed)
    let after = peek(@parsed)
    return after - before

pub fn main() -> i32
    let i = Inner { x: 1, y: 2 }
    let b = Box { n: 3, inner: i }
    if run(b) != 1100
        return 1
    return 42
"""

# Copy of a struct-typed `let` local (not a param), and direct field store.
# (`p` is moved by `var q = p`, so it is not read afterwards.)
VAR_FROM_LOCAL = """\
struct Pair
    a: i64
    b: i64

pub fn main() -> i32
    let p = Pair { a: 1, b: 2 }
    var q = p
    q.a = 40
    return (q.a + q.b) as i32
"""

# A scalar ident initializer must still bind an i64 (no regression).
SCALAR_IDENT = """\
fn twice(n: i64) -> i64
    var m = n
    m = m + n
    return m

pub fn main() -> i32
    return twice(21) as i32
"""

CASES = {
    "var_from_param": (VAR_FROM_PARAM, 42),
    "let_nested": (LET_NESTED, 42),
    "ref_and_mut": (REF_AND_MUT, 42),
    "var_from_local": (VAR_FROM_LOCAL, 42),
    "scalar_ident": (SCALAR_IDENT, 42),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_oracle(tmp_path, name):
    program, want = CASES[name]
    assert _run("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_var_from_struct_param(ritz1_bin, tmp_path, name):  # noqa: F811
    program, want = CASES[name]
    assert _run("ritz1", tmp_path, name, program) == want
