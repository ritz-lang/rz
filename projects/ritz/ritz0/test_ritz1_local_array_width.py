"""AGAST #1564: ritz1 must index a LOCAL `[N]T` array at T's real width.

THE DEFECT

emit_var_decl allocates `var st: [4]u32` as `alloca [4 x i32]`, but the three
local-array arms that address it knew only i8 / i32 / i64 / ptr:

    index store  (emitter_stmt.ritz, STMT_INDEX_ASSIGN array-local arm)
    index load   (emitter_expr_access.ritz, emit_expr_index array-local arm)
    `@arr[i]`    (emitter_expr_arith.ritz, EXPR_ADDR_OF of EXPR_INDEX)

u32 / u16 / i16 fell to their `[N x i64]` default: an 8-byte stride and an
8-byte store, so `st[3] = ...` wrote 8 bytes at offset 24 of a 16-byte alloca
(segfault), and `@st[0]` handed a callee a pointer the callee then strode at
4 bytes. u32 loads were also left unwidened (i32 used as i64 -> bad IR).
cryptosec's chacha20_block uses `var state: [16]u32` exactly like this.

Each program returns 42 only when every element has the right address, width
and signedness: a wrong stride, a store that clobbers a neighbour, or a
zext/sext mix-up returns a different code (or crashes). ritz0 is the oracle.
"""

import subprocess

import pytest

from test_ritz1_builtin_struct_shadow import _run, ritz1_bin  # noqa: F401

# The ticket's repro, verbatim.
REPRO = """\
fn qr(state: *u32, a: i64, d: i64) -> void
    state[d] = (state[d] ^ state[a])

pub fn main() -> i32
    var st: [4]u32
    st[0] = 0x00010000
    st[3] = 0x00000001
    qr(@st[0], 0, 3)
    return (st[3] >> 16) as i32
"""

# u32: each slot independent (no neighbour clobber), a value with the top bit
# set reads back zero-extended, and a callee writing through `@st[i]` lands
# on the slot the caller reads.
U32 = """\
fn put(p: *u32, i: i64, v: u32) -> void
    p[i] = v

pub fn main() -> i32
    var st: [4]u32
    st[0] = 0x11111111
    st[1] = 0x22222222
    st[2] = 0x80000001
    st[3] = 0x44444444
    if st[0] != 0x11111111
        return 1
    if st[1] != 0x22222222
        return 2
    if st[2] != 0x80000001
        return 3
    if st[3] != 0x44444444
        return 4
    let wide: u64 = st[2] as u64
    if wide != 0x80000001
        return 5
    put(@st[0], 2, 7)
    if st[2] != 7
        return 6
    put(@st[1], 2, 9)
    if st[3] != 9
        return 7
    if st[1] != 0x22222222
        return 8
    return 42
"""

# i32: negative values read back sign-extended.
I32 = """\
fn put(p: *i32, i: i64, v: i32) -> void
    p[i] = v

pub fn main() -> i32
    var a: [3]i32
    a[0] = 0 - 5
    a[1] = 100
    a[2] = 0 - 1
    if a[0] != 0 - 5
        return 1
    if a[1] != 100
        return 2
    let w: i64 = a[2] as i64
    if w != 0 - 1
        return 3
    put(@a[1], 1, 0 - 7)
    if a[2] != 0 - 7
        return 4
    if a[0] != 0 - 5
        return 5
    return 42
"""

# u16 / i16: 2-byte stride, zext vs sext.
W16 = """\
fn put(p: *u16, i: i64, v: u16) -> void
    p[i] = v

pub fn main() -> i32
    var h: [4]u16
    h[0] = 0x1111
    h[1] = 0x8001
    h[2] = 0x3333
    h[3] = 0x4444
    if h[0] != 0x1111
        return 1
    if h[1] != 0x8001
        return 2
    let wide: u64 = h[1] as u64
    if wide != 0x8001
        return 3
    if h[3] != 0x4444
        return 4
    put(@h[1], 1, 0x5555)
    if h[2] != 0x5555
        return 5
    if h[3] != 0x4444
        return 6
    var s: [2]i16
    s[0] = 0 - 3
    s[1] = 12
    if s[0] != 0 - 3
        return 7
    let sw: i64 = s[0] as i64
    if sw != 0 - 3
        return 8
    if s[1] != 12
        return 9
    return 42
"""

