"""AGAST #3972: an element reached through a field index, `x.f[i].k`.

ritz1 lowered a member of `x.f[i]`, or its address, only when `f` was a
`[N]T` or `**T` field.  With `f` a `*T` field every form was refused, and a
`let e = @x.f[i]` over a `Vec<T>` or `*T` field left `e` an untyped i64, so
`e.k` was refused too:

    s.rs[i].k               # rs: *R    "unhandled EXPR_MEMBER"
    s.rs[i].k = 7           #           "... in assignment"
    let m = @s.rs[0].m      #           "cannot take address"
    let e = @t.es[i]        # es: Vec<E>, then `e.y_min`: "unhandled EXPR_MEMBER"

None of them carried a source location.  lexis (`@sheet.rules[i].style_rule`)
and angelo (`@edge_table.edges[k]`, then `edge.y_min`) could not build under
ritz1.  ritz0 compiles them all.

Each row runs on ritz0, ritz1 and ritz1_selfhosted and exits with what the
element holds: element j has `k = 10 * j + 1` and `m.n = 100 + j`.
"""

import pytest

import test_table_rows as table_rows
from test_table_rows import Refused, Run, case

pytestmark = pytest.mark.integration


DECLS = """\
import ritzlib.gvec { Vec, vec_new }

struct M
    n: i32

struct E
    a: i64
    k: i32
    m: M

struct H
    pad: i64
    f: FIELD

struct O
    pad: i32
    h: H

fn peek(m: @M) -> i32
    m.n

fn take(e: E) -> i32
    e.k + e.m.n

"""

# `pvec`, a pointer to a Vec, indexes through the Vec (#3816), not as a `*E` does.
FIELDS = {"vec": "Vec<E>", "ptr": "*E", "arr": "[4]E", "pvec": "*Vec<E>"}

VEC_OF_FOUR = ("    var j: i32 = 0\n"
               "    while j < 4\n"
               "        {v}.push(E {{ a: 0, k: 10 * j + 1, m: M {{ n: 100 + j }} }})\n"
               "        j += 1\n")

# How each field kind gets four elements into `h.f`; `store` outlives `h`.
FILL = {
    "vec": "    h.f = vec_new<E>()\n" + VEC_OF_FOUR.format(v="h.f"),
    "ptr": "    h.f = @store[0]\n",
    "arr": "",
    "pvec": "    var vs = vec_new<E>()\n" + VEC_OF_FOUR.format(v="vs") + "    h.f = @vs\n",
}

# The element-wise start every kind shares: through `store` for `*E`, else `h.f`.
SET = ("    var s: i32 = 0\n"
       "    while s < 4\n"
       "        {arr}[s].k = 10 * s + 1\n"
       "        {arr}[s].m.n = 100 + s\n"
       "        s += 1\n")

# name -> (body over `h` and `i`, the exit it wants).  i is 2.
OPS = {
    "read": ("    return h.f[i].k\n", 21),
    "store": ("    h.f[i].k = 7\n    return h.f[i].k + h.f[1].k\n", 18),
    "addr": ("    let p = @h.f[i].k\n    return *p\n", 21),
    "addr_mut": ("    let p = @&h.f[i].k\n    *p = 5\n    return h.f[i].k\n", 5),
    "let_addr": ("    let e = @h.f[i]\n    return e.k\n", 21),
    "let_addr_mut": ("    let e = @&h.f[i]\n    e.k = 9\n    return h.f[i].k\n", 9),
    "let_addr_nested": ("    let e = @&h.f[i]\n    e.m.n = 3\n    return h.f[i].m.n\n", 3),
    "addr_member": ("    let m = @h.f[i].m\n    return m.n\n", 102),
    # lexis.ritz:147: the member's address into an `@M` param.  ritz1 left `m`
    # untyped, so the call reported a misleading "doesn't fit a reference slot".
    "addr_member_call": ("    let m = @h.f[i].m\n    return peek(m)\n", 102),
    # The whole element, by value.  lexis's selector_map.ritz:176
    # `rule_entry_new(rule.selectors.selectors[k], ...)` (selectors: *S): ritz1
    # loaded one byte for it and stored that i64 as the %S; clang refused it.
    "copy": ("    let e = h.f[i]\n    return e.k + e.m.n\n", 123),
    "copy_arg": ("    return take(h.f[i])\n", 123),
    # A copy is its own: a store to it leaves the element alone.
    "copy_is_a_copy": ("    var e = h.f[i]\n    e.k = 0\n    return h.f[i].k\n", 21),
}


