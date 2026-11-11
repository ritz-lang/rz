"""AGAST #2574: `let (a, b) = <call>` destructures the struct the call returns.

    struct P / x: i16 / y: i16
    impl C
        pub fn tp(self: @C, a: i16) -> P
    let (a, b) = c.tp(3)        # ritz1: "cannot emit: unknown identifier 'a'"

ritz1 took the struct's name from a FREE fn's return type only, so a method
or static method call (`c.tp(3)`, `C.sm(5)`) found no struct and bound
nothing: every later use of `a` / `b` was "unknown identifier", unlocated.
On a free fn it bound both names as i64 but widened only i32 / u32 fields,
so an i16 (or i8, f32, ...) field was stored into the i64 slot as it was and
clang refused the IR.  angelo's font.ritz:112 hits both.

Each name now gets its field's own type, the slot an annotated
`let a: i16 = p.x` would get.  ritz0 is the oracle: every row runs on all
three compilers and must exit 0.  Each program returns the number of the
first check that failed, so a red cell names the path.

The tuple return type `-> (i32, i32)` is #1526, not this ticket.
"""

import pytest

from test_ritz1_array_ptr_element import (  # noqa: F401  (fixtures)
    COMPILERS, RITZ1S, compile_with, run_with)

# (field type, k, v).  P is built as { x: v + k, y: v }.  The values differ
# above the low byte and are negative where the type is signed, so a field
# read at the wrong width or with the wrong extension fails a check.
TYPES = {
    "i8": ("-5", "-3"),
    "u8": ("100", "50"),
    "i16": ("-2", "-300"),
    "u16": ("1000", "40000"),
    "i32": ("-1", "-70000"),
    "u32": ("1", "3000000000"),
    "i64": ("-1", "-5000000000"),
    "f32": ("0.25", "1.5"),
    "f64": ("0.25", "-2.5"),
}

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


def _program(ty: str, source: str) -> str:
    k, v = TYPES[ty]
    src = SOURCES[source].format(k=k, v=v)
    return _PROGRAM.format(t=ty, k=k, v=v, src=src)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(TYPES))
@pytest.mark.parametrize("source", sorted(SOURCES))
def test_destructure_binds_each_field_at_its_type(run_with, source, ty, compiler):
    assert run_with(compiler, f"{source}_{ty}", _program(ty, source)) == 0


# The ticket's program, verbatim apart from the static method and free fn
# rows: ritz0 prints 43 for the method form.
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
@pytest.mark.parametrize("compiler", COMPILERS)
def test_ticket_program(run_with, compiler):
    assert run_with(compiler, "ticket", TICKET) == 43 + 15 + 15


# Fields of different types: each name takes its own field's type, not the
# first field's.  A struct field binds the struct, a pointer field its
# pointee, and a bool field still reads as a condition.
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
@pytest.mark.parametrize("compiler", COMPILERS)
def test_mixed_field_types(run_with, compiler):
    assert run_with(compiler, "mixed", MIXED) == 0


# Places the struct lives other than a call: a field (through a chain, an
# element and a call), a global, and a pointer's pointee.  ritz0 gives 20.
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
@pytest.mark.parametrize("compiler", COMPILERS)
def test_struct_from_a_field_global_or_pointer(run_with, compiler):
    assert run_with(compiler, "places", PLACES) == 20


# Shapes ritz1 still can't name the struct of.  Each is refused, located at
# the `let`, instead of binding nothing and failing at every later use with
# an unlocated "unknown identifier".  ritz0 runs each (7): a known gap.
_REFUSED_PRE = """\
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
"""
REFUSED = {
    # #2594: an Option payload and a chained method call.
    "unwrap": ("    let r: Option<P> = Some(P { x: 1, y: 6 })\n"
               "    let (a, b) = r.unwrap()\n", 2594),
    "chained_method": ("    let c = C { k: 1 }\n    let (a, b) = c.me().tp(3)\n", 2594),
}


def _refused(name: str) -> str:
    return _REFUSED_PRE + REFUSED[name][0] + "    return a + b\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_unnamed_struct_is_a_located_error(compile_with, name, compiler):
    comp, _ll, _work = compile_with(compiler, name, _refused(name))
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert "unknown identifier" not in out, out
    line = _refused(name).splitlines().index(
        next(x for x in _refused(name).splitlines() if "let (a, b)" in x)) + 1
    assert f":{line}:5: ritz1 can't tell which struct this `let (a, b) = ...` destructures" in out, out


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_unnamed_struct_runs_like_ritz0(request, run_with, name, compiler):
    if compiler != "ritz0":
        request.applymarker(pytest.mark.xfail(
            strict=True, reason=f"AGAST #{REFUSED[name][1]}: ritz1 refuses this shape"))
    assert run_with(compiler, name, _refused(name)) == 7


# #2592: an element of a `[N]P` local, field or global is a `%P`, so it
# destructures like any struct value.  These were refused ("can't tell which
# struct") while the element read as an i64.  ritz0 gives 7 for each.
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
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(INDEXED))
def test_array_element_destructures(run_with, name, compiler):
    prog = _INDEXED_PRE + INDEXED[name] + "    return a + b\n"
    assert run_with(compiler, f"indexed_{name}", prog) == 7


# A field ritz1 can't hold in a local (an array here) is refused, located.
# ritz0 runs it (7): a known gap, #2594.
ARRAY_FIELD = """\
struct P
    x: [2]i32
    y: i32

fn mk() -> P
    var p: P
    p.x[1] = 4
    p.y = 3
    p

pub fn main() -> i32
    let (a, b) = mk()
    return a[1] + b
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_array_field_is_a_located_error(compile_with, compiler):
    comp, _ll, _work = compile_with(compiler, "array_field", ARRAY_FIELD)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert ":12:5: ritz1 can't destructure a field of this type" in out, out


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_array_field_runs_like_ritz0(request, run_with, compiler):
    if compiler != "ritz0":
        request.applymarker(pytest.mark.xfail(
            strict=True, reason="AGAST #2594: ritz1 refuses an array field"))
    assert run_with(compiler, "array_field", ARRAY_FIELD) == 7
