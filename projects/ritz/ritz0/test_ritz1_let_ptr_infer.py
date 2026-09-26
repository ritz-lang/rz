"""Regression tests for AGAST #1453 — ritz1 must infer the pointee of an
unannotated pointer/reference local so member access through it works.

#175 taught ritz1's var-decl path to infer `let x = @expr` and
`let x = call()` returning `*Foo`. Two shapes were still missing, and each
left the local typed as a bare i64. Member access through it then failed with
"unhandled EXPR_MEMBER", and a store through it was silently dropped (#1439):

* `let p = raw as *P` (ritzlib/async/task.ritz's task_get_ring)
* `let m = get(l)` where `get` returns a reference `@L` / `@&L` (iris)

Every runnable program returns 42 only if the right field was read (or
written). ritz0 is the oracle.
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
            "could not build ritz1 for the let-pointer inference tests:\n"
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
    x: i64
    y: i64

"""

STRUCT_L = """\
struct L
    a: i32
    x: i32

"""

# --- `let p = <expr> as *T` -------------------------------------------------

# The ticket's repro, verbatim.
CAST_READ = (
    STRUCT_P
    + """\
fn get(raw: *u8) -> i64
    let p = raw as *P
    return p.y

pub fn main() -> i32
    var v: P = P { x: 3, y: 42 }
    return get(@v as *u8) as i32
"""
)

# task.ritz's shape: the cast source is a struct field, not a param.
CAST_FIELD_SOURCE = (
    STRUCT_P
    + """\
struct Task
    id: i64
    pool_ptr: *u8

fn ring(t: *Task) -> i64
    let pool = t.pool_ptr as *P
    return pool.y

pub fn main() -> i32
    var v: P = P { x: 3, y: 42 }
    var t: Task = Task { id: 1, pool_ptr: @v as *u8 }
    return ring(@t) as i32
"""
)

# A store through the inferred local must land, not be dropped.
CAST_STORE = (
    STRUCT_P
    + """\
fn set(raw: *u8)
    let p = raw as *P
    p.y = 42

pub fn main() -> i32
    var v: P = P { x: 3, y: 0 }
    set(@v as *u8)
    return v.y as i32
"""
)

# `var` goes through the same path.
CAST_VAR = (
    STRUCT_P
    + """\
fn get(raw: *u8) -> i64
    var p = raw as *P
    return p.y

pub fn main() -> i32
    var v: P = P { x: 3, y: 42 }
    return get(@v as *u8) as i32
"""
)

# A primitive pointee sets the load width and stride: this was stepped and
# loaded as i64 (returned 0).  The earlier `*P` param leaves the parser's
# last type name stale; it must not turn `*i32` into `*P`.
CAST_PRIMITIVE_PTR = (
    STRUCT_P
    + """\
fn third(unused: *P, raw: *u8) -> i32
    let q = raw as *i32
    return *(q + 2)

pub fn main() -> i32
    var buf: [4]i32
    buf[2] = 42
    var v: P = P { x: 3, y: 4 }
    return third(@v, @buf[0] as *u8)
"""
)

# A cast chain: the local takes the OUTERMOST target.
CAST_CHAIN = (
    STRUCT_P
    + """\
fn get(raw: *u8) -> i64
    let p = raw as u64 as *P
    return p.y

pub fn main() -> i32
    var v: P = P { x: 3, y: 42 }
    return get(@v as *u8) as i32
"""
)

CAST_CHAIN_PTRS = (
    STRUCT_P
    + """\
fn get(raw: *i64) -> i64
    let p = raw as *u8 as *P
    return p.y

pub fn main() -> i32
    var v: P = P { x: 3, y: 42 }
    return get(@v as *i64) as i32
"""
)

# `-> @i64` after a `@L` param: the stale struct name must not narrow the
# local to `*L` (it would then load `%L` for `*r`).
CALL_REF_PRIMITIVE = (
    STRUCT_L
    + """\
fn pick(l: @L, n: @i64) -> @i64
    return n

pub fn main() -> i32
    var l: L = L { a: 1, x: 2 }
    var n: i64 = 42
    let r = pick(@l, @n)
    return *r as i32
"""
)

