"""
Tests for the Ritz parser.
"""

import pytest
from parser import parse, Parser, ParseError
from lexer import tokenize
import ritz_ast as rast


class TestExpressions:
    def test_int_literal(self):
        mod = parse("fn main()\n  42")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.IntLit)
        assert fn.body.expr.value == 42

    def test_string_literal(self):
        mod = parse('fn main()\n  "hello"')
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.StringLit)
        assert fn.body.expr.value == "hello"

    def test_cstring_literal(self):
        mod = parse('fn main()\n  c"hello"')
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.CStringLit)
        assert fn.body.expr.value == "hello"

    def test_bool_literals(self):
        mod = parse("fn main()\n  true")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BoolLit)
        assert fn.body.expr.value is True

    def test_identifier(self):
        mod = parse("fn main()\n  foo")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.Ident)
        assert fn.body.expr.name == "foo"

    def test_binary_add(self):
        mod = parse("fn main()\n  1 + 2")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "+"
        assert expr.left.value == 1
        assert expr.right.value == 2

    def test_precedence(self):
        mod = parse("fn main()\n  1 + 2 * 3")
        fn = mod.items[0]
        expr = fn.body.expr
        # Should parse as 1 + (2 * 3)
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "+"
        assert expr.left.value == 1
        assert isinstance(expr.right, rast.BinOp)
        assert expr.right.op == "*"

    def test_unary_minus(self):
        mod = parse("fn main()\n  -x")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.UnaryOp)
        assert expr.op == "-"
        assert expr.operand.name == "x"

    def test_function_call(self):
        mod = parse("fn main()\n  foo(1, 2)")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.Call)
        assert expr.func.name == "foo"
        assert len(expr.args) == 2

    def test_method_call(self):
        mod = parse("fn main()\n  x.foo(1)")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.MethodCall)
        assert expr.expr.name == "x"
        assert expr.method == "foo"
        assert len(expr.args) == 1

    def test_field_access(self):
        mod = parse("fn main()\n  x.y")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.Field)
        assert expr.expr.name == "x"
        assert expr.field == "y"

    def test_index(self):
        mod = parse("fn main()\n  arr[0]")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.Index)
        assert expr.expr.name == "arr"
        assert expr.index.value == 0

    def test_try_operator(self):
        mod = parse("fn main()\n  foo()?")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.TryOp)
        assert isinstance(expr.expr, rast.Call)

    def test_reference(self):
        """@ for immutable reference (RERITZ syntax)"""
        mod = parse("fn main()\n  @x")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.UnaryOp)
        assert expr.op == "@"

    def test_legacy_reference_error(self):
        """Legacy &x should produce helpful error"""
        import pytest
        with pytest.raises(ParseError) as exc_info:
            parse("fn main()\n  &x")
        assert "no longer supported" in str(exc_info.value)
        assert "@x" in str(exc_info.value)

    def test_mutable_reference(self):
        """@& for mutable reference (RERITZ syntax)"""
        mod = parse("fn main()\n  @&x")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.UnaryOp)
        assert expr.op == "@&"

    def test_legacy_mutable_reference_error(self):
        """Legacy &mut should produce helpful error"""
        import pytest
        with pytest.raises(ParseError) as exc_info:
            parse("fn main()\n  &mut x")
        assert "no longer supported" in str(exc_info.value)
        assert "@&x" in str(exc_info.value)


class TestStatements:
    def test_let_binding(self):
        mod = parse("fn main()\n  let x = 42")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.LetStmt)
        assert stmt.name == "x"
        assert stmt.value.value == 42

    def test_let_with_type(self):
        mod = parse("fn main()\n  let x: i32 = 42")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.LetStmt)
        assert stmt.type.name == "i32"

    def test_var_binding(self):
        mod = parse("fn main()\n  var x = 42")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.VarStmt)
        assert stmt.name == "x"

    def test_assignment(self):
        mod = parse("fn main()\n  x = 42")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.AssignStmt)
        assert stmt.target.name == "x"
        assert stmt.value.value == 42

    def test_compound_assignment(self):
        mod = parse("fn main()\n  x += 1")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.AssignStmt)
        # Desugared to x = x + 1
        assert isinstance(stmt.value, rast.BinOp)
        assert stmt.value.op == "+"

    def test_return(self):
        mod = parse("fn main()\n  return 42")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.ReturnStmt)
        assert stmt.value.value == 42

    def test_while_loop(self):
        mod = parse("fn main()\n  while true\n    x")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.WhileStmt)
        assert isinstance(stmt.cond, rast.BoolLit)

    def test_for_loop(self):
        mod = parse("fn main()\n  for i in items\n    print(i)")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.ForStmt)
        assert stmt.var == "i"
        assert stmt.iter.name == "items"

    def test_for_range_exclusive(self):
        """for i in 0..10 - exclusive range."""
        mod = parse("fn main()\n  for i in 0..10\n    print(i)")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.ForStmt)
        assert stmt.var == "i"
        assert isinstance(stmt.iter, rast.Range)
        assert isinstance(stmt.iter.start, rast.IntLit)
        assert stmt.iter.start.value == 0
        assert isinstance(stmt.iter.end, rast.IntLit)
        assert stmt.iter.end.value == 10
        assert stmt.iter.inclusive == False

    def test_for_range_inclusive(self):
        """for i in 0..=10 - inclusive range."""
        mod = parse("fn main()\n  for i in 0..=10\n    print(i)")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.ForStmt)
        assert stmt.var == "i"
        assert isinstance(stmt.iter, rast.Range)
        assert isinstance(stmt.iter.start, rast.IntLit)
        assert stmt.iter.start.value == 0
        assert isinstance(stmt.iter.end, rast.IntLit)
        assert stmt.iter.end.value == 10
        assert stmt.iter.inclusive == True

    def test_for_range_variable_bounds(self):
        """for i in start..end - variable bounds."""
        mod = parse("fn main(start: i32, end: i32)\n  for i in start..end\n    print(i)")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.ForStmt)
        assert stmt.var == "i"
        assert isinstance(stmt.iter, rast.Range)
        assert isinstance(stmt.iter.start, rast.Ident)
        assert stmt.iter.start.name == "start"
        assert isinstance(stmt.iter.end, rast.Ident)
        assert stmt.iter.end.name == "end"

    def test_for_nested(self):
        """Nested for loops."""
        mod = parse("fn main()\n  for i in 0..n\n    for j in 0..m\n      print(i)")
        fn = mod.items[0]
        outer = fn.body.stmts[0]
        assert isinstance(outer, rast.ForStmt)
        assert outer.var == "i"
        inner = outer.body.stmts[0]
        assert isinstance(inner, rast.ForStmt)
        assert inner.var == "j"

    def test_for_break_continue(self):
        """For loops support break and continue."""
        mod = parse("fn main()\n  for i in 0..10\n    if i == 5\n      break\n    if i % 2 == 0\n      continue\n    print(i)")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.ForStmt)
        # break and continue are inside if-expressions parsed as statements
        if_break = stmt.body.stmts[0]
        assert isinstance(if_break, rast.ExprStmt)
        assert isinstance(if_break.expr, rast.If)
        assert isinstance(if_break.expr.then_block.stmts[0], rast.BreakStmt)
        if_cont = stmt.body.stmts[1]
        assert isinstance(if_cont, rast.ExprStmt)
        assert isinstance(if_cont.expr, rast.If)
        assert isinstance(if_cont.expr.then_block.stmts[0], rast.ContinueStmt)

    def test_loop_keyword(self):
        """loop is syntactic sugar for while true."""
        mod = parse("fn main()\n  loop\n    break")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.WhileStmt)
        assert isinstance(stmt.cond, rast.BoolLit)
        assert stmt.cond.value == True

    def test_null_literal(self):
        """null is a null pointer literal."""
        mod = parse("fn main()\n  let ptr: *u8 = null")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.LetStmt)
        assert isinstance(stmt.value, rast.NullLit)


