"""A statement `if` / `match` whose arms mix a value with no value (AGAST #4911).

An arm that calls a procedure, or that ends in an `if` with no `else`, has no
value. ritz0 gave each a dummy `i32 0` and merged it with the other arms', so a
statement whose other arm ends in a bool (as `Vec.push` does) was refused:

    match inst
        Inst.Jmp(o) => stack.push(pc + o)       # bool
        _ => vm.add(pc)                          # a procedure
    -> cannot use an integer as bool: write `x != 0`

ritz1 accepted all of these. A procedure arm and an else-less `if` arm are now
valueless, as a `pass` arm is (#3491), so the statement compiles. A *used* one
is still refused where it is emitted (test_match_void_arm_value.py, #2046).
"""

import pytest

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

HEADER = """\
# A stand-in for Vec: push returns a bool, clear nothing.
struct Stack
    n: i64

impl Stack
    fn push(self: @&Stack, x: i64) -> bool
        self.n += x
        true

    fn clear(self: @&Stack)
        self.n = 0

enum Inst
    Jmp(i64)
    Split(i64, i64)
    Found

fn note(v: @&Stack)
    v.clear()

"""

# name -> a fn whose statement `if` / `match` mixes a bool arm with a
# valueless one; each is its own arm shape. One program holds them all (a
# ritz0 case is paid on every gate: docs/TESTING.md), so each fn is renamed
# after its row.
STATEMENTS = {
    "if_procedure_else": """\
fn f(v: @&Stack, c: bool) -> i64
    if c
        v.push(1)
    else
        note(v)
    5
""",
    "if_else_if_procedure": """\
fn f(v: @&Stack, a: bool, b: bool) -> i64
    if a
        v.push(1)
    else if b
        v.push(2)
    else
        v.clear()
    5
""",
    "enum_match_procedure_arm": """\
fn f(v: @&Stack, x: Inst) -> i64
    match x
        Inst.Jmp(o) => v.push(o)
        _ => note(v)
    5
""",
    "enum_match_elseless_if_arm": """\
fn f(v: @&Stack, x: Inst, c: bool) -> i64
    match x
        Inst.Jmp(o) => v.push(o)
        Inst.Split(a, b) =>
            if c
                v.push(a)
        _ => pass
    5
""",
    "integer_match_procedure_arm": """\
fn f(v: @&Stack, n: i64) -> i64
    match n
        1 => v.push(n)
        _ => note(v)
    5
""",
}


def test_statements_with_valueless_arms_compile(tmp_path):
    program = HEADER + "\n".join(
        STATEMENTS[name].replace("fn f(", f"fn {name}(", 1) for name in sorted(STATEMENTS))
    src = tmp_path / "unit.ritz"
    src.write_text(program)
    result = run_ritz0([str(src), "-o", str(tmp_path / "unit.ll"), "--no-runtime"])
    assert result.returncode == 0, result.stderr
