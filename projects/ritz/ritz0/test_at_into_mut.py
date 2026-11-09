#!/usr/bin/env python3
"""An `@T` doesn't become an `@&T` (LANGUAGE_SPEC §3.2, §13.3, LARB ruling R1,
AGAST #2374).

Rule 1: an `@T` value where an `@&T` goes is an error, at every slot: a held
reference, a field, an element, a call result.
Rule 2: a method taking `self: @&T` is refused through an `@T` receiver, or a
receiver behind one, whichever way the method was found.
Rule 3: `@&` of a place behind an `@T` is an error wherever it's written. `@x` of
one is too where it lands in `@&T` or `:&`, with this message and not #2339's:
`@&x` wouldn't compile either.

The walk is #2338's, so a `*T` ends it, and what's behind one isn't judged.

Each row runs on ritz0, ritz1 and ritz1_selfhosted, and all three must report
the same `line:col: message`.

`@x` of a `var` into `@&T` or `:&` is #2339's error, whether an `@x` held in a `*T`
counts as a borrow is #2371's, and a reference to another type is #2367's and
#2368's. Nothing here decides those: the `@x` rows ask only that these rules stay
out of it.
"""

import pytest

from ref_rules import BORROW_THROUGH_SHARED, SHARED_INTO_MUT
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

impl C
    fn me(self: @C) -> @C
        self
    fn get(self: @C) -> i32
        self.x
    fn bump(self: @&C)
        self.x = 3

fn same(r: @C) -> @C
    r

fn mb(c: @&C) -> i32
    c.x = 3
    0

fn mi(n: @&i32) -> i32
    *n = 3
    0

fn li(n:& i32) -> i32
    n = 3
    0

fn sb(c: @C) -> i32
    c.x

fn pc(c: @&C) -> *C
    c

fn pi(n: @&i32) -> *i32
    n

fn pb(c: *C) -> i32
    c.x = 3
    0

var G: @C = null

