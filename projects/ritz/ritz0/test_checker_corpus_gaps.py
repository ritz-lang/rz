"""Checker false positives and crashes found running the corpus (AGAST #1823).

`--check-names` / `--check-types` had never run over real code. Each test here
is a valid program a checker rejected or crashed on, or an invalid one a fix
must not start accepting.
"""

import pytest
from parser import parse
from name_resolver import resolve_names
from type_checker import TypeChecker


def names(source: str) -> list:
    return [str(e) for e in resolve_names(parse(source))]


def types(source: str) -> list:
    return [str(e) for e in TypeChecker().check(parse(source))]


ENUM = """
enum Color
    Red
    Green(i32)

"""
POINT = """
struct Point
    x: i32
    y: i32

impl Point
    fn origin() -> Point
        Point { x: 0, y: 0 }

"""


class TestNameResolverCrashes:
    def test_struct_literal_field_values_are_walked(self):
        src = POINT + "fn main() -> i32\n    let p = Point { x: 1, y: missing }\n    0\n"
        assert any("missing" in e for e in names(src))

    def test_match_scrutinee_is_walked(self):
        src = "fn main() -> i32\n    match missing\n        _ => 0\n"
        assert any("missing" in e for e in names(src))

    def test_variant_pattern_binds_its_fields(self):
        src = ENUM + (
            "fn f(c: Color) -> i32\n    match c\n        Green(n) => n\n"
            "        Red => 0\n")
        assert names(src) == []

    def test_struct_pattern_binds_its_fields(self):
        # The parser has no struct-pattern syntax yet, so build the node.
        import ritz_ast as rast
        module = parse(POINT + "fn f(p: Point) -> i32\n    match p\n        _ => 0\n")
        match = next(i for i in module.items
                     if isinstance(i, rast.FnDef) and i.name == "f").body.expr
        arm = match.arms[0]
        span = arm.span
        arm.pattern = rast.StructPattern(
            span, "Point", [("x", rast.IdentPattern(span, "a", False))])
        arm.body = rast.Ident(span, "a")
        assert resolve_names(module) == []


class TestNameResolverFalsePositives:
    @pytest.mark.parametrize("ty", ["usize", "isize", "StrView"])
    def test_builtin_types(self, ty):
        assert names(f"fn f(x: {ty}) -> i32\n    0\n") == []

    def test_fn_type_param(self):
        assert names("fn id<T>(x: T) -> T\n    x\n") == []

    def test_struct_type_param(self):
        assert names("struct Box<T>\n    v: T\n") == []

    def test_impl_type_param(self):
        src = "struct Box<T>\n    v: T\n\nimpl<T> Box<T>\n    fn get(self: @Box<T>) -> T\n        self.v\n"
        assert names(src) == []

    @pytest.mark.parametrize("fn", [
        "aesenc", "aesdec", "aesimc", "aesenclast", "aesdeclast",
        "aeskeygenassist", "simd_add", "simd_xor", "simd_rotl", "cpuid_raw",
        "xgetbv", "sha256rnds2", "sha256msg1", "sha256msg2"])
    def test_emitter_intrinsics(self, fn):
        assert names(f"fn f() -> i32\n    {fn}(1, 2)\n    0\n") == []

    def test_nil_is_a_keyword(self):
        assert names("fn f() -> *u8\n    nil\n") == []

    def test_type_name_as_method_receiver(self):
        src = POINT + "fn f() -> Point\n    Point.origin()\n"
        assert names(src) == []

    def test_variant_constructor_and_unit_variant(self):
        src = ENUM + "fn f() -> Color\n    let a = Red\n    Green(1)\n"
        assert names(src) == []

    def test_call_through_local_fn_pointer(self):
        assert names("fn f(g: fn(i32) -> i32) -> i32\n    g(1)\n") == []

    def test_let_tuple_binds_its_names(self):
        assert names("fn f() -> i64\n    let (a, b) = (1, 2)\n    a + b\n") == []

    def test_still_rejects_unknown_function_and_type(self):
        errs = names("fn f(x: Nope) -> i32\n    nope(1)\n")
        assert any("Nope" in e for e in errs)
        assert any("nope" in e for e in errs)


