"""The expression dispatch lives in emitter/exprs.py (AGAST #1826, slice 2).

`_emit_expr` / `_emit_expr_core` were two LLVMEmitter methods in the 18k-line
emitter_llvmlite.py; the core was one 431-line if/elif chain with cyclomatic
complexity well over the #1826 ceiling of 60.  They are now an `ExprEmitter`
mixin whose families (identifiers, binary operators, operator selection) are
their own methods, and every moved function is under CC 60.

These tests pin the structure the split promises.  The corpus IR is unchanged:
`_emit_expr` and `_emit_expr_core` are moved verbatim, and the branches they
delegate to are the same code, so the full-corpus byte-identity replay (not a
unit test) is the behavioural evidence.
"""

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emitter.exprs import ExprEmitter  # noqa: E402
from emitter_llvmlite import LLVMEmitter  # noqa: E402

CC_LIMIT = 60

# Every method the split created, by module owner.  `_emit_expr` and
# `_emit_expr_core` are moved wholesale; the rest are the pieces the 431-line
# core was cut into so each stays under CC_LIMIT.
EXPRS_METHODS = (
    "_emit_expr",
    "_emit_expr_core",
    "_emit_expr_ident",
    "_emit_expr_binop",
    "_emit_binop_operands",
    "_emit_binop_result",
)


def _cyclomatic(fn: ast.AST) -> int:
    """1 + decision points, counting the shapes Python emits these methods in."""
    cc = 1
    for node in ast.walk(fn):
        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While,
                             ast.ExceptHandler, ast.Assert, ast.IfExp)):
            cc += 1
        elif isinstance(node, ast.BoolOp):
            cc += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            cc += 1 + len(node.ifs)
    return cc


def test_llvm_emitter_is_an_expr_emitter():
    assert issubclass(LLVMEmitter, ExprEmitter)


def test_expression_dispatch_is_owned_by_exprs_module():
    """The methods live on the mixin, not on LLVMEmitter or its source file."""
    for name in EXPRS_METHODS:
        fn = getattr(ExprEmitter, name)
        assert fn.__qualname__ == f"ExprEmitter.{name}", name
        # The old class body no longer defines it (moved, not copied).
        assert name not in LLVMEmitter.__dict__, name
        assert getattr(LLVMEmitter, name) is fn, name


def test_moved_functions_stay_under_the_cc_ceiling():
    """#1826: no function CC > 60.  The core was the worst offender."""
    source = Path(__file__).resolve().parent / "exprs.py"
    tree = ast.parse(source.read_text())
    methods = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ExprEmitter":
            methods = {n.name: n for n in node.body if isinstance(n, ast.FunctionDef)}
    for name in EXPRS_METHODS:
        assert name in methods, f"{name} missing from ExprEmitter"
        cc = _cyclomatic(methods[name])
        assert cc <= CC_LIMIT, f"{name} has cyclomatic complexity {cc} > {CC_LIMIT}"
