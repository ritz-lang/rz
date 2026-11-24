"""AGAST #4666 (folds #4668, #4671): programs ritz0 builds that ritz1 could not.

    let x = Cell<u32> { v: 1 }.v      # ritz1: "unhandled EXPR_MEMBER"
    m[1] = r                          # ritz1: "assigning a row ... is not supported"
    n(@b.v)                           # ritz1: a ptrtoint where the %Span$u8 goes

* A field of a struct literal: emit_member_ptr had no arm for a literal base.
  It is built in an entry alloca of its struct and the field GEP'd out of it,
  as a call result's is (#1647).
* A whole row (or plane) of an N-D array: copied over the sub-array the index
  chain stops at (emit_nd_sub_store), from a `[M]T` local, global, field,
  literal or fill, or a row of another N-D array.  `aoa_row_store` was the
  strict xfail of test_ritz1_whole_array.py (citing #2099, which did the
  struct element store, not the row).
* `@x.f` with `f` a `Vec<T>` field into a `Span<T>` slot is `{ f.data, f.len }`,
  as `@v` of a Vec local is.

Every row runs on all three compilers; ritz0 is the oracle.
"""

import pytest
import test_table_rows as table_rows
from test_ref_into_value import COMPILERS
from test_table_rows import Run, assert_runs

pytestmark = pytest.mark.integration

# ---- a field of a struct literal ------------------------------------------

LIT_STRUCTS = """\
struct Q
    x: i32
struct P
    a: Q
    b: i64
struct Cell<B>
    v: B
fn mk() -> P
    P { a: Q { x: 4 }, b: 5 }
fn mkc() -> Cell<u32>
    Cell<u32> { v: 6 }
"""

LITERAL_MEMBER = {
    # The ticket's repro: a generic instance's literal.
    "lit_generic": (LIT_STRUCTS + """\
pub fn main() -> i32
    let x = Cell<u32> { v: 1 }.v
    x as i32
""", 1),
    "lit_plain": (LIT_STRUCTS + """\
pub fn main() -> i32
    Q { x: 3 }.x
""", 3),
    # `.a.x`: the nested arm recurses into the literal's.
    "lit_nested": (LIT_STRUCTS + """\
pub fn main() -> i32
    let y = P { a: Q { x: 7 }, b: 2 }.a.x
    y
""", 7),
    "lit_generic_nested": (LIT_STRUCTS + """\
pub fn main() -> i32
    Cell<P> { v: P { a: Q { x: 9 }, b: 0 } }.v.a.x
""", 9),
    # An omitted field reads as zero (§9.2).
    "lit_omitted_zero": (LIT_STRUCTS + """\
pub fn main() -> i32
    let b = P { a: Q { x: 1 } }.b
    (b + 11) as i32
""", 11),
    # In a condition and as an argument.
    "lit_in_expr": (LIT_STRUCTS + """\
fn id(n: i64) -> i64
    n
pub fn main() -> i32
    if Q { x: 2 }.x == 2
        return id(P { a: Q { x: 1 }, b: 12 }.b) as i32
    1
""", 12),
    # A call result already worked (#1647); its generic instance too.
    "call_result": (LIT_STRUCTS + """\
pub fn main() -> i32
    mk().a.x + (mkc().v as i32)
""", 10),
}

# ---- a whole row of an N-D array ------------------------------------------

