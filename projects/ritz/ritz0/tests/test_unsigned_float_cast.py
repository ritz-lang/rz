"""AGAST #2192: an `as` between an unsigned integer and a float is unsigned.

    let x: u8 = 255
    let f = x as f32        # was -1.0: sitofp read the top bit as a sign
    let g: f64 = 200.0
    let y = g as u8         # was poison: fptosi to i8 can't hold 200

ritz0 emitted sitofp / fptosi for every int <-> float cast.  ritz1 carries
integers in i64, so u8/u16/u32 were already zero-extended, but u64 had the
same bug.  An int -> float cast is uitofp when the source is unsigned; a
float -> int cast converts by the target's signedness.

LANGUAGE_SPEC §7.5 "Float to integer": a float -> integer `as` rounds toward
zero and saturates at the target's range, and NaN converts to 0, on all three
compilers (llvm.fptoui.sat / llvm.fptosi.sat).  Before, an out-of-range value
was poison, so `200.0 as u8` gave whatever the instruction left behind (and
a check on it could be optimised away entirely).

Each unsigned row's value has its top bit set, so a signed conversion changes
it, and is exact in f32 and f64.  Every check has its own exit code.  The
values come from typed locals, never literals, so the conversion is the
runtime instruction rather than a folded constant.
"""

import pytest
from test_ref_into_value import COMPILERS, _run

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = [pytest.mark.integration, pytest.mark.batched]

# type -> (an integer value, the same value as a float literal).  The unsigned
# values have the top bit set; the signed ones are controls that must stay
# negative.  All are exact in both f32 and f64.
VALUES = {
    "u8": ("200", "200.0"),
    "u16": ("40000", "40000.0"),
    "u32": ("4000000000", "4000000000.0"),
    # 0xC000000000000000 = 2^63 + 2^62
    "u64": ("13835058055282163712", "13835058055282163712.0"),
    "i8": ("-56", "-56.0"),
    "i64": ("-4000000000", "-4000000000.0"),
}


def _to_float(ty: str) -> str:
    v, fv = VALUES[ty]
    return f"""\
fn f(x: {ty}) -> i32
    let d = x as f64
    let ed: f64 = {fv}
    if d != ed
        return 1
    let s = x as f32
    let es: f32 = {fv}
    if s != es
        return 2
    if d < 0.0 and ed > 0.0
        return 3
    return 0

pub fn main() -> i32
    let x: {ty} = {v}
    f(x)
"""


def _from_float(ty: str) -> str:
    v, fv = VALUES[ty]
    return f"""\
fn f(d: f64, s: f32) -> i32
    let a = d as {ty}
    let e: {ty} = {v}
    if a != e
        return 1
    let b = s as {ty}
    if b != e
        return 2
    return 0

pub fn main() -> i32
    let d: f64 = {fv}
    let s: f32 = {fv}
    f(d, s)
"""


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(VALUES))
def test_integer_to_float_keeps_the_value(tmp_path, compiler, ty):
    assert _run(compiler, tmp_path, f"to_float_{ty}", _to_float(ty)) == 0


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(VALUES))
def test_float_to_integer_keeps_the_value(tmp_path, compiler, ty):
    assert _run(compiler, tmp_path, f"from_float_{ty}", _from_float(ty)) == 0


# Out of range (§7.5): saturate at the target's bounds; NaN is 0.
# name -> (target type, float source expression, check that the result `r` is right)
SATURATE = {
    "u8_above": ("u8", "300.0", "r != 255"),
    "u8_negative": ("u8", "0.0 - 1.0", "r != 0"),
    "u8_nan": ("u8", "z / z", "r != 0"),
    "u16_above": ("u16", "70000.0", "r != 65535"),
    "u32_above": ("u32", "5000000000.0", "r != 4294967295"),
    "u64_above": ("u64", "100000000000000000000.0", "r + 1 != 0"),
    "u64_negative": ("u64", "0.0 - 1.0", "r != 0"),
    "i8_above": ("i8", "200.0", "r != 127"),
    "i32_below": ("i32", "0.0 - 10000000000.0", "r != -2147483648"),
    "i64_nan": ("i64", "z / z", "r != 0"),
}


def _saturate(name: str) -> str:
    ty, src, bad = SATURATE[name]
    return f"""\
fn f(z: f64) -> i32
    let d: f64 = {src}
    let r = d as {ty}
    if {bad}
        return 1
    let s: f32 = d as f32
    let q = s as {ty}
    if q != r
        return 2
    return 0

pub fn main() -> i32
    let z: f64 = 0.0
    f(z)
"""


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(SATURATE))
def test_out_of_range_float_saturates(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, f"sat_{name}", _saturate(name)) == 0
