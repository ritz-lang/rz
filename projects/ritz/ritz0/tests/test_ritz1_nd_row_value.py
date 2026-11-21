"""AGAST #3322: a row of an N-D array is a value, a copy (`let r = g[1]`).

    var g: [2][3]i32
    ...
    let r = g[1]                # an `[3]i32`, as `let r: [3]i32 = g[1]`
    r[0] = 99                   # g[1][0] is unchanged

An `[N][M]T` is an array of `[M]T` (LANGUAGE_SPEC §3.3), and an element read
by value is a copy (§7), so ritz0 binds `r: [M]T`, copied.  ritz1 already
copied the annotated form and a row passed to an `[M]T` parameter, but an
unannotated `let` / `var` was the located "a row ... is not a value" error:
the binding had no type to copy into.  It now takes the `[M]T` the
annotation would declare.

Each program copies a row, writes the copy and the source, and checks that
neither write reached the other: a binding that aliased the row, or a copy
of the wrong row / stride, returns a small code instead of 42.  ritz0 is the
oracle.  A Drop leaf's row is refused by both, as moving out of an array
element.

AGAST #3350: a row that is itself N-D, a plane (`g[1]` of `[2][2][3]T` is a
`[2][3]T`), is copied the same way, unannotated or annotated: ritz1 had no
N-D local initializer from an index chain, so it was the "not a value" error.
"""

import pytest

from array_rules import MOVE_OUT_OF_ELEMENT
from test_ritz1_array_ptr_element import COMPILERS, compile_with, run_with  # noqa: F401  (fixtures)

_S = "struct S\n    a: i32\n    b: i32\n\n"

# Where the N-D array lives: the text before main (`{t}` is the leaf type), the
# text at the top of main, and how a row of it is spelled (`{i}` the row index).
BASES = {
    "local": ("", "    var g: [2][3]{t}\n", "g[{i}]"),
    "global": ("var g: [2][3]{t}\n\n", "", "g[{i}]"),
    "field": (
        "struct H\n    n: i32\n    m: [2][3]{t}\n\n",
        "    var h: H\n    h.n = 5\n",
        "h.m[{i}]",
    ),
    # The inner row of a rank-3 array: `x[1][0]` of `[2][2][3]T` is a `[3]T`.
    "inner_3d": ("", "    var x: [2][2][3]{t}\n", "x[1][{i}]"),
}

# How the copy `c` is made from the row `{row}` (`{t}` the leaf type).
FORMS = {
    "let": "    let c = {row}\n",
    "var": "    var c = {row}\n",
    "let_annotated": "    let c: [3]{t} = {row}\n",
    # A by-value `[3]T` parameter is the copy; `take` writes it and checks it.
    "argument": "",
}


def _program(elem: str, base: str, form: str) -> str:
    """Fill rows 0 and 1 of the base, copy row 1 into `c`, write both sides.

    Cell (i, j) holds 10*i + j + 2 (in `.b` for a struct), so each row and
    each column differs from its neighbours.
    """
    pre, top, spell = BASES[base]
    t = "S" if elem == "struct" else "i32"
    f = ".b" if elem == "struct" else ""
    row = spell.format(i=1)
    out = (_S if elem == "struct" else "") + pre.format(t=t)
    # `take` copies too: it writes its parameter and the caller's row must
    # not see it; it checks it got row 1, not row 0 or a stride of i64s.
    out += f"fn take(c: [3]{t}) -> i32\n"
    out += f"    if c[0]{f} != 12 or c[2]{f} != 14\n        return 1\n"
    out += f"    c[0]{f} = 99\n    return c[0]{f} + c[1]{f} - 70\n\n"
    out += "pub fn main() -> i32\n" + top.format(t=t)
    for i in range(2):
        for j in range(3):
            cell = spell.format(i=i) + f"[{j}]"
            if elem == "struct":
                out += f"    {cell}.a = 1\n"
            out += f"    {cell}{f} = {10 * i + j + 2}\n"
    if form == "argument":
        out += f"    let got = take({row})\n"
        out += f"    if {row}[0]{f} != 12\n        return 2\n"
        return out + "    return got\n"
    out += FORMS[form].format(row=row, t=t)
    # The copy holds row 1 ...
    out += f"    if c[0]{f} != 12 or c[1]{f} != 13 or c[2]{f} != 14\n        return 3\n"
    # ... and a write to the source row doesn't reach it ...
    out += f"    {row}[2]{f} = 50\n"
    out += f"    if c[2]{f} != 14\n        return 4\n"
    if form != "let_annotated" and form != "let":
        # ... nor a write to a `var` copy the source.
        out += f"    c[0]{f} = 99\n"
        out += f"    if {row}[0]{f} != 12 or c[0]{f} != 99\n        return 5\n"
    # Row 0 is untouched by all of it.
    out += f"    if {spell.format(i=0)}[0]{f} != 2 or {spell.format(i=0)}[2]{f} != 4\n        return 6\n"
    return out + f"    return c[1]{f} + 29\n"


