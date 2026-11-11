"""Monomorph type walkers recurse into every compound type (AGAST #2741).

`TypeSubstitution.apply`, `Monomorphizer._visit_type` and
`Monomorphizer._rewrite_type` named NamedType, PtrType, RefType, ArrayType,
SliceType and FnType, and returned a TupleType (and DynType args, VectorType
inner) unchanged. A type parameter inside a tuple was never substituted:

    fn first<T>(p: (T, i32)) -> T

instantiated as `define i64 @"first$i64"({i8, i32} %"p.arg")`: the leftover
`T` lowered as i8, a wrong layout that compiled silently. Likewise a generic
struct named only inside a tuple was never instantiated, and never rewritten
to its mangled name.

`FnType` was rebuilt without its `callconv`, so a `win64` fn type became a
C-convention one after substitution or rewriting.
"""

import os
import subprocess
from pathlib import Path

import pytest

import ritz_ast as rast
from monomorph import Monomorphizer, TypeSubstitution, monomorphize
from parser import parse

RITZ_ROOT = Path(__file__).resolve().parent.parent


def named(name, *args):
    return rast.NamedType(None, name, list(args))


T = named("T")
I32 = named("i32")
I64 = named("i64")
SUB = TypeSubstitution({"T": I64})


def is_i64(ty):
    return isinstance(ty, rast.NamedType) and ty.name == "i64" and not ty.args


# --- TypeSubstitution.apply -------------------------------------------------


@pytest.mark.unit
class TestApply:
    def test_tuple_elements_substituted(self):
        out = SUB.apply(rast.TupleType(None, [T, I32]))
        assert isinstance(out, rast.TupleType)
        assert is_i64(out.elements[0])
        assert out.elements[1].name == "i32"

    def test_nested_tuple_substituted(self):
        out = SUB.apply(rast.PtrType(None, rast.TupleType(
            None, [rast.TupleType(None, [T])]), False))
        assert is_i64(out.inner.elements[0].elements[0])

    def test_dyn_args_substituted(self):
        out = SUB.apply(rast.DynType(None, "Iter", [T]))
        assert isinstance(out, rast.DynType)
        assert out.trait_name == "Iter"
        assert is_i64(out.args[0])

    def test_vector_inner_substituted(self):
        out = SUB.apply(rast.VectorType(None, 4, T))
        assert isinstance(out, rast.VectorType)
        assert out.count == 4
        assert is_i64(out.inner)

    def test_fn_type_keeps_callconv(self):
        out = SUB.apply(rast.FnType(None, [T], T, callconv="win64"))
        assert out.callconv == "win64"
        assert is_i64(out.params[0]) and is_i64(out.ret)


# --- Monomorphizer._visit_type / _rewrite_type ------------------------------


def _mono_with_box():
    """A Monomorphizer that knows `struct Box<T>` and its i32 instantiation."""
    m = Monomorphizer()
    mod = parse("struct Box<T>\n    value: T\n")
    m.generic_structs["Box"] = mod.items[0]
    return m


BOX_I32 = named("Box", I32)


@pytest.mark.unit
class TestVisitType:
    @pytest.mark.parametrize("wrap", [
        lambda t: rast.TupleType(None, [t, I32]),
        lambda t: rast.DynType(None, "Iter", [t]),
        lambda t: rast.VectorType(None, 4, t),
    ], ids=["tuple", "dyn", "vector"])
    def test_generic_struct_inside_compound_is_found(self, wrap):
        m = _mono_with_box()
        m._visit_type(wrap(BOX_I32))
        assert "Box$i32" in m.struct_instantiations.values()


@pytest.mark.unit
class TestRewriteType:
    def _rewriter(self):
        m = _mono_with_box()
        m._visit_type(BOX_I32)
        return m

    def test_tuple_elements_rewritten(self):
        out = self._rewriter()._rewrite_type(rast.TupleType(None, [BOX_I32, I32]))
        assert isinstance(out, rast.TupleType)
        assert out.elements[0].name == "Box$i32" and not out.elements[0].args

    def test_dyn_args_rewritten(self):
        out = self._rewriter()._rewrite_type(rast.DynType(None, "Iter", [BOX_I32]))
        assert isinstance(out, rast.DynType)
        assert out.args[0].name == "Box$i32"

    def test_vector_inner_rewritten(self):
        out = self._rewriter()._rewrite_type(rast.VectorType(None, 4, BOX_I32))
        assert isinstance(out, rast.VectorType)
        assert out.inner.name == "Box$i32"

    def test_fn_type_keeps_callconv(self):
        out = self._rewriter()._rewrite_type(
            rast.FnType(None, [BOX_I32], None, callconv="win64"))
        assert out.callconv == "win64"
        assert out.params[0].name == "Box$i32"


# --- whole pass -------------------------------------------------------------

FIRST_SRC = """\
fn first<T>(p: (T, i32)) -> T
    p.0

fn main() -> i32
    let t: (i64, i32) = (5, 2)
    first<i64>(t) as i32
"""


@pytest.mark.unit
def test_monomorphize_substitutes_tuple_param():
    result = monomorphize(parse(FIRST_SRC))
    fn = next(i for i in result.items
              if isinstance(i, rast.FnDef) and i.name == "first$i64")
    p = fn.params[0].type
    assert isinstance(p, rast.TupleType)
    assert is_i64(p.elements[0])


@pytest.mark.unit
def test_monomorphize_instantiates_struct_named_only_in_tuple():
    src = """\
struct Box<T>
    value: T

fn main() -> i32
    let t: (Box<i32>, i32) = (Box<i32> { value: 1 }, 2)
    0
"""
    result = monomorphize(parse(src))
    main = next(i for i in result.items
                if isinstance(i, rast.FnDef) and i.name == "main")
    let_ty = main.body.stmts[0].type
    assert let_ty.elements[0].name == "Box$i32"


@pytest.mark.integration
def test_ritz0_tuple_generic_param_runs(tmp_path):
    """The ticket's program: `first<i64>` must read the i64 back, exit 5."""
    from ritz0_inproc import run_ritz0

    src = tmp_path / "first.ritz"
    src.write_text(FIRST_SRC)
    ll = tmp_path / "first.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    assert comp.returncode == 0 and ll.exists(), comp.stderr[-2000:]
    assert '{i8, i32}' not in ll.read_text()
    exe = tmp_path / "first"
    link = subprocess.run(["clang", str(ll), "-o", str(exe), "-nostdlib"],
                          capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-2000:]
    assert subprocess.run([str(exe)], timeout=60).returncode == 5
