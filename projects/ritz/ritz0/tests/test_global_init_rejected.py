"""A global `var` initializer no compiler can lower is a located error (AGAST #3027).

ritz0's `_emit_global_var` ended its initializer chain in a bare Python
`ValueError` ("Unsupported global var initializer", "Complex unary op
initializer not supported", ...): a traceback, no file:line:col, for
`var g: i32 = 1 + 2` or `var g: i32 = true`, both of which ritz1 refuses with a
located error.

Every case runs through ritz0, ritz1 and ritz1_selfhosted.  The message is
ritz1's, and all three locate it at the initializer, not at the global's
declaration (AGAST #3043: ritz1 said column 1).  Accepted forms (`~0`, `-~2`) are run in test_ritz1_global_var_init.py.
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

_MAIN = "fn main() -> i32\n    0\n"
_NON_CONST = "global 'g' has a non-constant initializer"
_B2I = "cannot use bool as an integer: write `b as i32`"
_NOT_FLOAT = "global 'g' is not a float type but has a float initializer"

# name -> (source, line, column, message prefix)
REJECTED = {
    "bool_into_int": ("var g: i32 = true\n" + _MAIN, 1, 14, _B2I),
    "not_of_a_global": ("var x: bool\nvar g: bool = not x\n" + _MAIN, 2, 15, _NON_CONST),
    "neg_of_a_global": ("var x: i32\nvar g: i32 = -x\n" + _MAIN, 2, 14, _NON_CONST),
    "bit_not_of_a_global": ("var x: i32\nvar g: i32 = ~x\n" + _MAIN, 2, 14, _NON_CONST),
    # AGAST #1539: a char / float initializer folds, but only into a slot of
    # its kind.  ritz1 located the float misfits at column 1 until #3680.
    "float_into_int": ("var g: i32 = 1.5\n" + _MAIN, 1, 14, _NOT_FLOAT),
    "neg_float_into_int": ("var g: i64 = -0.5\n" + _MAIN, 1, 14, _NOT_FLOAT),
    "float_cast_into_int": ("var g: i64 = 1.5 as i64\n" + _MAIN, 1, 14, _NOT_FLOAT),
    "float_into_pointer": ("var g: *u8 = 1.5\n" + _MAIN, 1, 14, _NOT_FLOAT),
    "float_into_bool": ("var g: bool = 1.5\n" + _MAIN, 1, 15, "cannot use a float as bool"),
    "char_into_bool": ("var g: bool = 'A'\n" + _MAIN, 1, 15, "cannot use an integer as bool"),
    "bit_not_float": ("var g: f64 = ~1.5\n" + _MAIN, 1, 14, _NON_CONST),
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
                              env=env, capture_output=True, text=True, timeout=300)
    return proc, ll


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REJECTED))
def test_an_unlowerable_global_initializer_is_a_located_error(request, tmp_path, compiler, name):
    source, line, col, message = REJECTED[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    assert "Traceback" not in out and "ValueError" not in out, f"{compiler}, {name}:\n{out[-1500:]}"
    hits = re.findall(rf"unit\.ritz:{line}:{col}: (?:error: )?{re.escape(message)}", out)
    assert len(hits) == 1, f"{compiler}, {name}: want one {message!r} at {line}:{col}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
def test_ritz0_null_into_an_integer_global_is_a_located_error(request, tmp_path):
    """ritz0-only: ritz1 stores `null` in an integer global as 0.  ritz0 refuses
    it, but located, not as the bare ValueError it raised before #3027."""
    proc, ll = _compile(request, "ritz0", tmp_path, "var g: i32 = null\n" + _MAIN)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0 and "ValueError" not in out, out[-1500:]
    assert re.search(r"unit\.ritz:1:14: (?:error: )?global 'g' .*null", out), out[-1500:]
    assert not ll.exists()


# LARB R60 (§4.3): arithmetic and a float const are constant initialisers.
# ritz0 lowered them since #3479; ritz1 and ritz1_selfhosted since #3480.
# test_const_init_r60.py runs their values on every compiler.
# name -> (source, line, column)
_R60_FORMS = {
    "binary": ("var g: i32 = 1 + 2\n" + _MAIN, 1, 14),
    "cast_of_binary": ("var g: i64 = (1 + 2) as i64\n" + _MAIN, 1, 15),
    "float_const": ("const F: f64 = 1.5\nvar g: f64 = F\n" + _MAIN, 2, 14),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(_R60_FORMS))
