#!/usr/bin/env python3
"""AGAST #3980: a match STATEMENT's if/else arm is a statement, not a value.

ritz1 refused

    match get(n)
        Ok(v) =>
            if v != 2
                rc = 4
            else
                rc = 1
        Err(_) => rc = 6
    rc

with "an `if` expression arm does not end in a value" (nexus
test/test_repos.ritz).  The parser makes an arm block's trailing if/else
the arm's value (an EXPR_IF, block_tail_as_value), and Sema's if_arm check
(if_arm_value.ritz) judged every EXPR_IF as a value, without asking whether
the match around it was one.  The check predates its move onto Sema
(#3512): emit_if_expr ran it unconditionally since #1613.

Now "value wanted" is carried from the match to its arms, as ritz0's
_find_valueless_if carries `consumed`: a match statement whose value is
discarded (not the tail of a fn that returns one) walks its arms as
statements, and a nested match / if-else arm inherits that.  A match in value
position is still checked (VALUE_ROWS).

Each RUN_ROWS program exits 21 only if every arm assigned what it should.
"""

import pytest
from test_ref_into_value import _assert_refused, _run

pytestmark = pytest.mark.integration

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

NO_ELSE = ("an `if` with no `else` has no value when its condition is false, so it "
           "cannot be used as a value here; add an `else` arm")
NO_VALUE = "an `if` expression arm does not end in a value"

GET = """\
fn get(n: i32) -> Result<i32, i32>
    if n > 0
        return Ok(n)
    Err(n)

"""

# A match statement with an if/else arm; `{body}` is indented by `{ind}`.
IF_ELSE = """\
{ind}match get(n)
{ind}    Ok(v) =>
{ind}        if v != 2
{ind}            rc = rc + 4
{ind}        else
{ind}            rc = rc + 1
{ind}    Err(_) => rc = rc + 6
"""

# The else arm ends in an else-less `if`, the other arm in a block.
NESTED_NO_ELSE = """\
{ind}match get(n)
{ind}    Ok(v) =>
{ind}        if v != 2
{ind}            rc = rc + 4
{ind}        else
{ind}            if v == 2
{ind}                rc = rc + 1
{ind}    Err(_) =>
{ind}        rc = rc + 6
{ind}        rc = rc + 0
"""

# The arm's value is a nested match whose arm is an if/else; a `pass` arm.
NESTED_MATCH = """\
{ind}match get(n)
{ind}    Ok(v) =>
{ind}        match get(v)
{ind}            Ok(w) =>
{ind}                if w != 2
{ind}                    rc = rc + 4
{ind}                else
{ind}                    rc = rc + 1
{ind}            Err(_) => pass
{ind}    Err(_) => pass
"""

SHAPES = {"if_else": IF_ELSE, "nested_no_else": NESTED_NO_ELSE, "nested_match": NESTED_MATCH}


def _fn_body(shape):
    """`t(n)` with the match mid-body; 1 for n == 2, 4 for 3, 6 for -1."""
    return ("fn t(n: i32) -> i32\n    var rc: i32 = 0\n"
            + SHAPES[shape].format(ind="    ") + "    rc\n\n")


def _void_tail(shape):
    """The match as a void fn's last statement, writing through `rc`."""
    body = SHAPES[shape].format(ind="    ").replace("rc = rc +", "*rc = *rc +")
    return ("fn u(n: i32, rc: *i32)\n" + body + "\n"
            "fn t(n: i32) -> i32\n    var rc: i32 = 0\n    u(n, @rc)\n    rc\n\n")


def _loop(shape):
    """The match as a loop body's last statement, run once."""
    return ("fn t(n: i32) -> i32\n    var rc: i32 = 0\n    var i: i32 = 0\n"
            "    while i < 1\n        i = i + 1\n"
            + SHAPES[shape].format(ind="        ") + "    rc\n\n")


def _if_body(shape):
    """The match as an if statement's last statement, mid-fn."""
    return ("fn t(n: i32) -> i32\n    var rc: i32 = 0\n    if n != 0\n"
            + SHAPES[shape].format(ind="        ") + "    rc\n\n")


POSITIONS = {"fn_body": _fn_body, "void_tail": _void_tail, "loop": _loop, "if_body": _if_body}

# 1 + 4 + 16: n == 2 takes the else arm, 3 the then arm, -1 the Err arm.
MAIN = """\
fn main() -> i32
    var r: i32 = 0
    if t(2) == 1
        r = r + 1
    if t(3) == 4
        r = r + 4
    if t(-1) == {err}
        r = r + 16
    r
"""


def _rows():
    for pos in POSITIONS:
        for shape in SHAPES:
            for compiler in COMPILERS:
                yield pytest.param(compiler, pos, shape, id=f"{pos}-{shape}-{compiler}")


@pytest.mark.parametrize("compiler,pos,shape", list(_rows()))
def test_a_match_statements_if_else_arm_is_a_statement(compiler, tmp_path, pos, shape):
    # The nested match's Err(-1) arm is `pass` (rc stays 0); the others add 6.
    # nested_match's t(3): get(3) then get(3) is Ok(3), so 4 as well.
    err = 0 if shape == "nested_match" else 6
    src = GET + POSITIONS[pos](shape) + MAIN.format(err=err)
    assert _run(compiler, tmp_path, f"{pos}_{shape}", src) == 21


# A match that IS the value (a fn's tail) is still checked, as before.
VALUE_ROWS = {
    "assign_arm": ("""\
fn t(n: i32) -> i32
    var rc: i32 = 0
    match get(n)
        Ok(v) =>
            ^if v != 2
                rc = 4
            else
                rc = 1
        Err(_) => 6

fn main() -> i32
    t(2)
""", NO_VALUE),
    "no_else_arm": ("""\
fn t(n: i32) -> i32
    match get(n)
        Ok(v) =>
            if v != 2
                4
            else
                ^if v == 2
                    1
        Err(_) => 6

fn main() -> i32
    t(2)
""", NO_ELSE),
    # The tail of a fn's tail `if` is the fn's value too (ritz0 refuses it,
    # as reaching the end without one).
    "if_tail": ("""\
fn t(n: i32) -> i32
    var rc: i32 = 0
    if n > -5
        match get(n)
            Ok(v) =>
                ^if v != 2
                    rc = 4
                else
                    rc = 1
            Err(_) => 6
    else
        7

fn main() -> i32
    t(2)
""", NO_VALUE),
}


def _value_rows():
    for row in VALUE_ROWS:
        for compiler in ["ritz1", "ritz1_selfhosted"]:
            yield pytest.param(compiler, row, id=f"{row}-{compiler}")


@pytest.mark.parametrize("compiler,row", list(_value_rows()))
def test_a_match_in_value_position_still_wants_its_arms_values(compiler, tmp_path, row):
    marked, message = VALUE_ROWS[row]
    _assert_refused(compiler, tmp_path, row, GET + marked, message)
