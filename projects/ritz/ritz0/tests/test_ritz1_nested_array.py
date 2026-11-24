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
import re
import subprocess
from pathlib import Path

import pytest
import test_ir

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
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
            s.m[r][c] = (r * 3 + c + 1) as i32
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
    # The IR layout { i8, [4 x [4 x i8]], i8 } is 18 (ritz0 said 24
    # through the alias until AGAST #2151).
    if sizeof(B) != 18
        return 5
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
            put(@s, r as i32, c as i32, (r * 2 + c) as i64)
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
            a.b.m[i][j] = (i * 2 + j) as i32
            go.b.m[i][j] = (10 + i * 2 + j) as i32
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
            h.m[i][j].x = (i * 2 + j) as i32
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
            arr[0].m[i][j] = (100 + i * 3 + j) as i32
            arr[1].m[i][j] = (i * 3 + j) as i32
            ga[2].m[i][j] = (50 + i * 3 + j) as i32
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
    # AGAST #2099: a whole struct element `g[i][j] = q` stores the `%P` at the
    # element's address, as a 1-D `[N]P` element store does (#190). P's fields
    # differ in width, so a store at the wrong width or stride shows up in a
    # neighbour; a 3-D leaf takes the same path.
    "struct_elem_store": """\
struct P
    a: u8
    b: i64
    c: i16

pub fn main() -> i32
    var g: [2][2]P
    var h: [2][2][2]P
    for i in 0..2
        for j in 0..2
            g[i][j].a = 1
            g[i][j].b = 2
            g[i][j].c = 3
            h[i][j][1].c = 4
    var q: P
    q.a = 10
    q.b = 1099511627776
    q.c = 7
    g[1][0] = q
    h[1][0][0] = q
    if g[0][1].a != 1 or g[1][1].b != 2 or g[0][0].c != 3 or g[1][1].a != 1
        return 1
    if g[1][0].b != 1099511627776 or h[1][0][0].b != 1099511627776 or h[1][0][1].c != 4
        return 2
    return (g[1][0].a as i32) + (g[1][0].c as i32) + (h[1][0][0].c as i32) + 18
""",
    # ... into a global, from a call's result.
    "struct_elem_store_global": """\
struct P
    a: i32
    b: u8

var g: [3][2]P
var after: i32 = 5

fn mk(a: i32) -> P
    return P { a: a, b: 2 }

pub fn main() -> i32
    for i in 0..3
        for j in 0..2
            g[i][j].a = 1
            g[i][j].b = 1
    g[2][1] = mk(30)
    g[0][0] = mk(30)
    if g[2][0].a != 1 or g[1][1].b != 1 or after != 5
        return 1
    return g[2][1].a + (g[2][1].b as i32) + g[0][0].a / 3
""",
    # ... into an N-D field, of a local and through a pointer.
    "struct_elem_store_field": """\
struct P
    a: i16
    b: i64

struct M
    t: i32
    m: [2][3]P
    u: i8

fn put(p: *M, q: P)
    (*p).m[0][2] = q

pub fn main() -> i32
    var s: M
    s.t = 1
    s.u = 2
    for i in 0..2
        for j in 0..3
            s.m[i][j].a = 0
            s.m[i][j].b = 0
    var q: P
    q.a = 20
    q.b = 10
    s.m[1][2] = q
    q.a = 3
    put(@s, q)
    if s.m[1][1].a != 0 or s.m[0][1].b != 0 or s.t != 1 or s.u != 2
        return 1
    return (s.m[1][2].a as i32) + (s.m[1][2].b as i32) + (s.m[0][2].a as i32) + (s.m[0][2].b as i32) - 1
""",
    # ... with a generic leaf, `P$i64`.
    "struct_elem_store_generic": """\
struct P<T>
    v: T
    k: u8

struct W<T>
    a: [2][3]P<T>

pub fn main() -> i32
    var w: W<i64>
    w.a[1][1].v = 5
    var q: P<i64>
    q.v = 1099511627776
    q.k = 40
    w.a[1][2] = q
    if w.a[1][2].v != 1099511627776 or w.a[1][1].v != 5
        return 1
    return (w.a[1][2].k as i32) + 2
""",
    # AGAST #3377: N-D local initialisers, list and fill at every level
    # (an outer `[row; n]` copies the row), scalar and struct leaves.
    "local_initializers": """\
struct P
    a: i32
    b: u8

pub fn main() -> i32
    var g: [2][3]i32 = [ [1, 2, 3], [4, 5, 6] ]
    var h: [3][2]u8 = [ [7; 2]; 3]
    var k: [2][2][2]P = [ [ [P { a: 1, b: 2 }, P { a: 3, b: 4 }], [P { a: 5, b: 6 }; 2] ], [ [P { a: 9, b: 8 }; 2]; 2] ]
    h[2][1] = 9
    if g[0][0] != 1 or g[0][2] != 3 or g[1][0] != 4 or h[0][0] != 7 or h[2][0] != 7 or h[1][1] != 7
        return 1
    if k[0][0][1].a != 3 or k[0][1][0].b != 6 or k[0][1][1].a != 5 or k[1][1][1].a != 9 or k[1][0][0].b != 8
        return 2
    return g[1][2] + (h[2][1] as i32) + (k[0][0][0].b as i32) + 25
""",
    # ... of a Drop struct (LARB R39, AGAST #3376): a store drops the old
    # element and the stored one is moved, not dropped.  g must be
    # initialised (§3.3).  g[1][1] = q drops x=2, g[0][1] = .. drops x=0:
    # 30 + 7 + 3 + D (2).  Without the drop it is 40.
    "struct_elem_store_drop": """\
var D: i32 = 0

struct S
    x: i32

impl Drop for S
    fn drop(self:& S)
        D = D + self.x

pub fn main() -> i32
    var g: [2][2]S = [ [S { x: 0 }, S { x: 0 }], [S { x: 0 }, S { x: 0 }] ]
    g[1][1].x = 2
    g[1][0].x = 3
    var q: S = S { x: 30 }
    g[1][1] = q
    g[0][1] = S { x: 7 }
    return g[1][1].x + g[0][1].x + g[1][0].x + D
""",
    # AGAST #3306: a whole struct element read as a value loads the `%P` at
    # the element's address, as #2099 stores one: element to element, into an
    # annotated and an unannotated `let`, and a 3-D leaf.  P's fields differ
    # in width, so a load at the wrong width or stride shows in a neighbour.
    "struct_elem_load": """\
struct P
    a: u8
    b: i64
    c: i16

pub fn main() -> i32
    var g: [3][2]P
    var h: [2][2][2]P
    for i in 0..3
        for j in 0..2
            g[i][j].a = (i * 2 + j) as u8
            g[i][j].b = 1099511627776
            g[i][j].c = 1
    g[2][1].c = 9
    g[0][0] = g[2][1]
    h[1][0][1] = g[1][1]
    let i: i32 = 1
    let p: P = g[i][0]
    let q = h[1][0][1]
    var r: P = g[0][0]
    r.c = 2
    if g[0][0].b != 1099511627776 or g[0][1].a != 1 or g[2][1].a != 5 or g[0][0].c != 9
        return 1
    if p.b != 1099511627776 or q.b != 1099511627776 or r.b != 1099511627776
        return 2
    return (g[0][0].a as i32) + (g[0][0].c as i32) + (p.a as i32) + (q.a as i32) + (r.c as i32) + 21
""",
    # ... of a global.
    "struct_elem_load_global": """\
struct P
    a: i32
    b: u8

var g: [3][2]P
var after: i32 = 10

pub fn main() -> i32
    g[2][1].a = 15
    g[2][1].b = 2
    g[0][0] = g[2][1]
    let p: P = g[0][0]
    let q = g[2][1]
    return p.a + q.a + (p.b as i32) + after
""",
    # ... of an N-D field, of a local and through a pointer, and returned.
    "struct_elem_load_field": """\
struct P
    a: i64
    b: u8

struct M
    t: i32
    m: [2][3]P
    u: i8

fn get(p: *M) -> P
    return (*p).m[1][2]

pub fn main() -> i32
    var s: M
    s.t = 1
    s.u = 2
    s.m[1][2].a = 11
    s.m[1][2].b = 4
    s.m[0][1] = s.m[1][2]
    s.m[1][2].b = 7
    let y: P = get(@s)
    let z = s.m[0][1]
    let pm: *M = @s
    let w: P = (*pm).m[0][1]
    return (y.a as i32) + (y.b as i32) + (z.b as i32) + (w.a as i32) + s.t + (s.u as i32) + 6
""",
    # ... as a by-value argument and a method receiver: by value (`self`) and
    # mutating (`self:&`), which writes the element in place.
    "struct_elem_load_call": """\
struct P
    a: i32
    b: i16

impl P
    fn sum(self) -> i32
        return self.a + (self.b as i32)
    fn bump(self:& P, k: i32)
        self.a = self.a + k

struct M
    m: [2][3]P

fn take(p: P, k: i32) -> i32
    return p.a * k + (p.b as i32)

pub fn main() -> i32
    var g: [2][2]P
    g[1][0].a = 10
    g[1][0].b = 2
    g[0][1].a = 1
    g[0][1].b = 3
    g[0][1].bump(1)
    var s: M
    s.m[1][2].a = 1
    s.m[1][2].b = 0
    let pm: *M = @s
    (*pm).m[1][2].bump(2)
    return take(g[1][0], 3) + g[0][1].sum() + s.m[1][2].sum() + 2
""",
    # ... with a generic leaf, `P$i64`.
    "struct_elem_load_generic": """\
struct P<T>
    v: T
    k: u8

struct W<T>
    a: [2][3]P<T>

pub fn main() -> i32
    var w: W<i64>
    w.a[1][1].v = 1099511627776
    w.a[1][1].k = 40
    w.a[0][2] = w.a[1][1]
    let q: P<i64> = w.a[0][2]
    let r = w.a[1][1]
    if q.v != 1099511627776 or r.v != 1099511627776
        return 1
    return (q.k as i32) + 2 + 0 * (r.k as i32)
""",
    # ... of a Drop struct, through borrowing receivers: no read drops the
    # element (D is still 0 in the scope: 3 + 5 + 0).  g must be initialised
    # (§3.3) and drops at scope end in index order (LARB R39, AGAST #3376):
    # D = 0 + 5 + 0 + 3 after it, so 8 + 8 + 26.  Moving one out by value is
    # refused (FAIL_CLOSED).
    "struct_elem_load_drop": """\
var D: i32 = 0

struct S
    x: i32

impl S
    fn peek(self:@ S) -> i32
        return self.x
    fn bump(self:& S)
        self.x = self.x + 1

impl Drop for S
    fn drop(self:& S)
        D = D + self.x

pub fn main() -> i32
    var w: i32 = 0
    if true
        var g: [2][2]S = [ [S { x: 0 }, S { x: 0 }], [S { x: 0 }, S { x: 0 }] ]
        g[1][1].x = 2
        g[1][1].bump()
        g[0][1].x = 5
        w = g[1][1].peek() + g[0][1].peek() + D * 100
    return w + D + 26
""",
    # AGAST #3379 (LARB R40): a row of a `[2][3][2]u8` is a `[3][2]u8`, walked
    # in turn.  Cell (i, j, k) holds 6i + 2j + k: row[2][1] is 5 then 11, each
    # r[0] 6i + 2j (0 + 2 + 4 + 6 + 8 + 10): 46 over 6 inner trips.
    "for_in": """\
pub fn main() -> i32
    var g: [2][3][2]u8
    for i in 0..2
        for j in 0..3
            for k in 0..2
                g[i][j][k] = (6 * i + 2 * j + k) as u8
    var t: i32 = 0
    var n: i32 = 0
    for row in g
        t = t + (row[2][1] as i32)
        for r in row
            n = n + 1
            t = t + (r[0] as i32)
    if n != 6
        return 1
    return t - 4
""",
    # AGAST #2098: a `*[N][M]T` local and param point at the whole array:
    # `p[i][j]` and `(*p)[i][j]` are one element, a compound assign through one
    # included, over a local and a global; a null one compares as a pointer.
    "pointee": """\
var GG: [2][3]i32

fn put(p: *[2][3]i32, i: i32, j: i32, v: i32)
    p[i][j] = v

fn get(p: *[2][3]i32, i: i32, j: i32) -> i32
    return (*p)[i][j]

pub fn main() -> i32
    var g: [2][3]i32
    for i in 0..2
        for j in 0..3
            g[i][j] = 0
    var p: *[2][3]i32 = @g
    p[1][2] = 30
    p[1][1] = 1
    (*p)[0][2] = 5
    p[0][2] += 2
    if g[1][2] != 30 or g[0][2] != 7 or g[1][1] != 1 or g[0][1] != 0
        return 1
    put(@g, 1, 0, 3)
    if g[1][0] != 3 or g[0][2] != 7
        return 2
    var q: *[2][3]i32 = @GG
    q[1][2] = 2
    var r: *[2][3]i32 = null
    if r != null
        return 3
    return get(@g, 1, 2) + p[1][0] + (*q)[1][2] + GG[1][2] + 5
""",
    # AGAST #3635: a `*[N][M]T` held anywhere else than a param or a typed
    # local is the same plane pointer: a struct field, read, stored and `+=`
    # through as `s.p[i][j]` and `(*s.p)[i][j]` (the deref form crashed
    # ritz0 with "Cannot index type", #4123) ...
    "pointee_field": """\
struct S
    k: i32
    p: *[2][3]i32

fn get(s: *S, i: i32, j: i32) -> i32
    return s.p[i][j]

pub fn main() -> i32
    var g: [2][3]i32
    for i in 0..2
        for j in 0..3
            g[i][j] = (i * 3 + j) as i32
    var s: S = S { k: 1, p: @g }
    let q: *[2][3]i32 = s.p
    q[1][2] = 30
    var t: S = S { k: 2, p: null }
    if t.p != null
        return 1
    t.p = @g
    if s.p[0][1] != 1 or t.p[1][0] != 3 or s.p[0][2] != 2
        return 2
    s.p[0][0] = 9
    t.p[1][0] += 2
    (*s.p)[0][1] = 4
    (*t.p)[0][2] += 1
    if g[0][0] != 9 or g[1][0] != 5 or g[0][1] != 4 or g[0][2] != 3
        return 3
    return get(@s, 1, 2) + (*t.p)[1][0] + (*s.p)[0][1] - s.p[0][0] + s.k + t.k + 9
""",
    # ... a global, null until assigned, written through in another fn ...
    "pointee_global": """\
var GA: [2][3]i32
var gp: *[2][3]i32 = null

fn bump(i: i32, j: i32)
    gp[i][j] += 1

pub fn main() -> i32
    if gp != null
        return 1
    gp = @GA
    gp[1][2] = 30
    (*gp)[0][1] = 7
    bump(0, 1)
    if GA[1][2] != 30 or GA[0][1] != 8 or GA[1][1] != 0
        return 2
    return gp[1][2] + (*gp)[0][1] + 4
""",
    # ... a return type, held typed, inferred (`let q = whole()`) and assigned ...
    "pointee_return": """\
var GA: [2][3]i32

fn at(g: *[2][3]i32) -> *[2][3]i32
    return g

fn whole() -> *[2][3]i32
    return @GA

pub fn main() -> i32
    var g: [2][3]i32
    for i in 0..2
        for j in 0..3
            g[i][j] = 0
    let p: *[2][3]i32 = at(@g)
    p[1][2] = 30
    let q = whole()
    q[0][1] = 8
    var r: *[2][3]i32 = null
    r = whole()
    r[1][0] = 2
    (*whole())[0][2] = 1
    (*whole())[0][2] += 1
    if g[1][2] != 30 or GA[0][1] != 8 or GA[1][0] != 2 or g[0][1] != 0
        return 1
    return p[1][2] + q[0][1] + r[1][0] + (*whole())[0][2]
""",
    # ... a `**[N][M]T` local and param: `(*q)[i][j]` is element (i, j) of the
    # array `*q` points at, and `*q` is a `*[N][M]T` ...
    "pointee_ptr_ptr": """\
fn set(pp: **[2][3]i32, v: i32)
    (*pp)[1][1] = v

pub fn main() -> i32
    var g: [2][3]i32
    for i in 0..2
        for j in 0..3
            g[i][j] = 0
    var p: *[2][3]i32 = @g
    var q: **[2][3]i32 = @p
    (*q)[1][2] = 30
    let r: *[2][3]i32 = *q
    r[0][1] = 5
    set(@p, 4)
    var n: **[2][3]i32 = null
    if n != null
        return 1
    if g[1][2] != 30 or g[0][1] != 5 or g[1][1] != 4 or g[0][2] != 0
        return 2
    return g[1][2] + g[0][1] + g[1][1] + 3
""",
    # ... and `let c = *p` copies the whole `[N][M]T`, typed or not, through a
    # local, a global, a field, a call and a `**`: later stores to `g` and `GA`
    # don't reach the copies, and `c[i][j]` indexes the copy's shape, not a
    # flat `[6]i32`.
    "pointee_deref_copy": """\
var GA: [2][3]i32
var gp: *[2][3]i32 = null

struct H
    p: *[2][3]i32

fn mk() -> *[2][3]i32
    return @GA

pub fn main() -> i32
    var g: [2][3]i32
    for i in 0..2
        for j in 0..3
            g[i][j] = (i * 3 + j) as i32
            GA[i][j] = (10 + i * 3 + j) as i32
    let p: *[2][3]i32 = @g
    let c: [2][3]i32 = *p
    let c2 = *p
    gp = @GA
    let d = *gp
    let h: H = H { p: @g }
    let e = *h.p
    let f = *mk()
    var q: **[2][3]i32 = @p
    let k = **q
    g[1][2] = 0
    GA[1][2] = 0
    if c[1][2] != 5 or d[1][2] != 15 or e[1][2] != 5 or f[1][2] != 15 or k[1][2] != 5 or c2[1][2] != 5 or c2[1][0] != 3
        return 1
    return c[1][1] + d[0][1] + mk()[0][2] + 15
""",
    # ... a step `*(p + k)` copies the plane k past p's ...
    # AGAST #4122: and every other place a `*[N][M]T` can be written: behind a
    # reference (`@*[N][M]T` / `@&*[N][M]T`, `(*r)[i][j]`) ...
    "pointee_ref": """\
fn bump(r: @&*[2][3]i32)
    (*r)[0][1] += 1

fn read(p: *[2][3]i32) -> i32
    var r: @*[2][3]i32 = @p
    return (*r)[1][2] + (*r)[0][1]

fn write(p: *[2][3]i32)
    var q: *[2][3]i32 = p
    var m: @&*[2][3]i32 = @&q
    (*m)[1][2] = 30
    (*m)[0][1] = 7

pub fn main() -> i32
    var g: [2][3]i32
    for i in 0..2
        for j in 0..3
            g[i][j] = 0
    var p: *[2][3]i32 = @g
    write(p)
    bump(@&p)
    if g[1][2] != 30 or g[0][1] != 8 or g[0][2] != 0
        return 1
    return read(p) + 4
""",
    # ... an array of them, `a[k][i][j]` element (i, j) of the k-th plane ...
    "pointee_array_elem": """\
pub fn main() -> i32
    var g: [2][3]i32
    var h: [2][3]i32
    for i in 0..2
        for j in 0..3
            g[i][j] = 0
            h[i][j] = 0
    var a: [2]*[2][3]i32
    a[0] = @g
    a[1] = @h
    a[0][1][2] = 30
    a[1][0][1] = 7
    let q: *[2][3]i32 = a[1]
    q[1][1] = 2
    if g[1][2] != 30 or h[0][1] != 7 or h[1][1] != 2 or g[0][1] != 0
        return 1
    return a[0][1][2] + a[1][0][1] + a[1][1][1] + 3
""",
    # ... a `:&` param, written through and retargeted ...
    "pointee_borrow_param": """\
var GA: [2][3]i32

fn retarget(p:& *[2][3]i32)
    p[1][2] = 30
    p = @GA
    p[0][1] = 7

pub fn main() -> i32
    var g: [2][3]i32
    for i in 0..2
        for j in 0..3
            g[i][j] = 0
    var p: *[2][3]i32 = @g
    retarget(p)
    p[1][0] = 5
    if g[1][2] != 30 or GA[0][1] != 7 or GA[1][0] != 5 or g[1][0] != 0
        return 1
    return g[1][2] + GA[0][1] + GA[1][0]
""",
    # ... a cast to one, inferred and typed ...
    "pointee_cast": """\
pub fn main() -> i32
    var g: [6]i32
    for i in 0..6
        g[i] = i as i32
    let p = @g as *[2][3]i32
    p[1][2] = 30
    let q: *[2][3]i32 = @g as *[2][3]i32
    if p[0][1] != 1 or q[1][0] != 3 or g[5] != 30
        return 1
    return p[1][2] + q[1][0] + p[0][2] + 7
""",
    # ... and a `**[N][M]T` field, global and return, `(*x)[i][j]` each.
    "pointee_ptr_ptr_held": """\
var GA: [2][3]i32
var gp: *[2][3]i32 = null
var gq: **[2][3]i32 = null

struct S
    k: i32
    q: **[2][3]i32

fn pp() -> **[2][3]i32
    return @gp

pub fn main() -> i32
    for i in 0..2
        for j in 0..3
            GA[i][j] = 0
    gp = @GA
    var s: S = S { k: 1, q: @gp }
    (*s.q)[1][2] = 30
    gq = @gp
    (*gq)[0][1] = 7
    let r: **[2][3]i32 = pp()
    (*r)[1][0] = 2
    (*pp())[0][0] = 1
    if gq == null or GA[1][2] != 30 or GA[0][1] != 7 or GA[1][0] != 2 or GA[0][0] != 1
        return 1
    return (*s.q)[1][2] + (*gq)[0][1] + (*pp())[1][0] + s.k + 2
""",
    "pointee_deref_copy_step": """\
pub fn main() -> i32
    var g: [2][2][3]i32
    for i in 0..2
        for j in 0..2
            for k in 0..3
                g[i][j][k] = (6 * i + 3 * j + k) as i32
    let p: *[2][3]i32 = @g[0]
    let c = *(p + 1)
    g[1][1][2] = 0
    return c[1][2] + c[0][0] + 25
""",
    # ... and `h = *p` assigns the whole array, into a local and a global.
    "pointee_deref_assign": """\
var GH: [2][3]i32

pub fn main() -> i32
    var g: [2][3]i32
    for i in 0..2
        for j in 0..3
            g[i][j] = (i * 3 + j) as i32
    var h: [2][3]i32
    let p: *[2][3]i32 = @g
    h = *p
    GH = *p
    g[1][2] = 0
    let k: [2][3]i32 = *(p + 0)
    if h[1][2] != 5 or GH[1][2] != 5 or h[0][1] != 1 or k[1][2] != 0
        return 1
    return h[1][2] + GH[1][1] + h[1][0] + 30
""",
    # ... rank 3 (`[2][3][4]u8`, cell 12i + 4j + k), a struct leaf through a
    # param (`q[i][1].a`, `(*q)[i][0].b`), and an uninitialised local assigned.
    "pointee_3d_struct_leaf": """\
struct P
    a: i32
    b: i64

fn setp(q: *[2][2]P, i: i32, v: i32)
    q[i][1].a = v
    (*q)[i][0].b = 7

pub fn main() -> i32
    var g: [2][3][4]u8
    for i in 0..2
        for j in 0..3
            for k in 0..4
                g[i][j][k] = (i * 12 + j * 4 + k) as u8
    let p: *[2][3][4]u8 = @g
    var t: i32 = (p[1][2][3] as i32) + ((*p)[0][1][2] as i32)
    if t != 29
        return 1
    var ps: [2][2]P
    setp(@ps, 1, 30)
    setp(@ps, 0, 1)
    if ps[0][1].a != 1 or ps[1][0].b != 7 or ps[0][0].b != 7
        return 2
    var r: *[2][2]P
    r = @ps
    return r[1][1].a + (r[1][0].b as i32) + 5
""",
    # ... and `p + 1` steps the whole `[2][3]i32`, as ritz0 does: a plane of
    # `[2][2][3]i32` to the next one.
    # ... and the shape is the annotated local's alone: the next decl, an
    # uninitialised `var b: PA` with `PA` a `*[4]i32` alias, is a `*[4]i32`.
    "pointee_alias_after": """\
type PA = *[4]i32

pub fn main() -> i32
    var g: [2][3]i32
    g[1][2] = 30
    var a4: [4]i32 = [0, 0, 0, 0]
    let p: *[2][3]i32 = @g
    var b: PA
    b = @a4
    b[1] = 7
    b[3] = 5
    if a4[0] != 0 or a4[2] != 0
        return 1
    return p[1][2] + a4[1] + a4[3]
""",
    "pointee_step": """\
pub fn main() -> i32
    var g: [2][2][3]i32
    g[1][1][2] = 40
    g[1][0][0] = 2
    let p: *[2][3]i32 = @g[0]
    let q = p + 1
    return q[1][2] + (*q)[0][0]
""",
    # AGAST #3634: a by-value `[2][3]i32` param is `[2 x [3 x i32]] %a.arg`, as
    # ritz0 spells it, and the callee's own copy: its store doesn't reach g.
    # Cell (i, j) holds 3i + j (sum 15); `twice` hands its param on by value.
    "param_by_value": """\
fn sum(a: [2][3]i32) -> i32
    var t: i32 = 0
    for i in 0..2
        for j in 0..3
            t = t + a[i][j]
    a[0][0] = 100
    return t + a[0][0] - 100

fn twice(a: [2][3]i32) -> i32
    return sum(a) + a[1][2]

pub fn main() -> i32
    var g: [2][3]i32
    for i in 0..2
        for j in 0..3
            g[i][j] = (i * 3 + j) as i32
    let t = sum(g)
    if g[0][0] != 0 or t != 15
        return 1
    return twice(g) + 22
""",
    # ... rank 3 with a u8 leaf, and a struct leaf.
    "param_by_value_3d_struct": """\
struct P
    a: i32
    b: i64

fn cell(g: [2][3][4]u8, i: i32, j: i32, k: i32) -> i32
    return g[i][j][k] as i32

fn pb(ps: [2][2]P) -> i32
    return ps[1][0].a + (ps[0][1].b as i32)

pub fn main() -> i32
    var g: [2][3][4]u8
    for i in 0..2
        for j in 0..3
            for k in 0..4
                g[i][j][k] = (i * 12 + j * 4 + k) as u8
    var ps: [2][2]P
    ps[1][0].a = 3
    ps[0][1].b = 9
    if cell(g, 1, 2, 3) != 23 or cell(g, 0, 1, 2) != 6
        return 1
    return pb(ps) + 30
""",
    # AGAST #3634: `-> [2][3]i32` is `[2 x [3 x i32]]`; `return g` hands the
    # local back, and an annotated `var`, an inferred `let` and a param take it.
    "return_by_value": """\
fn mk(k: i32) -> [2][3]i32
    var g: [2][3]i32
    for i in 0..2
        for j in 0..3
            g[i][j] = (k * (i * 3 + j)) as i32
    return g

fn at(a: [2][3]i32, i: i32, j: i32) -> i32
    return a[i][j]

pub fn main() -> i32
    var g: [2][3]i32 = mk(1)
    let h = mk(2)
    g[0][0] = 7
    if g[1][2] != 5 or h[1][2] != 10 or h[0][1] != 2 or g[0][0] != 7
        return 1
    return g[1][2] + h[1][2] + at(mk(3), 1, 1) + at(h, 1, 0) + 9
""",
    # ... a large one (2 KiB, past SRET_MIN_BYTES) is `ptr byval` in and
    # `ptr sret` out, as a 1-D one is (#2306, #3181); both still copies.
    "by_value_large": """\
fn mk(k: i32) -> [16][32]i32
    var g: [16][32]i32
    for i in 0..16
        for j in 0..32
            g[i][j] = (k * (i * 32 + j)) as i32
    return g

fn bump(a: [16][32]i32) -> i32
    a[15][31] = 0
    return a[15][31] + a[1][2] + a[15][30]

pub fn main() -> i32
    let h = mk(1)
    var g: [16][32]i32 = mk(0)
    g = h
    if bump(g) != 34 + 510 or g[15][31] != 511
        return 1
    return g[1][1] + 9
""",
    # ... and a Drop leaf is moved, as ritz0 moves it: the callee drops the
    # param, the caller's `g` not again (D = 1 + 2), and a returned array
    # drops once, in the caller (D = 20 + 1 + 2).
    "by_value_drop": """\
var D: i32 = 0

struct S
    x: i32

impl Drop for S
    fn drop(self:& S)
        D = D + self.x

fn f(a: [2][1]S) -> i32
    return a[1][0].x

fn mk() -> [2][1]S
    var g: [2][1]S = [ [S { x: 1 }], [S { x: 2 }] ]
    return g

pub fn main() -> i32
    var t: i32 = 0
    if true
        var g: [2][1]S = [ [S { x: 1 }], [S { x: 2 }] ]
        t = f(g)
    if D != 3 or t != 2
        return 1
    if true
        let h = mk()
        D = D + 10 * h[1][0].x
    return D + 16
""",
    # AGAST #3634: `Box<[2][3]u8>` holds the whole array as its field.
    "generic_arg": """\
struct Box<T>
    v: T
    k: i32

pub fn main() -> i32
    var b: Box<[2][3]u8>
    for i in 0..2
        for j in 0..3
            b.v[i][j] = (i * 3 + j) as u8
    b.k = 30
    if b.v[0][2] != 2
        return 1
    return (b.v[1][2] as i32) + (b.v[1][1] as i32) + b.k + 3
""",
    # ... and through a generic fn (`id$arr2_arr3_i32`, as ritz0 mangles it),
    # `sizeof(T)`, and a struct leaf.
    "generic_arg_fn": """\
struct P
    a: i32
    b: i64

struct Box<T>
    v: T
    k: i32

fn id<T>(x: T) -> T
    return x

fn sz<T>() -> i64
    return sizeof(T)

fn keep<T>(x: T) -> T
    var y: T = x
    return y

fn corner<T>(a: [2][3]T) -> T
    return a[1][2]

pub fn main() -> i32
    var b: Box<[2][3]u8>
    b.v[1][2] = 7
    var c: Box<[2][2]P>
    c.v[1][0].a = 5
    var g: [2][3]i32
    g[1][2] = 10
    g[0][1] = 3
    let h = id<[2][3]i32>(g)
    let k = keep<[2][3]i32>(g)
    if sz<[2][3]i32>() != 24 or sz<[2][2]P>() != 64 or k[1][2] != 10
        return 1
    if corner<i32>(g) != 10 or corner<u8>(b.v) != 7
        return 2
    return h[1][2] + (b.v[1][2] as i32) + c.v[1][0].a + k[0][1] + 17
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
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link ({name}):\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RUNNABLE))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, RUNNABLE[name]) == EXPECTED


# ritz1 gaps against the oracle, as strict xfails: the room that closes one
# flips it.
RITZ1_GAPS: dict[str, int] = {}


@pytest.mark.integration
@pytest.mark.parametrize("name", [
    pytest.param(n, marks=[pytest.mark.xfail(
        strict=True, reason=f"AGAST #{RITZ1_GAPS[n]}: ritz1 does not do this yet")]
        if n in RITZ1_GAPS else [])
    for n in sorted(RUNNABLE)])
def test_ritz1_nested_array(ritz1_bin, tmp_path, name):
    """ritz1 must agree with ritz0 on every multi-dimensional array program."""
    assert _run("ritz1", tmp_path, name, RUNNABLE[name]) == EXPECTED


# Every multi-dimensional array use ritz1 does NOT lower must be a compile
# error naming the source line, never a silent `[N x i64]` (AGAST #1509).
# `needle` is the `:line:` the error must name.
FAIL_CLOSED = {
    # AGAST #2098 / #3635 / #4122: every `*[N][M]T` is lowered (RUNNABLE
    # "pointee*"); an address of another shape, or of a 1-D array, is refused
    # as ritz0 refuses it.
    "pointee_shape_mismatch": ("""\
