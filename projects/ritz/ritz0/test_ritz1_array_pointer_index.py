"""AGAST #2321, #2330: `p[i]` on a pointer to an array, `p` a `*[N]T`, `@[N]T` or `@&[N]T`.

    fn f(p: *[3]i32) -> i32
        return p[1]         # ritz0 20, ritz1 0 (#2321)

LARB R9 (projects/larb/review/4/rulings-2026-11.md): `p[i]` is element i of the
array behind `p`, at stride T, in every position:

    read, `p[i] = v`, `p[i] += v`, `@p[i]`, `@&p[i]`, `p[i].f = v`, `@p[i].f`,
    `let s: S = p[i]` (a copy)

Writes through `@[N]T` are §3.2's located error.  `p[i] = <whole [N]T>` is a type
error, since the element is a T.  `p[lo..hi]` stays refused.  `p + i` strides the
pointee, `[N]T`, and is how to walk rows, so `p[i]` isn't `*(p + i)` here.

#2321 made the read right on ritz1 and refused the rest, because ritz0 stored and
took addresses at stride `[N]T`, against its own read: `@p[1]` pointed a row on and
`p[1] = b` overwrote the next row.  #2330 made ritz0 agree with itself and lowers
every position on ritz1 (index_through.ritz's `*(p# + i)`).

A byte-wide element hides all of this, and `[2]i32` is 8 bytes, which hides a
wrong-size access, so the grids cover several sizes and element types, and pass
row 0 of a `[2][N]T` so a stride of `[N]T` lands on row 1.

Every case is a row of one table (test_table_rows.py, AGAST #3517), checked a
chunk of rows at a time per compiler; a row keeps the id its parametrised test
had, less the compiler, and a failure names each row that failed with what it
wanted and what it got.
"""

from pathlib import Path

import pytest

import array_rules
import ref_rules
import test_table_rows as table_rows
from test_borrow_param_ref_field import _compile, _run
from test_ref_into_value import _batch_build, _batch_compile
from test_table_rows import Refused, Row, Run

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent
SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# The pointer's spelling, and the `@` that makes one.
KINDS = {"pointer": ("*", "@"), "reference": ("@", "@"), "mut_reference": ("@&", "@&")}
# The kinds a write goes through.  `@[N]T` refuses it (§3.2).
WRITABLE = ("pointer", "mut_reference")

# A fill value, then two others.  bool has only two, so `first` differs from the
# fill and `second` doesn't.
SCALARS = {
    "i8": ("-2", "-3", "-5"),
    "u8": ("200", "201", "202"),
    "i16": ("-300", "-301", "-302"),
    "u16": ("40000", "40001", "40002"),
    "i32": ("-70000", "-70001", "-70002"),
    "u32": ("3000000000", "3000000001", "3000000002"),
    "i64": ("-5000000000", "-5000000001", "-5000000002"),
    "u64": ("5000000000", "5000000001", "5000000002"),
    "f32": ("1.5", "2.5", "3.5"),
    "f64": ("1.5", "2.5", "3.5"),
    "bool": ("true", "false", "true"),
}
SIZES = (2, 3, 8, 17)


@pytest.fixture
def compile_with(ritz1_bin, tmp_path):
    """_compile, by name.  The gate builds ritz1_selfhosted before pytest."""
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _compile("ritz0", None, tmp_path, name, program)
        return _compile("ritz1", bins[compiler], tmp_path, name, program)
    return go


@pytest.fixture
def run_with(ritz1_bin, tmp_path):
    """_run, by name."""
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _run("ritz0", None, tmp_path, name, program)
        return _run("ritz1", bins[compiler], tmp_path, name, program)
    return go


def _grid_size(kind: str, addr: str, ty: str, n: int, base: int) -> tuple[str, str]:
    """The fns reading `[n]ty` through `kind`, and the checks in main."""
    fill, first, second = SCALARS[ty]
    last = n - 1
    decls = f"""
fn read_const{n}(p: {kind}[{n}]{ty}) -> {ty}
    return p[{last}]

fn read_var{n}(p: {kind}[{n}]{ty}, i: i32) -> {ty}
    return p[i]
"""
    main = f"""\
    var a{n}: [{n}]{ty}
    var k{n}: i32 = 0
    while k{n} < {n}
        a{n}[k{n}] = {fill}
        k{n} = k{n} + 1
    a{n}[{last}] = {first}
    a{n}[0] = {second}
    if read_const{n}({addr}a{n}) != {first}
        return {base + 1}
    if read_var{n}({addr}a{n}, {last}) != {first}
        return {base + 2}
    if read_var{n}({addr}a{n}, 0) != {second}
        return {base + 3}
"""
    return decls, main


def _a(body: str) -> str:
    return "pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n" + body


# Every way a local comes to hold the pointer, and every value context.  Each
# program returns 20 unless it says otherwise.
READS = {
    "let_pointer": _a("    let p: *[3]i32 = @a\n    return p[1]\n"),
    "let_reference": _a("    let p: @[3]i32 = @a\n    return p[1]\n"),
    "let_mut_reference": _a("    let p: @&[3]i32 = @&a\n    return p[1]\n"),
    "infer_addr": _a("    let p = @a\n    return p[1]\n"),
    "infer_var_addr": _a("    var p = @a\n    return p[1]\n"),
    "infer_addr_mut": _a("    let p = @&a\n    return p[1]\n"),
    "infer_copy_pointer": "fn f(p: *[3]i32) -> i32\n    let q = p\n    return q[1]\n\n" + _a("    return f(@a)\n"),
    "infer_copy_reference": "fn f(p: @[3]i32) -> i32\n    let q = p\n    return q[1]\n\n" + _a("    return f(@a)\n"),
    "infer_copy_mut_reference": "fn f(p: @&[3]i32) -> i32\n    let q = p\n    return q[1]\n\n" + _a("    return f(@&a)\n"),
    "infer_copy_twice": "fn f(p: *[3]i32) -> i32\n    let q = p\n    let r = q\n    return r[1]\n\n" + _a("    return f(@a)\n"),
    "infer_from_lent": "fn f(a:& [3]i32) -> i32\n    let p = @a\n    return p[1]\n\n" + _a("    return f(@&a)\n"),
    "infer_from_by_value": "fn f(a: [3]i32) -> i32\n    let p = @a\n    return p[1]\n\n" + _a("    return f(a)\n"),
    "infer_from_global": "var g: [3]i32\n\npub fn main() -> i32\n    g[1] = 20\n    let p = @g\n    return p[1]\n",
    "infer_mut_from_global": "var g: [3]i32\n\npub fn main() -> i32\n    g[1] = 20\n    let p = @&g\n    return p[1]\n",
    "infer_from_field": "struct H\n    a: [3]i32\n\npub fn main() -> i32\n    var h: H\n    h.a[1] = 20\n    let p = @h.a\n    return p[1]\n",
    "infer_in_a_loop": "pub fn main() -> i32\n    var a: [3]i32 = [5, 7, 8]\n    var i: i32 = 0\n    var t: i32 = 0\n    while i < 3\n        let p = @a\n        t = t + p[i]\n        i = i + 1\n    return t\n",
    "reassigned": _a("    var b: [3]i32 = [1, 20, 3]\n    var p: *[3]i32 = @a\n    p = @b\n    return p[1]\n"),
    "method": "struct S\n    x: i32\n\nimpl S\n    fn get(self, p: *[3]i32) -> i32\n        return p[1]\n\n"
              + _a("    var s: S\n    return s.get(@a)\n"),
    "generic_pointer": "fn f<T>(p: *[3]T) -> T\n    return p[1]\n\n" + _a("    return f<i32>(@a)\n"),
    "generic_reference": "fn f<T>(p: @[3]T) -> T\n    return p[1]\n\n" + _a("    return f<i32>(@a)\n"),
    "generic_mut_reference": "fn f<T>(p: @&[3]T) -> T\n    return p[1]\n\n" + _a("    return f<i32>(@&a)\n"),
    "binary": "fn f(p: *[3]i32) -> i32\n    return p[1] + p[0] - p[0]\n\n" + _a("    return f(@a)\n"),
    "compare": "fn f(p: @[3]i32) -> i32\n    if p[1] == 20\n        return 20\n    return 1\n\n" + _a("    return f(@a)\n"),
    "argument": "fn g(x: i32) -> i32\n    return x\n\nfn f(p: @[3]i32) -> i32\n    return g(p[1])\n\n" + _a("    return f(@a)\n"),
    "cast": "fn f(p: *[3]i32) -> i32\n    let x: i64 = p[1] as i64\n    return x as i32\n\n" + _a("    return f(@a)\n"),
    "infer_element": "fn f(p: *[3]i32) -> i32\n    let x = p[1]\n    return x\n\n" + _a("    return f(@a)\n"),
    "index_is_an_element": "fn f(p: *[3]i32, q: *[3]i32) -> i32\n    return p[q[0]]\n\n"
                           "pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n    var i: [3]i32 = [1, 0, 0]\n    return f(@a, @i)\n",
    "cast_to_element_pointer": "fn f(p: *[3]i32) -> i32\n    let q: *i32 = p as *i32\n    return q[1]\n\n" + _a("    return f(@a)\n"),
    "negative_stays_negative": "fn f(p: *[3]i32) -> i32\n    let x: i64 = p[1] as i64\n    if x < 0\n        return 20\n    return 1\n\n"
                               "pub fn main() -> i32\n    var a: [3]i32 = [1, -2, 3]\n    return f(@a)\n",
    "unsigned_stays_positive": "fn f(p: *[3]u32) -> i32\n    let x: u64 = p[1] as u64\n    if x > 2147483648\n        return 20\n    return 1\n\n"
                               "pub fn main() -> i32\n    var a: [3]u32 = [1, 3000000000, 3]\n    return f(@a)\n",
    "double_arithmetic": "fn f(p: *[3]f64) -> f64\n    return p[1] + p[2]\n\n"
                         "pub fn main() -> i32\n    var a: [3]f64 = [1.0, 19.5, 0.5]\n    return f(@a) as i32\n",
    "float_let": "fn f(p: @[3]f32) -> i32\n    let x: f32 = p[1]\n    return x as i32\n\n"
                 "pub fn main() -> i32\n    var a: [3]f32 = [1.0, 20.5, 0.5]\n    return f(@a)\n",
    "bool_condition": "fn f(p: *[3]bool) -> i32\n    if p[1]\n        return 20\n    return 1\n\n"
                      "pub fn main() -> i32\n    var a: [3]bool\n    a[1] = true\n    return f(@a)\n",
    "struct_element_field": "struct S\n    x: i32\n    y: i64\n\nfn f(p: *[3]S) -> i32\n    return p[1].x\n\n"
                            "pub fn main() -> i32\n    var a: [3]S\n    a[1].x = 20\n    a[2].x = 9\n    return f(@a)\n",
    "deref_copies_the_whole_array": "fn f(p: *[3]i32) -> i32\n    var b: [3]i32 = *p\n    return b[1]\n\n" + _a("    return f(@a)\n"),
    "deref_store_is_the_way_to_store": "fn f(p: *[3]i32)\n    var b: [3]i32 = [1, 20, 3]\n    *p = b\n\n" + _a("    f(@a)\n    return a[1]\n"),
}


