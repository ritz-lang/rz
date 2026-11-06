"""AGAST #2287: ritz1 reads a whole array as the whole array.

THE DEFECT

emit_expr of a `[N]T` local gave its first 8 bytes as an i64, and three places
took that for the array, with no diagnostic from ritz1 or clang:

    fn g(a: [4]i32) -> i32      `g(a)`    a by-value param was an i64
    *p = a                                 8 bytes went through the pointer
    G = a                                  8 bytes went into the global

`g(a)` into `a:& [N]T` passed those 8 bytes as the pointer and segfaulted, and
`g(a)` into `a: *i32` did the same where ritz0 refuses it.

THE RULE, TAKEN FROM ritz0

    * A by-value array param is a first-class `[N x T]`, as ritz0 emits it.
    * `g(a)` into `a:& [N]T`, `a: @[N]T` or `a: @&[N]T` passes the address.
    * `[N]u8` into a `Span<u8>` keeps its coercion.
    * Any other param refuses a whole array, and a wrong length is refused
      everywhere.
    * Anything else that reads a whole array where only a scalar fits is an
      error, not a silent 8 bytes.

ritz0 also converts `[N]T1` to `[N]T2` element by element.  ritz1 refuses that,
as `b = a` and `h.a = a` already do; see ELEM_GAPS below.

Sizes matter: a `[2]i32` fits the 8 bytes that were copied, so the grid below
runs each route at sizes that fit and at sizes that don't.  ritz0 is the oracle
for every program.
"""

import os
import re
import subprocess

import pytest

from ritz0_inproc import run_ritz0
from test_ritz1_builtin_struct_shadow import RITZ_ROOT, _run


def _ints(values):
    return {"fill": lambda v, i: f"{v}[{i}] = {values(i)}",
            "check": lambda v, i: f"if {v}[{i}] != {values(i)}\n        return {10 + i}"}


def _floats():
    return {"fill": lambda v, i: f"{v}[{i}] = {i}.5",
            "check": lambda v, i: f"if {v}[{i}] != {i}.5\n        return {10 + i}"}


def _bools():
    # Alternating, so an all-zero copy can't pass.
    def check(v, i):
        cond = f"not {v}[{i}]" if i % 2 else f"{v}[{i}]"
        return f"if {cond}\n        return {10 + i}"
    return {"fill": lambda v, i: f"{v}[{i}] = {'true' if i % 2 else 'false'}", "check": check}


def _structs():
    return {"fill": lambda v, i: f"{v}[{i}].x = {i + 1}\n    {v}[{i}].y = {i + 2}",
            "check": lambda v, i: (f"if {v}[{i}].x != {i + 1}\n        return {10 + i}\n"
                                   f"    if {v}[{i}].y != {i + 2}\n        return {40 + i}")}


def _pointers():
    return {"fill": lambda v, i: f"{v}[{i}] = @N",
            "check": lambda v, i: f"if *{v}[{i}] != 7\n        return {10 + i}"}


# Each element type, with how to fill and check element i.
ELEMS = {
    "i8": _ints(lambda i: -(i + 1)),
    "u8": _ints(lambda i: 200 + i),
    "i16": _ints(lambda i: -(i + 300)),
    "u16": _ints(lambda i: 40000 + i),
    "i32": _ints(lambda i: -(i + 70000)),
    "u32": _ints(lambda i: 3000000000 + i),
    "i64": _ints(lambda i: -(i + 5000000000)),
    "u64": _ints(lambda i: 5000000000 + i),
    "f32": _floats(),
    "f64": _floats(),
    "bool": _bools(),
    "P": _structs(),
    "*i32": _pointers(),
}

# [2]u8 and [5]u8 fit in the 8 bytes that were copied; [17]u8 doesn't, and from
# i32 up neither does [5]T.
SIZES = (2, 5, 17)

PRELUDE = """\
struct P
    x: i32
    y: i64

struct R
    n: i32

var N: i32 = 7

"""

