"""AGAST #2767: an N-D scalar element compared with (or fed) a literal.

    var x: [2][3]f32
    x[1][1] = 1.5
    if x[1][1] != 1.5           # ritz1: `fcmp one double` on a `float` load
        return 4
    return 9                    # ritz0: 9

ritz1 typed the N-D element right for its load (a `float`) but not for the
literal beside it: the expression type of an index chain past the first rank
didn't report the scalar leaf, so the `1.5` stayed a double and clang rejected
the IR, unlocated.  1-D `[3]f32` and `*f32` derefs were fine.

Each program writes two neighbouring elements, then reads both back through
every comparison and arithmetic shape a literal can sit in, so a red cell says
which one broke (the return value) on which type and rank.  bool is pinned on
1-D only here: an N-D bool element store is #2768.
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
RANKS = {"1d": [3], "2d": [2, 3], "3d": [2, 2, 3], "4d": [2, 2, 2, 3]}

# What main checks; `{a}` is the target element, `{n}` its neighbour.
_CHECKS = """\
    if {a} != {v0}
        return 1
    if {n} != {v1}
        return 2
    if {v0} != {a}
        return 3
    if {a} == {v1}
        return 4
    if !({a} == {v0})
        return 5
    let c = {a}
    if c != {v0}
        return 6
"""

# Arithmetic and ordering with a literal, on numbers only.
_NUMERIC = """\
    if {a} + {one} - {one} != {v0}
        return 7
    if {a} > {a} + {one}
        return 8
    {a} = {a} + {one}
    if {a} - {one} != {v0}
        return 9
    {a} = {v3}
    if {a} != {v3}
        return 10
    if {n} != {v1}
        return 11
"""

NUMERIC = sorted(t for t in SCALARS if t != "bool")


def _program(rank, base, ty):
    dims = RANKS[rank]
    spell, pre, top = BASES[base]
    arr = "".join(f"[{d}]" for d in dims) + ty
    # Every index but the last: [1][0].. (none on 1-D).
    lead = ("[1]" + "[0]" * (len(dims) - 2)) if len(dims) > 1 else ""
    a, n = f"{spell}{lead}[1]", f"{spell}{lead}[2]"
    v0, v1, _, v3 = SCALARS[ty]
    body = _CHECKS
    if ty != "bool":
        body += _NUMERIC
    one = "1.0" if ty.startswith("f") else "1"
    body = body.format(a=a, n=n, v0=v0, v1=v1, v3=v3, one=one)
    return (f"{pre.format(ty=arr)}pub fn main() -> i32\n{top.format(ty=arr)}"
            f"    {a} = {v0}\n    {n} = {v1}\n{body}    return 42\n")


def _cells():
    for rank in sorted(RANKS):
        for base in sorted(BASES):
            yield rank, base


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", NUMERIC)
@pytest.mark.parametrize("rank,base", list(_cells()))
def test_nd_scalar_element_with_literal(run_with, rank, base, ty, compiler):
    """Every numeric scalar, rank and base."""
    program = _program(rank, base, ty)
    assert run_with(compiler, f"s_{rank}_{base}_{ty}", program) == 42


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("base", sorted(BASES))
def test_1d_bool_element_with_literal(run_with, base, compiler):
    """bool on 1-D; N-D bool element stores are #2768."""
    assert run_with(compiler, f"b_{base}", _program("1d", base, "bool")) == 42


# The ticket's own repro, verbatim, plus its 3-D twin.
TICKET = {
    "2d": ("pub fn main() -> i32\n    var x: [2][3]f32\n    x[1][1] = 1.5\n"
           "    if x[1][1] != 1.5\n        return 4\n    return 9\n"),
    "3d": ("pub fn main() -> i32\n    var x: [2][2][3]f32\n    x[1][0][1] = 1.5\n"
           "    if x[1][0][1] != 1.5\n        return 4\n    return 9\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("rank", sorted(TICKET))
def test_ticket_repro(run_with, rank, compiler):
    assert run_with(compiler, f"ticket_{rank}", TICKET[rank]) == 9
