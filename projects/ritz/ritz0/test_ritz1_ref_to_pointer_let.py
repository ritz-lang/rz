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


# AGAST #2537: `(*r)[i]` with `r: **T` loaded one byte on ritz1 whatever T was
# (`getelementptr i8` + `load i8`), annotated or inferred: wrong values on an
# integer, invalid IR on a float.  `*(*r + k)` already had T's stride.  Every
# `*(*r + k)` in _CHECKS becomes `(*r)[k]`; `**r` stays as the control.
def _indexed(source: str, amp: str, ty: str, annotate: bool) -> str:
    text = (
        _program(source, amp, ty)
        .replace("*(*r + 1)", "(*r)[1]")
        .replace("*(*r + 2)", "(*r)[2]")
    )
    if annotate:
        text = text.replace(f"let r = {amp}q", f"let r: **{ty} = {amp}q")
    return text


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(SCALARS))
@pytest.mark.parametrize("amp", ["@", "@&"], ids=["shared", "mut"])
@pytest.mark.parametrize("source", sorted(SOURCES))
def test_index_through_deref(run_with, source, amp, ty, compiler):
    name = f"index_{source}_{'mut' if amp == '@&' else 'shared'}_{ty}"
    assert run_with(compiler, name, _indexed(source, amp, ty, False)) == 0


# The written-out `let r: **T` took the same byte path.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(SCALARS))
def test_index_through_deref_annotated(run_with, ty, compiler):
    assert run_with(compiler, f"index_ann_{ty}", _indexed("local", "@", ty, True)) == 0


# A `r: **T` parameter, not a `let`: the base is `*r` all the same.
_PARAM_PP = (
    """\
fn g(r: **{t}) -> i32
    if (*r)[0] != {v0}
        return 1
    if (*r)[1] != {v1}
        return 2
    if (*r)[2] != {v2}
        return 3
    let i: i64 = 2
    let v = (*r)[i]
    if v != {v2}
        return 4
    return 0

pub fn main() -> i32
"""
    + _FILL
    + """\
    var q: *{t} = @x[0]
    return g(@q)
"""
)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(SCALARS))
def test_index_through_deref_param(run_with, ty, compiler):
    v0, v1, v2, _ = SCALARS[ty]
    assert (
        run_with(
            compiler,
            f"index_pp_param_{ty}",
            _PARAM_PP.format(t=ty, v0=v0, v1=v1, v2=v2),
        )
        == 0
    )


# AGAST #2545: the store side, `(*r)[i] = v` with `r: **T`.  ritz1 stored
# through the VALUE `(*r)[i]` read (segfault on i16) and as an i64 (invalid IR
# on f64).  Each store checks the element it aimed at and both neighbours, so a
# wide or byte-strided store can't pass; 7 reads the store back through r.
_STORE_CHECKS = """\
    let r = {amp}q
    (*r)[1] = {v3}
    if x[1] != {v3}
        return 1
    if x[0] != {v0}
        return 2
    if x[2] != {v2}
        return 3
    let i: i64 = 2
    (*r)[i] = {v3}
    if x[2] != {v3}
        return 4
    if x[1] != {v3}
        return 5
    if x[0] != {v0}
        return 6
    (*r)[0] = {v1}
    if (*r)[0] != {v1}
        return 7
    if x[1] != {v3}
        return 8
    return 0
"""


def _stored(source: str, amp: str, ty: str, annotate: bool) -> str:
    v0, v1, v2, v3 = SCALARS[ty]
    text = (
        SOURCES[source]
        .replace(_CHECKS, _STORE_CHECKS)
        .format(amp=amp, t=ty, v0=v0, v1=v1, v2=v2, v3=v3)
    )
    if annotate:
        text = text.replace(f"let r = {amp}q", f"let r: **{ty} = {amp}q")
    return text


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(SCALARS))
@pytest.mark.parametrize("amp", ["@", "@&"], ids=["shared", "mut"])
@pytest.mark.parametrize("source", sorted(SOURCES))
def test_store_through_deref_index(run_with, source, amp, ty, compiler):
    name = f"store_{source}_{'mut' if amp == '@&' else 'shared'}_{ty}"
    assert run_with(compiler, name, _stored(source, amp, ty, False)) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(SCALARS))
def test_store_through_deref_index_annotated(run_with, ty, compiler):
    assert run_with(compiler, f"store_ann_{ty}", _stored("local", "@", ty, True)) == 0


# A `r: **T` parameter stores through `*r` all the same.
_PARAM_PP_STORE = (
    """\
fn g(r: **{t}) -> i32
    (*r)[1] = {v2}
    let i: i64 = 2
    (*r)[i] = {v3}
    return 0

pub fn main() -> i32
"""
    + _FILL
    + """\
    var q: *{t} = @x[0]
    if g(@q) != 0
        return 9
    if x[0] != {v0}
        return 1
    if x[1] != {v2}
        return 2
    if x[2] != {v3}
        return 3
    return 0
"""
)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(SCALARS))
def test_store_through_deref_index_param(run_with, ty, compiler):
    v0, v1, v2, v3 = SCALARS[ty]
    program = _PARAM_PP_STORE.format(t=ty, v0=v0, v1=v1, v2=v2, v3=v3)
    assert run_with(compiler, f"store_pp_param_{ty}", program) == 0


