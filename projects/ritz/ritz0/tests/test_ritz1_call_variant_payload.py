"""AGAST #2595: a static or instance method's struct result as a variant payload.

    impl G
        pub fn empty() -> G
    fn f() -> Option<G>
        return Some(G.empty())  # ritz1: `store i64 %.8, ptr` of a %G: clang refuses

ritz1's variant constructor named a free fn's struct return (`Some(mk())`) and,
since #2572, a method on a typed local (`Some(v.slice(..))`), but not a static
method: `G.empty()`'s receiver is a type, not a local, so method_recv_type found
nothing and the `%G` aggregate was stored as an i64.  angelo's font.ritz
(`return Some(GlyphOutline.empty())`) hits it.

Every row builds the variant from a free fn, an instance method and a static
method, for `Some`, `Ok`, `Err` and a user enum's tuple variant, in a `return`
and in a tail, and matches it in main.  G mixes i16, i64 and f32 fields so a
wrong layout or width fails a check.  ritz0 is the oracle: each program
returns the number of the first check that failed, so every row must exit 0.
"""

import pytest

from test_ritz1_array_ptr_element import (  # noqa: F401  (fixtures)
    COMPILERS, run_with)

# How f gets its G.  `c` is a C holding the i16; the others take it as an arg.
SOURCES = {
    "free_fn": "mk(k)",
    "method": "c.mk(k)",
    "static_method": "G.make(k)",
}

# ctor -> (f's return type, constructor, main's pattern)
CTORS = {
    "Some": ("Option<G>", "Some", "Some"),
    "Ok": ("Result<G, i32>", "Ok", "Ok"),
    "Err": ("Result<i32, G>", "Err", "Err"),
    "user_enum": ("E", "E.Has", "E.Has"),
}

# `return` the variant from a branch, or yield it as f's tail.
PLACES = {
    "return": "    if k > 0\n        return {ctor}({src})\n    {ctor}({src})\n",
    "tail": "    {ctor}({src})\n",
}

_PROGRAM = """\
import ritzlib.option
import ritzlib.result

struct G
    a: i16
    b: i64
    c: f32

enum E
    Has(G)
    Empty

struct C
    d: i64

impl G
    pub fn make(k: i16) -> G
        G {{ a: k, b: -5000000000, c: 2.5 }}

impl C
    pub fn mk(self: @C, k: i16) -> G
        G {{ a: k, b: self.d, c: 2.5 }}

fn mk(k: i16) -> G
    G {{ a: k, b: -5000000000, c: 2.5 }}

fn f(k: i16) -> {ret}
    let c = C {{ d: -5000000000 }}
{body}
pub fn main() -> i32
    match f(-300)
        {pat}(g) =>
            if g.a != -300
                return 1
            if g.b != -5000000000
                return 2
            if g.c != 2.5
                return 3
            0
        _ => 4
"""


def _program(source: str, ctor: str, place: str) -> str:
    ret, build, pat = CTORS[ctor]
    body = PLACES[place].format(ctor=build, src=SOURCES[source])
    return _PROGRAM.format(ret=ret, body=body, pat=pat)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("place", sorted(PLACES))
@pytest.mark.parametrize("ctor", sorted(CTORS))
@pytest.mark.parametrize("source", sorted(SOURCES))
def test_call_result_payload_is_its_struct(run_with, source, ctor, place, compiler):
    name = f"{source}_{ctor}_{place}"
    assert run_with(compiler, name, _program(source, ctor, place)) == 0


# The ticket's program, verbatim: ritz0 exits 3.
TICKET = """\
import ritzlib.option

struct G
    a: i16
    b: i64

impl G
    pub fn empty() -> G
        G { a: 3, b: 4 }

fn mk() -> G
    G { a: 1, b: 2 }

fn f(t: i32) -> Option<G>
    if t > 1
        return Some(G.empty())
    Some(mk())

pub fn main() -> i32
    match f(5)
        Some(g) => g.a as i32
        None => 9
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_ticket_program(run_with, compiler):
    assert run_with(compiler, "ticket", TICKET) == 3