# Every form on a local, scalar and struct leaf: the binding paths.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("form", sorted(FORMS))
@pytest.mark.parametrize("elem", ["scalar", "struct"])
def test_row_copy_forms(run_with, elem, form, compiler):
    program = _program(elem, "local", form)
    assert run_with(compiler, f"row_copy_{elem}_{form}", program) == 42


# The unannotated `var` over every other base the row is spelled on.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("base", ["field", "global", "inner_3d"])
@pytest.mark.parametrize("elem", ["scalar", "struct"])
def test_row_copy_bases(run_with, elem, base, compiler):
    program = _program(elem, base, "var")
    assert run_with(compiler, f"row_base_{elem}_{base}", program) == 42


# A row of pointers keeps U: `c` is a `[3]*i32`, and `*c[1]` reads through it.
_PTR_ROW = """\
pub fn main() -> i32
    var a: i32 = 7
    var b: i32 = 9
    var g: [2][3]*i32
    g[1][1] = @a
    g[1][2] = @b
    var c = g[1]
    c[2] = @a
    return *c[1] + *c[2] + *g[1][2] + 19
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_row_copy_pointer_leaf(run_with, compiler):
    assert run_with(compiler, "row_ptr_leaf", _PTR_ROW) == 42


# A Drop leaf's row is move-only: the array still drops each element, so
# binding or passing a row by value moves out of it.  Both refuse it at the
# row, in ritz0's words (`^` marks where).
_DROP_ROW = """\
struct S
    x: i32

impl Drop for S
    fn drop(self:& S)
        self.x = 0

fn eat(r: [2]S) -> i32
    return 0

pub fn main() -> i32
    var g: [2][2]S
    g[1][1].x = 2
