"""AGAST #2573: a slice of a match-pattern binding, `Some(x) => x[1..3]`.

#2451 rewrites `v[lo..hi]` on a Vec, Span or String into `v.slice(lo, hi)`, but
only for a name monomorph has recorded as one: a param or a let.  A pattern
binding (`Some(x)`, `Ok(x)`, `Err(x)`, a user enum's `Hit(x)`) was never
recorded, so its slice fell to index_through's located refusal on ritz1:

    match wrap(v)
        Some(x) => x[1..3]   # ritz1: "this slice of a Vec, Span or String isn't
                             #         lowered by ritz1 (`let t = v[lo..hi]` is)"

The binding takes the payload's type, for that arm only.  Each program below
matches a helper's variant, as the arm's value, through a `let` in the arm and
through a `return` in the arm, with the scrutinee a call and a local.

ritz0 is the oracle: every expected status is what ritz0 returns.
"""

import pytest

import test_ritz1_for_header as for_header
import test_slice_value_local as slice_local
from test_index_through_reference import HEADER

# #2451's fixtures: compile, link with gvec/span/string, run.
compile_with = for_header.compile_with
run_with = slice_local.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# ritz0's monomorph types a pattern binding by its payload, per arm (#2725), so
# a pattern-bound Vec's slice instantiates vec_slice<T> on every compiler.


def _cells(boxes):
    """(box, compiler) pairs."""
    return [(b, c) for b in boxes for c in COMPILERS]

# box -> (its type, how main makes `v` hold 10, 20, 30, 40, an empty one,
#         t's length, t's element {k}).  A String's element is read through
#         its bytes: ritz0 indexes a String only when it's a let's own slice
#         (#2779), and that isn't what this tests.
BOXES = {
    "Vec": ("Vec<i32>",
            "    var v: Vec<i32> = vec_new<i32>()\n"
            "    v.push(10)\n    v.push(20)\n    v.push(30)\n    v.push(40)\n",
            "vec_new<i32>()", "t.len", "t[{k}]"),
    "Span": ("Span<i32>",
             "    var a: [4]i32 = [10, 20, 30, 40]\n"
             "    var v: Span<i32> = span_from_ptr<i32>(@a[0], 4)\n",
             "span_empty<i32>()", "t.len", "t[{k}]"),
    "String": ("String",
               "    var v: String\n    v.data = vec_new<u8>()\n"
               "    v.data.push(10)\n    v.data.push(20)\n    v.data.push(30)\n    v.data.push(40)\n",
               "string_new()", "t.data.len", "*(t.data.data + {k})"),
}

# name -> (range, length, last element).  An off-by-one in `..=` moves both.
RANGES = {"exclusive": ("1..3", 2, 30), "inclusive": ("1..=3", 3, 40)}

# ctor -> (return type with {T} for the box, the constructor, main's pattern)
CTORS = {
    "Some": ("Option<{T}>", "Some", "Some"),
    "Ok": ("Result<{T}, i32>", "Ok", "Ok"),
    "Err": ("Result<i32, {T}>", "Err", "Err"),
    "user_enum": ("Got", "Hit", "Hit"),
}

# How main names what it matches: the call itself, or a local holding it.
SCRUTINEES = {"call": ("", "wrap(v)"), "local": ("    let o = wrap(v)\n", "o")}


def _answer(box: str, length: int) -> str:
    _, _, _, length_of, element = BOXES[box]
    return f"{length_of} as i32 + {element.format(k=length - 1)} as i32"


# Where in the arm the slice is: its value, a `let`, a `return`.
def _arm_value(box, pat, scrut, spelled, length):
    return (f"    let t = match {scrut}\n"
            f"        {pat}(x) => x[{spelled}]\n"
            f"        _ => {BOXES[box][2]}\n"
            f"    return {_answer(box, length)}\n")


