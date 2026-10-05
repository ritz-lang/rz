"""Regression tests for AGAST #1497: bool values in struct literals, field
assignments and typed lets under ritz1.

Two root causes:

1. Bool *params* were spilled into `alloca i1` slots and loaded back as i1,
   while every other scalar in ritz1 (bool locals included) is an i64 value.
   Each consumer that assumed i64 then emitted invalid IR (`store i64 %x` with
   `%x` an i1, or `trunc i64 %x to i1`).
2. The struct-literal field-store dispatches had no TYPE_BOOL arm. The let/var
   loop fell back to an 8-byte `store i64` over the i1 field, clobbering the
   next field. emit_struct_lit_to_alloca (tail / return / reassignment
   literals) silently skipped the field.

Each program returns 42 when correct and a distinct small code naming the check
that failed otherwise. ritz0 is the oracle. Every case is checked at RUNTIME,
because (b) and (c) in the ticket compiled cleanly and only gave wrong answers.
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
            "could not build ritz1 for the bool-field tests:\n"
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


STRUCT_F = """\
struct F
    a: i64
    b: bool

"""

# bool first, then a narrow field: an 8-byte store at field 0 zeroes c.
STRUCT_G = """\
struct G
    b: bool
    c: i32

"""

# Bool fields are read only as `if x.b` here: `not x.b` (AGAST #1646) and
# `call().b` (AGAST #1647) are separate ritz1 gaps.
PROGRAMS = {
    # (a) bool PARAM into a let-bound literal: was invalid IR (store i64 of i1).
    "a_let_lit_from_param": STRUCT_F
    + """\
fn mk(b: bool) -> F
    let f = F { a: 1, b: b }
    f

pub fn main() -> i32
    let t = mk(true)
    let u = mk(false)
    if u.b
        return 2
    if t.b
        return 42
    return 1
""",
    # (b) bool LITERAL ahead of an i32: the 8-byte store clobbered c.
    "b_let_lit_clobber": STRUCT_G
    + """\
pub fn main() -> i32
    let g = G { c: 5, b: true }
    if g.c != 5
        return 1
    if g.b
        return 42
    return 2
""",
    # (b') same shape through a typed var, values from params.
    "b_var_lit_param_clobber": STRUCT_G
    + """\
fn mk(b: bool, c: i32) -> i32
    var g: G = G { c: c, b: b }
    if g.c != c
        return 1
    if g.b
        return 10
    return 20

pub fn main() -> i32
    if mk(true, 5) != 10
        return 1
    if mk(false, 9) != 20
        return 2
    return 42
""",
    # (c) tail-expression literal: the bool field was never stored.
    "c_tail_lit": STRUCT_F
    + """\
fn mk_lit() -> F
    F { a: 1, b: true }

fn mk_param(b: bool) -> F
    F { a: 1, b: b }

pub fn main() -> i32
    let f = mk_lit()
    if f.a != 1
        return 2
    let t = mk_param(true)
    let u = mk_param(false)
    if u.b
        return 4
    if not f.a == 1
        return 5
    if f.b
        if t.b
            return 42
        return 3
    return 1
""",
    # (c') emit_struct_lit_to_alloca via `return` and reassignment, with the
    # bool ahead of an i32 so a wide store would show up as a clobber.
    "c_return_and_assign": STRUCT_G
    + """\
fn mk(b: bool) -> G
    return G { b: b, c: 7 }

pub fn main() -> i32
    let g = mk(true)
    if g.c != 7
        return 2
    if g.b
        var h: G = G { b: true, c: 3 }
        h = G { c: 9, b: false }
        if h.b
            return 3
        if h.c != 9
            return 4
        h = G { c: 11, b: true }
        if h.c != 11
            return 6
        if h.b
            return 42
        return 5
    return 1
""",
    # A bool field read (an i1 register) copied into another literal.
    "c_field_to_field": STRUCT_G
    + """\
fn copy(src: G) -> G
    G { c: src.c + 1, b: src.b }

pub fn main() -> i32
    let a = G { b: true, c: 4 }
    let b = G { b: a.b, c: 6 }
    if b.c != 6
        return 1
    let c = copy(b)
    if c.c != 7
        return 2
    let f = G { b: false, c: 1 }
    let z = copy(f)
    if z.b
        return 3
    if c.b
        return 42
    return 4
""",
    # (d) field assign from a bool param: was invalid IR (trunc of an i1).
    "d_field_assign_param": STRUCT_G
    + """\
fn set(b: bool) -> G
    var g = G { b: false, c: 5 }
    g.b = b
    g

pub fn main() -> i32
    let t = set(true)
    let u = set(false)
    if t.c != 5
        return 2
    if u.b
        return 3
    if t.b
        return 42
    return 1
""",
    # (e) same root as (a)/(d) outside structs: typed let, return, call args,
    # logic and while on bool params.
    "e_typed_let_param": """\
fn k(b: bool) -> i32
    let c: bool = b
    if c
        return 1
    return 0

fn ident(b: bool) -> bool
    b

fn fwd(b: bool) -> bool
    ident(b)

fn both(x: bool, y: bool) -> bool
    x and not y

fn chk(b: bool) -> i32
    while b
        return 1
    return 0

pub fn main() -> i32
    if k(true) != 1
        return 1
    if k(false) != 0
        return 2
    if not fwd(true)
        return 3
    if fwd(false)
        return 4
    if not both(true, false)
        return 5
    if both(true, true)
        return 6
    if chk(true) != 1
        return 7
    return 42
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
def test_ritz1_bool_fields(ritz1_bin, tmp_path, name):
    """ritz1 mis-stored bools from params / in struct literals (#1497)."""
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
