"""AGAST #2956: tuple types `(A, B, ...)` must parse in ritz1, as they do in
ritz0, in a return type and as a generic argument, and a tuple expression
`(a, b)` must lower where its tuple type is known.

THE DEFECT

    fn f(a: i32) -> (i32, i32)      # ritz1: c3.ritz:1:21: unexpected ','
        (a, a)

    var b: Box<(u32, u32)>          # ritz1: c4.ritz:5:17: unexpected 'u32'

ritz1's `type_spec` had the unit `()` (#2272) but no `( T, U, ... )` form,
and no tuple expression at all: only `let (x, y) = ...` destructured one.

THE FIX

A tuple type is a struct ritz1 synthesizes once per spelling, named as
ritz0's mangle_type_name spells a TupleType (`tuple_u32_u32`, nested
`tuple_tuple_i32_i32_i32`), with fields `0`, `1`, ... laid out as ritz0's
literal `{T, U}`.  So `Vec<(u32, u32)>` is `Vec$tuple_u32_u32` under both
compilers, and every place a struct value travels (by value, Vec element,
generic field, destructure) carries a tuple too.

A tuple expression `(a, b)` parses as a struct literal whose type is
resolved from its slot: a fn's return type (tail or `return`), an annotated
`let` / `var`, or an enclosing tuple literal's element (nested tuples).  One
with no known slot is typed in the emitter, from a call's parameter, a
struct field or an earlier match arm, else from its elements (AGAST #3005).
A tuple over a generic parameter (`-> (T, T)`, `(K, V)`) is a template,
as a generic struct is: each instantiation substitutes it (`tuple_i32_i32`
at T = i32) and registers that tuple (AGAST #2975), as does one whose
element points at a parameter (`(*T, i32)` -> `tuple_ptr_i32_i32`, #3173;
`(**T, i32)` -> `tuple_ptr_ptr_i32_i32`, #3184).

Every program that runs is a row of one table (test_table_rows.py, AGAST
#3889, `ROWS`), checked a chunk of rows at a time per compiler, a chunk one
package build (test_ritz1_deref_struct_arg.pkg_build).  The IR checks stay
tests of their own.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import test_table_rows as table_rows
from test_ritz1_deref_struct_arg import assert_table
from test_table_rows import Row, Run

RITZ_ROOT = Path(__file__).resolve().parent.parent

# The ticket's first program: a tuple return type with a tuple tail, plus
# `return (..)`, if/else arms valued a tuple, an annotated `let` initialised
# by a call and by a literal, and destructuring of each.
# f(3) = (3, 4) -> 34; g(2) = (4, 2) -> 6; f(5) = (5, 6) -> 11;
# w = (1, 2) -> 3; h(true) = (7, 8) -> 78; h(false) = (8, 7) -> 87.
# Total 51 + 3 + 78 - 87 = 45.
RETURN = """\
fn f(a: i32) -> (i32, i32)
    (a, a + 1)

fn g(a: i32) -> (i32, i32)
    return (a * 2, a)

fn h(c: bool) -> (i32, i32)
    if c
        (7, 8)
    else
        (8, 7)

pub fn main() -> i32
    let (x, y) = f(3)
    let (u, v) = g(2)
    let t: (i32, i32) = f(5)
    let (m, n) = t
    let w: (i32, i32) = (1, 2)
    let (w0, w1) = w
    let (h0, h1) = h(true)
    let (k0, k1) = h(false)
    x * 10 + y + u + v + m + n + w0 + w1 + h0 * 10 + h1 - k0 * 10 - k1
"""

# The ticket's second program, verbatim: a tuple as a generic argument.
TICKET_BOX = """\
struct Box<T>
    v: T
pub fn main() -> i32
    var b: Box<(u32, u32)>
    7
"""

# A tuple as a generic struct's field and as a Vec element (angelo's
# `functions: Vec<(u32, u32)>`, with `vec_new<(u32, u32)>()`).
# (5 + 6) + (20 + 21) + 2 = 54.
GENERIC = """\
import ritzlib.gvec

struct Box<T>
    v: T

fn mk(a: u32) -> (u32, u32)
    (a, a + 1)

