"""Regression tests for AGAST #2063: a `*bool` must have one pointee layout in
ritz1, whatever it points at.

ritz0 lays every bool out as `i1` (one byte in memory): locals, arrays and
struct fields alike. ritz1 gave a bool struct field (and a `[N]bool` field)
an `i1` but a local `[N]bool` i64 slots ("bool keeps its i64 slot",
local_array_elem_llvm), so indexing through a `*bool` was wrong for one of
the two:

* a local `*bool` into a bool struct-field array (`q = @s.flags[0]`,
  `q[2] = true`) strode 8 bytes and stored an i64, 16 bytes past the end of
  a 5-byte struct (the ticket's repro: SIGSEGV);
* a `*bool` FIELD into a local `[4]bool` was kept fail-closed (#2053): an
  `i1` stride would hit byte 2 of element 0 of the i64 slots;
* `*(p + k)` strides by ptr_pointee_size(bool) = 1, also wrong for a local
  array laid out in i64 slots.

A local / global `[N]bool` is now `[N x i1]`, like a field, so every
`*bool` strides by one byte. Every program returns 3 on success; ritz0 is
the oracle.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
# Build product, not a tracked file; see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

CASES = {
    # The ticket's repro: a local `*bool` into a bool struct-field array.
    "local_ptr_into_field_array": """\
struct S
    flags: [4]bool
    after: u8

pub fn main() -> i32
    var s: S
    s.after = 3
    var q: *bool = @s.flags[0]
    q[2] = true
    if s.flags[2] and not s.flags[1] and not s.flags[3] and q[2] and not q[0]
        return s.after as i32
    return 100
""",
    # The inverse, formerly pinned fail-closed
    # (test_ritz1_member_store_fail_closed.py::nested_bool_ptr_field_index):
    # a nested `*bool` field into a local `[4]bool`.
    "nested_ptr_field_into_local_array": """\
struct B
    data: *bool

struct A
    b: B

pub fn main() -> i32
    var buf: [4]bool
    buf[0] = false
    buf[1] = false
    buf[2] = false
    buf[3] = false
    var a: A
    a.b.data = @buf[0]
    a.b.data[2] = true
    if buf[2] and not buf[1] and not buf[3] and not buf[0] and a.b.data[2]
        return 3
    return 100
""",
    # A direct `*bool` field into a local `[N]bool`, read and written both
    # ways, plus through a `*R` param.
    "ptr_field_into_local_array": """\
struct R
    head: u8
    p: *bool
    tail: i64

fn set(r: *R, i: i64)
    r.p[i] = true

pub fn main() -> i32
    var buf: [4]bool = [false, true, false, false]
    var r: R = R { head: 1, p: @buf[0], tail: 1 }
    r.p[3] = true
    set(@r, 2)
    r.p[1] = false
    if buf[3] and buf[2] and not buf[1] and not buf[0] and r.p[3]
        return r.head as i32 + r.tail as i32 + 1
    return 100
""",
    # `*(p + k)` over a local `[N]bool` (ptr_pointee_size(bool) == 1).
    "ptr_offset_into_local_array": """\
pub fn main() -> i32
    var buf: [4]bool = [true, false, false, false]
    var p: *bool = @buf[0]
    *(p + 3) = true
    *(p + 1) = *(p + 0)
    *p = false
    if buf[3] and buf[1] and not buf[2] and not buf[0] and *(p + 3)
        return 3
    return 100
""",
    # A `*bool` param indexing a local array, and a struct-field array, at
    # the same stride; the array element feeds calls, returns and phis.
    "param_ptr_both_layouts": """\
struct S
    lead: u8
    flags: [3]bool
    after: u8

fn count(p: *bool, n: i64) -> i32
    var c: i32 = 0
    var i: i64 = 0
    while i < n
        if p[i]
            c = c + 1
        i = i + 1
    return c

fn first(p: *bool) -> bool
    return p[0]

fn pick(b: bool) -> i32
    if b
        return 1
    return 0

pub fn main() -> i32
    var loc: [3]bool = [true, false, true]
    var s: S = S { lead: 7, flags: [false, true, false], after: 9 }
    let both: bool = loc[0] and loc[2]
    let either: bool = loc[1] or s.flags[1]
    if loc[0] == loc[2] and loc[0] != loc[1] and both and either and first(@loc[0]) and not first(@s.flags[0])
        return count(@loc[0], 3) + count(@s.flags[0], 3) + pick(loc[2]) - 1 + s.lead as i32 - 7 + s.after as i32 - 9
    return 100
""",
    # A global `[N]bool` through a `*bool`, and stored to directly.
    "global_array": """\
var G: [4]bool

pub fn main() -> i32
    var p: *bool = @G[0]
    p[1] = true
    *(p + 3) = true
    G[2] = true
    G[2] = G[0]
    if G[1] and G[3] and not G[0] and not G[2] and p[3]
        return 3
    return 100
""",
    # A whole local `[N]bool` copied into a bool-array field: refused
    # (field_elem_layout_differs) while the layouts differed.
    "local_array_copy_to_field": """\
struct W
    pre: u8
    vals: [3]bool
    post: u8

pub fn main() -> i32
    var a: [3]bool = [true, false, true]
    var w: W
    w.pre = 1
    w.post = 1
    w.vals = a
    if w.vals[0] and not w.vals[1] and w.vals[2]
        return w.pre as i32 + w.post as i32 + 1
    return 100
""",
    # A local array loop write / read / flip keeps every element.
    "local_array_rw": """\
pub fn main() -> i32
    var a: [5]bool
    var i: i64 = 0
    while i < 5
        a[i] = i % 2 == 1
        i = i + 1
    var c: i32 = 0
    i = 0
    while i < 5
        if a[i]
            c = c + 1
        i = i + 1
    a[4] = not a[4]
    if a[4]
        c = c + 1
    return c
""",
}


def _run(compiler: str, ritz1_bin, tmp_path: Path, name: str) -> int:
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    src = work / "main.ritz"
    src.write_text(CASES[name])
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=work, env=env, timeout=300)
    else:
        comp = subprocess.run(
            [str(ritz1_bin), str(src), "-o", str(ll)],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = work / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=work, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", None, tmp_path, name) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_bool_ptr_one_layout(ritz1_bin, tmp_path, name):
    """AGAST #2063. Before the fix: i64 strides through `*bool` / fail-closed."""
    assert _run("ritz1", ritz1_bin, tmp_path, name) == 3
