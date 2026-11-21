"""Regression tests for AGAST #1615: a float literal's `f32` / `f64` type
suffix (`2.5f32`) on ritz1.

ritz0 reads `2.5f32` as `2.5 as f32`. ritz1 only absorbed integer suffixes
(`0u32`, AGAST #107), so `2.5f32` lexed as FLOAT `2.5` + IDENT `f32` and every
row in FORMS was a parse error before the fix.

The suffix must also *type* the literal, not just be swallowed: `2.1f32` is
rounded to f32, so widened back to f64 it is no longer equal to `2.1`
(`inferred_f32_rounds`), while the unsuffixed control stays exact.

ritz0 is the oracle: each expected exit status is checked against it too.
"""

import pytest

from test_ritz1_move_param import _compile, _run

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# name -> (program, expected exit status)
FORMS = {
    # The ticket's repro, with the value observed.
    "f32_slot": ("""\
pub fn main() -> i32
    let c: f32 = 2.5f32
    return (c * 2.0) as i32
""", 5),
    "f64_slot": ("""\
pub fn main() -> i32
    let c: f64 = 2.5f64
    return (c * 4.0) as i32
""", 10),
    # The suffix types an unannotated binding: `2.1f32` is rounded to f32.
    "inferred_f32_rounds": ("""\
pub fn main() -> i32
    let c = 2.1f32
    let d: f64 = c as f64
    if d == 2.1
        return 1
    return 7
""", 7),
    "inferred_f64_exact": ("""\
pub fn main() -> i32
    let c = 2.1f64
    if c == 2.1
        return 8
    return 1
""", 8),
    # Inside an expression and as an argument.
    "suffix_in_expr_and_arg": ("""\
fn twice(x: f32) -> f32
    return x * 2.0

pub fn main() -> i32
    let s: f32 = twice(1.5f32) + 0.5f32
    return s as i32
""", 3),
}

# Controls that worked before the fix and must still work.
CONTROLS = {
    "no_suffix_f32": ("""\
pub fn main() -> i32
    let c: f32 = 2.5
    return (c * 2.0) as i32
""", 5),
    "no_suffix_inferred_exact": ("""\
pub fn main() -> i32
    let c = 2.1
    if c == 2.1
        return 9
    return 1
""", 9),
    "int_suffix": ("""\
pub fn main() -> i32
    let a = 3u32
    return a as i32
""", 3),
}

# Not a float suffix: refused on every compiler, never silently absorbed.
REFUSED = {
    "f16": "pub fn main() -> i32\n    let c: f32 = 2.5f16\n    0\n",
    "f32x": "pub fn main() -> i32\n    let c = 2.5f32x\n    0\n",
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
def test_float_suffix(request, tmp_path, compiler, name):
    """AGAST #1615. Before the fix each was a ritz1 parse error."""
    _check(request, tmp_path, compiler, FORMS, name)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CONTROLS))
def test_float_suffix_controls(request, tmp_path, compiler, name):
    _check(request, tmp_path, compiler, CONTROLS, name)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_bad_float_suffix_refused(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    comp, ll = _compile(compiler, tmp_path, REFUSED[name])
    assert comp.returncode != 0, f"{compiler} accepted {name}"
    assert not ll.exists()
