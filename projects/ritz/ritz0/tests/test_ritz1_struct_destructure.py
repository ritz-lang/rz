"""AGAST #2574/#3500: `let (a, b) = <named struct>` is refused (LARB R67).

    struct P / x: i16 / y: i16
    impl C
        pub fn tp(self: @C, a: i16) -> P
    let (a, b) = c.tp(3)        # ritz1: "cannot emit: unknown identifier 'a'"

#2574 taught ritz1 to bind each destructured name at its field's own type,
from a free fn, a method, a static method, a local, a field, a global, a
pointer's pointee, an array element, an `Option` payload, or an if / match
block -- angelo's font.ritz:112 used the method form.

LARB R67 (LANGUAGE_SPEC §4.1) refuses the whole class: a `(…)` pattern
destructures tuples only.  Binding a named struct's fields by position
silently rebinds every name after a field is added to the struct.  ritz0
refuses it at the `(` (#3499, test_tuple_pattern_tuples_only.py, and
ritz0/let_rules.py's tuple_pattern_on_struct); #3500 makes ritz1 and
ritz1_selfhosted say the same:

    `P` is a struct, not a tuple: read its fields

Each row below is one of the paths above, now a located refusal at the `(`.
A tuple still destructures: `test_a_tuple_still_destructures` is the boundary
control here, and test_ritz1_tuple_destructure_n.py / test_ritz1_tuple_type.py
hold the exhaustive tuple rows.
"""

import re

import pytest

from test_ritz1_array_ptr_element import (  # noqa: F401  (fixtures)
    RITZ1S, compile_with, run_with)


def _paren(program: str):
    """1-based line and column of the first `let (`'s `(`."""
    for line, text in enumerate(program.split("\n"), 1):
        at = text.find("let (")
        if at >= 0:
            return line, at + len("let ") + 1
    raise AssertionError("no `let (` in the program")


