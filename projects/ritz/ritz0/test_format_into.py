"""AGAST #1824: `format_into(sink, "...")` formats into a buffer.

THE GAP

`{expr}` interpolation worked only in a literal passed to print / eprint, so
nothing could format into a String or GrowBuf. ritz1's emitter builds each IR
line from 5-8 emit_str / emit_reg calls for want of it.

THE FEATURE (LANGUAGE_SPEC "Formatting into a buffer")

    format_into(sink, "  %{r} = trunc i64 %{v} to {ty}\\n")

takes the same literal, placeholder grammar and `{{` / `}}` escapes as print,
and appends each piece to `sink` through `sink.push_bytes(data: *u8, len: i64)`,
resolved statically like any method call. `String`, `GrowBuf` and `Vec<u8>`
provide it; so can any user type. Unsigned integers format as unsigned.

ORACLE

Every program is compiled by ritz0 and by ritz1. Both binaries must exit 0
and print the buffer's bytes, pinned to a literal expected string, so a bug
both compilers share cannot pass either. Rejected programs must fail to
compile in both, naming the problem.
"""

import os
import subprocess
from pathlib import Path

import pytest

from test_ritz1_builtin_struct_shadow import RITZ_ROOT

# Compiles and runs programs with both compilers (AGAST #1805).
pytestmark = [pytest.mark.usefixtures("ritz1_bin"), pytest.mark.integration]

def _build(compiler: str, tmp_path: Path, name: str, program: str):
    """Build `program` as a package (build.py compiles and links every
    imported ritzlib module). Returns (CompletedProcess, path to the binary)."""
    pkg = tmp_path / f"{name}_{compiler}"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "main.ritz").write_text(program)
    (pkg / "ritz.toml").write_text(
        f'[package]\nname = "{name}"\nversion = "0.1.0"\n\n'
        '[build]\ntarget = "x86_64-linux"\n'
    )
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        ["python3", str(RITZ_ROOT / "build.py"), "build", str(pkg),
         "--no-cache", "--compiler", compiler],
        cwd=RITZ_ROOT, env=env, capture_output=True, text=True, timeout=600,
    )
    return proc, pkg / "build" / "debug" / name


def _stdout(compiler: str, tmp_path: Path, name: str, program: str) -> bytes:
    proc, exe = _build(compiler, tmp_path, name, program)
    assert proc.returncode == 0 and exe.exists(), (
        f"{compiler} failed to build {name}:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"
    )
    run = subprocess.run([str(exe)], capture_output=True, timeout=60)
    assert run.returncode == 0, f"{compiler} binary for {name} exited {run.returncode}"
    return run.stdout


def _assert_parity(tmp_path: Path, name: str, program: str, expected: bytes) -> None:
    out0 = _stdout("ritz0", tmp_path, name, program)
    out1 = _stdout("ritz1", tmp_path, name, program)
    # The literal pin first: it names the right answer, not just agreement.
    assert out0 == expected, f"ritz0 printed {out0!r}"
    assert out1 == expected, f"ritz1 printed {out1!r}, ritz0 printed {out0!r}"


PRELUDE = """\
import ritzlib.string
import ritzlib.buf
import ritzlib.gvec

fn show(s: @String)
    print("{string_as_view(s)}")

"""

# Every integer width at both ends of its range, signed and unsigned.
INT_WIDTHS = PRELUDE + """\
pub fn main() -> i32
    var s: String = string_new()
    let a: i8 = -128
    let b: i8 = 127
    let c: i16 = -32768
    let d: i32 = -2147483648
    let e: i64 = -9223372036854775807 - 1
    let f: i64 = 9223372036854775807
    let g: u8 = 255
    let h: u16 = 65535
    let i: u32 = 4294967295
    let j: u64 = 18446744073709551615
    let z: i64 = 0
    let y: u8 = 0
    format_into(@&s, "i8={a},{b} i16={c} i32={d}\\n")
    format_into(@&s, "i64={e},{f} zero={z},{y}\\n")
    format_into(@&s, "u8={g} u16={h} u32={i} u64={j}\\n")
    show(@s)
    string_drop(@&s)
    return 0
"""


