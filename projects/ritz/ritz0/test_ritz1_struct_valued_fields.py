"""Regression tests for AGAST #1655: struct-valued fields in ritz1 struct literals.

    DirEntry { ino: d.d_ino, kind: d.d_type, name: strview_from_cstr(p) }

When #1655 was filed, ritz1 emitted the call and the field GEP for `name` but
never stored the result, so the field was left as stack garbage. The program
compiled, linked, and gave wrong answers at runtime (21_ls printed blank names).
#1497 then routed every struct-literal context through one field-store dispatch
with a TYPE_STRUCT arm, which fixed call results. The cases below keep that fix
in place for every context the dispatch serves: tail, `return`, `let`, typed
`var`, reassignment, and a struct field in the middle of narrower ones.

The other aggregate initialiser the ticket names is a NESTED literal,
`E { name: V { .. } }`. ritz1 rejected it outright ("struct literal not in var
initializer context"). These cases check that it is now written in place into
the field.

Each program returns 42 when correct and a distinct small code naming the
failed check otherwise. ritz0 is the oracle. Every case runs the program,
because the original bug only showed up at runtime.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# Build product, not a tracked file; see test_ritz1_ptr_arith_chain.py.
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
            "could not build ritz1 for the struct-valued field tests:\n"
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


# `name` is a two-word aggregate (the StrView shape) between a u8 and an i32,
# so a missing store reads as garbage and a misplaced one clobbers a neighbour.
PRELUDE = """\
struct V
    ptr: *u8
    len: i64

struct E
    ino: i64
    kind: u8
    name: V
    tail: i32

struct O
    a: u8
    e: E
    b: i16

fn mkv(n: i64) -> V
    V { ptr: null, len: n }

fn chk(e: E, n: i64) -> i32
    if e.name.len != n
        return 1
    if e.name.ptr != null
        return 2
    if e.ino != 1 or e.kind != 2 or e.tail != 3
        return 3
    0

"""

PROGRAMS = {
    # --- call-result field values (the shape in the ticket) ---
    "call_tail": """\
fn mk(n: i64) -> E
    E { ino: 1, kind: 2, name: mkv(n), tail: 3 }

pub fn main() -> i32
    if chk(mk(5), 5) != 0
        return 1
    42
""",
    "call_return": """\
fn mk(n: i64) -> E
    return E { name: mkv(n), ino: 1, kind: 2, tail: 3 }

pub fn main() -> i32
    if chk(mk(6), 6) != 0
        return 1
    42
""",
    "call_let": """\
pub fn main() -> i32
    let e = E { ino: 1, kind: 2, name: mkv(7), tail: 3 }
    if chk(e, 7) != 0
        return 1
    42
""",
    "call_var_reassign": """\
pub fn main() -> i32
    var e: E = E { ino: 1, kind: 2, name: mkv(8), tail: 3 }
    if e.name.len != 8
        return 1
    e = E { ino: 1, kind: 2, name: mkv(9), tail: 3 }
    if chk(e, 9) != 0
        return 2
    42
""",
    "param_value": """\
fn wrap(v: V) -> E
    E { ino: 1, kind: 2, name: v, tail: 3 }

pub fn main() -> i32
    if chk(wrap(mkv(10)), 10) != 0
        return 1
    42
""",
    # --- nested struct literals as field values ---
    "nested_tail": """\
fn mk(n: i64) -> E
    E { ino: 1, kind: 2, name: V { ptr: null, len: n }, tail: 3 }

pub fn main() -> i32
    if chk(mk(11), 11) != 0
        return 1
    42
""",
    "nested_return": """\
fn mk(n: i64) -> E
    return E { ino: 1, name: V { len: n, ptr: null }, kind: 2, tail: 3 }

pub fn main() -> i32
    if chk(mk(12), 12) != 0
        return 1
    42
""",
    "nested_let": """\
pub fn main() -> i32
    let e = E { ino: 1, kind: 2, name: V { ptr: null, len: 13 }, tail: 3 }
    if chk(e, 13) != 0
        return 1
    42
""",
    "nested_var_reassign": """\
pub fn main() -> i32
    var e: E = E { ino: 1, kind: 2, name: V { ptr: null, len: 14 }, tail: 3 }
    if e.name.len != 14
        return 1
    e = E { ino: 1, kind: 2, name: V { ptr: null, len: 15 }, tail: 3 }
    if chk(e, 15) != 0
        return 2
    42
""",
    # Two levels deep, mixing a nested literal with a call inside it.
    "nested_two_levels": """\
fn mk(n: i64) -> O
    O { a: 7, e: E { ino: 1, kind: 2, name: mkv(n), tail: 3 }, b: 9 }

pub fn main() -> i32
    let o = mk(16)
    if o.a != 7 or o.b != 9
        return 1
    if chk(o.e, 16) != 0
        return 2
    let p = O { b: 9, e: E { ino: 1, kind: 2, name: V { ptr: null, len: 17 }, tail: 3 }, a: 7 }
    if p.a != 7 or p.b != 9
        return 3
    if chk(p.e, 17) != 0
        return 4
    42
""",
}


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(PRELUDE + program)
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
def test_ritz1_struct_valued_fields(ritz1_bin, tmp_path, name):
    """ritz1 dropped call-result fields and rejected nested literals (#1655)."""
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
