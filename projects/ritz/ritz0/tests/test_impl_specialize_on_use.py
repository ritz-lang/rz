"""A generic impl's method is specialised only where a call reaches it (AGAST #3617, #3341).

Every compiler used to specialise EVERY method of a generic impl for EVERY
instance of its type, as soon as anything named the instance.  So a method
nothing calls was still emitted, type-checked and move-checked at every
instance: a `-nostdlib` importer of ritzlib.gvec linked `vec_grow$u8` and
`malloc`, `Vec<MoveOnly>`'s `pop` wrapper was refused "cannot move out of a
reference" though nothing popped, and `impl<T> Cell<T>`'s
`fn wrap(self) -> Cell<Cell<T>>` named a deeper instance at every level
(AGAST #3330's depth cap refused it).

Now an inherent impl's method is specialised for an instance only when a call
names it there, as a free generic fn already was: `x.m()` on that instance,
`T.m()` with the slot's instance, or a call from another method so
specialised.  A call whose receiver's type the compiler can't tell names `m`
on every instance, so nothing reachable is missed.  Trait impls (`Drop for`,
`Index for`, ...) are still specialised whole: the compiler calls them itself.

Each row exits with its number when it passes.
"""

import pytest

from test_ref_into_value import COMPILERS
from test_table_rows import assert_runs

pytestmark = pytest.mark.integration

W = """\
struct W<T>
    v: T
"""

# `far` calls a fn no object defines: emitted at any instance, the link fails.
NOWHERE = "fn nowhere_3617() -> i32 = extern\n"

ROWS = {
    # The ticket's malloc link failure, in small: an unused method's callee
    # is never referenced.  The receiver is a local, then a parameter.
    "unused_method_is_not_emitted": (NOWHERE + W + """\
impl<T> W<T>
    fn get(self: @W<T>) -> T
        self.v
    fn far(self: @W<T>) -> i32
        nowhere_3617()
fn via(p: @W<i32>) -> i32
    p.get()
fn main() -> i32
    let w = W<i32> { v: 1 }
    w.get() + via(@w)
""", 2),
    # Vec<MoveOnly>'s `pop`: a method that moves T out of a reference is
    # refused only at an instance that calls it.
    "unused_move_out_of_reference_is_not_checked": ("""\
trait Drop
    fn drop(self: @&Self)
struct Res
    h: i32
impl Drop for Res
    fn drop(self: @&Res)
        self.h = 0
""" + W + """\
impl<T> W<T>
    fn take(self: @W<T>) -> T
        self.v
    fn three(self: @W<T>) -> i32
        3
fn main() -> i32
    let w = W<Res> { v: Res { h: 1 } }
    w.three()
""", 3),
    # The ticket's #3341 row: Cell<i32>.wrap names Cell<Cell<i32>>, whose
    # `wrap` nothing calls, so instantiation stops there.
    "wrap_names_no_deeper_instance": ("""\
struct Cell<T>
    v: T
impl<T> Cell<T>
    fn wrap(self: @Cell<T>) -> Cell<Cell<T>>
        Cell<Cell<T>> { v: Cell<T> { v: self.v } }
fn main() -> i32
    let c = Cell<i32> { v: 9 }
    c.wrap().v.v - 5
""", 4),
    # A method reached only from another specialised method is specialised.
    "method_called_by_a_method": (NOWHERE + W + """\
impl<T> W<T>
    fn outer(self: @W<T>) -> i32
        self.inner() + 1
    fn inner(self: @W<T>) -> i32
        4
    fn far(self: @W<T>) -> i32
        nowhere_3617()
fn main() -> i32
    let w = W<u8> { v: 1 }
    w.outer()
""", 5),
    # `T.m()` takes the instance of the slot it fills.
    "static_method_by_slot": (NOWHERE + W + """\
impl<T> W<T>
    fn mk(x: T) -> W<T>
        W<T> { v: x }
    fn far(self: @W<T>) -> i32
        nowhere_3617()
fn main() -> i32
    let w: W<i32> = W.mk(6)
    w.v
""", 6),
    # A generic enum's impl, as a struct's.
    "enum_impl": (NOWHERE + """\
enum Slot<T>
    Empty
    Full(T)
impl<T> Slot<T>
    fn get_or(self: @Slot<T>, d: T) -> T
        match *self
            Full(x) => x
            Empty => d
    fn far(self: @Slot<T>) -> i32
        nowhere_3617()
fn main() -> i32
    let s: Slot<i32> = Empty
    s.get_or(7)
""", 7),
    # Each instance gets what is called on it: `get` at i32, `far` at none.
    "per_instance": (NOWHERE + W + """\
impl<T> W<T>
    fn get(self: @W<T>) -> T
        self.v
    fn far(self: @W<T>) -> i32
        nowhere_3617()
fn main() -> i32
    let a = W<i32> { v: 8 }
    let b = W<i64> { v: 0 }
    a.get() + b.v as i32
""", 8),
    # A print placeholder's call: ritz1 parses `{w.get()}` only when it
    # emits the literal, after monomorph (tier5 72_raii, 82_box).
    "called_in_a_print_placeholder": (W + """\
impl<T> W<T>
    fn get(self: @W<T>) -> T
        self.v
fn main() -> i32
    let w = W<i32> { v: 9 }
    print("{w.get()}\\n")
    9
""", 9),
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_impl_methods_specialise_on_use(tmp_path, compiler):
    assert_runs(compiler, tmp_path, ROWS)