# --- `let m = call()` returning `@T` / `@&T` --------------------------------

# The ticket's additional shape (iris).
CALL_MUT_REF = (
    STRUCT_L
    + """\
fn get(l: @&L) -> @&L
    return l

fn f(l: @&L) -> i32
    let m = get(l)
    return m.x

pub fn main() -> i32
    var l: L = L { a: 1, x: 42 }
    return f(@&l)
"""
)

CALL_REF = (
    STRUCT_L
    + """\
fn get(l: @L) -> @L
    return l

fn f(l: @L) -> i32
    let m = get(l)
    return m.x

pub fn main() -> i32
    var l: L = L { a: 1, x: 42 }
    return f(@l)
"""
)

CALL_MUT_REF_STORE = (
    STRUCT_L
    + """\
fn get(l: @&L) -> @&L
    return l

fn f(l: @&L)
    let m = get(l)
    m.x = 42

pub fn main() -> i32
    var l: L = L { a: 1, x: 0 }
    f(@&l)
    return l.x
"""
)

BROKEN_FORMS = {
    "cast_read": CAST_READ,
    "cast_field_source": CAST_FIELD_SOURCE,
    "cast_store": CAST_STORE,
    "cast_var": CAST_VAR,
    "cast_primitive_ptr": CAST_PRIMITIVE_PTR,
    "cast_chain": CAST_CHAIN,
    "cast_chain_ptrs": CAST_CHAIN_PTRS,
    "call_mut_ref": CALL_MUT_REF,
    "call_ref": CALL_REF,
    "call_mut_ref_store": CALL_MUT_REF_STORE,
}

# --- forms that already worked, pinned against regression -------------------

ANNOTATED_CAST = (
    STRUCT_P
    + """\
fn get(raw: *u8) -> i64
    let p: *P = raw as *P
    return p.y

pub fn main() -> i32
    var v: P = P { x: 3, y: 42 }
    return get(@v as *u8) as i32
"""
)

# #175's shapes.
ADDR_OF = (
    STRUCT_P
    + """\
pub fn main() -> i32
    var v: P = P { x: 3, y: 42 }
    let p = @v
    return p.y as i32
"""
)

CALL_PTR = (
    STRUCT_P
    + """\
fn get(p: *P) -> *P
    return p

pub fn main() -> i32
    var v: P = P { x: 3, y: 42 }
    let p = get(@v)
    return p.y as i32
"""
)

# A plain value cast must stay a value.
CAST_VALUE = """\
pub fn main() -> i32
    let big: i64 = 42
    let n = big as i32
    return n
"""

WORKING_FORMS = {
    "annotated_cast": ANNOTATED_CAST,
    "addr_of": ADDR_OF,
    "call_ptr": CALL_PTR,
    "cast_value": CAST_VALUE,
    "call_ref_primitive": CALL_REF_PRIMITIVE,
}


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


ALL_RUNNABLE = {**BROKEN_FORMS, **WORKING_FORMS}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ALL_RUNNABLE))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, ALL_RUNNABLE[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(BROKEN_FORMS))
def test_ritz1_infers_let_pointee(ritz1_bin, tmp_path, name):
    """AGAST #1453. Before the fix: "unhandled EXPR_MEMBER" or a dropped store."""
    assert _run("ritz1", tmp_path, name, BROKEN_FORMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(WORKING_FORMS))
def test_ritz1_already_working_forms(ritz1_bin, tmp_path, name):
    """Annotated casts, #175's shapes and non-struct casts are unchanged."""
    assert _run("ritz1", tmp_path, name, WORKING_FORMS[name]) == EXPECTED


@pytest.mark.integration
def test_ritz1_compiles_async_task_standalone(ritz1_bin, tmp_path):
    """The ticket's original victim: ritzlib/async/task.ritz on its own."""
    ll = tmp_path / "task.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        [
            str(RITZ1_BIN),
            str(RITZ_ROOT / "ritzlib" / "async" / "task.ritz"),
            "-o",
            str(ll),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and ll.exists(), out[-3000:]
    assert "unhandled EXPR_MEMBER" not in out
