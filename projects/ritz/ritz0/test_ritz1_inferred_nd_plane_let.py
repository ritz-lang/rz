"""AGAST #2558 / #2570: an inferred `let q = @x[i]` that names an N-D sub-array.

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
127 or garbage, SILENT.  #2558 refused the binding, located; that refused
`q as *i32` and an unused binding too, which ritz1 had got right.

#2570 carries the plane's shape on the binding (the dims after the index
chain): q is the flat `@[M*N]T` that strides a whole plane, and it keeps
`[M][N]T`, so `q[i][j]` reads and `q[i][j] = v` stores the element, as for
the array itself.  `let r = q + 1` (and `let r = q`) keep the shape.

Still refused, located (ritz1 can't carry these): a row of q as a value
(`return q[0]`), a store to a row (`q[0] = v`), and `@q`, a pointer to the
plane pointer.  More indices than the plane has (`q[i][j][k]` on `[M][N]T`)
is refused too, as ritz0 refuses it; it crashed.

Already fine before, kept as controls: #2555's rows (`@x[i]` on 2-D,
`@x[i][j]` on 3-D, `@x[i][j][k]` on 4-D), a full element `@x[1][0][1]`, an
annotated `let q: *i32 = @x[0][0][0]` and a direct `x[1][0][1]`.
"""

import re

import pytest

from test_ritz1_array_ptr_element import (  # noqa: F401  (fixtures)
    COMPILERS, RITZ1S, compile_with, run_with)

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

# What main does with q.  `{qix}` indexes q's own sub-array down to the cell
# main stored 9 in; `{flat}` is that cell's flat offset from q.
#   walk:  the ticket's repro: one sub-array on, as `*i32`, element 1 of it
#   cast:  q as `*i32` (right before #2558)
#   unused: (right before #2558)
#   index: `q[i][j]..` reads the element
#   copy_index: `let r = q + 1` keeps the shape, `r[i][j]..` reads
#   store: `q[i][j].. = 9` writes the element main then reads directly
USES = {
    "walk": "    let r = q + 1\n    let s = r as *i32\n    return s[1]\n",
    "cast": "    let s = q as *i32\n    return s[{flat}]\n",
    "unused": "    return 9\n",
    "index": "    return q{qix}\n",
    "copy_index": "    let r = q + 1\n    return r{qix}\n",
    "store": "    q{qix} = 9\n    return {spell}{ix}\n",
}
# The uses that read one sub-array on from q.
STEPPED = {"walk", "copy_index"}


def _program(dims, depth, base, binder, use):
    """main stores 9 where `use` reads it, then binds q to `@B[0]..` (depth 0s)."""
    spell, pre, top = BASES[base]
    ty = "".join(f"[{d}]" for d in dims) + "i32"
    pre = pre.format(ty=ty)
    top = top.format(ty=ty)
    if use in STEPPED:  # one sub-array on from q, then element 1 of it
        cell = [0] * (depth - 1) + [1] + [0] * (len(dims) - depth - 1) + [1]
    else:               # element 1 of q's own sub-array
        cell = [0] * (len(dims) - 1) + [1]
    flat = 0
    for d, i in zip(dims[depth:], cell[depth:]):
        flat = flat * d + i
    ix = "".join(f"[{i}]" for i in cell)
    qix = "".join(f"[{i}]" for i in cell[depth:])
    lead = "[0]" * depth
    first = "" if use == "store" else f"    {spell}{ix} = 9\n"
    program = (f"{pre}pub fn main() -> i32\n{top}{first}"
               f"    {binder}{spell}{lead}\n"
               + USES[use].format(flat=flat, qix=qix, spell=spell, ix=ix))
    return program


@pytest.mark.integration
@pytest.mark.parametrize("binder", sorted(BINDERS))
@pytest.mark.parametrize("base", sorted(BASES))
@pytest.mark.parametrize("plane", sorted(PLANES))
def test_ritz0_plane_walks(run_with, plane, base, binder):
    """The oracle: ritz0 strides a whole plane (9 in every row)."""
    dims, depth = PLANES[plane]
    program = _program(dims, depth, base, BINDERS[binder], "walk")
    assert run_with("ritz0", f"p0_{plane}_{base}_{binder}", program) == 9


