"""Pattern and match emission lives in emitter/patterns.py (AGAST #1826, slice 4).

The match family — `_emit_match`'s dispatch, the bare-constructor scrutinee
resolution, the float/tuple arm merge, `_emit_enum_match`, the integer and
StrView matches and every refusal helper they call — was ~1,240 lines of
LLVMEmitter methods in emitter_llvmlite.py.  They are now a `PatternEmitter`
mixin, moved verbatim.

These tests pin the structure the split promises.  The corpus IR is unchanged:
each method is moved without edits, so the full-corpus byte-identity replay
(not a unit test) is the behavioural evidence.
"""

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emitter import common  # noqa: E402
from emitter.patterns import PatternEmitter  # noqa: E402
from emitter_llvmlite import LLVMEmitter  # noqa: E402

CC_LIMIT = 60

# Every method the split moved into the pattern mixin.
PATTERN_METHODS = (
    "_emit_match",
    "_bare_ctor_type",
    "_builtin_ctor_parts",
    "_untyped_nested_ctor_type",
    "_emit_bare_ctor_scrutinee",
    "_require_covered",
    "_require_reachable",
    "_int_const_fits",
    "_float_tail_ids",
    "_float_annotation_llvm",
    "_enter_float_tails",
    "_leave_float_tails",
    "_float_merge_type",
    "_float_slot",
    "_mark_float_tails",
    "_is_float_arm_convertible",
    "_merge_arms_at_float",
    "_reject_pointer_into_float",
    "_reject_pointer_beside_float",
    "_merge_value_used",
    "_reject_mixed_int_float_arms",
    "_merge_float_arms",
    "_unify_tuple_arms",
    "_merge_match_arms",
    "_emit_enum_match",
    "_is_integer_const",
    "_refuse_arm_names",
    "_refuse_char_arms",
    "_refuse_pattern_kind",
    "_resolve_module_consts",
    "_require_field_count",
    "_require_payload_count",
    "_refuse_payload_pattern",
    "_own_match_scrutinee",
    "_end_diverging_arm",
    "_enum_match_result",
    "_emit_integer_match",
    "_refuse_string_arms",
    "_emit_strview_match",
    "_emit_scalar_arm_bodies",
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


def test_llvm_emitter_is_a_pattern_emitter():
    assert issubclass(LLVMEmitter, PatternEmitter)


def test_pattern_methods_are_owned_by_patterns_module():
    """The methods live on the mixin, not on LLVMEmitter or its source file."""
    for name in PATTERN_METHODS:
        fn = getattr(PatternEmitter, name)
        assert fn.__qualname__ == f"PatternEmitter.{name}", name
        # The old class body no longer defines it (moved, not copied).
        assert name not in LLVMEmitter.__dict__, name
        assert getattr(LLVMEmitter, name) is fn, name


def test_moved_functions_stay_under_the_cc_ceiling():
    """#1826: no function CC > 60."""
    source = Path(__file__).resolve().parent / "patterns.py"
    tree = ast.parse(source.read_text())
    methods = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "PatternEmitter":
            methods = {n.name: n for n in node.body if isinstance(n, ast.FunctionDef)}
    for name in PATTERN_METHODS:
        assert name in methods, f"{name} missing from PatternEmitter"
        cc = _cyclomatic(methods[name])
        assert cc <= CC_LIMIT, f"{name} has cyclomatic complexity {cc} > {CC_LIMIT}"


def test_match_sentinels_are_shared_through_common():
    """A match's "no value" sentinel and `pass` marker are used by both the
    pattern mixin and the rest of the emitter, so they live in common.py and
    stay re-exported from emitter_llvmlite."""
    assert common.NoValue.__module__ == "emitter.common"
    assert callable(common.has_no_value)
    # `_PASS_ARM` is a bare sentinel; identity is the contract.
    from emitter_llvmlite import NoValue, _PASS_ARM, has_no_value
    assert NoValue is common.NoValue
    assert _PASS_ARM is common._PASS_ARM
    assert has_no_value is common.has_no_value


def test_emit_match_is_not_a_monolith():
    """The dispatch stays a dispatcher: the arm bodies moved to their own
    methods rather than being pasted back into `_emit_match`."""
    source = Path(__file__).resolve().parent / "patterns.py"
    tree = ast.parse(source.read_text())
    body = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "PatternEmitter":
            for fn in node.body:
                if isinstance(fn, ast.FunctionDef) and fn.name == "_emit_match":
                    body = fn
    assert body is not None
    assert body.end_lineno - body.lineno < 120, "_emit_match was not split up"
