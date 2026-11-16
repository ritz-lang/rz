"""AGAST #3505: ritz1's implicit-narrowing check runs on Sema, before emission.

THE CHANGE (a child of #1816, after #3462's must_use)

`let n: i32 = <i64 expr>` is refused unless it provably fits (AGAST #1364;
the rule's own tests are test_implicit_narrowing.py, and its ritz0/ritz1
parity is test_ritz1_implicit_narrowing.py).  ritz1 checked it at the top of
emit_var_decl, against a flat per-fn table of written annotations.  It now
runs from the Sema walk, before each `let` / `var` is bound, against Sema's
lexical scope, where each binding carries the integer type it was written
with (a param's, a typed let's, a match binding's payload or scrutinee type).

THE TESTS

- A Sema error stops the compile before emission: an emitter-side error in
  the same file (a const that does not fold) is no longer printed.
- One program pins the check's reach to the emitter's, location by location:
  every block kind, a match arm binding (a payload `Some(x)` and a catch-all
  name), an if-expression arm, an impl method, each generic instance, and
  a `let` reading a name before it is bound.
- One verdict changes, to ritz0's.  The emitter's table never dropped a
  block's declarations, and gave up (silent) when two of a name disagreed:
  `a` is an i64 where it is read, after an i16 `a` in an earlier block, so
  it is refused now, as ritz0 refuses it.  (No shadowing, binder_check, so
  the dead declaration can't hide a live param or global of its name.)
- A const folded only at emit time (it names a later const) is resolved by
  Sema when it reads it: an i64 one too big for an i32 is refused, and a
  mask through one still proves the value fits.
"""

import re

import pytest
from test_ref_into_value import _compile

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

RULE = re.compile(
    r"implicit narrowing: `(\w+)` is declared `(\w+)` but its "
    r"initialiser has type `(\w+)`"
)

BIG = """\
import ritzlib.option

fn big() -> i64
    4294967301

"""

STOPS_BEFORE_EMIT = (
    BIG
    + """\
const BAD: i32 = big()

fn main() -> i32
    let n: i32 = big()
    n
"""
)

REACH = (
    BIG
    + """\
struct P
    x: i32

impl P
    fn go(self: @P) -> i32
        let a: i32 = big()
        a

fn twice<T>(x: T) -> i32
    let b: i16 = big()
    0

fn arms(o: Option<i64>, w: u64) -> i32
    match o
        Some(x) =>
            let c: i32 = x
            return c
        None => 0
    let d: u8 = match w
        k =>
            let e: u8 = k
            e
    d as i32

fn main() -> i32
    var n: i64 = big()
    for i in 0..2
        let f: i32 = n
    loop
        let g: i32 = n
        break
    unsafe
        let h: i32 = n
    defer
        let j: i32 = n
    if n == 1
        let q: i32 = n
    else
        let r: i32 = n
    while n > 100
        let t: i32 = n
        n = n - 1
    let u: i32 = if n == 2
        let v: i32 = n
        1
    else
        0
    let p: P = P { x: 1 }
    u + twice<i32>(1) + twice<i64>(2) + p.go() + arms(None, 3)
"""
)

# line:col of each report, one per lowered copy: twice<T> has two instances.
REACH_WANTED = sorted(
    [
        "11:9",
        "15:5",
        "15:5",
        "21:13",
        "26:13",
        "33:9",
        "35:9",
        "38:9",
        "40:9",
        "42:9",
        "44:9",
        "46:9",
        "49:9",
    ]
)

LEXICAL = (
    BIG
    + """\
fn block_shadowed(c: bool) -> i32
    if c
        let a: i16 = 1
        if a == 2
            return 0
    let a: i64 = big()
    let n: i32 = a
    n

fn main() -> i32
    block_shadowed(true)
"""
)

# LOW and TOO_BIG name consts declared after them, so the parser leaves them
# unfolded (CONST_FOLD_PENDING) for emit_module to resolve.  Sema runs first
# and resolves what it reads: unresolved, a const has no type for the check,
# and TOO_BIG's i64 into an i32 went unrefused.  LOW's mask still proves fit.
LATE_CONSTS = (
    BIG
    + """\
const LOW: i64 = HALF - 1
const HALF: i64 = 128
const TOO_BIG: i64 = HUGE + 1
const HUGE: i64 = 4294967300

fn main() -> i32
    let n: u8 = big() & LOW
    let m: i32 = TOO_BIG
    m + n as i32
"""
)


def _reports(comp):
    out = comp.stdout + comp.stderr
    return out, re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_sema_error_stops_before_emission(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "stop", STOPS_BEFORE_EMIT)
    out, found = _reports(comp)
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    assert len(found) == 1 and found[0][0] == "9:5", (
        f"{compiler}: wanted only the Sema error:\n{out}"
    )
    assert RULE.search(found[0][1]).groups() == ("n", "i32", "i64"), out


@pytest.mark.parametrize("compiler", COMPILERS)
def test_narrowing_reaches_what_the_emitter_reached(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "reach", REACH)
    out, found = _reports(comp)
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    assert all(RULE.search(msg) for _, msg in found), out
    assert sorted(at for at, _ in found) == REACH_WANTED, f"{compiler}:\n{out}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_narrowing_scope_is_lexical(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "lexical", LEXICAL)
    out, found = _reports(comp)
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    assert [(at, RULE.search(msg).groups()) for at, msg in found] == [
        ("12:5", ("n", "i32", "i64"))
    ], f"{compiler}:\n{out}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_late_const_is_resolved_for_the_check(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "late", LATE_CONSTS)
    out, found = _reports(comp)
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    assert [(at, RULE.search(msg).groups()) for at, msg in found] == [
        ("13:5", ("m", "i32", "i64"))
    ], f"{compiler}:\n{out}"
