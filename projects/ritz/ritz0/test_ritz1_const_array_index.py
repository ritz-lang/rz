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
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


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

# A local can't take a const's name (AGAST #2407): test_local_takes_module_name.py.

# Scalar consts still inline, and still work as an index into a const table.
SCALAR_CONST_INDEX = """\
const IDX: i64 = 2
const T: [4]i32 = [0, 0, 3, 0]

pub fn main() -> i32
    return T[IDX]
"""

# AGAST #3325: a whole struct element is a struct value, `load %P` from the
# `[N x %P]` GEP, as for a global `var g: [N]P` (#1553).  ritz1 refused it with
# "a whole array is not a value here".  Element 0 holds 3 in `b`, element 1 in
# `a`, so reading the wrong element or the wrong field gives something else.
STRUCT_ELEM = """\
struct P
    a: i32
    b: i64

const PS: [2]P = [P { a: 9, b: 3 }, P { a: 3, b: 9 }]

pub fn main() -> i32
    var i: i64 = 1
    let q: P = PS[i]
    return q.a
"""

# AGAST #3360: a method on a const element.  A shared `self: @P` reads the
# element in place, a by-value `self` a copy of it; ritz0 died with "Unknown
# identifier: PS" and ritz1 said an unlocated "cannot determine receiver type".
# 1 + 3 - 1 == 3 only when each call read its own element.
STRUCT_ELEM_METHOD = """\
struct P
    a: i32

const PS: [3]P = [P { a: 7 }, P { a: 1 }, P { a: 3 }]

impl P
    fn get(self: @P) -> i32
        self.a
    fn val(self) -> i32
        self.a

pub fn main() -> i32
    var i: i64 = 2
    PS[1].get() + PS[i].val() - PS[1].val()
"""

# AGAST #3398: an element whose field is itself a struct.  ritz1 and
# ritz1_selfhosted wrote `[%P { i64 0 }, ...]`, which clang refuses; #3651
# lowers the nested literal.  Read by field path and by a method on the inner
# struct, a constant and a runtime index: 3 + 3 - 3, element 0 gives -1.
NESTED_STRUCT_FIELD = """\
struct Q
    a: i32

struct P
    q: Q

const PS: [2]P = [P { q: Q { a: 1 } }, P { q: Q { a: 3 } }]

impl Q
    fn get(self: @Q) -> i32
        self.a

pub fn main() -> i32
    var i: i64 = 1
    PS[1].q.a + PS[i].q.get() - 3
"""

FORMS = {
    "i32_repro": I32_REPRO,
    "nested_struct_field": NESTED_STRUCT_FIELD,
    "struct_elem": STRUCT_ELEM,
    "struct_elem_method": STRUCT_ELEM_METHOD,
    "u8_repro": U8_REPRO,
    "multi_row_sum": MULTI_ROW_SUM,
    "u8_high_bit": U8_HIGH_BIT,
    "i32_runtime_index": I32_RUNTIME_INDEX,
    "u16_table": U16_TABLE,
    "u32_table": U32_TABLE,
    "i64_table": I64_TABLE,
    "u64_table": U64_TABLE,
    "chained_lookup": CHAINED_LOOKUP,
    "scalar_const_index": SCALAR_CONST_INDEX,
}

# LARB R48 (AGAST #3391): `@A[i]` of a const array is a shared `@T` into its
# read-only data, and `@A` is `@[N]T`.  #3337 refused both; these were the
# `addr_*` rows of CONST_PLACE_ERRORS.  ritz0 since #3391, ritz1 and
# ritz1_selfhosted since #3392 (test_addr_of_const_array).  Each reads a
# different element or field, so the wrong slot, a copy's garbage or a null
# base gives another code.
ADDR_ELEM = """\
const NS: [3]i32 = [10, 3, 30]

fn rd(p: @i32) -> i32
    *p

pub fn main() -> i32
    var i: i64 = 1
    rd(@NS[i])
"""

ADDR_STRUCT_ELEM = """\
const KS: [2]StrView = ["a", "abc"]

fn ln(s: @StrView) -> i64
    s.len

pub fn main() -> i32
    var i: i64 = 1
    ln(@KS[i]) as i32
"""

# `@KS[i].len`: the field's place inside the element, an `@i64`.
ADDR_ELEM_FIELD = """\
const KS: [2]StrView = ["a", "abc"]

pub fn main() -> i32
    var i: i64 = 1
    let p: @i64 = @KS[i].len
    *p as i32
"""

# `@NS` of the whole table is `@[3]i32`: 10 - 30 + 23 == 3.
ADDR_WHOLE = """\
const NS: [3]i32 = [10, 23, 30]

fn mix(a: @[3]i32) -> i32
    a[0] - a[2] + a[1]

pub fn main() -> i32
    mix(@NS)
"""

ADDR_FORMS = {
    "addr_elem": ADDR_ELEM,
    "addr_struct_elem": ADDR_STRUCT_ELEM,
    "addr_elem_field": ADDR_ELEM_FIELD,
    "addr_whole": ADDR_WHOLE,
}


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        binary = RITZ1_BIN.parent / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        cmd = [str(binary), str(src), "-o", str(ll)]
        comp = subprocess.run(
            cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
        )
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )

    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(FORMS) + sorted(ADDR_FORMS))
def test_ritz0_oracle(name: str, tmp_path: Path) -> None:
    """ritz0 is the reference: every program is written to exit 3."""
    assert _run("ritz0", tmp_path, name, {**FORMS, **ADDR_FORMS}[name]) == 3


