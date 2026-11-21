"""AGAST #3419 (LARB R45a, #3413 step 3b): ritz1 and ritz1_selfhosted refuse a
call to a fn or method declared without `pub` in another file, located at the
call, in ritz0's words (#3418, test_private_fn_cross_file.py):

    main.ritz:5:5: error: `helper` is private to a.ritz; mark it `pub` (#3413)
    <dir>/a.ritz:8:1: note: `helper` is declared here

Same rows and scope as ritz0's: free fns, method calls `p.get()` (and the
static `P.make()`), the mangled `P_get(p)`; not `extern fn`, `fn .. = extern`,
monomorph instances, a generated `E.from`, nor a call within one file.

ritz1 reports every error where ritz0 stops at its first, so a program with
several private calls names each.
"""

import os
import subprocess
from pathlib import Path

import pytest
from test_private_fn_cross_file import (
    A_DECL,
    A_ENUM,
    A_EXTERN,
    A_GENERIC,
    A_GENERIC_CALLER,
    A_INTERNAL,
    A_PRIVATE,
    A_PUB,
    MAIN_API,
    MAIN_CALLS,
    MAIN_ENUM,
    MAIN_EXTERN,
    MAIN_GENERIC,
    MAIN_TWICE,
    ONE_CALL,
    SAME_FILE,
)

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ1S = ["ritz1", "ritz1_selfhosted"]


def _ritz1(compiler, tmp_path, src, env_extra=None):
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    # An empty store of its own: an interface text another run stored for
    # a.ritz's bytes would be read instead of a.ritz (test_from_interface_text).
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}",
               RITZ_CACHE_DIR=str(tmp_path / "cas"), **(env_extra or {}))
    ll = tmp_path / f"{Path(src).stem}.ll"
    proc = subprocess.run([str(binary), src, "-o", str(ll)], cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=120,
                          check=False)
    return proc, ll


def _run(compiler, tmp_path, a_src, main_src, env_extra=None):
    (tmp_path / "a.ritz").write_text(a_src)
    (tmp_path / "main.ritz").write_text(main_src)
    return _ritz1(compiler, tmp_path, "main.ritz", env_extra)


def _refused(compiler, tmp_path, a_src, main_src, env_extra=None):
    """The compile fails; its diagnostic lines (errors and notes)."""
    proc, ll = _run(compiler, tmp_path, a_src, main_src, env_extra)
    assert proc.returncode != 0, proc.stderr
    assert not ll.exists()
    return [l for l in proc.stderr.splitlines()
            if "private to" in l or ": note: " in l]


def _error(line, col, display):
    return (f"main.ritz:{line}:{col}: error: `{display}` is private to a.ritz; "
            f"mark it `pub` (#3413)")


def _note(tmp_path, decl, display):
    return f"{tmp_path / 'a.ritz'}:{decl}: note: `{display}` is declared here"


# A static method (no `self`): `P.get(p)` is refused on its own account.
A_STATIC = """\
pub struct P
    v: i32

impl P
    fn make() -> i32
        3
"""


@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("call,display,col,decl", [
    pytest.param("helper()", "helper", 5, "8:1", id="free_fn"),
    pytest.param("p.get()", "P.get", 7, "5:5", id="method"),
    pytest.param("P_get(p)", "P_get", 5, "5:5", id="mangled_method"),
])
def test_cross_file_private_call_is_a_located_error(tmp_path, compiler, call,
                                                    display, col, decl):
    lines = _refused(compiler, tmp_path, A_PRIVATE, ONE_CALL.format(call=call))
    assert lines == [_error(5, col, display), _note(tmp_path, decl, display)]


@pytest.mark.parametrize("compiler", RITZ1S)
def test_a_static_method_call_is_a_located_error(tmp_path, compiler):
    lines = _refused(compiler, tmp_path, A_STATIC, ONE_CALL.format(call="P.make()"))
    assert lines == [_error(5, 7, "P.make"), _note(tmp_path, "5:5", "P.make")]


