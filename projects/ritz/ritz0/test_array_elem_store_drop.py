"""An element store drops the old element; arrays of any rank drop;
a Drop array must be initialised (LARB R39, AGAST #3305, #3376).

LANGUAGE_SPEC §13.6: `a[i] = v`, `g[i][j] = v` and `h.a[i] = v` drop the
element's old value after `v` and the index are evaluated, before `v` is
stored, as a field store does. An array of any rank drops element by element
in index order. §3.3: so every element always holds a value, a local array
whose element type has drop glue must have an initialiser.

`S`'s drop appends its `x` to `D` as a decimal digit string (`D * 10 + x`),
so `D` spells out both which elements dropped and in what order. Each program
exits 42 when `D` is what the spec says, otherwise `D % 200` (never 42).

Every row runs on ritz0, ritz1 and ritz1_selfhosted (ritz1: AGAST #3377).
"""

import re

import pytest
from test_ref_into_value import COMPILERS, _compile, _run

pytestmark = pytest.mark.integration

PRELUDE = """\
var D: i64 = 0

struct S
    x: i64

impl Drop for S
    fn drop(self:& S)
        D = D * 10 + self.x

struct H
    a: [2]S
    n: i32

fn mk(x: i64) -> S
    D = D * 10 + 8
    return S { x: x }

fn idx(i: i64) -> i64
    D = D * 10 + 7
    return i

fn verdict(want: i64) -> i32
    if D == want
        return 42
    let r = (D % 200) as i32
    if r == 42
        return 43
    return r

"""

RUNS = {
    # #3305's repro: the old x=2 drops at the store, then 1 and 30 at the
    # end: digits 2, 1, then 30 added on (D * 10 + 30).
    "one_rank1_store": ("""\
fn one()
    var a: [2]S = [S { x: 1 }, S { x: 2 }]
    a[1] = S { x: 30 }
""", "one()", (2 * 10 + 1) * 10 + 30),
    # The old element (2) drops after the index (7) is evaluated, and after
    # v (8) is; 1 and 3 drop at the end.  Which of v and the index goes first
    # is not pinned: ritz0 evaluates v first, ritz1 the index (AGAST #3432).
    "store_after_index": ("""\
fn f()
    var a: [2]S = [S { x: 1 }, S { x: 2 }]
    a[idx(1)] = S { x: 3 }
""", "f()", 7213),
    "store_after_value": ("""\
fn f()
    var a: [2]S = [S { x: 1 }, S { x: 2 }]
    a[1] = mk(3)
""", "f()", 8213),
    # As g[i][j] = v.
    "rank2_store_after_index_and_value": ("""\
fn f()
    var g: [1][2]S = [ [S { x: 1 }, S { x: 2 }] ]
    g[0][idx(1)] = S { x: 3 }
    g[0][0] = mk(4)
""", "f()", 72814 * 10 + 3),
    # Rank 2 at scope end: index order, g[0][0] .. g[1][1].
    "rank2_scope_end": ("""\
fn f()
    var g: [2][2]S = [ [S { x: 1 }, S { x: 2 }], [S { x: 3 }, S { x: 4 }] ]
""", "f()", 1234),
    # Rank 3 too.
    "rank3_scope_end": ("""\
fn f()
    var g: [2][1][2]S = [ [ [S { x: 1 }, S { x: 2 }] ], [ [S { x: 3 }, S { x: 4 }] ] ]
""", "f()", 1234),
    # g[1][0] = v drops the old g[1][0] (3) at the store.
    "rank2_store": ("""\
fn f()
    var g: [2][2]S = [ [S { x: 1 }, S { x: 2 }], [S { x: 3 }, S { x: 4 }] ]
    g[1][0] = S { x: 5 }
""", "f()", 31254),
    # A field's array: h.a[0] = v drops the old h.a[0] (1).
    "field_array_store": ("""\
fn f()
    var h: H = H { a: [S { x: 1 }, S { x: 2 }], n: 0 }
    h.a[0] = S { x: 5 }
""", "f()", 152),
    # A moved-out array owns nothing: storing into it drops nothing, and it
    # owns its elements again. The callee drops the moved one (1, 2).
    "store_into_moved_array_drops_nothing": ("""\
fn eat(a: [2]S)
    D = D * 10 + 9

fn f()
    var a: [2]S = [S { x: 1 }, S { x: 2 }]
    eat(a)
    a = [S { x: 3 }, S { x: 4 }]
    a[0] = S { x: 5 }
""", "f()", 9123 * 100 + 54),
    # Through a raw pointer, nothing owns the old element (as `p.f = v`,
    # AGAST #2179): only the local's own drops run.
    "store_through_pointer_drops_nothing": ("""\
fn put(p: *S)
    p[0] = S { x: 5 }

fn f()
    var a: [1]S = [S { x: 1 }]
    put(@a[0])
""", "f()", 5),
}


