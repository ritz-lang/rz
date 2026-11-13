"""AGAST #2359: `G + i` on a module-level `*Struct` global strides by
sizeof(Struct) on ritz1 and ritz1_selfhosted.

THE DEFECT

emit_expr_binary sizes a `*S` left operand with deref_pointee_struct_name
(emitter_expr_arith.ritz).  Its global arm read `glob.type_name`, which
global_var_new fills only for a by-value struct global (`var g: S`).  A
`var G: *S` keeps S in `pointee_type_name` (#1908), so the name came back
null, and ptr_arith_elem_size's global arm (#2034) knows only primitive
pointees: the stride fell back to 1 byte.  No diagnostic; `G + 2` was 2
bytes past G.  #1325 / #2034 fixed the primitive-pointee case.  A typed
local (`let b: *P = G; b + i`) was always right, which is how
ref_check.ritz worked around it until this fix.

THE TESTS

  * oracle: each program exits 42 under ritz0, ritz1 and ritz1_selfhosted.
  * IR: ritz1 scales `G + i` by 24 for a 24-byte P.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

STRUCT = """\
struct P
    a: i64
    b: i64
    c: i64

var G: *P = null

"""

# Each body sets G to a 4-element array of P with a = 10*k, b = k, then
# returns 42 if the probe holds.
SETUP = """\
pub fn main() -> i32
    var arr: [4]P
    for k in 0..4
        arr[k].a = (k * 10) as i64
        arr[k].b = k as i64
        arr[k].c = 0
    G = @arr as *P
"""

CASES = {
    # The ticket's shape: the byte distance of `G + 2` from G is 48.
    "distance": "    if ((G + 2) as i64) - (G as i64) != 48\n        return 1\n",
    # A runtime index, not a folded constant.
    "runtime_index": (
        "    let i: i64 = 3\n"
        "    if ((G + i) as i64) - (G as i64) != 72\n        return 1\n"
    ),
    # `-` strides the same way.
    "sub": (
        "    let e: *P = G + 3\n"
        "    if ((e as i64) - ((G - 1) as i64)) != 96\n        return 1\n"
    ),
    # A left-associated chain.
    "chain": "    if ((G + 3 - 1) as i64) - (G as i64) != 48\n        return 1\n",
    # Load through the stepped pointer.
    "deref_field": (
        "    let q: *P = G + 2\n    if q.a != 20 or q.b != 2\n        return 1\n"
    ),
    # A by-value load of `*(G + i)`: steps and loads the same P.
    "deref_value": (
        "    let v: P = *(G + 3)\n    if v.a != 30 or v.b != 3\n        return 1\n"
    ),
    # Store through the stepped pointer, read back through the array.
    "store": (
        "    let q: *P = G + 1\n"
        "    q.c = 7\n"
        "    if arr[1].c != 7 or arr[0].c != 0\n        return 1\n"
    ),
    # A function that walks the global.
    "walk": (
        "    var sum: i64 = 0\n"
        "    for k in 0..4\n"
        "        let q: *P = G + k\n"
        "        sum = sum + q.b\n"
        "    if sum != 6\n        return 1\n"
    ),
}


def _program(case: str) -> str:
    return STRUCT + SETUP + CASES[case] + "    return 42\n"


def _compile(compiler: str, binary, src: Path, ll: Path):
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


def _run(compiler: str, binary, tmp_path: Path, name: str, program: str) -> int:
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    comp = _compile(compiler, binary, src, ll)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, capture_output=True, text=True)
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
@pytest.mark.parametrize("case", sorted(CASES))
def test_global_struct_ptr_strides_by_sizeof(binaries, tmp_path, compiler, case):
    assert (
        _run(compiler, binaries[compiler], tmp_path, f"gsp_{case}", _program(case))
        == 42
    )


@pytest.mark.integration
def test_global_struct_ptr_add_is_scaled_in_ir(ritz1_bin, tmp_path):
    """`G + i` multiplies the index by sizeof(P) = 24 before the byte GEP."""
    src = tmp_path / "gsp_ir.ritz"
    src.write_text(
        STRUCT + "fn at(i: i64) -> *P\n    G + i\n\n" + "pub fn main() -> i32\n    0\n"
    )
    ll = tmp_path / "gsp_ir.ll"
    comp = _compile("ritz1", ritz1_bin, src, ll)
    assert comp.returncode == 0, comp.stderr[-2000:]
    ir = ll.read_text()
    m = re.search(r"define [^\n]*@at\(.*?\n}\n", ir, re.S)
    assert m, ir[:2000]
    assert re.search(r"= mul i64 %[\w.]+, 24\n", m.group(0)), m.group(0)
