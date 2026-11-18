"""AGAST #2137: `[[must_use]]` fns (LANGUAGE_SPEC §17.8).

The result of a call to a `[[must_use]]` fn may not be thrown away. Both
compilers reject a discarded call with the same located diagnostic:

    t.ritz:<line>:<col>: result of [[must_use]] fn '<fn>' is discarded

A call is discarded when it is not its block's value, and a block has a value
only when it is used as one (LARB R69): any statement but the last of a
block, the last statement of a fn that returns nothing, and the last line of
a statement `match` arm, a statement `if` branch or a loop body.

Why: valet's test_tls.ritz (AGAST #1903) had six void [[test]] fns that
called ritzunit's assert_eq_* as bare statements, so they could never fail.
Those helpers have since gone (AGAST #2127): ritzunit's string checks are
void [[test_helper]] fns that `assert`, so a bare call is their normal use
(test_ritzunit_assertions.py).
"""

import pytest

from test_attr_validation import COMPILERS, _assert_located_error, _ir, _need

pytestmark = pytest.mark.integration

RULE = "result of [[must_use]] fn 'check' is discarded"

# The fn every program below calls.
CHECK = """\
[[must_use]]
fn check(x: i32) -> i32
    if x == 0
        return 1
    0

"""

BARE_STMT = CHECK + """\
fn main() -> i32
    check(1)
    0
"""

VOID_TAIL = CHECK + """\
fn run()
    check(1)

fn main() -> i32
    run()
    0
"""

IN_LOOP = CHECK + """\
fn main() -> i32
    var i: i32 = 0
    while i < 3
        check(i)
        i = i + 1
    0
"""

IN_IF_BRANCH = CHECK + """\
fn main() -> i32
    var n: i32 = 0
    if n == 0
        check(n)
        n = 1
    0
"""

# An arm's last statement before its value is not the arm's value
# (AGAST #3515: ritz1 kept the arm's value apart from its statements and
# took the call for the block's tail).
IN_MATCH_ARM = CHECK + """\
fn main() -> i32
    match 3
        3 =>
            check(3)
            0
        _ => 0
"""

IN_IF_EXPR_ARM = CHECK + """\
fn main() -> i32
    var n: i32 = 2
    let v: i32 = if n == 2
        check(8)
        1
    else
        0
    v
"""

# LARB R69 (AGAST #3796): an arm of a statement `match`, a branch of a
# statement `if` and a loop body are never values, so a call as their last
# line is discarded too. name -> (program, line, col).
STMT_TAILS = {
    "statement_match_arm": (CHECK + """\
fn main() -> i32
    var n: i32 = 3
    match n
        3 => check(3)
        _ => n = 0
    0
""", 10, 14),
    # The `else if` branch: a nested if as a statement if's tail.
    "statement_else_if_branch": (CHECK + """\
fn main() -> i32
    var n: i32 = 3
    if n == 0
        n = 1
    else if n == 3
        check(n)
    0
""", 12, 9),
    # The match is a void fn's tail, which is no value either.
    "void_fn_tail_match": (CHECK + """\
fn run(n: i32)
    match n
        3 => check(3)
        _ => n = 0

fn main() -> i32
    run(3)
    0
""", 9, 14),
    "while_body": (CHECK + """\
fn main() -> i32
    var i: i32 = 0
    while i < 3
        i = i + 1
        check(i)
    0
""", 11, 9),
    "for_body": (CHECK + """\
fn main() -> i32
    for i in 0..3
        check(i)
    0
""", 9, 9),
}
# ritz1's half of R69 is AGAST #3997; each row there is a strict xfail.
RITZ1_STMT_TAIL_GAP = "AGAST #3997: ritz1 keeps a statement arm's value"

USED = CHECK + """\
fn first() -> i32
    check(1)

# A match or if that is the fn's value passes its arms' values on (R69).
fn picked(n: i32) -> i32
    match n
        0 => check(0)
        _ =>
            if n > 5
                check(n)
            else
                0

fn second() -> i32
    return check(2)

fn plain(x: i32) -> i32
    x

fn main() -> i32
    let a: i32 = check(0)
    var b: i32 = 0
    b = check(3)
    if check(4) != 0
        return 9
    plain(5)
    let m: i32 = match a
        0 => check(6)
        _ => 1
    a + b + m + first() + second() + picked(7)
"""

ON_STRUCT = """\
[[must_use]]
struct S
    a: i32

fn main() -> i32
    0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_bare_must_use_call_is_a_located_error(request, tmp_path, compiler):
    _need(compiler, request)
    _assert_located_error(compiler, tmp_path, BARE_STMT, 8, 5, RULE)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_tail_of_void_fn_discards(request, tmp_path, compiler):
    # The last line of a fn that returns nothing is not a value.
    _need(compiler, request)
    _assert_located_error(compiler, tmp_path, VOID_TAIL, 8, 5, RULE)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_discard_inside_loop_body(request, tmp_path, compiler):
    _need(compiler, request)
    _assert_located_error(compiler, tmp_path, IN_LOOP, 10, 9, RULE)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_discard_inside_if_branch(request, tmp_path, compiler):
    _need(compiler, request)
    _assert_located_error(compiler, tmp_path, IN_IF_BRANCH, 10, 9, RULE)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_discard_before_match_arm_value(request, tmp_path, compiler):
    _need(compiler, request)
    _assert_located_error(compiler, tmp_path, IN_MATCH_ARM, 10, 13, RULE)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_discard_before_if_expression_arm_value(request, tmp_path, compiler):
    _need(compiler, request)
    _assert_located_error(compiler, tmp_path, IN_IF_EXPR_ARM, 10, 9, RULE)


@pytest.mark.parametrize("compiler", [
    "ritz0",
    pytest.param("ritz1", marks=pytest.mark.xfail(strict=True, reason=RITZ1_STMT_TAIL_GAP)),
])
@pytest.mark.parametrize("name", sorted(STMT_TAILS))
def test_statement_tail_discards(request, tmp_path, compiler, name):
    # A statement match/if or a loop body has no value: its tail call is
    # discarded (LARB R69).
    _need(compiler, request)
    src, line, col = STMT_TAILS[name]
    _assert_located_error(compiler, tmp_path, src, line, col, RULE)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_used_results_compile(request, tmp_path, compiler):
    # let / assignment / return / condition / a non-void fn's tail use the
    # value; a plain fn's result may still be dropped.
    _need(compiler, request)
    _ir(compiler, tmp_path, USED)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_must_use_applies_to_fns_only(request, tmp_path, compiler):
    _need(compiler, request)
    _assert_located_error(compiler, tmp_path, ON_STRUCT, 1, 3, "must_use",
                          "applies to fn items")