# AGAST #3325: a const array is `internal constant` data, so a write into it
# faulted at run time (or was dropped).  Reading `KS[i].len` gave the field a
# pointer, which made `KS[0].len = 7` compile to that fault.  ritz1 refused the
# writes from #3325 on; ritz0 died on the const's name with an internal
# "Unknown identifier" traceback until #3337.  Each case is a located error on
# all three compilers, in ritz1's words.
#
# `@NS[i]` is legal, a shared `@T` (LARB R48): ADDR_FORMS above.  `@&` of an
# element stays refused here.
_CONST_HEAD = (
    "const NS: [3]i32 = [10, 20, 30]\n"
    'const KS: [2]StrView = ["a", "c"]\n\n'
    "fn w(x:& i32)\n    x = 1\n\n"
    "pub fn main() -> i32\n    var i: i64 = 1\n"
)
# After main, so the statement stays on line 9.  A `self:&` or `self: @&P`
# receiver lends the element mutably (AGAST #3360).
_CONST_TAIL = (
    "\nstruct P\n    a: i32\n\n"
    "const PS: [2]P = [P { a: 1 }, P { a: 2 }]\n\n"
    "impl P\n    fn bump(self:& P)\n        self.a = 5\n"
    "    fn bump_ref(self: @&P)\n        self.a = 5\n"
)
_THROUGH = "cannot assign through const `{}`; it is read-only data"
_BORROW = "cannot borrow const `{}` as mutable; it is read-only data"

# name -> (statement in main, line 9, column, message)
CONST_PLACE_ERRORS = {
    "elem": ("NS[0] = 5", 5, _THROUGH.format("NS")),
    "field": ("KS[0].len = 7", 5, _THROUGH.format("KS")),
    "compound": ("NS[1] += 1", 5, _THROUGH.format("NS")),
    "mut_borrow": ("let r: @&StrView = @&KS[0]", 24, _BORROW.format("KS")),
    "borrow_param": ("w(NS[0])", 7, _BORROW.format("NS")),
    "mut_receiver": ("PS[0].bump()", 5, _BORROW.format("PS")),
    "mut_ref_receiver": ("PS[i].bump_ref()", 5, _BORROW.format("PS")),
}

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CONST_PLACE_ERRORS))
def test_const_array_place_refused(request, compiler: str, name: str, tmp_path: Path) -> None:
    stmt, col, message = CONST_PLACE_ERRORS[name]
    src = tmp_path / "unit.ritz"
    src.write_text(_CONST_HEAD + f"    {stmt}\n    0\n" + _CONST_TAIL)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BIN.parent / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path,
                              env=env, capture_output=True, text=True, timeout=300)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    assert "Traceback" not in out, f"{compiler}, {name}:\n{out[-1500:]}"
    hits = re.findall(rf"unit\.ritz:9:{col}: (?:error: )?{re.escape(message)}", out)
    assert len(hits) == 1, f"{compiler}, {name}: want one {message!r} at 9:{col}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


# LARB R48 (AGAST #3392): ritz1 and ritz1_selfhosted read `@NS[i]`, `@KS[i]`,
# `@KS[i].len` and `@NS` from the const's global, as ritz0 does.  ritz1 refused
# each (#3337) until R48.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
@pytest.mark.parametrize("name", sorted(ADDR_FORMS))
def test_addr_of_const_array(request, compiler: str, name: str, tmp_path: Path) -> None:
    request.getfixturevalue("ritz1_bin")
    assert _run(compiler, tmp_path, name, ADDR_FORMS[name]) == 3


# LARB R48: a const scalar is inlined, so `@N` has nothing to point at, unlike
# a const array's `@A`.  ritz0 died with "Unknown variable: N", ritz1 said an
# unlocated "cannot take address" (#3392).  A located error on all three.
SCALAR_ADDR = """\
const N: i32 = 3

fn rd(p: @i32) -> i32
    *p

pub fn main() -> i32
    rd({}N)
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("op", ["@", "@&"])
def test_const_scalar_addr_refused(request, compiler: str, op: str, tmp_path: Path) -> None:
    src = tmp_path / "unit.ritz"
    src.write_text(SCALAR_ADDR.format(op))
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BIN.parent / compiler
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path,
                              env=env, capture_output=True, text=True, timeout=300)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0 and "Traceback" not in out, out[-1500:]
    message = "cannot take the address of const `N`; a const scalar has no storage"
    hits = re.findall(rf"unit\.ritz:7:8: (?:error: )?{re.escape(message)}", out)
    assert len(hits) == 1, f"{compiler}: want one {message!r} at 7:8:\n{out[-1500:]}"
    assert not ll.exists()


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(FORMS))
def test_ritz1_const_array_index(name: str, ritz1_bin: Path, tmp_path: Path) -> None:
    rc = _run("ritz1", tmp_path, name, FORMS[name])
    assert rc == 3, (
        f"ritz1 build of {name} exited {rc}, expected 3 "
        "(-11 = SIGSEGV: the index went through a null base)"
    )


# AGAST #3398: ritz1_selfhosted emitted the same unlinkable nested initializer,
# so the nested form runs on it too.  The other FORMS are ritz1-only.
@pytest.mark.integration
def test_ritz1_selfhosted_nested_struct_field(ritz1_bin: Path, tmp_path: Path) -> None:
    name = "nested_struct_field"
    assert _run("ritz1_selfhosted", tmp_path, name, FORMS[name]) == 3
