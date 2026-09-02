"""Tests for slice types as generic type arguments (AGAST #1285).

`[T]` is surface sugar for `Span<T>` — both denote the same non-owning
`{ ptr, len }` view. Historically the parser produced a distinct `SliceType`
AST node that only a handful of passes understood, so a slice used as a
*generic argument* (`Option<[u8]>`, `Result<[u8], E>`) blew up in the emitter
with `ValueError: Unknown type: SliceType(...)` when the builtin generic was
specialized.

The fix desugars `[T]` to `Span<T>` at every point a slice type is
constructed (hand-written parser, generated-parser adapter, and the metadata
type-string parser), so *every* downstream consumer — name resolution, type
checking, monomorphization, mangling, emission — sees one type.

These tests pin both halves: the desugaring itself, and the end-to-end
behaviour of slice payloads inside `Option`/`Result`.
"""

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import ritz_ast as rast  # noqa: E402
from emitter_llvmlite import emit  # noqa: E402
from lexer import Lexer  # noqa: E402
from parser import Parser  # noqa: E402

RITZ0_DIR = Path(__file__).parent
PROJECTS_DIR = RITZ0_DIR.parent.parent  # <root>/projects


def parse(source: str) -> rast.Module:
    """Parse ritz source to a module AST."""
    return Parser(Lexer(source, "test.ritz").tokenize()).parse_module()


def compile_to_ir(source: str) -> str:
    """Compile ritz source all the way to LLVM IR text."""
    return emit(parse(source), no_runtime=True)


def assert_is_span(ty: rast.Type, inner_name: str) -> None:
    """Assert `ty` is the desugared `Span<inner_name>` form of a slice type."""
    assert isinstance(ty, rast.NamedType), f"expected NamedType, got {ty!r}"
    assert ty.name == "Span", f"expected Span, got {ty.name}"
    assert len(ty.args) == 1
    assert isinstance(ty.args[0], rast.NamedType)
    assert ty.args[0].name == inner_name


class TestSliceDesugaring:
    """`[T]` parses as `Span<T>`, everywhere a type can appear."""

    def test_slice_param_type(self):
        fn = parse("fn f(x: [u8]) -> i32\n    0\n").items[0]
        assert_is_span(fn.params[0].type, "u8")

    def test_slice_return_type(self):
        fn = parse("fn f() -> [i32]\n    0\n").items[0]
        assert_is_span(fn.ret_type, "i32")

    def test_slice_as_generic_argument(self):
        """The bug's actual shape: a slice nested inside a generic."""
        fn = parse("fn f() -> Result<[u8], i32>\n    0\n").items[0]
        ret = fn.ret_type
        assert isinstance(ret, rast.NamedType)
        assert ret.name == "Result"
        assert_is_span(ret.args[0], "u8")

    def test_slice_of_non_primitive_inner(self):
        """`[Foo]` takes the generic (non-IDENT-fastpath) parse branch."""
        fn = parse("struct Foo\n    a: i32\n\nfn f(x: [*Foo]) -> i32\n    0\n").items[1]
        ty = fn.params[0].type
        assert isinstance(ty, rast.NamedType) and ty.name == "Span"
        assert isinstance(ty.args[0], rast.PtrType)

    def test_slice_behind_reference(self):
        fn = parse("fn f(x: @[u32]) -> i32\n    0\n").items[0]
        ty = fn.params[0].type
        assert isinstance(ty, rast.RefType)
        assert_is_span(ty.inner, "u32")

    def test_array_type_still_distinct(self):
        """Desugaring must not swallow the sized-array form `[N]T`."""
        fn = parse("fn f(x: [4]u8) -> i32\n    0\n").items[0]
        assert isinstance(fn.params[0].type, rast.ArrayType)

    def test_array_with_const_size_still_distinct(self):
        source = "const N: i64 = 4\n\nfn f(x: [N]u8) -> i32\n    0\n"
        fn = parse(source).items[1]
        assert isinstance(fn.params[0].type, rast.ArrayType)

    def test_metadata_type_string_desugars(self):
        """Cached metadata written before the fix still loads as a Span."""
        from import_resolver import parse_type_string

        assert_is_span(parse_type_string("[]u8"), "u8")

    def test_metadata_array_type_string_unaffected(self):
        from import_resolver import parse_type_string

        assert isinstance(parse_type_string("[4]u8"), rast.ArrayType)


