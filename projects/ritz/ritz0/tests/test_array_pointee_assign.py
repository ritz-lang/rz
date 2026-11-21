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

A pointer *value* of another pointee (LARB R71, AGAST #3684) is refused the
same way at a `let`, an assignment, an argument and a `return`: `*[4]i32`
into `*[3]i32`, another element type, `*C` into `*D`, `@C` into `@D`. Those
rows run on ritz0 only until ritz1's half lands (#3999). The byte pointer is
the way between, so `*[3]i32` through a `*u8` and back runs on all three.
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

# A pointer value of another pointee (LARB R71). ritz0 only: ritz1's is #3999.
_STRUCTS = "struct C\n    x: i32\n\nstruct D\n    y: i64\n\n"
VALUE_REFUSED = {
    "let_size": (
        "pub fn main() -> i32\n    var g: [4]i32\n    var q: *[4]i32 = @g\n"
        "    let r: *[3]i32 = ^q\n    return 0\n"
    ),
    "assign_element": (
        "pub fn main() -> i32\n    var g: [3]i64\n    var q: *[3]i64 = @g\n"
        "    var r: *[3]i32 = null\n    r = ^q\n    return 0\n"
    ),
    "argument_size": (
        "fn f(p: *[3]i32) -> i32\n    0\n\npub fn main() -> i32\n    var g: [4]i32\n"
        "    var q: *[4]i32 = @g\n    return f(^q)\n"
    ),
    # Into an `@U` param, only a sign apart: the emitter's pointer types match.
    "argument_sign_reference": (
        "fn f(p: @u32) -> i32\n    0\n\npub fn main() -> i32\n    var n: i32 = 1\n"
        "    let q: @i32 = @n\n    return f(^q)\n"
    ),
    "return_size": "fn f(p: *[4]i32) -> *[3]i32\n    return ^p\n\npub fn main() -> i32\n    return 0\n",
    "let_struct": (
        _STRUCTS + "pub fn main() -> i32\n    var c = C { x: 3 }\n    let p: *C = @c\n"
        "    let q: *D = ^p\n    return 0\n"
    ),
    "let_shared_ref": (
        _STRUCTS + "pub fn main() -> i32\n    var c = C { x: 3 }\n    let p: @C = @c\n"
        "    let q: @D = ^p\n    return 0\n"
    ),
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
    # LARB R71's byte pointer: any `*T` into `*u8`, and a `*u8` into any `*T`.
    "through_bytes": (
        "pub fn main() -> i32\n    var g: [3]i32\n    g[2] = 42\n    var q: *[3]i32 = @g\n"
        "    let b: *u8 = q\n    let r: *[3]i32 = b\n    return r[2]\n"
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


@pytest.mark.parametrize("name", _ids(VALUE_REFUSED))
def test_a_pointer_value_of_another_pointee_is_refused(tmp_path, name):
    _assert_refused("ritz0", tmp_path, name, VALUE_REFUSED[name], REF_TO_OTHER_TYPE)


def test_a_struct_pointer_at_a_call_keeps_its_wrong_type_words(tmp_path):
    """`f(p)` with `p: *C` into `*D`: #1948's words, which ritz1 says too,
    not R71's. R71 doesn't pre-empt it, as for `@c` (_check_other_referent)."""
    marked = (
        _STRUCTS + "fn f(p: *D) -> i32\n    0\n\npub fn main() -> i32\n    var c = C { x: 3 }\n"
        "    let p: *C = @c\n    return f(^p)\n"
    )
    _assert_refused("ritz0", tmp_path, "call_struct", marked,
                    "argument 1 of `f` has the wrong type: *C != *D")


# AGAST #1387: what the checker leaves to the emitter at a call, a struct
# pointer the emitter can't trace to a local (here a call's result), reached
# _convert_type's blanket bitcast and compiled. R71 lets that bitcast make a
# `*u8` of a pointer or a pointer of a `*u8`, nothing else: any other pointer
# goes to the call unconverted, and #1366's wrapper names the argument. A
# call through a fn pointer is the checker's (R71's words), so has no row.
_GIVE_C = _STRUCTS + "fn give(c: *C) -> *C\n    c\n\n"
CALL_REFUSED = {
    "direct": (
        _GIVE_C + "fn f(p: *D) -> i32\n    0\n\npub fn main() -> i32\n"
        "    var c = C { x: 3 }\n    return f(^give(@c))\n",
        "argument 1 of `f` has the wrong type: *C != *D",
    ),
    "method": (
        _GIVE_C + "impl C\n    fn take(self: @C, p: *D) -> i32\n        0\n\n"
        "pub fn main() -> i32\n    var c = C { x: 3 }\n    return c.take(^give(@c))\n",
        "argument 2 of `take` has the wrong type: *C != *D",
    ),
    "static_method": (
        _GIVE_C + "impl D\n    fn mk(p: *D) -> i32\n        0\n\n"
        "pub fn main() -> i32\n    var c = C { x: 3 }\n    return D.mk(^give(@c))\n",
        "argument 1 of `mk` has the wrong type: *C != *D",
    ),
}

# The byte pointer both ways, and a cast, still convert at a call: 42.
CALL_ACCEPTED = {
    "into_bytes": (
        _GIVE_C + "fn f(p: *u8) -> i32\n    let q: *C = p\n    q.x\n\n"
        "pub fn main() -> i32\n    var c = C { x: 42 }\n    return f(give(@c))\n"
    ),
    "from_bytes": (
        _STRUCTS + "fn bytes(c: *C) -> *u8\n    c\n\nfn f(p: *C) -> i32\n    p.x\n\n"
        "pub fn main() -> i32\n    var c = C { x: 42 }\n    return f(bytes(@c))\n"
    ),
    "cast": (
        _GIVE_C + "fn f(p: *D) -> i32\n    42\n\npub fn main() -> i32\n"
        "    var c = C { x: 3 }\n    return f(give(@c) as *D)\n"
    ),
}


@pytest.mark.parametrize("name", _ids(CALL_REFUSED))
def test_a_call_argument_pointer_is_not_bitcast(tmp_path, name):
    marked, message = CALL_REFUSED[name]
    _assert_refused("ritz0", tmp_path, name, marked, message)


@pytest.mark.parametrize("name", _ids(CALL_ACCEPTED))
def test_a_call_argument_byte_pointer_converts(tmp_path, name):
    assert _run("ritz0", tmp_path, name, CALL_ACCEPTED[name]) == 42
