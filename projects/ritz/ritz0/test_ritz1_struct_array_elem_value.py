"""AGAST #2592: a struct element of a `[N]P` read by value is a `%P`.

    struct P / x: i16 / y: f32
    var ps: [2]P
    ps[1] = P { x: -3, y: 2.5 }
    let p: P = ps[1]        # ritz1: load i64 ... store %P %i64 (clang refuses)
    let r = ps[1]           # ritz1: `r.x` is "unhandled EXPR_MEMBER", unlocated

emit_expr_index's local-array arm read every element as `[N x i64]` /
`load i64`, so an annotated copy stored an i64 into a %P slot and an
inferred `let` had no struct type to bind.  The global (#1553) and field
(#188) arms already loaded `%P`; the local one now does too, and an inferred
`let` takes the element's struct.  `let (a, b) = ps[1]` (#2574) names its
struct through index_elem_struct_name.

ritz0 is the oracle: every row runs on all three compilers and must exit 0.
Each program returns the number of the first check that failed.
"""

import pytest

from test_ritz1_array_ptr_element import (  # noqa: F401  (fixtures)
    COMPILERS, run_with)

# (field type, v0, v1).  Distinct above the low byte and negative where the
# type is signed, so a read at the wrong width or stride fails a check.
TYPES = {
    "i8": ("-5", "100"),
    "i16": ("-300", "1234"),
    "f32": ("2.5", "-0.75"),
}

# Where the array lives: its spelling and the declarations it needs.
HOLDERS = {
    "local": ("ps", "", "    var ps: [3]P\n"),
    "field": ("h.ps", "struct H\n    n: i64\n    ps: [3]P\n\n", "    var h: H\n"),
    "global": ("gp", "var gp: [3]P\n\n", ""),
}

# The middle element differs from both neighbours, so a wrong stride reads
# the wrong one.  Each FORM reads elements 1 and then 2 (a runtime index `k`)
# its own way, then checks it holds a copy, not an alias.
_PROGRAM = """\
struct P
    x: {t}
    y: {t}

{pre}pub fn main() -> i32
{setup}    {a}[0] = P {{ x: {v0}, y: {v0} }}
    {a}[1] = P {{ x: {v1}, y: {v0} }}
    {a}[2] = P {{ x: {v0}, y: {v1} }}
    var k: i64 = 2
{body}    0
"""

FORMS = {
    "annotated": """\
    let p: P = {a}[1]
    let q: P = {a}[k]
""",
    "inferred": """\
    let p = {a}[1]
    let q = {a}[k]
""",
    # #2574's destructure, rebuilt into a P so the checks below are shared.
    "destructure": """\
    let (px, py) = {a}[1]
    let (qx, qy) = {a}[k]
    let p = P {{ x: px, y: py }}
    let q = P {{ x: qx, y: qy }}
""",
}

_CHECKS = """\
    if p.x != {v1}
        return 1
    if p.y != {v0}
        return 2
    if q.x != {v0}
        return 3
    if q.y != {v1}
        return 4
    {a}[1] = P {{ x: {v0}, y: {v1} }}
    if p.x != {v1} or p.y != {v0}
        return 5
"""


def _program(holder: str, ty: str, form: str) -> str:
    a, pre, setup = HOLDERS[holder]
    v0, v1 = TYPES[ty]
    body = (FORMS[form] + _CHECKS).format(a=a, v0=v0, v1=v1)
    return _PROGRAM.format(t=ty, a=a, pre=pre, setup=setup, v0=v0, v1=v1,
                           body=body)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("form", sorted(FORMS))
@pytest.mark.parametrize("ty", sorted(TYPES))
@pytest.mark.parametrize("holder", sorted(HOLDERS))
def test_struct_element_by_value(run_with, holder, ty, form, compiler):
    assert run_with(compiler, f"{holder}_{ty}_{form}",
                    _program(holder, ty, form)) == 0


# Fields of mixed widths: i8, i16 and f32 in one struct, so the element's
# layout (padding included) is %Q's, not N i64s.
MIXED = """\
struct Q
    a: i8
    b: f32
    c: i16

var gq: [2]Q

pub fn main() -> i32
    var qs: [2]Q
    qs[1] = Q { a: -7, b: 2.5, c: -300 }
    gq[1] = Q { a: 9, b: -1.5, c: 1234 }
    let l: Q = qs[1]
    let m = qs[1]
    let n = gq[1]
    if l.a != -7 or l.b != 2.5 or l.c != -300
        return 1
    if m.a != -7 or m.b != 2.5 or m.c != -300
        return 2
    if n.a != 9 or n.b != -1.5 or n.c != 1234
        return 3
    0
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_mixed_width_element(run_with, compiler):
    assert run_with(compiler, "mixed", MIXED) == 0


# The ticket's program, verbatim, annotated and inferred: ritz0 gives -3.
TICKET = """\
struct P
    x: i16
    y: f32

pub fn main() -> i32
    var ps: [2]P
    ps[1] = P {{ x: -3, y: 2.5 }}
    {decl} = ps[1]
    return {name}.x as i32
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("decl", ["let p: P", "let r"])
def test_ticket_program(run_with, decl, compiler):
    name = decl.split()[1].rstrip(":")
    prog = TICKET.format(decl=decl, name=name)
    assert run_with(compiler, name, prog) == 256 - 3
