"""AGAST #2412: three forms ritz0 ran that ritz1 turned into invalid IR or a link error.

    w.s = "ab"          # s: StrView.  Stored a %Span$u8 as a %StrView
    v.push(1.5)         # v: Vec<f32>.  Passed the literal's double as a float
    v.push(a)           # in fn mk<T>, v: Vec<T>.  Called Vec$i32_push, never defined

A bare "..." is a %Span$u8, and a StrView field's store rebuilds it, as a struct
literal's does.  `v.push(..)` is a UFCS call to vec_push$f32, whose `item: T` is
f32 by then: its argument is coerced like a free call's.  And monomorph walks a
one-parameter specialisation's body, as it walks a two-parameter one's, so a
method on a local that `T` made concrete registers its helper.

Each row is one store or call path.  A program returns 0, or the number of the
first check that failed.
"""

import pytest

from test_ritz1_for_header import GVEC, compile_with, run_with  # noqa: F401 (fixtures)
from test_ritz1_for_iterable import COMPILERS, MAIN

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = pytest.mark.batched

W = "struct W\n    k: i32\n    s: StrView\n\n"
O = "struct O\n    n: i32\n    w: W\n\n"
# "ab", read back through the field it was stored in.
AB = "if {f}.len != 2\n    return 1\nif {f}.ptr[0] != 97 or {f}.ptr[1] != 98\n    return 2\nreturn 0\n"


def _body(text: str) -> str:
    return "".join("    " + line + "\n" for line in text.splitlines())


VIEW_STORES = {
    # STMT_LOCAL_FIELD_ASSIGN's struct arm.
    "local_field": W + MAIN + "    var w: W\n    w.s = \"ab\"\n" + _body(AB.format(f="w.s")),
    # Through a pointer: the same arm, from the loaded pointer.
    "field_through_pointer": (W + MAIN + "    var w: W\n    var p: *W = @w\n    p.s = \"ab\"\n"
                              + _body(AB.format(f="w.s"))),
    # emit_assign's EXPR_MEMBER struct arm.
    "nested_field": (W + O + MAIN + "    var o: O\n    o.w.s = \"ab\"\n"
                     + _body(AB.format(f="o.w.s"))),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(VIEW_STORES))
def test_a_string_literal_stores_into_a_strview_field(run_with, compiler, name):  # noqa: F811
    assert run_with(compiler, name, VIEW_STORES[name]) == 0


# (element type, pushed literals, their sum).  A literal passed at the wrong
# width is invalid IR; one passed unconverted reads back as a different number.
PUSHES = {
    "float_literal_to_f32": ("f32", ("1.5", "2.25"), "3.75"),
    "int_literal_to_f32": ("f32", ("2", "3"), "5.0"),
    # Already the param's width: passed as it is.
    "float_literal_to_f64": ("f64", ("1.5", "2.25"), "3.75"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PUSHES))
def test_push_coerces_a_literal_to_the_element(run_with, compiler, name):  # noqa: F811
    ty, values, total = PUSHES[name]
    program = (GVEC + MAIN + f"    var v: Vec<{ty}> = vec_new<{ty}>()\n"
               + "".join(f"    v.push({x})\n" for x in values)
               + _body(f"if v.len != {len(values)}\n    return 1\n"
                       f"var t: {ty} = 0.0\nvar i: i64 = 0\nwhile i < v.len\n"
                       f"    t = t + v[i]\n    i = i + 1\n"
                       f"if t != {total}\n    return 2\nreturn 0\n"))
    assert run_with(compiler, name, program) == 0


# `v.push(a)` in a generic fn, instantiated at a scalar and at a struct.  Read
# with a `for`: ritz0 only compiles the push when something else instantiates
# vec_push$T, as a `for` over the result does (AGAST #2944).
GENERIC = ("fn mk<T>(a: T, b: T) -> Vec<T>\n    var v: Vec<T> = vec_new<T>()\n"
           "    v.push(a)\n    v.push(b)\n    return v\n\n")
P = "struct P\n    x: i64\n    y: i64\n\n"
GENERIC_ROWS = {
    "scalar": (GENERIC + MAIN + "    var t: i32 = 0\n    for x in mk<i32>(3, 4)\n        t = t + x\n"),
    "struct": (P + GENERIC + MAIN + "    var a: P\n    a.x = 1\n    a.y = 2\n    var b: P\n"
               "    b.x = 3\n    b.y = 1\n    var t: i64 = 0\n    for q in mk<P>(a, b)\n"
               "        t = t + q.x + q.y\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(GENERIC_ROWS))
def test_push_in_a_generic_fn_links(run_with, compiler, name):  # noqa: F811
    program = GVEC + GENERIC_ROWS[name] + _body("if t != 7\n    return 1\nreturn 0\n")
    assert run_with(compiler, name, program) == 0


# Nothing but the generic fn pushes: the case ritz0 can't compile yet (#2944).
@pytest.mark.integration
@pytest.mark.parametrize("compiler", [c for c in COMPILERS if c != "ritz0"])
def test_push_in_a_generic_fn_is_its_only_push(run_with, compiler):  # noqa: F811
    program = (GVEC + GENERIC + MAIN + "    let v: Vec<i32> = mk<i32>(3, 4)\n"
               + _body("if v.len != 2\n    return 1\nif v[0] + v[1] != 7\n    return 2\nreturn 0\n"))
    assert run_with(compiler, "only_push", program) == 0
