"""Regression tests for AGAST #1596: ritz1 indexing through a pointer-typed
struct field (`s.data[i]` where `data: *T`).

Three defects, one per lowering site:

* STMT_LOCAL_FIELD_INDEX_ASSIGN (`b.data[2] = 42`, `b` a local or param)
  treated every field as an inline array: `getelementptr [0 x i32], ptr
  <field slot>, 0, i` wrote INTO the struct (clobbering the pointer and the
  fields after it) instead of loading the pointer and indexing through it.
* emit_assign's EXPR_INDEX(EXPR_MEMBER) arm (`a.b.data[2] = 42`, global
  `g.data[2] = 42`) evaluated the target as a value and stored through it;
  #1439 made it fail closed. It now stores at the pointee's width.
* emit_expr_index read `x.data[i]` with an i8 stride and a one-byte load
  whatever the pointee was.

ritz0 is the oracle: every RUNNABLE program returns 42 under it. The programs
also check the neighbouring elements and fields, so an over-wide store or a
store into the struct shows up as a wrong exit code, not just a wrong value.
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

EXPECTED = 42


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date; a stale ritz1 asserts the old emitter (#1322)."""
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
            "could not build ritz1 for the pointer-field index tests:\n"
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


# --- stores through a pointer field ------------------------------------------

STORES = {
    # The ticket's repro, plus a field after `data` and a neighbour element
    # that a store into the struct / an over-wide store would clobber.
    "local_i32": """\
struct B
    data: *i32
    tag: i64

pub fn main() -> i32
    var buf: [4]i32
    buf[0] = 0
    buf[1] = 0
    buf[2] = 0
    buf[3] = 5
    var b: B
    b.data = @buf[0]
    b.tag = 7
    b.data[2] = 42
    if b.tag != 7
        return 1
    if buf[3] != 5 or buf[1] != 0
        return 2
    return buf[2]
""",
    # Every narrow width, through a local struct.
    "local_widths": """\
struct W
    b: *u8
    h: *u16
    q: *i64

pub fn main() -> i32
    var bb: [4]u8
    var hh: [4]u16
    var qq: [4]i64
    bb[2] = 9
    hh[2] = 9
    qq[2] = 9
    var w: W
    w.b = @bb[0]
    w.h = @hh[0]
    w.q = @qq[0]
    w.b[1] = 200
    w.h[1] = 60000
    w.q[1] = 40
    if bb[2] != 9 or hh[2] != 9 or qq[2] != 9
        return 1
    if bb[1] != 200 or hh[1] != 60000
        return 2
    return (qq[1] + 2) as i32
""",
    # `q.data[i] = v` with `q: *B` a parameter (same statement kind).
    "param_i32": """\
struct B
    data: *i32
    tag: i64

fn set(q: *B)
    q.data[2] = 42

pub fn main() -> i32
    var buf: [4]i32
    buf[3] = 5
    var b: B
    b.data = @buf[0]
    b.tag = 7
    set(@b)
    if b.tag != 7 or buf[3] != 5
        return 1
    return buf[2]
""",
    # Compound assignment desugars to the same statement.
    "local_compound": """\
struct B
    data: *i32

pub fn main() -> i32
    var buf: [4]i32
    buf[2] = 2
    buf[3] = 5
    var b: B
    b.data = @buf[0]
    b.data[2] += 40
    if buf[3] != 5
        return 1
    return buf[2]
""",
    # Nested chain: emit_assign's EXPR_INDEX(EXPR_MEMBER) arm (refused by #1439).
    "nested_i32": """\
struct B
    data: *i32

struct A
    pad: i64
    b: B

pub fn main() -> i32
    var buf: [4]i32
    buf[3] = 5
    var a: A
    a.pad = 7
    a.b.data = @buf[0]
    a.b.data[2] = 42
    if a.pad != 7 or buf[3] != 5
        return 1
    return buf[2]
""",
    # Global struct base: the #1439 fallback re-lowers into emit_assign.
    "global_i32": """\
struct B
    data: *i32
    tag: i64

var g: B

pub fn main() -> i32
    var buf: [4]i32
    buf[3] = 5
    g.data = @buf[0]
    g.tag = 7
    g.data[2] = 42
    if g.tag != 7 or buf[3] != 5
        return 1
    return buf[2]
""",
    # Pointer-to-struct field: element stride is the struct size.
    "local_struct_pointee": """\
struct P
    x: i32
    y: i32

struct H
    ps: *P

pub fn main() -> i32
    var arr: [3]P
    arr[2].x = 9
    arr[2].y = 9
    var h: H
    h.ps = @arr[0]
    h.ps[1] = P { x: 40, y: 2 }
    if arr[2].x != 9 or arr[2].y != 9
        return 1
    return arr[1].x + arr[1].y
""",
    # `**T` field: element is a pointer.
    "local_ptr_ptr": """\
struct T
    items: **u8

pub fn main() -> i32
    var a: u8 = 42
    var arr: [3]*u8
    arr[2] = null
    var t: T
    t.items = @arr[0]
    t.items[1] = @a
    if arr[2] != null
        return 1
    return *arr[1] as i32
""",
}

