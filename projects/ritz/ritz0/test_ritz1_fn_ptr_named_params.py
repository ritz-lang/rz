"""Regression tests for AGAST #1544 — ritz1 must parse fn-pointer types whose
params carry names: `fn(node_id: NodeId, offset: Point)`.

ritz0 always accepted the named form. ritz1's `fn_ptr_params` rule only took
bare types (`type_spec COMMA fn_ptr_params | type_spec`, from ritz-task-169),
so a named param failed to parse wherever a type can appear: alias targets
(iris's `ScrollCallback`, tempest's `DomCallback`), struct fields and fn
params. It showed up as

    cannot parse item starting at 'pub'

The fix adds `IDENT COLON type_spec [COMMA fn_ptr_params]` alternatives ahead
of the bare ones and discards the names; a fn pointer lowers to TYPE_PTR either
way.

Every program returns 3 on success. ritz0 is the oracle.
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


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date so we never assert against a stale grammar."""
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
            "could not build ritz1 for the fn-pointer tests:\n"
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


# --- programs -----------------------------------------------------------------

# The ticket's repro, verbatim (iris's ScrollCallback shape).
REPRO = """\
struct Point
    x: i32

pub type ScrollCallback = fn(node_id: u32, offset: Point)

pub fn main() -> i32
    return 3
"""

# tempest's DomCallback: one named param plus a return type.
NAMED_WITH_RETURN = """\
struct DomRequest
    id: i32

struct DomResult
    code: i32

pub type DomCallback = fn(request: DomRequest) -> DomResult

pub fn main() -> i32
    return 3
"""

# Named params in a struct field type and in a fn param type, then called
# through the pointer, so the named form must lower to a working fn pointer.
FIELD_AND_PARAM = """\
fn add1(x: i32) -> i32
    return x + 1

struct Holder
    cb: fn(x: i32) -> i32

fn apply(f: fn(v: i32) -> i32, v: i32) -> i32
    return f(v)

pub fn main() -> i32
    var h: Holder = Holder { cb: add1 }
    return apply(h.cb, 2)
"""

# Several named params, pointer-typed params, and a named param that is
# itself a fn type.
MULTI_NAMED = """\
struct Point
    x: i32

type Visit = fn(node: *Point, depth: i32, done: fn(ok: bool)) -> i32

pub fn main() -> i32
    return 3
"""

# Named and bare params mixed in either order (ritz0 accepts both). A bare
# IDENT type (`Point`) starts like a named param, so the named alternative
# must fall back to the bare one when no COLON follows.
MIXED = """\
struct Point
    x: i32

type NamedFirst = fn(a: i32, i64, c: u8)
type BareFirst = fn(i32, b: i64) -> i32
type IdentBare = fn(Point, p: *Point, Point) -> Point

pub fn main() -> i32
    return 3
"""

# The pre-existing bare forms must keep parsing (spire's router callback).
UNNAMED = """\
struct Request
    id: i32

struct Response
    code: i32

pub type Handler = fn(*Request) -> Response
type Pair = fn(i32, i64) -> i32
type Nullary = fn() -> i32
type Unit = fn()

pub fn main() -> i32
    return 3
"""

PROGRAMS = {
    "repro": REPRO,
    "named_with_return": NAMED_WITH_RETURN,
    "field_and_param": FIELD_AND_PARAM,
    "multi_named": MULTI_NAMED,
    "mixed": MIXED,
    "unnamed": UNNAMED,
}

# A name with no type after the colon must still be rejected.
MALFORMED = {
    "missing_type": """\
type Bad = fn(x: ) -> i32

pub fn main() -> i32
    return 3
""",
    "trailing_colon_name": """\
type Bad = fn(x:)

pub fn main() -> i32
    return 3
""",
}


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    src = work / "main.ritz"
    src.write_text(program)
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
    comp = subprocess.run(
        cmd, cwd=work, env=env, capture_output=True, text=True, timeout=300
    )
    return comp, ll, work


def _run(compiler: str, tmp_path: Path, name: str) -> int:
    """Compile PROGRAMS[name] with `compiler`, link, run, return the exit code."""
    comp, ll, work = _compile(compiler, tmp_path, name, PROGRAMS[name])
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


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_fn_ptr_named_params(ritz1_bin, tmp_path, name):
    """AGAST #1544. Before the fix the named forms died with `cannot parse item`."""
    assert _run("ritz1", tmp_path, name) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_ritz1_rejects_malformed_fn_ptr(ritz1_bin, tmp_path, name):
    comp, ll, _ = _compile("ritz1", tmp_path, name, MALFORMED[name])
    assert comp.returncode != 0, (
        f"ritz1 accepted malformed fn type {name!r}:\n{comp.stdout[-1000:]}"
    )
    assert not ll.exists(), f"ritz1 wrote an artifact for malformed {name!r}"
