#!/usr/bin/env python3
"""`@T` is read-only (LANGUAGE_SPEC §3.2, §13.3, LARB ruling R1, AGAST #2338).

Rule 1: `p.f = v`, `p[i] = v` and `*p = v` through an `@T` are an error, directly
or through a chain of fields. A write that reaches a raw `*T` first isn't judged:
it writes the pointee.
Rule 2: `@x` of a `let`'s own storage doesn't fit `@&T` or `:&`, at any slot.

Each row runs on ritz0, ritz1 and ritz1_selfhosted, and all three must report
the same `line:col: message`.

Whether `@x` of a `var` fits `@&T` or `:&` is #2339's, and whether an `@x` held in
a `*T` counts as a borrow is #2371's. Nothing here decides either: those rows ask
only that rule 2 stays out of it.
"""

import pytest

from ref_rules import WRITE_THROUGH_SHARED, let_into_mut
from test_ref_into_value import COMPILERS, _assert_refused, _compile, _ids, _main, _run
from test_value_into_ref import SITES

pytestmark = pytest.mark.integration

TYPES = """\
struct C
    x: i32

struct W
    c: C
    a: [2]i32

struct H
    r: @C
    m: @&C
    q: *C
    n: *i32

impl C
    fn me(self: @C) -> @C
        self

fn same(r: @C) -> @C
    r

var G: @C = null

"""

# `^` marks where the error lands.
WRITES = {
    "param_field": "fn f(p: @C)\n    ^p.x = 3\n",
    "param_compound": "fn f(p: @C)\n    ^p.x += 3\n",
    "param_deref": "fn f(p: @i32)\n    ^*p = 3\n",
    "param_deref_struct": "fn f(p: @C, d: C)\n    ^*p = d\n",
    "param_deref_compound": "fn f(p: @i32)\n    ^*p += 3\n",
    "param_index": "fn f(p: @[2]i32)\n    ^p[1] = 3\n",
    "param_index_compound": "fn f(p: @[2]i32)\n    ^p[1] += 3\n",
    "scalar_index": "fn f(p: @i32)\n    ^p[1] = 3\n",
    "explicit_deref": "fn f(p: @C)\n    (^*p).x = 3\n",
    "self": "impl C\n    fn set(self: @C)\n        ^self.x = 3\n",
    "let_inferred": "fn f(d: C)\n    let p = @d\n    ^p.x = 3\n",
    "let_inferred_scalar": "fn f(n: i32)\n    let p = @n\n    ^*p = 3\n",
    "var_inferred": "fn f(d: C)\n    var p = @d\n    ^p.x = 3\n",
    "let_annotated": "fn f(d: C)\n    let p: @C = @d\n    ^p.x = 3\n",
    "let_copied": "fn f(p: @C)\n    let q = p\n    ^q.x = 3\n",
    "let_narrowed": "fn f(p: @&C)\n    let q: @C = p\n    ^q.x = 3\n",
    "chain": "fn f(p: @W)\n    ^p.c.x = 3\n",
    "chain_array": "fn f(p: @W)\n    ^p.a[1] = 3\n",
    "element_field": "fn f(p: @[2]C)\n    ^p[1].x = 3\n",
    "held_in_a_value": "fn f(h: H)\n    ^h.r.x = 3\n",
    "held_in_a_reference": "fn f(h: @&H)\n    ^h.r.x = 3\n",
    "held_in_a_pointer": "fn f(h: *H)\n    ^h.r.x = 3\n",
    "held_in_a_generic": "struct B<T>\n    r: @T\n\nfn f(h: B<C>)\n    ^h.r.x = 3\n",
    "mutable_behind_shared": "fn f(h: @H)\n    ^h.m.x = 3\n",
    "let_from_field": "fn f(h: H)\n    let p = h.r\n    ^p.x = 3\n",
    "call_result": "fn f(p: @C)\n    ^same(p).x = 3\n",
    "method_result": "fn f(p: @C)\n    ^p.me().x = 3\n",
    "let_from_call": "fn f(p: @C)\n    let q = same(p)\n    ^q.x = 3\n",
    "global": "fn f()\n    ^G.x = 3\n",
    "address_of": "fn f(d: C)\n    (^@d).x = 3\n",
    "deref_address_of": "fn f(n: i32)\n    ^*(@n) = 3\n",
    "if_body": "fn f(p: @C, b: i32)\n    if b > 0\n        ^p.x = 3\n",
    "while_body": "fn f(p: @C, b: i32)\n    while b > 0\n        ^p.x = 3\n",
    "match_arm": "fn f(p: @C, b: i32)\n    match b\n        0 => ^p.x = 3\n        _ => p.x\n",
    "generic_instance": "fn g<T>(p: @T, v: T)\n    ^*p = v\n\nfn f(p: @i32)\n    g<i32>(p, 3)\n",
}

# ritz1 can't lower `p[i].f = v` at all (#2373): it's refused, but not by this rule.
WRITE_GAPS = {"element_field": 2373}

