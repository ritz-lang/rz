#!/usr/bin/env python3
"""Code after an `if`/`else` (or `match`) whose every arm returns (AGAST #2485).

LANGUAGE_SPEC §6.1: such an `if` "never reaches the end and needs nothing after
it". The spec does not say what code *after* it means. Until a LARB ruling does
(filed with this ticket), the dead code is accepted and never runs: the program
gives the answer of its returns.

ritz0 used to leave the dead `if.end` / `match.merge` block with no
terminator, and clang refused the IR ("expected instruction opcode"). ritz1 and
ritz1_selfhosted already agreed on every row; they are pinned here so the three
can't drift apart.
"""

import pytest

from test_ref_into_value import COMPILERS, _run

pytestmark = pytest.mark.integration

# name: (source, exit code)
ROWS = {
    # The ticket's repro: a value tail after the if.
    "value_tail": ("""\
fn g(b: i32) -> i32
    if b > 0
        return 1
    else
        return 2
    0
fn main() -> i32
    g(1) * 10 + g(0)
""", 12),
    "else_if_chain": ("""\
fn g(b: i32) -> i32
    if b > 0
        return 1
    else if b == 0
        return 2
    else
        return 3
    0
fn main() -> i32
    g(1) * 100 + g(0) * 10 + g(-1)
""", 123),
    "nested_if": ("""\
fn g(b: i32) -> i32
    if b > 0
        if b > 5
            return 3
        else
            return 1
    else
        return 2
    0
fn main() -> i32
    g(9) * 10 + g(1) * 3 + g(0)
""", 35),
    # The tail is a statement, not a value: the fn's end is still unreachable.
    "statement_tail": ("""\
var G: i32
fn g(b: i32) -> i32
    if b > 0
        return 1
    else
        return 2
    G = 7
fn main() -> i32
    g(1) * 10 + g(0) + G
""", 12),
    "statements_then_value": ("""\
fn g(b: i32) -> i32
    var x = 0
    if b > 0
        return 1
    else
        return 2
    x = 5
    x
fn main() -> i32
    g(1) * 10 + g(0)
""", 12),
    "procedure": ("""\
var G: i32
fn p(b: i32)
    if b > 0
        G = G + 1
        return
    else
        G = G + 10
        return
    G = 100
fn main() -> i32
    p(1)
    p(0)
    G
""", 11),
    # AGAST #2271: the same hole, reached through a match.
    "match_every_arm_returns": ("""\
enum E
    A
    B
fn f(e: E) -> i32
    match e
        A => return 1
        B => return 2
    3
fn main() -> i32
    f(A) * 10 + f(B)
""", 12),
    "inside_loop": ("""\
fn g(b: i32) -> i32
    var i = 0
    while i < 3
        if b > 0
            return 1
        else
            return 2
        i = i + 1
    0
fn main() -> i32
    g(1) * 10 + g(0)
""", 12),
    # AGAST #2823: dead code after a plain `return` in a void fn, holding an
    # `if` whose body returns. ritz1 emitted `ret void` then `br` in one block
    # and left the `if.end` block with no terminator; clang refused the IR.
    "return_then_returning_if": ("""\
fn g(p: *u8, out_name: **u8, out_len: *i32)
    *out_name = p
    *out_len = 1
    return
    let q: *u8 = null
    if q == null
        return
    *out_name = q

pub fn main() -> i32
    var n: *u8 = null
    var l: i32 = 0
    g(c"x", @n, @l)
    return l - 1
""", 0),
    # The same shape in a method: emit_impl_method has its own body loop.
    "method_return_then_returning_if": ("""\
struct S
    n: i32
impl S
    fn set(self: *S, b: i32)
        self.n = b
        return
        if b > 0
            return
        self.n = 99
fn main() -> i32
    var s = S { n: 0 }
    s.set(4)
    s.n
""", 4),
    # A value fn: the dead block after the `if` ends `unreachable`.
    "value_fn_return_then_returning_if": ("""\
var G: i32
fn g(b: i32) -> i32
    return b + 1
    if b > 0
        return 7
    G = 9
fn main() -> i32
    g(2) + G
""", 3),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ROWS))
def test_dead_code_after_diverging_if(compiler, name, tmp_path):
    src, want = ROWS[name]
    assert _run(compiler, tmp_path, name, src) == want