class TestTypeCheckerFalsePositives:
    def test_global_var(self):
        assert types("var g_n: i32 = 0\n\nfn f() -> i32\n    g_n + 1\n") == []

    @pytest.mark.parametrize("ty", ["usize", "isize"])
    def test_pointer_sized_ints_are_integers(self, ty):
        assert types(f"fn f(a: [4]i32, i: {ty}) -> i32\n    a[i + 1]\n") == []

    def test_intrinsic(self):
        assert types("fn f() -> i32\n    aesenc(1, 2)\n    0\n") == []

    def test_enum_name_as_field_base(self):
        assert types(ENUM + "fn f() -> Color\n    Color.Red\n") == []

    def test_struct_name_as_static_receiver(self):
        assert types(POINT + "fn f() -> i32\n    Point.origin().x\n") == []

    def test_interp_string(self):
        assert types('fn f(n: i32) -> i32\n    print("n={n}\\n")\n    0\n') == []

    def test_interp_string_walks_its_expressions(self):
        errs = types('fn f() -> i32\n    print("n={nope}\\n")\n    0\n')
        assert any("nope" in e for e in errs)

    def test_float_literal_takes_f32_from_context(self):
        src = ("struct Q\n    a: f32\n\n"
               "fn f(q: Q) -> bool\n    let x: f32 = 1.5\n    q.a != 9.5\n")
        assert types(src) == []

    def test_f64_variable_is_not_an_f32(self):
        src = "fn f(d: f64) -> i32\n    let x: f32 = d\n    0\n"
        assert any("f32" in e for e in types(src))

    def test_null_for_a_type_param(self):
        src = "fn g<T>(d: T) -> T\n    d\n\nfn h<T>() -> T\n    g<T>(null)\n"
        assert types(src) == []

    def test_impl_type_param_is_opaque(self):
        src = ("struct Box<T>\n    v: T\n\nimpl<T> Box<T>\n"
               "    fn twice(self: @Box<T>) -> T\n        self.v + self.v\n")
        assert types(src) == []

    def test_method_return_checks_against_its_own_signature(self):
        # `size` as a free fn returns *u8; the method must not inherit that.
        src = ("struct S\n    n: i32\n\nfn size() -> *u8\n    null\n\nimpl S\n"
               "    fn size(self: @S) -> i32\n        return self.n\n")
        assert types(src) == []

    def test_type_alias_resolves(self):
        src = "type Fd = i32\n\nfn f(a: Fd) -> i32\n    a + 1\n"
        assert types(src) == []

    def test_fn_name_as_value(self):
        src = ("fn inc(x: i32) -> i32\n    x + 1\n\n"
               "fn f() -> i32\n    let g: fn(i32) -> i32 = inc\n    g(1)\n")
        assert types(src) == []

    def test_let_tuple_and_unsafe_block(self):
        src = ("fn f() -> i64\n    let (a, b) = (1, 2)\n    unsafe\n"
               "        let c = a\n    a + b\n")
        assert types(src) == []

    def test_unknown_does_not_cascade(self):
        errs = types("fn f() -> i32\n    let v = missing\n    v.x + 1\n")
        assert len(errs) == 1 and "missing" in errs[0]


