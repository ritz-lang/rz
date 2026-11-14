"""AGAST #2576: an un-annotated `let t = r.unwrap()` takes the payload's type.

    fn mk() -> Result<Vec<E>, i32>
    let tables = mk().unwrap()
    assert tables.len() == 2          # ritz1: "cannot determine receiver type"
    assert tables[0].offset == 64     # ritz1: "unhandled EXPR_MEMBER"

`.unwrap()` on an Option / Result is ritz1's try_emit_enum_unwrap intrinsic,
which has no FnDef, so the let's EXPR_METHOD arm found no return type and
left the slot i64: every use of `t` was refused, unlocated.  angelo's
loader/ttf.ritz [[test]] fns hit it (`parse_table_directory(..).unwrap()`).

ritz0 compiles [[test]] fns into a bin build too (as `internal` fns), so ritz1
compiling them is right; the gap was the type.  ritz0 is the oracle: every row
exits 0, and a failed check returns its own number.
"""

import pytest

from test_ritz1_for_header import COMPILERS, compile_with, run_with  # noqa: F401  (fixtures)

pytestmark = pytest.mark.batched

_TYPES = """\
import ritzlib.gvec

struct Tag
    v: u32

impl Tag
    pub fn eq({self}, o: Tag) -> bool
        self.v == o.v

struct E
    tag: Tag
    offset: u32

struct H
    k: u32

impl H
    pub fn res(self: @H) -> Result<{P}, i32>
        Ok({make_self})

    pub fn opt(self: @H) -> Option<{P}>
        Some({make_self})

fn mk_res(k: u32) -> Result<{P}, i32>
    Ok({make_k})

fn mk_opt(k: u32) -> Option<{P}>
    Some({make_k})

"""

# How a payload is built from `k`, and how main checks it.  Tag.eq takes
# `self` by value, as angelo's types.ritz does.  E is a struct
# whose first field is itself a struct with a method; Vec<E> is a generic
# instance (`%Vec$E`), indexed then read through.
PAYLOADS = {
    "struct": (
        "E",
        "E {{ tag: Tag {{ v: {k} }}, offset: {k} + 1 }}",
        """\
    if not t.tag.eq(Tag { v: 7 })
        return 1
    if t.offset != 8
        return 2
""",
    ),
    "vec": (
        "Vec<E>",
        "vec_of({k})",
        """\
    if t.len() != 2
        return 1
    if not t[0].tag.eq(Tag { v: 7 })
        return 2
    if t[1].offset != 64
        return 3
""",
    ),
}

_VEC_OF = """\
fn vec_of(k: u32) -> Vec<E>
    var v: Vec<E> = vec_new<E>()
    v.push(E { tag: Tag { v: k }, offset: k + 1 })
    v.push(E { tag: Tag { v: 2 }, offset: 64 })
    v

"""

# Where the Option / Result comes from: a free fn's result, a method's, or
# a local already bound to one.
SOURCES = {
    "call": ("", "mk_{c}(7)"),
    "method": ("    let h = H {{ k: 7 }}\n", "h.{c}()"),
    "local": ("    let r = mk_{c}(7)\n", "r"),
}


def _program(payload: str, carrier: str, source: str, recv: str = "self") -> str:
    ty, make, checks = PAYLOADS[payload]
    head = _TYPES.format(
        self=recv, P=ty, make_k=make.format(k="k"), make_self=make.format(k="self.k")
    )
    if payload == "vec":
        head += _VEC_OF
    pre, src = SOURCES[source]
    return (
        head
        + "pub fn main() -> i32\n"
        + pre.format(c=carrier)
        + f"    let t = {src.format(c=carrier)}.unwrap()\n"
        + checks
        + "    0\n"
    )


# Payload x source on Result; Option on the call path only: the carrier
# changes the payload lookup's family, not where the receiver's type comes from.
ROWS = [(p, "res", s) for p in PAYLOADS for s in SOURCES] + [
    (p, "opt", "call") for p in PAYLOADS
]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("payload,carrier,source", ROWS)
def test_unwrap_let_takes_payload_type(run_with, payload, carrier, source, compiler):
    name = f"unwrap_{payload}_{carrier}_{source}"
    assert run_with(compiler, name, _program(payload, carrier, source)) == 0


# `self: @Tag` borrows `t[0].tag`, so its address is taken.  ritz0 can't index
# the inferred `%Vec$E` local on that lvalue path (#3237); ritz1 runs it.
@pytest.mark.integration
@pytest.mark.parametrize(
    "compiler",
    [
        pytest.param(c, marks=pytest.mark.xfail(strict=True, reason="#3237"))
        if c == "ritz0"
        else c
        for c in COMPILERS
    ],
)
def test_unwrap_let_borrowed_receiver(run_with, compiler):
    program = _program("vec", "res", "call", recv="self: @Tag")
    assert run_with(compiler, "unwrap_borrowed_receiver", program) == 0
