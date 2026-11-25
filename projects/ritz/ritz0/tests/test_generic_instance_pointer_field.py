"""A `*T` field of a generic instance is the pointer it was substituted to (AGAST #4680).

    struct W<T>
        ptr: *T

    fn f(w: @&W<Point>) -> i32
        let v: i32 = w.ptr      # cannot initialize i32 with *Point

ritz0 types `w.ptr` as `*Point` and refuses it in an `i32` slot.  ritz1
monomorphises `W<Point>` into `W$Point` before Sema runs, but its clone of a
`*T` field substituted the pointee's name and never set the field's pointee
kind (`StructField.ptr_pointee`), so Sema couldn't class the value and every
slot took it.  Both clones (one parameter, and #1574's several) and every
argument shape: a struct `T`, a primitive `T` (`W<u8>`'s `*u8`).

One row per slot (a typed `let`, an assignment, an argument) per clone, plus
the primitive argument; the run rows take each in the slot that fits.  The
argument rows needed more than the field: ritz1 refused no scalar misfit of
a named fn's argument at all (a float, `null` or pointer for an integer
param, a narrow integer for a pointer one), so those have a row each.
"""

import pytest
from test_ref_into_value import COMPILERS
from test_table_rows import assert_refusals, assert_runs

pytestmark = pytest.mark.unit

_HEAD = """struct Point
    x: i32
    y: i32

struct W<T>
    ptr: *T
    n: i32
    home: *Point

struct P<A, B>
    a: *A
    b: B
    home: *Point

fn take(x: i32) -> i32
    x

fn take_point(p: *Point) -> i32
    p.x

fn take_byte(p: *u8) -> i32
    *p as i32

"""

_MAIN = "\nfn main() -> i32\n    0\n"
_SIG = "fn f(w: @&W<Point>, p: @P<Point, i32>, u: @W<u8>) -> i32\n"


def _refused(body: str) -> str:
    return _HEAD + _SIG + body + "    0\n" + _MAIN


_LET = "cannot initialize i32 with "
_ASSIGN = "cannot assign {} to i32"
_ARG = "argument 1 ('x'): expected i32, got "

REFUSED = {
    # The ticket's row: test_deref_field_types.py's, without the Deref impl.
    "let_one_param": (_refused("    ^let v: i32 = w.ptr\n"), _LET + "*Point"),
    "assign_one_param": (_refused("    var v: i32 = 0\n    ^v = w.ptr\n"), _ASSIGN.format("*Point")),
    "arg_one_param": (_refused("    take(^w.ptr)\n"), _ARG + "*Point"),
    "let_two_params": (_refused("    ^let v: i32 = p.a\n"), _LET + "*Point"),
    "assign_two_params": (_refused("    var v: i32 = 0\n    ^v = p.a\n"), _ASSIGN.format("*Point")),
    "arg_two_params": (_refused("    take(^p.a)\n"), _ARG + "*Point"),
    "let_primitive_param": (_refused("    ^let v: i32 = u.ptr\n"), _LET + "*u8"),
    # A pointer field that isn't the parameter's keeps the template's pointee.
    "let_fixed_pointer_field": (_refused("    ^let v: i32 = w.home\n"), _LET + "*Point"),
    "let_fixed_pointer_field_two_params": (_refused("    ^let v: i32 = p.home\n"), _LET + "*Point"),
    # ritz1 judged no scalar argument of a named fn's call (cc_kind's
    # SKF_NUM): these went unrefused whatever the argument was.
    "arg_float": (_refused("    let d: f64 = 1.5\n    take(^d)\n"), _ARG + "f64"),
    "arg_null": (_refused("    take(^null)\n"), _ARG + "null"),
    "arg_int_for_pointer": (_refused("    let n: i32 = 1\n    take_byte(^n)\n"),
                            "argument 1 ('p'): expected *u8, got i32"),
}

_RUN = _HEAD + """fn main() -> i32
    var pt: Point = Point { x: 7, y: 9 }
    var b: u8 = 5
    var w: W<Point> = W<Point> { ptr: @pt, n: 1, home: @pt }
    var p: P<Point, i32> = P<Point, i32> { a: @pt, b: 2, home: @pt }
    var u: W<u8> = W<u8> { ptr: @b, n: 3, home: @pt }
"""

RUNS = {
    "let_and_arg": (_RUN + "    let q: *Point = w.ptr\n    let r: *Point = p.a\n    let h: *Point = u.home\n"
                    "    take_point(q) + take_point(r) + take_point(w.ptr) + take_point(p.a) - 28 + take_byte(u.ptr) + take_point(h) - 7\n", 5),
    "assign": (_RUN + "    var s: *Point = null\n    s = w.ptr\n    let x: i32 = s.x\n"
               "    s = p.a\n    var c: *u8 = null\n    c = u.ptr\n    x + s.y + *c as i32\n", 21),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_every_compiler_refuses_a_pointer_field_in_an_int_slot(tmp_path, compiler):
    assert_refusals(compiler, tmp_path, REFUSED)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_every_compiler_takes_a_pointer_field_in_its_own_slot(tmp_path, compiler):
    assert_runs(compiler, tmp_path, RUNS)