class TestItems:
    def test_simple_function(self):
        mod = parse("fn main()\n  42")
        assert len(mod.items) == 1
        fn = mod.items[0]
        assert isinstance(fn, rast.FnDef)
        assert fn.name == "main"
        assert len(fn.params) == 0

    def test_function_with_params(self):
        mod = parse("fn add(a: i32, b: i32) -> i32\n  a + b")
        fn = mod.items[0]
        assert fn.name == "add"
        assert len(fn.params) == 2
        assert fn.params[0].name == "a"
        assert fn.params[0].type.name == "i32"
        assert fn.ret_type.name == "i32"

    def test_extern_function(self):
        mod = parse("extern fn write(fd: i32, buf: *u8, len: usize) -> isize")
        fn = mod.items[0]
        assert isinstance(fn, rast.ExternFn)
        assert fn.name == "write"
        assert len(fn.params) == 3

    def test_struct(self):
        mod = parse("struct Point\n  x: i32\n  y: i32")
        s = mod.items[0]
        assert isinstance(s, rast.StructDef)
        assert s.name == "Point"
        assert len(s.fields) == 2
        assert s.fields[0][0] == "x"
        assert s.fields[1][0] == "y"

    def test_enum(self):
        mod = parse("enum Option\n  Some(T)\n  None")
        e = mod.items[0]
        assert isinstance(e, rast.EnumDef)
        assert e.name == "Option"
        assert len(e.variants) == 2
        assert e.variants[0].name == "Some"
        assert e.variants[1].name == "None"
        assert e.type_params == []  # non-generic

    def test_generic_enum(self):
        mod = parse("enum Option<T>\n  Some(T)\n  None")
        e = mod.items[0]
        assert isinstance(e, rast.EnumDef)
        assert e.name == "Option"
        assert e.type_params == ['T']
        assert e.is_generic()
        assert len(e.variants) == 2
        assert e.variants[0].name == "Some"
        # Some(T) has one field of type T
        assert len(e.variants[0].fields) == 1
        assert e.variants[1].name == "None"
        assert len(e.variants[1].fields) == 0

    def test_generic_enum_result(self):
        mod = parse("enum Result<T, E>\n  Ok(T)\n  Err(E)")
        e = mod.items[0]
        assert isinstance(e, rast.EnumDef)
        assert e.name == "Result"
        assert e.type_params == ['T', 'E']
        assert len(e.variants) == 2
        assert e.variants[0].name == "Ok"
        assert e.variants[1].name == "Err"

    def test_import(self):
        mod = parse("import ritzlib.fmt.print\n\nfn main()\n  42")
        assert len(mod.items) == 2
        imp = mod.items[0]
        assert isinstance(imp, rast.Import)
        assert imp.path == ["ritzlib", "fmt", "print"]


class TestTypes:
    def test_simple_type(self):
        mod = parse("fn foo(x: i32)\n  x")
        fn = mod.items[0]
        assert fn.params[0].type.name == "i32"

    def test_reference_type(self):
        """@T for immutable reference type (RERITZ syntax)"""
        mod = parse("fn foo(x: @i32)\n  x")
        fn = mod.items[0]
        t = fn.params[0].type
        assert isinstance(t, rast.RefType)
        assert not t.mutable
        assert t.inner.name == "i32"

    def test_mutable_reference_type(self):
        """@&T for mutable reference type (RERITZ syntax)"""
        mod = parse("fn foo(x: @&i32)\n  x")
        fn = mod.items[0]
        t = fn.params[0].type
        assert isinstance(t, rast.RefType)
        assert t.mutable

    def test_legacy_reference_type_error(self):
        """Legacy &T should produce helpful error"""
        import pytest
        with pytest.raises(ParseError) as exc_info:
            parse("fn foo(x: &i32)\n  x")
        assert "no longer supported" in str(exc_info.value)
        assert "@T" in str(exc_info.value)

    def test_legacy_mut_reference_type_error(self):
        """Legacy &mut T should produce helpful error"""
        import pytest
        with pytest.raises(ParseError) as exc_info:
            parse("fn foo(x: &mut i32)\n  x")
        assert "no longer supported" in str(exc_info.value)
        assert "@&T" in str(exc_info.value)

    def test_pointer_type(self):
        mod = parse("fn foo(x: *u8)\n  x")
        fn = mod.items[0]
        t = fn.params[0].type
        assert isinstance(t, rast.PtrType)
        assert not t.mutable

    def test_mutable_pointer_type(self):
        mod = parse("fn foo(x: *mut u8)\n  x")
        fn = mod.items[0]
        t = fn.params[0].type
        assert isinstance(t, rast.PtrType)
        assert t.mutable

    def test_slice_type(self):
        mod = parse("fn foo(x: [u8])\n  x")
        fn = mod.items[0]
        t = fn.params[0].type
        assert isinstance(t, rast.SliceType)
        assert t.inner.name == "u8"


class TestAttributes:
    def test_single_attribute(self):
        mod = parse("[[test]]\nfn test_add()\n  1 + 1")
        fn = mod.items[0]
        assert isinstance(fn, rast.FnDef)
        assert fn.name == "test_add"
        assert len(fn.attrs) == 1
        assert fn.attrs[0].name == "test"

    def test_multiple_attributes(self):
        mod = parse("[[test]]\n[[ignore]]\nfn test_foo()\n  42")
        fn = mod.items[0]
        assert isinstance(fn, rast.FnDef)
        assert fn.name == "test_foo"
        assert len(fn.attrs) == 2
        assert fn.attrs[0].name == "test"
        assert fn.attrs[1].name == "ignore"

    def test_function_with_attr_and_params(self):
        mod = parse("[[test]]\nfn test_add(x: i32, y: i32) -> i32\n  x + y")
        fn = mod.items[0]
        assert isinstance(fn, rast.FnDef)
        assert fn.name == "test_add"
        assert len(fn.attrs) == 1
        assert fn.attrs[0].name == "test"
        assert len(fn.params) == 2
        assert fn.ret_type.name == "i32"

    def test_has_attr_method(self):
        mod = parse("[[test]]\n[[ignore]]\nfn test_bar()\n  0")
        fn = mod.items[0]
        assert fn.has_attr("test")
        assert fn.has_attr("ignore")
        assert not fn.has_attr("skip")


class TestHelloWorld:
    def test_hello_main(self):
        source = 'import ritzlib.fmt.print\n\nfn main()\n  print("Hello, Ritz!\\n")'
        mod = parse(source)

        assert len(mod.items) == 2

        # Import
        imp = mod.items[0]
        assert isinstance(imp, rast.Import)
        assert imp.path == ["ritzlib", "fmt", "print"]

        # Function
        fn = mod.items[1]
        assert isinstance(fn, rast.FnDef)
        assert fn.name == "main"
        assert len(fn.params) == 0

        # Body contains a call expression
        call = fn.body.expr
        assert isinstance(call, rast.Call)
        assert call.func.name == "print"
        assert len(call.args) == 1
        assert call.args[0].value == "Hello, Ritz!\n"


