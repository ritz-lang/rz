"""Regression tests for AGAST #1614 / #1529: ritz1 must accept the slice type
`[T]`, as sugar for `Span<T>`.

ritz0 has accepted `[T]` since #1285: `make_slice_type` (ritz0/ritz_ast.py)
desugars it to `NamedType('Span', [T])` the moment the type is built, so every
later pass sees exactly one type. LANGUAGE_SPEC §3.4 records that decision.

ritz1's `type_spec` only had the sized `[N]T`, so any `[T]` failed the whole
item with `cannot parse item starting at 'fn f'`. The fix builds the type
`Span<T>` builds (`Span$T`, a TYPE_STRUCT), so `[T]` works wherever
`Span<T>` does and the two are interchangeable at a call site.

Covered: `[T]` as a param (the #1614 and #1529 repros), a return type, a
local, a struct field, through a pointer, as a generic argument
(`Option<[u8]>`, `Result<[u8], E>`), and mixed with `Span<T>` in both
directions. Controls pin `[N]T`, `[N][M]T` and `[N * 2]T`, which share the
`[` prefix with the new alternative.

ritz0 is the oracle. Each program's expected exit status is checked against
it, so an oracle change shows up as its own failure.
"""

import re
from pathlib import Path

import pytest

from test_ritz1_move_param import _compile, _run

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

SPAN = "import ritzlib.span\n\n"

# Crossers: each takes one spelling and returns the other, so a value changes
# spelling at every call. They also hand a `[u8]` local its value without the
# `@array` initialiser that #2502 refuses.
CROSS = SPAN + """\
fn as_slice(s: Span<u8>) -> [u8]
    return s

fn as_span(s: [u8]) -> Span<u8>
    return s

"""

