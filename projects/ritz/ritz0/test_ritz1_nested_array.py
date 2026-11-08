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
    # AGAST #2097: an N-D array struct field `m: [2][3]i32`.  Every index is
    # written with a distinct value and read back; the neighbouring scalar
    # fields catch a field laid out too small (overrun) or at the wrong
    # offset.  sum(r*3+c+1 for 2x3) = 21; 21 + tag 1 + tail 20 = 42.
    "struct_field": """\
struct M
    tag: i32
    m: [2][3]i32
    tail: i64

pub fn main() -> i32
    var s: M
    s.tag = 1
    s.tail = 20
    for r in 0..2
        for c in 0..3
            s.m[r][c] = r * 3 + c + 1
    var sum: i32 = 0
    for r in 0..2
        for c in 0..3
            if s.m[r][c] != r * 3 + c + 1
                return 1
            sum = sum + s.m[r][c]
    if s.tag != 1 or s.tail != 20
        return 2
    if sizeof(M) != 40
        return 3
    let p: *i32 = @s.m[1][0]
    if *p != 4 or *(p - 1) != 3 or *(p + 2) != 6
        return 4
    return sum + s.tag + (s.tail as i32)
""",
    # The same through a `type Grid = [4][4]u8` alias, a u8 leaf.
    # sum((r*4+c) for 4x4) = 120; 120 - 78 = 42.
    "alias_in_field": """\
type Grid = [4][4]u8

struct B
    pre: u8
    g: Grid
    post: u8

pub fn main() -> i32
    var b: B
    b.pre = 7
    b.post = 9
    for r in 0..4
        for c in 0..4
            b.g[r][c] = (r * 4 + c) as u8
    var sum: i32 = 0
    for r in 0..4
        for c in 0..4
            if b.g[r][c] as i32 != r * 4 + c
                return 1
            sum = sum + (b.g[r][c] as i32)
    # sizeof(B) is not checked: ritz0 says 24 through the alias (AGAST
    # #2151); the IR layout { i8, [4 x [4 x i8]], i8 } is 18.
    if b.pre != 7 or b.post != 9
        return 2
    let row: *u8 = @b.g[2][0]
    if *(row + 3) != 11 or *(row + 4) != 12
        return 3
    return sum - 78
""",
    # Pointer-to-struct base `p.m[i][j]` (param and local), stores through
    # one pointer read back through the value and vice versa.
    "ptr_base": """\
struct M
    tag: i32
    m: [3][2]i64

fn put(p: *M, i: i32, j: i32, v: i64)
    p.m[i][j] = v

fn get(p: *M, i: i32, j: i32) -> i64
    return p.m[i][j]

pub fn main() -> i32
    var s: M
    s.tag = 5
    for r in 0..3
        for c in 0..2
            put(@s, r, c, (r * 2 + c) as i64)
    let q: *M = @s
    q.m[2][1] = 30
    if s.m[2][1] != 30 or get(@s, 2, 0) != 4 or q.m[0][1] != 1
        return 1
    let e: *i64 = @q.m[1][1]
    *e = 7
    if s.m[1][1] != 7 or s.tag != 5
        return 2
    return (get(@s, 2, 1) + s.m[1][1] + q.m[0][1]) as i32 + s.tag - 1
""",
    # Nested member base `a.b.m[i][j]`, local and global, plus compound
    # assignment and a 3-D field.
    "nested_member_base": """\
struct In
    x: i32
    m: [2][2]i32
    t: [2][2][2]u16

struct Out
    h: i64
    b: In

var go: Out

pub fn main() -> i32
    var a: Out
    a.h = 1
    a.b.x = 2
    for i in 0..2
        for j in 0..2
            a.b.m[i][j] = i * 2 + j
            go.b.m[i][j] = 10 + i * 2 + j
            for k in 0..2
                a.b.t[i][j][k] = (i * 4 + j * 2 + k) as u16
    a.b.m[1][1] += 10
    if a.b.m[1][1] != 13 or a.b.m[1][0] != 2 or a.b.m[0][1] != 1
        return 1
    if go.b.m[1][0] != 12 or go.b.m[0][0] != 10
        return 2
    if a.b.t[1][0][1] != 5 or a.b.t[0][1][1] != 3 or a.b.t[1][1][1] != 7
        return 3
    let gp: *i32 = @go.b.m[0][1]
    if *(gp + 2) != 13
        return 4
    return a.b.m[1][1] + go.b.m[1][1] + (a.h as i32) + a.b.x + (a.b.t[1][1][0] as i32) + 7
""",
    # sizeof over an N-D field, its row, and a struct holding one by value
    # (copied, and passed by value).  24 + 12 + 6 = 42.
    "field_sizeof_and_copy": """\
struct M
    t: i32
    m: [2][3]i32

fn f(x: M) -> i32
    return x.m[1][2] + x.t

pub fn main() -> i32
    var s: M
    s.t = 2
    s.m[1][2] = 40
    var c: M = s
    if f(c) != 42 or sizeof(M) != 28
        return 1
    return (sizeof(s.m) + sizeof(s.m[0]) + 6) as i32
""",
    # A generic struct with an N-D field: every specialisation keeps the
    # field's shape (monomorph clones it).
    "generic_struct_field": """\
struct Box<T>
    v: T
    m: [2][3]u8

pub fn main() -> i32
    var b: Box<i64>
    b.v = 30
    for i in 0..2
        for j in 0..3
            b.m[i][j] = (i * 3 + j) as u8
    if b.m[0][2] != 2 or b.m[1][0] != 3
        return 1
    return (b.v as i32) + (b.m[1][2] as i32) + 7
""",
    # A struct leaf in a field: `s.m[i][j].f`.  H is declared before P, so
    # %P must be emitted first (the field holds P by value).
    "struct_leaf_in_field": """\
struct H
    k: i32
    m: [2][2]P

struct P
    x: i32
    y: i64

pub fn main() -> i32
    var h: H
    h.k = 2
    for i in 0..2
        for j in 0..2
            h.m[i][j].x = i * 2 + j
            h.m[i][j].y = 10
    h.m[1][1].y = 30
    let px: *i32 = @h.m[1][0].x
    if *px != 2 or h.m[0][1].x != 1 or h.m[1][0].y != 10
        return 1
    return h.m[1][1].x + (h.m[1][1].y as i32) + h.k + 7
""",
    # AGAST #2152: an N-D field reached through an indexed base -- a local
    # and a global array of structs, `arr[i].m[j][k]`.  Neighbouring
    # elements and rows are checked so a wrong stride shows.
    "index_base_array": """\
struct M
    t: i32
    m: [2][3]i32

var ga: [3]M

pub fn main() -> i32
    var arr: [2]M
    for i in 0..2
        for j in 0..3
            arr[0].m[i][j] = 100 + i * 3 + j
            arr[1].m[i][j] = i * 3 + j
            ga[2].m[i][j] = 50 + i * 3 + j
    arr[1].m[1][2] = 40
    arr[1].m[0][1] += 5
    if arr[0].m[1][2] != 105 or arr[1].m[0][1] != 6 or arr[1].m[1][1] != 4
        return 1
    if ga[2].m[1][0] != 53 or ga[2].m[0][2] != 52
        return 2
    let q: *i32 = @arr[1].m[1][0]
    if *(q + 2) != 40
        return 3
    let k: i32 = 1
    return arr[k].m[k][k + 1] + ga[2].m[0][0] - 48
""",
    # `p[i].m[j][k]` over a `*M` param, an N-D struct leaf `g[i][j].m[k][l]`,
    # and an array-of-struct field `o.items[i].m[j][k]`.
    "index_base_ptr_nd_and_field": """\
struct M
    t: i32
    m: [2][3]i32

struct O
    h: i64
    items: [2]M

fn put(p: *M, i: i32, v: i32)
    p[i].m[1][2] = v
    p[i].m[0][0] = 1

fn get(p: *M, i: i32) -> i32
    return p[i].m[1][2]

pub fn main() -> i32
    var arr: [2]M
    put(@arr[0], 1, 30)
    put(@arr[0], 0, 7)
    if arr[0].m[1][2] != 7 or arr[1].m[0][0] != 1
        return 1
    var g: [2][2]M
    g[1][0].m[1][1] = 4
    g[0][1].m[1][1] = 9
    var o: O
    o.items[1].m[0][2] = 3
    o.items[0].m[0][2] = 8
    if g[0][1].m[1][1] != 9 or o.items[0].m[0][2] != 8
        return 2
    return get(@arr[0], 1) + g[1][0].m[1][1] + o.items[1].m[0][2] + 5
""",
    # A dereferenced base `(*p).m[i][j]`, over a local pointer, a param and
    # a pointer-typed field `(*w.p).m[i][j]`; and a nested field behind an
    # index `arr[i].b.m[j][k]`.
    "deref_base": """\
struct M
    t: i32
    m: [2][3]i32

struct W
    x: i32
    p: *M

struct N
    h: i64
    b: M

fn rd(p: *M) -> i32
    return (*p).m[1][2]

pub fn main() -> i32
    var s: M
    let p: *M = @s
    (*p).m[1][2] = 20
    (*p).m[1][1] = 3
    (*p).m[1][2] += 10
    var w: W
    w.p = @s
    (*w.p).m[0][2] = 2
    if s.m[1][2] != 30 or s.m[1][1] != 3 or s.m[0][2] != 2
        return 1
    var na: [2]N
    na[1].b.m[1][0] = 5
    na[0].b.m[1][0] = 9
    if na[0].b.m[1][0] != 9
        return 2
    return rd(@s) + (*w.p).m[0][2] + na[1].b.m[1][0] + 5
""",
    # The pointer-shaped bases: an array of `*M` `ap[i].m[j][k]` and a
    # `**M` field `h.pp[i].m[j][k]`.
    "ptr_shaped_bases": """\
struct M
    t: i32
    m: [2][3]i32

struct H
    n: i32
    pp: **M

pub fn main() -> i32
    var a: M
    var b: M
    a.m[1][2] = 20
    var ap: [2]*M
    ap[0] = @a
    ap[1] = @b
    ap[1].m[0][1] = 12
    ap[0].m[0][1] = 1
    var h: H
    h.pp = @ap[0]
    h.pp[1].m[1][0] = 3
    if a.m[1][2] != 20 or b.m[0][1] != 12 or a.m[0][1] != 1 or b.m[1][0] != 3
        return 1
    return a.m[1][2] + ap[1].m[0][1] + h.pp[1].m[1][0] + 7
""",
    # AGAST #2166: `(*gp).f` with a module-level `var gp: *M`.  ritz1
    # resolved the field type (#2152) but emit_member_ptr could not address
    # it: "unhandled EXPR_MEMBER" on both read and assign.  The scalar
    # repro, an N-D field element, a compound assign, a nested
    # `(*(*gp).nx).t` base, and a local `gp` shadowing the global (its
    # writes must not land in the global's target).
    "global_ptr_deref_scalar": """\
struct M
    t: i32
    u: i32

var gp: *M

pub fn main() -> i32
    var a: M
    a.u = 7
    gp = @a
    (*gp).t = 40
    if a.u != 7 or a.t != 40
        return 1
    return (*gp).t + 2
""",
    "global_ptr_deref_field": """\
struct M
    t: i32
    m: [2][3]i32
    nx: *M

var gp: *M

fn shadow(q: *M) -> i32
    (*q).t = 5
    return (*q).t

pub fn main() -> i32
    var a: M
    var b: M
    a.nx = @b
    b.t = 1
    gp = @a
    (*gp).m[1][2] = 20
    (*gp).m[1][1] = 3
    (*gp).m[1][2] += 10
    (*gp).t = 2
    (*(*gp).nx).t = 4
    if a.m[1][2] != 30 or a.m[1][1] != 3 or a.t != 2 or b.t != 4
        return 1
    if shadow(@b) != 5 or a.t != 2 or b.t != 5
        return 2
    return (*gp).m[1][2] + (*gp).m[1][1] + (*gp).t + (*(*gp).nx).t + 2
""",
    # sizeof over an element, a row and the whole N-D field through every
    # base shape: 4 + 12 + 4 + 4 + 12 + 6 = 42.
    "field_elem_sizeof": """\
struct M
    t: i32
    m: [2][3]i32

pub fn main() -> i32
    var s: M
    var arr: [2]M
    let p: *M = @s
    if sizeof(arr[1].m) != 24 or sizeof((*p).m) != 24
        return 1
    return (sizeof(s.m[0][1]) + sizeof(s.m[1]) + sizeof(arr[1].m[0][2]) + sizeof((*p).m[1][2]) + sizeof(arr[0].m[1]) + 6) as i32
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
    # AGAST #2097: field_new keeps an N-D shape now, but an enum payload
    # binding has no N-D lowering (`A(g) => g[1][2]` loaded the payload as
    # an i64 and indexed it as a byte pointer), so both payload forms stay
    # located errors.
    "enum_tuple_payload": ("""\
