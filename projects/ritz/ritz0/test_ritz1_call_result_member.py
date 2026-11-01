"""Regression tests for AGAST #1647 (and its duplicate #1470): reading a field
off a call or method result that returns a struct by value.

    if mk(true).a == 1        # ritz0: fine; ritz1: "unhandled EXPR_MEMBER"

emit_member_ptr (ritz1/src/emitter_expr.ritz) resolved idents, nested
members, derefs, pointer arithmetic and index bases, but had no arm for an
EXPR_CALL / EXPR_METHOD base, so ritz1 failed closed.  The fix spills the
returned aggregate into an alloca of the callee's return struct and GEPs the
field out of it.

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

STRUCTS = """\
struct F
    a: i64
    b: bool

struct N
    c: i32
    d: u8
    e: i64

struct Inner
    x: i64
    y: i32

struct Outer
    tag: u8
    inner: Inner

struct Deep
    o: Outer

struct PtrHolder
    p: *Inner

fn mk(b: bool) -> F
    F { a: 1, b: b }

fn mkn() -> N
    N { c: 7, d: 100, e: 0 - 3 }

fn mko(x: i64) -> Outer
    Outer { tag: 9, inner: Inner { x: x, y: 5 } }

fn mkd(x: i64) -> Deep
    Deep { o: mko(x) }

"""

PROGRAMS = {
    # The ticket's repro: an i64 field off a call in a condition.
    "call_scalar": STRUCTS
    + """\
pub fn main() -> i32
    if mk(true).a == 1
        return 42
    return 1
""",
    # A bool field off a call, as a condition and negated.
    "call_bool": STRUCTS
    + """\
pub fn main() -> i32
    if mk(false).b
        return 1
    if not mk(true).b
        return 2
    if mk(true).b
        return 42
    return 3
""",
    # Narrow fields (i32, u8, negative i64) keep their width and signedness
    # when read off a call.  d stays below 128: ritz0 sign-extends a u8 read
    # off a call result (AGAST #2042).
    "call_narrow": STRUCTS
    + """\
pub fn main() -> i32
    if mkn().c != 7
        return 1
    if mkn().d != 100
        return 2
    if mkn().e != 0 - 3
        return 3
    let c: i32 = mkn().c + 1
    if c != 8
        return 4
    return mkn().c * 6
""",
    # Nested struct fields: one and two levels below the call.
    "call_nested": STRUCTS
    + """\
pub fn main() -> i32
    if mko(11).tag != 9
        return 1
    if mko(11).inner.x != 11
        return 2
    if mko(11).inner.y != 5
        return 3
    if mkd(30).o.inner.x != 30
        return 4
    if mkd(30).o.tag != 9
        return 5
    return (mkd(37).o.inner.x + mko(0).inner.y) as i32
""",
    # A nested struct field copied out whole, then read.
    "call_nested_copy": STRUCTS
    + """\
pub fn main() -> i32
    let i: Inner = mko(40).inner
    if i.y != 5
        return 1
    return (i.x + 2) as i32
""",
    # A pointer field off a call, then through the pointer.
    "call_ptr_field": STRUCTS
    + """\
fn hold(p: *Inner) -> PtrHolder
    PtrHolder { p: p }

pub fn main() -> i32
    var i: Inner = Inner { x: 40, y: 2 }
    if hold(@i).p.y != 2
        return 1
    return (hold(@i).p.x + hold(@i).p.y as i64) as i32
""",
    # Pointer arithmetic on a `*i32` field off a call: the stride comes from
    # the field's pointee type (get_ptr_elem_size -> member_field_def).
    "call_ptr_stride": """\
struct Buf
    p: *i32
    n: i64

fn mkbuf(p: *i32) -> Buf
    Buf { p: p, n: 3 }

pub fn main() -> i32
    var arr: [3]i32 = [5, 40, 7]
    let q: *i32 = mkbuf(@arr[0]).p + 1
    if *q != 40
        return 1
    return *(mkbuf(@arr[0]).p + 1) + 2
