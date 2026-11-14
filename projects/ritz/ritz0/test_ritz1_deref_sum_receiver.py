"""A method call on `(*(q + k))`, a deref of a pointer sum (AGAST #3109).

    fn f(q: *S) -> i64
        return (*(q + 1)).get()   # ritz1: "cannot determine receiver type", unlocated

emit_expr_method's deref arm (ritz1/src/emitter_expr_call.ritz) dispatched
only a deref that leaves a `*S` (`(*pp).m()`, #2145).  One that leaves the
struct itself, `(*(q + k))` or `(*q)`, named no receiver type.  LARB R9 (#2175)
rules `*p` a place, so the method runs on the pointee: the operand's pointer is
the receiver, the sum evaluated once.

Each program returns 42 when correct.  ritz0 is the oracle for what a method
reads; for what an `@&` method writes it still mutates a copy (#2175's ritz0
half), so that row is a strict xfail there.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

PRELUDE = """\
var MADE: i32 = 0

struct S
    x: i32
    y: i64

impl S
    fn get(self: S) -> i64
        return self.y
    fn bump(self: @&S) -> i64
        self.y = self.y + 1
        return self.y

fn one() -> i64
    MADE = MADE + 1
    return 1

"""

# name -> (program, {compiler: ticket} for a strict xfail)
PROGRAMS = {
    # The ticket's repro: by-value self, q a param.
    "value_self_param": ("""\
fn f(q: *S) -> i64
    return (*(q + 1)).get()

pub fn main() -> i32
    var a: [2]S
    a[0] = S { x: 1, y: 7 }
    a[1] = S { x: 2, y: 42 }
    return f(@a[0]) as i32
""", {}),
    # q a local, k a variable.
    "value_self_local": ("""\
pub fn main() -> i32
    var a: [3]S
    a[0] = S { x: 1, y: 7 }
    a[1] = S { x: 2, y: 8 }
    a[2] = S { x: 3, y: 42 }
    let q: *S = @a[0]
    let k: i64 = 2
    return (*(q + k)).get() as i32
""", {}),
    # An `@&` self, q a param: its result.
    "mut_ref_self_param": ("""\
fn f(q: *S) -> i64
    return (*(q + 1)).bump()

pub fn main() -> i32
    var a: [2]S
    a[0] = S { x: 1, y: 7 }
    a[1] = S { x: 2, y: 41 }
    return f(@a[0]) as i32
""", {}),
    # An `@&` self, q a local: its result.
    "mut_ref_self_local": ("""\
pub fn main() -> i32
    var a: [2]S
    a[0] = S { x: 1, y: 7 }
    a[1] = S { x: 2, y: 41 }
    let q: *S = @a[0]
    return (*(q + 1)).bump() as i32
""", {}),
    # The sum is evaluated once: `one()` runs a single time.
    "sum_evaluated_once": ("""\
pub fn main() -> i32
    var a: [2]S
    a[0] = S { x: 1, y: 7 }
    a[1] = S { x: 2, y: 41 }
    let q: *S = @a[0]
    let v: i64 = (*(q + one())).get()
    return (v as i32) + MADE
""", {}),
    # R9: the `@&` method writes the element itself, not a copy.
    "mut_ref_self_writes_in_place": ("""\
pub fn main() -> i32
    var a: [2]S
    a[0] = S { x: 1, y: 7 }
    a[1] = S { x: 2, y: 40 }
    let q: *S = @a[0]
    (*(q + 1)).bump()
    (*(q + 1)).bump()
    return a[1].y as i32
""", {"ritz0": 2175}),
    # `(*q).m()` takes the same arm: it works like `(*(q + k)).m()`.
    "bare_deref_param": ("""\
fn f(q: *S) -> i64
    return (*q).get()

pub fn main() -> i32
    var s: S = S { x: 1, y: 42 }
    return f(@s) as i32
""", {}),
}


def _params():
    out = []
    for name in sorted(PROGRAMS):
        gaps = PROGRAMS[name][1]
        for compiler in COMPILERS:
            marks = []
            if compiler in gaps:
                marks.append(pytest.mark.xfail(
                    strict=True,
                    reason=f"AGAST #{gaps[compiler]}: {compiler} runs the method "
                           f"on a copy of `*p`"))
            out.append(pytest.param(compiler, name, marks=marks, id=f"{compiler}-{name}"))
    return out


def _run(request, tmp_path, compiler, program):
    src = tmp_path / "main.ritz"
    src.write_text(PRELUDE + program)
    ll = tmp_path / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        comp = subprocess.run([str(RITZ1_BUILD / compiler), str(src), "-o", str(ll)],
                              cwd=tmp_path, env=env, capture_output=True, text=True,
                              timeout=300)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}")
    exe = tmp_path / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.parametrize("compiler,name", _params())
def test_deref_sum_receiver(request, tmp_path, compiler, name):
    rc = _run(request, tmp_path, compiler, PROGRAMS[name][0])
    assert rc == 42, f"{compiler} {name}: exit {rc}, expected 42"
