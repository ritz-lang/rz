"""AGAST #1948: a pointer to struct A passed where a pointer to struct B is
expected is a located error in every compiler.

THE DEFECT

ritz0 rejects the ticket's program ("argument 2 of `vec_read_all_fd` has the
wrong type: Vec$u8* != GrowBuf*", the #1366 diagnostic). ritz1 and
ritz1_selfhosted compiled and linked it silently: in ritz1's value model
every pointer is an i64, so nothing below the type checker ever sees the
pointee. It ran only because GrowBuf and Vec<u8> share a field layout; with
different layouts the callee reads and writes the wrong fields.

THE FIX

ritz1's call emitter compares the argument's static pointee struct (from
`@x` / `@&x` of a struct local or field, or a pointer-to-struct local) with
the parameter's pointee struct, and reports a mismatch at the call site,
naming the callee and argument number, as ritz0 does.

THE TESTS

  * reject: the ticket's program, plus a `*A` local into a `*B` param, plus a
    same-layout pair whose mismatch would run "correctly" — each compiler
    exits non-zero with a located diagnostic naming the callee.
  * control: the matching-struct versions of the same calls still compile
    and run with the expected exit code under every compiler.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration


def _compile(compiler, tmp_path, src, name="t"):
    path = tmp_path / f"{name}.ritz"
    path.write_text(src)
    ll = tmp_path / f"{name}_{compiler}.ll"
    if ll.exists():
        ll.unlink()
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(path), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300), ll
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    proc = subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)
    return proc, ll


# The ticket's repro, verbatim: GrowBuf where @&Vec<u8> is expected.
GROWBUF_AS_VEC = """\
import ritzlib.sys
import ritzlib.buf
import ritzlib.gvec
fn main() -> i32
    var g: GrowBuf = growbuf_new()
    let n: i64 = vec_read_all_fd(0, @&g)
    return n as i32
"""

TWO_STRUCTS = """\
struct A
    x: i64
    y: i64

struct B
    x: i64
    y: i64

struct C
    z: i32

fn take_b(tag: i64, p: *B) -> i64
    return p.x + p.y + tag

fn take_c(p: @&C) -> i32
    p.z = p.z + 1
    return p.z
"""

# Same layout: would "work", which is exactly why it must be refused.
ADDR_OF_LOCAL = TWO_STRUCTS + """
fn main() -> i32
    var a: A = A { x: 1, y: 2 }
    return take_b(0, @a) as i32
"""

# A *A local into a *B param (no `@` at the call).
PTR_LOCAL = TWO_STRUCTS + """
fn main() -> i32
    var a: A = A { x: 1, y: 2 }
    let pa: *A = @a
    return take_b(0, pa) as i32
"""

# Different layout: a mutable borrow of A into @&C writes A.x's low half.
MUT_REF = TWO_STRUCTS + """
fn main() -> i32
    var a: A = A { x: 1, y: 2 }
    return take_c(@&a)
"""

# `@&w.a`: a struct-typed field chain, into a different-layout @&C.
MEMBER = TWO_STRUCTS + """
struct W
    k: i32
    a: A

fn main() -> i32
    var w: W = W { k: 0, a: A { x: 1, y: 2 } }
    return take_c(@&w.a)
"""

# A method call: the receiver is argument 1, as ritz0 numbers it.
METHOD = TWO_STRUCTS + """
impl B
    fn bump(self: *B, c: @&C) -> i32
        return take_c(c)

fn main() -> i32
    var b: B = B { x: 1, y: 2 }
    var a: A = A { x: 1, y: 2 }
    return b.bump(@&a)
"""

# UFCS: `s.push_string(x)` lowers to string_push_string(@s, x), which takes
# `other: @String`.  GrowBuf has String's layout ({ptr, len, cap}).
UFCS = """\
import ritzlib.sys
import ritzlib.buf
import ritzlib.string
fn main() -> i32
    var s: String = string_new()
    var g: GrowBuf = growbuf_new()
    return s.push_string(@g)
"""

# Static method `C.get(@&a)`: no receiver, so `c` is argument 1.
STATIC = TWO_STRUCTS + """
impl C
    fn get(c: @&C) -> i64
        return take_c(c) as i64

fn main() -> i32
    var a: A = A { x: 1, y: 2 }
    return C.get(@&a) as i32
