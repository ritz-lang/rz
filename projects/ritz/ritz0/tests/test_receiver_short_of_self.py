#!/usr/bin/env python3
"""A method whose `self` is a pointer to a pointer borrows a place one level
short of it (LANGUAGE_SPEC §5.4, AGAST #2403).

`q.rd()` with `q: *C` and `fn rd(self: **C)`: `self` takes the levels it asks
for, so `q` is borrowed, as `@&q` would be (`@q` for `self: @*C`). That's the
rule `name:& *U` already has for an argument (§13.3): a `*U` place is borrowed.
ritz0 passed `q`'s value as the `C**` and the program died with SIGSEGV.

Nothing else is borrowed for you, so the rest is refused where the receiver is:
a call result (there's no place to borrow), and a receiver two levels short
(`c.rd()` with `c: C`, `q.r3()` with `self: ***C`), which would take a pointer
to a temporary. A `let` lends its storage only to a shared `self: @*C`.
A receiver with all the levels `self` asks for is #2397's, in
test_receiver_through_levels.py.

Expected exits come from what the programs mean. No compiler is the oracle:
`GAPS` lists who's wrong, each a strict xfail citing its ticket.
"""

import pytest

from ref_rules import RECEIVER_SHORT_OF_SELF, let_into_mut
from test_ref_into_value import COMPILERS, _assert_refused, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

TYPES = """\
struct C
    x: i32

struct H
    p: *C

impl C
    fn rd(self: **C) -> i32
        self.x
    fn sh(self: @*C) -> i32
        self.x
    fn r3(self: ***C) -> i32
        self.x

"""

# `*self = n` re-aims the caller's pointer: only a borrow of the place shows it.
SWAP = "impl C\n    fn swap(self: **C, n: *C)\n        *self = n\n\n"

PASS_ON = ("fn f(s: **C) -> i32\n    s.x\n\n"
           "impl C\n    fn on(self: **C) -> i32\n        f(self)\n"
           "    fn top(self: **C) -> i32\n        let p: *C = *self\n        p.x\n\n")

MAKE = "    var c = C { x: 3 }\n    var e = C { x: 5 }\n    var q: *C = @&c\n"


def _main(body, top=""):
    return f"{TYPES}{top}pub fn main() -> i32\n{MAKE}{body}"


# name: (source, exit code). A swap row wants 5 from the pointer it re-aimed and
# 3 from `c`, which it must not have written: 5 * 10 + 3.
RUNS = {
    "local": (_main("    q.rd()\n"), 3),
    "local_swap": (_main("    q.swap(@&e)\n    q.x * 10 + c.x\n", SWAP), 53),
    "local_shared": (_main("    q.sh()\n"), 3),
    "let_shared": (_main("    let p: *C = @&c\n    p.sh()\n"), 3),
    "param": (_main("    g(q)\n", "fn g(p: *C) -> i32\n    p.rd()\n\n"), 3),
    "field": (_main("    var h = H { p: q }\n    h.p.rd()\n"), 3),
    "field_swap": (_main("    var h = H { p: q }\n    h.p.swap(@&e)\n    h.p.x * 10 + c.x\n", SWAP), 53),
    "element": (_main("    var a: [1]*C = [q]\n    a[0].rd()\n"), 3),
    "element_swap": (_main("    var a: [1]*C = [q]\n    a[0].swap(@&e)\n    a[0].x * 10 + c.x\n", SWAP), 53),
    "global": (_main("    G = q\n    G.rd()\n", "var G: *C = null\n\n"), 3),
    "global_swap": (_main("    G = q\n    G.swap(@&e)\n    G.x * 10 + c.x\n", SWAP + "var G: *C = null\n\n"), 53),
    # `*pp` of a `**C` is the `*C` place `pp` points at.
    "deref_swap": (_main("    g(@&q, @&e)\n    q.x * 10 + c.x\n",
                         SWAP + "fn g(pp: **C, e: *C)\n    (*pp).swap(e)\n\n"), 53),
    # The place's operands run once (§5.4).
    "index_is_evaluated_once": (_main("    var a: [1]*C = [q]\n    a[i()].rd() * 10 + N\n",
                                      "var N: i32 = 0\n\nfn i() -> i32\n    N += 1\n    0\n\n"), 31),
    # An argument that re-aims the pointer first changes nothing: `self` is the
    # place, not what it held.
    "argument_reaims_the_receiver": (
        _main("    var d = C { x: 7 }\n    var pq: **C = @&q\n    q.swap(aim(pq, @&e, @&d))\n    q.x * 10 + c.x\n",
              SWAP + "fn aim(p: **C, e: *C, d: *C) -> *C\n    *p = e\n    d\n\n"), 73),
    # Two levels on each side: nothing to borrow, as before #2403.
    "ptr_ptr": (_main("    var r: **C = @&q\n    r.rd()\n"), 3),
    # `self` is a `**C` in the body (#3071): passed on as one, from a lent place
    # and from a receiver with the levels, and `*self` is the `*C` it points at.
    "self_is_passed_on": (_main("    var r: **C = @&q\n    q.on() * 10 + r.on()\n", PASS_ON), 33),
    "self_is_dereferenced": (_main("    var r: **C = @&q\n    q.top() * 10 + r.top()\n", PASS_ON), 33),
}

# name: (source with `^` where the error is, message).
REFUSED = {
    "call_result": (_main("    ^h(q).rd()\n", "fn h(p: *C) -> *C\n    p\n\n"), RECEIVER_SHORT_OF_SELF),
    "method_result": (_main("    ^q.me().rd()\n", "impl C\n    fn me(self: *C) -> *C\n        self\n\n"),
                      RECEIVER_SHORT_OF_SELF),
    "struct_value": (_main("    ^c.rd()\n"), RECEIVER_SHORT_OF_SELF),
    "struct_literal": (_main("    ^C { x: 3 }.rd()\n"), RECEIVER_SHORT_OF_SELF),
    "two_levels_short": (_main("    ^q.r3()\n"), RECEIVER_SHORT_OF_SELF),
    "let_into_mutable": (_main("    let p: *C = @&c\n    ^p.rd()\n"), let_into_mut("p")),
}

# ritz1 lowered a `self: **C` as a `*C` until #3071, at the call and in the body.
GAPS = {"ritz0": {}, "ritz1": {}, "ritz1_selfhosted": {}}


def _params(table):
    for row in table:
        for compiler in COMPILERS:
            gap = GAPS[compiler].get(row)
            marks = [pytest.mark.xfail(strict=True, reason=f"AGAST #{gap}")] if gap else []
            yield pytest.param(row, compiler, marks=marks, id=f"{row}-{compiler}")


@pytest.mark.parametrize("row,compiler", list(_params(RUNS)))
def test_a_place_one_level_short_is_borrowed(tmp_path, compiler, row):
    src, want = RUNS[row]
    assert _run(compiler, tmp_path, row, src) == want


@pytest.mark.parametrize("row,compiler", list(_params(REFUSED)))
def test_nothing_else_is_borrowed_for_self(tmp_path, compiler, row):
    src, message = REFUSED[row]
    _assert_refused(compiler, tmp_path, row, src, message)