# An inferred local was an i64 slot.  What it could do then, it does now.
INFERRED_STAYS_A_POINTER = {
    "cast_to_element_pointer": _a("    let p = @a\n    let q: *i32 = p as *i32\n    return q[1]\n"),
    "mut_cast_to_element_pointer": _a("    let p = @&a\n    let q: *i32 = p as *i32\n    return q[1]\n"),
    "cast_to_integer": _a("    let p = @a\n    let x: i64 = p as i64\n    if x == 0\n        return 1\n    return 20\n"),
    "null": _a("    let p = @a\n    if p == null\n        return 1\n    return 20\n"),
    "mut_null": _a("    let p = @&a\n    if p == null\n        return 1\n    return 20\n"),
    "whole_copy": _a("    let p = @a\n    var b: [3]i32 = *p\n    return b[1]\n"),
    "whole_store": _a("    let p = @&a\n    var b: [3]i32 = [1, 20, 3]\n    *p = b\n    return a[1]\n"),
    "to_pointer_param": "fn g(p: *[3]i32) -> i32\n    return p[1]\n\n" + _a("    let p = @a\n    return g(p)\n"),
    "to_reference_param": "fn g(p: @[3]i32) -> i32\n    return p[1]\n\n" + _a("    let p = @a\n    return g(p)\n"),
    "to_mut_reference_param": "fn g(p: @&[3]i32) -> i32\n    return p[1]\n\n" + _a("    let p = @&a\n    return g(p)\n"),
    "mut_to_pointer_param": "fn g(p: *[3]i32) -> i32\n    return p[1]\n\n" + _a("    let p = @&a\n    return g(p)\n"),
    # R1: an `@T` into `:&` is refused, an `@&T` passes (test_bare_place_borrow.py).
    "to_borrow_param": "fn g(p:& [3]i32) -> i32\n    return p[1]\n\n" + _a("    let p = @&a\n    return g(p)\n"),
    "returned": "fn g(a: *[3]i32) -> *[3]i32\n    let q = a\n    return q\n\n" + _a("    let p: *[3]i32 = g(@a)\n    return p[1]\n"),
    # Written `: i64`, these are integers (var_declared_type, #2352), not the
    # inferred `let x = @a` above, and must still read as the integer they were.
    "annotated_integer": _a("    let x: i64 = @a\n    return 20\n"),
    "annotated_integer_copy": "fn f(p: *[3]i32) -> i32\n    let x: i64 = p\n    return 20\n\n" + _a("    return f(@a)\n"),
    "annotated_integer_arithmetic": _a("    let x: i64 = @a as i64\n    let y: i64 = x + 4\n    let q: *i32 = y as *i32\n    return *q\n"),
}


# `@&T` fits `@T` (LARB R1).  An `@&` local is a `ptr` on ritz1 and an `@` param
# the i64 value model, so the call converts it (#2334, #2416).  An inferred `@&a`
# is an `@&` local, as an annotated one is: R1 makes `@T` read-only, so recording
# it as `@` instead would be refused at `*p = b` once that's checked.
MUT_INTO_SHARED = {
    "param": "fn g(p: @[3]i32) -> i32\n    return p[1]\n\n" + _a("    let p = @&a\n    return g(p)\n"),
    "copy": "fn g(p: @[3]i32) -> i32\n    return p[1]\n\n" + _a("    let p = @&a\n    let q = p\n    return g(q)\n"),
    "method": "struct W\n    v: i32\n\nimpl W\n    fn m(self:& W, q: @[3]i32) -> i32\n        return q[1]\n\n" + _a("    let p = @&a\n    var w: W\n    w.v = 0\n    return w.m(p)\n"),
    "annotated": "fn g(p: @[3]i32) -> i32\n    return p[1]\n\n" + _a("    let p: @&[3]i32 = @&a\n    return g(p)\n"),
    "from_param": "fn g(p: @[3]i32) -> i32\n    return p[1]\n\nfn f(p: @&[3]i32) -> i32\n    return g(p)\n\n"
                  + _a("    return f(@&a)\n"),
    "scalar": "fn g(q: @i32) -> i32\n    return *q\n\n" + _a("    let p: @&i32 = @&a[1]\n    return g(p)\n"),
}


def _store_grid(kind: str, addr: str, ty: str, n: int, base: int, writable: bool) -> tuple[str, str]:
    """Stores and addresses through `kind` into `r.a` of an `R{n}`, whose `b` lies
    right behind it: a stride of `[n]ty` reaches `b`, which must keep its fill."""
    fill, first, second = SCALARS[ty]
    last = n - 1
    decls = f"""
struct R{n}
    a: [{n}]{ty}
    b: [{n}]{ty}

fn at{n}(p: {kind}[{n}]{ty}, i: i32) -> {ty}
    let q: *{ty} = @p[i]
    return *q
"""
    main = f"""\
    var r{n}: R{n}
    var k{n}: i32 = 0
    while k{n} < {n}
        r{n}.a[k{n}] = {fill}
        r{n}.b[k{n}] = {fill}
        k{n} = k{n} + 1
    r{n}.a[1] = {first}
    if at{n}({addr}r{n}.a, 1) != {first}
        return {base + 1}
"""
    if writable:
        decls += f"""
fn set_const{n}(p: {kind}[{n}]{ty}, v: {ty})
    p[1] = v

fn set_var{n}(p: {kind}[{n}]{ty}, i: i32, v: {ty})
    p[i] = v

fn put{n}(p: {kind}[{n}]{ty}, i: i32, v: {ty})
    let q: @&{ty} = @&p[i]
    *q = v
"""
        main += f"""\
    r{n}.a[1] = {fill}
    set_const{n}({addr}r{n}.a, {first})
    if r{n}.a[1] != {first}
        return {base + 2}
    if r{n}.b[1] != {fill} or r{n}.a[0] != {fill}
        return {base + 3}
    set_var{n}({addr}r{n}.a, {last}, {second})
    if r{n}.a[{last}] != {second}
        return {base + 4}
    put{n}({addr}r{n}.a, 0, {second})
    if r{n}.a[0] != {second}
        return {base + 5}
    if r{n}.b[0] != {fill} or r{n}.b[{last}] != {fill}
        return {base + 6}
"""
    return decls, main


def _store(kind: str, addr: str, stmt: str, ty: str = "i32") -> str:
    """`stmt` in `f`, over a `[3]ty` of ones; 20 when a[1] is 7 and the rest ones."""
    return f"""\
fn f(p: {kind}[3]{ty}, i: i32, v: {ty})
    {stmt}

pub fn main() -> i32
    var a: [3]{ty}
    a[0] = 1 as {ty}
    a[1] = 1 as {ty}
    a[2] = 1 as {ty}
    f({addr}a, 1, 7 as {ty})
    if a[0] != 1 as {ty} or a[2] != 1 as {ty}
        return 1
    if a[1] != 7 as {ty}
        return 2
    return 20
"""


