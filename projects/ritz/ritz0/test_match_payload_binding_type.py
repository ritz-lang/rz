#!/usr/bin/env python3
"""A match binding of a narrow integer payload has the payload's type (AGAST #3116).

`Full(v)` over a `Slot<u8>` bound `v` as an i64 on ritz1: `sizeof(v)` was 8
and `(v + v) / 2` did not wrap at u8, both silently.  ritz0 binds it as the
declared u8, as a `let v: u8` would be.  Every enum kind took the same i64
path: a generic instance, a concrete enum, Option, and either side of Result.

Each arm yields `sizeof(v) * 10 + w`, w 1 when `(v + v) / 2` wrapped at the
payload's width (each value doubles past its type's range).  A row per path
the binding is typed on; the concrete row carries all six narrow widths, the
tagged rows one width and sign each, so the rule is covered without the cross
product (docs/TESTING.md, "What a ritz0 pytest case costs").
"""

import pytest

from test_generic_enum_instance import COMPILERS, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

# type -> (a value whose double overflows it, (v + v) / 2 after the wrap)
WRAP = {"u8": (200, 72), "i8": (100, -28), "u16": (40000, 7232), "i16": (20000, -12768),
        "u32": (3000000000, 852516352), "i32": (2000000000, -147483648)}


def _arm(pattern, ty):
    return f"        {pattern} => sizeof(v) as i32 * 10 + (if ((v + v) / 2) == {WRAP[ty][1]} then 1 else 0)\n"


def _tagged(ty, slot, ctor, other):
    return (f"fn main() -> i32\n    let x: {ty} = {WRAP[ty][0]}\n    let s: {slot} = {ctor}(x)\n"
            f"    match s\n" + _arm(f"{ctor}(v)", ty) + f"        {other} => 0\n")


CONCRETE_TYPES = ["u8", "i8", "u16", "i16", "u32", "i32"]
CONCRETE = (
    "enum E\n" + "".join(f"    V{t}({t})\n" for t in CONCRETE_TYPES)
    + "fn f(e: E) -> i32\n    match e\n" + "".join(_arm(f"V{t}(v)", t) for t in CONCRETE_TYPES)
    + "fn main() -> i32\n    var n: i32 = 0\n"
    + "".join(f"    let x{t}: {t} = {WRAP[t][0]}\n    n = n + f(V{t}(x{t}))\n" for t in CONCRETE_TYPES)
    + "    n\n")

# name -> (program, exit code)
RUNS = {
    # The ticket's: a generic instance's payload.
    "generic_instance_u8": ("enum Slot<T>\n    Full(T)\n    Empty\n" + _tagged("u8", "Slot<u8>", "Full", "Empty"), 11),
    # Each width and sign, through a concrete enum's declared field type.
    "concrete_enum_all_widths": (CONCRETE, (1 + 1 + 2 + 2 + 4 + 4) * 10 + 6),
    "option_some_i16": (_tagged("i16", "Option<i16>", "Some", "None"), 21),
    "result_ok_u32": (_tagged("u32", "Result<u32, i64>", "Ok", "Err(e)"), 41),
    "result_err_i8": (_tagged("i8", "Result<i64, i8>", "Err", "Ok(e)"), 11),
}


@pytest.fixture
def need_ritz1(request):
    def need(compiler):
        if compiler != "ritz0":
            request.getfixturevalue("ritz1_bin")
    return need


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_a_narrow_payload_binds_at_its_type(tmp_path, need_ritz1, compiler, name):
    need_ritz1(compiler)
    src, code = RUNS[name]
    assert _run(compiler, tmp_path, src) == code, f"{compiler}, {name}"
