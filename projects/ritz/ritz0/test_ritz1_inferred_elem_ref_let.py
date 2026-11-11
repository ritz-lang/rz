"""AGAST #2571: an inferred `let q = @&x[i]` to a full scalar array element.

    var x: [3]i32
    x[1] = 9
    let q = @&x[1]
    return *q                   # ritz0: 9

ritz1 kept the inferred slot an untyped i64 but stored the `ptr` that `@&`
yields: clang rejected `store i64 %ptr` ("defined with type 'ptr' but expected
'i64'"), unlocated.  Same on every rank (`@&x[1][1]`, `@&x[1][0][1]`).

The immutable `let q = @x[1]` compiled (a ptrtoint into the i64), but `*q`
loaded and `*q = v` would store 8 bytes whatever the element was, and `q + 1`
strode one byte.  Narrow reads passed only because the load was truncated.

Both now hold what ritz0 gives them: a pointer to the element type, so `*q`
loads and stores one element and `q + 1` is the next one.  Rows (`@x[i]` one
short of the rank, #2555) and planes (#2558) are pinned elsewhere
(test_ritz1_inferred_nd_plane_let.py).
"""

import pytest

from test_ritz1_array_ptr_element import (  # noqa: F401  (fixtures)
    COMPILERS, SCALARS, run_with)

# Where the array lives: its spelling, what comes before main, and the top of
# main (`{ty}` is the full array type).
BASES = {
    "local": ("x", "", "    var x: {ty}\n"),
    "global": ("g", "var g: {ty}\n\n", ""),
    "field": ("h.m", "struct H\n    n: i64\n    m: {ty}\n\n", "    var h: H\n"),
}

# Each rank's dims; the last is 3 so element [..][1] has a neighbour [..][2].
RANKS = {"1d": [3], "2d": [2, 3], "3d": [2, 2, 3]}

BINDERS = {"let_ref": "let q = @", "let_mut_ref": "let q = @&",
           "var_ref": "var q = @", "var_mut_ref": "var q = @&"}

# What main does with q; `{a}` is the target element, `{n}` its neighbour.
# Every check returns its own number, so a red cell says which one broke.
USES = {
    # Read the element, and the next one through `q + 1` (a stride of one
    # element, not one byte).
    "read": ("    if *q != {v0}\n        return 1\n"
             "    let r = q + 1\n    if *r != {v1}\n        return 2\n"),
    # Store through q: one element wide, so the neighbour survives.
    "write": ("    *q = {v3}\n    if {n} != {v1}\n        return 3\n"
              "    if {a} != {v3}\n        return 4\n    if *q != {v3}\n        return 5\n"),
}


def _program(rank, base, binder, use, ty):
    dims = RANKS[rank]
    spell, pre, top = BASES[base]
    arr = "".join(f"[{d}]" for d in dims) + ty
    # Every index but the last: [1][0].. (none on 1-D).  The target is the
    # element at last index 1, its neighbour the one at 2.
    lead = ("[1]" + "[0]" * (len(dims) - 2)) if len(dims) > 1 else ""
    a, n = f"{spell}{lead}[1]", f"{spell}{lead}[2]"
    v0, v1, _, v3 = SCALARS[ty]
    body = USES[use].format(a=a, n=n, v0=v0, v1=v1, v3=v3)
    return (f"{pre.format(ty=arr)}pub fn main() -> i32\n{top.format(ty=arr)}"
            f"    {a} = {v0}\n    {n} = {v1}\n"
            f"    {BINDERS[binder]}{a}\n{body}    return 9\n")


