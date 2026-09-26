"""Regression tests for AGAST #1534 — ritz1 must index a module const array
through its global: `const T: [4]i32 = [1, 2, 3, 4]` then `T[2]`.

ritz1 already emitted the table as `@T = internal constant [4 x i32] [...]`
(emit_const_array_entry), but emit_expr_index never looked at const entries:
`T` resolved as neither a local nor a global, fell to the pointer fallback, and
emit_expr_ident inlined the const's scalar value (0 for an array). The result
was `inttoptr i64 0 to ptr` plus an i8-wide GEP/load, a segfault whatever the
element type. cryptosec's AES SBOX/INV_SBOX/RCON and ed25519's L_BYTES lookups
all take that shape.

Every program returns 3 when the element was read from the right slot at the
right width with the right extension, and something else otherwise. The
assertion is on the runtime exit code, with ritz0 run as the oracle.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date; a stale binary would test the old emitter."""
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        ["make", "-C", "ritz1", "ritz1"],
        cwd=RITZ_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if proc.returncode != 0 or not RITZ1_BIN.exists():
        pytest.fail(
            "could not build ritz1 for the const-array index tests:\n"
            f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )


def _build_runtime_start() -> None:
    proc = subprocess.run(
        ["make", "-C", "runtime", RITZ_START.name],
        cwd=RITZ_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0 or not RITZ_START.exists():
        pytest.fail(
            f"could not build the runtime start object {RITZ_START}:\n"
            f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
        )


@pytest.fixture(scope="module")
def ritz1_bin() -> Path:
    _build_ritz1()
    _build_runtime_start()
    return RITZ1_BIN


# --- the ticket's repros ------------------------------------------------------

I32_REPRO = """\
const T: [4]i32 = [1, 2, 3, 4]

pub fn main() -> i32
    return T[2]
"""

U8_REPRO = """\
const T: [4]u8 = [1, 2, 3, 4]

pub fn main() -> i32
    return T[2] as i32
"""

# cryptosec's shape: a multi-row table with a trailing comma, read with a
# runtime index in a loop. Only the last row sums to 3, so reading the wrong
# row, the wrong stride, or a null base all give something else.
MULTI_ROW_SUM = """\
const TABLE: [12]u8 = [
    0x10, 0x20, 0x30, 0x40,
    0x50, 0x60, 0x70, 0x7f,
    0x00, 0x01, 0x01, 0x01,
]

pub fn main() -> i32
    var sum: i32 = 0
    var i: i32 = 8
    while i < 12
        sum = sum + TABLE[i] as i32
        i = i + 1
    return sum
"""

# --- element widths and extension --------------------------------------------

# The high-bit cases compare explicitly: exit codes are mod 256, so an
# arithmetic answer like `v - 250` still exits 3 when a wrong sext makes v
# -3 (-253 & 0xff == 3). That coincidence let a zext->sext mutation survive.

# 0xfd must zero-extend to 253.
U8_HIGH_BIT = """\
const SBOX: [4]u8 = [0x63, 0xfd, 0x77, 0x7b]

pub fn main() -> i32
    let v: i64 = SBOX[1] as i64
    if v == 253
        return 3
    return 1
"""

# An i32 stride over 1, 2, 3: a byte-wide GEP would land inside element 0.
I32_RUNTIME_INDEX = """\
const T: [5]i32 = [100, 200, 300, 3, 500]

pub fn main() -> i32
    var k: i32 = 3
    return T[k]
"""

U16_TABLE = """\
const T: [3]u16 = [1000, 60003, 7]

pub fn main() -> i32
    let v: i64 = T[1] as i64
    if v == 60003
        return 3
    return 1
"""

U32_TABLE = """\
const T: [3]u32 = [1, 4000000003, 7]

pub fn main() -> i32
    let v: i64 = T[1] as i64
    if v == 4000000003
        return 3
    return 1
"""

# Values that need all 64 bits: an i32/i8-wide load would drop the high word.
I64_TABLE = """\
const T: [3]i64 = [1, 8589934595, 7]

pub fn main() -> i32
    return (T[1] - 8589934592) as i32
"""

U64_TABLE = """\
const RCON: [4]u64 = [1, 2, 4294967299, 8]

pub fn main() -> i32
    return (RCON[2] - 4294967296) as i32
"""

# Two const tables, one feeding the other's index (AES InvSubBytes(SubBytes)).
CHAINED_LOOKUP = """\
const FWD: [4]u8 = [2, 3, 0, 1]
const INV: [4]u8 = [9, 9, 3, 9]

pub fn main() -> i32
    let x: u8 = FWD[1]
    return INV[x - 1] as i32
"""

# A local of the same name shadows the module const: must read the local.
LOCAL_SHADOWS_CONST = """\
const T: [4]i32 = [9, 9, 9, 9]

pub fn main() -> i32
    let T: [4]i32 = [0, 3, 0, 0]
    return T[1]
"""

# Scalar consts still inline, and still work as an index into a const table.
SCALAR_CONST_INDEX = """\
const IDX: i64 = 2
const T: [4]i32 = [0, 0, 3, 0]

pub fn main() -> i32
    return T[IDX]
"""

FORMS = {
    "i32_repro": I32_REPRO,
    "u8_repro": U8_REPRO,
    "multi_row_sum": MULTI_ROW_SUM,
    "u8_high_bit": U8_HIGH_BIT,
    "i32_runtime_index": I32_RUNTIME_INDEX,
    "u16_table": U16_TABLE,
    "u32_table": U32_TABLE,
    "i64_table": I64_TABLE,
    "u64_table": U64_TABLE,
    "chained_lookup": CHAINED_LOOKUP,
    "local_shadows_const": LOCAL_SHADOWS_CONST,
    "scalar_const_index": SCALAR_CONST_INDEX,
}


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
    comp = subprocess.run(
        cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )

    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(FORMS))
def test_ritz0_oracle(name: str, tmp_path: Path) -> None:
    """ritz0 is the reference: every program is written to exit 3."""
    assert _run("ritz0", tmp_path, name, FORMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(FORMS))
def test_ritz1_const_array_index(name: str, ritz1_bin: Path, tmp_path: Path) -> None:
    rc = _run("ritz1", tmp_path, name, FORMS[name])
    assert rc == 3, (
        f"ritz1 build of {name} exited {rc}, expected 3 "
        "(-11 = SIGSEGV: the index went through a null base)"
    )
