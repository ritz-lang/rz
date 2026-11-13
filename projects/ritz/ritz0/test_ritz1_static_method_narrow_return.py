"""AGAST #1962: ritz1 static method `T.m(...)` returning a narrow int.

ritz1's value model carries every integer as an i64 register; a call whose
callee returns i8/i16/i32/bool is widened back to i64 right after the call.
The instance-method and direct-call paths did that, but the static-method arm
of `emit_expr_method` returned the raw `call i32` register, so a consumer
emitted `trunc i64 %.5 to i32` (or `icmp ... i64 %.5`) on an i32 value and
clang rejected the IR.

Each program below is built by ritz0 (the oracle), ritz1 and ritz1_selfhosted,
linked and run; all three must exit with the same expected code.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration


# The ticket's repro, verbatim.
REPRO = """\
struct C
    z: i32
fn take_c(p: @&C) -> i32
    p.z = p.z + 1
    return p.z
impl C
    fn get(c: @&C) -> i32
        return take_c(c)
fn main() -> i32
    var c: C = C { z: 5 }
    return C.get(@&c)
"""

# Result used in a comparison and in arithmetic, not just returned.  The
# param is i64 on purpose: narrowing a literal ARG into an i32 param is the
# other half of the static arm's width bugs, tracked by AGAST #1733.
COMPARE = """\
struct S
    k: i32
impl S
    fn of(n: i64) -> i32
        return (n + 1) as i32
fn main() -> i32
    if S.of(3) != 4
        return 1
    let x: i32 = S.of(10) * 2
    return x
"""

# Each narrow width, signed results kept negative to catch zext-for-sext.
WIDTHS = """\
struct W
    k: i32
impl W
    fn i8v() -> i8
        return -3 as i8
    fn u8v() -> u8
        return 200 as u8
    fn i16v() -> i16
        return -300 as i16
    fn u16v() -> u16
        return 60000 as u16
    fn u32v() -> u32
        return 4000000000 as u32
    fn yes() -> bool
        return true
fn main() -> i32
    if W.i8v() as i64 != -3
        return 1
    if W.u8v() as i64 != 200
        return 2
    if W.i16v() as i64 != -300
        return 3
    if W.u16v() as i64 != 60000
        return 4
    if W.u32v() as i64 != 4000000000
        return 5
    if not W.yes()
        return 6
    return 42
"""

CASES = {
    "repro": (REPRO, 6),
    "compare": (COMPARE, 22),
    "widths": (WIDTHS, 42),
}


def _build_and_run(compiler, tmp_path, src):
    path = tmp_path / "t.ritz"
    path.write_text(src)
    ll = tmp_path / f"t_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        proc = run_ritz0([str(path), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=tmp_path, env=env,
                              capture_output=True, text=True, timeout=300)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and ll.exists(), f"{compiler} failed to compile:\n{out[-2000:]}"
    exe = tmp_path / f"t_{compiler}"
    link_cmd = ["clang", "-Wno-override-module", str(ll), "-o", str(exe), "-nostdlib", "-no-pie"]
    if compiler != "ritz0":
        link_cmd.insert(1, str(RITZ_START))
    link = fast_link.clang(link_cmd, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler} IR did not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], timeout=60).returncode


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("case", sorted(CASES))
def test_static_method_narrow_return(compiler, case, tmp_path):
    src, want = CASES[case]
    assert _build_and_run(compiler, tmp_path, src) == want