# These were REFUSED (#2321): ritz0 stored at stride `[N]T`, so a scalar didn't fit.
# Each returns 20.
STORES = {
    "infer_mut_addr_store": _a("    let p = @&a\n    p[1] = 7\n    return a[1] - 7 + 20\n"),
    "infer_copy_store": "fn f(p: *[3]i32)\n    let q = p\n    q[1] = 7\n\n" + _a("    f(@a)\n    return a[1] + 13\n"),
    "let_store": _a("    let p: *[3]i32 = @a\n    p[1] = 7\n    return a[1] + 13\n"),
    "generic_pointer_store": "fn f<T>(p: *[3]T, v: T)\n    p[1] = v\n\n" + _a("    f<i32>(@a, 7)\n    return a[1] + 13\n"),
    "generic_mut_reference_store": "fn f<T>(p: @&[3]T, v: T)\n    p[1] = v\n\n" + _a("    f<i32>(@&a, 7)\n    return a[1] + 13\n"),
    # The view `p[i]` goes through shares p's slot, so it moves with p.
    "reassigned": _a("    var b: [3]i32 = [1, 2, 3]\n    var p: *[3]i32 = @a\n    p = @b\n    p[1] = 7\n    return a[1] + b[1] - 7\n"),
    "in_a_loop": _a("    let p: *[3]i32 = @a\n    var i: i32 = 0\n    while i < 3\n        p[i] = p[i] + i\n        i = i + 1\n    return a[1] - 1\n"),
    # Two array pointers side by side, of different widths: each has its own view.
    "two": "fn f(p: *[3]i32, q: *[3]i64)\n    p[1] = 7\n    q[1] = 9\n    p[2] = 4\n\n"
           "pub fn main() -> i32\n    var a: [3]i32 = [0, 0, 0]\n    var b: [3]i64 = [0, 0, 0]\n    f(@a, @b)\n"
           "    return a[1] + a[2] + b[1] as i32\n",
    "method": "struct W\n    v: i32\n\nimpl W\n    fn put(self, p: *[3]i32)\n        p[1] = 7\n\n"
              + _a("    var w: W\n    w.v = 0\n    w.put(@a)\n    return a[1] + 13\n"),
}
for _kind in WRITABLE:
    _spelled, _addr = KINDS[_kind]
    STORES[f"{_kind}_store_const"] = _store(_spelled, _addr, "p[1] = 7")
    STORES[f"{_kind}_store_var"] = _store(_spelled, _addr, "p[i] = v")
    STORES[f"{_kind}_store_compound"] = _store(_spelled, _addr, "p[1] += 6")
    STORES[f"{_kind}_store_compound_var"] = _store(_spelled, _addr, "p[i] += v - 1")
    STORES[f"{_kind}_store_byte"] = _store(_spelled, _addr, "p[1] = 7", "u8")
    STORES[f"{_kind}_store_short_compound"] = _store(_spelled, _addr, "p[1] += 6", "i16")
    STORES[f"{_kind}_store_wide"] = _store(_spelled, _addr, "p[i] = v", "i64")
    STORES[f"{_kind}_store_double"] = _store(_spelled, _addr, "p[1] = 7.0", "f64")
    STORES[f"{_kind}_store_float_compound"] = _store(_spelled, _addr, "p[1] += 6.0", "f32")


# §3.2: an `@[N]T` is read-only, whatever is written through it, at the place.
SHARED_WRITES = {
    "store_const": ("    p[1] = 7\n", ref_rules.WRITE_THROUGH_SHARED, "2:5"),
    "store_var": ("    p[i] = 7\n", ref_rules.WRITE_THROUGH_SHARED, "2:5"),
    "compound": ("    p[1] += 7\n", ref_rules.WRITE_THROUGH_SHARED, "2:5"),
    "whole_array": ("    var b: [3]i32 = [1, 2, 3]\n    p[1] = b\n", ref_rules.WRITE_THROUGH_SHARED, "3:5"),
    "mut_address": ("    let q: @&i32 = @&p[1]\n    *q = 7\n", "cannot borrow through an `@T` as mutable", "2:20"),
    "inferred": ("    let q = p\n    q[1] = 7\n", ref_rules.WRITE_THROUGH_SHARED, "3:5"),
}


# The element is the slot a literal lands in, as `a[1] = 300` on the array itself.
# Base refused these stores outright; lowered without the slot, `300` was 44.
SLOTS = {
    "too_big": ("u8", "p[1] = 300", "`300` does not fit in `u8`"),
    "too_small": ("i8", "p[i] = -129", "`-129` does not fit in `i8`"),
    "int_into_bool": ("bool", "p[1] = 1", "cannot use an integer as bool"),
    "bool_into_int": ("i32", "p[1] = true", "cannot use bool as an integer"),
    "inferred": ("u16", "let q = p\n    q[1] = 70000", "`70000` does not fit in `u16`"),
}


# Row 0's pointer, into a `[2][3]i32`.  ritz0 took these at stride `[N]T` (#2330):
# `@p[1]` was row 1's first element, 4, and `p[1] = b` replaced row 1 whole.  R9:
# element 1 of row 0, and a type error.
RITZ0_STRIDES_BY_THE_ARRAY = {
    "address": ("""\
fn f(p: *[3]i32) -> i32
    let q: *i32 = @p[1]
    return *q

pub fn main() -> i32
    var a: [2][3]i32
    a[0][1] = 2
    a[1][0] = 4
    return f(@a[0])
""", 2),
    "whole_array_store": ("""\
fn f(p: *[3]i32)
    var b: [3]i32 = [1, 2, 3]
    p[1] = b

pub fn main() -> i32
    var a: [2][3]i32
    a[0][1] = 7
    a[1][0] = 9
    f(@a[0])
    return a[0][1] * 10 + a[1][0]
""", array_rules.ELEMENT_NOT_ARRAY),
}


# `p + i` strides `[N]T`, the pointee: it walks rows (R9).  Row 1 of a `[2][3]i32`.
ROW_WALK = {
    "let": "    let q = p + 1\n    return q[0] * 10 + q[2]\n",
    "annotated": "    let q: *[3]i32 = p + 1\n    return q[0] * 10 + q[2]\n",
}


# Struct elements: H keeps a second array right behind the first, so a stride of
# `[3]S` lands in `h.b`, which must keep its 40s.  S has padding, P more, B none.
_STRUCTS = {
    "S": "struct S\n    x: i32\n    y: i64\n",
    "P": "struct P\n    a: u8\n    x: i32\n    c: u16\n    y: i64\n",
    "B": "struct B\n    x: i32\n    y: i8\n",
}


def _struct_program(name: str, kind: str, body: str, ret: str) -> str:
    """`f` does `body` and returns `ret`; main returns f's result * 100 + h.b's check."""
    spelled, addr = KINDS[kind]
    t = name
    return f"""\
{_STRUCTS[t]}
struct H
    a: [3]{t}
    b: [3]{t}

fn g(s: {t}) -> i32
    return s.x

fn f(p: {spelled}[3]{t}) -> i32
{body}    return {ret}

pub fn main() -> i32
    var h: H
    var k: i32 = 0
    while k < 3
        h.a[k].x = k + 4
        h.a[k].y = (k + 5) as {'i8' if t == 'B' else 'i64'}
        h.b[k].x = 40
        k = k + 1
    let r: i32 = f({addr}h.a)
    if h.b[0].x != 40 or h.b[1].x != 40 or h.b[2].x != 40
        return 99
    return r
"""


# Each: the body, what f returns, and what the program returns.  a[i].x is i + 4
# and a[i].y is i + 5.
STRUCT_READS = {
    "field": ("", "p[1].x + p[2].y as i32", 12),
    "field_address": ("    let q: *i32 = @p[2].x\n", "*q", 6),
    "by_value": ("    let s = g(p[0])\n", "s", 4),
    "copy": ("    let s: {t} = p[1]\n", "s.x * 10 + s.y as i32", 56),
    "assigned": ("    var s: {t}\n    s = p[2]\n", "s.x", 6),
    "element_address": ("    let q: *{t} = @p[1]\n", "q.x", 5),
}
STRUCT_WRITES = {
    "field_store": ("    p[1].x = 7\n", "p[1].x + p[0].x + p[2].x", 17),
    "field_compound": ("    p[1].y += 3\n", "p[1].y as i32", 9),
    "field_mut_address": ("    let q: @&i32 = @&p[2].x\n    *q = 1\n", "p[2].x + p[1].x", 6),
    "element_store": ("    var s: {t}\n    s.x = 9\n    s.y = 2\n    p[1] = s\n", "p[1].x + p[1].y as i32 + p[2].x", 17),
    "element_from_element": ("    p[0] = p[2]\n", "p[0].x * 10 + p[0].y as i32", 67),
}


# ritz0 fails at clang; a value that was a row must not come out as an integer.
# R9 makes `p[i]` a row here, and `p[i] = row` its store: `*[N][M]T` is #2098's.
ROWS = {
    "row_element": "fn f(p: @[2][3]i32) -> i32\n    return p[1][2]\n\n",
    # An `@[2][3]i32` param, not a `:&` one: main's `f(@a)` would be refused
    # first, on Sema since AGAST #4011 (`@x` doesn't fit a `:&` slot).
    "inferred": "fn f(a: @[2][3]i32) -> i32\n    let p = a\n    return p[1][2]\n\n",
}

