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

A non-literal `[N]T1` fits `[N]T2` only when T1 is T2 (LARB R5, AGAST #2343), so
the element-type programs are in REJECTED below; test_array_store_rule.py has the
rule at every store.

Sizes matter: a `[2]i32` fits the 8 bytes that were copied, so the grid below
runs each route at sizes that fit and at sizes that don't.  ritz0 is the oracle
for every program.

The matrices are table rows (AGAST #4141): `test_every_row[<compiler>-<chunk>]`
checks TABLE with test_table_rows' assert_rows, ~64 rows a chunk (_size), each row under
the id its parametrised test had less the compiler: `test_grid_ritz0[a-b-2]` and
`test_grid_ritz1[a-b-2]` are row `grid[a-b-2]` on each, `test_ritz0_refuses[x]`
and `test_ritz1_refuses[x]` are `refuses[x]`, `test_ritz1_matches_ritz0[x]` is
`matches_ritz0[x]` and `test_ritz1_refusal_names_the_argument[x]` is
`refusal_names_the_argument[x]`.  A failure names each row that failed.  A
matches_ritz0 row wants ritz0's answer (ANSWERS) on both compilers, so ritz1
still has to give ritz0's.
"""

import os
import re
import subprocess

import pytest

import batching
import test_ir
import test_table_rows as table_rows
from ritz0_inproc import run_ritz0
from test_ritz1_builtin_struct_shadow import RITZ_ROOT, _batch_build, _batch_compile, _run
from test_table_rows import Prefix, Refused, Row, Run

COMPILERS = ("ritz0", "ritz1")


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
    let p = @&b
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


# Each route, element and size exits 3 on both.
GRID_ROWS = [Row(f"grid[{_grid_id(case)}]", COMPILERS, Run(_program(*case), 3)) for case in GRID]


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
    return g<i32>(@a)
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
    return f(@&a)
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
    return g(@a)
""",
    "ref_at_mut_reads": """\
fn g(a: @&[4]i32) -> i32
    var b: [4]i32 = *a
    return b[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return g(@&a)
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
    return g(@a) as i32
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
    return g(*p)

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return f(@a)
""",
    "arg_addr": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return g(a)
""",
    "span_arg": """\
import ritzlib.span

fn g(s: Span<i32>) -> i64
    return s.len

pub fn main() -> i32
    var a: [3]i32 = [0, 0, 3]
    return g(@a) as i32
""",
    "span_param": """\
import ritzlib.span

fn g(s: Span<i32>) -> i64
    return s.len

fn f(a: [3]i32) -> i64
    return g(@a)

pub fn main() -> i32
    var a: [3]i32 = [0, 0, 3]
    return f(a) as i32
""",
    # A local can't take a global's name (AGAST #2407): test_local_takes_module_name.py.
    # AGAST #2517: a 1-D row of an N-D array is a whole-array source.
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
}

# AGAST #2302: a fn returning `[N]T` returns a first-class `[N x T]`, as in
# ritz0: from a local, a param, a literal or a tail; into a typed or untyped
# local, an assignment, a by-value argument or nowhere; through a direct, fn
# pointer, static or method call.  These were strict xfails until it did.
RETURNS = {
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

# AGAST #2302: one per rule the return ABI adds.  Element spellings: a named
# struct, `i1`, `ptr`.  Sources: a call (`return f()` as a tail).  Instances: a
# generic fn's `[4]T` at T = i32, and a generic `fn() -> [4]T` param's.  Calls: a method on `self`, a typed local fn
# pointer.  Targets: a global, a field, `*p`.
RETURNS.update({
    "ret_struct_elem": """\
struct P
    x: i32
    y: i64

fn f() -> [3]P
    var a: [3]P
    a[2].x = 3
    a[2].y = 4
    return a

pub fn main() -> i32
    let b = f()
    return b[2].x + b[2].y as i32
""",
    "ret_bool_elem": """\
fn f() -> [3]bool
    return [false, true, false]

pub fn main() -> i32
    let b = f()
    if b[1] and not b[2]
        return 3
    return 1
""",
    "ret_ptr_elem": """\
var N: i32 = 3

fn f() -> [2]*i32
    var a: [2]*i32
    a[1] = @N
    return a

pub fn main() -> i32
    let b = f()
    return *b[1]
""",
    "ret_call_tail": """\
fn f() -> [4]i32
    [0, 0, 0, 3]

fn g() -> [4]i32
    f()

pub fn main() -> i32
    let b = g()
    return b[3]
""",
    "ret_generic": """\
fn f<T>(v: T) -> [4]T
    var a: [4]T
    a[3] = v
    return a

pub fn main() -> i32
    let b = f<i32>(3)
    return b[3]
""",
    "ret_generic_fnptr": """\
fn f() -> [4]i32
    [0, 0, 0, 3]

fn app<T>(h: fn() -> [4]T) -> T
    let b = h()
    return b[3]

pub fn main() -> i32
    return app<i32>(f)
""",
    "ret_method_self": """\
struct S
    n: i32

impl S
    fn f(self: *S) -> [4]i32
        var a: [4]i32 = [0, 0, 0, 0]
        a[3] = self.n
        return a

pub fn main() -> i32
    var s: S = S { n: 3 }
    var b: [4]i32 = s.f()
    return b[3]
""",
    "ret_fnptr_typed": """\
fn f() -> [4]i32
    [0, 0, 0, 3]

fn call(h: fn() -> [4]i32) -> i32
    var b: [4]i32 = h()
    return b[3]

pub fn main() -> i32
    return call(f)
""",
    "ret_to_global": """\
var G: [4]i32

fn f() -> [4]i32
    return [0, 0, 0, 3]

pub fn main() -> i32
    G = f()
    return G[3]
""",
    "ret_to_field": """\
struct H
    a: [4]i32

fn f() -> [4]i32
    return [0, 0, 0, 3]

pub fn main() -> i32
    var h: H
    h.a = f()
    return h.a[3]
""",
    "ret_to_deref": """\
fn f() -> [4]i32
    return [0, 0, 0, 3]

fn s(p: *[4]i32)
    *p = f()

pub fn main() -> i32
    var b: [4]i32
    s(@b)
    return b[3]
""",
    # An element of the array a call returns is a value, read from a spill
    # (AGAST #3234); it was refused on both.
    "ret_index": """\
fn f() -> [4]i32
    var a: [4]i32 = [0, 0, 0, 3]
    return a

pub fn main() -> i32
    return f()[3]
""",
})

CASES.update(RETURNS)

# AGAST #2304: `*x = a` and `*x` read whole through any `*[N]T` that records N
# and T: a field, a global, and `x + k` / `x - k` at stride `[N]T` over one.
# These were strict xfails.
DEREF_THROUGH = {
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
    "deref_ptr_arith_nested": """\
fn s(p: *[4]i32)
    var a: [4]i32 = [0, 0, 0, 3]
    *((p + 2) - 1) = a

pub fn main() -> i32
    var b: [8]i32
    s(@b as *[4]i32)
    return b[7]
""",
    "deref_ptr_arith_read": """\
fn s(p: *[4]i32) -> i32
    let c: [4]i32 = *(p + 1)
    return c[3]

pub fn main() -> i32
    var b: [8]i32
    b[7] = 3
    return s(@b as *[4]i32)
""",
    "deref_field_read": """\
struct W
    p: *[4]i32

pub fn main() -> i32
    var b: [4]i32 = [0, 0, 0, 3]
    var w: W = W { p: @b }
    let c: [4]i32 = *w.p
    return c[3]
""",
    "deref_field_ptr_arith": """\
struct W
    p: *[4]i32

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var b: [8]i32
    var w: W = W { p: @b as *[4]i32 }
    *(w.p + 1) = a
    return b[7]
""",
    "deref_global_lit": """\
var P: *[4]i32

pub fn main() -> i32
    var b: [4]i32 = [0, 0, 0, 0]
    P = @b
    *P = [0, 0, 0, 3]
    return b[3]
""",
    "deref_global_read": """\
var P: *[4]i32

pub fn main() -> i32
    var b: [4]i32 = [0, 0, 0, 3]
    P = @b
    var c: [4]i32 = [0, 0, 0, 0]
    c = *P
    return c[3]
""",
    # `P + 1` stepped one byte on a global and refused on a field.
    "ptr_arith_field_global_value": """\
var P: *[4]i32

struct W
    p: *[4]i32

pub fn main() -> i32
    var b: [8]i32
    b[4] = 3
    b[5] = 4
    P = @b as *[4]i32
    var w: W = W { p: @b as *[4]i32 }
    let q: *i32 = (P + 1) as *i32
    let r: *i32 = (w.p + 1) as *i32
    return *q * 10 + *r
""",
}

CASES.update(DEREF_THROUGH)

# AGAST #3191: an untyped `let c = *x` of a `*[N]T` is the `[N]T` local
# `let c: [N]T = *x` declares, a copy.  `*P` on a global read the pointer's own
# bytes, SILENT, until #2304 refused all four; these were strict xfails.
UNTYPED_DEREF = {
    "untyped_deref_local": """\
fn s(p: *[4]i32) -> i32
    let c = *p
    return c[3]

pub fn main() -> i32
    var b: [4]i32 = [0, 0, 0, 3]
    return s(@b)
""",
    "untyped_deref_field": """\
struct W
    p: *[4]i32

pub fn main() -> i32
    var b: [4]i32 = [0, 0, 0, 3]
    var w: W = W { p: @b }
    let c = *w.p
    return c[3]
""",
    "untyped_deref_global": """\
var P: *[4]i32

pub fn main() -> i32
    var b: [4]i32 = [0, 0, 0, 3]
    P = @b
    let c = *P
    return c[3]
""",
    "untyped_deref_arith": """\
fn s(p: *[4]i32) -> i32
    let c = *(p + 1)
    return c[3]

pub fn main() -> i32
    var b: [8]i32
    b[7] = 3
    return s(@b as *[4]i32)
""",
    # A copy: a store through `p` after the let doesn't reach `c`, nor `c`'s
    # store `b`.
    "untyped_deref_is_copy": """\
pub fn main() -> i32
    var b: [4]i32 = [0, 0, 0, 3]
    let p: *[4]i32 = @b
    var c = *p
    b[3] = 9
    c[0] = 7
    return c[3] + b[0]
""",
    # T is the pointer's: `[4]u8`, so `c[3]` reads one byte.
    "untyped_deref_u8": """\
fn s(p: *[4]u8) -> i32
    let c = *p
    return c[3] as i32

pub fn main() -> i32
    var b: [4]u8 = [1, 1, 1, 3]
    return s(@b)
""",
}

CASES.update(UNTYPED_DEREF)

# AGAST #2305: whole-array sources and targets ritz1 refused or failed closed on
# (they were SOURCE_GAPS).  ritz0 is the oracle for each.  The Span programs
# take `@`: a bare array into a `Span<T>` is ritz0's "write `@x` to borrow it",
# so the bare forms the ticket listed were xfailing on ritz0's refusal.
SOURCES = {
    # An `if` value of array type: each arm stores its own array (no phi).
    "if_call_arms_tail": """\
fn f() -> [4]i32
    [0, 0, 0, 3]

fn g() -> [4]i32
    [0, 0, 0, 4]

fn h(c: i32) -> [4]i32
    if c == 0
        f()
    else
        g()

pub fn main() -> i32
    let r = h(0)
    return r[3]
""",
    "if_call_arms_let": """\
fn f() -> [4]i32
    [0, 0, 0, 3]

fn g() -> [4]i32
    [0, 0, 0, 4]

pub fn main() -> i32
    let r = if 1 == 1 then f() else g()
    return r[3]
""",
    "if_tail_array": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var b: [4]i32 = [0, 0, 0, 4]
    return g(if a[0] == 0 then a else b)
""",
    "if_untyped_locals": """\
pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var b: [4]i32 = [0, 0, 0, 4]
    let r = if a[0] == 0 then a else b
    return r[3]
""",
    # Every target: a typed let, a global, `*p`, an assignment with a block arm.
    "if_targets": """\
fn f() -> [4]i32
    [0, 0, 0, 3]

fn g() -> [4]i32
    [0, 0, 0, 4]

var G: [4]i32

fn put(p: *[4]i32, c: i32)
    *p = if c == 0 then f() else g()

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 1]
    let r: [4]i32 = if 1 == 1 then f() else g()
    var q: [4]i32 = if 1 == 2 then a else g()
    G = if 1 == 1 then a else q
    var w: [4]i32
    put(@w, 1)
    var z: [4]i32
    z = if 1 == 2
        a
    else
        let t: [4]i32 = [0, 0, 0, 5]
        t
    return r[3] * 1000 + q[3] * 100 + G[3] * 10 + w[3] + z[3] - 4 - 5
""",
    # A method's tail, an `else if` chain, and an arm that returns early.
    "if_method_tail_chain": """\
struct S
    n: i32

impl S
    fn pick(self: *S, c: i32) -> [3]i64
        var a: [3]i64 = [0, 0, 1]
        var b: [3]i64 = [0, 0, 2]
        if c == 0
            a
        else if c == 1
            b
        else
            if self.n == 9
                return [0, 0, 9]
            [0, 0, 4]

pub fn main() -> i32
    var s: S = S { n: 9 }
    let x = s.pick(0)
    let y = s.pick(1)
    let z = s.pick(2)
    s.n = 0
    let w = s.pick(2)
    return (x[2] + y[2] * 10 + z[2] * 100 + w[2] * 1000) as i32
""",
    # `[N]u8` / `[N]i8` into a StrView, bare or `@`: `{ &a[0], N }`.
    "strview_arg": """\
fn g(s: StrView) -> i32
    return 3

pub fn main() -> i32
    var a: [3]u8 = [0, 0, 3]
    return g(a)
""",
    "strview_reads": """\
struct H
    a: [3]u8

var G: [3]u8

fn g(s: StrView) -> i32
    return (s.len as i32) * 10 + (s.ptr[2] as i32)

pub fn main() -> i32
    var a: [3]u8 = [0, 0, 4]
    var b: [3]i8 = [0, 0, 2]
    var h: H
    h.a[2] = 4
    G[2] = 1
    return g(a) + g(@a) + g(b) + g(h.a) + g(G) + g(@G) - 160
""",
    # A Span from a global, a field, and on a method's param.
    "span_global": """\
import ritzlib.span

var G: [3]i32

fn g(s: Span<i32>) -> i64
    return s.len

pub fn main() -> i32
    return g(@G) as i32
""",
    "span_field": """\
import ritzlib.span

struct H
    a: [3]i32

fn g(s: Span<i32>) -> i64
    return s.len + (s.ptr[2] as i64)

pub fn main() -> i32
    var h: H
    h.a[2] = 4
    return g(@h.a) as i32
""",
    "span_let_global_field": """\
import ritzlib.span

struct H
    a: [3]i32

var G: [3]i32

pub fn main() -> i32
    var h: H
    h.a[2] = 4
    let s: Span<i32> = @G
    var t: Span<i32> = @h.a
    return (s.len + t.len * 10 + (t.ptr[2] as i64) * 100) as i32
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
    return r.len(@a) as i32
""",
    # Generic `T = [N]U`: a param, a return, a local, and a struct element.
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
    "generic_local_and_struct": """\
struct C
    x: i32
    y: i64

fn g<T>(a: T) -> T
    var x: T = a
    return x

fn h<T>(a: T) -> T
    a

pub fn main() -> i32
    var a: [3]u8 = [0, 0, 3]
    var b: [3]u8 = g<[3]u8>(a)
    var c: [2]C
    c[1].y = 4
    var d: [2]C = h<[2]C>(c)
    var e: [5]i64 = [0, 0, 0, 0, 7]
    let f = g<[5]i64>(e)
    return (b[2] as i32) + (d[1].y as i32) * 10 + (f[4] as i32) * 100 - 700
""",
    # `fn g<T>(a: @[4]T)` with `var b: [4]T = *a`, given `@a`.
    "generic_ref": """\
fn g<T>(a: @[4]T) -> i32
    var b: [4]T = *a
    return b[3] as i32

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return g<i32>(@a)
""",
    # `*@a` is the array `a`: a local, a `:&` param, a global.
    "deref_addr": """\
var G: [2]i32

fn f(a:& [2]i32) -> i32
    let b: [2]i32 = *@a
    return b[1]

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    var c: [2]i32 = *@a
    G = *@&a
    return f(@&a) + c[1] + G[1] - 6
""",
}

CASES.update(SOURCES)

# AGAST #3277: `T = [N]U` inferred from the argument, as `g<[4]i32>(a)` above
# spells it: from an array local, a by-value array param, and a generic call's
# `-> T` result; with a primitive, a struct and a pointer element.
GENERIC_INFER = {
    "generic_infer_array": """\
fn g<T>(a: T) -> i32
    return 3

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return g(a)
""",
    "generic_infer_array_param": """\
fn g<T>(a: T) -> T
    var x: T = a
    return x

fn h(a: [4]i32) -> i32
    var b: [4]i32 = g(a)
    return b[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return h(a)
""",
    "generic_infer_array_struct": """\
struct C
    x: i32
    y: i64

fn g<T>(a: T) -> T
    a

pub fn main() -> i32
    var c: [2]C
    c[1].y = 3
    var d: [2]C = g(c)
    return d[1].y as i32
""",
    "generic_infer_array_ptr": """\
fn g<T>(a: T) -> T
    a

pub fn main() -> i32
    var x: i32 = 3
    var p: [2]*i32
    p[1] = @x
    var q: [2]*i32 = g(p)
    return *q[1]
""",
    "generic_infer_array_result": """\
fn g<T>(a: T) -> T
    a

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    let b = g(a)
    var c: [4]i32 = g(b)
    return c[3]
""",
}

CASES.update(GENERIC_INFER)

# AGAST #3276: a `match` value of array type, as #2305 lowered `if`: each arm
# stores its own array into the destination, dispatched by emit_match's own
# pattern tests (no `[N x T]` phi).  A fn tail, a method tail, `return match`,
# every store target, an untyped `let`, an enum payload arm, a block arm, a
# nested `match`, an `if` inside an arm, and an arm that returns early.
MATCHES = {
    "match_call_arms_tail": """\
fn f() -> [4]i32
    [0, 0, 0, 3]

fn g() -> [4]i32
    [0, 0, 0, 4]

fn h(c: i32) -> [4]i32
    match c
        0 => f()
        _ => g()

pub fn main() -> i32
    let r = h(0)
    let s = h(1)
    return r[3] * 10 + s[3] - 31
""",
    "match_targets": """\
fn f() -> [4]i32
    [0, 0, 0, 3]

fn g() -> [4]i32
    [0, 0, 0, 4]

var G: [4]i32

fn put(p: *[4]i32, c: i32)
    *p = match c
        0 => f()
        _ => g()

fn ret(c: i32) -> [4]i32
    return match c
        1 => [0, 0, 0, 6]
        _ => f()

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 1]
    let c: i32 = 2
    let r: [4]i32 = match c
        2 => f()
        _ => g()
    var q: [4]i32 = match c
        0 => a
        _ => g()
    let u = match c
        2 => a
        _ => q
    G = match c
        2 => q
        _ => a
    var w: [4]i32
    put(@w, 1)
    var z: [4]i32
    z = match c
        0 => a
        _ =>
            let t: [4]i32 = [0, 0, 0, 5]
            t
    let v = ret(1)
    return r[3] * 100000 + q[3] * 10000 + u[3] * 1000 + G[3] * 100 + w[3] * 10 + z[3] + v[3] - 341448
""",
    "match_enum_arms": """\
enum Shape
    Dot
    Bar(i32)

fn pick(o: Option<i32>, b: [3]i64) -> [3]i64
    match o
        Some(n) =>
            if n == 9
                return [0, 0, 9]
            [0, 0, n as i64]
        None => b

fn shape(s: Shape) -> [2]i32
    match s
        Dot => [0, 1]
        Bar(k) => match k
            0 => [0, 2]
            _ => [0, k]

struct S
    n: i32

impl S
    fn row(self: *S, c: i32) -> [2]i32
        match c
            0 => [0, self.n]
            _ =>
                if c == 1
                    [0, 7]
                else
                    [0, 8]

pub fn main() -> i32
    var b: [3]i64 = [0, 0, 4]
    let x = pick(Some(2), b)
    let y = pick(Some(9), b)
    let z = pick(None, b)
    let p = shape(Dot)
    let q = shape(Bar(0))
    let r = shape(Bar(5))
    var s: S = S { n: 6 }
    let m0 = s.row(0)
    let m1 = s.row(1)
    let m2 = s.row(2)
    let lhs: i64 = x[2] + y[2] * 10 + z[2] * 100
    let rhs: i32 = p[1] + q[1] * 10 + r[1] * 100 + m0[1] * 1000 + m1[1] * 10000 + m2[1] * 100000
    return ((lhs - 492) as i32) + rhs - 876521 + 3
""",
    # An untyped `let` whose every arm is a nested `match` (its shape is read
    # through them), and a statement-`if` tail whose block ends in a `match`.
    "match_nested_shapes": """\
fn f() -> [2]i32
    [0, 1]

fn h(c: i32, d: i32) -> [2]i32
    if c == 0
        [0, 2]
    else
        let e: i32 = d + 1
        match e
            1 => f()
            _ => [0, e]

pub fn main() -> i32
    var a: [2]i32 = [0, 4]
    var b: [2]i32 = [0, 5]
    let c: i32 = 1
    let k = match c
        0 => match c
            0 => a
            _ => b
        _ => match c
            1 => b
            _ => a
    let x = h(0, 0)
    let y = h(1, 0)
    let z = h(1, 6)
    return k[1] * 1000 + x[1] * 100 + y[1] * 10 + z[1] - 5210 - 7 + 3
""",
}

CASES.update(MATCHES)

# AGAST #1748: a struct literal's array field from a local or a by-value
# array param (was a strict-xfail gap).
STRUCT_LITERALS = {
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

assert not set(STRUCT_LITERALS) & set(CASES)
CASES.update(STRUCT_LITERALS)

# AGAST #3634: a by-value N-D param and a whole N-D global assignment (were
# strict-xfail gaps under #2098 and #2099).
ND_WHOLE = {
    "arg_2d": """\
fn g(a: [2][3]i32) -> i32
    return a[1][2]

pub fn main() -> i32
    var a: [2][3]i32
    a[1][2] = 3
    return g(a)
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

assert not set(ND_WHOLE) & set(CASES)
CASES.update(ND_WHOLE)

# `aoa_row_store`, a whole row of an N-D array (`m[1] = r`), was the last strict
# xfail here; ritz1 lowers it since AGAST #4666 (test_ritz1_parity_emit_gaps.py),
# so the gap tests that guarded it went with it.

# Programs ritz0 refuses.  ritz1 has to refuse them too, and write no .ll: most of
# these used to read the array's first 8 bytes, and the `wrong_elem` ones went
# through ritz0's element conversion (#2343).  `self_copy`, `*p = [(*p)[3], ...]`, was
# here: ritz0 refuses it only by failing on `(*p)[i]` (#2331), which LARB R9 makes
# legal, so it's in test_ritz1_array_pointer_index.py now (#2330).
REJECTED = {
    # AGAST #3277: two arrays of different lengths bind T two ways.
    "generic_infer_array_conflict": """\
fn g<T>(a: T, b: T) -> i32
    return 3

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    var b: [3]i32 = [0, 0, 3]
    return g(a, b)
""",
    # AGAST #2305: a StrView takes only an `[N]u8` / `[N]i8`, bare or `@`.
    "strview_wrong_elem": """\
fn g(s: StrView) -> i32
    return 3

pub fn main() -> i32
    var a: [3]i32 = [0, 0, 3]
    return g(a)
""",
    "strview_addr_wrong_elem": """\
fn g(s: StrView) -> i32
    return 3

pub fn main() -> i32
    var a: [3]i32 = [0, 0, 3]
    return g(@a)
""",
    # AGAST #2305: `T = [4]i32` is held to its length; `*@a` to `a`'s; a Span
    # of a global to its element.
    "generic_wrong_len": """\
fn g<T>(a: T) -> i32
    return 3

pub fn main() -> i32
    var a: [3]i32 = [0, 0, 3]
    return g<[4]i32>(a)
""",
    "deref_addr_wrong_len": """\
pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    let b: [3]i32 = *@a
    return b[1]
""",
    # An `if` arm is judged as the store it is: `*i64` isn't `*i32`.
    "if_arm_wrong_elem": """\
fn f(a: [4]*i64, c: [4]*i32, n: i32) -> i32
    let r: [4]*i32 = if n > 0 then a else c
    return 0

pub fn main() -> i32
    0
""",
    "span_global_wrong_elem": """\
import ritzlib.span

var G: [3]i64

fn g(s: Span<i32>) -> i64
    return s.len

pub fn main() -> i32
    return g(@G) as i32
""",
    # AGAST #3276: a `pass` arm of a `match` stored into a whole array.
    "match_pass_arm": """\
pub fn main() -> i32
    let c: i32 = 0
    var q: [2]i32 = match c
        0 => [0, 3]
        _ => pass
    return q[1]
""",
    # AGAST #2302: a call's `[N]T` is held to the rule a local's is.
    "ret_wrong_len": """\
fn f() -> [4]i32
    return [0, 0, 0, 3]

pub fn main() -> i32
    var b: [5]i32 = f()
    return b[3]
""",
    "ret_wrong_elem": """\
fn f() -> [4]i32
    return [0, 0, 0, 3]

pub fn main() -> i32
    var b: [4]i64 = f()
    return b[3] as i32
""",
    "ret_local_wrong_elem": """\
fn f() -> [4]i32
    var a: [4]i64
    return a

pub fn main() -> i32
    return 0
""",
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
    # AGAST #2304: through a field, a global or `p + k`, N and T are the pointer's.
    "deref_field_wrong_len": """\
struct W
    p: *[4]i32

pub fn main() -> i32
    var a: [3]i32 = [0, 0, 3]
    var b: [4]i32 = [0, 0, 0, 0]
    var w: W = W { p: @b }
    *w.p = a
    return b[3]
""",
    "deref_global_wrong_elem": """\
var P: *[4]i32

pub fn main() -> i32
    var a: [4]i64 = [0, 0, 0, 3]
    var b: [4]i32 = [0, 0, 0, 0]
    P = @b
    *P = a
    return b[3]
""",
    "deref_arith_wrong_len": """\
fn s(p: *[4]i32)
    var a: [5]i32 = [0, 0, 0, 0, 3]
    *(p + 1) = a

pub fn main() -> i32
    var b: [8]i32
    s(@b as *[4]i32)
    return b[7]
""",
    "deref_field_read_wrong_len": """\
struct W
    p: *[4]i32

pub fn main() -> i32
    var b: [4]i32 = [0, 0, 0, 3]
    var w: W = W { p: @b }
    let c: [5]i32 = *w.p
    return c[3]
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
    "lent_to_ptr": """\
fn g(p: *[4]i32) -> i32
    var b: [4]i32 = *p
    return b[3]

fn f(a:& [4]i32) -> i32
    return g(a)

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return f(@&a)
""",
    "lent_to_scalar_ptr": """\
fn g(p: *i32) -> i32
    return 3

fn f(a:& [4]i32) -> i32
    return g(a)

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return f(@&a)
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


# ritz0's exit code for each of CASES, the oracle: 3 unless it's here.  A row
# wants it on both compilers, so ritz1 has to give ritz0's answer.
ANSWERS = {
    "arg_many": 10, "arg_mutate_callee": 93, "drop_arg": 22, "generic_local_and_struct": 43,
    "if_method_tail_chain": 57, "if_targets": 82, "ptr_arith_field_global_value": 33,
    "ret_struct_elem": 7, "span_field": 7, "span_let_global_field": 177, "strview_reads": 36,
}
assert set(ANSWERS) <= set(CASES)

MATCH_ROWS = [Row(f"matches_ritz0[{name}]", COMPILERS, Run(CASES[name], ANSWERS.get(name, 3)))
              for name in sorted(CASES)]


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
    line = next(l for l in text.splitlines()
                if l.startswith("define") and re.search(test_ir.symbol("g") + r"\(", l))
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


# AGAST #3276: test_ritz1_refuses_array_tail_value pinned ritz1's refusal of
# a `match` of `-> [N]T` calls as a fn's tail.  It's lowered now, and
# MATCHES["match_call_arms_tail"] compares it with ritz0 above.


# AGAST #2305: an `if` arm of another length than the array it's stored in.
# ritz0 writes a `phi [4 x i32]` of a `[3 x i32]`, which only clang refuses.
# AGAST #3276: a `match` arm is held to the destination the same way.
IF_WRONG_LEN = {
    "match_let": """\
pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 1]
    var b: [3]i32
    let c: i32 = 1
    var q: [4]i32 = match c
        0 => a
        _ => b
    return q[3]
""",
    "match_tail": """\
fn h(c: i32) -> [4]i32
    var b: [3]i32
    match c
        0 => [0, 0, 0, 3]
        _ => b

pub fn main() -> i32
    let r = h(0)
    return r[3]
""",
    "let": """\
pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 1]
    var b: [3]i32
    var q: [4]i32 = if 1 == 2 then a else b
    return q[3]
""",
    "tail": """\
fn f() -> [4]i32
    [0, 0, 0, 3]

fn h(c: i32) -> [4]i32
    var b: [3]i32
    if c == 0
        f()
    else
        b

pub fn main() -> i32
    let r = h(0)
    return r[3]
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(IF_WRONG_LEN))
def test_ritz1_refuses_if_arm_of_another_length(ritz1_bin, tmp_path, name):
    comp, ll = _compile("ritz1", ritz1_bin, tmp_path, name, IF_WRONG_LEN[name])
    assert comp.returncode != 0 and not ll.exists()
    assert "array length does not match the local array's length" in comp.stdout + comp.stderr


