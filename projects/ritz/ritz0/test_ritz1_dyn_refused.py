"""AGAST #2298: ritz1 refuses `dyn Trait` at the `dyn`, wherever a type is written.

    fn md(p: @P) -> dyn Speak
        return p as dyn Speak

ritz1 has no trait objects, and whether the language has them at all is
AGAST #1620's decision (LANGUAGE_SPEC §12 says it doesn't; ritz0 implements
them).  ritz1 used to read `dyn` as a type name, so `-> dyn Speak` left
`Speak` over and the error was "cannot parse item starting at ' MADE'", on the
body.  Now each `dyn` is one located error at the `dyn` token, and the rest of
the item still parses, so nothing else is reported.

Only ritz1's refusal is tested here: ritz0 compiles these (test_level40,
test_method_receiver_once.py's `dyn_receiver`).
"""

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ1S = ["ritz1", "ritz1_selfhosted"]

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
    "pointer_param_type": """\
fn f(s: *dyn Speak) -> i32
    return 0
""" + MAIN,
    "let_type": """\
pub fn main() -> i32
    var p = P { x: 1 }
    let s: @dyn Speak = @p
    return 0
""",
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


def _dyn_sites(src: str):
    """(line, col) of every `dyn` token, 1-based, as ritz1 reports positions."""
    sites = []
    for ln, text in enumerate(src.split("\n"), start=1):
        col = text.find("dyn ")
        while col != -1:
            sites.append((ln, col + 1))
            col = text.find("dyn ", col + 1)
    return sites


@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(CASES))
def test_dyn_refused_at_the_dyn_token(ritz1_bin, tmp_path, compiler, name):
    src = tmp_path / "main.ritz"
    program = PRELUDE + CASES[name]
    src.write_text(program)
    ll = tmp_path / "main.ll"
    comp = subprocess.run([str(RITZ1_BUILD / compiler), str(src), "-o", str(ll)],
                          cwd=tmp_path, env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
                          capture_output=True, text=True, timeout=120)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted `dyn`:\n{out[-2000:]}"
    assert not ll.exists(), f"{compiler} wrote IR for a refused program"
    errors = [ln for ln in out.splitlines() if ln.startswith("error:")]
    expected = [f"error: {src}:{line}:{col}: {MESSAGE}" for line, col in _dyn_sites(program)]
    # Exactly one error per `dyn`, at it, and nothing else: no "cannot parse
    # item" on the body, and no repeat when the parser backtracks over it.
    assert errors == expected, f"{compiler} {name}:\n{out[-2000:]}"
