#!/usr/bin/env python3
"""AGAST #4070: a statement if/else's arms are not merged into a phi.

ritz0 lowered an if/else whose value is discarded (an expression
statement, the tail of a procedure, a loop body or an `unsafe` block) as
a value: `_emit_if` merged the
arms' last expressions in a phi.  With one arm ending in a unit call (whose
dummy value is an i32) and the other in a struct-returning call, the phi
was typed i32 but fed the struct, and clang refused the IR:

    fn run(flag: i32, out: @&i32)
        if flag == 1
            side(out)
        else
            mk(out)

Neither arm's value is wanted, so neither reaches a phi.  Each program
exits 0 only if every arm ran its side effect the right number of times.

The rows are a table, one test per compiler (test_table_rows.py; AGAST
#4999 folded the 21-case matrix to keep the suite under its cap).
"""

import pytest
from test_ref_into_value import COMPILERS
from test_table_rows import assert_runs

pytestmark = pytest.mark.integration

PRELUDE = """\
struct V
    tag: i32
    num: f64

fn mk(out: @&i32) -> V
    *out = *out + 10
    V { tag: 1, num: 2.0 }

fn side(out: @&i32)
    *out = *out + 1

fn flip(out: @&i32) -> bool
    *out = *out + 10
    true

"""

# The if/else is a procedure's tail.
TAIL = """\
fn run(flag: i32, out: @&i32)
    if flag == 1
        side(out)
    else
        mk(out)
"""

# The if/else is a statement with more after it.
MID = """\
fn run(flag: i32, out: @&i32)
    if flag == 1
        side(out)
    else
        mk(out)
    *out = *out + 100
"""

# A nested else-if chain, struct arm first, as the tail.  AGAST #4924: its
# inner if/else ends in a bool-valued call (`s.push(c)` on a String) beside a
# unit call's dummy i32, which ritz0 refused as "bool as an integer".
NESTED = """\
fn run(flag: i32, out: @&i32)
    if flag == 0
        mk(out)
    else if flag == 1
        side(out)
    else
        flip(out)
"""

# AGAST #4450: the tail else ends in a statement match, which has no value.
MATCH = """\
fn run(flag: i32, out: @&i32)
    if flag == 1
        side(out)
    else
        match flag
            0 =>
                var k: i32 = 10
                *out = *out + k
            _ => pass
"""

# The if/else is a statement in a fn that returns a value.
VALUED = """\
fn run(flag: i32, out: @&i32) -> i32
    if flag == 1
        side(out)
    else
        mk(out)
    7
"""

# The if/else is the tail of a loop body, whose value is discarded too.
LOOP = """\
fn run(flag: i32, out: @&i32)
    var k: i32 = 0
    while k < 1
        k = k + 1
        if flag == 1
            side(out)
        else
            mk(out)
"""

# The same, in a `for` body.
FOR = """\
fn run(flag: i32, out: @&i32)
    for k in 0..1
        if flag == 1
            side(out)
        else
            mk(out)
"""

# The if/else is an `unsafe` block's tail (AGAST #2248 runs it).
UNSAFE = """\
fn run(flag: i32, out: @&i32)
    unsafe
        if flag == 1
            side(out)
        else
            mk(out)
"""

MAIN = """
pub fn main() -> i32
    var n: i32 = 0
    run(0, @&n)
    run(1, @&n)
    n - {want}
"""

BODIES = {
    "tail": (TAIL, 11),
    "mid": (MID, 211),
    "nested": (NESTED, 11),
    "match": (MATCH, 11),
    "valued": (VALUED, 11),
    "loop": (LOOP, 11),
    "for": (FOR, 11),
    "unsafe": (UNSAFE, 11),
}

# Each row exits 0: `main` subtracts what its arms should have added.
ROWS = {
    row: (PRELUDE + body + MAIN.format(want=want), 0)
    for row, (body, want) in BODIES.items()
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_discarded_if_arms_of_differing_types(compiler, tmp_path):
    assert_runs(compiler, tmp_path, ROWS)
