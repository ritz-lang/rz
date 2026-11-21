"""Float literals with an exponent: `2.0e10`, `1e-5`, `1E+3` (AGAST #3929).

LANGUAGE_SPEC §2 (float literals): a float is digits `.` digits, digits with
an exponent `[eE][+-]?digits`, or both. ritz0 has always lexed the exponent;
ritz1's lexer stopped at the fraction, so `2.0e10` was `2.0` then the
identifier `e10`, and `1e-5` was `1`, `e`, `-`, `5`.

The refusals are ritz0's: `1e` and `1e+` (no digit after the exponent) are a
lexer error at the byte where the digit should be; `1.e5` is no float (`1.`
is no fraction), so it is `1 . e5`, a field of an integer, refused too.

Every row runs on ritz0, ritz1 and ritz1_selfhosted.
"""

import pytest
from test_ref_into_value import COMPILERS, _assert_refused, _compile, _run

pytestmark = pytest.mark.integration

# Each body returns 42 when the literal has the value written beside it.
# Values are compared exactly: every one is the double the decimal rounds to,
# and the right-hand literal spells the same number without an exponent.
RUNS = {
    # LANGUAGE_SPEC.md's own example (#3928 found it): fraction and exponent.
    "spec_example": """\
fn f() -> f64
    let b = 2.0e10
    let c = 1e-5
    b + c

pub fn main() -> i32
    if f() == 20000000000.00001
        return 42
    1
""",
    "fraction_and_exponent": """\
pub fn main() -> i32
    let x: f64 = 2.0e10
    if x == 20000000000.0
        return 42
    1
""",
    "no_fraction_negative_exponent": """\
pub fn main() -> i32
    let x: f64 = 1e-5
    if x == 0.00001
        return 42
    1
""",
    "capital_e_plus_sign": """\
pub fn main() -> i32
    let x: f64 = 1E+3
    if x == 1000.0
        return 42
    1
""",
    "fraction_negative_exponent": """\
pub fn main() -> i32
    let x: f64 = 2.5e-1
    if x == 0.25
        return 42
    1
""",
    "zero_exponent": """\
pub fn main() -> i32
    let x: f64 = 7e0
    if x == 7.0
        return 42
    1
""",
    "as_int": """\
pub fn main() -> i32
    let n: i64 = 12e2 as i64
    if n == 1200
        return 42
    1
""",
    "negated": """\
pub fn main() -> i32
    let x: f64 = -1.5e2
    if x == -150.0
        return 42
    1
""",
    # A suffix after the exponent types the literal, as after a fraction.
    "f32_suffix": """\
pub fn main() -> i32
    let x: f32 = 2.5e3f32
    if x == 2500.0 as f32
        return 42
    1
""",
    "f32_slot": """\
pub fn main() -> i32
    let x: f32 = 1e-1
    if x == 0.1 as f32
        return 42
    1
""",
    "global_init": """\
var G: f64 = 4e3

pub fn main() -> i32
    if G == 4000.0
        return 42
    1
""",
    # A const struct's f32 field is rounded by ritz1 at compile time
    # (f32_literal_bits): the exponent must scale it.
    "const_f32_field": """\
struct P
    x: f32
    y: f64

const PS: [2]P = [P { x: 1.25e2, y: 3e-2 }, P { x: 5e-1, y: 1.0e1 }]

pub fn main() -> i32
    if PS[0].x == 125.0 as f32 and PS[0].y == 0.03 and PS[1].x == 0.5 as f32 and PS[1].y == 10.0
        return 42
    1
""",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_float_exponent_value(tmp_path, compiler, name):
    rc = _run(compiler, tmp_path, name, RUNS[name])
    assert rc == 42, f"{compiler}: {name} exited {rc}"


NO_DIGIT = "Expected digit after exponent"

# `^` marks where the error is reported: the byte after `e` (and its sign).
REFUSED = {
    "bare_e": "pub fn main() -> i32\n    let x: f64 = 1e^\n    0\n",
    "e_plus": "pub fn main() -> i32\n    let x: f64 = 1e+^\n    0\n",
    "e_minus_ident": "pub fn main() -> i32\n    let x: f64 = 2.0e-^y\n    0\n",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_exponent_without_digits_is_refused(tmp_path, compiler, name):
    _assert_refused(compiler, tmp_path, name, REFUSED[name], NO_DIGIT)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_dot_then_exponent_is_no_float(tmp_path, compiler):
    """`1.e5` is `1 . e5` (ritz0 too): refused, never the float 100000."""
    src = "pub fn main() -> i32\n    let x: f64 = 1.e5\n    0\n"
    comp, ll, _ = _compile(compiler, tmp_path, "dot_e", src)
    assert comp.returncode != 0, f"{compiler} accepted `1.e5`"
    assert not ll.exists()
