"""AGAST #2532: `let r = @q` with `q: *T` is a `**T`, and ritz1 forgot the T.

    var x: [3]i16       # 1, 2, 3
    var q: *i16 = @x[0]
    let r = @q
    **r = 7             # ritz1: `store i64`, x[1] overwritten
    if **r == 7         # ritz1: `load i64`

infer_ref_to_pointer_let typed `let r = @q` only when q's pointee was a struct
(#2372).  A scalar `*T` left `r` an i64 with no pointee, so both derefs guessed
8 bytes.  #2376 fixed the array-element form (`let r = @a[i]`), pinned in
test_ritz1_array_ptr_element.py; this is the plain-local form.

The exit code is the low byte, so `return **r as i32` can't see a wide load.
Every check compares the whole value, and every store checks its neighbour.
Expected values come from the program; ritz0 agrees on every row.
"""

import pytest

from test_ritz1_array_ptr_element import COMPILERS, RITZ1S, SCALARS, run_with  # noqa: F401  (fixture)

# 1-3 load, 4-5 store, 6-7 compound, 8 the value a `let` copies out.  `{amp}` is
# `@` or `@&`, `x` the three scalars, and q points at x[0].
_CHECKS = """\
    let r = {amp}q
    if **r != {v0}
        return 1
    if *(*r + 1) != {v1}
        return 2
    if *(*r + 2) != {v2}
        return 3
    **r = {v3}
    if x[0] != {v3}
        return 4
    if x[1] != {v1}
        return 5
    let v = **r
    if v != {v3}
        return 6
    return 0
"""

_FILL = """\
    var x: [3]{t}
    x[0] = {v0}
    x[1] = {v1}
    x[2] = {v2}
"""

# How q comes to hold @x[0].  `param` is a `q: *T` parameter, not a local.
SOURCES = {
    "local": "pub fn main() -> i32\n" + _FILL + "    var q: *{t} = @x[0]\n" + _CHECKS,
    "param": (
        "fn f(q: *{t}, x: *{t}) -> i32\n"
        + _CHECKS
        + "\n"
        + "pub fn main() -> i32\n"
        + _FILL
        + "    return f(@x[0], @x[0])\n"
    ),
}


def _program(source: str, amp: str, ty: str) -> str:
    v0, v1, v2, v3 = SCALARS[ty]
    return SOURCES[source].format(amp=amp, t=ty, v0=v0, v1=v1, v2=v2, v3=v3)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(SCALARS))
@pytest.mark.parametrize("amp", ["@", "@&"], ids=["shared", "mut"])
@pytest.mark.parametrize("source", sorted(SOURCES))
def test_reference_to_a_scalar_pointer(run_with, source, amp, ty, compiler):
    name = f"{source}_{'mut' if amp == '@&' else 'shared'}_{ty}"
    assert run_with(compiler, name, _program(source, amp, ty)) == 0


_X = "pub fn main() -> i32\n    var x: [3]i16\n    x[0] = 1\n    x[1] = 2\n    x[2] = 3\n"


def _is(expr: str, want: str) -> str:
    return f"    if {expr} == {want}\n        return 0\n    return 1\n"


# The ticket's program and the shapes around it, all on i16.
SHAPES = {
    "ticket_store": _X
    + "    var q: *i16 = @x[0]\n    let r = @q\n    **r = 7\n"
    + _is("x[1]", "2"),
    "ticket_load": _X
    + "    var q: *i16 = @x[0]\n    let r = @q\n    **r = 7\n"
    + _is("**r", "7"),
    "compound": _X
    + "    var q: *i16 = @x[0]\n    let r = @q\n    x[0] = -1\n    **r += 1\n"
    + _is("x[1]", "2"),
    "var_binding": _X
    + "    var q: *i16 = @x[0]\n    var r = @q\n    **r = 7\n"
    + _is("x[1]", "2"),
    # `*r` is q itself: moving it through r moves q.
    "replace_through": _X
    + "    var q: *i16 = @x[0]\n    let r = @&q\n    *r = @x[2]\n"
    + _is("*q", "3"),
    # `q: **i16`: `r` is a `***i16`, three levels to the i16.
    "three_levels": _X
    + "    var p: *i16 = @x[0]\n    var q: **i16 = @p\n    let r = @q\n    ***r = 7\n"
    + "    if x[1] != 2\n        return 2\n"
    + _is("***r", "7"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(SHAPES))
def test_reference_to_pointer_shape(run_with, name, compiler):
    assert run_with(compiler, name, SHAPES[name]) == 0


# AGAST #2537: `(*r)[i]` with `r: **T` loads one byte on ritz1 whatever T is,
# annotated or inferred, and is invalid IR on a float.  Not this ticket's.
@pytest.mark.integration
@pytest.mark.parametrize(
    "compiler",
    [
        "ritz0",
        *(
            pytest.param(c, marks=pytest.mark.xfail(strict=True, reason="AGAST #2537"))
            for c in RITZ1S
        ),
    ],
)
@pytest.mark.parametrize("ty", ["i16", "f64"])
def test_index_through_deref(run_with, ty, compiler):
    assert (
        run_with(
            compiler,
            f"index_{ty}",
            _program("local", "@", ty).replace("*(*r + 2)", "(*r)[2]"),
        )
        == 0
    )