ROW_STORE = {
    # The ticket's repro (was test_ritz1_whole_array.py's ROW_GAPS).
    "aoa_row_store": ("""\
pub fn main() -> i32
    var m: [2][4]i32
    var r: [4]i32 = [0, 0, 0, 3]
    m[1] = r
    return m[1][3]
""", 3),
    # The other rows are left alone.
    "row_store_only_that_row": ("""\
pub fn main() -> i32
    var m: [3][2]i64 = [ [1, 2], [3, 4], [5, 6] ]
    let r: [2]i64 = [10, 20]
    m[1] = r
    (m[0][1] + m[1][0] + m[1][1] + m[2][0]) as i32
""", 37),
    "row_from_row": ("""\
pub fn main() -> i32
    var m: [2][4]i32
    var n: [2][4]i32 = [ [1, 2, 3, 4], [5, 6, 7, 8] ]
    m[0] = n[1]
    m[0][0] + m[0][3]
""", 13),
    "row_from_literal": ("""\
pub fn main() -> i32
    var m: [2][3]u8
    m[1] = [4, 5, 6]
    (m[1][0] + m[1][2]) as i32
""", 10),
    "row_from_fill": ("""\
pub fn main() -> i32
    var m: [2][3]i16
    m[0] = [7; 3]
    (m[0][0] + m[0][2]) as i32
""", 14),
    # A literal reading the row it replaces sees the old row: a swap.
    "row_literal_reads_old_row": ("""\
pub fn main() -> i32
    var m: [1][2]i32 = [ [1, 2] ]
    m[0] = [m[0][1], m[0][0]]
    m[0][0] * 10 + m[0][1]
""", 21),
    "row_runtime_index": ("""\
fn pick(i: i64) -> i64
    i
pub fn main() -> i32
    var m: [3][2]i32
    m[pick(2)] = [8, 9]
    m[2][1]
""", 9),
    "row_of_global": ("""\
var G: [2][4]i64
pub fn main() -> i32
    G[1] = [10, 20, 30, 40]
    G[1][3] as i32
""", 40),
    "row_from_global": ("""\
var R: [3]i32 = [1, 2, 3]
pub fn main() -> i32
    var m: [2][3]i32
    m[1] = R
    m[1][2]
""", 3),
    "row_of_field": ("""\
struct H
    m: [2][3]i32
pub fn main() -> i32
    var h: H
    h.m[1] = [9, 8, 7]
    h.m[1][0] + h.m[1][2]
""", 16),
    "row_from_field": ("""\
struct W
    a: [2]i64
pub fn main() -> i32
    let w = W { a: [5, 6] }
    var m: [2][2]i64
    m[1] = w.a
    m[1][1] as i32
""", 6),
    # A 3-D array: `c[1] = p` stores a plane, `c[0][1] = r` a row.
    "plane_store_3d": ("""\
pub fn main() -> i32
    var c: [2][2][3]u8
    var p: [2][3]u8
    p[1][2] = 5
    c[1] = p
    c[1][1][2] as i32
""", 5),
    "row_store_3d": ("""\
pub fn main() -> i32
    var c: [2][2][3]i32
    let r: [3]i32 = [1, 2, 3]
    c[0][1] = r
    c[1][0] = [7; 3]
    c[0][1][2] + c[1][0][0]
""", 10),
    # A struct leaf, copyable.
    "row_of_structs": ("""\
struct Pt
    x: i32
    y: i32
pub fn main() -> i32
    var m: [2][2]Pt
    let r: [2]Pt = [Pt { x: 1, y: 2 }, Pt { x: 3, y: 4 }]
    m[1] = r
    m[1][1].x + m[1][0].y
""", 5),
}

# ---- a program's own `struct Span<T>` of another layout (was #4667) ---------
#
# `Span` is not reserved: LANGUAGE_SPEC reserves no type name, and ritz0 takes
# the program's Span as its own (test_span_builtin_checkers.py's
# test_declared_span_is_the_programs_own).  ritz1 refused it, "struct Span$u8
# must be { ptr: *u8, len: i64 }", because bare "..." lowered to %Span$u8; it
# lowers to the layout-equal %StrView then.

OWN_SPAN = """\
struct Span<T>
    ptr: *T
    len: i64
    cap: i64
"""

