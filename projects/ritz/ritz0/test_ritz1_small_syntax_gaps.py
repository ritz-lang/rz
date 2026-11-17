"""Regression tests for AGAST #1794: four small forms ritz0 accepts that ritz1
did not (items 2-5 of #1530, all used by angelo).

    let d: [0]u8 = []               # empty array literal
    let r = id<@E>(e)               # generic call with an `@T` type argument
    match o                         # qualified enum PATTERN
        Opt.None => 1
    self.glyph_points = points[:]   # full slice (a copy, for a Vec)

Before the fix, `[]`, `Opt.None =>` and `a[:]` died with `cannot parse item`.
`id<@E>(e)` already parsed through generic_args (#1612), but its type argument
had no spelling: ritz1 emitted `call void @id$(void ...)`.  ritz0 mangles it
`id$ref_E`, and that is what ritz1 now does too.

`a[:]` lowers to `a.slice(0, a.len())` as in ritz0, which for a Vec reaches
`vec_slice<T>`.  Two monomorph bugs on that path are covered here too:
`vec_slice<T>` declares `let item: T`, and a bare `T` local became the struct
`%T$i32`; and `vec_slice$T` was never instantiated for a Vec reached through
a `:&` / `@` / `*` binding (angelo's `points:& Vec<HintPoint>`), only for a
by-value one.

ritz0 is the oracle: each program's expected exit code is checked against
both compilers.  Programs that import ritzlib go through build.py, which also
links the imported modules (gvec needs ritzlib.memory's allocator).
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0
from test_ritz1_builtin_struct_shadow import _run_pkg

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
# Build product, not a tracked file (see test_ritz1_ptr_arith_chain.py).
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


# --- item 2: empty array literal `[]` -----------------------------------------

EMPTY_ARRAY = {
    # angelo/src/loader/glyf.ritz's shape, plus a wider element type.
    "empty_array_literal": (
        """\
fn main() -> i32
    let d: [0]u8 = []
    var e: [0]i64 = []
    return 7
""",
        7,
    ),
}

# --- item 3: generic call with an `@T` type argument ---------------------------

REF_TYPE_ARG = {
    # angelo's shape: the argument is an `@E` parameter, the result passed on.
    "ref_type_arg_param": (
        """\
struct E
    x: i32

fn id<T>(v: T) -> T
    return v

fn getx(e: @E) -> i32
    return e.x

fn g(e: @E) -> i32
    let r = id<@E>(e)
    return getx(r)

fn main() -> i32
    var e: E = E { x: 42 }
    return g(@e)
""",
        42,
    ),
    # The result is a reference: field access through it must see E's layout.
    "ref_type_arg_member": (
        """\
struct E
    a: i64
    x: i32

fn id<T>(v: T) -> T
    return v

fn main() -> i32
    var e: E = E { a: 5, x: 37 }
    let r = id<@E>(@e)
    return (r.a as i32) + r.x
""",
        42,
    ),
}

# --- item 4: qualified enum pattern `E.V =>` -----------------------------------

QUALIFIED_PATTERN = {
    # #1530's repro shape: qualified unit variant arms and a wildcard.
    "qualified_unit_pattern": (
        """\
enum Mode
    Off
    Low
    High

fn f(m: Mode) -> i32
    match m
        Mode.High => 40
        Mode.Low => 2
        _ => 0

fn main() -> i32
    return f(Mode.High) + f(Mode.Low) + f(Mode.Off)
""",
        42,
    ),
    # angelo's other site binds a payload: `ParsedGlyph.Simple(outline) =>`,
    # over a user enum with a payload variant (laid out by ritz1 since
    # AGAST #1797; it was `{ i8 }`, with no payload slot).
    "qualified_payload_pattern": (
        """\
enum Opt
    Vacant
    Holds(i32)

fn f(o: Opt) -> i32
    match o
        Opt.Holds(v) => v
        Opt.Vacant => 100

fn main() -> i32
    return f(Holds(41)) + f(Opt.Vacant) - 99
""",
        42,
    ),
    # Match as an expression, with every arm qualified.
    "qualified_pattern_match_expr": (
        """\
enum Shade
    Light
    Dark

fn code(s: Shade) -> i32
    let r = match s
        Shade.Light => 2
        Shade.Dark => 40
    return r

fn main() -> i32
    return code(Shade.Light) + code(Shade.Dark)
