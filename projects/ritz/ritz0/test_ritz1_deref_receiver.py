"""Regression tests for AGAST #2145: a method call on a dereferenced receiver.

    fn via(pp: **Res) -> u64
        (*pp).peek()     # ritz0: fine; ritz1: "cannot determine receiver type"

emit_expr_method (ritz1/src/emitter_expr_call.ritz) had no EXPR_UNARY arm, so
`(*p).m()` / `(*pp).m()` / `(**pp).m()` never resolved a receiver type.  The fix
resolves the deref operand with emit_deref_operand_ptr (as emit_member_ptr does
for `(*pp).w`): one level left is the struct itself, two levels is a `*S`
value dispatched ptr-of-ptr.

Each program returns 42 when correct and a distinct small code naming the check
that failed otherwise.  ritz0 is the oracle; every case runs at runtime.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

EXPECTED = 42

RES_DEF = """\
struct Res
    v: u64
    w: u64

impl Res
    fn peek(self: *Res) -> u64
        self.w
    fn bump(self: *Res, n: u64)
        self.w = self.w + n
    fn plus(self: *Res, n: i32) -> i32
        (self.w as i32) + n

"""

PROGRAMS = {
    # The ticket's repro: `(*pp).peek()` on a `**Res` param.
    "ptr_ptr_param_read": RES_DEF
    + """\
fn via(pp: **Res) -> u64
    (*pp).peek()

pub fn main() -> i32
    var r: Res = Res { v: 1, w: 42 }
    var p: *Res = @r
    return via(@p) as i32
""",
    # A mutating method through `(*pp)` writes the pointee, not a copy.
    "ptr_ptr_param_mutate": RES_DEF
    + """\
fn bump_via(pp: **Res)
    (*pp).bump(10)
    (*pp).bump(2)

pub fn main() -> i32
    var r: Res = Res { v: 1, w: 30 }
    var p: *Res = @r
    bump_via(@p)
    if r.w != 42
        return 1
    return r.w as i32
""",
    # Narrow argument and result through `(*pp)`.
    "ptr_ptr_param_args": RES_DEF
    + """\
fn plus_via(pp: **Res) -> i32
    (*pp).plus(2)

pub fn main() -> i32
    var r: Res = Res { v: 1, w: 40 }
    var p: *Res = @r
    return plus_via(@p)
""",
    # A `**Res` local, not a param.
    "ptr_ptr_local": RES_DEF
    + """\
pub fn main() -> i32
    var r: Res = Res { v: 1, w: 40 }
    var p: *Res = @r
    let pp: **Res = @p
    (*pp).bump(2)
    return (*pp).peek() as i32
""",
    # A `**Res` field: `(*h.pp).m()`.
    "ptr_ptr_field": RES_DEF
    + """\
struct Holder
    pp: **Res

pub fn main() -> i32
    var r: Res = Res { v: 1, w: 40 }
    var p: *Res = @r
    var h: Holder = Holder { pp: @p }
    (*h.pp).bump(2)
    return (*h.pp).peek() as i32
""",
}

# A deref that leaves a struct VALUE: ritz0 runs the method on a copy (a
# mutating method is lost), so ritz1 keeps rejecting it until #2175 settles
# the semantics.  These pin the fail-closed error.
FAIL_CLOSED = {
    "double_deref_param": RES_DEF
    + """\
fn via2(pp: **Res) -> u64
    (**pp).peek()

pub fn main() -> i32
    var r: Res = Res { v: 1, w: 42 }
    var p: *Res = @r
    return via2(@p) as i32
""",
    "ptr_local_deref": RES_DEF
    + """\
pub fn main() -> i32
    var r: Res = Res { v: 1, w: 42 }
    let p: *Res = @r
    return (*p).peek() as i32
"""
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
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
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
def test_ritz1_deref_receiver(ritz1_bin, tmp_path, name):
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(FAIL_CLOSED))
def test_ritz1_struct_value_deref_receiver_fails_closed(ritz1_bin, tmp_path, name):
    src = tmp_path / f"{name}.ritz"
    src.write_text(FAIL_CLOSED[name])
    ll = tmp_path / f"{name}.ll"
    comp = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode != 0 and not ll.exists()
    assert "cannot determine receiver type" in comp.stdout + comp.stderr


# The ticket's related issue: a `fn(...) -> T` param is a TYPE_PTR, but type_fn
# sets no pointee, so param_new copied a stale struct name (the earlier
# `r: *Res`, or the fn type's own `*Res` param).  `f.w` then GEP'd into Res.
FN_PARAM_DEFS = """\
struct Res
    v: u64
    w: u64

fn twice(r: *Res) -> i32
    (r.w as i32) * 2

fn plain(k: i32) -> i32
    k + 1

"""

# Valid fn-typed params next to `*Res` params still compile and run.
FN_PARAM_OK = FN_PARAM_DEFS + """\
fn apply(f: fn(*Res) -> i32, r: *Res) -> i32
    f(r)

fn relay(f: fn(*Res) -> i32, r: *Res) -> i32
    let g = f
    apply(g, r) + apply(f, r) - f(r)

fn after(r: *Res, f: fn(i32) -> i32) -> i32
    f(r.w as i32)

pub fn main() -> i32
    var r: Res = Res { v: 1, w: 10 }
    return relay(twice, @r) + after(@r, plain) + 11
"""

FN_PARAM_FIELD = FN_PARAM_DEFS + """\
fn bad(r: *Res, f: fn(i32) -> i32) -> u64
    f.w

pub fn main() -> i32
    0
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_fn_param_after_struct_ptr_param_runs(ritz1_bin, tmp_path, compiler):
    assert _run(compiler, tmp_path, "fn_param_ok", FN_PARAM_OK) == EXPECTED


@pytest.mark.integration
def test_ritz1_fn_param_has_no_struct_fields(ritz1_bin, tmp_path):
    src = tmp_path / "fn_param_field.ritz"
    src.write_text(FN_PARAM_FIELD)
    ll = tmp_path / "fn_param_field.ll"
    comp = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
    )
    # ritz0 rejects it too ("Cannot access field on non-struct pointer").
    assert comp.returncode != 0 and not ll.exists(), comp.stdout + comp.stderr
