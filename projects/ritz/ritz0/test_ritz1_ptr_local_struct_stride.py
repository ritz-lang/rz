"""Regression tests for AGAST #1451 — ritz1 must scale pointer arithmetic on
an annotated `let x: *Struct = ...` local by sizeof(Struct), not by 8.

The bug. `emit_var_decl` registered a `*Struct` local with
`add_local_struct`, which records the struct NAME but hard-codes
`pointee_type = TYPE_I64`.  The parser had already recorded
`var_pointee_type = TYPE_STRUCT`; the registration threw it away.
`get_ptr_elem_size` then saw an "i64 pointee" and scaled `base + k` by 8.
For a 16-byte struct that lands half-way into the wrong element.  It is a
SILENT miscompile: ritz1 exits 0 and the binary returns a wrong value.

Function PARAMETERS of the same type were always fine: they are registered
with `add_local_full(..., param_pointee_type)`, which keeps TYPE_STRUCT.  So
the same arithmetic gave different answers depending on whether the pointer
came in as an argument or was bound with `let`.

Why #1361's tests did not catch it: that program WRITES through `base + 1`
and then reads back through `base + i - 1`.  Both sides were scaled by the
same wrong stride, so the round trip agreed with itself.  Here the elements
are written by array index (`arr[k].start = ...`, which uses the real
struct layout) and read back through pointer arithmetic, so a wrong stride
reads the wrong bytes.

Every case below must return 10, the `start` of element 1.  Element 0 holds
0 and element 2 holds 20, so landing on the wrong element is distinguishable
from landing on the right one, and a half-element offset reads `length`
fields (all 0) or lands between elements.

Assertions are on the runtime exit code of the linked binary, not on IR
text: only running it proves the address is right.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# See test_ritz1_ptr_arith_chain.py: ritz1 output needs this runtime object
# for `_start`, and it is a gitignored build product, so build it.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date — a stale binary would assert nothing."""
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
            "could not build ritz1 for the *Struct stride tests:\n"
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


# Three 16-byte elements with start = 0, 10, 20, written by ARRAY INDEX so
# the stores use the real struct layout independently of pointer arithmetic.
#
# `LBVec` stands in for `Vec<LB>`: the ticket's second repro was
# `let base: *LB = lines.data` with `lines: @Vec<LineBounds>`.  A single-file
# compile cannot link ritzlib.gvec (imports are separate compile units that
# build.py links, and gvec needs the allocator), and what is under test is
# the `let base: *LB` binding, not how its initialiser was produced — so a
# struct with the same `data: *LB` field shape exercises the same code.
#
# `top` is `base + i` (element 2).  It gives the `- 1` cases a starting
# point above element 1 using the same kind of binding as `base`.
PROGRAM = """\
struct LB
    start: i64
    length: i64

struct LBVec
    data: *LB
    len: i64

fn main() -> i32
    var arr: [3]LB
    arr[0].start = 0
    arr[0].length = 0
    arr[1].start = 10
    arr[1].length = 0
    arr[2].start = 20
    arr[2].length = 0
    var vec: LBVec
    vec.data = @arr[0]
    vec.len = 3
    let base: *LB = %(base)s
    let i: i64 = 2
    let top: *LB = base + i
    let p: *LB = %(expr)s
    return p.start as i32
"""

BASES = {
    "addr_of_elem": "@arr[0]",
    "vec_data": "vec.data",
}

EXPRS = {
    "plus_1": "base + 1",
    "plus_i_minus_1": "base + (i - 1)",
    "minus_1": "top - 1",
}

CASES = [
    pytest.param(BASES[b], EXPRS[e], id=f"{b}-{e}") for b in BASES for e in EXPRS
]


def _compile_and_run(compiler: str, tmp_path: Path, src_text: str) -> int:
    """Compile `src_text` with `compiler`, link, run; return the exit code."""
    src = tmp_path / f"case_{compiler}.ritz"
    src.write_text(src_text)
    ll = tmp_path / f"case_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))

    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
    comp = subprocess.run(
        cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile:\n{src_text}\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )

    exe = tmp_path / f"case_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _run(compiler: str, tmp_path: Path, base: str, expr: str) -> int:
    return _compile_and_run(
        compiler, tmp_path, PROGRAM % {"base": base, "expr": expr}
    )


@pytest.mark.integration
@pytest.mark.parametrize("base,expr", CASES)
def test_ritz0_oracle(tmp_path, base, expr):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, base, expr) == 10


@pytest.mark.integration
@pytest.mark.parametrize("base,expr", CASES)
def test_ritz1_scales_let_struct_ptr_by_struct_size(ritz1_bin, tmp_path, base, expr):
    """AGAST #1451: `let base: *LB = ...; base ± k` must step by 16 bytes.

    Before the fix `+ (i - 1)` from @arr[0] exited 0: it stepped 8 bytes,
    landing on element 0's `length` field.
    """
    assert _run("ritz1", tmp_path, base, expr) == 10


# Parameter-bound pointers were already correct (registered with the
# parser's TYPE_STRUCT pointee).  Pinned so a fix to the `let` path that
# routes both through one helper cannot regress the arm that worked.
PARAM_PROGRAM = """\
struct LB
    start: i64
    length: i64

fn pick(base: *LB, i: i64) -> i64
    let p: *LB = base + (i - 1)
    return p.start

fn main() -> i32
    var arr: [3]LB
    arr[0].start = 0
    arr[0].length = 0
    arr[1].start = 10
    arr[1].length = 0
    arr[2].start = 20
    arr[2].length = 0
    return pick(@arr[0], 2) as i32
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_param_struct_ptr_still_scaled(ritz1_bin, tmp_path, compiler):
    assert _compile_and_run(compiler, tmp_path, PARAM_PROGRAM) == 10


# Fail-closed.  Inside a generic fn, monomorph does not substitute the type
# name of a `let p: *T` local, so after instantiation with T=u8 the local
# still says "pointer to struct T" — a struct that does not exist.
# get_ptr_elem_size used to answer 8 for that (get_struct_size_by_name's
# miss value): `p + 1` stepped 8 bytes into a [3]u8 and read past the end.
# It must now refuse, naming the operand, and write no output.  (ritz0 gets
# 10; teaching monomorph to substitute the name is a separate ticket — this
# pins that ritz1 errors rather than guessing.)
UNKNOWN_POINTEE_PROGRAM = """\
fn second<T>(x: *T) -> T
    let p: *T = x
    let q: *T = p + 1
    return *q

fn main() -> i32
    var arr: [3]u8
    arr[0] = 1
    arr[1] = 10
    arr[2] = 20
    return second<u8>(@arr[0]) as i32
"""


@pytest.mark.integration
def test_ritz1_unknown_pointee_is_an_error_not_a_guess(ritz1_bin, tmp_path):
    src = tmp_path / "unknown_pointee.ritz"
    src.write_text(UNKNOWN_POINTEE_PROGRAM)
    ll = tmp_path / "unknown_pointee.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode != 0, "ritz1 guessed an element size instead of failing"
    assert "element size of pointee unknown for 'p'" in comp.stderr, comp.stderr
    assert not ll.exists(), "ritz1 wrote output despite an emitter error"