class TestSliceGenericSpecialization:
    """Builtin generics specialize with a slice payload without blowing up."""

    def test_option_slice_specializes(self):
        ir = compile_to_ir(
            "fn f(d: Span<u8>) -> Option<[u8]>\n"
            "    Some(d[0..1])\n"
        )
        assert "Option$" in ir

    def test_result_slice_specializes(self):
        ir = compile_to_ir(
            "fn f(d: Span<u8>) -> Result<[u8], i32>\n"
            "    Ok(d[0..1])\n"
        )
        assert "Result$" in ir

    def test_slice_payload_mangles_as_span(self):
        """A slice payload names the same specialization a Span payload would.

        `Option<Span<u8>>` cannot be spelled directly yet (the lexer does not
        split the `>>` closing two nested type-argument lists), so this asserts
        on the mangled specialization name the Span form would also produce.
        """
        ir = compile_to_ir(
            "fn f(d: Span<u8>) -> Option<[u8]>\n"
            "    Some(d[0..1])\n"
        )
        assert "Option$Span$u8" in ir


def run_ritzunit(name: str) -> None:
    """Run a ritzunit suite from ritz0/test and assert every case passed."""
    test_file = RITZ0_DIR / "test" / name
    assert test_file.exists(), test_file

    env = dict(os.environ)
    env.setdefault("RITZ_PATH", str(PROJECTS_DIR))
    result = subprocess.run(
        [sys.executable, str(RITZ0_DIR / "ritz0.py"), str(test_file), "--test"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(RITZ0_DIR),
    )
    assert "0 failed" in result.stdout, (
        f"ritzunit run failed\n--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
    assert result.returncode == 0, result.stderr


class TestSliceGenericRuntime:
    """End-to-end: the ritzunit suites for this work pass."""

    def test_slice_generic_payload_suite(self):
        run_ritzunit("test_issue_slice_generic_payload.ritz")

    def test_slice_generic_sibling_suite(self):
        """The gaps found alongside the slice-as-generic-argument bug."""
        run_ritzunit("test_issue_slice_generic_siblings.ritz")


class TestNumericLiteralSuffixes:
    """`0u32` lexes as one literal, not `0` followed by an identifier."""

    def test_int_suffix(self):
        from lexer import tokenize

        tokens = tokenize("0u32")
        assert len(tokens) == 2, tokens  # INT, EOF
        assert tokens[0].value == 0
        assert tokens[0].suffix == "u32"

    def test_float_suffix(self):
        from lexer import tokenize

        tokens = tokenize("1.5f32")
        assert tokens[0].value == 1.5
        assert tokens[0].suffix == "f32"

    def test_hex_suffix(self):
        from lexer import tokenize

        tokens = tokenize("0x64u8")
        assert len(tokens) == 2, tokens
        assert tokens[0].value == 0x64
        assert tokens[0].suffix == "u8"

    def test_identifier_is_not_a_suffix(self):
        from lexer import tokenize

        tokens = tokenize("0u32x")
        # `u32x` is a longer identifier, so nothing is consumed as a suffix.
        assert tokens[0].suffix is None
        assert tokens[1].value == "u32x"

    def test_suffix_lowers_to_a_cast(self):
        fn = parse("fn f() -> u32\n    0u32\n").items[0]
        cast = fn.body.expr
        assert isinstance(cast, rast.Cast), cast
        assert isinstance(cast.expr, rast.IntLit)
        assert cast.target.name == "u32"

    def test_unsuffixed_literal_is_untouched(self):
        fn = parse("fn f() -> i64\n    7\n").items[0]
        assert isinstance(fn.body.expr, rast.IntLit)
