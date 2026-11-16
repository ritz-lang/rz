"""AGAST #1872: the `\\xNN` and `\\e` escapes, in ritz0 and ritz1 alike.

LANGUAGE_SPEC listed only `\\n \\t \\r \\\\ \\" \\' \\0` (plus `\\{` `\\}`), so
code that needed ESC built it by hand: ritzunit's reporter stored byte 27
into a buffer ("Ritz doesn't support \\x escape sequences") and rzsh's line
editor assembled `ESC [ n D` byte by byte, three times over.

The rule, in every literal kind ("...", c"...", '.'):

  * `\\e` is ESC, 0x1B.
  * `\\x` takes exactly two hex digits, either case, and gives that byte.
    The byte must be ASCII (at most `\\x7F`): a literal is UTF-8 text, so a
    lone `\\xC3` would be half a character. Write a non-ASCII character as
    itself. (Rust's `str` literals draw the same line.)
  * Anything else after `\\x` is a located error at the `x`, the column every
    other bad escape reports.

Every case runs on both compilers: ritz0 is the oracle, and ritz1 must give
the same bytes, or the same message at the same line:col.
"""

import pytest

from test_format_into import _assert_parity
from test_ritz1_builtin_struct_shadow import _run
from test_ritz1_unknown_escape import _compile

pytestmark = pytest.mark.integration

EXPECTED = 42

# --- accepted: each returns 42 iff every escape cooked to the right byte ---
ACCEPT = {
    "cstr": """\
pub fn main() -> i32
    let s: *u8 = c"\\e[\\x41\\x7f\\x7F\\x0a\\x00z"
    if *s != 27
        return 1
    if *(s + 1) != 91
        return 2
    if *(s + 2) != 65
        return 3
    if *(s + 3) != 127
        return 4
    if *(s + 4) != 127
        return 5
    if *(s + 5) != 10
        return 6
    if *(s + 6) != 0
        return 7
    if *(s + 7) != 122
        return 8
    42
""",
    # \\x00 inside a StrView is counted: len is the cooked byte count.
    "str": """\
import ritzlib.strview

pub fn main() -> i32
    let s: StrView = "\\e[2J\\x1b\\x00\\x5c\\x22"
    if s.len != 8
        return 1
    let p: *u8 = s.ptr
    if *p != 27
        return 2
    if *(p + 4) != 27
        return 3
    if *(p + 5) != 0
        return 4
    if *(p + 6) != 92
        return 5
    if *(p + 7) != 34
        return 6
    42
""",
    "char": """\
pub fn main() -> i32
    if '\\e' != 27
        return 1
    if '\\x1B' != 27
        return 2
    if '\\x41' != 65
        return 3
    if '\\x00' != 0
        return 4
    if '\\x7f' != 127
        return 5
    if '\\x27' != 39
        return 6
    42
""",
}


@pytest.mark.parametrize("name", sorted(ACCEPT))
def test_ritz0_accepts_hex_and_esc(tmp_path, name):
    assert _run("ritz0", tmp_path, name, ACCEPT[name]) == EXPECTED


@pytest.mark.parametrize("name", sorted(ACCEPT))
def test_ritz1_accepts_hex_and_esc(ritz1_bin, tmp_path, name):
    assert _run("ritz1", tmp_path, name, ACCEPT[name]) == EXPECTED


def test_print_literal_cooks_hex_and_esc(ritz1_bin, tmp_path):
    """print splits a placeholder literal from its RAW text and re-cooks it
    (ritz1: emitter_print.ritz), so the escapes must decode there too."""
    program = (
        "fn main() -> i32\n"
        "    let n: i32 = 7\n"
        '    print("\\e[{n}D\\x41\\e[0m\\n")\n'
        '    print("\\e\\x42\\n")\n'
        "    0\n"
    )
    _assert_parity(tmp_path, "print_hex", program, b"\x1b[7DA\x1b[0m\n\x1bB\n")


# --- rejected: (literal type, literal text, message) ------------------------
DIGITS = "Hex escape '\\x' needs exactly two hex digits"
REJECT = {
    "cstr_z": ("*u8", 'c"\\xZ1"', DIGITS),
    "cstr_one": ("*u8", 'c"\\x1"', DIGITS),
    "cstr_bare": ("*u8", 'c"a\\x"', DIGITS),
    "cstr_g": ("*u8", 'c"\\x1g"', DIGITS),
    "str_z": ("StrView", '"\\xZ"', DIGITS),
    "str_one": ("StrView", '"ab\\x1"', DIGITS),
    "str_space": ("StrView", '"\\x 41"', DIGITS),
    "char_one": ("u8", "'\\x1'", DIGITS),
    "char_z": ("u8", "'\\xZZ'", DIGITS),
    "char_bare": ("u8", "'\\x'", DIGITS),
    # the #1978 repro: half of the UTF-8 encoding of 'Ã'
    "cstr_c3": ("*u8", 'c"a\\xC3b"', "Hex escape '\\xC3' is above '\\x7F'"),
    "str_80": ("StrView", '"\\x80"', "Hex escape '\\x80' is above '\\x7F'"),
    "char_ff": ("u8", "'\\xff'", "Hex escape '\\xff' is above '\\x7F'"),
}


def _reject_program(ty: str, lit: str) -> str:
    return f"pub fn main() -> i32\n    let v: {ty} = {lit}\n    0\n"


def _col(ty: str, lit: str) -> int:
    """1-based column of the `x`: the escape char, where ritz0 reports."""
    return len(f"    let v: {ty} = ") + lit.index("\\") + 2


@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", sorted(REJECT))
def test_bad_hex_escape_is_located_error(ritz1_bin, tmp_path, name, compiler):
    ty, lit, msg = REJECT[name]
    res, ll = _compile(compiler, tmp_path, name, _reject_program(ty, lit))
    out = res.stdout + res.stderr
    assert res.returncode != 0, f"{compiler} accepted {lit!r}:\n{out[-2000:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {lit!r}"
    assert msg in out, out[-2000:]
    assert f"{name}_{compiler}.ritz:2:{_col(ty, lit)}:" in out, out[-2000:]
