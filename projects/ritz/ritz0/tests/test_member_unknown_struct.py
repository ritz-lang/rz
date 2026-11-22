"""`.field` on a value whose struct type is never declared (AGAST #3362).

Found by #3347: without `import ritzlib.string`, `let s: String = "abc"` then
`s.len` got #3347's located error at the literal, and then ritz1 also said
"cannot emit: unhandled EXPR_MEMBER" and the unlocated "emitted 1 unlowerable
expression(s)", because `String` names no struct.  The same unlocated pair was
all a `var s: Foo` or a `s: String` param got.

The rule: a member access on a local whose struct type is undeclared is one
located error at the base, naming the type, given once per type name; a type
that #3347 already refused at a literal is not reported again.  ritz0 raised a
ValueError traceback on these, with no location (AGAST #3404); its checker now
gives ritz1's error.

Since AGAST #3932 the undeclared type itself is that one error, at its name
("unknown type `Foo`"), on every compiler, before any member access or literal
is lowered.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

UNKNOWN = "unknown type"

# name -> (source, expected first-error location, type it must name)
LOCATED = {
    # A local of an undeclared type, and a second access to the same type.
    "var": ("fn main() -> i32\n    var s: Foo\n    let n: i64 = s.len + s.cap\n    0\n",
            "unit.ritz:2:12:", "`Foo`"),
    # A by-value param of an undeclared type.
    "param": ("fn f(s: String) -> i64\n    s.len\n\nfn main() -> i32\n    0\n",
              "unit.ritz:1:9:", "`String`"),
}

# The ticket's program: one error, at the type (AGAST #3932), not also at the
# literal (#3347) or the member.
TICKET = ('pub fn main() -> i32\n    let s: String = "abc"\n'
          '    let n: i64 = s.len\n    print("{n}\\n")\n    0\n')


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
    # 1, a refusal: not 0 (accepted) and not a signal (a crash after the error).
    assert proc.returncode == 1, f"{compiler} exited {proc.returncode}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR"
    # A located line counts though it lacks "error": ritz0 prints each slot
    # error after the first on a line of its own.
    return [ln for ln in out.splitlines()
            if "error" in ln.lower() or re.search(r"unit\.ritz:\d+:\d+:", ln)]


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
    assert "unit.ritz:2:12:" in errors[0] and "unknown type `String`" in errors[0], errors


# Declared types the rule must leave alone (the gate's rzsh build, #3404): a
# global generic instance, whose bare name `Vec` monomorph turns into an
# instance, and a local one.  ritz0's own rule; ritz1's reads only locals.
ACCEPTED = {
    # A module-level `Vec` is refused: a value with Drop is never dropped
    # (§13.6, AGAST #2159). The global holds a pointer; its declared type
    # still names the generic instance this row is about.
    "global_generic": ("import ritzlib.gvec\nimport ritzlib.memory\n\nvar g: *Vec<i64> = null\n\n"
                       "fn main() -> i32\n    g = malloc(sizeof(Vec<i64>)) as *Vec<i64>\n"
                       "    *g = vec_new<i64>()\n    let n: i64 = g.len\n    0\n"),
    "local_generic": ("import ritzlib.gvec\n\nfn main() -> i32\n"
                      "    var v: Vec<i64> = vec_new<i64>()\n    let n: i64 = v.len\n    0\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_member_on_a_declared_generic_instance_compiles(tmp_path, name):
    src = tmp_path / "unit.ritz"
    src.write_text(ACCEPTED[name])
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    assert proc.returncode == 0 and ll.exists(), proc.stdout + proc.stderr
