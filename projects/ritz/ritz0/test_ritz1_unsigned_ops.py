"""AGAST #1604: ritz1 uses unsigned compares and div/mod for u64 operands.

THE DEFECT

emit_expr_binary (ritz1/src/emitter_expr_arith.ritz) always emitted
`icmp slt/sgt/sle/sge`, `sdiv` and `srem` for `<` `>` `<=` `>=` `/` `%`. ritz1
holds every integer in an i64. u8/u16/u32 values are zero-extended into it, so
they are never negative there and the signed ops happen to agree. A u64 with the
top bit set is negative as an i64, so

    let a: u64 = 0xffffffffffffff00 as u64
    a > 1            # ritz1: false (sgt)   ritz0: true (ugt)
    a / 16           # ritz1: sdiv, a negative quotient

ritz0 picks the unsigned op when either operand is unsigned
(_infer_unsigned_expr). ritz1 now does the same whenever either operand is u64.

Oracle: ritz0 compiles every program, and both binaries exit 42 (each failing
check returns its own code, so a mismatch names the check). The IR test
checks the instructions directly, so a fix that gets the answer right some other
way still has to emit icmp u* / udiv / urem.
"""

import re

import pytest

from test_ritz1_builtin_struct_shadow import _run, ritz1_bin  # noqa: F401

TOP = 0xFFFFFFFFFFFFFF00

# u64 locals with the top bit set: every ordering predicate, both directions,
# against a u64 local and against a bare literal.
U64_COMPARE = f"""\
pub fn main() -> i32
    let a: u64 = {TOP:#x} as u64
    let b: u64 = 1 as u64
    if not (a > b)
        return 1
    if a < b
        return 2
    if not (a >= b)
        return 3
    if a <= b
        return 4
    if not (b < a)
        return 5
    if b > a
        return 6
    if not (a > 1)
        return 7
    if a < 1
        return 8
    if not (a >= a)
        return 9
    if not (a <= a)
        return 10
    # Only the right operand is u64: the literal on the left is i64.
    if not (1 < a)
        return 11
    if 1 >= a
        return 12
    return 42
"""

# u64 division and remainder with the top bit set.
U64_DIVMOD = f"""\
pub fn main() -> i32
    let a: u64 = {TOP:#x} as u64
    let d: u64 = 16 as u64
    let q: u64 = a / d
    if q != {TOP // 16:#x} as u64
        return 1
    let r: u64 = a % (7 as u64)
    if r != {TOP % 7} as u64
        return 2
    if a / (3 as u64) != {TOP // 3:#x} as u64
        return 3
    if (a + (5 as u64)) % (256 as u64) != 5 as u64
        return 4
    var c: u64 = a
    c = c / (2 as u64)
    if c != {TOP // 2:#x} as u64
        return 5
    var m: u64 = a + (3 as u64)
    m = m % (10 as u64)
    if m != {(TOP + 3) % 10} as u64
        return 6
    return 42
"""

# The same, through u64 parameters (the ticket notes params are affected too).
U64_PARAMS = f"""\
fn gt(x: u64, y: u64) -> bool
    x > y

fn lt(x: u64, y: u64) -> bool
    x < y

fn ge(x: u64, y: u64) -> bool
    x >= y

fn le(x: u64, y: u64) -> bool
    x <= y

fn dv(x: u64, y: u64) -> u64
    x / y

fn md(x: u64, y: u64) -> u64
    x % y

pub fn main() -> i32
    let a: u64 = {TOP:#x} as u64
    let b: u64 = 1 as u64
    if not gt(a, b)
        return 1
    if lt(a, b)
        return 2
    if not ge(a, b)
        return 3
    if le(a, b)
        return 4
    if dv(a, 16 as u64) != {TOP // 16:#x} as u64
        return 5
    if md(a, 7 as u64) != {TOP % 7} as u64
        return 6
    return 42
"""

