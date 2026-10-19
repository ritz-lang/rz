"""Regression tests for AGAST #1652 / #1672: an `@&T` value used where a `*T`
is expected.

ritz1 lowers `*T` as i64 (its value model) but `@&T` as `ptr`.  When an
`@&T` local (or an `@&v` expression) flows into a `*T` slot, the `ptr` must be
ptrtoint'd, or clang rejects the IR ("defined with type 'ptr' but expected
'i64'").  #1644 fixed the free-function call argument; these are the other
`*T` sinks:

* `let p: *S = s` (typed let) and `p = s` (assignment to a `*S` local)
* `s as *S` (the cast was a no-op that left a `ptr`), also `as i64`
* `return s` / tail `s` from a `-> *S` fn
* `h.p = s` (store into a `*S` struct field, through a pointer or a local)

Each program exits 42 only if the pointer that lands in the `*T` slot still
aliases the caller's struct (writes through it are seen by the caller).
ritz0 is the oracle.  The call-argument and by-value `*b` deref forms from the
tickets already work on main (#1644) and are pinned in WORKING.
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
            "could not build ritz1 for the @&T -> *T tests:\n"
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


# Shared prelude: `S` plus a `*S` consumer that writes through its pointer.
PRELUDE = """\
struct S
    a: i32

struct H
    p: *S

struct O
    h: H

fn bump(s: *S) -> i32
    s.a = s.a + 2
    s.a
"""

# --- `let` / assignment into a `*S` local -------------------------------------

LET_ASSIGN = {
    # #1652: `let p: *S = s` stored the ptr as `store i64 <ptr>`.
    "let_typed": """\
fn f(s: @&S) -> i32
    let p: *S = s
    p.a = p.a + 2
    0

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
    s.a
""",
    # `p = s` after the declaration takes the emit_assign local path.
    "assign_local": """\
fn f(s: @&S) -> i32
    var p: *S = null
    p = s
    bump(p)

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
    # `@&v` straight into a `*S` let.
    "let_from_addr_mut": """\
pub fn main() -> i32
    var s: S = S { a: 40 }
    let p: *S = @&s
    bump(p)
""",
}

# --- `as *S` / `as i64` casts --------------------------------------------------

CAST = {
    # #1652: `s as *S` was a no-op, leaving a `ptr` in an i64 call arg.
    "cast_call_arg": """\
fn f(s: @&S) -> i32
    bump(s as *S)

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
    "cast_let": """\
fn f(s: @&S) -> i32
    let p: *S = s as *S
    bump(p)

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
    # The cast result is an integer address equal to the caller's `@s`.
    "cast_to_int": """\
fn addr(s: @&S) -> i64
    (s as *S) as i64

pub fn main() -> i32
    var s: S = S { a: 40 }
    let got: i64 = addr(@&s)
    let p: *S = @s
    if got != p as i64
        return 1
    42
""",
}

# --- return / field store -----------------------------------------------------