@pytest.mark.parametrize("compiler", RITZ1S)
def test_every_private_call_is_an_error(tmp_path, compiler):
    """ritz1 goes on after an error: each of the three calls is named."""
    lines = _refused(compiler, tmp_path, A_PRIVATE, MAIN_CALLS)
    assert lines == [
        _error(5, 5, "helper"), _note(tmp_path, "8:1", "helper"),
        _error(5, 18, "P.get"), _note(tmp_path, "5:5", "P.get"),
        _error(5, 26, "P_get"), _note(tmp_path, "5:5", "P_get"),
    ]


@pytest.mark.parametrize("compiler", RITZ1S)
def test_a_deferred_private_call_is_one_error(tmp_path, compiler):
    """A `defer` is emitted at each exit; its call is refused once."""
    a = "fn helper()\n    return\n"
    main = """\
import a

pub fn main() -> i32
    defer helper()
    if 1 == 2
        return 1
    0
"""
    lines = _refused(compiler, tmp_path, a, main)
    assert lines == [_error(4, 11, "helper"), _note(tmp_path, "1:1", "helper")]


@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("a_src,main_src", [
    pytest.param(A_PUB, MAIN_CALLS, id="pub"),
    pytest.param(A_STATIC.replace("fn make", "pub fn make"),
                 ONE_CALL.format(call="P.make()"), id="pub_static"),
    pytest.param("", SAME_FILE, id="same_file"),
    pytest.param(A_EXTERN, MAIN_EXTERN, id="extern_fn"),
    pytest.param(A_DECL, MAIN_EXTERN, id="decl_only_fn"),
    pytest.param(A_ENUM, MAIN_ENUM, id="generated_from"),
    pytest.param(A_GENERIC, MAIN_GENERIC, id="monomorph"),
    pytest.param(A_INTERNAL, MAIN_API, id="callee_file_own_helper"),
    pytest.param(A_GENERIC_CALLER, MAIN_TWICE, id="instance_calls_own_helper"),
])
def test_allowed(tmp_path, compiler, a_src, main_src):
    proc, ll = _run(compiler, tmp_path, a_src, main_src)
    assert proc.returncode == 0 and ll.exists(), proc.stderr
    assert "private to" not in proc.stderr


@pytest.mark.parametrize("compiler", RITZ1S)
def test_module_calling_its_own_private_fn_is_silent(tmp_path, compiler):
    """Compiling a.ritz itself: helper is called from its own file."""
    (tmp_path / "a.ritz").write_text(A_INTERNAL)
    proc, ll = _ritz1(compiler, tmp_path, "a.ritz")
    assert proc.returncode == 0 and ll.exists(), proc.stderr
    assert "private to" not in proc.stderr


@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("a_src,main_src,refused", [
    pytest.param(A_PRIVATE, ONE_CALL.format(call="helper()"), True,
                 id="stripped_private"),
    pytest.param(A_PUB, MAIN_CALLS, False, id="stripped_pub"),
    pytest.param(A_DECL, MAIN_EXTERN, False, id="written_decl"),
])
def test_from_interface_text(tmp_path, compiler, a_src, main_src, refused):
    """An import read from ritz0's interface text (main.ritz load_and_parse)
    is held to the same rule.  The text turns every body it drops into a
    `fn .. = extern`; only one written so (#1900) goes unchecked."""
    import module_interface as mi
    tokens, module = mi._parse_with_tokens(a_src, "a.ritz")
    k = mi.text_key(a_src.encode())
    text = tmp_path / "cas" / "objects" / k[:2] / f"{k}.{mi.TEXT_EXT}"
    text.parent.mkdir(parents=True)
    text.write_text(mi.interface_text(a_src, tokens, module))
    log = tmp_path / "parsed.log"
    env = {"RITZ1_PARSE_LOG": str(log)}
    if refused:
        lines = _refused(compiler, tmp_path, a_src, main_src, env)
        assert lines == [_error(5, 5, "helper"), _note(tmp_path, "8:1", "helper")]
    else:
        proc, ll = _run(compiler, tmp_path, a_src, main_src, env)
        assert proc.returncode == 0 and ll.exists(), proc.stderr
    assert "a.ritz" not in log.read_text(), "a.ritz was parsed, not its text"
