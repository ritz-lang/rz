"""AGAST #3749: a statement `if`/`else` whose value is discarded gets no phi.

In `fn pick(c) -> Option<i64>`, an `if c == 0 / one() / else / one()`
followed by `None` is a statement, not the fn's value.  ritz1 joined its
arms' (discarded, i64) call results with a phi typed from the fn's return
type, `phi %Option$i64 [ %i64reg, ... ]`, which clang rejects.  A scalar
return type hid it: the phi was i64 either way.

Rows: the ticket's program (an `if` with a following statement), an `if`
ending an arm of it, and the `loop` / `while` body forms, where the `if` is
the body's last statement (a loop body has no value) or is followed by
`break`.  ritz0 always ran these, so only the two ritz1 compilers are rows.
"""

import pytest

from test_match_endless_loop_arm import _run

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

_HEAD = (
    "import ritzlib.option\n"
    "fn one() -> i32\n"
    "    1\n"
    "fn pick(c: i64) -> Option<i64>\n"
)
_MAIN = (
    "fn main() -> i32\n"
    "    match pick(0)\n"
    "        Some(_) => 1\n"
    "        None => 0\n"
)

# name -> body of `pick`.  Each `main` exits 0 only if `pick` returns None.
PROGRAMS = {
    # The ticket's program: the `if` has a following statement.
    "followed_by_tail": (
        "    if c == 0\n"
        "        one()\n"
        "    else\n"
        "        one()\n"
        "    None\n"
    ),
    # An `if` ending an arm of a discarded `if` is discarded too.
    "nested_in_arm": (
        "    if c == 0\n"
        "        if c == 1\n"
        "            one()\n"
        "        else\n"
        "            one()\n"
        "    else\n"
        "        one()\n"
        "    None\n"
    ),
    # A `loop` body: the `if` is followed by `break`.
    "loop_body_then_break": (
        "    loop\n"
        "        if c == 0\n"
        "            one()\n"
        "        else\n"
        "            one()\n"
        "        break\n"
        "    None\n"
    ),
    # A `loop` body ending in the `if`: a loop body has no value.
    "loop_body_last": (
        "    var i: i64 = 0\n"
        "    loop\n"
        "        i = i + 1\n"
        "        if i > 3\n"
        "            break\n"
        "        if c == 0\n"
        "            one()\n"
        "        else\n"
        "            one()\n"
        "    None\n"
    ),
    # A `while` body ending in the `if`.
    "while_body_last": (
        "    var i: i64 = 0\n"
        "    while i < 3\n"
        "        i = i + 1\n"
        "        if c == 0\n"
        "            one()\n"
        "        else\n"
        "            one()\n"
        "    None\n"
    ),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_a_discarded_statement_if_gets_no_return_typed_phi(tmp_path, name, compiler):
    assert _run(compiler, tmp_path, _HEAD + PROGRAMS[name] + _MAIN) == 0
