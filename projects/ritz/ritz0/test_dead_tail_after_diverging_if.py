#!/usr/bin/env python3
"""A statement that can never run is refused: "unreachable code" (AGAST #2520).

LARB ruling (Aaron, 2026-11-15): a statement is unreachable when it follows, in
the same block, a `return`, `break` or `continue`; an `if`/`else` (else-if
chains and nested ifs included) or a `match` whose every arm diverges; or a
`loop` (or `while` on the literal `true`) with no `break` that leaves it. The
first such statement of a block is a located error, on ritz0, ritz1 and
ritz1_selfhosted alike. It extends R13 (every match arm must be reachable) to
statements; LANGUAGE_SPEC §6.1.

Before the ruling (#2485) all three accepted these rows and never ran the dead
code. Their old shapes are kept here as refusals; `^` marks the statement each
compiler must name. ritz0 once left the dead `if.end` block with no terminator
and ritz1 wrote `ret` then `br` into one block (#2823): neither can happen now,
since no compiler reaches IR for these programs.

The controls are programs that look close and must still compile and run.
"""

import pytest

from test_ref_into_value import COMPILERS, _assert_refused, _run

pytestmark = pytest.mark.integration

MESSAGE = "unreachable code"

# name: source with a `^` before the first unreachable statement
REFUSED = {
    # The #2485 repro: a value tail after an if whose arms both return.
    "value_tail": """\
fn g(b: i32) -> i32
    if b > 0
        return 1
    else
        return 2
    ^0
fn main() -> i32
    g(1) * 10 + g(0)
""",
    "else_if_chain": """\
fn g(b: i32) -> i32
    if b > 0
        return 1
    else if b == 0
        return 2
    else
        return 3
    ^0
fn main() -> i32
    g(1)
""",
    "nested_if": """\
fn g(b: i32) -> i32
    if b > 0
        if b > 5
            return 3
        else
            return 1
    else
        return 2
    ^0
fn main() -> i32
    g(9)
""",
    # The tail is a statement, not a value.
    "statement_tail": """\
var G: i32
fn g(b: i32) -> i32
    if b > 0
        return 1
    else
        return 2
    ^G = 7
fn main() -> i32
    g(1)
""",
    "statements_then_value": """\
fn g(b: i32) -> i32
    var x = 0
    if b > 0
        return 1
    else
        return 2
    ^x = 5
    x
fn main() -> i32
    g(1)
""",
    "procedure": """\
var G: i32
fn p(b: i32)
    if b > 0
        G = G + 1
        return
    else
        G = G + 10
        return
    ^G = 100
fn main() -> i32
    p(1)
    G
""",
    # AGAST #2271: the same shape, through a match.
    "match_every_arm_returns": """\
enum E
    A
    B
fn f(e: E) -> i32
    match e
        A => return 1
        B => return 2
    ^3
fn main() -> i32
    f(A)
""",
    # Dead inside a loop body: the `if` leaves the fn on every arm.
    "inside_loop": """\
fn g(b: i32) -> i32
    var i = 0
    while i < 3
        if b > 0
            return 1
        else
            return 2
        ^i = i + 1
    0
fn main() -> i32
    g(1)
""",
    # AGAST #2823: a plain `return`, then a block holding a returning `if`.
    "return_then_returning_if": """\
fn g(p: *u8, out_name: **u8, out_len: *i32)
    *out_name = p
    *out_len = 1
    return
    ^let q: *u8 = null
    if q == null
        return
    *out_name = q

pub fn main() -> i32
    var n: *u8 = null
    var l: i32 = 0
    g(c"x", @n, @l)
    return l - 1
""",
    # The same in a method: emit_impl_method has its own body loop.
    "method_return_then_returning_if": """\
struct S
    n: i32
impl S
    fn set(self: *S, b: i32)
        self.n = b
        return
        ^if b > 0
            return
        self.n = 99
fn main() -> i32
    var s = S { n: 0 }
    s.set(4)
    s.n
""",
    "value_fn_return_then_returning_if": """\
var G: i32
fn g(b: i32) -> i32
    return b + 1
    ^if b > 0
        return 7
    G = 9
fn main() -> i32
    g(2)
""",
    # The ruling's other causes.
    "after_return": """\
fn g(b: i32) -> i32
    return b
    ^b + 1
fn main() -> i32
    g(2)
""",
    "after_break": """\
fn main() -> i32
    var i = 0
    while i < 5
        break
        ^i = i + 1
    i
""",
    "after_continue": """\
fn main() -> i32
    var i = 0
    while i < 5
        i = i + 1
        continue
        ^i = 9
    i
""",
    # The 12 sites #2520 migrated: a dead tail after a loop that only returns.
    "after_loop": """\
fn g() -> i32
    var i = 0
    loop
        i = i + 1
        if i == 3
            return i
    ^return 0
fn main() -> i32
    g()
""",
    "after_while_true": """\
fn g() -> i32
    var i = 0
    while true
        i = i + 1
        if i == 3
            return i
    ^return 0
fn main() -> i32
    g()
""",
    # An inner loop's `break` leaves the inner loop only.
    "after_loop_inner_break": """\
fn g() -> i32
    var i = 0
    loop
        i = i + 1
        for j in 0..3
            if j == 1
                break
        if i == 3
            return i
    ^return 0
fn main() -> i32
    g()
""",
    # An if whose arms leave the loop is itself a diverging statement.
    "after_if_break_else_continue": """\
fn main() -> i32
    var i = 0
    while i < 5
        i = i + 1
        if i > 2
            break
        else
            continue
        ^i = 9
    i
""",
    # A block arm's trailing value after its `return` (ritz1 keeps it apart,
    # as the arm's `body`). Was a test_ritz1_fn_tail_requires_value row.
    "arm_tail_after_return": """\
fn g(n: i64) -> i64
    match n
        0 =>
            return 1
            ^n + 1
        _ => 2
fn main() -> i32
    g(0) as i32
""",
    # An arm that is itself a match whose arms all return.
    "after_match_with_a_match_arm": """\
fn f(n: i64) -> i64
    match n
        0 => match n
            1 => return 1
            _ => return 2
        _ => return 3
    ^var z: i64 = n
fn main() -> i32
    f(0) as i32
""",
    # Nested: the dead statement is the first one of an inner block.
    "in_if_arm": """\
fn main() -> i32
    var i = 0
    if i == 0
        return 3
        ^i = 4
    i
""",
    # An `unsafe` block diverges when its body does (AGAST #2248).
    "after_unsafe_block_that_returns": """\
fn g(b: i32) -> i32
    unsafe
        return b
    ^b + 1
fn main() -> i32
    g(2)
""",
    "in_unsafe_block": """\
fn main() -> i32
    var i = 0
    unsafe
        return 3
        ^i = 4
    i
""",
}