# AGAST #4290: `p[1]` of an `@[2][3]i32` is a row, a `[3]i32` value, which an
# `as *i32` can't make a pointer: Sema says so before the emitter's limit, in
# ritz0's words at ritz0's place.
ROW_AS_POINTER = ("fn f(p: @[2][3]i32) -> i32\n    let r: *i32 = p[1] as *i32\n    return r[2]\n\n"
                  "pub fn main() -> i32\n    var a: [2][3]i32\n    a[1][2] = 6\n    return f(@a)\n")


# `p[i]` over a pointer to an array of pointers is element i, a pointer (LARB R9,
# #2522).  The traps are widths: a store through `*p[1]` writes the element's
# pointee, not 8 bytes (#2330's view gave 70 for 72 at i16, clobbering x[1]).  A
# second array right behind x catches a store that runs past it.  `a[i]` on the
# array itself is #2332's, and test_ritz1_array_ptr_element.py covers it.
# {t}: the pointee; x[0] and x[1] are 1 and 2, so a right store of 7 into x[0]
# answers 72 and a read of x[0], x[1] answers 13 when the elements are swapped.
_PTRS = """
pub fn main() -> i32
    var x: [2]{t}
    var y: [2]{t}
    x[0] = 1
    x[1] = 2
    y[0] = 4
    y[1] = 4
    var a: [2]*{t}
    a[0] = @x[1]
    a[1] = @x[0]
    return f({addr}a) + (x[0] * 10 + x[1]) as i32 + (y[0] + y[1]) as i32 - 8
"""
# all: every kind.  w: the writable kinds; the element's own store goes through the
# array, which `@[N]T` refuses (§3.2).  A store through the element is the
# pointee's business (#2443), so `@` takes those.  *: `*` only, a read.
_PTR_FNS = {
    "deref_store": ("all", "fn f(p: {k}[2]*{t}) -> i32\n    *p[1] = 7\n    return 0\n", 72),
    "deref_store_plus": ("all", "fn f(p: {k}[2]*{t}) -> i32\n    *p[1] += 6\n    return 0\n", 72),
    "index_store": ("all", "fn f(p: {k}[2]*{t}) -> i32\n    p[1][1] = 9\n    return 0\n", 19),
    "deref_load": ("*", "fn f(p: {k}[2]*{t}) -> i32\n    return *p[1] as i32\n", 13),
    "index_load": ("*", "fn f(p: {k}[2]*{t}) -> i32\n    return p[1][0] as i32 * 100 + p[0][0] as i32\n", 114),
    "infer_then_deref": ("*", "fn f(p: {k}[2]*{t}) -> i32\n    let q = p[1]\n    return *q as i32\n", 13),
    "annotated": ("*", "fn f(p: {k}[2]*{t}) -> i32\n    let q: *{t} = p[1]\n    return *q as i32\n", 13),
    "element_store": ("w", "fn f(p: {k}[2]*{t}) -> i32\n    p[1] = p[0]\n    *p[1] = 5\n    return 0\n", 15),
    "address": ("w", "fn f(p: {k}[2]*{t}) -> i32\n    let pp: **{t} = @p[0]\n    **pp = 8\n    return 0\n", 18),
}
POINTER_ELEMENT = {}
for _t in ("u8", "i16", "i32", "u64"):
    for _kind in ("pointer", "reference", "mut_reference"):
        for _form, (_only, _fn, _want) in _PTR_FNS.items():
            spelled, addr = KINDS[_kind]
            if (_only == "*" and _kind != "pointer") or (_only == "w" and _kind not in WRITABLE):
                continue
            POINTER_ELEMENT[f"{_form}_{_kind}_{_t}"] = (
                _fn.format(k=spelled, t=_t) + _PTRS.format(t=_t, addr=addr), _want)
# A struct pointee: `p[1].x` through the element.
_SP = """struct S
    x: i32
    y: i32

fn f(p: {k}[2]*S) -> i32
{body}
pub fn main() -> i32
    var s: [2]S
    var t: [2]S
    s[0].x = 1
    s[0].y = 2
    s[1].x = 3
    s[1].y = 4
    t[0].x = 5
    var a: [2]*S
    a[0] = @s[1]
    a[1] = @s[0]
    return f({addr}a) + s[0].x * 10 + s[0].y + t[0].x - 5
"""
for _kind in ("pointer", "reference", "mut_reference"):
    spelled, addr = KINDS[_kind]
    POINTER_ELEMENT[f"struct_load_{_kind}"] = (
        _SP.format(k=spelled, addr=addr, body="    return p[1].y * 10 + p[0].x\n"), 35)
    POINTER_ELEMENT[f"struct_store_{_kind}"] = (
        _SP.format(k=spelled, addr=addr, body="    p[1].x = 7\n    return 0\n"), 72)
    POINTER_ELEMENT[f"struct_field_address_{_kind}"] = (
        _SP.format(k=spelled, addr=addr, body="    let q: *i32 = @p[1].y\n    *q = 6\n    return 0\n"), 16)


# Bases that aren't locals (#2329) bind their view at the site (through_spill).
_PMAIN = _PTRS.replace("    return f({addr}a)", "{setup}    return f({arg})")
for _t in ("i16", "i32"):
    for _base, _decl, _setup, _arg, _b in (
            ("field", "struct H\n    r: *[2]*{t}\n\nfn f(h: *H) -> i32\n", "    var h: H\n    h.r = @a\n", "@h", "h.r"),
            ("global", "var g: *[2]*{t}\n\nfn f(z: i32) -> i32\n", "    g = @a\n", "0", "g"),
            ("call", "fn h(p: *[2]*{t}) -> *[2]*{t}\n    return p\n\nfn f(p: *[2]*{t}) -> i32\n", "", "@a", "h(p)")):
        for _form, _body, _want in (("deref_store", "    *B[1] = 7\n    return 0\n", 72),
                                    ("deref_load", "    return *B[1] as i32\n", 13),
                                    ("index_store", "    B[1][1] = 9\n    return 0\n", 19)):
            POINTER_ELEMENT[f"{_base}_{_form}_{_t}"] = (
                _decl.format(t=_t) + _body.replace("B", _b)
                + _PMAIN.format(t=_t, setup=_setup, arg=_arg), _want)


# A whole struct element by value.  R9 makes a copy legal: `let s: S = p[i]`, `g(p[i])`.
# The rest put a struct where a number goes.  ritz0 refuses them or fails at clang;
# ritz1 keeps #2321's located refusal, since `*(p# + i)` there failed at clang (#2525).
_S = "struct S\n    x: i32\n    y: i64\n\n"
_SMAIN = "pub fn main() -> i32\n    var a: [3]S\n    a[1].x = 5\n    a[1].y = 6\n    return f(@a) as i32\n"
_SMUT = _SMAIN.replace("f(@a)", "f(@&a)")
STRUCT_COPIES = {
    "by_value": _S + "fn f(p: *[3]S) -> i32\n    let s: S = p[1]\n    return s.x\n\n" + _SMAIN,
    "by_value_argument": _S + "fn g(s: S) -> i32\n    return s.x\n\nfn f(p: *[3]S) -> i32\n    return g(p[1])\n\n" + _SMAIN,
    "by_value_inferred": _S + "fn f(p: *[3]S) -> i32\n    let s = p[1]\n    return s.x\n\n" + _SMAIN,
    # AGAST #2524: the un-annotated copy through a reference, and the `*(q + 1)`
    # whole-struct deref it stands for, type as S.  A `var` copy is a copy too.
    "by_value_inferred_reference": _S + "fn f(p: @[3]S) -> i32\n    let s = p[1]\n    return s.x\n\n" + _SMAIN,
    "by_value_inferred_mut_reference": _S + "fn f(p: @&[3]S) -> i32\n    var s = p[1]\n    s.x = 9\n    return p[1].x + s.x - 9\n\n"
    + _SMUT,
    "by_value_inferred_deref": _S + "fn f(q: *S) -> i32\n    let s = *(q + 1)\n    return s.x\n\n"
    + _SMAIN.replace("f(@a)", "f(@a[0])"),
    "by_value_inferred_deref_plain": _S + "fn f(q: *S) -> i32\n    let s = *q\n    return s.x\n\n"
    + _SMAIN.replace("f(@a)", "f(@a[1])"),
    # AGAST #2996: `return a[1]` from a `-> S` fn, on a `[3]S` itself, is a copy
    # too, beside the integer uses WHOLE_STRUCT_ELEMENT refuses.
    "returned_local": _S + "fn f() -> S\n    var a: [3]S\n    a[1].x = 5\n    return a[1]\n\n"
    + "pub fn main() -> i32\n    let s = f()\n    return s.x\n",
    "returned_global": _S + "var G: [3]S\n\nfn f() -> S\n    return G[1]\n\n"
    + "pub fn main() -> i32\n    G[1].x = 5\n    let s = f()\n    return s.x\n",
    "returned_field": _S + "struct H\n    cs: [3]S\n\nfn f() -> S\n    var h: H\n    h.cs[1].x = 5\n    return h.cs[1]\n\n"
    + "pub fn main() -> i32\n    let s = f()\n    return s.x\n",
    # AGAST #3147: a `-> S` tail is a copy into the return slot, as `return` is.
    # ritz1 refused `p[1]` there, fn or method, as a struct in an integer slot.
    "tail_pointer_element": _S + "fn f(q: *S) -> S\n    q[1]\n\n"
    + "pub fn main() -> i32\n    var a: [3]S\n    a[1].x = 5\n    let s = f(@a[0])\n    return s.x\n",
    "tail_pointer_element_method": _S + "struct H\n    k: i32\n\nimpl H\n    fn f(self: @H, q: *S) -> S\n        q[1]\n\n"
    + "pub fn main() -> i32\n    var a: [3]S\n    a[1].x = 5\n    var h: H\n    let s = h.f(@a[0])\n    return s.x\n",
}


