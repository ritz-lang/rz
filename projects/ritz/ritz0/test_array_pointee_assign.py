#!/usr/bin/env python3
"""An address assigned to a `*[N]T` local is checked against N (AGAST #3636).

    var g: [4]i32
    var r: *[3]i32 = null
    r = @g          # ritz0: refused at 4:9. ritz1: compiled, rc 0

A declaration's slot (`let p: *[3]i32 = @g`) and a param's carried the
pointee's N, T and N-D shape, but a pointer local's slot carried only the
shape, so an assignment into it never compared sizes. The N-D form was missed
the same way: `r = @g` into `*[2][3]i32` with `g: [2][4]i32`.

Each refused row runs on ritz0, ritz1 and ritz1_selfhosted, and all three must
report the same `line:col: message`.  The accepted rows, the same sizes on
both sides, keep the check from refusing what fits.
"""

import pytest
from ref_rules import REF_TO_OTHER_TYPE
from test_ref_into_value import COMPILERS, _assert_refused, _ids, _run

pytestmark = pytest.mark.integration

# `^` marks where the error lands: on the address assigned.
REFUSED = {
    "flat_size": "pub fn main() -> i32\n    var g: [4]i32\n    var r: *[3]i32 = null\n    r = ^@g\n    return 0\n",
    "nested_shape": (
        "pub fn main() -> i32\n    var g: [2][4]i32\n    var r: *[2][3]i32 = null\n"
        "    r = ^@g\n    return 0\n"
    ),
    # The same N, another element type.
    "flat_element": "pub fn main() -> i32\n    var g: [3]i64\n    var r: *[3]i32 = null\n    r = ^@g\n    return 0\n",
}

# The same sizes on both sides: these compile and run, returning 42.
ACCEPTED = {
    "flat_size": (
        "pub fn main() -> i32\n    var g: [3]i32\n    g[2] = 42\n    var r: *[3]i32 = null\n"
        "    r = @g\n    return r[2]\n"
    ),
    "nested_shape": (
        "pub fn main() -> i32\n    var g: [2][3]i32\n    g[1][2] = 42\n"
        "    var r: *[2][3]i32 = null\n    r = @g\n    return r[1][2]\n"
    ),
    "pointer_local": (
        "pub fn main() -> i32\n    var g: [3]i32\n    g[1] = 42\n    var q: *[3]i32 = @g\n"
        "    var r: *[3]i32 = null\n    r = q\n    return r[1]\n"
    ),
}


def _params(table):
    for name in _ids(table):
        for compiler in COMPILERS:
            yield pytest.param(name, compiler, id=f"{name}-{compiler}")


@pytest.mark.parametrize("name,compiler", list(_params(REFUSED)))
def test_an_address_of_another_array_is_refused(tmp_path, name, compiler):
    _assert_refused(compiler, tmp_path, name, REFUSED[name], REF_TO_OTHER_TYPE)


@pytest.mark.parametrize("name,compiler", list(_params(ACCEPTED)))
def test_an_address_of_the_same_array_is_taken(tmp_path, name, compiler):
    assert _run(compiler, tmp_path, name, ACCEPTED[name]) == 42
