"""AGAST #202 (#198 Phase 3): `{x}` in print / println / eprint / eprintln
is `Display::show`, not a type switch, and `{x:?}` is `Debug::show_debug`,
auto-derived for a struct that has no impl of its own.

THE GAP

    struct Point
        x: i64
        y: i64

    impl Display for Point
        fn show(self: @Point, w: @&Writer) -> i64
            ...

    print("p={p}\\n")

ritz0's `_emit_print_value` dispatched on the LLVM type, so a user type was
an emitter error ("Cannot print value of type %Point") and the `impl
Display` was never consulted. The value's own `show` is the only word on how
it prints now; the compiler's primitive formatters remain only as the
fallback for a self-contained program that has no ritzlib in scope.

AGAST #4381 ported the same dispatch to ritz1, so every case here runs on all
three compilers; both compilers must accept the same programs.

The `Writer` here is declared by the test, as ritzlib.fmt.Writer is: sink,
state, fd, cap, len. The compiler fills it for an implicit print (stdout or
stderr) and passes it to `show`; a type's `show` writes through the sink.

ORACLE

Each program is compiled, linked and run; stdout and stderr are pinned to
literal bytes. The missing-impl case compiles to a located diagnostic naming
the type and the impl to add -- not a Python traceback, not an emitter
internal error.
"""

import re
import subprocess
from pathlib import Path

import pytest

from test_ref_into_value import COMPILERS, _compile, _link

pytestmark = [pytest.mark.integration]


# The standalone Writer and the Display trait a program can use without
# importing ritzlib: ritzlib.fmt.Writer's shape, and Display's one method.
SHAPE = """\
struct Writer
    sink: fn(@&Writer, *u8, i64) -> i64
    state: *u8
    fd: i32
    cap: i64
    len: i64

fn raw_write(w: @&Writer, s: StrView) -> i64
    let n: i64 = (w.sink)(w, s.ptr, s.len)
    if n > 0
        w.len = w.len + n
    n

trait Display
    fn show(self: @Self, w: @&Writer) -> i64

"""

POINT = """\
struct Point
    x: i64
    y: i64

impl Display for Point
    fn show(self: @Point, w: @&Writer) -> i64
        raw_write(w, "POINT")

"""


def _run_compiler(compiler: str, tmp_path: Path, name: str, program: str):
    """Compile and link `program` with `compiler`; returns its work directory."""
    comp, ll, work = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} refused {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}")
    link, exe = _link(compiler, ll, work)
    assert link.returncode == 0, f"{compiler}: {name} would not link:\n{link.stderr[-2000:]}"
    return work


def _run(compiler: str, tmp_path: Path, name: str, program: str):
    work = _run_compiler(compiler, tmp_path, name, program)
    run = subprocess.run([str(work / "main")], capture_output=True, timeout=60, check=False)
    assert run.returncode == 0, (
        f"{compiler}: {name} exited {run.returncode}; stderr={run.stderr[-500:]!r}")
    return run.stdout, run.stderr


def _compile_only(compiler: str, tmp_path: Path, name: str, program: str):
    comp, _ll, _work = _compile(compiler, tmp_path, name, program)
    return comp


# ---------------------------------------------------------------------------
# `{x}` asks the value's Display.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_user_type_with_display_prints_through_it(tmp_path, compiler):
    program = SHAPE + POINT + """\
pub fn main() -> i32
    let p: Point = Point { x: 3, y: 4 }
    print("p={p}!\\n")
    0
"""
    out, err = _run(compiler, tmp_path, "display_print", program)
    assert out == b"p=POINT!\n", f"{compiler}: {out!r}"
    assert err == b"", f"{compiler}: {err!r}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_eprint_asks_display_and_writes_stderr(tmp_path, compiler):
    program = SHAPE + POINT + """\
pub fn main() -> i32
    let p: Point = Point { x: 3, y: 4 }
    eprint("p={p}!\\n")
    0
"""
    out, err = _run(compiler, tmp_path, "display_eprint", program)
    assert out == b"", f"{compiler}: {out!r}"
    assert err == b"p=POINT!\n", f"{compiler}: {err!r}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_println_and_eprintln_ask_display(tmp_path, compiler):
    program = SHAPE + POINT + """\
pub fn main() -> i32
    let p: Point = Point { x: 3, y: 4 }
    println("out={p}")
    eprintln("err={p}")
    0
"""
    out, err = _run(compiler, tmp_path, "display_lines", program)
    assert out == b"out=POINT\n", f"{compiler}: {out!r}"
    assert err == b"err=POINT\n", f"{compiler}: {err!r}"