RET_FIELD = {
    "return_stmt": """\
fn as_ptr(s: @&S) -> *S
    return s

pub fn main() -> i32
    var s: S = S { a: 40 }
    bump(as_ptr(@&s))
""",
    "return_tail": """\
fn as_ptr(s: @&S) -> *S
    s

pub fn main() -> i32
    var s: S = S { a: 40 }
    bump(as_ptr(@&s))
""",
    # Tail return from an impl method (emit_impl_method's own tail path).
    "return_tail_method": """\
struct W
    k: i64

impl W
    fn pick(self: *W, s: @&S) -> *S
        s

pub fn main() -> i32
    var s: S = S { a: 40 }
    var w: W
    let wp: *W = @w
    bump(wp.pick(@&s))
""",
    # Field store through a `*H`.
    "field_store_via_ptr": """\
fn hold(h: *H, s: @&S) -> i32
    h.p = s
    0

pub fn main() -> i32
    var s: S = S { a: 40 }
    var h: H
    hold(@h, @&s)
    bump(h.p)
""",
    # The emit_assign member path: a global struct field, and nested fields
    # (through a pointer and in a local).
    "field_store_global": """\
var G: H

fn f(s: @&S) -> i32
    G.p = s
    bump(G.p)

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
    "field_store_nested_via_ptr": """\
fn f(o: *O, s: @&S) -> i32
    o.h.p = s
    bump(o.h.p)

pub fn main() -> i32
    var s: S = S { a: 40 }
    var o: O
    f(@o, @&s)
""",
    "field_store_nested_local": """\
fn f(s: @&S) -> i32
    var o: O
    o.h.p = s
    bump(o.h.p)

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
    # Field store into a local struct.
    "field_store_local": """\
fn f(s: @&S) -> i32
    var h: H
    h.p = s
    bump(h.p)

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
}

# --- forms that already worked on main (#1644); pinned -------------------------

WORKING = {
    # #1652's original repro: call argument into a `*T` param.
    "call_arg": """\
fn f(s: @&S) -> i32
    bump(s)

pub fn main() -> i32
    var s: S = S { a: 40 }
    f(@&s)
""",
    # #1672 repro 1.
    "call_arg_extra_args": """\
struct G
    len: i64

fn app(b: *G, len: i64) -> i32
    b.len = b.len + len
    return 0

fn via_mut(b: @&G) -> i32
    return app(b, 3)

pub fn main() -> i32
    var g: G
    g.len = 39
    via_mut(@&g)
    g.len as i32
""",
    # #1672 repro 2: by-value deref of an `@&` struct param.
    "deref_by_value": """\
struct Buffer
    pos: i64
    end: i64

fn f(b: @&Buffer) -> i64
    let start: Buffer = *b
    b.pos = 0
    return start.pos + start.end

pub fn main() -> i32
    var b: Buffer = Buffer { pos: 40, end: 2 }
    let r: i64 = f(@&b)
    if b.pos != 0
        return 1
    r as i32
""",
    # `@s` is already i64: a `*S` let must not ptrtoint it again.
    "let_from_addr": """\
pub fn main() -> i32
    var s: S = S { a: 40 }
    let p: *S = @s
    bump(p)
""",
}

BROKEN = {**LET_ASSIGN, **CAST, **RET_FIELD}
ALL = {**BROKEN, **WORKING}


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(PRELUDE + "\n" + program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
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
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ALL))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, ALL[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(LET_ASSIGN))
def test_ritz1_mut_ref_into_ptr_local(ritz1_bin, tmp_path, name):
    """`let p: *S = s` / `p = s` with `s: @&S` ptrtoints into the i64 slot."""
    assert _run("ritz1", tmp_path, name, LET_ASSIGN[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CAST))
def test_ritz1_mut_ref_cast_to_ptr(ritz1_bin, tmp_path, name):
    """`s as *S` yields the i64 address, not the raw `ptr`."""
    assert _run("ritz1", tmp_path, name, CAST[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RET_FIELD))
def test_ritz1_mut_ref_into_ptr_return_and_field(ritz1_bin, tmp_path, name):
    """`return s` from `-> *S` and `h.p = s` into a `*S` field."""
    assert _run("ritz1", tmp_path, name, RET_FIELD[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(WORKING))
def test_ritz1_already_working_forms(ritz1_bin, tmp_path, name):
    """Forms that worked before #1652 (call arg, by-value deref, `@s`)."""
    assert _run("ritz1", tmp_path, name, WORKING[name]) == 42


@pytest.mark.integration
def test_ritz1_ptr_let_from_addr_is_not_cast_again(ritz1_bin, tmp_path):
    """`@s` is already i64: the `*S` let must not add a second ptrtoint."""
    comp, ll = _compile("ritz1", tmp_path, "addr_ir", WORKING["let_from_addr"])
    assert comp.returncode == 0, comp.stdout[-2000:]
    main_ir = ll.read_text().split("define i32 @main", 1)[1]
    assert main_ir.count("ptrtoint ptr") == 1, main_ir  # the `@s` itself
    assert "#1652" not in main_ir, main_ir
