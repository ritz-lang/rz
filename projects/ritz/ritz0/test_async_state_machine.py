"""AGAST #3727: an async fn's poll is a state machine over its whole body.

ritz0's lowering (ritz0/async_transform_v2.py) built `NAME_poll` as one
`if state == N` block per await, each running its awaited expression once,
then a final state that evaluated only the body's TAIL.  So every statement
that wasn't `let x = await ...` was dropped (`sum = await f()`, `sum += await
f()`, an `if ... return` between two awaits), an await in a `while` ran once,
both arms' awaits of an `if` ran, and a param used in a `while` or as an
assignment target stayed unresolved ("Unknown identifier: n").

The poll is now a dispatch loop over the body's control-flow graph: each await
is a resume point in its own state, wherever it sits (a loop, an arm), and the
statements between resume points run in the states that reach them.  The
awaited future lives in the future struct, so a Pending inner future is polled
again, not rebuilt.

ritz1's lowering (ritz1/src/async_lower.ritz, #3814) is ritz0's step for step,
so each table runs on every compiler: the futures' layouts must agree.
"""

from __future__ import annotations

import pytest

from test_ref_into_value import COMPILERS
from test_row_table import assert_refusals, assert_runs

# dbl is Ready on its first poll with twice its argument.
_DBL = "async fn dbl(x: i32) -> i32\n    x * 2\n\n"
_STORE = "fn store(p: *i32, v: i32)\n    *p = v\n\n"


def _go(sig: str, body: str, call: str) -> str:
    """`async fn go<sig>` with `body`, and a main exiting with `await go<call>`."""
    return f"async fn go{sig}\n{body}\npub fn main() -> i32\n    await go{call}\n"


# A hand-written poll source: Pending until it has been polled `PENDS` times.
# `await later()` in an async fn re-evaluates it on each poll of the future.
_LATER = ("var TICKS: i32 = 0\nvar CALLS: i32 = 0\n\n"
          "fn later() -> i32\n    TICKS += 1\n    if TICKS <= 2\n        return 0 - 1\n    5\n\n")
# main polls go by hand, counting Pending answers into the exit code.
_POLL_GO = ("pub fn main() -> i32\n    var f: go_Future = go()\n    var pends: i32 = 0\n"
            "    var r: i32 = go_poll(@f)\n    while r == 0 - 1\n        pends += 1\n"
            "        r = go_poll(@f)\n    r + pends * 100\n")

# A and B count their runs; each is Ready at once.
_AB = ("var A: i32 = 0\nvar B: i32 = 0\n\n"
       "async fn a() -> i32\n    A += 1\n    1\n\nasync fn b() -> i32\n    B += 1\n    2\n\n")

