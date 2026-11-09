#!/usr/bin/env python3
"""`@x` is shared: it fits `@T` and `*T`, never `@&T` or `:&` (LANGUAGE_SPEC §3.2,
§13.3-13.4, LARB ruling R1, Aaron's ruling on AGAST #2339).

Mutation is written `@&x`, or a bare place into a `:&` parameter. Each refusal runs
on ritz0, ritz1 and ritz1_selfhosted, and all three must report the same
`line:col: message`.

`@x` of a `let`, or of a place behind an `@T`, keeps the more exact message #2338
and #2374 gave it: declaring the binding `var` or making the reference `@&T` is the
fix there, and `@&x` wouldn't compile either.
"""

import pytest

from ref_rules import ADDR_INTO_MUT, BORROW_THROUGH_SHARED, let_into_mut
from test_ref_into_value import COMPILERS, _assert_refused, _compile, _ids, _main, _run
from test_value_into_ref import SITES

pytestmark = pytest.mark.integration

TYPES = """\
struct C
    x: i32

struct W
    c: C
    a: [2]i32

struct K
    n: i32

impl K
    fn put(self: @K, p: @&C) -> i32
        self.n
    fn lend(self: @K, p:& C) -> i32
        self.n

impl C
    fn add(self: @&C, d: @&C)
        self.x = d.x

fn mb(c: @&C) -> i32
    c.x = 3
    0

fn lb(c:& C) -> i32
    c.x = 3
    0

fn mi(n: @&i32) -> i32
    *n = 3
    0

fn li(n:& i32) -> i32
    n = 3
    0

fn ma(a: @&[2]i32) -> i32
    0

fn mp(p: @&*C) -> i32
    0

fn gm<T>(r: @&T) -> i32
    0

fn gl<T>(r:& T) -> i32
    0

"""

# The slot types SITES fills in. `c` is what `{B}` binds.
SITE_TYPES = ("struct C\n    x: i32\n\nstruct W\n    r: @&C\n\nstruct K\n    n: i32\n\n"
              "enum E\n    V(@&C)\n    N\n\nimpl K\n    fn take(self: @K, p: @&C) -> i32\n"
              "        self.n\n\nfn g(p: @&C) -> i32\n    0\n\n")

# `^` marks where the error lands. Everything here is a `var`, or reached through
# something that may be written.
PLACES = {
    "var": "var c = C { x: 1 }\n    mb(^@c)\n",
    "var_scalar": "var n: i32 = 1\n    mi(^@n)\n",
    "var_array": "var a: [2]i32 = [1, 2]\n    ma(^@a)\n",
    "var_pointer": "var p: *C = null\n    mp(^@p)\n",
    "field": "var w = W { c: C { x: 1 }, a: [1, 2] }\n    mb(^@w.c)\n",
    "field_scalar": "var w = W { c: C { x: 1 }, a: [1, 2] }\n    mi(^@w.c.x)\n",
    "element": "var a: [2]i32 = [1, 2]\n    mi(^@a[1])\n",
    "element_of_a_field": "var w = W { c: C { x: 1 }, a: [1, 2] }\n    mi(^@w.a[1])\n",
    "grouped": "var c = C { x: 1 }\n    mb((^@c))\n",
    "second_argument": "var c = C { x: 1 }\n    var d = C { x: 1 }\n    two(@&c, ^@d)\n",
    "generic": "var n: i32 = 1\n    gm<i32>(^@n)\n",
    "lent_struct": "var c = C { x: 1 }\n    lb(^@c)\n",
    "lent_grouped": "var c = C { x: 1 }\n    lb((^@c))\n",
    "lent_scalar": "var n: i32 = 1\n    li(^@n)\n",
    "lent_field": "var w = W { c: C { x: 1 }, a: [1, 2] }\n    li(^@w.c.x)\n",
    "lent_element": "var a: [2]i32 = [1, 2]\n    li(^@a[1])\n",
    "lent_generic": "var n: i32 = 1\n    gl<i32>(^@n)\n",
    "method": "var c = C { x: 1 }\n    let k = K { n: 1 }\n    k.put(^@c)\n",
    "method_lent": "var c = C { x: 1 }\n    let k = K { n: 1 }\n    k.lend(^@c)\n",
    "receiver_method": "var c = C { x: 1 }\n    var d = C { x: 1 }\n    c.add(^@d)\n    0\n",
    "fn_pointer": "var c = C { x: 1 }\n    let f = mb\n    f(^@c)\n",
    "let_slot": "var c = C { x: 1 }\n    let p: @&C = ^@c\n    0\n",
    "var_slot": "var c = C { x: 1 }\n    var p: @&C = ^@c\n    0\n",
}

