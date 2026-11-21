#!/usr/bin/env python3
"""A trait bound is checked where the generic is instantiated, located
(LANGUAGE_SPEC §11.5, LARB R55; ritz0 #3468, ritz1 #3469).

`<T: A + B>` on a fn, struct or impl: each type argument needs an impl of
each trait, exact or through a generic impl.  Otherwise the error is at the
type argument, or at the call when the argument is inferred:

    `Nope` doesn't implement `Area`, which `T` of `total` requires

An unknown trait is an error at the bound, and at an impl's trait name
(#4197, #4211).  Before #3468 a failed bound was an unlocated Python
TypeError on ritz0; before #3469 ritz1 couldn't parse `<T: A>` at all.
A generic impl satisfying a bound is test_trait_bounds.ritz's run row.

Every row runs on ritz0, ritz1 and ritz1_selfhosted, and all three must
report the same `line:col: message`.  One row per code path.
"""

import pytest

from test_ref_into_value import COMPILERS, _assert_refused, _run

pytestmark = pytest.mark.integration

PRELUDE = """\
trait Area
    fn area(self: @Self) -> i64
struct Nope
    x: i64
fn total<T: Area>(x: @T) -> i64
    0
struct Holder<T: Area>
    v: T
struct Bag<T>
    v: T
"""