WHOLE_STRUCT_ELEMENT = {
    "cast": _S + "fn f(p: *[3]S) -> i64\n    return p[1] as i64\n\n" + _SMAIN,
    "let_integer": _S + "fn f(p: *[3]S) -> i64\n    let n: i64 = p[1]\n    return n\n\n" + _SMAIN,
    "returned": _S + "fn f(p: *[3]S) -> i64\n    return p[1]\n\n" + _SMAIN,
    "compared": _S + "fn f(p: @[3]S) -> i64\n    if p[1] == 5\n        return 1\n    return 0\n\n" + _SMAIN,
    "added": _S + "fn f(p: *[3]S) -> i64\n    return p[1] + 1\n\n" + _SMAIN,
    "mut_reference": _S + "fn f(p: @&[3]S) -> i64\n    return p[1] as i64\n\n" + _SMUT,
    "variable_index": _S + "fn f(p: *[3]S, i: i32) -> i64\n    return p[i] as i64\n\npub fn main() -> i32\n    var a: [3]S\n    return f(@a, 1) as i32\n",
    "inferred_copy": _S + "fn f(p: *[3]S) -> i64\n    let q = p\n    return q[1] as i64\n\n" + _SMAIN,
    "inferred_copy_of_reference": _S + "fn f(p: @[3]S) -> i64\n    let q = p\n    return q[1] as i64\n\n" + _SMAIN,
    "inferred_copy_of_mut_reference": _S + "fn f(p: @&[3]S) -> i64\n    let q = p\n    return q[1] as i64\n\n" + _SMUT,
    "inferred_var_copy": _S + "fn f(p: @[3]S) -> i64\n    var q = p\n    return q[1] as i64\n\n" + _SMAIN,
    "inferred_local": _S + "pub fn main() -> i32\n    var a: [3]S\n    let p = @a\n    return p[1] as i32\n",
    "inferred_mut_local": _S + "pub fn main() -> i32\n    var a: [3]S\n    let p = @&a\n    return p[1] as i32\n",
    # `@&a` into the `:&`: `@a` is refused first, on Sema since AGAST #4011.
    "inferred_borrow": _S + "fn f(a:& [3]S) -> i64\n    let p = @a\n    return p[1] as i64\n\n" + _SMUT,
    "inferred_global": _S + "var G: [3]S\n\npub fn main() -> i32\n    let p = @G\n    return p[1] as i32\n",
    "inferred_field": _S + "struct H\n    cs: [3]S\n\npub fn main() -> i32\n    var h: H\n    let p = @h.cs\n    return p[1] as i32\n",
    # AGAST #2993: `let n: i64 = a[1]` on a `[3]S` itself (local, global, field) is
    # declared i64; #2592's `let r = a[1]` copy must not retype it as %S.
    "let_integer_local": _S + "pub fn main() -> i32\n    var a: [3]S\n    a[1].x = 5\n    let n: i64 = a[1]\n    return n as i32\n",
    "let_integer_global": _S + "var G: [3]S\n\npub fn main() -> i32\n    let n: i64 = G[1]\n    return n as i32\n",
    "let_integer_field": _S + "struct H\n    cs: [3]S\n\npub fn main() -> i32\n    var h: H\n    let n: i64 = h.cs[1]\n    return n as i32\n",
    # AGAST #3147: `(*r)[1]` through a `**S` loads the `%S`, a copy only.
    "returned_deref_pointer": _S + "fn f(r: **S) -> i64\n    return (*r)[1]\n\n"
    + "pub fn main() -> i32\n    var a: [3]S\n    var p: *S = @a[0]\n    return f(@p) as i32\n",
}
# AGAST #2996: every other integer use of `a[1]` on a `[3]S` itself.  ritz1 loaded
# a `%S` and clang refused the IR, unlocated.  ritz0 refuses `+` and `=`, and since
# #2999 `as` and `return` too (test_ritz0_refuses_a_struct_as_an_integer).
_DIRECT_BASES = {
    "local": ("", "    var a: [3]S\n", "a"),
    "global": ("var G: [3]S\n\n", "", "G"),
    "field": ("struct H\n    cs: [3]S\n\n", "    var h: H\n", "h.cs"),
}
_DIRECT_USES = {
    "cast": "    return B[1] as i32\n",
    "added": "    let n: i64 = B[1] + 1\n    return n as i32\n",
    "assigned": "    var n: i64 = 0\n    n = B[1]\n    return n as i32\n",
}
for _db, (_ddecl, _dsetup, _dname) in _DIRECT_BASES.items():
    for _u, _body in _DIRECT_USES.items():
        WHOLE_STRUCT_ELEMENT[f"{_u}_{_db}"] = _S + _ddecl + "pub fn main() -> i32\n" + _dsetup + _body.replace("B", _dname)
    WHOLE_STRUCT_ELEMENT[f"returned_{_db}"] = (_S + _ddecl + "fn f() -> i64\n" + _dsetup + f"    return {_dname}[1]\n\n"
                                             + "pub fn main() -> i32\n    return f() as i32\n")


# AGAST #2999: ritz0 typed `a[1] as i32`, and `return a[1]` from an `-> i64` fn, as
# the struct itself, and clang refused the IR ("value doesn't match function result
# type").  ritz0 refuses any struct value as an integer, located; ritz1's rows above.
RITZ0_STRUCT_AS_INTEGER = sorted(n for n in WHOLE_STRUCT_ELEMENT if n.startswith(("cast", "returned")))
# Not only an element: a struct local, param or call result, cast or returned,
# and the `return` in a match arm and the tail that stand for one.
_SMK = "fn mk() -> S\n    var s: S\n    s.x = 5\n    return s\n\n"
STRUCT_AS_INTEGER = {
    "cast_struct_local": _S + "pub fn main() -> i32\n    var s: S\n    return s as i32\n",
    "cast_struct_param": _S + _SMK + "fn f(s: S) -> i32\n    return s as i32\n\npub fn main() -> i32\n    return f(mk())\n",
    "cast_struct_call": _S + _SMK + "pub fn main() -> i32\n    return mk() as i32\n",
    "cast_struct_to_alias": "type Word = i64\n\n" + _S + "pub fn main() -> i32\n    var s: S\n    let w = s as Word\n"
    + "    return w as i32\n",
    "returned_struct_local": _S + "fn f() -> i64\n    var s: S\n    return s\n\n"
    + "pub fn main() -> i32\n    return f() as i32\n",
    "returned_struct_param": _S + _SMK + "fn f(s: S) -> i64\n    return s\n\n"
    + "pub fn main() -> i32\n    return f(mk()) as i32\n",
    "returned_struct_call": _S + _SMK + "fn f() -> i64\n    return mk()\n\npub fn main() -> i32\n    return f() as i32\n",
    "returned_struct_in_match": _S + _SMK + "fn f(k: i32) -> i64\n    let v = match k\n        0 => return mk()\n"
    + "        _ => 1\n    return v\n\npub fn main() -> i32\n    return f(0) as i32\n",
    "tail_struct_call": _S + _SMK + "fn f() -> i64\n    mk()\n\npub fn main() -> i32\n    return f() as i32\n",
}


# What stays legal beside it: the element's address cast to a pointer, an integer
# field cast, and (STRUCT_COPIES' returned_*) `return a[1]` from an `-> S` fn.
# AGAST #3008: and the same of a struct local, param or call result.
STRUCT_NEIGHBOURS = {
    "cast_local_address": _S + "pub fn main() -> i32\n    var s: S\n    s.x = 5\n    let p = @s as *i32\n    return *p\n",
    "cast_local_field": _S + "fn f(s: S) -> i64\n    return s.x as i64\n\npub fn main() -> i32\n    var s: S\n    s.x = 5\n"
    + "    return f(s) as i32\n",
    "cast_call_field": _S + _SMK + "pub fn main() -> i32\n    return mk().x as i32\n",
    "returned_struct_as_struct": _S + _SMK + "fn f() -> S\n    let s = mk()\n    return s\n\n"
    + "pub fn main() -> i32\n    let s = f()\n    return s.x\n",
    "tail_struct_as_struct": _S + _SMK + "fn f() -> S\n    mk()\n\npub fn main() -> i32\n    return f().x\n",
    "cast_address": _S + "pub fn main() -> i32\n    var a: [3]S\n    a[1].x = 5\n    let p = @a[1] as *i32\n"
    + "    return *p\n",
    "cast_field": _S + "pub fn main() -> i32\n    var a: [3]S\n    a[1].x = 5\n    return a[1].x as i32\n",
    "cast_field_widened": _S + "fn f() -> i64\n    var a: [3]S\n    a[1].x = 5\n    return a[1].x as i64\n\n"
    + "pub fn main() -> i32\n    return f() as i32\n",
}