""",
        42,
    ),
}

# --- item 5: full slice `a[:]` --------------------------------------------------

FULL_SLICE = {
    # A Vec full slice is a COPY (ritz0: vec_slice<T>(&v, 0, len)): pushing
    # onto it leaves the original alone.  3 * 10 + 2.  (`s` is annotated:
    # an un-annotated local from a method call loses its type, #1798.)
    "full_slice_vec_copy": (
        """\
import ritzlib.memory
import ritzlib.gvec

fn main() -> i32
    var a: Vec<i32> = vec_new<i32>()
    a.push(3)
    a.push(4)
    var s = a[:]
    s.push(5)
    return (s.len() * 10 + a.len()) as i32
""",
        32,
    ),
    # angelo's shape: `points[:]` on a `:&` Vec of POD structs, values kept.
    "full_slice_borrowed_struct_vec": (
        """\
import ritzlib.memory
import ritzlib.gvec

struct HintPoint
    x: i32
    y: i32

fn dup_sum(points:& Vec<HintPoint>) -> i32
    var c: Vec<HintPoint> = points[:]
    var q: HintPoint
    q.x = 100
    q.y = 100
    c.push(q)
    return (c.len() * 10 + points.len()) as i32 + c[1].y

fn main() -> i32
    var v: Vec<HintPoint> = vec_new<HintPoint>()
    var p: HintPoint
    p.x = 1
    p.y = 2
    v.push(p)
    p.y = 10
    v.push(p)
    return dup_sum(@&v)
""",
        42,
    ),
}

# --- colon slices `a[lo:hi]`, `a[:hi]`, `a[lo:]` (AGAST #3766) -------------------
# ritz0's colon slice (ritz_ast.Slice) is `a[lo..hi]` with a missing end taken
# as 0 / `a.len()`.  ritz1 parsed only `a[:]`, so ritzlib/tests/
# test_slice_syntax.ritz failed whole (0/13) under ritz1.

_COLON_VEC = """\
import ritzlib.memory
import ritzlib.gvec

fn make() -> Vec<i64>
    var v: Vec<i64> = vec_new<i64>()
    v.push(10)
    v.push(20)
    v.push(30)
    v.push(40)
    return v

fn main() -> i32
"""

COLON_SLICE = {
    # [20, 30]: 2 * 10 + 30.
    "colon_slice_closed": (_COLON_VEC + """\
    var v: Vec<i64> = make()
    var s: Vec<i64> = v[1:3]
    return (s.len() * 10 + s[1]) as i32
""", 50),
    # [10, 20, 30]: 3 * 10 + 30.
    "colon_slice_open_start": (_COLON_VEC + """\
    var v: Vec<i64> = make()
    var s: Vec<i64> = v[:3]
    return (s.len() * 10 + s[2]) as i32
""", 60),
    # The open end is the receiver's own length, with postfix ops after it:
    # [30, 40] has len 2 and [0] 30.
    "colon_slice_open_end": (_COLON_VEC + """\
    var v: Vec<i64> = make()
    return (v[2:].len() * 100 + v[2:][0]) as i32
""", 230),
}

# --- monomorph: a bare `T` local in a generic body ------------------------------

GENERIC_LOCAL = {
    # `let y: T` at T = i32 was emitted `alloca %T$i32` (unsized type).
    "generic_let_t": (
        """\
fn id<T>(x: T) -> T
    let y: T = x
    return y

fn main() -> i32
    return id<i32>(42)
""",
        42,
    ),
    # vec_slice<T>'s shape: a `T` local loaded through a `*T`, in a loop.
    "generic_var_t_from_ptr": (
        """\
fn last<T>(p: *T, n: i64) -> T
    var r: T = *p
    for i in 0..n
        let item: T = *(p + i)
        r = item
    return r

fn main() -> i32
    var a: [3]i64 = [1, 2, 42]
    return last<i64>(@a[0], 3) as i32
""",
        42,
    ),
}

# --- AGAST #3803: slicing a Vec / String held in a struct field ------------------
#
# ritz1 rewrote `v[lo..hi]` into `v.slice(lo, hi)` only for a local `v`, so
# `h.v[2..4]` stayed an index and was refused: "this can't be sliced".  Each row
# is a separate receiver shape the rewrite resolves, in range (`h.v[2..4]`) and
# colon (`h.v[2:]`, #3766) syntax; `h.v[:]` already lowered to a method call
# and guards that path.

MEMBER_SLICE_PRELUDE = """\
import ritzlib.memory
import ritzlib.gvec

