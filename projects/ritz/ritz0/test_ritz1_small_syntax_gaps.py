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
    # #1530's repro shape: qualified unit variant arms and a wildcard.  (A
    # user enum WITH payload variants is miscompiled by ritz1 whether its
    # arms are qualified or not -- see #1797 -- so this enum is
    # unit-only.)
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
    # angelo's other site binds a payload: `ParsedGlyph.Simple(outline) =>`.
    # Option is the payload enum ritz1 lays out today.
    "qualified_payload_pattern": (
        """\
import ritzlib.option

fn f(o: Option<i32>) -> i32
    match o
        Option.Some(v) => v
        Option.None => 100

fn main() -> i32
    return f(Some(41)) + f(None) - 99
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
    var s: Vec<i32> = a[:]
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
    return dup_sum(@v)
""",
        42,
    ),
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

PROGRAMS = {
    **EMPTY_ARRAY,
    **REF_TYPE_ARG,
    **QUALIFIED_PATTERN,
    **FULL_SLICE,
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
    link = subprocess.run(link_cmd, cwd=work, capture_output=True, text=True)
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
@pytest.mark.parametrize("name", sorted(GENERIC_LOCAL))
def test_ritz1_generic_bare_t_local(ritz1_bin, tmp_path, name):
    """`let y: T` at T = i32 became `alloca %T$i32`."""
    _check(_run("ritz1", tmp_path, name), name)
