"""AGAST #3891: a plain `import` is private (LANGUAGE_SPEC §15.1, §15.4).

`import b` brings in what `b` declares and what `b` re-exports with `pub
import`; what `b` reaches only through its own plain `import c` is not
brought in (LARB R54's rule for what a module defines). A name used that way
is an error at the use, with a hint:

    main.ritz:4:15: `c_val` is undefined (#3891): it comes from `c`; import it, or have `b` `pub import` it

ritz0 adds a note at the declaration; ritz1 doesn't. The three-module chain:
main imports b, and b imports c. With b's `import c`, main sees none of c's
names. With b's `pub import c`, it sees them all. On all three compilers.
"""

import os
import subprocess
from pathlib import Path

import pytest
from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

C = """\
import ritzlib.option
import ritzlib.strview

pub const C_K: i32 = 5

pub fn c_val() -> i32
    7

pub struct CS
    x: i32
"""

B = """\
{pub}import c

pub fn b_val() -> i32
    c_val()
"""

MAIN_FN = """\
import b

pub fn main() -> i32
    b_val() + c_val() + C_K
"""

MAIN_STRUCT = """\
import b

pub fn main() -> i32
    let s: CS = CS { x: 1 }
    s.x
"""

MAIN_ALL = """\
import b

pub fn main() -> i32
    let s: CS = CS { x: 1 }
    b_val() + c_val() + C_K + s.x
"""

# A local of a hidden name's name is the local, and a built-in (`Option`,
# `StrView`) is everywhere, even where only c's imports declare it.
MAIN_NOT_HIDDEN = """\
import b

pub fn main() -> i32
    let c_val: i32 = 2
    let o: Option<i32> = Some(1)
    let sv: StrView = "ab"
    b_val() + c_val + sv.len as i32
"""


def _compile(compiler, tmp_path, b_pub, main_src):
    """Compile main.ritz over the chain; (exit code, error lines), each line
    as `main.ritz:L:C: message`, whichever compiler's prefix it had."""
    (tmp_path / "c.ritz").write_text(C)
    (tmp_path / "b.ritz").write_text(B.format(pub="pub " if b_pub else ""))
    (tmp_path / "main.ritz").write_text(main_src)
    ll = tmp_path / "main.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}",
               RITZ_CACHE_DIR=str(tmp_path / "cas"))
    if compiler == "ritz0":
        proc = run_ritz0(["main.ritz", "-o", str(ll)], cwd=tmp_path, env=env,
                         timeout=300)
    else:
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries first.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), "main.ritz", "-o", str(ll)],
                              cwd=tmp_path, env=env, capture_output=True,
                              text=True, timeout=120, check=False)
    errors = []
    for line in proc.stderr.splitlines():
        line = line.removeprefix("Error: ")
        if line.startswith("main.ritz:"):
            errors.append(line.replace(": error: ", ": ", 1))
    return proc.returncode, errors


def _hidden(line, col, name):
    return (f"main.ritz:{line}:{col}: `{name}` is undefined (#3891): it comes "
            f"from `c`; import it, or have `b` `pub import` it")


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_plain_import_does_not_pass_its_names_on(tmp_path, compiler):
    rc, errors = _compile(compiler, tmp_path, False, MAIN_FN)
    assert rc != 0
    assert errors == [_hidden(4, 15, "c_val"), _hidden(4, 25, "C_K")]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_struct_through_a_plain_import_is_undefined(tmp_path, compiler):
    """The annotation and the literal are both uses (ritz1 locates the
    annotation's at its `let`)."""
    rc, errors = _compile(compiler, tmp_path, False, MAIN_STRUCT)
    assert rc != 0
    assert errors and all(e.startswith("main.ritz:4:") and "`CS` is undefined" in e
                          for e in errors), errors


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_pub_import_passes_its_names_on(tmp_path, compiler):
    rc, errors = _compile(compiler, tmp_path, True, MAIN_ALL)
    assert (rc, errors) == (0, [])


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_local_or_a_builtin_is_not_hidden(tmp_path, compiler):
    rc, errors = _compile(compiler, tmp_path, False, MAIN_NOT_HIDDEN)
    assert (rc, errors) == (0, [])