struct H
    v: Vec<i64>

struct O
    h: H

struct P
    p: *Vec<i64>

struct Q
    h: P

struct R
    r: @Vec<i64>

fn make() -> Vec<i64>
    var v: Vec<i64> = vec_new<i64>()
    for i in 0..6
        v.push(i * 10)
    return v

"""

MEMBER_SLICE = {
    # The ticket's repro: the slice is a method receiver and an index base.
    # 2 * 100 + 20.
    "member_range_chain": (
        MEMBER_SLICE_PRELUDE
        + """\
fn main() -> i32
    var h: H = H { v: make() }
    return (h.v[2..4].len() * 100 + h.v[2..4][0]) as i32
""",
        220,
    ),
    # Into an annotated local, through two members, inclusive: 1..=3 is 3
    # elements, the last 30.  3 * 10 + 30.
    "nested_member_range_decl": (
        MEMBER_SLICE_PRELUDE
        + """\
fn main() -> i32
    var o: O = O { h: H { v: make() } }
    var s: Vec<i64> = o.h.v[1..=3]
    return (s.len() * 10 + s[2]) as i32
""",
        60,
    ),
    # A String field: string_slice, a copy.  The length is `data.len`.
    # "abcdef"[1..4] is "bcd": 3 * 10 + 'd' (100).
    "string_member_range": (
        """\
import ritzlib.memory
import ritzlib.gvec
import ritzlib.string

struct N
    s: String

fn main() -> i32
    var n: N = N { s: string_from("abcdef") }
    var t: String = n.s[1..4]
    return (t.data.len * 10) as i32 + (*(t.data.data + 2) as i32)
""",
        130,
    ),
    # A Span field with no ritzlib.span: the view built in place, so a write
    # through `t` lands in `a`.  2 * 10 + 7 + 30.
    "span_member_range_view": (
        """\
struct G
    s: Span<i32>

fn main() -> i32
    var a: [4]i32 = [10, 20, 30, 40]
    var g: G
    g.s = Span<i32> { ptr: @a[0], len: 4 }
    var t: Span<i32> = g.s[1..3]
    t[0] = 7
    return (t.len * 10) as i32 + a[1] + t[1]
""",
        57,
    ),
    # The ticket's colon shape, open end: the field's own length bounds it.
    # [20, 30, 40, 50]: 4 * 10 + 20.
    "member_colon_open_end_chain": (
        MEMBER_SLICE_PRELUDE
        + """\
fn main() -> i32
    var h: H = H { v: make() }
    return (h.v[2:].len() * 10 + h.v[2:][0]) as i32
""",
        60,
    ),
    # Closed colon slice through two members: [10, 20], 2 * 10 + 20.
    "nested_member_colon_closed": (
        MEMBER_SLICE_PRELUDE
        + """\
fn main() -> i32
    var o: O = O { h: H { v: make() } }
    var s: Vec<i64> = o.h.v[1:3]
    return (s.len() * 10 + s[1]) as i32
""",
        40,
    ),
    # The colon form: a copy, so a push leaves the field alone.  7 * 10 + 6.
    "member_colon_full": (
        MEMBER_SLICE_PRELUDE
        + """\
fn main() -> i32
    var h: H = H { v: make() }
    var s: Vec<i64> = h.v[:]
    s.push(99)
    return (s.len() * 10 + h.v.len()) as i32
""",
        76,
    ),
    # AGAST #3823: a field holding a POINTER or reference to the collection
    # slices through it, as a pointer local does (R9 rule 2).  ritz0 passed
    # the field's address (a `Vec$i64**`) and llvmlite threw; ritz1 refused
    # it.  The field is `make()`'s [0, 10, 20, 30, 40, 50].  [20, 30]:
    # 2 * 100 + 30.
    "ptr_member_range_chain": (
        MEMBER_SLICE_PRELUDE
        + """\
fn main() -> i32
    var v: Vec<i64> = make()
    var h: P = P { p: @v }
    return (h.p[2..4].len() * 100 + h.p[2..4][1]) as i32
