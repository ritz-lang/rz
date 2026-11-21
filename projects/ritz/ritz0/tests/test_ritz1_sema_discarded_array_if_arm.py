"""AGAST #3512 (#1816): two small checks move off ritz1's emitter onto Sema.

THE CHANGE (the #3462 pattern: must_use.ritz + sema_walk.ritz)

- discarded_array (AGAST #3189): an array field alone as a statement (`w.a`
  mid-block, or the tail of a fn or method that returns nothing) does
  nothing.  Its rule's own tests, all three compilers, are
  test_array_statement.py.
- if_arm (AGAST #1613 / #1406): an if-expression arm that ends in no value
  (an else-less `if`, an assignment) is refused unless it leaves the block
  (`return` / `break` / `continue`).  Its rule's own tests are
  test_ritz1_if_expr.py's MALFORMED and test_if_expression_requires_else.py.

Both now report through diag (`<file>:<line>:<col>: error: `) in the
emitter's words.  The emitter printed discarded_array as
`error: <file>:<line>:<col>: ` and if_arm with no location at all; Sema
locates if_arm where ritz0 does (the inner `if` that lacks the `else`) and
the generic wording at the if expression.

THE TESTS

- An error on Sema stops the compile before emission: an emitter-side error
  later in the same file (a fn whose frame is over the stack, frame_limit)
  is no longer printed.  Before the move all three were.  (It was a literal
  that doesn't fit its slot until literal_slot moved onto Sema, AGAST #3510.)
- One program per check pins its reach to the emitter's, location by
  location.  discarded_array: every receiver shape the emitter typed (a
  param, a member chain, `*p`, `p.f` through a pointer field, an element, a
  call, a call returning a pointer, a method call), a loop body, a void fn's
  tail and a method's, and an arm's last statement before its value (AGAST
  #3920: the emitter only ever judged a statement with a next one).
  LARB R69 (AGAST #3968): the trailing value of an else-less `if` body, a
  statement `if` / `match` arm's and a loop body's, which are discarded.
  if_arm: a nested else-less `if`, an array-valued if (emit_array_if_into),
  a `return if`, the generic wording; an arm that returns is not refused.
"""

import re

import pytest

from array_rules import WHOLE_ARRAY_NOT_A_VALUE
from test_ref_into_value import _compile

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

NO_ELSE = ("an `if` with no `else` has no value when its condition is false, so it "
           "cannot be used as a value here; add an `else` arm")
NO_VALUE = "an `if` expression arm does not end in a value"

STOPS_BEFORE_EMIT = """\
struct W
    a: [2]i32

fn f(w: W, c: i32) -> i32
    w.a
    let n: i32 = if c == 1
        if c == 2
            1
    else
        2
    var m: i32 = huge()
    n

pub fn main() -> i32
    0

fn huge() -> i32
    var big: [16777216]u8
    big[0] = 1
    big[0] as i32
"""

ARRAY_REACH = """\
struct W
    a: [2]i32
    n: i32

struct H
    w: W
    p: *W

impl W
    fn get(self: @W) -> W
        W { a: [1, 2], n: 0 }
    fn g(self: *W)
        self.a

fn mk() -> W
    W { a: [1, 2], n: 0 }

fn mkp(w: *W) -> *W
    w

fn f(w: W, h: H, p: *W, ws: [2]W, c: i32) -> i32
    w.a
    h.w.a
    h.p.a
    (*p).a
    ws[0].a
    mk().a
    mkp(p).a
    w.get().a
    w.n
    if c == 1
        w.a
    while c == 2
        h.w.a
        break
    match c
        3 =>
            w.a
            1
        _ => 0
    3

fn v(w: W)
    w.a

pub fn main() -> i32
    0

fn s(w: W, c: i32) -> [2]i32
    if c == 1
        w.a
    else
        w.a
    while c == 2
        w.a
    for i in 0..2
        w.a
    loop
        if c == 7
            break
        w.a
    match c
        4 => w.a
        _ => pass
    let b: [2]i32 = if c == 5
        w.a
    else
        w.a
    if c == 6
        w.a
    else
        b
"""

# line:col of each report, as ritz0 makes them.  38:13, an arm's statement
# before its value, joined in AGAST #3920.  LARB R69 (AGAST #3968): 32:9, the
# trailing value of an else-less `if` body, and fn s's statement `if` / loop
# bodies' tails and statement `match` arm; its `let` and tail `if` are values.
ARRAY_WANTED = sorted(["22:5", "23:5", "24:5", "25:6", "26:5", "27:5", "28:5",
                       "29:5", "32:9", "34:9", "38:13", "44:5", "13:9",
                       "51:9", "53:9", "55:9", "57:9", "61:9", "63:14"])

IF_REACH = """\
fn f(c: i32, d: i32) -> i32
    let n: i32 = if c == 1
        if d == 1
            1
    else
        2
    let k: i32 = if c == 2 then 1 else 3
    n + k

fn g(c: i32) -> i32
    let a: [2]i32 = if c == 1
        [1, 2]
    else
        if c == 3
            [3, 4]
    a[0]

fn h(c: i32) -> i32
    let n: i32 = if c == 1
        return 4
    else
        2
    n

fn k(c: i32) -> i32
    return if c == 1
        if c == 2
            5
    else
        if c == 5
            return 6
        else
            3

fn q(c: i32) -> i32
    var x: i32 = 0
    let n: i32 = if c == 1
        x = 2
    else
        3
    n + x

pub fn main() -> i32
    0
"""

IF_WANTED = sorted([("3:9", NO_ELSE), ("14:9", NO_ELSE), ("27:9", NO_ELSE),
                    ("37:18", NO_VALUE)])


def _reports(comp):
    out = comp.stdout + comp.stderr
    return out, re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)


def _refused(request, tmp_path, compiler, name, src):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, name, src)
    out, found = _reports(comp)
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted {name}:\n{out}"
    return out, found


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_sema_error_stops_before_emission(request, tmp_path, compiler):
    out, found = _refused(request, tmp_path, compiler, "stop", STOPS_BEFORE_EMIT)
    assert found == [("5:5", WHOLE_ARRAY_NOT_A_VALUE), ("7:9", NO_ELSE)], (
        f"{compiler}: wanted only the two Sema errors:\n{out}")


@pytest.mark.parametrize("compiler", COMPILERS)
def test_discarded_array_reaches_what_the_emitter_reached(request, tmp_path, compiler):
    out, found = _refused(request, tmp_path, compiler, "array", ARRAY_REACH)
    assert {m for _, m in found} == {WHOLE_ARRAY_NOT_A_VALUE}, out
    assert sorted(w for w, _ in found) == ARRAY_WANTED, f"{compiler}:\n{out}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_if_arm_reaches_what_the_emitter_reached(request, tmp_path, compiler):
    out, found = _refused(request, tmp_path, compiler, "if_arm", IF_REACH)
    assert sorted(found) == IF_WANTED, f"{compiler}:\n{out}"
