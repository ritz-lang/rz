"""`.field` on a value whose struct type is never declared (AGAST #3362).

Found by #3347: without `import ritzlib.string`, `let s: String = "abc"` then
`s.len` got #3347's located error at the literal, and then ritz1 also said
"cannot emit: unhandled EXPR_MEMBER" and the unlocated "emitted 1 unlowerable
expression(s)", because `String` names no struct.  The same unlocated pair was
all a `var s: Foo` or a `s: String` param got.

The rule: a member access on a local whose struct type is undeclared is one
located error at the base, naming the type, given once per type name; a type
that #3347 already refused at a literal is not reported again.  ritz1 only:
ritz0 raises a ValueError on these (AGAST #3404).
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

COMPILERS = ["ritz1", "ritz1_selfhosted"]

UNKNOWN = "names no declared struct"

# name -> (source, expected first-error location, type it must name)
LOCATED = {
    # A local of an undeclared type, and a second access to the same type.
    "var": ("fn main() -> i32\n    var s: Foo\n    let n: i64 = s.len + s.cap\n    0\n",
            "unit.ritz:3:18:", "`Foo`"),
    # A by-value param of an undeclared type.
    "param": ("fn f(s: String) -> i64\n    s.len\n\nfn main() -> i32\n    0\n",
              "unit.ritz:2:5:", "`String`"),
}

# The ticket's program: #3347's error at the literal is the only one.
TICKET = ('pub fn main() -> i32\n    let s: String = "abc"\n'
          '    let n: i64 = s.len\n    print("{n}\\n")\n    0\n')


def _compile(request, compiler, tmp_path, source):
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=300, check=False)
    out = proc.stdout + proc.stderr
    # 1, a refusal: not 0 (accepted) and not a signal (a crash after the error).
    assert proc.returncode == 1, f"{compiler} exited {proc.returncode}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR"
    return [ln for ln in out.splitlines() if "error" in ln.lower()]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(LOCATED))
def test_member_on_an_undeclared_struct_is_one_located_error(request, tmp_path, compiler, name):
    source, where, type_name = LOCATED[name]
    errors = _compile(request, compiler, tmp_path, source)
    assert len(errors) == 1, f"{compiler}, {name}: {errors}"
    assert where in errors[0] and UNKNOWN in errors[0] and type_name in errors[0], errors


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_string_refused_at_its_literal_is_not_reported_again(request, tmp_path, compiler):
    errors = _compile(request, compiler, tmp_path, TICKET)
    assert len(errors) == 1, f"{compiler}: {errors}"
    assert "unit.ritz:2:21:" in errors[0], errors
