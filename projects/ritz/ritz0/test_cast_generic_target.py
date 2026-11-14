"""AGAST #3124: a cast's target type may be generic: `x as *Box<i64>`.

    struct Box<T>
        v: T
    pub fn main() -> i32
        var raw: i64 = 0
        let p = (@raw) as *u8 as *Box<i64>
        p.v = 3
        return raw as i32 - 3

ritz0 parsed a cast's type without type arguments, so `Box<i64>` after `as *`
was read as `Box < i64 ...` and ran on into the next line ("Expected
expression, got EQ"); in parentheses it failed at the `)`.  ritz1 parsed it,
but monomorph didn't instantiate a type named only by a cast, so `p.v = 3`
had no `Box$i64` to resolve.

The parser now reads `<...>` after a cast's named type speculatively and keeps
it only when it closes and isn't followed by an operand, so `a as i64 < b`
(and `n as Sz < b, c > d` in an argument list) stay comparisons.

Each program returns 0, or the number of the first check that failed.
ritz0 is the oracle.
"""

import pytest

import ritz_ast as rast
from parser import parse

import test_ritz1_for_header as for_header

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]


# ---------------------------------------------------------------------------
# Parser: which tokens a cast's target type takes
# ---------------------------------------------------------------------------

def _ret_expr(body: str) -> rast.Expr:
    """The value of `return <body>` in a one-statement function."""
    src = ("type Sz = i64\n"
           "fn f(a: i64, b: i64, c: i64, d: i64, x: *u8) -> i64\n"
           f"    return {body}\n")
    fn = [i for i in parse(src).items if isinstance(i, rast.FnDef)][0]
    return fn.body.stmts[0].value


def _show(t: rast.Type) -> str:
    if isinstance(t, rast.PtrType):
        return "*" + _show(t.inner)
    assert isinstance(t, rast.NamedType), t
    if not t.args:
        return t.name
    return f"{t.name}<{', '.join(_show(a) for a in t.args)}>"


GENERIC_TARGETS = {
    # The ticket's shape, at end of line.
    "ptr": ("x as *Box<i64>", "*Box<i64>"),
    "value": ("x as Box<i64>", "Box<i64>"),
    "ptr_ptr": ("x as **Box<i64>", "**Box<i64>"),
    # Two arguments, one itself generic: the `,` must not end the cast.
    "nested_pair": ("x as *Pair<Box<i64>, i32>", "*Pair<Box<i64>, i32>"),
    # `>>` closes two lists (the lexer's RSHIFT is split, #1299).
    "nested_rshift": ("x as *Box<Box<i64>>", "*Box<Box<i64>>"),
    "chained": ("x as *u8 as *Box<i64>", "*Box<i64>"),
}


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(GENERIC_TARGETS))
def test_cast_target_takes_type_arguments(name):
    body, want = GENERIC_TARGETS[name]
    e = _ret_expr(body)
    assert isinstance(e, rast.Cast), e
    assert _show(e.target) == want


@pytest.mark.unit
def test_generic_cast_in_parentheses_then_field():
    # `(x as *Box<i64>).v`: the `)` used to be "Expected expression".
    e = _ret_expr("(x as *Box<i64>).v")
    assert isinstance(e, rast.Field) and e.field == "v", e
    assert _show(e.expr.target) == "*Box<i64>"


@pytest.mark.unit
def test_generic_cast_then_operator():
    # The cast ends at `>`; `+ 1` is the outer expression's.
    e = _ret_expr("(x as *Box<i64>) as i64 + 1")
    assert isinstance(e, rast.BinOp) and e.op == "+", e


COMPARISONS = {
    # `< b` never closes, so these stay comparisons.
    "primitive": "a as i64 < b",
    "primitive_both_sides": "a as i64 < b as i64",
    # And through a named (alias) target.
    "alias_then_lt": "a as Sz < b",
    "alias_lt_and": "a as Sz < b and c > d",
    # `>>` here is a shift, not two closers: `(a as Sz) < (b >> c)`.
    "alias_lt_shift": "a as Sz < b >> c",
}


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(COMPARISONS))
def test_cast_followed_by_lt_is_still_a_comparison(name):
    e = _ret_expr(COMPARISONS[name])
    while isinstance(e, rast.BinOp) and e.op in ("and", "&&"):
        e = e.left
    assert isinstance(e, rast.BinOp) and e.op == "<", e
    assert isinstance(e.left, rast.Cast) and not e.left.target.args, e.left