# ---------------------------------------------------------------------------
# A type with no Display is a located compile error naming what to add.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("compiler", COMPILERS)
def test_missing_display_is_a_friendly_located_error(tmp_path, compiler):
    program = SHAPE + """\
struct Bare
    n: i64

pub fn main() -> i32
    let b: Bare = Bare { n: 7 }
    print("b={b}\\n")
    0
"""
    comp = _compile_only(compiler, tmp_path, "display_missing", program)
    assert comp.returncode != 0, f"{compiler} compiled a type with no Display"
    text = comp.stdout + comp.stderr
    line = program[:program.index('    print("b={b}')].count("\n") + 1
    assert "Traceback" not in text, text
    assert re.search(rf"main\.ritz:{line}:\d+: ", text), text
    assert "doesn't implement Display" in text, text
    assert "impl Display for Bare" in text, text


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_field_of_a_type_without_display_is_named(tmp_path, compiler):
    """The message names the value's type, not the struct that holds it."""
    program = SHAPE + """\
struct Inner
    n: i64

struct Outer
    inner: Inner

pub fn main() -> i32
    let o: Outer = Outer { inner: Inner { n: 1 } }
    print("{o.inner}\\n")
    0
"""
    comp = _compile_only(compiler, tmp_path, "display_missing_field", program)
    assert comp.returncode != 0, f"{compiler} compiled a type with no Display"
    text = comp.stdout + comp.stderr
    assert "Traceback" not in text, text
    assert "doesn't implement Display" in text, text
    assert "impl Display for Inner" in text, text


# ---------------------------------------------------------------------------
# write / writeln: the program names the Writer; no implicit fd.
# ---------------------------------------------------------------------------

WRITER_SINK = """\
var buf: [256]u8

fn buf_sink(w: @&Writer, data: *u8, len: i64) -> i64
    let base: *u8 = w.state
    var i: i64 = 0
    while i < len
        *(base + w.len + i) = *(data + i)
        i = i + 1
    len

"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_write_and_writeln_use_the_explicit_writer(tmp_path, compiler):
    program = SHAPE + POINT + WRITER_SINK + """\
pub fn main() -> i32
    var w: Writer = Writer { sink: buf_sink, state: @buf[0] as *u8, fd: -1, cap: 0, len: 0 }
    let p: Point = Point { x: 3, y: 4 }
    writeln(@&w, "p={p}")
    write(@&w, "!{p}")
    let v: StrView = StrView { ptr: @buf[0] as *u8, len: w.len }
    print("[{v}] {w.len}\\n")
    0
"""
    out, err = _run(compiler, tmp_path, "display_writer", program)
    assert out == b"[p=POINT\n!POINT] 14\n", f"{compiler}: {out!r}"
    assert err == b"", f"{compiler}: {err!r}"


PACKAGE_WRITER = """\
import ritzlib.fmt
import ritzlib.string

struct Point
    x: i64
    y: i64

impl Display for Point
    fn show(self: @Point, w: @&Writer) -> i64
        let start: i64 = w.len()
        match write(w, "({self.x}, {self.y})")
            Ok(_) => w.len() - start
            Err(e) => -(e.code() as i64)

pub fn main() -> i32
    var s: String = string_new()
    var w: Writer = string_writer(@&s)
    let p: Point = Point { x: 3, y: 4 }
    match writeln(@&w, "p={p} x={p.x}")
        Ok(_) => pass
        Err(_) => return 1
    let v: StrView = s.as_view()
    print("[{v}] {w.len()}\\n")
    0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_write_into_ritzlib_string_writer(tmp_path, compiler):
    """The real ritzlib Writer: string_writer + writer_view round trip."""
    from test_format_into import _build

    proc, exe = _build(compiler, tmp_path, "display_pkg_writer", PACKAGE_WRITER)
    assert proc.returncode == 0 and exe.exists(), (
        f"{compiler} failed to build:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}")
    run = subprocess.run([str(exe)], capture_output=True, timeout=60, check=False)
    assert run.returncode == 0, run.stderr[-1000:]
    assert run.stdout == b"[p=(3, 4) x=3\n] 13\n", f"{compiler}: {run.stdout!r}"
    assert run.stderr == b"", f"{compiler}: {run.stderr!r}"


# ---------------------------------------------------------------------------
# `{x:?}` asks Debug; a struct with no Debug impl auto-derives one.
# ---------------------------------------------------------------------------

DEBUG_TRAIT = """\
trait Debug
    fn show_debug(self: @Self, w: @&Writer) -> i64

"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_struct_without_debug_auto_derives_it(tmp_path, compiler):
    """No Debug impl anywhere: the compiler prints the fields."""
    program = SHAPE + """\
