"""Regression tests for AGAST #2073: a method called on a struct-valued call
result (`mk(v).scale(f)`) must spill the receiver as `%S`, not `i64`.

emit_expr_method's EXPR_CALL receiver arm did `alloca i64` and then
`store i64 %<%S value>`, which clang rejects.  Only tagged enums got a
struct-typed slot.  Each program is compiled by both ritz0 (the oracle) and
ritz1, and ritz1's exit code must match ritz0's.  The cases cover a
one-field f64 struct, a two-field integer struct, a u8 struct, a large
sret-returned struct (>= SRET_MIN_BYTES, already in memory), a mutating
`self: *S` method on the temporary, and nested call-result receivers.
"""

import os
import re
import subprocess

import pytest

from test_ritz1_builtin_struct_shadow import RITZ1_BIN, RITZ_ROOT, _run

# The ticket: a one-field `{ double }` struct.  0.75 * 2 = 1.5, then * 2 = 3.
F64_ONE = """\
struct Pt
    x: f64

impl Pt
    fn scale(self: @Pt, f: f64) -> f64
        self.x * f

fn mk(v: f64) -> Pt
    Pt { x: v }

pub fn main() -> i32
    let b: f64 = mk(0.75).scale(2.0)
    return (b * 2.0) as i32
"""

# A two-field integer struct and a method that reads both fields: 10 + 7.
I64_PAIR = """\
struct Pair
    a: i64
    b: i64

impl Pair
    fn sum(self: @Pair) -> i64
        self.a + self.b

fn mk(a: i64, b: i64) -> Pair
    Pair { a: a, b: b }

pub fn main() -> i32
    return mk(10, 7).sum() as i32
"""

# A struct narrower than i64: the slot must not be `i64`-sized either.
U8_ONE = """\
struct Byte
    v: u8

impl Byte
    fn get(self: @Byte) -> u8
        self.v

fn mk(v: u8) -> Byte
    Byte { v: v }

pub fn main() -> i32
    return mk(42 as u8).get() as i32
"""

# A struct of 40 i64s (320 bytes) is returned via sret; the method reads the
# first and last element: 5 + 6.
SRET_BIG = """\
struct Big
    xs: [40]i64

impl Big
    fn ends(self: @Big) -> i64
        self.xs[0] + self.xs[39]

fn mk(a: i64, b: i64) -> Big
    var g: Big
    var i: i64 = 0
    while i < 40
        g.xs[i] = 0
        i = i + 1
    g.xs[0] = a
    g.xs[39] = b
    g

pub fn main() -> i32
    return mk(5, 6).ends() as i32
"""

# A mutating method on the temporary: it must see the call's value, and its
# write lands in the spill slot.  4 + 1 = 5.
MUTATE = """\
struct Ctr
    n: i32

impl Ctr
    fn bump(self: *Ctr) -> i32
        self.n = self.n + 1
        self.n

fn mk(n: i32) -> Ctr
    Ctr { n: n }

pub fn main() -> i32
    return mk(4).bump()
"""

# Two call-result receivers in one expression, one nested in another's
# argument: mk(mk(3).get() + 2).get() + mk(1).get() = 5 + 1 = 6.
NESTED = """\
struct W
    v: i32

impl W
    fn get(self: @W) -> i32
        self.v

fn mk(v: i32) -> W
    W { v: v }

pub fn main() -> i32
    return mk(mk(3).get() + 2).get() + mk(1).get()
"""

CASES = {
    "f64_one": (F64_ONE, 3),
    "i64_pair": (I64_PAIR, 17),
    "u8_one": (U8_ONE, 42),
    "sret_big": (SRET_BIG, 11),
    "mutate": (MUTATE, 5),
    "nested": (NESTED, 6),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    prog, want = CASES[name]
    assert _run("ritz0", tmp_path, name, prog) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_matches_ritz0(ritz1_bin, tmp_path, name):
    """AGAST #2073. Before the fix: `store i64 %<%S>` -> clang error."""
    prog, _ = CASES[name]
    assert _run("ritz1", tmp_path, name, prog) == _run("ritz0", tmp_path, name, prog)


@pytest.mark.integration
def test_ritz1_sret_receiver_is_the_sret_slot(ritz1_bin, tmp_path):
    """An sret call's result is already in memory: the method must get that
    slot as `self`, not a fresh copy (which exit codes alone cannot see)."""
    src = tmp_path / "sret_big.ritz"
    src.write_text(SRET_BIG)
    ll = tmp_path / "sret_big.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll)], env=env, check=True, timeout=300
    )
    ir = ll.read_text()
    slot = re.search(r"call void @mk\(ptr sret\(%Big\) (%[\w.]+)", ir)
    recv = re.search(r"call i64 @Big_ends\(ptr (%[\w.]+)\)", ir)
    assert slot and recv, ir
    assert recv.group(1) == slot.group(1), ir
