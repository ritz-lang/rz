"""AGAST #4006 / LARB R79: a held future, handed over as `@&Future`.

Every generated future starts with a fixed header, poll fn first:

    struct NAME$Future
        __poll: fn(*u8) -> bool     # NAME_poll, set by the constructor
        __state: i32                # -1 once finished (a later poll is true at once)
        __result: T                 # none for a unit fn (R78)
        ...

`Future` is a built-in type that means "some async fn's future".  It has no
size, so only a reference to one is a value: any async fn's future fits an
`@&Future` slot.  `future_poll(f: @&Future) -> bool` calls `f`'s header poll
fn on it.  `await p`, with `p` a held future (`var p = f(args)`), drives it to
completion if it isn't finished, then reads its result: after an executor has
driven it, it only reads.

ritz0 landed as #4006, ritz1 as #4007.  Each row separates one rule: polling
through the header, `await p` before and after it's driven (in a sync fn and
inside an async fn), an i64 result above 2^31 and a real -1 through both, and
each by-value `Future` slot refused where the `Future` is written.  All three
compilers answer alike.
"""

from __future__ import annotations

import pytest

from test_ref_into_value import COMPILERS
from test_table_rows import assert_refusals, assert_runs

# `slow` is Pending twice: its awaited poll source answers the reserved
# POLL_PENDING (-4096) until its third call.  RUNS counts how often its body finished, so a finished future that
# ran again shows.
_SLOW = (
    "var TICKS: i32 = 0\nvar RUNS: i32 = 0\n\n"
    "fn tick() -> i32\n    TICKS = TICKS + 1\n    if TICKS < 3\n        return 0 - 4096\n    0\n\n"
    "async fn slow() -> i64\n    let t: i32 = await tick()\n    RUNS = RUNS + 1\n    5000000000 + t as i64\n\n"
    "async fn neg() -> i32\n    let t: i32 = await tick()\n    RUNS = RUNS + 1\n    t - 1\n\n"
)
# An executor's view: poll through the header until true; how many polls.
_DRIVE = "fn drive(f: @&Future) -> i32\n    var n: i32 = 1\n    while !future_poll(f)\n        n = n + 1\n    n\n\n"

_OK = "        return 0\n    1\n"

RUNS = {
    # future_poll calls the header's poll fn: Pending twice, then true.
    "future_poll_until_true": (_SLOW + _DRIVE + "pub fn main() -> i32\n    var p = slow()\n"
                               "    if drive(@&p) == 3 and RUNS == 1\n" + _OK, 0),
    # After an executor drove it, `await p` only reads: the body doesn't run again.
    "await_after_driven_i64": (_SLOW + _DRIVE + "pub fn main() -> i32\n    var p = slow()\n    drive(@&p)\n"
                               "    let v: i64 = await p\n    if v == 5000000000 and RUNS == 1 and TICKS == 3\n" + _OK, 0),
    "await_after_driven_minus_one": (_SLOW + _DRIVE + "pub fn main() -> i32\n    var p = neg()\n    drive(@&p)\n"
                                     "    let v: i32 = await p\n    if v == 0 - 1 and RUNS == 1\n" + _OK, 0),
    # Before it's driven, `await p` drives it to completion.
    "await_before_driven_i64": (_SLOW + "pub fn main() -> i32\n    var p = slow()\n    let v: i64 = await p\n"
                                "    if v == 5000000000 and RUNS == 1 and TICKS == 3\n" + _OK, 0),
    "await_before_driven_minus_one": (_SLOW + "pub fn main() -> i32\n    var p = neg()\n    let v: i32 = await p\n"
                                      "    if v == 0 - 1 and RUNS == 1\n" + _OK, 0),
    # Inside an async fn: a held future is a resume point, polled until true.
    "async_await_held_i64": (_SLOW + "async fn go() -> i64\n    var p = slow()\n    let v: i64 = await p\n    v + 1\n\n"
                             "pub fn main() -> i32\n    let v: i64 = await go()\n"
                             "    if v == 5000000001 and RUNS == 1\n" + _OK, 0),
    "async_await_held_minus_one": (_SLOW + "async fn go() -> i32\n    var p = neg()\n    let v: i32 = await p\n    v\n\n"
                                   "pub fn main() -> i32\n    let v: i32 = await go()\n"
                                   "    if v == 0 - 1 and RUNS == 1\n" + _OK, 0),
    # ...and one already finished there is only read.
    "async_await_after_driven": (_SLOW + _DRIVE + "async fn go() -> i64\n    var p = slow()\n    drive(@&p)\n"
                                 "    let v: i64 = await p\n    v + 1\n\n"
                                 "pub fn main() -> i32\n    let v: i64 = await go()\n"
                                 "    if v == 5000000001 and RUNS == 1\n" + _OK, 0),
    # A unit fn's future fits too.  The future's type is unspellable (AGAST
    # #3606), so an executor holds it untyped.
    "named_future_and_unit_fn": ("var DONE: i32 = 0\n\nasync fn u()\n    DONE = 5\n\n" + _DRIVE
                                 + "pub fn main() -> i32\n    var p = u()\n    drive(@&p)\n    DONE\n", 5),
    # An `@&Future` field to a future held elsewhere.
    "future_ref_field": (_SLOW + "struct Task\n    f: @&Future\n\n"
                         "fn run(t: @&Task) -> i32\n    var n: i32 = 1\n    while !future_poll(t.f)\n        n = n + 1\n    n\n\n"
                         "pub fn main() -> i32\n    var p = slow()\n    var t = Task { f: @&p }\n"
                         "    if run(@&t) == 3\n        let v: i64 = await p\n        if v == 5000000000 and RUNS == 1\n"
                         "            return 0\n    1\n", 0),
}

_NO_SIZE = "`Future` has no size; take it by reference, `@&Future`"
_F = "async fn f() -> i32\n    7\n\n"

# Each by-value `Future` slot, at the `Future` (the `^`).
REFUSALS = {
    "let": (_F + "pub fn main() -> i32\n    let x: ^Future = f()\n    0\n", _NO_SIZE),
    "var": (_F + "pub fn main() -> i32\n    var x: ^Future = f()\n    0\n", _NO_SIZE),
    "field": ("struct S\n    x: i32\n    f: ^Future\n\npub fn main() -> i32\n    0\n", _NO_SIZE),
    "param": ("fn take(f: ^Future) -> i32\n    0\n\npub fn main() -> i32\n    0\n", _NO_SIZE),
    "array_element": ("pub fn main() -> i32\n    var a: [2]^Future\n    0\n", _NO_SIZE),
    "return": ("fn give() -> ^Future\n    give()\n\npub fn main() -> i32\n    0\n", _NO_SIZE),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_held_future_behind_a_future_ref(compiler, tmp_path):
    assert_runs(compiler, tmp_path, RUNS)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_future_by_value_is_refused(compiler, tmp_path):
    assert_refusals(compiler, tmp_path, REFUSALS)
