#!/usr/bin/env python3
"""A trait bound is checked where the generic is instantiated, located
(LANGUAGE_SPEC §11.5, LARB R55, AGAST #3468).

`<T: A + B>` on a fn, struct, enum or impl: each type argument needs an impl
of each trait, exact or through a generic impl.  Otherwise the error is at
the type argument, or at the call when the argument is inferred:

    `Nope` doesn't implement `Area`, which `T` of `total` requires

An unknown trait is an error at the bound, and at an impl's trait name
(#4197).  Before #3468 a failed bound was an
unlocated Python TypeError, and an unknown trait read "does not implement".
A generic impl satisfying a bound is test_trait_bounds.ritz's run row.

ritz0 only: ritz1's half is #3469.  One row per code path.
"""

import os
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent

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

# Each row: (program after PRELUDE, line:column of the error, message).
# PRELUDE is 10 lines, so a row's first line is line 11.  `Bag<Nope>`,
# unbounded, names `Nope` first: the error is still at the bounded use.
ROWS = {
    # Defect 1, explicit: at the type argument `Nope`.
    "explicit_fn_arg": (
        "fn main() -> i32\n"
        "    var b: Bag<Nope>\n"
        "    total<Nope>(@b.v) as i32\n",
        "13:11", "`Nope` doesn't implement `Area`, which `T` of `total` requires"),
    # Defect 1, inferred: at the call.
    "inferred_fn_arg": (
        "fn main() -> i32\n"
        "    var b: Bag<Nope>\n"
        "    total(@b.v) as i32\n",
        "13:5", "`Nope` doesn't implement `Area`, which `T` of `total` requires"),
    # A struct's bound, from a type annotation: at the type argument.
    "struct_type_arg": (
        "fn main() -> i32\n"
        "    var h: Holder<Nope>\n"
        "    0\n",
        "12:19", "`Nope` doesn't implement `Area`, which `T` of `Holder` requires"),
    # An impl's bound is on its type's args: `W<Nope>` instantiates it.
    "impl_bound": (
        "struct W<T>\n"
        "    v: T\n"
        "impl<T: Area> W<T>\n"
        "    fn get(self: @W<T>) -> i64\n"
        "        0\n"
        "fn main() -> i32\n"
        "    var w: W<Nope>\n"
        "    0\n",
        "17:14", "`Nope` doesn't implement `Area`, which `T` of `impl W` requires"),
    # Defect 3: an unknown trait is an error at the bound, used or not.
    "unknown_trait": (
        "fn f<U: Nonesuch>(x: U) -> U\n"
        "    x\n"
        "fn main() -> i32\n"
        "    0\n",
        "11:9", "unknown trait `Nonesuch` in the bound on `U`"),
    # ...and at an impl's trait name (#4197): it compiled silently.  A
    # declared trait (`Area`) and a compiler trait (`Drop`) are known.
    "unknown_impl_trait": (
        "impl Area for Nope\n"
        "    fn area(self: @Nope) -> i64\n"
        "        0\n"
        "impl Drop for Nope\n"
        "    fn drop(self: @&Nope)\n"
        "        return\n"
        "impl Nonesuch for Nope\n"
        "    fn g(self: @Nope) -> i32\n"
        "        0\n"
        "fn main() -> i32\n"
        "    0\n",
        "17:6", "unknown trait `Nonesuch`"),
}


@pytest.mark.parametrize("row", sorted(ROWS))
def test_failed_bound_is_located(row, tmp_path):
    body, where, message = ROWS[row]
    src = tmp_path / "unit.ritz"
    src.write_text(PRELUDE + body)
    proc = run_ritz0([str(src), "-o", str(tmp_path / "unit.ll")], cwd=tmp_path,
                     env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)), timeout=120)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, out
    assert "Traceback" not in out and "TypeError" not in out, out
    assert f"unit.ritz:{where}: {message}" in out, out
    assert "does not implement" not in out, out
    # Only the row's own: a known trait (`Area`, `Drop`) is never "unknown".
    assert out.count("unknown trait") == message.count("unknown trait"), out