def test_int_widths(tmp_path: Path):
    _assert_parity(tmp_path, "int_widths", INT_WIDTHS, (
        b"i8=-128,127 i16=-32768 i32=-2147483648\n"
        b"i64=-9223372036854775808,9223372036854775807 zero=0,0\n"
        b"u8=255 u16=65535 u32=4294967295 u64=18446744073709551615\n"
    ))


# StrView by value, by reference and as a field; C strings; bool; calls.
VIEWS = PRELUDE + """\
struct Named
    name: StrView
    id: u32

fn tag() -> *u8
    return c"tagged"

fn put(s: @&String, v: @StrView, n: @Named)
    format_into(s, "ref=[{v}] field=[{n.name}] id={n.id}\\n")

pub fn main() -> i32
    var s: String = string_new()
    let v: StrView = "view"
    let long: StrView = "abcdef"
    let part: StrView = StrView { ptr: long.ptr + 1, len: 3 }
    let c: *u8 = c"cstr"
    let t: bool = true
    let n: Named = Named { name: "nm", id: 7 }
    format_into(@&s, "v=[{v}] part=[{part}] c=[{c}] call=[{tag()}]\\n")
    format_into(@&s, "t={t} f={1 > 2} sum={n.id + 1}\\n")
    put(@&s, @v, @n)
    show(@s)
    string_drop(@&s)
    return 0
"""


def test_views_cstrings_bools(tmp_path: Path):
    _assert_parity(tmp_path, "views", VIEWS, (
        b"v=[view] part=[bcd] c=[cstr] call=[tagged]\n"
        b"t=true f=false sum=8\n"
        b"ref=[view] field=[nm] id=7\n"
    ))


# print's splitting rules: `{{` / `}}` are one brace, `\\{` / `\\}` literal
# braces, an unmatched `{` or lone `}` is itself. An LLVM inline-asm
# constraint, the reason c"..." never interpolates, is written with `{{`.
ESCAPES = PRELUDE + """\
pub fn main() -> i32
    var s: String = string_new()
    let x: i64 = 9
    format_into(@&s, "dbl {{x}} close }} open {{\\n")
    format_into(@&s, "esc \\{x\\} val {x}\\n")
    format_into(@&s, "lone } brace, lone { here\\n")
    format_into(@&s, "\\"={{rax}},{{rdi}},~{{rcx}}\\"\\t{x}\\n")
    format_into(@&s, "no placeholders\\n")
    format_into(@&s, c"cstr verbatim\\n")
    format_into(@&s, "{x}{x}")
    format_into(@&s, "\\n")
    show(@s)
    string_drop(@&s)
    return 0
"""


def test_escapes(tmp_path: Path):
    _assert_parity(tmp_path, "escapes", ESCAPES, (
        b"dbl {x} close } open {\n"
        b"esc {x} val 9\n"
        b"lone } brace, lone { here\n"
        b"\"={rax},{rdi},~{rcx}\"\t9\n"
        b"no placeholders\n"
        b"cstr verbatim\n"
        b"99\n"
    ))