# u8 / i8: 1-byte stride, zext vs sext; `@b[i]` into a *u8 callee.
W8 = """\
fn put(p: *u8, i: i64, v: u8) -> void
    p[i] = v

pub fn main() -> i32
    var b: [4]u8
    b[0] = 0x11
    b[1] = 0x81
    b[2] = 0x33
    b[3] = 0x44
    if b[1] != 0x81
        return 1
    let wide: u64 = b[1] as u64
    if wide != 0x81
        return 2
    put(@b[1], 1, 0x55)
    if b[2] != 0x55
        return 3
    if b[3] != 0x44
        return 4
    var c: [2]i8
    c[0] = 0 - 2
    c[1] = 5
    let cw: i64 = c[0] as i64
    if cw != 0 - 2
        return 5
    if c[1] != 5
        return 6
    return 42
"""

# The chacha20 shape: a `[16]u32` local worked in place through `*u32`, with
# 32-bit wrap-around, copied element-wise into a second local array.
CHACHA_SHAPE = """\
fn qr(x: *u32, a: i64, b: i64, c: i64, d: i64) -> void
    x[a] = x[a] + x[b]
    x[d] = (x[d] ^ x[a]).rotl(16)
    x[c] = x[c] + x[d]
    x[b] = (x[b] ^ x[c]).rotl(12)
    x[a] = x[a] + x[b]
    x[d] = (x[d] ^ x[a]).rotl(8)
    x[c] = x[c] + x[d]
    x[b] = (x[b] ^ x[c]).rotl(7)

pub fn main() -> i32
    var state: [16]u32
    var working: [16]u32
    var i: i64 = 0
    while i < 16
        state[i] = 0x9e3779b9 * (i as u32 + 1)
        i = i + 1
    i = 0
    while i < 16
        working[i] = state[i]
        i = i + 1
    qr(@working[0], 0, 4, 8, 12)
    qr(@working[0], 1, 5, 9, 13)
    var acc: u32 = 0
    i = 0
    while i < 16
        acc = acc ^ (working[i] + state[i])
        i = i + 1
    if working[2] != state[2]
        return 1
    return (acc & 0x3f) as i32
"""

CASES = {
    "repro": REPRO,
    "u32": U32,
    "i32": I32,
    "w16": W16,
    "w8": W8,
    "chacha_shape": CHACHA_SHAPE,
}

# Fixed expectations (the ritz0 oracle is also checked against them).
WANT = {
    "repro": 1,
    "u32": 42,
    "i32": 42,
    "w16": 42,
    "w8": 42,
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_local_array_width_ritz1_matches_ritz0(ritz1_bin, tmp_path, name):  # noqa: F811
    program = CASES[name]
    want = _run("ritz0", tmp_path, name, program)
    if name in WANT:
        assert want == WANT[name]
    assert _run("ritz1", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize(
    "elem,llvm",
    [("u8", "i8"), ("i8", "i8"), ("u16", "i16"), ("i16", "i16"),
     ("u32", "i32"), ("i32", "i32"), ("u64", "i64"), ("i64", "i64")],
)
def test_local_array_ir_uses_alloca_element_type(ritz1_bin, tmp_path, elem, llvm):  # noqa: F811
    """Every GEP over the local indexes the alloca's own `[N x T]`."""
    src = tmp_path / f"arr_{elem}.ritz"
    src.write_text(
        f"fn take(p: *{elem}) -> void\n"
        "    p[0] = 1\n"
        "\n"
        "pub fn main() -> i32\n"
        f"    var a: [4]{elem}\n"
        "    a[3] = 2\n"
        "    take(@a[1])\n"
        "    return a[3] as i32\n"
    )
    ll = tmp_path / f"arr_{elem}.ll"
    proc = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    main_ir = ll.read_text().split("define i32 @main", 1)[1]
    assert f"alloca [4 x {llvm}]" in main_ir
    geps = [ln for ln in main_ir.splitlines() if "getelementptr [4 x" in ln]
    assert len(geps) == 3, geps
    for g in geps:
        assert f"getelementptr [4 x {llvm}]" in g, g
    assert f"store {llvm} " in main_ir
