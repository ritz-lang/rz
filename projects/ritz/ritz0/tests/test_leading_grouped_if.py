"""AGAST #4163: an expression that starts with a parenthesised `if` goes on
past its `)`.

    let m: i64 = (if c then a else a) * 2      # was: `*x` needs a pointer
    let n: i64 = (if c then 200 else 100) + 2  # was: Expected expression, got PLUS

ritz0's `parse_expr` returned at once when its left operand was an `If` or
`Match`: a block `if` ends in a DEDENT, and an operator after it belongs to
the next line.  The grouped primary `( expr )` hands back the inner node
itself, so a parenthesised `if` looked like a bare one, the expression ended
at its `)`, and the operator after it opened a new (unary) statement.  Only the
leading position was hit: `2 * (if ...)` parses the `if` as a right operand.

ritz1's grammar already reads `( if ... )` as a grouped primary; the rows run
on all three compilers so neither can drift.  Each row puts the grouped `if`
first in a different statement that takes a value (`let`, `return`, a fn's
tail), and every program returns 42 only if both arms were taken correctly.
"""

import pytest
from test_borrow_param_ref_field import _run
from test_ritz1_for_iterable import SELFHOSTED_BIN

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration

# Each `pick(c, a)` is called with both truth values, so no arm is folded away.
MAIN = """
pub fn main() -> i32
    if pick(true, 3) != 6
        return 1
    if pick(false, 3) != 2
        return 2
    42
"""

# name: the `pick` fn, which must return 6 when c is true and 2 when false.
RUNS = {
    # The ticket's first line: `*` was read as a deref of the next statement.
    "let_times": "fn pick(c: bool, a: i64) -> i64\n"
                 "    let m: i64 = (if c then a else 1) * 2\n"
                 "    m\n",
    # The ticket's second: `+` was a parse error.  `- 1 * 3` also checks the
    # loop carries on with its precedences: (8|4) - 3, not ((8|4) - 1) * 3.
    "let_plus_chain": "fn pick(c: bool, a: i64) -> i64\n"
                      "    let n: i64 = (if c then a + 5 else 4) + 1 - 1 * 3\n"
                      "    n\n",
    "return": "fn pick(c: bool, a: i64) -> i64\n"
              "    return (if c then a else 1) * 2\n",
    # A tail expression is parsed as a statement, not after a `=`.
    "tail": "fn pick(c: bool, a: i64) -> i64\n"
            "    (if c then a else 1) * 2\n",
}


@pytest.fixture
def run_with(ritz1_bin, tmp_path):
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _run("ritz0", None, tmp_path, name, program)
        return _run("ritz1", bins[compiler], tmp_path, name, program)
    return go


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_a_leading_grouped_if_takes_the_operator_after_it(run_with, compiler, name):
    assert run_with(compiler, name, RUNS[name] + MAIN) == 42