# AGAST #2539: `let r = @q` with `q: *[N]T` or `q: *Enum` stayed an i64 after
# #2532.  The array form was silent: after `let p = *r`, `p[1]` read the wrong
# slot (exit 1) and a store through it crashed.  The enum form was invalid IR.
# ritz0 is the oracle: 0 on every row.  `{ann}` is "" (inferred) or the
# written-out type, the control: inference must match it.  The written-out
# `**[3]T` was just as wrong: ritz1's parser dropped N and T past one `*`.
_ARRAY = """\
pub fn main() -> i32
    var x: [3]{t}
    x[0] = {v0}
    x[1] = {v1}
    x[2] = {v2}
    var q: *[3]{t} = @x
    let r{ann} = {amp}q
{body}"""

ARRAY_BODIES = {
    # The ticket's program: copy the array pointer out, then index it.
    "copy_out": "    let p = *r\n"
    "    if p[1] != {v1}\n        return 1\n"
    "    p[1] = {v3}\n"
    "    if x[1] != {v3}\n        return 2\n"
    "    if x[0] != {v0}\n        return 3\n"
    "    if x[2] != {v2}\n        return 4\n"
    "    return 0\n",
    # Index through the deref without the copy.
    "index_through": "    if (*r)[2] != {v2}\n        return 1\n"
    "    (*r)[0] = {v3}\n"
    "    if x[0] != {v3}\n        return 2\n"
    "    if x[1] != {v1}\n        return 3\n"
    "    return 0\n",
    # `*r` is q itself: re-pointing it through r re-points q.
    "replace_through": "    var y: [3]{t}\n    y[1] = {v3}\n"
    "    *r = @y\n"
    "    if q[1] != {v3}\n        return 1\n"
    "    return 0\n",
}

ARRAY_TYPES = ["i8", "u8", "i16", "i32", "i64", "f64"]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", ARRAY_TYPES)
@pytest.mark.parametrize("ann", ["inferred", "annotated"])
@pytest.mark.parametrize("body", sorted(ARRAY_BODIES))
def test_reference_to_an_array_pointer(request, run_with, body, ann, ty, compiler):
    if body == "index_through" and compiler in RITZ1S:
        request.applymarker(
            pytest.mark.xfail(strict=True, reason="AGAST #2331: (*pp)[i] on a **[N]T")
        )
    v0, v1, v2, v3 = SCALARS[ty]
    amp = "@&" if body == "replace_through" else "@"
    program = _ARRAY.format(
        t=ty,
        v0=v0,
        v1=v1,
        v2=v2,
        amp=amp,
        ann="" if ann == "inferred" else f": **[3]{ty}",
        body=ARRAY_BODIES[body].format(t=ty, v0=v0, v1=v1, v2=v2, v3=v3),
    )
    assert run_with(compiler, f"arr_{body}_{ann}_{ty}", program) == 0


_ENUM = """\
enum Color
    Red
    Green
    Blue

pub fn main() -> i32
    var c = Color.Green
    var q: *Color = @c
    let r{ann} = @q
{body}"""

ENUM_BODIES = {
    "match_load": "    match **r\n        Color.Green => 0\n        _ => 1\n",
    "store_then_match": "    **r = Color.Blue\n"
    "    match c\n        Color.Blue => 0\n        _ => 1\n",
    "store_then_load": "    **r = Color.Red\n"
    "    let v = **r\n"
    "    match v\n        Color.Red => 0\n        _ => 1\n",
    "compare": "    if **r == Color.Green\n        return 0\n    return 1\n",
    # store_then_load's control: the written-out `v` needs no inference.
    "store_then_load_annotated_v": "    **r = Color.Red\n"
    "    let v: Color = **r\n"
    "    match v\n        Color.Red => 0\n        _ => 1\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ann", ["inferred", "annotated"])
@pytest.mark.parametrize("body", sorted(ENUM_BODIES))
def test_reference_to_an_enum_pointer(request, run_with, body, ann, compiler):
    if body == "store_then_load" and compiler in RITZ1S:
        request.applymarker(
            pytest.mark.xfail(
                strict=True, reason="AGAST #2542: `let v = *p` isn't typed"
            )
        )
    program = _ENUM.format(
        ann="" if ann == "inferred" else ": **Color", body=ENUM_BODIES[body]
    )
    assert run_with(compiler, f"enum_{body}_{ann}", program) == 0


_COLOR = "enum Color\n    Red\n    Green\n    Blue\n\n"
_S3 = "struct S\n    a: i32\n    b: i32\n\npub fn main() -> i32\n    var x: [3]S\n    x[1].b = 5\n"

AGGREGATE_SHAPES = {
    # `q: **Color`: `r` is a `***Color`, three levels to the enum.
    "enum_three_levels": _COLOR
    + "pub fn main() -> i32\n    var c = Color.Green\n    var p: *Color = @c\n    var q: **Color = @p\n"
    + "    let r = @q\n    ***r = Color.Blue\n    if ***r != Color.Blue\n        return 1\n"
    + "    let v: Color = ***r\n    match v\n        Color.Blue => 0\n        _ => 2\n",
    # One level, no `@q`: the tag compare reads the %Color `*q` loads.
    "enum_one_level_compare": _COLOR
    + "pub fn main() -> i32\n    var c = Color.Green\n    var q: *Color = @c\n"
    + "    if *q == Color.Green\n        return 0\n    return 1\n",
    # A `*[3]S` names S, but `@q` isn't an `@*S`: re-point q through r.
    "struct_array_replace": _S3
    + "    var q: *[3]S = @x\n    let r = @&q\n    var y: [3]S\n    y[1].b = 7\n    *r = @y\n"
    + _is("q[1].b", "7"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(AGGREGATE_SHAPES))
def test_reference_to_an_aggregate_pointer_shape(run_with, name, compiler):
    assert run_with(compiler, name, AGGREGATE_SHAPES[name]) == 0
