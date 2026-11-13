"""Regression tests for AGAST #2062: an integer-valued initializer into a
float local (`var x: f64 = 3`, `var x: f32 = n`) must convert to the slot's
float width, as ritz0 does.

Before the fix ritz1 exited 0 but emitted `store double %<i64>` /
`store float %<i64>`, which clang rejects (`'%.2' defined with type 'i64'
but expected 'double'`). emit_var_decl's F32 / F64 store arms assumed the
init was already a float.

`*p = 3` through a `*f64` (emit_assign's deref arm) had the same gap and is
covered here. AGAST #2065 extends it to the sibling store paths that lower
through emit_field_elem_narrow / emit_assign's local arm: struct-literal float
fields (`R { a: 3 }`), `r.a = 3`, `p[i] = 3`, a plain `x = 3`, and a u64
source (sitofp, as ritz0 does).

Each program is instantiated for f64 and f32 and returns 3 on success.
ritz0 is the oracle.
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

# `T` is the float type.

# The ticket's repro.
LITERAL = """\
pub fn main() -> i32
    var x: T = 3
    return x as i32
"""

# A negative literal and an integer expression: -1 + (2 * 2) = 3.
EXPR = """\
pub fn main() -> i32
    let a: T = -1
    let b: T = 2 * 2
    return (a + b) as i32
"""

# Integer-typed locals of several widths, including one that is not a
# literal at all: sitofp, not a bit-reinterpretation.
INT_LOCAL = """\
pub fn main() -> i32
    let n: i32 = 1
    let m: i64 = 1
    let k: u8 = 1
    var x: T = n
    let y: T = m
    let z: T = k
    return (x + y + z) as i32
"""

# The converted value is a real float: arithmetic on it stays fractional
# (3 / 2 = 1.5, 1.5 * 2 = 3), which an integer slot would not give.
FRACTIONAL = """\
pub fn main() -> i32
    var x: T = 3
    x = x / 2.0
    return (x * 2.0) as i32
"""

# An `if` with an integer arm is converted per-arm by the float hint
# (#1946); it must not be sitofp'd a second time as a whole.  (`match` is
# covered by test_ritz1_match_float_arms.py's annotated_int case.)
ARM_HINT = """\
fn pick(c: bool) -> i32
    let a: T = if c then 2 else 0.5
    return a as i32

pub fn main() -> i32
    return pick(true) + 1
"""

# `*p = 3` through a `*T` (emit_assign deref arm).
PTR_STORE = """\
pub fn main() -> i32
    var x: T = 0.5
    let p: *T = @x
    *p = 3
    return x as i32
"""

# A float-returning method on an rvalue struct receiver is already a float
# register, though get_expr_type falls back to i64 for it: it must not be
# sitofp'd (the gate's test_issue_method_autoborrow_rvalue regression).
RVALUE_METHOD = """\
struct Pt
    x: T

impl Pt
    fn scale(self: @Pt, f: T) -> T
        self.x * f

pub fn main() -> i32
    let a = Pt { x: 0.5 as T }.scale(2.0 as T)
    var b: T = Pt { x: 0.75 as T }.scale(2.0 as T)
    var c: T = 0.5
    let p: *T = @c
    *p = Pt { x: 0.25 as T }.scale(2.0 as T)
    return (a + b + c) as i32
"""

# AGAST #2065: struct-literal float field (`R { a: 3 }`).
STRUCT_LIT = """\
struct R
    a: T
    b: T

pub fn main() -> i32
    let n: i32 = 2
    let r: R = R { a: 1, b: n }
    return (r.a + r.b) as i32
"""

# AGAST #2065: field assign (`r.a = 3`), and through a pointer (`q.a = 3`).
FIELD_ASSIGN = """\
struct R
    a: T
    b: T

pub fn main() -> i32
    var r: R = R { a: 0.5, b: 0.5 }
    r.a = 1
    let q: *R = @r
    q.b = 2
    return (r.a + r.b) as i32
"""

# AGAST #2065: indexed store through a `*T` (`p[1] = 3`) and into a local
# `[N]T` array.
INDEX_STORE = """\
pub fn main() -> i32
    var arr: [2]T = [0.5, 0.5]
    let p: *T = @arr[0]
    p[1] = 2
    arr[0] = 1
    return (arr[0] + arr[1]) as i32
"""

# AGAST #2065: plain local reassign (`x = 3`).
LOCAL_ASSIGN = """\
pub fn main() -> i32
    var x: T = 0.5
    x = 3
    return x as i32
"""

# AGAST #2065: a global float reassigned from an integer.
GLOBAL_ASSIGN = """\
var g: T

pub fn main() -> i32
    g = 3
    return g as i32
"""

# AGAST #2065: a u64 source is sitofp'd too (ritz0 does; values here fit).
U64_SOURCE = """\
struct R
    a: T

pub fn main() -> i32
    let u: u64 = 1
    var r: R = R { a: u }
    var x: T = 0.5
    x = u
    r.a = r.a + x + (u as T)
    return r.a as i32
"""

PROGRAMS = {
    "struct_lit": STRUCT_LIT,
    "field_assign": FIELD_ASSIGN,
    "index_store": INDEX_STORE,
    "local_assign": LOCAL_ASSIGN,
    "global_assign": GLOBAL_ASSIGN,
    "u64_source": U64_SOURCE,
    "rvalue_method": RVALUE_METHOD,
    "literal": LITERAL,
    "expr": EXPR,
    "int_local": INT_LOCAL,
    "fractional": FRACTIONAL,
    "arm_hint": ARM_HINT,
    "ptr_store": PTR_STORE,
}

CASES = {
    f"{name}_{ty}": prog.replace("T", ty)
    for name, prog in PROGRAMS.items()
    for ty in ("f64", "f32")
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
def test_ritz1_int_init_float_local(ritz1_bin, tmp_path, name):
    """AGAST #2062. Before the fix: `store double %<i64>` -> clang error."""
    assert _run("ritz1", ritz1_bin, tmp_path, name) == 3