# name -> (program, expected exit status)
SLICE_FORMS = {
    # #1614's repro: `[u8]` as a param, never read.
    "repro_1614": (SPAN + """\
fn f(p: [u8]) -> i32
    0

pub fn main() -> i32
    let b: [2]u8 = [7, 8]
    return f(@b) + 3
""", 3),
    # #1529's repro, with the `@b` LANGUAGE_SPEC §3.4 requires (a bare `b` is
    # refused: see test_slice_param_rejects_bare_array).
    "param_index_and_len": (SPAN + """\
fn f(a: [u8]) -> i32
    return a[0] as i32 + a.len as i32

pub fn main() -> i32
    var b: [2]u8 = [7, 8]
    return f(@b)
""", 9),
    "param_i32_elements": (SPAN + """\
fn sum(xs: [i32]) -> i32
    var t: i32 = 0
    for i in 0..xs.len
        t = t + xs[i]
    return t

pub fn main() -> i32
    let a: [4]i32 = [1, 2, 3, 4]
    return sum(@a)
""", 10),
    "return_type": (SPAN + """\
fn head(s: Span<u8>, n: i64) -> [u8]
    return s[0..n]

pub fn main() -> i32
    let b: [4]u8 = [5, 6, 7, 8]
    let h = head(@b, 2)
    return h.len as i32 * 10 + h[1] as i32
""", 26),
    "local": (CROSS + """\
pub fn main() -> i32
    let b: [3]u8 = [1, 2, 3]
    let v: [u8] = as_slice(@b)
    return v[2] as i32 + v.len as i32
""", 6),
    "local_from_array": (SPAN + """\
pub fn main() -> i32
    let b: [3]u8 = [1, 2, 3]
    let v: [u8] = @b
    return v[2] as i32 + v.len as i32
""", 6),
    "struct_field": (CROSS + """\
struct Packet
    tag: i32
    data: [u8]

fn weigh(p: Packet) -> i32
    return p.tag + p.data[1] as i32 + p.data.len as i32

pub fn main() -> i32
    let b: [3]u8 = [4, 5, 6]
    let p = Packet { tag: 10, data: as_slice(@b) }
    return weigh(p)
""", 18),
    "struct_field_from_array": (SPAN + """\
struct Packet
    tag: i32
    data: [u8]

fn weigh(p: Packet) -> i32
    return p.tag + p.data[1] as i32 + p.data.len as i32

pub fn main() -> i32
    let b: [3]u8 = [4, 5, 6]
    let p = Packet { tag: 10, data: @b }
    return weigh(p)
""", 18),
    "through_pointer": (CROSS + """\
fn count(s: *[u8]) -> i64
    return s.len

pub fn main() -> i32
    let b: [5]u8 = [1, 1, 1, 1, 1]
    let v: [u8] = as_slice(@b)
    return count(@v) as i32
""", 5),
    "through_pointer_from_array": (SPAN + """\
fn count(s: *[u8]) -> i64
    return s.len

pub fn main() -> i32
    let b: [5]u8 = [1, 1, 1, 1, 1]
    let v: [u8] = @b
    return count(@v) as i32
""", 5),
    # Generic arguments. The payload is a name or a call here; the
    # `*_payload` rows write a range slice straight into `Some(..)` / `Ok(..)`
    # (#2572; test_slice_variant_payload.py covers every box and ctor).
    "option_arg": (CROSS + """\
fn pick(s: [u8], ok: bool) -> Option<[u8]>
    if ok
        return Some(s)
    None

pub fn main() -> i32
    let b: [4]u8 = [2, 4, 6, 8]
    let a = match pick(@b, true)
        Some(s) => s[0] as i32 + s[3] as i32
        None => 99
    let c = match pick(@b, false)
        Some(s) => 50
        None => 7
    return a + c
""", 17),
    "result_arg": (CROSS + """\
fn read_n(data: [u8], n: i64) -> Result<[u8], i32>
    if data.len < n
        return Err(42)
    Ok(as_slice(data))

pub fn main() -> i32
    let buf: [4]u8 = [10, 20, 30, 40]
    let a = match read_n(@buf, 3)
        Ok(s) => s[2] as i32
        Err(e) => e
    let c = match read_n(@buf, 5)
        Ok(s) => 0
        Err(e) => e
    return a + c
""", 72),
    "option_payload": ("import ritzlib.result\n" + SPAN + """\
fn take_prefix(data: Span<u8>, n: i64) -> Option<[u8]>
    if data.len < n
        return None
    Some(data[0..n])

pub fn main() -> i32
    let buf: [4]u8 = [2, 4, 6, 8]
    let a = match take_prefix(@buf, 2)
        Some(s) => s[0] as i32 + s[1] as i32
        None => 99
    let b = match take_prefix(@buf, 9)
        Some(s) => 50
        None => 7
    return a + b
""", 13),
    "result_payload": ("import ritzlib.result\n" + SPAN + """\
fn read_slice(data: [u8], n: i64) -> Result<[u8], i32>
    if data.len < n
        return Err(42)
    Ok(data[0..n])

pub fn main() -> i32
    let buf: [4]u8 = [10, 20, 30, 40]
    let a = match read_slice(@buf, 3)
        Ok(s) => s[2] as i32
        Err(e) => e
    let b = match read_slice(@buf, 5)
        Ok(s) => 0
        Err(e) => e
    return a + b
""", 72),
    # `[T]` and `Span<T>` are one type: either fits the other's slot.
    "slice_value_into_span_param": (CROSS + """\
fn n(s: Span<u8>) -> i64
    return s.len

pub fn main() -> i32
    let b: [3]u8 = [1, 2, 3]
    let v: [u8] = as_slice(@b)
    return n(v) as i32
""", 3),
    "span_value_into_slice_param": (CROSS + """\
fn n(s: [u8]) -> i64
    return s.len + s[0] as i64

pub fn main() -> i32
    let b: [3]u8 = [9, 2, 3]
    let v: Span<u8> = as_span(@b)
    return n(v) as i32
""", 12),
    "slice_return_into_span_local": (CROSS + """\
pub fn main() -> i32
    let b: [2]u8 = [4, 4]
    let v: Span<u8> = as_slice(@b)
    let w: [u8] = v
    let x: Span<u8> = as_span(as_slice(w))
    return x.len as i32 + w[1] as i32
""", 6),
}

# Rows that fail on ritz1 and ritz1_selfhosted for a reason other than `[T]`.
# `Span<T>` written out fails identically (test_slice_and_span_emit_the_same_ir
# checks that), so each is the named ticket's, not #1614's. Strict: a fix
# turns the row XPASS, and the gate red until the entry goes.
RITZ1_GAPS = {
    "local_from_array": "AGAST #2502 — `@array` into a Span local emits invalid IR",
    "struct_field_from_array": "AGAST #2502 — `@array` into a Span field",
    "through_pointer_from_array": "AGAST #2502 — `@array` into a Span local",
}