# Each row: (program after PRELUDE with `^` at the error, message).
# `Bag<Nope>`, unbounded, names `Nope` first: the error is still at the
# bounded use.
ROWS = {
    # Explicit: at the type argument `Nope`.
    "explicit_fn_arg": (
        "fn main() -> i32\n"
        "    var b: Bag<Nope>\n"
        "    total<^Nope>(@b.v) as i32\n",
        "`Nope` doesn't implement `Area`, which `T` of `total` requires"),
    # Inferred: at the call.
    "inferred_fn_arg": (
        "fn main() -> i32\n"
        "    let n = Nope { x: 1 }\n"
        "    ^total(@n) as i32\n",
        "`Nope` doesn't implement `Area`, which `T` of `total` requires"),
    # The second of two params: at its own argument.
    "second_param": (
        "fn pair<U, T: Area>(u: U, x: @T) -> i64\n"
        "    0\n"
        "fn main() -> i32\n"
        "    var b: Bag<Nope>\n"
        "    pair<i64, ^Nope>(1, @b.v) as i32\n",
        "`Nope` doesn't implement `Area`, which `T` of `pair` requires"),
    # The second trait of `A + B`.
    "second_trait": (
        "trait Peri\n"
        "    fn peri(self: @Self) -> i64\n"
        "impl Area for Nope\n"
        "    fn area(self: @Nope) -> i64\n"
        "        0\n"
        "fn both<T: Area + Peri>(x: @T) -> i64\n"
        "    0\n"
        "fn main() -> i32\n"
        "    var b: Bag<Nope>\n"
        "    both<^Nope>(@b.v) as i32\n",
        "`Nope` doesn't implement `Peri`, which `T` of `both` requires"),
    # Transitive: `total<Nope>` is only ever `total<U>` in `outer`'s body,
    # so the error is at that `U`.
    "transitive_fn_arg": (
        "fn outer<U>(x: @U) -> i64\n"
        "    total<^U>(x)\n"
        "fn main() -> i32\n"
        "    let n = Nope { x: 1 }\n"
        "    outer<Nope>(@n) as i32\n",
        "`Nope` doesn't implement `Area`, which `T` of `total` requires"),
    # A struct's bound, from a type annotation: at the type argument.
    "struct_type_arg": (
        "fn main() -> i32\n"
        "    var h: Holder<^Nope>\n"
        "    0\n",
        "`Nope` doesn't implement `Area`, which `T` of `Holder` requires"),
    # An impl's bound is on its type's args: `W<Nope>` instantiates it.
    "impl_bound": (
        "struct W<T>\n"
        "    v: T\n"
        "impl<T: Area> W<T>\n"
        "    fn get(self: @W<T>) -> i64\n"
        "        0\n"
        "fn main() -> i32\n"
        "    var w: W<^Nope>\n"
        "    0\n",
        "`Nope` doesn't implement `Area`, which `T` of `impl W` requires"),
    # A generic trait impl's bound is on its type's args too: in
    # `Bag<Bag<Nope>>`, `Bag<Nope>` misses `Area` because `impl<T: Area>
    # Area for Bag<T>`'s own bound fails on `Nope`.  The outer instance is
    # judged first, at its argument; the arg is spelled as written.
    "generic_trait_impl_bound": (
        "impl<T: Area> Area for Bag<T>\n"
        "    fn area(self: @Bag<T>) -> i64\n"
        "        0\n"
        "fn main() -> i32\n"
        "    var b: Bag<^Bag<Nope>>\n"
        "    total<Bag<Nope>>(@b.v) as i32\n",
        "`Bag<Nope>` doesn't implement `Area`, which `T` of `impl Bag` requires"),
    # An unknown trait is an error at the bound, used or not.
    "unknown_trait": (
        "fn f<U: ^Nonesuch>(x: U) -> U\n"
        "    x\n"
        "fn main() -> i32\n"
        "    0\n",
        "unknown trait `Nonesuch` in the bound on `U`"),
    # ...on a struct's param, and as the second of `A + B`.
    "unknown_trait_struct_second": (
        "struct S<T: Area + ^Nonesuch>\n"
        "    v: T\n"
        "fn main() -> i32\n"
        "    0\n",
        "unknown trait `Nonesuch` in the bound on `T`"),
    # ...on an impl's param.
    "unknown_trait_impl": (
        "impl<T: ^Nonesuch> Bag<T>\n"
        "    fn get(self: @Bag<T>) -> i64\n"
        "        0\n"
        "fn main() -> i32\n"
        "    0\n",
        "unknown trait `Nonesuch` in the bound on `T`"),
    # ...and at an impl's trait name (#4197, #4211).  A declared trait
    # (`Area`) and a compiler trait (`Drop`) are known.
    "unknown_impl_trait": (
        "impl Area for Nope\n"
        "    fn area(self: @Nope) -> i64\n"
        "        0\n"
        "impl Drop for Nope\n"
        "    fn drop(self: @&Nope)\n"
        "        return\n"
        "impl ^Nonesuch for Nope\n"
        "    fn g(self: @Nope) -> i32\n"
        "        0\n"
        "fn main() -> i32\n"
        "    0\n",
        "unknown trait `Nonesuch`"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(ROWS))
def test_failed_bound_is_located(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    body, message = ROWS[row]
    _assert_refused(compiler, tmp_path, row, PRELUDE + body, message)


# The real ritzlib bounds (#4295): `fmt_show` and `fmt_show_with` need
# `Display`, `fmt_show_debug` needs `Debug`.  A `T` without the trait is an
# error at the call, not inside ritzlib/fmt/display.ritz: a whole program,
# not PRELUDE + body, because the imports come first.
FMT_BOUNDS = {
    "fmt_show": (
        "^fmt_show(@n, @&w) as i32",
        "`Nope` doesn't implement `Display`, which `T` of `fmt_show` requires"),
    "fmt_show_debug": (
        "^fmt_show_debug(@n, @&w) as i32",
        "`Nope` doesn't implement `Debug`, which `T` of `fmt_show_debug` requires"),
    "fmt_show_with": (
        '^fmt_show_with(@n, @&w, "x") as i32',
        "`Nope` doesn't implement `Display`, which `T` of `fmt_show_with` requires"),
}

FMT_PROGRAM = """\
import ritzlib.fmt.display
import ritzlib.fmt.writer

struct Nope
    x: i64

fn main() -> i32
    let n = Nope { x: 1 }
    var w: Writer = null_writer()
    {call}
"""


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(FMT_BOUNDS))
def test_fmt_bound_is_located_at_the_call(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    call, message = FMT_BOUNDS[row]
    marked = FMT_PROGRAM.replace("{call}", call)
    _assert_refused(compiler, tmp_path, f"fmt_{row}", marked, message)


# Satisfied bounds compile and run: exact impls, a generic impl (with its
# own bound met), a compiler trait, inferred and explicit, and a method
# called on `T` through the bound.
SATISFIED = """\
trait Area
    fn area(self: @Self) -> i64
trait Peri
    fn peri(self: @Self) -> i64
struct Sq
    s: i64
impl Area for Sq
    fn area(self: @Sq) -> i64
        self.s * self.s
impl Peri for Sq
    fn peri(self: @Sq) -> i64
        4 * self.s
struct Bag<T>
    v: T
impl<T: Area> Area for Bag<T>
    fn area(self: @Bag<T>) -> i64
        self.v.area() + 1
struct Res
    n: i64
impl Drop for Res
    fn drop(self: @&Res)
        return
fn total<T: Area>(a: @T, b: @T) -> i64
    a.area() + b.area()
fn both<U, T: Area + Peri>(u: U, x: @T) -> i64
    x.area() + x.peri()
fn owns<T: Drop>(x: @T) -> i64
    7
struct Holder<T: Area>
    v: T
impl<T: Area> Holder<T>
    fn get(self: @Holder<T>) -> i64
        self.v.area()

pub fn main() -> i32
    let a = Sq { s: 2 }
    let b = Sq { s: 3 }
    if total(@a, @b) != 13
        return 1
    if total<Sq>(@a, @b) != 13
        return 2
    if both<i32, Sq>(0, @b) != 21
        return 3
    let g = Bag<Sq> { v: a }
    if total(@g, @g) != 10
        return 4
    let r = Res { n: 1 }
    if owns(@r) != 7
        return 5
    let h = Holder<Sq> { v: b }
    if h.get() != 9
        return 6
    0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_satisfied_bounds_run(request, tmp_path, compiler):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    assert _run(compiler, tmp_path, "satisfied", SATISFIED) == 0