# AGAST #2329, LARB R9: every base follows #2330's table, not just locals and
# params.  A field, a global, a call result and `let q = h(p)` record no pointee N
# and T on ritz1, which read 0 and stored `g[1] = 7` 8 bytes wide at stride 8.
_H = "struct H\n    r: {ty}\n\nfn f(h: *H) -> i32\n    return h.r[1]\n\npub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n    var h: H\n    h.r = @a\n    return f(@h)\n"
_G = "var g: *[3]i32 = null\n\n" + _a("    g = @a\n    return g[1]\n")
_R = "fn h(p: *[3]i32) -> {ty}\n    return p\n\nfn f(p: *[3]i32) -> i32\n    return h(p)[1]\n\n" + _a("    return f(@a)\n")
OPEN_BASES = {
    "field_pointer": _H.format(ty="*[3]i32"),
    "field_reference": _H.format(ty="@[3]i32"),
    "global": _G,
    "call_pointer": _R.format(ty="*[3]i32"),
    "call_reference": _R.format(ty="@[3]i32"),
    "let_from_call": "fn h(p: *[3]i32) -> *[3]i32\n    return p\n\nfn f(p: *[3]i32) -> i32\n    let q = h(p)\n    return q[1]\n\n" + _a("    return f(@a)\n"),
}


GLOBAL_STORE = "var g: *[3]i32 = null\n\n" + _a("    g = @a\n    g[1] = 7\n    return a[1]\n")


def _base(base: str, kind: str, body: str, check: str) -> str:
    """`body` in `f`, with `B` the base `base` over `a`, a `[3]i32` of 10, 20, 30.
    main returns `check`, with `r` what f returned."""
    spelled, addr = KINDS[kind]
    ty = f"{spelled}[3]i32"
    decls, params, args, setup, prefix, b = "", "", "", "", "", ""
    if base == "field":
        decls = f"struct H\n    r: {ty}\n\n"
        params, args, setup, b = "h: *H", "@h", f"    var h: H\n    h.r = {addr}a\n", "h.r"
    elif base == "global":
        decls = f"var g: {ty} = null\n\n"
        setup, b = f"    g = {addr}a\n", "g"
    else:
        decls = f"fn h(p: {ty}) -> {ty}\n    return p\n\n"
        params, args, b = f"p: {ty}", f"{addr}a", "h(p)"
        if base == "let_from_call":
            prefix, b = "    let q = h(p)\n", "q"
    return (decls + "fn rd(q: *i32) -> i32\n    return *q\n\n"
            + f"fn f({params}) -> i32\n{prefix}{body.replace('B', b)}\n"
            + "pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n"
            + f"{setup}    let r: i32 = f({args})\n    return {check}\n")


# Each returns 20.  The neighbours are checked, since `g[1] = 7` once stored an
# i64 at offset 8 and cleared a[2].
_NEIGHBOURS = " + a[0] - 10 + a[2] - 30"
BASE_OPS = {
    "read": ("    return B[1]\n", "r"),
    "read_var": ("    var i: i32 = 2\n    return B[i] - 10\n", "r"),
    "address": ("    return rd(@B[1] as *i32)\n", "r"),
    # `@B[0]` is an `*i32`, so `+ 1` steps one element.
    "address_step": ("    return rd(@B[0] + 1)\n", "r"),
    "store": ("    B[1] = 7\n    return 0\n", "a[1] + 13" + _NEIGHBOURS),
    "store_var": ("    var i: i32 = 1\n    B[i] = 7\n    return 0\n", "a[1] + 13" + _NEIGHBOURS),
    "compound": ("    B[1] += 7\n    return 0\n", "a[1] - 7" + _NEIGHBOURS),
    "mut_address": ("    let e: @&i32 = @&B[1]\n    *e = 7\n    return 0\n", "a[1] + 13" + _NEIGHBOURS),
}
BASES = ("field", "global", "call", "let_from_call")
_WRITES = {"store", "store_var", "compound", "mut_address"}


def _base_cases():
    for base in BASES:
        # A global is null until main points it, and only a pointer is nullable.
        kinds = ("pointer",) if base == "global" else sorted(KINDS)
        for kind in kinds:
            for op in sorted(BASE_OPS):
                yield base, kind, op


# A struct element through each base: `.f` reads and writes element i's field.
_SB = "struct S\n    x: i32\n    y: i64\n\n"
_SA = "    var a: [3]S\n    a[1].x = 5\n    a[1].y = 6\n"
STRUCT_BASES = {
    "field_read": _SB + "struct H\n    r: *[3]S\n\nfn f(h: *H) -> i32\n    return h.r[1].y as i32 + h.r[1].x\n\n"
                  "pub fn main() -> i32\n" + _SA + "    var h: H\n    h.r = @a\n    return f(@h)\n",
    "field_write": _SB + "struct H\n    r: @&[3]S\n\nfn f(h: *H)\n    h.r[1].y = 9\n\n"
                   "pub fn main() -> i32\n" + _SA + "    a[0].x = 0\n    a[2].x = 0\n    var h: H\n    h.r = @&a\n    f(@h)\n    return a[1].y as i32 + a[0].x + a[2].x + 2\n",
    "global_write": _SB + "var g: *[3]S = null\n\npub fn main() -> i32\n" + _SA
                    + "    a[0].x = 0\n    a[2].x = 0\n    g = @a\n    g[1].x = 7\n    return a[1].x + a[0].x + a[2].x + 4\n",
    "call_read": _SB + "fn h(p: *[3]S) -> *[3]S\n    return p\n\npub fn main() -> i32\n" + _SA
                 + "    return h(@a)[1].y as i32 + h(@a)[1].x\n",
    "let_from_call_read": _SB + "fn h(p: @&[3]S) -> @&[3]S\n    return p\n\npub fn main() -> i32\n" + _SA
                          + "    let q = h(@&a)\n    return q[1].y as i32 + q[1].x\n",
}


# The base is evaluated once per use: a store, an address and `op=` call h once
# each (`x op= v` reads and writes one place: AGAST #2529, test_compound_assign_once.py).
CALLED_ONCE = """\
var calls: i32 = 0

fn h(p: *[3]i32) -> *[3]i32
    calls = calls + 1
    return p

pub fn main() -> i32
    var a: [3]i32 = [10, 20, 30]
    h(@a)[1] = 27
    let e: *i32 = @h(@a)[2] as *i32
    *e = 1
    h(@a)[0] += 7
    return a[1] - 27 + a[2] - 1 + a[0] - 17 + calls * 10
"""


# The element's type, where nothing annotates it: `let v = B[1]` is an f64.
_F = "    var a: [3]f64 = [1.5, 10.0, 2.5]\n"
FLOAT_BASES = {
    "field": "struct H\n    r: *[3]f64\n\npub fn main() -> i32\n" + _F
             + "    var h: H\n    h.r = @a\n    let v = h.r[1]\n    return (v * 2.0) as i32\n",
    "global": "var g: @[3]f64 = null\n\npub fn main() -> i32\n" + _F
              + "    g = @a\n    let v = g[1]\n    return (v * 2.0) as i32\n",
    "call": "fn h(p: @&[3]f64) -> @&[3]f64\n    return p\n\npub fn main() -> i32\n" + _F
            + "    let v = h(@&a)[1]\n    return (v * 2.0) as i32\n",
}


# A generic struct's field and a generic fn's return keep N and T when T is a scalar.
GENERIC_BASES = {
    "struct_field": "struct Box<T>\n    r: *[3]i32\n    t: T\n\npub fn main() -> i32\n"
                    "    var a: [3]i32 = [10, 20, 30]\n    var b: Box<i64>\n    b.r = @a\n    b.t = 0\n"
                    "    b.r[2] = 7\n    return b.r[1] + a[2] - 7\n",
    "fn_return": "fn h<T>(p: *[3]i32, t: T) -> *[3]i32\n    return p\n\npub fn main() -> i32\n"
                 "    var a: [3]i32 = [10, 20, 30]\n    h<i64>(@a, 0)[2] = 7\n    return h<i64>(@a, 0)[1] + a[2] - 7\n",
}


# A field of a field: `a.b.data[2] = 1` was ritz1's fail-closed refusal (an array
# pointee had no element kind), pinned in test_ritz1_member_store_fail_closed.py.
NESTED_FIELD = """\
struct B
    data: *[4]u8

struct A
    b: B

pub fn main() -> i32
    var buf: [4]u8 = [9, 9, 9, 9]
    var a: A
    a.b.data = @buf
    a.b.data[2] = 1
    return buf[0] + buf[1] + buf[2] * 10 + buf[3]
"""


# ---- the rows ---------------------------------------------------------------
#
# Each was a parametrised test; its row id is that test's id, less `test_` and
# the compiler.

ALL = table_rows.ALL
RITZ0 = ("ritz0",)
RITZ1S = ("ritz1", "ritz1_selfhosted")
_MUT_BORROW = "cannot borrow through an `@T` as mutable"