pub fn main() -> i32
    var b: Box<(u32, u32)> = Box<(u32, u32)> { v: mk(5) }
    let (p, q) = b.v
    var fns: Vec<(u32, u32)> = vec_new<(u32, u32)>()
    vec_push<(u32, u32)>(@&fns, mk(10))
    vec_push<(u32, u32)>(@&fns, mk(20))
    let (s, l) = vec_get<(u32, u32)>(@fns, 1)
    (p + q + s + l + fns.len as u32) as i32
"""

# A 3-tuple of mixed widths, and a nested tuple whose inner literal takes
# its type from the outer one's element.  `t.0` reads an element by index.
# 4 + 8 + 3 + 10 + 11 + 12 = 48.
WIDE_AND_NESTED = """\
fn tri(a: i32) -> (i32, i64, u8)
    (a, a as i64 * 2, 3)

fn nest(a: i32) -> ((i32, i32), i32)
    ((a, a + 1), a + 2)

pub fn main() -> i32
    let t: (i32, i64, u8) = tri(4)
    let (p, c) = nest(10)
    let (a, b) = p
    t.0 + t.1 as i32 + t.2 as i32 + a + b + c
"""

# AGAST #2974: `let (x, y) = ..` of a tuple literal, or of an if / match whose
# arms are tuple literals, has no tuple type to name; ritz1 binds each name to
# its element instead.  `sp` is the ticket's program (angelo
# raster/fill.ritz:59).  sp(1, 4) + sp(4, 1) + pick(0) + pick(1) + pick(7)
# = 3 + 3 + 12 + 34 + 56 = 108.
SPLIT_IF = """\
fn sp(a: f32, b: f32) -> i32
    let (x0, x1) = if a <= b
        (a, b)
    else
        (b, a)
    (x1 - x0) as i32

fn pick(n: i32) -> i32
    let (p, q) = if n == 0
        (1, 2)
    else if n == 1
        (3, 4)
    else
        (5, 6)
    p * 10 + q

pub fn main() -> i32
    sp(1.0, 4.0) + sp(4.0, 1.0) + pick(0) + pick(1) + pick(7)
"""

# A literal, one of locals, and one whose elements differ in type.
# (40 - 3) + (5 + 7) = 49.
SPLIT_LITERAL = """\
pub fn main() -> i32
    let (x, y) = (3, 40)
    let (u, v) = (y, x)
    let (f, n) = (2.5, 7u8)
    u - v + (f * 2.0) as i32 + n as i32
"""

# A match whose arms bind nothing.  12 + 34 + 56 = 102.
SPLIT_MATCH = """\
fn m(n: i32) -> i32
    let (a, b) = match n
        0 => (1, 2)
        1 => (3, 4)
        _ => (5, 6)
    a * 10 + b

pub fn main() -> i32
    m(0) + m(1) + m(9)
"""

# The condition and the chosen arm's elements each run once, in order.
SPLIT_ONCE = """\
var g: i32 = 0

fn bump(k: i32) -> i32
    g = g * 10 + k
    k

pub fn main() -> i32
    let (a, b) = if bump(1) == 1
        (bump(2), bump(3))
    else
        (bump(4), bump(5))
    g + (a + b) * 0
"""


# AGAST #2975: a tuple type over a generic parameter is the tuple over the
# instantiation's argument, `(T, T)` at T = i32 being `tuple_i32_i32`.
# The ticket's program: sw<i32>(1, 2) = (2, 1) -> 21.
GEN_FN = """\
fn sw<T>(a: T, b: T) -> (T, T)
    (b, a)

pub fn main() -> i32
    let (x, y) = sw<i32>(1, 2)
    x * 10 + y
"""

# A nested tuple over T: nn<i64>(1, 2) = ((1, 2), 3) -> 123.
GEN_NESTED = """\
fn nn<T>(a: T, b: T) -> ((T, T), i32)
    ((a, b), 3)

pub fn main() -> i32
    let (p, c) = nn<i64>(1, 2)
    let (a, b) = p
    (a * 100 + b * 10) as i32 + c
"""

# A param, at two instantiations: 5 * 10 + 7 = 57.
GEN_PARAM = """\
fn fst<T>(t: (T, i32)) -> T
    let (a, b) = t
    a

pub fn main() -> i32
    let t: (i64, i32) = (5, 2)
    let u: (u8, i32) = (7, 1)
    (fst<i64>(t) * 10) as i32 + fst<u8>(u) as i32
