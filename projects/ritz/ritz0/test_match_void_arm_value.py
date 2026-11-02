"""AGAST #2046: a match / if-expression used as a value with a valueless arm.

    let x: i32 = match o
        Some(e) => say(e)       # say returns nothing
        None => 1

The arm has no value, so the program is ill-typed. ritz0 accepted it silently
(the arm fed nothing useful to the binding). ritz1, after #1654, treats a match
with a void-call arm as valueless (no phi, register 0), so the consumer named
the undefined `%.0`, ritz1 exited 0 and clang rejected the IR.

Both compilers now reject a match or if-expression whose value is USED (let /
var initialiser, assignment, return, call argument, operator operand) when an
arm has no value: a call to a void fn, or a nested match / if whose own arms
are valueless. The diagnostic is located at the offending arm,
`<file>:<line>:<col>`.

Still legal (the `LEGAL` table): a statement-position match or if, whatever
its arms; an if/else or match nested as an arm of a statement match; a
diverging arm (`return`) in a value match. #1654's statement forms are pinned
by test_ritz1_match_void_arms.py, test_match_mixed_void_arms.py and the
test_diff_match_void_arms.ritz matrix case.

ritz1's grammar has no multi-line match in an argument or assignment, so its
argument / operand cases use the inline `if c then a else b` form; ritz0 also
gets the multi-line match argument.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent

HEADER = """\
import ritzlib.option

fn say(x: i32)
    pass

fn take(x: i32) -> i32
    x

"""
# Line numbers below are 1-based within the whole file; HEADER is 8 lines.
H = HEADER.count("\n")

# name -> (body, line of the offending arm, col of the offending arm,
#          compilers that parse it)
BOTH = ("ritz0", "ritz1")
REJECTED = {
    # The ticket's repro: `let` with an annotation.
    "let_match": ("""\
pub fn main() -> i32
    let o: Option<i32> = None
    let x: i32 = match o
        Some(e) => say(e)
        None => 1
    x
""", H + 4, 20, BOTH),
    "var_match": ("""\
pub fn main() -> i32
    let o: Option<i32> = None
    var x: i32 = match o
        None => 1
        Some(e) => say(e)
    x
""", H + 5, 20, BOTH),
    "return_match": ("""\
fn f(o: Option<i32>) -> i32
    return match o
        Some(e) => say(e)
        None => 1

pub fn main() -> i32
    f(None)
""", H + 3, 20, BOTH),
    # A block-bodied arm whose tail is the void call.
    "let_match_block_arm": ("""\
pub fn main() -> i32
    let o: Option<i32> = None
    let x: i32 = match o
        Some(e) =>
            let t: i32 = e + 1
            say(t)
        None => 1
    x
""", H + 6, 13, BOTH),
    # A nested match whose own arm is a void call: the inner match has no
    # value, so neither does the outer arm. Located at the innermost call.
    "let_match_nested": ("""\
pub fn main() -> i32
    let o: Option<i32> = None
    let p: Option<i32> = None
    let x: i32 = match o
        Some(e) => match p
            Some(f) => say(f)
            None => 2
        None => 1
    x
""", H + 6, 24, BOTH),
    # if-expressions (block form) with a void-call arm.
    "let_if": ("""\
pub fn main() -> i32
    let c: i32 = 1
    let x: i32 = if c == 1
        say(1)
    else
        2
    x
""", H + 4, 9, BOTH),
    "return_if": ("""\
fn f(c: i32) -> i32
    return if c == 1
        2
    else
        say(c)

pub fn main() -> i32
    f(1)
""", H + 5, 9, BOTH),
    # Argument and operand positions: inline if-expression.
    "argument_inline_if": ("""\
pub fn main() -> i32
    let c: i32 = 1
    take(if c == 1 then say(1) else 2)
""", H + 3, 25, BOTH),
    "argument_inline_if_let": ("""\
pub fn main() -> i32
    let c: i32 = 1
    let r: i32 = take(if c == 1 then 2 else say(1))
    r
""", H + 3, 45, BOTH),
    "operand_inline_if": ("""\
pub fn main() -> i32
    let c: i32 = 1
    let r: i32 = 1 + (if c == 1 then say(1) else 2)
    r