class TestStillRejected:
    """The acceptance cases: loosening must not lose these."""

    def test_ptr_where_strview_expected(self):
        src = "fn t(s: StrView) -> i32\n    0\n\nfn f(p: *u8) -> i32\n    t(p)\n"
        errs = types(src)
        assert any("expected StrView, got *u8" in e for e in errs)

    def test_error_carries_line_and_column(self):
        src = "fn t(s: StrView) -> i32\n    0\n\nfn f(p: *u8) -> i32\n    t(p)\n"
        assert any(":5:7:" in e for e in types(src))

    def test_int_mask_condition(self):
        # `x & 0x80 != 0` parses as `x & (0x80 != 0)`: an int, not a bool.
        errs = types("fn f(x: i32) -> i32\n    if x & 0x80 != 0\n        return 1\n    0\n")
        assert any("if condition must be bool" in e for e in errs)

    def test_undefined_variable(self):
        assert any("undefined variable: nope" in e
                   for e in types("fn f() -> i32\n    nope\n"))


class TestEmitterBuiltins:
    """Names the emitter supplies, with no declaration in any source file."""

    def test_pass_statement(self):
        src = "fn f() -> i32\n    pass\n    0\n"
        assert names(src) == [] and types(src) == []

    @pytest.mark.parametrize("ty", ["Option<i32>", "Result<i32, StrView>", "Span<u8>"])
    def test_builtin_generic_types(self, ty):
        assert names(f"fn f(x: {ty}) -> i32\n    0\n") == []

    def test_builtin_variants(self):
        src = ("fn a() -> Option<i32>\n    Some(1)\n\nfn b() -> Option<i32>\n    None\n\n"
               "fn c() -> Result<i32, i32>\n    Ok(1)\n\n"
               "fn d() -> Result<i32, i32>\n    Err(1)\n")
        assert names(src) == [] and types(src) == []

    def test_self_type(self):
        src = "struct S\n    n: i32\n\nimpl S\n    fn mk() -> Self\n        S { n: 0 }\n"
        assert names(src) == [] and types(src) == []

    def test_strview_fields(self):
        assert types("fn f(s: StrView) -> i64\n    s.len\n") == []

    def test_strview_has_no_other_fields(self):
        errs = types("fn f(s: StrView) -> i32\n    s.data\n    0\n")
        assert any("no field 'data'" in e for e in errs)

    @pytest.mark.parametrize("recv,method", [
        ("Result<i32, i32>", "unwrap"), ("Span<u8>", "len"),
        ("u32", "popcnt"), ("f32", "ceil")])
    def test_methods_the_emitter_provides(self, recv, method):
        assert types(f"fn f(x: {recv}) -> i32\n    x.{method}()\n    0\n") == []

    def test_method_missing_on_a_user_struct_is_still_an_error(self):
        errs = types("struct S\n    n: i32\n\nfn f(s: S) -> i32\n    s.nope()\n    0\n")
        assert any("no method 'nope'" in e for e in errs)


class TestModuleQualifiers:
    """`import lib.css.token` makes `token.X` a name."""

    SRC = ("struct Tok\n    kind: i32\n\nconst K: i32 = 1\n\n"
           "fn f(t: token.Tok) -> i32\n"
           "    if t.kind == token.K\n        return 1\n    0\n")

    def test_names(self):
        assert resolve_names(parse(self.SRC), {"token"}) == []

    def test_types(self):
        assert TypeChecker({"token"}).check(parse(self.SRC)) == []

    def test_qualifier_on_a_pattern(self):
        src = ("enum E\n    A\n\nfn f(e: E) -> i32\n    match e\n"
               "        token.A => 1\n        _ => 0\n")
        assert resolve_names(parse(src), {"token"}) == []

    def test_unimported_qualifier_is_still_an_error(self):
        assert resolve_names(parse(self.SRC), set()) != []


