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

from test_ritz1_move_param import _run

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
