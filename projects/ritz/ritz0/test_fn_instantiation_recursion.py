#!/usr/bin/env python3
"""A generic fn that calls a deeper instance of itself is refused (AGAST #3343).

    fn deep<T>(x: T, n: i32) -> i32
        deep<Cell<T>>(Cell<T> { v: x }, n - 1)

deep<i32> names deep<Cell<i32>>, which names deep<Cell<Cell<i32>>>, and so on
(polymorphic recursion).  ritz0 has refused it since #3330 with the generation
cap it shares with ritz1 (MAX_INSTANCE_DEPTH).  ritz1 never reached the cap:
specialising a body left T unsubstituted inside a nested explicit type
argument, so deep<i32> called `deep$Cell$T`, which clang rejected ("invalid
type for function argument").  The same slip broke a generic fn that calls a
deeper instance of another fn a fixed number of times, so FINITE is the
substitution's own test and RECURSIVE the cap's.

The ritz1 compilers run under a timeout, so a hang fails here rather than
stalling the suite.
"""

import pytest

from test_impl_instantiation_recursion import COMPILERS, _compile
from test_right_shift import _run

# The ticket's program.  `deep` is defined on line 3, column 1.
RECURSIVE = """\
struct Cell<T>
    v: T
fn deep<T>(x: T, n: i32) -> i32
    if n == 0
        return 0
    deep<Cell<T>>(Cell<T> { v: x }, n - 1)
fn main() -> i32
    deep<i32>(1, 3)
"""

# mid<T> names the deeper leaf<Cell<T>> once, at three types: mid<i32> ->
# leaf<Cell<i32>>, mid<i64> -> leaf<Cell<i64>>, and mid<Cell<i32>> ->
# leaf<Cell<Cell<i32>>>, where T is itself generic.  ritz0 used to name that
# last Cell<Cell<i32>> two ways (`Cell$Cell$i32` for the let annotation,
# `Cell$Cell_i32` for leaf's argument) and refuse the program (AGAST #3356).
# Exits 0 only if each kept its value.
FINITE = """\
struct Cell<T>
    v: T
fn leaf<T>(x: T) -> T
    x
fn mid<T>(x: T) -> T
    let c: Cell<T> = leaf<Cell<T>>(Cell<T> { v: x })
    c.v
fn main() -> i32
    let a: i32 = mid<i32>(7)
    let b: i64 = mid<i64>(5)
    let d: i32 = mid<Cell<i32>>(Cell<i32> { v: 9 }).v
    a - 7 + (b - 5) as i32 + (d - 9)
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_recursive_fn_is_refused_at_the_fn(request, compiler, tmp_path):
    proc = _compile(request, compiler, tmp_path, RECURSIVE)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, out
    assert "Traceback" not in out, out
    assert "unit.ritz:3:1: " in out, out
    assert ("instantiating `deep` recurses: each instance names a deeper one "
            "(stopped after 64)") in out, out


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_fixed_depth_deeper_instance_compiles(request, compiler, tmp_path):
    assert _run(request, compiler, tmp_path, FINITE) == 0

# A generic impl's method body is substituted the same way: get() at
# T = Cell<i32> first names Cell<Cell<i32>> in its own body.  ritz0 declared
# `c` a bare `Cell` while its initialiser was a `Cell$Cell_i32` (AGAST #3356).
IMPL_BODY = """\
struct Cell<T>
    v: T
struct Box<T>
    v: T
impl<T> Box<T>
    fn get(self: @Box<T>) -> T
        let c: Cell<T> = Cell<T> { v: self.v }
        c.v
fn main() -> i32
    let b: Box<Cell<i32>> = Box<Cell<i32>> { v: Cell<i32> { v: 7 } }
    b.get().v - 7
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_impl_method_names_a_deeper_instance(request, compiler, tmp_path):
    assert _run(request, compiler, tmp_path, IMPL_BODY) == 0
