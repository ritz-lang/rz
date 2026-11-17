"""AGAST #3502: ritz1's bool_check runs on Sema, before emission (#1816).

THE CHANGE

bool_check (LARB R4, AGAST #2342: `bool` is its own type) was 13 `pub fn
bool_check_*(s: *EmitterState, ..)` calls made mid-lowering.  It now takes
`sm: *Sema` and runs from sema_walk.ritz, at each place the emitter called it
and before that place's own sub-expressions, so the reports and their order
are the emitter's.  It judges with sema_bool_kind, its port of the emitter's
bool_kind onto Sema's scope; the emitter keeps bool_kind (bool_kind.ritz) for
codegen, and RITZ1_SEMA_PROBE pins the two together
(test_ritz1_sema_type.py).  A bool error now stops the compile before emission.

The diagnostics themselves are the shared table's (test_bool_type.py,
test_ritz1_bool_*.py), unchanged; the commit compared every file of ritz0/test,
ritzlib, examples and ritz1/src, plain and --test-table, against the pre-move
compiler: the same IR, and the same words for each refusal.

THE TEST

One program, both ritz1 compilers.  Its two bool errors sit in places the
walk had to learn to reach: a `match` statement's scrutinee (`match b + 1`)
and a struct literal's field (`P { x: true }`).  A literal that doesn't fit
its slot after them is literal_slot's error, still on the emitter: it is no
longer printed.  Before the move all three were.  (It was a write to a `let`
until let_check moved onto Sema too, AGAST #3504.)
"""

import re

import pytest

from test_ref_into_value import _compile

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

PROGRAM = """\
struct P
    x: i64

fn main() -> i32
    let b: bool = true
    match b + 1
        _ => 0
    let p: P = P { x: true }
    var m: u8 = 300
    0
"""

WANTED = [
    ("6:11", "operand of `+` must be a number, got bool"),
    ("8:23", "cannot use bool as an integer: write `b as i32`"),
]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_bool_errors_stop_the_compile_before_emission(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_bool", PROGRAM)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)
    assert found == WANTED, f"{compiler}:\n{out}"
