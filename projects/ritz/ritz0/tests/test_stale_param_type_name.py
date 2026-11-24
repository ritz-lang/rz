"""AGAST #2139: a `*prim` param must not inherit an earlier type's name.

ritz1's parser leaves the name of the last named type it parsed in
`last_type_name`; a primitive (`u8`) never resets it.  param_new copied that
name into every pointer/reference param, so `fn first(d: *u8)` written after
`self: *Res` (or after a struct with a `s: St` field) recorded `d` as a
pointer to Res (or St).  Method-call syntax then dispatched `d.peek()` to
`Res_peek` instead of the free `peek(d: *u8)`, reading a Res out of a byte
buffer.

ritz0 has no method-call syntax on a `*u8`/`**u8`/`@u8` receiver and rejects
`d.peek()`; ritz1 now rejects it too, where it used to call Res_peek.  #4294
naming `u8`/`*u8` for its own impls changed only ritz0's wording (below):
`peek` is no type's method, `**u8` has no impl target.  The
controls (named pointees, which must keep their name) return 42 on ritz0,
ritz1 and ritz1_selfhosted.
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

pytestmark = pytest.mark.integration


def _compile(compiler, tmp_path, src):
    path = tmp_path / "t.ritz"
    path.write_text(src)
    ll = tmp_path / f"t_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    if compiler == "ritz0":
        proc = run_ritz0([str(path), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=tmp_path,
                              env=env, capture_output=True, text=True, timeout=300)
    return proc, ll


def _run(compiler, tmp_path, src):
    """Compile, link and run `src`; return its exit code."""
    proc, ll = _compile(compiler, tmp_path, src)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and ll.exists(), f"{compiler} rejected:\n{out}"
    objs = [str(ll)] if compiler == "ritz0" else [str(RITZ_START), str(ll)]
    exe = tmp_path / f"t_{compiler}"
    link = fast_link.clang(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                           "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


# Res_peek reads `w`, at offset 8 of whatever `d` points at.
_RES = """\
struct Res
    v: u64
    w: u64

impl Res
    fn peek(self: *Res) -> u64
        self.w

"""

STALE = {
    # The ticket's shape: `d: *u8` after a `*Res` param.
    "ptr_u8": _RES + """\
fn peek(d: *u8) -> u64
    (*(d + 1)) as u64

fn first(d: *u8) -> u64
    d.peek()

fn main() -> i32
    var buf: [16]u8
    buf[1] = 42
    first(@buf[0]) as i32
""",
    # `**u8`: the innermost pointee is primitive too.
    "ptr_ptr_u8": _RES + """\
fn peek(d: **u8) -> u64
    (*(*d + 1)) as u64

fn first(d: **u8) -> u64
    d.peek()

fn main() -> i32
    var buf: [16]u8
    buf[1] = 42
    var q: *u8 = @buf[0]
    first(@q) as i32
""",
    # `@u8`: a reference to a primitive.
    "ref_u8": _RES + """\
fn peek(d: @u8) -> u64
    (*d) as u64

fn first(d: @u8) -> u64
    d.peek()

fn main() -> i32
    var b: u8 = 42
    first(@b) as i32
""",
    # The stale name came from a struct field (`s: St`), not a param.
    "after_enum_field": """\
enum St: u8
    Ok
    Bad = 5

struct Res
    v: u64
    s: St

fn peek(d: *u8) -> u64
    (*(d + 1)) as u64

fn first(d: *u8) -> u64
    d.peek()

fn main() -> i32
    var r: Res
    r.s = St.Bad
    var buf: [16]u8
    buf[1] = 37
    (first(@buf[0]) + r.s as u64) as i32
""",
}

# Controls: a named pointee keeps its name (member access and method calls
# resolve through it), each declared after a `*u8` param.
NAMED = {
    "named_pointees_kept": _RES + """\
fn byte(d: *u8) -> u64
    (*d) as u64

fn via_ptr(r: *Res) -> u64
    r.peek()

fn via_ref(r: @Res) -> u64
    r.w

fn via_ptr_ptr(pp: **Res) -> u64
    (*pp).w

fn main() -> i32
    var r: Res
    r.v = 0
    r.w = 14
    var q: *Res = @r
    var b: u8 = 0
    (via_ptr(@r) + via_ref(@r) + via_ptr_ptr(@q) + byte(@b)) as i32
""",
}


REJECTED_BY = {
    "ritz0": "Cannot call method 'peek' on unknown type",
    # AGAST #4665: ritz1 says it in ritz0's words, not as an emitter failure.
    "ritz1": "Cannot call method 'peek' on unknown type",
    "ritz1_selfhosted": "Cannot call method 'peek' on unknown type",
}

# #4294 lets a trait impl target `u8` and `*u8`, so ritz0 now names those
# receivers instead of calling them unknown; `peek` is still not an impl
# method, and the refusal stands with a more precise message.  `**u8` has no
# impl target, so it keeps the unknown-type message.
RITZ0_NAMED_RECEIVER = {
    "ptr_u8": "No method 'peek' found for type '*u8'",
    "ref_u8": "No method 'peek' found for type 'u8'",
    "after_enum_field": "No method 'peek' found for type '*u8'",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("case", sorted(STALE))
def test_prim_pointer_param_has_no_type_name(compiler, case, tmp_path):
    proc, _ = _compile(compiler, tmp_path, STALE[case])
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted `d.peek()` on a primitive pointer:\n{out}"
    expected = RITZ0_NAMED_RECEIVER.get(case) if compiler == "ritz0" else None
    assert (expected or REJECTED_BY[compiler]) in out, out


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("case", sorted(NAMED))
def test_named_pointee_param_keeps_name(compiler, case, tmp_path):
    assert _run(compiler, tmp_path, NAMED[case]) == 42