# name: (source, exit code). Each must still compile and run.
ACCEPTED = {
    # §6.1: a diverging if/else needs nothing after it, and may have nothing.
    "diverging_if_else_ends_fn": ("""\
fn g(b: i32) -> i32
    if b > 0
        return 1
    else
        return 2
fn main() -> i32
    g(1) * 10 + g(0)
""", 12),
    # An if with no else can be skipped, so what follows it runs.
    "if_without_else_then_code": ("""\
fn g(b: i32) -> i32
    if b > 0
        return 1
    5
fn main() -> i32
    g(1) * 10 + g(0)
""", 15),
    # A loop that ends in nothing: the #2520 migration's shape.
    "loop_ends_fn": ("""\
fn g() -> i32
    var i = 0
    loop
        i = i + 1
        if i == 3
            return i
fn main() -> i32
    g()
""", 3),
    # A loop whose `break` (nested in an if) leaves it: code after it runs.
    "loop_with_break_then_code": ("""\
fn main() -> i32
    var i = 0
    loop
        i = i + 1
        if i == 4
            break
    i + 1
""", 5),
    # A `break` in an `unsafe` block leaves the loop around it.
    "loop_left_from_an_unsafe_block_then_code": ("""\
fn main() -> i32
    var i = 0
    loop
        i = i + 1
        unsafe
            if i == 4
                break
    i + 2
""", 6),
    # Only the literal `true` makes a `while` infinite.
    "while_cond_then_code": ("""\
fn main() -> i32
    var i = 0
    while i < 3
        i = i + 1
    i + 4
""", 7),
    # A match with one arm that falls through is not diverging.
    "match_one_arm_falls_through": ("""\
enum E
    A
    B
fn f(e: E) -> i32
    var r = 0
    match e
        A => return 1
        B => r = 2
    r + 1
fn main() -> i32
    f(A) * 10 + f(B)
""", 13),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_unreachable_code_refused(compiler, name, tmp_path):
    _assert_refused(compiler, tmp_path, name, REFUSED[name], MESSAGE)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_reachable_code_accepted(compiler, name, tmp_path):
    src, want = ACCEPTED[name]
    assert _run(compiler, tmp_path, name, src) == want
