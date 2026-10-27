"""AGAST #1908: ritz1 lowers `p[i].field` and `@p[i]` where `p` is a `*Struct`.

ritzunit's runner (`slots[i].pid = 0`, `outcomes[n].done`) and JUnit
reporter (`g_junit_results[n].name = ...`, a `*JunitTestResult` global)
index a struct pointer and take a field. ritz1 handled `arr[i].field` for
arrays and Vecs, and `(p + i).field`, but not an index on a pointer: both
the read and the store were "ritz1 cannot emit: unhandled EXPR_MEMBER", so
ritzunit could not be built by ritz1 at all.

Each program is compiled by ritz0 (the oracle) and ritz1, linked and run;
the exit codes must match.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

pytestmark = pytest.mark.integration

STRUCT = """\
struct Slot
    pid: i64
    fd: i32
    done: u8
"""

PARAM = STRUCT + """
fn fill(slots: *Slot, n: i64)
    for i in 0..n
        slots[i].pid = 10 + i
        slots[i].fd = (i * 2) as i32
        slots[i].done = 1

fn total(slots: *Slot, n: i64) -> i64
    var t: i64 = 0
    for i in 0..n
        if slots[i].done == 1
            t = t + slots[i].pid + slots[i].fd as i64
    t

pub fn main() -> i32
    var buf: [3]Slot
    fill(@buf[0], 3)
    total(@buf[0], 3) as i32
"""

LOCAL = STRUCT + """
pub fn main() -> i32
    var buf: [4]Slot
    var p: *Slot = @buf[0]
    var k: i64 = 3
    p[k].pid = 40
    p[k - 1].fd = 2
    (p[k].pid + p[2].fd as i64) as i32
"""

GLOBAL = STRUCT + """
var g_slots: *Slot = 0 as *Slot
var g_count: i32 = 0

fn record(pid: i64)
    g_slots[g_count].pid = pid
    g_slots[g_count].done = 1
    g_count = g_count + 1

pub fn main() -> i32
    var buf: [4]Slot
    g_slots = @buf[0]
    record(20)
    record(22)
    if g_slots[1].done != 1
        return 1
    (g_slots[0].pid + g_slots[1].pid) as i32
"""

# `@p[i]` over `*Slot` must step one Slot per index. ritz1 used a byte stride
# (`getelementptr i8`), so `@tests[1]` in ritzunit pointed 1 byte into the
# first entry and every test after the first had a garbage name.
ADDR_LOCAL = STRUCT + """
fn second(slots: *Slot) -> *Slot
    @slots[1]

pub fn main() -> i32
    var buf: [3]Slot
    buf[1].pid = 30
    buf[2].pid = 12
    let p: *Slot = @buf[0]
    let q: *Slot = @p[2]
    let s: *Slot = second(p)   # not `second(p).pid`: that is #1647
    (s.pid + q.pid) as i32
"""

# `@g[i]` with `var g: *Slot` indexes the pointee. ritz1 GEPed off the
# global's own storage (`getelementptr i8, ptr @g`).
ADDR_GLOBAL = STRUCT + """
var g_slots: *Slot = 0 as *Slot

pub fn main() -> i32
    var buf: [3]Slot
    buf[2].pid = 42
    g_slots = @buf[0]
    let r: *Slot = @g_slots[2]
    r.pid as i32
"""

PROGRAMS = {"param": (PARAM, 10 + 11 + 12 + 0 + 2 + 4), "local": (LOCAL, 42),
            "global": (GLOBAL, 42), "addr_local": (ADDR_LOCAL, 42),
            "addr_global": (ADDR_GLOBAL, 42)}


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        comp = subprocess.run([str(RITZ1_BIN), str(src), "-o", str(ll)], cwd=tmp_path,
                              env=env, capture_output=True, text=True, timeout=300)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}")
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", "-Wno-override-module", str(ll), "-o", str(exe), "-nostdlib", "-no-pie"]
    if compiler == "ritz1":
        link_cmd.insert(1, str(RITZ_START))
    link = subprocess.run(link_cmd, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler} IR did not link ({name}):\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    program, expected = PROGRAMS[name]
    assert _run("ritz0", tmp_path, name, program) == expected


@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_ptr_index_member(ritz1_bin, tmp_path, name):
    program, expected = PROGRAMS[name]
    assert _run("ritz1", tmp_path, name, program) == expected