"""

# A generic struct's field: 3 * 10 + 4 = 34.
GEN_STRUCT = """\
struct P<T>
    f: (T, i32)

pub fn main() -> i32
    var p: P<i64> = P<i64> { f: (3, 4) }
    let (a, b) = p.f
    a as i32 * 10 + b
"""

# `Vec<(T, i32)>` in a one-parameter fn, named in a call's type argument:
# 4 * 10 + 2 = 42.
GEN_VEC = """\
import ritzlib.gvec

fn mk<T>(a: T) -> Vec<(T, i32)>
    var v: Vec<(T, i32)> = vec_new<(T, i32)>()
    vec_push<(T, i32)>(@&v, (a, 2))
    v

pub fn main() -> i32
    let v: Vec<(i64, i32)> = mk<i64>(4)
    let (a, b) = vec_get<(i64, i32)>(@v, 0)
    a as i32 * 10 + b
"""

# `Vec<(K, V)>` in a two-parameter generic impl: 6 * 10 + 7 + 2 = 69.
GEN_IMPL_VEC = """\
import ritzlib.gvec

struct Map<K, V>
    items: Vec<(K, V)>

impl<K, V> Map<K, V>
    fn put(self: @&Map<K, V>, k: K, v: V)
        vec_push<(K, V)>(@&self.items, (k, v))

    fn at(self: @Map<K, V>, i: i64) -> (K, V)
        vec_get<(K, V)>(@self.items, i)

pub fn main() -> i32
    var m: Map<i32, i64> = Map<i32, i64> { items: vec_new<(i32, i64)>() }
    m.put(4, 5)
    m.put(6, 7)
    let (k, v) = m.at(1)
    k * 10 + v as i32 + m.items.len as i32
"""

# AGAST #3173: an element pointing at the parameter, at T = i32, at a
# struct and at T = *u8 (`tuple_ptr_ptr_u8_i32`):
# (5 + 1) + (9 + 1) + (11 + 1) = 28.
GEN_PTR = """\
struct Foo
    a: i32

fn pp<T>(p: *T) -> (*T, i32)
    (p, 1)

pub fn main() -> i32
    var x: i32 = 5
    var g: Foo = Foo { a: 9 }
    var b: u8 = 200
    var pb: *u8 = @b
    let (q, c) = pp<i32>(@x)
    let (s, e) = pp<Foo>(@g)
    let (w, z) = pp<*u8>(@pb)
    var k: i32 = 0
    if **w == 200
        k = 11
    *q + c + s.a + e + k + z
"""

# `*T` at T = *u8 is `**u8`: `**w` loads a u8.  The u8 is the low byte of
# a u16 0x07C8, so a wider load reads 1992 or more, compared in full (an
# exit status keeps only the low byte).  A destructured name is typed by its
# tuple element, generic or not: ritz0 dropped that type, so `b` and `**w`
# were bare LLVM `i8`s and widened signed, 200 -> -56 (AGAST #3192).
GEN_PTR_U8 = """\
fn pp<T>(p: *T) -> (*T, i32)
    (p, 1)

fn qq(b: u8) -> (u8, i32)
    (b, 1)

pub fn main() -> i32
    var h: u16 = 1992
    var pb: *u8 = @h as *u8
    let (w, z) = pp<*u8>(@pb)
    let (b, y) = qq(200)
    if b as i32 != 200
        return 4
    if **w as i32 == 200
        return 10 + z
    3
"""

# `@T` at a struct and `@&T` at i64 (`tuple_ref_Foo_i32`,
# `tuple_refmut_i64_i32`), read by index: ritz1 can't destructure a `@`
# element, generic or not.  Unannotated, so the instantiation alone types
# them.  (4 + 2) * 10 + (7 + 3) = 70.
GEN_REF = """\
struct Foo
    a: i32

fn rp<T>(p: @T) -> (@T, i32)
    (p, 2)

fn mp<T>(p: @&T) -> (@&T, i32)
    (p, 3)

pub fn main() -> i32
    let f: Foo = Foo { a: 4 }
    let t = rp<Foo>(@f)
    var n: i64 = 7
    let u = mp<i64>(@&n)
    (t.0.a + t.1) * 10 + *u.0 as i32 + u.1
"""

# AGAST #3184: an element `**T`, at T = i32 (the ticket's program,
# `tuple_ptr_ptr_i32_i32`) and at a struct (`tuple_ptr_ptr_Foo_i32`):
# (5 + 1) + (9 + 1) = 16.
GEN_PTR_PTR = """\
struct Foo
    a: i32

