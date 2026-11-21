"""`let s: String = "abc"` with no `import ritzlib.string` (AGAST #3347).

`String` isn't built in (not in builtin_types.BUILTIN_TYPES): ritzlib.string
declares it, and ritz0 makes a literal into one through its
`string_from_bytes`.  Without the import, refusing is right, but ritz0 raised
a bare ValueError (a Python traceback) and ritz1 stored the literal's
`{ ptr, len }` into an undeclared `%String`, or, with a `.len` after it,
refused with only the unlocated "emitted 1 unlowerable expression(s)".

The rule: all three compilers refuse it at the literal, `file:line:col`, with
the same words, naming the fix.  Since AGAST #3932 the annotation is refused
first: `String` names nothing without the import, so the one error is
"unknown type `String`" at the type's name.

With the import it is refused too (LARB R49, AGAST #3361, #3393): a literal
is a `StrView`, or a `*u8` in a `*u8` slot, and nothing else converts
(LANGUAGE_SPEC section 3.5).  A `String` allocates, so the source says so:
`string_from("abc")`.  ritz0 used to lower the literal to
`string_from_bytes(ptr, 3)`; ritz1 refused it as "`s` is declared `String`
but its initialiser is a `Span$u8`", at the `let`.  All three now give one
message, at the literal, quoting it back as source.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# The type is at line 2, column 12 in each row (the literal at column 21).
_TAIL = "    0\n"
REJECTED = {
    "let": 'fn main() -> i32\n    let s: String = "abc"\n' + _TAIL,
    "var": 'fn main() -> i32\n    var s: String = "abc"\n' + _TAIL,
    # The ticket's own program: the `.len` after it changes nothing.
    "ticket": ('pub fn main() -> i32\n    let s: String = "abc"\n'
               '    let n: i64 = s.len\n    print("{n}\\n")\n' + _TAIL),
}

# LARB R49: with the import, each row is refused at line 4, column 21, and
# the fix quotes the literal back as it is written: `"` and `\\` escaped, a
# non-ASCII character as itself.
_IMPORT = "import ritzlib.string\n\nfn main() -> i32\n"
_NOT_STRING = "a string literal is not a `String`: write `string_from({})`"
WITH_IMPORT = {
    "let": (_IMPORT + '    let s: String = "abc"\n' + _TAIL, '"abc"'),
    "var": (_IMPORT + '    var s: String = "abc"\n' + _TAIL, '"abc"'),
    "escapes": (_IMPORT + '    let s: String = "q\\"\\\\\\n\\t\\0\U0001F600"\n' + _TAIL,
                '"q\\"\\\\\\n\\t\\0\U0001F600"'),
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
    # One diagnostic, at the type (AGAST #3932).
    errors = [ln for ln in out.splitlines() if "error" in ln.lower()]
    assert len(errors) == 1, f"{compiler}, {name}:\n{out[-1500:]}"
    assert "unit.ritz:2:12:" in errors[0], f"{compiler}, {name}:\n{out[-1500:]}"
    assert "unknown type `String`" in errors[0], f"{compiler}, {name}:\n{out[-1500:]}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(WITH_IMPORT))
def test_string_literal_with_the_import_is_refused(request, tmp_path, compiler, name):
    source, quoted = WITH_IMPORT[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"
    assert "Traceback" not in out, out
    errors = [ln for ln in out.splitlines() if "error" in ln.lower()]
    # One error, ours: not ritz1's old "is declared `String`" as well.
    assert len(errors) == 1, f"{compiler}, {name}:\n{out[-1500:]}"
    assert "unit.ritz:4:21:" in errors[0], f"{compiler}, {name}:\n{out[-1500:]}"
    assert errors[0].endswith(_NOT_STRING.format(quoted)), f"{compiler}, {name}:\n{out[-1500:]}"
