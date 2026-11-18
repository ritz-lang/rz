"""AGAST #3728 / LARB R78: a poll answers `bool`; the result lives in the future.

Every generated `NAME_poll` returned `i32`, with -1 meaning Pending.  So an
`async fn -> i64` (or a pointer, or a struct) was squeezed through i32, and an
async fn whose genuine result was -1 could not be told from Pending: `await`
spun forever on it.

R78: every poll is `fn(*u8) -> bool` (typed `*NAME_Future` here), true once
the body has finished, having written the result into the future's
`__result` field, of the fn's declared type (a unit fn has none).  `await`
polls until true, then reads the field.

Each row separates one path: `await` in a sync fn (the emitter's poll loop)
or inside an async fn (the state machine's resume point), for each result
shape the old i32 lost: an i64 > 2^31, a Ready(-1), a pointer, a struct.
"""

from __future__ import annotations

import pytest

from test_ref_into_value import COMPILERS
from test_table_rows import assert_runs

# 5000000000 > 2^32: any narrowing to 32 bits changes it.
_BIG = "async fn big() -> i64\n    5000000000\n\n"
# A genuine -1: the old Pending.
_NEG = "async fn neg() -> i32\n    0 - 1\n\n"
_PAIR = "struct Pair\n    a: i64\n    b: i32\n\nasync fn pair() -> Pair\n    Pair { a: 5000000000, b: 0 - 1 }\n\n"

# name -> (program, exit code)
RUNS = {
    # The acceptance rows: an i64 > 2^31 and a Ready(-1), through `await`
    # in a sync fn and inside an async fn.
    "i64_sync_await": (_BIG + "pub fn main() -> i32\n    let v: i64 = await big()\n"
                       "    if v == 5000000000\n        return 0\n    1\n", 0),
    "i64_async_await": (_BIG + "async fn go() -> i64\n    let v: i64 = await big()\n    v + 1\n\n"
                        "pub fn main() -> i32\n    let v: i64 = await go()\n"
                        "    if v == 5000000001\n        return 0\n    1\n", 0),
    "ready_minus_one_sync_await": (_NEG + "pub fn main() -> i32\n    let v: i32 = await neg()\n    v + 1\n", 0),
    "ready_minus_one_async_await": (_NEG + "async fn go() -> i32\n    let v: i32 = await neg()\n    v + 2\n\n"
                                    "pub fn main() -> i32\n    await go()\n", 1),
    # An untyped binding of an await takes the awaited fn's declared type,
    # not the old poll's i32.
    "untyped_let_await_is_i64": (_BIG + "async fn go() -> i64\n    let v = await big()\n    v\n\n"
                                 "pub fn main() -> i32\n    let v: i64 = await go()\n"
                                 "    if v == 5000000000\n        return 0\n    1\n", 0),
    # A pointer result comes back whole.
    "pointer_result": ("async fn id(p: *i64) -> *i64\n    p\n\n"
                       "async fn go(p: *i64) -> *i64\n    let q: *i64 = await id(p)\n    q\n\n"
                       "pub fn main() -> i32\n    var x: i64 = 7\n    let q: *i64 = await go(@x)\n"
                       "    let r: *i64 = await id(@x)\n    if q == @x and r == @x\n        return 0\n    1\n", 0),
    # A struct result, through both awaits.
    "struct_result": (_PAIR + "async fn go() -> Pair\n    let p: Pair = await pair()\n    p\n\n"
                      "pub fn main() -> i32\n    let p: Pair = await go()\n"
                      "    if p.a == 5000000000 and p.b == 0 - 1\n        return 0\n    1\n", 0),
    # The poll itself: false while Pending, then true with `__result` set.
    "poll_is_bool_result_in_future": (_NEG + "pub fn main() -> i32\n    var f: neg_Future = neg()\n"
                                      "    if neg_poll(@f)\n        return f.__result + 1\n    9\n", 0),
    # The checker knows a generated future's fields: `f.__result` on a local
    # of one is not an undeclared struct's member (#3404's rule).
    "result_field_read_in_helper": (_BIG + "fn drive() -> i64\n    var f: big_Future = big()\n"
                                    "    while !big_poll(@f)\n        pass\n    f.__result\n\n"
                                    "pub fn main() -> i32\n    if drive() == 5000000000\n        return 0\n    1\n", 0),
    # A unit fn's poll is true when done; its future has no result field.
    "unit_poll_true": ("var RAN: i32 = 0\n\nasync fn u()\n    RAN = 4\n\n"
                       "pub fn main() -> i32\n    var f: u_Future = u()\n"
                       "    if u_poll(@f)\n        return RAN\n    9\n", 4),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_poll_bool_result_in_future(tmp_path, compiler):
    assert_runs(compiler, tmp_path, RUNS)
