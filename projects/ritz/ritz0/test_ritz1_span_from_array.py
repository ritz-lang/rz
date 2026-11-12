"""Regression tests for AGAST #2502: `@a`, with `a` an `[N]T` local, coerces
to `Span<T>` (or `[T]`, the same type since #1614) in every slot that holds
one, not only a parameter.

A `Span<T>` parameter has built `Span { &a[0], N }` from `@a` since
ritz-task-102. A `let` / `var` initialiser, an assignment and a struct-literal
field missed it: ritz1 emitted the `ptrtoint` of `@a` and then
`store %Span$u8 <i64>`, which clang rejected (an unlocated error). Each row
here failed that way before the fix; test_ritz1_slice_type.py pins the `[T]`
spellings (`local_from_array`, `struct_field_from_array`,
`through_pointer_from_array`).

ritz0 is the oracle: each expected exit status is checked against it too.

AGAST #2781 (and #2366 for a parameter): the array's element must be the
Span's T. MISMATCHED holds the refusals, the same located error on all three.
"""

import pytest

from array_rules import ELEMENT_MISMATCH
from test_ref_into_value import _assert_refused
from test_ritz1_move_param import _run

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

SPAN = "import ritzlib.span\n\n"

# name -> (program, expected exit status)
FORMS = {
    # The ticket's repro.
    "let_span_u8": (SPAN + """\
pub fn main() -> i32
    var a: [4]u8 = [10, 20, 30, 40]
    let v: Span<u8> = @a
    return v[1] as i32
""", 20),
    "var_span_u8_len": (SPAN + """\
pub fn main() -> i32
    let a: [3]u8 = [1, 2, 3]
    var v: Span<u8> = @a
    return v.len as i32 * 10 + v[2] as i32
""", 33),
    # Wider elements: the GEP and the Span both take the element type.
    "let_span_i32": (SPAN + """\
pub fn main() -> i32
    let a: [4]i32 = [1, 2, 3, 4]
    let v: Span<i32> = @a
    var t: i32 = 0
    for i in 0..v.len
        t = t + v[i]
    return t
""", 10),
    "let_span_i64": (SPAN + """\
pub fn main() -> i32
    let a: [2]i64 = [5, 7]
    let v: Span<i64> = @a
    return (v[0] + v[1]) as i32 + v.len as i32
""", 14),
    "assign_span_local": (SPAN + """\
pub fn main() -> i32
    let a: [2]u8 = [1, 2]
    let b: [3]u8 = [4, 5, 6]
    var v: Span<u8> = @a
    v = @b
    return v.len as i32 * 10 + v[2] as i32
""", 36),
    "struct_field_span": (SPAN + """\
struct Packet
    tag: i32
    data: Span<u8>

pub fn main() -> i32
    let b: [3]u8 = [4, 5, 6]
    let p = Packet { tag: 10, data: @b }
    return p.tag + p.data[1] as i32 + p.data.len as i32
""", 18),
    "struct_field_span_i32": (SPAN + """\
struct Bag
    xs: [i32]

pub fn main() -> i32
    let b: [2]i32 = [20, 22]
    let g = Bag { xs: @b }
    return g.xs[0] + g.xs[1]
""", 42),
    "assign_struct_field": (SPAN + """\
struct Packet
    tag: i32
    data: [u8]

pub fn main() -> i32
    let a: [1]u8 = [1]
    let b: [4]u8 = [4, 5, 6, 7]
    var p = Packet { tag: 1, data: @a }
    p.data = @b
    return p.tag + p.data[3] as i32 + p.data.len as i32
""", 12),
    # Control: the parameter path, which always worked, is unchanged.
    "param_span": (SPAN + """\
fn sum(xs: Span<u8>) -> i32
    var t: i32 = 0
    for i in 0..xs.len
        t = t + xs[i] as i32
    return t

pub fn main() -> i32
    let a: [3]u8 = [1, 2, 3]
    return sum(@a)
""", 6),
}


