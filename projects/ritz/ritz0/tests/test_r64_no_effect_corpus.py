"""LARB R64 corpus repair (AGAST #3490): no statement in these files is a no-op.

R64 measured 277 expression statements whose value is discarded and which do
nothing: 259 bare `"FAIL: ...\\n"` strings in 15 zeus test files (every failure
message was lost), 11 bare `c"...{x}"` lines in examples 70 and 71 (they print
nothing), and 7 deliberate `555` lines in codegen regressions 93/94. The repair
turned each into a call. This test pins that, ahead of the compiler check R64
also asks for, so nothing regrows in the files it named.

Parse-only: no compile, no link. The no-effect set is R64's: a literal, name,
field, index, cast, aggregate literal or operator as a statement that is not
its block's value. Calls, assignments and `if`/`match`/blocks are allowed.
"""

import dataclasses
from pathlib import Path

import pytest

import ritz_ast as rast
from parser import parse

ROOT = Path(__file__).resolve().parents[4]

NO_EFFECT = (
    rast.IntLit, rast.FloatLit, rast.StringLit, rast.CStringLit,
    rast.InterpString, rast.CharLit, rast.BoolLit, rast.NullLit, rast.Ident,
    rast.QualifiedIdent, rast.BinOp, rast.UnaryOp, rast.Index, rast.SliceExpr,
    rast.Field, rast.StructLit, rast.ArrayLit, rast.ArrayFill, rast.TupleLit,
    rast.Cast, rast.Range, rast.Grouped,
)

# The files R64 found hits in, grouped so a regression names its area.
GROUPS = {
    "zeus_tests": sorted((ROOT / "projects/zeus/test").glob("*.ritz")),
    "examples_70_71_interp": [
        ROOT / "projects/ritz/examples/tier5_async/70_interp_string/src/main.ritz",
        ROOT / "projects/ritz/examples/tier5_async/70_interp_string/test/test_interp.ritz",
        ROOT / "projects/ritz/examples/tier5_async/71_type_inference/src/main.ritz",
    ],
    # 93_fn_boundary_label was retired by AGAST #3526 (its guard is now
    # ritz0/test_ritz1_entry_block_label.py).
    "regression_94": [
        ROOT / "projects/ritz/examples/tier1_basics/94_method_tail_return/src/main.ritz",
    ],
}


def no_effect_statements(node, out):
    """Append every no-effect ExprStmt under `node` (any AST shape) to `out`."""
    if isinstance(node, list):
        for n in node:
            no_effect_statements(n, out)
        return
    if not dataclasses.is_dataclass(node):
        return
    if isinstance(node, rast.Block):
        for s in node.stmts:
            if isinstance(s, rast.ExprStmt) and isinstance(s.expr, NO_EFFECT):
                out.append(s)
    for f in dataclasses.fields(node):
        no_effect_statements(getattr(node, f.name), out)


@pytest.mark.parametrize("group", sorted(GROUPS))
def test_no_statement_without_effect(group):
    files = GROUPS[group]
    assert files, f"{group}: no files found; did they move?"
    hits = []
    for path in files:
        found = []
        no_effect_statements(parse(path.read_text(), str(path)), found)
        rel = path.relative_to(ROOT)
        hits += [f"{rel}:{s.span.line}: {type(s.expr).__name__}" for s in found]
    assert not hits, (
        f"{len(hits)} statement(s) with no effect (LARB R64); a bare string "
        "prints nothing, call prints/print:\n" + "\n".join(hits)
    )


def test_walk_finds_a_bare_fail_string():
    """The walk itself sees the R64 shape, so a green run means something."""
    src = (
        "fn t(x: i64) -> i32\n"
        "    if x != 1\n"
        '        "FAIL: x is {x}\\n"\n'
        "        return 1\n"
        "    0\n"
    )
    found = []
    no_effect_statements(parse(src, "<r64>"), found)
    assert [type(s.expr) for s in found] == [rast.StringLit]