# u8/u16/u32 with the top bit of their own width set. These are zero-extended
# into ritz1's i64 and were already right; they guard against a fix that
# breaks the narrow widths.
NARROW = """\
fn cmp8(x: u8, y: u8) -> bool
    x > y

fn cmp16(x: u16, y: u16) -> bool
    x > y

fn cmp32(x: u32, y: u32) -> bool
    x > y

pub fn main() -> i32
    let a8: u8 = 200 as u8
    let b8: u8 = 3 as u8
    if not (a8 > b8)
        return 1
    if a8 / b8 != 66 as u8
        return 2
    if a8 % b8 != 2 as u8
        return 3
    if not cmp8(a8, b8)
        return 4
    let a16: u16 = 0xff00 as u16
    let b16: u16 = 7 as u16
    if a16 < b16
        return 5
    if a16 / b16 != 9325 as u16
        return 6
    if a16 % b16 != 5 as u16
        return 7
    if not cmp16(a16, b16)
        return 8
    let a32: u32 = 0xffffff00 as u32
    let b32: u32 = 7 as u32
    if a32 <= b32
        return 9
    if a32 / b32 != 613566720 as u32
        return 10
    if a32 % b32 != 0 as u32
        return 11
    if not cmp32(a32, b32)
        return 12
    return 42
"""

# Signed controls: i64 must keep slt/sdiv/srem.
SIGNED = """\
pub fn main() -> i32
    let n: i64 = -7
    let one: i64 = 1
    if not (n < one)
        return 1
    if n > one
        return 2
    if n / 2 != -3
        return 3
    if n % 2 != -1
        return 4
    let w: i32 = -9
    if w >= 0
        return 5
    if w / 2 != -4
        return 6
    return 42
"""

CASES = [
    ("u64_compare", U64_COMPARE),
    ("u64_divmod", U64_DIVMOD),
    ("u64_params", U64_PARAMS),
    ("narrow", NARROW),
    ("signed", SIGNED),
]


@pytest.mark.integration
@pytest.mark.parametrize("name,program", CASES, ids=[c[0] for c in CASES])
def test_unsigned_ops_match_ritz0(ritz1_bin, tmp_path, name, program):  # noqa: F811
    expected = _run("ritz0", tmp_path, name, program)
    got = _run("ritz1", tmp_path, name, program)
    assert expected == 42, f"{name}: ritz0 exit {expected} (test program is wrong)"
    assert got == expected, f"{name}: ritz1 exit {got}, ritz0 exit {expected}"


def _fn_body(ll_text: str, name: str) -> str:
    m = re.search(rf"^define [^\n]*@{name}\(.*?^\}}", ll_text, re.M | re.S)
    assert m, f"no definition of @{name} in ritz1 IR"
    return m.group(0)


# One fn per op, so each instruction is checked where it is emitted.
IR_PROGRAM = """\
fn ult(x: u64, y: u64) -> bool
    x < y

fn ugt(x: u64, y: u64) -> bool
    x > y

fn ule(x: u64, y: u64) -> bool
    x <= y

fn uge(x: u64, y: u64) -> bool
    x >= y

fn udv(x: u64, y: u64) -> u64
    x / y

fn urm(x: u64, y: u64) -> u64
    x % y

fn ulit(x: u64) -> bool
    x > 1

fn ulitr(x: u64) -> bool
    1 < x

fn udvr(x: u64) -> u64
    1000 / x

fn slt(x: i64, y: i64) -> bool
    x < y

fn sdv(x: i64, y: i64) -> i64
    x / y

fn srm(x: i64, y: i64) -> i64
    x % y

pub fn main() -> i32
    return 0
"""

IR_EXPECT = {
    "ult": "icmp ult i64",
    "ugt": "icmp ugt i64",
    "ule": "icmp ule i64",
    "uge": "icmp uge i64",
    "udv": "udiv i64",
    "urm": "urem i64",
    "ulit": "icmp ugt i64",
    "ulitr": "icmp ult i64",
    "udvr": "udiv i64",
    "slt": "icmp slt i64",
    "sdv": "sdiv i64",
    "srm": "srem i64",
}


@pytest.mark.integration
def test_unsigned_ops_ir(ritz1_bin, tmp_path):  # noqa: F811
    assert _run("ritz1", tmp_path, "ir", IR_PROGRAM) == 0
    ll = (tmp_path / "ir_ritz1.ll").read_text()
    wrong = []
    for fn, instr in IR_EXPECT.items():
        body = _fn_body(ll, fn)
        # Every ordering compare / div / rem in the fn: (signedness letter, op).
        ops = re.findall(
            r"icmp ([us])(?:lt|gt|le|ge) i64|\b([us])(?:div|rem) i64", body
        )
        letters = {a or b for a, b in ops}
        want = "s" if fn.startswith("s") else "u"
        if instr not in body or letters != {want}:
            wrong.append(f"@{fn}: expected only `{instr}`-signedness ops:\n{body}")
    assert not wrong, "\n\n".join(wrong)
