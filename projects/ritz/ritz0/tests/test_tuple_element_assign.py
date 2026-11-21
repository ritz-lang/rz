"""AGAST #2283: `p.0 = v` stores a tuple's element, as `s.f = v` does a field.

THE DEFECT

ritz0's AssignStmt only knew named structs, so `var p = (1, 2); p.0 = 40`
died with `ValueError: Cannot determine struct type for field assignment`.
Both of its routes needed the tuple case: the place addressed through a
pointer (`p.0`, `s.pair.0`, `r.0` with `r = @&p`) and the one addressed as
a value (`q.0.1`, a tuple inside a tuple).

Dropping the old element and refusing a `let` tuple are covered by
`tuple_element_assigned_*` in test_ownership_free_count.py and
`*-tuple-elem` in test_let_immutability.py. This file pins that the store
lands where a read of the element finds it, on all three compilers.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# name -> program; each returns 42 when the store landed in the element.
CASES = {
    "local": """\
pub fn main() -> i32
    var p = (1, 2)
    p.0 = 40
    return (p.0 + p.1) as i32
""",
    "nested": """\
pub fn main() -> i32
    var q = ((1, 2), 3)
    q.0.1 = 39
    return (q.0.1 + q.1) as i32
""",
    "struct_field": """\
struct S
    pair: (i64, i64)

pub fn main() -> i32
    var s = S { pair: (1, 2) }
    s.pair.1 = 41
    return (s.pair.0 + s.pair.1) as i32
""",
    "through_borrow": """\
pub fn main() -> i32
    var p = (1, 2)
    var r = @&p
    r.0 = 40
    return (p.0 + p.1) as i32
""",
}


def _params():
    return [pytest.param(c, n, id=f"{c}-{n}") for n in sorted(CASES) for c in COMPILERS]


def _compile(compiler, src, ll, cwd):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=cwd, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run(
        [str(binary), str(src), "-o", str(ll)],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


@pytest.mark.integration
@pytest.mark.parametrize("compiler,name", _params())
def test_tuple_element_assign(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    src = tmp_path / "main.ritz"
    src.write_text(CASES[name])
    ll = tmp_path / "main.ll"
    comp = _compile(compiler, src, ll, tmp_path)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-2000:]}"
    rc = subprocess.run(
        [str(exe)], capture_output=True, timeout=60, check=False
    ).returncode
    assert rc == 42, f"{compiler} {name}: exit {rc}, expected 42"
