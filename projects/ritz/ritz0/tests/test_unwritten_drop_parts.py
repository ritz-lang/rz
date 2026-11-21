"""Definite initialisation of a binding with drop glue (LANGUAGE_SPEC §13.6,
AGAST #4033, #4096; Aaron's decision of 2026-11-19, option (a)).

`var w: W` with no initialiser, W holding a field with drop glue, used to be
movable, returnable and droppable with that field never written: whoever
dropped it ran `drop` over stack bytes (nexus `page_cache_new` crashed so).
Now each part of W with drop glue starts unwritten (ritz0/uninit_rules.py,
ritz1 own_start_unwritten), and on all three compilers:

- using `w` whole (moving, returning, lending it), or an unwritten part, is an
  error at the use, until every path wrote the part;
- `w` dropped (the end of its block, `return`, `break`) with a part unwritten
  on some path is an error;
- a written part is dropped, once; the first store into a part drops nothing;
- `@w as *U` hands w to code that writes it through the pointer (ritzlib's
  ptr_read): w counts as written whole from there.

Each run row dirties the stack first (0xAA, as nexus test/test_page_cache.ritz
does), so a drop of an unwritten part counts in BAD and the row fails
deterministically on a compiler without the rule.  A run row exits with the
number of drops, or 200 + BAD.
"""

import pytest

from test_ref_into_value import COMPILERS
from test_table_rows import assert_refusals, assert_runs

pytestmark = pytest.mark.integration

PRELUDE = """\
var BAD: i32 = 0
var DROPS: i32 = 0

struct G
    tag: i64

impl Drop for G
    fn drop(self: @&G)
        DROPS = DROPS + 1
        if self.tag != 7
            BAD = BAD + 1

struct W
    g: G
    n: i32

struct O
    k: i32
    w: W

struct P<T>
    p: *T
    n: i32

[[noinline]]
fn dirty_stack() -> i32
    var d: [8192]u8 = [0; 8192]
    var i: i32 = 0
    while i < 8192
        volatile_store(@d[i], 170)
        i = i + 1
    volatile_load(@d[77]) as i32

fn eat(w: W) -> i32
    w.n

fn peek(w: @W) -> i32
    w.n

fn cond() -> bool
    DROPS == 0

"""

MAIN = """
pub fn main() -> i32
    dirty_stack()
    f()
    if BAD != 0
        return 200 + BAD
    DROPS
"""


def _run(body: str) -> str:
    return PRELUDE + "[[noinline]]\n" + body + MAIN


RAW_COPY = """\
fn cp(d: *u8, s: *u8, n: i64)
    var i: i64 = 0
    while i < n
        *(d + i) = *(s + i)
        i = i + 1

fn rd(p: *{T}) -> {T}
    var out: {T}
    cp(@out as *u8, p as *u8, sizeof({T}))
    out

"""

# What a binding with every part written does: it drops each written part once.
RUNS = {
    # A part written field by field, then returned: the caller drops it once.
    "written_then_returned": (
        "fn mk() -> W\n    var w: W\n    w.g = G { tag: 7 }\n    w.n = 1\n    w\n\n"
        "fn f() -> i32\n    var w = mk()\n    w.n\n", 1),
    # Dropped where it was declared, which used to leak it (no drop at all).
    "written_then_dropped": (
        "fn f() -> i32\n    var w: W\n    w.g = G { tag: 7 }\n    w.n = 2\n    w.n\n", 1),
    "written_on_both_arms": (
        "fn f() -> i32\n    var w: W\n    if cond()\n        w.g = G { tag: 7 }\n"
        "    else\n        w.g = G { tag: 7 }\n    w.n = 1\n    eat(w)\n", 1),
    # A second store drops the first value; the first dropped nothing.
    "written_twice": (
        "fn f() -> i32\n    var w: W\n    w.g = G { tag: 7 }\n    w.g = G { tag: 7 }\n"
        "    w.n = 1\n    w.n\n", 2),
    "assigned_whole": (
        "fn f() -> i32\n    var w: W\n    w.n = 5\n    w = W { g: G { tag: 7 }, n: 1 }\n    w.n\n", 1),
    "nested_part": (
        "fn mk() -> O\n    var o: O\n    o.k = 1\n    o.w.n = 2\n    o.w.g = G { tag: 7 }\n    o\n\n"
        "fn f() -> i32\n    let o = mk()\n    o.k\n", 1),
    # Declared in a loop body: each pass starts unwritten again.
    "in_a_loop": (
        "fn f() -> i32\n    var i: i32 = 0\n    while i < 3\n        var w: W\n"
        "        w.g = G { tag: 7 }\n        w.n = i\n        i = i + 1\n    i\n", 3),
    # A type with its own drop starts unwritten whole: it owns nothing until
    # assigned, so the assignment drops nothing and an unassigned one nothing.
    "own_drop_assigned": (
        "fn f() -> i32\n    var g: G\n    g = G { tag: 7 }\n    0\n", 1),
    "own_drop_never_assigned": (
        "fn f() -> i32\n    var g: G\n    0\n", 0),
    # Move-only only through its type argument (`Vec<G>`'s shape): no part
    # has drop glue, so nothing is unwritten and nothing drops.
    "move_only_by_its_argument": (
        "fn mk() -> P<G>\n    var b: P<G>\n    b.p = null\n    b.n = 0\n    b\n\n"
        "fn f() -> i32\n    let b = mk()\n    b.n\n", 0),
    # `@x as *U` hands x to raw code that writes it (ritzlib's ptr_read): x
    # counts as written whole there.  A bitwise copy, so both copies drop.
    "raw_written_whole": (RAW_COPY.format(T="G") +
        "fn f() -> i32\n    var g = G { tag: 7 }\n    let h = rd(@g)\n    0\n", 2),
    "raw_written_parts": (RAW_COPY.format(T="W") +
        "fn f() -> i32\n    var w = W { g: G { tag: 7 }, n: 1 }\n    let v = rd(@w)\n    v.n\n", 2),
    # Written so and dropped where it was declared: its drop runs.
    "raw_written_then_dropped_whole": (RAW_COPY.format(T="G") +
        "fn f() -> i32\n    var g = G { tag: 7 }\n    var o: G\n"
        "    cp(@o as *u8, @g as *u8, sizeof(G))\n    0\n", 2),
    "raw_written_then_dropped_parts": (RAW_COPY.format(T="W") +
        "fn f() -> i32\n    var w = W { g: G { tag: 7 }, n: 1 }\n    var o: W\n"
        "    cp(@o as *u8, @w as *u8, sizeof(W))\n    o.n\n", 2),
}