def _refused(compile_with, compiler, name, program, structs):
    """`program` is refused at the `(`, naming each struct in `structs`."""
    comp, ll, _work = compile_with(compiler, name, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted {name}:\n{out[-800:]}"
    for struct in structs:
        msg = f"`{struct}` is a struct, not a tuple: read its fields"
        assert msg in out, f"{compiler} did not name `{struct}` for {name}:\n{out[-800:]}"
    # The first refusal is at the first pattern's `(`.
    line, col = _paren(program)
    first = (rf"main\.ritz:{line}:{col}: error: `{re.escape(structs[0])}` "
             rf"is a struct, not a tuple: read its fields")
    assert re.search(first, out, re.M), f"{compiler} {name} not located at the `(`:\n{out[-800:]}"
    assert "Traceback" not in out and "ValueError" not in out, out[-800:]
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


# The initialiser's type no longer changes the outcome (every named struct is
# refused), so one field type covers all four ways main gets its P.
_TYPE = ("i16", "-2", "-300")   # (t, k, v): P is { x: v + k, y: v }

# How main gets its P.  `c` is a C with k in it; the static method and the
# free fn take k as an argument.
SOURCES = {
    "method": "c.tp({v})",
    "static_method": "C.sm({v}, {k})",
    "free_fn": "mk({v}, {k})",
    "local": "p",   # an already-bound P: the path that worked before
}

_PROGRAM = """\
struct P
    x: {t}
    y: {t}

struct C
    k: {t}

impl C
    pub fn tp(self: @C, a: {t}) -> P
        P {{ x: a + self.k, y: a }}

    pub fn sm(a: {t}, k: {t}) -> P
        P {{ x: a + k, y: a }}

fn mk(a: {t}, k: {t}) -> P
    P {{ x: a + k, y: a }}

pub fn main() -> i32
    let c = C {{ k: {k} }}
    let p = mk({v}, {k})
    let (a, b) = {src}
    let want_a: {t} = {v} + {k}
    let want_b: {t} = {v}
    if a != want_a
        return 1
    if b != want_b
        return 2
    # Each name has its field's type: an annotated binding takes it as is.
    let ta: {t} = a
    let tb: {t} = b
    if ta != want_a
        return 3
    if tb != want_b
        return 4
    # Arithmetic at the field's width: `a - b` is k.
    let d: {t} = a - b
    if d != {k}
        return 5
    0
"""


def _program(source: str) -> str:
    t, k, v = _TYPE
    return _PROGRAM.format(t=t, k=k, v=v, src=SOURCES[source].format(k=k, v=v))


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("source", sorted(SOURCES))
def test_destructuring_a_named_struct_is_refused(compile_with, source, compiler):
    _refused(compile_with, compiler, f"{source}_{_TYPE[0]}", _program(source), ["P"])


# The ticket's program, verbatim apart from the static method and free fn
# rows: ritz0 printed 43 for the method form.  All three patterns are refused.
TICKET = """\
struct P
    x: i16
    y: i16

struct C
    k: i16

impl C
    pub fn tp(self: @C, a: i16) -> P
        P { x: a + self.k, y: a }

    pub fn sm(a: i16) -> P
        P { x: a + a, y: a }

fn mk(a: i16) -> P
    P { x: a + 1, y: a }

pub fn main() -> i32
    let c = C { k: 1 }
    let (a, b) = c.tp(3)
    let (d, e) = C.sm(5)
    let (f, g) = mk(7)
    return a as i32 * 10 + b as i32 + d as i32 + e as i32 + f as i32 + g as i32
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_ticket_program(compile_with, compiler):
    _refused(compile_with, compiler, "ticket", TICKET, ["P"])
    comp, _ll, _work = compile_with(compiler, "ticket_count", TICKET)
    out = comp.stdout + comp.stderr
    assert out.count("`P` is a struct, not a tuple: read its fields") == 3, out[-800:]


# Fields of different types; a struct field, a pointer field and a bool field.
# M, N and B are each a named struct: each is refused, at its own `(`.
MIXED = """\
struct In
    u: i32
    w: i64

struct M
    a: i8
    b: f32

struct N
    q: In
    r: *i16

struct B
    ok: bool
    n: i64

impl In
    pub fn sum(self: @In) -> i64
        self.u as i64 + self.w

fn mk_m() -> M
    M { a: -7, b: 2.5 }

fn mk_b() -> B
    B { ok: true, n: 9 }

pub fn main() -> i32
    var cell: i16 = -1234
    let n = N { q: In { u: -3, w: 10 }, r: @cell }
    let (a, b) = mk_m()
    if a != -7
        return 1
    if b != 2.5
        return 2
    let (q, r) = n
    if q.u != -3
        return 3
    if q.sum() != 7
        return 4
    if *r != -1234
        return 5
    let (ok, k) = mk_b()
    if not ok
        return 6
    if k != 9
        return 7
    0
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_mixed_field_types(compile_with, compiler):
    _refused(compile_with, compiler, "mixed", MIXED, ["M", "N", "B"])


# Places the struct lives other than a call: a field (through a chain, an
# element and a call), a global, and a pointer's pointee.  Each is a P.
PLACES = """\
struct P
    x: i16
    y: i32

struct H
    p: P

var g: P

fn mk() -> H
    H { p: P { x: -3, y: 70000 } }

pub fn main() -> i32
    let h = H { p: P { x: 1, y: 2 } }
    let hs: [1]H = [h]
    let (a, b) = hs[0].p
    let (c, d) = h.p
    let (e, f) = mk().p
    g = P { x: 5, y: 6 }
    let (i, j) = g
    let q: *P = @h.p
    let (k, l) = *q
    if e != -3 or f != 70000
        return 99
    return a as i32 + b + c as i32 + d + i as i32 + j + k as i32 + l
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_struct_from_a_field_global_or_pointer(compile_with, compiler):
    _refused(compile_with, compiler, "places", PLACES, ["P"])


# Inits whose struct is named by more than a call's or a local's type.
#   unwrap          an Option<P>'s payload (sema types it through the receiver)
#   unwrap_or       a None's default, whose select is on %P
#   chained_method  `c.me()` names the C `.tp(3)` is dispatched on
#   match / if      a block init: the arms' phi names it
_NAMED_PRE = """\
import ritzlib.option

struct P
    x: i32
    y: i32

struct C
    k: i32

impl C
    pub fn me(self: @C) -> C
        C { k: self.k }

    pub fn tp(self: @C, a: i32) -> P
        P { x: a + self.k, y: a }

pub fn main() -> i32
    let t = 1
"""
NAMED = {
    "unwrap": "    let r: Option<P> = Some(P { x: 1, y: 6 })\n"
              "    let (a, b) = r.unwrap()\n",
    "unwrap_or": "    let r: Option<P> = None\n"
                 "    let (a, b) = r.unwrap_or(P { x: 1, y: 6 })\n",
    "chained_method": "    let c = C { k: 1 }\n    let (a, b) = c.me().tp(3)\n",
    "match": "    let (a, b) = match t\n        1 => P { x: 1, y: 6 }\n"
             "        _ => P { x: 3, y: 5 }\n",
    "if": "    let (a, b) = if t == 1\n        P { x: 1, y: 6 }\n"
          "    else\n        P { x: 3, y: 5 }\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(NAMED))
def test_named_struct_init_is_refused(compile_with, name, compiler):
    prog = _NAMED_PRE + NAMED[name] + "    return a + b\n"
    _refused(compile_with, compiler, f"named_{name}", prog, ["P"])


# An element of a `[N]P` local, field or global is a `%P`, so it is refused
# like any other struct value.
INDEXED = {
    "local": "    var ps: [2]P\n    ps[1] = P { x: 1, y: 6 }\n"
             "    let (a, b) = ps[1]\n",
    "field": "    var h: H\n    h.ps[1] = P { x: 1, y: 6 }\n"
             "    let (a, b) = h.ps[1]\n",
    "global": "    gp[0] = P { x: 1, y: 6 }\n    let (a, b) = gp[0]\n",
}

_INDEXED_PRE = """\
struct P
    x: i32
    y: i32

struct H
    n: i64
    ps: [2]P

var gp: [2]P

pub fn main() -> i32
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(INDEXED))
def test_array_element_destructures_is_refused(compile_with, name, compiler):
    prog = _INDEXED_PRE + INDEXED[name] + "    return a + b\n"
    _refused(compile_with, compiler, f"indexed_{name}", prog, ["P"])