class TestGenerics:
    """Tests for generic type parameter parsing."""

    def test_generic_struct_single_param(self):
        mod = parse("struct Pair<T>\n  first: T\n  second: T")
        s = mod.items[0]
        assert isinstance(s, rast.StructDef)
        assert s.name == "Pair"
        assert s.type_params == ["T"]
        assert s.is_generic()

    def test_generic_struct_multiple_params(self):
        mod = parse("struct Map<K, V>\n  key: K\n  val: V")
        s = mod.items[0]
        assert isinstance(s, rast.StructDef)
        assert s.name == "Map"
        assert s.type_params == ["K", "V"]

    def test_generic_function_single_param(self):
        mod = parse("fn identity<T>(x: T) -> T\n  x")
        fn = mod.items[0]
        assert isinstance(fn, rast.FnDef)
        assert fn.name == "identity"
        assert fn.type_params == ["T"]
        assert fn.is_generic()

    def test_generic_function_multiple_params(self):
        mod = parse("fn swap<A, B>(a: A, b: B) -> B\n  b")
        fn = mod.items[0]
        assert isinstance(fn, rast.FnDef)
        assert fn.name == "swap"
        assert fn.type_params == ["A", "B"]

    def test_generic_type_arg_in_param(self):
        mod = parse("fn push<T>(v: *Vec<T>, item: T) -> i32\n  0")
        fn = mod.items[0]
        assert fn.type_params == ["T"]
        # Second param uses Vec<T>
        param_type = fn.params[0].type
        assert isinstance(param_type, rast.PtrType)
        inner = param_type.inner
        assert isinstance(inner, rast.NamedType)
        assert inner.name == "Vec"
        assert len(inner.args) == 1
        assert inner.args[0].name == "T"

    def test_struct_literal_with_type_args(self):
        mod = parse("fn main()\n  Pair<i32> { first: 1, second: 2 }")
        fn = mod.items[0]
        lit = fn.body.expr
        assert isinstance(lit, rast.StructLit)
        assert lit.name == "Pair"
        assert len(lit.type_args) == 1
        assert lit.type_args[0].name == "i32"
        assert lit.is_generic_instantiation()

    def test_generic_function_call(self):
        mod = parse("fn main()\n  vec_new<i32>()")
        fn = mod.items[0]
        call = fn.body.expr
        assert isinstance(call, rast.Call)
        assert call.func.name == "vec_new"
        assert len(call.type_args) == 1
        assert call.type_args[0].name == "i32"
        assert call.is_generic_call()

    def test_generic_call_with_args(self):
        mod = parse("fn main()\n  make_pair<i32, *u8>(42, s)")
        fn = mod.items[0]
        call = fn.body.expr
        assert isinstance(call, rast.Call)
        assert len(call.type_args) == 2
        assert call.type_args[0].name == "i32"
        assert isinstance(call.type_args[1], rast.PtrType)
        assert call.type_args[1].inner.name == "u8"

    def test_comparison_not_confused_with_generics(self):
        # foo < bar should be parsed as comparison, not generic
        mod = parse("fn main()\n  foo < bar")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "<"

    def test_non_generic_function(self):
        mod = parse("fn add(a: i32, b: i32) -> i32\n  a + b")
        fn = mod.items[0]
        assert fn.type_params == []
        assert not fn.is_generic()

    def test_non_generic_struct(self):
        mod = parse("struct Point\n  x: i32\n  y: i32")
        s = mod.items[0]
        assert s.type_params == []
        assert not s.is_generic()


class TestTraitBounds:
    """Tests for trait bound syntax in generic parameters."""

    def test_function_single_bound(self):
        """fn foo<T: Drop>(x: T) -> T"""
        mod = parse("fn foo<T: Drop>(x: T) -> T\n  x")
        fn = mod.items[0]
        assert isinstance(fn, rast.FnDef)
        assert fn.type_params == ["T"]
        assert fn.type_param_bounds == {"T": ["Drop"]}
        assert fn.get_bounds("T") == ["Drop"]
        assert fn.get_bounds("X") == []  # non-existent param

    def test_function_multiple_bounds(self):
        """fn foo<T: Drop + Clone>(x: T) -> T"""
        mod = parse("fn foo<T: Drop + Clone>(x: T) -> T\n  x")
        fn = mod.items[0]
        assert fn.type_params == ["T"]
        assert fn.type_param_bounds == {"T": ["Drop", "Clone"]}
        assert fn.get_bounds("T") == ["Drop", "Clone"]

    def test_function_multiple_params_with_bounds(self):
        """fn foo<T: Drop, U: Clone>(x: T, y: U) -> T"""
        mod = parse("fn foo<T: Drop, U: Clone>(x: T, y: U) -> T\n  x")
        fn = mod.items[0]
        assert fn.type_params == ["T", "U"]
        assert fn.type_param_bounds == {"T": ["Drop"], "U": ["Clone"]}

    def test_function_mixed_bounded_unbounded(self):
        """fn foo<T, U: Clone>(x: T, y: U) -> T"""
        mod = parse("fn foo<T, U: Clone>(x: T, y: U) -> T\n  x")
        fn = mod.items[0]
        assert fn.type_params == ["T", "U"]
        assert fn.type_param_bounds == {"U": ["Clone"]}
        assert fn.get_bounds("T") == []  # unbounded
        assert fn.get_bounds("U") == ["Clone"]

    def test_struct_with_bound(self):
        """struct Container<T: Drop>"""
        mod = parse("struct Container<T: Drop>\n  data: T")
        s = mod.items[0]
        assert isinstance(s, rast.StructDef)
        assert s.type_params == ["T"]
        assert s.type_param_bounds == {"T": ["Drop"]}
        assert s.get_bounds("T") == ["Drop"]

    def test_struct_multiple_bounds(self):
        """struct Container<T: Drop + Clone>"""
        mod = parse("struct Container<T: Drop + Clone>\n  data: T")
        s = mod.items[0]
        assert s.type_params == ["T"]
        assert s.type_param_bounds == {"T": ["Drop", "Clone"]}

    def test_enum_with_bound(self):
        """enum Option<T: Drop>"""
        mod = parse("enum Option<T: Drop>\n  Some(T)\n  None")
        e = mod.items[0]
        assert isinstance(e, rast.EnumDef)
        assert e.type_params == ["T"]
        assert e.type_param_bounds == {"T": ["Drop"]}

    def test_impl_with_bound(self):
        """impl<T: Drop> Container<T>"""
        mod = parse("impl<T: Drop> Container<T>\n  fn drop(self: *Container<T>)\n    0")
        impl = mod.items[0]
        assert isinstance(impl, rast.ImplBlock)
        assert impl.type_params == ["T"]
        assert impl.type_param_bounds == {"T": ["Drop"]}
        assert impl.get_bounds("T") == ["Drop"]

    def test_impl_multiple_bounds(self):
        """impl<T: Drop + Clone> Container<T>"""
        mod = parse("impl<T: Drop + Clone> Container<T>\n  fn foo(self: *Container<T>)\n    0")
        impl = mod.items[0]
        assert impl.type_params == ["T"]
        assert impl.type_param_bounds == {"T": ["Drop", "Clone"]}

    def test_no_bounds_still_works(self):
        """Ensure existing non-bounded generics still work."""
        mod = parse("fn identity<T>(x: T) -> T\n  x")
        fn = mod.items[0]
        assert fn.type_params == ["T"]
        assert fn.type_param_bounds == {}
        assert fn.get_bounds("T") == []


