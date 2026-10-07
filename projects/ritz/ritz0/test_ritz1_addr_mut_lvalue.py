"""Regression tests for AGAST #1488: ritz1's `@&` (mutable address-of) must
accept the same lvalues as `@` does, not only a bare local.

Before the fix, ritz1's OP_ADDR_MUT branch (ritz1/src/emitter_expr_arith.ritz)
handled only `EXPR_IDENT` resolving to a local. Every other operand failed with
`error: ritz1 cannot emit: cannot take mutable address` (exit 1, no output):
`@&s.field`, `@&p.field` through a pointer or `@&` param, `@&o.a.b` (nested),
`@&arr[i]`, `@&arr[i].f`, and `@&g` for a module-level global. The OP_ADDR
branch right above it already lowered all of these. ritzlib/argspec.ritz writes
`vec_push<ArgFlag>(@&spec.flags, f)` seven times, so ritz1 could not compile it
(examples/tier2_stdlib/77_args).

The fix routes `@` and `@&` through one lvalue-address helper so the two can't
drift apart again. `@` yields an i64 (ptrtoint) and `@&` yields the ptr.

Every program writes through the `@&` pointer, and the caller then reads the
lvalue back. A fix that takes the address of a COPY (a load into a fresh temp
alloca) compiles, but its write never reaches the caller, so the exit code
comes out wrong. ritz0 is run as the oracle.
"""

