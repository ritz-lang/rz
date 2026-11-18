"""AGAST #1744: both compilers pick byval/sret by the exact LLVM alloc size.

THE DEFECT

#1739 passes a by-value struct param of at least SRET_MIN_BYTES (256) as
`ptr byval(%T) align 8`, and smaller ones first-class.  For a RETURN the
threshold is ABI-neutral (LLVM returns a large first-class aggregate through a
hidden pointer anyway), but for a PARAM it is the ABI: a first-class `%T`
argument is split into scalars, a byval one is a pointer to a stack copy.

ritz1 measures a struct with its padded layout (get_struct_size_by_name), so
`{[63]i32, u8}` is 256 bytes and byval.  ritz0's `_sret_struct_type` summed
the unpadded field sizes (`_type_size_bytes`), so the same struct was 253
bytes and first-class.  A ritz0 object calling a ritz1 object (or the
reverse) then passed every such argument wrongly, with nothing to catch it.

THE FIX

ritz0's predicate uses `_abi_size_align`, the padded x86-64 layout walk that
already decides large arrays (#2306) and that mirrors ritz1's.

THE TESTS

* A size table: each struct's LLVM alloc size, read back from each
  compiler's own IR through LLVM's x86-64 DataLayout (llvmlite.binding), and
  whether each compiler passes it byval.  Every struct whose size crosses
  256 only through padding is in it: tail padding, an array of padded
  structs, bool + f32, a nested struct, a tagged enum, an Option.
* Interop: each compiler's object calls the other's definitions, ritz0 with
  ritz1 and with ritz1_selfhosted, both ways, and checks the values arrive.
"""

import os
import re
import subprocess
from pathlib import Path

import llvmlite.binding as llvm
import pytest
from llvmlite import ir

from emitter_llvmlite import _abi_size_align
from test_ritz1_large_struct_ret import (
    RITZ_ROOT,
    _clang_bounded,
    _link_run,
    _ritz0_ll,
)

SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
COMPILERS = ("ritz0", "ritz1", "ritz1_selfhosted")

# x86-64 Linux, as clang writes it for the default target.
X86_64_DATA_LAYOUT = (
    "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-f80:128-n8:16:32:64-S128"
)

TYPES = """\
struct I
    x: i64
    y: u8

struct Q
    a: [31]i64

enum E
    P(i64)
    R
"""

# name: (fields, LLVM alloc size, the statements that fill `v` from `k`,
#        the condition that `v` was filled from `k`)
#
# Sizes are x86-64 DataLayout alloc sizes; the size table checks them
# against LLVM.  "unpadded" is the sum ritz0 used to compare against 256.
CASES = {
    # Tail padding alone: 252 + 1 = 253 unpadded.  The ticket's struct.
    "A": (
        "    a: [63]i32\n    b: u8\n",
        256,
        "    v.a[0] = k\n    v.a[62] = k + 1\n    v.b = (k + 2) as u8\n",
        "v.a[0] == k and v.a[62] == k + 1 and v.b == (k + 2) as u8",
    ),
    # Below the threshold with no padding: first-class in both.
    "U": (
        "    a: [63]i32\n",
        252,
        "    v.a[0] = k\n    v.a[62] = k + 1\n",
        "v.a[0] == k and v.a[62] == k + 1",
    ),
    # Exactly 256 without padding: byval in both, before and after.
    "X": (
        "    a: [64]i32\n",
        256,
        "    v.a[0] = k\n    v.a[63] = k + 1\n",
        "v.a[0] == k and v.a[63] == k + 1",
    ),
    # An array of padded structs: 16 x 9 = 144 unpadded.
    "N": (
        "    a: [16]I\n",
        256,
        "    v.a[0].x = k as i64\n    v.a[15].y = (k + 1) as u8\n    v.a[15].x = (k + 2) as i64\n",
        "v.a[0].x == k as i64 and v.a[15].y == (k + 1) as u8 and v.a[15].x == (k + 2) as i64",
    ),
    # The same, padded to just under: first-class in both.
    "M": (
        "    a: [15]I\n    b: u8\n",
        248,
        "    v.a[14].y = k as u8\n    v.b = (k + 1) as u8\n",
        "v.a[14].y == k as u8 and v.b == (k + 1) as u8",
    ),
    # bool then f32: 248 + 1 + 4 = 253 unpadded.
    "F": (
        "    a: [31]i64\n    b: bool\n    c: f32\n",
        256,
        "    v.a[30] = k as i64\n    v.b = true\n    v.c = 1.5\n",
        "v.a[30] == k as i64 and v.b and v.c == 1.5",
    ),
    # bool then f32, padded to just under: first-class in both.
    "FU": (
        "    a: [61]i32\n    b: bool\n    c: f32\n",
        252,
        "    v.a[60] = k\n    v.b = true\n    v.c = 2.5\n",
        "v.a[60] == k and v.b and v.c == 2.5",
    ),
    # A nested struct aligned past a u8: 1 + 248 = 249 unpadded.
    "NS": (
        "    a: u8\n    b: Q\n",
        256,
        "    v.a = k as u8\n    v.b.a[30] = (k + 1) as i64\n",
        "v.a == k as u8 and v.b.a[30] == (k + 1) as i64",
    ),
    # A tagged user enum: 236 + 16 + 1 = 253 unpadded.
    "TE": (
        "    a: [59]i32\n    e: E\n    b: u8\n",
        256,
        "    v.a[58] = k\n    v.e = E.P((k + 1) as i64)\n    v.b = (k + 2) as u8\n",
        "v.a[58] == k and enum_is(v.e, (k + 1) as i64) and v.b == (k + 2) as u8",
    ),
    # A builtin tagged enum, Option<i64>.
    "TO": (
        "    a: [59]i32\n    o: Option<i64>\n    b: u8\n",
        256,
        "    v.a[58] = k\n    v.o = Some((k + 1) as i64)\n    v.b = (k + 2) as u8\n",
        "v.a[58] == k and option_is(v.o, (k + 1) as i64) and v.b == (k + 2) as u8",
    ),
    # SIMD vector fields (AGAST #3656): `v4i64` is 32 bytes, 32-aligned, so
    # V is 256 B and byval at align 32.  ritz1 sized a vector field 8/8 and
    # spelled it `%v4i64`, an undeclared type.
    "V": (
        "    a: [8]v4i64\n",
        256,
        "    v_set(@v, 0, k as i64)\n    v_set(@v, 31, (k + 1) as i64)\n",
        "v_get(@v, 0) == k as i64 and v_get(@v, 31) == (k + 1) as i64",
    ),
}

