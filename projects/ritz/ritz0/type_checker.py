"""
Type Checker for ritz0

Semantic type checking pass that runs after parsing and before code generation.
Catches type errors early with helpful error messages.

Type inference rules:
- Literals: i64 for integers, bool for true/false, *u8 for strings, null for pointers
- Variables: declared type or inferred from initializer
- Binary ops: operands must be compatible, result type depends on operator
- Function calls: arguments must match parameter types
- Field access: expr must be struct type, field must exist
- Index access: expr must be array/pointer, index must be integer

Built-in functions:
- sizeof(T) -> i64: compile-time size of type
- print(str_lit) -> void: print string literal
- syscallN(...) -> i64: system call wrappers
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import ritz_ast as rast


class TypeError(Exception):
    """Type checking error with source location."""
    def __init__(self, message: str, span: Optional[rast.Span] = None):
        self.span = span
        if span:
            super().__init__(f"{span.file}:{span.line}:{span.column}: {message}")
        else:
            super().__init__(message)


@dataclass
class FnSig:
    """Function signature for type checking."""
    name: str
    params: List[Tuple[str, rast.Type]]  # (param_name, param_type)
    ret_type: Optional[rast.Type]
    type_params: List[str] = field(default_factory=list)


@dataclass
class StructInfo:
    """Struct definition for type checking."""
    name: str
    fields: List[Tuple[str, rast.Type]]  # (field_name, field_type)
    type_params: List[str] = field(default_factory=list)


@dataclass
class EnumInfo:
    """Enum definition for type checking."""
    name: str
    variants: List[rast.Variant]
    type_params: List[str] = field(default_factory=list)


class TypeChecker:
    """
    Semantic type checker for Ritz.

    Performs type inference and checking on AST nodes, catching errors like:
    - Type mismatches in binary operations (e.g., i32 + *u8)
    - Wrong number/types of function arguments
    - Accessing non-existent struct fields
    - Invalid return type
    """

    # Primitive integer types
    INT_TYPES = {'i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64'}
    SIGNED_INT_TYPES = {'i8', 'i16', 'i32', 'i64'}
    UNSIGNED_INT_TYPES = {'u8', 'u16', 'u32', 'u64'}

    # Numeric types (integers + floats)
    NUMERIC_TYPES = INT_TYPES | {'f32', 'f64'}

    def __init__(self):
        self.errors: List[TypeError] = []

        # Symbol tables
        self.functions: Dict[str, FnSig] = {}
        self.structs: Dict[str, StructInfo] = {}
        self.enums: Dict[str, EnumInfo] = {}
        self.type_aliases: Dict[str, rast.Type] = {}
        self.constants: Dict[str, rast.Type] = {}

        # Variant to enum mapping
        self.variant_to_enum: Dict[str, str] = {}

        # Trait implementations: trait_name -> set of type names that implement it
        self.trait_impls: Dict[str, Set[str]] = {}

        # Current context
        self.locals: Dict[str, rast.Type] = {}  # local variables
        self.current_fn: Optional[FnSig] = None
        self.scope_stack: List[Dict[str, rast.Type]] = []
        self.current_type_params: Set[str] = set()  # type parameters in scope (T, E, etc.)

    def check(self, module: rast.Module) -> List[TypeError]:
        """Type check a module. Returns list of errors."""
        self.errors = []

        # First pass: collect all type definitions
        for item in module.items:
            if isinstance(item, rast.StructDef):
                self._register_struct(item)
            elif isinstance(item, rast.EnumDef):
                self._register_enum(item)
            elif isinstance(item, rast.TypeAlias):
                self.type_aliases[item.name] = item.target
            elif isinstance(item, rast.ConstDef):
                self.constants[item.name] = item.type

        # Second pass: collect function signatures
        for item in module.items:
            if isinstance(item, rast.FnDef):
                self._register_function(item)
            elif isinstance(item, rast.ExternFn):
                self._register_extern(item)

        # Also collect impl block methods and trait implementations
        for item in module.items:
            if isinstance(item, rast.ImplBlock):
                # Track trait implementations
                if item.trait_name:
                    if item.trait_name not in self.trait_impls:
                        self.trait_impls[item.trait_name] = set()
                    self.trait_impls[item.trait_name].add(item.type_name)
                # Register methods
                for method in item.methods:
                    self._register_method(item, method)

        # Third pass: check function bodies
        for item in module.items:
            if isinstance(item, rast.FnDef):
                self._check_function(item)

        # Check impl methods
        for item in module.items:
            if isinstance(item, rast.ImplBlock):
                for method in item.methods:
                    self._check_function(method)

        return self.errors

    def _register_struct(self, struct: rast.StructDef):
        """Register struct definition."""
        self.structs[struct.name] = StructInfo(
            name=struct.name,
            fields=list(struct.fields),
            type_params=struct.type_params or []
        )

    def _register_enum(self, enum: rast.EnumDef):
        """Register enum definition."""
        self.enums[enum.name] = EnumInfo(
            name=enum.name,
            variants=enum.variants,
            type_params=enum.type_params
        )
        for variant in enum.variants:
            self.variant_to_enum[variant.name] = enum.name

    def _register_function(self, fn: rast.FnDef):
        """Register function signature."""
        self.functions[fn.name] = FnSig(
            name=fn.name,
            params=[(p.name, p.type) for p in fn.params],
            ret_type=fn.ret_type,
            type_params=fn.type_params or []
        )

    def _register_extern(self, fn: rast.ExternFn):
        """Register extern function signature."""
        self.functions[fn.name] = FnSig(
            name=fn.name,
            params=[(p.name, p.type) for p in fn.params],
            ret_type=fn.ret_type
        )

    def _register_method(self, impl: rast.ImplBlock, method: rast.FnDef):
        """Register impl method with mangled name."""
        # Mangled name: TypeName_methodName or TypeName$T_methodName for generics
        mangled = f"{impl.type_name}_{method.name}"
        self.functions[mangled] = FnSig(
            name=mangled,
            params=[(p.name, p.type) for p in method.params],
            ret_type=method.ret_type,
            type_params=method.type_params or []
        )

    def _push_scope(self):
        """Enter new scope."""
        self.scope_stack.append(dict(self.locals))

    def _pop_scope(self):
        """Exit scope."""
        if self.scope_stack:
            self.locals = self.scope_stack.pop()

    def _lookup_var(self, name: str) -> Optional[rast.Type]:
        """Look up variable type."""
        if name in self.locals:
            return self.locals[name]
        if name in self.constants:
            return self.constants[name]
        return None

    def _check_function(self, fn: rast.FnDef):
        """Type check a function body."""
        self.current_fn = self.functions.get(fn.name)
        self.locals = {}
        self.scope_stack = []

        # Track type parameters (T, E, etc.) so they're treated as valid types
        self.current_type_params = set(fn.type_params) if fn.type_params else set()

        # Add parameters to scope
        for param in fn.params:
            self.locals[param.name] = param.type

        # Check body
        self._check_block(fn.body, fn.ret_type)

        self.current_fn = None
        self.current_type_params = set()

    def _check_block(self, block: rast.Block, expected_ret: Optional[rast.Type] = None):
        """Type check a block."""
        for stmt in block.stmts:
            self._check_stmt(stmt)

        # Check trailing expression matches expected return type
        if block.expr and expected_ret:
            expr_type = self._infer_type(block.expr)
            if not self._types_compatible(expr_type, expected_ret):
                self._error(f"block expression has type {self._type_str(expr_type)}, "
                          f"expected {self._type_str(expected_ret)}", block.expr.span)

    def _check_stmt(self, stmt: rast.Stmt):
        """Type check a statement."""
        if isinstance(stmt, rast.VarStmt):
            if stmt.value:
                init_type = self._infer_type(stmt.value)
                if stmt.type:
                    if not self._types_compatible(init_type, stmt.type):
                        self._error(f"cannot initialize {self._type_str(stmt.type)} "
                                  f"with {self._type_str(init_type)}", stmt.span)
                    self.locals[stmt.name] = stmt.type
                else:
                    self.locals[stmt.name] = init_type
            elif stmt.type:
                self.locals[stmt.name] = stmt.type
            else:
                self._error(f"variable '{stmt.name}' needs type annotation or initializer", stmt.span)

        elif isinstance(stmt, rast.LetStmt):
            if stmt.value:
                init_type = self._infer_type(stmt.value)
                if stmt.type:
                    if not self._types_compatible(init_type, stmt.type):
                        self._error(f"cannot initialize {self._type_str(stmt.type)} "
                                  f"with {self._type_str(init_type)}", stmt.span)
                    self.locals[stmt.name] = stmt.type
                else:
                    self.locals[stmt.name] = init_type
            elif stmt.type:
                self.locals[stmt.name] = stmt.type
            else:
                self._error(f"let binding '{stmt.name}' needs type annotation or initializer", stmt.span)

        elif isinstance(stmt, rast.ExprStmt):
            self._infer_type(stmt.expr)

        elif isinstance(stmt, rast.ReturnStmt):
            if stmt.value:
                ret_type = self._infer_type(stmt.value)
                if self.current_fn and self.current_fn.ret_type:
                    if not self._types_compatible(ret_type, self.current_fn.ret_type):
                        self._error(f"return type {self._type_str(ret_type)} doesn't match "
                                  f"expected {self._type_str(self.current_fn.ret_type)}", stmt.span)

        elif isinstance(stmt, rast.AssignStmt):
            target_type = self._infer_type(stmt.target)
            value_type = self._infer_type(stmt.value)
            if not self._types_compatible(value_type, target_type):
                self._error(f"cannot assign {self._type_str(value_type)} "
                          f"to {self._type_str(target_type)}", stmt.span)

        elif isinstance(stmt, rast.WhileStmt):
            cond_type = self._infer_type(stmt.cond)
            if not self._is_bool_type(cond_type):
                self._error(f"while condition must be bool, got {self._type_str(cond_type)}",
                          stmt.cond.span)
            self._push_scope()
            self._check_block(stmt.body)
            self._pop_scope()

        elif isinstance(stmt, rast.ForStmt):
            self._push_scope()
            # Infer iterator element type
            iter_type = self._infer_type(stmt.iter)
            elem_type = self._get_iterator_element_type(iter_type)
            self.locals[stmt.var] = elem_type
            self._check_block(stmt.body)
            self._pop_scope()

        elif isinstance(stmt, rast.AssertStmt):
            cond_type = self._infer_type(stmt.condition)
            if not self._is_bool_type(cond_type):
                self._error(f"assert condition must be bool, got {self._type_str(cond_type)}",
                          stmt.condition.span)

    def _infer_type(self, expr: rast.Expr) -> rast.Type:
        """Infer the type of an expression."""
        if isinstance(expr, rast.IntLit):
            # Integer literals default to i64
            return rast.NamedType(expr.span, 'i64', [])

        elif isinstance(expr, rast.FloatLit):
            return rast.NamedType(expr.span, 'f64', [])

        elif isinstance(expr, rast.BoolLit):
            return rast.NamedType(expr.span, 'bool', [])

        elif isinstance(expr, rast.CharLit):
            return rast.NamedType(expr.span, 'u8', [])

        elif isinstance(expr, rast.StringLit):
            # Bare string literals produce StrView (AGAST #98, Wave 3).
            # `"hello"` is a zero-copy view { ptr, len }. Use `c"..."` for
            # null-terminated *u8, and call a `String` constructor explicitly
            # for a heap-owned String.
            return rast.NamedType(expr.span, 'StrView', [])

        elif isinstance(expr, rast.CStringLit):
            # C-string literals: c"hello" -> *u8 (null-terminated)
            return rast.PtrType(expr.span, rast.NamedType(expr.span, 'u8', []), mutable=False)

        elif isinstance(expr, rast.SpanStringLit):
            # Span string literals: s"hello" -> Span<u8> { ptr, len }
            # Generic type Span with u8 type argument
            return rast.NamedType(expr.span, 'Span', [rast.NamedType(expr.span, 'u8', [])])

        elif isinstance(expr, rast.NullLit):
            # Null is a special pointer type compatible with any pointer
            # We use a special 'null' named type that is compatible with any *T
            return rast.NamedType(expr.span, 'null', [])

        elif isinstance(expr, rast.Ident):
            ty = self._lookup_var(expr.name)
            if ty is None:
                # Check if it's a unit enum variant
                if expr.name in self.variant_to_enum:
                    enum_name = self.variant_to_enum[expr.name]
                    return rast.NamedType(expr.span, enum_name, [])
                self._error(f"undefined variable: {expr.name}", expr.span)
                return rast.NamedType(expr.span, 'unknown', [])
            return ty

        elif isinstance(expr, rast.BinOp):
            return self._check_binop(expr)

        elif isinstance(expr, rast.UnaryOp):
            return self._check_unaryop(expr)

        elif isinstance(expr, rast.Call):
            return self._check_call(expr)

        elif isinstance(expr, rast.Field):
            return self._check_field_access(expr)

        elif isinstance(expr, rast.Index):
            return self._check_index(expr)

        elif isinstance(expr, rast.If):
            return self._check_if(expr)

        elif isinstance(expr, rast.Block):
            self._push_scope()
            for stmt in expr.stmts:
                self._check_stmt(stmt)
            result = rast.NamedType(expr.span, 'void', [])
            if expr.expr:
                result = self._infer_type(expr.expr)
            self._pop_scope()
            return result

        elif isinstance(expr, rast.StructLit):
            return self._check_struct_lit(expr)

        elif isinstance(expr, rast.ArrayLit):
            if not expr.elements:
                return rast.ArrayType(expr.span, 0, rast.NamedType(expr.span, 'unknown', []))
            elem_type = self._infer_type(expr.elements[0])
            return rast.ArrayType(expr.span, len(expr.elements), elem_type)

        elif isinstance(expr, rast.ArrayFill):
            elem_type = self._infer_type(expr.value)
            return rast.ArrayType(expr.span, expr.count, elem_type)

        elif isinstance(expr, rast.TupleLit):
            # Infer tuple type from element types
            element_types = [self._infer_type(elem) for elem in expr.elements]
            return rast.TupleType(expr.span, element_types)

        elif isinstance(expr, rast.Cast):
            # Just check the source expression is valid
            self._infer_type(expr.expr)
            return expr.target

        elif isinstance(expr, rast.Match):
            return self._check_match(expr)

        elif isinstance(expr, rast.TryOp):
            return self._check_try_op(expr)

        elif isinstance(expr, rast.MethodCall):
            return self._check_method_call(expr)

        elif isinstance(expr, rast.SliceExpr):
            base_type = self._infer_type(expr.expr)
            if expr.start:
                self._check_integer_type(self._infer_type(expr.start), expr.start.span)
            if expr.end:
                self._check_integer_type(self._infer_type(expr.end), expr.end.span)
            # Slice returns same type (for now - could return Span<T> later)
            return base_type

        elif isinstance(expr, rast.Range):
            if expr.start:
                self._infer_type(expr.start)
            if expr.end:
                self._infer_type(expr.end)
            return rast.NamedType(expr.span, 'Range', [])

        elif isinstance(expr, rast.Await):
            # Await unwraps a Future<T> to T
            inner_type = self._infer_type(expr.expr)
            # The awaited expression should be a Future or async fn call
            # For now, just return unknown since we don't track future types
            return rast.NamedType(expr.span, 'unknown', [])

        elif isinstance(expr, rast.Closure):
            # Infer closure type from parameters and body
            param_types = []
            for p in expr.params:
                if p.type:
                    param_types.append(p.type)
                else:
                    param_types.append(rast.NamedType(expr.span, 'unknown', []))
            body_type = self._infer_type(expr.body)
            return rast.FnType(expr.span, param_types, body_type)

        elif isinstance(expr, rast.Lambda):
            # Lambda is an older form of closure with explicit param types
            param_types = [p.type for p in expr.params]
            body_type = self._infer_type(expr.body)
            return rast.FnType(expr.span, param_types, body_type if body_type else rast.NamedType(expr.span, 'unknown', []))

        else:
            self._error(f"cannot infer type of {type(expr).__name__}", getattr(expr, 'span', None))
            return rast.NamedType(expr.span if hasattr(expr, 'span') else None, 'unknown', [])

    def _check_binop(self, expr: rast.BinOp) -> rast.Type:
        """Type check binary operation and return result type."""
        left_type = self._infer_type(expr.left)
        right_type = self._infer_type(expr.right)

        # Comparison operators return bool
        if expr.op in ('==', '!=', '<', '>', '<=', '>='):
            if not self._types_compatible(left_type, right_type):
                self._error(f"cannot compare {self._type_str(left_type)} "
                          f"with {self._type_str(right_type)}", expr.span)
            return rast.NamedType(expr.span, 'bool', [])

        # Logical operators require bool, return bool
        if expr.op in ('&&', '||'):
            if not self._is_bool_type(left_type):
                self._error(f"logical operator requires bool, got {self._type_str(left_type)}",
                          expr.left.span)
            if not self._is_bool_type(right_type):
                self._error(f"logical operator requires bool, got {self._type_str(right_type)}",
                          expr.right.span)
            return rast.NamedType(expr.span, 'bool', [])

        # Arithmetic operators
        if expr.op in ('+', '-', '*', '/', '%'):
            # Pointer/reference arithmetic: ptr + int or ptr - int
            if isinstance(left_type, (rast.PtrType, rast.RefType)) and self._is_integer_type(right_type):
                # Return as pointer type for arithmetic result
                if isinstance(left_type, rast.RefType):
                    return rast.PtrType(expr.span, left_type.inner, mutable=left_type.mutable)
                return left_type
            if isinstance(right_type, (rast.PtrType, rast.RefType)) and self._is_integer_type(left_type):
                if isinstance(right_type, rast.RefType):
                    return rast.PtrType(expr.span, right_type.inner, mutable=right_type.mutable)
                return right_type

            # Numeric arithmetic
            if not self._is_numeric_type(left_type):
                self._error(f"arithmetic operator requires numeric type, "
                          f"got {self._type_str(left_type)}", expr.left.span)
            if not self._is_numeric_type(right_type):
                self._error(f"arithmetic operator requires numeric type, "
                          f"got {self._type_str(right_type)}", expr.right.span)
            # Return the "wider" type (simplified: just return left type)
            return self._promote_numeric_types(left_type, right_type)

        # Bitwise operators
        if expr.op in ('&', '|', '^', '<<', '>>'):
            if not self._is_integer_type(left_type):
                self._error(f"bitwise operator requires integer, got {self._type_str(left_type)}",
                          expr.left.span)
            if not self._is_integer_type(right_type):
                self._error(f"bitwise operator requires integer, got {self._type_str(right_type)}",
                          expr.right.span)
            return left_type

        return left_type

    def _check_unaryop(self, expr: rast.UnaryOp) -> rast.Type:
        """Type check unary operation."""
        operand_type = self._infer_type(expr.operand)

        if expr.op == '-':
            if not self._is_numeric_type(operand_type):
                self._error(f"negation requires numeric type, got {self._type_str(operand_type)}",
                          expr.operand.span)
            return operand_type

        elif expr.op == '!':
            if not self._is_bool_type(operand_type):
                self._error(f"logical not requires bool, got {self._type_str(operand_type)}",
                          expr.operand.span)
            return rast.NamedType(expr.span, 'bool', [])

        elif expr.op in ('&', '@'):
            # Immutable borrow: @ in RERITZ, & for legacy compatibility
            return rast.RefType(expr.span, operand_type, mutable=False)

        elif expr.op in ('&mut', '@&'):
            # Mutable borrow: @& in RERITZ, &mut for legacy compatibility
            return rast.RefType(expr.span, operand_type, mutable=True)

        elif expr.op == '*':
            # Dereference
            if isinstance(operand_type, rast.PtrType):
                return operand_type.inner
            elif isinstance(operand_type, rast.RefType):
                return operand_type.inner
            else:
                self._error(f"cannot dereference non-pointer type {self._type_str(operand_type)}",
                          expr.span)
                return rast.NamedType(expr.span, 'unknown', [])

        return operand_type

    def _check_call(self, expr: rast.Call) -> rast.Type:
        """Type check function call."""
        # Get function name
        if isinstance(expr.func, rast.Ident):
            fn_name = expr.func.name

            # Handle built-in functions that don't need signature lookup
            # sizeof(Type) -> i64
            if fn_name == 'sizeof':
                if len(expr.args) != 1:
                    self._error("sizeof() requires exactly 1 type argument", expr.span)
                return rast.NamedType(expr.span, 'i64', [])

            # typeof(expr) -> type info (returns i64 type id for now)
            if fn_name == 'typeof':
                if len(expr.args) == 1:
                    self._infer_type(expr.args[0])
                return rast.NamedType(expr.span, 'i64', [])

            # __builtin_alloca(size) -> *i8
            if fn_name == '__builtin_alloca':
                if len(expr.args) == 1:
                    arg_type = self._infer_type(expr.args[0])
                    if not self._is_integer_type(arg_type):
                        self._error(f"__builtin_alloca expects integer size, got {self._type_str(arg_type)}", expr.span)
                return rast.PtrType(expr.span, rast.NamedType(expr.span, 'i8', []), mutable=True)

            # syscall0..syscall6 -> i64
            if fn_name.startswith('syscall') or fn_name.startswith('__syscall'):
                for arg in expr.args:
                    self._infer_type(arg)
                return rast.NamedType(expr.span, 'i64', [])

            # print(str) -> void
            if fn_name == 'print':
                for arg in expr.args:
                    self._infer_type(arg)
                return rast.NamedType(expr.span, 'void', [])

            # Check if it's an enum variant constructor
            if fn_name in self.variant_to_enum:
                enum_name = self.variant_to_enum[fn_name]
                return rast.NamedType(expr.span, enum_name, [])

            # Look up function
            fn_sig = self.functions.get(fn_name)
            if fn_sig is None:
                self._error(f"undefined function: {fn_name}", expr.func.span)
                return rast.NamedType(expr.span, 'unknown', [])

            # Check argument count
            if len(expr.args) != len(fn_sig.params):
                self._error(f"function '{fn_name}' expects {len(fn_sig.params)} arguments, "
                          f"got {len(expr.args)}", expr.span)
            else:
                # Check argument types
                for i, (arg, (param_name, param_type)) in enumerate(zip(expr.args, fn_sig.params)):
                    arg_type = self._infer_type(arg)
                    if not self._types_compatible(arg_type, param_type):
                        self._error(f"argument {i+1} ('{param_name}'): expected {self._type_str(param_type)}, "
                                  f"got {self._type_str(arg_type)}", arg.span)

            return fn_sig.ret_type or rast.NamedType(expr.span, 'void', [])

        else:
            # Indirect call - just infer args
            for arg in expr.args:
                self._infer_type(arg)
            return rast.NamedType(expr.span, 'unknown', [])

    def _check_method_call(self, expr: rast.MethodCall) -> rast.Type:
        """Type check method call."""
        receiver_type = self._infer_type(expr.expr)
        type_name = self._get_type_name(receiver_type)

        # Look up method - try several name patterns
        fn_sig = None
        tried_names = []

        # Try exact match first
        mangled = f"{type_name}_{expr.method}"
        tried_names.append(mangled)
        fn_sig = self.functions.get(mangled)

        if fn_sig is None:
            # For generic types like Vec<u8>, try base name (Vec_method)
            base_name = type_name.split('<')[0].split('$')[0]
            if base_name != type_name:
                mangled = f"{base_name}_{expr.method}"
                tried_names.append(mangled)
                fn_sig = self.functions.get(mangled)

        if fn_sig is None:
            # Try as free function (common for string_len, vec_push, etc.)
            # Convention: type_method for String -> string_method
            lower_name = f"{type_name.lower()}_{expr.method}"
            tried_names.append(lower_name)
            fn_sig = self.functions.get(lower_name)

        if fn_sig is None:
            # Try just the method name
            tried_names.append(expr.method)
            fn_sig = self.functions.get(expr.method)

        if fn_sig is None:
            self._error(f"no method '{expr.method}' on type {self._type_str(receiver_type)}",
                      expr.span)
            return rast.NamedType(expr.span, 'unknown', [])

        # Check args (receiver is already the first implicit arg)
        for arg in expr.args:
            self._infer_type(arg)

        return fn_sig.ret_type or rast.NamedType(expr.span, 'void', [])

    def _check_field_access(self, expr: rast.Field) -> rast.Type:
        """Type check field access."""
        base_type = self._infer_type(expr.expr)

        # Unwrap pointers/refs for field access
        inner_type = base_type
        while isinstance(inner_type, (rast.PtrType, rast.RefType)):
            inner_type = inner_type.inner

        # Handle tuple field access: tuple.0, tuple.1, etc.
        if isinstance(inner_type, rast.TupleType):
            if expr.field.isdigit():
                index = int(expr.field)
                if index < len(inner_type.elements):
                    return inner_type.elements[index]
                else:
                    self._error(f"tuple index {index} out of bounds for tuple with {len(inner_type.elements)} elements", expr.span)
                    return rast.NamedType(expr.span, 'unknown', [])
            else:
                self._error(f"tuple fields must be numeric indices, got '{expr.field}'", expr.span)
                return rast.NamedType(expr.span, 'unknown', [])

        if not isinstance(inner_type, rast.NamedType):
            self._error(f"cannot access field on {self._type_str(base_type)}", expr.span)
            return rast.NamedType(expr.span, 'unknown', [])

        struct_info = self.structs.get(inner_type.name)
        if struct_info is None:
            # Check for Box<T> implicit deref
            if inner_type.name.startswith('Box$') or inner_type.name.startswith('Box_'):
                # Try to get inner type from Box
                pass
            self._error(f"type {inner_type.name} has no fields", expr.span)
            return rast.NamedType(expr.span, 'unknown', [])

        # Find field
        for field_name, field_type in struct_info.fields:
            if field_name == expr.field:
                return field_type

        self._error(f"struct '{struct_info.name}' has no field '{expr.field}'", expr.span)
        return rast.NamedType(expr.span, 'unknown', [])

    def _check_index(self, expr: rast.Index) -> rast.Type:
        """Type check index operation."""
        base_type = self._infer_type(expr.expr)
        index_type = self._infer_type(expr.index)

        # Index must be integer
        if not self._is_integer_type(index_type):
            self._error(f"index must be integer, got {self._type_str(index_type)}",
                      expr.index.span)

        # Get element type
        if isinstance(base_type, rast.ArrayType):
            return base_type.inner
        elif isinstance(base_type, rast.PtrType):
            return base_type.inner
        elif isinstance(base_type, rast.RefType):
            inner = base_type.inner
            if isinstance(inner, rast.ArrayType):
                return inner.inner
            return inner
        elif isinstance(base_type, rast.NamedType):
            # Could be Vec<T>, String, etc - allow indexing
            # In full implementation, would look up Index trait
            return rast.NamedType(expr.span, 'unknown', [])
        else:
            self._error(f"cannot index into {self._type_str(base_type)}", expr.span)
            return rast.NamedType(expr.span, 'unknown', [])

    def _check_if(self, expr: rast.If) -> rast.Type:
        """Type check if expression."""
        cond_type = self._infer_type(expr.cond)
        if not self._is_bool_type(cond_type):
            self._error(f"if condition must be bool, got {self._type_str(cond_type)}",
                      expr.cond.span)

        self._push_scope()
        then_type = rast.NamedType(expr.span, 'void', [])
        for stmt in expr.then_block.stmts:
            self._check_stmt(stmt)
        if expr.then_block.expr:
            then_type = self._infer_type(expr.then_block.expr)
        self._pop_scope()

        if expr.else_block:
            self._push_scope()
            else_type = rast.NamedType(expr.span, 'void', [])
            for stmt in expr.else_block.stmts:
                self._check_stmt(stmt)
            if expr.else_block.expr:
                else_type = self._infer_type(expr.else_block.expr)
            self._pop_scope()

            # Both branches should have same type
            if not self._types_compatible(then_type, else_type):
                self._error(f"if branches have different types: {self._type_str(then_type)} "
                          f"and {self._type_str(else_type)}", expr.span)
            return then_type

        return then_type

    def _check_struct_lit(self, expr: rast.StructLit) -> rast.Type:
        """Type check struct literal."""
        struct_info = self.structs.get(expr.name)
        if struct_info is None:
            self._error(f"undefined struct: {expr.name}", expr.span)
            return rast.NamedType(expr.span, expr.name, [])

        # Check all fields are provided and have correct types
        provided_fields = {name: value for name, value in expr.fields}
        expected_fields = {name: ty for name, ty in struct_info.fields}

        for field_name in provided_fields:
            if field_name not in expected_fields:
                self._error(f"struct '{expr.name}' has no field '{field_name}'", expr.span)

        for name, value in expr.fields:
            if name in expected_fields:
                value_type = self._infer_type(value)
                if not self._types_compatible(value_type, expected_fields[name]):
                    self._error(f"field '{name}': expected {self._type_str(expected_fields[name])}, "
                              f"got {self._type_str(value_type)}", value.span)

        return rast.NamedType(expr.span, expr.name, list(expr.type_args) if expr.type_args else [])

    def _check_match(self, expr: rast.Match) -> rast.Type:
        """Type check match expression."""
        match_type = self._infer_type(expr.expr)

        result_type = None
        for arm in expr.arms:
            self._push_scope()
            self._check_pattern(arm.pattern, match_type)
            if arm.guard:
                guard_type = self._infer_type(arm.guard)
                if not self._is_bool_type(guard_type):
                    self._error(f"match guard must be bool", arm.guard.span)

            arm_type = self._infer_type(arm.body)
            if result_type is None:
                result_type = arm_type
            elif not self._types_compatible(arm_type, result_type):
                self._error(f"match arms have different types: {self._type_str(result_type)} "
                          f"and {self._type_str(arm_type)}", arm.body.span)
            self._pop_scope()

        return result_type or rast.NamedType(expr.span, 'void', [])

    def _check_try_op(self, expr: rast.TryOp) -> rast.Type:
        """Type check try operator (?)."""
        inner_type = self._infer_type(expr.expr)

        # Should be Result<T, E> - extract T
        if isinstance(inner_type, rast.NamedType):
            if inner_type.name.startswith('Result'):
                # Extract success type from Result<T, E>
                if inner_type.args:
                    return inner_type.args[0]

        return rast.NamedType(expr.span, 'unknown', [])

    def _check_pattern(self, pattern: rast.Pattern, expected_type: rast.Type):
        """Type check a pattern and bind variables."""
        if isinstance(pattern, rast.IdentPattern):
            self.locals[pattern.name] = expected_type
        elif isinstance(pattern, rast.VariantPattern):
            # Look up variant - use qualifier if provided, otherwise fall back to lookup
            enum_name = None
            if pattern.qualifier:
                # Qualified pattern: Type.Variant - use the qualifier as enum name
                enum_name = pattern.qualifier
            elif pattern.name in self.variant_to_enum:
                # Unqualified pattern: look up which enum this variant belongs to
                enum_name = self.variant_to_enum[pattern.name]

            if enum_name:
                enum_info = self.enums.get(enum_name)
                if enum_info:
                    for variant in enum_info.variants:
                        if variant.name == pattern.name:
                            # Bind sub-patterns to variant field types
                            for sub_pat, field_type in zip(pattern.fields, variant.fields):
                                self._check_pattern(sub_pat, field_type)
                            break
        elif isinstance(pattern, rast.StructPattern):
            struct_info = self.structs.get(pattern.name)
            if struct_info:
                field_types = {name: ty for name, ty in struct_info.fields}
                for field_name, sub_pat in pattern.fields:
                    if field_name in field_types:
                        self._check_pattern(sub_pat, field_types[field_name])

    # Helper methods

    def _is_bool_type(self, ty: rast.Type) -> bool:
        """Check if type is bool."""
        return isinstance(ty, rast.NamedType) and ty.name == 'bool'

    def _is_integer_type(self, ty: rast.Type) -> bool:
        """Check if type is an integer type."""
        if isinstance(ty, rast.NamedType):
            return ty.name in self.INT_TYPES
        return False

    def _is_numeric_type(self, ty: rast.Type) -> bool:
        """Check if type is numeric (integer or float)."""
        if isinstance(ty, rast.NamedType):
            return ty.name in self.NUMERIC_TYPES
        return False

    def _check_integer_type(self, ty: rast.Type, span: Optional[rast.Span]):
        """Check that type is an integer, error if not."""
        if not self._is_integer_type(ty):
            self._error(f"expected integer type, got {self._type_str(ty)}", span)

    def _types_compatible(self, actual: rast.Type, expected: rast.Type) -> bool:
        """Check if actual type is compatible with expected type."""
        # Handle None/unknown
        if actual is None or expected is None:
            return True

        # Null is compatible with any pointer type
        if isinstance(actual, rast.NamedType) and actual.name == 'null':
            return isinstance(expected, (rast.PtrType, rast.RefType)) or \
                   (isinstance(expected, rast.NamedType) and expected.name == 'null')

        if isinstance(expected, rast.NamedType) and expected.name == 'null':
            return isinstance(actual, (rast.PtrType, rast.RefType)) or \
                   (isinstance(actual, rast.NamedType) and actual.name == 'null')

        # Type parameters (T, E, etc.) are compatible with any type in their scope
        # This allows generic functions to work without full monomorphization tracking
        if isinstance(expected, rast.NamedType) and expected.name in self.current_type_params:
            return True
        if isinstance(actual, rast.NamedType) and actual.name in self.current_type_params:
            return True

        # Also treat single uppercase letters as type parameters (Ritz convention)
        # This handles cases like Result<T, E> where the generic enum definition uses T/E
        def is_type_param_name(name: str) -> bool:
            return len(name) == 1 and name.isupper()

        if isinstance(expected, rast.NamedType) and is_type_param_name(expected.name):
            return True
        if isinstance(actual, rast.NamedType) and is_type_param_name(actual.name):
            return True

        # Same named type
        if isinstance(actual, rast.NamedType) and isinstance(expected, rast.NamedType):
            if actual.name == expected.name:
                return True
            # Integer literal coercion: i64 literal can be used where smaller int expected
            if actual.name == 'i64' and expected.name in self.INT_TYPES:
                return True
            if actual.name in self.INT_TYPES and expected.name in self.INT_TYPES:
                return True  # Allow integer type coercion for now
            if actual.name == 'unknown' or expected.name == 'unknown':
                return True
            # void compatible with no return
            if actual.name == 'void' or expected.name == 'void':
                return True

        # Pointer-to-integer and integer-to-pointer coercion (common for low-level code)
        if isinstance(actual, (rast.PtrType, rast.RefType)) and isinstance(expected, rast.NamedType):
            if expected.name in {'i64', 'u64', 'isize', 'usize'}:
                return True
        if isinstance(actual, rast.NamedType) and isinstance(expected, (rast.PtrType, rast.RefType)):
            if actual.name in {'i64', 'u64', 'isize', 'usize'}:
                return True

        # String -> *u8 implicit coercion (Issue #89)
        # String can be passed where *u8 is expected; compiler will call string_as_ptr()
        if isinstance(actual, rast.NamedType) and actual.name == 'String':
            if isinstance(expected, rast.PtrType):
                if isinstance(expected.inner, rast.NamedType) and expected.inner.name == 'u8':
                    return True

        # Pointer types
        if isinstance(actual, rast.PtrType) and isinstance(expected, rast.PtrType):
            return self._types_compatible(actual.inner, expected.inner)

        # Reference types
        if isinstance(actual, rast.RefType) and isinstance(expected, rast.RefType):
            return self._types_compatible(actual.inner, expected.inner)

        # Pointer and reference are compatible for now
        if isinstance(actual, rast.PtrType) and isinstance(expected, rast.RefType):
            return self._types_compatible(actual.inner, expected.inner)
        if isinstance(actual, rast.RefType) and isinstance(expected, rast.PtrType):
            return self._types_compatible(actual.inner, expected.inner)

        # Array types
        if isinstance(actual, rast.ArrayType) and isinstance(expected, rast.ArrayType):
            return self._types_compatible(actual.inner, expected.inner)

        # Tuple types
        if isinstance(actual, rast.TupleType) and isinstance(expected, rast.TupleType):
            if len(actual.elements) != len(expected.elements):
                return False
            return all(self._types_compatible(a, e)
                       for a, e in zip(actual.elements, expected.elements))

        # Function pointer types
        if isinstance(actual, rast.FnType) and isinstance(expected, rast.FnType):
            if len(actual.params) != len(expected.params):
                return False
            for a, e in zip(actual.params, expected.params):
                if not self._types_compatible(a, e):
                    return False
            return self._types_compatible(actual.ret, expected.ret)

        # Trait objects (dyn Trait)
        if isinstance(actual, rast.DynType) and isinstance(expected, rast.DynType):
            # Same trait name = compatible (ignore args for now)
            return actual.trait_name == expected.trait_name

        # Coercion to dyn Trait: &T -> &dyn Trait when T implements Trait
        if isinstance(expected, rast.DynType):
            # Reference/pointer to dyn Trait
            if isinstance(actual, (rast.RefType, rast.PtrType)):
                inner = actual.inner
                if isinstance(inner, rast.NamedType):
                    # Check if the concrete type implements the trait
                    if self._type_implements_trait(inner.name, expected.trait_name):
                        return True

        # Reference/pointer wrapping dyn Trait
        if isinstance(expected, (rast.RefType, rast.PtrType)):
            if isinstance(expected.inner, rast.DynType):
                if isinstance(actual, (rast.RefType, rast.PtrType)):
                    inner = actual.inner
                    if isinstance(inner, rast.NamedType):
                        # &T -> &dyn Trait coercion
                        if self._type_implements_trait(inner.name, expected.inner.trait_name):
                            return True

        # Unknown is compatible with function types (for inference)
        if isinstance(actual, rast.NamedType) and actual.name == 'unknown':
            return True
        if isinstance(expected, rast.NamedType) and expected.name == 'unknown':
            return True

        return False

    def _type_implements_trait(self, type_name: str, trait_name: str) -> bool:
        """Check if a type implements a given trait."""
        if trait_name in self.trait_impls:
            return type_name in self.trait_impls[trait_name]
        return False

    def _promote_numeric_types(self, t1: rast.Type, t2: rast.Type) -> rast.Type:
        """Get the common type for two numeric types."""
        # Simplified: just return the first type
        # Full implementation would return the "wider" type
        return t1

    def _get_iterator_element_type(self, iter_type: rast.Type) -> rast.Type:
        """Get element type from an iterator type."""
        if isinstance(iter_type, rast.NamedType):
            if iter_type.name == 'Range':
                return rast.NamedType(iter_type.span, 'i64', [])
        return rast.NamedType(None, 'unknown', [])

    def _get_type_name(self, ty: rast.Type) -> str:
        """Get the base type name for method lookup."""
        if isinstance(ty, rast.NamedType):
            return ty.name
        elif isinstance(ty, rast.PtrType):
            return self._get_type_name(ty.inner)
        elif isinstance(ty, rast.RefType):
            return self._get_type_name(ty.inner)
        return 'unknown'

    def _type_str(self, ty: Optional[rast.Type]) -> str:
        """Convert type to string for error messages."""
        if ty is None:
            return 'void'
        if isinstance(ty, rast.NamedType):
            if ty.args:
                args = ', '.join(self._type_str(a) for a in ty.args)
                return f"{ty.name}<{args}>"
            return ty.name
        elif isinstance(ty, rast.PtrType):
            return f"*{self._type_str(ty.inner)}"
        elif isinstance(ty, rast.RefType):
            if ty.mutable:
                return f"@&{self._type_str(ty.inner)}"
            return f"@{self._type_str(ty.inner)}"
        elif isinstance(ty, rast.ArrayType):
            return f"[{ty.size}]{self._type_str(ty.inner)}"
        elif isinstance(ty, rast.UnionType):
            return ' | '.join(self._type_str(v) for v in ty.variants)
        elif isinstance(ty, rast.FnType):
            params = ', '.join(self._type_str(p) for p in ty.params)
            return f"fn({params}) -> {self._type_str(ty.ret)}"
        elif isinstance(ty, rast.TupleType):
            elem_strs = ', '.join(self._type_str(e) for e in ty.elements)
            return f"({elem_strs})"
        return str(ty)

    def _error(self, message: str, span: Optional[rast.Span]):
        """Record a type error."""
        self.errors.append(TypeError(message, span))
