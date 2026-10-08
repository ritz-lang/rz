"""AGAST #1362: ritz1 lowers a struct literal in any value position.

THE DEFECT

ritz1 only lowered `T { ... }` as a let/var initialiser, a return value, a
reassignment, a nested field initialiser, or a method receiver: each of
those paths wrote the literal into a known slot. Everywhere else the
generic EXPR_STRUCT_LIT arm of emit_expr (ritz1/src/emitter_expr.ritz)
refused with "struct literal not in var initializer context". Before #1369
it emitted `add i64 0, 0` instead, which clang rejected. The contexts that hit it:

  * a function / method argument     `f(P { x: 3, y: 4 })`
  * a variant-constructor argument   `Some(P { .. })`, `Ok(Font { .. })`
  * an array-repeat element          `[P { .. }; 4]` (ritzlib/lang/tokens.ritz)
  * the same, nested as a field init `Q { ps: [P { .. }; 2], n: 1 }`

THE FIX

The generic arm now spills the literal into a fresh `alloca %T`, fills it
through emit_struct_lit_to_alloca (the one field-store loop every other
struct-literal path uses), and loads the `%T` aggregate as its value. For
`[T { .. }; N]`, emit_array_fill_into takes the element type from the
literal itself and stores that aggregate into each slot. Two consumers had
to learn the literal is an aggregate. One is the variant-ctor payload store
(emit_variant_struct). The other is the scalar→newtype arg boxing in the
impl-method and UFCS call paths, which re-boxed it through an i64.

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

# --- function / method arguments -------------------------------------------

FN_ARG = """\
struct P
    x: i64
    y: i64

fn area(p: P) -> i64
    return p.x * p.y

pub fn main() -> i32
    return area(P { x: 6, y: 7 }) as i32
"""

# Narrow and mixed-width fields, the literal between two scalar args, and
# fields written out of declaration order.
FN_ARG_MIXED = """\
struct M
    a: u8
    b: i32
    c: bool
    d: i64
    e: u16

fn check(k: i64, m: M, j: i32) -> i32
    if m.a != 200
        return 1
    if m.b != -5
        return 2
    if m.c != true
        return 3
    if m.d != 1000000000000
        return 4
    if m.e != 60000
        return 5
    return (k + j as i64) as i32

pub fn main() -> i32
    return check(30, M { e: 60000, d: 1000000000000, c: true, b: -5, a: 200 }, 12)
"""

# Two literals in one call, both by value: each needs its own temp.
TWO_ARGS = """\
struct P
    x: i64
    y: i64

fn dot(a: P, b: P) -> i64
    return a.x * b.x + a.y * b.y

pub fn main() -> i32
    return dot(P { x: 2, y: 3 }, P { x: 6, y: 10 }) as i32
"""

# The field values are expressions, including a call taking a literal.
NESTED_CALL = """\
struct P
    x: i64
    y: i64

fn sum(p: P) -> i64
    return p.x + p.y

pub fn main() -> i32
    return sum(P { x: sum(P { x: 10, y: 11 }), y: 21 }) as i32
"""

# A literal argument inside a loop body: the temp is re-filled each time.
IN_LOOP = """\
struct P
    x: i64
    y: i64

fn sum(p: P) -> i64
    return p.x + p.y

pub fn main() -> i32
    var t: i64 = 0
    var i: i64 = 0
    while i < 6
        t = t + sum(P { x: i, y: 2 })
        i = i + 1
    return (t + 15) as i32
"""

METHOD_ARG = """\
struct P
    x: i64
    y: i64

struct Acc
    base: i64

impl Acc
    fn add(self: @Acc, p: P) -> i64
        return self.base + p.x + p.y

pub fn main() -> i32
    let a: Acc = Acc { base: 30 }
    return a.add(P { x: 5, y: 7 }) as i32
"""

# A struct with a struct-valued field, built inline in the argument.
NESTED_STRUCT_FIELD = """\
struct P
    x: i64
    y: i64

struct R
    lo: P
    hi: P

