"""Regression tests for AGAST #1553 and #1555 — ritz1 must read and store a
whole struct element of a global `[N]Struct` array by value.

AGAST #1504 taught ritz1 to GEP a global `[N]T` array directly, but left
struct elements out. A whole-element read (`let q: P = g[i]`) fell through to
the pointer path — `load i64, ptr @g`, a byte GEP, `load i64` — so storing the
result into a `%P` slot was rejected by clang ("'%.N' defined with type 'i64'
but expected '%P'"). A whole-element store (`g[i] = q`, #1555's `g_slot[2] =
*v`) loaded @g as a pointer base and emitted `store i64 %P-value`.

ritzunit's shuffle_tests swaps `g_tests` elements with exactly these shapes
(`let tmp: TestEntry = g_tests[i]`, `g_tests[i] = g_tests[j]`).

Every runnable program returns 7 only when the whole element was copied at
the right address; a wrong stride or a partial copy returns something else.
ritz0 is run as the oracle.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

EXPECTED = 7


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date; make's dependency graph decides the work.

    A stale ritz1 would assert against the old emitter (see AGAST #1322).
    """
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
            "could not build ritz1 for the global struct-array tests:\n"
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
    a: i64
    b: i64

"""

# --- read side (#1553) -------------------------------------------------------

# The #1553 ticket's repro, verbatim.
READ_REPRO = (
    STRUCT_P
    + """\
var g: [4]P

pub fn main() -> i32
    g[1].b = 7
    let q: P = g[1]
    return q.b as i32
"""
)

# Loop-indexed read of every field: a stride of 8 (i64) instead of 16 would
# read g[1] as {g[0].b, g[1].a}. Only element 2 is populated: 3 + 4 = 7.
READ_LOOP = (
    STRUCT_P
    + """\
var g: [4]P

pub fn main() -> i32
    g[2].a = 3
    g[2].b = 4
    var sum: i64 = 0
    var i: i64 = 0
    while i < 4
        let q: P = g[i]
        sum = sum + q.a + q.b * (i - 1)
        i = i + 1
    return sum as i32
"""
)

# The read is a copy: writing the copy must not touch the global.
READ_IS_COPY = (
    STRUCT_P
    + """\
var g: [2]P

pub fn main() -> i32
    g[0].a = 3
    g[0].b = 4
    var q: P = g[0]
    q.a = 100
    return (g[0].a + g[0].b) as i32
"""
)

# Mixed-width fields: the load must use the %M layout (i32, u8, i64 = 16
# bytes with padding), not a single i64.
READ_MIXED = """\
struct M
    x: i32
    y: u8
    z: i64

var g: [3]M

pub fn main() -> i32
    g[2].x = 1
    g[2].y = 2
    g[2].z = 4
    let m: M = g[2]
    return (m.x as i64 + m.y as i64 + m.z) as i32
"""

# --- store side (#1553 + #1555) ----------------------------------------------

# A struct local stored into a global element.
STORE_LOCAL = (
    STRUCT_P
    + """\
var g: [4]P

pub fn main() -> i32
    var q: P
    q.a = 3
    q.b = 4
    g[2] = q
    return (g[2].a + g[2].b + g[1].a + g[3].b) as i32
"""
)

# The #1555 ticket's repro, verbatim: a deref'd reference param.
STORE_DEREF_1555 = """\
struct D
    a: i64
    b: i64
var g_slot: [4]D
fn put(v: @D)
    g_slot[2] = *v
pub fn main() -> i32
    var d: D
    d.a = 3
    d.b = 4
    put(@d)
    return (g_slot[2].a + g_slot[2].b) as i32
"""

# A struct returned by value from a call, stored at a loop index.
STORE_CALL = (
    STRUCT_P
    + """\
var g: [4]P

fn mk(a: i64, b: i64) -> P
    var p: P
    p.a = a
    p.b = b
    return p

pub fn main() -> i32
    var i: i64 = 0
    while i < 4
        g[i] = mk(i, 1)
        i = i + 1
    return (g[3].a + g[2].b + g[1].a + g[0].b + g[0].a + 1) as i32
"""
)

# Element-to-element copy on the same global: `g[i] = g[j]`.
COPY_ELEMENT = (
    STRUCT_P
    + """\
var g: [4]P

pub fn main() -> i32
    g[0].a = 3
    g[0].b = 4
    g[3] = g[0]
    g[0].a = 50
    return (g[3].a + g[3].b) as i32
