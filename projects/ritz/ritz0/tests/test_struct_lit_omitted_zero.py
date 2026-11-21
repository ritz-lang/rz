"""AGAST #1749: a field a struct literal leaves out is zero, on every compiler.

THE DEFECT

For `struct S { a: [64]i64, count: i32 }`, ritz1 lowered

    var z: S = S { count: 3 }

to a store of `count` and nothing else, so `z.a[5]` read whatever the stack
held (undef at -O2: a larger program returned a wrong result at -O2 only).
ritz0 zeroes an omitted field (`_zero_constant`; a memset for a large one
since #1741), and existing code relies on it.  docs/LANGUAGE_SPEC.md §9.2 now
states the rule.

THE FIX

ritz1 zeroes every field a literal omits, after the fields it gives: a
scalar with a `store zeroinitializer`, an array or struct through
@__ritz_sret_zero (never llvm.memset: #3218, ritz links -nostdlib).  Both
literal lowerings do it: emit_var_decl's `let`/`var` loop and
emit_struct_lit_to_alloca (return, reassignment, rvalue, nested literal).

Each form below is one of those paths.  `dirty()` fills the stack with 0xAA
through volatile stores just before it, and every form and reader is
`[[noinline]]`, so an omitted field that is not written reads 0xAA bytes and
fails at run time.  The exit code has bit k set when form k (FORMS) read a
non-zero omitted field.
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

COMPILERS = ("ritz0", "ritz1", "ritz1_selfhosted")

FORMS = (
    "typed_var",
    "untyped_let",
    "reassign",
    "returned",
    "nested_omitted",
    "nested_partial",
    "scalars",
    "rvalue",
)

PROGRAM = """\
struct S
    a: [64]i64
    count: i32

struct Inner
    x: i64
    y: [8]i32

struct Outer
    tag: i32
    inner: Inner

struct P
    a: i32
    b: i64
    c: *u8
    d: bool
    e: u8

[[noinline]]
fn dirty() -> i32
    var d: [8192]u8 = [0; 8192]
    var i: i32 = 0
    while i < 8192
        volatile_store(@d[i], 170)
        i = i + 1
    volatile_load(@d[77]) as i32

# Every element of `a`, plus `count`.
[[noinline]]
fn s_sum(p: *S) -> i64
    var t: i64 = 0
    var i: i32 = 0
    while i < 64
        t = t + p.a[i]
        i = i + 1
    t + p.count as i64

[[noinline]]
fn inner_sum(p: *Inner) -> i64
    var t: i64 = p.x
    var i: i32 = 0
    while i < 8
        t = t + p.y[i] as i64
        i = i + 1
    t

[[noinline]]
fn p_sum(p: *P) -> i64
    var t: i64 = p.a as i64 + p.b + p.e as i64
    if p.c != null
        t = t + 1000
    if p.d
        t = t + 2000
    t

# emit_var_decl: a typed `var` (the ticket).
[[noinline]]
fn typed_var() -> i64
    var z: S = S { count: 3 }
    s_sum(@z)

# emit_var_decl: an untyped `let`.
[[noinline]]
fn untyped_let() -> i64
    let z = S { count: 3 }
    s_sum(@z)

# Reassignment: the old `a` must not survive.
[[noinline]]
fn reassign() -> i64
    var z = S { a: [5; 64], count: 1 }
    z = S { count: 3 }
    s_sum(@z)

[[noinline]]
fn make(c: i32) -> S
    S { count: c }

# A returned literal (sret).
[[noinline]]
fn returned() -> i64
    var z: S = make(3)
    s_sum(@z)

# An omitted nested-struct field.
[[noinline]]
fn nested_omitted() -> i64
    var o = Outer { tag: 3 }
    inner_sum(@o.inner) + o.tag as i64

# A nested literal that omits a field of its own.
[[noinline]]
fn nested_partial() -> i64
    var o = Outer { tag: 1, inner: Inner { x: 2 } }
    inner_sum(@o.inner) + o.tag as i64

# Scalars of every width, a pointer and a bool.
[[noinline]]
fn scalars() -> i64
    var p = P { a: 3 }
    p_sum(@p)

[[noinline]]
fn by_value(s: S) -> i64
    s_sum(@s)

# An rvalue literal passed by value.
[[noinline]]
fn rvalue() -> i64
    by_value(S { count: 3 })

fn main() -> i32
    var bad: i32 = 0
    dirty()
    if typed_var() != 3
        bad = bad | 1
    dirty()
    if untyped_let() != 3
        bad = bad | 2
    dirty()
    if reassign() != 3
        bad = bad | 4
    dirty()
    if returned() != 3
        bad = bad | 8
    dirty()
    if nested_omitted() != 3
        bad = bad | 16
    dirty()
    if nested_partial() != 3
        bad = bad | 32
    dirty()
    if scalars() != 3
        bad = bad | 64
    dirty()
    if rvalue() != 3
        bad = bad | 128
    bad
"""


def _ll(request, compiler: str, tmp_path: Path) -> Path:
    src = tmp_path / "olz.ritz"
    src.write_text(PROGRAM)
    ll = tmp_path / f"olz_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run(
            [str(binary), str(src), "-o", str(ll)],
            cwd=tmp_path,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
    assert proc.returncode == 0 and ll.exists(), (
        f"{compiler} failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
    )
    return ll


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_omitted_struct_lit_fields_are_zero_at_O2(request, tmp_path, compiler):
    ll = _ll(request, compiler, tmp_path)
    obj = tmp_path / "olz.o"
    cc = subprocess.run(
        ["clang", "-c", "-O2", "-Wno-override-module", str(ll), "-o", str(obj)],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cc.returncode == 0, cc.stderr[-2000:]
    exe = tmp_path / "olz"
    link = ["clang", "-nostdlib", "-o", str(exe), str(obj)]
    if compiler != "ritz0":
        # ritz0 emits its own _start for `main`; ritz1 links the runtime's.
        link.append(str(RITZ_START))
    built = fast_link.clang(
        link, check=False, capture_output=True, text=True, timeout=120
    )
    assert built.returncode == 0, f"{compiler}: link:\n{built.stderr[-2000:]}"
    rc = subprocess.run([str(exe)], check=False, timeout=60).returncode
    bad = [f for k, f in enumerate(FORMS) if rc & (1 << k)]
    assert rc == 0, f"{compiler}: an omitted field read non-zero in {bad} (exit {rc})"
