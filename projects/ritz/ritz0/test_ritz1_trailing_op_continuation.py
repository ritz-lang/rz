"""AGAST #2954: a line ending in a binary operator continues onto the next
line at the SAME indent, under ritz1 as under ritz0.

THE DEFECT

    fn f(a: i32, b: i32) -> bool
        a == 0 and          # ritz1: c1.ritz:2:15: unexpected end of line
        b == 0

ritz0's Pratt loop skips the NEWLINE tokens after it consumes an infix
operator (parser.py `parse_expr`), so the expression carries on.  ritz1's
grammar had each operator followed directly by its right operand, and the
NEWLINE ended the statement there.  prism hit it at rect.ritz:88 (`and`),
color.ritz:43 (`|`) and damage.ritz:104 (`and`).

THE FIX

Each binary operator in ritz1's grammar may be followed by one NEWLINE
(`op_nl`) before its right operand; its lexer already folds blank and
comment-only lines, so one is all there can be.  INDENT / DEDENT are left
alone: a DEEPER-indented continuation is #2193, undecided, and refused by
both compilers alike.

THE TESTS

One row per operator the ticket names, each continued at the same indent in
a `let`, a `return` and a fn's tail, plus a row where the line does NOT end
in an operator and so still ends the statement.  ritz0 is the oracle.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = pytest.mark.batched

# `and`: prism rect.ritz:88 / damage.ritz:104.  f(0, 0) true, f(0, 1) false.
AND = """\
fn f(a: i32, b: i32) -> bool
    a == 0 and
    b == 0

fn g(a: i32, b: i32) -> bool
    let t = a == 0 and
    b == 0
    t

pub fn main() -> i32
    if not f(0, 0) or f(0, 1)
        return 1
    if not g(0, 0) or g(0, 1)
        return 2
    42
"""

# `or`: f(1, 0) and f(0, 1) true, f(0, 0) false.
OR = """\
fn f(a: i32, b: i32) -> bool
    return a == 1 or
    b == 1

fn g(a: i32, b: i32) -> bool
    a == 1 or
    b == 1

pub fn main() -> i32
    if not f(1, 0) or not f(0, 1) or f(0, 0)
        return 1
    if not g(1, 0) or not g(0, 1) or g(0, 0)
        return 2
    42
"""

# `|`: prism color.ritz:43, packing bytes into a u32.  0x01020304.
PIPE = """\
fn pack(r: u8, g: u8, b: u8, a: u8) -> u32
    ((r as u32) << 24) | ((g as u32) << 16) |
    ((b as u32) << 8) |
    (a as u32)

pub fn main() -> i32
    let x: u32 = (1 as u32) |
    (2 as u32)
    if x != 3
        return 1
    if pack(1, 2, 3, 4) != 0x01020304
        return 2
    42
"""

# `+`, chained across three lines: 10 + 20 + 12.
PLUS = """\
fn sum(a: i32, b: i32, c: i32) -> i32
    a +
    b +
    c

pub fn main() -> i32
    let x = 10 +
    20
    sum(x, 0, 12)
"""

# A line NOT ending in an operator still ends its statement: `x = x + 1`
# then a separate tail `-x`.  Were that NEWLINE dropped too, the body
# would be `x = x + 1 - x` with no tail, and not compile.
NOT_CONTINUED = """\
fn f(a: i32) -> i32
    var x = a
    x = x + 1
    -x

pub fn main() -> i32
    f(-43)
"""

CASES = {
    "and": (AND, 42),
    "or": (OR, 42),
    "pipe": (PIPE, 42),
    "plus": (PLUS, 42),
    "not_continued": (NOT_CONTINUED, 42),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_oracle(tmp_path, name):
    program, want = CASES[name]
    assert _run("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_trailing_op_continuation(ritz1_bin, tmp_path, name):
    program, want = CASES[name]
    assert _run("ritz1", tmp_path, name, program) == want