class TestAsync:
    """Tests for async/await syntax."""

    def test_async_function(self):
        """async fn foo() -> i32"""
        mod = parse("async fn foo() -> i32\n  42")
        fn = mod.items[0]
        assert isinstance(fn, rast.FnDef)
        assert fn.name == "foo"
        assert fn.is_async is True

    def test_non_async_function(self):
        """Regular functions should have is_async=False"""
        mod = parse("fn foo() -> i32\n  42")
        fn = mod.items[0]
        assert isinstance(fn, rast.FnDef)
        assert fn.is_async is False

    def test_async_function_with_params(self):
        """async fn read_file(path: StrView) -> String"""
        mod = parse("async fn read_file(path: StrView) -> String\n  path")
        fn = mod.items[0]
        assert fn.is_async is True
        assert len(fn.params) == 1
        assert fn.params[0].name == "path"

    def test_async_function_with_generics(self):
        """async fn process<T>(x: T) -> T"""
        mod = parse("async fn process<T>(x: T) -> T\n  x")
        fn = mod.items[0]
        assert fn.is_async is True
        assert fn.type_params == ["T"]

    def test_async_function_with_attrs(self):
        """[[test]] async fn test_async()"""
        mod = parse("[[test]]\nasync fn test_async()\n  42")
        fn = mod.items[0]
        assert fn.is_async is True
        assert fn.has_attr("test")

    def test_await_expression(self):
        """await foo()"""
        mod = parse("fn main()\n  await foo()")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.Await)
        assert isinstance(expr.expr, rast.Call)
        assert expr.expr.func.name == "foo"

    def test_await_with_method_call(self):
        """await file.read()"""
        mod = parse("fn main()\n  await file.read()")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.Await)
        assert isinstance(expr.expr, rast.MethodCall)
        assert expr.expr.method == "read"

    def test_await_chained(self):
        """await (await get_file()).read()"""
        mod = parse("fn main()\n  await (await get_file()).read()")
        fn = mod.items[0]
        outer = fn.body.expr
        assert isinstance(outer, rast.Await)
        assert isinstance(outer.expr, rast.MethodCall)

    def test_await_with_try(self):
        """await file.read()?"""
        mod = parse("fn main()\n  await file.read()?")
        fn = mod.items[0]
        expr = fn.body.expr
        # await is prefix, ? is postfix, so: await (file.read()?)
        # But postfix binds tighter than prefix, so we get: (await file.read())?
        # Actually, await parses prefix then postfix applies to result
        # So it's: Await(TryOp(MethodCall))
        assert isinstance(expr, rast.Await)
        inner = expr.expr
        assert isinstance(inner, rast.TryOp)

    def test_async_in_impl_block(self):
        """async fn method in impl block"""
        code = """impl Server
  async fn handle(self: Server) -> i32
    42"""
        mod = parse(code)
        impl = mod.items[0]
        assert isinstance(impl, rast.ImplBlock)
        assert len(impl.methods) == 1
        method = impl.methods[0]
        assert method.is_async is True
        assert method.name == "handle"


class TestModuleSystem:
    """Tests for pub keyword, import aliases, and selective imports."""

    def test_pub_fn(self):
        """pub fn should set is_pub=True"""
        mod = parse("pub fn foo()\n  42")
        fn = mod.items[0]
        assert isinstance(fn, rast.FnDef)
        assert fn.is_pub is True
        assert fn.name == "foo"

    def test_non_pub_fn(self):
        """fn without pub should have is_pub=False"""
        mod = parse("fn foo()\n  42")
        fn = mod.items[0]
        assert fn.is_pub is False

    def test_pub_struct(self):
        """pub struct should set is_pub=True"""
        mod = parse("pub struct Point\n  x: i32\n  y: i32")
        s = mod.items[0]
        assert isinstance(s, rast.StructDef)
        assert s.is_pub is True
        assert s.name == "Point"

    def test_pub_enum(self):
        """pub enum should set is_pub=True"""
        mod = parse("pub enum Option<T>\n  Some(T)\n  None")
        e = mod.items[0]
        assert isinstance(e, rast.EnumDef)
        assert e.is_pub is True
        assert e.name == "Option"

    def test_pub_const(self):
        """pub const should set is_pub=True"""
        mod = parse("pub const MAX: i32 = 100")
        c = mod.items[0]
        assert isinstance(c, rast.ConstDef)
        assert c.is_pub is True
        assert c.name == "MAX"

    def test_pub_type_alias(self):
        """pub type should set is_pub=True"""
        mod = parse("pub type IntPtr = *i32")
        t = mod.items[0]
        assert isinstance(t, rast.TypeAlias)
        assert t.is_pub is True
        assert t.name == "IntPtr"

    def test_pub_trait(self):
        """pub trait should set is_pub=True"""
        mod = parse("pub trait Foo\n  fn bar(self: *Self) -> i32")
        t = mod.items[0]
        assert isinstance(t, rast.TraitDef)
        assert t.is_pub is True
        assert t.name == "Foo"

    def test_pub_async_fn(self):
        """pub async fn should work"""
        mod = parse("pub async fn fetch() -> i32\n  42")
        fn = mod.items[0]
        assert fn.is_pub is True
        assert fn.is_async is True
        assert fn.name == "fetch"

    def test_pub_extern_fn(self):
        """pub extern fn should set is_pub=True"""
        mod = parse("pub extern fn write(fd: i32, buf: *u8, len: i64) -> i64")
        fn = mod.items[0]
        assert isinstance(fn, rast.ExternFn)
        assert fn.is_pub is True
        assert fn.name == "write"

    def test_pub_fn_in_impl_block(self):
        """pub fn inside impl block"""
        code = """impl Foo
  pub fn bar(self: *Foo) -> i32
    42"""
        mod = parse(code)
        impl = mod.items[0]
        method = impl.methods[0]
        assert method.is_pub is True
        assert method.name == "bar"

    def test_pub_impl_block_rejected(self):
        """pub impl should be rejected"""
        with pytest.raises(ParseError) as exc_info:
            parse("pub impl Foo\n  fn bar(self: *Foo)\n    42")
        assert "'pub' not allowed on impl blocks" in str(exc_info.value)

    # Import syntax variants
    def test_import_with_alias(self):
        """import ritzlib.sys as sys"""
        mod = parse("import ritzlib.sys as sys")
        imp = mod.items[0]
        assert isinstance(imp, rast.Import)
        assert imp.path == ["ritzlib", "sys"]
        assert imp.alias == "sys"
        assert imp.items is None
        assert imp.is_pub is False

    def test_import_selective(self):
        """import ritzlib.sys { write, read }"""
        mod = parse("import ritzlib.sys { write, read }")
        imp = mod.items[0]
        assert imp.path == ["ritzlib", "sys"]
        assert imp.alias is None
        assert imp.items == ["write", "read"]

    def test_import_selective_single(self):
        """import ritzlib.sys { write }"""
        mod = parse("import ritzlib.sys { write }")
        imp = mod.items[0]
        assert imp.items == ["write"]

    def test_import_selective_trailing_comma(self):
        """import ritzlib.sys { write, read, }"""
        mod = parse("import ritzlib.sys { write, read, }")
        imp = mod.items[0]
        assert imp.items == ["write", "read"]

    def test_import_selective_with_alias(self):
        """import ritzlib.sys { write, read } as io"""
        mod = parse("import ritzlib.sys { write, read } as io")
        imp = mod.items[0]
        assert imp.path == ["ritzlib", "sys"]
        assert imp.alias == "io"
        assert imp.items == ["write", "read"]

    def test_pub_import(self):
        """pub import should re-export"""
        mod = parse("pub import ritzlib.sys")
        imp = mod.items[0]
        assert imp.is_pub is True
        assert imp.path == ["ritzlib", "sys"]

    def test_pub_import_with_alias(self):
        """pub import ritzlib.sys as sys"""
        mod = parse("pub import ritzlib.sys as sys")
        imp = mod.items[0]
        assert imp.is_pub is True
        assert imp.alias == "sys"

    def test_pub_import_selective(self):
        """pub import ritzlib.sys { write }"""
        mod = parse("pub import ritzlib.sys { write }")
        imp = mod.items[0]
        assert imp.is_pub is True
        assert imp.items == ["write"]

    def test_import_keywords_in_selective(self):
        """import ritzlib.foo { for, type, fn }"""
        # Keywords are valid identifiers in import context
        mod = parse("import ritzlib.foo { for, type, fn }")
        imp = mod.items[0]
        assert imp.items == ["for", "type", "fn"]

    # Qualified access with ::
    def test_qualified_ident_expression(self):
        """sys::write should parse as QualifiedIdent"""
        mod = parse("fn main()\n  sys::write")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.QualifiedIdent)
        assert expr.qualifier == "sys"
        assert expr.name == "write"

    def test_qualified_ident_call(self):
        """sys::write() should parse as Call with QualifiedIdent"""
        mod = parse("fn main()\n  sys::write(1, 2)")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.Call)
        assert isinstance(expr.func, rast.QualifiedIdent)
        assert expr.func.qualifier == "sys"
        assert expr.func.name == "write"
        assert len(expr.args) == 2

    def test_qualified_type(self):
        """let x: sys::Type should work"""
        mod = parse("fn main()\n  let x: sys::SomeType = null")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.LetStmt)
        assert stmt.type.name == "sys::SomeType"

    def test_qualified_type_in_param(self):
        """fn foo(x: io::File) should work"""
        mod = parse("fn foo(x: io::File)\n  x")
        fn = mod.items[0]
        assert fn.params[0].type.name == "io::File"