@pytest.mark.unit
def test_lt_comma_gt_in_call_args_is_two_comparisons():
    # `f(a as Sz < b, c > d)`: `<b, c>` closes, but an operand follows the `>`,
    # so it is two arguments, not a cast to `Sz<b, c>`.
    e = _ret_expr("g(a as Sz < b, c > d)")
    assert isinstance(e, rast.Call) and len(e.args) == 2, e
    assert [a.op for a in e.args] == ["<", ">"]


@pytest.mark.unit
def test_cast_lt_geq_is_still_a_comparison():
    # `>=` would split into `>` `=`; a cast never ends in `=`.
    e = _ret_expr("a as Sz < b >= c")
    assert isinstance(e, rast.BinOp) and e.op == ">=", e


# ---------------------------------------------------------------------------
# All three compilers: the cast's type is instantiated and the local takes it
# ---------------------------------------------------------------------------

PRELUDE = """\
struct Box<T>
    v: T

struct Pair<A, B>
    a: A
    b: B

type Sz = i64

fn both(x: bool, y: bool) -> i32
    if x and y
        return 0
    return 3

"""

PROGRAMS = {
    # The ticket's program, verbatim.
    "ticket": ("    var raw: i64 = 0\n"
               "    let p = (@raw) as *u8 as *Box<i64>\n"
               "    p.v = 3\n"
               "    return raw as i32 - 3\n"),
    # In parentheses, then a field of the parenthesised cast.
    "parenthesised": ("    var raw: i64 = 0\n"
                      "    let q = (@raw) as *u8\n"
                      "    (q as *Box<i64>).v = 5\n"
                      "    if raw != 5\n        return 1\n"
                      "    if (q as *Box<i64>).v != 5\n        return 2\n"
                      "    return 0\n"),
    # `**Box<i64>`: store a *Box<i64> through a pointer to it.
    "ptr_ptr": ("    var raw: i64 = 0\n"
                "    var bp: *Box<i64> = null\n"
                "    let pp = (@bp) as *u8 as **Box<i64>\n"
                "    *pp = (@raw) as *u8 as *Box<i64>\n"
                "    bp.v = 7\n"
                "    if raw != 7\n        return 1\n"
                "    return 0\n"),
    # A nested generic argument; Pair<Box<i64>, i32> is first named here.
    "nested_pair": ("    var raw: [2]i64\n"
                    "    raw[0] = 0\n    raw[1] = 0\n"
                    "    let p = (@raw[0]) as *u8 as *Pair<Box<i64>, i32>\n"
                    "    p.a.v = 9\n"
                    "    p.b = 4\n"
                    "    if raw[0] != 9\n        return 1\n"
                    "    if (raw[1] & 4294967295) != 4\n        return 2\n"
                    "    return 0\n"),
    # `a as i64 < b` stays a comparison end to end.
    "comparison": ("    let a: i32 = 2\n    let b: i64 = 3\n"
                   "    if a as i64 < b\n        return 0\n"
                   "    return 1\n"),
    # And through a named (alias) target, where `<` could open a list:
    # `< b and c >` never closes; `< b, c > d` closes but an operand follows.
    "named_comparison": ("    let a: i64 = 2\n    let b: i64 = 3\n"
                         "    let c: i64 = 5\n    let d: i64 = 4\n"
                         "    if not (a as Sz < b)\n        return 1\n"
                         "    if not (a as Sz < b and c > d)\n        return 2\n"
                         "    return both(a as Sz < b, c > d)\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_generic_cast_target_runs(run_with, compiler, name):
    program = PRELUDE + "pub fn main() -> i32\n" + PROGRAMS[name]
    assert run_with(compiler, name, program) == 0
