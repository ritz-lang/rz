"""Regression tests for AGAST #3238: `?` over a METHOD's Result, in ritz1.

`let a = r.rd()?` inside `fn parse(..) -> Result<P, i32>`, with
`R.rd -> Result<u32, i32>`, spilled the operand as the enclosing fn's
`%Result$P$i32`: emit_expr_try (emitter_expr.ritz, "try: spill scrutinee")
typed a CALL's Result from its FnDef but fell back to the fn's return type for
an EXPR_METHOD, so clang refused `store %Result$P$i32 %.4` with `%.4` a
`%Result$u32$i32`.  The free-fn form `rdf(r)?` was fine.  The untyped let's
slot (emitter_stmt.ritz EXPR_TRY arm) had the same gap for a struct payload.

Found in angelo loader/ttf.ritz:85, `let v = reader.read_u32()?`.

Each program's exit code is checked on all three compilers (ritz0 the oracle).
"""

import pytest

import test_ritz1_for_header as for_header

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = pytest.mark.batched

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

R = """\
struct R
    n: u32
struct P
    a: u32
    b: u32
"""

PROGRAMS = {
    # The ticket's repro, verbatim: a method's `?` into an untyped let, inside
    # a fn returning a different Result.  7 + 7.
    "untyped_let": (
        R
        + """impl R
    pub fn rd(self: @R) -> Result<u32, i32>
        Ok(self.n)
fn rdf(r: @R) -> Result<u32, i32>
    Ok(r.n)
fn parse(r: @R) -> Result<P, i32>
    let a = r.rd()?
    let b = rdf(r)?
    Ok(P { a: a, b: b })
pub fn main() -> i32
    let r = R { n: 7 }
    match parse(@r)
        Ok(p) => (p.a + p.b) as i32
        Err(e) => 100
""",
        14,
    ),
    # No let: the method's `?` is an operand.
    "operand": (
        R
        + """impl R
    pub fn rd(self: @R) -> Result<u32, i32>
        Ok(self.n)
fn parse(r: @R) -> Result<P, i32>
    Ok(P { a: r.rd()? + 1, b: r.rd()? })
pub fn main() -> i32
    let r = R { n: 7 }
    match parse(@r)
        Ok(p) => (p.a + p.b) as i32
        Err(e) => 100
""",
        15,
    ),
    # The Err short-circuit through a method's `?` returns the caller's Err.
    "err_propagates": (
        R
        + """impl R
    pub fn rd(self: @R) -> Result<u32, i32>
        if self.n == 0
            return Err(9)
        Ok(self.n)
fn parse(r: @R) -> Result<P, i32>
    let a = r.rd()?
    Ok(P { a: a, b: 0 })
pub fn main() -> i32
    let r = R { n: 0 }
    match parse(@r)
        Ok(p) => 100
        Err(e) => e
""",
        9,
    ),
    # A struct Ok payload: the untyped let's slot is the struct, not an i64.
    "struct_payload": (
        R
        + """impl R
    pub fn mk(self: @R) -> Result<P, i32>
        Ok(P { a: self.n, b: self.n * 2 })
fn sum(r: @R) -> Result<u32, i32>
    let p = r.mk()?
    Ok(p.a + p.b)
pub fn main() -> i32
    let r = R { n: 5 }
    match sum(@r)
        Ok(v) => v as i32
        Err(e) => 100
""",
        15,
    ),
    # angelo's shape: a StrView error, a mutable receiver, a u32 read.
    "strview_err": (
        """\
struct Reader
    pos: u32
struct Off
    v: u32
impl Reader
    pub fn read_u32(self: @&Reader) -> Result<u32, StrView>
        self.pos = self.pos + 4
        Ok(self.pos)
fn parse(reader: @&Reader) -> Result<Off, StrView>
    let v = reader.read_u32()?
    let w = reader.read_u32()?
    Ok(Off { v: v + w })
pub fn main() -> i32
    var r = Reader { pos: 1 }
    match parse(@&r)
        Ok(o) => o.v as i32
        Err(e) => 100
""",
        14,
    ),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_try_over_a_method_result(run_with, name, compiler):
    program, expected = PROGRAMS[name]
    assert run_with(compiler, name, program) == expected