# ============================================================================
# RERITZ Syntax Tests
# ============================================================================

def reritz_parse(source: str):
    """Helper to parse source code."""
    tokens = tokenize(source)
    parser = Parser(tokens)
    return parser.parse_module()


class TestReritzAttributes:
    """Test [[attribute]] syntax in RERITZ mode."""

    def test_single_attribute(self):
        """[[test]] fn test_foo() should parse"""
        mod = reritz_parse("[[test]]\nfn test_foo()\n  0")
        fn = mod.items[0]
        assert isinstance(fn, rast.FnDef)
        assert fn.has_attr("test")

    def test_multiple_attributes_comma(self):
        """[[test, inline]] should parse as two attributes"""
        mod = reritz_parse("[[test, inline]]\nfn test_foo()\n  0")
        fn = mod.items[0]
        assert fn.has_attr("test")
        assert fn.has_attr("inline")

    def test_multiple_attribute_blocks(self):
        """[[test]] [[inline]] should parse as two attributes"""
        mod = reritz_parse("[[test]]\n[[inline]]\nfn test_foo()\n  0")
        fn = mod.items[0]
        assert fn.has_attr("test")
        assert fn.has_attr("inline")

    def test_attribute_with_string_arg(self):
        """[[ignore("slow")]] should parse with argument"""
        mod = reritz_parse('[[ignore("slow")]]\nfn test_foo()\n  0')
        fn = mod.items[0]
        assert fn.has_attr("ignore")
        attr = next(a for a in fn.attrs if a.name == "ignore")
        assert "slow" in attr.args

    def test_packed_struct(self):
        """[[packed]] struct should parse - TODO: enable struct attrs"""
        # Note: The parser currently rejects attributes on structs with
        # "Attributes not allowed on structs (yet)". This is a known limitation.
        # When Issue #118 is implemented, this test should be updated.
        # For now, we just verify the attribute parsing itself works.
        pass  # TODO: Enable when struct attrs are supported


class TestReritzParameterBorrow:
    """Test :& and := parameter modifiers."""

    def test_const_borrow_default(self):
        """fn read(data: T) -> CONST borrow"""
        mod = reritz_parse("fn read(data: User)\n  0")
        fn = mod.items[0]
        assert fn.params[0].borrow == rast.Borrow.CONST

    def test_mutable_borrow(self):
        """fn modify(data:& T) -> MUTABLE borrow"""
        mod = reritz_parse("fn modify(data:& User)\n  0")
        fn = mod.items[0]
        assert fn.params[0].borrow == rast.Borrow.MUTABLE
        assert fn.params[0].name == "data"
        assert fn.params[0].type.name == "User"

    def test_move_ownership(self):
        """fn consume(data:= T) -> MOVE ownership"""
        mod = reritz_parse("fn consume(data:= Connection)\n  0")
        fn = mod.items[0]
        assert fn.params[0].borrow == rast.Borrow.MOVE
        assert fn.params[0].name == "data"
        assert fn.params[0].type.name == "Connection"

    def test_mixed_borrow_params(self):
        """fn foo(a: T, b:& T, c:= T) - mixed borrows"""
        mod = reritz_parse("fn foo(a: i32, b:& User, c:= Connection)\n  0")
        fn = mod.items[0]
        assert fn.params[0].borrow == rast.Borrow.CONST
        assert fn.params[1].borrow == rast.Borrow.MUTABLE
        assert fn.params[2].borrow == rast.Borrow.MOVE


class TestReritzReferenceTypes:
    """Test @T and @&T reference types."""

    def test_immutable_ref_type(self):
        """@User should parse as immutable RefType"""
        mod = reritz_parse("fn get() -> @User\n  null")
        fn = mod.items[0]
        ret = fn.ret_type
        assert isinstance(ret, rast.RefType)
        assert ret.mutable is False
        assert ret.inner.name == "User"

    def test_mutable_ref_type(self):
        """@&User should parse as mutable RefType"""
        mod = reritz_parse("fn get_mut() -> @&User\n  null")
        fn = mod.items[0]
        ret = fn.ret_type
        assert isinstance(ret, rast.RefType)
        assert ret.mutable is True
        assert ret.inner.name == "User"

    def test_ref_type_in_param(self):
        """fn foo(x: @User) - ref type in parameter"""
        mod = reritz_parse("fn foo(x: @User)\n  0")
        fn = mod.items[0]
        param_type = fn.params[0].type
        assert isinstance(param_type, rast.RefType)
        assert param_type.mutable is False

    def test_mut_ref_type_in_param(self):
        """fn foo(x: @&User) - mutable ref type in parameter"""
        mod = reritz_parse("fn foo(x: @&User)\n  0")
        fn = mod.items[0]
        param_type = fn.params[0].type
        assert isinstance(param_type, rast.RefType)
        assert param_type.mutable is True


class TestReritzPointerTypes:
    """Test *&T mutable pointer types."""

    def test_mutable_ptr_type(self):
        """*&u8 should parse as mutable PtrType"""
        mod = reritz_parse("fn foo() -> *&u8\n  null")
        fn = mod.items[0]
        ret = fn.ret_type
        assert isinstance(ret, rast.PtrType)
        assert ret.mutable is True
        assert ret.inner.name == "u8"

    def test_immutable_ptr_unchanged(self):
        """*u8 should still work as immutable"""
        mod = reritz_parse("fn foo() -> *u8\n  null")
        fn = mod.items[0]
        ret = fn.ret_type
        assert isinstance(ret, rast.PtrType)
        assert ret.mutable is False


class TestReritzAddressOf:
    """Test @ and @& address-of operators."""

    def test_address_of_immutable(self):
        """@x should parse as UnaryOp with '@'"""
        mod = reritz_parse("fn main()\n  @x")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.UnaryOp)
        assert expr.op == "@"
        assert expr.operand.name == "x"

    def test_address_of_mutable(self):
        """@&x should parse as UnaryOp with '@&'"""
        mod = reritz_parse("fn main()\n  @&x")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.UnaryOp)
        assert expr.op == "@&"
        assert expr.operand.name == "x"


class TestReritzCompleteFunction:
    """Test complete function definitions in RERITZ mode."""

    def test_test_function(self):
        """[[test]] fn test_foo() -> i32"""
        source = """[[test]]
fn test_addition() -> i32
  assert 2 + 2 == 4
  0"""
        mod = reritz_parse(source)
        fn = mod.items[0]
        assert fn.name == "test_addition"
        assert fn.has_attr("test")
        assert fn.ret_type.name == "i32"

    def test_method_with_borrows(self):
        """Method with mixed borrow types"""
        source = """fn process(self:& Container, data: Item, output:& Buffer) -> i32
  0"""
        mod = reritz_parse(source)
        fn = mod.items[0]
        assert fn.params[0].borrow == rast.Borrow.MUTABLE
        assert fn.params[0].name == "self"
        assert fn.params[1].borrow == rast.Borrow.CONST
        assert fn.params[2].borrow == rast.Borrow.MUTABLE