def _let_in_arm(box, pat, scrut, spelled, length):
    return (f"    match {scrut}\n"
            f"        {pat}(x) =>\n"
            f"            let t = x[{spelled}]\n"
            f"            return {_answer(box, length)}\n"
            f"        _ => return 1\n"
            f"    return 2\n")


POSITIONS = {"arm_value": _arm_value, "let_in_arm": _let_in_arm}


def _program(box: str, ctor: str, scrutinee: str, position: str, rng: str) -> str:
    ty, setup, _, _, _ = BOXES[box]
    ret, make, pat = CTORS[ctor]
    bind, scrut = SCRUTINEES[scrutinee]
    spelled, length, _ = RANGES[rng]
    body = POSITIONS[position](box, pat, scrut, spelled, length)
    return (f"{HEADER}enum Got\n    Hit({ty})\n    Miss\n\n"
            f"fn wrap(v: {ty}) -> {ret.format(T=ty)}\n    {make}(v)\n\n"
            f"pub fn main() -> i32\n{setup}{bind}{body}")


@pytest.mark.integration
@pytest.mark.parametrize("rng", sorted(RANGES))
@pytest.mark.parametrize("position", sorted(POSITIONS))
@pytest.mark.parametrize("scrutinee", sorted(SCRUTINEES))
@pytest.mark.parametrize("ctor", sorted(CTORS))
@pytest.mark.parametrize("box,compiler", _cells(sorted(BOXES)))
def test_a_slice_of_a_pattern_binding(run_with, box, ctor, scrutinee, position, rng, compiler):
    """The slice of the payload: its length and its last element come back."""
    _, length, last = RANGES[rng]
    program = _program(box, ctor, scrutinee, position, rng)
    assert run_with(compiler, "pat", program) == length + last


# The slice used in place, never bound: `return x[1..3].len + x[1..3][1]`.
# ritz1 typed no member of it until #2726 (test_slice_in_place_member.py).
@pytest.mark.integration
@pytest.mark.parametrize("ctor", sorted(CTORS))
@pytest.mark.parametrize("box,compiler", _cells(("Span", "Vec")))
def test_a_slice_of_a_pattern_binding_returned(run_with, box, ctor, compiler):
    ty, setup, _, _, _ = BOXES[box]
    ret, make, pat = CTORS[ctor]
    program = (f"{HEADER}enum Got\n    Hit({ty})\n    Miss\n\n"
               f"fn wrap(v: {ty}) -> {ret.format(T=ty)}\n    {make}(v)\n\n"
               f"pub fn main() -> i32\n{setup}"
               f"    match wrap(v)\n"
               f"        {pat}(x) =>\n"
               f"            return x[1..3].len as i32 + x[1..3][1] as i32\n"
               f"        _ => return 1\n"
               f"    return 2\n")
    assert run_with(compiler, "ret", program) == 32