BIND"""

DROP_FORMS = {
    "let": "    let t = ^g[1]\n    return t[1].x\n",
    "let_annotated": "    let t: [2]S = ^g[1]\n    return t[1].x\n",
    "argument": "    return eat(^g[1])\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("form", sorted(DROP_FORMS))
def test_drop_row_is_not_moved_out(compile_with, form, compiler):
    marked = _DROP_ROW.replace("BIND", DROP_FORMS[form])
    before = marked[: marked.index("^")]
    where = f":{before.count(chr(10)) + 1}:{len(before) - before.rfind(chr(10))}:"
    comp, ll, _ = compile_with(compiler, f"drop_row_{form}", marked.replace("^", ""))
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, (
        f"{compiler} moved a Drop row out of its array ({form})"
    )
    assert not ll.exists()
    assert where in out and MOVE_OUT_OF_ELEMENT in out, out


# AGAST #3350: a plane, a row that is itself N-D.  Where the rank-3 array
# lives and how a plane of it is spelled, as BASES.
PLANE_BASES = {
    "local": ("", "    var g: [2][2][3]{t}\n", "g[{i}]"),
    "global": ("var g: [2][2][3]{t}\n\n", "", "g[{i}]"),
    "field": (
        "struct H\n    n: i32\n    m: [2][2][3]{t}\n\n",
        "    var h: H\n    h.n = 5\n",
        "h.m[{i}]",
    ),
    # The inner plane of a rank-4 array: `x[1][0]` of `[2][2][2][3]T`.
    "inner_4d": ("", "    var x: [2][2][2][3]{t}\n", "x[1][{i}]"),
}

PLANE_FORMS = {
    "let": "    let c = {row}\n",
    "var": "    var c = {row}\n",
    "let_annotated": "    let c: [2][3]{t} = {row}\n",
    "var_annotated": "    var c: [2][3]{t} = {row}\n",
}


def _plane_program(elem: str, base: str, form: str) -> str:
    """Fill planes 0 and 1, copy plane 1 into `c`, write both sides.

    Cell (p, i, j) holds 20*p + 5*i + j + 1 (in `.b` for a struct): every
    plane, row and column differs, so a wrong plane, row stride or leaf
    stride reads a wrong value.
    """
    pre, top, spell = PLANE_BASES[base]
    t = "S" if elem == "struct" else "i32"
    f = ".b" if elem == "struct" else ""
    src = spell.format(i=1)
    out = (_S if elem == "struct" else "") + pre.format(t=t)
    out += "pub fn main() -> i32\n" + top.format(t=t)
    for p in range(2):
        for i in range(2):
            for j in range(3):
                cell = spell.format(i=p) + f"[{i}][{j}]"
                if elem == "struct":
                    out += f"    {cell}.a = 1\n"
                out += f"    {cell}{f} = {20 * p + 5 * i + j + 1}\n"
    out += PLANE_FORMS[form].format(row=src, t=t)
    # The copy holds plane 1, every row of it ...
    out += f"    if c[0][0]{f} != 21 or c[0][2]{f} != 23 or c[1][0]{f} != 26 or c[1][2]{f} != 28\n        return 3\n"
    # ... and a write to the source plane doesn't reach it ...
    out += f"    {src}[1][2]{f} = 50\n"
    out += f"    if c[1][2]{f} != 28\n        return 4\n"
    if form.startswith("var"):
        # ... nor a write to a `var` copy the source.
        out += f"    c[1][1]{f} = 99\n"
        out += f"    if {src}[1][1]{f} != 27 or c[1][1]{f} != 99\n        return 5\n"
    # Plane 0 is untouched by all of it.
    p0 = spell.format(i=0)
    out += f"    if {p0}[0][0]{f} != 1 or {p0}[1][2]{f} != 8\n        return 6\n"
    return out + f"    return c[0][0]{f} + 21\n"


# Every form on a local, scalar and struct leaf: the binding paths.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("form", sorted(PLANE_FORMS))
@pytest.mark.parametrize("elem", ["scalar", "struct"])
def test_plane_copy_forms(run_with, elem, form, compiler):
    program = _plane_program(elem, "local", form)
    assert run_with(compiler, f"plane_copy_{elem}_{form}", program) == 42


# The unannotated `var` over every other base the plane is spelled on.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("base", ["field", "global", "inner_4d"])
@pytest.mark.parametrize("elem", ["scalar", "struct"])
def test_plane_copy_bases(run_with, elem, base, compiler):
    program = _plane_program(elem, base, "var")
    assert run_with(compiler, f"plane_base_{elem}_{base}", program) == 42


# A plane whose shape doesn't match the annotation is refused by both.
_PLANE_MISMATCH = """\
pub fn main() -> i32
    var g: [2][2][3]i32
    let c: [3][2]i32 = g[1]
    return c[0][0]
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_plane_shape_mismatch_refused(compile_with, compiler):
    comp, ll, _ = compile_with(compiler, "plane_mismatch", _PLANE_MISMATCH)
    assert comp.returncode != 0, f"{compiler} copied a [2][3] plane into a [3][2]"
    assert not ll.exists()


# A Drop leaf's plane is move-only, as its row is: refused at the plane.
_DROP_PLANE = """\
struct S
    x: i32

impl Drop for S
    fn drop(self:& S)
        self.x = 0

pub fn main() -> i32
    var g: [2][2][2]S
    g[1][1][1].x = 2
BIND"""

DROP_PLANE_FORMS = {
    "let": "    let t = ^g[1]\n    return t[1][1].x\n",
    "let_annotated": "    let t: [2][2]S = ^g[1]\n    return t[1][1].x\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("form", sorted(DROP_PLANE_FORMS))
def test_drop_plane_is_not_moved_out(compile_with, form, compiler):
    marked = _DROP_PLANE.replace("BIND", DROP_PLANE_FORMS[form])
    before = marked[: marked.index("^")]
    where = f":{before.count(chr(10)) + 1}:{len(before) - before.rfind(chr(10))}:"
    comp, ll, _ = compile_with(compiler, f"drop_plane_{form}", marked.replace("^", ""))
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, (
        f"{compiler} moved a Drop plane out of its array ({form})"
    )
    assert not ll.exists()
    assert where in out and MOVE_OUT_OF_ELEMENT in out, out
