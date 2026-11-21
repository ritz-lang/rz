"""AGAST #3462: ritz1's `must_use` check runs on Sema, before emission.

THE CHANGE (step 1 of #1816; LARB review/5 ritz1 N1)

ritz1 ran every semantic check inside code generation.  #3462 adds the
checking phase, a `Sema` pass over the AST that main runs after
monomorphisation and before emit_module and that stops the compile on any
error, and moves the first check onto it: a discarded call to a
`[[must_use]]` fn (AGAST #2137, LANGUAGE_SPEC §17.8; the rule's own tests,
both compilers, are test_must_use.py).

THE TESTS

- An error on Sema stops the compile before emission: an emitter-side error
  later in the same file (a fn whose frame is over the stack, frame_limit)
  is no longer printed.  Before the move both were.  (It was an integer `if`
  condition until bool_check moved onto Sema, AGAST #3502, then a write to a
  `let` until let_check did, AGAST #3504, then a literal that doesn't fit its
  slot until literal_slot did, AGAST #3510.)
- One program pins the move's reach to the emitter's, location by location:
  every block kind that reported before still does, an impl method and each
  generic instance included, and a local fn pointer named like the fn still
  doesn't.  A match / if-expression arm's last statement before its value
  (49:13, 53:9) did not report before the move either; AGAST #3515 closed
  that gap, so it reports now, as ritz0 always has.

  One report is new: `check(6)` in the `defer` block (37:9).  The emitter
  lowered a defer body at the fn's exit, after `let check: fn(..)` was
  declared, so it took that call for the local's and said nothing.  Sema
  judges the call where it is written, where `check` is still the fn.
  Likewise `check(n)` after the `if n == 99` block (68:5): the block's local
  `check` is out of scope there, but the emitter never dropped a block's
  locals.
"""

import re

import pytest

from test_ref_into_value import _compile

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

RULE = "result of [[must_use]] fn 'check' is discarded"

CHECK = """\
[[must_use]]
fn check(x: i32) -> i32
    if x == 0
        return 1
    0

fn other(x: i32) -> i32
    x

"""

STOPS_BEFORE_EMIT = CHECK + """\
fn main() -> i32
    let n: i32 = 1
    check(n)
    var m: i32 = huge()
    0

fn huge() -> i32
    var big: [16777216]u8
    big[0] = 1
    big[0] as i32
"""

REACH = CHECK + """\
struct P
    x: i32

impl P
    fn go(self: @P) -> i32
        check(self.x)
        0

fn twice<T>(x: T) -> i32
    check(1)
    0

fn run()
    check(2)

fn main() -> i32
    var n: i32 = 3
    for i in 0..2
        check(i as i32)
        n = n + 1
    loop
        check(2)
        break
    unsafe
        check(5)
        n = n + 1
    defer
        check(6)
        n = n + 1
    if n == 1
        n = 2
    else
        check(7)
        n = 3
    while n > 100
        check(9)
        n = n - 1
    match n
        3 =>
            check(3)
            pass
        _ => pass
    let v: i32 = if n == 2
        check(8)
        1
    else
        0
    let w: i32 = match n
        3 =>
            if n == 3
                check(1)
                n = 4
            1
        _ => 0
    if n == 99
        let check: fn(i32) -> i32 = other
        check(1)
        n = 1
    check(n)
    n = n + 1
    let check: fn(i32) -> i32 = other
    check(1)
    let p: P = P { x: 1 }
    run()
    v + w + twice<i32>(1) + twice<i64>(2) + p.go()
"""

# line:col of each report, one per lowered copy: twice<T> has two instances.
# The statement `match` arms end in `pass`, not `0`: a discarded arm value is
# LARB R69's (no_effect.ritz, AGAST #3492), and this test pins must_use's reach.
REACH_WANTED = sorted(["15:9", "19:5", "19:5", "23:5", "28:9", "31:9", "34:9",
                       "37:9", "42:9", "45:9", "49:13", "53:9", "60:17",
                       "68:5"])


def _reports(comp):
    out = comp.stdout + comp.stderr
    return out, re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_sema_error_stops_before_emission(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "stop", STOPS_BEFORE_EMIT)
    out, found = _reports(comp)
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    assert found == [("12:5", RULE)], f"{compiler}: wanted only the Sema error:\n{out}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_must_use_reaches_what_the_emitter_reached(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "reach", REACH)
    out, found = _reports(comp)
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    assert all(msg == RULE for _, msg in found), out
    assert sorted(at for at, _ in found) == REACH_WANTED, f"{compiler}:\n{out}"