# The same writes where the place isn't behind an `@T`. Each leaves 3 in `c.x`.
ALLOWED = {
    "mutable_reference": ("fn g(p: @&C)\n    p.x = 3\n", "g(@&c)"),
    "deref_mutable_address_of": ("fn g()\n    pass\n", "*@&c.x = 3"),
    "deref_mutable_address_of_element": ("fn g()\n    pass\n",
                                         "var a: [3]i8 = [1, 2, 3]\n    *@&a[1] = 7\n"
                                         "    c.x = a[0] as i32 + a[2] as i32 + a[1] as i32 - 8"),
    "lent": ("fn g(p:& C)\n    p.x = 3\n", "g(c)"),
    "lent_compound": ("fn g(p:& C)\n    p.x += 2\n", "g(c)"),
    "pointer": ("fn g(p: *C)\n    p.x = 3\n", "g(@&c)"),
    "pointer_deref": ("fn g(p: *C, d: C)\n    *p = d\n", "g(@&c, C { x: 3 })"),
    "pointer_in_a_shared_struct": ("fn g(h: @H)\n    h.q.x = 3\n",
                                   "var h = H { r: null, m: null, q: @&c, n: null }\n    g(@h)"),
    "element_in_a_shared_struct": ("fn g(h: @H)\n    h.n[0] = 3\n",
                                   "var h = H { r: null, m: null, q: null, n: @&c.x }\n    g(@h)"),
    "pointer_behind_a_shared_reference": ("fn g(p: @*C)\n    p.x = 3\n",
                                          "var q: *C = @&c\n    g(@q)"),
    "deref_pointer_behind_a_shared_reference": ("fn g(p: @*i32)\n    **p = 3\n",
                                                "var q: *i32 = @&c.x\n    g(@q)"),
    "cast_to_a_pointer": ("fn g(p: @C)\n    (p as *C).x = 3\n", "g(@c)"),
}

# ritz1 fails these with no `@T` to blame: #2373 can't lower the cast, and #2372
# writes into the `*C` rather than through it.
ALLOWED_GAPS = {"cast_to_a_pointer": 2373, "pointer_behind_a_shared_reference": 2372}

# Whole bindings and by-value fields: the reference is what changes, not what it
# refers to.
REBINDS = {
    "binding": "fn f(a: @C, b: @C) -> @C\n    var p = a\n    p = b\n    p\n",
    "param_in_a_var": "fn f(a: @C, b: @C) -> @C\n    var p: @C = a\n    p = b\n    p\n",
    "field": "fn f(a: @C, h: H) -> @C\n    var k = h\n    k.r = a\n    k.r\n",
    "field_through_mutable": "fn f(a: @C, h: @&H) -> @C\n    h.r = a\n    h.r\n",
}

# A `let`'s own storage, and what it refers to. `^` as above.
PLACES = {
    "binding": ("let c = C { x: 1 }\n    g_c(^@c)\n", "c"),
    "scalar": ("let n: i32 = 1\n    g_n(^@n)\n", "n"),
    "field": ("let w = W { c: C { x: 1 }, a: [1, 2] }\n    g_c(^@w.c)\n", "w"),
    "field_scalar": ("let w = W { c: C { x: 1 }, a: [1, 2] }\n    g_n(^@w.c.x)\n", "w"),
    "element": ("let a: [2]i32 = [1, 2]\n    g_n(^@a[1])\n", "a"),
    "element_in_a_field": ("let w = W { c: C { x: 1 }, a: [1, 2] }\n    g_n(^@w.a[1])\n", "w"),
    "grouped": ("let c = C { x: 1 }\n    g_c((^@c))\n", "c"),
    "shadowing_a_var": ("var c = C { x: 1 }\n    if c.x > 0\n        let c = C { x: 2 }\n"
                        "        g_c(^@c)\n    0\n", "c"),
}
PLACE_TYPES = "fn g_c(p: {M}C) -> i32\n    0\n\nfn g_n(p: {M}i32) -> i32\n    0\n\n"
MUTABLE = {"reference": "p: @&", "lent": "p:& "}

# Not a `let`'s own storage, so not rule 2's. Each asks only that it stays out.
NOT_LET = {
    "var": "var c = C { x: 1 }\n    g(@c)\n",
    "var_field": "var w = W { c: C { x: 1 }, a: [1, 2] }\n    g(@w.c)\n",
    "var_shadows_the_let": "let c = C { x: 1 }\n    var d = c\n    if d.x > 0\n"
                           "        var c = d\n        g(@c)\n    0\n",
    "pattern_shadows_the_let": "let c = C { x: 1 }\n    match c\n        c => g(@c)\n",
    "behind_a_let_pointer": "var d = C { x: 1 }\n    let p: *W = null\n    g(@p.c)\n",
    "behind_a_let_reference": "var w = W { c: C { x: 1 }, a: [1, 2] }\n"
                              "    let p: @&W = @&w\n    g(@p.c)\n",
}


def _wrap(body):
    return _main(TYPES + body, "    0\n")


def _with_gaps(table, gaps):
    """Each row on each compiler, a ritz1 gap as a strict xfail citing its ticket."""
    for site in _ids(table):
        for compiler in COMPILERS:
            if site in gaps and compiler != "ritz0":
                mark = pytest.mark.xfail(strict=True, reason=f"#{gaps[site]}")
                yield pytest.param(site, compiler, marks=mark)
            else:
                yield pytest.param(site, compiler)


