"""Regression tests for AGAST #1644: ritz1 reading through a SCALAR mutable
borrow, and passing an `@&` value into a `*T` parameter.

Three separate ritz1 defects, all of which made clang reject the IR:

1. `*x` READ with `x: @&i64`.  A TYPE_MUT_REF local loads as `ptr`, but the
   OP_DEREF rvalue arm assumed the i64 value model and emitted
   `inttoptr i64 %p to ptr` on it.  The STORE side (`*x = v`) already skipped
   the cast (AGAST #173); the read now does the same, and loads at the
   pointee's width (`@&i32` loads i32, not i64).

2. The `x:& T` borrow form.  ritz0 auto-dereferences it: reading `x` reads the
   pointee, `x = v` / `x += v` store through it, and `@&x` forwards the
   caller's pointer.  ritz1 parsed it as a plain `@&T` and treated `x + n` as
   pointer arithmetic.  A scalar `x:& T` param is now bound as a local whose
   storage slot IS the caller's pointer, so every read, write and `@&x` lowers
   as it would for the caller's own variable.  Struct pointees (`c:& C`,
   `c.n = ...`) keep the existing pointer lowering, which already worked.

3. `@&x` (a `ptr`) passed into a `*T` parameter (lowered as i64) got no
   `ptrtoint`.  It now does, also for a TYPE_MUT_REF ident forwarded into a
   `*T` param.

Every program exits 42 only if the write lands in the caller's variable at
the right width.  ritz0 is run as the oracle.
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
            "could not build ritz1 for the scalar mutable-borrow tests:\n"
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


# --- 1. `*x` read through an `@&` scalar -------------------------------------

DEREF_READ = {
    # The ticket's repro.
    "at_amp_i64_deref_read": """\
fn bump(x: @&i64, n: i64)
    *x = *x + n

pub fn main() -> i32
    var x: i64 = 2
    bump(@&x, 40)
    x as i32
""",
    # Narrow pointee: the read must load i32, not 8 bytes of the caller's slot.
    "at_amp_i32_deref_read": """\
fn dbl(p: @&i32)
    *p = *p * 2

pub fn main() -> i32
    var w: i32 = 21
    dbl(@&w)
    w
""",
    # Width check: an 8-byte read of `q.a` would pull in `q.b` (-1) as the
    # high half, so the full i64 is compared, not just its truncation.
    "at_amp_i32_deref_width": """\
struct P
    a: i32
    b: i32

fn get(p: @&i32) -> i64
    *p

pub fn main() -> i32
    var q: P = P { a: 40, b: -1 }
    let v: i64 = get(@&q.a)
    if v != 40
        return 1
    42
""",
    # The read alone, as a returned value.
    "at_amp_i64_deref_return": """\
fn get(x: @&i64) -> i64
    *x + 40

pub fn main() -> i32
    var x: i64 = 2
    get(@&x) as i32
""",
}

# --- 2. the `x:& T` auto-deref borrow ----------------------------------------

BORROW = {
    # The ticket's second form.
    "borrow_i64_assign": """\
fn bump(x:& i64, n: i64)
    x = x + n

pub fn main() -> i32
    var x: i64 = 2
    bump(@&x, 40)
    x as i32
""",
    # Compound assignment, i32 width, and a unary use of the value.
    "borrow_i32_compound_and_neg": """\
fn bump(x:& i32, n: i32)
    x = x + n
    x += 1

fn neg(x:& i32)
    x = 0 - x

pub fn main() -> i32
    var a: i32 = 2
    bump(@&a, 40)
    var b: i32 = 1
    neg(@&b)
    a + b
""",
    # u8: the store must truncate to one byte (255 + 1 wraps to 0).
    "borrow_u8_wraps": """\
fn inc(b:& u8)
    b = b + 1

pub fn main() -> i32
    var b: u8 = 255
    inc(@&b)
    (b as i32) + 42
""",
    # Read-only uses: a `let` copy and a tail value.
    "borrow_i64_reads": """\
fn copy(x:& i64) -> i64
    let y: i64 = x
    y + 1

fn get(x:& i64) -> i64
    x

pub fn main() -> i32
    var x: i64 = 20
    (copy(@&x) + get(@&x) + 1) as i32
