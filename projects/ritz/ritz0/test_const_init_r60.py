"""One constant-initialiser rule for `const` and global `var` (LARB R60, R75; AGAST #3479).

LANGUAGE_SPEC §4.3: a global `var`'s initialiser, like a const's, is a
*constant initialiser*: a literal (int, float, bool, char, `"…"`), a const,
arithmetic or a cast of constant initialisers, an array or struct literal of
them, or a unit enum variant (R75).  No call runs before `main`; a const or
global of a type with `Drop` is an error.  A struct const is read-only data
like a const array (R48): `@C` is `@S`, `@&C` and a write through it are
errors, and it isn't a pattern.

ritz0 only: ritz1's half is #3480 (until then ritz1 still refuses these
programs; test_global_init_rejected.py pins that).  Each run row is a program
that exits 3 when every value it reads is right, and a distinct code
otherwise; the rows are cut by code path, not by the cross product (TESTING.md,
"What a ritz0 pytest case costs").
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent

# Shared declarations: a struct with every field kind the rule lowers, a
# unit-only enum and an enum with a payload (its unit variant has a data
# buffer to zero).
_DECLS = """\
struct In
    k: i64

struct P
    a: i32
    b: i64
    x: f64
    s: StrView
    c: Color
    n: In

enum Color
    Red
    Blue

enum Shape
    Empty
    Circle(i64)

const K: i64 = 4
const F: f64 = 1.5

fn col(c: Color) -> i32
    match c
        Color.Red => 1
        Color.Blue => 2

fn shp(s: Shape) -> i64
    match s
        Shape.Empty => 7
        Shape.Circle(r) => r

"""

RUN = {
    # R60 table: `var g: f64 = 2.5`; float arithmetic and a float const.
    "float": """\
var g: f64 = 2.5
var h: f64 = F * 2.0 - 0.5
var i: f32 = 0.25
var j: f64 = (K + 0.5) / 8.0

pub fn main() -> i32
    if g != 2.5
        return 10
    if h != 2.5
        return 11
    if i != 0.25
        return 12
    if j != 0.5625
        return 13
    3
""",
    # `K * 2 + 1`, a cast of arithmetic, a char, a wrapping cast.
    "int_arith": """\
var g: i64 = K * 2 + 1
var cg: i64 = (1 + 2) as i64
var ch: u8 = 'A' + 1
var w: u8 = 300 as u8

pub fn main() -> i32
    if g != 9
        return 10
    if cg != 3
        return 11
    if ch != 66
        return 12
    if w != 44
        return 13
    3
""",
    # Array and fill globals, writable.
    "array": """\
var a: [3]i64 = [1, K, K + 1]
var f: [4]i32 = [7; 4]

pub fn main() -> i32
    a[0] = 10
    if a[0] + a[1] + a[2] != 19
        return 10
    if f[0] + f[3] != 14
        return 11
    3
""",
    # A struct global with a float, StrView, enum and nested struct field;
    # an array of structs.
    "struct_global": """\
var p: P = P { a: 5, b: K, x: F, s: "hey", c: Color.Blue, n: In { k: 9 } }
var t: [2]In = [In { k: 1 }, In { k: K }]

pub fn main() -> i32
    p.a = p.a + 1
    if p.a != 6 or p.b != 4
        return 10
    if p.x != 1.5 or p.s.len != 3
        return 11
    if col(p.c) != 2 or p.n.k != 9
        return 12
    if t[0].k + t[1].k != 5
        return 13
    3
""",
    # A StrView global.
    "strview": """\
var sv: StrView = "hello"

pub fn main() -> i32
    if sv.len != 5
        return 10
    3
""",
    # `const C: P = P {…}`: read by field, by value and as `@P` (R48).
    "struct_const": """\
const C: P = P { a: 5, b: 6, x: 0.5, s: "ab", c: Color.Red, n: In { k: 2 } }

fn rd(p: @P) -> i64
    p.b + p.n.k

pub fn main() -> i32
    if C.a + C.b != 11
        return 10
    let q = C
    if q.s.len != 2 or col(q.c) != 1
        return 11
    if rd(@C) != 8
        return 12
    3
""",
    # R75: a unit variant as a const's whole value, a global's, an array
    # element; a payload enum's unit variant.
    "enum_variant": """\
const E: Color = Color.Blue
var g: Color = Color.Blue
var cs: [2]Color = [Color.Red, Color.Blue]
const SH: Shape = Shape.Empty

pub fn main() -> i32
    if col(E) != 2 or col(g) != 2
        return 10
    if col(cs[0]) != 1 or col(cs[1]) != 2
        return 11
    if shp(SH) != 7
        return 12
    g = Color.Red
    if col(g) != 1
        return 13
    3
""",
    # A const table of f64 literals, each the double nearest its literal
    # (ritz-task-2787's sage POW10, which works around it with u64 bits).
    "float_table": """\
const POW10: [6]f64 = [
    1.0e0, 1.0e1, 1.0e2,
    0.1, -2.5e-3,
    1.0e308
]
const FILL: [3]f64 = [F; 3]

pub fn main() -> i32
    var k: i64 = 2
    if POW10[k] != 100.0 or POW10[3] != 0.1 or POW10[4] != -0.0025
        return 10
    if POW10[5] != 1.0e308
        return 11
    if FILL[2] != 1.5
        return 12
    3
