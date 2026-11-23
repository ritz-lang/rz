"""AGAST #201 (#198 Phase 2): `{expr:spec}` format specs in print / eprint /
format_into placeholders.

A placeholder's spec is the text after its last top-level `:` (not inside
nested `()`, `[]`, `{}` or a string / char literal). The v1 specs are
ritzlib/fmt/spec.ritz `fmt_spec_parse`'s grammar:

    ?               Debug
    <N  >N  ^N      alignment in a width N
    [0][N]R         R one of x X b o; a leading 0 needs a width

with N decimal digits <= 4096. Any other spec is a compile error at the
literal, the same text from all three compilers.

Printing a spec is AGAST #202 (through ritzlib.fmt's Display). `?` prints on
every compiler since AGAST #4381 ported the dispatch to ritz1: Debug, with a
struct's fields auto-derived when it has no impl. Every other spec is still
parsed and refused at the emitter, so no program silently prints its value
unformatted.

    INVALID      each unknown spec, refused with SPEC_MSG
    NOT_PRINTED  each remaining valid spec, refused with LATER_MSG (print,
                 eprint and format_into)
    test_debug_spec_prints_a_scalar
                 `{x:?}` runs on ritz0, ritz1 and ritz1_selfhosted
    test_placeholders_without_a_spec_are_unchanged
                 `{x}`, a call, `{{x}}`, a struct literal and a char
                 literal holding `:` still print the same bytes
"""

import subprocess

import pytest

from test_ref_into_value import COMPILERS, _assert_refused, _compile, _link

pytestmark = [pytest.mark.integration]


def SPEC_MSG(expr, spec):
    return (f"unknown format spec `{spec}` in `{{{expr}:{spec}}}`: the v1 specs are "
            "x X b o, a zero-padded width (08x), <N >N ^N and ?")


def LATER_MSG(spec):
    return f"format spec `{spec}` is parsed but not printed until AGAST #202; drop `:{spec}` for now"


# format_into's sink: counts the bytes appended and sums them.
SINK = """\
struct Sink
    bytes: i64
    sum: i64

impl Sink
    fn push_bytes(self: @&Sink, data: Span<u8>) -> i32
        var i: i64 = 0
        while i < data.len
            self.sum = self.sum + (*(data.ptr + i)) as i64
            i = i + 1
        self.bytes = self.bytes + data.len
        return 0

"""


def _prog(line):
    return (SINK +
            "pub fn main() -> i32\n"
            "    let x: i32 = 42\n"
            "    let s: StrView = \"ab\"\n"
            "    var buf: Sink = Sink { bytes: 0, sum: 0 }\n"
            f"    {line}\n"
            "    0\n")


INVALID = {
    "d": ('print(^"{x:d}\\n")', "x", "d"),
    "bare_align": ('print(^"{x:<}\\n")', "x", "<"),
    "align_radix": ('print(^"{x:<4x}\\n")', "x", "<4x"),
    "zero": ('print(^"{x:0}\\n")', "x", "0"),
    "width_only": ('print(^"{x:8}\\n")', "x", "8"),
    "zero_no_width": ('print(^"{x:0x}\\n")', "x", "0x"),
    "two_radix": ('print(^"{x:xx}\\n")', "x", "xx"),
    "fill": ('print(^"{x:*<8}\\n")', "x", "*<8"),
    "alt_debug": ('print(^"{x:#?}\\n")', "x", "#?"),
    "precision": ('print(^"{x:.3}\\n")', "x", ".3"),
    "empty": ('print(^"{x:}\\n")', "x", ""),
    "space": ('print(^"{x: x}\\n")', "x", " x"),
    "too_wide": ('print(^"{x:>4097}\\n")', "x", ">4097"),
    "expr_trimmed": ('print(^"{ x + 1 :q}\\n")', "x + 1", "q"),
    "last_colon": ('eprint(^"{x:x:d}\\n")', "x:x", "d"),
    "format_into": ('format_into(@&buf, ^"{x:y}")', "x", "y"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(INVALID))
def test_an_unknown_spec_is_refused(tmp_path, compiler, name):
    line, expr, spec = INVALID[name]
    _assert_refused(compiler, tmp_path, f"bad_{name}", _prog(line), SPEC_MSG(expr, spec))


NOT_PRINTED = {
    "zero_hex": ('print(^"{x:08x}\\n")', "08x"),
    "hex": ('print(^"{x:x}\\n")', "x"),
    "bin_width": ('print(^"{x:8b}\\n")', "8b"),
    "oct": ('eprint(^"{x:o}\\n")', "o"),
    "left": ('print(^"{s:<4}")', "<4"),
    "right": ('print(^"[{s:>10}]")', ">10"),
    "centre_max": ('print(^"{s:^4096}")', "^4096"),
    "format_into": ('format_into(@&buf, ^"{x:X}")', "X"),
    "after_plain": ('print(^"{x} {x:X}\\n")', "X"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(NOT_PRINTED))
def test_a_valid_spec_is_refused_until_202(tmp_path, compiler, name):
    line, spec = NOT_PRINTED[name]
    _assert_refused(compiler, tmp_path, f"later_{name}", _prog(line), LATER_MSG(spec))


# `?` prints on every compiler since AGAST #4381 ported ritz1's Display/Debug
# dispatch. A scalar's Debug is its intrinsic form, so no Writer is needed.
@pytest.mark.parametrize("compiler", COMPILERS)
def test_debug_spec_prints_a_scalar(tmp_path, compiler):
    comp, ll, work = _compile(compiler, tmp_path, "debug_scalar",
                              _prog('print("{x:?}\\n")'))
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} refused:\n{comp.stdout}{comp.stderr}")
    link, exe = _link(compiler, ll, work)
    assert link.returncode == 0, link.stderr[-2000:]
    run = subprocess.run([str(exe)], capture_output=True, timeout=60)
    assert run.returncode == 0
    assert run.stdout == b"42\n", f"{compiler}: {run.stdout!r}"


UNCHANGED = SINK + """\
struct P
    x: i32
    y: i32

fn f(a: i32, b: i32) -> i32
    a * 10 + b

fn g(c: u8) -> i32
    c as i32

fn py(p: P) -> i32
    p.y

pub fn main() -> i32
    let x: i32 = 42
    let a: i32 = 3
    let b: i32 = 4
    print("x={x} f={f(a, b)} esc={{x}} p={py(P { x: 7, y: 8 })} c={g(':')}\\n")
    eprint("e={x}\\n")
    var buf: Sink = Sink { bytes: 0, sum: 0 }
    format_into(@&buf, "fi={x} {{}} {py(P { x: 1, y: 2 })}\\n")
    print("sink {buf.bytes} {buf.sum}\\n")
    0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_placeholders_without_a_spec_are_unchanged(tmp_path, compiler):
    comp, ll, work = _compile(compiler, tmp_path, "unchanged", UNCHANGED)
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused:\n{comp.stdout}{comp.stderr}"
    link, exe = _link(compiler, ll, work)
    assert link.returncode == 0, link.stderr[-2000:]
    run = subprocess.run([str(exe)], capture_output=True, timeout=60)
    assert run.returncode == 0
    assert run.stdout == b"x=42 f=34 esc={x} p=8 c=58\nsink 11 742\n", f"{compiler}: {run.stdout!r}"
    assert run.stderr == b"e=42\n", f"{compiler}: {run.stderr!r}"
