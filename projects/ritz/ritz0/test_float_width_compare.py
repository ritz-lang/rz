"""f32 meeting f64: arithmetic widens, a comparison asks for `as` (AGAST #3607,
LANGUAGE_SPEC §7.1, §7.2; Aaron, 2026-11-17).

    let y: f32 = 3.0
    let x: f64 = 2.0
    let z = y * x        # f64: y widens, losslessly
    if x > y             # error: cannot compare `f64` with `f32`: write `as` ...
    if x > (y as f64)    # fine, and so is `(x as f32) > y`

`a: f32 = 0.1` and `b: f64 = 0.1` give `a == b` false and `a > b` true: each
side widened correctly, and still almost never what the writer meant.  A float
literal takes the other side's type, so `y == 0.1` compares in f32.

Before this ticket ritz0's `--check-types` refused the comparison and nothing
else did: ritz0's default compile and both ritz1s fpext'd and compared.  Each
row is one compile per compiler, as a table (test_table_rows.py): six operators
in both orders, the widened result of an arithmetic op meeting f32, and the
programs that must still run.
"""

import re

import pytest

from float_rules import mixed_float_compare
from test_ref_into_value import COMPILERS
from test_table_rows import assert_refusals, assert_runs

pytestmark = pytest.mark.integration

OPS = ["==", "!=", "<", "<=", ">", ">="]

# `^` marks where each compiler must report the error: the comparison's start.
COMPARE = """\
fn f(y: f32, x: f64) -> i32
    if {cond}
        return 1
    return 0

pub fn main() -> i32
    return f(3.0, 2.0)
"""


def _refused():
    rows = {}
    for i, op in enumerate(OPS):
        rows[f"f32_{op}_f64"] = (COMPARE.format(cond=f"^y {op} x"), mixed_float_compare("f32", "f64"))
        rows[f"f64_{op}_f32"] = (COMPARE.format(cond=f"^x {op} y"), mixed_float_compare("f64", "f32"))
    # An arithmetic result is f64 once an f64 meets an f32 in it.
    rows["widened_product_vs_f32"] = (COMPARE.format(cond="^y * x > y"), mixed_float_compare("f64", "f32"))
    rows["f32_vs_widened_sum"] = (COMPARE.format(cond="^y < x + y"), mixed_float_compare("f32", "f64"))
    return rows


RUNS = {
    # §7.1: the f32 widens, the result is f64, and an f64 slot takes it.
    "product_is_f64": ("""\
pub fn main() -> i32
    let y: f32 = 3.0
    let x: f64 = 2.5
    let z = y * x
    let w: f64 = z
    return (w * 2.0) as i32
""", 15),
    # Every op, `%` too: ritz1 had it as fadd (#3798), then it needed libm (#3817).
    "both_orders_and_each_op": ("""\
pub fn main() -> i32
    let y: f32 = 3.0
    let x: f64 = 2.0
    let s: f64 = (y + x) + (x - y) + (y * x) + (y / x) * 2.0 + (y % x) + (x % y) * 2.0
    return s as i32
""", 18),
    # §7.2: both spellings choose a precision; 0.1 differs in f32 and f64.
    "as_f32_compares_in_f32": ("""\
pub fn main() -> i32
    let a: f32 = 0.1
    let b: f64 = 0.1
    if a == b as f32
        return 7
    return 1
""", 7),
    "as_f64_compares_in_f64": ("""\
pub fn main() -> i32
    let a: f32 = 0.1
    let b: f64 = 0.1
    if a as f64 == b
        return 1
    if a as f64 > b
        return 8
    return 2
""", 8),
    # A literal takes the other side's type: `y == 0.1` is an f32 compare.
    "literal_takes_f32": ("""\
pub fn main() -> i32
    let y: f32 = 0.1
    if y == 0.1 and 0.1 == y and not (y > 0.1) and y >= -0.5
        return 9
    return 1
""", 9),
    # So does an expression of literals alone: `0.0 + 0.1` is an f32 0.1 here.
    "literal_expression_takes_f32": ("""\
pub fn main() -> i32
    let y: f32 = 0.1
    let m: f32 = -0.2
    if y == 0.0 + 0.1 and (0.3 - 0.2) * 1.0 != 0.3 - 0.2 + y and m == y * (0.0 - 2.0)
        return 11
    return 1
""", 11),
    # f32 arithmetic with a literal stays f32, so it compares with an f32.
    "f32_arith_with_literal_stays_f32": ("""\
pub fn main() -> i32
    let y: f32 = 1.5
    let h: f32 = 3.0
    if y * 2.0 == h and h > y + 1.0
        return 10
    return 1
""", 10),
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_mixed_float_compare_is_refused(tmp_path, compiler):
    assert_refusals(compiler, tmp_path, _refused())


@pytest.mark.parametrize("compiler", COMPILERS)
def test_widening_and_explicit_as_run(tmp_path, compiler):
    assert_runs(compiler, tmp_path, RUNS)


@pytest.mark.parametrize("cond, words", [("y < x", ("f32", "f64")), ("x == y", ("f64", "f32"))])
def test_ritz0_emitter_refuses_without_the_typing_pass(cond, words):
    """The emitter's own guard: emit_module alone, no typing pass before it."""
    from emitter_llvmlite import EmitError, LLVMEmitter
    from lexer import tokenize
    from parser import Parser
    module = Parser(tokenize(COMPARE.format(cond=cond))).parse_module()
    with pytest.raises(EmitError, match=re.escape(mixed_float_compare(*words))):
        LLVMEmitter().emit_module(module)


def _typed(src):
    from lexer import tokenize
    from parser import Parser
    from typed import type_module
    module = Parser(tokenize(src)).parse_module()
    return module, type_module(module)


def test_ritz0_typing_pass_refuses_on_every_compile():
    """typed.py's slot errors are reported without --check-types (ritz0.py)."""
    _, table = _typed(COMPARE.format(cond="x >= y"))
    assert [str(e).split(": ", 1)[1] for e in table.slot_errors] == [mixed_float_compare("f64", "f32")]
    _, table = _typed(COMPARE.format(cond="y == 0.1 and x == (y as f64)"))
    assert table.slot_errors == []


def test_ritz0_typing_pass_widens_arithmetic():
    """`y * x` is f64; `y * 2.0` stays f32 (the literal takes y's type)."""
    module, table = _typed(COMPARE.format(cond="y * x + 2.0 > 0.0 and 2.0 * y > y"))
    first = module.items[0].body.stmts[0]
    cond = getattr(first, "expr", first).cond
    wide, narrow = cond.left.left, cond.right.left
    assert table.type_of(wide).name == "f64"
    assert table.type_of(wide.left).name == "f64"
    assert table.type_of(narrow).name == "f32"
