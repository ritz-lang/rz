"""R36's revisit (#4294): a trait impl on a primitive or built-in, in the
trait's file only.

LARB R36 closed primitives to `impl` (#3288).  Aaron's revisit (2026-11-20,
rz-larb) makes a *trait* impl legal — and only in the file that declares the
trait:

    impl Display for i64
    impl Display for bool
    impl Display for StrView
    impl Display for Span<u8>
    impl Display for *u8

An inherent impl stays "`u8` is a built-in type; it can't have an `impl`"
(test_impl_unknown_type_refused.py), and one outside the trait's file is
"`i64` is a built-in type: a trait impl for it must be in the trait's file
(§12.2)".  Option and Result are not in the ruling and stay closed
(test_impl_builtin_refused.py).

The positive rows put the trait and the impl in one file, which is the
trait's file, and call the method through the receiver's primitive/built-in
type — the dispatch half of the ruling, and (#4946) a method chained onto
that call's result.  Each returns 42.  ritz0, ritz1 and
ritz1_selfhosted all agree.
"""

import os
import re
import subprocess

import pytest

from ritz0_inproc import run_ritz0
from test_ref_into_value import COMPILERS, RITZ1_BUILD, RITZ_ROOT, _located, _run

pytestmark = pytest.mark.integration


# name -> (program, exit code).  A trait `Pick`/`Size`/`Truth`/`Zero` is
# declared here, so this file is the trait's file.
ROWS = {
    # AGAST #4946: the method's result is typed through the primitive
    # receiver, so a method chained onto it resolves: on a bounded type
    # param at i64 (`a.rank(@b).is_lt()`, T: Rank) and on an i64 local in a
    # bare condition.
    "i64": ("""\
enum Order
    Less
    NotLess

impl Order
    fn is_lt(self: Order) -> bool
        self == Order.Less

trait Rank
    fn rank(self: @Self, other: @Self) -> Order

impl Rank for i64
    fn rank(self: @i64, other: @i64) -> Order
        if *self < *other then Order.Less else Order.NotLess

fn first<T: Rank>(a: T, b: T) -> bool
    a.rank(@b).is_lt()

pub fn main() -> i32
    let x: i64 = 41
    let y: i64 = 42
    if not first<i64>(x, y) or first<i64>(y, x)
        return 1
    if x.rank(@y).is_lt()
        return 42
    2
""", 42),
    "bool": ("""\
trait Truth
    fn truth(self: @Self) -> i32

impl Truth for bool
    fn truth(self: @bool) -> i32
        if *self
            return 7
        0

pub fn main() -> i32
    let b: bool = true
    b.truth() * 6
""", 42),
    "strview": ("""\
trait Size
    fn size(self: @Self) -> i32

impl Size for StrView
    fn size(self: @StrView) -> i32
        self.len as i32

pub fn main() -> i32
    let s: StrView = "hello"
    s.size() + 37
""", 42),
    "span_u8": ("""\
trait Size
    fn size(self: @Self) -> i32

impl Size for Span<u8>
    fn size(self: @Span<u8>) -> i32
        self.len as i32

pub fn main() -> i32
    var a: [3]u8
    let s: Span<u8> = Span { ptr: @a[0], len: 3 }
    s.size() * 14
""", 42),
    "pointer_u8": ("""\
trait Zero
    fn zero(self: @Self) -> i32

impl Zero for *u8
    fn zero(self: @*u8) -> i32
        if *self == null
            return 42
        0

pub fn main() -> i32
    let p: *u8 = null
    p.zero()
""", 42),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(ROWS))
def test_trait_impl_on_builtin_in_trait_file(request, tmp_path, compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    src, code = ROWS[row]
    assert _run(compiler, tmp_path, f"builtin_{row}", src) == code


# --- the same impl in another file: refused --------------------------------

TRAIT_FILE = """\
pub trait Pick
    fn pick(self: @Self) -> i32
"""

# name -> (impl target as written, expected message).  `^` marks where the
# diagnostic must be: main.ritz line 3, the target's column.
MISPLACED = {
    "i64": ("i64", "`i64` is a built-in type: a trait impl for it must be "
                    "in the trait's file (§12.2)"),
    "pointer_u8": ("*u8", "`*u8` is a built-in type: a trait impl for it must "
                          "be in the trait's file (§12.2)"),
    "span_u8": ("Span<u8>", "`Span` is a built-in type: a trait impl for it "
                            "must be in the trait's file (§12.2)"),
}


def _emit_pair(compiler, work):
    """Compile work/main.ritz (which imports work/a.ritz); return the process."""
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{work}")
    cmd = ["main.ritz", "-o", "main.ll"]
    if compiler == "ritz0":
        return run_ritz0(cmd, cwd=work, env=env, timeout=300)
    return subprocess.run([str(RITZ1_BUILD / compiler), *cmd], cwd=work, env=env,
                          capture_output=True, text=True, timeout=300)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(MISPLACED))
def test_trait_impl_on_builtin_outside_trait_file_refused(request, tmp_path,
                                                          compiler, row):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    target, message = MISPLACED[row]
    marked = f"""\
import a

impl Pick for ^{target}
    fn pick(self: @{target}) -> i32
        return 0

pub fn main() -> i32
    return 0
"""
    src, where = _located(marked)
    work = tmp_path / f"misplaced_{row}_{compiler}"
    work.mkdir()
    (work / "a.ritz").write_text(TRAIT_FILE)
    (work / "main.ritz").write_text(src)
    proc = _emit_pair(compiler, work)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {row}:\n{src}"
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert (where, message) in found, (
        f"{compiler}: {row}, wanted {where} {message!r}:\n{src}\n{out[-2000:]}")