# --- reads through a pointer field -------------------------------------------

READS = {
    # i8 stride would read byte 2 of buf[0] (0).
    "local_i32": """\
struct B
    data: *i32

pub fn main() -> i32
    var buf: [4]i32
    buf[0] = 10
    buf[1] = 20
    buf[2] = 42
    buf[3] = 30
    var b: B
    b.data = @buf[0]
    return b.data[2]
""",
    "nested_i32": """\
struct B
    data: *i32

struct A
    pad: i64
    b: B

pub fn main() -> i32
    var buf: [4]i32
    buf[0] = 10
    buf[1] = 20
    buf[2] = 42
    buf[3] = 30
    var a: A
    a.b.data = @buf[0]
    return a.b.data[2]
""",
    "param_i32": """\
struct B
    data: *i32

fn get(q: *B) -> i32
    return q.data[2]

pub fn main() -> i32
    var buf: [4]i32
    buf[0] = 10
    buf[1] = 20
    buf[2] = 42
    buf[3] = 30
    var b: B
    b.data = @buf[0]
    return get(@b)
""",
    # Width and signedness of each narrow pointee.
    "local_widths": """\
struct W
    b: *i8
    h: *u16
    q: *i64

pub fn main() -> i32
    var bb: [4]i8
    var hh: [4]u16
    var qq: [4]i64
    bb[0] = 1
    bb[1] = -2
    hh[0] = 1
    hh[1] = 60000
    qq[0] = 1
    qq[1] = 5000000000
    var w: W
    w.b = @bb[0]
    w.h = @hh[0]
    w.q = @qq[0]
    if w.h[1] != 60000
        return 1
    if w.q[1] != 5000000000
        return 2
    if w.b[1] != -2
        return 3
    return 42
""",
    "local_ptr_ptr": """\
struct T
    items: **u8

pub fn main() -> i32
    var a: u8 = 1
    var c: u8 = 42
    var arr: [2]*u8
    arr[0] = @a
    arr[1] = @c
    var t: T
    t.items = @arr[0]
    let p: *u8 = t.items[1]
    return *p as i32
""",
}

RUNNABLE = {f"store_{k}": v for k, v in STORES.items()}
RUNNABLE.update({f"read_{k}": v for k, v in READS.items()})


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
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
def test_ritz1_ptr_field_index(ritz1_bin, tmp_path, name):
    """ritz1 must index THROUGH the pointer, at the pointee's width."""
    assert _run("ritz1", tmp_path, name, RUNNABLE[name]) == EXPECTED


@pytest.mark.integration
def test_ritz1_local_ptr_field_store_loads_the_pointer(ritz1_bin, tmp_path):
    """The ticket's IR shape: no `[0 x i32]` GEP over the struct's field slot."""
    comp, ll = _compile("ritz1", tmp_path, "ir_shape", STORES["local_i32"])
    assert comp.returncode == 0, comp.stderr[-2000:]
    main = ll.read_text()
    main = main[main.index("define i32 @main") :]
    assert "getelementptr [0 x i32]" not in main, main
    assert "getelementptr i32, ptr " in main, main
    assert "store i32 " in main, main


# A pointee ritz1 cannot index at the right width must refuse, not miscompile.
UNSUPPORTED_POINTEE = """\
struct F
    data: *f64

pub fn main() -> i32
    var buf: [4]f64
    var f: F
    f.data = @buf[0]
    f.data[2] = 1.5
    return 0
"""


@pytest.mark.integration
def test_ritz1_unsupported_pointee_store_fails_closed(ritz1_bin, tmp_path):
    comp, ll = _compile("ritz1", tmp_path, "unsupported", UNSUPPORTED_POINTEE)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"ritz1 accepted a *f64 field store:\n{out[-2000:]}"
    assert "unhandled indexed EXPR_MEMBER in assignment" in out, out[-2000:]
    assert not ll.exists(), "ritz1 must refuse to write output on an emit error"
