"""Statement dispatch lives in emitter/stmts.py (AGAST #1826, slice 3).

`_emit_stmt_inner` was one 631-line LLVMEmitter method in emitter_llvmlite.py
with cyclomatic complexity ~119.  It is now a `StmtEmitter` mixin whose
statement families (return, var, let, tuple let, assignment, expression) are
their own methods, and every moved function is under CC 60.

These tests pin the structure the split promises.  The corpus IR is unchanged:
each branch is moved verbatim into its new method, so the full-corpus
byte-identity replay (not a unit test) is the behavioural evidence.
"""

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emitter.stmts import StmtEmitter  # noqa: E402
from emitter_llvmlite import LLVMEmitter  # noqa: E402

CC_LIMIT = 60

# Every method the split created, by module owner.  `_emit_stmt_inner` becomes
# the dispatch; the rest are the statement families it used to inline.
STMTS_METHODS = (
    "_emit_stmt_inner",
    "_emit_return_stmt",
    "_emit_var_stmt",
    "_emit_let_stmt",
    "_emit_let_tuple_stmt",
    "_emit_assign_stmt",
    "_emit_assign_value",
    "_emit_assign_index_value",
    "_emit_assign_to_ident",
    "_emit_assign_to_index",
    "_emit_assign_to_deref",
    "_emit_assign_to_field",
    "_emit_expr_stmt",
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


def test_llvm_emitter_is_a_stmt_emitter():
    assert issubclass(LLVMEmitter, StmtEmitter)


def test_statement_dispatch_is_owned_by_stmts_module():
    """The methods live on the mixin, not on LLVMEmitter or its source file."""
    for name in STMTS_METHODS:
        fn = getattr(StmtEmitter, name)
        assert fn.__qualname__ == f"StmtEmitter.{name}", name
        # The old class body no longer defines it (moved, not copied).
        assert name not in LLVMEmitter.__dict__, name
        assert getattr(LLVMEmitter, name) is fn, name


def test_moved_functions_stay_under_the_cc_ceiling():
    """#1826: no function CC > 60.  _emit_stmt_inner was the worst offender."""
    source = Path(__file__).resolve().parent / "stmts.py"
    tree = ast.parse(source.read_text())
    methods = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "StmtEmitter":
            methods = {n.name: n for n in node.body if isinstance(n, ast.FunctionDef)}
    for name in STMTS_METHODS:
        assert name in methods, f"{name} missing from StmtEmitter"
        cc = _cyclomatic(methods[name])
        assert cc <= CC_LIMIT, f"{name} has cyclomatic complexity {cc} > {CC_LIMIT}"


def test_dispatch_stays_a_dispatcher():
    """The 631-line body is gone: dispatch is a thin switch over statement kinds."""
    source = Path(__file__).resolve().parent / "stmts.py"
    tree = ast.parse(source.read_text())
    body = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "StmtEmitter":
            for fn in node.body:
                if isinstance(fn, ast.FunctionDef) and fn.name == "_emit_stmt_inner":
                    body = fn
    assert body is not None
    # 631 lines before the split; a dispatcher stays in the low hundreds.
    assert body.end_lineno - body.lineno < 200, "statement body was not split up"
