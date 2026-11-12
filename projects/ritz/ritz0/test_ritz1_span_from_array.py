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
"""

import pytest

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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(FORMS))
def test_span_from_array(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    program, expected = FORMS[name]
    rc = _run(compiler, tmp_path, program)
    assert rc == expected, f"{compiler} {name}: exit {rc}, expected {expected}"
