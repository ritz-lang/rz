"""AGAST #2572: a range slice as an enum-variant payload, `Some(v[lo..hi])`.

#2451 rewrites `v[lo..hi]` on a Vec, Span or String local into `v.slice(lo, hi)`,
a method call yielding the `%Vec$T` / `%Span$T` / `%String` aggregate.  ritz1's
variant constructor typed its payload by the expression's form and had no rule
for a method call, so it stored the aggregate as an i64:

    fn wrap(s: Span<u8>) -> Option<Span<u8>>
        Some(s[0..2])       # ritz1: `store i64 %.4`, %.4 a %Span$u8 -> clang error

ritz0 was right throughout.  Each program below builds the variant in a helper
fn's tail and matches it in main, for every constructor (`Some`, `Ok`, `Err`, a
user enum's tuple variant), every box (Vec, Span, `[T]`, String) and both range
spellings.  A whole-value payload (`Some(v)`), already right, is the control.

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

# box -> (its type, how main makes `v` hold 10, 20, 30, 40, t's length spelled for it)
BOXES = {
    "Vec": ("Vec<i32>",
            "    var v: Vec<i32> = vec_new<i32>()\n"
            "    v.push(10)\n    v.push(20)\n    v.push(30)\n    v.push(40)\n",
            "t.len"),
    "Span": ("Span<i32>",
             "    var a: [4]i32 = [10, 20, 30, 40]\n"
             "    var v: Span<i32> = span_from_ptr<i32>(@a[0], 4)\n",
             "t.len"),
    # `[i32]` is `Span<i32>` (#1614): `-> Option<[i32]>` must come for free.
    "Slice": ("[i32]",
              "    var a: [4]i32 = [10, 20, 30, 40]\n"
              "    var v: Span<i32> = span_from_ptr<i32>(@a[0], 4)\n",
              "t.len"),
    "String": ("String",
               "    var v: String\n    v.data = vec_new<u8>()\n"
               "    v.data.push(10)\n    v.data.push(20)\n    v.data.push(30)\n    v.data.push(40)\n",
               "t.data.len"),
}

# name -> (range, length, last element).  An off-by-one in `..=` moves both.
RANGES = {"exclusive": ("1..3", 2, 30), "inclusive": ("1..=2", 2, 30),
          "inclusive_to_the_end": ("1..=3", 3, 40)}

# ctor -> (return type with {T} for the box, the constructor, main's pattern)
CTORS = {
    "Some": ("Option<{T}>", "Some", "Some"),
    "Ok": ("Result<{T}, i32>", "Ok", "Ok"),
    "Err": ("Result<i32, {T}>", "Err", "Err"),
    "user_enum": ("Got", "Hit", "Hit"),
}


def _program(box: str, ctor: str, payload: str, body: str) -> str:
    ty, setup, _ = BOXES[box]
    ret, make, pat = CTORS[ctor]
    return (f"{HEADER}enum Got\n    Hit({ty})\n    Miss\n\n"
            f"fn wrap(v: {ty}) -> {ret.format(T=ty)}\n    {make}({payload})\n\n"
            f"pub fn main() -> i32\n{setup}"
            f"    match wrap(v)\n        {pat}(t) => {body}\n        _ => 1\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("rng", sorted(RANGES))
@pytest.mark.parametrize("ctor", sorted(CTORS))
@pytest.mark.parametrize("box", sorted(BOXES))
def test_a_slice_payload(run_with, box, ctor, rng, compiler):
    """The payload is the slice: its length and its last element come back."""
    spelled, length, last = RANGES[rng]
    _, _, length_of = BOXES[box]
    body = f"{length_of} as i32 + t[{length - 1}] as i32"
    program = _program(box, ctor, f"v[{spelled}]", body)
    assert run_with(compiler, "slice", program) == length + last


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ctor", sorted(CTORS))
@pytest.mark.parametrize("box", sorted(BOXES))
def test_a_whole_value_payload(run_with, box, ctor, compiler):
    """Control: `Some(v)`, the box itself, was already right."""
    _, _, length_of = BOXES[box]
    program = _program(box, ctor, "v", f"{length_of} as i32 + t[3] as i32")
    assert run_with(compiler, "whole", program) == 44