"""
)

# The #1553 ticket's second test, ritzunit shuffle_tests' shape: swap two
# elements through a temporary. After the swap g[1] = {3, 4}, g[2] = {1, 2}.
SWAP = (
    STRUCT_P
    + """\
var g: [4]P

fn swap(i: i64, j: i64)
    let tmp: P = g[i]
    g[i] = g[j]
    g[j] = tmp

pub fn main() -> i32
    g[1].a = 1
    g[1].b = 2
    g[2].a = 3
    g[2].b = 4
    swap(1, 2)
    if g[2].a != 1 or g[2].b != 2
        return 1
    return (g[1].a + g[1].b) as i32
"""
)

# Mixed-width store: a store of `i64` would drop z entirely.
STORE_MIXED = """\
struct M
    x: i32
    y: u8
    z: i64

var g: [3]M

pub fn main() -> i32
    var m: M
    m.x = 1
    m.y = 2
    m.z = 4
    g[1] = m
    return (g[1].x as i64 + g[1].y as i64 + g[1].z) as i32
"""

BROKEN_FORMS = {
    "read_repro": READ_REPRO,
    "read_loop": READ_LOOP,
    "read_is_copy": READ_IS_COPY,
    "read_mixed": READ_MIXED,
    "store_local": STORE_LOCAL,
    "store_deref_1555": STORE_DEREF_1555,
    "store_call": STORE_CALL,
    "copy_element": COPY_ELEMENT,
    "swap": SWAP,
    "store_mixed": STORE_MIXED,
}

# --- forms that already worked, pinned against regression -------------------

# Field access on a global struct array goes through emit_member_ptr (#190).
FIELD_ACCESS = (
    STRUCT_P
    + """\
var g: [4]P

pub fn main() -> i32
    g[3].a = 3
    g[3].b = 4
    return (g[3].a + g[3].b) as i32
"""
)

# ritzunit json_reporter: a struct-typed field of a global struct element.
MEMBER_STRUCT_STORE = (
    STRUCT_P
    + """\
struct Rec
    d: P
    n: i64

var g_recs: [4]Rec

fn put(v: @P, i: i64)
    g_recs[i].d = *v

pub fn main() -> i32
    var d: P
    d.a = 3
    d.b = 4
    put(@d, 2)
    return (g_recs[2].d.a + g_recs[2].d.b) as i32
"""
)

# Scalar global arrays keep #1504's width-specific path.
SCALAR_GLOBAL = """\
var g: [4]i32

pub fn main() -> i32
    g[1] = 3
    g[2] = 4
    return g[1] + g[2]
"""

WORKING_FORMS = {
    "field_access": FIELD_ACCESS,
    "member_struct_store": MEMBER_STRUCT_STORE,
    "scalar_global": SCALAR_GLOBAL,
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
    comp = subprocess.run(
        cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
    )
    return comp, ll


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
def test_ritz1_global_struct_array(ritz1_bin, tmp_path, name):
    """AGAST #1553/#1555. Before the fix: `i64`/`%P` type mismatch, no link."""
    assert _run("ritz1", tmp_path, name, BROKEN_FORMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(WORKING_FORMS))
def test_ritz1_already_working_forms(ritz1_bin, tmp_path, name):
    """Field access and scalar global arrays keep their existing paths."""
    assert _run("ritz1", tmp_path, name, WORKING_FORMS[name]) == EXPECTED


@pytest.mark.integration
def test_ritz1_struct_elem_ir_is_typed(ritz1_bin, tmp_path):
    """The whole-element read loads `%P` and the store stores `%P`, both at a
    `[4 x %P]` GEP of @g; @g is never loaded as a pointer base."""
    comp, ll = _compile("ritz1", tmp_path, "swap_ir", SWAP)
    assert comp.returncode == 0, comp.stderr[-2000:]
    ir = ll.read_text()
    swap_body = ir[ir.index("define weak_odr void @swap") :]
    swap_body = swap_body[: swap_body.index("\n}\n")]
    assert "getelementptr [4 x %P], ptr @g, i64 0, i64 " in swap_body
    assert "= load %P, ptr " in swap_body
    assert "store %P " in swap_body
    assert "load i64, ptr @g\n" not in swap_body
    # Only the i/j param spills store i64; no struct value is stored as one.
    assert not re.search(r"store i64 %\.\d+", swap_body)