""", H + 3, 38, BOTH),
    # ritz1 has no multi-line match argument or `x = match` assignment.
    "argument_match": ("""\
pub fn main() -> i32
    let o: Option<i32> = None
    take(match o
        Some(e) => say(e)
        None => 1
    )
""", H + 4, 20, ("ritz0",)),
    "assign_match": ("""\
pub fn main() -> i32
    let o: Option<i32> = None
    var x: i32 = 0
    x = match o
        Some(e) => say(e)
        None => 1
    x
""", H + 5, 20, ("ritz0",)),
}

LEGAL = {
    # A diverging arm has no value either, but never reaches the binding.
    "let_match_return_arm": """\
fn f(o: Option<i32>) -> i32
    let x: i32 = match o
        Some(e) => return e
        None => 1
    x

pub fn main() -> i32
    f(None) - 1
""",
    # Statement-position match: void arms everywhere, plus a value arm.
    "stmt_match": """\
pub fn main() -> i32
    let o: Option<i32> = None
    match o
        Some(e) => say(e)
        None => 1
    0
""",
    # An if/else arm of a statement match whose branches are void calls.
    "stmt_match_if_arm": """\
pub fn main() -> i32
    let o: Option<i32> = Some(3)
    let c: i32 = 1
    match o
        Some(e) =>
            if c == 1
                say(1)
            else
                say(2)
        None => say(3)
    0
""",
    # A nested valueless match as an arm of a statement match.
    "stmt_match_nested": """\
pub fn main() -> i32
    let o: Option<i32> = Some(1)
    let p: Option<i32> = None
    match o
        Some(e) => match p
            Some(f) => say(f)
            None => say(e)
        None => say(0)
    0
""",
    # An inline if statement with void arms.
    "stmt_inline_if": """\
pub fn main() -> i32
    let c: i32 = 1
    if c == 1 then say(1) else say(2)
    0
""",
    # A void procedure ending in an if/else with void-call arms.
    "void_proc_tail_if": """\
fn g(c: i32)
    if c == 1
        say(1)
    else
        say(2)

pub fn main() -> i32
    g(1)
    0
""",
}


def _ritz0(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    out = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    proc = run_ritz0([str(src), "-o", str(out)], env=env, timeout=300)
    return proc.returncode, proc.stdout + proc.stderr, out


def _ritz1(ritz1_bin, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    out = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    proc = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(out)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300,
    )
    return proc.returncode, proc.stdout + proc.stderr, out


def _compile(compiler, request, tmp_path, source):
    if compiler == "ritz0":
        return _ritz0(tmp_path, source)
    return _ritz1(request.getfixturevalue("ritz1_bin"), tmp_path, source)


_REJECT_CASES = [
    pytest.param(compiler, name, id=f"{compiler}-{name}")
    for name, (_, _, _, compilers) in sorted(REJECTED.items())
    for compiler in compilers
]


@pytest.mark.integration
@pytest.mark.parametrize("compiler,name", _REJECT_CASES)
def test_valueless_arm_in_value_position_is_a_located_error(
        request, tmp_path, compiler, name):
    body, line, col, _ = REJECTED[name]
    rc, output, _ = _compile(compiler, request, tmp_path, HEADER + body)
    assert rc != 0, f"{compiler} accepted a valueless arm used as a value:\n{output}"
    assert "has no value" in output, f"rejected for another reason:\n{output}"
    m = re.search(r"unit\.ritz:(\d+):(\d+): .*has no value", output)
    assert m, f"diagnostic is not located at <line>:<col>:\n{output}"
    assert (int(m.group(1)), int(m.group(2))) == (line, col), output


@pytest.mark.integration
@pytest.mark.parametrize("compiler", BOTH)
@pytest.mark.parametrize("name", sorted(LEGAL))
def test_statement_and_diverging_forms_stay_legal(
        request, tmp_path, compiler, name):
    rc, output, ll = _compile(compiler, request, tmp_path, HEADER + LEGAL[name])
    assert rc == 0 and ll.exists(), output
    cc = subprocess.run(
        ["clang", "-w", "-c", "-x", "ir", str(ll), "-o", str(tmp_path / "unit.o")],
        capture_output=True, text=True, timeout=300,
    )
    assert cc.returncode == 0, cc.stderr[-2000:]