struct Point
    x: i64
    y: i64

pub fn main() -> i32
    let p: Point = Point { x: 3, y: 4 }
    print("{p:?}\\n")
    0
"""
    out, err = _run(compiler, tmp_path, "debug_derive", program)
    assert out == b"Point { x: 3, y: 4 }\n", f"{compiler}: {out!r}"
    assert err == b"", f"{compiler}: {err!r}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_auto_debug_nests_and_is_typed_per_field(tmp_path, compiler):
    """A struct field recurses; each scalar prints by its own type."""
    program = SHAPE + """\
struct Inner
    n: i32
    flag: bool

struct Outer
    inner: Inner
    count: u64

pub fn main() -> i32
    let o: Outer = Outer { inner: Inner { n: -7, flag: true }, count: 9 }
    print("{o:?}\\n")
    0
"""
    out, err = _run(compiler, tmp_path, "debug_nested", program)
    assert out == b"Outer { inner: Inner { n: -7, flag: true }, count: 9 }\n", (
        f"{compiler}: {out!r}")
    assert err == b"", f"{compiler}: {err!r}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_explicit_debug_impl_wins_over_auto_derive(tmp_path, compiler):
    program = SHAPE + DEBUG_TRAIT + """\
struct Point
    x: i64
    y: i64

impl Debug for Point
    fn show_debug(self: @Point, w: @&Writer) -> i64
        raw_write(w, "POINT!")

pub fn main() -> i32
    let p: Point = Point { x: 3, y: 4 }
    print("p={p:?}\\n")
    0
"""
    out, err = _run(compiler, tmp_path, "debug_explicit", program)
    assert out == b"p=POINT!\n", f"{compiler}: {out!r}"
    assert err == b"", f"{compiler}: {err!r}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_display_impl_does_not_answer_the_debug_spec(tmp_path, compiler):
    """`{p:?}` asks Debug alone; a Display-only type still auto-derives."""
    program = SHAPE + POINT + """\
pub fn main() -> i32
    let p: Point = Point { x: 3, y: 4 }
    print("p={p:?}\\n")
    0
"""
    out, err = _run(compiler, tmp_path, "debug_not_display", program)
    assert out == b"p=Point { x: 3, y: 4 }\n", f"{compiler}: {out!r}"
    assert err == b"", f"{compiler}: {err!r}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_integer_and_bool_debug_is_their_display(tmp_path, compiler):
    program = SHAPE + """\
pub fn main() -> i32
    let n: i32 = -5
    let u: u8 = 200
    let b: bool = true
    print("{n:?} {u:?} {b:?}\\n")
    0
"""
    out, err = _run(compiler, tmp_path, "debug_scalars", program)
    assert out == b"-5 200 true\n", f"{compiler}: {out!r}"
    assert err == b"", f"{compiler}: {err!r}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_missing_debug_is_a_friendly_located_error(tmp_path, compiler):
    """A StrView has no Debug impl in a self-contained program: named."""
    program = SHAPE + """\
pub fn main() -> i32
    let s: StrView = "hi"
    print("s={s:?}\\n")
    0
"""
    comp = _compile_only(compiler, tmp_path, "debug_missing", program)
    assert comp.returncode != 0, f"{compiler} compiled a value with no Debug"
    text = comp.stdout + comp.stderr
    line = program[:program.index('    print("s={s:?}')].count("\n") + 1
    assert "Traceback" not in text, text
    assert re.search(rf"main\.ritz:{line}:\d+: ", text), text
    assert "doesn't implement Debug" in text, text
    assert "impl Debug for StrView" in text, text


PACKAGE_DEBUG = """\
import ritzlib.fmt

struct Point
    name: StrView
    x: i64

pub fn main() -> i32
    let p: Point = Point { name: "hi", x: 3 }
    println("{p:?}")
    0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_auto_debug_uses_ritzlib_impls_for_the_fields(tmp_path, compiler):
    """A StrView field quotes through ritzlib.fmt's real Debug impl."""
    from test_format_into import _build

    proc, exe = _build(compiler, tmp_path, "debug_pkg", PACKAGE_DEBUG)
    assert proc.returncode == 0 and exe.exists(), (
        f"{compiler} failed to build:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}")
    run = subprocess.run([str(exe)], capture_output=True, timeout=60, check=False)
    assert run.returncode == 0, run.stderr[-1000:]
    assert run.stdout == b'Point { name: "hi", x: 3 }\n', f"{compiler}: {run.stdout!r}"
    assert run.stderr == b"", f"{compiler}: {run.stderr!r}"