def test_r60_initializer_is_accepted_by_every_compiler(request, tmp_path, compiler, name):
    source, line, col = _R60_FORMS[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and ll.exists(), f"{compiler} refused {name}:\n{out[-1500:]}"


# `null` fits a pointer slot only.  ritz0's words, at the initializer under
# every compiler since LARB R60 (#3480); ritz1 used to say "is a float type
# but has a null initializer" for an f64.  (Non-zero f32 is lowered now too.)
# name -> (source, line, column, message)
_RITZ1_ONLY = {
    "null_into_float": ("var g: f64 = null\n" + _MAIN, 1, 14,
                        "global 'g' is not a pointer but has a null initializer"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(_RITZ1_ONLY))
def test_ritz1_a_misfit_float_global_is_located_at_the_initializer(request, tmp_path, compiler, name):
    source, line, col, message = _RITZ1_ONLY[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    hits = re.findall(rf"unit\.ritz:{line}:{col}: (?:error: )?{re.escape(message)}", out)
    assert len(hits) == 1, f"{compiler}, {name}: want one {message!r} at {line}:{col}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


# LARB R38 (#3374): a global's type is written, never read off its initializer.
# name -> (source, line, column, message)
_UNTYPED = {
    "bool": ("var g = true\n" + _MAIN, 1, 7, "a global needs a type: write `var g: bool = ...`"),
    "int": ("var counter = 5\n" + _MAIN, 1, 13,
            "a global needs a type: write `var counter: i64 = ...`"),
    "unknown": ("var g = null\n" + _MAIN, 1, 7, "a global needs a type: write `var g: T = ...`"),
    "float": ("var g = 1.5\n" + _MAIN, 1, 7, "a global needs a type: write `var g: f64 = ...`"),
    "str": ('var g = "hi"\n' + _MAIN, 1, 7, "a global needs a type: write `var g: StrView = ...`"),
    "cstr": ('var g = c"hi"\n' + _MAIN, 1, 7, "a global needs a type: write `var g: *u8 = ...`"),
    "char": ("var g = 'A'\n" + _MAIN, 1, 7, "a global needs a type: write `var g: u8 = ...`"),
    "pub_neg_int": ("pub var g = -5\n" + _MAIN, 1, 11, "a global needs a type: write `var g: i64 = ...`"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(_UNTYPED))
def test_an_untyped_global_var_is_an_error_at_the_eq(request, tmp_path, compiler, name):
    """Every compiler, one message at the `=`.  ritz1 used to stop with a parse
    error ("unexpected '='", "cannot parse item starting at 'var g'"); its
    grammar now takes the untyped form and refuses it (#3375)."""
    source, line, col, message = _UNTYPED[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    assert "Traceback" not in out and "ValueError" not in out, out[-1500:]
    assert "cannot parse item" not in out and "unexpected" not in out, f"{compiler}, {name}:\n{out[-1500:]}"
    hits = re.findall(rf"unit\.ritz:{line}:{col}: (?:error: )?{re.escape(message)}", out)
    assert len(hits) == 1, f"{compiler}, {name}: want one {message!r} at {line}:{col}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("source", ["let g = true\n", "let g: bool = true\n"])
def test_a_module_level_let_is_refused(request, tmp_path, compiler, source):
    """No compiler has a module-level `let` (R38 names one; it isn't an item),
    so typed or not it stays a located refusal at the `let`, under one message:
    ritz0's since LARB R60 (#3479), ritz1's since #3480 (it was the parse error
    "cannot parse item starting at 'let g'")."""
    proc, ll = _compile(request, compiler, tmp_path, source + _MAIN)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, out[-1500:]
    assert "Traceback" not in out, out[-1500:]
    assert re.search(r"unit\.ritz:1:1: (?:error: )?there is no module-level `let`", out), out[-1500:]
    assert "Parse error" not in out, out[-1500:]
    assert not ll.exists()