def _program(kind: str, op: str, holder: str) -> str:
    body, _ = OPS[op]
    arr = {"ptr": "store", "pvec": "vs"}.get(kind, "h.f")
    setup = ("    var store: [4]E\n    var h: H\n" + FILL[kind] + SET.format(arr=arr))
    out = DECLS.replace("FIELD", FIELDS[kind])
    if holder == "nested":
        # `o.h.f[i]`: the field one member deeper, as lexis's `rule.selectors.selectors[k]`.
        setup = setup.replace("var h: H", "var o: O").replace("h.f", "o.h.f")
        out += "pub fn main() -> i32\n" + setup + "    var i: u32 = 2\n" + body.replace("h.f", "o.h.f")
    elif holder == "borrow":
        # The element is reached through a `:&` param, as lexis's and angelo's are.
        out += "fn go(h:& H, i: u32) -> i32\n" + body + "\n"
        out += "pub fn main() -> i32\n" + setup + "    return go(h, 2)\n"
    else:
        out += "pub fn main() -> i32\n" + setup + "    var i: u32 = 2\n" + body
    return out


@case(holder=["borrow", "local", "nested"], op=list(OPS), kind=list(FIELDS))
def _field_index(kind, op, holder):
    return Run(_program(kind, op, holder), OPS[op][1])


# `@x[i]` with `x` a local `*E` or Vec: the same element typing, without a field.
# ritz1 left `e` untyped for both ("unhandled EXPR_MEMBER").
LOCAL_BASE = {
    "ptr": "    var store: [4]E\n" + SET.format(arr="store") + "    let x: *E = @store[0]\n",
    "vec": "    var x = vec_new<E>()\n" + VEC_OF_FOUR.format(v="x"),
}


@case(op=["let_addr", "let_addr_mut", "let_addr_nested"], base=list(LOCAL_BASE))
def _local_base(base, op):
    body, want = OPS[op]
    return Run(DECLS.replace("FIELD", "i64") + "pub fn main() -> i32\n" + LOCAL_BASE[base]
               + "    var i: u32 = 2\n" + body.replace("h.f", "x"), want)


# The ticket's REPRO A (angelo's raster/fill.ritz:164), verbatim.
@case()
def _repro_vec_field_borrowed_element():
    return Run("""\
import ritzlib.gvec { Vec, vec_new }
struct E
    x: f32
    y_min: f32
struct T
    es: Vec<E>
fn f(t:& T, y: f32) -> i32
    var i = 0usize
    let e = @t.es[i]
    if e.y_min <= y
        return 1
    0
pub fn main() -> i32
    var t = T { es: vec_new<E>() }
    t.es.push(E { x: 3.0, y_min: 0.0 })
    f(@&t, 1.0)
""", 1)


# The ticket's REPRO B (lexis's Stylesheet.rules: *CssRule): read, store, address.
@case()
def _repro_ptr_field_read_store_address():
    return Run("""\
struct R
    k: i32
    m: M
struct M
    n: i32
struct S
    rs: *R
fn rd(s: @S, i: u32) -> i32
    s.rs[i].k
fn wr(s:& S, i: u32)
    s.rs[i].k = 7
fn first(s: @S) -> i32
    let m = @s.rs[0].m
    m.n
pub fn main() -> i32
    var rs: [2]R
    rs[0].k = 1
    rs[0].m.n = 30
    rs[1].k = 2
    var s = S { rs: @rs[0] }
    wr(s, 1)
    rd(@s, 1) + first(@s)
""", 37)


# A member ritz1 still can't lower is refused at its line:col.  It said only
# "ritz1 cannot emit: unhandled EXPR_MEMBER", so lexis's 9 named no line.
# ritz0 refuses `nobody` itself ("Unknown identifier"), elsewhere in its words.
UNLOWERABLE = "struct P\n    a: i32\n\npub fn main() -> i32\n"


@case(compilers=("ritz1", "ritz1_selfhosted"))
def _unlowerable_member_read_is_located():
    return Refused(UNLOWERABLE + "    let x = nobody.a\n    0\n",
                   "ritz1 cannot emit: unhandled EXPR_MEMBER", at=(5, 13))


@case(compilers=("ritz1", "ritz1_selfhosted"))
def _unlowerable_member_store_is_located():
    return Refused(UNLOWERABLE + "    nobody.a = 3\n    0\n",
                   "ritz1 cannot emit: unhandled EXPR_MEMBER in assignment", at=(5, 5))


@case(compilers=("ritz1", "ritz1_selfhosted"))
def _unlowerable_indexed_member_store_is_located():
    return Refused(UNLOWERABLE + "    nobody.a[0] = 3\n    0\n",
                   "ritz1 cannot emit: unhandled indexed EXPR_MEMBER in assignment", at=(5, 5))


TABLE = table_rows.cases(globals())


@pytest.mark.parametrize("compiler,chunk", table_rows.chunks(TABLE),
                         ids=[f"{c}-{i}" for c, i in table_rows.chunks(TABLE)])
def test_field_index_element(ritz1_bin, tmp_path, compiler, chunk):
    table_rows.assert_ritzlib_rows(compiler, table_rows.chunk(TABLE, compiler, chunk),
                                   ritz1_bin, tmp_path)
