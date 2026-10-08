"""Regression tests for AGAST #1439 — ritz1 must never silently drop a store
to a struct field.

STMT_LOCAL_FIELD_ASSIGN (`name.field = v`) and STMT_LOCAL_FIELD_INDEX_ASSIGN
(`name.field[i] = v`) emitted NOTHING when `name` was not a local or param, or
when the field did not resolve: no GEP, no store, no diagnostic, exit 0. A
read of the same member already failed closed ("unhandled EXPR_MEMBER").

Two consequences, both covered here:

* stores to a field of a GLOBAL struct (`ops.n = 5`) were dropped even though
  the field is valid — goliath's vtable was never filled. They now get a real
  GEP + store, and ritz0 is the oracle;
* any store whose target still does not resolve now fails with a diagnostic
  instead of compiling to nothing.

`x.f[i] = v` where `x.f` is not an inline array used to fall through to
emit_assign's generic deref store, which evaluates `x.f[i]` as a value and
stores THROUGH it (segfault). Pointer fields are lowered since #1596; any
other shape still fails closed.
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
            "could not build ritz1 for the member-store tests:\n"
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


STRUCT_P = """\
struct P
    a: i32

"""

# --- unresolved store targets: must be a compile error ----------------------

# Each maps to (program, diagnostic substring).
MEMBER = "unhandled EXPR_MEMBER in assignment"
INDEXED = "unhandled indexed EXPR_MEMBER in assignment"

UNRESOLVED = {
    # The ticket's local-var repro.
    "local_unknown_field": (
        STRUCT_P
        + """\
pub fn main() -> i32
    var p: P
    p.nope = 3
    return 0
""",
        MEMBER,
    ),
    # The ticket's pointer-param repro.
    "param_unknown_field": (
        STRUCT_P
        + """\
fn set(q: *P)
    q.nope = 3

pub fn main() -> i32
    return 0
""",
        MEMBER,
    ),
    # `s.f += v` desugars to the same statement kind.
    "compound_unknown_field": (
        STRUCT_P
        + """\
pub fn main() -> i32
    var p: P
    p.nope += 3
    return 0
""",
        MEMBER,
    ),
    # Base is neither a local, a param nor a global.
    "unknown_base": (
        STRUCT_P
        + """\
pub fn main() -> i32
    nobody.a = 3
    return 0
""",
        MEMBER,
    ),
    "global_unknown_field": (
        STRUCT_P
        + """\
var g: P

pub fn main() -> i32
    g.nope = 3
    return 0
""",
        MEMBER,
    ),
    "local_unknown_field_index": (
        STRUCT_P
        + """\
pub fn main() -> i32
    var p: P
    p.nope[0] = 3
    return 0
""",
        INDEXED,
    ),
    # A pointer field whose pointee ritz1 cannot address at a known width.
    # (Integer, pointer and struct pointees are lowered since #1596 — see
    # test_ritz1_ptr_field_index.py.)
    "nested_bool_ptr_field_index": (
        """\
struct B
    data: *bool

struct A
    b: B

pub fn main() -> i32
    var buf: [4]bool
    var a: A
    a.b.data = @buf[0]
    a.b.data[2] = true
    return 0
""",
        INDEXED,
    ),
    # Shapes that already failed closed — pinned so they stay that way.
    "nested_unknown_field": (
        """\
struct In
    v: i32

struct Out
    i: In

pub fn main() -> i32
    var o: Out
    o.i.nope = 3
    return 0
""",
        MEMBER,
    ),
    "explicit_deref_unknown_field": (
        STRUCT_P
        + """\
fn set(q: *P)
    (*q).nope = 3

pub fn main() -> i32
    return 0
""",
        MEMBER,
    ),
    "array_elem_unknown_field": (
        STRUCT_P
        + """\
pub fn main() -> i32
    var arr: [2]P
    arr[1].nope = 3
    return 0
""",
        MEMBER,
    ),
}

# --- valid stores: must land (ritz0 is the oracle) --------------------------

RUNNABLE = {
    # The #1450 survey's trigger (a), made to return 42.
    "global_field": """\
struct Ops
    n: i32

var ops: Ops

fn init() -> i32
    ops.n = 42
    return ops.n

pub fn main() -> i32
    return init()
""",
    "global_array_field": """\
struct Ops
    n: [4]i32

var ops: Ops

pub fn main() -> i32
    ops.n[2] = 42
    return ops.n[2]
""",
    # Every width: an over-wide store into `n` would clobber `c`.
    "global_field_widths": """\
struct Ops
    a: i64
    n: i32
    c: u8
    h: u16
    p: *i64

var ops: Ops

pub fn main() -> i32
    var x: i64 = 2
    ops.a = 7
    ops.c = 255
    ops.h = 9
    ops.n = 40
    ops.p = @x
    ops.n += *ops.p
    if ops.c == 255 and ops.a == 7 and ops.h == 9
        return ops.n
    return 1
""",
    # The #1450 survey's trigger (b): fixed by #1453, pinned here.
    "unannotated_ref_local": """\
struct L
    a: i32
    x: i32

fn get(l: @&L) -> @&L
    return l

fn f(l: @&L)
    let m = get(l)
    m.x = 42

pub fn main() -> i32
    var l: L = L { a: 1, x: 0 }
    f(@&l)
    return l.x
""",
    # Positive controls: the fast local / param paths are unchanged.
    "local_known_field": """\
struct P
    a: i32
    b: i32

pub fn main() -> i32
    var p: P
    p.a = 1
    p.b = 42
    return p.b
""",
    "param_known_field": """\
struct P
    a: i32
    b: i32

fn set(q: *P)
    q.b = 42

pub fn main() -> i32
    var p: P = P { a: 1, b: 0 }
    set(@p)
    return p.b
""",
}

# A global bool field store must be 1 byte wide. Checked in the IR because
# reading a global bool field back is broken separately (#1597).
GLOBAL_BOOL = """\
struct Flags
    on: bool
    n: i32

var flags: Flags

pub fn main() -> i32
    flags.on = true
    return 0
"""


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
@pytest.mark.parametrize("name", sorted(UNRESOLVED))
def test_ritz1_unresolved_member_store_fails_closed(ritz1_bin, tmp_path, name):
    """Before #1439 most of these compiled to nothing and exited 0."""
    program, diagnostic = UNRESOLVED[name]
    comp, ll = _compile("ritz1", tmp_path, name, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, (
        f"ritz1 accepted an unresolvable store ({name}); the store was dropped:\n"
        f"{out[-2000:]}"
    )
    assert diagnostic in out, f"missing diagnostic {diagnostic!r}:\n{out[-2000:]}"
    assert not ll.exists(), "ritz1 must refuse to write output on an emit error"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RUNNABLE))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, RUNNABLE[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RUNNABLE))
def test_ritz1_member_store_lands(ritz1_bin, tmp_path, name):
    """Global-struct field stores used to be dropped silently (exit 0)."""
    assert _run("ritz1", tmp_path, name, RUNNABLE[name]) == EXPECTED


@pytest.mark.integration
def test_ritz1_global_bool_field_store_is_one_byte(ritz1_bin, tmp_path):
    comp, ll = _compile("ritz1", tmp_path, "global_bool", GLOBAL_BOOL)
    assert comp.returncode == 0, comp.stderr[-2000:]
    ir = ll.read_text()
    main = ir[ir.index("define i32 @main") :]
    assert "getelementptr %Flags, ptr @flags, i32 0, i32 0" in main
    assert "store i1 " in main, f"global bool field not stored as i1:\n{main}"
    assert "store i64 " not in main, f"8-byte store into a bool field:\n{main}"
