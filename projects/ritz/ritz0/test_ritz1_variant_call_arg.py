"""AGAST #1498 (and #1570): ritz1 builds a variant constructor passed directly
as a call argument at the CALLEE's parameter type.

THE DEFECT

emit_variant_struct (ritz1/src/emitter_expr_call.ritz) and the unit-`None`
path (emitter_expr_access.ritz) took their enum type only from a typed
let/var binding (`s.ctx_enum_name`) or the ENCLOSING function's return type.
No call path set the context from the callee's parameter type, so
`g(Some(10))` with `g(o: Option<i64>)`:

  * in a fn that doesn't return an Option, fell back to `add i64 0, 0` and
    clang rejected `call i32 @g(%Option$i64 %.1)`;
  * in a fn returning `Option<i64>`, built an `%Option$i64` for a
    `%Option$i32` param: a type confusion clang caught only because the
    layouts differed.

THE FIX

Every call path (plain, impl method, static `Type.method`, UFCS) now emits
each argument with the enum context set from its parameter: the param's
type when it is a tagged enum, else no context at all. Inside an argument
the enclosing fn's return type is never consulted, so a constructor with no
enum-typed parameter to land in is a ritz1 error rather than invalid IR.

Oracle: ritz0 builds and runs every program with the same exit code.
"""

import os
import subprocess

import pytest

from test_ritz1_builtin_struct_shadow import (  # noqa: F401
    RITZ1_BIN,
    RITZ_ROOT,
    _run,
    _run_pkg,
    ritz1_bin,
)

G_I64 = """\
fn g(o: Option<i64>) -> i32
    let r: i32 = match o
        Some(v) => (v - 3) as i32
        None => 0
    return r
"""

# Ticket repro: Some(x) / None straight into an Option<i64> param from a fn
# that does not return an Option (the zero-i64 fallback).
SOME_I64 = (
    G_I64
    + """
pub fn main() -> i32
    return g(Some(10))
"""
)

NONE_I64 = (
    G_I64
    + """
pub fn main() -> i32
    return g(None) + 5
"""
)

# Ticket "worse variant": inside a fn returning Option<i64>, a ctor passed to
# an Option<i32> param must not borrow the return type.
NESTED_RET = """\
fn g(o: Option<i32>) -> i32
    let r: i64 = match o
        Some(v) => v as i64 + 4
        None => 1
    return r as i32

fn h() -> Option<i64>
    let r: i32 = g(Some(3 as i32))
    let n: i32 = g(None)
    Some((r + n * 10) as i64)

pub fn main() -> i32
    let o: Option<i64> = h()
    let r: i32 = match o
        Some(v) => v as i32
        None => 99
    return r
"""

# A typed let's context must not leak into a call argument inside its
# initialiser: `let v: Option<i64> = wrap(g(Some(..)))` with g taking
# Option<i32>. (The `Some(g(Some(..)))` spelling is avoided: ritz0 itself
# leaks the let's type there — AGAST #1577.)
LET_CTX_LEAK = """\
fn g(o: Option<i32>) -> i64
    let r: i64 = match o
        Some(v) => v as i64 * 2
        None => 1
    return r

fn wrap(x: i64) -> Option<i64>
    Some(x)

pub fn main() -> i32
    let v: Option<i64> = wrap(g(Some(20 as i32)) + g(None))
    let r: i32 = match v
        Some(x) => x as i32
        None => 99
    return r
"""

# AGAST #1570 repro.
PICK_1570 = """\
fn pick(o: Option<i32>) -> i32
    let r: i64 = match o
        Some(v) => v as i64 + 1
        None => 0
    return r as i32

pub fn main() -> i32
    if pick(None) != 0
        return 1
    return pick(Some(41))
"""

# Result params too, and a second arg after a non-enum one.
RESULT_ARG = """\
fn f(k: i64, r: Result<i64, i32>) -> i32
    let x: i32 = match r
        Ok(v) => (v + k) as i32
        Err(e) => e
    return x

pub fn main() -> i32
    return f(2, Ok(30)) + f(0, Err(10))
"""

# Method-call receiver variant: `x.m(Some(1))` (impl method, self skipped).
METHOD_ARG = """\
struct S
    base: i64

impl S
    fn m(self: @S, o: Option<i64>) -> i32
        let r: i64 = match o
            Some(v) => self.base + v
            None => 100
        return r as i32

pub fn main() -> i32
    let x: S = S { base: 40 }
    if x.m(None) != 100
        return 1
    return x.m(Some(2))
"""