""",
    # `@&x` inside a borrow forwards the CALLER's pointer, not the param slot.
    "borrow_forwarded": """\
fn inner(x:& i64, n: i64)
    x += n

fn outer(x:& i64)
    inner(@&x, 20)
    x = x + 1

pub fn main() -> i32
    var x: i64 = 21
    outer(@&x)
    x as i32
""",
}

# --- 3. `@&` value into a `*T` (i64) parameter -------------------------------

PTR_PARAM = {
    # The ticket's third form.
    "addr_mut_into_ptr_param": """\
fn bump(x: *i64, n: i64)
    *x = *x + n

pub fn main() -> i32
    var x: i64 = 2
    bump(@&x, 40)
    x as i32
""",
    # An `@&i64` local forwarded into a `*i64` param.
    "at_amp_ident_into_ptr_param": """\
fn wr(p: *i64)
    *p = 42

fn fwd(x: @&i64)
    wr(x)

pub fn main() -> i32
    var x: i64 = 0
    fwd(@&x)
    x as i32
""",
}

# --- forms that already worked, pinned against regression --------------------

WORKING = {
    # #1488's shape: a struct pointee, through both borrow spellings.
    "struct_at_amp_field": """\
struct C
    n: i64

fn add(c: @&C, k: i64)
    c.n = c.n + k

pub fn main() -> i32
    var c: C = C { n: 2 }
    add(@&c, 40)
    c.n as i32
""",
    "struct_borrow_field": """\
struct C
    n: i64

fn add(c:& C, k: i64)
    c.n = c.n + k

pub fn main() -> i32
    var c: C = C { n: 2 }
    add(@&c, 40)
    c.n as i32
""",
    # `@x` (i64 in ritz1's value model) into a `*T` param must stay uncast.
    "addr_into_ptr_param": """\
fn bump(x: *i64, n: i64)
    *x = *x + n

pub fn main() -> i32
    var x: i64 = 2
    bump(@x, 40)
    x as i32
""",
    # `*x = v` store through `@&i64` (AGAST #173).
    "at_amp_store_only": """\
fn set(x: @&i64)
    *x = 42

pub fn main() -> i32
    var x: i64 = 0
    set(@&x)
    x as i32
""",
}

BROKEN = {**DEREF_READ, **BORROW, **PTR_PARAM}
ALL = {**BROKEN, **WORKING}


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
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
@pytest.mark.parametrize("name", sorted(DEREF_READ))
def test_ritz1_deref_read_through_at_amp_scalar(ritz1_bin, tmp_path, name):
    """`*x` with `x: @&T` scalar: no inttoptr on the ptr, pointee-width load."""
    assert _run("ritz1", tmp_path, name, DEREF_READ[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(BORROW))
def test_ritz1_scalar_borrow_auto_derefs(ritz1_bin, tmp_path, name):
    """`x:& T` scalar: reads, writes and `@&x` go through the caller's pointer."""
    assert _run("ritz1", tmp_path, name, BORROW[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PTR_PARAM))
def test_ritz1_mut_ref_arg_into_ptr_param(ritz1_bin, tmp_path, name):
    """A `ptr`-valued `@&` argument is ptrtoint'd for a `*T` (i64) param."""
    assert _run("ritz1", tmp_path, name, PTR_PARAM[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(WORKING))
def test_ritz1_already_working_forms(ritz1_bin, tmp_path, name):
    """Borrow and pointer forms that worked before #1644 must still work."""
    assert _run("ritz1", tmp_path, name, WORKING[name]) == 42


@pytest.mark.integration
def test_ritz1_ptr_param_from_addr_is_not_cast(ritz1_bin, tmp_path):
    """`@x` is already i64: the `*T` coercion must not ptrtoint it again."""
    comp, ll = _compile("ritz1", tmp_path, "addr_ir", WORKING["addr_into_ptr_param"])
    assert comp.returncode == 0, comp.stdout[-2000:]
    main_ir = ll.read_text().split("define i32 @main", 1)[1]
    assert "ptrtoint ptr" in main_ir  # the `@x` itself
    assert main_ir.count("ptrtoint ptr") == 1, main_ir