fn width(r: R) -> i64
    return (r.hi.x - r.lo.x) + (r.hi.y - r.lo.y)

pub fn main() -> i32
    return width(R { lo: P { x: 1, y: 2 }, hi: P { x: 21, y: 24 } }) as i32
"""

# --- variant-constructor arguments -----------------------------------------

# #1460 repro shape (Option<Point>), without the ritzlib.option import.
SOME_POINT = """\
struct Point
    x: i64
    y: i64

fn make() -> Option<Point>
    return Some(Point { x: 6, y: 7 })

pub fn main() -> i32
    var o: Option<Point> = make()
    let r: i64 = match o
        Some(p) => p.x * p.y
        None => 99
    return r as i32
"""

# angelo's `Ok(Font { ... })`.
OK_FONT = """\
struct Font
    size: i32
    weight: i64

fn load(ok: bool) -> Result<Font, i32>
    if ok
        return Ok(Font { size: 12, weight: 30 })
    return Err(7)

pub fn main() -> i32
    var r: Result<Font, i32> = load(true)
    let v: i64 = match r
        Ok(f) => f.size as i64 + f.weight
        Err(e) => e as i64
    return v as i32
"""

# --- array-repeat elements --------------------------------------------------

# The ticket's repro, every slot checked.
ARRAY_REPEAT = """\
struct P
    x: i64
    y: i64

pub fn main() -> i32
    var arr: [4]P = [P { x: 20, y: 22 }; 4]
    var i: i32 = 0
    while i < 4
        if arr[i].x != 20 or arr[i].y != 22
            return i + 1
        i = i + 1
    return (arr[2].x + arr[3].y) as i32
"""

# Narrow fields: the element stride is sizeof(S), not 8.
ARRAY_REPEAT_NARROW = """\
struct S
    a: u8
    b: i32
    c: u8

pub fn main() -> i32
    var arr: [5]S = [S { a: 1, b: 40, c: 1 }; 5]
    var t: i32 = 0
    var i: i32 = 0
    while i < 5
        if arr[i].a != 1 or arr[i].c != 1 or arr[i].b != 40
            return i + 1
        t = t + arr[i].a as i32 + arr[i].c as i32
        i = i + 1
    return t + 32
"""

# N > 16: the loop lowering of emit_array_fill_into rather than the unroll.
ARRAY_REPEAT_LARGE = """\
struct P
    x: i64
    y: i64

pub fn main() -> i32
    var arr: [40]P = [P { x: 1, y: 0 }; 40]
    var t: i64 = 0
    var i: i32 = 0
    while i < 40
        t = t + arr[i].x + arr[i].y
        i = i + 1
    return (t + 2) as i32
"""

# The ticket's nested form: a struct-element fill as a field initialiser.
ARRAY_REPEAT_FIELD = """\
struct P
    x: i64
    y: i64

struct Q
    ps: [2]P
    n: i64

pub fn main() -> i32
    let q: Q = Q { ps: [P { x: 10, y: 11 }; 2], n: 0 }
    if q.ps[0].x != 10 or q.ps[1].y != 11
        return 1
    return (q.ps[0].x + q.ps[0].y + q.ps[1].x + q.ps[1].y + q.n) as i32
"""

# The element literal's fields are evaluated once, not once per slot.
ARRAY_REPEAT_ONCE = """\
var calls: i64 = 0

fn seven() -> i64
    calls = calls + 1
    return 7

struct P
    x: i64
    y: i64

pub fn main() -> i32
    var arr: [3]P = [P { x: seven(), y: 0 }; 3]
    if calls != 1
        return calls as i32
    return (arr[0].x + arr[1].x + arr[2].x + 21) as i32
