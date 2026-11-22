"""`_` digit separators in numeric literals (AGAST #3584, LARB R73).

LANGUAGE_SPEC §2.6: a `_` may separate two digits of a numeric literal,
decimal, hex or binary (`1_000_000`, `0xFFFF_FFFF`), and has no value.  It
may not start or end the digits, follow the `0x` / `0b` prefix, stand next to
another `_`, or touch a `.`, exponent or type suffix.

ritz0 accepted every `_` a number's digits ran into, wherever it stood, and
dropped it; ritz1 accepted none (`let b: u64 = 1_000 as u64` was "Parse error
at pos 23").  Now all three compilers take the same literals, and refuse a
misplaced `_` with one lexical error at that `_`.

One table on all three compilers (test_table_rows.py).  The accepted rows
separate the literal forms and the places ritz1 reads a literal's text again
(a value, the 2^64 overflow check, a float's digits, a suffix, a match arm);
the refused rows are one per placement rule.
"""

import pytest

import test_ritz1_for_header as for_header
import test_table_rows as table_rows
from test_table_rows import Refused, Run, case

MESSAGE = "`_` must stand between two digits of a numeric literal"


def _returns_42_if(cond, decl=""):
    return f"{decl}pub fn main() -> i32\n    if {cond}\n        return 42\n    1\n"


# ---- accepted -------------------------------------------------------------

# The ticket's program.
@case()
def the_ticket_cast():
    return Run("pub fn main() -> i32\n    let b: u64 = 1_000 as u64\n"
               "    if b == 1000 as u64\n        return 42\n    1\n", 42)


@case()
def decimal_groups():
    return Run(_returns_42_if("1_000_000 == 1000000"), 42)


# One digit per group, and a leading zero: any two digits may be split.
@case()
def single_digit_groups():
    return Run(_returns_42_if("0_1_2_3 == 123"), 42)


@case()
def hex_groups():
    return Run(_returns_42_if("0xFFFF_FFFF as u64 == 4294967295 as u64"), 42)


# A u64 past i64's range: ritz1 reads the text again for its 2^64 check.
# `+%` because the row wraps at 2^64, and R63 stops a plain `+` that does.
@case()
def hex_past_i64():
    return Run("pub fn main() -> i32\n    let m: u64 = 0xFFFF_FFFF_FFFF_FFF8\n"
               "    if m +% 8 == 0\n        return 42\n    1\n", 42)


@case()
def binary_groups():
    return Run(_returns_42_if("0b1010_0101 == 165"), 42)


# A suffix after the last digit.
@case()
def suffixed():
    return Run(_returns_42_if("1_000u64 == 1000 as u64 and 0xF_Fi32 == 255"), 42)


# A float's integer part, fraction and exponent.
@case()
def float_parts():
    return Run(_returns_42_if("1_000.2_5 == 1000.25 and 2.5e1_0 == 25000000000.0"), 42)


# A match arm's literal is its own parser path in ritz1.
@case()
def match_arm():
    return Run("pub fn main() -> i32\n    let n: i32 = 1000\n    match n\n"
               "        1_000 => 42\n        _ => 1\n", 42)


# ---- refused --------------------------------------------------------------
# `let x = <literal>` puts the literal at column 13; `at` is the bad `_`.

BAD = {
    "trailing": ("1_", 1),
    "doubled": ("1__0", 1),
    "after_hex_prefix": ("0x_FF", 2),
    "after_binary_prefix": ("0b_1", 2),
    "trailing_hex": ("0xFF_", 4),
    # `2` is a digit, but not of base 2: the `_` ends the binary digits.
    "before_a_non_binary_digit": ("0b1_2", 3),
    "before_dot": ("1_.5", 1),
    "after_dot": ("1._5", 2),
    "trailing_fraction": ("1.5_", 3),
    "before_exponent": ("1_e5", 1),
    "after_exponent": ("1e_5", 2),
    "after_exponent_sign": ("1e+_5", 3),
    "before_int_suffix": ("1_u8", 1),
    "before_float_suffix": ("2.5_f32", 3),
}


@case(where=sorted(BAD))
def misplaced(where):
    literal, offset = BAD[where]
    return Refused(f"pub fn main() -> i32\n    let x = {literal}\n    0\n",
                   MESSAGE, at=(2, 13 + offset))


TABLE = table_rows.cases(globals())


@pytest.mark.integration
@pytest.mark.parametrize("compiler,chunk", table_rows.chunks(TABLE),
                         ids=[f"{c}-{i}" for c, i in table_rows.chunks(TABLE)])
def test_every_row(ritz1_bin, tmp_path, compiler, chunk):
    table_rows.assert_rows(compiler, table_rows.chunk(TABLE, compiler, chunk),
                           build=for_header.batch_build(ritz1_bin),
                           compile=for_header.batch_compile(ritz1_bin), work=tmp_path)
