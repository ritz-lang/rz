"""Regression tests for AGAST #1645: ritz1 match expressions whose arms yield
an aggregate (struct) value.

ritz1's match lowering (emitter_match.ritz) merged the arm values with
`phi i64` whatever the arm type was. When the arms yield a struct such as
`%StrView` (`option_unwrap_or<StrView>`: `Some(v) => v / None => default`),
LLVM rejects the IR:

    '%.13' defined with type '%StrView = type { ptr, i64 }' but expected 'i64'
    %.19 = phi i64 [ %.13, %L1 ], [ %.17, %L3 ], [ %.18, %L4 ]

The phi, and its synthesised non-exhaustive fallthrough value, must use the
arm's real LLVM type. That was the last ritz1 error in `import ritzlib.argspec`.

Each program returns 42 when correct and a distinct small code naming the check
that failed otherwise. ritz0 is the oracle.
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
            "could not build ritz1 for the match-aggregate tests:\n"
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


STRUCT_POINT = """\
struct Point
    x: i64
    y: i64

"""

PROGRAMS = {
    # The ticket's repro: the ritzlib generic, StrView payload, both arms.
    "a_unwrap_or_strview": """\
import ritzlib.option
import ritzlib.strview

pub fn main() -> i32
    let o: Option<StrView> = None
    let v = option_unwrap_or<StrView>(@o, "abc")
    if v.len != 3
        return 1
    let s: Option<StrView> = Some("hello")
    let w = option_unwrap_or<StrView>(@s, "abc")
    if w.len != 5
        return 2
    return 42
""",
    # Same generic with a user struct payload.
    "b_unwrap_or_user_struct": STRUCT_POINT
    + """\
import ritzlib.option

pub fn main() -> i32
    let d = Point { x: 7, y: 8 }
    let o: Option<Point> = None
    let a = option_unwrap_or<Point>(@o, d)
    if a.x != 7 or a.y != 8
        return 1
    let p = Point { x: 30, y: 12 }
    let s: Option<Point> = Some(p)
    let d2 = Point { x: 7, y: 8 }
    let b = option_unwrap_or<Point>(@s, d2)
    if b.x != 30 or b.y != 12
        return 2
    return b.x + b.y
""",
    # A non-generic tail match through a pointer, user struct payload.
    "c_tail_match_user_struct": STRUCT_POINT
    + """\
import ritzlib.option

fn pick(o: *Option<Point>, d: Point) -> Point
    match *o
        Some(p) => p
        None => d

pub fn main() -> i32
    let d = Point { x: 1, y: 2 }
    let n: Option<Point> = None
    let a = pick(@n, d)
    if a.x != 1 or a.y != 2
        return 1
    let q = Point { x: 40, y: 2 }
    let s: Option<Point> = Some(q)
    let d2 = Point { x: 1, y: 2 }
    let b = pick(@s, d2)
    b.x + b.y
""",
    # A tail match on an Option local whose arms are StrView params/bindings.
    "d_tail_match_strview": """\
import ritzlib.option
import ritzlib.strview

fn choose(o: Option<StrView>, d: StrView) -> StrView
    match o
        Some(v) => v
        None => d

pub fn main() -> i32
    let n: Option<StrView> = None
    let a = choose(n, "four")
    if a.len != 4
        return 1
    let s: Option<StrView> = Some("thirty-eight-chars-long-string-here!!!")
    let b = choose(s, "four")
    b.len as i32 + a.len as i32
""",
    # The pattern binding is the only arm whose struct type ritz1 can name
    # (a field read is not resolved), so the type has to be taken while
    # `p` is still bound, before the arm scope is popped.
    "d2_binding_is_only_typed_arm": STRUCT_POINT
    + """\
import ritzlib.option

struct Holder
    d: Point

fn pick(o: *Option<Point>, h: *Holder) -> Point
    match *o
        Some(p) => p
        None => h.d

pub fn main() -> i32
    let d = Point { x: 1, y: 2 }
    var h = Holder { d: d }
    let n: Option<Point> = None
    let a = pick(@n, @h)
    if a.x != 1 or a.y != 2
        return 1
    let q = Point { x: 40, y: 2 }
    let s: Option<Point> = Some(q)
    let b = pick(@s, @h)
    b.x + b.y
""",
    # Scalar arms must still phi as i64 (no regression of the common case).
    "e_scalar_arms_unchanged": """\
import ritzlib.option

pub fn main() -> i32
    let o: Option<i64> = None
    let a = option_unwrap_or<i64>(@o, 40)
    let s: Option<i64> = Some(2)
    let b = option_unwrap_or<i64>(@s, 99)
    (a + b) as i32
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


# The acceptance target. argspec pulls in the allocator (`realloc`), which this
# file's bare `-nostdlib` link does not provide, so it is checked to the object
# file: what #1645 broke was the IR, which clang rejected before linking.
ARGSPEC_PROGRAM = """\
import ritzlib.argspec

pub fn main() -> i32
    return 42
"""


def _compile_to_object(compiler: str, tmp_path: Path, program: str) -> None:
    src = tmp_path / f"argspec_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"argspec_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)]
    comp = subprocess.run(
        cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile argspec:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    obj = tmp_path / f"argspec_{compiler}.o"
    cc = subprocess.run(
        ["clang", "-c", "-x", "ir", str(ll), "-o", str(obj)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert cc.returncode == 0, (
        f"{compiler} emitted invalid IR for import ritzlib.argspec:\n"
        f"{cc.stderr[-2000:]}"
    )


@pytest.mark.integration
def test_ritz0_compiles_argspec(tmp_path):
    _compile_to_object("ritz0", tmp_path, ARGSPEC_PROGRAM)


@pytest.mark.integration
def test_ritz1_compiles_argspec(ritz1_bin, tmp_path):
    """`import ritzlib.argspec` hit the StrView phi in option_unwrap_or (#1645)."""
    _compile_to_object("ritz1", tmp_path, ARGSPEC_PROGRAM)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, PROGRAMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_match_aggregate_phi(ritz1_bin, tmp_path, name):
    """ritz1 merged struct-valued match arms with `phi i64` (#1645)."""
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