def _grid(make, ty: str, kind: str, *extra) -> str:
    """`make`'s decls and checks for each of SIZES, in one program."""
    spelled, addr = KINDS[kind]
    parts = [make(spelled, addr, ty, n, 10 * (k + 1), *extra) for k, n in enumerate(SIZES)]
    return ("".join(d for d, _ in parts) + "\npub fn main() -> i32\n"
            + "".join(m for _, m in parts) + "    return 0\n")


def _escaped(text: str) -> str:
    """A string parameter as pytest spelled it in an id."""
    return text.encode("unicode_escape").decode()


# Stride T, not `[N]T`: row 0's pointer reads row 0, and never reaches row 1.
def _stride(kind: str) -> str:
    spelled, addr = KINDS[kind]
    return f"""\
fn f(p: {spelled}[3]i32) -> i32
    return p[1]

pub fn main() -> i32
    var a: [2][3]i32
    a[0][1] = 2
    a[1][1] = 5
    a[1][0] = 4
    return f({addr}a[0])
"""


# The element is a T, so a whole `[N]T` doesn't fit it, on all three, at the store.
WHOLE_FORMS = ["p[1] = b", "p[i] = b", "(*p)[1] = b", "p[1] = [1, 2, 3]", "p[1] = [0; 3]"]


def _whole(form: str, kind: str) -> Refused:
    spelled, addr = KINDS[kind]
    program = (f"fn f(p: {spelled}[3]i32, i: i32)\n    var b: [3]i32 = [1, 2, 3]\n    {form}\n\n"
               + _a(f"    f({addr}a, 1)\n    return 0\n"))
    # `(*p)[1] = b` is located at the `*`, as `(*p).f = v` is.
    return Refused(program, array_rules.ELEMENT_NOT_ARRAY, at=(3, 6) if form.startswith("(*p)") else (3, 5))


def _slot(name: str, kind: str) -> Refused:
    ty, stmt, message = SLOTS[name]
    spelled, addr = KINDS[kind]
    program = (f"fn f(p: {spelled}[3]{ty}, i: i32)\n    {stmt}\n\n"
               f"pub fn main() -> i32\n    var a: [3]{ty}\n    f({addr}a, 1)\n    return 0\n")
    line = 2 + stmt.count("\n")
    col = ("    " + stmt).splitlines()[-1].index("=") + 3
    return Refused(program, message, at=(line, col))


def _range(kind: str) -> str:
    spelled, addr = KINDS[kind]
    return f"fn f(p: {spelled}[3]i32) -> i32\n    let t = p[1..3]\n    return t[0]\n\n" + _a(f"    return f({addr}a)\n")


def _strides_by_the_element(name: str):
    program, expected = RITZ0_STRIDES_BY_THE_ARRAY[name]
    if isinstance(expected, int):
        return Run(program, expected)
    return Refused(program, expected, at=(3, 5))


# `@p[i]` and `@&p[i]` as an argument, every kind.  `@&` through `@[N]T` is §3.2's.
def _address(kind: str, addr_op: str):
    spelled, addr = KINDS[kind]
    program = (f"fn g(q: *i32) -> i32\n    return *q\n\nfn f(p: {spelled}[3]i32) -> i32\n"
               f"    return g({addr_op}p[1] as *i32)\n\n" + _a(f"    return f({addr}a)\n"))
    if kind == "reference" and addr_op == "@&":
        return Refused(program, _MUT_BORROW, at=(5, 14))
    return Run(program, 20)


def _row_walk(name: str, kind: str) -> Run:
    # mut_reference: `p + 1` of an `@&[3]i32` was a `ptr` fed to inttoptr (#2554).
    spelled, addr = KINDS[kind]
    body = ROW_WALK[name].replace("*[3]i32", f"{spelled}[3]i32") if name == "annotated" else ROW_WALK[name]
    return Run(f"fn f(p: {spelled}[3]i32) -> i32\n{body}\n"
               "pub fn main() -> i32\n    var a: [2][3]i32\n    a[0][0] = 1\n    a[0][2] = 3\n"
               f"    a[1][0] = 4\n    a[1][2] = 6\n    return f({addr}a[0])\n", 46)


def _struct_row(table: dict, name: str, struct: str, kind: str) -> Run:
    body, ret, expected = table[name]
    return Run(_struct_program(struct, kind, body.replace("{t}", struct), ret), expected)


def _struct_shared_write(name: str) -> Refused:
    # Which of §3.2's two it is follows from the write: `@&` borrows, the rest store.
    body, ret, _ = STRUCT_WRITES[name]
    return Refused(_struct_program("S", "reference", body.replace("{t}", "S"), ret),
                   _MUT_BORROW if "@&" in body else ref_rules.WRITE_THROUGH_SHARED)


# An un-annotated local that holds the pointer: `let q = p`, `let q = @h.a`.
def _inferred_writes(bind: str, kind: str) -> Run:
    body = f"    {bind}\n    q[1].x = 7\n    let r: *i32 = @q[2].x\n    *r = 1\n    let s: S = q[1]\n"
    return Run(_struct_program("S", kind, body, "s.x * 10 + p[2].x"), 71)


def _address_taken(take: str) -> Run:
    program = _struct_program("S", "pointer", "", "p[0].x").replace(
        "    let r: i32 = f(@h.a)\n",
        f"    let q = {take}h.a\n    let r: i32 = q[1].x * 10 + q[2].x\n")
    if take == "@&":
        program = program.replace("    let r: i32 = q[1]", "    q[1].x = 7\n    let r: i32 = q[1]")
    return Run(program, 76 if take == "@&" else 56)


# A whole struct element out of a fn, and into a struct literal's field.
def _returned(kind: str) -> Run:
    spelled, _ = KINDS[kind]
    body = "    let w: W = W { s: p[1] }\n    let t: S = e(p)\n"
    program = _struct_program("S", kind, body, "w.s.x * 10 + t.x")
    return Run(program.replace("fn f(", f"struct W\n    s: S\n\nfn e(p: {spelled}[3]S) -> S\n    return p[2]\n\nfn f("), 56)


# A whole-array store built from `(*p)[i]` reads, from test_ritz1_whole_array.py's
# REJECTED, where it sat because ritz0 couldn't index `(*p)` until #2331.
SELF_COPY = """\
fn s(p: *[4]i32)
    *p = [(*p)[3], (*p)[2], (*p)[1], (*p)[0]]

pub fn main() -> i32
    var b: [4]i32 = [3, 0, 0, 0]
    s(@b)
    return b[3]
"""


# A method on an element: `p[i].m()` is a call on element i (#2382's row, here).
def _method(kind: str) -> Run:
    spelled, addr = KINDS[kind]
    call = "p[1].get()" if kind == "reference" else "p[1].bump() + p[1].get() - 1"
    return Run(f"struct C\n    x: i32\n\nimpl C\n    fn bump(self: @&C) -> i32\n        self.x = self.x + 1\n        0\n\n"
               f"    fn get(self: @C) -> i32\n        self.x\n\nfn f(p: {spelled}[2]C) -> i32\n    return {call}\n\n"
               f"pub fn main() -> i32\n    var a: [2]C\n    a[0].x = 1\n    a[1].x = 6\n    return f({addr}a) * 10 + a[0].x\n",
               61)


# `(*p)[i]` is `p[i]` (R9).  It falls out of #2330 on ritz1, and #2331 on ritz0.
def _deref_index(kind: str) -> Run:
    spelled, addr = KINDS[kind]
    return Run(f"fn f(p: {spelled}[3]i32) -> i32\n    (*p)[1] = 7\n    return (*p)[1] + (*p)[2]\n\n"
               + _a(f"    return f({addr}a) - 17\n"), 20)


# §3.2: the element of an `@[N]*U` is the array's, so storing one is refused, at
# the place; a store through it is the pointee's business, and runs above.
SHARED_POINTER_ELEMENT_OPS = ["    p[1] = p[0]\n", "    p[1] += 1\n"]


def _struct_as_integer(name: str, program: str) -> Refused:
    # The cast's own refusal, not the `return` it sits in.
    return Refused(program, ("a struct is not an integer",
                             "cannot cast struct `S`" if name.startswith("cast") else "the fn returns `i"))


# The ordinary pointer stays pointer arithmetic, and its store stays a store.
ELEMENT_POINTER = """\
fn f(p: *i32)
    p[1] = 7

pub fn main() -> i32
    var a: [3]i32 = [10, 20, 30]
    f(@a[0])
    return a[0] + a[1] + a[2]
"""


def _every_base(base: str, kind: str, op: str):
    body, check = BASE_OPS[op]
    program = _base(base, kind, body, check)
    if kind == "reference" and op in _WRITES:
        # §3.2: nothing is written through an `@[N]T`, whatever the base.
        return Refused(program, _MUT_BORROW if op == "mut_address" else ref_rules.WRITE_THROUGH_SHARED,
                       located=False)
    return Run(program, 20)


