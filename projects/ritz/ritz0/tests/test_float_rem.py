"""Float `%` links and is C's exact fmod on every compiler (AGAST #3798, #3817).

ritz1's float binop dispatch had no arm for OP_MOD, so `x % y` on floats fell
through to `fadd` (#3798).  It then emitted `frem`, as ritz0 always had, but on
x86-64 LLVM lowers a non-constant `frem` to a libm `fmod`/`fmodf` call, and
Ritz links no libc: `x % y` on float parameters failed at link (#3817).  Each
emitter now calls a module-internal `__ritz_fmod`/`__ritz_fmodf` instead.

`%` is exact, as fmod is: `x - trunc(x / y) * y` gives 0 for 1e17 % 3 (the
quotient rounds), where the answer is 1.  The operands go through parameters
so no compiler can fold them.  Each row exits with its number when it passes.
"""

import pytest

from test_ref_into_value import COMPILERS
from test_table_rows import assert_runs

pytestmark = pytest.mark.integration

HELPERS = """\
fn r(x: f64, y: f64) -> f64
    return x % y

fn rf(x: f32, y: f32) -> f32
    return x % y

fn r_f32_f64(y: f32, x: f64) -> f64
    return y % x

fn r_f64_f32(y: f32, x: f64) -> f64
    return x % y

fn pow2(n: i32) -> f64
    var p: f64 = 1.0
    var i: i32 = 0
    while i < n
        p = p * 2.0
        i = i + 1
    return p

fn tiny() -> f64
    var p: f64 = 1.0
    var i: i32 = 0
    while i < 1074
        p = p * 0.5
        i = i + 1
    return p

"""


def _row(cond, code):
    return (HELPERS + f"pub fn main() -> i32\n    if {cond}\n        return {code}\n    return 99\n", code)


ROWS = {
    # C's fmod: the result takes x's sign; |result| < |y|.
    "f64_signs": _row("r(7.5, 2.0) == 1.5 and r(0.0 - 7.5, 2.0) == 0.0 - 1.5 and r(7.5, 0.0 - 2.0) == 1.5", 1),
    "f64_smaller_x_is_x": _row("r(1.5, 4.0) == 1.5 and r(0.0 - 1.5, 4.0) == 0.0 - 1.5", 2),
    # Exact, where x - trunc(x/y)*y gives 0.
    "f64_exact_large": _row("r(100000000000000000.0, 3.0) == 1.0", 3),
    "f32_exact_large": _row("rf(10000000000.0, 3.0) == 1.0 and rf(7.5, 2.0) == 1.5", 4),
    # Mixed widths widen the f32 (AGAST #1965) and stay exact.
    "mixed_both_orders": _row("r_f32_f64(7.5, 2.0) == 1.5 and r_f64_f32(3.0, 100000000000000000.0) == 1.0", 5),
    # -4 % 2 is -0.0: 1 / -0.0 is -inf.
    "negative_zero": _row("1.0 / r(0.0 - 4.0, 2.0) < 0.0 and 1.0 / r(4.0, 0.0 - 2.0) > 0.0", 6),
    # y == 0 or x infinite is NaN; y infinite leaves x.
    "nan_and_inf": _row("r(1.0, 0.0) != r(1.0, 0.0) and r(1.0 / 0.0, 2.0) != r(1.0 / 0.0, 2.0) "
                        "and r(5.0, 1.0 / 0.0) == 5.0 and r(0.0 / 0.0, 2.0) != r(0.0 / 0.0, 2.0) "
                        "and r(2.0, 0.0 / 0.0) != r(2.0, 0.0 / 0.0)", 7),
    # The widest exponent spread: 2^1000 % 3 is 1, and % the least subnormal is 0.
    "extreme_exponents": _row("r(pow2(1000), 3.0) == 1.0 and r(pow2(1000), tiny()) == 0.0 "
                              "and r(tiny() * 3.0, tiny() * 2.0) == tiny()", 8),
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_float_rem_runs_exactly(tmp_path, compiler):
    assert_runs(compiler, tmp_path, ROWS)