def _cells():
    """Writes need a mutable binder: ritz0 refuses a store through an `@`."""
    for rank in sorted(RANKS):
        for base in sorted(BASES):
            for binder in sorted(BINDERS):
                for use in sorted(USES):
                    if use == "write" and "mut" not in binder:
                        continue
                    yield rank, base, binder, use


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("rank,base,binder,use", list(_cells()))
def test_inferred_i32_element_ref(run_with, rank, base, binder, use, compiler):
    """Every rank, base and binder, on i32 (the ticket's own element type)."""
    program = _program(rank, base, binder, use, "i32")
    assert run_with(compiler, f"e_{rank}_{base}_{binder}_{use}", program) == 9


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("use", sorted(USES))
@pytest.mark.parametrize("ty", sorted(SCALARS))
def test_inferred_element_ref_every_scalar(run_with, ty, use, compiler):
    """Every scalar element width, through `@&` on a local 1-D array.

    1-D, not N-D: ritz1 can't yet compare an N-D f32 element with a literal
    (#2767) or store a bool into an N-D element (#2768), both without any q.
    """
    program = _program("1d", "local", "let_mut_ref", use, ty)
    assert run_with(compiler, f"t_{ty}_{use}", program) == 9


# The ticket's own repro, verbatim, on each rank.
TICKET = {
    "1d": "pub fn main() -> i32\n    var x: [3]i32\n    x[1] = 9\n    let q = @&x[1]\n    return *q\n",
    "2d": "pub fn main() -> i32\n    var x: [2][3]i32\n    x[1][1] = 9\n    let q = @&x[1][1]\n    return *q\n",
    "3d": ("pub fn main() -> i32\n    var x: [2][2][3]i32\n    x[1][0][1] = 9\n"
           "    let q = @&x[1][0][1]\n    return *q\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("rank", sorted(TICKET))
def test_ticket_repro(run_with, rank, compiler):
    assert run_with(compiler, f"ticket_{rank}", TICKET[rank]) == 9


# An N-D struct or enum element is a `*S`, as a 1-D one already was (#175):
# the same i64 slot, so `@&` gave IR clang rejected and `q.b` was "unhandled
# EXPR_MEMBER" (#2769).  The enum array is a zeroed global, so its element is
# E.A: ritz1 can't yet store into an N-D enum element.
_S = "struct S\n    a: i32\n    b: i32\n\n"
_E = "enum E\n    A\n    B\n\n"
ND_NAMED = {
    **{f"struct_{base}_{b}": (
        _S + BASES[base][1].format(ty="[2][3]S") + "pub fn main() -> i32\n"
        + BASES[base][2].format(ty="[2][3]S")
        + f"    {BASES[base][0]}[1][1].b = 9\n    {BINDERS[b]}{BASES[base][0]}[1][1]\n"
        + "    return q.b\n")
       for base in BASES for b in ("let_ref", "let_mut_ref")},
    "enum_global": (_E + "var g: [2][3]E\n\npub fn main() -> i32\n    let q = @&g[1][1]\n"
                    "    match *q\n        E.A => return 9\n        E.B => return 1\n"),
    "ptr_local": ("pub fn main() -> i32\n    var v: i32 = 9\n    var x: [2][3]*i32\n"
                  "    x[1][1] = @v\n    let q = @&x[1][1]\n    return **q\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ND_NAMED))
def test_nd_named_element_ref(run_with, name, compiler):
    assert run_with(compiler, f"nd_{name}", ND_NAMED[name]) == 9


# Controls: a 1-D element that isn't a scalar keeps the arm that already
# typed it, never a `*T` of a scalar T.
NON_SCALAR = {
    "struct_elem": (_S + "pub fn main() -> i32\n    var x: [3]S\n    x[1].b = 9\n"
                    "    let q = @&x[1]\n    return q.b\n"),
    "struct_field_elem": (_S + "struct H\n    n: i64\n    m: [3]S\n\n"
                          "pub fn main() -> i32\n    var h: H\n    h.m[1].b = 9\n"
                          "    let q = @&h.m[1]\n    return q.b\n"),
    "enum_elem": (_E + "pub fn main() -> i32\n    var x: [3]E\n    x[1] = E.B\n"
                  "    let q = @&x[1]\n    match *q\n        E.A => return 1\n"
                  "        E.B => return 9\n"),
    "ptr_elem": ("pub fn main() -> i32\n    var v: i32 = 9\n    var x: [3]*i32\n"
                 "    x[1] = @v\n    let q = @&x[1]\n    return **q\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(NON_SCALAR))
def test_non_scalar_element_ref_unchanged(run_with, name, compiler):
    assert run_with(compiler, f"ns_{name}", NON_SCALAR[name]) == 9
