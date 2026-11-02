"""Regression tests for AGAST #1509: ritz1 multi-dimensional arrays.

The ticket reported `@g[1][0]` failing with "cannot take address". The real
gap was wider: ritz1 had no multi-dimensional arrays at all. `type_array`
recorded only the OUTER dimension, so `var g: [4][8]u8` became
`alloca [4 x i64]` and `g[1][0] = 9` loaded an i64 out of the slot and
stored THROUGH it. That compiled and exited 0, then segfaulted at runtime.
rzsh's `var g_history: [100][512]u8` (stores, loads and five
`@g_history[idx][0]`) is the motivating user.

ritz0 is the oracle: every RUNNABLE program returns 42 under it.  Locals are
not zero-initialised (ritz0's alloca is not), so a neighbour a program checks
is written first. The programs
check neighbouring elements and rows, so a wrong stride or a flattened
layout shows up as a wrong exit code, not just a wrong value.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

EXPECTED = 42

RUNNABLE = {
    # The ticket's repro, returning 42 instead of 9.
    "repro_local": """\
pub fn main() -> i32
    var g: [4][8]u8
    g[1][0] = 42
    let p: *u8 = @g[1][0]
    return *p as i32
""",
    # Element stores and loads on a local 2-D array: rows must not alias.
    # The value model narrows/widens at the leaf width (u8 here).
    "local_store_load": """\
pub fn main() -> i32
    var g: [4][8]u8
    for r in 0..4
        for c in 0..8
            g[r][c] = (r * 10 + c) as u8
    if g[0][7] != 7 or g[3][0] != 30 or g[2][5] != 25
        return 1
    return (g[1][2] as i32) + (g[3][7] as i32) - 7
""",
    # The rzsh shape: a global [N][M]u8 written row by row and read back
    # through `@g[idx][0]` (history.ritz).
    "global_rzsh": """\
var g_history: [8][16]u8
var g_after: i64 = 5

fn put(idx: i32, a: u8, b: u8)
    g_history[idx][0] = a
    g_history[idx][1] = b
    g_history[idx][2] = 0

fn get(idx: i32) -> *u8
    return @g_history[idx][0]

pub fn main() -> i32
    put(3, 40, 2)
    put(4, 7, 7)
    let p: *u8 = get(3)
    if *(p + 16) != 7
        return 1
    if g_after != 5 or g_history[2][0] != 0
        return 2
    return (*p as i32) + (*(p + 1) as i32)
""",
    # Non-constant indices, writing through the pointer, read back by index.
    "nonconst_index_write_through": """\
pub fn main() -> i32
    var g: [3][5]i32
    for r in 0..3
        for c in 0..5
            g[r][c] = 0
    var i: i32 = 2
    var j: i32 = 3
    let p: *i32 = @g[i][j]
    *p = 40
    let q: *i32 = @g[i - 1][j + 1]
    *q = 2
    if g[1][3] != 0 or g[2][4] != 0
        return 1
    return g[2][3] + g[1][4]
""",
    # Element width: an i64 leaf strides 8 bytes, rows stride 8 * M.
    "i64_stride": """\
pub fn main() -> i32
    var g: [2][3]i64
    g[0][2] = 1
    g[1][0] = 41
    let p: *i64 = @g[0][0]
    if *(p + 3) != 41 or *(p + 2) != 1
        return 1
    return (*(p + 2) + *(p + 3)) as i32
""",
    # A 3-D array, local and global.
    "three_d": """\
var gg: [2][3][4]u16

pub fn main() -> i32
    var g: [2][3][4]i32
    var a: i32 = 1
    var b: i32 = 2
    var c: i32 = 3
    g[a][b][c] = 30
    g[1][2][2] = 1
    g[0][2][3] = 0
    gg[1][1][3] = 12
    let p: *i32 = @g[a][b][c]
    let q: *u16 = @gg[a][1][3]
    if *(p - 1) != 1 or g[0][2][3] != 0
        return 1
    let base: *u16 = @gg[0][0][0]
    if *(base + 12 + 4 + 3) != 12
        return 2
    return *p + (*q as i32)
""",
    # Compound assignment desugars to a load + store on the same element.
    "compound_assign": """\
pub fn main() -> i32
    var g: [2][2]i32
    g[0][1] = 0
    g[1][0] = 0
    g[1][1] = 40
    g[1][1] += 2
    if g[1][0] != 0 or g[0][1] != 0
        return 1
    return g[1][1]