"""

# Rule 1. `^` marks where the error lands.
VALUES = {
    "param": "fn f(r: @C) -> i32\n    mb(^r)\n",
    "grouped": "fn f(r: @C) -> i32\n    mb((^r))\n",
    "scalar": "fn f(r: @i32) -> i32\n    mi(^r)\n",
    "array": "fn g(a: @&[2]i32)\n    pass\n\nfn f(r: @[2]i32)\n    g(^r)\n",
    "to_a_pointer": "fn g(a: @&*C)\n    pass\n\nfn f(r: @*C)\n    g(^r)\n",
    "self": "impl C\n    fn g(self: @C) -> i32\n        mb(^self)\n",
    "let_inferred": "fn f(d: C) -> i32\n    let r = @d\n    mb(^r)\n",
    "var_inferred": "fn f(d: C) -> i32\n    var r = @d\n    mb(^r)\n",
    "let_annotated": "fn f(d: C) -> i32\n    let r: @C = @d\n    mb(^r)\n",
    "let_copied": "fn f(p: @C) -> i32\n    let r = p\n    mb(^r)\n",
    "let_narrowed": "fn f(p: @&C) -> i32\n    let r: @C = p\n    mb(^r)\n",
    "of_a_var": "fn f() -> i32\n    var c = C { x: 1 }\n    let r = @c\n    mb(^r)\n",
    "of_a_let": "fn f() -> i32\n    let c = C { x: 1 }\n    let r = @c\n    mb(^r)\n",
    "field": "fn f(h: H) -> i32\n    mb(^h.r)\n",
    "field_of_a_reference": "fn f(h: @&H) -> i32\n    mb(^h.r)\n",
    "field_of_a_pointer": "fn f(h: *H) -> i32\n    mb(^h.r)\n",
    "field_of_a_generic": "struct B<T>\n    r: @T\n\nfn f(h: B<C>) -> i32\n    mb(^h.r)\n",
    "let_from_field": "fn f(h: H) -> i32\n    let r = h.r\n    mb(^r)\n",
    "element": "fn f(a: [1]@C) -> i32\n    mb(^a[0])\n",
    "deref": "fn f(r: @@C) -> i32\n    mb(^*r)\n",
    "call_result": "fn f(r: @C) -> i32\n    mb(^same(r))\n",
    "method_result": "fn f(r: @C) -> i32\n    mb(^r.me())\n",
    "let_from_call": "fn f(p: @C) -> i32\n    let r = same(p)\n    mb(^r)\n",
    "global": "fn f() -> i32\n    mb(^G)\n",
    "generic_instance": "fn g<T>(r: @T, m: fn(@&T) -> i32) -> i32\n    let q: @&T = ^r\n    0\n\n"
                        "fn f(r: @C) -> i32\n    g<C>(r, mb)\n",
    "nested_call": "fn f(r: @C) -> i32\n    sb(same(r)) + mb(^r)\n",
    "condition": "fn f(r: @C) -> i32\n    if mb(^r) > 0\n        return 1\n    0\n",
    "some_payload": "fn f(r: @C) -> Option<@&C>\n    return Some(^r)\n",
    "in_a_field_target": "fn f(r: @C)\n    pc(^r).x = 3\n",
    "in_a_deref_target": "fn f(r: @i32)\n    *pi(^r) = 3\n",
    "in_an_index": "fn f(r: @C, a: @&[2]i32)\n    var b: [2]i32 = [0, 0]\n    b[mb(^r)] = 3\n",
}

# ritz1 keeps no payload for `Option<@&C>` (#2384), so the slot goes unjudged.
VALUE_GAPS = {"some_payload": 2384}

# Rule 2. `^` as above.
RECEIVERS = {
    "param": "fn f(r: @C)\n    ^r.bump()\n",
    "self": "impl C\n    fn g(self: @C)\n        ^self.bump()\n",
    "let_inferred": "fn f(d: C)\n    let r = @d\n    ^r.bump()\n",
    "of_a_var": "fn f()\n    var c = C { x: 1 }\n    let r = @c\n    ^r.bump()\n",
    "of_a_let": "fn f()\n    let c = C { x: 1 }\n    let r = @c\n    ^r.bump()\n",
    "field": "fn f(h: H)\n    ^h.r.bump()\n",
    "call_result": "fn f(r: @C)\n    ^same(r).bump()\n",
    "method_result": "fn f(r: @C)\n    ^r.me().bump()\n",
    "global": "fn f()\n    ^G.bump()\n",
    "place_behind": "fn f(p: @W)\n    ^p.c.bump()\n",
    "element_behind": "fn f(p: @[2]C)\n    ^p[1].bump()\n",
    "mutable_behind": "fn f(h: @H)\n    ^h.m.bump()\n",
    "generic_impl": "struct B<T>\n    v: T\n\nimpl<T> B<T>\n    fn set(self: @&B<T>, v: T)\n"
                    "        self.v = v\n\nfn f(r: @B<i32>)\n    ^r.set(3)\n",
    "lent_self": "impl C\n    fn lb(self:& C)\n        self.x = 3\n\nfn f(r: @C)\n    ^r.lb()\n",
    "trait_method": "trait Tr\n    fn tm(self: @&Self)\n\nimpl Tr for C\n    fn tm(self: @&C)\n"
                    "        self.x = 3\n\nfn f(r: @C)\n    ^r.tm()\n",
    "standalone": "import ritzlib.string\n\nfn f(s: @String)\n    ^s.as_ptr()\n",
    "standalone_generic": "import ritzlib.gvec\n\nfn f(v: @Vec<u8>)\n    ^v.push(3 as u8)\n",
    "standalone_field": "import ritzlib.gvec\n\nstruct S\n    v: Vec<u8>\n\n"
                        "fn f(s: @S)\n    ^s.v.push(3 as u8)\n",
    "standalone_self": "import ritzlib.gvec\n\nstruct S\n    v: Vec<u8>\n\nimpl S\n"
                       "    fn add(self: @S)\n        ^self.v.push(3 as u8)\n",
    "standalone_held": "import ritzlib.gvec\n\nstruct S\n    v: @Vec<u8>\n\n"
                       # #2383: only a tracked use instantiates `vec_push$u8`.
                       "fn k()\n    var v = vec_new<u8>()\n    v.push(3 as u8)\n\n"
                       "fn f(s: S)\n    ^s.v.push(3 as u8)\n",
}

# ritz1 couldn't lower `p[1].m()` (#2382), so it was refused, but not by this rule.
# Through a pointer to an array it's `*(p# + 1)` now (#2330), and this rule refuses it.
RECEIVER_GAPS = {}

# Rule 3. `^` as above.
PLACES = {
    "field": "fn f(r: @C)\n    let m = ^@&r.x\n",
    "deref": "fn f(r: @C)\n    let m = ^@&*r\n",
    "index": "fn f(p: @[2]i32)\n    let m = ^@&p[1]\n",
    "chain": "fn f(p: @W)\n    let m = ^@&p.c.x\n",
    "chain_array": "fn f(p: @W)\n    let m = ^@&p.a[1]\n",
    "self": "impl C\n    fn g(self: @C)\n        let m = ^@&self.x\n",
    "held_in_a_value": "fn f(h: H)\n    let m = ^@&h.r.x\n",
    "held_in_a_reference": "fn f(h: @&H)\n    let m = ^@&h.r.x\n",
    "mutable_behind_shared": "fn f(h: @H)\n    let m = ^@&h.m.x\n",
    "call_result": "fn f(r: @C)\n    let m = ^@&same(r).x\n",
    "let_inferred": "fn f(d: C)\n    let r = @d\n    let m = ^@&r.x\n",
    "annotated": "fn f(r: @C)\n    let m: @&i32 = ^@&r.x\n",
    "shared_slot": "fn f(r: @C)\n    let m: @i32 = ^@&r.x\n",
    "pointer_slot": "fn f(r: @C)\n    let m: *i32 = ^@&r.x\n",
    "var": "fn f(r: @C)\n    var m = ^@&r.x\n",
    "assign": "fn f(r: @C, q: @&i32)\n    var m = q\n    m = ^@&r.x\n",
    "argument": "fn f(r: @C) -> i32\n    mi(^@&r.x)\n",
    "lent_argument": "fn f(r: @C) -> i32\n    li(^@&r.x)\n",
    "return": "fn f(r: @C) -> @&i32\n    return ^@&r.x\n",
    "tail": "fn f(r: @C) -> @&i32\n    ^@&r.x\n",
    "condition": "fn f(r: @C) -> i32\n    if mi(^@&r.x) > 0\n        return 1\n    0\n",
    "while_condition": "fn f(r: @C)\n    while mi(^@&r.x) > 0\n        pass\n",
    "for_range": "fn f(r: @C)\n    for i in 0..mi(^@&r.x)\n        pass\n",
    "field_init": "struct P\n    n: *i32\n\nfn f(r: @C)\n    let p = P { n: ^@&r.x }\n",
    "element_init": "fn f(r: @C)\n    let a: [1]*i32 = [^@&r.x]\n",
    "element_store": "fn f(r: @C, q: *i32)\n    var a: [1]*i32 = [q]\n    a[0] = ^@&r.x\n",
    "if_body": "fn f(r: @C, b: i32)\n    if b > 0\n        let m = ^@&r.x\n",
    "match_arm": "fn f(r: @C, b: i32) -> i32\n    match b\n        0 => mi(^@&r.x)\n        _ => 0\n",
    "in_a_field_target": "fn f(r: @W)\n    pc(^@&r.c).x = 3\n",
    "in_a_deref_target": "fn f(r: @C)\n    *pi(^@&r.x) = 3\n",
    "in_an_index": "fn f(r: @C)\n    var b: [2]i32 = [0, 0]\n    b[mi(^@&r.x)] = 3\n",
    "generic_instance": "fn g<T>(r: @B<T>)\n    let m = ^@&r.v\n\nstruct B<T>\n    v: T\n\n"
                        "fn f(r: @B<i32>)\n    g<i32>(r)\n",
    "address_of_an_at_field": "fn f(r: @C)\n    mi(^@r.x)\n",
    "address_of_at_let": "fn f(r: @C)\n    let m: @&i32 = ^@r.x\n",
    "address_of_at_lent": "fn f(r: @C) -> i32\n    li(^@r.x)\n",
}

# What R1 keeps. Each is `fn g`'s source, then a call on `var c = C { x: 1 }`; `c.x`
# must come out as the last value.
ALLOWED = {
    "shared_into_shared": ("fn g(r: @C) -> i32\n    sb(r)\n", "g(@c)", 1),
    "shared_into_pointer": ("fn g(r: @C) -> i32\n    pb(r)\n", "g(@c)", 3),
    "shared_cast_to_a_pointer": ("fn g(r: @C) -> i32\n    pb(r as *C)\n", "g(@c)", 3),
    "mutable_into_shared": ("fn g(m: @&C) -> i32\n    sb(m)\n", "g(@&c)", 1),
    "mutable_into_mutable": ("fn g(m: @&C) -> i32\n    mb(m)\n", "g(@&c)", 3),
    "mutable_into_pointer": ("fn g(m: @&C) -> i32\n    pb(m)\n", "g(@&c)", 3),
    "pointer_into_mutable": ("fn g(p: *C) -> i32\n    mb(p)\n", "g(@&c)", 3),
    "pointer_into_shared": ("fn g(p: *C) -> i32\n    sb(p)\n", "g(@&c)", 1),
    "shared_held_in_a_pointer": ("fn g(r: @C) -> i32\n    let p: *C = r\n    mb(p)\n",
                                 "g(@c)", 3),
    "pointer_field_of_shared": ("fn g(h: @H) -> i32\n    mb(h.q)\n",
                                "var h = H { r: null, m: null, q: @&c }\n    g(@h)", 3),
    "receiver_shared_self": ("fn g(r: @C) -> i32\n    r.get()\n", "g(@c)", 1),
    "receiver_mutable": ("fn g(m: @&C)\n    m.bump()\n", "g(@&c)", 3),
    "receiver_pointer": ("fn g(p: *C)\n    p.bump()\n", "g(@&c)", 3),
    "receiver_shared_standalone": ("import ritzlib.gvec\n\nfn g(v: @Vec<u8>) -> i64\n    v.len()\n",
                                   "var v = vec_new<u8>()\n    c.x = g(@v) as i32 + 1", 1),
    "receiver_var_autoref": ("fn g()\n    pass\n", "c.bump()", 3),
    "receiver_pointer_field_of_shared": ("fn g(h: @H)\n    h.q.bump()\n",
                                         "var h = H { r: null, m: null, q: @&c }\n    g(@h)", 3),
    "borrow_through_mutable": ("fn g(m: @&C) -> i32\n    mi(@&m.x)\n", "g(@&c)", 3),
    "borrow_through_pointer": ("fn g(p: *C) -> i32\n    mi(@&p.x)\n", "g(@&c)", 3),
    "borrow_pointer_field_of_shared": ("fn g(h: @H) -> i32\n    mi(@&h.q.x)\n",
                                       "var h = H { r: null, m: null, q: @&c }\n    g(@h)", 3),
    "shared_borrow_behind_shared": ("fn g(r: @C) -> i32\n    let n: @i32 = @r.x\n    *n\n",
                                    "g(@c)", 1),
    "borrow_of_the_binding": ("fn g(r: @C) -> i32\n    var q = r\n    let h: @&@C = @&q\n    0\n",
                              "g(@c)", 1),
}

# ritz1 can't lower a method on a method's result (#2295).
ALLOWED["receiver_chained"] = ("fn g(r: @C) -> i32\n    r.me().get()\n", "g(@c)", 1)
ALLOWED_GAPS = {"receiver_chained": 2295}

# The same, where running would need an allocator: these only have to compile.
COMPILES = {
    "receiver_mutable_standalone": "import ritzlib.gvec\n\nfn g(v: @&Vec<u8>)\n    v.push(3 as u8)\n",
    "receiver_var_standalone": "import ritzlib.gvec\n\nfn g()\n    var v = vec_new<u8>()\n    v.push(3 as u8)\n",
    "receiver_pointer_standalone": "import ritzlib.gvec\n\nfn g(v: *Vec<u8>)\n    v.push(3 as u8)\n",
    "receiver_shared_field_read": "import ritzlib.gvec\n\nstruct S\n    v: Vec<u8>\n\n"
                                  "fn g(s: @S) -> i64\n    s.v.len()\n",
}

# `@x` of what isn't behind an `@T`: #2339 refuses these. Each asks only that rule 3
# stays out.
NOT_THESE_RULES = {
    "var": "fn f() -> i32\n    var c = C { x: 1 }\n    mb(@c)\n",
    "var_field": "fn f() -> i32\n    var c = C { x: 1 }\n    mi(@c.x)\n",
    "var_let": "fn f() -> i32\n    var c = C { x: 1 }\n    let m: @&C = @c\n    0\n",
    "var_lent": "fn f() -> i32\n    var c = C { x: 1 }\n    li(@c.x)\n",
    "behind_a_mutable_reference": "fn f(m: @&C) -> i32\n    mi(@m.x)\n",
    "behind_a_pointer": "fn f(p: *C) -> i32\n    mi(@p.x)\n",
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


@pytest.mark.parametrize("site,compiler", list(_with_gaps(VALUES, VALUE_GAPS)))
def test_a_shared_value_into_a_mutable_slot_is_refused(tmp_path, compiler, site):
    _assert_refused(compiler, tmp_path, site, _wrap(VALUES[site]), SHARED_INTO_MUT)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", _ids(SITES))
def test_a_shared_value_at_each_slot_a_mutable_one_can_be(tmp_path, compiler, site):
    body = SITES[site].replace("{S}", "@&C").replace("{B}", "c: @C")
    types = ("struct C\n    x: i32\n\nstruct W\n    r: @&C\n\nstruct K\n    n: i32\n\n"
             "enum E\n    V(@&C)\n    N\n\nimpl K\n    fn take(self: @K, p: @&C) -> i32\n"
             "        self.n\n\nfn g(p: @&C) -> i32\n    0\n\n")
    _assert_refused(compiler, tmp_path, site, _main(types + body, "    0\n"), SHARED_INTO_MUT)


@pytest.mark.parametrize("site,compiler", list(_with_gaps(RECEIVERS, RECEIVER_GAPS)))
def test_a_mutating_method_on_a_shared_receiver_is_refused(tmp_path, compiler, site):
    _assert_refused(compiler, tmp_path, site, _wrap(RECEIVERS[site]), SHARED_INTO_MUT)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", _ids(PLACES))
def test_a_mutable_borrow_behind_a_shared_reference_is_refused(tmp_path, compiler, site):
    _assert_refused(compiler, tmp_path, site, _wrap(PLACES[site]), BORROW_THROUGH_SHARED)


@pytest.mark.parametrize("site,compiler", list(_with_gaps(ALLOWED, ALLOWED_GAPS)))
def test_what_r1_keeps_still_runs(tmp_path, compiler, site):
    fn, call, want = ALLOWED[site]
    src = _main(TYPES + fn, f"    var c = C {{ x: 1 }}\n    {call}\n    c.x\n")
    assert _run(compiler, tmp_path, site, src) == want


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", _ids(COMPILES))
def test_what_r1_keeps_still_compiles(tmp_path, compiler, site):
    comp, _, _ = _compile(compiler, tmp_path, site, _wrap(COMPILES[site]))
    assert comp.returncode == 0, comp.stdout + comp.stderr


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", _ids(NOT_THESE_RULES))
def test_these_rules_stay_out_of_address_of(tmp_path, compiler, site):
    comp, _, _ = _compile(compiler, tmp_path, site, _wrap(NOT_THESE_RULES[site]))
    out = comp.stdout + comp.stderr
    assert SHARED_INTO_MUT not in out and BORROW_THROUGH_SHARED not in out


@pytest.mark.xfail(strict=True, reason="#2381")
@pytest.mark.parametrize("compiler", COMPILERS)
def test_mutable_field_behind_shared(tmp_path, compiler):
    """`h.m` is an `@&T`, so rule 1 doesn't reach it, though `h.m.x = v`, `h.m.bump()`
    and `@&h.m.x` are refused. Whether it should be is #2381's."""
    _assert_refused(compiler, tmp_path, "mutable_field", _wrap("fn f(h: @H) -> i32\n    mb(^h.m)\n"),
                    SHARED_INTO_MUT)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_mutable_field_behind_shared_writes_today(tmp_path, compiler):
    """What #2381 has to decide: this is a write past an `@T`, and it happens."""
    src = _main(TYPES + "fn g(h: @H) -> i32\n    mb(h.m)\n",
                "    var c = C { x: 1 }\n    var h = H { r: null, m: @&c, q: null }\n"
                "    g(@h)\n    c.x\n")
    assert _run(compiler, tmp_path, "mutable_field_writes", src) == 3