# What the place is reached through, in a fn of its own. `^` as above.
ROOTS = {
    "lent_param": "fn f(c:& C) -> i32\n    mb(^@c)\n",
    "lent_param_field": "fn f(c:& C) -> i32\n    mi(^@c.x)\n",
    "value_param": "fn f(c: C) -> i32\n    mb(^@c)\n",
    "value_param_field": "fn f(c: C) -> i32\n    mi(^@c.x)\n",
    "behind_a_mutable_reference": "fn f(m: @&C) -> i32\n    mi(^@m.x)\n",
    "behind_a_pointer": "fn f(p: *C) -> i32\n    mi(^@p.x)\n",
    "behind_a_let_reference": "fn f(m: @&C) -> i32\n    let q: @&C = m\n    mi(^@q.x)\n",
    "behind_a_let_pointer": "fn f(p: *C) -> i32\n    let q: *C = p\n    mi(^@q.x)\n",
    "self_field": "impl W\n    fn go(self: @&W) -> i32\n        mb(^@self.c)\n",
    "self_lent": "impl W\n    fn go(self:& W) -> i32\n        mb(^@self.c)\n",
    "generic_body": "fn f<T>(r: T) -> i32\n    var v: T = r\n    gm<T>(^@v)\n\n"
                    "fn use() -> i32\n    f<i32>(1)\n",
}

# Controls: each compiles and writes, or reads, as written.
ALLOWED = {
    "written_into_a_reference": ("", "    var c = C { x: 1 }\n    mb(@&c)\n    c.x\n", 3),
    "written_into_a_lent_param": ("", "    var c = C { x: 1 }\n    lb(@&c)\n    c.x\n", 3),
    "bare_place_into_a_lent_param": ("", "    var c = C { x: 1 }\n    lb(c)\n    c.x\n", 3),
    "bare_field_into_a_lent_param": ("", "    var c = C { x: 1 }\n    li(c.x)\n    c.x\n", 3),
    "written_field": ("", "    var c = C { x: 1 }\n    mi(@&c.x)\n    c.x\n", 3),
    "written_element": ("", "    var a: [2]i32 = [1, 2]\n    mi(@&a[0])\n    a[0]\n", 3),
    "written_scalar_lent": ("", "    var n: i32 = 1\n    li(@&n)\n    n\n", 3),
    "shared_into_shared": ("fn rd(c: @C) -> i32\n    c.x\n\n",
                           "    var c = C { x: 3 }\n    rd(@c)\n", 3),
    "shared_into_pointer": ("fn wr(c: *C)\n    c.x = 3\n\n",
                            "    var c = C { x: 1 }\n    wr(@c)\n    c.x\n", 3),
    "mutable_into_shared": ("fn rd(c: @C) -> i32\n    c.x\n\n",
                            "    var c = C { x: 3 }\n    rd(@&c)\n", 3),
    "mutable_into_pointer": ("fn wr(c: *C)\n    c.x = 3\n\n",
                             "    var c = C { x: 1 }\n    wr(@&c)\n    c.x\n", 3),
    "held_mutable": ("", "    var c = C { x: 1 }\n    let m: @&C = @&c\n    mb(m)\n    c.x\n", 3),
    "pointer_into_a_reference": ("", "    var c = C { x: 1 }\n    let p: *C = @c\n    mb(p)\n    c.x\n", 3),
    "pointer_into_a_lent_param": ("", "    var c = C { x: 1 }\n    let p: *C = @c\n    lb(p)\n    c.x\n", 3),
    "pass_on_a_lent_param": ("fn on(c:& C) -> i32\n    lb(c)\n\n",
                             "    var c = C { x: 1 }\n    on(c)\n    c.x\n", 3),
    "pass_on_written": ("fn on(c:& C) -> i32\n    mb(@&c)\n\n",
                        "    var c = C { x: 1 }\n    on(c)\n    c.x\n", 3),
    "mutable_reference_into_shared": ("fn rd(c: @C) -> i32\n    c.x\n\nfn on(m: @&C) -> i32\n    rd(m)\n\n",
                                      "    var c = C { x: 3 }\n    on(@&c)\n", 3),
}

