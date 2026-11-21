"""AGAST #2564: a field of an element of a `Vec<S>` struct field, `x.vf[i].f`.

    struct T
        edges: Vec<E>
    fn f(t: @T) -> f32
        t.edges[0].y            # ritz1: "cannot emit: unhandled EXPR_MEMBER"

`v[i].f` worked with `v` a Vec name (a local or an `@Vec<E>` param), since
index_through took it as `*(v.data + i)`.  With the Vec a field, `x.vf`, the root
isn't a name and index_through only looked for a `*[N]T` field (#2329): the member
path found no S, so reads, stores, `+=`, `self.edges[i].step()` and the
whole-element `self.edges[i] = self.edges[j]` were all refused, unlocated, on every
holder (a local, `@T`, `@&T`, `*T`, `self:&`, `self: @`).  angelo's raster/edge.ritz
has 19 of these.  `let e = x.vf[i]` (and `let e = v[i]` on a Vec name) left `e` an
i64, so `e.f` was refused too.

A scalar element was worse: `t.vi[1] = 7` through a local, `@&T` or `*T` took the
inline-array arm of STMT_LOCAL_FIELD_INDEX_ASSIGN and wrote 7 into the Vec's len,
SILENT, and `t.vf[0] += 1.0` was invalid IR.  Scalar reads were already right.

ritz0 is the oracle: 0 on every row.  A check returns its own number when it
fails, so a red cell says which access broke.
"""

import pytest

from test_ritz1_for_header import COMPILERS, compile_with, run_with  # noqa: F401  (fixtures)

# `n` before `edges` puts the Vec off offset 0, so a base taken at the struct
# rather than at the field shows.  E's y and k differ in kind and width.
_TYPES = """\
import ritzlib.gvec

struct E
    y: f32
    k: i32

impl E
    pub fn step(self:& E)
        self.k = self.k + 100
        self.y = self.y + 0.5

    pub fn get(self: @E) -> i32
        self.k

struct T
    n: i64
    edges: Vec<E>
    vi: Vec<i32>
    vf: Vec<f32>

"""

_FILL = """\
    var t: T
    t.n = 9
    t.edges = vec_new<E>()
    t.edges.push(E { y: 0.5, k: 1 })
    t.edges.push(E { y: 1.5, k: 2 })
    t.edges.push(E { y: 2.5, k: 3 })
    t.vi = vec_new<i32>()
    t.vi.push(10)
    t.vi.push(20)
    t.vf = vec_new<f32>()
    var c0: f32 = 0.25
    var c1: f32 = 0.75
    t.vf.push(c0)
    t.vf.push(c1)
"""

# 1-2 read (f32, i32); 3-6 store and neighbours; 7-8 `+=`; 9-11 a method through the
# element, mutating and shared; 12-14 whole-element store and copy; 15 a computed index;
# 16-18 scalar Vec<i32> / Vec<f32> fields: store, `+=`, and the Vec header and the
# field before it untouched (through an `@&T`, `t.vi[1] = 7` wrote the len, SILENT).
_MUTATE = """\
    if {x}.edges[1].k != 2
        return 1
    if {x}.edges[0].y != 0.5
        return 2
    {x}.edges[1].k = 40
    if {x}.edges[1].k != 40
        return 3
    if {x}.edges[0].k != 1
        return 4
    {x}.edges[0].y = 4.5
    if {x}.edges[0].y != 4.5
        return 5
    if {x}.edges[1].y != 1.5
        return 6
    {x}.edges[1].k += 3
    if {x}.edges[1].k != 43
        return 7
    {x}.edges[0].y += 1.0
    if {x}.edges[0].y != 5.5
        return 8
    {x}.edges[1].step()
    if {x}.edges[1].k != 143
        return 9
    if {x}.edges[1].y != 2.0
        return 10
    if {x}.edges[1].get() != 143
        return 11
    {x}.edges[0] = {x}.edges[1]
    if {x}.edges[0].k != 143 or {x}.edges[0].y != 2.0
        return 12
    if {x}.edges[2].k != 3
        return 13
    let tmp = {x}.edges[2]
    if tmp.k != 3 or tmp.y != 2.5
        return 14
    var i: i64 = 2
    {x}.edges[i].k = {x}.edges[i - 1].k + 1
    if {x}.edges[2].k != 144
        return 15
    {x}.vi[1] = 7
    {x}.vi[0] += 1
    if {x}.vi[1] != 7 or {x}.vi[0] != 11 or {x}.vi.len() != 2
        return 16
    {x}.vf[1] = 1.5
    {x}.vf[0] += 1.0
    if {x}.vf[1] != 1.5 or {x}.vf[0] != 1.25 or {x}.vf.len() != 2
        return 17
    if {x}.n != 9
        return 18
    return 0
"""

