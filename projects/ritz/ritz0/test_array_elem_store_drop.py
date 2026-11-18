"""An element store drops the old element; arrays of any rank drop;
a Drop array must be initialised (LARB R39, AGAST #3305, #3376).

LANGUAGE_SPEC §13.6: `a[i] = v`, `g[i][j] = v` and `h.a[i] = v` evaluate the
place (`a`, then each index, left to right), then `v` (LARB R61); then the
element's old value drops and `v` is stored, as a field store does. An array of any rank drops element by element
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
    # LARB R61: the index (7), then v (8), left to right; then the old
    # element (2) drops and v is stored.  1 and 3 drop at the end.
    "store_after_index_and_value": ("""\
fn f()
    var a: [2]S = [S { x: 1 }, S { x: 2 }]
    a[idx(1)] = mk(3)
""", "f()", 78213),
    # As g[i][j] = v: i (7) before j (6) before v (8).  The old g[0][1] (2)
    # drops, then g[0][0] (1) and the new g[0][1] (3) at the end.
    "rank2_store_after_index_and_value": ("""\
fn jdx(j: i64) -> i64
    D = D * 10 + 6
    return j

fn f()
    var g: [1][2]S = [ [S { x: 1 }, S { x: 2 }] ]
    g[idx(0)][jdx(1)] = mk(3)
""", "f()", 768213),
    # As h.a[i] = v: the index (7), then v (8); the old h.a[0] (1) drops.
    "field_array_store_after_index_and_value": ("""\
fn f()
    var h: H = H { a: [S { x: 1 }, S { x: 2 }], n: 0 }
    h.a[idx(0)] = mk(5)
""", "f()", 78152),
    # The same order in a match arm (an assignment expression): the index
    # (7), then v (8); a[1] then holds 3.
    "match_arm_store_after_index_and_value": ("""\
fn val(x: i64) -> i64
    D = D * 10 + 8
    return x

fn f()
    var a: [2]i64 = [1, 2]
    let o: Option<i64> = Some(1)
    match o
        Some(k) => a[idx(k)] = val(3)
        None => D = 0
    D = D * 10 + a[1]
""", "f()", 783),
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


@pytest.mark.parametrize("compiler", COMPILERS)
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
    # A call index: base (6), then index (7), LARB R61.  ritz0 ran the index
    # first (AGAST #3562): 762.
    "index_order": ("""\
var P: *i32 = null

fn arr() -> *i32
    D = D * 10 + 6
    return P

fn f()
    var a: [3]i32 = [1, -3, 4]
    P = @a[0]
    let v: i64 = arr()[idx(1)] as i64
    D = D * 10 + (v + 5)
""", "f()", 672),
    # The same through a method's `*i32` result.
    "method_index_order": ("""\
var P: *i32 = null

struct B
    n: i32

impl B
    fn arr(self: @B) -> *i32
        D = D * 10 + 6
        return P

fn f()
    var a: [3]i32 = [1, -3, 4]
    P = @a[0]
    var b: B = B { n: 0 }
    let v: i64 = b.arr()[idx(1)] as i64
    D = D * 10 + (v + 5)
""", "f()", 672),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CALL_BASE_LOAD))
def test_load_from_call_result(tmp_path, compiler, name):
    body, call, want = CALL_BASE_LOAD[name]
    rc = _run(compiler, tmp_path, f"call_load_{name}", _source(body, call, want))
    assert rc == 42, f"{compiler}: {name}: D % 200 == {rc}, spec says D == {want}"


# `b.arr()[i]`: the same, through a method's `*T` / `**T` result.  ritz1
# missed the method base (AGAST #4060) and read a byte at `b.arr() + i`:
# `b.arr()[1]` over a `*i32` read 0.  CALL_BASE_LOAD's rows with a free
# `arr()`, made a method of `B`.
def _arr_as_method(body):
    """`fn arr() -> T` (one level in) as `impl B`'s `fn arr(self: @B) -> T`."""
    body = re.sub(r"^fn arr\(\) -> (.*)$", r"struct B\n    n: i32\n\nimpl B\n    fn arr(self: @B) -> \1",
                  body, flags=re.MULTILINE)
    return re.sub(r"^    D = D \* 10 \+ 6\n    return ([PQ])$", r"        D = D * 10 + 6\n        return \1",
                  body, flags=re.MULTILINE)


