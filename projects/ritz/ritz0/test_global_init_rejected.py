"""A global `var` initializer no compiler can lower is a located error (AGAST #3027).

ritz0's `_emit_global_var` ended its initializer chain in a bare Python
`ValueError` ("Unsupported global var initializer", "Complex unary op
initializer not supported", ...): a traceback, no file:line:col, for
`var g: i32 = 1 + 2` or `var g: i32 = true`, both of which ritz1 refuses with a
located error.

Every case runs through ritz0, ritz1 and ritz1_selfhosted.  The message is
ritz1's, and all three locate it at the initializer, not at the global's
declaration (AGAST #3043: ritz1 said column 1).  Accepted forms (`~0`, `-~2`) are run in test_ritz1_global_var_init.py.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

_MAIN = "fn main() -> i32\n    0\n"
_NON_CONST = "global 'g' has a non-constant initializer"
_B2I = "cannot use bool as an integer: write `b as i32`"

# name -> (source, line, column, message prefix)
REJECTED = {
    "binary": ("var g: i32 = 1 + 2\n" + _MAIN, 1, 14, _NON_CONST),
    "bool_into_int": ("var g: i32 = true\n" + _MAIN, 1, 14, _B2I),
    "not_of_a_global": ("var x: bool\nvar g: bool = not x\n" + _MAIN, 2, 15, _NON_CONST),
    "neg_of_a_global": ("var x: i32\nvar g: i32 = -x\n" + _MAIN, 2, 14, _NON_CONST),
    "bit_not_of_a_global": ("var x: i32\nvar g: i32 = ~x\n" + _MAIN, 2, 14, _NON_CONST),
    "cast_of_binary": ("var g: i64 = (1 + 2) as i64\n" + _MAIN, 1, 15, _NON_CONST),
}


def _compile(request, compiler, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path,
                              env=env, capture_output=True, text=True, timeout=300)
    return proc, ll


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REJECTED))
def test_an_unlowerable_global_initializer_is_a_located_error(request, tmp_path, compiler, name):
    source, line, col, message = REJECTED[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    assert "Traceback" not in out and "ValueError" not in out, f"{compiler}, {name}:\n{out[-1500:]}"
    hits = re.findall(rf"unit\.ritz:{line}:{col}: (?:error: )?{re.escape(message)}", out)
    assert len(hits) == 1, f"{compiler}, {name}: want one {message!r} at {line}:{col}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
def test_ritz0_null_into_an_integer_global_is_a_located_error(request, tmp_path):
    """ritz0-only: ritz1 stores `null` in an integer global as 0.  ritz0 refuses
    it, but located, not as the bare ValueError it raised before #3027."""
    proc, ll = _compile(request, "ritz0", tmp_path, "var g: i32 = null\n" + _MAIN)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0 and "ValueError" not in out, out[-1500:]
    assert re.search(r"unit\.ritz:1:14: (?:error: )?global 'g' .*null", out), out[-1500:]
    assert not ll.exists()
