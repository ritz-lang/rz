"""Regression tests for AGAST #2053: ritz1 must load and store through a
struct field whose type is a pointer to a float or bool (`p: *f64`,
`p: *f32`, `p: *bool`) at the pointee's own width.

Before the fix ritz1 lowered `*r.p` to `load i8, ptr` and `*r.p = v` to
`store i64 %double, ptr`: the member-pointee lookups (get_member_pointee_type
and ptr_field_elem_kind, emitter_core.ritz) knew integer pointees only, so a
float pointee fell to their `u8` / `i64` defaults. The IR did not even pass
llc (`'%.12' defined with type 'i64' but expected 'double'`).

Each program is instantiated for f64 and f32 (and bool where the program
makes sense for it) and returns 3 on success. ritz0 is the oracle.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
# Build product, not a tracked file; see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

# `T` is the float pointee.

# The ticket's repro: read and write through the field (1.5 + 1.5 = 3).
FLOAT_REPRO = """\
struct R
    p: *T

pub fn main() -> i32
    var x: T = 1.5
    var r: R = R { p: @x }
    *r.p = *r.p + 1.5
    return x as i32
"""

# Through a pointer to the outer struct, and a read whose value is the exit
# code: x goes 0.5 -> 1.75 (in bump) -> 3.0 (in main).
FLOAT_VIA_PTR = """\
struct R
    p: *T

fn bump(r: *R)
    *r.p = *r.p + 1.25

fn get(r: *R) -> T
    return *r.p

pub fn main() -> i32
    var x: T = 0.5
    var r: R = R { p: @x }
    bump(@r)
    *r.p = *r.p + 1.25
    return get(@r) as i32
"""

# The float pointer field sits between fields of other widths, and is
# indexed / offset (`r.p[i]`, `*(r.p + i)`): both must stride by the float.
FLOAT_INDEX = """\
struct R
    head: u8
    p: *T
    tail: i64

pub fn main() -> i32
    var a: [3]T = [0.25, 0.5, 0.75]
    var r: R = R { head: 1, p: @a[0], tail: 1 }
    r.p[1] = r.p[1] + 0.5
    *(r.p + 2) = *(r.p + 2) + 0.25
    let s: T = r.p[0] + r.p[1] + *(r.p + 2) - 1.25
    return s as i32 + r.head as i32 + r.tail as i32
"""

FLOAT_PROGRAMS = {
    "repro": FLOAT_REPRO,
    "via_ptr": FLOAT_VIA_PTR,
    "index": FLOAT_INDEX,
}

# A `*bool` field pointing at a bool field of another struct, an `i1` packed
# between neighbours, and at a bool local (an i64 slot in ritz1): stored
# through, flipped via `*R`, read back. An i64 store through the field
# clobbers `c` / `after` (exit 0 before the fix). Indexing through a `*bool`
# field stays fail-closed (#2063; test_ritz1_member_store_fail_closed.py).
BOOL_PROGRAM = """\
struct S
    before: bool
    b: bool
    c: bool
    after: u8

struct R
    head: u8
    p: *bool
    tail: i64

fn flip(r: *R)
    *r.p = not *r.p

pub fn main() -> i32
    var s: S = S { before: false, b: false, c: false, after: 1 }
    var r: R = R { head: 1, p: @s.b, tail: 1 }
    *r.p = true
    flip(@r)
    flip(@r)
    var lb: bool = true
    var l: R = R { head: 0, p: @lb, tail: 0 }
    flip(@l)
    if *r.p and s.b and not s.c and not s.before and not *l.p and not lb
        return s.after as i32 + r.head as i32 + r.tail as i32
    return 100
"""

# The `*bool` deref arms are shared with plain pointers, so a local `*bool`
# into an `i1` field stops overwriting the field after it too (exit 0 before).
LOCAL_BOOL_PROGRAM = """\
struct S
    a: bool
    b: bool
    c: u8

pub fn main() -> i32
    var s: S = S { a: false, b: false, c: 3 }
    var q: *bool = @s.a
    *q = true
    if *q and s.a and not s.b
        return s.c as i32
    return 100
"""

CASES = {
    f"{name}_{ty}": prog.replace("T", ty)
    for name, prog in FLOAT_PROGRAMS.items()
    for ty in ("f64", "f32")
} | {
    "bool": BOOL_PROGRAM,
    "local_bool": LOCAL_BOOL_PROGRAM,
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
    link = subprocess.run(link_cmd, cwd=work, capture_output=True, text=True)
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
def test_ritz1_float_bool_ptr_field(ritz1_bin, tmp_path, name):
    """AGAST #2053. Before the fix: `load i8` / `store i64 %double` -> llc error."""
    assert _run("ritz1", ritz1_bin, tmp_path, name) == 3
