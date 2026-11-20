"""AGAST #3676: the instantiation walk enters every expression kind.

THE DEFECT

`Monomorphizer._visit_expr`, the walk that finds which generic instances a
program names, listed the expression kinds it entered and had no fallback.
A kind it did not list (TupleLit, TryOp, Grouped, AssignExpr, InterpString,
...) was never entered, so a generic struct literal or generic call found
only beneath one was never instantiated.  The rewrite then left the bare
template name, and the emitter raised an internal

    ValueError: Unknown struct: W

a traceback, not a diagnostic.  #3664 patched one kind (`heap`); the fix is
the generic `map_child_nodes` fallback `_rewrite_expr` and `_specialize_expr`
already have (#1937), so no kind is skipped.

Each case below names its generic instance only beneath the kind under test,
plain and nested (`W<W<i64>>`, whose inner `W<i64>` is named nowhere else).
Every program exits 42 when the values round-trip.  ritz1's walk already
enters these kinds, so all three compilers run them.
"""

import pytest
import ritz_ast as rast
import test_ritz1_for_header as for_header
import test_table_rows as table_rows
from monomorph import Monomorphizer
from parser import parse
from test_table_rows import Row, Run

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

HEAD = """\
import ritzlib.result

struct W<T>
    tag: u8
    v: T

fn pass<T>(x: T) -> Result<T, i32>
    Ok(x)

fn tag_of<T>(w: W<T>) -> i32
    w.tag as i32

"""

CASES = {
    # A tuple operand: TupleLit's elements were never entered.
    "tuple": """\
fn main() -> i32
    let t = (W<i64> { tag: 1, v: 40 }, 1)
    t.0.tag as i32 + t.0.v as i32 + t.1 as i32
""",
    "tuple_nested": """\
fn main() -> i32
    let t = (W<W<i64>> { tag: 1, v: W<i64> { tag: 2, v: 38 } }, 1)
    t.0.tag as i32 + t.0.v.tag as i32 + t.0.v.v as i32 + t.1 as i32
""",
    # A `?` operand: TryOp's operand was never entered, so neither the
    # generic call `pass<W<i64>>` nor the literal it is passed was found.
    "try": """\
fn go() -> Result<i32, i32>
    let w = pass<W<i64>>(W<i64> { tag: 2, v: 40 })?
    Ok(w.tag as i32 + w.v as i32)

fn main() -> i32
    match go()
        Ok(v) => v
        Err(_) => 1
""",
    "try_nested": """\
fn go() -> Result<i32, i32>
    let w = pass<W<W<i64>>>(W<W<i64>> { tag: 1, v: W<i64> { tag: 2, v: 39 } })?
    Ok(w.tag as i32 + w.v.tag as i32 + w.v.v as i32)

fn main() -> i32
    match go()
        Ok(v) => v
        Err(_) => 1
""",
    # A match arm's `return`: ReturnExpr's value was never entered, so
    # neither `tag_of<i64>` nor `W<i64>` was found.
    "arm_return": """\
fn main() -> i32
    match 1
        0 => return 1
        _ => return tag_of<i64>(W<i64> { tag: 42, v: 0 })
""",
    "arm_return_nested": """\
fn main() -> i32
    match 1
        0 => return 1
        _ => return tag_of<W<i64>>(W<W<i64>> { tag: 42, v: W<i64> { tag: 0, v: 0 } })
""",
    # A match arm's assignment: AssignExpr's value was never entered.
    "arm_assign": """\
fn main() -> i32
    var r: i32 = 0
    match 1
        0 => r = 1
        _ => r = tag_of<i64>(W<i64> { tag: 42, v: 0 })
    r
""",
    "arm_assign_nested": """\
fn main() -> i32
    var r: i32 = 0
    match 1
        0 => r = 1
        _ => r = tag_of<W<i64>>(W<W<i64>> { tag: 42, v: W<i64> { tag: 0, v: 0 } })
    r
""",
    # Parenthesised inside a tuple: the parens parse away, the tuple stays.
    "grouped_in_tuple": """\
fn main() -> i32
    let t = ((W<i64> { tag: 2, v: 40 }), 0)
    t.0.tag as i32 + t.0.v as i32 + t.1 as i32
""",
}


# One table per compiler (AGAST #4418): each case used to launch its own
# `build.py` package.  The nine cases share HEAD's imports, so as rows they
# pay one ritzlib compile per process per compiler (#3906).
RUNS = [Row(f"generic_instance_under_unlisted_kind_is_instantiated[{name}]",
            table_rows.ALL, Run(HEAD + CASES[name], 42)) for name in sorted(CASES)]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_generic_instance_under_unlisted_kind_is_instantiated(ritz1_bin, tmp_path, compiler):
    table_rows.assert_rows(compiler, RUNS, build=table_rows.ritzlib_build(ritz1_bin),
                           compile=for_header.batch_compile(ritz1_bin), work=tmp_path)


# --- the walk itself, every wrapping kind ------------------------------------
#
# `Grouped`, `Await` and `InterpString` cannot hold a struct literal from a
# real parse today (Grouped is built only by the const-expression parser), so
# they are pinned on hand-built trees: the fallback must not depend on which
# kinds the parser happens to produce.


def _lit():
    """`W<i64> { tag: 1 }`."""
    return rast.StructLit(None, "W", [("tag", rast.IntLit(None, 1))],
                          [rast.NamedType(None, "i64", [])])


WRAPS = {
    "Grouped": lambda e: rast.Grouped(None, e),
    "TupleLit": lambda e: rast.TupleLit(None, [rast.IntLit(None, 0), e]),
    "TryOp": lambda e: rast.TryOp(None, e),
    "Await": lambda e: rast.Await(None, e),
    "ReturnExpr": lambda e: rast.ReturnExpr(None, e),
    "AssignExpr": lambda e: rast.AssignExpr(None, rast.Ident(None, "r"), e),
    "InterpString": lambda e: rast.InterpString(None, ["", ""], [e]),
}


def _mono():
    m = Monomorphizer()
    m.generic_structs["W"] = parse("struct W<T>\n    tag: u8\n    v: T\n").items[0]
    return m


@pytest.mark.unit
@pytest.mark.parametrize("kind", sorted(WRAPS))
def test_visit_enters_kind(kind):
    m = _mono()
    m._visit_expr(WRAPS[kind](_lit()))
    assert "W$i64" in m.struct_instantiations.values()


@pytest.mark.unit
@pytest.mark.parametrize("kind", sorted(WRAPS))
def test_visit_enters_kind_twice_nested(kind):
    """The kind under test inside itself, around a literal whose field holds
    a second generic literal: every level is entered."""
    inner = _lit()
    outer = rast.StructLit(None, "W", [("v", inner)],
                           [rast.NamedType(None, "W", [rast.NamedType(None, "i64", [])])])
    m = _mono()
    m._visit_expr(WRAPS[kind](WRAPS[kind](outer)))
    assert {"W$i64", "W$W_i64"} <= set(m.struct_instantiations.values())

