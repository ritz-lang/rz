"""AGAST #1632: ritz1 accepts `self` as a `let` / `var` binding name.

THE DEFECT

    fn get(p: *i64) -> i64
        let self: *i64 = p
        return *self

ritz1: `cannot parse item 'fn get'`, so the whole fn is dropped. ritz0 compiles
it. `self` lexes as SELF, not IDENT, and every let/var alternative in
grammars/ritz1.grammar named only IDENT. Reads were already fine: primary_expr
turns SELF into an ordinary EXPR_IDENT. examples/tier5_async/63_executor binds
`let self: *SimpleFuture = ...` and hit this.

THE FIX

A `binding_name` nonterminal (IDENT | SELF) replaces IDENT in the let/var rules.

ORACLE (as in test_ritz1_self_param.py, #1375)

Each program is compiled three ways, and all three exit codes must agree:
ritz0 on the `self` spelling, ritz1 on the `self` spelling, and ritz1 with
`self` renamed to `me`.
"""

import re

import pytest

from test_ritz1_builtin_struct_shadow import _run, ritz1_bin  # noqa: F401

# The ticket's repro: typed `let`, deref read.
LET_TYPED = """\
fn get(p: *i64) -> i64
    let self: *i64 = p
    return *self

pub fn main() -> i32
    var x: i64 = 42
    return get(@x) as i32
"""

# Inferred `let`.
LET_INFERRED = """\
fn twice(n: i64) -> i64
    let self = n * 2
    return self

pub fn main() -> i32
    return twice(21) as i32
"""

# `var`: typed, inferred and declared without an initialiser, each reassigned.
VAR_FORMS = """\
fn typed(n: i64) -> i64
    var self: i64 = n
    self = self + 1
    return self

fn inferred(n: i64) -> i64
    var self = n
    self += 2
    return self

fn uninit(n: i64) -> i64
    var self: i64
    self = n * 3
    return self

pub fn main() -> i32
    if typed(1) != 2
        return 1
    if inferred(1) != 3
        return 2
    if uninit(2) != 6
        return 3
    return 42
"""

# The 63_executor shape: member read and write through `let self: *T` cast
# from an opaque pointer, plus a match-expression initialiser.
MEMBER = """\
struct Fut
    state: i64
    value: i64

fn poll(raw: *u8) -> i64
    let self: *Fut = raw as *Fut
    self.state = self.state + 1
    self.value = self.value * 2
    return self.value + self.state

fn pick(n: i64) -> i64
    let self = match n
        0 => 10
        _ => 20
    return self

pub fn main() -> i32
    var f: Fut = Fut { state: 1, value: 15 }
    let r: i64 = poll(@f as *u8)
    if f.state != 2
        return 1
    if pick(0) + pick(1) != 30
        return 2
    return r as i32
"""

CASES = {
    "let_typed": LET_TYPED,
    "let_inferred": LET_INFERRED,
    "var_forms": VAR_FORMS,
    "member": MEMBER,
}


def _rename_self(program: str) -> str:
    return re.sub(r"\bself\b", "me", program)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_let_self_matches_ritz0_and_renamed_twin(ritz1_bin, tmp_path, name):  # noqa: F811
    program = CASES[name]
    oracle = _run("ritz0", tmp_path, name, program)
    got = _run("ritz1", tmp_path, name, program)
    assert got == oracle, f"ritz1 exit {got} != ritz0 exit {oracle} for {name}"
    twin = _run("ritz1", tmp_path, f"{name}_me", _rename_self(program))
    assert twin == got, f"`me` twin exits {twin}, `self` exits {got}"
