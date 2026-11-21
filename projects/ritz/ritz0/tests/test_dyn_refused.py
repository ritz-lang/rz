"""AGAST #1620 / #2298: `dyn` is a reserved keyword, and every use of it is
refused at the `dyn` token, by ritz0, ritz1 and ritz1_selfhosted alike.

    fn md(p: @P) -> dyn Speak       # error at the `dyn`
        return p as dyn Speak       # and here

The language has no trait objects (LANGUAGE_SPEC §12.2: traits are
structural, statically resolved, no dynamic dispatch).  ritz0 used to build
vtables and fat pointers for `dyn Trait`; Aaron removed that on 2026-11-15
(#1620) and runtime polymorphism is #3251's design.  ritz1 used to read `dyn`
as a type name, so `-> dyn Speak` left `Speak` over and the error was "cannot
parse item starting at ' MADE'", on the body (#2298).

Each row is one place a type is written.  ritz1 reports every `dyn`, and the
rest of the item still parses, so nothing else is reported.  ritz0's parser
stops at its first error, so it reports the first `dyn`: the same line, column
and message as ritz1's first.

The rows here replace the `dyn` rows other files carried while ritz0 compiled
`dyn` (test_level40, test_dyn_trait, test_method_receiver_once.py's
`dyn_receiver`, the REJECTED_RITZ0_ONLY rows of test_procedure_call_value.py
and test_fn_tail_requires_value.py, test_string_literal_slots.py's `dyn_arg`,
test_borrow_param_ref_slot.py's `@dyn` slots, test_match_void_arm_value.py's
`let_if_dyn_method`): each of their shapes is a row below.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

MESSAGE = "`dyn Trait` is not supported (AGAST #1620)"

PRELUDE = """\
trait Speak
    fn say(self: @Self) -> i32

struct P
    x: i32

impl Speak for P
    fn say(self: @P) -> i32
        return self.x

"""

MAIN = """
pub fn main() -> i32
    return 0
"""

# name -> program after PRELUDE.  Each `dyn` in it is one expected error.
CASES = {
    # The ticket's program: a return type, and the cast it returns.
    "return_type": """\
fn md(p: @P) -> dyn Speak
    return p as dyn Speak
""" + MAIN,
    "param_type": """\
fn f(s: @dyn Speak) -> i32
    return 0
""" + MAIN,
    # A method called through the pointer: the receiver test_procedure_call_value
    # and test_fn_tail_requires_value used.
    "pointer_param_method_call": """\
fn f(s: *dyn Speak) -> i32
    return s.say()
""" + MAIN,
    # A by-value `dyn` parameter, and a cast to it as the argument.
    "value_param_and_cast_arg": """\
fn go(t: dyn Speak) -> i32
    return t.say()

pub fn main() -> i32
    var p = P { x: 1 }
    return go(@p as dyn Speak)
""",
    "let_type": """\
pub fn main() -> i32
    var p = P { x: 1 }
    let s: @dyn Speak = @p
    return 0
""",
    "var_type": """\
pub fn main() -> i32
    var p = P { x: 1 }
    var s: *dyn Speak = @p
    return 0
""",
    "field_type": """\
struct H
    s: *dyn Speak
""" + MAIN,
    "cast": """\
pub fn main() -> i32
    var p = P { x: 1 }
    let s = @p as dyn Speak
    return 0
""",
    # A generic argument, here one closed by `>>`.
    "nested_generic_arg": """\
struct W<T>
    v: T

fn f(w: *W<W<dyn Speak>>) -> i32
    return 0
""" + MAIN,
}

# "Parse error: <file>:<line>:<col>: <message>" (ritz0) or
# "<file>:<line>:<col>: error: <message>" (ritz1, diag.ritz, AGAST #3445).
DIAG = {
    "ritz0": re.compile(r"^Parse error: (.+?):(\d+):(\d+): (.*)$"),
    "ritz1": re.compile(r"^(.+?):(\d+):(\d+): error: (.*)$"),
}


def _dyn_sites(src: str):
    """(line, col) of every `dyn` token, 1-based."""
    sites = []
    for ln, text in enumerate(src.split("\n"), start=1):
        col = text.find("dyn ")
        while col != -1:
            sites.append((ln, col + 1))
            col = text.find("dyn ", col + 1)
    return sites


def _compile(compiler, src: Path, ll: Path):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=src.parent, env=env, timeout=120)
    return subprocess.run([str(RITZ1_BUILD / compiler), str(src), "-o", str(ll)],
                          cwd=src.parent, env=env, capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CASES))
def test_dyn_refused_at_the_dyn_token(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    src = tmp_path / "main.ritz"
    program = PRELUDE + CASES[name]
    src.write_text(program)
    ll = tmp_path / "main.ll"
    comp = _compile(compiler, src, ll)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted `dyn`:\n{out[-2000:]}"
    assert not ll.exists(), f"{compiler} wrote IR for a refused program"
    diag = DIAG["ritz0" if compiler == "ritz0" else "ritz1"]
    errors = [m.groups() for m in map(diag.match, out.splitlines()) if m]
    expected = [(str(src), str(line), str(col), MESSAGE) for line, col in _dyn_sites(program)]
    if compiler == "ritz0":
        expected = expected[:1]  # its parser stops at the first error
    # Exactly one error per `dyn`, at it, and nothing else: no "cannot parse
    # item" on the body, and no repeat when the parser backtracks over it.
    assert errors == expected, f"{compiler} {name}:\n{out[-2000:]}"