# AGAST #2302: ritz0's array return, read from its IR: `[4 x i32]` at the
# definition, the method, the extern declare and every call.
RET_ABI = """\
struct S
    n: i32

impl S
    fn m(self: *S) -> [4]i32
        [0, 0, 0, self.n]

extern fn ext() -> [4]i32

fn f() -> [4]i32
    [0, 0, 0, 3]

fn use_ext() -> i32
    let c = ext()
    return c[3]

pub fn main() -> i32
    var s: S = S { n: 3 }
    let a = f()
    let b = s.m()
    return a[3] + b[3]
"""


def _ret_spellings(text):
    """{(kind, fn): return type} for the define / declare / call of f, S_m, ext."""
    out = {}
    for line in text.splitlines():
        m = re.match(r'\s*(?:%"?[.\w]+"? = )?(define|declare|call)\b(.*?)@"?'
                     r'(f|S_m|ext)(?:__[0-9a-f]{8})?"?\(', line)
        if m:
            words = [w for w in m.group(2).split() if w not in ("internal", "external", "weak_odr")]
            out[(m.group(1), m.group(3))] = " ".join(words)
    return out


@pytest.mark.integration
def test_ritz1_return_abi_is_ritz0s(ritz1_bin, tmp_path):
    comp0, ll0 = _compile("ritz0", None, tmp_path, "rabi", RET_ABI)
    comp1, ll1 = _compile("ritz1", ritz1_bin, tmp_path, "rabi", RET_ABI)
    assert comp0.returncode == 0 and comp1.returncode == 0, comp0.stdout + comp1.stderr
    want = _ret_spellings(ll0.read_text())
    assert want == {(k, fn): "[4 x i32]" for k, fn in [
        ("define", "f"), ("define", "S_m"), ("declare", "ext"),
        ("call", "f"), ("call", "S_m"), ("call", "ext")]}, want
    assert _ret_spellings(ll1.read_text()) == want


