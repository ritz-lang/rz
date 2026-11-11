"""AGAST #2726: a Vec/Span slice used in place, `v[1..3].len` / `v[1..3][1]`.

#2451 rewrites `v[lo..hi]` into the method call `v.slice(lo, hi)`, which
emit_expr_method dispatches by UFCS to vec_slice$T / span_slice$T.  ritz1's
call_result_struct_name looked a method's callee up in the impl table only, so a
field of that call's result had no struct:

    fn f(v: Span<i32>) -> i32
        return v[1..3].len as i32     # ritz1: "unhandled EXPR_MEMBER", unlocated

`let t = v[1..3]; t.len` was already right.  Each program below reads the
slice's length and an element straight off `v[lo..hi]`, with v a param or a
local, in a `return`, a `let` and an `if` condition.  (The pattern-binding
holder is test_slice_pattern_binding.py's test_a_slice_of_a_pattern_binding_returned.)

ritz0 is the oracle: every expected status is what ritz0 returns.
"""

import pytest

import test_ritz1_for_header as for_header
import test_slice_value_local as slice_local
from test_index_through_reference import HEADER

compile_with = for_header.compile_with
run_with = slice_local.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# box -> (its type, statements making `v` hold 10, 20, 30, 40)
BOXES = {
    "Vec": ("Vec<i32>",
            "    var v: Vec<i32> = vec_new<i32>()\n"
            "    v.push(10)\n    v.push(20)\n    v.push(30)\n    v.push(40)\n"),
    "Span": ("Span<i32>",
             "    var a: [4]i32 = [10, 20, 30, 40]\n"
             "    var v: Span<i32> = span_from_ptr<i32>(@a[0], 4)\n"),
}

# name -> (range, length, last element).  An off-by-one in `..=` moves both.
RANGES = {"exclusive": ("1..3", 2, 30), "inclusive": ("1..=3", 3, 40)}


# Where the in-place slice is read: each body ends by returning len + last.
def _in_return(spelled, length):
    return f"    return v[{spelled}].len as i32 + v[{spelled}][{length - 1}] as i32\n"


def _in_let(spelled, length):
    return (f"    let n = v[{spelled}].len\n"
            f"    let e = v[{spelled}][{length - 1}]\n"
            f"    return n as i32 + e as i32\n")


def _in_condition(spelled, length):
    return (f"    if v[{spelled}].len != {length}\n        return 1\n"
            f"    if v[{spelled}][{length - 1}] < 0\n        return 2\n"
            f"    return v[{spelled}].len as i32 + v[{spelled}][{length - 1}] as i32\n")


POSITIONS = {"return": _in_return, "let": _in_let, "condition": _in_condition}


def _program(box, holder, position, rng):
    ty, setup = BOXES[box]
    spelled, length, _ = RANGES[rng]
    body = POSITIONS[position](spelled, length)
    if holder == "param":
        return (f"{HEADER}fn f(v: {ty}) -> i32\n{body}\n"
                f"pub fn main() -> i32\n{setup}    return f(v)\n")
    return f"{HEADER}pub fn main() -> i32\n{setup}{body}"


@pytest.mark.integration
@pytest.mark.parametrize("rng", sorted(RANGES))
@pytest.mark.parametrize("position", sorted(POSITIONS))
@pytest.mark.parametrize("holder", ["param", "local"])
@pytest.mark.parametrize("box", sorted(BOXES))
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_slice_read_in_place(run_with, compiler, box, holder, position, rng):
    _, length, last = RANGES[rng]
    assert run_with(compiler, "inplace", _program(box, holder, position, rng)) == length + last


# The element read off `v[1..3]` is at the element's own stride, and an element
# that is a struct takes a field: `v[1..3][1].b`.  A byte stride or the slice's
# own header would read something else.
ELEMS = {
    "i8": ("i8", "{n}", ""),
    "i64": ("i64", "{n}", ""),
    "struct": ("P", "P {{ a: 1, b: {n} }}", ".b"),
}


def _elem_program(box, elem, holder):
    ty, make, field = ELEMS[elem]
    vals = [make.format(n=n) for n in (10, 20, 30, 40)]
    if box == "Vec":
        setup = (f"    var v: Vec<{ty}> = vec_new<{ty}>()\n"
                 + "".join(f"    v.push({x})\n" for x in vals))
    else:
        setup = (f"    var a: [4]{ty} = [{', '.join(vals)}]\n"
                 f"    var v: Span<{ty}> = span_from_ptr<{ty}>(@a[0], 4)\n")
    body = (f"    return v[1..3].len as i32 + v[1..3][1]{field} as i32"
            f" + v[1..=3][2]{field} as i32\n")
    struct = "struct P\n    a: i32\n    b: i64\n\n"
    if holder == "param":
        return (f"{HEADER}{struct}fn f(v: {box}<{ty}>) -> i32\n{body}\n"
                f"pub fn main() -> i32\n{setup}    return f(v)\n")
    return f"{HEADER}{struct}pub fn main() -> i32\n{setup}{body}"


@pytest.mark.integration
@pytest.mark.parametrize("holder", ["param", "local"])
@pytest.mark.parametrize("elem", sorted(ELEMS))
@pytest.mark.parametrize("box", sorted(BOXES))
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_element_of_a_slice_in_place(run_with, compiler, box, elem, holder):
    assert run_with(compiler, "elem", _elem_program(box, elem, holder)) == 2 + 30 + 40


# The ticket's program, verbatim.
TICKET = """\
import ritzlib.span
fn f(v: Span<i32>) -> i32
    return v[1..3].len as i32 + v[1..3][1] as i32
pub fn main() -> i32
    var a: [4]i32 = [10, 20, 30, 40]
    return f(span_from_ptr<i32>(@a[0], 4))
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_tickets_program(run_with, compiler):
    assert run_with(compiler, "ticket", TICKET) == 32
