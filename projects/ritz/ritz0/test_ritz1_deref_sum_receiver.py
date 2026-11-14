"""A method call on `(*(q + k))`, a deref of a pointer sum (AGAST #3109).

    fn f(q: *S) -> i64
        return (*(q + 1)).get()   # ritz1: "cannot determine receiver type", unlocated

emit_expr_method's deref arm (ritz1/src/emitter_expr_call.ritz) dispatched
only a deref that leaves a `*S` (`(*pp).m()`, #2145).  One that leaves the
struct itself, `(*(q + k))` or `(*q)`, named no receiver type.  LARB R9 (#2175)
rules `*p` a place, so the method runs on the pointee: the operand's pointer is
the receiver, the sum evaluated once.

Each program returns 42 when correct, on all three compilers.  ritz0 ran a
mutating method on a copy of `*p`, so the write was lost (#2175): the
`*_in_place` rows read the pointee back after the call.  A by-value `self`
still copies, and `@T` is still no `@&T` (§3.2).
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
    fn poke(self: *S, n: i64)
        self.y = self.y + n
    fn peek(self: @S) -> i64
        return self.y

fn one() -> i64
    MADE = MADE + 1
    return 1

fn at(q: *S) -> *S
    MADE = MADE + 1
    return q

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
""", {}),
    # LARB R9 (#2175): `(*p).m()` is `p.m()`.  A `self: *S` method on a `*S`.
    "ptr_self_in_place": ("""\
pub fn main() -> i32
    var s: S = S { x: 1, y: 40 }
    let p: *S = @s
    (*p).poke(2)
    return s.y as i32
""", {}),
    # An `@&S` method, `p` a `*S` and an `@&S`.
    "mut_ref_self_bare_deref_in_place": ("""\
pub fn main() -> i32
    var s: S = S { x: 1, y: 40 }
    let p: *S = @s
    (*p).bump()
    (*p).bump()
    return s.y as i32
""", {}),
    "mut_ref_through_mut_ref_in_place": ("""\
pub fn main() -> i32
    var s: S = S { x: 1, y: 40 }
    let p: @&S = @&s
    (*p).bump()
    (*p).bump()
    return s.y as i32
""", {}),
    # Two levels: `(**pp)` is the struct.
    "double_deref_in_place": ("""\
pub fn main() -> i32
    var s: S = S { x: 1, y: 40 }
    var p: *S = @s
    let pp: **S = @p
    (**pp).poke(2)
    return s.y as i32
""", {}),
    # A call's pointer: the pointee changes and the call runs once.
    "call_result_in_place": ("""\
pub fn main() -> i32
    var s: S = S { x: 1, y: 40 }
    (*at(@s)).poke(1)
    return (s.y as i32) + MADE
""", {}),
    # Reads: an `@S` self, and `var c = *p`, which is a copy.
    "shared_self_read": ("""\
pub fn main() -> i32
    var s: S = S { x: 1, y: 42 }
    let p: *S = @s
    return (*p).peek() as i32
""", {}),
    "let_deref_is_a_copy": ("""\
pub fn main() -> i32
    var s: S = S { x: 1, y: 42 }
    let p: *S = @s
    var c = *p
    c.y = 1
    c.poke(1)
    return (s.y as i32) + (c.y as i32) - 2
""", {}),
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


def _compile(request, tmp_path, compiler, program):
    """Compile PRELUDE + `program` to main.ll: (completed process, ll path)."""
    src = tmp_path / "main.ritz"
    src.write_text(PRELUDE + program)
    ll = tmp_path / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300), ll
    request.getfixturevalue("ritz1_bin")
    return subprocess.run([str(RITZ1_BUILD / compiler), str(src), "-o", str(ll)],
                          cwd=tmp_path, env=env, capture_output=True, text=True,
                          timeout=300), ll


def _run(request, tmp_path, compiler, program):
    comp, ll = _compile(request, tmp_path, compiler, program)
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


# §3.2: `(*p).m()` is `p.m()`, so an `@&S` method on an `@S` is refused, in
# the same words and place on all three.
SHARED_INTO_MUT = """\
pub fn main() -> i32
    var s: S = S { x: 1, y: 40 }
    let p: @S = @s
    return (*p).bump() as i32
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_mut_ref_self_on_shared_deref_refused(request, tmp_path, compiler):
    comp, _ = _compile(request, tmp_path, compiler, SHARED_INTO_MUT)
    out = comp.stdout + comp.stderr
    line = PRELUDE.count("\n") + 4
    assert comp.returncode != 0, f"{compiler} accepted it:\n{out}"
    assert f"main.ritz:{line}:13: " in out and "doesn't fit an `@&T` slot" in out, out
