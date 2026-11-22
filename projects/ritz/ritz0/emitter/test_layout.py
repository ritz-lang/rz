"""Struct layout and type lowering live in emitter/layout.py (AGAST #1826, slice 4).

The struct layout registry (`FieldLayout`, `StructLayout`, `StructRegistry`),
the Ritz-to-LLVM type lowering (`_ritz_type_to_llvm`), the size/align helpers
behind `sizeof` and the enum body/field layout all shared one concern: how a
Ritz type is laid out in LLVM.  They are now `emitter/layout.py` — the three
dataclasses at module level and a `LayoutEmitter` mixin for the methods,
moved verbatim.

These tests pin the structure the split promises.  The corpus IR is unchanged:
each method is moved without edits, so the full-corpus byte-identity replay
(not a unit test) is the behavioural evidence.
"""

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emitter import layout  # noqa: E402
from emitter.layout import (FieldLayout, LayoutEmitter, StructLayout,  # noqa: E402
                            StructRegistry)
from emitter_llvmlite import LLVMEmitter  # noqa: E402

CC_LIMIT = 60

# Every method the split moved into the layout mixin.
LAYOUT_METHODS = (
    "_struct_layout_on_demand",
    "_ritz_type_size_and_align",
    "_sizeof_operand_size",
    "_sizeof_is_value",
    "_sizeof_value_llvm_type",
    "_sizeof_operand_type",
    "_sizeof_names_type",
    "_sizeof_ritz_type",
    "_ritz_type_to_llvm",
    "_ensure_strview_type",
    "_is_builtin_strview",
    "_ensure_builtin_generic_struct_specialization",
    "_ensure_builtin_generic_specialization",
    "_type_size_bytes",
    "_type_size",
    "_enum_payload_shape",
    "_set_enum_body",
    "_enum_size_and_align",
    "_enum_variant_field_layout",
    "_param_to_llvm_type",
    "_sizeof_type",
    "_struct_lit_layout",
    "_struct_lit_field_indices",
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


def test_llvm_emitter_is_a_layout_emitter():
    assert issubclass(LLVMEmitter, LayoutEmitter)


def test_layout_classes_are_owned_by_layout_module():
    for cls in (FieldLayout, StructLayout, StructRegistry):
        assert getattr(layout, cls.__name__) is cls
        assert cls.__module__ == "emitter.layout", cls.__name__


def test_layout_classes_stay_re_exported_from_the_emitter():
    """`emitter_llvmlite` was the old home; keep the names importable there
    (existing tests and callers import them from it)."""
    from emitter_llvmlite import (FieldLayout as FL, StructLayout as SL,
                                  StructRegistry as SR)
    assert FL is FieldLayout
    assert SL is StructLayout
    assert SR is StructRegistry


def test_layout_methods_are_owned_by_layout_module():
    """The methods live on the mixin, not on LLVMEmitter or its source file."""
    for name in LAYOUT_METHODS:
        fn = getattr(LayoutEmitter, name)
        assert fn.__qualname__ == f"LayoutEmitter.{name}", name
        # The old class body no longer defines it (moved, not copied).
        assert name not in LLVMEmitter.__dict__, name
        assert getattr(LLVMEmitter, name) is fn, name


def test_moved_functions_stay_under_the_cc_ceiling():
    """#1826: no function CC > 60.  `_ritz_type_to_llvm` is the largest here."""
    source = Path(__file__).resolve().parent / "layout.py"
    tree = ast.parse(source.read_text())
    methods = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "LayoutEmitter":
            methods = {n.name: n for n in node.body if isinstance(n, ast.FunctionDef)}
    for name in LAYOUT_METHODS:
        assert name in methods, f"{name} missing from LayoutEmitter"
        cc = _cyclomatic(methods[name])
        assert cc <= CC_LIMIT, f"{name} has cyclomatic complexity {cc} > {CC_LIMIT}"


def test_abi_layout_helper_is_a_module_function():
    """`_abi_size_align` is pure over an `ir.Type`; no `self` to reach for."""
    assert callable(layout._abi_size_align)
    # Still importable from the emitter for `frame_too_large`.
    from emitter_llvmlite import _abi_size_align
    assert _abi_size_align is layout._abi_size_align


def test_sizeof_primitives_table_moved_with_the_lowering():
    assert "i32" in LayoutEmitter._SIZEOF_PRIMITIVES
    assert "_SIZEOF_PRIMITIVES" not in LLVMEmitter.__dict__
