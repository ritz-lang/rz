"""AGAST #3727: an async fn's poll is a state machine over its whole body.

ritz0's lowering (ritz0/async_transform_v2.py) built the poll as one
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
from test_table_rows import assert_refusals, assert_runs

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
# main polls go by hand, counting Pending answers into the exit code.  A poll
# is false while Pending, and true with the value in `__result` (R78, #3728).
_POLL_GO = ("pub fn main() -> i32\n    var f = go()\n    var pends: i32 = 0\n"
            "    while !future_poll(@&f)\n        pends += 1\n    f.__result + pends * 100\n")

# A and B count their runs; each is Ready at once.
_AB = ("var A: i32 = 0\nvar B: i32 = 0\n\n"
       "async fn a() -> i32\n    A += 1\n    1\n\nasync fn b() -> i32\n    B += 1\n    2\n\n")

_BUMP = "fn bump(x: i32) -> i32\n    B += 1\n    x\n\n"
_AND_RHS = "    if c && bump(await a()) > 0\n        return B * 10 + A\n    A + B\n"

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
    # A loop body's local used after the await is live across a state
    # boundary: it stays a future field (AGAST #4527's crossing half).
    "loop_body_local_used_after_await": (_DBL + _go(
        "(n: i32) -> i32", "    var i: i32 = 0\n    var s: i32 = 0\n    while i < n\n"
        "        i += 1\n        let v: i32 = i * 10\n        await dbl(i)\n        s += v\n    s\n", "(3)"), 60),
    # Pending: the poll returns, and the next poll resumes at the await.  The
    # statement ahead of it ran once (CALLS), not once per poll.
    "pending_resumes_at_await": (_LATER + "async fn go() -> i32\n    CALLS += 1\n    let v: i32 = await later()\n"
                                 "    v + CALLS * 10\n\n" + _POLL_GO, 215),
    # The inner future is kept in go's: mid's statement ahead of its own
    # pending await runs once, not on every poll of go.
    # AGAST #4013: the right of `&&` / `||` awaits only when it is evaluated,
    # through a bool field: A counts a()'s runs, B b()'s.
    # bump counts into B: the right operand runs once, not again where the
    # condition reads its value.
    "and_rhs_runs": (_AB + _BUMP + _go("(c: bool) -> i32", _AND_RHS, "(true)"), 11),
    "and_rhs_short": (_AB + _BUMP + _go("(c: bool) -> i32", _AND_RHS, "(false)"), 0),
    "or_rhs_short_let": (_AB + _go("(c: bool) -> i32", "    let v: bool = c || (await b()) > 1\n    if v\n"
                                   "        return 10 + B\n    B\n", "(true)"), 10),
    # A `while` condition's right operand is awaited again on every pass.
    "and_rhs_in_while_cond": (_DBL + _go("(n: i32) -> i32", "    var i: i32 = 0\n"
                                         "    while i < 5 && (await dbl(i)) < n\n        i += 1\n    i\n", "(6)"), 3),
    # A range `for` (AGAST #4188): the loop var and the end are future
    # fields, the end evaluated once; `continue` increments.
    "for_body": (_DBL + _go("(n: i32) -> i32", "    var s: i32 = 0\n    for i in 0..n\n"
                            "        s += await dbl(i)\n    s\n", "(3)"), 6),
    "for_continue_break_end_once": (_DBL + "var CALLS: i32 = 0\n\nfn lim(n: i32) -> i32\n    CALLS += 1\n    n\n\n"
                                    + _go("(n: i32) -> i32", "    var s: i32 = 0\n    for i in 1..lim(n)\n"
                                          "        if i == 2\n            continue\n        if i == 5\n"
                                          "            break\n        s += await dbl(i)\n    s * 10 + CALLS\n",
                                          "(9)"), 161),
    # An awaited bound, `..=`, and sibling loops on one name: two awaiting,
    # one not.
    "for_inclusive_await_bound": (_DBL + _go("(n: i32) -> i32",
                                             "    var s: i32 = 0\n    for i in (await dbl(1))..=n\n"
                                             "        s += await dbl(i)\n    for i in 0..(2 as i32)\n"
                                             "        s += await dbl(i)\n    for i in 0..(3 as i32)\n        s += i\n"
                                             "    s\n", "(4)"), 23),
    # The loop var survives a Pending poll; the statement ahead runs once.
    "for_pending_resumes": (_LATER + "async fn go() -> i32\n    CALLS += 1\n    var s: i32 = 0\n"
                            "    for i in 0..(2 as i32)\n        s += i + await later()\n    s + CALLS * 10\n\n"
                            + _POLL_GO, 221),
    # #4013's `__short_K` and #4188's `__for_K` fields in one future.
    "for_and_rhs": (_DBL + _go("(n: i32) -> i32", "    var s: i32 = 0\n    for i in 0..n\n"
                               "        if i > 1 && (await dbl(i)) > 4\n            s += i\n    s\n", "(5)"), 7),
    # A `match` whose arms await (AGAST #4189): only the taken arm's do.
    "match_arm_taken": (_AB + _go("(x: i32) -> i32", "    let v: i32 = match x\n        0 => await a()\n"
                                  "        _ => await b()\n    v * 100 + A * 10 + B\n", "(0)"), 110),
    "match_arm_other": (_AB + _go("(x: i32) -> i32", "    match x\n        0 => await a()\n        _ => 2\n",
                                  "(7)"), 2),
    # Only the scrutinee awaits: the match runs whole after it, so its type
    # needn't be told; and a tail match that doesn't await, in a fn that does.
    "match_scrutinee_await_only": (_DBL + "struct P\n    n: i32\n\nasync fn go(p: *P) -> i32\n"
                                   "    match p.n + await dbl(1)\n        0 => 1\n        k => k * 10\n\n"
                                   "pub fn main() -> i32\n    var p: P = P { n: 3 }\n    await go(@p)\n", 50),
    "match_tail_no_await": (_DBL + _go("(x: i32) -> i32", "    let a: i32 = await dbl(1)\n    match x\n"
                                       "        0 => 1\n        _ => a\n", "(5)"), 2),
    # An arm's binding is read after the await: the scrutinee is a future
    # field, `__match_K`, matched again in each of the arm's states.
    "match_binding_across_await": (_DBL + _go("(x: i32) -> i32", "    match x\n        0 => 1\n"
                                              "        n => n + await dbl(n)\n", "(5)"), 15),
    # A variant's payload survives a Pending poll; the scrutinee is awaited.
    "match_payload_pending": (_LATER + "enum E\n    A(i32)\n    B\n\nasync fn mk(v: i32) -> E\n    E.A(v)\n\n"
                              "async fn go() -> i32\n    CALLS += 1\n    match await mk(4)\n        A(v) =>\n"
                              "            let w: i32 = await later()\n            v + w + CALLS * 10\n"
                              "        B => 1\n\n" + _POLL_GO, 219),
    # `break` / `continue` in a `match` of a loop that awaits, and a `pass` arm.
    "match_break_continue": (_DBL + _go("() -> i32", "    var s: i32 = 0\n    var i: i32 = 0\n    while i < 10\n"
                                        "        i += 1\n        match i\n            2 => continue\n"
                                        "            5 => break\n            _ => pass\n"
                                        "        s += await dbl(i)\n    s * 10 + i\n", "()"), 165),
    # A nested binding match, in a range `for` beside a short-circuit:
    # #4013's `__short_K`, #4188's `__for_K` and `__match_K` in one future.
    "match_nested_in_for": (_DBL + "enum E\n    A(i32)\n    B\n\n"
                            + _go("(e: E) -> i32", "    var s: i32 = 0\n    for i in 0..(3 as i32)\n"
                                  "        if i > 0 && (await dbl(i)) > 2\n            s += 100\n"
                                  "        match e\n            A(v) =>\n                match (i + v) as i32\n"
                                  "                    5 =>\n                        s += await dbl(v)\n"
                                  "                    w =>\n                        s += w * 10 + await dbl(i)\n"
                                  "            B =>\n                s += 1\n    s\n", "(E.A(4))"), 212),
    # A value `if` that is an operand, and awaits (AGAST #4190): its value is
    # an `__if_K` field the taken arm's states write, which the expression
    # reads.  Only the taken arm awaits; A counts a()'s runs, B b()'s.
    "if_operand_then": (_AB + _go("(c: bool) -> i32", "    let v: i32 = 1 + if c then await a() else await b()\n"
                                  "    v * 50 + A * 10 + B\n", "(true)"), 110),
    "if_operand_else": (_AB + _go("(c: bool) -> i32", "    let v: i32 = 1 + if c then await a() else await b()\n"
                                  "    v * 50 + A * 10 + B\n", "(false)"), 151),
    # An arm that doesn't await, in a loop: the field's type is the arm
    # value's that isn't a bare literal (an i64 field would be narrowed).
    "if_operand_literal_arm": (_DBL + _go("(c: bool) -> i32", "    var s: i32 = 0\n    while s < 30\n"
                                          "        s = s + 2 * if c then 7 else 1 + await dbl(2)\n"
                                          "        c = !c\n    s\n", "(true)"), 38),
    # Survives a Pending poll; the statement ahead of it runs once.
    "if_operand_pending": (_LATER + "async fn go() -> i32\n    CALLS += 1\n"
                           "    let v: i32 = 0 + if CALLS > 0 then await later() else 0\n"
                           "    v + CALLS * 10\n\n" + _POLL_GO, 215),
    # An `&&` in the condition and a nested awaiting `if` in an arm's sum
    # (its type read through the `+`), in a range `for`: `__for_K`,
    # `__short_K` and two `__if_K` fields in one future.
    "if_operand_nested_for": (_DBL + _go("(n: i32) -> i32", "    var s: i32 = 0\n    for i in 0..n\n"
                                         "        s += 1 + if i > 0 && (await dbl(i)) > 2 then "
                                         "100 + (if i == 2 then await dbl(5) else await dbl(20)) else 0\n"
                                         "    s\n", "(4)"), 254),
    "pending_inner_future_kept": (_LATER + "async fn mid() -> i32\n    CALLS += 1\n    let v: i32 = await later()\n"
                                  "    v\n\nasync fn go() -> i32\n    let v: i32 = await mid()\n"
                                  "    v + CALLS * 10\n\n" + _POLL_GO, 215),
    # AGAST #4191: a `defer` in a block the machine splits runs at every exit
    # edge of that block, not at the end of a state.  G counts its runs, so a
    # row that doesn't run it (or runs it twice) exits differently.
    # Falling off the end: the tail value is evaluated first (G is 0 there),
    # the deferred body runs (G is 1), then Ready; main reads G back.
    "defer_fallthrough": ("var G: i32 = 0\n\n" + _DBL +
                          "async fn go(n: i32) -> i32\n    defer G = G + 1\n"
                          "    let v: i32 = await dbl(n)\n    v * 10 + G\n\n"
                          "pub fn main() -> i32\n    let r: i32 = await go(3)\n    G * 100 + r\n", 160),
    # `return` in the block: the value is computed (6 + G, G still 0), then
    # the defer runs (G is 10), then Ready.
    "defer_on_return": ("var G: i32 = 0\n\n" + _DBL +
                        "async fn go(n: i32) -> i32\n    defer G = G + 10\n"
                        "    let v: i32 = await dbl(n)\n    if v > 0\n        return v + G\n    v\n\n"
                        "pub fn main() -> i32\n    let r: i32 = await go(3)\n    G + r\n", 16),
    # `break` leaves the loop body: its defer runs once per pass, including
    # the pass that breaks.
    "defer_loop_break": ("var G: i32 = 0\n\n" + _DBL +
                         "async fn go(n: i32) -> i32\n    var s: i32 = 0\n    var i: i32 = 0\n"
                         "    while i < n\n        i += 1\n        defer G = G + 1\n"
                         "        let d: i32 = await dbl(i)\n        if d > 4\n            break\n"
                         "        s += d\n    s * 10 + G\n\n"
                         "pub fn main() -> i32\n    await go(3)\n", 63),
    # `continue` leaves the loop body too: the deferred body runs on that pass.
    "defer_loop_continue": ("var G: i32 = 0\n\n" + _DBL +
                            "async fn go(n: i32) -> i32\n    var s: i32 = 0\n    var i: i32 = 0\n"
                            "    while i < n\n        i += 1\n        defer G = G + 1\n"
                            "        if i == 2\n            continue\n"
                            "        s += await dbl(i)\n    s * 10 + G\n\n"
                            "pub fn main() -> i32\n    await go(4)\n", 164),
    # Two defers in one block run in reverse order (LIFO).
    "defer_lifo": ("var G: i32 = 0\n\n" + _DBL +
                   "async fn go(n: i32) -> i32\n    defer G = G * 10 + 1\n    defer G = G * 10 + 2\n"
                   "    let v: i32 = await dbl(n)\n    v\n\n"
                   "pub fn main() -> i32\n    let r: i32 = await go(3)\n    G * 10 + r\n", 216),
    # A defer in an arm of an awaiting `if`, after its await: the arm's exit
    # runs it, then the fn's tail reads it.
    "defer_in_awaiting_arm_taken": ("var G: i32 = 0\n\n" + _DBL +
                                    "async fn go(c: bool, n: i32) -> i32\n    var x: i32 = 0\n"
                                    "    if c\n        let v: i32 = await dbl(n)\n        defer G = G + 10\n"
                                    "        x = v\n    else\n        x = 1\n    x * 10 + G\n\n"
                                    "pub fn main() -> i32\n    await go(true, 3)\n", 70),
    "defer_in_awaiting_arm_not_taken": ("var G: i32 = 0\n\n" + _DBL +
                                        "async fn go(c: bool, n: i32) -> i32\n    var x: i32 = 0\n"
                                        "    if c\n        let v: i32 = await dbl(n)\n        defer G = G + 10\n"
                                        "        x = v\n    else\n        x = 1\n    x * 10 + G\n\n"
                                        "pub fn main() -> i32\n    await go(false, 3)\n", 10),
    # A no-await arm of an awaiting `if` holding a defer: ritz0 keeps the arm
    # whole, so ritz1 must lower the same defer (AGAST #4191, al_lower_arm).
    "defer_in_no_await_arm": ("var G: i32 = 0\n\n" + _DBL +
                              "async fn go(c: bool, n: i32) -> i32\n    var x: i32 = 0\n"
                              "    if c\n        x = await dbl(n)\n"
                              "    else\n        defer G = G + 10\n        x = 1\n    x * 10 + G\n\n"
                              "pub fn main() -> i32\n    await go(false, 3)\n", 20),
    # A `return` leaves two blocks: the loop body's defer, then the fn's,
    # innermost first; the return value is computed before either (G is 1
    # there, 2 once the body's defer runs, 12 once the fn's does too).
    "defer_nested_return": ("var G: i32 = 0\n\n" + _DBL +
                            "async fn go(n: i32) -> i32\n    defer G = G + 10\n    var i: i32 = 0\n"
                            "    while i < n\n        i += 1\n        defer G = G + 1\n"
                            "        let d: i32 = await dbl(i)\n        if d > 2\n"
                            "            return i * 10 + G\n    G\n\n"
                            "pub fn main() -> i32\n    let r: i32 = await go(3)\n    G * 10 + r\n", 141),
    # The deferred statement is evaluated at exit, seeing its names' values
    # then: n is 13 by the tail's await, and the defer reads that 13.
    "defer_evaluated_at_exit": ("var G: i32 = 0\n\n" + _DBL +
                                "async fn go(n: i32) -> i32\n    defer G = G + n\n    n = n + 10\n"
                                "    await dbl(n)\n\n"
                                "pub fn main() -> i32\n    let r: i32 = await go(3)\n    r + G\n", 39),
    # The block form of `defer`: its statements run in source order at exit.
    "defer_block_form": ("var G: i32 = 0\n\n" + _DBL +
                         "async fn go(n: i32) -> i32\n    defer\n        G = G + 1\n        G = G + 2\n"
                         "    await dbl(n)\n\n"
                         "pub fn main() -> i32\n    let r: i32 = await go(3)\n    G * 10 + r\n", 36),
    # `break` leaves the loop body, not the fn: the body's defer runs, the
    # fn's does not (it waits for the tail's Ready).
    "defer_break_skips_outer": ("var G: i32 = 0\n\n" + _DBL +
                                "async fn go(n: i32) -> i32\n    defer G = G + 10\n    var i: i32 = 0\n"
                                "    while i < n\n        i += 1\n        defer G = G + 1\n"
                                "        let d: i32 = await dbl(i)\n        if d > 4\n            break\n"
                                "    i * 10 + G\n\n"
                                "pub fn main() -> i32\n    let r: i32 = await go(3)\n    r + G * 10\n", 163),
}


# AGAST #4527: an owned local declared in a block the machine re-enters (a
# loop body, or a `defer` body, which #4191 runs on every exit edge) must not
# become one future field, or each pass stores over the last and nothing drops
# the old one.  It stays a poll local and the emitter's block-end drop frees it
# once per run.  `DROPS` counts the frees, and the future is polled to
# completion inside an inner block so it is destroyed before the counter is
# read.
_TRACKED = """\
trait Drop
    fn drop(self: @&Self)

