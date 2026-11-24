"""Regression tests for AGAST #4572: i64's minimum through ritz1's own
print/format helpers.

Each helper negated a value that can be i64::MIN with `0 - n`, which has no
i64 result, so under LARB R63 (#3488) it stopped the program instead of
printing:

  - ritz1/src/deref_field.ritz df_put_call_part, which spells an integer
    argument in the method-and-fn-field diagnostic: a u64 literal
    0x8000000000000000 is held in the AST as i64::MIN;
  - ritz1/src/emitter.ritz emit_const_float_field, an integer literal in a
    const's float field: the same literal, negated.  Unnegated, it was read
    as -2^63 rather than 2^63.

ritz1/runtime/io_minimal.ritz print_int / eprint_int had it too; that file
was dead (nothing imported it) and #4565 deleted it with the legacy printers.

sage's push_i64 had the same bug; its test is the `[[test]]` beside it in
projects/sage/src/float.ritz.
"""

import pytest
from ref_rules import method_and_field
from test_fn_field_call import FNS
from test_ref_into_value import COMPILERS, _assert_refused, _run

pytestmark = pytest.mark.integration


# The method-and-fn-field diagnostic spells an integer argument as ritz0's
# _field_call_text does: str(value), so 2^63 in full and unsigned.
@pytest.mark.parametrize("compiler", COMPILERS)
def test_method_and_field_spells_u64_literal(tmp_path, compiler):
    program = FNS + """
impl H
    fn f(self: @H, x: u64) -> i32
        99

pub fn main() -> i32
    let h = H { f: dbl, g: add, n: 0 }
    h.^f(0x8000000000000000)
"""
    message = method_and_field("f", "H", "(h.f)(9223372036854775808)")
    _assert_refused(compiler, tmp_path, "u64_min_arg", program, message)


# 2^63 as an integer literal in a const's f64 and f32 fields, plain and
# negated.  2^63 is exact in both float types.  Exits 3 when all four hold.
FLOAT_CONST = """\
struct P
    d: f64
    s: f32

const T: [2]P = [P { d: 0x8000000000000000, s: 0x8000000000000000 }, P { d: -0x8000000000000000, s: -0x8000000000000000 }]

pub fn main() -> i32
    if T[0].d != 9223372036854775808.0
        return 10
    if T[0].s != 9223372036854775808.0
        return 11
    if T[1].d != -9223372036854775808.0
        return 12
    if T[1].s != -9223372036854775808.0
        return 13
    3
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_const_float_field_from_2_pow_63(tmp_path, compiler):
    assert _run(compiler, tmp_path, "float_const", FLOAT_CONST) == 3