def _method_load_base(body):
    body = re.sub(r"^(    let .* = )arr\(\)\[", r"    var b: B = B { n: 0 }\n\1b.arr()[",
                  _arr_as_method(body), flags=re.MULTILINE)
    assert "b.arr()[" in body and "impl B" in body, body
    return body


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(n for n, (b, _, _) in CALL_BASE_LOAD.items() if "\nfn arr() ->" in b))
def test_load_from_method_result(tmp_path, compiler, name):
    body, call, want = CALL_BASE_LOAD[name]
    rc = _run(compiler, tmp_path, f"method_load_{name}", _source(_method_load_base(body), call, want))
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


# `b.arr()[i] = v`: the same, through a method's `*T` / `**T` result.  ritz1
# missed the method base (AGAST #3528) and stored through the VALUE of
# `b.arr()[i]`: a SIGSEGV.  CALL_BASE's rows, with `arr` a method of `B`.
def _method_base(body):
    body = _arr_as_method(body).replace("    arr()[", "    var b: B = B { n: 0 }\n    b.arr()[")
    assert "b.arr()[" in body and "impl B" in body, body
    return body


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CALL_BASE))
def test_store_into_method_result(tmp_path, compiler, name):
    body, call, want = CALL_BASE[name]
    rc = _run(compiler, tmp_path, f"method_base_{name}", _source(_method_base(body), call, want))
    assert rc == 42, f"{compiler}: {name}: D % 200 == {rc}, spec says D == {want}"


