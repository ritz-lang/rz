"""AGAST #3085: an unsigned integer widens implicitly by zero-extension.

    var x: u8 = 200
    let w: i64 = x          # was -56 on ritz0: `sext i8 ... to i64`

ritz0's `_convert_type` widened every non-bool integer with `sext`, so a u8,
u16 or u32 with its top bit set turned negative when it landed in a wider
slot: a let/var initialiser, an assignment, an argument, a return, a field,
an array element, a store through a pointer.  ritz1 and ritz1_selfhosted
already zero-extend.  Explicit casts, compares and arithmetic were already
right (#1963, #2361); this is only the implicit widening.

The rows are sized to the code paths (TESTING.md "What a ritz0 pytest case
costs"): every slot kind with a u8 source and its i8 control, every width at
a `let`, and every kind of source expression at a `let`.  The u8/u16/u32
values have the top bit of their width set, so a sign-extension turns them
negative; the i8 control must stay negative.
"""

import pytest
from test_ref_into_value import COMPILERS, _run

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = [pytest.mark.integration, pytest.mark.batched]

# pair -> (source type, slot type, source value, the value in the slot)
PAIRS = {
    "u8_i64": ("u8", "i64", "200", "200"),
    "i8_i64": ("i8", "i64", "-56", "-56"),
    "u16_i32": ("u16", "i32", "60000", "60000"),
    "u32_i64": ("u32", "i64", "4000000000", "4000000000"),
    "u8_u64": ("u8", "u64", "200", "200"),
}

# site -> program body.  `{s}` source type, `{t}` slot type, `{w}` the value
# expected in the slot.  Exit 1 means the value was wrong.
SITES = {
    "let": """\
fn f(x: {s}) -> i32
    let d: {t} = x
    if d != {w}
        return 1
    0
""",
    "assign": """\
fn f(x: {s}) -> i32
    var d: {t} = 0
    d = x
    if d != {w}
        return 1
    0
""",
    "arg": """\
fn g(d: {t}) -> {t}
    d

fn f(x: {s}) -> i32
    if g(x) != {w}
        return 1
    0
""",
    "method_arg": """\
struct K
    k: i32

impl K
    fn get(self, d: {t}) -> {t}
        d

fn f(x: {s}) -> i32
    let k = K {{ k: 0 }}
    if k.get(x) != {w}
        return 1
    0
""",
    "return": """\
fn g(x: {s}) -> {t}
    return x

fn f(x: {s}) -> i32
    if g(x) != {w}
        return 1
    0
""",
    "tail": """\
fn g(x: {s}) -> {t}
    x

fn f(x: {s}) -> i32
    if g(x) != {w}
        return 1
    0
""",
    "field_lit": """\
struct P
    d: {t}

fn f(x: {s}) -> i32
    let p = P {{ d: x }}
    if p.d != {w}
        return 1
    0
""",
    "field_store": """\
struct P
    d: {t}

fn f(x: {s}) -> i32
    var p = P {{ d: 0 }}
    p.d = x
    if p.d != {w}
        return 1
    0
""",
    "elem_store": """\
fn f(x: {s}) -> i32
    var a: [2]{t} = [0, 0]
    a[1] = x
    if a[1] != {w}
        return 1
    0
""",
    "deref_store": """\
fn f(x: {s}) -> i32
    var d: {t} = 0
    let p: *{t} = @&d
    *p = x
    if d != {w}
        return 1
    0
""",
}


def _program(body: str, pair: str) -> str:
    s, t, v, w = PAIRS[pair]
    return f"{body.format(s=s, t=t, w=w)}\npub fn main() -> i32\n    let x: {s} = {v}\n    f(x)\n"


# AGAST #3097: ritz1 stores `*p = x` at the source's width, so an i8 -56
# reaches only the low byte of the i64 (and reads back as 200).
_DEREF_STORE_NARROW = pytest.mark.xfail(strict=True, reason="AGAST #3097")


def _slot_rows():
    for site in sorted(SITES):
        for pair in ("u8_i64", "i8_i64"):
            for compiler in COMPILERS:
                marks = ()
                if site == "deref_store" and pair == "i8_i64" and compiler != "ritz0":
                    marks = (_DEREF_STORE_NARROW,)
                yield pytest.param(site, pair, compiler, marks=marks,
                                   id=f"{site}-{pair}-{compiler}")


@pytest.mark.parametrize("site,pair,compiler", list(_slot_rows()))
def test_every_slot_widens_by_the_source_signedness(tmp_path, compiler, site, pair):
    assert _run(compiler, tmp_path, f"{site}_{pair}", _program(SITES[site], pair)) == 0


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("pair", ["u16_i32", "u32_i64", "u8_u64"])
def test_every_unsigned_width_zero_extends(tmp_path, compiler, pair):
    assert _run(compiler, tmp_path, f"let_{pair}", _program(SITES["let"], pair)) == 0


# source -> program: a u8 of 200 reached through another kind of expression,
# landing in an i64 `let`.
SOURCES = {
    "call": """\
fn get(p: *u8) -> u8
    *p

pub fn main() -> i32
    var x: u8 = 200
    let w: i64 = get(@&x)
    if w != 200
        return 1
    0
""",
    "field": """\
struct B
    b: u8

pub fn main() -> i32
    let s = B { b: 200 }
    let w: i64 = s.b
    if w != 200
        return 1
    0
""",
    "deref": """\
pub fn main() -> i32
    var x: u8 = 200
    let p: *u8 = @&x
    let w: i64 = *p
    if w != 200
        return 1
    0
""",
    "index": """\
pub fn main() -> i32
    let a: [2]u8 = [1, 200]
    let w: i64 = a[1]
    if w != 200
        return 1
    0
""",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("source", sorted(SOURCES))
def test_every_unsigned_source_zero_extends(tmp_path, compiler, source):
    assert _run(compiler, tmp_path, f"src_{source}", SOURCES[source]) == 0
