"""AGAST #2945: an integer converts implicitly into a float slot only when exact.

    let x: u32 = 4000000000
    let d: f64 = x          # was -294967296.0: ritz0 sitofp'd every int
    let e: f64 = big_i64    # now an error: write `big_i64 as f64`

LANGUAGE_SPEC §7.5 "Integer and float conversions" (Aaron, 2026-11-13): a
non-literal integer converts implicitly into a float slot only when every
value of its type is exact there -- into f64: i8 i16 i32 u8 u16 u32; into
f32: i8 i16 u8 u16 -- and by its own signedness (uitofp for unsigned).  Every
other pair is one located error asking for `as`.  Integer literals are
unaffected.

The rows are sized to the code paths (TESTING.md "What a ritz0 pytest case
costs"): each slot kind is its own conversion site in ritz1 (let, assignment,
free-call argument, method argument, return, struct field), and each pair
picks one instruction (uitofp to double, uitofp to float, sitofp).  ritz1
keeps a u8/u16/u32 zero-extended in its i64 register, so its run rows pass
with sitofp too; its refusal rows are what show each site is checked.
"""

import pytest
from float_rules import int_into_float_inexact
from test_ref_into_value import COMPILERS, _assert_refused, _run

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = [pytest.mark.integration, pytest.mark.batched]

# pair -> (source type, slot type, source value, the value as a float literal)
# The unsigned values have the top bit of their width set, so a signed
# conversion turns them negative; i32 is the control that must stay negative.
EXACT = {
    "u32_f64": ("u32", "f64", "4000000000", "4000000000.0"),
    "u16_f32": ("u16", "f32", "40000", "40000.0"),
    "i32_f64": ("i32", "f64", "-2000000000", "-2000000000.0"),
}

# site -> program body.  `{s}` source type, `{f}` float type, `{v}` source
# value, `{fv}` expected float literal.  Exit 1 means the value was wrong.
SITES = {
    "let": """\
fn f(x: {s}) -> i32
    let d: {f} = x
    let e: {f} = {fv}
    if d != e
        return 1
    0
""",
    "assign": """\
fn f(x: {s}) -> i32
    var d: {f} = 0.0
    d = x
    let e: {f} = {fv}
    if d != e
        return 1
    0
""",
    "arg": """\
fn g(d: {f}) -> {f}
    d

fn f(x: {s}) -> i32
    let e: {f} = {fv}
    if g(x) != e
        return 1
    0
""",
    "method_arg": """\
struct K
    k: i32

impl K
    fn get(self, d: {f}) -> {f}
        d

fn f(x: {s}) -> i32
    let k = K {{ k: 0 }}
    let e: {f} = {fv}
    if k.get(x) != e
        return 1
    0
""",
    "return": """\
fn g(x: {s}) -> {f}
    return x

fn f(x: {s}) -> i32
    let e: {f} = {fv}
    if g(x) != e
        return 1
    0
""",
    "field": """\
struct P
    d: {f}

fn f(x: {s}) -> i32
    let p = P {{ d: x }}
    let e: {f} = {fv}
    if p.d != e
        return 1
    0
""",
}


def _exact(site: str, pair: str) -> str:
    s, f, v, fv = EXACT[pair]
    body = SITES[site].format(s=s, f=f, v=v, fv=fv)
    return f"{body}\npub fn main() -> i32\n    let x: {s} = {v}\n    f(x)\n"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("pair", sorted(EXACT))
@pytest.mark.parametrize("site", sorted(SITES))
def test_exact_integer_converts_by_its_signedness(tmp_path, compiler, site, pair):
    assert _run(compiler, tmp_path, f"{site}_{pair}", _exact(site, pair)) == 0


# name -> (source type, slot type, program with `^` at the refused value).
# i64 -> f64 at every site; the other inexact pairs at a `let`.
REFUSED = {
    "let_i64_f64": ("i64", "f64", """\
fn f(x: i64) -> f64
    let d: f64 = ^x
    d
"""),
    "assign_i64_f64": ("i64", "f64", """\
fn f(x: i64) -> f64
    var d: f64 = 0.0
    d = ^x
    d
"""),
    "arg_i64_f64": ("i64", "f64", """\
fn g(d: f64) -> f64
    d

fn f(x: i64) -> f64
    g(^x)
"""),
    "method_arg_i64_f64": ("i64", "f64", """\
struct K
    k: i32

impl K
    fn get(self, d: f64) -> f64
        d

fn f(x: i64) -> f64
    let k = K { k: 0 }
    k.get(^x)
"""),
    "field_i64_f64": ("i64", "f64", """\
struct P
    d: f64

fn f(x: i64) -> f64
    let p = P { d: ^x }
    p.d
"""),
    "return_i64_f64": ("i64", "f64", """\
fn f(x: i64) -> f64
    return ^x
"""),
    "let_u64_f64": ("u64", "f64", """\
fn f(x: u64) -> f64
    let d: f64 = ^x
    d
"""),
    "let_i32_f32": ("i32", "f32", """\
fn f(x: i32) -> f32
    let d: f32 = ^x
    d
"""),
    "let_u32_f32": ("u32", "f32", """\
fn f(x: u32) -> f32
    let d: f32 = ^x
    d
"""),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_inexact_integer_is_refused(tmp_path, compiler, name):
    src, dst, body = REFUSED[name]
    marked = body + "\npub fn main() -> i32\n    0\n"
    _assert_refused(compiler, tmp_path, name, marked, int_into_float_inexact(src, dst))


# Every refused pair compiles with `as` (keeping #2192's semantics), and
# integer literals are unaffected, inexact ones included.
WITH_AS_AND_LITERALS = """\
fn f(a: i64, b: u64, c: i32, d: u32) -> i32
    let w: f64 = a as f64
    let x: f64 = b as f64
    let y: f32 = c as f32
    let z: f32 = d as f32
    if w != 0.0 - 5.0 or x != 13835058055282163712.0 or y != 0.0 - 7.0 or z != 4000000000.0
        return 1
    let p: f64 = 4000000000
    let q: f32 = 16777216
    let r: f64 = 0 - 3
    let t: f64 = -3
    if p != 4000000000.0 or q != 16777216.0 or r != 0.0 - 3.0 or t != r
        return 2
    0

pub fn main() -> i32
    let a: i64 = -5
    let b: u64 = 13835058055282163712
    let c: i32 = -7
    let d: u32 = 4000000000
    f(a, b, c, d)
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_as_and_literals_still_convert(tmp_path, compiler):
    assert _run(compiler, tmp_path, "as_and_literals", WITH_AS_AND_LITERALS) == 0