""",
        230,
    ),
    # Open-ended colon slice through a `@Vec` field: its length bounds it,
    # read through the reference.  [20, 30, 40, 50]: 4 * 10 + 20.
    "ref_member_colon_open_end": (
        MEMBER_SLICE_PRELUDE
        + """\
fn main() -> i32
    var v: Vec<i64> = make()
    var r: R = R { r: @v }
    var s: Vec<i64> = r.r[2:]
    return (s.len() * 10 + s[0]) as i32
""",
        60,
    ),
    # The full colon slice through a pointer field is a copy: a push leaves
    # the pointee alone.  7 * 10 + 6.
    "ptr_member_colon_full": (
        MEMBER_SLICE_PRELUDE
        + """\
fn main() -> i32
    var v: Vec<i64> = make()
    var h: P = P { p: @v }
    var s: Vec<i64> = h.p[:]
    s.push(99)
    return (s.len() * 10 + h.p.len()) as i32
""",
        76,
    ),
    # Two members deep, then through the pointer: [10, 20, 30], 3 * 10 + 30.
    "nested_ptr_member_range": (
        MEMBER_SLICE_PRELUDE
        + """\
fn main() -> i32
    var v: Vec<i64> = make()
    var q: Q = Q { h: P { p: @v } }
    var s: Vec<i64> = q.h.p[1..=3]
    return (s.len() * 10 + s[2]) as i32
""",
        60,
    ),
}

PROGRAMS = {
    **EMPTY_ARRAY,
    **REF_TYPE_ARG,
    **QUALIFIED_PATTERN,
    **FULL_SLICE,
    **COLON_SLICE,
    **GENERIC_LOCAL,
}


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    src = work / "main.ritz"
    src.write_text(program)
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=work, env=env, timeout=300)
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)]
        comp = subprocess.run(
            cmd, cwd=work, env=env, capture_output=True, text=True, timeout=300
        )
    return comp, ll, work


def _run(compiler: str, tmp_path: Path, name: str) -> int:
    """Compile PROGRAMS[name] with `compiler`, link and run it; return its exit code."""
    program, _ = PROGRAMS[name]
    if "import " in program:
        return _run_pkg(compiler, tmp_path, name, program)
    comp, ll, work = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = work / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=work, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _check(code: int, name: str) -> None:
    want = PROGRAMS[name][1]
    assert code == want, f"{name}: exit {code}, want {want}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    _check(_run("ritz0", tmp_path, name), name)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(EMPTY_ARRAY))
def test_ritz1_empty_array_literal(ritz1_bin, tmp_path, name):
    """Item 2: `[]` died with `cannot parse item`."""
    _check(_run("ritz1", tmp_path, name), name)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(REF_TYPE_ARG))
def test_ritz1_generic_call_ref_type_arg(ritz1_bin, tmp_path, name):
    """Item 3: `id<@E>(e)` called `@id$` with a `void` argument."""
    _check(_run("ritz1", tmp_path, name), name)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(QUALIFIED_PATTERN))
def test_ritz1_qualified_enum_pattern(ritz1_bin, tmp_path, name):
    """Item 4: `Opt.None =>` died with `cannot parse item`."""
    _check(_run("ritz1", tmp_path, name), name)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(FULL_SLICE))
def test_ritz1_full_slice(ritz1_bin, tmp_path, name):
    """Item 5: `a[:]` died with `cannot parse item`."""
    _check(_run("ritz1", tmp_path, name), name)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(COLON_SLICE))
def test_ritz1_colon_slice(ritz1_bin, tmp_path, name):
    """`a[lo:hi]`, `a[:hi]` and `a[lo:]` died with `unexpected ':'`."""
    _check(_run("ritz1", tmp_path, name), name)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MEMBER_SLICE))
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1", "ritz1_selfhosted"])
def test_member_slice(request, tmp_path, compiler, name):
    """AGAST #3803: `h.v[2..4]` was "this can't be sliced" under ritz1."""
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    program, want = MEMBER_SLICE[name]
    code = _run_pkg(compiler, tmp_path, name, program)
    assert code == want, f"{compiler} {name}: exit {code}, want {want}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(GENERIC_LOCAL))
def test_ritz1_generic_bare_t_local(ritz1_bin, tmp_path, name):
    """`let y: T` at T = i32 became `alloca %T$i32`."""
    _check(_run("ritz1", tmp_path, name), name)
