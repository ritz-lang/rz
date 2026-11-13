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
with no known slot is a located error rather than a guess, as is a tuple
over a generic parameter (`-> (T, T)`), which monomorphization would
leave a `%T` field in.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg

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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize(
    "name,program,expected",
    [
        ("tuple_return", RETURN, 45),
        ("tuple_box_ticket", TICKET_BOX, 7),
        ("tuple_generic", GENERIC, 54),
        ("tuple_wide_nested", WIDE_AND_NESTED, 48),
    ],
)
def test_tuple_programs_run(ritz1_bin, tmp_path, compiler, name, program, expected):
    assert _run_pkg(compiler, tmp_path, name, program) == expected


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
def test_ritz1_rejects_tuple_expr_with_no_known_type(ritz1_bin, tmp_path):
    """A tuple expression whose slot names no tuple type is a located error,
    not a struct literal of an unnamed type."""
    proc = _ritz1_ir(
        ritz1_bin,
        tmp_path,
        "fn f(a: i32) -> i32\n    let x = (a, a)\n    a\n\npub fn main() -> i32\n    f(1)\n",
    )
    assert proc.returncode != 0
    assert re.search(r"t\.ritz:2:13: .*tuple", proc.stderr), proc.stderr[-2000:]


@pytest.mark.integration
def test_ritz1_rejects_tuple_over_generic_param(ritz1_bin, tmp_path):
    """`-> (T, T)` in `fn f<T>` would be a `%tuple_T_T = {%T, %T}` that
    monomorphization never substitutes (invalid IR); ritz1 refuses it,
    located, instead of emitting it."""
    proc = _ritz1_ir(
        ritz1_bin,
        tmp_path,
        "fn sw<T>(a: T, b: T) -> (T, T)\n    (b, a)\n\n"
        "pub fn main() -> i32\n    let (x, y) = sw<i32>(1, 2)\n    x * 10 + y\n",
    )
    assert proc.returncode != 0
    assert re.search(r"t\.ritz:1:\d+: .*tuple type over generic parameter `T`", proc.stderr), (
        proc.stderr[-2000:]
    )