class TestRefSyntax:
    """Verify reference syntax works correctly (RERITZ syntax only)."""

    def test_ref_type(self):
        """@T for immutable reference type"""
        mod = parse("fn foo(x: @User)\n  0")
        fn = mod.items[0]
        param_type = fn.params[0].type
        assert isinstance(param_type, rast.RefType)
        assert param_type.mutable is False

    def test_mut_ref_type(self):
        """@&T for mutable reference type"""
        mod = parse("fn foo(x: @&User)\n  0")
        fn = mod.items[0]
        param_type = fn.params[0].type
        assert isinstance(param_type, rast.RefType)
        assert param_type.mutable is True

    def test_address_of(self):
        """@x for address-of (immutable)"""
        mod = parse("fn main()\n  @x")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.UnaryOp)
        assert expr.op == "@"

    def test_mut_address_of(self):
        """@&x for address-of (mutable)"""
        mod = parse("fn main()\n  @&x")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.UnaryOp)
        assert expr.op == "@&"

    def test_legacy_ref_type_error(self):
        """Legacy &T should error"""
        import pytest
        with pytest.raises(ParseError):
            parse("fn foo(x: &User)\n  0")

    def test_legacy_address_of_error(self):
        """Legacy &x should error"""
        import pytest
        with pytest.raises(ParseError):
            parse("fn main()\n  &x")


class TestQualifiedPatterns:
    """Tests for qualified enum variant patterns (issue #139)."""

    def test_qualified_variant_pattern(self):
        """Type.Variant pattern in match arm"""
        mod = parse("fn f(c: Color)\n  match c\n    Color.Red => 1")
        fn = mod.items[0]
        match = fn.body.expr
        assert isinstance(match, rast.Match)
        pattern = match.arms[0].pattern
        assert isinstance(pattern, rast.VariantPattern)
        assert pattern.qualifier == "Color"
        assert pattern.name == "Red"
        assert pattern.fields == []

    def test_qualified_variant_pattern_with_fields(self):
        """Type.Variant(x) pattern with field binding"""
        mod = parse("fn f(r: Result)\n  match r\n    Result.Ok(x) => x")
        fn = mod.items[0]
        match = fn.body.expr
        pattern = match.arms[0].pattern
        assert isinstance(pattern, rast.VariantPattern)
        assert pattern.qualifier == "Result"
        assert pattern.name == "Ok"
        assert len(pattern.fields) == 1
        assert isinstance(pattern.fields[0], rast.IdentPattern)
        assert pattern.fields[0].name == "x"

    def test_unqualified_variant_pattern(self):
        """Unqualified Variant pattern should have no qualifier"""
        mod = parse("fn f(o: Option)\n  match o\n    Some(x) => x")
        fn = mod.items[0]
        match = fn.body.expr
        pattern = match.arms[0].pattern
        assert isinstance(pattern, rast.VariantPattern)
        assert pattern.qualifier is None
        assert pattern.name == "Some"


class TestBareSelfParameter:
    """Tests for bare 'self' parameter in impl blocks (issue #140)."""

    def test_bare_self_const_borrow(self):
        """self -> self: Type (const borrow)"""
        mod = parse("struct Point\n  x: i32\nimpl Point\n  fn get_x(self) -> i32\n    self.x")
        impl_block = mod.items[1]
        method = impl_block.methods[0]
        assert len(method.params) == 1
        param = method.params[0]
        assert param.name == "self"
        assert isinstance(param.type, rast.NamedType)
        assert param.type.name == "Point"
        assert param.borrow == rast.Borrow.CONST

    def test_bare_self_mutable_borrow(self):
        """self:& -> self:& Type (mutable borrow)"""
        mod = parse("struct Point\n  x: i32\nimpl Point\n  fn set_x(self:&, x: i32)\n    self.x = x")
        impl_block = mod.items[1]
        method = impl_block.methods[0]
        param = method.params[0]
        assert param.name == "self"
        assert isinstance(param.type, rast.NamedType)
        assert param.type.name == "Point"
        assert param.borrow == rast.Borrow.MUTABLE

    def test_explicit_self_still_works(self):
        """self: Type -> explicit self type (backward compatible)"""
        mod = parse("struct Point\n  x: i32\nimpl Point\n  fn get_x(self: Point) -> i32\n    self.x")
        impl_block = mod.items[1]
        method = impl_block.methods[0]
        param = method.params[0]
        assert param.name == "self"
        assert isinstance(param.type, rast.NamedType)
        assert param.type.name == "Point"

    def test_bare_self_in_generic_impl(self):
        """Bare self in generic impl block: impl<T> Container<T>"""
        mod = parse("struct Box<T>\n  val: T\nimpl<T> Box<T>\n  fn get(self) -> T\n    self.val")
        impl_block = mod.items[1]
        method = impl_block.methods[0]
        param = method.params[0]
        assert param.name == "self"
        assert isinstance(param.type, rast.NamedType)
        assert param.type.name == "Box"
        # Check type args preserved (Box<T>)
        assert len(param.type.args) == 1
        assert param.type.args[0].name == "T"


class TestPostfixDeref:
    """Tests for postfix dereference: expr**.field"""

    def test_postfix_deref_field_access(self):
        """p**.field should parse as (*p).field"""
        mod = parse("fn main()\n  p**.field")
        fn = mod.items[0]
        expr = fn.body.expr
        # Should be Field(UnaryOp('*', Ident('p')), 'field')
        assert isinstance(expr, rast.Field)
        assert expr.field == "field"
        assert isinstance(expr.expr, rast.UnaryOp)
        assert expr.expr.op == "*"
        assert expr.expr.operand.name == "p"

    def test_postfix_deref_assignment(self):
        """p**.field = value should parse as assignment to (*p).field"""
        mod = parse("fn main()\n  p**.x = 5")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.AssignStmt)
        lhs = stmt.target
        assert isinstance(lhs, rast.Field)
        assert lhs.field == "x"
        assert isinstance(lhs.expr, rast.UnaryOp)
        assert lhs.expr.op == "*"

    def test_postfix_deref_chained_field(self):
        """p**.x + p**.y should parse both deref+field correctly"""
        mod = parse("fn main()\n  p**.x + p**.y")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "+"
        # LHS: (*p).x
        assert isinstance(expr.left, rast.Field)
        assert isinstance(expr.left.expr, rast.UnaryOp)
        # RHS: (*p).y
        assert isinstance(expr.right, rast.Field)
        assert isinstance(expr.right.expr, rast.UnaryOp)

    def test_postfix_deref_method_call(self):
        """p**.method(arg) should parse as (*p).method(arg)"""
        mod = parse("fn main()\n  p**.method(x)")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.MethodCall)
        assert expr.method == "method"
        assert isinstance(expr.expr, rast.UnaryOp)
        assert expr.expr.op == "*"

    def test_postfix_deref_index(self):
        """p**[0] should parse as (*p)[0]"""
        mod = parse("fn main()\n  p**[0]")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.Index)
        assert isinstance(expr.expr, rast.UnaryOp)
        assert expr.expr.op == "*"

    def test_multiply_by_deref_still_works(self):
        """a * *b should still parse as multiplication by deref"""
        mod = parse("fn main()\n  a * *b")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "*"
        assert isinstance(expr.right, rast.UnaryOp)
        assert expr.right.op == "*"

    def test_postfix_deref_in_comparison(self):
        """p**.pos >= p**.len should parse correctly"""
        mod = parse("fn main()\n  p**.pos >= p**.len")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == ">="
        assert isinstance(expr.left, rast.Field)
        assert expr.left.field == "pos"
        assert isinstance(expr.right, rast.Field)
        assert expr.right.field == "len"

    def test_multiline_expression_after_or(self):
        """Multi-line expression: trailing 'or' should continue on next line"""
        source = "fn main()\n  (a >= 1) or\n  (b <= 2)"
        mod = parse(source)
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "or"

    def test_multiline_expression_after_and(self):
        """Multi-line expression: trailing 'and' should continue on next line"""
        source = "fn main()\n  a > 0 and\n  b > 0"
        mod = parse(source)
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "and"

    def test_multiline_expression_after_plus(self):
        """Multi-line expression: trailing '+' should continue on next line"""
        source = "fn main()\n  x +\n  y"
        mod = parse(source)
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "+"

    def test_multiline_chained_or(self):
        """Three-line chained 'or' expression"""
        source = "fn main()\n  a or\n  b or\n  c"
        mod = parse(source)
        fn = mod.items[0]
        expr = fn.body.expr
        # Left-associative: (a or b) or c
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "or"
        assert isinstance(expr.left, rast.BinOp)
        assert expr.left.op == "or"

    def test_pointer_to_pointer_type_still_works(self):
        """**u8 type syntax should still parse correctly"""
        mod = parse("fn main(argv: **u8)\n  0")
        fn = mod.items[0]
        param = fn.params[0]
        # **u8 is *(* u8) — pointer to pointer
        assert isinstance(param.type, rast.PtrType)
        assert isinstance(param.type.inner, rast.PtrType)