# An array field, from a call's result and from a local.
ARRAY_FIELD = """\
struct P
    x: [2]i32
    y: i32

struct Q
    n: i8
    w: [3]i16

fn mk() -> P
    var p: P
    p.x[1] = 4
    p.y = 3
    p

pub fn main() -> i32
    var q: Q
    q.n = 2
    q.w[2] = -300
    let (n, w) = q
    if w[2] != -300 or n != 2
        return 1
    let (a, b) = mk()
    return a[1] + b
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_array_field_runs_like_ritz0(compile_with, compiler):
    _refused(compile_with, compiler, "array_field", ARRAY_FIELD, ["Q", "P"])


# A `@` field was refused by the emitter before R67; the pattern is now
# refused earlier, at the `(`, like every other named struct.
REF_FIELD = """\
struct Q
    r: @i32
    y: i32

pub fn main() -> i32
    let v: i32 = 3
    let q = Q { r: @v, y: 4 }
    let (a, b) = q
    return *a + b
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_ref_field_is_a_located_error(compile_with, compiler):
    _refused(compile_with, compiler, "ref_field", REF_FIELD, ["Q"])


# A generic struct: the refusal names the struct without its type arguments
# (`G`, not `G$u8`).  `G<T>` is specialised by monomorph before sema sees it.
_WIDEN = """\
struct P
    a: {t}
    n: i32

struct G<T>
    a: T
    n: i32

pub fn main() -> i32
    let p: P = P {{ a: {v}, n: 1 }}
    let (a, n) = p
    if a as i32 != {v}
        return 1
    if a as i64 != {v}
        return 2
    let g: G<{t}> = G<{t}> {{ a: {v}, n: 2 }}
    let (b, m) = g
    if b as i32 != {v}
        return 3
    return 10 + n + m
"""
WIDEN = {"u8": "200", "i8": "-5", "u16": "40000"}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("ty", sorted(WIDEN))
def test_destructured_field_widens_by_its_type(compile_with, ty, compiler):
    prog = _WIDEN.format(t=ty, v=WIDEN[ty])
    _refused(compile_with, compiler, f"widen_{ty}", prog, ["P", "G"])


# The ticket's program, verbatim.
TICKET_3217 = """\
struct P
    a: u8
    n: i32

pub fn main() -> i32
    let p: P = P { a: 200, n: 1 }
    let (a, n) = p
    if a as i32 == 200
        return 11
    3
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_ticket_3217_program(compile_with, compiler):
    _refused(compile_with, compiler, "ticket_3217", TICKET_3217, ["P"])


# The boundary: a tuple (a nameless tuple literal, a fn's tuple return, and a
# tuple whose element is a named struct) still destructures and runs.
TUPLE_CONTROLS = {
    "literal_pair": """\
pub fn main() -> i32
    let (a, b) = (1, 2)
    if (a + b) as i32 != 3
        return 1
    0
""",
    "call_pair": """\
fn two() -> (i32, i64)
    (3, -5000000000)

pub fn main() -> i32
    let (a, b) = two()
    if a != 3
        return 1
    if b != -5000000000
        return 2
    0
""",
    "named_element": """\
struct P
    x: i32
    y: i32

fn two() -> (P, u8)
    (P { x: 1, y: 2 }, 200)

pub fn main() -> i32
    let (p, k) = two()
    if p.y != 2
        return 1
    if k != 200
        return 2
    0
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(TUPLE_CONTROLS))
def test_a_tuple_still_destructures(run_with, name, compiler):
    assert run_with(compiler, f"tuple_{name}", TUPLE_CONTROLS[name]) == 0