TABLE = [
    *(Row(f"every_kind_element_type_and_size[{ty}-{kind}]", ALL, Run(_grid(_grid_size, ty, kind), 0))
      for ty in sorted(SCALARS) for kind in sorted(KINDS)),
    *(Row(f"the_stride_is_the_element_not_the_array[{kind}]", ALL, Run(_stride(kind), 2)) for kind in sorted(KINDS)),
    *(Row(f"reads[{name}]", ALL, Run(READS[name], 20)) for name in sorted(READS)),
    *(Row(f"an_inferred_local_stays_a_pointer[{name}]", ALL, Run(INFERRED_STAYS_A_POINTER[name], 20))
      for name in sorted(INFERRED_STAYS_A_POINTER)),
    *(Row(f"an_mut_reference_passes_as_a_reference[{name}]", ALL, Run(MUT_INTO_SHARED[name], 20))
      for name in sorted(MUT_INTO_SHARED)),
    # Every element type and size: a store, a store at a variable index, `@p[i]`
    # read and `@&p[i]` written, and row 1 untouched.  `@[N]T` takes the address only.
    *(Row(f"every_kind_stores_and_addresses_element_i[{ty}-{kind}]", ALL,
          Run(_grid(_store_grid, ty, kind, kind in WRITABLE), 0))
      for ty in sorted(SCALARS) for kind in sorted(KINDS)),
    *(Row(f"a_store_through_the_index_is_element_i[{name}]", ALL, Run(STORES[name], 20)) for name in sorted(STORES)),
    *(Row(f"a_write_through_a_shared_array_is_section_3_2s[{name}]", ALL,
          Refused(f"fn f(p: @[3]i32, i: i32)\n{body}\n" + _a("    f(@a, 1)\n    return 0\n"), message,
                  at=tuple(map(int, where.split(":")))))
      for name, (body, message, where) in sorted(SHARED_WRITES.items())),
    # `let p = @a` is an `@[N]T` too.
    Row("an_inferred_shared_array_refuses_a_store", ALL,
        Refused(_a("    let p = @a\n    p[1] = 7\n    return a[1]\n"), ref_rules.WRITE_THROUGH_SHARED, at=(4, 5))),
    *(Row(f"a_whole_array_is_not_an_element[{form}-{kind}]", ALL, _whole(form, kind))
      for form in WHOLE_FORMS for kind in WRITABLE),
    *(Row(f"the_element_is_the_literal_s_slot[{name}-{kind}]", ALL, _slot(name, kind))
      for name in sorted(SLOTS) for kind in WRITABLE),
    # Every compiler words it "can't be sliced" now; ritz0 used to say otherwise.
    *(Row(f"a_range_is_refused[{kind}]", ALL, Refused(_range(kind), "can't be sliced", located=False))
      for kind in sorted(KINDS)),
    *(Row(f"these_stride_by_the_element_now[{name}]", ALL, _strides_by_the_element(name))
      for name in sorted(RITZ0_STRIDES_BY_THE_ARRAY)),
    *(Row(f"every_address_of_an_element[{addr_op}-{kind}]", ALL, _address(kind, addr_op))
      for addr_op in ("@", "@&") for kind in sorted(KINDS)),
    *(Row(f"pointer_arithmetic_walks_rows[{name}-{kind}]", ALL, _row_walk(name, kind))
      for name in sorted(ROW_WALK) for kind in sorted(KINDS)),
    *(Row(f"a_struct_element_reads[{name}-{struct}-{kind}]", ALL, _struct_row(STRUCT_READS, name, struct, kind))
      for name in sorted(STRUCT_READS) for struct in sorted(_STRUCTS) for kind in sorted(KINDS)),
    *(Row(f"a_struct_element_writes[{name}-{struct}-{kind}]", ALL, _struct_row(STRUCT_WRITES, name, struct, kind))
      for name in sorted(STRUCT_WRITES) for struct in sorted(_STRUCTS) for kind in WRITABLE),
    *(Row(f"a_struct_element_write_through_a_shared_array_is_section_3_2s[{name}]", ALL, _struct_shared_write(name))
      for name in sorted(STRUCT_WRITES)),
    *(Row(f"an_inferred_local_writes_a_struct_element[{bind}-{kind}]", ALL, _inferred_writes(bind, kind))
      for bind in ("let q = p", "var q = p", "let q = p + 0") for kind in WRITABLE),
    *(Row(f"an_address_taken_local_indexes_struct_elements[{take}]", ALL, _address_taken(take)) for take in ("@", "@&")),
    *(Row(f"a_struct_element_is_returned_and_held[{kind}]", ALL, _returned(kind)) for kind in sorted(KINDS)),
    Row("a_deref_index_reads_into_a_whole_array_store", ALL, Run(SELF_COPY, 3)),
    *(Row(f"a_method_on_an_element[{kind}]", ALL, _method(kind)) for kind in sorted(KINDS)),
    *(Row(f"a_deref_index_is_the_same_place[{kind}]", ALL, _deref_index(kind)) for kind in WRITABLE),
    # AGAST #4313: ritz1 and ritz1_selfhosted lower a row of an `@[N][M]T`
    # plane now, so these run on every compiler instead of being refused.
    *(Row(f"an_at_plane_is_indexed[{name}]", ALL,
          Run(ROWS[name] + "pub fn main() -> i32\n    var a: [2][3]i32\n    a[1][2] = 6\n    return f(@a)\n", 6))
      for name in sorted(ROWS)),
    Row("a_row_is_no_pointer", ALL, Refused(ROW_AS_POINTER, ref_rules.VALUE_INTO_SHARED_REF, at=(2, 19))),
    *(Row(f"a_pointer_element[{name}]", ALL, Run(*POINTER_ELEMENT[name])) for name in sorted(POINTER_ELEMENT)),
    *(Row(f"a_shared_pointer_element_is_read_only[{_escaped(op)}]", ALL,
          Refused("fn f(p: @[2]*i16) -> i32\n" + op + "    return 0\n" + _PTRS.format(t="i16", addr="@"),
                  ref_rules.WRITE_THROUGH_SHARED, at=(2, 5)))
      for op in SHARED_POINTER_ELEMENT_OPS),
    *(Row(f"a_whole_struct_element_copies[{name}]", ALL, Run(STRUCT_COPIES[name], 5)) for name in sorted(STRUCT_COPIES)),
    *(Row(f"ritz1_refuses_a_whole_struct_element[{name}]", RITZ1S,
          Refused(WHOLE_STRUCT_ELEMENT[name], "a whole struct is not a value here in ritz1"))
      for name in sorted(WHOLE_STRUCT_ELEMENT)),
    # AGAST #2999: ritz0 typed `a[1] as i32`, and `return a[1]` from an `-> i64` fn,
    # as the struct itself; it refuses any struct value as an integer.
    *(Row(f"ritz0_refuses_a_struct_as_an_integer[{name}]", RITZ0,
          _struct_as_integer(name, WHOLE_STRUCT_ELEMENT.get(name) or STRUCT_AS_INTEGER[name]))
      for name in RITZ0_STRUCT_AS_INTEGER + sorted(STRUCT_AS_INTEGER)),
    # AGAST #3008: ritz1 refused only the `[N]S` element (#2996); a struct local,
    # param or call result cast or returned as an integer passed it and failed at clang.
    *(Row(f"ritz1_refuses_a_struct_as_an_integer[{name}]", RITZ1S, _struct_as_integer(name, STRUCT_AS_INTEGER[name]))
      for name in sorted(STRUCT_AS_INTEGER)),
    *(Row(f"a_struct_field_or_address_still_casts[{name}]", ALL, Run(STRUCT_NEIGHBOURS[name], 5))
      for name in sorted(STRUCT_NEIGHBOURS)),
    Row("a_pointer_to_an_element_still_stores", ALL, Run(ELEMENT_POINTER, 47)),
    *(Row(f"every_base_reads_element_i[{name}]", ALL, Run(OPEN_BASES[name], 20)) for name in sorted(OPEN_BASES)),
    # R9 makes `g[1] = 7` element 1's store, as for a local.
    Row("a_global_stores_element_i", ALL, Run(GLOBAL_STORE, 7)),
    *(Row(f"every_base_is_element_i_in_every_position[{base}-{kind}-{op}]", ALL, _every_base(base, kind, op))
      for base, kind, op in _base_cases()),
    *(Row(f"every_base_reaches_a_struct_element[{name}]", ALL, Run(STRUCT_BASES[name], 11))
      for name in sorted(STRUCT_BASES)),
    Row("a_call_base_is_evaluated_once", ALL, Run(CALLED_ONCE, 30)),
    # The element's type, where nothing annotates it: `let v = B[1]` is an f64.
    *(Row(f"every_base_types_its_element[{name}]", ALL, Run(FLOAT_BASES[name], 20)) for name in sorted(FLOAT_BASES)),
    *(Row(f"a_generic_base_is_element_i[{name}]", ALL, Run(GENERIC_BASES[name], 20)) for name in sorted(GENERIC_BASES)),
    Row("a_nested_field_stores_element_i", ALL, Run(NESTED_FIELD, 37)),
]

# `"..." as io.StrView` (harland's `as serial.StrView`) is refused now: there is
# no `module.item` access (§15.3, AGAST #2215; test_qualified_access_refused.py).


@pytest.mark.integration
@pytest.mark.parametrize("compiler,chunk", table_rows.chunks(TABLE),
                         ids=[f"{c}-{i}" for c, i in table_rows.chunks(TABLE)])
def test_every_row(ritz1_bin, tmp_path, compiler, chunk):
    table_rows.assert_rows(compiler, table_rows.chunk(TABLE, compiler, chunk),
                           build=_batch_build, compile=_batch_compile, work=tmp_path)