ROUTES = {
    "argument": """\
fn check(a: {ty}) -> i32
{check_a}
    return 3

pub fn main() -> i32
    var a: {ty}
{fill_a}
    return check(a)
""",
    "method_argument": """\
impl R
    fn check(self: *R, a: {ty}) -> i32
{check_a_method}
        return 3

pub fn main() -> i32
    var r: R = R {{ n: 0 }}
    var a: {ty}
{fill_a}
    return r.check(a)
""",
    "deref_untyped_let": """\
pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var b: [4]i32 = [0, 0, 0, 0]
    let p = @b
    *p = a
    return b[3]
""",
    "deref_store": """\
fn s(p: *{ty})
    var a: {ty}
{fill_a}
    *p = a

pub fn main() -> i32
    var b: {ty}
    s(@b)
{check_b}
    return 3
""",
    "global_store": """\
var G: {ty}

pub fn main() -> i32
    var a: {ty}
{fill_a}
    G = a
{check_g}
    return 3
""",
    "borrow_argument": """\
fn check(a:& {ty}) -> i32
    var b: {ty} = a
{check_b}
    return 3

pub fn main() -> i32
    var a: {ty}
{fill_a}
    return check(a)
""",
}


def _lines(fn, var, size, indent=""):
    text = "\n".join("    " + fn(var, i) for i in range(size))
    return "\n".join(indent + line for line in text.split("\n"))


def _program(route: str, elem: str, size: int) -> str:
    e = ELEMS[elem]
    return PRELUDE + ROUTES[route].format(
        ty=f"[{size}]{elem}",
        fill_a=_lines(e["fill"], "a", size),
        check_a=_lines(e["check"], "a", size),
        check_a_method=_lines(e["check"], "a", size, "    "),
        check_b=_lines(e["check"], "b", size),
        check_g=_lines(e["check"], "G", size),
    )


GRID = [(r, e, n) for r in ROUTES for e in ELEMS for n in SIZES]


def _grid_id(case):
    route, elem, size = case
    return f"{route}-{elem.replace('*', 'p')}-{size}"


@pytest.mark.integration
@pytest.mark.parametrize("case", GRID, ids=_grid_id)
def test_grid_ritz0(tmp_path, case):
    assert _run("ritz0", tmp_path, "g", _program(*case)) == 3


@pytest.mark.integration
@pytest.mark.parametrize("case", GRID, ids=_grid_id)
def test_grid_ritz1(ritz1_bin, tmp_path, case):
    assert _run("ritz1", tmp_path, "g", _program(*case)) == 3


