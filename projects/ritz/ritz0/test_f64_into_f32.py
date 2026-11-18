"""AGAST #3802 (LARB R70): an f64 value into an f32 slot needs `as f32`.

    let x: f64 = 2.0
    let n: f32 = x          # was a silent fptrunc; now an error
    let m: f32 = y * x      # y: f32 -- the product is an f64, same error

LANGUAGE_SPEC §7.5 "Float narrowing": an f64 into an f32 slot (let/var
initialiser, assignment, argument, return, field, array element) is one
located error, "implicit conversion from `f64` to `f32` can lose precision:
write `<expr> as f32`".  Exempt: a float literal, and a constant expression
of float literals (evaluated as f64, rounded once).  f32 into f64 stays
implicit.

The rows are sized to the code paths (TESTING.md "What a ritz0 pytest case
costs"): one refusal per slot kind, since each reaches the conversion from
its own emitter site; one row for the f32*f64 product and one for an if
whose f64 arm is not a literal; and one accepted program holding every
exemption, including an if whose other arm is a literal (it merges at f32).  ritz1's half is #3998, so the refusal rows
are ritz0's alone; the accepted program runs on every compiler, which both
accept today.  Two shapes are ritz0's alone (RITZ0_ONLY, below) for
separate ritz1 bugs.
"""

import pytest
from float_rules import f64_into_f32
from test_ref_into_value import COMPILERS, _assert_refused, _run

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = [pytest.mark.integration, pytest.mark.batched]

NARROW = f64_into_f32()

# name -> program with `^` at the refused value.
REFUSED = {
    "let": """\
fn f(x: f64) -> f32
    let d: f32 = ^x
    d
""",
    "var": """\
fn f(x: f64) -> f32
    var d: f32 = ^x
    d
""",
    "assign": """\
fn f(x: f64) -> f32
    var d: f32 = 0.0
    d = ^x
    d
""",
    "arg": """\
fn g(d: f32) -> f32
    d

fn f(x: f64) -> f32
    g(^x)
""",
    "method_arg": """\
struct K
    k: i32

impl K
    fn get(self, d: f32) -> f32
        d

fn f(x: f64) -> f32
    let k = K { k: 0 }
    k.get(^x)
""",
    "return": """\
fn f(x: f64) -> f32
    return ^x
""",
    "tail": """\
fn f(x: f64) -> f32
    ^x
""",
    "field": """\
struct P
    d: f32

fn f(x: f64) -> f32
    let p = P { d: ^x }
    p.d
""",
    "array_elem": """\
fn f(x: f64) -> f32
    let a: [2]f32 = [1.0, ^x]
    a[0]
""",
    "if_arm": """\
fn f(x: f64, y: f32, c: bool) -> f32
    let q = if c
        y
    else
        x
    let d: f32 = ^q
    d
""",
    "product": """\
fn f(x: f64, y: f32) -> f32
    let d: f32 = ^y * x
    d
""",
}


@pytest.mark.parametrize("name", sorted(REFUSED))
def test_f64_into_f32_is_refused(tmp_path, name):
    marked = REFUSED[name] + "\npub fn main() -> i32\n    0\n"
    _assert_refused("ritz0", tmp_path, f"f64_f32_{name}", marked, NARROW)


# Every exemption, and `as f32`, in one program.  Exit n names the first
# value that came out wrong.
ACCEPTED = """\
struct P
    d: f32

fn g(d: f32) -> f32
    d

fn lit_return() -> f32
    return 0.1

fn f(x: f64, y: f32, c: bool) -> i32
    let a: f32 = 0.1
    let b: f32 = 0.0 - 7.5
    let e: f32 = -(1.0 / 4.0)
    let h: f32 = x as f32
    let k: f32 = (y * x) as f32
    let m: f32 = if c then 1.5 else 2.5
    let p = P { d: 0.25 }
    let arr: [2]f32 = [0.5, 1.0 / 8.0]
    var v: f32 = 0.0
    v = 3.25
    let q = if c
        y / 2.0
    else
        0.0
    let r: f32 = q
    let t = if c
        0.0
    else
        y
    let t32: f32 = t
    if a != (0.1 as f32)
        return 1
    if b != (0.0 - 7.5) as f32 or e != (0.0 - 0.25) as f32
        return 2
    if h != (2.5 as f32) or k != (7.5 as f32)
        return 3
    if m != (1.5 as f32) or p.d != (0.25 as f32) or arr[1] != (0.125 as f32)
        return 4
    if v != (3.25 as f32) or g(0.75) != (0.75 as f32) or lit_return() != (0.1 as f32)
        return 5
    if r != (1.5 as f32) or t32 != 0.0
        return 6
    0

pub fn main() -> i32
    let x: f64 = 2.5
    let y: f32 = 3.0
    f(x, y, true)
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_literals_as_and_widening_still_convert(tmp_path, compiler):
    assert _run(compiler, tmp_path, "f64_f32_accepted", ACCEPTED) == 0


# ritz0 alone, for two separate ritz1 bugs filed from this ticket: f32 into
# f64 stays implicit (at a let, an assignment and an argument; ritz1 omits the
# fpext for an f32 parameter), and a match of literal arms assigned into an
# f32 var narrows (ritz1 stores the double; this is the row that reaches the
# match exemption, since an annotated let converts each arm on its own).
RITZ0_ONLY = """\
fn wide(d: f64) -> f64
    d

fn f(y: f32, c: bool) -> i32
    let w: f64 = y
    var v: f64 = 0.0
    v = y
    if w != 3.0 or v != 3.0 or wide(y) != 3.0
        return 1
    var u: f32 = 0.0
    u = match c
        true => 1.5
        false => 2.5
    if u != (1.5 as f32)
        return 2
    0

pub fn main() -> i32
    f(3.0, true)
"""


def test_widening_and_match_narrowing(tmp_path):
    assert _run("ritz0", tmp_path, "f32_f64_ritz0_only", RITZ0_ONLY) == 0
