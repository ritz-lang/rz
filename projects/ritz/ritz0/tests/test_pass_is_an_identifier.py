"""AGAST #3320: `pass` is an ordinary identifier on every compiler.

THE DEFECT

    fn pass(x: i32) -> i32
        x + 1
    pub fn main() -> i32
        return pass(2)

ritz0: exit 3.  ritz1 and ritz1_selfhosted: `1:4: unexpected 'pass'`.
docs/LANGUAGE_SPEC.md says `self` and `pass` are not keywords, just ordinary
identifiers, but ritz1's lexer made `pass` a PASS token, so no name position
(fn, param, local, field, member, call) accepted it.

THE FIX

ritz1 lexes `pass` as an IDENT.  A bare `pass` is the no-op (a statement, and
a valueless match arm) as before, unless a call, member or index follows it
(`pass(2)`, `s.pass`), or the enclosing fn binds `pass` as a param or local,
when it reads that binding: ritz0's order (locals and params first, then the
no-op).

Each program returns 0, or the number of the first check that failed, on all
three compilers.  ritz0 is the oracle: every program passes there too.
"""

import pytest

import test_ritz1_for_header as for_header

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

PROGRAMS = {
    # The ticket's program: a fn named `pass`, called.
    "fn_name": """\
fn pass(x: i32) -> i32
    x + 1

pub fn main() -> i32
    if pass(2) != 3
        return 1
    return 0
""",
    # Params, locals (let, typed and inferred; var, reassigned) and a for
    # variable named `pass`, each read back bare.
    "bindings": """\
fn param(pass: i32) -> i32
    return pass * 2

fn let_typed() -> i32
    let pass: i32 = 5
    return pass

fn let_inferred() -> i64
    let pass = 7
    pass + 1

fn var_assigned() -> i32
    var pass: i32 = 1
    pass = pass + 10
    pass += 1
    return pass

fn loop_var() -> i32
    var sum: i32 = 0
    for pass in 0..4
        sum += pass as i32
    return sum

pub fn main() -> i32
    if param(4) != 8
        return 1
    if let_typed() != 5
        return 2
    if let_inferred() != 8
        return 3
    if var_assigned() != 12
        return 4
    if loop_var() != 6
        return 5
    return 0
""",
    # A struct field named `pass`: declared, initialised, read and written.
    "field": """\
struct Gate
    pass: i32
    fail: i32

fn bump(g: *Gate)
    g.pass = g.pass + 1

pub fn main() -> i32
    var g: Gate = Gate { pass: 4, fail: 1 }
    bump(@g)
    if g.pass != 5
        return 1
    if g.fail != 1
        return 2
    return 0
""",
    # `pass` is still the no-op: a statement, an `if` branch and a valueless
    # match arm, including in a fn after one that bound `pass` (the binding
    # does not leak).  It has no value: `let z: i32 = pass` is refused
    # (AGAST #3759, test_match_pass_arm_value.py).
    "still_the_noop": """\
fn binds(pass: i32) -> i32
    return pass

fn arms(n: i32) -> i32
    var r: i32 = 7
    match n
        0 => pass
        _ => r = 9
    if n == 0
        pass
    else
        r += 1
    return r

pub fn main() -> i32
    pass
    if binds(3) != 3
        return 1
    if arms(0) != 7
        return 2
    if arms(1) != 10
        return 3
    return 0
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
@pytest.mark.parametrize("compiler", COMPILERS)
def test_pass_as_identifier_runs(run_with, compiler, name):
    assert run_with(compiler, name, PROGRAMS[name]) == 0