""",
    # Every index of a local and a global 2-D array: store a distinct value
    # at each, read every one back.  A wrong stride / aliasing rows changes
    # the checksum.  sum(r*8+c+1 for 4x8) = 528; 528 % 256 = 16; + 26 = 42.
    "every_index_local_and_global": """\
var gg: [4][8]u16

pub fn main() -> i32
    var g: [4][8]u8
    for r in 0..4
        for c in 0..8
            g[r][c] = (r * 8 + c + 1) as u8
            gg[r][c] = (r * 8 + c + 1) as u16
    var sum: i32 = 0
    var gsum: i32 = 0
    for r in 0..4
        for c in 0..8
            if g[r][c] as i32 != r * 8 + c + 1
                return 1
            if gg[r][c] as i32 != r * 8 + c + 1
                return 2
            sum = sum + (g[r][c] as i32)
            gsum = gsum + (gg[r][c] as i32)
    if sum != gsum
        return 3
    return (sum % 256) + 26
""",
    # `@g[i][j]` handed to a function that writes through it.
    "addr_passed_to_writer": """\
var gh: [4][6]i32

fn fill(p: *i32, n: i32, v: i32)
    for k in 0..n
        *(p + k) = v

pub fn main() -> i32
    var g: [3][4]i32
    for r in 0..3
        for c in 0..4
            g[r][c] = 0
    var i: i32 = 1
    fill(@g[i][1], 3, 7)
    fill(@gh[2][0], 6, 5)
    if g[1][0] != 0 or g[2][0] != 0 or g[0][3] != 0
        return 1
    if gh[1][5] != 0 or gh[3][0] != 0 or gh[2][5] != 5
        return 2
    return g[1][1] + g[1][2] + g[1][3] + gh[2][0] + gh[2][5] + 11
""",
    # A struct leaf: `g[i][j].field` reads, stores and `@`.
    "struct_leaf_field": """\
struct P
    x: i32
    y: i64

var gp: [2][3]P

pub fn main() -> i32
    var g: [2][3]P
    var i: i32 = 1
    var j: i32 = 2
    g[i][j].x = 30
    g[i][j].y = 5
    g[1][1].x = 9
    gp[0][1].y = 7
    let px: *i32 = @g[i][j].x
    if g[1][1].x != 9 or gp[0][1].y != 7 or gp[0][2].y != 0
        return 1
    return *px + (g[1][2].y as i32) + (gp[0][1].y as i32)
""",
    # Guards: neighbouring address forms that already work (the briefing
    # asked to confirm they share no gap): `@s.arr[i]`, `@g[i].field`.
    "guard_struct_field_index": """\
struct S
    tag: i64
    arr: [4]i32

pub fn main() -> i32
    var s: S
    s.tag = 1
    var i: i32 = 2
    s.arr[2] = 41
    let p: *i32 = @s.arr[i]
    return *p + (s.tag as i32)
""",
    "guard_index_member": """\
struct P
    x: i32
    y: i32

var gs: [3]P

pub fn main() -> i32
    gs[1].y = 20
    var lp: [3]P
    lp[2].y = 22
    var k: i32 = 1
    let q: *i32 = @gs[k].y
    let r: *i32 = @lp[k + 1].y
    return *q + *r
""",
}


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
        proc = subprocess.run(
            cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
        )
    return proc, ll


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    comp, ll = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(1, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link ({name}):\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RUNNABLE))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, RUNNABLE[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RUNNABLE))
def test_ritz1_nested_array(ritz1_bin, tmp_path, name):
    """ritz1 must agree with ritz0 on every multi-dimensional array program."""
    assert _run("ritz1", tmp_path, name, RUNNABLE[name]) == EXPECTED


# Every multi-dimensional array use ritz1 does NOT lower must be a compile
# error naming the source line, never a silent `[N x i64]` (AGAST #1509).
# `needle` is the `:line:` the error must name.
FAIL_CLOSED = {
    "struct_field": ("""\
struct M
    tag: i32
    m: [2][3]i32

pub fn main() -> i32
    var s: M
    s.tag = 1
    return s.tag
""", ":3:", "multi-dimensional array type is not supported as a struct field"),
    "param": ("""\
fn f(a: [2][3]i32) -> i32
    return 0

pub fn main() -> i32
    return 0
""", ":1:", "multi-dimensional array type is not supported as a parameter"),
    "pointee": ("""\
pub fn main() -> i32
    var p: *[2][3]i32 = null
    return 0
