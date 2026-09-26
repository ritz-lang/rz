"""AGAST #1506: ritz1 lowers BitOps methods on integer-primitive receivers.

THE DEFECT

emit_expr_method (ritz1/src/emitter_expr_call.ritz) resolved a receiver type
only for struct-typed receivers. `x.rotl(3)` on a `u32` left type_name null
and failed with "cannot determine receiver type for method call", which kept
cryptosec's chacha20 (`(state[d] ^ state[a]).rotl(16)`) -- and so mausoleum
and nexus -- from building under ritz1.

ritz0 lowers the BitOps set on u8..u64 / i8..i64 to LLVM intrinsics:

    rotl  -> llvm.fshl.iN(x, x, n)      rotr -> llvm.fshr.iN(x, x, n)
    clz   -> llvm.ctlz.iN(x, false)     ctz  -> llvm.cttz.iN(x, false)
    popcnt-> llvm.ctpop.iN(x)           swap_bytes -> llvm.bswap.iN(x)

The rotate cases are chosen so a rotate at the WRONG width (ritz1 carries
every integer in an i64 register) gives a different answer: rotating
0x80000001 left by 1 is 3 at 32 bits but 0x100000002 at 64.

Oracle: ritz0 builds and runs every program with the same exit code.
"""

import subprocess

import pytest

from test_ritz1_builtin_struct_shadow import _run, ritz1_bin  # noqa: F401

# The ticket's repro.
REPRO = """\
pub fn main() -> i32
    let x: u32 = 5
    let y: u32 = x.rotl(3)
    return y as i32
"""

# Wrap-around at 32 bits, both directions, plus a non-literal shift amount.
ROT_WIDTH_U32 = """\
pub fn main() -> i32
    let x: u32 = 0x80000001
    let a: u32 = x.rotl(1)
    let one: u32 = 1
    let b: u32 = one.rotr(1)
    let n: u8 = 4
    let c: u32 = x.rotl(n)
    if a != 3
        return 1
    if b != 0x80000000
        return 2
    if c != 0x18
        return 3
    return 42
"""

# The chacha20 shape: a parenthesised binary receiver over indexed u32 slots.
# The array is a global: a LOCAL `var st: [4]u32` is itself miscompiled by
# ritz1 today (indexed as [4 x i64], #1564), independent of this ticket.
PAREN_RECEIVER = """\
var g_st: [4]u32

fn qr(state: *u32, a: i64, d: i64) -> void
    state[d] = (state[d] ^ state[a]).rotl(16)

pub fn main() -> i32
    g_st[0] = 0x00010000
    g_st[3] = 0x00000001
    qr(@g_st[0], 0, 3)
    let st: *u32 = @g_st[0]
    let x: u32 = 0x80000000
    let y: u32 = 1
    let z: u32 = (x ^ y).rotl(4)
    if st[3] != 0x00010001
        return 1
    if z != 0x18
        return 2
    return 42
"""

# Other widths and a signed receiver.
ROT_WIDTHS = """\
pub fn main() -> i32
    let b: u8 = 0x81
    let b2: u8 = b.rotl(1)
    let h: u16 = 0x8001
    let h2: u16 = h.rotr(1)
    let q: u64 = 0x8000000000000001
    let q2: u64 = q.rotl(1)
    let i: i32 = 0 - 2147483647
    let i2: i32 = i.rotl(1)
    if b2 != 3
        return 1
    if h2 != 0xC000
        return 2
    if q2 != 3
        return 3
    if i2 != 3
        return 4
    # Used directly (not re-truncated through a `let`), the i32 result must
    # be sign-extended: 1 rotr 1 is i32::MIN.
    let one: i32 = 1
    if one.rotr(1) >= 0
        return 5
    return 42
"""

# Receivers whose width get_expr_type alone misreports as i64: a BitOps
# chain (a method call), also inside a binary's left operand; and a count
# (u8) fed back into a rotate.
REFINED_TYPE = """\
pub fn main() -> i32
    let x: u32 = 0x80000001
    let a: u32 = x.rotl(1).rotl(1)
    let b: u32 = (x.rotl(1) ^ x).rotl(1)
    let c: u8 = x.popcnt().rotl(7)
    if a != 6
        return 1
    if b != 5
        return 2
    if c != 1
        return 3
    return 42
"""

