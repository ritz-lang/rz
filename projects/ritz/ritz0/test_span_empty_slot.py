"""`Span.empty()` takes its `T` from the slot it lands in (AGAST #2296).

The receiver is the type `Span`, not a value, and the type argument is never
spelled: a `-> Span<T>` return, a `let s: Span<T>` annotation or a `Span<T>`
parameter supplies it. Where none does, every compiler refuses with a located
error rather than ritz1's "cannot determine receiver type" or ritz0's
"Unknown identifier: Span" traceback.

Each row can fail on its own: one per slot kind, one where an argument's `T`
must win over the enclosing function's return type, and one per way of having
no slot.

`Span<T>` itself is built in, with no import (AGAST #3127): rows for a
`Span<i32>` parameter, a generic fn's `Span<X>` instance, the built-in `*T`
pointee's stride, and a program's own `Span<T>` winning over it.
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

# `cN(s)` exits 0 only when `s` is a `{ null, 0 }` Span<uN/iN>: an undefined
# pointer or length fails.
def _checks(*types):
    return "".join(f"""\
fn c{bits}(s: Span<{t}>) -> i32
    if s.ptr as i64 != 0
        return 1
    if s.len() != 0
        return 2
    return 0

""" for bits, t in types)


CHECKS = {"8": "u8", "32": "i32", "64": "i64"}


# The checkers `program` calls, before it. No row imports ritzlib.span: every
# `Span<T>` is built in (AGAST #3127; ritz1 declared only `Span$u8` before).
def _with_checks(program):
    return _checks(*((b, t) for b, t in CHECKS.items() if f"c{b}(" in program)) + program

# name -> program; each must exit 0.
ACCEPTS = {
    "return": """\
fn ms() -> Span<u8>
    return Span.empty()

pub fn main() -> i32
    return c8(ms())
""",
    "typed_let": """\
pub fn main() -> i32
    let s: Span<i64> = Span.empty()
    return c64(s)
""",
    # A `return` leaves the let it sits in: the fn's T, not the let's slot.
    "return_inside_let_arm": """\
fn ms(n: i64) -> Span<u8>
    let k: i64 = match n
        5 => return Span.empty()
        _ => n
    return Span.empty()

pub fn main() -> i32
    return c8(ms(5))
""",
    "argument": """\
pub fn main() -> i32
    return c8(Span.empty())
""",
    # The parameter's T, not the enclosing fn's: a `Span<u8>` here is the
    # wrong type for `c32`.
    "argument_not_return": """\
fn ms() -> Span<u8>
    if c32(Span.empty()) != 0
        return Span.empty()
    return Span.empty()

pub fn main() -> i32
    return c8(ms())
""",
    # A `Span<i32>` parameter alone, `s.ptr` read through it (AGAST #3127).
    "span_i32_parameter": """\
fn n32(s: Span<i32>) -> i32
    if s.ptr as i64 != 0
        return 1
    return s.len() as i32

pub fn main() -> i32
    return n32(Span.empty())
""",
    # A generic fn's `Span<X>` instance, at u8 and at i32 (AGAST #3127).
    "generic_fn": """\
fn gen<X>(s: Span<X>) -> i32
    if s.ptr as i64 != 0
        return 1
    return s.len() as i32

pub fn main() -> i32
    let a: Span<u8> = Span.empty()
    let b: Span<i32> = Span.empty()
    return gen(a) + gen(b)
""",
    # The built-in `ptr: *T` is a `*T`: `s.ptr + 1` strides by sizeof(T).
    "builtin_ptr_strides_by_t": """\
fn second(s: Span<i64>) -> i64
    return *(s.ptr + 1)

pub fn main() -> i32
    var a: [3]i64 = [10, 20, 30]
    var s: Span<i64> = Span.empty()
    s.ptr = @a[0]
    s.len = 3
    return (second(s) - 20) as i32
""",
    # A program's own `Span<T>` wins over the built-in one.
    "own_span_template": """\
struct Span<T>
    ptr: *T
    len: i64
    tag: i64

fn t(s: Span<i32>) -> i64
    return s.tag

pub fn main() -> i32
    var s: Span<i32>
    s.tag = 7
    return (t(s) - 7) as i32
""",
}

# name -> (program, line of the refused `Span.empty()`)
REFUSES = {
    # An untyped let gives no T, even in a fn that returns a Span.
    "untyped_let": ("""\
fn ms() -> Span<u8>
    let s = Span.empty()
    return s

pub fn main() -> i32
    return 0
""", 2),
    # A parameter that isn't a Span gives none, and the return type
    # doesn't leak into an argument.
    "non_span_parameter": ("""\
fn take(n: i64) -> i64
    return n

fn ms() -> Span<u8>
    take(Span.empty())
    return Span.empty()

pub fn main() -> i32
    return 0
""", 5),
    # An arm of an `i64` let lands in the let, not the fn's `Span<u8>`.
    "in_a_let_arm": ("""\
fn ms(b: bool) -> Span<u8>
    let n: i64 = if b
        Span.empty().len()
    else
        0
    return Span.empty()

pub fn main() -> i32
    return 0
""", 3),
    # A receiver lands in no slot: `-> i32` isn't a Span.
    "receiver": ("""\
pub fn main() -> i32
    return Span.empty().len() as i32
""", 2),
}


def _params(table):
    return [pytest.param(c, n, id=f"{c}-{n}") for n in sorted(table) for c in COMPILERS]


def _compile(request, tmp_path, compiler, program):
    src = tmp_path / "main.ritz"
    src.write_text(program)
    ll = tmp_path / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        comp = subprocess.run([str(RITZ1_BUILD / compiler), str(src), "-o", str(ll)],
                              cwd=tmp_path, env=env, capture_output=True, text=True, check=False,
                              timeout=300)
    return comp, ll


@pytest.mark.parametrize("compiler,name", _params(ACCEPTS))
def test_slot_gives_span_empty_its_type(request, tmp_path, compiler, name):
    program = _with_checks(ACCEPTS[name])
    comp, ll = _compile(request, tmp_path, compiler, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}")
    exe = tmp_path / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-2000:]}"
    rc = subprocess.run([str(exe)], capture_output=True, timeout=60, check=False).returncode
    assert rc == 0, f"{compiler} {name}: exit {rc} (1: ptr not null, 2: len not 0)"


@pytest.mark.parametrize("compiler,name", _params(REFUSES))
def test_no_slot_is_a_located_refusal(request, tmp_path, compiler, name):
    program, line = REFUSES[name]
    comp, ll = _compile(request, tmp_path, compiler, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 or not ll.exists(), f"{compiler} accepted it:\n{out[-2000:]}"
    assert "Traceback" not in out, f"{compiler} crashed:\n{out[-2000:]}"
    assert f"main.ritz:{line}:" in out and "needs its type argument" in out, (
        f"{compiler}: not a located refusal:\n{out[-2000:]}")
