"""`.field` on a scalar, by value or through a pointer (AGAST #4155).

Found by #4034: `fn f(p: *i32) -> i64` then `p.len` raised ritz0's
"ValueError: Cannot access field on non-struct pointer: i32" traceback, and
ritz1 said only "cannot emit: unhandled EXPR_MEMBER".  A by-value scalar
(`x: i64`, `x.len`) and a store (`p.len = 3`) fell the same way.

The rule: one located error at the base, naming it and its type:
"`p` has type `*i32`, which is not a struct: it has no field `len`".  ritz0's
checker gives it (type_checker.py, _refuse_primitive_member); ritz1 gives it
in the same words (emitter_expr_access.ritz, primitive_member_refused).
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

MAIN = "\nfn main() -> i32\n    0\n"

# name -> (source, location of the one error, the words it must say)
CASES = {
    # The ticket's program: a read through a pointer param.
    "ptr_read": ("fn f(p: *i32) -> i64\n    p.len\n" + MAIN,
                 "unit.ritz:2:5:", "`p` has type `*i32`, which is not a struct: it has no field `len`"),
    # A store through it (ritz0's emitter raised at the assign twin).
    "ptr_store": ("fn f(p: *u8)\n    p.len = 3\n" + MAIN,
                  "unit.ritz:2:5:", "`p` has type `*u8`, which is not a struct: it has no field `len`"),
    # A by-value scalar local.
    "value": ("fn main() -> i32\n    var x: i64 = 0\n    let n: i64 = x.len\n    0\n",
              "unit.ritz:3:18:", "`x` has type `i64`, which is not a struct: it has no field `len`"),
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
                              env=env, capture_output=True, text=True, timeout=300, check=False)
    out = proc.stdout + proc.stderr
    # 1, a refusal: not 0 (accepted) and not a traceback or signal.
    assert proc.returncode == 1, f"{compiler} exited {proc.returncode}:\n{out[-1500:]}"
    assert "Traceback" not in out, out[-1500:]
    assert not ll.exists(), f"{compiler} wrote IR"
    return [ln for ln in out.splitlines()
            if "error" in ln.lower() or re.search(r"unit\.ritz:\d+:\d+:", ln)]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CASES))
def test_member_on_a_scalar_is_one_located_error(request, tmp_path, compiler, name):
    source, where, words = CASES[name]
    errors = _compile(request, compiler, tmp_path, source)
    assert len(errors) == 1, f"{compiler}, {name}: {errors}"
    assert where in errors[0] and words in errors[0], errors
