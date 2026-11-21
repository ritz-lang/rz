"""AGAST #1819: a parse error reports file:line:col AND the expected tokens.

The item-level diagnostic used to name only what was found:

    t.ritz:3:1: error: cannot parse item starting at ')'

It now also lists what the grammar would have accepted there, from the
farthest point the parse reached:

    t.ritz:3:1: error: cannot parse item starting at ')'; expected one of: ...

Pinned on ritz1 and ritz1_selfhosted (ritz0 is the Python bootstrap and has
its own message format).
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

# A stray `)` where a top-level item should start: no item alternative can
# consume it, so the farthest failure is the item's first token.
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
def test_syntax_error_lists_expected_tokens(compiler, tmp_path):
    out = _stderr(compiler, tmp_path, SYNTAX_ERROR)
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert lines, f"{compiler}: no diagnostics:\n{out}"
    # Located at the offending token, as before.
    assert re.match(r".*t\.ritz:3:1: error: cannot parse item starting at '\)'",
                    lines[0]), f"{compiler}: not located:\n{out}"
    # ...and now says what the grammar expected there.  The item rule's
    # FIRST set is the keyword that opens each alternative.
    assert re.search(r"; expected one of: .*\bfn\b", lines[0]), \
        f"{compiler}: no expected-token list:\n{out}"
    for tok in ("struct", "impl", "trait"):
        assert re.search(rf"\b{tok}\b", lines[0]), \
            f"{compiler}: expected list missing `{tok}`:\n{out}"