# ritz0 refuses each of REJECTED; ritz1 too, saying "error" and writing no .ll
# (_compile_no_ll).
REFUSAL_ROWS = [Row(f"refuses[{name}]", (compiler,), Refused(REJECTED[name], want, located=False))
                for name in sorted(REJECTED) for compiler, want in (("ritz0", None), ("ritz1", "error"))]


# A later check would refuse most of these too, without saying where or why.
# The argument check names the call, as ritz0 does.
LOCATED = {
    "strview_wrong_elem": "the parameter doesn't take a whole array",
    "strview_addr_wrong_elem": "the parameter doesn't take a whole array",
    "generic_wrong_len": "the array's length isn't the parameter's",
    "arg_wrong_len": "the array's length isn't the parameter's",
    "arg_ptr_i32": "the parameter doesn't take a whole array",
    "arg_ptr_array": "the parameter doesn't take a whole array",
    "arg_scalar": "the parameter doesn't take a whole array",
    "borrow_literal": "a `:&` parameter needs a place to borrow",
    "borrow_wrong_len": "the array isn't the one the parameter points at",
    "ref_wrong_len": "the array isn't the one the parameter points at",
    "lent_to_ptr": "the parameter doesn't take a whole array",
}


# The slot checks refuse these arguments too, in ref_rules' and array_rules'
# words, beside the call check's "argument 1 of `g` has the wrong type": both on
# Sema (AGAST #4011, #4173).
LOCATED_ON_SEMA = {
    "arg_ptr_array": "a value doesn't fit a reference slot: write `@x` to borrow it",
    "arg_ptr_i32": "a whole array is not a pointer: `@a[0]` points at its first element",
    "lent_to_ptr": "a value doesn't fit a reference slot: write `@x` to borrow it",
    "ref_wrong_len": "a value doesn't fit a reference slot: write `@x` to borrow it",
}