"""

CASES = {
    "fn_arg": (FN_ARG, 42),
    "fn_arg_mixed": (FN_ARG_MIXED, 42),
    "two_args": (TWO_ARGS, 42),
    "nested_call": (NESTED_CALL, 42),
    "in_loop": (IN_LOOP, 42),
    "method_arg": (METHOD_ARG, 42),
    "nested_struct_field": (NESTED_STRUCT_FIELD, 42),
    "some_point": (SOME_POINT, 42),
    "ok_font": (OK_FONT, 42),
    "array_repeat": (ARRAY_REPEAT, 42),
    "array_repeat_narrow": (ARRAY_REPEAT_NARROW, 42),
    "array_repeat_large": (ARRAY_REPEAT_LARGE, 42),
    "array_repeat_field": (ARRAY_REPEAT_FIELD, 42),
    "array_repeat_once": (ARRAY_REPEAT_ONCE, 42),
}

# --- ticket repros that need ritzlib (built as packages) --------------------

# The original repro: a literal straight into a generic Vec push.
VEC_PUSH = """\
import ritzlib.sys
import ritzlib.gvec

struct LineBounds
    start: i64
    length: i64

fn main() -> i32
    var lines: Vec<LineBounds> = vec_with_cap<LineBounds>(8)
    vec_push<LineBounds>(@lines, LineBounds { start: 7, length: 2 })
    vec_push<LineBounds>(@lines, LineBounds { start: 30, length: 3 })
    let l0: *LineBounds = lines.data + 0
    let l1: *LineBounds = lines.data + 1
    if l0.start != 7 or l0.length != 2
        return 1
    (l0.start + l0.length + l1.start + l1.length) as i32
"""

# #1460 repro verbatim (option_is_some needs ritzlib.option).
OPTION_POINT = """\
import ritzlib.sys
import ritzlib.option

struct Point
    x: i64
    y: i64

fn make() -> Option<Point>
    return Some(Point { x: 3, y: 4 })

fn main() -> i32
    var o: Option<Point> = make()
    return option_is_some<Point>(@o) - 1
"""

# UFCS path: `s.plus(..)` on a String dispatches to the free fn
# `string_plus(@s, ..)` (try_emit_ufcs_method), receiver param skipped.
UFCS_ARG = """\
import ritzlib.string

struct P
    x: i64
    y: i64

fn string_plus(s: @String, p: P) -> i64
    return string_len(s) + p.x + p.y

fn main() -> i32
    let s: String = string_new()
    s.plus(P { x: 20, y: 22 }) as i32
"""

PKG_CASES = {
    "vec_push": (VEC_PUSH, 42),
    "option_point": (OPTION_POINT, 0),
    "ufcs_arg": (UFCS_ARG, 42),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    program, want = CASES[name]
    assert _run("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_struct_lit_rvalue(ritz1_bin, tmp_path, name):  # noqa: F811
    """ritz1 refused a struct literal outside a var initialiser (#1362)."""
    program, want = CASES[name]
    assert _run("ritz1", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PKG_CASES))
def test_ritz0_oracle_pkg(tmp_path, name):
    program, want = PKG_CASES[name]
    assert _run_pkg("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PKG_CASES))
def test_ritz1_struct_lit_rvalue_pkg(ritz1_bin, tmp_path, name):  # noqa: F811
    program, want = PKG_CASES[name]
    assert _run_pkg("ritz1", tmp_path, name, program) == want


@pytest.mark.integration
def test_ritz1_compiles_ritzlib_lang_tokens(ritz1_bin, tmp_path):  # noqa: F811
    """Acceptance: tokendefs_new's `[TokenDef { .. }; N]` lowers under ritz1."""
    src = RITZ_ROOT / "ritzlib" / "lang" / "tokens.ritz"
    out = tmp_path / "tokens.ll"
    comp = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(out)],
        cwd=tmp_path,
        env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode == 0 and out.exists(), (
        f"ritz1 failed on ritzlib/lang/tokens.ritz:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    # The IR must also be valid, not merely emitted.
    obj = subprocess.run(
        ["clang", "-c", str(out), "-o", str(tmp_path / "tokens.o")],
        capture_output=True,
        text=True,
    )
    assert obj.returncode == 0, f"invalid IR for tokens.ritz:\n{obj.stderr[-2000:]}"
