"""AGAST #3510: ritz1's literal slot rules run on Sema, before emission (#1816).

THE CHANGE

literal_slot.ritz (AGAST #2341: a literal takes its slot's type; #3083, #2138
the literals no type holds; #3112 R21's literal operand; #3440 a `c"..."` in a
view slot) ran mid-lowering on EmitterState, at each slot the emitter reached.
Its refusal, lit_check_fits, was one of the emitter checks
tools/ritz1_emitter_checks.allow listed (that allowlist is now gone: the
check freeze is the grep being empty, #1816).  It now takes `sm: *Sema` and
runs from sema_walk.ritz at the slots bool_check visits.  What it learns it
writes on the AST for the emitter to read: a `"..."` in a `*u8` slot becomes a
`c"..."`, and a `/` or `%` in a wider integer slot records it (Expr.slot_type,
#3225).  The type of an element slot (`p[i] = v`, `*a[i] = v`) is
index_through's type fact, now answered on Sema by sema_type.ritz.

The words are the shared tables' (test_string_literal_slots.py,
test_literal_type_context.py, test_literal_takes_operand_type.py,
test_wider_slot_widens.py, ..), unchanged; the commit compared every file of
ritz0/test, ritzlib, examples and ritz1/src, and every program the ritz1
pytest files compile, against the pre-move compilers.

THE TESTS

One program, both ritz1 compilers: a literal that doesn't fit each kind of
slot (a return, a fn's tail arm, a `let`, an assignment, an element through a
`[N]*T` element and through a `*[N]T`, a call's and a method's argument, a
field, R21's operand, an array element), a `c"..."` in a StrView; then a
`*[2][3]i32` given a `*[2][4]i32`, ref_check's slot error: on the emitter it
was no longer printed after these, and since AGAST #4011 it is Sema's, so it
is again, in walk order.  The literal inside
`sizeof(..)` is never lowered, so it isn't judged, as on the emitter.
"""

import re

import pytest

from test_ref_into_value import _compile

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

PROGRAM = """\
struct P
    b: u8

impl P
    fn put(self: *P, v: u8)
        self.b = v

fn take(v: u8) -> u8
    v

fn ret() -> i16
    return 70000

fn tail(c: bool) -> u8
    if c
        1
    else
        256

fn main() -> i32
    let a: u8 = 300
    var n: i16 = 0
    n = 70000
    var xs: [3]i16
    var ps: [2]*i16
    ps[0] = @xs[0]
    *ps[0] = 70000
    var buf: [4]u8
    let pb: *[4]u8 = @buf
    pb[1] = 300
    take(300)
    var p: P = P { b: 300 }
    p.put(256)
    let w: u8 = (n as u8) + 300
    let sv: StrView = c"no"
    let arr: [2]u8 = [1, 999]
    let s: i64 = sizeof(take(300))
    var g: [2][4]i32
    let rp: *[2][3]i32 = @g
    0
"""

WANTED = [
    ("12:12", "`70000` does not fit in `i16`"),
    ("18:9", "`256` does not fit in `u8`"),
    ("21:17", "`300` does not fit in `u8`"),
    ("23:9", "`70000` does not fit in `i16`"),
    ("27:14", "`70000` does not fit in `i16`"),
    ("30:13", "`300` does not fit in `u8`"),
    ("31:10", "`300` does not fit in `u8`"),
    ("32:23", "`300` does not fit in `u8`"),
    ("33:11", "`256` does not fit in `u8`"),
    ("34:29", "`300` does not fit in `u8`"),
    ("35:23", 'a `c"..."` literal is a `*u8`, not a `StrView`: write a plain `"..."` literal'),
    ("36:26", "`999` does not fit in `u8`"),
    ("39:26", "a reference to one type doesn't fit a reference to another: cast it with `as`"),
]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_literal_slot_errors_stop_the_compile_before_emission(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_literal", PROGRAM)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)
    assert found == WANTED, f"{compiler}:\n{out}"


# AGAST #3029's array payloads: the `[N]T` a variant declares is the slot, as
# the emitter's emit_array_payload_into had it, whether the variant is named
# (`E.V`, `V`) or carried by the Option / Result its slot names.
PAYLOAD = """\
import ritzlib.option

enum E
    V([2]u8)
    W([2]*u8)

fn opt(c: bool) -> Option<[2]u8>
    if c
        Some([7, 900])
    else
        None

fn main() -> i32
    let e: E = E.V([1, 300])
    let f: E = V([1, 301])
    var o: Option<[2]u8> = Some([3, 302])
    o = Some([1, 903])
    let w: E = E.W(["a", "b"])
    0
"""

_PTR_LITERAL = ('a string literal is a `StrView`; a `*u8` slot takes `c"..."` '
                '(C interop only) — or use a `StrView` API (S-TEXT-1)')

PAYLOAD_WANTED = [
    ("9:18", "`900` does not fit in `u8`"),
    ("14:24", "`300` does not fit in `u8`"),
    ("15:22", "`301` does not fit in `u8`"),
    ("16:37", "`302` does not fit in `u8`"),
    ("17:18", "`903` does not fit in `u8`"),
    # AGAST #4694: `E.W([2]*u8)`'s array payload is a `*u8` slot per element,
    # same as any other, so `"a"` / `"b"` are refused there too.
    ("18:21", _PTR_LITERAL),
    ("18:26", _PTR_LITERAL),
]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_array_payload_elements_land_in_the_variants_array(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_literal_payload", PAYLOAD)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)
    assert found == PAYLOAD_WANTED, f"{compiler}:\n{out}"


# float_slot (AGAST #2945, #3313): Sema finds an integer's source type at an
# f32 / f64 slot, refuses an inexact one, and notes an exact unsigned one for
# the emitter's `uitofp` (a u32 sits zero-extended in its i64 register, so
# `sitofp` reads the same number: only the IR tells them apart).  A block arm
# ending in its own `let` is typed off that `let`'s annotation, as the
# emitter's table had it.
FLOAT_OK = """\
fn widen(x: u32, n: i32) -> f64
    let a: f64 = x
    let b: f64 = n
    a + b

fn arm(c: bool, x: u32) -> f64
    let a: f64 = if c
        let y: u32 = x
        y
    else
        1
    a

fn main() -> i32
    0
"""

FLOAT_BAD = """\
fn arm(c: bool, x: i64) -> f64
    let a: f64 = if c
        let y: i64 = x
        y
    else
        1
    a

fn main() -> i32
    0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_unsigned_source_converts_by_uitofp(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_float_ok", FLOAT_OK)
    assert comp.returncode == 0 and ll.exists(), f"{compiler}:\n{comp.stdout + comp.stderr}"
    ir = ll.read_text()
    # `x` and the arm's `y` (both u32) by uitofp; `n` (i32) and the `1` by sitofp.
    assert ir.count("= uitofp i64") == 2, ir
    assert ir.count("= sitofp i64") == 2, ir


@pytest.mark.parametrize("compiler", COMPILERS)
def test_block_arm_local_into_float_slot_is_judged(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_float_bad", FLOAT_BAD)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)
    assert found == [("4:9", "implicit conversion from `i64` to `f64` can lose precision: write `<expr> as f64`")], f"{compiler}:\n{out}"
