"""AGAST #2566: a field of a by-value struct array element, `a[i].f` with `a: [N]S`.

    struct P
        n: i64
        p: *i32
    var a: [2]P
    a[1].p = @x[0]
    *(a[1].p + 1)          # ritz0 20, ritz1 0: the `+` stepped one byte, SILENT

member_field_def gave `a[i].f` no StructField when `a` held S by value (it took
`[N]*S` only, #2332), so anything typing through it missed: the `+` stride, and
#2564's Vec-field element path, so `a[i].vf[j].f` stayed "unhandled EXPR_MEMBER".

ritz0 is the oracle: 0 on every row.  A check returns its own number when it
fails, so a red cell says which access broke.
"""

import pytest

from test_ritz1_for_header import COMPILERS, compile_with, run_with  # noqa: F401  (fixtures)

# `n` first puts `p` off offset 0.  Q is the `*S` pointee: 16 bytes, so a byte
# stride or an 8-byte one both show.
_TYPES = """\
import ritzlib.gvec

struct Q
    u: i64
    w: i64

struct P
    n: i64
    b: *i8
    p: *i32
    l: *i64
    q: *Q

struct H
    m: i64
    a: [2]P

"""

_ARRAYS = """\
    var xb: [3]i8 = [1, 2, 3]
    var xi: [3]i32 = [10, 20, 30]
    var xl: [3]i64 = [100, 200, 300]
    var xq: [3]Q
    xq[0] = Q { u: 1, w: 2 }
    xq[1] = Q { u: 3, w: 4 }
    xq[2] = Q { u: 5, w: 6 }
"""

_POINT = """\
    {a}[1].n = 7
    {a}[1].b = @xb[0]
    {a}[1].p = @xi[0]
    {a}[1].l = @xl[0]
    {a}[1].q = @xq[0]
"""

# 1-4 each pointee width at a constant offset; 5-6 a computed element and offset;
# 7 a store through the stepped pointer.
_STRIDE = """\
    if *({a}[1].b + 1) != 2
        return 1
    if *({a}[1].p + 1) != 20
        return 2
    if *({a}[1].l + 2) != 300
        return 3
    if (*({a}[1].q + 1)).w != 4
        return 4
    var i: i64 = 1
    var k: i64 = 2
    if *({a}[i].p + k) != 30
        return 5
    if *({a}[i - 1 + 1].l + k - 1) != 200
        return 6
    *({a}[i].p + 1) = 21
    if xi[1] != 21
        return 7
    return 0
"""

_HEAD = _TYPES + "var g: [2]P\nvar gh: H\n\n"


def _main(a: str, setup: str = "") -> str:
    return (_HEAD + "pub fn main() -> i32\n" + _ARRAYS + setup + _POINT.format(a=a)
            + _STRIDE.format(a=a))


def _in_fn(param: str, a: str, arg: str, setup: str, c: str = "c") -> str:
    # The pointers are set in main and read in f, through the param.
    return (_HEAD + f"fn f(x: {param}, xi: *i32) -> i32\n"
            + _STRIDE.replace("xi[1]", "*(xi + 1)").format(a=a) + "\n"
            + "pub fn main() -> i32\n" + _ARRAYS + setup + _POINT.format(a=c)
            + f"    return f({arg}, @xi[0])\n")


STRIDES = {
    "local": _main("a", "    var a: [2]P\n"),
    "global": _main("g"),
    "local_field": _main("h.a", "    var h: H\n"),
    "global_field": _main("gh.a"),
    "array_ref_param": _in_fn("@[2]P", "x", "@c", "    var c: [2]P\n"),
    "array_mut_ref_param": _in_fn("@&[2]P", "x", "@&c", "    var c: [2]P\n"),
    "holder_ref_param": _in_fn("@H", "x.a", "@hh", "    var hh: H\n", "hh.a"),
    "holder_mut_ref_param": _in_fn("@&H", "x.a", "@&hh", "    var hh: H\n", "hh.a"),
    "holder_ptr_param": _in_fn("*H", "x.a", "@hh", "    var hh: H\n", "hh.a"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(STRIDES))
def test_pointer_field_of_an_array_element_strides_by_its_pointee(run_with, name, compiler):
    assert run_with(compiler, name, STRIDES[name]) == 0


# `a[i].edges[j].k` with `a: [N]T`, `T { edges: Vec<E> }`: #2564's shape one level out.
_VTYPES = """\
import ritzlib.gvec

struct E
    y: f32
    k: i32

impl E
    pub fn step(self:& E)
        self.k = self.k + 100

    pub fn get(self: @E) -> i32
        self.k

struct T
    n: i64
    edges: Vec<E>

struct H
    m: i64
    a: [2]T

var g: [2]T
var gh: H

fn fill(t: *T)
    t.n = 9
    t.edges = vec_new<E>()
    t.edges.push(E { y: 0.5, k: 1 })
    t.edges.push(E { y: 1.5, k: 2 })

"""

# 1 read; 2 store; 3 `+=`; 4 a mutating method; 5 a shared one; 6 `edges.data + 1`
# strides by E (it stepped bytes when #2564 first took this); 7 the neighbour.
_VCHECK = """\
    var i: i64 = 1
    if {a}[i].edges[1].k != 2
        return 1
    {a}[i].edges[0].k = 40
    if {a}[1].edges[0].k != 40
        return 2
    {a}[i].edges[1].k += 3
    if {a}[1].edges[1].k != 5
        return 3
    {a}[i].edges[1].step()
    if {a}[1].edges[1].k != 105
        return 4
    if {a}[i].edges[0].get() != 40
        return 5
    if (*({a}[i].edges.data + 1)).k != 105
        return 6
    if {a}[1].n != 9 or {a}[1].edges.len() != 2
        return 7
    return 0
"""


def _vmain(a: str, setup: str, holder: str) -> str:
    return (_VTYPES + "pub fn main() -> i32\n" + setup + f"    fill(@{holder}[1])\n"
            + _VCHECK.format(a=a))


def _vfn(param: str, a: str, arg: str, setup: str, holder: str) -> str:
    return (_VTYPES + f"fn f(x: {param}) -> i32\n" + _VCHECK.format(a=a) + "\n"
            + "pub fn main() -> i32\n" + setup + f"    fill(@{holder}[1])\n"
            + f"    return f({arg})\n")


VEC_FIELDS = {
    "local": _vmain("a", "    var a: [2]T\n", "a"),
    "global": _vmain("g", "", "g"),
    "local_field": _vmain("h.a", "    var h: H\n", "h.a"),
    "global_field": _vmain("gh.a", "", "gh.a"),
    "array_mut_ref_param": _vfn("@&[2]T", "x", "@&c", "    var c: [2]T\n", "c"),
    "holder_mut_ref_param": _vfn("@&H", "x.a", "@&hh", "    var hh: H\n", "hh.a"),
    "holder_ptr_param": _vfn("*H", "x.a", "@hh", "    var hh: H\n", "hh.a"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(VEC_FIELDS))
def test_vec_field_of_an_array_element(run_with, name, compiler):
    assert run_with(compiler, name, VEC_FIELDS[name]) == 0
