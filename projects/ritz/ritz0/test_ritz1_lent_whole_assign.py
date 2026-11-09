"""AGAST #2346: `r = v` on a `r:& T` param, T a struct, an enum or StrView.

    fn w(r:& C, v: C)
        r = v

ritz0 auto-dereferences the borrow, so `r = v` overwrites the caller's value.
ritz1 left these params TYPE_MUT_REF locals (only integer and array pointees
are bound as the referent) and its named-target store wrote the value as an
i64 into the local's own slot:

    store i64 %.3, ptr %.1     ; %.3 is a %C: a clang error with no location

For `r = v` with `v:& C` as well, the value IS a pointer, so it compiled and
silently reseated `r` onto `v`: the caller's struct was never written.

ritz1 now loads the borrow's pointer and stores the value at T.  The f32 / f64
store (#1668's) goes through the same arm and is pinned here too; READING a
`:&` float or a `:& bool` at all is still #1668, pinned in KNOWN_GAPS.

Every program returns 3 only if the caller sees the whole new value, and the
neighbouring rows check the store is exactly T wide.
"""

from pathlib import Path

import pytest

from test_borrow_param_ref_field import _run

RITZ_ROOT = Path(__file__).resolve().parent.parent
SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
RITZ1S = ["ritz1", "ritz1_selfhosted"]

_C = "struct C\n    a: i64\n    b: i64\n\n"
_E = "enum E\n    A\n    B\n    C\n\n"
_T = "enum E\n    A(i64)\n    B\n    C(i64)\n\n"

# The value the caller sees decides the exit code; a wrong store anywhere
# gives some other number.
_C_CHECK = "    if c.b != 4\n        return 9\n    c.a as i32\n"
_E_CHECK = "    match e\n        E.A => 1\n        E.B => 3\n        E.C => 2\n"
_T_CHECK = "    match e\n        E.A(x) => 1\n        E.B => 3\n        E.C(y) => 2\n"

SHAPES = {
    # The ticket's repro.
    "struct_from_value": _C + """\
fn w(r:& C, v: C)
    r = v

pub fn main() -> i32
    var c = C { a: 1, b: 2 }
    w(@&c, C { a: 3, b: 4 })
""" + _C_CHECK,
    # Compiled on ritz1 before, as a reseat of `r`: c stayed 1.
    "struct_from_borrow": _C + """\
fn w(r:& C, v:& C)
    r = v

pub fn main() -> i32
    var c = C { a: 1, b: 2 }
    var d = C { a: 3, b: 4 }
    w(@&c, @&d)
""" + _C_CHECK,
    # The value reads `r` before the store writes it.
    "struct_literal_reads_self": _C + """\
fn w(r:& C)
    r = C { a: r.b, b: r.a + 3 }

pub fn main() -> i32
    var c = C { a: 1, b: 3 }
    w(@&c)
""" + _C_CHECK,
    "struct_from_call": _C + """\
fn mk() -> C
    C { a: 3, b: 4 }

fn w(r:& C)
    r = mk()

pub fn main() -> i32
    var c = C { a: 1, b: 2 }
    w(@&c)
""" + _C_CHECK,
    "plain_enum": _E + """\
fn w(r:& E)
    r = E.B

pub fn main() -> i32
    var e = E.A
    w(@&e)
""" + _E_CHECK,
    "plain_enum_from_borrow": _E + """\
fn w(r:& E, v:& E)
    r = v

pub fn main() -> i32
    var e = E.A
    var f = E.B
    w(@&e, @&f)
""" + _E_CHECK,
    "tagged_enum_unit": _T + """\
fn w(r:& E)
    r = E.B

pub fn main() -> i32
    var e = E.A(7)
    w(@&e)
""" + _T_CHECK,
    "tagged_enum_payload": _T + """\
fn w(r:& E, n: i64)
    r = E.C(n)

pub fn main() -> i32
    var e = E.A(7)
    w(@&e, 3)
    match e
        E.A(x) => 1
        E.B => 2
        E.C(y) => y as i32
""",
    "tagged_enum_from_borrow": _T + """\
fn w(r:& E, v:& E)
    r = v

pub fn main() -> i32
    var e = E.A(7)
    var f = E.B
    w(@&e, @&f)
""" + _T_CHECK,
    "strview_literal": """\
fn w(r:& StrView)
    r = "abc"

pub fn main() -> i32
    var s: StrView = "hello"
    w(@&s)
    if s.ptr[2] != 99
        return 9
    s.len as i32
""",
    "strview_from_borrow": """\
fn w(r:& StrView, v:& StrView)
    r = v

pub fn main() -> i32
    var s: StrView = "hello"
    var t: StrView = "abc"
    w(@&s, @&t)
    if s.ptr[2] != 99
        return 9
    s.len as i32
""",
    # Width: a plain enum is one byte, the field after it must survive.
    "plain_enum_field_neighbour": _E + """\
struct H
    e: E
    k: u8
    n: i64

fn w(r:& E)
    r = E.B

pub fn main() -> i32
    var h = H { e: E.A, k: 200, n: 5 }
    w(@&h.e)
    if h.k != 200 or h.n != 5
        return 9
    match h.e
        E.A => 1
        E.B => 3
        E.C => 2
""",
    # f32 / f64: the same store, #1668's, covered by the same arm.
    "f64_literal": """\
fn w(r:& f64)
    r = 3.0

pub fn main() -> i32
    var x: f64 = 1.0
    w(@&x)
    x as i32
""",
    "f32_field_neighbour": """\
struct P
    x: f32
    y: f32

fn w(r:& f32)
    r = 3.5

pub fn main() -> i32
    var p = P { x: 1.0, y: 2.25 }
    w(@&p.x)
    if p.y != 2.25
        return 9
    p.x as i32
""",
}

# ritz0 is right; ritz1 refuses or miscompiles.  All READ a `:&` float or
# bool, which #1668 hasn't lowered: the store above is not the problem.
KNOWN_GAPS = {
    "f32_from_borrow": (1668, """\
fn w(r:& f32, v:& f32)
    r = v

pub fn main() -> i32
    var x: f32 = 1.0
    var y: f32 = 3.0
    w(@&x, @&y)
    x as i32
"""),
    "f64_compound": (1668, """\
fn w(r:& f64)
    r += 2.0

pub fn main() -> i32
    var x: f64 = 1.0
    w(@&x)
    x as i32
"""),
    "bool_literal": (1668, """\
fn w(r:& bool)
    r = true

pub fn main() -> i32
    var x: bool = false
    w(@&x)
    if x
        return 3
    1
"""),
}


@pytest.fixture
def run_with(ritz1_bin, tmp_path):
    """_run, by name.  The gate builds ritz1_selfhosted before pytest."""
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _run("ritz0", None, tmp_path, name, program)
        return _run("ritz1", bins[compiler], tmp_path, name, program)
    return go


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(SHAPES))
def test_whole_assign_writes_the_referent(run_with, name, compiler):
    assert run_with(compiler, name, SHAPES[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(KNOWN_GAPS))
def test_ritz0_has_the_known_gaps_right(run_with, name):
    assert run_with("ritz0", name, KNOWN_GAPS[name][1]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize(
    "name",
    [pytest.param(n, marks=pytest.mark.xfail(strict=True, reason=f"AGAST #{KNOWN_GAPS[n][0]}"))
     for n in sorted(KNOWN_GAPS)])
def test_ritz1_known_gaps(run_with, name, compiler):
    assert run_with(compiler, name, KNOWN_GAPS[name][1]) == 3