USER_SPAN = {
    # The ticket's repro, reading the field the builtin lacks.
    "own_span_u8": (OWN_SPAN + """\
pub fn main() -> i32
    var a: [3]u8 = [1, 2, 3]
    let s = Span<u8> { ptr: @a[0], len: 3, cap: 3 }
    (s.cap + s.len) as i32
""", 6),
    # String literals beside it: a `let`, a StrView slot, an argument, `.len`.
    "own_span_u8_with_literals": (OWN_SPAN + """\
fn first(s: Span<u8>) -> i64
    s.cap
fn n(t: StrView) -> i64
    t.len
pub fn main() -> i32
    var a: [3]u8 = [1, 2, 3]
    let s = Span<u8> { ptr: @a[0], len: 3, cap: 9 }
    let t = "hello"
    let u: StrView = "ab"
    let k = "xyz".len
    (first(s) + t.len + n(u) + n("q") + k) as i32
""", 20),
    # A literal's bytes, through the StrView it lowers to.
    "own_span_literal_bytes": (OWN_SPAN + """\
struct Named
    name: StrView
pub fn main() -> i32
    let w = Named { name: "AZ" }
    let p = w.name.ptr
    (*(p + 1) - *p) as i32
""", 25),
    "own_span_other_elem": (OWN_SPAN + """\
fn total(s: Span<i32>) -> i64
    var t: i64 = 0
    var i: i64 = 0
    while i < s.len
        t = t + *(s.ptr + i) as i64
        i = i + 1
    t + s.cap
pub fn main() -> i32
    var a: [2]i32 = [4, 5]
    total(Span<i32> { ptr: @a[0], len: 2, cap: 30 }) as i32
""", 39),
}

RUNS = {**LITERAL_MEMBER, **ROW_STORE, **USER_SPAN}
assert len(RUNS) == len(LITERAL_MEMBER) + len(ROW_STORE) + len(USER_SPAN)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_rvalue_member_and_row_store_run(tmp_path, compiler):
    assert_runs(compiler, tmp_path, RUNS)


# ---- `@x.f` of a Vec field into a Span slot (was #4671) --------------------

VEC_FIELD = """\
import ritzlib.gvec
import ritzlib.span
fn n(s: Span<u8>) -> i64
    s.len
fn sum(s: Span<i32>) -> i64
    var t: i64 = 0
    var i: i64 = 0
    while i < s.len
        t = t + s[i] as i64
        i = i + 1
    t
struct Box
    v: Vec<u8>
    w: Vec<i32>
struct Outer
    b: Box
fn mkbox() -> Box
    var v: Vec<u8> = vec_new<u8>()
    v.push(1)
    v.push(2)
    var w: Vec<i32> = vec_new<i32>()
    w.push(10)
    w.push(20)
    Box { v: v, w: w }
"""

VEC_SPAN = {
    # The ticket's repro, with an empty Vec.
    "vec_field_arg_empty": ("""\
import ritzlib.gvec
import ritzlib.span
fn n(s: Span<u8>) -> i64
    s.len
struct Box
    v: Vec<u8>
pub fn main() -> i32
    var v: Vec<u8> = vec_new<u8>()
    let b: Box = Box { v: v }
    n(@b.v) as i32
""", 0),
    "vec_field_arg": (VEC_FIELD + """\
pub fn main() -> i32
    let b = mkbox()
    n(@b.v) as i32
""", 2),
    # The elements, not only the length: the Span views the Vec's data.
    "vec_field_elems": (VEC_FIELD + """\
pub fn main() -> i32
    let b = mkbox()
    sum(@b.w) as i32
""", 30),
    "vec_field_mut_borrow": (VEC_FIELD + """\
pub fn main() -> i32
    var b = mkbox()
    n(@&b.v) as i32
""", 2),
    "vec_field_nested": (VEC_FIELD + """\
pub fn main() -> i32
    let o = Outer { b: mkbox() }
    sum(@o.b.w) as i32
""", 30),
    "vec_field_through_ptr": (VEC_FIELD + """\
fn via(p: *Box) -> i64
    n(@p.v)
pub fn main() -> i32
    var b = mkbox()
    via(@b) as i32
""", 2),
    "vec_field_through_ref": (VEC_FIELD + """\
fn via(b: @Box) -> i64
    sum(@b.w)
pub fn main() -> i32
    let b = mkbox()
    via(@b) as i32
""", 30),
}

VEC_SPAN_ROWS = [table_rows.Row(f"vec_field_span[{name}]", table_rows.ALL, Run(*VEC_SPAN[name]))
                 for name in sorted(VEC_SPAN)]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_vec_field_into_span_runs(ritz1_bin, tmp_path, compiler):
    table_rows.assert_ritzlib_rows(compiler, VEC_SPAN_ROWS, ritz1_bin, tmp_path)
