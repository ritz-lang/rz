"""AGAST #4656 (was #4662): an untyped array / tuple literal is typed from all
of its elements, on all three compilers.

ritz1 typed an array literal from whichever element named a struct, so
`let a = [1, t]` (t a struct) built IR clang refused, and ritz0 died in an
llvmlite traceback.  Both now refuse it, at the element that doesn't fit:
an array's element type is element 0's (or the declared one).

The other way round, ritz0 builds literals whose elements are references or
tuples, and ritz1 refused them ("it has no `[N]T` slot", "can't infer the type
of this tuple element").  Those are test_move_checker.py
TestArrayTupleLiteralMoves' rows, run here end to end: `[t, t]` / `(t, t)`
of a reference param, `[@t]` / `(@t, 1)`, and `[(t, 1)]`.
"""

import pytest

from test_ref_into_value import COMPILERS
from test_table_rows import assert_refusals, assert_runs

pytestmark = pytest.mark.integration

# Res drops, as in test_move_checker.py, so an element moves into the literal.
DEFS = """\
trait Drop
    fn drop(self: @&Self)

struct Res
    h: i32

impl Drop for Res
    fn drop(self: @&Res)
        pass

fn make() -> Res
    return Res { h: 1 }

"""

MESSAGE = "array literal element 1 is not the array's element type"


def _main(body):
    return DEFS + "fn main() -> i32\n    var t = make()\n" + body + "    return 0\n"


REFUSED = {
    "array_not_first": (_main("    let a = [1, ^t]\n"), MESSAGE),
    "struct_then_int": (_main("    let a = [t, ^1]\n"), MESSAGE),
    "declared_struct": (_main("    let a: [2]Res = [t, ^1]\n"), MESSAGE),
    "declared_int": (_main("    let a: [2]i64 = [1, ^t]\n"), MESSAGE),
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_element_of_another_type_is_refused(tmp_path, compiler):
    assert_refusals(compiler, tmp_path, REFUSED)


RUNS = {
    "reference_param": (DEFS + (
        "fn f(t: @Res) -> i32\n"
        "    let a = [t, t]\n"
        "    let b = (t, t)\n"
        "    a[1].h + b.1.h\n\n"
        "fn main() -> i32\n    let r = make()\n    f(@r)\n"), 2),
    "borrowed_element": (DEFS + (
        "fn main() -> i32\n"
        "    var t = make()\n"
        "    let a = [@t]\n"
        "    let b = (@t, 1)\n"
        "    a[0].h + b.0.h + (b.1 as i32)\n"), 3),
    "tuple_in_array": (DEFS + (
        "fn main() -> i32\n"
        "    var t = make()\n"
        "    let a = [(t, 4)]\n"
        "    a[0].0.h + (a[0].1 as i32)\n"), 5),
    # Controls: elements that do agree.
    "one_type": (DEFS + (
        "fn main() -> i32\n"
        "    let a = [make(), make()]\n"
        "    let b = [1, 2 as i32, 3]\n"
        "    a[1].h + (b[2] as i32)\n"), 4),
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_reference_and_tuple_elements_build(tmp_path, compiler):
    assert_runs(compiler, tmp_path, RUNS)
