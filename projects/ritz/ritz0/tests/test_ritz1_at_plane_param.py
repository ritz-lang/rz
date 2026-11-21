"""AGAST #4313: index through an `@[N][M]T` / `@&[N][M]T` plane param.

Sema types a row of an `@` / `@&` plane through SemaVar.shape (AGAST #4290),
and ritz0 compiles every shape below.  ritz1's emitter kept the plane's shape
in LocalVar.pointee_array_shape only for a `*[N][M]T` param
(bind_nd_pointee_param), so an `@`/`@&` param's index chain was not a plane
pointer's: `p[1][2]` was "a pointer to a multi-dimensional array can't be
indexed", `(*p)[1][2]` was "a whole array is not a value here", a member on the
element was "unhandled EXPR_MEMBER", a method "cannot determine receiver
type", and `@`/`@&` of a row "the address of an element through a pointer to an
array is refused" / "cannot take mutable address".

The fix records the shape for TYPE_REF / TYPE_MUT_REF pointee arrays too, so
the plane-pointer index paths (nd_index_shape -> plane_ptr_shape ->
emit_nd_index_ptr) take the chain and lower it exactly as a `*` plane's.

Each row is one shape from the ticket, run on all three compilers: ritz0 is the
oracle, and the ritz1 binaries must return the same value it does.  The shapes
are the ticket's six repros plus a store through the mutable plane; a cross
product of element types/forms would only repeat the same lowering.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# A two-row, three-column plane filled with 0..5, and one of D whose n is
# 10 + i*10 + j.  Every row goes through a param, so the shape has to come from
# the parameter binding rather than a local array.
HEAD = """\
struct D
    n: i32

impl D
    fn get(self: @D) -> i32
        self.n

fn fill_m(m: @&[2][3]i32)
    var i: i32 = 0
    while i < 2
        var j: i32 = 0
        while j < 3
            m[i][j] = i * 3 + j
            j = j + 1
        i = i + 1

fn fill_d(d: @&[2][3]D)
    var i: i32 = 0
    while i < 2
        var j: i32 = 0
        while j < 3
            d[i][j].n = 10 + i * 10 + j
            j = j + 1
        i = i + 1

"""

MAIN_M = """\
pub fn main() -> i32
    var m: [2][3]i32
    fill_m(@&m)
    {}
"""

MAIN_D = """\
pub fn main() -> i32
    var d: [2][3]D
    fill_d(@&d)
    {}
"""

# name -> (program, exit code).  The values are small enough that the 8-bit
# exit code is the value itself.
PROGRAMS = {
    # a2: `(*p)[i][j]` through a mutable plane, the deref form.
    "deref_index": (HEAD + """\
fn f(p: @&[2][3]i32) -> i32
    (*p)[1][2]
""" + MAIN_M.format("f(@&m)"), 5),
    # a3: `p[i][j]` through a mutable plane, the bare form.
    "index": (HEAD + """\
fn f(p: @&[2][3]i32) -> i32
    p[1][2]
""" + MAIN_M.format("f(@&m)"), 5),
    # a4: a member of a struct element of a dereferenced shared plane.
    "deref_member": (HEAD + """\
fn f(p: @[2][3]D) -> i32
    (*p)[0][1].n
""" + MAIN_D.format("f(@d)"), 11),
    # a5: a method on a struct element of a shared plane.
    "method": (HEAD + """\
fn f(p: @[2][3]D) -> i32
    p[1][2].get()
""" + MAIN_D.format("f(@d)"), 22),
    # a8: `@p[i]` is a row of a mutable plane.
    "addr_row": (HEAD + """\
fn f(p: @&[2][3]i32) -> i32
    let r = @p[1]
    r[2]
""" + MAIN_M.format("f(@&m)"), 5),
    # a9: `@&(*p)[i]` is a mutable row of a mutable plane.
    "addr_mut_row": (HEAD + """\
fn f(p: @&[2][3]i32) -> i32
    let r = @&(*p)[1]
    r[2]
""" + MAIN_M.format("f(@&m)"), 5),
    # And a store: the index chain is a place through the plane, in both forms.
    # m[1][2] = 7 and m[0][1] = 3, read back as 73.
    "plane_store": (HEAD + """\
fn f(p: @&[2][3]i32)
    p[1][2] = 7
    (*p)[0][1] = 3
""" + MAIN_M.format("f(@&m)\n    m[1][2] * 10 + m[0][1]"), 73),
}


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        binary = RITZ1_BIN.parent / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        comp = subprocess.run(
            [str(binary), str(src), "-o", str(ll)],
            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300,
        )
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )

    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_every_compiler_indexes_the_plane_param_identically(request, name, tmp_path):
    """ritz0 is the oracle: ritz1 and ritz1_selfhosted return its value."""
    request.getfixturevalue("ritz1_bin")
    program, want = PROGRAMS[name]
    got = {compiler: _run(compiler, tmp_path, name, program) for compiler in COMPILERS}
    assert got == {compiler: want for compiler in COMPILERS}, (
        f"{name}: ritz0 is the oracle (want {want}); got {got}"
    )