# Two arms bind the same name at different types: each slice is its own arm's.
# A binding that outlived its arm would make the second `x` the first's, and a
# `Vec<i64>` arm would instantiate vec_slice$i32 rather than its own.
SECOND = {
    "Span<i32>": "    var a: [4]i32 = [50, 60, 70, 80]\n"
                 "    var s: Span<i32> = span_from_ptr<i32>(@a[0], 4)\n",
    "Vec<i64>": "    var s: Vec<i64> = vec_new<i64>()\n"
                "    s.push(50)\n    s.push(60)\n    s.push(70)\n    s.push(80)\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("second", sorted(SECOND))
@pytest.mark.parametrize("first", ["A", "B"])
def test_a_binding_is_its_own_arms(run_with, first, second, compiler):
    program = (f"{HEADER}enum Two\n    A(Vec<i32>)\n    B({second})\n\n"
               f"fn pick(v: Vec<i32>, s: {second}, a: i32) -> Two\n"
               "    if a == 1\n        return A(v)\n    B(s)\n\n"
               "fn len_of(w: Two) -> i32\n"
               "    match w\n"
               "        A(x) =>\n"
               "            let t = x[0..3]\n"
               "            return t.len as i32 + t[2] as i32\n"
               "        B(x) =>\n"
               "            let t = x[1..2]\n"
               "            return t.len as i32 + t[0] as i32\n"
               "    return 0\n\n"
               "pub fn main() -> i32\n"
               "    var v: Vec<i32> = vec_new<i32>()\n"
               "    v.push(10)\n    v.push(20)\n    v.push(30)\n    v.push(40)\n"
               f"{SECOND[second]}"
               f"    return len_of(pick(v, s, {1 if first == 'A' else 0}))\n")
    assert run_with(compiler, "own", program) == (33 if first == "A" else 61)


# The ticket's program, verbatim: `Some(x) => x[1..3]` over a `[4]u8`.
TICKET = """\
import ritzlib.span
fn wrap(s: Span<u8>) -> Option<Span<u8>>
    Some(s)
pub fn main() -> i32
    let b: [4]u8 = [1, 2, 3, 4]
    let inner = match wrap(@b)
        Some(x) => x[1..3]
        None => span_empty<u8>()
    return inner.len as i32 * 10 + inner[0] as i32
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_tickets_program(run_with, compiler):
    assert run_with(compiler, "ticket", TICKET) == 22



# Result's T is as many mangled components as its type takes (`Result$Span$u8$i32`
# is T = `Span$u8`): a Span with no ritzlib.span, which names no template to
# count from, and an Option or Result in T, ahead of the Err payload.
NESTED = {
    "span_u8_no_import": ("", "Result<[u8], i32>", "Ok",
                          "    let b: [4]u8 = [1, 2, 3, 4]\n", "@b"),
    "option_in_ok": ("import ritzlib.span\n", "Result<Option<i32>, Span<u8>>", "Err",
                     "    let b: [4]u8 = [1, 2, 3, 4]\n", "@b"),
    "result_in_ok": ("import ritzlib.span\n", "Result<Result<i32, i64>, Span<u8>>", "Err",
                     "    let b: [4]u8 = [1, 2, 3, 4]\n", "@b"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("nested", sorted(NESTED))
def test_a_result_payload_after_a_nested_type(run_with, nested, compiler):
    imports, ret, ctor, setup, arg = NESTED[nested]
    program = (f"{imports}fn wrap(s: Span<u8>) -> {ret}\n    {ctor}(s)\n\n"
               f"pub fn main() -> i32\n{setup}"
               f"    match wrap({arg})\n"
               f"        {ctor}(x) =>\n"
               f"            let t = x[1..3]\n"
               f"            return t.len as i32 * 10 + t[1] as i32\n"
               f"        _ => return 1\n"
               f"    return 2\n")
    assert run_with(compiler, "nested", program) == 23


# An open end, `x[1:]`: ritz0 takes the end from vec_len<T>, named by the same
# element type as vec_slice<T> when the binding's Vec<T> is unmangled (#2725).
# ritz0 only: `x[1:]` is ritz0's colon slice, which ritz1 doesn't parse.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0"])
@pytest.mark.parametrize("ctor", sorted(CTORS))
def test_an_open_ended_slice_of_a_pattern_binding(run_with, ctor, compiler):
    ty, setup, _, _, _ = BOXES["Vec"]
    ret, make, pat = CTORS[ctor]
    program = (f"{HEADER}enum Got\n    Hit({ty})\n    Miss\n\n"
               f"fn wrap(v: {ty}) -> {ret.format(T=ty)}\n    {make}(v)\n\n"
               f"pub fn main() -> i32\n{setup}"
               f"    match wrap(v)\n"
               f"        {pat}(x) =>\n"
               f"            let t = x[1:]\n"
               f"            return t.len as i32 + t[2] as i32\n"
               f"        _ => return 1\n"
               f"    return 2\n")
    assert run_with(compiler, "open", program) == 43
