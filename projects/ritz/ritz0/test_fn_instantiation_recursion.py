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

# mid<T> names the deeper leaf<Cell<T>> once, at two types: mid<i32> ->
# leaf<Cell<i32>>, mid<i64> -> leaf<Cell<i64>>.  Exits 0 only if each kept
# its value.  (mid<Cell<i32>>, a T that is itself generic, is left out: ritz0
# mangles its leaf<Cell<T>> two ways and refuses it; AGAST #3356.)
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
    a - 7 + (b - 5) as i32
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
