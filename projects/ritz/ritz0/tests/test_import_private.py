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

RITZ_ROOT = Path(__file__).resolve().parents[2]
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

impl CS
    pub fn make() -> CS
        CS { x: 3 }

    pub fn get(self: @CS) -> i32
        self.x

pub enum CE
    A
    B(i32)

pub type CA = i32
"""

B = """\
{pub}import c

pub fn b_val() -> i32
    c_val()

pub fn b_cs() -> CS
    CS {{ x: 4 }}
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


# sizeof's operand is a type, and a use of its name (#3981): bare, and as an
# array element type. (No compiler folds sizeof in a const initialiser, and an
# array length can't hold one, so a function body is the only place.)
MAIN_SIZEOF = """\
import b

pub fn main() -> i32
    if sizeof(CS) <= 0
        return 9
    sizeof([2]CS) as i32
"""

# Not a hidden name but no name at all: an error, not a guess at its size
# (valet's test once said sizeof "falls back to 8" for one).
MAIN_SIZEOF_UNKNOWN = """\
import b

pub fn main() -> i32
    sizeof(Nope) as i32
"""

# An enum's name is a use in an annotation, at `E.V`, and as a pattern's
# qualifier, bare or with a binding (#3907).
MAIN_ENUM = """\
import b

pub fn main() -> i32
    let e: CE = CE.A
    match e
        CE.A => 1
        CE.B(n) => n
"""

MAIN_ALIAS = """\
import b

pub fn main() -> i32
    let a: CA = 2
    a
"""

# `CS.make()` names CS; `CS_make()` is the same method by its mangled name, so
# it is hidden as CS is (#3907).
MAIN_STATIC = """\
import b

pub fn main() -> i32
    CS.make().x + CS_make().x
"""

# A method on a value names no item: the value's type is checked where it is
# written, and here it is written in b.  Method syntax reaches no free fn
# (LANGUAGE_SPEC §9.4, #3244), so there is no UFCS use of a hidden fn (#3907).
MAIN_METHOD = """\
import b

pub fn main() -> i32
    b_cs().get()
"""

MAIN_TYPES = """\
import b

pub fn main() -> i32
    let e: CE = CE.B(2)
    let a: CA = match e
        CE.A => 1
        CE.B(n) => n
    a + CS.make().x + CS_make().get()
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
        for prefix in ("Error: ", "Compiler error: ", "error: "):
            line = line.removeprefix(prefix)
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


@pytest.mark.parametrize("compiler", COMPILERS)
def test_sizeof_of_a_hidden_type_is_undefined(tmp_path, compiler):
    """#3981: ritz0 let `sizeof(CS)` through where it refused `let s: CS`."""
    rc, errors = _compile(compiler, tmp_path, False, MAIN_SIZEOF)
    assert rc != 0
    assert errors[:1] == [_hidden(4, 15, "CS")], errors
    assert all("`CS` is undefined (#3891)" in e for e in errors), errors


@pytest.mark.parametrize("compiler", COMPILERS)
def test_sizeof_through_a_pub_import_compiles(tmp_path, compiler):
    rc, errors = _compile(compiler, tmp_path, True, MAIN_SIZEOF)
    assert (rc, errors) == (0, [])


@pytest.mark.parametrize("compiler", COMPILERS)
def test_sizeof_of_an_unknown_name_is_an_error(tmp_path, compiler):
    rc, errors = _compile(compiler, tmp_path, False, MAIN_SIZEOF_UNKNOWN)
    assert rc != 0
    assert errors == ["main.ritz:4:12: sizeof: unknown type or value `Nope`"]


def _lines(errors, name):
    """The lines errors are on, after checking each is `name`'s (ritz1
    locates an annotation's at its `let`, ritz0 at the type)."""
    assert errors and all(f"`{name}` is undefined (#3891)" in e
                          for e in errors), errors
    return sorted({int(e.split(":")[1]) for e in errors})


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_enum_through_a_plain_import_is_undefined(tmp_path, compiler):
    rc, errors = _compile(compiler, tmp_path, False, MAIN_ENUM)
    assert rc != 0
    assert _lines(errors, "CE") == [4, 6, 7]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_type_alias_through_a_plain_import_is_undefined(tmp_path, compiler):
    rc, errors = _compile(compiler, tmp_path, False, MAIN_ALIAS)
    assert rc != 0
    assert _lines(errors, "CA") == [4]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_static_call_on_a_hidden_type_is_undefined(tmp_path, compiler):
    rc, errors = _compile(compiler, tmp_path, False, MAIN_STATIC)
    assert rc != 0
    assert errors == [_hidden(4, 5, "CS"), _hidden(4, 19, "CS_make")]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_method_on_a_value_is_not_a_use(tmp_path, compiler):
    rc, errors = _compile(compiler, tmp_path, False, MAIN_METHOD)
    assert (rc, errors) == (0, [])


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_pub_import_passes_enums_aliases_and_methods_on(tmp_path, compiler):
    rc, errors = _compile(compiler, tmp_path, True, MAIN_TYPES)
    assert (rc, errors) == (0, [])
