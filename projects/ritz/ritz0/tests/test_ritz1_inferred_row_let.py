"""AGAST #2555: an inferred `let q = @x[i]` on an `[M][N]T` holds an `@[N]T`.

    var x: [2][3]i32
    x[1][1] = 9
    let q = @x[0]               # an `@[3]i32`, as `let q: @[3]i32 = @x[0]`
    let r = q + 1
    return r[1]                 # ritz0: 9

ritz1's inferred-local path recorded no `[N]T` pointee for an `@x[i]` /
`@&x[i]` whose element is itself an array, so `q + 1` strode one byte and
`r[1]` loaded an i8 (exit 0, SILENT), and `q[1]` was an unlocated
"unlowerable expression".  The annotated `@[3]i32` / `*[3]i32` forms and a 1-D
`let q = @x` were already right.

The rows: an `@` and an `@&` binding, a scalar and a struct T, over a 2-D
local, the inner row of a 3-D local (`@x[i][j]` of `[2][2][3]T`), a 2-D global
and a 2-D field.  A struct row records S in pointee_array_elem_name, as #2552
does for the annotated local, so `q.b` stays refused.  ritz0 is the oracle.
"""

import pytest

from test_ritz1_array_ptr_element import COMPILERS, run_with  # noqa: F401  (fixture)

_S = "struct S\n    a: i32\n    b: i32\n\n"

# Where the array lives: its dims, how it is spelled, and what comes before main
# (`{t}` is the element type) and at the top of main.
BASES = {
    "local": ([2, 3], "x", "", "    var x: [2][3]{t}\n"),
    "local_3d": ([2, 2, 3], "x", "", "    var x: [2][2][3]{t}\n"),
    "global": ([2, 3], "g", "var g: [2][3]{t}\n\n", ""),
    "field": ([2, 3], "h.m", "struct H\n    n: i32\n    m: [2][3]{t}\n\n",
              "    var h: H\n"),
}


def _cells(dims):
    """Every index tuple of `dims`, row-major."""
    out = [()]
    for d in dims:
        out = [c + (i,) for c in out for i in range(d)]
    return out


def _v(dims, at) -> int:
    """The distinct value cell `at` holds: its row-major position, plus 2."""
    flat = 0
    for d, i in zip(dims, at):
        flat = flat * d + i
    return flat + 2


def _ix(at) -> str:
    return "".join(f"[{i}]" for i in at)


def _program(elem: str, base: str, decl: str, body: str) -> str:
    """main fills the array, binds `DECL B[0]..` (the first row) and runs body.

    body may use {B} (the array), {f} (`.b` for a struct, else ``), and
    {v:I} for the value at row-relative index I = "r,c" (r rows on from q's).
    """
    dims, spell, pre, top = BASES[base]
    t = "S" if elem == "struct" else "i32"
    out = (_S if elem == "struct" else "") + pre.format(t=t)
    out += "pub fn main() -> i32\n" + top.format(t=t)
    for at in _cells(dims):
        if elem == "struct":
            out += f"    {spell}{_ix(at)}.a = 1\n    {spell}{_ix(at)}.b = {_v(dims, at)}\n"
        else:
            out += f"    {spell}{_ix(at)} = {_v(dims, at)}\n"
    lead = [0] * (len(dims) - 1)   # q is the row B[0]..[0]

    def val(rc: str) -> str:
        r, c = (int(n) for n in rc.split(","))
        at = list(lead)
        at[-1] += r
        return str(_v(dims, tuple(at) + (c,)))

    out += f"    {decl.format(t=t)}{spell}{_ix(lead)}\n"
    f = ".b" if elem == "struct" else ""
    row1 = spell + _ix(lead[:-1] + [1])
    while "{v:" in body:
        i = body.index("{v:")
        j = body.index("}", i)
        body = body[:i] + val(body[i + 3:j]) + body[j + 1:]
    return out + body.replace("{f}", f).replace("{R1}", row1)


# Reads, row walks and copies: every binding runs these.
_READS = """\
    if q[1]{f} != {v:0,1}
        return 1
    if q[2]{f} != {v:0,2}
        return 2
    let r = q + 1
    if r[1]{f} != {v:1,1}
        return 3
    let r0 = r - 1
    if r0[0]{f} != {v:0,0}
        return 4
    let q2 = q
    if q2[2]{f} != {v:0,2}
        return 5
    return 0
"""

# Stores through an `@&` (or `*`) row land in the array, at the element's stride.
_STORES = """\
    q[2]{f} = 77
    if {R1}[0]{f} != {v:1,0}
        return 11
    let r = q + 1
    r[1]{f} = 66
    if {R1}[1]{f} != 66
        return 12
    if q[2]{f} != 77
        return 13
    return 0
"""

# How q is bound.  `ptr_annotated` is #2556's `let q: *[3]S = @x[0]`, which
# named no S either; the same fix names it (the scalar `*[3]i32` was right).
OPS = {"ref": "let q = @", "mut_ref": "let q = @&", "ptr_annotated": "let q: *[3]{t} = @"}
MUT_OPS = ["mut_ref", "ptr_annotated"]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("op", sorted(OPS))
@pytest.mark.parametrize("base", sorted(BASES))
@pytest.mark.parametrize("elem", ["scalar", "struct"])
def test_inferred_row_reads(run_with, elem, base, op, compiler):
    program = _program(elem, base, OPS[op], _READS)
    assert run_with(compiler, f"row_reads_{elem}_{base}_{op}", program) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("op", MUT_OPS)
@pytest.mark.parametrize("base", sorted(BASES))
@pytest.mark.parametrize("elem", ["scalar", "struct"])
def test_inferred_mut_row_stores(run_with, elem, base, op, compiler):
    program = _program(elem, base, OPS[op], _STORES)
    assert run_with(compiler, f"row_stores_{elem}_{base}_{op}", program) == 0


# A struct row is an `@[3]S`, not an `@S`: `q.b` is not element 0's b.
NOT_AN_ELEMENT = {
    "field": "    return q.b\n",
    "copy_field": "    let q2 = q\n    return q2.b\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("op", sorted(OPS))
@pytest.mark.parametrize("base", sorted(BASES))
@pytest.mark.parametrize("name", sorted(NOT_AN_ELEMENT))
def test_inferred_struct_row_is_not_its_element(run_with, name, base, op, compiler):
    program = _program("struct", base, OPS[op], NOT_AN_ELEMENT[name])
    tag = f"row_not_elem_{name}_{base}_{op}"
    with pytest.raises(AssertionError, match=f"failed on {tag}"):
        run_with(compiler, tag, program)


# A row of pointers keeps U (`[2][3]*i32`'s `@x[0]` is an `@[3]*i32`), so `*q[1]`
# reads an i32 through element 1.  Without U it was refused.  (`q + k` on any
# `*[N]*U`, annotated too, is still a located refusal in ritz1.)
_PTR_ROW = """\
pub fn main() -> i32
    var a: i32 = 7
    var b: i32 = 9
    var x: [2][3]*i32
    x[0][1] = @a
    x[0][2] = @b
    let q = OP x[0]
    return *q[1] + *q[2]
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("op", ["@", "@&"])
def test_inferred_pointer_row(run_with, op, compiler):
    program = _PTR_ROW.replace("OP ", op)
    assert run_with(compiler, f"ptr_row_{len(op)}", program) == 16