# Every sink shape: *String, GrowBuf, a *Vec<u8> reached through a struct
# field (as ritz1's EmitterState.out), and a user type whose push_bytes is an
# impl method. Nothing else here calls vec_push_bytes<u8>: format_into alone
# must make the compiler instantiate it.
SINKS = PRELUDE + """\
struct State
    out: *Vec<u8>

struct Counter
    bytes: i64
    calls: i64

impl Counter
    fn push_bytes(self: @&Counter, data: *u8, len: i64) -> i32
        self.bytes = self.bytes + len
        self.calls = self.calls + 1
        return 0

fn via_ptr(sp: *String)
    format_into(sp, "ptr {1 + 1}\\n")

fn emit_trunc(st: *State, r: i32, v: i32)
    format_into(st.out, "  %{r} = trunc i64 %{v} to i32\\n")

pub fn main() -> i32
    var s: String = string_from("pre:")
    via_ptr(@&s)
    show(@s)

    var g: GrowBuf = growbuf_new()
    format_into(@&g, "grow {3}|")
    format_into(@&g, "buf\\n")
    let gv: StrView = StrView { ptr: g.data, len: g.len }
    print("{gv}")

    var v: Vec<u8> = vec_new<u8>()
    var st: State = State { out: @&v }
    emit_trunc(@&st, 4, 2)
    let vv: StrView = StrView { ptr: v.data, len: v.len }
    print("{vv}")

    var c: Counter = Counter { bytes: 0, calls: 0 }
    format_into(@&c, "ab{12}cd")
    print("counter {c.bytes} {c.calls}\\n")

    string_drop(@&s)
    return 0
"""


def test_sinks(tmp_path: Path):
    _assert_parity(tmp_path, "sinks", SINKS, (
        b"pre:ptr 2\n"
        b"grow 3|buf\n"
        b"  %4 = trunc i64 %2 to i32\n"
        b"counter 6 3\n"
    ))


# The sink expression and every placeholder are evaluated exactly once, left
# to right, and format_into appends: it never clears the buffer.
ONCE = PRELUDE + """\
var g_sink_calls: i64 = 0
var g_next: i64 = 0

fn sink(s: *String) -> *String
    g_sink_calls = g_sink_calls + 1
    return s

fn next() -> i64
    g_next = g_next + 1
    return g_next

pub fn main() -> i32
    var s: String = string_from("keep ")
    format_into(sink(@&s), "{next()} {next()} {next()}\\n")
    show(@s)
    print("sink calls {g_sink_calls}\\n")
    string_drop(@&s)
    return 0
"""


def test_evaluated_once_and_appends(tmp_path: Path):
    _assert_parity(tmp_path, "once", ONCE, b"keep 1 2 3\nsink calls 1\n")


def _assert_rejected(tmp_path: Path, name: str, program: str, needle: str) -> None:
    for compiler in ("ritz0", "ritz1"):
        proc, _ = _build(compiler, tmp_path, name, program)
        out = proc.stdout + proc.stderr
        assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-2000:]}"
        assert needle in out, f"{compiler} rejected {name} without naming it:\n{out[-2000:]}"


REJECTS = {
    # A runtime format string would have to be parsed at run time.
    "non_literal": ("""\
pub fn main() -> i32
    var s: String = string_new()
    let f: StrView = "{x}"
    format_into(@&s, f)
    return 0
""", "must be a string literal"),
    # #1374: a c"..." placeholder would be appended verbatim.
    "cstring_placeholder": ("""\
pub fn main() -> i32
    var s: String = string_new()
    let x: i64 = 1
    format_into(@&s, c"x={x}")
    return 0
""", "do not interpolate"),
    # No push_bytes: nothing to append through.
    "no_push_bytes": ("""\
struct Nope
    n: i64

pub fn main() -> i32
    var n: Nope = Nope { n: 0 }
    format_into(@&n, "x")
    return 0
""", "'Nope' has no push_bytes"),
    # A sink by value would append to a copy.
    "by_value": ("""\
pub fn main() -> i32
    var s: String = string_new()
    format_into(s, "x")
    return 0
""", "not a value"),
    # A struct has no formatted form.
    "unformattable": ("""\
struct P
    x: i64

pub fn main() -> i32
    var s: String = string_new()
    let p: P = P { x: 1 }
    format_into(@&s, "p={p}")
    return 0
""", "cannot format"),
    "arity": ("""\
pub fn main() -> i32
    var s: String = string_new()
    format_into(@&s)
    return 0
""", "takes two arguments"),
}


@pytest.mark.parametrize("name", sorted(REJECTS))
def test_rejected(tmp_path: Path, name: str):
    body, needle = REJECTS[name]
    _assert_rejected(tmp_path, name, "import ritzlib.string\n\n" + body, needle)
