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
        mod = parse("fn main()\n  &x")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.UnaryOp)
        assert expr.op == "&"

    def test_mutable_reference(self):
        mod = parse("fn main()\n  &mut x")
        fn = mod.items[0]
        expr = fn.body.expr
        assert isinstance(expr, rast.UnaryOp)
        assert expr.op == "&mut"


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
        mod = parse("fn foo(x: &i32)\n  x")
        fn = mod.items[0]
        t = fn.params[0].type
        assert isinstance(t, rast.RefType)
        assert not t.mutable
        assert t.inner.name == "i32"

    def test_mutable_reference_type(self):
        mod = parse("fn foo(x: &mut i32)\n  x")
        fn = mod.items[0]
        t = fn.params[0].type
        assert isinstance(t, rast.RefType)
        assert t.mutable

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
        mod = parse("@test\nfn test_add()\n  1 + 1")
        fn = mod.items[0]
        assert isinstance(fn, rast.FnDef)
        assert fn.name == "test_add"
        assert len(fn.attrs) == 1
        assert fn.attrs[0].name == "test"

    def test_multiple_attributes(self):
        mod = parse("@test\n@ignore\nfn test_foo()\n  42")
        fn = mod.items[0]
        assert isinstance(fn, rast.FnDef)
        assert fn.name == "test_foo"
        assert len(fn.attrs) == 2
        assert fn.attrs[0].name == "test"
        assert fn.attrs[1].name == "ignore"

    def test_function_with_attr_and_params(self):
        mod = parse("@test\nfn test_add(x: i32, y: i32) -> i32\n  x + y")
        fn = mod.items[0]
        assert isinstance(fn, rast.FnDef)
        assert fn.name == "test_add"
        assert len(fn.attrs) == 1
        assert fn.attrs[0].name == "test"
        assert len(fn.params) == 2
        assert fn.ret_type.name == "i32"

    def test_has_attr_method(self):
        mod = parse("@test\n@ignore\nfn test_bar()\n  0")
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
        """async fn read_file(path: &str) -> String"""
        mod = parse("async fn read_file(path: &str) -> String\n  path")
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
        """@test async fn test_async()"""
        mod = parse("@test\nasync fn test_async()\n  42")
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
  async fn handle(self: &Server) -> i32
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
