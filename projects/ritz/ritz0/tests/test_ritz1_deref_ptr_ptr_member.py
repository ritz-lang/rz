"""AGAST #2805: `(*(qq + i)).f` on a `**S` reads S's field f.

ritz1 refused `(*(qq + 1)).b` with `qq: **S` (annotated, or inferred from
`vec_as_ptr<*S>(@v)` / a `-> **S` fn since #2791) as an unlocated
"unhandled EXPR_MEMBER": emit_member_ptr had no receiver arm for a
parenthesised deref of `**S` pointer arithmetic, though ptr_levels_of /
deref_ptr_ptr_struct_name already name S for it.  ritz0 compiled it and is
the oracle.

Each program reads `.b` of the element at index 1 (b = 7), so it returns 7
only when the receiver resolved to the right `*S` and field.
"""

import pytest

import test_ritz1_for_header as for_header

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

PRELUDE = (
    for_header.GVEC
    + "struct S\n    a: i64\n    b: i32\n\n"
    + "fn ident(p: **S) -> **S\n    return p\n\n"
    + "fn via_param(pp: **S) -> i32\n    return (*(pp + 1)).b\n\n"
)

# How the `**S` holding [&s0, &s1] is reached; `{x}` is then read as `(*({x} + 1)).b`.
SHAPES = {
    "annotated": "    let qq: **S = vec_as_ptr<*S>(@w)\n",
    "inferred_vec": "    let qq = vec_as_ptr<*S>(@w)\n",
    "inferred_fn": "    let qq = ident(vec_as_ptr<*S>(@w))\n",
    "bare_call": "",
}


def _program(shape: str, read: str) -> str:
    return (
        PRELUDE
        + "pub fn main() -> i32\n"
        + "    var s0: S\n    s0.a = 1\n    s0.b = 3\n"
        + "    var s1: S\n    s1.a = 2\n    s1.b = 7\n"
        + "    var w: Vec<*S> = vec_new<*S>()\n"
        + "    vec_push<*S>(@&w, @s0)\n    vec_push<*S>(@&w, @s1)\n"
        + SHAPES[shape]
        + f"    return {read}\n"
    )


def _read(shape: str) -> str:
    x = "vec_as_ptr<*S>(@w)" if shape == "bare_call" else "qq"
    return f"(*({x} + 1)).b"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_member_of_deref_ptr_ptr_arith(run_with, compiler, shape):
    assert run_with(compiler, shape, _program(shape, _read(shape))) == 7


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_annotation_survives_generic_type_arg(run_with, compiler):
    """`let p: *i32 = pick<*u8>(..)`: the `<*u8>` overwrote the annotation's
    pointee in the parser, so `p + 2` strode one byte, not four."""
    prog = (
        "fn pick<T>(a: *i32, b: T) -> *i32\n    return a\n\n"
        "pub fn main() -> i32\n"
        "    var a: [3]i32\n    a[0] = 1\n    a[1] = 2\n    a[2] = 7\n"
        "    let p: *i32 = pick<*u8>(@a[0], c\"x\")\n"
        "    return *(p + 2)\n"
    )
    assert run_with(compiler, "pointee", prog) == 7


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_member_of_deref_ptr_ptr_param(run_with, compiler):
    """A `**S` param, and `(*qq).b` (no arithmetic) on the same local: 7 + 3 * 10."""
    prog = _program("annotated", "via_param(qq) + (*qq).b * 10")
    assert run_with(compiler, "param", prog) == 37
