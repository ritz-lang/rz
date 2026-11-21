"""`rast.SliceType` is retired: kept for legacy importers, handled by no pass.

AGAST #1285 made `[T]` desugar to `Span<T>` at every construction site
(`rast.make_slice_type`), so the parser, the `[]T` metadata read path and
cached interfaces never produce a `SliceType`. A pickled `.rzi` from before
the desugaring cannot be returned either: its key hashes `parser.py` and
`ritz_ast.py` (`module_interface.parser_fingerprint`).

AGAST #1294 deleted the `isinstance(..., rast.SliceType)` arms that were
left in the monomorphizer, metadata writer, import resolver, move checker
and emitter. The class stays, documented as read-only for legacy tooling, and
codegen rejects it rather than spelling it: a `SliceType` reaching a mangler
or the LLVM lowering is a front-end bug, not a type to name.
"""

import ast
from pathlib import Path

import pytest

import ritz_ast as rast
from emitter_llvmlite import LLVMEmitter
from monomorph import mangle_type_name

pytestmark = pytest.mark.unit

RITZ0 = Path(__file__).resolve().parents[1]
I32 = rast.NamedType(None, "i32", [])


def _names_slice_type(path: Path) -> bool:
    """`path` refers to `SliceType` by name or as an attribute (`rast.SliceType`)."""
    tree = ast.parse(path.read_text(), str(path))
    return any(
        (isinstance(n, ast.Attribute) and n.attr == "SliceType")
        or (isinstance(n, ast.Name) and n.id == "SliceType")
        for n in ast.walk(tree))


def test_only_ritz_ast_names_slice_type():
    # Every compiler module, not tests: a new arm would be dead on arrival.
    sources = [p for p in RITZ0.rglob("*.py")
               if not p.name.startswith("test_") and "test" not in p.parts[len(RITZ0.parts):-1]]
    offenders = sorted(str(p.relative_to(RITZ0)) for p in sources
                       if p.name != "ritz_ast.py" and _names_slice_type(p))
    assert offenders == []


def test_node_still_constructs_for_legacy_importers():
    # Not deleted: third-party tooling importing `rast.SliceType` keeps working.
    assert rast.SliceType(None, I32).inner == I32


def test_mangle_type_name_rejects_slice_type():
    with pytest.raises(TypeError, match="SliceType"):
        mangle_type_name(rast.SliceType(None, I32))


def test_emitter_name_suffix_rejects_slice_type():
    with pytest.raises(TypeError, match="SliceType"):
        LLVMEmitter()._type_to_name_suffix(rast.SliceType(None, I32))


def test_emitter_lowering_rejects_slice_type():
    with pytest.raises(ValueError, match="SliceType"):
        LLVMEmitter()._ritz_type_to_llvm(rast.SliceType(None, I32))
