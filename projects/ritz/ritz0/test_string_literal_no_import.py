"""`let s: String = "abc"` with no `import ritzlib.string` (AGAST #3347).

`String` isn't built in (not in builtin_types.BUILTIN_TYPES): ritzlib.string
declares it, and ritz0 makes a literal into one through its
`string_from_bytes`.  Without the import, refusing is right, but ritz0 raised
a bare ValueError (a Python traceback) and ritz1 stored the literal's
`{ ptr, len }` into an undeclared `%String`, or, with a `.len` after it,
refused with only the unlocated "emitted 1 unlowerable expression(s)".

The rule: all three compilers refuse it at the literal, `file:line:col`, with
the same words, naming the fix.  With the import ritz0 still builds the
String; ritz1 refuses that one for its own reason (a literal is a StrView,
LANGUAGE_SPEC section 3.5), which this rule leaves alone.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from emitter_llvmlite import STRING_LIT_NO_IMPORT
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# The literal is at line 2, column 21 in each row.
_TAIL = "    0\n"
REJECTED = {
    "let": 'fn main() -> i32\n    let s: String = "abc"\n' + _TAIL,
    "var": 'fn main() -> i32\n    var s: String = "abc"\n' + _TAIL,
    # The ticket's own program: the `.len` after it changes nothing.
    "ticket": ('pub fn main() -> i32\n    let s: String = "abc"\n'
               '    let n: i64 = s.len\n    print("{n}\\n")\n' + _TAIL),
}

_WITH_IMPORT = ('import ritzlib.string\n\nfn main() -> i32\n'
                '    let s: String = "abc"\n    string_len(@s) as i32\n')


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
    return proc, ll


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REJECTED))
def test_string_literal_without_the_import_is_a_located_error(request, tmp_path, compiler, name):
    proc, ll = _compile(request, compiler, tmp_path, REJECTED[name])
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"
    assert "Traceback" not in out, out
    # The first diagnostic is ours, at the literal.
    first = next(ln for ln in out.splitlines() if "error" in ln.lower())
    assert "unit.ritz:2:21:" in first, f"{compiler}, {name}:\n{out[-1500:]}"
    assert STRING_LIT_NO_IMPORT in first, f"{compiler}, {name}:\n{out[-1500:]}"


@pytest.mark.integration
def test_ritz0_with_the_import_still_builds_the_string(request, tmp_path):
    # Compiled, not linked: ritzlib.string's bodies are another module's.
    proc, ll = _compile(request, "ritz0", tmp_path, _WITH_IMPORT)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    ir = ll.read_text()
    assert re.search(r'call %"[^"]*String" @"string_from_bytes"\(i8\* %"[^"]*", i64 3\)', ir), ir[-2000:]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_ritz1_with_the_import_is_not_this_error(request, tmp_path, compiler):
    proc, _ = _compile(request, compiler, tmp_path, _WITH_IMPORT)
    assert STRING_LIT_NO_IMPORT not in proc.stdout + proc.stderr
