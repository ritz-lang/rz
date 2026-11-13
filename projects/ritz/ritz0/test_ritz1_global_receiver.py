"""Regression tests for AGAST #2044: a method call whose receiver is a global.

    var g_p: P
    g_p.get()        # ritz0: fine; ritz1: "cannot determine receiver type"

emit_expr_method (ritz1/src/emitter_expr_call.ritz) resolved an EXPR_IDENT
receiver only from locals.  The fix adds a global arm: a struct global's
receiver pointer is `@g` itself (auto-borrowed, so a mutating method writes
the global), and a `*S` global's is loaded from `@g` (like emit_member_ptr's
#1892 arm).

Each program returns 42 when correct and a distinct small code naming the check
that failed otherwise.  ritz0 is the oracle; every case runs at runtime.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

EXPECTED = 42

P_DEF = """\
struct P
    v: i64

impl P
    fn get(self: *P) -> i64
        self.v
    fn add(self: *P, n: i64)
        self.v = self.v + n
    fn plus(self: *P, n: i32) -> i32
        (self.v as i32) + n

"""

PROGRAMS = {
    # The ticket's repro: a read through a struct global.
    "struct_global_read": P_DEF
    + """\
var g_p: P

pub fn main() -> i32
    g_p.v = 42
    return g_p.get() as i32
""",
    # A mutating method writes the global itself, not a copy.
    "struct_global_mutate": P_DEF
    + """\
var g_p: P

pub fn main() -> i32
    g_p.v = 30
    g_p.add(10)
    g_p.add(2)
    if g_p.v != 42
        return 1
    return g_p.get() as i32
""",
    # Narrow argument and result through a struct global receiver.
    "struct_global_args": P_DEF
    + """\
var g_p: P

pub fn main() -> i32
    g_p.v = 40
    return g_p.plus(2)
""",
    # A `*P` global: the pointer is loaded from @g and dispatched on.
    "ptr_global": P_DEF
    + """\
var g_q: *P

pub fn main() -> i32
    var p: P = P { v: 30 }
    g_q = @p
    g_q.add(12)
    if p.v != 42
        return 1
    return g_q.get() as i32
""",
    # A local can't take a global's name (AGAST #2407): test_local_takes_module_name.py.
}


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)]
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
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link ({name}):\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    assert _run("ritz0", tmp_path, name, PROGRAMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_global_receiver(ritz1_bin, tmp_path, name):
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