# Static `Type.method(Some(..))` (no receiver param to skip).
STATIC_METHOD_ARG = """\
struct S
    base: i64

impl S
    fn mk(o: Option<i64>) -> S
        let b: i64 = match o
            Some(v) => v
            None => 7
        return S { base: b }

pub fn main() -> i32
    let a: S = S.mk(Some(35))
    let b: S = S.mk(None)
    return (a.base + b.base) as i32
"""

# StrView payloads need ritzlib, so these build as packages.
G_STRVIEW = """\
import ritzlib.option
import ritzlib.strview

fn g(o: Option<StrView>) -> i32
    if option_is_some<StrView>(@o) != 0
        return 7
    0
"""

SOME_STRVIEW = (
    G_STRVIEW
    + """
fn main() -> i32
    g(Some("10"))
"""
)

NONE_STRVIEW = (
    G_STRVIEW
    + """
fn main() -> i32
    g(None) + 3
"""
)

# Same StrView payload through a typed let: the ctor stored the "..."
# literal's %Span$u8 aggregate as an i64.
LET_SOME_STRVIEW = (
    G_STRVIEW
    + """
fn main() -> i32
    let o: Option<StrView> = Some("10")
    g(o) + 1
"""
)

# UFCS path: `s.take(..)` on a String dispatches to the free fn
# `string_take(@s, ..)` (ufcs_non_generic_prefix); receiver param skipped.
UFCS_ARG = """\
import ritzlib.string

fn string_take(s: @String, o: Option<i64>) -> i64
    let r: i64 = match o
        Some(v) => v + string_len(s)
        None => 30
    return r

fn main() -> i32
    let s: String = string_new()
    (s.take(Some(12)) + s.take(None)) as i32
"""

CASES = {
    "some_i64": (SOME_I64, 7),
    "none_i64": (NONE_I64, 5),
    "nested_ret": (NESTED_RET, 17),
    "let_ctx_leak": (LET_CTX_LEAK, 41),
    "pick_1570": (PICK_1570, 42),
    "result_arg": (RESULT_ARG, 42),
    "method_arg": (METHOD_ARG, 42),
    "static_method_arg": (STATIC_METHOD_ARG, 42),
}

PKG_CASES = {
    "some_strview": (SOME_STRVIEW, 7),
    "none_strview": (NONE_STRVIEW, 3),
    "let_some_strview": (LET_SOME_STRVIEW, 8),
    "ufcs_arg": (UFCS_ARG, 42),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_oracle(tmp_path, name):
    program, want = CASES[name]
    assert _run("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_variant_call_arg(ritz1_bin, tmp_path, name):  # noqa: F811
    program, want = CASES[name]
    assert _run("ritz1", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PKG_CASES))
def test_ritz0_oracle_pkg(tmp_path, name):
    program, want = PKG_CASES[name]
    assert _run_pkg("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PKG_CASES))
def test_ritz1_variant_call_arg_pkg(ritz1_bin, tmp_path, name):  # noqa: F811
    program, want = PKG_CASES[name]
    assert _run_pkg("ritz1", tmp_path, name, program) == want


# A ctor whose parameter is not an enum has no type to be built at. It used
# to borrow the enclosing fn's Option return type (or emit a zero i64) and
# fail only at clang; it must now be a ritz1 error.
NO_ENUM_PARAM = """\
fn k(x: i64) -> i64
    return x

fn h() -> Option<i64>
    let r: i64 = k(Some(1))
    Some(r)

pub fn main() -> i32
    0
"""

NO_ENUM_PARAM_NONE = NO_ENUM_PARAM.replace("k(Some(1))", "k(None)")

# Same, but the enum type on offer comes from a typed let rather than the
# return type: the let's context must be cleared for k's i64 param.
NO_ENUM_PARAM_LET = """\
fn k(x: i64) -> i64
    return x

fn wrap(x: i64) -> Option<i64>
    Some(x)

pub fn main() -> i32
    let v: Option<i64> = wrap(k(Some(1)))
    0
"""


@pytest.mark.integration
@pytest.mark.parametrize(
    "program",
    [NO_ENUM_PARAM, NO_ENUM_PARAM_NONE, NO_ENUM_PARAM_LET],
    ids=["some", "none", "let"],
)
def test_ritz1_ctor_without_enum_param_is_an_error(ritz1_bin, tmp_path, program):  # noqa: F811
    src = tmp_path / "noenum.ritz"
    src.write_text(program)
    comp = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(tmp_path / "noenum.ll")],
        cwd=tmp_path,
        env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode != 0, "ritz1 accepted a ctor with no enum-typed param"
    assert "enum context" in comp.stderr, comp.stderr[-2000:]