def _source(body, call, want):
    return (PRELUDE + body + "\npub fn main() -> i32\n    " + call
            + f"\n    return verdict({want})\n")


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_element_store_and_nd_drops(tmp_path, compiler, name):
    body, call, want = RUNS[name]
    rc = _run(compiler, tmp_path, name, _source(body, call, want))
    assert rc == 42, f"{compiler}: {name}: D % 200 == {rc}, spec says D == {want}"


# `f()[i] = v`, `f` returning a `*T`: the store goes through the pointer
# `f()` returns, and (LARB R61) evaluates `f()` (6), then the index (7), then
# `v` (8).  ritz1 evaluated `f()[i]` as a value and stored through it: a
# SIGSEGV (AGAST #3442).  Through a raw pointer nothing owns the old element,
# so it doesn't drop (as `p[i] = v`); the local's own 1 and 3 drop at the end.
CALL_BASE = {
    # A `*i32`: a 4-byte stride and store, the next element untouched.
    "scalar": ("""\
var P: *i32 = null

fn arr() -> *i32
    D = D * 10 + 6
    return P

fn val(x: i32) -> i32
    D = D * 10 + 8
    return x

fn f()
    var a: [3]i32 = [1, 2, 4]
    P = @a[0]
    arr()[idx(1)] = val(3)
    D = ((D * 10 + a[0] as i64) * 10 + a[1] as i64) * 10 + a[2] as i64
""", "f()", 678134),
    "struct": ("""\
var P: *S = null

fn arr() -> *S
    D = D * 10 + 6
    return P

fn f()
    var a: [2]S = [S { x: 1 }, S { x: 2 }]
    P = @a[0]
    arr()[idx(1)] = mk(3)
""", "f()", 67813),
    # A `**i32`: the element stored is a pointer.
    "pointer": ("""\
var Q: **i32 = null

fn arr() -> **i32
    D = D * 10 + 6
    return Q

fn val(p: *i32) -> *i32
    D = D * 10 + 8
    return p

fn f()
    var x: i32 = 1
    var y: i32 = 3
    var ps: [2]*i32 = [@x, @x]
    Q = @ps[0]
    arr()[idx(1)] = val(@y)
    D = (D * 10 + *ps[0] as i64) * 10 + *ps[1] as i64
""", "f()", 67813),
}


@pytest.mark.parametrize("compiler", [
    pytest.param(c, marks=pytest.mark.xfail(
        strict=True, reason="AGAST #3482: ritz0 evaluates v before the place"))
    if c == "ritz0" else c for c in COMPILERS])
@pytest.mark.parametrize("name", sorted(CALL_BASE))
def test_store_into_call_result(tmp_path, compiler, name):
    body, call, want = CALL_BASE[name]
    rc = _run(compiler, tmp_path, f"call_base_{name}", _source(body, call, want))
    assert rc == 42, f"{compiler}: {name}: D % 200 == {rc}, spec says D == {want}"


