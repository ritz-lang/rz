"""Regression tests for AGAST #1504 — ritz1 must index a global `[N]T` array
as an array, not as a pointer.

Index lowering in ritz1 handled only an array *local* (read in
`emit_expr_index`, store in the STMT_INDEX_ASSIGN arm of `emit_stmt`). A global
of array type fell through to the pointer path: `load i64 @g; inttoptr; gep` —
it read the array's first element and used it as a base address, so the ticket's
repro (`g[1] = 7`) segfaulted. That blocks the ritzunit runner (`g_tests[i]`).

Every runnable program returns 7 when element access has the right address,
width and signedness. A wrong stride, a store that clobbers its neighbour, a
zext/sext mix-up or the old pointer path each give a different code or crash.
ritz0 is run as the oracle.
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
            "could not build ritz1 for the global-array tests:\n"
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


# --- forms #1504 miscompiles -------------------------------------------------

# The ticket's repro, verbatim.
REPRO_I64 = """\
var g: [4]i64

pub fn main() -> i32
    g[1] = 7
    return g[1] as i32
"""

# The ticket's second case: a global `[4]u8` read in a loop. Filled through
# the store path, then summed through the read path; a wrong stride or width
# sums the wrong bytes. 1+2+0+4 = 7.
U8_LOOP_READ = """\
var g: [4]u8

pub fn main() -> i32
    g[0] = 1
    g[1] = 2
    g[3] = 4
    var sum: i64 = 0
    var i: i64 = 0
    while i < 4
        sum = sum + g[i] as i64
        i = i + 1
    return sum as i32
"""

# Loop-indexed stores (high to low), then direct reads. An i64-wide store into
# an i32 array clobbers the next element. g = [1, 2, 3, 4]; 1+2+4+3-3 = 7.
I32_LOOP_STORE = """\
var g: [4]i32

pub fn main() -> i32
    var i: i64 = 3
    while i >= 0
        g[i] = (i + 1) as i32
        i = i - 1
    return (g[0] + g[1] + g[3] + g[2] - 3) as i32
"""

# u8 elements zero-extend: 200 reads back as 200, not -56. Compared in full,
# not folded into the exit code: -249 and 7 are the same exit status.
U8_ZEXT = """\
var g: [2]u8

pub fn main() -> i32
    g[1] = 200
    let v: i64 = g[1] as i64
    if v != 200
        return 1
    return 7
"""

# i8 elements sign-extend: -3 reads back as -3, not 253 (compared in full,
# as 263 and 7 are the same exit status).
I8_SEXT = """\
var g: [2]i8

pub fn main() -> i32
    g[0] = 10
    g[1] = -3
    let v: i64 = g[1] as i64
    if v != -3
        return 1
    return (g[0] as i64 + v) as i32
"""

# i16 elements: a stride-8 or stride-1 GEP reads the wrong halfword.
I16_STRIDE = """\
var g: [4]i16

pub fn main() -> i32
    g[0] = 1000
    g[1] = 2
    g[2] = 5
    g[3] = -1000
    let neg: i64 = g[3] as i64
    if neg != -1000
        return 1
    return (g[0] as i64 + g[1] as i64 + g[2] as i64 + neg) as i32
"""

# Read-modify-write on the same global element.
READ_MODIFY_WRITE = """\
var g: [3]i64

pub fn main() -> i32
    g[2] = 3
    g[2] = g[2] + 4
    return g[2] as i32
"""

# Two global arrays side by side: each index must hit its own array.
TWO_GLOBALS = """\
var a: [2]i64
var b: [2]i64

pub fn main() -> i32
    a[1] = 5
    b[0] = 2
    b[1] = 100
    return (a[1] + b[0]) as i32
"""

# The global array is written from one function and read from another.
ACROSS_FUNCTIONS = """\
var g: [4]i32

fn fill()
    var i: i64 = 0
    while i < 4
        g[i] = i as i32
        i = i + 1

pub fn main() -> i32
    fill()
    return (g[1] + g[2] + g[3] + 1) as i32
"""

# A local array shadowing a global of the same name must still hit the local,
# while main's own `g[0]` store hits the global.
LOCAL_SHADOWS_GLOBAL = """\
var g: [4]i64

pub fn main() -> i32
    g[0] = 100
    return helper()

fn helper() -> i32
    var g: [4]i64
    g[1] = 7
    return g[1] as i32
"""

BROKEN_FORMS = {
    "repro_i64": REPRO_I64,
    "u8_loop_read": U8_LOOP_READ,
    "i32_loop_store": I32_LOOP_STORE,
    "u8_zext": U8_ZEXT,
    "i8_sext": I8_SEXT,
    "i16_stride": I16_STRIDE,
    "read_modify_write": READ_MODIFY_WRITE,
    "two_globals": TWO_GLOBALS,
    "across_functions": ACROSS_FUNCTIONS,
    "local_shadows_global": LOCAL_SHADOWS_GLOBAL,
}

# --- forms that already worked, pinned against regression -------------------

# A global *pointer* still indexes through the pointer (AGAST #1332's path).
GLOBAL_PTR_INDEX = """\
var backing: [4]i64
var p: *i64

pub fn main() -> i32
    p = @backing[0]
    p[2] = 7
    return p[2] as i32
"""

WORKING_FORMS = {
    "global_ptr_index": GLOBAL_PTR_INDEX,
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
def test_ritz1_global_array_index(ritz1_bin, tmp_path, name):
    """AGAST #1504. Before the fix: pointer-path GEP off g[0], segfault (-11)."""
    assert _run("ritz1", tmp_path, name, BROKEN_FORMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(WORKING_FORMS))
def test_ritz1_already_working_forms(ritz1_bin, tmp_path, name):
    """A global pointer still indexes through the pointer (AGAST #1332)."""
    assert _run("ritz1", tmp_path, name, WORKING_FORMS[name]) == EXPECTED


@pytest.mark.integration
def test_ritz1_repro_ir_indexes_the_array_directly(ritz1_bin, tmp_path):
    """The emitted IR GEPs `[4 x i64], ptr @g, i64 0, ...` and never loads @g
    as a pointer base (the old `load i64, ptr @g` + `inttoptr`)."""
    comp, ll = _compile("ritz1", tmp_path, "repro_ir", REPRO_I64)
    assert comp.returncode == 0, comp.stderr[-2000:]
    ir = ll.read_text()
    main_body = ir[ir.index("define i32 @main") :]
    assert "getelementptr [4 x i64], ptr @g, i64 0, i64 " in main_body
    assert "load i64, ptr @g\n" not in main_body
