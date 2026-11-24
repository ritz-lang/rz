"""ritz1's own intentional wraps are spelled `+%`/`-%`/`*%` (AGAST #4548).

ritz0 builds ritz1, and since LARB R63 (#3488) ritz0's `+`, `-`, `*` stop
the program on overflow. ritz1 had arithmetic whose correctness depends on
wrapping, so the ritz1 binary itself stopped with `integer overflow in ...`:

- `narrow_mul_ok` (narrowing.ritz) proves a literal product fits by
  multiplying and dividing back; an overflowing product must wrap so the
  check can answer "not proven" (an implicit-narrowing error);
- `const_fold_int` (ast_helpers.ritz) and `global_init_fold` (emitter.ritz,
  pointer globals) negate and complement an i64 that also holds u64 values, so
  `-9223372036854775808` and `~0x8000000000000000` negate i64::MIN.

ritz1_selfhosted is built by ritz1, which traps too since #3489, so both
binaries run every row.
"""

import pytest
from test_ritz1_move_param import _compile, _run

pytestmark = [pytest.mark.integration]

# name -> (program, the located error). ritz1 must refuse each where it is
# written, in ritz0's words, rather than trap inside the compiler. Before
# AGAST #4665 ritz1 answered with an implicit-narrowing error here: the
# narrowing check ran before the constant was computed.
REFUSED = {
    "mul_overflow_let": ("""\
pub fn main() -> i32
    let x: i32 = 4294967296 * 4294967296
    return 0
""", "main.ritz:2:18: error: integer overflow in `*`"),
    "mul_overflow_arg": ("""\
fn take(x: i32) -> i32
    x

pub fn main() -> i32
    return take(3037000500 * 3037000500)
""", "main.ritz:5:17: error: integer overflow in `*`"),
}

# name -> (program, expected exit status); ritz0 is the oracle.
RUNS = {
    "global_neg_i64_min": ("""\
var G: i64 = -9223372036854775808

pub fn main() -> i32
    if G < 0
        return 7
    return 1
""", 7),
    "global_not_u64_msb": ("""\
var G: u64 = ~0x8000000000000000

pub fn main() -> i32
    if G == 0x7FFFFFFFFFFFFFFF
        return 7
    return 1
""", 7),
    # A pointer global's initialiser goes through global_init_fold instead.
    "ptr_global_neg_i64_min": ("""\
var P: *u8 = (-0x8000000000000000) as *u8

pub fn main() -> i32
    if P as u64 == 0x8000000000000000
        return 7
    return 1
""", 7),
    "ptr_global_not_u64_msb": ("""\
var P: *u8 = (~0x8000000000000000) as *u8

pub fn main() -> i32
    if P as u64 == 0x7FFFFFFFFFFFFFFF
        return 7
    return 1
""", 7),
}


@pytest.mark.parametrize("compiler", ["ritz0", "ritz1", "ritz1_selfhosted"])
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_ritz1_refuses_overflowing_product(tmp_path, compiler, name):
    program, located = REFUSED[name]
    comp, _ = _compile(compiler, tmp_path, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out[-2000:]
    # ritz0 omits "error: "; a trap inside the compiler carries no location.
    path, message = located.split(" error: ")
    assert path in out and message in out, f"{compiler}:\n{out[-2000:]}"


@pytest.mark.parametrize("compiler", ["ritz0", "ritz1", "ritz1_selfhosted"])
@pytest.mark.parametrize("name", sorted(RUNS))
def test_global_initialiser_folds_i64_min(tmp_path, compiler, name):
    program, want = RUNS[name]
    assert _run(compiler, tmp_path, program) == want