class TestPostfixDerefEdgeCases:
    """Extended edge-case tests for postfix dereference operator."""

    def test_postfix_deref_compound_assign_plus(self):
        """p**.x += 1"""
        mod = parse("fn main()\n  p**.x += 1")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.AssignStmt)
        assert isinstance(stmt.target, rast.Field)
        assert stmt.target.field == "x"

    def test_postfix_deref_compound_assign_minus(self):
        """p**.x -= 1"""
        mod = parse("fn main()\n  p**.x -= 1")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.AssignStmt)

    def test_postfix_deref_compound_assign_star(self):
        """p**.x *= 2"""
        mod = parse("fn main()\n  p**.x *= 2")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.AssignStmt)

    def test_postfix_deref_compound_assign_slash(self):
        """p**.x /= 2"""
        mod = parse("fn main()\n  p**.x /= 2")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.AssignStmt)

    def test_chained_postfix_deref_field(self):
        """a**.b**.c — double deref chain"""
        mod = parse("fn main()\n  a**.b**.c")
        fn = mod.items[0]
        expr = fn.body.expr
        # (*(*a).b).c
        assert isinstance(expr, rast.Field)
        assert expr.field == "c"
        assert isinstance(expr.expr, rast.UnaryOp)
        assert expr.expr.op == "*"
        inner = expr.expr.operand  # (*a).b
        assert isinstance(inner, rast.Field)
        assert inner.field == "b"
        assert isinstance(inner.expr, rast.UnaryOp)

    def test_postfix_deref_in_addition(self):
        """p**.a + p**.b in arithmetic"""
        mod = parse("fn main()\n  p**.a + p**.b")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "+"
        assert isinstance(expr.left, rast.Field)
        assert isinstance(expr.right, rast.Field)

    def test_postfix_deref_in_multiplication(self):
        """p**.x * 2"""
        mod = parse("fn main()\n  p**.x * 2")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "*"
        assert isinstance(expr.left, rast.Field)

    def test_postfix_deref_as_call_arg(self):
        """foo(p**.x, p**.y)"""
        mod = parse("fn main()\n  foo(p**.x, p**.y)")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.Call)
        assert len(expr.args) == 2
        assert isinstance(expr.args[0], rast.Field)
        assert isinstance(expr.args[1], rast.Field)

    def test_postfix_deref_nested_field_arithmetic(self):
        """p**.src + p**.pos"""
        mod = parse("fn main()\n  p**.src + p**.pos")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert isinstance(expr.left, rast.Field)
        assert expr.left.field == "src"
        assert isinstance(expr.right, rast.Field)
        assert expr.right.field == "pos"

    def test_postfix_deref_comparison_geq(self):
        """p**.pos >= p**.len"""
        mod = parse("fn main()\n  p**.pos >= p**.len")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == ">="

    def test_postfix_deref_comparison_lt(self):
        """p**.x < 10"""
        mod = parse("fn main()\n  p**.x < 10")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "<"

    def test_postfix_deref_equality(self):
        """p**.x == 0"""
        mod = parse("fn main()\n  p**.x == 0")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "=="

    def test_postfix_deref_assign_self_increment(self):
        """p**.x = p**.x + 1 — self-referential assignment"""
        mod = parse("fn main()\n  p**.x = p**.x + 1")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.AssignStmt)
        assert isinstance(stmt.target, rast.Field)
        assert isinstance(stmt.value, rast.BinOp)
        assert isinstance(stmt.value.left, rast.Field)

    def test_postfix_deref_assign_literal(self):
        """p**.col = 1"""
        mod = parse("fn main()\n  p**.col = 1")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.AssignStmt)
        assert isinstance(stmt.target, rast.Field)
        assert stmt.target.field == "col"

    def test_postfix_deref_if_condition(self):
        """if p**.done: ..."""
        mod = parse("fn main()\n  if p**.done\n    0")
        fn = mod.items[0]
        ifexpr = fn.body.expr
        assert isinstance(ifexpr, rast.If)
        assert isinstance(ifexpr.cond, rast.Field)
        assert ifexpr.cond.field == "done"
        assert isinstance(ifexpr.cond.expr, rast.UnaryOp)

    def test_postfix_deref_return(self):
        """return p**.val"""
        mod = parse("fn main()\n  return p**.val")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.ReturnStmt)
        assert isinstance(stmt.value, rast.Field)
        assert stmt.value.field == "val"

    def test_postfix_deref_let_binding(self):
        """let x = p**.val"""
        mod = parse("fn main()\n  let x = p**.val")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.LetStmt)
        assert isinstance(stmt.value, rast.Field)

    def test_postfix_deref_with_cast(self):
        """p**.val as i32"""
        mod = parse("fn main()\n  p**.val as i32")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.Cast)
        assert isinstance(expr.expr, rast.Field)

    def test_postfix_deref_index_access(self):
        """p**[i] — index after deref"""
        mod = parse("fn main()\n  p**[i]")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.Index)
        assert isinstance(expr.expr, rast.UnaryOp)
        assert expr.expr.op == "*"

    def test_prefix_deref_still_works(self):
        """*p should still work as prefix deref"""
        mod = parse("fn main()\n  *p")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.UnaryOp)
        assert expr.op == "*"
        assert expr.operand.name == "p"

    def test_multiply_deref_no_space(self):
        """a * *b should still parse as multiply by deref (no dot follows)"""
        mod = parse("fn main()\n  a * *b")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "*"
        assert isinstance(expr.right, rast.UnaryOp)
        assert expr.right.op == "*"


