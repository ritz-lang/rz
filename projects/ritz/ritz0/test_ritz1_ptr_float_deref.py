"""AGAST #2022: ritz1 lowers `*p` on a `*f32` / `*f64` to `load float` /
`load double`.

THE DEFECT

get_expr_type types `*p` as the pointee (F32 / F64), but OP_DEREF's
emission (ritz1/src/emitter_expr_arith.ritz) only knew integer widths and
fell to `load i64`.  `*p != x` then emitted `fcmp one float %<i64>`, which
clang rejects ("defined with type 'i64' but expected 'float'").  `*p = v`
likewise stored `i64 %float` (emitter_stmt.ritz deref store).

THE TESTS

  * oracle: each program runs to exit 42 under ritz0, ritz1 and
    ritz1_selfhosted (ritz0 already lowers float derefs).
  * IR shape: ritz1 loads `float` / `double` for the deref, never i64.

The ritz0/test/test_issue_ptr_float_deref.ritz repro runs the same cases
through the regression matrix.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# Covers `*p`, `*(p + i)`, a param, a global, a compare, a binop and a
# store-then-reload that would expose a too-wide load.
PROG = """\
var g: *{t} = null

fn first(p: *{t}) -> {t}
    *p

fn at(p: *{t}, i: i64) -> {t}
    *(p + i)

pub fn main() -> i32
    var a: [3]{t} = [3.5, -1.25, 6.0]
    let p: *{t} = @a as *{t}
    let x0: {t} = 3.5
    let x1: {t} = -1.25
    let x2: {t} = 6.0
    if *p != x0
        return 1
    if *(p + 1) != x1
        return 2
    if *(p + 2) != x2
        return 3
    if *(p + 1) * 2.0 != -2.5
        return 4
    let y: {t} = *(p + 2) + *p
    let want: {t} = 9.5
    if y != want
        return 5
    if first(p) != x0
        return 6
    if at(p, 2) != x2
        return 7
    g = p
    if *g != x0
        return 8
    # `*(g + 1)` omitted: a global *T strides by i8 (AGAST #2034).
    *p = 0.5
    let half: {t} = 0.5
    if *p != half
        return 10
    if *(p + 1) != x1
        return 11
    return 42
"""

# The ticket's repro, verbatim.
REPRO = """\
pub fn main() -> i32
    var a: [2]f32 = [3.5, 1.0]
    let p: *f32 = @a as *f32
    let x: f32 = 3.5
    if *p != x
        return 1
    return 42
"""


def _compile(compiler: str, binary: Path, src: Path, ll: Path):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0(
            [str(src), "-o", str(ll)], cwd=src.parent, env=env, timeout=300
        )
    return subprocess.run(
        [str(binary), str(src), "-o", str(ll)],
        cwd=src.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


def _run(compiler: str, binary: Path, tmp_path: Path, name: str, program: str) -> int:
    """Compile, link and run `program`; return its exit code."""
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    comp = _compile(compiler, binary, src, ll)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.fixture(scope="session")
def binaries(ritz1_bin):
    """{compiler: binary}.  The gate builds ritz1_selfhosted before pytest;
    never skip (#1327)."""
    assert SELFHOSTED_BIN.exists(), (
        f"{SELFHOSTED_BIN} missing; run `make -C ritz1 bootstrap`"
    )
    return {"ritz0": None, "ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("t", ["f32", "f64"])
def test_ptr_float_deref_runs(binaries, tmp_path, compiler, t):
    prog = PROG.format(t=t)
    assert _run(compiler, binaries[compiler], tmp_path, f"pfd_{t}", prog) == 42


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_ticket_repro(binaries, tmp_path, compiler):
    assert _run(compiler, binaries[compiler], tmp_path, "pfd_repro", REPRO) == 42


@pytest.mark.integration
@pytest.mark.parametrize("t,llty", [("f32", "float"), ("f64", "double")])
def test_ptr_float_deref_ir_loads_float(ritz1_bin, tmp_path, t, llty):
    """`first(p)` is a bare `*p`: its body must load the float type."""
    src = tmp_path / f"pfd_ir_{t}.ritz"
    src.write_text(PROG.format(t=t))
    ll = tmp_path / f"pfd_ir_{t}.ll"
    comp = _compile("ritz1", ritz1_bin, src, ll)
    assert comp.returncode == 0, comp.stderr[-2000:]
    ir = ll.read_text()
    m = re.search(r"define [^\n]*@first\(.*?\n}\n", ir, re.S)
    assert m, ir[:2000]
    body = m.group(0)
    assert f"load {llty}, ptr" in body, body