# `(e as *T)[i] = v` and `(q + k)[i] = v`: a cast or pointer-arithmetic base
# stores through the `*T` it names, base, index, then value (LARB R61).
# ritz1 stored through the VALUE of `x[i]` (AGAST #3565): a SIGSEGV.  One row
# per pointee shape and base kind; `arr()` (6) roots the arithmetic rows so
# the base's place in the order shows.
EXPR_BASE = {
    "cast_scalar": ("""\
var P: i64 = 0

fn base() -> i64
    D = D * 10 + 6
    return P

fn val(x: i32) -> i32
    D = D * 10 + 8
    return x

fn f()
    var a: [3]i32 = [1, 2, 4]
    P = @a[0] as i64
    (base() as *i32)[idx(1)] = val(3)
    D = ((D * 10 + a[0] as i64) * 10 + a[1] as i64) * 10 + a[2] as i64
""", "f()", 678134),
    "cast_struct": ("""\
var P: i64 = 0

fn base() -> i64
    D = D * 10 + 6
    return P

fn f()
    var a: [2]S = [S { x: 1 }, S { x: 2 }]
    P = @a[0] as i64
    (base() as *S)[idx(1)] = mk(3)
""", "f()", 67813),
    "arith_scalar": ("""\
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
    (arr() + 1)[idx(1)] = val(3)
    D = ((D * 10 + a[0] as i64) * 10 + a[1] as i64) * 10 + a[2] as i64
""", "f()", 678123),
    # A `*S` local root: `q + 1` names a[1].
    "arith_struct": ("""\
fn f()
    var a: [2]S = [S { x: 1 }, S { x: 2 }]
    let q: *S = @a[0]
    (q + 1)[idx(0)] = mk(3)
""", "f()", 7813),
    # `**i32`: the element stored is a pointer, through a cast and through
    # arithmetic on a `**i32` local.
    "pointer": ("""\
var P: i64 = 0

fn base() -> i64
    D = D * 10 + 6
    return P

fn val(p: *i32) -> *i32
    D = D * 10 + 8
    return p

fn f()
    var x: i32 = 1
    var y: i32 = 3
    var ps: [3]*i32 = [@x, @x, @x]
    P = @ps[0] as i64
    (base() as **i32)[idx(1)] = val(@y)
    let q: **i32 = @ps[0]
    (q + 1)[1] = @y
    D = ((D * 10 + *ps[0] as i64) * 10 + *ps[1] as i64) * 10 + *ps[2] as i64
""", "f()", 678133),
    # A global root under arithmetic, and a parenthesised `*i32` local.
    "global_and_name_roots": ("""\
var G: *i32 = null

fn f()
    var a: [3]i32 = [1, 2, 4]
    G = @a[0]
    let p: *i32 = @a[0]
    (G + 1)[idx(1)] = 5
    (p)[0] = 3
    D = ((D * 10 + a[0] as i64) * 10 + a[1] as i64) * 10 + a[2] as i64
""", "f()", 7325),
    # `(@a[0] + 1)[i]`: arithmetic on an `@T` root (LARB R20), which
    # Sema refused and ritz1 couldn't type (AGAST #3757).  `@a[0] + 1` names
    # a[1]; as through any pointer base, the old element isn't dropped.
    "addr_arith_scalar": ("""\
fn val(x: i32) -> i32
    D = D * 10 + 8
    return x

fn f()
    var a: [3]i32 = [1, 2, 4]
    (@a[0] + 1)[idx(1)] = val(3)
    D = ((D * 10 + a[0] as i64) * 10 + a[1] as i64) * 10 + a[2] as i64
""", "f()", 78123),
    "addr_arith_struct": ("""\
fn f()
    var a: [3]S = [S { x: 1 }, S { x: 2 }, S { x: 4 }]
    (@a[0] + 1)[idx(0)] = mk(3)
""", "f()", 78134),
    # A global array root, and a `[N]i64` param's (its own copy: the store
    # shows in the sum g returns).
    "addr_arith_global_and_param": ("""\
var G: [3]u8

fn g(b: [3]i64) -> i64
    (@b[0] + 2)[0] = 9
    b[0] + b[1] + b[2]

fn f()
    G[0] = 1
    G[1] = 2
    G[2] = 4
    (@G[1] + 1)[idx(0)] = 5
    D = ((D * 10 + G[0] as i64) * 10 + G[1] as i64) * 10 + G[2] as i64
    let b: [3]i64 = [1, 2, 4]
    D = D * 100 + g(b)
""", "f()", 712512),
    # `(p as @&T)[i]`: a reference cast's pointee, which the parser kept
    # only for a struct (#3443); ritz1 emitted invalid IR (AGAST #3757).
    "ref_cast_scalar": ("""\
fn val(x: i32) -> i32
    D = D * 10 + 8
    return x

fn f()
    var a: [3]i32 = [1, 2, 4]
    let p: *i32 = @a[0]
    (p as @&i32)[idx(1)] = val(5)
    D = ((D * 10 + a[0] as i64) * 10 + a[1] as i64) * 10 + a[2] as i64
""", "f()", 78154),
    "ref_cast_struct": ("""\
fn f()
    var a: [2]S = [S { x: 1 }, S { x: 2 }]
    let p: *S = @a[0]
    (p as @&S)[idx(1)] = mk(3)
""", "f()", 7813),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(EXPR_BASE))
def test_store_into_cast_or_arith_base(tmp_path, compiler, name):
    body, call, want = EXPR_BASE[name]
    rc = _run(compiler, tmp_path, f"expr_base_{name}", _source(body, call, want))
    assert rc == 42, f"{compiler}: {name}: D % 200 == {rc}, spec says D == {want}"


# Reading `(e as **T)[i]` loads the `*T` at element i, a pointer's stride, as
# the store above writes one, evaluating `e` once (6).  ritz1 had no arm for a
# cast base and read one byte at `e + i` as the pointer: a SIGSEGV
# (AGAST #3756).  §13.6 orders an assignment's place; a read's isn't pinned.
CAST_PTR_PTR_LOAD = """\
var P: i64 = 0

fn base() -> i64
    D = D * 10 + 6
    return P

fn f()
    var x: i32 = 1
    var y: i32 = 3
    var z: i32 = 4
    var ps: [3]*i32 = [@x, @y, @z]
    P = @ps[0] as i64
    let r: *i32 = (base() as **i32)[1]
    let t: *i32 = (P as **i32)[2]
    D = (D * 10 + *r as i64) * 10 + *t as i64
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_load_from_cast_ptr_ptr_base(tmp_path, compiler):
    rc = _run(compiler, tmp_path, "cast_pp_load", _source(CAST_PTR_PTR_LOAD, "f()", 634))
    assert rc == 42, f"{compiler}: D % 200 == {rc}, spec says D == 634"


# Reading `(e as *T)[i]` and `(q + k)[i]` loads element i at the pointee's
# stride and width, as the stores above write one: a scalar, a `%S` (a copy
# only) or, through a `**T`, a pointer.  ritz1 read one byte at `base + i`:
# 300's byte 1, an i64 into a `%S` slot (clang refused it), or a SIGSEGV
# (AGAST #3833).
EXPR_BASE_LOAD = {
    # `base()` is evaluated once (6); element 1 is 7, not byte 1 of 300.
    "cast_scalar": ("""\