pub fn main() -> i32
    var g: [2][4]i32
    let p: *[2][3]i32 = @g
    return 0
""", ":3:", "a reference to one type doesn't fit a reference to another"),
    "pointee_flat_mismatch": ("""\
fn f(p: *[2][3]i32) -> i32
    return p[1][2]

pub fn main() -> i32
    var g: [6]i32
    return f(@g)
""", ":6:", "a reference to one type doesn't fit a reference to another"),
    # AGAST #3635: `let c = *p` copies, but not move-only elements out from
    # behind the pointer, as ritz0 refuses it.
    "pointee_deref_copy_move_only": ("""\
struct S
    x: i32

impl Drop for S
    fn drop(self:& S)
        self.x = 0

pub fn main() -> i32
    var g: [1][2]S = [ [S { x: 1 }, S { x: 2 }] ]
    let p: *[1][2]S = @g
    let c = *p
    return c[0][1].x
""", ":11:", "moves its move-only elements out from behind the pointer"),
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
""", ":6:", "whole-array assignment to a local array from this value"),
    # A nested array literal does not even parse in ritz1 (closed already).
    "nested_literal": ("""\
pub fn main() -> i32
    var g: [2][2]i32 = [[1, 2], [3, 4]]
    return g[1][1]
""", ":1:", "cannot parse item"),
    # AGAST #3377: an N-D local initialiser is `[a, b, ..]` / `[v; n]` at
    # every level, with each level's count: a scalar row, a short literal, a
    # named row and a move-only row copied by `[row; n]` are refused.
    "local_initializer": ("""\
pub fn main() -> i32
    var g: [2][2]i32 = [0; 2]
    return g[1][1]
""", ":2:", "a row of a multi-dimensional array initializer must be"),
    # A literal short of its slot's length is LARB R42's error, on Sema since
    # AGAST #4011: it stops the compile before the emitter's shape refusal.
    "local_initializer_short": ("""\
pub fn main() -> i32
    var g: [2][2]i32 = [ [1, 2] ]
    return g[1][1]
""", ":2:24:", "an array literal of 1 element for a `[2][2]i32`"),
    "local_initializer_short_row": ("""\
pub fn main() -> i32
    var g: [2][2]i32 = [ [1, 2], [3] ]
    return g[1][1]
""", ":2:34:", "an array literal of 1 element for a `[2]i32`"),
    "local_initializer_named_row": ("""\
pub fn main() -> i32
    var r: [2]i32 = [1, 2]
    var g: [2][2]i32 = [ r, [3, 4] ]
    return g[1][1]
""", ":3:", "a row of a multi-dimensional array initializer must be"),
    "local_initializer_move_only_rows": ("""\
struct S
    x: i32

impl Drop for S
    fn drop(self:& S)
        let k = self.x

pub fn main() -> i32
    var g: [2][1]S = [ [S { x: 1 }; 1]; 2]
    return 0
""", ":9:", "`[v; n]` copies `v` into every element"),
    "global_initializer": ("""\
var gg: [2][2]i32 = [0; 2]

pub fn main() -> i32
    return gg[1][1]
""", ":1:", "an initializer on a multi-dimensional array is not supported"),
    "row_as_value": ("""\
fn take(p: i64) -> i32
    return 0

pub fn main() -> i32
    var g: [2][3]i32
    return take(g[1] as i64)
""", ":6:", "a row or a struct element of a multi-dimensional array is not a value"),
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
    # AGAST #4666: a row store is lowered (test_ritz1_parity_emit_gaps.py); a
    # scalar is no row, refused as a whole-array store from it is.
    "row_assign": ("""\
pub fn main() -> i32
    var g: [2][3]u8
    g[1] = 0
    return 0
""", ":3:", "whole-array assignment to a local array from this value"),
    # AGAST #3306: a struct element is a value only where a struct goes.
    "struct_elem_int_slot": ("""\
struct P
    a: i32

pub fn main() -> i32
    var g: [2][2]P
    g[1][1].a = 3
    return g[1][1]
""", ":7:", "a whole struct is not a value here"),
    # ... and a Drop one isn't moved out of the array that still drops it.
    "struct_elem_drop_move": ("""\
struct S
    x: i32

impl Drop for S
    fn drop(self:& S)
        self.x = 0

pub fn main() -> i32
    var g: [2][2]S
    g[1][1].x = 2
    let t: S = g[1][1]
    return t.x
""", ":11:", "cannot move out of an array element"),
    # AGAST #3634: a by-value N-D param, return or whole assignment takes an
    # array of its own shape only, as ritz0 says it at the value.
    "param_shape_mismatch": ("""\
fn f(a: [2][3]i32) -> i32
    return a[1][2]

pub fn main() -> i32
    var g: [3][2]i32
    return f(g)
""", ":6:", "an array only fits a slot of the same element type"),
    "param_leaf_mismatch": ("""\
fn f(a: [2][3]u8) -> i32
    return 0

pub fn main() -> i32
    var g: [2][3]i32
    return f(g)
""", ":6:", "an array only fits a slot of the same element type"),
    "param_not_an_array": ("""\
fn f(a: [2][3]i32) -> i32
    return a[1][2]

pub fn main() -> i32
    return f(0)
""", ":5:", "this value is not a multi-dimensional array of that shape"),
    "return_shape_mismatch": ("""\
fn mk() -> [2][3]i32
    var g: [3][2]i32
    return g

pub fn main() -> i32
    return 0
""", ":3:", "an array only fits a slot of the same element type"),
    "whole_assign_shape_mismatch": ("""\
pub fn main() -> i32
    var g: [2][3]i32
    var h: [3][2]i32
    g = h
    return 0
""", ":4:", "an array only fits a slot of the same element type"),
    # ... and a move-only leaf isn't copied over the old elements.
    "whole_assign_move_only": ("""\
struct S
    x: i32

impl Drop for S
    fn drop(self:& S)
        self.x = 0

pub fn main() -> i32
    var g: [1][1]S = [ [S { x: 1 }] ]
    var h: [1][1]S = [ [S { x: 2 }] ]
    g = h
    return 0
""", ":11:", "assigning a whole multi-dimensional array is not supported"),
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
def test_ritz1_nested_array_by_value_abi(ritz1_bin, tmp_path):
    """AGAST #3634: a by-value `[N][M]T` param and return are ritz0's nested
    `[N x [M x T]]`, and a large one (`by_value_large`) `ptr byval` / `ptr
    sret` at the leaf's alignment, as a 1-D one is (#2306, #3181)."""
    # A private free fn is external under a mangled symbol in ritz1 (#4356),
    # so match its `define` line by name and check the ABI text after it.
    sigs = {
        "return_by_value": [
            rf"define\b[^\n]*\[2 x \[3 x i32\]\] {test_ir.symbol('mk')}\(i32 %k\.arg\)",
            rf"define\b[^\n]*i32 {test_ir.symbol('at')}\(\[2 x \[3 x i32\]\] %a\.arg, i32 %i\.arg, i32 %j\.arg\)",
            rf"call \[2 x \[3 x i32\]\] {test_ir.symbol('mk')}\(",
        ],
        "by_value_large": [
            rf"define\b[^\n]*void {test_ir.symbol('mk')}\(ptr sret\(\[16 x \[32 x i32\]\]\) %ret\.sret, i32 %k\.arg\)",
            rf"define\b[^\n]*i32 {test_ir.symbol('bump')}\(ptr byval\(\[16 x \[32 x i32\]\]\) align 4 %a\.arg\)",
        ],
    }
    for name, want in sigs.items():
        comp, ll = _compile("ritz1", tmp_path, name, RUNNABLE[name])
        assert comp.returncode == 0, comp.stderr[-2000:]
        ir = ll.read_text()
        for w in want:
            assert re.search(w, ir), (w, ir)


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
