"""A statement-position `match`/`if` is not a value: its arms needn't agree
(AGAST #3593).

`--check-names --check-types` refused 31 sites in angelo, prism and mausoleum
the emitter accepts: a `match`/`if` whose value is dropped (an expression
statement, the tail of a unit fn or of a loop body, an arm of one that is
itself dropped) was held to "arms have different types".  Only a match/if in
a value slot compares its arms.

Two more parts of the same ticket:
- an assignment is `()`, not the value it assigns, so `1 => m.n = 5` beside
  `_ => 7` in a value slot is refused;
- a real mismatch is reported at the arm (its pattern), not at column 1 of a
  block arm's indented body.
"""

import re

import pytest

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

PRELUDE = """\
struct M
    n: i32
    alt: bool

fn get() -> i32
    1

fn pop() -> Result<i32, i32>
    Ok(1)

fn push(v: i32) -> Result<(), i32>
    Ok(())

fn find(m: *M) -> *M
    m

fn note()
    pass

"""

MAIN = """
fn main() -> i32
    0
"""


def _check(tmp_path, body):
    src = tmp_path / "unit.ritz"
    src.write_text(PRELUDE + body + MAIN)
    return run_ritz0([str(src), "-o", str(tmp_path / "unit.ll"), "--no-runtime",
                      "--check-names", "--check-types"])


# Each row drops the match/if's value a different way; each fails on its own
# if that way is still taken for a value slot.
DISCARDED = {
    # angelo hinting/interpreter.ritz: an expression statement, block arm.
    "expr_stmt": """\
fn step(op: u8) -> Result<(), i32>
    match op
        0 => pop()?
        _ =>
            push(2)?
    Ok(())
""",
    # prism input/keyboard.ritz: the tail of a unit fn.
    "unit_fn_tail": """\
fn upd(k: i32)
    match k
        1 => get()
        _ => pass
""",
    # mausoleum lib/recovery.ritz: an if/else-if chain ending a while body.
    "loop_body_tail": """\
fn scan(m: *M, k: i32)
    var i = 0
    while i < k
        i = i + 1
        if i == 1
            find(m)
        else if i == 2
            note()
""",
    # An arm of a dropped match is dropped too.
    "nested_arm": """\
fn step2(op: u8, c: bool) -> Result<(), i32>
    match op
        0 => pass
        _ =>
            if c
                pop()?
            else
                push(1)?
    Ok(())
""",
}


@pytest.mark.parametrize("name", sorted(DISCARDED))
def test_discarded_match_or_if_arms_needn_t_agree(tmp_path, name):
    result = _check(tmp_path, DISCARDED[name])
    assert result.returncode == 0, result.stderr


def _error_at(result):
    """(line, col, message) of the one type error ritz0 reported."""
    found = re.findall(r"unit\.ritz:(\d+):(\d+): (.*)", result.stderr)
    assert result.returncode != 0 and found, result.stderr
    line, col, message = found[0]
    return int(line) - PRELUDE.count("\n"), int(col), message


def test_assignment_is_unit(tmp_path):
    """prism's `KeyCode.AltLeft => self.modifiers.alt = true` was typed bool:
    an assignment yields (), so it can't stand beside 7 in a value slot."""
    result = _check(tmp_path, """\
fn val(m: @&M, k: i32) -> i32
    let x: i32 = match k
        1 => m.n = 5
        _ => 7
    x
""")
    line, col, message = _error_at(result)
    assert "match arms have different types: () and" in message, message
    assert (line, col) == (4, 9), result.stderr


def test_value_slot_mismatch_reported_at_arm(tmp_path):
    """A value slot still compares arms, and points at the arm, not column 1
    of a block arm's body."""
    result = _check(tmp_path, """\
fn val(k: i32) -> Result<i32, i32>
    let x: i32 = match k
        1 => pop()?
        _ =>
            push(2)?
    Ok(x)
""")
    line, col, message = _error_at(result)
    assert message.startswith("match arms have different types: i32 and ()"), message
    assert (line, col) == (4, 9), result.stderr


def test_value_slot_if_mismatch_reported_at_else(tmp_path):
    result = _check(tmp_path, """\
fn val(m: *M, c: bool) -> *M
    if c
        find(m)
    else
        note()
""")
    line, col, message = _error_at(result)
    assert message.startswith("if branches have different types"), message
    assert (line, col) == (5, 9), result.stderr
