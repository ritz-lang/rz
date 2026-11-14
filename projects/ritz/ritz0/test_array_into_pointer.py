#!/usr/bin/env python3
"""A whole array where a `*T` goes is refused, located, by all three compilers
(AGAST #2392).

`fn f() -> *i32 / var a: [2]i32 = [1, 2] / return a`: ritz1 and
ritz1_selfhosted refuse the array with its own words, at the array. ritz0's
slot check only refused a value of the pointee's own type, a `:&` param or any
value into an `@T` / `@&T`, so the array fell through to the emitter: a `ret
[2 x i32]` from a `ptr` fn that clang rejects, a Python TypeError for a field,
or a store mismatch for an assignment.

An array into an `@T`, `@&T` or `*[N]T` is the value-into-reference rule's
(test_value_into_ref.py), and an array into a Span is too. What's here is the
array into a `*U` of anything else.

Each row runs on ritz0, ritz1 and ritz1_selfhosted, and all three must report
the same `line:col: message`.
"""

import pytest

from array_rules import WHOLE_ARRAY_NOT_A_VALUE
from ref_rules import VALUE_INTO_SHARED_REF
from test_ref_into_value import COMPILERS, _assert_refused, _ids, _main, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

HEAD = "struct W\n    p: *i32\n\nfn g(p: *i32) -> i32\n    0\n\n"

# `^` marks where the error lands: on the array, whatever the slot.
SITES = {
    "return": "fn f() -> *i32\n    var a: [2]i32 = [1, 2]\n    return ^a\n",
    "tail": "fn f() -> *i32\n    var a: [2]i32 = [1, 2]\n    ^a\n",
    "let": "fn f() -> i32\n    var a: [2]i32 = [1, 2]\n    let p: *i32 = ^a\n    0\n",
    "var": "fn f() -> i32\n    var a: [2]i32 = [1, 2]\n    var p: *i32 = ^a\n    0\n",
    "argument": "fn f() -> i32\n    var a: [2]i32 = [1, 2]\n    g(^a)\n",
    "field": "fn f() -> i32\n    var a: [2]i32 = [1, 2]\n    let w = W { p: ^a }\n    0\n",
    "assign": "fn f(q: *i32) -> i32\n    var a: [2]i32 = [1, 2]\n    var p: *i32 = q\n    p = ^a\n    0\n",
    "field_assign": ("fn f(q: *i32) -> i32\n    var a: [2]i32 = [1, 2]\n    var w = W { p: q }\n"
                     "    w.p = ^a\n    0\n"),
    # Another element type: not `same` either, so the same gap.
    "other_element": "fn f() -> *i32\n    var a: [2]u8 = [1, 2]\n    return ^a\n",
    # A param, not a local, and an array of pointers into a pointer.
    "param": "fn f(a: [2]i32) -> *i32\n    ^a\n",
    "pointer_elements": "fn f(a: [2]*i32) -> *i32\n    return ^a\n",
}

# A `:&` array param is the value-into-reference rule's, on all three: its
# words, not these (test_value_into_ref.py, #2337).
LENT = "fn f(a:& [2]i32) -> *i32\n    return ^a\n"

# What the error's alternatives say, written out: they compile and run.
WRITTEN = {
    "element_address": ("fn f(a: @[2]i32) -> *i32\n    return @a[1]\n",
                        "    var a: [2]i32 = [1, 3]\n    let p = f(@a)\n    *p\n", 3),
    "array_pointer": ("fn f(a: @&[2]i32) -> *[2]i32\n    return a\n",
                      "    var a: [2]i32 = [1, 3]\n    let p = f(@&a)\n    p[1]\n", 3),
    "element_of_pointers": ("fn f(a: [2]*i32) -> *i32\n    return a[1]\n",
                            "    var n: i32 = 3\n    let a: [2]*i32 = [@n, @n]\n    *f(a)\n", 3),
}


def _params(table):
    for name in _ids(table):
        for compiler in COMPILERS:
            yield pytest.param(name, compiler, id=f"{name}-{compiler}")


@pytest.mark.parametrize("site,compiler", list(_params(SITES)))
def test_a_whole_array_never_fits_a_pointer_slot(tmp_path, compiler, site):
    _assert_refused(compiler, tmp_path, site, _main(HEAD + SITES[site], "    0\n"),
                    WHOLE_ARRAY_NOT_A_VALUE)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_lent_array_is_a_value_into_a_reference(tmp_path, compiler):
    _assert_refused(compiler, tmp_path, "lent", _main(LENT, "    0\n"), VALUE_INTO_SHARED_REF)


@pytest.mark.parametrize("name,compiler", list(_params(WRITTEN)))
def test_the_written_forms_still_compile(tmp_path, compiler, name):
    body, entry, want = WRITTEN[name]
    assert _run(compiler, tmp_path, name, _main(body, entry)) == want
