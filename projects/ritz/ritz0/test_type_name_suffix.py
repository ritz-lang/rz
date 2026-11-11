"""The emitter's `_type_to_name_suffix` spells every type, without a span.

AGAST #2742: `_type_to_name_suffix` named NamedType, PtrType and TupleType
and fell back to `str(ty)` for everything else. `str(ty)` embeds the source
span, so `Box2<fn(i32) -> i32>` written at two places gave two struct names
for one type (the #1321 defect, in a different set of types). It also spelled
`*mut T` as `ptr_T`, while `mangle_type_name` spells `ptrmut_T`, so one type
had two names depending on which path named it.

The suffix now matches `mangle_type_name` for every Type node, except that a
generic NamedType nested inside keeps the emitter's `Base$args` spelling
(the name the struct is registered under), and raises on an unknown node.
"""

from dataclasses import dataclass

import pytest

import ritz_ast as rast
from emitter_llvmlite import LLVMEmitter
from monomorph import mangle_type_name
from ritz0_inproc import run_ritz0


def named(name, *args):
    return rast.NamedType(None, name, list(args))


I32 = named("i32")
U8 = named("u8")


def suffix(ty):
    return LLVMEmitter()._type_to_name_suffix(ty)


# Every Type node whose spelling has no nested generic NamedType: here the
# emitter and the monomorphizer must agree exactly.
AGREE = [
    pytest.param(I32, id="named"),
    pytest.param(rast.PtrType(None, U8, False), id="ptr"),
    pytest.param(rast.PtrType(None, U8, True), id="ptrmut"),
    pytest.param(rast.RefType(None, I32, False), id="ref"),
    pytest.param(rast.RefType(None, I32, True), id="refmut"),
    pytest.param(rast.ArrayType(None, 4, I32), id="array"),
    pytest.param(rast.SliceType(None, I32), id="slice"),
    pytest.param(rast.TupleType(None, []), id="unit"),
    pytest.param(rast.TupleType(None, [I32, U8]), id="tuple"),
    pytest.param(rast.FnType(None, [I32], I32), id="fn"),
    pytest.param(rast.FnType(None, [I32, U8], None), id="fn-unit-ret"),
    pytest.param(rast.DynType(None, "Show", []), id="dyn"),
    pytest.param(rast.DynType(None, "Iter", [I32]), id="dyn-args"),
    pytest.param(rast.VectorType(None, 4, I32), id="vector"),
    pytest.param(rast.UnionType(None, [I32, U8]), id="union"),
    pytest.param(rast.FnType(None, [rast.PtrType(None, U8, True)],
                             rast.TupleType(None, [])), id="fn-nested"),
]


@pytest.mark.unit
@pytest.mark.parametrize("ty", AGREE)
def test_suffix_matches_mangle_type_name(ty):
    assert suffix(ty) == mangle_type_name(ty)


@pytest.mark.unit
@pytest.mark.parametrize("ty", AGREE)
def test_suffix_has_no_span(ty):
    assert "span" not in suffix(ty)


@pytest.mark.unit
def test_ptr_mutability_is_spelled():
    assert suffix(rast.PtrType(None, U8, True)) != suffix(
        rast.PtrType(None, U8, False))


@pytest.mark.unit
def test_nested_generic_keeps_emitter_spelling():
    # Inside a fn type, `Vec<i32>` is the struct `Vec$i32`, as at top level.
    assert suffix(rast.FnType(None, [named("Vec", I32)], I32)) == (
        "fn1_Vec$i32_ret_i32")


@pytest.mark.unit
def test_unknown_type_node_raises():
    @dataclass
    class Mystery(rast.Type):
        pass

    with pytest.raises(TypeError, match="Mystery"):
        suffix(Mystery(None))


def _compile(tmp_path, source):
    src = tmp_path / "prog.ritz"
    src.write_text(source)
    ll_path = tmp_path / "prog.ll"
    result = run_ritz0([str(src), "-o", str(ll_path), "--no-runtime"])
    assert result.returncode == 0, result.stderr
    return ll_path.read_text()


# `Box2<fn(i32) -> i32>` written at two spans (the ticket's case). The
# monomorphizer names user structs, so this guards the struct path.
TWO_FN_BOXES = """\
struct Box2<T>
    val: T

fn double(x: i32) -> i32
    x * 2

fn make() -> Box2<fn(i32) -> i32>
    Box2<fn(i32) -> i32> { val: double }

fn run(b: Box2<fn(i32) -> i32>) -> i32
    let f: fn(i32) -> i32 = b.val
    f(21)

fn main() -> i32
    run(make()) - 42
"""


@pytest.mark.integration
def test_fn_type_struct_arg_at_two_spans_one_struct(tmp_path):
    ll = _compile(tmp_path, TWO_FN_BOXES)
    assert "span=" not in ll, "a mangled name still embeds a source span"
    assert '"struct.ritz_module_1.Box2$fn1_i32_ret_i32" = type' in ll


# `Option<fn(i32) -> i32>` written at two spans. The emitter synthesizes
# Option itself, so this is where `str(ty)` leaked the span: two enums,
# `Option$FnType(span=...:4:27, ...)` and `Option$FnType(span=...:9:28, ...)`.
TWO_FN_OPTIONS = """\
fn dbl(x: i32) -> i32
    x * 2

fn pick(n: i32) -> Option<fn(i32) -> i32>
    if n < 0
        return None
    Some(dbl)

fn pick2(n: i32) -> Option<fn(i32) -> i32>
    pick(n)

fn main() -> i32
    match pick2(1)
        Some(f) => f(21) - 42
        None => 1
"""


@pytest.mark.integration
def test_fn_type_option_at_two_spans_one_enum(tmp_path):
    ll = _compile(tmp_path, TWO_FN_OPTIONS)
    assert "span=" not in ll, "a mangled name still embeds a source span"
    assert '"Option$fn1_i32_ret_i32"' in ll


# `Span<*mut u8>` is named by the emitter; it must spell the mutability the
# way the monomorphizer does (`ptrmut_`), not collapse it into `ptr_`.
MUT_PTR_SPAN = """\
fn first(s: Span<*mut u8>) -> i64
    s.len

fn main() -> i32
    0
"""


@pytest.mark.integration
def test_mut_ptr_span_spells_ptrmut(tmp_path):
    ll = _compile(tmp_path, MUT_PTR_SPAN)
    assert '"Span$ptrmut_u8"' in ll
    assert '"Span$ptr_u8"' not in ll