# Rows ritz1 and ritz1_selfhosted do not meet yet, each with its ticket.
GAPS = {"fn_pointer": 2417, "mutable_into_shared": 2416}


def _wrap(body):
    return _main(TYPES + "fn two(a: @&C, b: @&C) -> i32\n    0\n\n" + body, "    0\n")


def _with_gaps(table):
    for site in _ids(table):
        for compiler in COMPILERS:
            if site in GAPS and compiler != "ritz0":
                yield pytest.param(site, compiler,
                                   marks=pytest.mark.xfail(strict=True, reason=f"#{GAPS[site]}"))
            else:
                yield pytest.param(site, compiler)


@pytest.mark.parametrize("site,compiler", list(_with_gaps(PLACES)))
def test_address_of_a_place_into_a_mutable_slot_is_refused(tmp_path, compiler, site):
    _assert_refused(compiler, tmp_path, site, _wrap(f"fn f() -> i32\n    {PLACES[site]}\n"),
                    ADDR_INTO_MUT)


@pytest.mark.parametrize("site,compiler", list(_with_gaps(ROOTS)))
def test_however_the_place_is_reached_it_is_refused(tmp_path, compiler, site):
    _assert_refused(compiler, tmp_path, site, _wrap(ROOTS[site]), ADDR_INTO_MUT)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", _ids(SITES))
def test_address_of_a_var_at_each_slot_a_mutable_one_can_be(tmp_path, compiler, site):
    """`c:& C` so that a `return` isn't refused for leaving the fn."""
    body = SITES[site].replace("{S}", "@&C").replace("{B}", "c:& C")
    body = body.replace("^c", "^@c").replace("        c\n", "        @&c\n")
    body = body.replace("=> c\n", "=> @&c\n").replace("return c\n", "return @&c\n")
    _assert_refused(compiler, tmp_path, site, _main(SITE_TYPES + body, "    0\n"), ADDR_INTO_MUT)


@pytest.mark.parametrize("site,compiler", list(_with_gaps(ALLOWED)))
def test_what_the_ruling_keeps_still_runs(tmp_path, compiler, site):
    fn, entry, want = ALLOWED[site]
    assert _run(compiler, tmp_path, site, _main(TYPES + fn, entry)) == want


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_let_keeps_its_own_message(tmp_path, compiler):
    """`@&c` wouldn't compile either, so `write @&x` would be the wrong advice."""
    _assert_refused(compiler, tmp_path, "let",
                    _wrap("fn f() -> i32\n    let c = C { x: 1 }\n    mb(^@c)\n"), let_into_mut("c"))


@pytest.mark.parametrize("compiler", COMPILERS)
def test_behind_a_shared_reference_keeps_its_own_message(tmp_path, compiler):
    _assert_refused(compiler, tmp_path, "shared",
                    _wrap("fn f(r: @C) -> i32\n    mi(^@r.x)\n"), BORROW_THROUGH_SHARED)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_one_report_for_one_site(tmp_path, compiler):
    """Two sites on a line are two errors, and each is reported once."""
    src = _wrap("fn f() -> i32\n    var c = C { x: 1 }\n    var d = C { x: 1 }\n    two(^@c, @d)\n")
    comp, _, _ = _compile(compiler, tmp_path, "once", src.replace("^", ""))
    assert (comp.stdout + comp.stderr).count(ADDR_INTO_MUT) == 2


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_narrower_integer_slot_is_refused_at_the_address(tmp_path, compiler):
    """#2348's program as written. `@&n` of the same `i64` is another type (#2368)."""
    src = _main("fn w(r:& i32)\n    r = 3\n\n", "    var n: i64 = 1\n    w(^@n)\n    return n as i32\n")
    _assert_refused(compiler, tmp_path, "narrow", src, ADDR_INTO_MUT)
