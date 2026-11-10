"""AGAST #2565: an impl method `-> usize` / `-> isize` whose body ends in an
implicit tail value returns `i64`, not `%usize`.

THE DEFECT

    struct G
        v: Vec<i64>
    impl G
        pub fn c1(self) -> usize
            self.v.len()

ritz1 wrote `ret %usize %.4` inside `define weak_odr i64 @G_c1`, which clang
rejects (`expected '%usize = type opaque'`; angelo shaper/types.ritz:102
GlyphRun.glyph_count).  The parser has no primitive token for usize/isize,
so the return type is TYPE_STRUCT named "usize".  The `define` line maps
that name through emit_llvm_type_struct (-> `i64`); emit_method's implicit
tail took its "struct-returning method" branch and wrote `ret %<name>`
from the raw name.

THE MATRIX

receiver x return type x tail shape, ritz0 as the oracle.

  * receiver: by-value `self`, `self:&`, typed `self: @G`, a static method
    `G.count(g: @G)`, and a free fn `count(g: @G)` (control)
  * return type: usize, isize
  * tail: a call (`.v.len()`, an i64), an i64 field, an `as` cast, and a
    local of the return type (an EXPR_IDENT, which the struct branch read
    as a pointer); plus an explicit `return` as a control

A usize/isize *field* is not in the matrix: `G { n: 4 }` with `n: usize`
emits `store %usize` in main whatever the method does (AGAST #2198).

MEASURED ON 5e3b9598

  * broken: every method cell (self, self:&, self: @G, static) x both
    types x all four implicit tails (32 cells).
  * already fine: the free-fn control (all tails), and an explicit
    `return` in every method form.

THE FIX

The method tail's struct branch applies only when the return type lowers
to a named `%T`; a primitive name (usize/isize/...) takes the scalar `ret`
typed by emit_llvm_type_struct, the mapping the `define` line already uses.

Every program has v.len() == 3, n == 4, k == 5 and exits with the value.
"""

import itertools

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg

# The returned expression, with `{r}` the receiver, and the exit code.
TAILS = {
    "call": ("{r}.v.len()", 3),
    "field": ("{r}.n", 4),
    "cast": ("{r}.k as {ty}", 5),
    "local": ("let x: {ty} = {r}.k as {ty}\n{indent}x", 5),
    # Control: an explicit `return`, which emit_stmt types (already fine).
    "explicit": ("return {r}.k as {ty}", 5),
}

# (signature, receiver name in the body, call expression in main).
RECEIVERS = {
    "self_value": ("    pub fn count(self) -> {ty}\n", "self", "g.count()"),
    "self_lent": ("    pub fn count(self:&) -> {ty}\n", "self", "g.count()"),
    "self_typed": ("    pub fn count(self: @G) -> {ty}\n", "self", "g.count()"),
    "static": ("    pub fn count(g: @G) -> {ty}\n", "g", "G.count(@g)"),
    "free_fn": ("fn count(g: @G) -> {ty}\n", "g", "count(@g)"),
}

TYPES = ["usize", "isize"]


def _program(recv: str, ty: str, tail: str) -> str:
    sig, r, call = RECEIVERS[recv]
    expr, _ = TAILS[tail]
    indent = "    " if recv == "free_fn" else "        "
    body = expr.format(r=r, ty=ty, indent=indent)
    head = "" if recv == "free_fn" else "impl G\n"
    return (
        "import ritzlib.gvec\n\n"
        "struct G\n"
        "    v: Vec<i64>\n"
        "    n: i64\n"
        "    k: i64\n\n"
        f"{head}{sig.format(ty=ty)}{indent}{body}\n\n"
        "pub fn main() -> i32\n"
        "    var g: G = G { v: vec_new<i64>(), n: 4, k: 5 }\n"
        "    g.v.push(7)\n"
        "    g.v.push(8)\n"
        "    g.v.push(9)\n"
        f"    let c: {ty} = {call}\n"
        "    return c as i32\n"
    )


CELLS = list(itertools.product(RECEIVERS, TYPES, TAILS))


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("recv,ty,tail", CELLS, ids=["-".join(c) for c in CELLS])
def test_method_usize_tail(compiler, recv, ty, tail, tmp_path):
    prog = _program(recv, ty, tail)
    assert _run_pkg(compiler, tmp_path, "mut", prog) == TAILS[tail][1], prog