""",
    # A unit-enum field off a call, compared and bound: the enum type comes
    # from unit_enum_expr_name -> resolve_member_chain_field.
    "call_enum_field": """\
enum Kind
    A
    B

struct T
    k: Kind
    v: i64

fn mkt(b: bool) -> T
    if b
        return T { k: Kind.B, v: 1 }
    T { k: Kind.A, v: 2 }

pub fn main() -> i32
    if mkt(false).k == Kind.B
        return 1
    if mkt(true).k != Kind.B
        return 2
    let k = mkt(true).k
    if k != Kind.B
        return 3
    return 42
""",
    # The call is evaluated exactly once per field read.
    "call_evaluated_once": STRUCTS
    + """\
var g_calls: i64 = 0

fn count(x: i64) -> F
    g_calls = g_calls + 1
    F { a: x, b: true }

pub fn main() -> i32
    let v: i64 = count(5).a
    if g_calls != 1
        return 1
    if count(6).b
        if g_calls != 2
            return 2
    if v != 5
        return 3
    return 42
""",
    # Field reads as call arguments and in arithmetic.
    "call_field_as_arg": STRUCTS
    + """\
fn add(a: i64, b: i64) -> i64
    a + b

pub fn main() -> i32
    return add(mk(true).a, mko(41).inner.x) as i32
""",
    # A large struct returned through an sret slot.
    "call_sret": """\
struct Big
    a: i64
    b: i64
    c: i64
    d: i64
    e: i32

fn big(n: i64) -> Big
    Big { a: n, b: n + 1, c: n + 2, d: n + 3, e: 9 }

pub fn main() -> i32
    if big(10).a != 10
        return 1
    if big(10).e != 9
        return 2
    return (big(39).d) as i32
""",
    # AGAST #1470's repro shape: a StrView field off a call.
    "call_strview_field": """\
import ritzlib.strview

struct Box
    value: StrView

fn mk() -> Box
    Box { value: "hello" }

pub fn main() -> i32
    if mk().value.len != 5
        return 1
    return (mk().value.len + 37) as i32
""",
    # Field off an instance method result.
    "method_scalar": STRUCTS
    + """\
struct P
    v: i64

impl P
    fn pair(self: *P) -> F
        F { a: self.v, b: self.v > 0 }
    fn outer(self: *P) -> Outer
        mko(self.v)

pub fn main() -> i32
    var p: P = P { v: 3 }
    if p.pair().a != 3
        return 1
    if not p.pair().b
        return 2
    if p.outer().inner.y != 5
        return 3
    return (p.outer().inner.x + 39) as i32
""",
    # Field off a static method result.
    "static_method": """\
struct Q
    x: i64
    y: i32

impl Q
    fn make(n: i64) -> Q
        Q { x: n, y: 2 }

pub fn main() -> i32
    if Q.make(40).y != 2
        return 1
    return (Q.make(40).x + Q.make(0).y as i64) as i32
""",
    # Generic return types: a generic fn returning its struct argument, and a
    # generic struct built by a generic fn.
    "generic_return": STRUCTS
    + """\
struct Wrap<T>
    val: T
    n: i32

fn id<T>(x: T) -> T
    x

fn wrap<T>(x: T) -> Wrap<T>
    Wrap<T> { val: x, n: 2 }

pub fn main() -> i32
    let f: F = F { a: 40, b: true }
    if not id<F>(f).b
        return 1
    let g: F = F { a: 40, b: true }
    if wrap<i64>(5).n != 2
        return 2
    if wrap<i64>(5).val != 5
        return 3
    if wrap<F>(F { a: 6, b: true }).val.a != 6
        return 4
    return (id<F>(g).a + wrap<i64>(2).val) as i32
""",
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
def test_ritz1_call_result_member(ritz1_bin, tmp_path, name):
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
