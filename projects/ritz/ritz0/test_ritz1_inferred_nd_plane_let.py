"""AGAST #2558: an inferred `let q = @x[i]` that names an N-D sub-array is refused.

    var x: [2][2][3]i32
    x[1][0][1] = 9
    let q = @x[0]               # an `@[2][3]i32`, a plane
    let r = q + 1
    let s = r as *i32
    return s[1]                 # ritz0: 9

#2555 types an inferred `@x[i]..` that is exactly one index short of the
rank: a row, `@[N]T`.  Two or more short, it is an `@[M][N]T`.  ritz1 can't
hold an N-D pointee (nd_array_reject refuses `*[M][N]T`, AGAST #1509), so q
stayed an untyped i64.  `q + 1` added one byte, and an `@` plane returned 0,
127 or garbage, SILENT.  An `@&` plane emitted IR that clang rejected
("defined with type 'ptr' but expected 'i64"), with no source location.
ritz1 now refuses the binding itself, located at the `let` / `var`.

KNOWN GAP: ritz0 computes 9 for every refused row.  So does `q as *i32` on a
plane, which ritz1 got right before (the cast never looked at the pointee),
and an unused plane binding.  Both are now refused too: the refusal is at the
binding, not at the arithmetic.  Carrying the plane's shape would lift it;
test_ritz1_plane_computes_like_ritz0 pins that as a strict xfail.

Already fine before, kept as controls: #2555's rows (`@x[i]` on 2-D,
`@x[i][j]` on 3-D, `@x[i][j][k]` on 4-D), a full element `@x[1][0][1]`, an
annotated `let q: *i32 = @x[0][0][0]` and a direct `x[1][0][1]`.
"""

import re

import pytest

from test_ritz1_array_ptr_element import (  # noqa: F401  (fixtures)
    COMPILERS, RITZ1S, compile_with, run_with)

REFUSAL = ("a multi-dimensional array type is not supported as the pointee of "
           "an inferred binding in ritz1")

# Where the array lives: its spelling, and what comes before main and at the
# top of main (`{ty}` is the full array type).
BASES = {
    "local": ("x", "", "    var x: {ty}\n"),
    "global": ("g", "var g: {ty}\n\n", ""),
    "field": ("h.m", "struct H\n    n: i32\n    m: {ty}\n\n", "    var h: H\n"),
}

# (dims, number of indices on the `@`).  A plane leaves two or more
# dimensions; a row leaves exactly one.
PLANES = {"3d_x0": ([2, 2, 3], 1), "4d_x0": ([2, 2, 2, 3], 1),
          "4d_x00": ([2, 2, 2, 3], 2)}
ROWS = {"2d_x0": ([2, 3], 1), "3d_x00": ([2, 2, 3], 2),
        "4d_x000": ([2, 2, 2, 3], 3)}

BINDERS = {"let_ref": "let q = @", "let_mut_ref": "let q = @&",
           "var_ref": "var q = @", "var_mut_ref": "var q = @&"}

# What main does with q.  `walk` is the ticket's repro: step one sub-array on,
# view it as `*i32`, read element 1.  `cast` and `unused` were right before;
# a plane refuses them too (the KNOWN GAP above).
USES = {
    "walk": "    let r = q + 1\n    let s = r as *i32\n    return s[1]\n",
    "cast": "    let s = q as *i32\n    return s[{flat}]\n",
    "unused": "    return 9\n",
}

def _program(dims, depth, base, binder, use):
    """main stores 9 where `use` reads it, then binds q to `@B[0]..` (depth 0s)."""
    spell, pre, top = BASES[base]
    ty = "".join(f"[{d}]" for d in dims) + "i32"
    pre = pre.format(ty=ty)
    top = top.format(ty=ty)
    if use == "walk":   # one sub-array on from q, then element 1 of it
        cell = [0] * (depth - 1) + [1] + [0] * (len(dims) - depth - 1) + [1]
    else:               # element 1 of q's own sub-array
        cell = [0] * (len(dims) - 1) + [1]
    flat = 0
    for d, i in zip(dims[depth:], cell[depth:]):
        flat = flat * d + i
    ix = "".join(f"[{i}]" for i in cell)
    lead = "[0]" * depth
    program = (f"{pre}pub fn main() -> i32\n{top}    {spell}{ix} = 9\n"
               f"    {binder}{spell}{lead}\n" + USES[use].format(flat=flat))
    # The 1-based line of the binding, where the refusal must point.
    line = program.split("\n").index(f"    {binder}{spell}{lead}") + 1
    return program, line