var DROPS: i32 = 0
var MARKS: i32 = 0

struct Tracked
    id: i32

impl Drop for Tracked
    fn drop(self: @&Tracked)
        DROPS = DROPS + 1

fn tracked(id: i32) -> Tracked
    return Tracked { id: id }
"""

_POLL_IN_BLOCK = """\

pub fn main() -> i32
    var out: i32 = 0
    if true
        var f = go(3)
        while !future_poll(@&f)
            out = out + 100
    return out * 10 + {tail}
"""

# Rows for AGAST #4527: a local in a re-entered block drops once per run.
_OWNED_LOCAL_ROWS = {
    # A plain owned local in an awaiting loop body: three passes make three
    # values, each must drop once.
    "loop_body_owned_local_drops_per_pass": (_TRACKED + _DBL +
        "async fn go(n: i32) -> i32\n    var i: i32 = 0\n    while i < n\n"
        "        i += 1\n        let inner: Tracked = tracked(i)\n        await dbl(i)\n"
        + _POLL_IN_BLOCK.format(tail="DROPS"), 3),
    # ...and the same in a `defer` body, which runs once per pass (#4191):
    # MARKS counts its runs (3), DROPS its owned locals' frees (3).
    "defer_body_owned_local_drops_per_run": (_TRACKED + _DBL +
        "async fn go(n: i32) -> i32\n    var i: i32 = 0\n    while i < n\n"
        "        i += 1\n        defer\n            let inner: Tracked = tracked(i)\n"
        "            MARKS = MARKS + 1\n        await dbl(i)\n"
        + _POLL_IN_BLOCK.format(tail="MARKS * 4 + DROPS"), 15),
}

OWNED_LOCAL_GAPS = {}


# An awaiting `if` operand in the block form, whose arms hold statements:
# ritz1's grammar takes only the inline `if c then a else b` as an operand,
# so these rows are ritz0's (AGAST #4190).
RITZ0_RUNS = {
    "if_operand_block_arms": (_DBL + _go("(c: bool) -> i32", "    var s: i32 = 0\n    while s < 30\n"
                                         "        s = s + 2 * if c\n            7\n        else\n"
                                         "            let t: i32 = await dbl(2)\n            t + 1\n"
                                         "        c = !c\n    s\n", "(true)"), 38),
    "if_operand_block_nested": (_DBL + _go("(n: i32) -> i32", "    var s: i32 = 0\n    for i in 0..n\n"
                                           "        s += 1 + if i > 0 && (await dbl(i)) > 2\n"
                                           "            100 + if i == 2\n                await dbl(5)\n"
                                           "            else\n                await dbl(20)\n"
                                           "        else\n            0\n    s\n", "(4)"), 254),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_async_body_runs_as_written(tmp_path, compiler):
    assert_runs(compiler, tmp_path, {**RUNS, **(RITZ0_RUNS if compiler == "ritz0" else {})})


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_owned_local_in_reentered_block_drops(tmp_path, compiler):
    """AGAST #4527: an owned local in a re-entered block drops once per run.

    A local that dies within one state of a loop or `defer` body stays a
    poll local, so the emitter's block-end drop frees it each pass; one live
    across an `await` stays a future field (the RUNS row above)."""
    assert_runs(compiler, tmp_path, _OWNED_LOCAL_ROWS, OWNED_LOCAL_GAPS)


# Forms whose awaits the state machine doesn't place yet (AGAST #4013): each
# is refused where it is, not silently run in the wrong order.
_UNPLACED = "`await` inside {what} in an async fn is not supported yet (AGAST #4013)"

# name -> (program with `^` at the diagnostic, message)
REFUSALS = {
    # An arm that binds a name re-matches the scrutinee from a future field,
    # which needs a type (#4189).
    "match_untyped_scrutinee": (_DBL + "struct P\n    n: i32\n\nasync fn go(p: *P) -> i32\n    match ^p.n\n"
                                "        0 => 1\n        k => k + await dbl(k)\n\n"
                                "pub fn main() -> i32\n    var p: P = P { n: 3 }\n    await go(@p)\n",
                                "cannot infer the type of the `match`'s scrutinee, which `go`'s future holds across "
                                "an `await`: match a typed local (`let v: T = ...`)"),
    "for_iterable": (_DBL + "async fn go(q: i32) -> i32\n    var s: i32 = 0\n    for x in q\n"
                     "        s += ^await dbl(x)\n    s\n\npub fn main() -> i32\n    await go(3)\n",
                     _UNPLACED.format(what="a `for` over an iterable")),
    # An awaiting `for`'s var is a future field, which needs a type (#4188).
    "for_untyped_bound": (_DBL + "struct P\n    n: i32\n\nasync fn go(p: *P) -> i32\n    var s: i32 = 0\n"
                          "    ^for i in 0..p.n\n        s += await dbl(1)\n    s\n\n"
                          "pub fn main() -> i32\n    var p: P = P { n: 3 }\n    await go(@p)\n",
                          "cannot infer the type of `i`, which `go`'s future holds across an `await`: "
                          "cast a bound of its range (`0..(n as i64)`)"),
    # An awaiting `if` operand's value is a future field, which needs a type
    # (#4190): neither arm's tells it.
    "if_operand_untyped": (_DBL + "struct P\n    n: i32\n\nasync fn go(p: *P, c: bool) -> i32\n"
                           "    let v: i32 = 1 + ^if c then p.n else p.n + await dbl(1)\n    v\n\n"
                           "pub fn main() -> i32\n    var p: P = P { n: 3 }\n    await go(@p, true)\n",
                           "cannot infer the type of the `if`'s value, which `go`'s future holds across "
                           "an `await`: cast an arm (`x as i32`)"),
    # A deferred statement that itself awaits would need its own states on
    # every exit edge: refused at the `await` (AGAST #4191).
    "defer_body_awaits": (_DBL + "async fn go(n: i32) -> i32\n    defer ^await dbl(n)\n    n\n\n"
                          "pub fn main() -> i32\n    await go(3)\n",
                          "`await` inside a `defer` in an async fn is not supported yet (AGAST #4013)"),
}

# An awaiting `match` that is an operand is refused, as is a jump out of the
# loop from an operand's arm: only a value `match` (a let's, an assignment's,
# a return's) and an awaiting `if` operand (#4190) are lowered.  ritz1's
# grammar takes no such operand (`1 + match x` is its parse error, and an
# inline `if`'s arms hold no `break`), so these rows are ritz0's.
RITZ0_REFUSALS = {
    "match_in_expression": (_DBL + "async fn go(x: i32) -> i32\n    let v: i32 = 1 + match x\n"
                            "        0 => ^await dbl(1)\n        _ => 2\n    v\n\npub fn main() -> i32\n    await go(0)\n",
                            _UNPLACED.format(what="a `match` inside an expression")),
    "jump_in_operand": (_DBL + "async fn go(c: bool) -> i32\n    var s: i32 = 0\n    while s < 10\n"
                        "        s += await dbl(1)\n        let v: i32 = 1 + if c\n            ^break\n"
                        "        else\n            2\n        s += v\n    s\n\npub fn main() -> i32\n    await go(true)\n",
                        "`break` / `continue` inside an expression of an async fn's loop that awaits "
                        "is not supported yet (AGAST #4013)"),
    # An awaiting `if` operand is lowered (#4190), but not an arm's jump out
    # of the loop: it would leave the poll's dispatch loop.
    "jump_in_awaiting_operand": (_DBL + "async fn go(c: bool) -> i32\n    var s: i32 = 0\n    while s < 10\n"
                                 "        let v: i32 = 1 + if c\n            ^break\n"
                                 "        else\n            await dbl(2)\n        s += v\n    s\n\n"
                                 "pub fn main() -> i32\n    await go(true)\n",
                                 "`break` / `continue` inside an expression of an async fn's loop that awaits "
                                 "is not supported yet (AGAST #4013)"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_unplaced_await_is_refused(tmp_path, compiler):
    assert_refusals(compiler, tmp_path, {**REFUSALS, **(RITZ0_REFUSALS if compiler == "ritz0" else {})})
