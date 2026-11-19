#!/usr/bin/env python3
"""A generic impl whose called method names a deeper instance is refused (AGAST #3330).

    impl<T> Cell<T>
        fn deep(self: @Cell<T>) -> i32
            let c = Cell<Cell<T>> { v: *self }
            c.deep()

`deep` at Cell<i32> calls `deep` at Cell<Cell<i32>>, which calls it at
Cell<Cell<Cell<i32>>>, and so on.  ritz0 gave up after 100 rounds and died in
the emitter with a Python traceback; ritz1 and ritz1_selfhosted never finished.
All three compilers now cap how deep instantiation goes: an instance
discovered while specialising another is one generation deeper, and past 64
generations instantiation stops with an error at the generic impl, naming the
type.

A method is specialised only where a call reaches it (AGAST #3617, #3341), so
the ticket's first program, `fn wrap(self) -> Cell<Cell<T>>` called once,
now compiles: Cell<Cell<i32>>'s `wrap` is never called
(test_impl_specialize_on_use.py).

The ritz1 compilers run under a timeout, so a regression to the old hang fails
here rather than stalling the suite.
"""

import os
import subprocess

import pytest

from test_right_shift import RITZ1_BUILD, RITZ_ROOT, _run

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# The ticket's program.  The impl is on line 3, column 1.
RECURSIVE = """\
struct Cell<T>
    v: T
impl<T> Cell<T>
    fn deep(self: @Cell<T>) -> i32
        let c = Cell<Cell<T>> { v: *self }
        c.deep()
fn main() -> i32
    let c = Cell<i32> { v: 9 }
    c.deep()
"""

# Nesting the program spells out is finite, so it still compiles: two levels
# of Cell, each with an impl whose method names nothing deeper.
FINITE = """\
struct Cell<T>
    v: T
impl<T> Cell<T>
    fn get(self: @Cell<T>) -> T
        self.v
fn main() -> i32
    let c = Cell<Cell<i32>> { v: Cell<i32> { v: 9 } }
    c.get().get() - 9
"""


def _compile(request, compiler, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    if compiler == "ritz0":
        run_ritz0 = request.getfixturevalue("run_ritz0")
        return run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=120)
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    # A hang is the bug: TimeoutExpired fails the test instead of the suite.
    return subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=60)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_recursive_impl_is_refused_at_the_impl(request, compiler, tmp_path):
    proc = _compile(request, compiler, tmp_path, RECURSIVE)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, out
    assert "Traceback" not in out, out
    assert "unit.ritz:3:1: " in out, out
    assert "instantiating `Cell` recurses: Cell<Cell<...>>" in out, out


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_finite_nesting_still_compiles(request, compiler, tmp_path):
    assert _run(request, compiler, tmp_path, FINITE) == 0
