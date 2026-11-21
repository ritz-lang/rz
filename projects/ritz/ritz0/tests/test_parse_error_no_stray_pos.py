"""AGAST #3691: a located parse-time refusal is not followed by a stray
unlocated "Parse error at pos N" line.

ritz1's driver printed "Parse error at pos N" whenever the parse failed, even
though every failure the parser can produce has already been reported at a
`<file>:<line>:<col>` (module_require_eof's three failure branches, and the
parse-time refusals counted in g_attr_errors).  The driver now prints its own
line only for a failure nothing reported, and locates it.

Pinned on ritz1 and ritz1_selfhosted (ritz0 never printed the line).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
COMPILERS = ["ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration

# A parse-time refusal counted in g_attr_errors (#1879).
EXTERN_VAR_INIT = """\
extern var g: i32 = 1

fn main() -> i32
    0
"""

# A plain syntax error: a stray `)` where an item should start.
SYNTAX_ERROR = """\
fn main() -> i32
    0
)
"""


def _stderr(compiler, tmp_path, src):
    path = tmp_path / "t.ritz"
    path.write_text(src)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    proc = subprocess.run([str(binary), str(path), "-o", str(tmp_path / "t.ll")],
                          cwd=tmp_path, env=env, capture_output=True, text=True,
                          timeout=120)
    assert proc.returncode != 0, f"{compiler} accepted:\n{src}"
    return proc.stdout + proc.stderr


@pytest.mark.parametrize("compiler", COMPILERS)
def test_extern_var_init_one_error_line(compiler, tmp_path):
    out = _stderr(compiler, tmp_path, EXTERN_VAR_INIT)
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == 1, f"{compiler}: expected one error line:\n{out}"
    assert re.match(r".*t\.ritz:1:\d+: error: extern var cannot have an initializer",
                    lines[0]), f"{compiler}: not the located refusal:\n{out}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_syntax_error_located_without_stray_pos(compiler, tmp_path):
    out = _stderr(compiler, tmp_path, SYNTAX_ERROR)
    assert "Parse error at pos" not in out, f"{compiler}: stray unlocated line:\n{out}"
    # The located item error and the file-wide tally (#3445), nothing else.
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == 2, f"{compiler}: expected two error lines:\n{out}"
    assert re.match(r".*t\.ritz:3:1: error: cannot parse item starting at '\)'",
                    lines[0]), f"{compiler}: syntax error not located:\n{out}"
    assert re.match(r".*t\.ritz: error: 1 top-level item\(s\) failed to parse",
                    lines[1]), f"{compiler}: no failure tally:\n{out}"