fn pp<T>(p: **T) -> (**T, i32)
    (p, 1)

pub fn main() -> i32
    var x: i32 = 5
    var px: *i32 = @x
    var g: Foo = Foo { a: 9 }
    var pg: *Foo = @g
    let (q, c) = pp<i32>(@px)
    let (s, e) = pp<Foo>(@pg)
    let fs: *Foo = *s
    **q + c + fs.a + e
"""

# `**T` at T = i16 binds a `**i16`: `**q` loads 2 bytes.  The i16 is the
# low half of an i32 0x00050007, so a wider load reads far more than 7;
# compared in full (an exit status keeps only the low byte).
GEN_PTR_PTR_I16 = """\
fn pp<T>(p: **T) -> (**T, i32)
    (p, 1)

pub fn main() -> i32
    var h: i32 = 327687
    var ph: *i16 = @h as *i16
    let (q, c) = pp<i16>(@ph)
    if **q as i32 == 7
        return 10 + c
    3
"""

# `**T` at T = *u8 is `***u8` (`tuple_ptr_ptr_ptr_u8_i32`): `***w` loads
# the u8, the low byte of a u16 0x07C8.
GEN_PTR_PTR_DEEP = """\
fn pp<T>(p: **T) -> (**T, i32)
    (p, 1)

pub fn main() -> i32
    var h: u16 = 1992
    var pb: *u8 = @h as *u8
    var ppb: **u8 = @pb
    let (w, z) = pp<*u8>(@ppb)
    let v: u8 = ***w
    if v == 200
        return 10 + z
    3
"""

# AGAST #3005: a tuple no slot types (the rejections of #2956 / #2974), typed
# from its elements.  `let x = (a, a)`: f(1) = 1 + 1 + 1 = 3.
INFER_LET = """\
fn f(a: i32) -> i32
    let x = (a, a)
    let (p, q) = x
    a + p + q

pub fn main() -> i32
    f(1)
"""

# An if arm with statements before its tuple.  f(true) + f(false) = 4 + 0.
INFER_IF_ARM_STMTS = """\
fn f(c: bool) -> i32
    let (x, y) = if c
        let q = 3
        (q, 1)
    else
        (0, 0)
    x + y

pub fn main() -> i32
    f(true) + f(false)
"""

# A match arm binding a name its tuple reads; ritz0 can't build it (#3022).
# f(Some(2)) + f(None) = 3 + 0.
INFER_MATCH_ARM_BINDS = """\
import ritzlib.option

fn f(o: Option<i32>) -> i32
    let (x, y) = match o
        Some(v) => (v, 1)
        _ => (0, 0)
    x + y

pub fn main() -> i32
    f(Some(2)) + f(None)
