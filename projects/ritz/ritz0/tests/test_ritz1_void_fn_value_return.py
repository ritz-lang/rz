#!/usr/bin/env python3
"""ritz1 refuses a value `return` in a fn with no return type (AGAST #4840).

`return g(x)` in a fn with no return type, `g` one too, is the call and then a
bare `ret void` (ritz0/test/test_issue_void_call_return.ritz runs it under all
three compilers).  Any other value there wrote `ret void %.N`, which clang
rejects with no source location.  ritz1 and ritz1_selfhosted now refuse it at
the `return`, exit 1 and write no IR.  (ritz0 infers the fn's type from the
value instead; ritz1 has no return-type inference.)
"""

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

# An int value, and a call of a fn that has one.
REFUSED = {
    "int_literal": "fn f()\n    return 5\n",
    "valued_call": "fn g() -> i32\n    7\n\nfn f()\n    return g()\n",
}
_MAIN = "\npub fn main() -> i32\n    f()\n    0\n"


@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
@pytest.mark.parametrize("row", sorted(REFUSED))
def test_value_return_in_void_fn_refused(request, tmp_path, compiler, row):
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    source = REFUSED[row] + _MAIN
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)
    line = source.split("\n").index(next(t for t in source.split("\n") if "return" in t)) + 1
    assert proc.returncode == 1, proc.stderr
    assert f"unit.ritz:{line}:5: error:" in proc.stderr, proc.stderr
    assert "`return <value>` in a fn with no return type" in proc.stderr, proc.stderr
    assert not ll.exists()