def _as_span(program: str) -> str:
    """The same program with every `[T]` written `Span<T>`."""
    return re.sub(r"\[(u8|i32)\]", r"Span<\1>", program)


# --- array forms sharing the `[` prefix, pinned against regression ----------

CONTROL_FORMS = {
    "sized_array": ("""\
pub fn main() -> i32
    let a: [3]i32 = [1, 2, 3]
    return a[0] + a[2]
""", 4),
    "nd_array": ("""\
pub fn main() -> i32
    var g: [2][3]i32
    g[1][2] = 6
    g[0][1] = 2
    return g[1][2] + g[0][1]
""", 8),
    # `[N]` with a bare const name: `N` alone also parses as a type, so this
    # pins `[N]T` being tried before `[T]`.
    "const_name_array": ("""\
const N: i32 = 3

pub fn main() -> i32
    var a: [N]u8 = [1, 2, 5]
    return a[2] as i32
""", 5),
    "const_expr_array": ("""\
const N: i32 = 2

pub fn main() -> i32
    var a: [N * 2]u8 = [1, 2, 3, 4]
    return a[3] as i32
""", 4),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(SLICE_FORMS))
def test_slice_type(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    if compiler != "ritz0" and name in RITZ1_GAPS:
        request.applymarker(pytest.mark.xfail(reason=RITZ1_GAPS[name], strict=True))
    program, expected = SLICE_FORMS[name]
    rc = _run(compiler, tmp_path, program)
    assert rc == expected, f"{compiler} {name}: exit {rc}, expected {expected}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(SLICE_FORMS))
def test_slice_and_span_emit_the_same_ir(request, tmp_path, compiler, name):
    """`[T]` IS `Span<T>`: spelling every `[T]` out as `Span<T>` changes
    nothing. Same IR when both compile; the same diagnostics when they don't
    (the RITZ1_GAPS rows, whose failure is then Span's, not `[T]`'s)."""
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    program = SLICE_FORMS[name][0]
    assert _as_span(program) != program, "the rewrite must change something"
    outs = []
    for sub, text in (("slice", program), ("span", _as_span(program))):
        d = tmp_path / sub
        d.mkdir()
        comp, ll = _compile(compiler, d, text)
        diag = (comp.stdout + comp.stderr).replace(str(d), "<dir>")
        ir = ll.read_text().replace(str(d), "<dir>") if ll.exists() else None
        outs.append((comp.returncode, ir, diag))
    (rc_a, ir_a, diag_a), (rc_b, ir_b, diag_b) = outs
    assert "Traceback" not in diag_a + diag_b, diag_a[-2000:] + diag_b[-2000:]
    assert rc_a == rc_b, f"{compiler} {name}: `[T]` exit {rc_a}, `Span<T>` exit {rc_b}:\n{diag_a[-1500:]}"
    assert ir_a == ir_b, f"{compiler} {name}: `[T]` and `Span<T>` emit different IR"
    if ir_a is None:
        assert diag_a == diag_b, f"{compiler} {name}: different diagnostics"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CONTROL_FORMS))
def test_array_type_controls(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    program, expected = CONTROL_FORMS[name]
    rc = _run(compiler, tmp_path, program)
    assert rc == expected, f"{compiler} {name}: exit {rc}, expected {expected}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_slice_param_rejects_bare_array(request, tmp_path: Path, compiler):
    """#1529's literal repro passes `b`, not `@b`. A whole array doesn't fit a
    `Span<T>` slot (§3.4/§13), so it doesn't fit `[T]` either: every compiler
    refuses it with the same message."""
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    comp, ll = _compile(compiler, tmp_path, SPAN + """\
fn f(a: [u8]) -> i32
    return a[0] as i32

pub fn main() -> i32
    var b: [2]u8 = [7, 8]
    return f(b)
""")
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted a bare array:\n{out[-1000:]}"
    assert "Traceback" not in out, out[-2000:]
    assert "a value doesn't fit a reference slot" in out, out[-2000:]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_empty_brackets_rejected(request, tmp_path: Path, compiler):
    """`[]` names no element type: still a parse error, never a crash."""
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    comp, ll = _compile(compiler, tmp_path, """\
fn f(a: []) -> i32
    return 0

pub fn main() -> i32
    return 0
""")
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted `[]`:\n{out[-1000:]}"
    assert "Traceback" not in out, out[-2000:]
    assert not ll.exists(), f"{compiler} wrote an artifact for `[]`"