# Through an `@T` nothing is stored: the reads, a shared method, a copy.
_READ = """\
    if {x}.edges[1].k != 2
        return 1
    if {x}.edges[0].y != 0.5
        return 2
    if {x}.edges[2].k + {x}.edges[0].k != 4
        return 3
    if {x}.edges[2].y - {x}.edges[1].y != 1.0
        return 4
    if {x}.edges[1].get() != 2
        return 5
    let tmp = {x}.edges[2]
    if tmp.k != 3
        return 6
    var i: i64 = 2
    if {x}.edges[i - 1].k != 2
        return 7
    if {x}.vi[1] - {x}.vi[0] != 10
        return 8
    if {x}.vf[1] - {x}.vf[0] != 0.5
        return 9
    return 0
"""


def _local(checks: str) -> str:
    return _TYPES + "pub fn main() -> i32\n" + _FILL + checks.format(x="t")


def _in_fn(param: str, arg: str, checks: str) -> str:
    return (_TYPES + f"fn f(t: {param}) -> i32\n" + checks.format(x="t") + "\n"
            + "pub fn main() -> i32\n" + _FILL + f"    return f({arg})\n")


def _in_method(recv: str, checks: str) -> str:
    return (_TYPES + f"impl T\n    pub fn f(self{recv} T) -> i32\n"
            + "".join("    " + line + "\n" for line in checks.format(x="self").splitlines())
            + "\npub fn main() -> i32\n" + _FILL + "    return t.f()\n")


PROGRAMS = {
    "local": _local(_MUTATE),
    "mut_ref_param": _in_fn("@&T", "@&t", _MUTATE),
    "ptr_param": _in_fn("*T", "@t", _MUTATE),
    "self_mut": _in_method(":&", _MUTATE),
    "local_read": _local(_READ),
    "shared_ref_param": _in_fn("@T", "@t", _READ),
    "self_shared": _in_method(": @", _READ),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_field_of_an_element_of_a_vec_field(run_with, name, compiler):
    assert run_with(compiler, name, PROGRAMS[name]) == 0


# infer_through_elem_let types `let e = v[i]` on a bare Vec name too: it was the
# same "unhandled EXPR_MEMBER" at `e.k`.  A copy: a store to it leaves v alone.
_COPY = """\
    let e = {v}[1]
    if e.k != 2 or e.y != 1.5
        return 1
    var w = {v}[0]
    w.k = 50
    if {v}[0].k != 1
        return 2
    return 0
"""

COPIES = {
    "vec_local": _TYPES + "pub fn main() -> i32\n" + _FILL + "    var v = t.edges\n" + _COPY.format(v="v"),
    "vec_shared_param": (_TYPES + "fn f(v: @Vec<E>) -> i32\n" + _COPY.format(v="v") + "\n"
                         + "pub fn main() -> i32\n" + _FILL + "    return f(@t.edges)\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(COPIES))
def test_inferred_copy_of_a_vec_element(run_with, name, compiler):
    assert run_with(compiler, name, COPIES[name]) == 0


# The base can itself be an element: of a Vec field (`o.ts[i].edges[j]`), of a Vec
# name (`v[i].edges[j]`), or of an array at a computed index (`a[i - 1].edges[j]`).
_NESTED = """\
    if {b}.edges[1].k != 2
        return 1
    {b}.edges[1].k += 5
    {b}.edges[0] = {b}.edges[1]
    {b}.edges[0].step()
    if {b}.edges[0].k != 107 or {b}.edges[1].k != 7 or {b}.edges[0].y != 2.0
        return 2
    return 0
"""

_MAIN = _TYPES + "struct O\n    m: i64\n    ts: Vec<T>\n\n" + "pub fn main() -> i32\n" + _FILL
NESTED = {
    "vec_of_t": _MAIN + ("    var o: O\n    o.m = 1\n    o.ts = vec_new<T>()\n    o.ts.push(t)\n"
                         "    var i: i64 = 0\n" + _NESTED.format(b="o.ts[i]")),
    "vec_name_of_t": _MAIN + ("    var v: Vec<T> = vec_new<T>()\n    v.push(t)\n    var i: i64 = 0\n"
                              + _NESTED.format(b="v[i]")),
    "array_of_t": _MAIN + "    var a: [2]T\n    a[1] = t\n    var i: i64 = 2\n" + _NESTED.format(b="a[i - 1]"),
}

# ritz0 crashed indexing `o.ts[i].edges`, 'Cannot index type: Vec$E' (#2567).
# `a[i].edges[j]` was refused on ritz1 until member_field_def typed a field of a
# by-value array element (#2566); test_ritz1_array_elem_field_type.py has the rest.


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(NESTED))
def test_vec_field_of_an_element(run_with, name, compiler):
    assert run_with(compiler, name, NESTED[name]) == 0
