"""AGAST #3924: an `@&` of a `let` is refused at the `@` (LARB R68).

R68: a diagnostic about an expression is located at the first column of the
smallest expression that's wrong.  For "cannot borrow `let` binding `x` as
mutable" that's the borrow `@&x`, not its operand `x`, and not the statement
that holds it (`let q: *Pt = @&p` reports at the `@`, not the `let`).  ritz1
already did; ritz0 reported the operand, two columns on.

One row per syntactic home of an `@&` that the compilers reach by different
paths: a statement's initialiser, an assignment's value, a call argument, a
match arm's expression, and an `@&` of a field (whose smallest wrong
expression is still the whole borrow, not `p` or `p.x`).  An implicit borrow
(a `:&` argument, a `self:&` receiver) has no `@`, so stays at its operand:
test_ritz1_sema_let.py pins those.
"""

import pytest

from test_ref_into_value import _assert_refused

pytestmark = [pytest.mark.integration, pytest.mark.batched]

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

MESSAGE = "cannot borrow `let` binding `p` as mutable; declare it `var`"

HEAD = """\
struct Pt
    x: i64
    y: i64

fn pt_x(p: *Pt) -> i64
    p.x

fn i_x(p: *i64) -> i64
    *p

fn main() -> i32
    let p = Pt { x: 1, y: 2 }
"""

# `^` marks the column every compiler must report.
ROWS = {
    "let_init": "    let q: *Pt = ^@&p\n    0\n",
    "assign": "    var q: *Pt = null\n    q = ^@&p\n    0\n",
    "call_arg": "    pt_x(^@&p) as i32\n",
    "match_arm": ("    let o: Option<i64> = Some(3)\n"
                  "    let n = match o\n"
                  "        Some(v) => pt_x(^@&p)\n"
                  "        None => 0\n"
                  "    0\n"),
    "field": "    i_x(^@&p.x) as i32\n",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(ROWS))
def test_let_mut_borrow_is_located_at_the_at(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    _assert_refused(compiler, tmp_path, f"let_borrow_{row}", HEAD + ROWS[row], MESSAGE)