class TestRoundThree:
    def test_single_capital_struct_is_not_a_type_param(self):
        src = "struct S\n    n: i32\n\nfn f(s: S) -> i32\n    let p: *u8 = s\n    0\n"
        assert any("cannot initialize" in e for e in types(src))

    def test_closure_params_are_in_scope(self):
        src = "fn f() -> i32\n    let g = |x| x + 1\n    0\n"
        assert names(src) == [] and types(src) == []

    def test_union_alias_accepts_itself(self):
        src = "type N = i32 | bool\n\nfn f(a: N) -> i32\n    let b: N = a\n    0\n"
        assert types(src) == []

    def test_variant_constructor_through_enum_name(self):
        assert types(ENUM + "fn f() -> Color\n    Color.Green(1)\n") == []

    def test_sizeof_takes_a_type(self):
        src = "fn f() -> i64\n    sizeof(i32) + sizeof(u8)\n"
        assert names(src) == [] and types(src) == []

    def test_multi_segment_qualifier(self):
        src = "struct K\n    n: i32\n\nfn f(k: fs.kblob.K) -> i32\n    k.n\n"
        assert resolve_names(parse(src), {"kblob"}) == []
        assert TypeChecker({"kblob"}).check(parse(src)) == []

    def test_async_fn_future_type(self):
        src = "async fn get() -> i32\n    1\n\nfn f(p: get_Future) -> i32\n    0\n"
        assert names(src) == []

    def test_builtin_variant_pattern_binds(self):
        src = ("fn g(n: i32) -> i32\n    n\n\n"
               "fn f(r: Result<i32, i32>) -> i32\n    match r\n"
               "        Ok(v) => g(v)\n        Err(e) => g(e)\n")
        assert names(src) == [] and types(src) == []

    def test_async_call_yields_a_future_not_its_return_type(self):
        src = ("async fn get() -> i32\n    1\n\n"
               "fn f() -> i32\n    var p: get_Future = get()\n    0\n")
        assert types(src) == []

    def test_union_type_members_are_resolved(self):
        module = parse("fn f(a: i32 | Nope) -> i32\n    0\n")
        assert any("Nope" in str(e) for e in resolve_names(module))


class TestMutationSurvivors:
    """Each of these was a mutant the tests above let through."""

    def test_impl_type_param_with_a_long_name(self):
        src = ("struct Box<Elem>\n    v: Elem\n\nimpl<Elem> Box<Elem>\n"
               "    fn twice(self: @Box<Elem>) -> Elem\n        self.v + self.v\n")
        assert types(src) == []

    def test_unsafe_body_is_checked(self):
        src = "fn f() -> i32\n    unsafe\n        nope\n    0\n"
        assert any("undefined variable: nope" in e for e in types(src))

    def test_module_qualified_const_keeps_its_type(self):
        src = "const K: i32 = 1\n\nfn f() -> i32\n    let p: *u8 = token.K\n    0\n"
        errs = [str(e) for e in TypeChecker({"token"}).check(parse(src))]
        assert any("cannot initialize *u8 with i32" in e for e in errs)


@pytest.mark.integration
class TestThroughCompileFile:
    """The flags end to end: the wiring in ritz0.py, not just the passes."""

    def run(self, tmp_path, source, *flags):
        import subprocess
        import sys
        from pathlib import Path
        (tmp_path / "token.ritz").write_text("pub const KIND: i32 = 1\n")
        main = tmp_path / "main.ritz"
        main.write_text(source)
        ritz0 = Path(__file__).with_name("ritz0.py")
        return subprocess.run(
            [sys.executable, str(ritz0), str(main), "-o", str(tmp_path / "o.ll"),
             "--no-runtime", "--project-root", str(tmp_path), *flags],
            capture_output=True, text=True)

    def test_ill_typed_program_rejected_with_location(self, tmp_path):
        r = self.run(tmp_path, "fn t(s: StrView) -> i32\n    0\n\n"
                               "fn f(p: *u8) -> i32\n    t(p)\n", "--check-types")
        assert r.returncode != 0
        assert "main.ritz:5:7: argument 1 ('s'): expected StrView, got *u8" in r.stderr

    def test_import_is_a_qualifier_for_both_checkers(self, tmp_path):
        r = self.run(tmp_path, "import token\n\nfn f() -> i32\n    token.KIND\n",
                     "--check-types", "--check-names")
        assert r.returncode == 0, r.stderr