HELPERS = """\
fn enum_is(e: E, n: i64) -> bool
    match e
        P(x) => x == n
        R => false

fn option_is(o: Option<i64>, n: i64) -> bool
    match o
        Some(x) => x == n
        None => false

fn v_set(v: *V, i: i32, n: i64)
    let p: *i64 = v as *i64
    p[i] = n

fn v_get(v: *V, i: i32) -> i64
    let p: *i64 = v as *i64
    p[i]
"""


def _structs() -> str:
    return TYPES + "".join(f"\nstruct {n}\n{c[0]}" for n, c in CASES.items()) + "\n"


def _maker(n: str, fill: str, vis: str = "pub ") -> str:
    return f"{vis}fn mk_{n}(k: i32) -> {n}\n    var v: {n}\n{fill}    v\n\n"


def _checker(n: str, cond: str, prefix: str) -> str:
    # `k` follows the struct: an argument passed with the wrong ABI moves it.
    return (
        f"pub fn {prefix}_{n}(v: {n}, k: i32) -> i32\n"
        f"    if {cond}\n        return 0\n    1\n\n"
    )


# The size table's program: a global of each struct (LLVM reads its type
# back) and a fn taking it by value (its header shows byval or not).
SIZES = (
    _structs()
    + HELPERS
    + "".join(f"var g_{n}: {n}\n" for n in CASES)
    + "\n"
    + "".join(_checker(n, c[3], "t") for n, c in CASES.items())
)

# The library defines a maker and a checker per struct; the app calls them.
LIB = (
    _structs()
    + HELPERS
    + "".join(_maker(n, c[2]) + _checker(n, c[3], "chk") for n, c in CASES.items())
)


def _app() -> str:
    externs = "".join(
        f"extern fn mk_{n}(k: i32) -> {n}\nextern fn chk_{n}(v: {n}, k: i32) -> i32\n"
        for n in CASES
    )
    # The app checks a lib-made value with its own checker, and the lib
    # checks an app-made one: the value crosses the boundary both ways.
    local = "".join(
        _maker(n, c[2], vis="") + _checker(n, c[3], "here") for n, c in CASES.items()
    )
    body = ""
    for i, n in enumerate(CASES):
        k = 10 * (i + 1) + 1
        body += (
            f"    if chk_{n}(mk_here_{n}({k}), {k}) != 0\n        return {2 * i + 1}\n"
            f"    if here_{n}(mk_{n}({k}), {k}) != 0\n        return {2 * i + 2}\n"
        )
    local = local.replace("fn mk_", "fn mk_here_")
    return (
        _structs()
        + HELPERS
        + externs
        + "\n"
        + local
        + "fn main() -> i32\n"
        + body
        + "    0\n"
    )


