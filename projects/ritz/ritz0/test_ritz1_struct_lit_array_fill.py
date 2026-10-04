"""Regression tests for AGAST #1605 — an array field initialised with `[v; N]`
inside a struct literal.

ritz1 lowered the fill literal through emit_expr's generic EXPR_ARRAY_FILL
fallback: a shadow `alloca [N x i64]`, then `ptrtoint` of that alloca stored
as an i64 over the field — overwriting a[0..1] with a stack address and never
writing the fill value into the field at all. ritz0 got it right.

Two emitter paths build struct literals and both are covered:

* `let s: S = S { ... }` — the struct-literal loop in emit_var_decl;
* `return S { ... }` / `s = S { ... }` — emit_struct_lit_to_alloca.

Each program returns 42 when correct and a distinct small code naming the
check that failed otherwise. ritz0 is the oracle.

Zero fills lower to `llvm.memset` in ritz1 (the same lowering `let b: [N]T =
[0; N]` uses), which clang turns into a call to `memset`. Real builds link
ritzlib.str's memset (the regression matrix links it into every cell); these
single-file programs define the same function themselves. ritz1's libcall
dependency here, which ritz0 does not have, is tracked separately.
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
            "could not build ritz1 for the struct-literal fill tests:\n"
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


# ritzlib.str's memset, for the zero-fill programs (see module docstring).
MEMSET = """\
pub fn memset(dest: *u8, c: u8, n: i64) -> *u8
    for i in 0..n
        *(dest + i) = c
    return dest

"""

PROGRAMS = {
    # The ticket's repro (test_level9::test_indent_stack_struct shape), with
    # every slot checked rather than just a[0].
    "repro_i64_zero": MEMSET
    + """\
struct S
    a: [4]i64

pub fn main() -> i32
    let s: S = S { a: [0; 4] }
    var i: i32 = 0
    while i < 4
        if s.a[i] != 0
            return i + 1
        i = i + 1
    return 42
""",
    # Non-zero fill, with a neighbour field initialised BEFORE the array in
    # the literal — the old 8-byte pointer store also never wrote 7 anywhere.
    "i64_nonzero_neighbour": """\
struct S
    b: i64
    a: [4]i64
    c: i64

pub fn main() -> i32
    let s: S = S { c: 9, a: [7; 4], b: 5 }
    if s.b != 5
        return 1
    if s.c != 9
        return 2
    var sum: i64 = 0
    var i: i32 = 0
    while i < 4
        if s.a[i] != 7
            return 10 + i
        sum = sum + s.a[i]
        i = i + 1
    return (sum + 14) as i32
""",
    # u8 elements: an i64 store into a [5]u8 would also clobber `post`.
    "u8_elements": """\
struct S
    pre: u8
    a: [5]u8
    post: u8

pub fn main() -> i32
    let s: S = S { pre: 1, a: [200; 5], post: 2 }
    if s.pre != 1
        return 1
    if s.post != 2
        return 2
    var i: i32 = 0
    while i < 5
        if s.a[i] != 200
            return 10 + i
        i = i + 1
    return 42
""",
    # i32 elements, non-zero and zero fill side by side.
    "i32_elements": MEMSET
    + """\
struct S
    a: [3]i32
    z: [3]i32
    tail: i32

pub fn main() -> i32
    let s: S = S { a: [-3; 3], z: [0; 3], tail: 51 }
    var i: i32 = 0
    while i < 3
        if s.a[i] != -3
            return 10 + i
        if s.z[i] != 0
            return 20 + i
        i = i + 1
    return s.tail + s.a[0] * 3
""",
    # N > 16: the loop lowering rather than the unrolled one.
    "i32_large_n": """\
struct S
    a: [40]i32
    tail: i32

pub fn main() -> i32
    let s: S = S { a: [1; 40], tail: 2 }
    var sum: i32 = 0
    var i: i32 = 0
    while i < 40
        sum = sum + s.a[i]
        i = i + 1
    return sum + s.tail
""",
    # The fill value is evaluated exactly once, not once per slot.
    "fill_value_evaluated_once": """\
var calls: i32 = 0

fn seven() -> i64
    calls = calls + 1
    return 7

struct S
    a: [4]i64

pub fn main() -> i32
    let s: S = S { a: [seven(); 4] }
    if calls != 1
        return calls
    if s.a[0] != 7 or s.a[3] != 7
        return 20
    return 42
""",
    # emit_struct_lit_to_alloca: struct literal in return position.
    "return_position": """\
struct S
    a: [4]i32
    b: i32

fn make() -> S
    return S { a: [10; 4], b: 2 }

pub fn main() -> i32
    let s: S = make()
    if s.b != 2
        return 1
    return s.a[0] + s.a[1] + s.a[2] + s.a[3] + s.b
""",
    # emit_struct_lit_to_alloca: reassignment over dirty slots — a zero fill
    # that writes nothing would leave the 9s in place.
    "assign_over_dirty": MEMSET
    + """\
struct S
    a: [4]u8
    b: i32

pub fn main() -> i32
    var s: S = S { a: [9; 4], b: 1 }
    var j: i32 = 0
    while j < 4
        s.a[j] = 9
        j = j + 1
    s = S { a: [0; 4], b: 42 }
    var i: i32 = 0
    while i < 4
        if s.a[i] != 0
            return 10 + i
        i = i + 1
    return s.b
""",
}


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
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
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, PROGRAMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_struct_lit_array_fill(ritz1_bin, tmp_path, name):
    """ritz1 stored the shadow array's address over the field (#1605)."""
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