# Reading `f()[i]`, `f` returning a `*T`, loads the element at T's stride and
# width, as `p[i]` does (f() appends 6).  ritz1 had no arm for a
# call base and read one byte at `f() + i`, whatever T was: `arr()[1]` over a
# `*i32` read 0, byte 1 of the i32 1 (AGAST #3527).
CALL_BASE_LOAD = {
    # A `*i32`: 4-byte stride and width, and sign-extended (-3).
    "scalar": ("""\
var P: *i32 = null

fn arr() -> *i32
    D = D * 10 + 6
    return P

fn f()
    var a: [3]i32 = [1, -3, 4]
    P = @a[0]
    let v: i64 = arr()[1] as i64
    D = D * 10 + (v + 5)
""", "f()", 62),
    # A `*C`: the `%C` at a stride of sizeof(C), copied out whole.
    "struct": ("""\
struct C
    x: i32
    y: i64

var P: *C = null

fn arr() -> *C
    D = D * 10 + 6
    return P

fn f()
    var a: [2]C = [C { x: 1, y: 2 }, C { x: 3, y: 4 }]
    P = @a[0]
    let c: C = arr()[1]
    D = (D * 10 + c.x as i64) * 10 + c.y
""", "f()", 634),
    # A `**i32`: the element read is a pointer.
    "pointer": ("""\
var Q: **i32 = null

fn arr() -> **i32
    D = D * 10 + 6
    return Q

fn f()
    var x: i32 = 1
    var y: i32 = 3
    var ps: [2]*i32 = [@x, @y]
    Q = @ps[0]
    let p: *i32 = arr()[1]
    D = D * 10 + *p as i64
""", "f()", 63),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CALL_BASE_LOAD))
def test_load_from_call_result(tmp_path, compiler, name):
    body, call, want = CALL_BASE_LOAD[name]
    rc = _run(compiler, tmp_path, f"call_load_{name}", _source(body, call, want))
    assert rc == 42, f"{compiler}: {name}: D % 200 == {rc}, spec says D == {want}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_struct_load_from_call_result_is_a_copy_only(tmp_path, compiler):
    """A `*C` call's `%C` element where a number goes is refused at the
    element, as `p[i]` is (each compiler in its own words)."""
    body = ("struct C\n    x: i64\n\nvar P: *C = null\n\nfn arr() -> *C\n    return P\n\n"
            "fn f()\n    let n: i64 = arr()[0] + 1\n")
    comp, ll, _ = _compile(compiler, tmp_path, "call_load_struct_int", _source(body, "f()", 0))
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted a struct where an i64 goes:\n{out[-1000:]}"
    assert not ll.exists()
    assert "Traceback" not in out, out[-2000:]
    where = f"main.ritz:{PRELUDE.count(chr(10)) + 10}:18:"
    assert where in out, f"{compiler}: wanted the error at {where}:\n{out[-2000:]}"


# §3.3: a Drop array local needs an initialiser; the error is at the name.
UNINIT = {
    "rank1": "    var a: [2]S\n",
    "rank2": "    var a: [2][2]S\n",
    "field_holder": "    var a: [2]H\n",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(UNINIT))
def test_uninitialised_drop_array_refused(tmp_path, compiler, name):
    body = "fn f()\n    let k = 1\n" + UNINIT[name]
    comp, ll, _ = _compile(compiler, tmp_path, name, _source(body, "f()", 0))
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted an uninitialised Drop array:\n{out[-1000:]}"
    assert not ll.exists()
    assert "Traceback" not in out, out[-2000:]
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    where = f"{PRELUDE.count(chr(10)) + 3}:9"
    assert (where, "`a` must be initialised: its elements have `drop`") in found, \
        f"{compiler}: wanted the error at {where}:\n{out[-2000:]}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_uninitialised_copy_array_and_drop_struct_accepted(tmp_path, compiler):
    """Only an array of a drop-glue type needs one: a `[2]i32`, and a plain
    `var b: S` (the constructor idiom, 13 in the corpus), stay as they were."""
    body = "fn f()\n    var a: [2]i32\n    a[0] = 1\n    var b: S\n    b.x = 4\n"
    comp, ll, _ = _compile(compiler, tmp_path, "uninit_ok", _source(body, "f()", 4))
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler}:\n{out[-2000:]}"