enum E
    A([2][3]u8)
    B(i32)

fn get(e: E) -> i32
    match e
        A(g) => return g[1][2] as i32
        B(x) => return x
    return 0

pub fn main() -> i32
    return get(E.B(42))
""", ":2:", "multi-dimensional array type is not supported as an enum variant payload"),
    "enum_struct_payload": ("""\
enum E
    A
        g: [2][3]u8
    B(i32)

pub fn main() -> i32
    let e: E = E.B(1)
    return 0
""", ":2:", "multi-dimensional array type is not supported as an enum variant payload"),
    # AGAST #2097: a row of a struct field is no more a value than a row
    # of a local.
    "field_row_as_value": ("""\
struct M
    m: [2][3]i32

fn take(p: i64) -> i32
    return 0

pub fn main() -> i32
    var s: M
    return take(s.m[1] as i64)
""", ":9:", "a row or a struct element of a multi-dimensional array is not a value"),
    "field_row_assign": ("""\
struct M
    m: [2][3]u8

pub fn main() -> i32
    var s: M
    s.m[1] = 0
    return 0
""", ":6:", "assigning a row or a whole struct element"),
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
    # The local is `l`: it can't take the global's name (AGAST #2407).
    local = decl.replace("var g", "var l")
    program = f"{decl}\n\npub fn main() -> i32\n    {local}\n    return 0\n"
    comp, ll = _compile("ritz1", tmp_path, "layout", program)
    assert comp.returncode == 0, comp.stderr[-2000:]
    ir = ll.read_text()
    assert f"@g = weak_odr global {llvm} zeroinitializer" in ir, ir
    assert f"alloca {llvm}" in ir, ir


@pytest.mark.integration
def test_ritz1_nested_array_field_layout(ritz1_bin, tmp_path):
    """AGAST #2097: an N-D field is declared with ritz0's struct ABI."""
    program = (
        "type Grid = [4][4]u8\n\n"
        "struct M\n    tag: i32\n    m: [2][3]i32\n    g: Grid\n\n"
        "pub fn main() -> i32\n    var s: M\n    s.tag = 0\n    return s.tag\n"
    )
    comp, ll = _compile("ritz1", tmp_path, "field_layout", program)
    assert comp.returncode == 0, comp.stderr[-2000:]
    ir = ll.read_text()
    assert "%M = type {i32, [2 x [3 x i32]], [4 x [4 x i8]]}" in ir, ir


@pytest.mark.integration
def test_ritz1_nested_array_field_struct_leaf_order(ritz1_bin, tmp_path):
    """AGAST #2097: a `[N][M]P` field holds P by value, so %P is emitted
    before its holder, as for a 1-D `[N]P` field (struct_deps_satisfied)."""
    program = (
        "struct H\n    k: i32\n    m: [2][2]P\n\n"
        "struct P\n    x: i32\n    y: i64\n\n"
        "pub fn main() -> i32\n    var h: H\n    h.k = 0\n    return h.k\n"
    )
    comp, ll = _compile("ritz1", tmp_path, "leaf_order", program)
    assert comp.returncode == 0, comp.stderr[-2000:]
    ir = ll.read_text()
    assert "%H = type {i32, [2 x [2 x %P]]}" in ir, ir
    assert ir.index("%P = type") < ir.index("%H = type"), ir