"""


# Every program runs as a table row (AGAST #3889), its id the old
# parametrised test's less the compiler, and less the program text and exit
# status pytest spelled out in it: `test_tuple_programs_run[tuple_return-<text>-45-ritz0]`
# is `tuple_programs_run[tuple_return]` on ritz0.  ROWS is assembled below.
BOTH = ("ritz0", "ritz1")

# The programs ritz1 refused until AGAST #3005 now run, as on ritz0.  ritz0
# can't build INFER_MATCH_ARM_BINDS (#3022): ritz1 only.
NO_SLOT = [
    ("tuple_infer_let", INFER_LET, 3, BOTH),
    ("tuple_infer_if_arm_stmts", INFER_IF_ARM_STMTS, 4, BOTH),
    ("tuple_infer_match_arm_binds", INFER_MATCH_ARM_BINDS, 3, ("ritz1",)),
]

PROGRAMS = [
    ("tuple_return", RETURN, 45),
    ("tuple_box_ticket", TICKET_BOX, 7),
    ("tuple_generic", GENERIC, 54),
    ("tuple_wide_nested", WIDE_AND_NESTED, 48),
    ("tuple_split_if", SPLIT_IF, 108),
    ("tuple_split_literal", SPLIT_LITERAL, 49),
    ("tuple_split_match", SPLIT_MATCH, 102),
    ("tuple_split_once", SPLIT_ONCE, 123),
    ("tuple_generic_fn", GEN_FN, 21),
    ("tuple_generic_nested", GEN_NESTED, 123),
    ("tuple_generic_param", GEN_PARAM, 57),
    ("tuple_generic_struct", GEN_STRUCT, 34),
    ("tuple_generic_vec", GEN_VEC, 42),
    ("tuple_generic_impl_vec", GEN_IMPL_VEC, 69),
    ("tuple_generic_ptr", GEN_PTR, 28),
    ("tuple_generic_ref", GEN_REF, 70),
    ("tuple_generic_ptr_ptr", GEN_PTR_PTR, 16),
    ("tuple_generic_ptr_ptr_i16", GEN_PTR_PTR_I16, 11),
    ("tuple_generic_ptr_ptr_deep", GEN_PTR_PTR_DEEP, 11),
]


def _ritz1_ir(ritz1_bin, tmp_path, src_text: str) -> subprocess.CompletedProcess:
    src = tmp_path / "t.ritz"
    src.write_text(src_text)
    out = tmp_path / "t.ll"
    proc = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(out)],
        cwd=tmp_path,
        env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        capture_output=True,
        text=True,
        timeout=300,
    )
    proc.ir = out.read_text() if proc.returncode == 0 and out.exists() else ""
    return proc


@pytest.mark.integration
def test_ritz1_mangles_and_lays_out_tuples_as_ritz0(ritz1_bin, tmp_path):
    """`(u32, u32)` is ritz0's `tuple_u32_u32`, laid out `{i32, i32}`; a
    nested tuple spells its element's spelling; `Box<(u32, u32)>` is
    `Box$tuple_u32_u32`."""
    proc = _ritz1_ir(
        ritz1_bin,
        tmp_path,
        "struct Box<T>\n    v: T\n\n"
        "fn f(b: Box<(u32, u32)>, n: ((i32, i64), u8)) -> i32\n    0\n\n"
        "pub fn main() -> i32\n    0\n",
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    ir = proc.ir
    assert re.search(r"^%tuple_u32_u32 = type \{\s*i32,\s*i32\s*\}$", ir, re.M), ir[:3000]
    assert re.search(r"^%tuple_i32_i64 = type \{\s*i32,\s*i64\s*\}$", ir, re.M), ir[:3000]
    assert re.search(
        r"^%tuple_tuple_i32_i64_u8 = type \{\s*%tuple_i32_i64,\s*i8\s*\}$", ir, re.M
    ), ir[:3000]
    assert re.search(r"^%Box\$tuple_u32_u32 = type \{\s*%tuple_u32_u32\s*\}$", ir, re.M), ir[:3000]


@pytest.mark.integration
def test_ritz1_rejects_tuple_element_it_cannot_type(ritz1_bin, tmp_path):
    """A tuple with no tuple type is typed from its elements (AGAST #3005);
    an element ritz1 can't spell as a tuple field (a pointer) is a located
    error at that element, not a struct literal of an unnamed type."""
    proc = _ritz1_ir(
        ritz1_bin,
        tmp_path,
        "fn f(p: *u8) -> i32\n    let t = (p, 1)\n    0\n\npub fn main() -> i32\n    f(null)\n",
    )
    assert proc.returncode != 0
    assert re.search(r"t\.ritz:2:14: .*tuple element.*#3024", proc.stderr), proc.stderr[-2000:]


@pytest.mark.integration
def test_ritz1_substitutes_tuple_over_generic_param(ritz1_bin, tmp_path):
    """AGAST #2975: `-> (T, T)` in `fn sw<T>` was refused (#2956), since the
    `%tuple_T_T = {%T, %T}` it parsed to was never substituted.  At sw<i32>
    it is ritz0's `tuple_i32_i32`, `{i32, i32}`, and the template's
    `tuple_T_T` is never emitted."""
    proc = _ritz1_ir(ritz1_bin, tmp_path, GEN_FN)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert re.search(r"^%tuple_i32_i32 = type \{\s*i32,\s*i32\s*\}$", proc.ir, re.M), proc.ir[:3000]
    assert re.search(r"define\b.*%tuple_i32_i32 @\"?sw\$i32", proc.ir), proc.ir[:3000]
    assert "tuple_T_T" not in proc.ir, proc.ir[:3000]


@pytest.mark.integration
def test_ritz1_substitutes_tuple_element_pointing_at_generic_param(ritz1_bin, tmp_path):
    """AGAST #3173: `(*T, i32)` was refused.  At pp<i32> it is ritz0's
    `tuple_ptr_i32_i32`, `{ptr, i32}`; the template's `tuple_ptr_T_i32` is
    never emitted."""
    proc = _ritz1_ir(ritz1_bin, tmp_path, GEN_PTR)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert re.search(r"^%tuple_ptr_i32_i32 = type \{\s*ptr,\s*i32\s*\}$", proc.ir, re.MULTILINE), proc.ir[:3000]
    assert re.search(r"define\b.*%tuple_ptr_i32_i32 @\"?pp\$i32", proc.ir), proc.ir[:3000]
    assert "ptr_T" not in proc.ir, proc.ir[:3000]


@pytest.mark.integration
def test_ritz1_substitutes_tuple_element_double_pointer_at_generic_param(ritz1_bin, tmp_path):
    """AGAST #3184: `(**T, i32)` was refused.  At pp<i32> it is ritz0's
    `tuple_ptr_ptr_i32_i32`, `{ptr, i32}`; the template's
    `tuple_ptr_ptr_T_i32` is never emitted."""
    proc = _ritz1_ir(ritz1_bin, tmp_path, GEN_PTR_PTR)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert re.search(r"^%tuple_ptr_ptr_i32_i32 = type \{\s*ptr,\s*i32\s*\}$", proc.ir, re.MULTILINE), proc.ir[:3000]
    assert re.search(r"^%tuple_ptr_ptr_Foo_i32 = type \{\s*ptr,\s*i32\s*\}$", proc.ir, re.MULTILINE), proc.ir[:3000]
    assert re.search(r"define\b.*%tuple_ptr_ptr_i32_i32 @\"?pp\$i32", proc.ir), proc.ir[:3000]
    assert "ptr_T" not in proc.ir, proc.ir[:3000]


# AGAST #3232: a number straight after `.` is a tuple field index, never a
# float.  The lexer's `[0-9]+\.[0-9]+` took `0.1` in `p.0.1` as one FLOAT
# (ritz1: "unexpected '0.1'"); ritz0 had the same defect until #2284.
# (3, 4), 5 -> p.0.1 + p.1 = 4 + 5 = 9.  `q.1.0` checks the other order, and
# `2.5` after a `+` (not a `.`) must still lex as a float: 9 + 0 + 2 = 11.
NESTED_INDEX = """\
fn main() -> i32
    let p: ((i32, i32), i32) = ((3, 4), 5)
    p.0.1 + p.1
"""

NESTED_INDEX_MIXED = """\
fn main() -> i32
    let p: ((i32, i32), i32) = ((3, 4), 5)
    let q: (i32, (i32, i32)) = (1, (0, 7))
    let f: f64 = 0.0 + 2.5
    p.0.1 + p.1 + q.1.0 + (f as i32)
"""


NESTED_INDEX_PROGRAMS = [
    ("tuple_nested_index", NESTED_INDEX, 9),
    ("tuple_nested_index_mixed", NESTED_INDEX_MIXED, 11),
]

ROWS = (
    [Row(f"tuple_with_no_slot_runs[{name}]", compilers, Run(program, want))
     for name, program, want, compilers in NO_SLOT]
    + [Row(f"tuple_programs_run[{name}]", BOTH, Run(program, want))
       for name, program, want in PROGRAMS]
    # AGAST #3173/#3192: `(*T, i32)` at T = *u8 binds a `**u8`, and a
    # destructured `u8` (generic or not) widens as a u8.
    + [Row("destructured_u8_widens_unsigned", BOTH, Run(GEN_PTR_U8, 11))]
    # AGAST #3232: `p.0.1` is p . 0 . 1, not p . <float 0.1>.
    + [Row(f"nested_tuple_index_lexes_as_ints[{name}]", BOTH, Run(program, want))
       for name, program, want in NESTED_INDEX_PROGRAMS]
)


@pytest.mark.integration
@pytest.mark.parametrize("compiler,chunk", table_rows.chunks(ROWS),
                         ids=[f"{c}-{i}" for c, i in table_rows.chunks(ROWS)])
def test_every_row(ritz1_bin, tmp_path, compiler, chunk):
    """Every program above runs, and exits as it says."""
    assert_table(compiler, table_rows.chunk(ROWS, compiler, chunk), tmp_path)