var P: i64 = 0

fn base() -> i64
    D = D * 10 + 6
    return P

fn f()
    var a: [3]i32 = [300, 7, 9]
    P = @a[0] as i64
    let v: i32 = (base() as *i32)[1]
    D = D * 10 + v as i64
""", "f()", 67),
    "cast_struct": ("""\
struct V
    x: i64
    y: i64

var P: i64 = 0

fn f()
    var a: [2]V = [V { x: 1, y: 2 }, V { x: 3, y: 4 }]
    P = @a[0] as i64
    let v: V = (P as *V)[1]
    D = (D * 10 + v.x) * 10 + v.y
""", "f()", 34),
    "arith_scalar": ("""\
fn f()
    var a: [3]i32 = [300, 7, 9]
    let q: *i32 = @a[0]
    D = D * 10 + (q + 1)[1] as i64
""", "f()", 9),
    # AGAST #3757: the roots the stores above gained, read.
    "addr_arith_and_ref_cast": ("""\
fn f()
    var a: [3]i32 = [300, 7, 9]
    let p: *i32 = @a[0]
    D = (D * 10 + (@a[0] + 1)[1] as i64) * 10 + (p as @&i32)[1] as i64
""", "f()", 97),
    "arith_pointer": ("""\
fn f()
    var x: i32 = 1
    var y: i32 = 3
    var z: i32 = 5
    var ps: [3]*i32 = [@x, @y, @z]
    let q: **i32 = @ps[0]
    let r: *i32 = (q + 1)[1]
    D = D * 10 + *r as i64
""", "f()", 5),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(EXPR_BASE_LOAD))
def test_load_from_cast_or_arith_base(tmp_path, compiler, name):
    body, call, want = EXPR_BASE_LOAD[name]
    rc = _run(compiler, tmp_path, f"expr_base_load_{name}", _source(body, call, want))
    assert rc == 42, f"{compiler}: {name}: D % 200 == {rc}, spec says D == {want}"


# The `%S` element is a copy only: as an integer it is refused at the element,
# as `p[i]` with `p: *S` is (AGAST #3188), not handed to clang.
STRUCT_ELEM_AS_INT = {
    "ritz0": "cannot cast struct `V` to `i64`: a struct is not an integer "
             "(read one of its fields, or take its address with @)",
    "ritz1": "a whole struct is not a value here in ritz1 (copy it into a `let s: S`, or read its fields)",
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_struct_elem_of_cast_base_as_int_refused(tmp_path, compiler):
    body = "struct V\n    x: i64\n    y: i64\n\nfn f(p: i64)\n    let n: i64 = (p as *V)[1] as i64\n"
    comp, ll, _ = _compile(compiler, tmp_path, "cast_struct_as_int", _source(body, "f(0)", 0))
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted a whole `%V` as an i64:\n{out[-1000:]}"
    assert not ll.exists()
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    where = f"{PRELUDE.count(chr(10)) + 6}:19"
    msg = STRUCT_ELEM_AS_INT[compiler if compiler == "ritz0" else "ritz1"]
    assert found == [(where, msg)], f"{compiler}: wanted {msg!r} at {where}:\n{out[-2000:]}"


# `*((e as **T) + k)` reads the same `*T` as `(e as **T)[k]`: the sum strides
# a pointer's width and the deref loads a pointer (AGAST #3834; ritz1 loaded
# from `e + k` bytes, a SIGSEGV).  `*(e as **T)` is element 0.
CAST_PTR_PTR_DEREF = """\
var P: i64 = 0

fn base() -> i64
    D = D * 10 + 6
    return P