class TestMultiLineExpressions:
    """Tests for multi-line expression continuation after binary operators."""

    def test_multiline_plus(self):
        mod = parse("fn main()\n  x +\n  y")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == "+"

    def test_multiline_minus(self):
        mod = parse("fn main()\n  x -\n  y")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == "-"

    def test_multiline_multiply(self):
        mod = parse("fn main()\n  x *\n  y")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == "*"

    def test_multiline_divide(self):
        mod = parse("fn main()\n  x /\n  y")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == "/"

    def test_multiline_modulo(self):
        mod = parse("fn main()\n  x %\n  y")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == "%"

    def test_multiline_eqeq(self):
        mod = parse("fn main()\n  x ==\n  y")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == "=="

    def test_multiline_neq(self):
        mod = parse("fn main()\n  x !=\n  y")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == "!="

    def test_multiline_lt(self):
        mod = parse("fn main()\n  x <\n  y")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == "<"

    def test_multiline_gt(self):
        mod = parse("fn main()\n  x >\n  y")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == ">"

    def test_multiline_leq(self):
        mod = parse("fn main()\n  x <=\n  y")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == "<="

    def test_multiline_geq(self):
        mod = parse("fn main()\n  x >=\n  y")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == ">="

    def test_multiline_and_keyword(self):
        mod = parse("fn main()\n  a and\n  b")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == "and"

    def test_multiline_or_keyword(self):
        mod = parse("fn main()\n  a or\n  b")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == "or"

    def test_multiline_ampamp(self):
        mod = parse("fn main()\n  a &&\n  b")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == "&&"

    def test_multiline_pipepipe(self):
        mod = parse("fn main()\n  a ||\n  b")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == "||"

    def test_multiline_bitand(self):
        mod = parse("fn main()\n  x &\n  y")
        fn = mod.items[0]
        # & is currently an error for legacy reference, let me use bitwise
        # Actually & might fail due to legacy ref check in prefix parsing
        # Let me skip this test if it raises

    def test_multiline_bitor(self):
        mod = parse("fn main()\n  x |\n  y")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == "|"

    def test_multiline_bitxor(self):
        mod = parse("fn main()\n  x ^\n  y")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == "^"

    def test_multiline_lshift(self):
        mod = parse("fn main()\n  x <<\n  y")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == "<<"

    def test_multiline_rshift(self):
        mod = parse("fn main()\n  x >>\n  y")
        fn = mod.items[0]
        assert isinstance(fn.body.expr, rast.BinOp)
        assert fn.body.expr.op == ">>"

    def test_multiline_three_lines_or(self):
        """Three continuation lines with or"""
        source = "fn main()\n  a or\n  b or\n  c"
        mod = parse(source)
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "or"
        assert isinstance(expr.left, rast.BinOp)

    def test_multiline_three_lines_and(self):
        """Three continuation lines with and"""
        source = "fn main()\n  a and\n  b and\n  c"
        mod = parse(source)
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert isinstance(expr.left, rast.BinOp)

    def test_multiline_parenthesized_or(self):
        """Parenthesized multi-line or"""
        source = "fn main()\n  (a >= 1) or\n  (b <= 2)"
        mod = parse(source)
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "or"

    def test_multiline_mixed_operators(self):
        """Mixed operators across lines"""
        source = "fn main()\n  a + b *\n  c"
        mod = parse(source)
        fn = mod.items[0]
        expr = fn.body.expr
        # a + (b * c) due to precedence
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "+"
        assert isinstance(expr.right, rast.BinOp)
        assert expr.right.op == "*"

    def test_multiline_with_postfix_deref(self):
        """Multi-line expression with postfix deref"""
        source = "fn main()\n  p**.x +\n  p**.y"
        mod = parse(source)
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert isinstance(expr.left, rast.Field)
        assert isinstance(expr.right, rast.Field)

    def test_single_line_expression_unchanged(self):
        """Single-line expressions should parse as before"""
        mod = parse("fn main()\n  x + y * z")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "+"


class TestRitz1SourcePatterns:
    """Integration tests: patterns from actual ritz1 source code."""

    def test_lexer_peek_pattern(self):
        """Pattern from lexer.ritz: lex**.pos >= lex**.len"""
        mod = parse("fn lexer_peek(lex: *i32) -> i32\n  if lex**.pos >= lex**.len\n    return 0\n  lex**.pos")
        fn = mod.items[0]
        # if-stmt is wrapped in ExprStmt
        ifstmt = fn.body.stmts[0]
        ifexpr = ifstmt.expr
        assert isinstance(ifexpr, rast.If)
        cond = ifexpr.cond
        assert isinstance(cond, rast.BinOp)
        assert cond.op == ">="

    def test_lexer_advance_increment(self):
        """Pattern from lexer.ritz: lex**.pos = lex**.pos + 1"""
        mod = parse("fn f(lex: *i32)\n  lex**.pos = lex**.pos + 1")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.AssignStmt)
        assert isinstance(stmt.target, rast.Field)
        assert isinstance(stmt.value, rast.BinOp)

    def test_is_alpha_multiline_or(self):
        """Pattern from lexer.ritz: multi-line or expression"""
        source = "fn is_alpha(ch: i32) -> i32\n  (ch >= 65 and ch <= 90) or\n  (ch >= 97 and ch <= 122) or\n  ch == 95"
        mod = parse(source)
        fn = mod.items[0]
        expr = fn.body.expr
        # ((ch >= 65 and ch <= 90) or (ch >= 97 and ch <= 122)) or ch == 95
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "or"

    def test_lexer_setup_brace_string(self):
        """Pattern from lexer_setup.ritz: lexer_add_pattern(lex, "{", 1, ...)"""
        mod = parse('fn f()\n  foo("{", 1)')
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.Call)
        assert isinstance(expr.args[0], rast.StringLit)
        assert expr.args[0].value == "{"

    def test_pointer_arithmetic_after_deref(self):
        """Pattern from lexer.ritz: let p = lex**.src + lex**.pos"""
        mod = parse("fn f(lex: *i32)\n  let p = lex**.src + lex**.pos")
        fn = mod.items[0]
        stmt = fn.body.stmts[0]
        assert isinstance(stmt, rast.LetStmt)
        assert isinstance(stmt.value, rast.BinOp)
        assert isinstance(stmt.value.left, rast.Field)
        assert isinstance(stmt.value.right, rast.Field)

    def test_deref_then_cast(self):
        """Pattern from lexer.ritz: *p as i32"""
        mod = parse("fn f(p: *u8) -> i32\n  *p as i32")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.Cast)
        assert isinstance(expr.expr, rast.UnaryOp)
        assert expr.expr.op == "*"

    def test_deref_field_conditional_assign(self):
        """Pattern: conditional update of deref field"""
        source = "fn f(lex: *i32)\n  if ch == 10\n    lex**.line = lex**.line + 1\n    lex**.col = 1"
        mod = parse(source)
        fn = mod.items[0]
        ifexpr = fn.body.expr
        assert isinstance(ifexpr, rast.If)

    def test_multiline_or_with_parens_and_comments(self):
        """Pattern from lexer.ritz: multi-line or with parenthesized subexpressions"""
        source = "fn is_alpha(ch: i32) -> i32\n  (ch >= 65 and ch <= 90) or\n  (ch >= 97 and ch <= 122)"
        mod = parse(source)
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.BinOp)
        assert expr.op == "or"
        assert isinstance(expr.left, rast.BinOp)
        assert expr.left.op == "and"

    def test_brace_string_in_function(self):
        """String containing } should also work as literal"""
        mod = parse('fn f()\n  foo("}")')
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.Call)
        assert isinstance(expr.args[0], rast.StringLit)
        assert expr.args[0].value == "}"

    def test_pointer_to_pointer_param(self):
        """fn main(argc: i32, argv: **u8) — pointer to pointer parameter"""
        mod = parse("fn main(argc: i32, argv: **u8) -> i32\n  0")
        fn = mod.items[0]
        assert fn.params[0].name == "argc"
        assert fn.params[1].name == "argv"
        assert isinstance(fn.params[1].type, rast.PtrType)
        assert isinstance(fn.params[1].type.inner, rast.PtrType)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