@pytest.mark.parametrize("site,compiler", list(_with_gaps(WRITES, WRITE_GAPS)))
def test_a_write_through_a_shared_reference_is_refused(tmp_path, compiler, site):
    _assert_refused(compiler, tmp_path, site, _wrap(WRITES[site]), WRITE_THROUGH_SHARED)


@pytest.mark.parametrize("site,compiler", list(_with_gaps(ALLOWED, ALLOWED_GAPS)))
def test_a_write_that_a_shared_reference_does_not_guard(tmp_path, compiler, site):
    fn, call = ALLOWED[site]
    src = _main(TYPES + fn, f"    var c = C {{ x: 1 }}\n    {call}\n    c.x\n")
    assert _run(compiler, tmp_path, site, src) == 3


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_pointer_behind_a_shared_reference_compiles(tmp_path, compiler):
    """What it does at run time is #2372's. That it isn't refused is this rule's."""
    fn, _ = ALLOWED["pointer_behind_a_shared_reference"]
    comp, _, _ = _compile(compiler, tmp_path, "pointer_compiles", _wrap(fn))
    assert comp.returncode == 0, comp.stdout + comp.stderr


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_index_set_through_a_shared_reference_is_refused(tmp_path, compiler):
    """`m[k] = v` is an insert, and the map is in what the `@T` refers to."""
    src = ("import ritzlib.hashmap\n\nstruct S\n    m: HashMapI64\n\nfn g(p: @S)\n"
           "    ^p.m[10] = 100\n\npub fn main() -> i32\n    0\n")
    _assert_refused(compiler, tmp_path, "index_set", src, WRITE_THROUGH_SHARED)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", _ids(REBINDS))
def test_rebinding_a_shared_reference_is_not_a_write_through_it(tmp_path, compiler, site):
    comp, _, _ = _compile(compiler, tmp_path, site, _wrap(REBINDS[site]))
    assert comp.returncode == 0, comp.stdout + comp.stderr


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", _ids(SITES))
def test_address_of_a_let_into_a_mutable_slot(tmp_path, compiler, site):
    """`@c` of a `let` at each slot `@&C` can be, whatever `c`'s neighbours are."""
    body = SITES[site].replace("{S}", "@&C").replace("{B}", "z: i32")
    body = body.replace("^c", "^@c").replace("        c\n", "        @c\n")
    body = body.replace("=> c\n", "=> @c\n").replace("return c\n", "return @c\n")
    head, _, rest = body.partition("\n")
    src = head + "\n    let c = C { x: 1 }\n" + rest
    types = ("struct C\n    x: i32\n\nstruct W\n    r: @&C\n\nstruct K\n    n: i32\n\n"
             "enum E\n    V(@&C)\n    N\n\nimpl K\n    fn take(self: @K, p: @&C) -> i32\n"
             "        self.n\n\nfn g(p: @&C) -> i32\n    0\n\n")
    _assert_refused(compiler, tmp_path, site, _main(types + src, "    0\n"), let_into_mut("c"))


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("slot", _ids(MUTABLE))
@pytest.mark.parametrize("place", _ids(PLACES))
def test_every_place_in_a_let_is_refused(tmp_path, compiler, place, slot):
    body, name = PLACES[place]
    types = TYPES + PLACE_TYPES.replace("p: {M}", MUTABLE[slot])
    src = _main(types + f"fn f() -> i32\n    {body}\n", "    0\n")
    _assert_refused(compiler, tmp_path, f"{place}_{slot}", src, let_into_mut(name))


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_lent_method_argument_is_refused(tmp_path, compiler):
    src = _main("struct C\n    x: i32\n\nstruct K\n    n: i32\n\nimpl K\n"
                "    fn take(self: @K, p:& C) -> i32\n        self.n\n\n"
                "fn f(k: K) -> i32\n    let c = C { x: 1 }\n    k.take(^@c)\n", "    0\n")
    _assert_refused(compiler, tmp_path, "lent_method", src, let_into_mut("c"))


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("slot", _ids(MUTABLE))
@pytest.mark.parametrize("site", _ids(NOT_LET))
def test_rule_two_stays_out_of_what_is_not_a_let(tmp_path, compiler, site, slot):
    types = TYPES + f"fn g({MUTABLE[slot]}C) -> i32\n    0\n\n"
    comp, _, _ = _compile(compiler, tmp_path, f"{site}_{slot}",
                          _main(types + f"fn f() -> i32\n    {NOT_LET[site]}\n", "    0\n"))
    assert "`let` binding" not in comp.stdout + comp.stderr


@pytest.mark.parametrize("compiler", COMPILERS)
def test_address_of_a_let_still_fits_a_shared_slot(tmp_path, compiler):
    src = _main("struct C\n    x: i32\n\nfn g(p: @C) -> i32\n    p.x\n\n",
                "    let c = C { x: 3 }\n    let p: @C = @c\n    g(p) + g(@c) - 3\n")
    assert _run(compiler, tmp_path, "shared", src) == 3