# AGAST #2781 (and #2366, the parameter): `@a` with `a: [N]T1` fits a
# `Span<T2>` / `[T2]` slot only when T1 is T2.  Before the fix a let, var, `=`
# and struct-literal field slot took any element on all three compilers, and
# a parameter on ritz1: the Span viewed the array at the wrong stride.  The
# error is the array-store one (LARB R5): converting is a loop you write.
#
# `^` marks where the error lands.
POINT = "struct P\n    x: i32\n\nstruct Q\n    x: i32\n\n"

MISMATCHED = {
    # The ticket's repro.
    "let_u8_from_i32": SPAN + """\
pub fn main() -> i32
    let a: [2]i32 = [1, 2]
    let v: Span<u8> = ^@a
    return v.len as i32
""",
    "let_slice_spelling": SPAN + """\
pub fn main() -> i32
    let a: [2]i32 = [1, 2]
    let v: [u8] = ^@a
    return v.len as i32
""",
    "var_i32_from_i64": SPAN + """\
pub fn main() -> i32
    var a: [3]i64 = [1, 2, 3]
    var v: Span<i32> = ^@a
    return v.len as i32
""",
    # Same width, other sign: LLVM spells both `i32`.
    "let_u32_from_i32": SPAN + """\
pub fn main() -> i32
    let a: [2]i32 = [1, 2]
    let v: Span<u32> = ^@a
    return v.len as i32
""",
    "assign": SPAN + """\
pub fn main() -> i32
    let a: [2]u8 = [1, 2]
    let b: [3]i32 = [4, 5, 6]
    var v: Span<u8> = @a
    v = ^@b
    return v.len as i32
""",
    "struct_literal_field": SPAN + """\
struct Packet
    tag: i32
    data: Span<u8>

pub fn main() -> i32
    let b: [3]i64 = [4, 5, 6]
    let p = Packet { tag: 10, data: ^@b }
    return p.tag
""",
    "struct_literal_slice_field": SPAN + """\
struct Bag
    xs: [i32]

pub fn main() -> i32
    let b: [2]u8 = [20, 22]
    let g = Bag { xs: ^@b }
    return g.xs.len as i32
""",
    "struct_element": SPAN + POINT + """\
pub fn main() -> i32
    let a: [2]P = [P { x: 1 }, P { x: 2 }]
    let v: Span<Q> = ^@a
    return v.len as i32
""",
    # #2366: the parameter, which ritz1 let through.
    "param": SPAN + """\
fn g(s: Span<i32>) -> i32
    return s.len as i32

pub fn main() -> i32
    var a: [3]i64 = [1, 2, 3]
    return g(^@a)
""",
}

# #2781: matching elements of every kind the check spells still coerce.
FORMS.update({
    "let_span_struct": (SPAN + POINT + """\
pub fn main() -> i32
    let a: [2]P = [P { x: 3 }, P { x: 4 }]
    let v: Span<P> = @a
    return v[0].x * 10 + v[1].x + v.len as i32
""", 36),
    "let_span_bool": (SPAN + """\
pub fn main() -> i32
    let a: [3]bool = [false, true, false]
    let v: Span<bool> = @a
    if v[1]
        return v.len as i32
    return 0
""", 3),
    "let_span_f64": (SPAN + """\
pub fn main() -> i32
    let a: [2]f64 = [1.5, 2.5]
    let v: [f64] = @a
    return (v[0] + v[1]) as i32
""", 4),
    "let_span_u16": (SPAN + """\
pub fn main() -> i32
    let a: [2]u16 = [300, 7]
    let v: Span<u16> = @a
    return (v[0] - 290) as i32 + v[1] as i32
""", 17),
    "let_span_ptr": (SPAN + """\
pub fn main() -> i32
    let a: [2]*u8 = [c"ab", c"xyz"]
    let v: Span<*u8> = @a
    return *(v[1] + 2) as i32
""", 122),
})


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(MISMATCHED))
def test_span_from_array_of_other_element_is_refused(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    _assert_refused(compiler, tmp_path, name, MISMATCHED[name], ELEMENT_MISMATCH)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(FORMS))
def test_span_from_array(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    program, expected = FORMS[name]
    rc = _run(compiler, tmp_path, program)
    assert rc == expected, f"{compiler} {name}: exit {rc}, expected {expected}"