# name -> (program, exit code)
RUNS = {
    # The ticket's table.
    "assign_await": (_DBL + _go("() -> i32", "    var sum: i32 = 1\n    sum = await dbl(5)\n    sum\n", "()"), 10),
    "assign_after_let_await": (_DBL + _go(
        "() -> i32", "    var sum: i32 = 1\n    let v: i32 = await dbl(5)\n    sum = sum + v\n    sum\n", "()"), 11),
    "compound_assign_await": (_DBL + _go("() -> i32", "    var sum: i32 = 1\n    sum += await dbl(5)\n    sum\n", "()"), 11),
    "let_await_tail": (_DBL + _go("() -> i32", "    let v = await dbl(5)\n    v + 1\n", "()"), 11),
    # No await: a param in a `while` condition, and as an assignment target.
    "param_in_while_no_await": (_go("(n: i32) -> i32",
                                    "    var i: i32 = 0\n    var s: i32 = 0\n    while i < n\n"
                                    "        s += i\n        i += 1\n    s\n", "(5)"), 10),
    "param_deref_assign_no_await": ("async fn put(p: *i32)\n    *p = 7\n\n"
                                    "pub fn main() -> i32\n    var x: i32 = 0\n    await put(@x)\n    x\n", 7),
    # Only the taken arm's await runs: A * 10 + B.
    "if_arms_then": (_AB + _go("(c: bool) -> i32", "    if c\n        await a()\n    else\n        await b()\n"
                               "    A * 10 + B\n", "(true)"), 10),
    "if_arms_else": (_AB + _go("(c: bool) -> i32", "    if c\n        await a()\n    else\n        await b()\n"
                               "    A * 10 + B\n", "(false)"), 1),
    # AGAST #3023: a let ahead of the first await runs.
    "let_before_await": ("async fn fetch(x: i32) -> i32\n    x\n\n" + _go(
        "(x: i32) -> i32", "    let y: i32 = x * 2\n    let v: i32 = await fetch(y)\n    v\n", "(7)"), 14),
    # 54_async_fs's shape: an early return between two awaits.
    "return_between_awaits_taken": (_DBL + _go(
        "(x: i32) -> i32", "    let a: i32 = await dbl(x)\n    if a < 5\n        return 3\n"
        "    let b: i32 = await dbl(a)\n    b + 1\n", "(2)"), 3),
    "return_between_awaits_not_taken": (_DBL + _go(
        "(x: i32) -> i32", "    let a: i32 = await dbl(x)\n    if a < 5\n        return 3\n"
        "    let b: i32 = await dbl(a)\n    b + 1\n", "(3)"), 13),
    # Loops: `break` and `continue` leave or restart the loop the await is in.
    "loop_break": (_DBL + _go("(n: i32) -> i32",
                              "    var i: i32 = 0\n    var s: i32 = 0\n    while i < n\n"
                              "        let d: i32 = await dbl(i)\n        if d > 4\n            break\n"
                              "        s += d\n        i += 1\n    s * 10 + i\n", "(9)"), 63),
    "loop_continue": (_DBL + _go("(n: i32) -> i32",
                                 "    var i: i32 = 0\n    var s: i32 = 0\n    while i < n\n        i += 1\n"
                                 "        if i == 2\n            continue\n        s += await dbl(i)\n    s\n", "(4)"), 16),
    # Nested loops: each inner pass re-runs, and the outer counter advances.
    "nested_loops": (_DBL + _go("(n: i32) -> i32",
                                "    var s: i32 = 0\n    var i: i32 = 0\n    while i < n\n        var j: i32 = 0\n"
                                "        while j < n\n            s += await dbl(1)\n            j += 1\n"
                                "        i += 1\n    s\n", "(3)"), 18),
    # The condition's await is re-polled on every pass.
    "await_in_while_cond": ("async fn id(x: i32) -> i32\n    x\n\n" + _go(
        "() -> i32", "    var i: i32 = 0\n    while (await id(i)) < 4\n        i += 1\n    i\n", "()"), 4),
    # A param assigned from an await.
    "param_assigned_from_await": (_DBL + _go("(n: i32) -> i32", "    n = n + await dbl(1)\n    n\n", "(5)"), 7),
    # A value `if` whose arms await, bound by a let.
    "let_if_value_awaits": (_AB + _go("(c: bool) -> i32",
                                      "    let v: i32 = if c\n        await a()\n    else\n        await b()\n"
                                      "    v * 100 + A * 10 + B\n", "(false)"), 201),
    # A unit fn awaiting in a loop writes through its param.
    "unit_fn_loop": (_DBL + _STORE + "async fn fill(p: *i32, n: i32)\n    var i: i32 = 0\n    while i < n\n"
                     "        *p = *p + await dbl(i)\n        i += 1\n\n"
                     "pub fn main() -> i32\n    var x: i32 = 1\n    await fill(@x, 4)\n    x\n", 13),
    # Pending: the poll returns, and the next poll resumes at the await.  The
    # statement ahead of it ran once (CALLS), not once per poll.
    "pending_resumes_at_await": (_LATER + "async fn go() -> i32\n    CALLS += 1\n    let v: i32 = await later()\n"
                                 "    v + CALLS * 10\n\n" + _POLL_GO, 215),
    # The inner future is kept in go's: mid's statement ahead of its own
    # pending await runs once, not on every poll of go.
    "pending_inner_future_kept": (_LATER + "async fn mid() -> i32\n    CALLS += 1\n    let v: i32 = await later()\n"
                                  "    v\n\nasync fn go() -> i32\n    let v: i32 = await mid()\n"
                                  "    v + CALLS * 10\n\n" + _POLL_GO, 215),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_async_body_runs_as_written(tmp_path, compiler):
    assert_runs(compiler, tmp_path, RUNS)


# Forms whose awaits the state machine doesn't place yet (AGAST #4013): each
# is refused where it is, not silently run in the wrong order.
_UNPLACED = "`await` inside {what} in an async fn is not supported yet (AGAST #4013)"

# name -> (program with `^` at the diagnostic, message)
REFUSALS = {
    "match_arm": (_DBL + "async fn go(x: i32) -> i32\n    match x\n        0 => ^await dbl(1)\n        _ => 2\n\n"
                  "pub fn main() -> i32\n    await go(0)\n", _UNPLACED.format(what="a `match`")),
    "for_body": (_DBL + "async fn go(n: i32) -> i32\n    var s: i32 = 0\n    for i in 0..n\n"
                 "        s += ^await dbl(1)\n    s\n\npub fn main() -> i32\n    await go(3)\n",
                 _UNPLACED.format(what="a `for` loop")),
    # A defer the machine would split: refused at the `defer` itself.
    "defer_among_states": (_DBL + "async fn go(n: i32) -> i32\n    ^defer n = 0\n    await dbl(n)\n\n"
                           "pub fn main() -> i32\n    await go(3)\n",
                           "`defer` in an async fn that awaits is not supported yet (AGAST #4013)"),
    "and_rhs": (_DBL + "async fn go(c: bool) -> i32\n    if c && (^await dbl(1)) > 0\n        return 1\n    0\n\n"
                "pub fn main() -> i32\n    await go(true)\n", _UNPLACED.format(what="the right of `&&`")),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_unplaced_await_is_refused(tmp_path, compiler):
    assert_refusals(compiler, tmp_path, REFUSALS)