def _ll(compiler: str, tmp_path: Path, name: str, program: str) -> Path:
    if compiler == "ritz0":
        return _ritz0_ll(tmp_path, name, program)
    binary = (
        SELFHOSTED_BIN
        if compiler == "ritz1_selfhosted"
        else RITZ_ROOT / "ritz1" / "build" / "ritz1"
    )
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    comp = subprocess.run(
        [str(binary), str(src), "-o", str(ll)],
        check=False,
        cwd=tmp_path,
        env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    return ll


def _object(ll: Path) -> Path:
    obj = ll.with_suffix(".o")
    r = _clang_bounded(
        ["-c", "-O0", "-Wno-override-module", str(ll), "-o", str(obj)], ll.parent
    )
    assert r.returncode == 0, f"clang on {ll.name} failed:\n{r.stderr[-2000:]}"
    return obj


def _header(text: str, fn: str) -> str:
    pat = re.compile(rf'^define\b.*@"?{re.escape(fn)}"?\(')
    lines = [line for line in text.splitlines() if pat.search(line)]
    assert len(lines) == 1, f"no single define for @{fn}"
    return lines[0]


_I8, _I32, _I64 = ir.IntType(8), ir.IntType(32), ir.IntType(64)
_LAYOUT_TYPES = [
    ir.IntType(1),
    _I8,
    ir.IntType(16),
    _I32,
    _I64,
    ir.IntType(128),
    ir.FloatType(),
    ir.DoubleType(),
    _I8.as_pointer(),
    ir.LiteralStructType([ir.ArrayType(_I32, 63), _I8]),
    ir.LiteralStructType([_I8, ir.LiteralStructType([_I64, _I8])]),
    ir.ArrayType(ir.LiteralStructType([_I64, _I8]), 16),
    ir.LiteralStructType([ir.ArrayType(_I64, 31), ir.IntType(1), ir.FloatType()]),
    ir.LiteralStructType([_I8, _I32], packed=True),
    ir.VectorType(_I64, 4),
    ir.VectorType(_I32, 4),
    ir.VectorType(_I32, 3),
    ir.LiteralStructType([ir.ArrayType(ir.VectorType(_I64, 4), 7), _I8]),
]


@pytest.mark.unit
@pytest.mark.parametrize("ty", _LAYOUT_TYPES, ids=str)
def test_ritz0_layout_walk_matches_llvm(ty):
    """ritz0's `_abi_size_align` is LLVM's x86-64 (alloc size, ABI align)."""
    td = llvm.create_target_data(X86_64_DATA_LAYOUT)
    g = llvm.parse_assembly(f"@g = external global {ty}\n").get_global_variable("g")
    want = (
        td.get_abi_size(g.global_value_type),
        td.get_abi_alignment(g.global_value_type),
    )
    assert _abi_size_align(ty) == want


@pytest.fixture(scope="module")
def size_table(ritz1_bin, tmp_path_factory):
    """{compiler: {struct: (LLVM alloc size, passed byval?, byval align,
    LLVM ABI align)}}."""
    td = llvm.create_target_data(X86_64_DATA_LAYOUT)
    table = {}
    for compiler in COMPILERS:
        text = _ll(
            compiler, tmp_path_factory.mktemp(compiler), "sizes", SIZES
        ).read_text()
        module = llvm.parse_assembly(text)
        globals_ = {g.name: g for g in module.global_variables}
        table[compiler] = {}
        for n in CASES:
            ty = globals_[f"g_{n}"].global_value_type
            header = _header(text, f"t_{n}")
            m = re.search(r"byval\([^)]*\) align (\d+)", header)
            table[compiler][n] = (
                td.get_abi_size(ty),
                "byval" in header,
                int(m.group(1)) if m else None,
                td.get_abi_alignment(ty),
            )
    return table


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_struct_sizes_are_the_llvm_alloc_sizes(size_table, compiler):
    """Every compiler lays each struct out as LLVM does on x86-64."""
    got = {n: row[0] for n, row in size_table[compiler].items()}
    assert got == {n: c[1] for n, c in CASES.items()}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_byval_iff_alloc_size_reaches_threshold(size_table, compiler):
    """A param is byval exactly when its LLVM alloc size is >= 256 bytes."""
    got = {n: row[1] for n, row in size_table[compiler].items()}
    assert got == {n: c[1] >= 256 for n, c in CASES.items()}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_byval_align_is_at_least_the_struct_align(size_table, compiler):
    """A byval struct is `align max(8, alignof T)`, as clang passes an
    over-aligned C struct (AGAST #3656): V's 32, not 8."""
    got = {n: row[2] for n, row in size_table[compiler].items() if row[1]}
    want = {
        n: max(8, row[3]) for n, row in size_table[compiler].items() if row[1]
    }
    assert got == want


@pytest.mark.integration
@pytest.mark.parametrize(
    "lib_c,app_c",
    (
        ("ritz0", "ritz1"),
        ("ritz1", "ritz0"),
        ("ritz0", "ritz1_selfhosted"),
        ("ritz1_selfhosted", "ritz0"),
    ),
)
def test_structs_straddling_256_cross_compilers_intact(
    ritz1_bin, tmp_path, lib_c, app_c
):
    lib = _object(_ll(lib_c, tmp_path, "lib", LIB))
    app = _object(_ll(app_c, tmp_path, "app", _app()))
    # ritz0 emits its own _start for a `main`; ritz1 links the runtime's.
    rc = _link_run([app, lib], tmp_path / "xlink", with_start=app_c != "ritz0")
    if rc:
        n = list(CASES)[(rc - 1) // 2]
        side = "lib checking an app value" if rc % 2 else "app checking a lib value"
        pytest.fail(f"struct {n} arrived wrong ({side}), exit {rc}")
