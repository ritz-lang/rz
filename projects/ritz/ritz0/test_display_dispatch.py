"""AGAST #202 (#198 Phase 3): `{x}` in print / println / eprint / eprintln
is `Display::show`, not a type switch.

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

The `Writer` here is declared by the test, as ritzlib.fmt.Writer is: sink,
state, fd, cap, len. The compiler fills it for an implicit print (stdout or
stderr) and passes it to `show`; a type's `show` writes through the sink.

ORACLE

ritz0 compiles, links and runs each program; stdout and stderr are pinned to
literal bytes. The missing-impl case compiles to a located diagnostic naming
the type and the impl to add -- not a Python traceback, not an emitter
internal error.
"""

import os
import re
import subprocess
from pathlib import Path

import fast_link
import pytest
from ritz0_inproc import run_ritz0
from test_ritz1_builtin_struct_shadow import RITZ_ROOT

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
    (w.sink)(w, s.ptr, s.len)

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


def _compile(tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    return src, proc, ll


def _run(tmp_path: Path, name: str, program: str):
    _src, comp, ll = _compile(tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"ritz0 refused {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}")
    exe = tmp_path / name
    link = fast_link.clang(["clang", str(ll), "-o", str(exe), "-nostdlib"],
                           cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, f"{name} would not link:\n{link.stderr[-2000:]}"
    run = subprocess.run([str(exe)], capture_output=True, timeout=60, check=False)
    assert run.returncode == 0, (
        f"{name} exited {run.returncode}; stderr={run.stderr[-500:]!r}")
    return run.stdout, run.stderr


# ---------------------------------------------------------------------------
# `{x}` asks the value's Display.
# ---------------------------------------------------------------------------

def test_a_user_type_with_display_prints_through_it(tmp_path):
    program = SHAPE + POINT + """\
pub fn main() -> i32
    let p: Point = Point { x: 3, y: 4 }
    print("p={p}!\\n")
    0
"""
    out, err = _run(tmp_path, "display_print", program)
    assert out == b"p=POINT!\n", out
    assert err == b"", err


def test_eprint_asks_display_and_writes_stderr(tmp_path):
    program = SHAPE + POINT + """\
pub fn main() -> i32
    let p: Point = Point { x: 3, y: 4 }
    eprint("p={p}!\\n")
    0
"""
    out, err = _run(tmp_path, "display_eprint", program)
    assert out == b"", out
    assert err == b"p=POINT!\n", err


def test_println_and_eprintln_ask_display(tmp_path):
    program = SHAPE + POINT + """\
pub fn main() -> i32
    let p: Point = Point { x: 3, y: 4 }
    println("out={p}")
    eprintln("err={p}")
    0
"""
    out, err = _run(tmp_path, "display_lines", program)
    assert out == b"out=POINT\n", out
    assert err == b"err=POINT\n", err


# ---------------------------------------------------------------------------
# A type with no Display is a located compile error naming what to add.
# ---------------------------------------------------------------------------

def test_missing_display_is_a_friendly_located_error(tmp_path):
    program = SHAPE + """\
struct Bare
    n: i64

pub fn main() -> i32
    let b: Bare = Bare { n: 7 }
    print("b={b}\\n")
    0
"""
    _src, comp, _ll = _compile(tmp_path, "display_missing", program)
    assert comp.returncode != 0, "a type with no Display compiled"
    text = comp.stderr
    line = program[:program.index('    print("b={b}')].count("\n") + 1
    assert "Traceback" not in text, text
    assert re.search(rf"display_missing\.ritz:{line}:\d+: ", text), text
    assert "doesn't implement Display" in text, text
    assert "impl Display for Bare" in text, text


def test_a_field_of_a_type_without_display_is_named(tmp_path):
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
    _src, comp, _ll = _compile(tmp_path, "display_missing_field", program)
    assert comp.returncode != 0, "a type with no Display compiled"
    text = comp.stderr
    assert "Traceback" not in text, text
    assert "doesn't implement Display" in text, text
    assert "impl Display for Inner" in text, text
