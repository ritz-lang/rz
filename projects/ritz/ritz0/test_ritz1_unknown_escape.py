"""Regression tests for AGAST #1978: ritz1 must reject an escape sequence
that the language does not define, exactly as ritz0 does.

    let s: *u8 = c"a\\xC3b"

ritz0: ``Lexer error: b.ritz:2:22: Unknown escape sequence '\\x'``
ritz1 (before): compiled, cooking the literal to ``axC3b`` -- the backslash of
an unknown escape was dropped and the next byte kept, so the program saw 'x'.

ROOT CAUSE: every escape-cooking site in ritz1 (lexer_nfa.ritz's plain-string
scanner, the c"..." scanners, and expr_char for char literals) ended its
if/else chain with "unknown escape -> emit the literal char".

The fix routes all of them through one table (lexer_cook_escape) holding the
escapes ritz0 accepts, and turns anything else into a located, fatal lexer
error.  `\\xNN` is deliberately NOT added: LANGUAGE_SPEC lists the escapes and
widening it is a LARB decision.

The accepted sets are ritz0's, per literal kind:

  * ``"..."`` (StrView) and ``'.'`` (char): ``\\n \\t \\r \\\\ \\" \\' \\0 \\{ \\}``
  * ``c"..."``: the same minus ``\\{`` and ``\\}`` (no interpolation there)

Every one of them is a must-still-compile control below, checked by value:
ritz1 previously got ``\\'`` (and ``\\"`` in chars, ``\\{``/``\\}`` everywhere)
right only *by accident*, via the fallback this ticket removes.
"""

import os
import subprocess

import pytest

from ritz0_inproc import run_ritz0
from test_ritz1_builtin_struct_shadow import RITZ1_BIN, RITZ_ROOT, _run

pytestmark = pytest.mark.integration

EXPECTED = 42

# --- rejected: (literal kind, source text of the literal) -------------------
# The body must lex the literal; using it in a typed `let` keeps every case a
# complete, otherwise-valid program, so the escape is the only error.
REJECT = {
    # the ticket repro
    "cstr_x": ("*u8", 'c"a\\xC3b"'),
    "cstr_q": ("*u8", 'c"a\\qb"'),
    "cstr_a": ("*u8", 'c"\\a"'),
    "cstr_u": ("*u8", 'c"\\u0041"'),
    "cstr_1": ("*u8", 'c"\\1"'),
    "cstr_space": ("*u8", 'c"a\\ b"'),
    # braces are only escapes where interpolation exists
    "cstr_lbrace": ("*u8", 'c"\\{"'),
    "cstr_rbrace": ("*u8", 'c"\\}"'),
    "str_x": ("StrView", '"a\\xC3b"'),
    "str_q": ("StrView", '"a\\qb"'),
    "str_e": ("StrView", '"\\e"'),
    "str_1": ("StrView", '"\\1"'),
    "char_x": ("u8", "'\\x'"),
    "char_q": ("u8", "'\\q'"),
    "char_a": ("u8", "'\\a'"),
    "char_1": ("u8", "'\\1'"),
}


def _reject_program(ty: str, lit: str) -> str:
    return f"pub fn main() -> i32\n    let v: {ty} = {lit}\n    0\n"


# --- accepted: each program returns 42 iff every escape cooked correctly ---
ACCEPT = {
    "cstr_all": """\
pub fn main() -> i32
    let s: *u8 = c"\\n\\t\\r\\\\\\"\\'x\\0y"
    if *s != 10
        return 1
    if *(s + 1) != 9
        return 2
    if *(s + 2) != 13
        return 3
    if *(s + 3) != 92
        return 4
    if *(s + 4) != 34
        return 5
    if *(s + 5) != 39
        return 6
    if *(s + 6) != 120
        return 7
    if *(s + 7) != 0
        return 8
    if *(s + 8) != 121
        return 9
    42
""",
    "cstr_raw_braces": """\
pub fn main() -> i32
    let s: *u8 = c"{}"
    if *s != 123
        return 1
    if *(s + 1) != 125
        return 2
    42
""",
    "str_all": """\
import ritzlib.strview

pub fn main() -> i32
    let s: StrView = "\\n\\t\\r\\\\\\"\\'\\0\\{\\}"
    if s.len != 9
        return 1
    let p: *u8 = s.ptr
    if *p != 10
        return 2
    if *(p + 1) != 9
        return 3
    if *(p + 2) != 13
        return 4
    if *(p + 3) != 92
        return 5
    if *(p + 4) != 34
        return 6
    if *(p + 5) != 39
        return 7
    if *(p + 6) != 0
        return 8
    if *(p + 7) != 123
        return 9
    if *(p + 8) != 125
        return 10
    42
""",
    "char_all": """\
pub fn main() -> i32
    if '\\n' != 10
        return 1
    if '\\t' != 9
        return 2
    if '\\r' != 13
        return 3
    if '\\\\' != 92
        return 4
    if '\\"' != 34
        return 5
    if '\\'' != 39
        return 6
    if '\\0' != 0
        return 7
    if '\\{' != 123
        return 8
    if '\\}' != 125
        return 9
    if 'x' != 120
        return 10
    42
""",
}


def _compile(compiler: str, tmp_path, name: str, program: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        res = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        res = subprocess.run(
            [str(RITZ1_BIN), str(src), "-o", str(ll)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
    return res, ll


@pytest.mark.parametrize("name", sorted(REJECT))
def test_ritz0_oracle_rejects(tmp_path, name):
    res, _ = _compile("ritz0", tmp_path, name, _reject_program(*REJECT[name]))
    assert res.returncode != 0
    assert "Unknown escape sequence" in res.stdout + res.stderr


@pytest.mark.parametrize("name", sorted(REJECT))
def test_ritz1_rejects_unknown_escape(ritz1_bin, tmp_path, name):
    ty, lit = REJECT[name]
    res, ll = _compile("ritz1", tmp_path, name, _reject_program(ty, lit))
    out = res.stdout + res.stderr
    assert res.returncode != 0, f"ritz1 accepted {lit!r}:\n{out[-2000:]}"
    assert not ll.exists(), f"ritz1 wrote IR for {lit!r}"
    # Names the escape, at the line:col ritz0 reports: the escape char itself.
    esc = lit[lit.index("\\") : lit.index("\\") + 2]
    assert f"Unknown escape sequence '{esc}'" in out, out[-2000:]
    col = len(f"    let v: {ty} = ") + lit.index("\\") + 2
    assert f"{name}_ritz1.ritz:2:{col}:" in out, out[-2000:]


@pytest.mark.parametrize("name", sorted(REJECT))
def test_ritz0_oracle_location(tmp_path, name):
    """The column the ritz1 test expects is the one ritz0 reports."""
    ty, lit = REJECT[name]
    res, _ = _compile("ritz0", tmp_path, name, _reject_program(ty, lit))
    col = len(f"    let v: {ty} = ") + lit.index("\\") + 2
    assert f"{name}_ritz0.ritz:2:{col}:" in res.stdout + res.stderr


@pytest.mark.parametrize("name", sorted(ACCEPT))
def test_ritz0_oracle_accepts(tmp_path, name):
    assert _run("ritz0", tmp_path, name, ACCEPT[name]) == EXPECTED


@pytest.mark.parametrize("name", sorted(ACCEPT))
def test_ritz1_accepts_known_escapes(ritz1_bin, tmp_path, name):
    assert _run("ritz1", tmp_path, name, ACCEPT[name]) == EXPECTED