# The walk on every plane and base (the operand's emit path differs by base),
# with `@` and `@&` (an i64 slot vs a ptr one); `var` adds nothing to either.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("binder", ["let_ref", "let_mut_ref"])
@pytest.mark.parametrize("base", sorted(BASES))
@pytest.mark.parametrize("plane", sorted(PLANES))
def test_ritz1_plane_walks_like_ritz0(run_with, plane, base, binder, compiler):
    dims, depth = PLANES[plane]
    program = _program(dims, depth, base, BINDERS[binder], "walk")
    assert run_with(compiler, f"w_{plane}_{base}_{binder}", program) == 9


# Every use of q on every plane shape, local, through `@&` (store needs it);
# `var q = @` on one plane covers the remaining binder.
USE_ROWS = ([(p, "let_mut_ref", u) for p in sorted(PLANES) for u in sorted(USES)
             if u != "walk"]
            + [("3d_x0", "var_ref", u) for u in sorted(USES) if u != "store"])


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("plane,binder,use", USE_ROWS)
def test_plane_use_computes(run_with, plane, binder, use, compiler):
    dims, depth = PLANES[plane]
    program = _program(dims, depth, "local", BINDERS[binder], use)
    assert run_with(compiler, f"u_{plane}_{binder}_{use}", program) == 9


_GRID = "pub fn main() -> i32\n    var x: [2][2][3]i32\n    x[1][1][2] = 9\n"
_SGRID = ("struct P\n    a: i32\n    b: i32\n\n"
          "pub fn main() -> i32\n    var x: [2][2][3]P\n")
OTHER_PLANES = {
    # A struct leaf: q + 1 strides planes of P, which q has to name.
    "struct_walk": _SGRID + "    x[1][1][2].b = 9\n    let q = @x[0]\n"
                   "    let r = q + 1\n    return r[1][2].b\n",
    "struct_field_store": _SGRID + "    let q = @&x[1]\n    q[1][2].b = 9\n"
                          "    return x[1][1][2].b\n",
    # `@q[i]` is a row of the plane, as `@x[1][i]` is.
    "row_of_plane": _GRID + "    let q = @x[1]\n    let r = @q[1]\n    return r[2]\n",
    # `q = q + 1` keeps the plane's shape: it's on q, not on its initialiser.
    "var_reassign": _GRID + "    var q = @&x[0]\n    q = q + 1\n    return q[1][2]\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(OTHER_PLANES))
def test_other_plane_forms_compute(run_with, name, compiler):
    assert run_with(compiler, f"o_{name}", OTHER_PLANES[name]) == 9


# What ritz1 still can't carry: refused, located at the expression (or the
# `let`), never a guess.
_PLANE = "pub fn main() -> i32\n    var x: [2][2][3]i32\n    x[0][1][2] = 9\n    let q = @&x[0]\n"
REFUSED = {
    # A row as a value: ritz1 has no `[N]T` value for it.
    "row_value": (_PLANE + "    return q[1]\n", 5,
                  "a row or a struct element of a multi-dimensional array is not a value"),
    # A store to a whole row.
    "row_store": (_PLANE + "    q[1] = 9\n    return 9\n", 5, "is refused"),
    # A pointer to the plane pointer: `**[M][N]T` isn't carried.
    "ref_to_plane": (_PLANE + "    let rr = @q\n    return 9\n", 5,
                     "a multi-dimensional array type is not supported as the pointee"),
    # More indices than the plane has dimensions (ritz0 refuses it too).  It
    # read past q and crashed.
    "overindex": (_PLANE + "    return q[1][2][0]\n", 5,
                  "indexes more dimensions than the plane"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_ritz1_refuses_what_it_cannot_carry(compile_with, name, compiler):
    program, line, msg = REFUSED[name]
    comp, _, _ = compile_with(compiler, f"r_{name}", program)
    assert comp.returncode != 0, f"{name}: ritz1 accepted it\n{comp.stderr[-1500:]}"
    want = re.compile(rf"main\.ritz:{line}:\d+: .*{re.escape(msg)}")
    assert want.search(comp.stderr), f"{name}: not a located refusal\n{comp.stderr[-1500:]}"


# Controls: rows stay #2555's typed `@[N]T`, on every base and binder.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("binder", sorted(BINDERS))
@pytest.mark.parametrize("base", sorted(BASES))
@pytest.mark.parametrize("row", sorted(ROWS))
def test_inferred_row_still_walks(run_with, row, base, binder, compiler):
    dims, depth = ROWS[row]
    program = _program(dims, depth, base, BINDERS[binder], "walk")
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