""", ":2:", "multi-dimensional array type is not supported as a pointee"),
    "alias_in_field": ("""\
type Grid = [4][4]u8

struct B
    g: Grid

pub fn main() -> i32
    return 0
""", ":4:", "multi-dimensional array type is not supported as a struct field"),
    # A nested array literal does not even parse in ritz1 (closed already).
    "nested_literal": ("""\
pub fn main() -> i32
    var g: [2][2]i32 = [[1, 2], [3, 4]]
    return g[1][1]
""", ":1:", "cannot parse item"),
    # Any initializer that does parse reaches emit_var_decl's guard.
    "local_initializer": ("""\
pub fn main() -> i32
    var g: [2][2]i32 = [0; 2]
    return g[1][1]
""", ":2:", "an initializer on a multi-dimensional array is not supported"),
    "global_initializer": ("""\
var gg: [2][2]i32 = [0; 2]

pub fn main() -> i32
    return gg[1][1]
""", ":1:", "an initializer on a multi-dimensional array is not supported"),
    "return_type": ("""\
fn f() -> [2][3]i32
    var g: [2][3]i32
    return g

pub fn main() -> i32
    return 0
""", ":1:", "multi-dimensional array type is not supported as a return type"),
    "row_as_value": ("""\
fn take(p: i64) -> i32
    return 0

pub fn main() -> i32
    var g: [2][3]i32
    return take(g[1] as i64)
""", ":6:", "a row or a struct element of a multi-dimensional array is not a value"),
    "for_in": ("""\
pub fn main() -> i32
    var g: [2][3]u8
    for row in g
        return 1
    return 0
""", ":3:", "iterating a multi-dimensional array is not supported"),
    "generic_arg": ("""\
struct Box<T>
    v: T

pub fn main() -> i32
    var b: Box<[2][3]u8>
    return 0
""", ":5:", "multi-dimensional array type is not supported as a generic type argument"),
    "name_assign_local": ("""\
pub fn main() -> i32
    var g: [2][3]u8
    g = 0
    return 0
""", ":3:", "assigning a whole multi-dimensional array is not supported"),
    "name_assign_global": ("""\
var g: [2][3]u8

pub fn main() -> i32
    g = 0
    return 0
""", ":4:", "assigning a whole multi-dimensional array is not supported"),
    "row_assign": ("""\
pub fn main() -> i32
    var g: [2][3]u8
    g[1] = 0
    return 0
""", ":3:", "assigning a row or a whole struct element"),
    "struct_elem_assign": ("""\
struct P
    x: i32

pub fn main() -> i32
    var g: [2][2]P
    var q: P
    q.x = 1
    g[1][1] = q
    return 0
""", ":8:", "assigning a row or a whole struct element"),
    "whole_array_use": ("""\
fn take(a: i64) -> i32
    return 0

pub fn main() -> i32
    var g: [2][3]u8
    g[0][0] = 1
    return take(g)
""", ":7:", "a multi-dimensional array is not a value"),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(FAIL_CLOSED))
def test_ritz1_nested_array_fails_closed(ritz1_bin, tmp_path, name):
    program, needle, what = FAIL_CLOSED[name]
    comp, ll = _compile("ritz1", tmp_path, name, program)
    assert comp.returncode != 0, (
        f"ritz1 accepted an unlowered N-D array use ({name}):\n"
        f"{ll.read_text() if ll.exists() else ''}"
    )
    assert not ll.exists(), "a failed compile must not leave IR behind"
    assert what in comp.stderr, comp.stderr
    assert needle in comp.stderr, comp.stderr


@pytest.mark.integration
@pytest.mark.parametrize(
    "decl, llvm",
    [
        ("var g: [4][8]u8", "[4 x [8 x i8]]"),
        ("var g: [2][3][4]i32", "[2 x [3 x [4 x i32]]]"),
    ],
)
def test_ritz1_nested_array_layout(ritz1_bin, tmp_path, decl, llvm):
    """The storage is the real nested type, local and global, as ritz0 lays it out."""
    program = f"{decl}\n\npub fn main() -> i32\n    {decl}\n    return 0\n"
    comp, ll = _compile("ritz1", tmp_path, "layout", program)
    assert comp.returncode == 0, comp.stderr[-2000:]
    ir = ll.read_text()
    assert f"@g = weak_odr global {llvm} zeroinitializer" in ir, ir
    assert f"alloca {llvm}" in ir, ir
