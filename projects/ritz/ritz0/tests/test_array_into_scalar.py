"""A whole array at a scalar return slot or as a cast's source is refused,
located, by ritz0 (AGAST #3187, #3190).

`fn f() -> i64 / return [1, 2]` and `return [1, 2] as i32` compiled to a
`ret [2 x i64]` in an i64 / i32 fn, which clang rejects; so did `return a` of a
named array, a `:&` param's included (#3190), and `a as i32`. ritz1 refuses
them at the same column (#3014's "no `[N]T` slot" for a literal, "a whole
array is not a value" for a named one), all but the `:&` param, which it
reads as its address (#2322, test_ritz1_borrow_array.py's LAX). ritz0 already refused the same array into a
`var x: i64` (a store mismatch) and into a `*T` (#2392,
test_array_into_pointer.py): here it says #2392's words, at the array.

A scalar is a number or a bool. An array into a pointer or reference, a Span,
or an array of another element type has its own rule and words, and a cast to
`bool` its own error too; none of those changes here.

ritz0 only: ritz1's literal wording differs, and its refusals are its own
tests' (test_ritz1_untyped_scalar_array_let.py, test_ritz1_borrow_array.py).
"""

import pytest
from array_rules import WHOLE_ARRAY_NOT_A_VALUE
from test_ref_into_value import _assert_refused, _main, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

HEAD = "struct W\n    a: [2]i32\n\n"

# `^` marks where the error lands: on the array, whatever the slot.
RETURNS = {
    # The ticket's program, a fill, and a tail.
    "literal": "fn f() -> i64\n    return ^[1, 2]\n",
    "fill": "fn f() -> i64\n    return ^[0; 2]\n",
    "literal_tail": "fn f() -> i64\n    ^[1, 2]\n",
    # A named array: a local, a by-value param, a `:&` param (#3190), a field.
    "local": "fn f() -> i64\n    var a: [2]i32 = [1, 3]\n    return ^a\n",
    "param_tail": "fn f(a: [2]i32) -> i32\n    ^a\n",
    "lent": "fn f(a:& [2]i32) -> i64\n    return ^a\n",
    "field": "fn f(w: W) -> i32\n    return ^w.a\n",
    # The slot reaches an `if` arm's tail, and a float slot is a scalar too.
    "if_arm_tail": "fn f(c: bool) -> f64\n    if c\n        ^[1.5, 2.5]\n    else\n        0.5\n",
    "bool": "fn f() -> bool\n    var a: [2]bool = [true, false]\n    return ^a\n",
}

CASTS = {
    # The ticket's second program.
    "literal": "fn f() -> i32\n    return ^[1, 2] as i32\n",
    "local": "fn f() -> i32\n    var a: [2]i32 = [1, 3]\n    let x: i64 = ^a as i64\n    0\n",
    # test_ritz1_borrow_array.py's LAX `cast_to_integer`, now at the array.
    "lent": "fn f(a:& [2]i32) -> i64\n    let x: i64 = ^a as i64\n    x\n",
    "to_float": "fn f() -> f64\n    var a: [2]f64 = [1.5, 2.5]\n    return ^a as f64\n",
}

# What the error's alternatives say, and the array slots beside these: they
# compile and run.
WRITTEN = {
    "array_return": ("fn f() -> [2]i64\n    return [1, 2]\n",
                     "    let a = f()\n    (a[0] + a[1]) as i32\n", 3),
    "element_return": ("fn f(a:& [2]i32) -> i64\n    return a[1] as i64\n",
                       "    var a: [2]i32 = [1, 3]\n    f(@&a) as i32\n", 3),
    "element_cast": ("fn f() -> i32\n    var a: [2]i64 = [1, 3]\n    return a[1] as i32\n",
                     "    f()\n", 3),
    "array_tail": ("fn f(a: [2]i32) -> [2]i32\n    a\n",
                   "    let a = f([1, 2])\n    a[0] + a[1]\n", 3),
}


@pytest.mark.parametrize("site", sorted(RETURNS))
def test_a_whole_array_never_fits_a_scalar_return(tmp_path, site):
    _assert_refused("ritz0", tmp_path, f"return_{site}", _main(HEAD + RETURNS[site], "    0\n"),
                    WHOLE_ARRAY_NOT_A_VALUE)


@pytest.mark.parametrize("site", sorted(CASTS))
def test_a_whole_array_never_casts_to_a_scalar(tmp_path, site):
    _assert_refused("ritz0", tmp_path, f"cast_{site}", _main(HEAD + CASTS[site], "    0\n"),
                    WHOLE_ARRAY_NOT_A_VALUE)


@pytest.mark.parametrize("name", sorted(WRITTEN))
def test_the_written_forms_still_compile(tmp_path, name):
    body, entry, want = WRITTEN[name]
    assert _run("ritz0", tmp_path, name, _main(body, entry)) == want