"""

REJECTS = {
    # name: (source, line of the bad call, callee, argument number)
    "growbuf_as_vec": (GROWBUF_AS_VEC, 6, "vec_read_all_fd", 2),
    "addr_of_local": (ADDR_OF_LOCAL, 21, "take_b", 2),
    "ptr_local": (PTR_LOCAL, 22, "take_b", 2),
    "mut_ref": (MUT_REF, 21, "take_c", 1),
    "member": (MEMBER, 25, "take_c", 1),
    "method": (METHOD, 26, "bump", 2),
    "ufcs": (UFCS, 7, "push_string", 2),
    "static": (STATIC, 25, "get", 1),
}


# ritz0's #1366 check is llvmlite's LLVM-type comparison, so two user structs
# with identical field types pass it, and a method, UFCS or static-method call
# (whatever the layout) is not checked at all.  Strict: these go red when #1960 lands.
RITZ0_SAME_LAYOUT_GAP = {"addr_of_local", "ptr_local", "method", "ufcs", "static"}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("case", sorted(REJECTS))
def test_struct_ptr_arg_mismatch_rejected(compiler, case, tmp_path, request):
    if compiler == "ritz0" and case in RITZ0_SAME_LAYOUT_GAP:
        request.applymarker(pytest.mark.xfail(
            strict=True, reason="AGAST #1960 — ritz0 compares LLVM layout, not struct identity"))
    src, line, callee, argno = REJECTS[case]
    proc, ll = _compile(compiler, tmp_path, src)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted a struct-pointer mismatch ({case}):\n{out}"
    assert re.search(rf"t\.ritz:{line}\b", out), (
        f"{compiler}: diagnostic not located at t.ritz:{line}:\n{out[-2000:]}")
    assert callee in out, f"{compiler}: diagnostic does not name `{callee}`:\n{out[-2000:]}"
    assert re.search(rf"argument {argno}\b", out), (
        f"{compiler}: diagnostic does not name argument {argno}:\n{out[-2000:]}")
    assert "wrong type" in out, f"{compiler}: rejected, but not as a type mismatch:\n{out[-2000:]}"


# Controls: the same call shapes with the right struct.
CONTROLS = {
    "addr_of_local": (TWO_STRUCTS + """
fn main() -> i32
    var b: B = B { x: 1, y: 2 }
    return take_b(4, @b) as i32
""", 7),
    "ptr_local": (TWO_STRUCTS + """
fn main() -> i32
    var b: B = B { x: 3, y: 2 }
    let pb: *B = @b
    return take_b(0, pb) as i32
""", 5),
    "mut_ref": (TWO_STRUCTS + """
fn main() -> i32
    var c: C = C { z: 8 }
    return take_c(@&c)
""", 9),
    "member": (TWO_STRUCTS + """
struct W
    k: i32
    c: C

fn main() -> i32
    var w: W = W { k: 0, c: C { z: 4 } }
    return take_c(@&w.c)
""", 5),
    "method": (TWO_STRUCTS + """
impl B
    fn bump(self: *B, c: @&C) -> i32
        return take_c(c)

fn main() -> i32
    var b: B = B { x: 1, y: 2 }
    var c: C = C { z: 1 }
    return b.bump(@&c)
""", 2),
    "ufcs": ("""\
import ritzlib.sys
import ritzlib.string
fn main() -> i32
    var s: String = string_new()
    var t: String = string_new()
    return s.push_string(@t) + 3
""", None),
    "static": (TWO_STRUCTS + """
impl C
    fn get(c: @&C) -> i64
        return take_c(c) as i64

fn main() -> i32
    var c: C = C { z: 5 }
    return C.get(@&c) as i32
""", 6),
    # An explicit cast is the programmer's own call to make.
    "cast": (TWO_STRUCTS + """
fn main() -> i32
    var a: A = A { x: 1, y: 2 }
    return take_b(0, @a as *B) as i32
""", 3),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("case", sorted(CONTROLS))
def test_matching_struct_ptr_arg_accepted(compiler, case, tmp_path):
    src, want = CONTROLS[case]
    proc, ll = _compile(compiler, tmp_path, src)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and ll.exists(), f"{compiler} rejected a control ({case}):\n{out}"
    if want is None:
        # Imports ritzlib: ritz1 emits only `declare`s for it, so the unit
        # cannot link on its own.  Accepting it is the point.
        return
    exe = tmp_path / f"t_{compiler}"
    link_cmd = ["clang", "-Wno-override-module", str(ll), "-o", str(exe), "-nostdlib", "-no-pie"]
    if compiler != "ritz0":
        link_cmd.insert(1, str(RITZ_START))
    link = subprocess.run(link_cmd, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler} IR did not link:\n{link.stderr[-2000:]}"
    assert subprocess.run([str(exe)], timeout=60).returncode == want