""",
    # "a const" is a constant initialiser: a struct const names another.
    "const_of_const": """\
const C: In = In { k: 6 }
const D: In = C
var g: In = C

pub fn main() -> i32
    if D.k + g.k != 12
        return 10
    3
""",
}


def _compile(tmp_path, name, src):
    work = tmp_path / name
    work.mkdir()
    path = work / "main.ritz"
    path.write_text(src)
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(path), "-o", str(ll)], cwd=work, env=env, timeout=300)
    return proc, ll, work


@pytest.mark.parametrize("name", sorted(RUN))
def test_a_constant_initialiser_runs(tmp_path, name):
    proc, ll, work = _compile(tmp_path, name, _DECLS + RUN[name])
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and ll.exists(), f"ritz0 refused {name}:\n{out[-2000:]}"
    exe = work / "main"
    link = fast_link.clang(["clang", "-Wno-override-module", str(ll), "-o", str(exe),
                            "-nostdlib", "-no-pie"], cwd=work, capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-2000:]
    assert subprocess.run([str(exe)], timeout=60, check=False).returncode == 3


_NON_CONST = "global 'g' has a non-constant initializer"
_DROP_TYPE = "struct D\n    v: i64\n\nimpl Drop for D\n    fn drop(self: @&D)\n        pass\n\n"
_HOLDS_DROP = "struct H\n    d: D\n\n"
_MAIN = "\npub fn main() -> i32\n    0\n"
_USE = "\npub fn main() -> i32\n    {}\n    0\n"

# name -> (source with `^` where the error lands, message prefix)
REFUSED = {
    # No call runs before `main`.
    "call": ("fn f() -> i64\n    1\n\nvar g: i64 = ^f()\n" + _MAIN, _NON_CONST),
    # A global is not a const.
    "global": ("var x: i64 = 1\nvar g: i64 = ^x + 1\n" + _MAIN, _NON_CONST),
    "float_global": ("var x: f64 = 1.0\nvar g: f64 = ^x * 2.0\n" + _MAIN, _NON_CONST),
    # R75: payload variants stay refused, whole value or a field.
    "payload_variant": ("var g: Shape = ^Shape.Circle(1)\n" + _MAIN,
                        "global 'g' is a variant with a payload, which isn't a constant initialiser"),
    "payload_variant_field": (
        "struct W\n    s: Shape\n\nconst C: W = W { s: ^Shape.Circle(1) }\n" + _MAIN,
        "const 'C' field 's' is a variant with a payload, which isn't a constant initialiser"),
    # The literal must fit its type (the R51 slot check, before emission).
    "short_array": ("var g: [3]i32 = ^[1, 2]\n" + _MAIN,
                    "an array literal of 2 elements for a `[3]i32`"),
    "missing_field": ("var g: In = ^In { }\n" + _MAIN, "global 'g' has no value for field 'k'"),
    "wrong_struct": ("var g: In = ^P { a: 1 }\n" + _MAIN, "global 'g' is a `P` literal for a `In`"),
    # A const of a type with Drop, or holding one.  A global `var`'s half
    # waits on migrating the globals that have one (AGAST #4079).
    "drop_const": (_DROP_TYPE + "^const C: D = D { v: 1 }\n" + _MAIN,
                   "const 'C' has type `D`, which has Drop: a module-level value is never dropped"),
    "drop_inside": (_DROP_TYPE + _HOLDS_DROP + "^const C: H = H { d: D { v: 1 } }\n" + _MAIN,
                    "const 'C' has type `H`, which has Drop: a module-level value is never dropped"),
    # A struct const is read-only data (R48).  It isn't a pattern: an arm
    # naming it is refused as any binder taking a const's name is.
    "const_mut_borrow": ("const C: In = In { k: 1 }\n\nfn w(p: @&In)\n    p.k = 2\n"
                         + _USE.format("w(^@&C)"),
                         "cannot borrow const `C` as mutable; it is read-only data"),
    "const_field_write": ("const C: In = In { k: 1 }\n" + _USE.format("^C.k = 2"),
                          "cannot assign through const `C`; it is read-only data"),
    "const_pattern": ("const C: Color = Color.Blue\n\nfn m(c: Color) -> i32\n    match c\n"
                      "        ^C => 1\n        _ => 0\n" + _MAIN,
                      "a local can't take the name of a const: 'C'"),
    # There is no module-level `let`.
    "module_let": ("^let g: i64 = 1\n" + _MAIN, "there is no module-level `let`"),
}


def _located(text):
    before = text[:text.index("^")]
    line = before.count("\n") + 1
    return text.replace("^", "", 1), f"{line}:{len(before) - before.rfind(chr(10))}"


@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_non_constant_initialiser_is_a_located_error(tmp_path, name):
    marked, message = REFUSED[name]
    src, where = _located(_DECLS + marked)
    proc, ll, _ = _compile(tmp_path, name, src)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"ritz0 accepted {name}:\n{src}"
    assert "Traceback" not in out and "ValueError" not in out, out[-2000:]
    assert "Parse error" not in out, out[-2000:]
    hits = re.findall(rf"main\.ritz:{where}: (?:error: )?{re.escape(message)}", out)
    assert len(hits) == 1, f"{name}: want {message!r} at {where}:\n{out[-2000:]}"
    assert not ll.exists()
