"""Regression tests for AGAST #1520: ritz1 never specialized the methods of a
generic impl block (`impl<T> Box<T>`, `impl<T> Tr for W<T>`).

find_generic_impl looked for a `$` in the impl's type name, but the parser
stores the plain base name (`Box`), so no generic impl was ever found and
every call `b.set(9)` linked against an undefined `Box$i64_set`
(examples/tier5_async/72_raii, ritz0/test/test_level30.ritz).

A type can have several generic impls (ritzlib.box has `impl<T> Drop for
Box<T>` and `impl<T> Box<T>`); each one's methods must be specialized.

ritz0 is the oracle for every program.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg

PROGRAMS = {
    # The ticket's repro: inherent impl from ritzlib.box.
    "box_set_get": """\
import ritzlib.box

pub fn main() -> i32
    var b: Box<i64> = box_new<i64>(4)
    b.set(9)
    return b.get() as i32
""",
    # Second generic impl of the same type (`impl<T> Drop for Box<T>`):
    # calling drop explicitly needs Box$i32_drop alongside Box$i32_get.
    "box_drop_and_get": """\
import ritzlib.box

pub fn main() -> i32
    var b: Box<i32> = box_new<i32>(7)
    let v: i32 = b.get()
    b.drop()
    return v + b.valid()
""",
    # A user-defined inherent generic impl, used at two type arguments.
    "inherent_two_args": """\
struct W<T>
    v: T

impl<T> W<T>
    fn val(self: *W<T>) -> T
        return self.v

    fn bump(self: *W<T>, by: T)
        self.v = self.v + by

pub fn main() -> i32
    var a: W<i32> = W<i32> { v: 3 }
    var b: W<i64> = W<i64> { v: 10 }
    a.bump(2)
    b.bump(20)
    return a.val() + b.val() as i32
""",
    # Trait impl for a generic type (test_level30's shape).
    "trait_impl": """\
struct W<T>
    v: T

trait Tr
    fn tag(self: *Self) -> i32

impl<T> Tr for W<T>
    fn tag(self: *W<T>) -> i32
        return 42

pub fn main() -> i32
    var a: W<i32> = W<i32> { v: 1 }
    var b: W<i64> = W<i64> { v: 2 }
    return a.tag() + b.tag() - 40
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_matches_ritz0(ritz1_bin, tmp_path, name):
    program = PROGRAMS[name]
    expected = _run_pkg("ritz0", tmp_path, name, program)
    assert _run_pkg("ritz1", tmp_path, name, program) == expected