# ritz1 only: a located diagnostic that starts with the argument and says why,
# printed as an `error:` (AGAST #3621; _compile_no_ll hides one that isn't),
# and LOCATED_ON_SEMA's, where the slot checks refuse the argument too.
def _argument_message(name):
    said = f"argument 1 of `g` has the wrong type: {LOCATED[name]}"
    if name not in LOCATED_ON_SEMA:
        return Prefix(said)
    return (f"error: {LOCATED_ON_SEMA[name]}", f"error: {said}")


ARGUMENT_ROWS = [Row(f"refusal_names_the_argument[{name}]", ("ritz1",),
                     Refused(REJECTED[name], _argument_message(name)))
                 for name in sorted(LOCATED)]


def _compile_no_ll(compiler, src, work):
    """_batch_compile, but a ritz1 refusal that still wrote its .ll loses its
    "error"s and `main.ritz:` locations, so no refusal row is answered by it;
    nor is an ARGUMENT_ROWS row by a ritz1 argument diagnostic with no
    `error: ` label (the table's diagnostic match takes the label as optional)."""
    code, out = _batch_compile(compiler, src, work)
    if compiler == "ritz1":
        out = re.sub(r"(main\.ritz:\d+:\d+: )(argument 1 of `g`)", r"\1[no error: label] \2", out)
    if compiler != "ritz0" and code != 0 and (work / "main.ll").exists():
        return code, "[wrote main.ll as it refused: nothing counts]\n" + re.sub(
            "error", "e-rror", out).replace("main.ritz:", "main.ritz?")
    return code, out