fn f()
    var x: i32 = 1
    var y: i32 = 3
    var z: i32 = 4
    var ps: [3]*i32 = [@x, @y, @z]
    P = @ps[0] as i64
    let r: *i32 = *((base() as **i32) + 1)
    let t: *i32 = *((P as **i32) + 2)
    let u: *i32 = *(P as **i32)
    D = ((D * 10 + *r as i64) * 10 + *t as i64) * 10 + *u as i64
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_deref_cast_ptr_ptr_sum(tmp_path, compiler):
    rc = _run(compiler, tmp_path, "cast_pp_deref", _source(CAST_PTR_PTR_DEREF, "f()", 6341))
    assert rc == 42, f"{compiler}: D % 200 == {rc}, spec says D == 6341"


# A scalar base reached that generic path too: refused in ritz0's words for
# `n[i] = v`, on every compiler (ritz0 raised a traceback until AGAST #3754),
# at the `[` (index_scalar_check, AGAST #3755).  `(@a[0] + 1)[i]` was refused
# here on ritz1 until it stored through it (AGAST #3757, EXPR_BASE).
EXPR_BASE_REFUSED = {
    "int_arith": ("    (n + 1)[0] = 5\n", 12, "`i64` can't be indexed: it doesn't implement `Index` (§7.8)"),
    "int_cast": ("    (n as i64)[0] = 5\n", 15, "`i64` can't be indexed: it doesn't implement `Index` (§7.8)"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(EXPR_BASE_REFUSED))
def test_store_into_untyped_base_refused(tmp_path, compiler, name):
    line, col, msg = EXPR_BASE_REFUSED[name]
    body = "fn f()\n    var a: [2]i32 = [1, 2]\n    var n: i64 = 0\n" + line
    comp, ll, _ = _compile(compiler, tmp_path, f"expr_base_refused_{name}", _source(body, "f()", 0))
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted {line.strip()!r}:\n{out[-1000:]}"
    assert not ll.exists()
    assert "Traceback" not in out, out[-2000:]
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    where = f"{PRELUDE.count(chr(10)) + 4}:{col}"
    assert (where, msg) in found, f"{compiler}: wanted {msg!r} at {where}:\n{out[-2000:]}"
    assert len(found) == 1, f"{compiler}: reported more than once:\n{out[-2000:]}"


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


# Storing into an element of a moved-out array is a use of the moved value
# (AGAST #3434): `h.a` as `a`, though `h` itself still holds `n`.  Each row:
# body, the moved path, the store's line:col and the move's, both as lines
# into f's body (1 = its first line); then how many errors.  In the loop the
# second iteration stores into, then moves, the `h.a` the first one moved.
MOVED_STORE = {
    "local": ("""\
    var a: [2]S = [S { x: 1 }, S { x: 2 }]
    eat(a)
    a[0] = S { x: 5 }
""", "a", (3, 5), (2, 9), 1),
    "field": ("""\
    var h: H = H { a: [S { x: 1 }, S { x: 2 }], n: 0 }
    eat(h.a)
    h.a[0] = S { x: 5 }
""", "h.a", (3, 5), (2, 9), 1),
    "field_in_loop": ("""\
    var h: H = H { a: [S { x: 1 }, S { x: 2 }], n: 0 }
    var i: i32 = 0
    while i < 2
        h.a[0] = S { x: 5 }
        eat(h.a)
        i += 1
""", "h.a", (4, 9), (5, 13), 2),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(MOVED_STORE))
def test_store_into_moved_array_refused(tmp_path, compiler, name):
    body, what, (sl, sc), (ml, mc), errors = MOVED_STORE[name]
    src = "fn eat(a: [2]S)\n    D = D * 10 + 9\n\nfn f()\n" + body
    comp, ll, _ = _compile(compiler, tmp_path, f"moved_store_{name}", _source(src, "f()", 0))
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted a store into moved `{what}`:\n{out[-1000:]}"
    assert not ll.exists()
    assert "Traceback" not in out, out[-2000:]
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    f0 = PRELUDE.count("\n") + 4  # the `fn f()` line
    msg = f"use of moved value: `{what}` (moved at "
    hit = [m for loc, m in found if loc == f"{f0 + sl}:{sc}" and m.startswith(msg)
           and m.endswith(f"main.ritz:{f0 + ml}:{mc})")]
    assert hit, f"{compiler}: wanted {f0 + sl}:{sc}: {msg}..{f0 + ml}:{mc}):\n{out[-2000:]}"
    assert len(found) == errors, f"{compiler}: wanted {errors} error(s):\n{out[-2000:]}"