import os
import subprocess
from pathlib import Path

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date. A stale ritz1 would test the old emitter (#1322)."""
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
            "could not build ritz1 for the @& lvalue tests:\n"
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


# Shared prelude: `bump` writes through an `@&C`. The pointee is a struct
# because that is argspec's shape (`@&Vec<T>`). (A read through a SCALAR
# `@&i64` param was a separate ritz1 bug, fixed by #1644 and covered in
# test_ritz1_scalar_mut_borrow.py.)
_BUMP = """\
struct C
    n: i64

fn bump(c: @&C, k: i64)
    c.n = c.n + k

struct P
    a: i64
    c: C

"""

# name -> (program, expected exit code). The expected code is ritz0's answer
# and test_ritz0_is_the_oracle pins it.
FIXED_FORMS = {
    # The ticket's repro: `@&s.v` where s is itself an `@&S` param.
    "repro_param_vec_field": ("""\
import ritzlib.memory
import ritzlib.gvec

struct S
    v: Vec<i64>

fn add(s: @&S, x: i64)
    vec_push<i64>(@&s.v, x)

pub fn main() -> i32
    var s: S
    s.v = vec_new<i64>()
    add(@&s, 5)
    (s.v.len) as i32
""", 1),
    # The ticket's second shape: a field of a LOCAL struct.
    "local_vec_field": ("""\
import ritzlib.memory
import ritzlib.gvec

struct S
    v: Vec<i64>

pub fn main() -> i32
    var s: S
    s.v = vec_new<i64>()
    vec_push<i64>(@&s.v, 5)
    vec_push<i64>(@&s.v, 6)
    (s.v.len) as i32
""", 2),
    "local_struct_field": (_BUMP + """\
pub fn main() -> i32
    var p: P
    p.a = 1
    p.c.n = 2
    bump(@&p.c, 40)
    (p.a + p.c.n) as i32
""", 43),
    # Field through a raw pointer param.
    "ptr_param_field": (_BUMP + """\
fn f(q: *P)
    bump(@&q.c, 40)

pub fn main() -> i32
    var p: P
    p.a = 1
    p.c.n = 2
    f(@p)
    (p.a + p.c.n) as i32
""", 43),
    # Nested member chain through an `@&` param: `@&o.inner.c`.
    "nested_member": (_BUMP + """\
struct O
    pad: i64
    inner: P

fn f(o: @&O)
    bump(@&o.inner.c, 40)

pub fn main() -> i32
    var o: O
    o.pad = 7
    o.inner.a = 1
    o.inner.c.n = 2
    f(@&o)
    (o.pad + o.inner.a + o.inner.c.n) as i32
""", 50),
    # Field of an array element: `@&arr[i].c`.
    "array_elem_field": (_BUMP + """\
pub fn main() -> i32
    var arr: [3]P
    arr[0].c.n = 1
    arr[1].c.n = 2
    arr[2].c.n = 3
    let i: i64 = 1
    bump(@&arr[i].c, 40)
    (arr[0].c.n + arr[1].c.n + arr[2].c.n) as i32
""", 46),
    # Element of a local array: `@&arr[i]`.
    "local_array_elem": (_BUMP + """\
pub fn main() -> i32
    var arr: [4]C
    arr[0].n = 1
    arr[1].n = 2
    arr[2].n = 3
    arr[3].n = 4
    let i: i64 = 2
    bump(@&arr[i], 30)
    (arr[0].n + arr[1].n + arr[2].n + arr[3].n) as i32
""", 40),
    # Element of an array field: `@&h.xs[i]`.
    "array_field_elem": (_BUMP + """\
struct H
    n: i64
    xs: [4]C

pub fn main() -> i32
    var h: H
    h.n = 1
    h.xs[0].n = 1
    h.xs[1].n = 2
    h.xs[2].n = 3
    h.xs[3].n = 4
    bump(@&h.xs[3], 20)
    (h.n + h.xs[0].n + h.xs[1].n + h.xs[2].n + h.xs[3].n) as i32
""", 31),
    # Module-level globals: a whole struct global, and a field of one.
    "global_struct": (_BUMP + """\
var g_c: C

pub fn main() -> i32
    g_c.n = 2
    bump(@&g_c, 40)
    g_c.n as i32
""", 42),
    "global_struct_field": (_BUMP + """\
var g_p: P

pub fn main() -> i32
    g_p.a = 1
    g_p.c.n = 2
    bump(@&g_p.c, 40)
    (g_p.a + g_p.c.n) as i32
""", 43),
}

# Forms that worked before #1488, pinned so the refactor can't break them.
WORKING_FORMS = {
    "bare_local": (_BUMP + """\
pub fn main() -> i32
    var c: C
    c.n = 2
    bump(@&c, 40)
    c.n as i32
""", 42),
    # `@` (immutable address-of) shares the helper now; pin a field, an
    # index and a global form of it.
    "addr_of_field_index_global": ("""\
struct P
    a: i64
    b: i64

var g_x: i64

fn rd(x: *i64) -> i64
    *x

pub fn main() -> i32
    var p: P = P { a: 1, b: 40 }
    var arr: [3]i64
    arr[0] = 0
    arr[1] = 0
    arr[2] = 2
    g_x = 100
    (rd(@p.b) + rd(@arr[2]) + p.a + rd(@g_x) - 100) as i32
""", 43),
}

ALL_RUNNABLE = {**FIXED_FORMS, **WORKING_FORMS}


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)]
    comp = subprocess.run(
        cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
    )
    return comp, ll


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code.

    A program that imports ritzlib goes through build.py, which also compiles
    and links the imported modules (gvec needs ritzlib.memory's allocator).
    """
    if "import " in program:
        return _run_pkg(compiler, tmp_path, name, program)
    comp, ll = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )

    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ALL_RUNNABLE))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    program, expected = ALL_RUNNABLE[name]
    assert _run("ritz0", tmp_path, name, program) == expected


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(FIXED_FORMS))
def test_ritz1_addr_mut_of_lvalue(ritz1_bin, tmp_path, name):
    """AGAST #1488. Before the fix each was `cannot take mutable address` (exit 1)."""
    program, expected = FIXED_FORMS[name]
    assert _run("ritz1", tmp_path, name, program) == expected


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(WORKING_FORMS))
def test_ritz1_already_working_addr_forms(ritz1_bin, tmp_path, name):
    """Address-of forms that worked before the fix must still work."""
    program, expected = WORKING_FORMS[name]
    assert _run("ritz1", tmp_path, name, program) == expected


@pytest.mark.integration
def test_ritz1_addr_mut_of_rvalue_still_fails_closed(ritz1_bin, tmp_path):
    """`@&` of a non-lvalue is still an honest ritz1 error with no output (#1369)."""
    program = _BUMP + """\
fn five() -> i64
    5

pub fn main() -> i32
    bump(@&five(), 1)
    0
"""
    comp, ll = _compile("ritz1", tmp_path, "rvalue", program)
    assert comp.returncode != 0, f"ritz1 accepted `@&five()`:\n{comp.stdout[-1000:]}"
    assert "cannot take mutable address" in comp.stdout + comp.stderr
    assert not ll.exists(), "ritz1 wrote an artifact for `@&five()`"