# The counting / byte-swap members of the BitOps set.
COUNT_OPS = """\
pub fn main() -> i32
    let x: u32 = 1
    let e: u32 = 8
    let f: u32 = 0xff00ff
    let w: u32 = 0x11223344
    let q: u64 = 1
    if x.clz() != 31
        return 1
    if e.ctz() != 3
        return 2
    if f.popcnt() != 16
        return 3
    if w.swap_bytes() != 0x44332211
        return 4
    if q.clz() != 63
        return 5
    return 42
"""

# Receivers that are a struct field and a call result; the call must be
# evaluated exactly once.
OTHER_RECEIVERS = """\
struct S
    w: u32

var g_calls: i32 = 0

fn mk() -> u32
    g_calls = g_calls + 1
    0x80000001

pub fn main() -> i32
    var s: S
    s.w = 0x01000000
    let a: u32 = s.w.rotl(8)
    let b: u32 = mk().rotl(1)
    if a != 1
        return 1
    if b != 3
        return 2
    if g_calls != 1
        return 3
    return 42
"""

CASES = {
    "repro": (REPRO, 40),
    "rot_width_u32": (ROT_WIDTH_U32, 42),
    "paren_receiver": (PAREN_RECEIVER, 42),
    "rot_widths": (ROT_WIDTHS, 42),
    "count_ops": (COUNT_OPS, 42),
    "refined_type": (REFINED_TYPE, 42),
}

# ritz1-only, hand-derived expectation: ritz0 evaluates a call receiver of a
# BitOps method twice (g_calls == 2, exit 3), so it is no oracle here (#1563).
RITZ1_ONLY = {
    "other_receivers": (OTHER_RECEIVERS, 42),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_oracle(tmp_path, name):
    program, want = CASES[name]
    assert _run("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_int_method(ritz1_bin, tmp_path, name):  # noqa: F811
    program, want = CASES[name]
    assert _run("ritz1", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ1_ONLY))
def test_ritz1_only_int_method(ritz1_bin, tmp_path, name):  # noqa: F811
    program, want = RITZ1_ONLY[name]
    assert _run("ritz1", tmp_path, name, program) == want


@pytest.mark.integration
def test_ritz1_declares_each_used_intrinsic_once(ritz1_bin, tmp_path):  # noqa: F811
    """Every intrinsic called gets exactly one matching `declare`.

    clang 21 implicitly declares an undeclared `@llvm.*` call, so the
    runtime cases above would pass without them; older LLVM tools reject it.
    """
    src = tmp_path / "decls.ritz"
    src.write_text(
        "pub fn main() -> i32\n"
        "    let x: u32 = 5\n"
        "    let q: u64 = 9\n"
        "    let h: u16 = 7\n"
        "    let a: u32 = x.rotl(3) + x.rotl(1) + x.rotr(2)\n"
        "    let b: u64 = q.popcnt() as u64 + q.clz() as u64\n"
        "    let c: u16 = h.swap_bytes() + h.ctz() as u16\n"
        "    return (a as u64 + b + c as u64) as i32\n"
    )
    ll = tmp_path / "decls.ll"
    proc = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    decls = [ln for ln in ll.read_text().splitlines() if ln.startswith("declare")]
    want = [
        "declare i32 @llvm.fshl.i32(i32, i32, i32)",
        "declare i32 @llvm.fshr.i32(i32, i32, i32)",
        "declare i64 @llvm.ctlz.i64(i64, i1)",
        "declare i16 @llvm.cttz.i16(i16, i1)",
        "declare i64 @llvm.ctpop.i64(i64)",
        "declare i16 @llvm.bswap.i16(i16)",
    ]
    for d in want:
        assert decls.count(d) == 1, (d, decls)
    assert not [d for d in decls if "@llvm.fsh" in d and ".i64" in d], decls
