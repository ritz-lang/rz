"""Float `!=` is true when either side is NaN, on every compiler (AGAST #3836).

Both emitters lowered float `!=` to LLVM's `fcmp one` (ordered and not
equal), which is false whenever an operand is NaN, so `n != n` was false for
`n = 0.0 / 0.0`.  IEEE 754 and C make `!=` the negation of `==`: `fcmp une`.
The NaN reaches each compare through a parameter so no compiler can fold it,
and one row builds it from literals in place.  Each row exits with its
number when it passes.
"""

import pytest

from test_ref_into_value import COMPILERS
from test_row_table import assert_runs

pytestmark = pytest.mark.integration

HELPERS = """\
fn ne(x: f64, y: f64) -> bool
    return x != y

fn nef(x: f32, y: f32) -> bool
    return x != y

"""


def _row(cond, code):
    return (HELPERS + f"pub fn main() -> i32\n    if {cond}\n        return {code}\n    return 99\n", code)


ROWS = {
    # NaN is unequal to everything, itself included, and `==` stays false.
    "f64_nan": _row("ne(0.0 / 0.0, 0.0 / 0.0) and ne(0.0 / 0.0, 1.0) and ne(1.0, 0.0 / 0.0)", 1),
    "f32_nan": _row("nef(0.0 / 0.0, 0.0 / 0.0) and nef(0.0 / 0.0, 1.0) and nef(1.0, 0.0 / 0.0)", 2),
    # Ordinary values are unchanged: equal is not unequal, -0.0 equals 0.0.
    "ordinary": _row("ne(1.0, 2.0) and not ne(1.0, 1.0) and not ne(0.0, 0.0 - 0.0) "
                     "and nef(1.0, 2.0) and not nef(1.0, 1.0)", 3),
    # A NaN local compared in place, as the ticket writes it.
    "local_nan": ("pub fn main() -> i32\n    let n: f64 = 0.0 / 0.0\n"
                  "    if n != n and n != 1.0 and not (n == n)\n        return 4\n    return 99\n", 4),
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_float_ne_is_true_on_nan(tmp_path, compiler):
    assert_runs(compiler, tmp_path, ROWS)