# Every program here is one ritz0 compiles; ritz1 has to give the same exit code.
CASES = {
    "generic_box_elem": """\
struct Box<T>
    v: T
    w: i64

fn g<T>(a: [3]Box<T>) -> T
    return a[2].v

pub fn main() -> i32
    var a: [3]Box<i32>
    a[2].v = 3
    return g<i32>(a)
""",
    "generic_ref_pass": """\
fn g<T>(a: @[4]T) -> i32
    return 3

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return g<i32>(a)
""",
    "arg_mutate_callee": """\
fn g(a: [4]i32) -> i32
    a[3] = 9
    return a[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    let r: i32 = g(a)
    return r * 10 + a[3]
""",
    "arg_literal": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    return g([0, 0, 0, 3])
""",
    "arg_fill": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    return g([3; 4])
""",
    "arg_field": """\
struct H
    a: [4]i32

fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    var h: H
    h.a = [0, 0, 0, 3]
    return g(h.a)
""",
    "arg_deref": """\
fn g(a: [4]i32) -> i32
    return a[3]

fn f(p: *[4]i32) -> i32
    return g(*p)

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return f(@a)
""",
    "arg_global": """\
var G: [4]i32

fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    G[3] = 3
    return g(G)
""",
    "arg_forward": """\
fn g(a: [4]i32) -> i32
    return a[3]

fn f(a: [4]i32) -> i32
    return g(a)

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return f(a)
""",
    "arg_many": """\
fn g(x: i32, a: [4]i32, y: i32, b: [5]i64) -> i32
    return x + a[3] + y + (b[4] as i32)

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var b: [5]i64 = [0, 0, 0, 0, 4]
    return g(1, a, 2, b)
""",
    "arg_big": """\
fn g(a: [100]i32) -> i32
    return a[99]

pub fn main() -> i32
    var a: [100]i32
    a[99] = 3
    return g(a)
""",
    "extern_decl_order": """\
pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return g(a)

fn g(a: [4]i32) -> i32
    return a[3]
""",
    "array_of_ptr_arg": """\
fn g(a: [3]*i32) -> i32
    return *a[2]

pub fn main() -> i32
    var n: i32 = 3
    var a: [3]*i32
    a[2] = @n
    return g(a)
""",
    "generic_arg": """\
fn g<T>(a: [4]T) -> T
    return a[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return g<i32>(a)
""",
    "generic_struct_elem": """\
struct P
    x: i32
    y: i64

fn g<T>(a: [3]T) -> i32
    return 3

pub fn main() -> i32
    var a: [3]P
    return g<P>(a)
""",
    "static_method": """\
struct S
    n: i32

impl S
    fn get(a: [4]i32) -> i32
        return a[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return S.get(a)
""",
    "fnptr_arg": """\
fn g(a: [4]i32) -> i32
    return a[3]

fn call(f: fn([4]i32) -> i32, a: [4]i32) -> i32
    return f(a)

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return call(g, a)
""",
    "drop_arg": """\
var D: i32 = 0

struct S
    x: i32

impl Drop for S
    fn drop(self:& S)
        D = D + 1

fn g(a: [2]S) -> i32
    return a[1].x

pub fn main() -> i32
    var a: [2]S = [S { x: 1 }, S { x: 2 }]
    let r: i32 = g(a)
    return r * 10 + D
""",
    "sign_arg": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    var a: [4]u32 = [0, 0, 0, 3]
    return g(a)
""",
    "sign_local": """\
pub fn main() -> i32
    var a: [4]u32 = [0, 0, 0, 3]
    var b: [4]i32 = a
    return b[3]
""",
    "deref_lit": """\
fn s(p: *[4]i32)
    *p = [0, 0, 0, 3]

pub fn main() -> i32
    var b: [4]i32 = [0, 0, 0, 0]
    s(@b)
    return b[3]
""",
    "deref_fill": """\
fn s(p: *[4]i32)
    *p = [3; 4]

pub fn main() -> i32
    var b: [4]i32 = [0, 0, 0, 0]
    s(@b)
    return b[3]
""",
    "deref_from_deref": """\
fn s(p: *[4]i32, q: *[4]i32)
    *p = *q

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var b: [4]i32 = [0, 0, 0, 0]
    s(@b, @a)
    return b[3]
""",
    "deref_let_ptr": """\
pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var b: [4]i32 = [0, 0, 0, 0]
    let p: *[4]i32 = @b
    *p = a
    return b[3]
""",
    "deref_at_mut": """\
fn s(p: @&[4]i32)
    var a: [4]i32 = [0, 0, 0, 3]
    *p = a

pub fn main() -> i32
    var b: [4]i32 = [0, 0, 0, 0]
    s(@&b)
    return b[3]
""",
    "self_alias": """\
fn s(p: *[4]i32, q: *[4]i32)
    *p = *q

pub fn main() -> i32
    var a: [4]i32 = [0, 1, 2, 3]
    s(@a, @a)
    return a[3]
""",
    "global_lit": """\
var G: [4]i32

pub fn main() -> i32
    G = [0, 0, 0, 3]
    return G[3]
""",
    "global_fill": """\
var G: [4]i32

pub fn main() -> i32
    G = [3; 4]
    return G[3]
""",
    "global_from_global": """\
var G: [4]i32
var H: [4]i32

pub fn main() -> i32
    H[3] = 3
    G = H
    return G[3]
""",
    "global_to_local": """\
var G: [4]i32

pub fn main() -> i32
    G[3] = 3
    var a: [4]i32 = G
    return a[3]
""",
    "global_structs": """\
struct S
    x: i32
    y: i64

var G: [3]S

pub fn main() -> i32
    var a: [3]S
    a[2].y = 3
    G = a
    return G[2].y as i32
""",
    "let_untyped_global": """\
var G: [4]i32

pub fn main() -> i32
    G[3] = 3
    let b = G
    return b[3]
""",
    "field_from_param": """\
struct H
    a: [4]i32

fn f(a: [4]i32) -> i32
    var h: H
    h.a = a
    return h.a[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return f(a)
""",
    "borrow_global": """\
var G: [4]i32

fn g(a:& [4]i32) -> i32
    var b: [4]i32 = a
    return b[3]

pub fn main() -> i32
    G[3] = 3
    return g(G)
""",
    "borrow_field": """\
struct H
    a: [4]i32

fn g(a:& [4]i32) -> i32
    var b: [4]i32 = a
    return b[3]

pub fn main() -> i32
    var h: H
    h.a[3] = 3
    return g(h.a)
""",
    "borrow_param": """\
fn g(a:& [4]i32) -> i32
    var b: [4]i32 = a
    return b[3]

fn f(a: [4]i32) -> i32
    return g(a)

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return f(a)
""",
    "borrow_forward": """\
fn g(a:& [4]i32) -> i32
    var b: [4]i32 = a
    return b[3]

fn f(a:& [4]i32) -> i32
    return g(a)

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return f(@a)
""",
    "borrow_writes": """\
fn g(a:& [4]i32, p: *i32)
    var b: [4]i32 = a
    *p = b[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var r: i32 = 0
    g(a, @r)
    return r
""",
    "ref_at_reads": """\
fn g(a: @[4]i32) -> i32
    var b: [4]i32 = *a
    return b[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return g(a)
""",
    "ref_at_mut_reads": """\
fn g(a: @&[4]i32) -> i32
    var b: [4]i32 = *a
    return b[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return g(a)
""",
    "ref_at_structs": """\
struct S
    x: i32
    y: i64

fn g(a: @[3]S) -> i64
    var b: [3]S = *a
    return b[2].y

pub fn main() -> i32
    var a: [3]S
    a[2].y = 3
    return g(a) as i32
""",
    "method_ref": """\
struct R
    n: i32

impl R
    fn m(self: *R, a:& [4]i32) -> i32
        var b: [4]i32 = a
        return b[3]

pub fn main() -> i32
    var r: R = R { n: 0 }
    var a: [4]i32 = [0, 0, 0, 3]
    return r.m(a)
""",
    "arg_ptr_val": """\
fn g(a: [4]i32) -> i32
    return a[3]

fn f(p: *[4]i32) -> i32
    return g(p)

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return f(@a)
""",
    "arg_addr": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return g(@a)
""",
    "span_arg": """\
import ritzlib.span

fn g(s: Span<i32>) -> i64
    return s.len

pub fn main() -> i32
    var a: [3]i32 = [0, 0, 3]
    return g(a) as i32
""",
    "span_param": """\
import ritzlib.span

fn g(s: Span<i32>) -> i64
    return s.len

fn f(a: [3]i32) -> i64
    return g(a)

pub fn main() -> i32
    var a: [3]i32 = [0, 0, 3]
    return f(a) as i32
""",
    "shadow_global": """\
var G: [4]i32

fn g(G: i32) -> i32
    return G

pub fn main() -> i32
    return g(3)
""",
}

# Strict xfails: ritz0 lowers each of these and ritz1 refuses it, which is safe
# but isn't parity.  test_ritz1_gap_is_refused_not_wrong keeps it safe: a wrong
# value would satisfy the xfail just as a refusal does.
RETURN_GAPS = {
    "ret_fnptr": """\
fn f() -> [4]i32
    [0, 0, 0, 3]

fn call(h: fn() -> [4]i32) -> i32
    let b = h()
    return b[3]

pub fn main() -> i32
    return call(f)
""",
    "ret_static": """\
struct S
    n: i32

impl S
    fn f() -> [4]i32
        [0, 0, 0, 3]

pub fn main() -> i32
    let b = S.f()
    return b[3]
""",
    "ret_local": """\
fn f() -> [4]i32
    var a: [4]i32 = [0, 0, 0, 3]
    return a

pub fn main() -> i32
    var b: [4]i32 = f()
    return b[3]
""",
    "ret_param": """\
fn f(a: [4]i32) -> [4]i32
    return a

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var b: [4]i32 = f(a)
    return b[3]
""",
    "ret_literal": """\
fn f() -> [4]i32
    return [0, 0, 0, 3]

pub fn main() -> i32
    var b: [4]i32 = f()
    return b[3]
""",
    "ret_tail": """\
fn f() -> [4]i32
    var a: [4]i32 = [0, 0, 0, 3]
    a

pub fn main() -> i32
    var b: [4]i32 = f()
    return b[3]
""",
    "ret_to_assign": """\
fn f() -> [4]i32
    var a: [4]i32 = [0, 0, 0, 3]
    return a

pub fn main() -> i32
    var b: [4]i32
    b = f()
    return b[3]
""",
    "ret_as_arg": """\
fn f() -> [4]i32
    var a: [4]i32 = [0, 0, 0, 3]
    return a

fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    return g(f())
""",
    "ret_untyped": """\
fn f() -> [4]i32
    var a: [4]i32 = [0, 0, 0, 3]
    return a

pub fn main() -> i32
    let b = f()
    return b[3]
""",
    "ret_discard": """\
fn f() -> [4]i32
    var a: [4]i32 = [0, 0, 0, 3]
    return a

pub fn main() -> i32
    f()
    return 3
""",
    "ret_lit_untyped": """\
fn f() -> [4]i32
    [0, 0, 0, 3]

pub fn main() -> i32
    let b = f()
    return b[3]
""",
    "ret_lit_typed": """\
fn f() -> [4]i32
    [0, 0, 0, 3]

pub fn main() -> i32
    var b: [4]i32 = f()
    return b[3]
""",
    "ret_lit_discard": """\
fn f() -> [4]i32
    [0, 0, 0, 3]

pub fn main() -> i32
    f()
    return 3
""",
    "ret_lit_method": """\
struct S
    n: i32

impl S
    fn f(self: *S) -> [4]i32
        [0, 0, 0, 3]

pub fn main() -> i32
    var s: S = S { n: 0 }
    let b = s.f()
    return b[3]
""",
}

ELEM_GAPS = {
    "arg_wrong_elem": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    var a: [4]i64 = [0, 0, 0, 3]
    return g(a)
""",
    "wrong_elem_store": """\
fn s(p: *[4]i32)
    var a: [4]i64 = [0, 0, 0, 3]
    *p = a

pub fn main() -> i32
    var b: [4]i32 = [0, 0, 0, 0]
    s(@b)
    return b[3]
""",
    "wrong_elem_global": """\
var G: [4]i32

pub fn main() -> i32
    var a: [4]i64 = [0, 0, 0, 3]
    G = a
    return G[3]
""",
    "wrong_elem_local": """\
pub fn main() -> i32
    var a: [4]i64 = [0, 0, 0, 3]
    var b: [4]i32 = [0, 0, 0, 0]
    b = a
    return b[3]
""",
    "wrong_elem_float": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    var a: [4]f64 = [0.0, 0.0, 0.0, 3.0]
    return g(a)
""",
    "wrong_elem_widen": """\
fn g(a: [4]i64) -> i64
    return a[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return g(a) as i32
""",
}

DEREF_GAPS = {
    "deref_field_ptr": """\
struct W
    p: *[4]i32

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var b: [4]i32 = [0, 0, 0, 0]
    var w: W = W { p: @b }
    *w.p = a
    return b[3]
""",
    "deref_field_lit": """\
struct W
    p: *[4]i32

pub fn main() -> i32
    var b: [4]i32 = [0, 0, 0, 0]
    var w: W = W { p: @b }
    *w.p = [0, 0, 0, 3]
    return b[3]
""",
    "deref_global_ptr": """\
var P: *[4]i32

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var b: [4]i32 = [0, 0, 0, 0]
    P = @b
    *P = a
    return b[3]
""",
    "deref_ptr_arith": """\
fn s(p: *[4]i32)
    var a: [4]i32 = [0, 0, 0, 3]
    *(p + 1) = a

pub fn main() -> i32
    var b: [8]i32
    s(@b as *[4]i32)
    return b[7]
""",
}

SOURCE_GAPS = {
    "if_tail_array": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var b: [4]i32 = [0, 0, 0, 4]
    return g(if a[0] == 0 then a else b)
""",
    "strview_arg": """\
fn g(s: StrView) -> i32
    return 3

pub fn main() -> i32
    var a: [3]u8 = [0, 0, 3]
    return g(a)
""",
    "span_global": """\
import ritzlib.span

var G: [3]i32

fn g(s: Span<i32>) -> i64
    return s.len

pub fn main() -> i32
    return g(G) as i32
""",
    "span_field": """\
import ritzlib.span

struct H
    a: [3]i32

fn g(s: Span<i32>) -> i64
    return s.len

pub fn main() -> i32
    var h: H
    return g(h.a) as i32
""",
    "method_span": """\
import ritzlib.span

struct S
    n: i32

impl S
    fn len(self: *S, s: Span<i32>) -> i64
        return s.len

pub fn main() -> i32
    var r: S = S { n: 0 }
    var a: [3]i32 = [0, 0, 3]
    return r.len(a) as i32
""",
    "generic_whole": """\
fn g<T>(a: T) -> T
    return a

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var b: [4]i32 = g<[4]i32>(a)
    return b[3]
""",
    "generic_T_is_array": """\
fn g<T>(a: T) -> i32
    return 3

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return g<[4]i32>(a)
""",
    "generic_ref": """\
fn g<T>(a: @[4]T) -> i32
    var b: [4]T = *a
    return b[3] as i32

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return g<i32>(a)
""",
}

STRUCT_LITERAL_GAPS = {
    "struct_lit_local": """\
struct H
    a: [4]i32

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var h: H = H { a: a }
    return h.a[3]
""",
    "struct_lit_param": """\
struct H
    a: [4]i32

fn f(a: [4]i32) -> i32
    var h: H = H { a: a }
    return h.a[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return f(a)
""",
}

PARAM_ND_GAPS = {
    "arg_2d": """\
fn g(a: [2][3]i32) -> i32
    return a[1][2]

pub fn main() -> i32
    var a: [2][3]i32
    a[1][2] = 3
    return g(a)
""",
}

ROW_GAPS = {
    "aoa_row_arg": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    var m: [2][4]i32
    m[1][3] = 3
    return g(m[1])
""",
    "aoa_row_read": """\
pub fn main() -> i32
    var m: [2][4]i32
    m[1][3] = 3
    var r: [4]i32 = m[1]
    return r[3]
""",
    "aoa_row_store": """\
pub fn main() -> i32
    var m: [2][4]i32
    var r: [4]i32 = [0, 0, 0, 3]
    m[1] = r
    return m[1][3]
""",
    "aoa_whole": """\
pub fn main() -> i32
    var m: [2][4]i32
    m[1][3] = 3
    var n: [2][4]i32 = m
    return n[1][3]
""",
    "nd_global_store": """\
var G: [2][2]i32
var H: [2][2]i32

pub fn main() -> i32
    H[1][1] = 3
    G = H
    return G[1][1]
""",
}

GAPS = [
    (RETURN_GAPS, "AGAST #2302: a fn returning `[N]T` isn't lowered"),
    (ELEM_GAPS, "AGAST #2303: ritz0 converts `[N]T1` to `[N]T2`; ritz1 refuses"),
    (DEREF_GAPS, "AGAST #2304: `*p = a` needs a local or param `p: *[N]T`"),
    (SOURCE_GAPS, "AGAST #2305: a whole-array source or target ritz1 doesn't lower"),
    (STRUCT_LITERAL_GAPS, "AGAST #1748: a struct literal's array field takes only array literals"),
    (PARAM_ND_GAPS, "AGAST #2098: a multi-dimensional array param"),
    (ROW_GAPS, "AGAST #2099: a whole row of a multi-dimensional array"),
]

# Programs ritz0 refuses.  ritz1 has to refuse them too, and write no .ll: each
# of these used to read the array's first 8 bytes.
REJECTED = {
    "lent_to_ptr": """\
fn g(p: *[4]i32) -> i32
    var b: [4]i32 = *p
    return b[3]

fn f(a:& [4]i32) -> i32
    return g(a)

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return f(@a)
""",
    "lent_to_scalar_ptr": """\
fn g(p: *i32) -> i32
    return 3

fn f(a:& [4]i32) -> i32
    return g(a)

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return f(@a)
""",
    "wrong_elem_struct": """\
struct A
    x: i32
struct B
    x: i32

fn g(a: [2]A) -> i32
    return a[1].x

pub fn main() -> i32
    var a: [2]B
    a[1].x = 3
    return g(a)
""",
    "global_read_scalar": """\
var G: [4]i32

pub fn main() -> i32
    var x: i64 = G
    return x as i32
""",
    "global_read_arith": """\
var G: [4]i32

pub fn main() -> i32
    let x: i64 = G + 1
    return x as i32
""",
    "nd_global_fill": """\
var G: [2][2]i32

pub fn main() -> i32
    G = [0; 2]
    return 3
""",
    "arg_wrong_len": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    var a: [3]i32 = [0, 0, 3]
    return g(a)
""",
    "arg_ptr_i32": """\
fn g(a: *i32) -> i32
    return 3

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return g(a)
""",
    "arg_ptr_u8": """\
fn g(a: *u8) -> i32
    return 3

pub fn main() -> i32
    var a: [2]u8 = [1, 3]
    return g(a)
""",
    "arg_ptr_array": """\
fn g(a: *[2]i32) -> i32
    return 3

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return g(a)
""",
    "arg_scalar": """\
fn g(a: i64) -> i32
    return 3

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return g(a)
""",
    "struct_arg": """\
struct S
    x: i32

fn g(s: S) -> i32
    return 3

pub fn main() -> i32
    var a: [3]u8 = [0, 0, 3]
    return g(a)
""",
    "borrow_wrong_len": """\
fn g(a:& [4]i32) -> i32
    var b: [4]i32 = a
    return b[3]

pub fn main() -> i32
    var a: [3]i32 = [0, 0, 3]
    return g(a)
""",
    "borrow_literal": """\
fn g(a:& [4]i32) -> i32
    var b: [4]i32 = a
    return b[3]

pub fn main() -> i32
    return g([0, 0, 0, 3])
""",
    "deref_wrong_len": """\
fn s(p: *[4]i32)
    var a: [3]i32 = [0, 0, 3]
    *p = a

pub fn main() -> i32
    var b: [4]i32 = [0, 0, 0, 0]
    s(@b)
    return b[3]
""",
    "deref_scalar_ptr": """\
fn s(p: *i64)
    var a: [4]i32 = [0, 0, 0, 3]
    *p = a

pub fn main() -> i32
    var b: i64 = 0
    s(@b)
    return b as i32
""",
    "global_wrong_len": """\
var G: [4]i32

pub fn main() -> i32
    var a: [3]i32 = [0, 0, 3]
    G = a
    return G[2]
""",
    "scalar_from_array": """\
pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var x: i64 = a
    return x as i32
""",
    "scalar_field_from_array": """\
struct W
    x: i64

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var w: W = W { x: 0 }
    w.x = a
    return w.x as i32
""",
    "arith_on_array": """\
pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    let x: i64 = a + 1
    return x as i32
""",
    "global_scalar_from_array": """\
var G: i64

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    G = a
    return G as i32
""",
    "field_read_as_arg_ptr": """\
struct H
    a: [4]u8

fn g(p: *u8) -> i32
    return 3

pub fn main() -> i32
    var h: H
    return g(h.a)
""",
    "const_arg": """\
const C: [4]i32 = [0, 0, 0, 3]

fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    return g(C)
""",
    "const_scalar": """\
const C: [4]i32 = [0, 0, 0, 3]

pub fn main() -> i32
    var x: i64 = C
    return x as i32
""",
    "arg_ptr_wrong_len": """\
fn g(a: [4]i32) -> i32
    return a[3]

fn f(p: *[3]i32) -> i32
    return g(p)

pub fn main() -> i32
    var a: [3]i32 = [0, 0, 3]
    return f(@a)
""",
    "arg_addr_wrong_len": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    var a: [3]i32 = [0, 0, 3]
    return g(@a)
""",
    "ref_wrong_len": """\
fn g(a: @[4]i32) -> i32
    return 3

pub fn main() -> i32
    var a: [3]i32 = [0, 0, 3]
    return g(a)
""",
    "arg_null": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    return g(null) + 3
""",
    "arg_int": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    return g(0) + 3
""",
    "arg_i64_var": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    var x: i64 = 5
    return g(x) + 3
""",
    "arg_struct_val": """\
struct S
    x: i32

fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    var s: S = S { x: 1 }
    return g(s) + 3
""",
    "arg_call_scalar": """\
fn k() -> i32
    return 1

fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    return g(k()) + 3
""",
    "literal_into_ptr": """\
fn g(p: *i32) -> i32
    return 3

pub fn main() -> i32
    return g([1, 2])
""",
    "literal_wrong_len": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    return g([1, 2])
""",
    "self_copy": """\
fn s(p: *[4]i32)
    *p = [(*p)[3], (*p)[2], (*p)[1], (*p)[0]]

pub fn main() -> i32
    var b: [4]i32 = [3, 0, 0, 0]
    s(@b)
    return b[3]
""",
    "ret_index": """\
fn f() -> [4]i32
    var a: [4]i32 = [0, 0, 0, 3]
    return a

pub fn main() -> i32
    return f()[3]
""",
}


def _compile(compiler, ritz1_bin, tmp_path, name, program):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        comp = subprocess.run([str(ritz1_bin), str(src), "-o", str(ll)], cwd=tmp_path,
                              env=env, capture_output=True, text=True, timeout=300)
    return comp, ll


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_matches_ritz0(ritz1_bin, tmp_path, name):
    want = _run("ritz0", tmp_path, name, CASES[name])
    assert _run("ritz1", tmp_path, name, CASES[name]) == want


def _gap_params():
    return [pytest.param(program, id=name,
                         marks=pytest.mark.xfail(strict=True, reason=reason))
            for programs, reason in GAPS for name, program in sorted(programs.items())]


@pytest.mark.integration
@pytest.mark.parametrize("program", _gap_params())
def test_ritz1_gap(ritz1_bin, tmp_path, program):
    want = _run("ritz0", tmp_path, "gap", program)
    assert _run("ritz1", tmp_path, "gap", program) == want


def _refused_not_wrong():
    return [pytest.param(p, id=n) for programs, _ in GAPS for n, p in sorted(programs.items())]


# A gap is safe only while ritz1 refuses it.  Compiling is fine once it gives
# ritz0's answer, which is what turns test_ritz1_gap's xfail into a failure.
@pytest.mark.integration
@pytest.mark.parametrize("program", _refused_not_wrong())
def test_ritz1_gap_is_refused_not_wrong(ritz1_bin, tmp_path, program):
    comp, ll = _compile("ritz1", ritz1_bin, tmp_path, "gap", program)
    assert comp.returncode != 0 or not ll.exists() or _links_and_matches(tmp_path, program)


def _links_and_matches(tmp_path, program):
    """clang refusing the IR is also a refusal; a linked program has to agree."""
    try:
        got = _run("ritz1", tmp_path, "gap2", program)
    except AssertionError:
        return True
    return got == _run("ritz0", tmp_path, "gap0", program)


# ritz0 refuses this `R.m(a)` where it takes `r.m(a)`: its static calls don't take
# the address.  ritz1 does, and has to pass the real one.
STATIC_METHOD_BORROW = """\
struct R
    n: i32

impl R
    fn m(a:& [4]i32) -> i32
        var b: [4]i32 = a
        return b[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return R.m(a)
"""


@pytest.mark.integration
def test_ritz1_static_method_borrow(ritz1_bin, tmp_path):
    assert _run("ritz1", tmp_path, "s", STATIC_METHOD_BORROW) == 3


# ritz0's ABI, read from its IR: a by-value array is a first-class `[N x T]`.
ABI = """\
struct S
    x: i32
    y: i64

fn g(n: i32, a: [4]i32, b: [3]S, c: [2]*i32, d: [3]bool, e: [2]f32) -> i32
    return n

pub fn main() -> i32
    var a: [4]i32
    var b: [3]S
    var c: [2]*i32
    var d: [3]bool
    var e: [2]f32
    return g(3, a, b, c, d, e)
"""


def _signature(text):
    """The param types in `@g`'s definition, with the name mangling dropped."""
    line = next(l for l in text.splitlines() if l.startswith("define") and re.search(r'@"?g"?\(', l))
    params = line[line.index("(") + 1:line.index(")")]
    return [re.sub(r'%"?struct\.[a-z_0-9]*\.', "%", p.rsplit(" ", 1)[0]).replace('"', "").replace("*", "").strip()
            for p in params.split(", ")]


@pytest.mark.integration
def test_ritz1_abi_is_ritz0s(ritz1_bin, tmp_path):
    comp0, ll0 = _compile("ritz0", None, tmp_path, "abi", ABI)
    comp1, ll1 = _compile("ritz1", ritz1_bin, tmp_path, "abi", ABI)
    assert comp0.returncode == 0 and comp1.returncode == 0, comp0.stdout + comp1.stderr
    want = _signature(ll0.read_text())
    assert want[1:3] == ["[4 x i32]", "[3 x %S]"], want
    assert _signature(ll1.read_text())[1:3] == want[1:3]


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(REJECTED))
def test_ritz0_refuses(tmp_path, name):
    comp, _ = _compile("ritz0", None, tmp_path, name, REJECTED[name])
    assert comp.returncode != 0


# A later check would refuse most of these too, without saying where or why.
# The argument check names the call, as ritz0 does.
LOCATED = {
    "arg_wrong_len": "the array's length isn't the parameter's",
    "arg_ptr_i32": "the parameter doesn't take a whole array",
    "arg_ptr_array": "the parameter doesn't take a whole array",
    "arg_scalar": "the parameter doesn't take a whole array",
    "borrow_literal": "a `:&` parameter needs a place to borrow",
    "borrow_wrong_len": "the array isn't the one the parameter points at",
    "ref_wrong_len": "the array isn't the one the parameter points at",
    "lent_to_ptr": "the parameter doesn't take a whole array",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(LOCATED))
def test_ritz1_refusal_names_the_argument(ritz1_bin, tmp_path, name):
    comp, _ = _compile("ritz1", ritz1_bin, tmp_path, name, REJECTED[name])
    out = comp.stdout + comp.stderr
    assert re.search(r"\.ritz:\d+:\d+: argument 1 of `g` has the wrong type: ", out), out
    assert LOCATED[name] in out


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(REJECTED))
def test_ritz1_refuses(ritz1_bin, tmp_path, name):
    comp, ll = _compile("ritz1", ritz1_bin, tmp_path, name, REJECTED[name])
    assert comp.returncode != 0, comp.stdout + comp.stderr
    assert not ll.exists()
    assert "error" in comp.stdout + comp.stderr
