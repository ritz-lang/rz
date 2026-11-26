"""Where ritz1 reports a print placeholder that is not one expression (AGAST #4697).

`print("x={x +}")`'s placeholder must hold exactly one expression.  Until
#4697 the emitter parsed each placeholder as it lowered the call
(emitter_print -> interp -> parser_gen), so it was the emitter that refused
`{x +}` ("ritz1 cannot emit: ..."), and only once every Sema check had
passed: a program with a Sema error as well never heard about the
placeholder.

Sema parses the placeholders now (call_check.ritz, `cc_interp_names`) and
notes each parse on the literal (`Expr.interp`), which the emitter and
nothing else reads.  So the diagnostic moved, and these rows pin where:

* it is Sema's, in diag's form, without the emitter's "cannot emit" prefix;
* it comes with the program's other Sema errors, in source order;
* it is reported only where the emitter would have parsed the placeholder:
  a `{expr:spec}` with a spec print does not print is still the emitter's
  spec error, not a parse error (a spec is refused before its expression is
  read).

ritz0 refuses the placeholder at parse time (parser.py "Invalid
interpolation expression"), so the move also brings ritz1 nearer ritz0.

Rows run through ritz1 and ritz1_selfhosted.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

COMPILERS = ["ritz1", "ritz1_selfhosted"]

_INVALID = (
    "error: invalid interpolation expression: a `{...}` placeholder must hold "
    "exactly one expression (write `{{` for a literal brace)"
)

_PRINT = """\
import ritzlib.io

fn main() -> i32
    let x: i32 = 5
    print("x={x +}\\n")
    0
"""

_FORMAT_INTO = """\
import ritzlib.io
import ritzlib.string

fn main() -> i32
    var s: String = string_new()
    format_into(@s, "a{)}b")
    0
"""

# A Sema error earlier in the file: both are reported, in source order.  Before
# #4697 only `nope` was: the emitter, which refused the placeholder, never ran.
_WITH_SEMA_ERROR = """\
import ritzlib.io

fn other() -> i32
    nope()

fn main() -> i32
    print("x={1 +}\\n")
    0
"""

# `:x` is refused before the expression is read, by the emitter, as before.
_SPEC = """\
import ritzlib.io

fn main() -> i32
    let x: i32 = 5
    print("{x +:x}\\n")
    0
"""

# name -> (source, the diagnostics in order, lines that must not appear)
CASES = {
    "print": (_PRINT, [f"unit.ritz:5:11: {_INVALID}"], ["cannot emit"]),
    "format_into": (_FORMAT_INTO, [f"unit.ritz:6:21: {_INVALID}"], ["cannot emit"]),
    "with_sema_error": (
        _WITH_SEMA_ERROR,
        ["unit.ritz:4:5: error: Unknown function: nope", f"unit.ritz:7:11: {_INVALID}"],
        ["cannot emit"],
    ),
    "spec_first": (
        _SPEC,
        ["unit.ritz:5:11: error: format spec `x` is parsed but not printed until "
         "AGAST #202; drop `:x` for now"],
        ["invalid interpolation expression"],
    ),
}


def _compile(request, compiler, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    proc = subprocess.run([str(binary), src.name, "-o", ll.name], cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=300)
    return proc, ll


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CASES))
def test_placeholder_diagnostic_is_semas(request, tmp_path, compiler, name):
    source, messages, absent = CASES[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"
    lines = [ln for ln in out.splitlines() if ": error: " in ln]
    assert lines == messages, (
        f"{compiler} {name}: expected exactly\n  " + "\n  ".join(messages)
        + "\ngot\n  " + "\n  ".join(lines) + f"\n\nfull output:\n{out[-1500:]}")
    for text in absent:
        assert text not in out, f"{compiler} {name}: `{text}` in\n{out[-1500:]}"
