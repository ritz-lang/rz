"""AGAST #2128: print / eprint render unsigned integers unsigned.

THE BUG

    let a: u8 = 200
    print("{a}\\n")          # printed -56

ritz0's `_emit_print_value` sign-extended every LLVM integer (the LLVM type
carries no signedness), and ritz1's `emit_print_value` deliberately truncated
and sign-extended to match it byte for byte. So `u8` 200 printed `-56`,
`u32` 4000000000 printed `-294967296`, and `u64::MAX` printed `-1`.

THE FIX

Signedness comes from the Ritz type (ritz0 `_infer_ritz_type`, ritz1
`get_expr_type`). An unsigned value is zero-extended and formatted by
`@__ritz_fmt_int(buf, v, signed=0)`, the integer core #1824 added for
`format_into`, which divides unsigned. Signed values go through the same
helper with `signed=1`, so print, eprint and format_into share one formatter.

ORACLE

Each program is compiled by ritz0 and by ritz1 and run. Both binaries must
exit 0, and stdout and stderr are each pinned to literal bytes, so a bug the
two compilers share cannot pass.
"""

import pytest

from test_eprint_interpolation import _assert_parity

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("ritz1_bin")]


# The matrix body, with PRINT standing for `print` or `eprint`.
MATRIX = """\
struct Rec
    small: u8
    wide: u64

fn big32() -> u32
    return 4000000000

fn max64() -> u64
    return 18446744073709551615

pub fn main() -> i32
    let u8z: u8 = 0
    let u8h: u8 = 200
    let u8m: u8 = 255
    let u16z: u16 = 0
    let u16h: u16 = 40000
    let u16m: u16 = 65535
    let u32z: u32 = 0
    let u32h: u32 = 3000000000
    let u32m: u32 = 4294967295
    let u64z: u64 = 0
    # 2^63 + 1: ritz1 hangs on the literal 2^63 itself (AGAST #2129).
    let u64h: u64 = 9223372036854775809
    let u64m: u64 = 18446744073709551615
    PRINT("u8 {u8z} {u8h} {u8m}\\n")
    PRINT("u16 {u16z} {u16h} {u16m}\\n")
    PRINT("u32 {u32z} {u32h} {u32m}\\n")
    PRINT("u64 {u64z} {u64h} {u64m}\\n")

    let i8n: i8 = -128
    let i8x: i8 = 127
    let i16n: i16 = -32768
    let i16x: i16 = 32767
    let i32n: i32 = -2147483648
    let i32x: i32 = 2147483647
    let i64n: i64 = -9223372036854775807 - 1
    let i64x: i64 = 9223372036854775807
    PRINT("i8 {i8n} {i8x}\\n")
    PRINT("i16 {i16n} {i16x}\\n")
    PRINT("i32 {i32n} {i32x}\\n")
    PRINT("i64 {i64n} {i64x}\\n")

    var r: Rec
    r.small = 250
    r.wide = 18446744073709551614
    PRINT("field {r.small} {r.wide}\\n")
    PRINT("call {big32()} {max64()}\\n")
    let n: i32 = -1
    let m: i64 = -2
    let w: i64 = 456
    PRINT("cast {n as u32} {m as u64} {w as u8}\\n")
    return 0
"""

EXPECTED = (
    b"u8 0 200 255\n"
    b"u16 0 40000 65535\n"
    b"u32 0 3000000000 4294967295\n"
    b"u64 0 9223372036854775809 18446744073709551615\n"
    b"i8 -128 127\n"
    b"i16 -32768 32767\n"
    b"i32 -2147483648 2147483647\n"
    b"i64 -9223372036854775808 9223372036854775807\n"
    b"field 250 18446744073709551614\n"
    b"call 4000000000 18446744073709551615\n"
    b"cast 4294967295 18446744073709551614 200\n"
)


@pytest.mark.parametrize("builtin", ["print", "eprint"])
def test_integer_matrix_prints_by_signedness(tmp_path, builtin):
    out, err = (EXPECTED, b"") if builtin == "print" else (b"", EXPECTED)
    _assert_parity(
        tmp_path, f"unsigned_{builtin}", MATRIX.replace("PRINT", builtin), out, err
    )


# The ticket's own reproduction, kept verbatim.
TICKET = """\
pub fn main() -> i32
    let a: u8 = 200
    let b: u16 = 65000
    let c: u32 = 4000000000
    let d: u64 = 18446744073709551615
    print("{a} {b} {c} {d}\\n")
    return 0
"""


def test_ticket_reproduction(tmp_path):
    _assert_parity(
        tmp_path,
        "unsigned_ticket",
        TICKET,
        b"200 65000 4000000000 18446744073709551615\n",
        b"",
    )
