"""Regression tests for AGAST #4245: an integer literal's type suffix (`1u32`)
types the literal on ritz1, as it does on ritz0.

ritz0 reads `1u32` as `1 as u32` (parser._apply_literal_suffix). ritz1's lexer
absorbed the suffix (AGAST #107) and parse_int ignored it, so `1u32` was a
bare literal and `let p = 1u32` an i64 local. Its narrowing checks then
refused `take_u32(p)` (test_ritz1_implicit_narrowing_slots.py holds those
rows); here the suffix must also type the arithmetic the local feeds. Before
the fix each FORMS row computed in i64 and returned 1.

ritz0 is the oracle: each expected exit status is checked against it too.
"""

import pytest

from test_ritz1_move_param import _compile, _run

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# name -> (program, expected exit status)
FORMS = {
    # A u8 local wraps at 256: 200 + 100 is 44, not 300.
    "u8_local_wraps": ("""\
pub fn main() -> i32
    let a = 200u8
    let b = a + 100
    if b < 100
        return 7
    return 1
""", 7),
    # An i8 local is signed at 8 bits: 127 + 1 is -128.
    "i8_local_wraps": ("""\
pub fn main() -> i32
    let a = 127i8
    let b = a + 1
    if b < 0
        return 6
    return 1
""", 6),
    # A u32 local wraps below 0 and compares unsigned.
    "u32_local_wraps": ("""\
pub fn main() -> i32
    let a = 0u32
    let b = a - 1
    if b == 4294967295
        return 5
    return 1
""", 5),
    # A hex literal takes its suffix too.
    "hex_u8": ("""\
pub fn main() -> i32
    let a = 0xFFu8
    let b = a + 1
    if b == 0
        return 4
    return 1
""", 4),
}

# Controls that worked before the fix and must still work.
CONTROLS = {
    "unsuffixed_is_i64": ("""\
pub fn main() -> i32
    let a = 200
    let b = a + 100
    if b == 300
        return 3
    return 1
""", 3),
    "usize_suffix": ("""\
pub fn main() -> i32
    let n = 3usize
    return n as i32
""", 3),
    "neg_i32_suffix": ("""\
pub fn main() -> i32
    let a = -2i32
    return (a + 4) as i32
""", 2),
}


# AGAST #4273: a suffix is lowercase only (LANGUAGE_SPEC §2.6). ritz0's
# NUMBER_SUFFIXES has no `U`/`I` form, so `1U32` lexes as `1` and the
# identifier `U32`, and the program is refused downstream at the `U`; ritz1's
# lexer took `[uUiI]` and compiled it. Each must fail on all three at the
# suffix's column, naming the stray identifier, in one wording: a second
# statement on the line is "unexpected 'U32'" everywhere (AGAST #4283).
# name -> (program, "line:col", message fragment)
UPPERCASE = {
    "upper_u32": ("pub fn main() -> i32\n    let a = 1U32\n    return 0\n",
                  "2:14", "unexpected 'U32'"),
    "upper_i8_hex": ("pub fn main() -> i32\n    let a = 0xFFI8\n    return 0\n",
                     "2:17", "unexpected 'I8'"),
    "upper_usize": ("pub fn main() -> i32\n    let a = 3Usize\n    return 0\n",
                    "2:14", "unexpected 'Usize'"),
    "upper_i64_arg": ("fn f(x: i64) -> i64\n    x\n\npub fn main() -> i32\n"
                      "    f(2I64) as i32\n",
                      "5:8", ""),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(UPPERCASE))
def test_uppercase_suffix_refused(request, tmp_path, compiler, name):
    """AGAST #4273. Before the fix ritz1 compiled each."""
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    program, where, fragment = UPPERCASE[name]
    comp, _ = _compile(compiler, tmp_path, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} {name} compiled:\n{out[-2000:]}"
    assert f"main.ritz:{where}:" in out, f"{compiler} {name}: not at {where}:\n{out[-2000:]}"
    assert fragment in out, f"{compiler} {name}: no {fragment!r}:\n{out[-2000:]}"


def _check(request, tmp_path, compiler, table, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    program, expected = table[name]
    rc = _run(compiler, tmp_path, program)
    assert rc == expected, f"{compiler} {name}: exit {rc}, expected {expected}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(FORMS))
def test_int_suffix_types_the_local(request, tmp_path, compiler, name):
    """AGAST #4245. Before the fix ritz1 computed each in i64."""
    _check(request, tmp_path, compiler, FORMS, name)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CONTROLS))
def test_int_suffix_controls(request, tmp_path, compiler, name):
    _check(request, tmp_path, compiler, CONTROLS, name)