USE = "`{p}` may be unwritten: `{b}` has no initialiser (§13.6)"
DROP = "`{p}` may be unwritten when `{b}` is dropped: `{b}` has no initialiser (§13.6)"


def _use(p, b="w"):
    return USE.format(p=p, b=b)


def _drop(p, b="w"):
    return DROP.format(p=p, b=b)


def _refused(body: str) -> str:
    return PRELUDE + body + "\npub fn main() -> i32\n    0\n"


REFUSALS = {
    "returned_as_tail": (
        _refused("fn mk() -> W\n    var w: W\n    w.n = 1\n    ^w\n"), _use("w.g")),
    "returned": (
        _refused("fn mk() -> W\n    var w: W\n    w.n = 1\n    return ^w\n"), _use("w.g")),
    "passed_by_value": (
        _refused("fn f() -> i32\n    var w: W\n    w.n = 1\n    eat(^w)\n"), _use("w.g")),
    "lent": (
        _refused("fn f() -> i32\n    var w: W\n    w.n = 1\n    peek(^@w)\n"), _use("w.g")),
    # Without the cast, lending it to a `*W` parameter is a use (spire's
    # `var c: Cache; cache_init_tcp(@c, ..); c`).
    "lent_to_a_raw_parameter": (
        _refused("fn init(p: *W)\n    p.n = 1\n\nfn f() -> i32\n    var w: W\n    init(^@w)\n    0\n"),
        _use("w.g")),
    "nested_part_returned": (
        _refused("fn mk() -> O\n    var o: O\n    o.k = 1\n    o.w.n = 2\n    ^o\n"),
        _use("o.w.g", "o")),
    "written_on_one_arm": (
        _refused("fn mk() -> W\n    var w: W\n    w.n = 1\n    if cond()\n"
                 "        w.g = G { tag: 7 }\n    ^w\n"), _use("w.g")),
    # A part that can't be split (G has its own drop) is written whole or
    # not at all: a store into it is a use of the unwritten part (LARB R59).
    "unwritten_part_field_store": (
        _refused("fn f() -> i32\n    var w: W\n    w.n = 1\n    ^w.g.tag = 7\n    w.n\n"),
        _use("w.g")),
    "own_drop_field_store": (
        _refused("fn f() -> i64\n    var g: G\n    ^g.tag = 7\n    0\n"), _use("g", "g")),
    "own_drop_field_read": (
        _refused("fn f() -> i64\n    var g: G\n    let t = ^g.tag\n    t\n"), _use("g", "g")),
    "own_drop_lent": (
        _refused("fn see(g: @G) -> i64\n    g.tag\n\n"
                 "fn f() -> i64\n    var g: G\n    see(^@g)\n"), _use("g", "g")),
    "dropped_at_its_block_end": (
        _refused("fn f() -> i32\n    var ^w: W\n    w.n = 1\n    w.n\n"), _drop("w.g")),
    "dropped_by_return": (
        _refused("fn f() -> i32\n    var w: W\n    w.n = 1\n    if cond()\n        ^return 0\n"
                 "    w.g = G { tag: 7 }\n    w.n\n"), _drop("w.g")),
    "dropped_by_break": (
        _refused("fn f() -> i32\n    while cond()\n        var w: W\n        w.n = 1\n        ^break\n"
                 "    0\n"), _drop("w.g")),
    "dropped_after_one_arm": (
        _refused("fn f() -> i32\n    var ^w: W\n    w.n = 1\n    if cond()\n"
                 "        w.g = G { tag: 7 }\n    w.n\n"), _drop("w.g")),
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_written_part_drops_once(compiler, tmp_path):
    assert_runs(compiler, tmp_path, {k: (_run(b), n) for k, (b, n) in RUNS.items()})


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_unwritten_part_is_refused(compiler, tmp_path):
    assert_refusals(compiler, tmp_path, REFUSALS)
