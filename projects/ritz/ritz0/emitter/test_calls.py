"""Call and method dispatch lives in emitter/calls.py (AGAST #1826, slice 3).

`_emit_call_inner`, `_emit_method_call` and `_dispatch_method_call` were
LLVMEmitter methods in emitter_llvmlite.py, the last two together well over
the #1826 ceiling of 60.  They are now a `CallEmitter` mixin: the call
dispatch over indirect calls, builtins, user fns and externs, and the method
dispatch over receiver-type resolution, built-in families and its static and
instance call paths.

These tests pin the structure the split promises.  The corpus IR is unchanged:
each branch is moved verbatim into its new method, so the full-corpus
byte-identity replay (not a unit test) is the behavioural evidence.
"""

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emitter.calls import CallEmitter  # noqa: E402
from emitter_llvmlite import LLVMEmitter  # noqa: E402

CC_LIMIT = 60

# Every method the split created, by module owner.  The three entry points are
# moved; the rest are the arms and paths they used to inline.
CALLS_METHODS = (
    "_emit_call_inner",
    "_emit_indirect_call",
    "_emit_builtin_call",
    "_emit_print_call",
    "_emit_user_call",
    "_emit_user_call_args",
    "_emit_extern_call",
    "_emit_method_call",
    "_dispatch_method_call",
    "_try_emit_enum_ctor_on_type",
    "_resolve_receiver_type",
    "_static_receiver_peek",
    "_probe_receiver_type",
    "_fallback_receiver_type",
    "_try_emit_receiver_builtin",
    "_emit_static_method_call",
    "_emit_instance_method_call",
    "_method_receiver_value",
    "_method_explicit_args",
    "_convert_method_args",
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


def test_llvm_emitter_is_a_call_emitter():
    assert issubclass(LLVMEmitter, CallEmitter)


def test_call_dispatch_is_owned_by_calls_module():
    """The methods live on the mixin, not on LLVMEmitter or its source file."""
    for name in CALLS_METHODS:
        fn = getattr(CallEmitter, name)
        assert fn.__qualname__ == f"CallEmitter.{name}", name
        # The old class body no longer defines it (moved, not copied).
        assert name not in LLVMEmitter.__dict__, name
        assert getattr(LLVMEmitter, name) is fn, name


def test_moved_functions_stay_under_the_cc_ceiling():
    """#1826: no function CC > 60.  The method dispatch was the worst."""
    source = Path(__file__).resolve().parent / "calls.py"
    tree = ast.parse(source.read_text())
    methods = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "CallEmitter":
            methods = {n.name: n for n in node.body if isinstance(n, ast.FunctionDef)}
    for name in CALLS_METHODS:
        assert name in methods, f"{name} missing from CallEmitter"
        cc = _cyclomatic(methods[name])
        assert cc <= CC_LIMIT, f"{name} has cyclomatic complexity {cc} > {CC_LIMIT}"


def test_dispatch_stays_a_dispatcher():
    """The inline chains are gone: dispatch delegates each family."""
    source = Path(__file__).resolve().parent / "calls.py"
    tree = ast.parse(source.read_text())
    bodies = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "CallEmitter":
            for fn in node.body:
                if isinstance(fn, ast.FunctionDef):
                    bodies[fn.name] = fn
    for name in ("_emit_call_inner", "_dispatch_method_call"):
        fn = bodies[name]
        assert fn.end_lineno - fn.lineno < 120, f"{name} was not split up"