def _refused(compile_with, compiler, tag, program, line):
    comp, ll, _ = compile_with(compiler, tag, program)
    assert comp.returncode != 0, f"{tag}: ritz1 accepted an N-D pointee\n{comp.stderr[-1500:]}"
    # Located at the binding: `main.ritz:<line>:5: <REFUSAL>`.
    want = re.compile(rf"main\.ritz:{line}:5: {re.escape(REFUSAL)}")
    assert want.search(comp.stderr), f"{tag}: not a located refusal\n{comp.stderr[-1500:]}"


@pytest.mark.integration
@pytest.mark.parametrize("binder", sorted(BINDERS))
@pytest.mark.parametrize("base", sorted(BASES))
@pytest.mark.parametrize("plane", sorted(PLANES))
def test_ritz0_plane_walks(run_with, plane, base, binder):
    """The oracle: ritz0 strides a whole plane (9 in every row)."""
    dims, depth = PLANES[plane]
    program, _ = _program(dims, depth, base, BINDERS[binder], "walk")
    assert run_with("ritz0", f"p0_{plane}_{base}_{binder}", program) == 9


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("use", sorted(USES))
@pytest.mark.parametrize("binder", sorted(BINDERS))
@pytest.mark.parametrize("base", sorted(BASES))
@pytest.mark.parametrize("plane", sorted(PLANES))
def test_ritz1_refuses_inferred_plane(compile_with, plane, base, binder, use, compiler):
    dims, depth = PLANES[plane]
    program, line = _program(dims, depth, base, BINDERS[binder], use)
    _refused(compile_with, compiler, f"p1_{plane}_{base}_{binder}_{use}", program, line)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("plane", sorted(PLANES))
@pytest.mark.xfail(strict=True, reason="AGAST #2558 known gap: ritz1 refuses an inferred "
                   "N-D plane binding that ritz0 computes (carrying the shape is #2570)")
def test_ritz1_plane_computes_like_ritz0(run_with, plane, compiler):
    dims, depth = PLANES[plane]
    program, _ = _program(dims, depth, "local", BINDERS["let_ref"], "walk")
    assert run_with(compiler, f"gap_{plane}", program) == 9


# Controls: rows stay #2555's typed `@[N]T`, on every base and binder.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("binder", sorted(BINDERS))
@pytest.mark.parametrize("base", sorted(BASES))
@pytest.mark.parametrize("row", sorted(ROWS))
def test_inferred_row_still_walks(run_with, row, base, binder, compiler):
    dims, depth = ROWS[row]
    program, _ = _program(dims, depth, base, BINDERS[binder], "walk")
    assert run_with(compiler, f"row_{row}_{base}_{binder}", program) == 9


_HEAD = "pub fn main() -> i32\n    var x: [2][2][3]i32\n    x[1][0][1] = 9\n"
OTHER_CONTROLS = {
    # 7 = the flat index of [1][0][1] in a [2][2][3]
    "annotated_elem_ptr": _HEAD + "    let q: *i32 = @x[0][0][0]\n    return q[7]\n",
    "direct": _HEAD + "    return x[1][0][1]\n",
    "full_element": _HEAD + "    let q = @x[1][0][1]\n    return *q\n",
    # #2571: a `*i32`, as ritz0 types it (test_ritz1_inferred_elem_ref_let.py)
    "full_element_mut": _HEAD + "    let q = @&x[1][0][1]\n    return *q\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(OTHER_CONTROLS))
def test_other_forms_unchanged(run_with, name, compiler):
    assert run_with(compiler, f"ctl_{name}", OTHER_CONTROLS[name]) == 9