TABLE = GRID_ROWS + MATCH_ROWS + REFUSAL_ROWS + ARGUMENT_ROWS
for _c in COMPILERS:  # one row per id on each compiler
    _ids = [r.id for r in table_rows.for_compiler(TABLE, _c)]
    assert len(_ids) == len(set(_ids)), _c


def _one_import_set_a_chunk(compiler, size):
    return all(len({frozenset(batching._imports(r.spec.program)) for r in table_rows.chunk(TABLE, compiler, i, size)}) == 1
               for c, i in table_rows.chunks(TABLE, (compiler,), size))


def _size(compiler):
    """The least chunk size from CHUNK at which the `import ritzlib.span` rows
    get a chunk of their own without costing one (AGAST #3906).  A chunk mixing
    them with the rest compiles each of the rest alone too: ritz0's 57 were 11 s."""
    return next((size for size in range(table_rows.CHUNK, 2 * table_rows.CHUNK)
                 if _one_import_set_a_chunk(compiler, size)), table_rows.CHUNK)


SIZE = {c: _size(c) for c in COMPILERS}
CHUNKS = [chunk for c in COMPILERS for chunk in table_rows.chunks(TABLE, (c,), SIZE[c])]


@pytest.mark.integration
@pytest.mark.parametrize("compiler,chunk", CHUNKS, ids=[f"{c}-{i}" for c, i in CHUNKS])
def test_every_row(ritz1_bin, tmp_path, compiler, chunk):
    table_rows.assert_rows(compiler, table_rows.chunk(TABLE, compiler, chunk, SIZE[compiler]),
                           build=_batch_build, compile=_compile_no_ll, work=tmp_path)


@pytest.mark.integration
def test_ritz1_array_conflict_cant_infer(ritz1_bin, tmp_path):
    """AGAST #3277: `[4]i32` and `[3]i32` for one T is ritz0's located refusal."""
    name = "generic_infer_array_conflict"
    comp, _ = _compile("ritz1", ritz1_bin, tmp_path, name, REJECTED[name])
    assert re.search(r"\.ritz:7:12: error: can't infer `T` for `g`: write `g<T>\(\.\.\.\)`",
                     comp.stdout + comp.stderr), comp.stdout + comp.stderr
