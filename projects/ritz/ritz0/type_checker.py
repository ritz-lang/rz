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

import copy
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import array_rules
import bool_rules
import ref_rules
import ritz_ast as rast
from tail_value import slot_tails
from monomorph import mangle_generic_name
from ufcs import find_ufcs_function
from name_resolver import (BUILTIN_GENERICS, BUILTIN_VARIANTS, INTRINSICS,
                           SYSCALL_BUILTINS)


class FloatLitType(rast.NamedType):
    """A float literal's type: f64, unless its context makes it an f32."""


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
    is_async: bool = False
    # Indexes of `name:& T` params: the slot is the caller's place, not a `T`.
    lent: Set[int] = field(default_factory=set)


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
    INT_TYPES = {'i8', 'i16', 'i32', 'i64', 'isize',
                 'u8', 'u16', 'u32', 'u64', 'usize'}
    SIGNED_INT_TYPES = {'i8', 'i16', 'i32', 'i64', 'isize'}
    UNSIGNED_INT_TYPES = {'u8', 'u16', 'u32', 'u64', 'usize'}

    # Numeric types (integers + floats)
    NUMERIC_TYPES = INT_TYPES | {'f32', 'f64'}

    def __init__(self, module_names: Optional[Set[str]] = None,
                 slots_only: bool = False):
        self.errors: List[TypeError] = []

        # Report only what doesn't fit between values and references
        # (check_ref_slots).
        self.slots_only = slots_only
        self._arg_depth = 0  # >0 while a call argument is checked
        # `name:& T` params of the current fn, by name, with their `T`: `*name`
        # is the `T` itself.
        self.lent_locals: Dict[str, rast.Type] = {}
        # The slot an `if`, `match` or block's tails land in (_infer_into).
        self._tail_slot: Optional[rast.Type] = None
        # id(expr) already reported: a literal's elements are inferred twice.
        self._slot_reported: Set[int] = set()
        # The types `let` bindings of the current fn hold, each its own copy, so
        # that a name is a `let` when its current type is one of them. A `var` or
        # pattern binding copies what it infers, or `var d = c` would be `c`'s.
        self._let_types: List[rast.Type] = []
        # Bindings of the current fn that definitely hold a reference to a local
        # root (§13.5), by id of the type they hold: (that type, the root's name,
        # how many loops the binding was declared in).
        self._local_refs: Dict[int, Tuple[rast.Type, str, int]] = {}
        # The loops around the statement being checked.
        self._loop_depth = 0
        # What each call in the current fn reached: its signature, and how many
        # of its params the arguments skip.
        self._callees: Dict[int, Tuple[FnSig, int]] = {}

        # Imported modules, which qualify names: `token.Kind`
        self.module_names: Set[str] = set(module_names or ())

        # Symbol tables
        self.functions: Dict[str, FnSig] = {}
        # StrView is the emitter's own struct: no source file declares it.
        self.structs: Dict[str, StructInfo] = {'StrView': StructInfo('StrView', [
            ('ptr', rast.PtrType(None, rast.NamedType(None, 'u8', []), mutable=False)),
            ('len', rast.NamedType(None, 'i64', []))])}
        self.enums: Dict[str, EnumInfo] = {}
        self.type_aliases: Dict[str, rast.Type] = {}
        self.constants: Dict[str, rast.Type] = {}
        self.globals: Dict[str, Optional[rast.Type]] = {}  # module-level `var`

        # Variant to enum mapping
        self.variant_to_enum: Dict[str, str] = {}
        # How many enums declare each variant: an instance of a generic enum
        # shares its variants' names with every other instance.
        self.variant_owners: Dict[str, int] = {}

        # Trait implementations: trait_name -> set of type names that implement it
        self.trait_impls: Dict[str, Set[str]] = {}

        # Current context
        self.locals: Dict[str, rast.Type] = {}  # local variables
        self.current_fn: Optional[FnSig] = None
        self.scope_stack: List[Dict[str, rast.Type]] = []
        self.current_type_params: Set[str] = set()  # type parameters in scope (T, E, etc.)

    def check(self, module: rast.Module, emits_body=None) -> List[TypeError]:
        """Type check a module. Returns list of errors. `emits_body`, if
        given, picks the fns whose bodies are checked."""
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
            elif isinstance(item, rast.VarDef):
                self.globals[item.name] = item.type

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
        wanted = emits_body or (lambda _fn: True)
        for item in module.items:
            if isinstance(item, rast.FnDef) and wanted(item):
                self._check_function(item)

        # Check impl methods
        for item in module.items:
            if isinstance(item, rast.ImplBlock):
                for method in item.methods:
                    if wanted(method):
                        self._check_function(method, item)

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
            self.variant_owners[variant.name] = self.variant_owners.get(variant.name, 0) + 1

    def _register_function(self, fn: rast.FnDef):
        """Register function signature."""
        self.functions[fn.name] = FnSig(
            name=fn.name,
            params=[(p.name, p.type) for p in fn.params],
            ret_type=fn.ret_type,
            type_params=fn.type_params or [],
            is_async=getattr(fn, 'is_async', False),
            lent=self._lent_params(fn)
        )

    def _register_extern(self, fn: rast.ExternFn):
        """Register extern function signature."""
        self.functions[fn.name] = FnSig(
            name=fn.name,
            params=[(p.name, p.type) for p in fn.params],
            ret_type=fn.ret_type,
            lent=self._lent_params(fn)
        )

    def _register_method(self, impl: rast.ImplBlock, method: rast.FnDef):
        """Register impl method with mangled name."""
        # Mangled name: TypeName_methodName or TypeName$T_methodName for generics
        mangled = f"{impl.type_name}_{method.name}"
        self.functions[mangled] = FnSig(
            name=mangled,
            params=[(p.name, p.type) for p in method.params],
            ret_type=method.ret_type,
            type_params=method.type_params or [],
            lent=self._lent_params(method)
        )

    @staticmethod
    def _lent_params(fn) -> Set[int]:
        return {i for i, p in enumerate(fn.params)
                if p.borrow == rast.Borrow.MUTABLE}

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
        if name in self.globals:
            # An untyped global's type comes from its initialiser: not tracked.
            return self.globals[name] or rast.NamedType(None, 'unknown', [])
        return None

    def _check_function(self, fn: rast.FnDef, impl: Optional[rast.ImplBlock] = None):
        """Type check a function body; `impl` is the block a method sits in."""
        # A method is registered mangled: `fn.name` alone would find a free
        # function of the same name and check against that signature.
        self.current_fn = self.functions.get(
            f"{impl.type_name}_{fn.name}" if impl else fn.name)
        self.locals = {}
        self.scope_stack = []

        # Track type parameters (T, E, etc.) so they're treated as valid types
        self.current_type_params = set(fn.type_params or [])
        if impl:
            self.current_type_params |= set(impl.type_params or [])

        # Add parameters to scope
        self.lent_locals = {}
        self._let_types = []
        self._local_refs = {}
        self._loop_depth = 0
        self._callees = {}
        for param in fn.params:
            self.locals[param.name] = param.type
            if param.borrow == rast.Borrow.MUTABLE:
                self.lent_locals[param.name] = param.type

        # Check body
        self._check_block(fn.body, fn.ret_type)

        self.current_fn = None
        self.current_type_params = set()

    def _check_block(self, block: rast.Block, expected_ret: Optional[rast.Type] = None):
        """Type check a block."""
        for stmt in block.stmts:
            self._check_stmt(stmt)

        # Check trailing expression matches expected return type
        if block.expr:
            expr_type = self._infer_into(block.expr, expected_ret)
            if expected_ret and not self._value_fits(block.expr, expr_type, expected_ret):
                self._error(f"block expression has type {self._type_str(expr_type)}, "
                          f"expected {self._type_str(expected_ret)}", block.expr.span)

    def _check_stmt(self, stmt: rast.Stmt):
        """Type check a statement."""
        if isinstance(stmt, rast.VarStmt):
            if stmt.value:
                init_type = self._infer_into(stmt.value, stmt.type)
                root = self._referent(stmt.value)
                if stmt.type:
                    if not self._value_fits(stmt.value, init_type, stmt.type):
                        self._error(f"cannot initialize {self._type_str(stmt.type)} "
                                  f"with {self._type_str(init_type)}", stmt.span)
                    # Its own copy: `_local_refs` tells bindings apart by it.
                    self.locals[stmt.name] = copy.copy(stmt.type)
                else:
                    self.locals[stmt.name] = copy.copy(init_type)
                self._note_local_ref(stmt.name, root)
            elif stmt.type:
                self.locals[stmt.name] = stmt.type
            else:
                self._error(f"variable '{stmt.name}' needs type annotation or initializer", stmt.span)

        elif isinstance(stmt, rast.LetStmt):
            if stmt.value:
                init_type = self._infer_into(stmt.value, stmt.type)
                root = self._referent(stmt.value)
                if stmt.type:
                    if not self._value_fits(stmt.value, init_type, stmt.type):
                        self._error(f"cannot initialize {self._type_str(stmt.type)} "
                                  f"with {self._type_str(init_type)}", stmt.span)
                    self.locals[stmt.name] = self._as_let(stmt.type)
                else:
                    self.locals[stmt.name] = self._as_let(init_type)
                self._note_local_ref(stmt.name, root)
            elif stmt.type:
                self.locals[stmt.name] = self._as_let(stmt.type)
            else:
                self._error(f"let binding '{stmt.name}' needs type annotation or initializer", stmt.span)

        elif isinstance(stmt, rast.LetTupleStmt):
            value_type = self._infer_type(stmt.value)
            elements = value_type.elements if isinstance(value_type, rast.TupleType) else []
            for i, name in enumerate(stmt.names):
                self.locals[name] = (elements[i] if i < len(elements)
                                     else rast.NamedType(stmt.span, 'unknown', []))

        elif isinstance(stmt, rast.UnsafeBlock):
            self._push_scope()
            self._check_block(stmt.body)
            self._pop_scope()

        elif isinstance(stmt, rast.ExprStmt):
            self._infer_type(stmt.expr)

        elif isinstance(stmt, rast.ReturnStmt):
            if stmt.value:
                ret_type = self._infer_into(stmt.value, self._ret_slot())
                if self.current_fn and self.current_fn.ret_type:
                    if not self._value_fits(stmt.value, ret_type, self.current_fn.ret_type):
                        self._error(f"return type {self._type_str(ret_type)} doesn't match "
                                  f"expected {self._type_str(self.current_fn.ret_type)}", stmt.span)

        elif isinstance(stmt, rast.AssignStmt):
            target_type = self._infer_type(stmt.target)
            self._check_write(stmt.target)
            value_type = self._infer_into(stmt.value, target_type)
            if not self._value_fits(stmt.value, value_type, target_type):
                self._error(f"cannot assign {self._type_str(value_type)} "
                          f"to {self._type_str(target_type)}", stmt.span)

        elif isinstance(stmt, rast.WhileStmt):
            cond_type = self._infer_type(stmt.cond)
            if not self._is_bool_or_opaque(cond_type):
                self._error(f"while condition must be bool, got {self._type_str(cond_type)}",
                          stmt.cond.span)
            self._push_scope()
            self._loop_depth += 1
            self._check_block(stmt.body)
            self._loop_depth -= 1
            self._pop_scope()

        elif isinstance(stmt, rast.ForStmt):
            self._push_scope()
            # Infer iterator element type
            iter_type = self._infer_type(stmt.iter)
            elem_type = self._get_iterator_element_type(iter_type)
            self.locals[stmt.var] = elem_type
            self._loop_depth += 1
            self._check_block(stmt.body)
            self._loop_depth -= 1
            self._pop_scope()

        elif isinstance(stmt, rast.AssertStmt):
            cond_type = self._infer_type(stmt.condition)
            if not self._is_bool_or_opaque(cond_type):
                self._error(f"assert condition must be bool, got {self._type_str(cond_type)}",
                          stmt.condition.span)

    def _infer_type(self, expr: rast.Expr) -> rast.Type:
        """Infer the type of an expression."""
        if isinstance(expr, rast.IntLit):
            # Integer literals default to i64
            return rast.NamedType(expr.span, 'i64', [])

        elif isinstance(expr, rast.FloatLit):
            return FloatLitType(expr.span, 'f64', [])

        elif isinstance(expr, rast.BoolLit):
            return rast.NamedType(expr.span, 'bool', [])

        elif isinstance(expr, rast.CharLit):
            return rast.NamedType(expr.span, 'u8', [])

        elif isinstance(expr, rast.InterpString):
            for part in expr.exprs:
                self._infer_type(part)
            return rast.NamedType(expr.span, 'StrView', [])

        elif isinstance(expr, rast.StringLit):
            # Bare string literals produce StrView (AGAST #98, Wave 3).
            # `"hello"` is a zero-copy view { ptr, len }. Use `c"..."` for
            # null-terminated *u8, and call a `String` constructor explicitly
            # for a heap-owned String.
            return rast.NamedType(expr.span, 'StrView', [])

        elif isinstance(expr, rast.CStringLit):
            # C-string literals: c"hello" -> *u8 (null-terminated)
            return rast.PtrType(expr.span, rast.NamedType(expr.span, 'u8', []), mutable=False)

        # Note: SpanStringLit (s"...") was removed in AGAST #98 — bare
        # StringLit now produces StrView which is layout-compatible.

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
                # A type as a receiver: `Errno.Fault`, `Point.new()`
                if expr.name in self.enums or expr.name in self.structs:
                    return rast.NamedType(expr.span, expr.name, [])
                if expr.name in self.type_aliases:
                    return self.type_aliases[expr.name]
                if expr.name in self.current_type_params:
                    return rast.NamedType(expr.span, expr.name, [])
                # A function as a value
                sig = self.functions.get(expr.name)
                if sig is not None:
                    return rast.FnType(expr.span, [ty for _, ty in sig.params],
                                       sig.ret_type)
                if expr.name == 'nil':
                    return rast.NamedType(expr.span, 'null', [])
                if expr.name == 'pass' or expr.name in BUILTIN_VARIANTS \
                        or expr.name in self.module_names:
                    return rast.NamedType(expr.span, 'unknown', [])
                self._error(f"undefined variable: {expr.name}", expr.span)
                return rast.NamedType(expr.span, 'unknown', [])
            return ty

        elif isinstance(expr, rast.Grouped):
            return self._infer_type(expr.expr)

        elif isinstance(expr, rast.HeapExpr):
            return rast.PtrType(expr.span, self._infer_type(expr.expr), mutable=True)

        elif isinstance(expr, (rast.BreakExpr, rast.ContinueExpr)):
            return rast.NamedType(expr.span, 'unknown', [])  # the never type

        elif isinstance(expr, rast.ReturnExpr):
            if expr.value:
                self._infer_into(expr.value, self._ret_slot())
            return rast.NamedType(expr.span, 'unknown', [])  # the never type

        elif isinstance(expr, rast.AssignExpr):
            target_type = self._infer_type(expr.target)
            self._check_write(expr.target)
            return self._infer_into(expr.value, target_type)

        elif isinstance(expr, (rast.QualifiedIdent, rast.TypeExpr)):
            return rast.NamedType(expr.span, 'unknown', [])

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
            slot = self._take_tail_slot()
            self._push_scope()
            for stmt in expr.stmts:
                self._check_stmt(stmt)
            result = rast.NamedType(expr.span, 'void', [])
            if expr.expr:
                result = self._infer_into(expr.expr, slot)
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
            self._check_array_slot(expr.expr, self._infer_type(expr.expr), expr.target)
            if self._is_bool_type(expr.target):
                self._error(bool_rules.AS_BOOL_REMOVED, expr.span)
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
            self._push_scope()
            for p in expr.params:
                if p.type:
                    param_types.append(p.type)
                else:
                    param_types.append(rast.NamedType(expr.span, 'unknown', []))
                self.locals[p.name] = param_types[-1]
            body_type = self._infer_type(expr.body)
            self._pop_scope()
            return rast.FnType(expr.span, param_types, body_type)

        elif isinstance(expr, rast.Lambda):
            # Lambda is an older form of closure with explicit param types
            param_types = [p.type for p in expr.params]
            self._push_scope()
            for p in expr.params:
                self.locals[p.name] = p.type
            body_type = self._infer_type(expr.body)
            self._pop_scope()
            return rast.FnType(expr.span, param_types, body_type if body_type else rast.NamedType(expr.span, 'unknown', []))

        else:
            self._error(f"cannot infer type of {type(expr).__name__}", getattr(expr, 'span', None))
            return rast.NamedType(expr.span if hasattr(expr, 'span') else None, 'unknown', [])

    def _check_binop(self, expr: rast.BinOp) -> rast.Type:
        """Type check binary operation and return result type."""
        left_type = self._infer_type(expr.left)
        right_type = self._infer_type(expr.right)

        # Comparison operators return bool
        if expr.op in bool_rules.COMPARISONS:
            if not self._types_compatible(left_type, right_type):
                self._error(f"cannot compare {self._type_str(left_type)} "
                          f"with {self._type_str(right_type)}", expr.span)
            return rast.NamedType(expr.span, 'bool', [])

        # Logical operators require bool, return bool
        if expr.op in bool_rules.LOGICAL:
            if not self._is_bool_or_opaque(left_type):
                self._error(f"logical operator requires bool, got {self._type_str(left_type)}",
                          expr.left.span)
            if not self._is_bool_or_opaque(right_type):
                self._error(f"logical operator requires bool, got {self._type_str(right_type)}",
                          expr.right.span)
            return rast.NamedType(expr.span, 'bool', [])

        # Arithmetic operators
        if expr.op in ('+', '-', '*', '/', '%'):
            # Pointer/reference arithmetic: ptr + int or ptr - int
            if isinstance(left_type, (rast.PtrType, rast.RefType)) and self._is_int_or_opaque(right_type):
                # Return as pointer type for arithmetic result
                if isinstance(left_type, rast.RefType):
                    return rast.PtrType(expr.span, left_type.inner, mutable=left_type.mutable)
                return left_type
            if isinstance(right_type, (rast.PtrType, rast.RefType)) and self._is_int_or_opaque(left_type):
                if isinstance(right_type, rast.RefType):
                    return rast.PtrType(expr.span, right_type.inner, mutable=right_type.mutable)
                return right_type

            # Numeric arithmetic
            if not self._is_numeric_or_opaque(left_type):
                self._error(f"arithmetic operator requires numeric type, "
                          f"got {self._type_str(left_type)}", expr.left.span)
            if not self._is_numeric_or_opaque(right_type):
                self._error(f"arithmetic operator requires numeric type, "
                          f"got {self._type_str(right_type)}", expr.right.span)
            # Return the "wider" type (simplified: just return left type)
            return self._promote_numeric_types(left_type, right_type)

        # Bitwise operators
        if expr.op in ('&', '|', '^', '<<', '>>'):
            if not self._is_int_or_opaque(left_type):
                self._error(f"bitwise operator requires integer, got {self._type_str(left_type)}",
                          expr.left.span)
            if not self._is_int_or_opaque(right_type):
                self._error(f"bitwise operator requires integer, got {self._type_str(right_type)}",
                          expr.right.span)
            return left_type

        return left_type

    def _check_unaryop(self, expr: rast.UnaryOp) -> rast.Type:
        """Type check unary operation."""
        operand_type = self._infer_type(expr.operand)

        if expr.op == '-':
            if not self._is_numeric_or_opaque(operand_type):
                self._error(f"negation requires numeric type, got {self._type_str(operand_type)}",
                          expr.operand.span)
            return operand_type

        elif expr.op == '~':
            if not self._is_int_or_opaque(operand_type):
                self._error(f"bitwise operator requires integer, got {self._type_str(operand_type)}",
                          expr.operand.span)
            return operand_type

        elif expr.op in ('!', 'not'):
            if not self._is_bool_or_opaque(operand_type):
                self._error(f"logical not requires bool, got {self._type_str(operand_type)}",
                          expr.operand.span)
            return rast.NamedType(expr.span, 'bool', [])

        elif expr.op in ('&', '@'):
            # Immutable borrow: @ in RERITZ, & for legacy compatibility
            self._forget_local_ref(expr.operand)
            return rast.RefType(expr.span, operand_type, mutable=False)

        elif expr.op in ('&mut', '@&'):
            # Mutable borrow: @& in RERITZ, &mut for legacy compatibility
            self._check_borrow(expr)
            self._forget_local_ref(expr.operand)
            return rast.RefType(expr.span, operand_type, mutable=True)

        elif expr.op == '*':
            # Dereference
            if isinstance(expr.operand, rast.Ident) and expr.operand.name in self.lent_locals \
                    and not isinstance(self._resolve_alias(operand_type),
                                       (rast.PtrType, rast.RefType)):
                return operand_type
            if isinstance(operand_type, rast.PtrType):
                return operand_type.inner
            elif isinstance(operand_type, rast.RefType):
                return operand_type.inner
            elif self._is_opaque(operand_type):
                return rast.NamedType(expr.span, 'unknown', [])
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

            # Volatile / atomic memory builtins (LANGUAGE_SPEC §18.4-§18.5,
            # AGAST #1879): the value-returning ones return the pointee type.
            if fn_name in ('volatile_load', 'volatile_store', 'atomic_load',
                           'atomic_store', 'atomic_xchg', 'atomic_cmpxchg',
                           'atomic_fetch_add', 'atomic_fetch_sub', 'atomic_fetch_and',
                           'atomic_fetch_or', 'atomic_fetch_xor', 'fence'):
                arg_types = [self._infer_type(arg) for arg in expr.args]
                if fn_name in ('volatile_store', 'atomic_store', 'fence') or not arg_types:
                    return rast.NamedType(expr.span, 'void', [])
                ptr_ty = arg_types[0]
                if isinstance(ptr_ty, (rast.PtrType, rast.RefType)):
                    return ptr_ty.inner
                return rast.NamedType(expr.span, 'unknown', [])

            # print(str) / eprint(str) -> void (eprint: AGAST #1641);
            # format_into(sink, str) -> void (AGAST #1824)
            if fn_name in ('print', 'eprint', 'format_into'):
                for arg in expr.args:
                    self._infer_type(arg)
                return rast.NamedType(expr.span, 'void', [])

            # Instructions the emitter lowers by name
            if fn_name in INTRINSICS or fn_name in (
                    'simd_load', 'simd_loadu', 'simd_store', 'simd_storeu',
                    'simd_shuffle', 'simd_extract', 'simd_insert', 'simd_sad',
                    'simd_clmul'):
                for arg in expr.args:
                    self._infer_type(arg)
                return rast.NamedType(expr.span, 'unknown', [])

            # A call through a local or global function pointer
            if fn_name in self.locals or fn_name in self.globals:
                callee = self._lookup_var(fn_name)
                slots = callee.params if isinstance(callee, rast.FnType) else []
                for i, arg in enumerate(expr.args):
                    self._infer_into(arg, slots[i] if i < len(slots) else None)
                if isinstance(callee, rast.FnType):
                    return callee.ret or rast.NamedType(expr.span, 'void', [])
                return rast.NamedType(expr.span, 'unknown', [])

            # Check if it's an enum variant constructor
            if fn_name in self.variant_to_enum:
                enum_name = self.variant_to_enum[fn_name]
                # A bare `V(x)` of a name several enums declare says nothing
                # about which: _check_parts knows when a slot does.
                only = self.variant_owners[fn_name] == 1 and '$' not in enum_name
                self._check_payload(expr.args, enum_name if only else None, fn_name)
                return rast.NamedType(expr.span, enum_name, [])

            # Look up function
            fn_sig = self.functions.get(fn_name)
            if fn_sig is None and (fn_name in SYSCALL_BUILTINS
                                   or fn_name in BUILTIN_VARIANTS):
                for arg in expr.args:
                    self._infer_type(arg)
                return rast.NamedType(expr.span, 'unknown', [])
            if fn_sig is None:
                self._error(f"undefined function: {fn_name}", expr.func.span)
                return rast.NamedType(expr.span, 'unknown', [])

            self._callees[id(expr)] = (fn_sig, 0)

            # Check argument count
            if len(expr.args) != len(fn_sig.params):
                self._error(f"function '{fn_name}' expects {len(fn_sig.params)} arguments, "
                          f"got {len(expr.args)}", expr.span)
            else:
                # Check argument types
                for i, (arg, (param_name, param_type)) in enumerate(zip(expr.args, fn_sig.params)):
                    if i in fn_sig.lent:
                        # `name:& T` borrows a `T` place, and takes what
                        # already points at one (§13.4).
                        arg_type = self._infer_type(arg)
                        self._check_addr_into_mut(arg)
                        self._check_lent_referent(arg, arg_type, param_type)
                        self._forget_local_ref(arg)
                        if isinstance(self._resolve_alias(arg_type),
                                      (rast.PtrType, rast.RefType)):
                            continue
                    else:
                        self._arg_depth += 1
                        arg_type = self._infer_into(arg, param_type)
                        self._arg_depth -= 1
                    if not self._value_fits(arg, arg_type, param_type):
                        self._error(f"argument {i+1} ('{param_name}'): expected {self._type_str(param_type)}, "
                                  f"got {self._type_str(arg_type)}", arg.span)

            if fn_sig.is_async:
                # The call makes a `<fn>_Future`; only `.await` gives ret_type.
                return rast.NamedType(expr.span, 'unknown', [])
            return fn_sig.ret_type or rast.NamedType(expr.span, 'void', [])

        else:
            # Indirect call - just infer args
            for arg in expr.args:
                self._infer_type(arg)
            return rast.NamedType(expr.span, 'unknown', [])

    def _check_method_call(self, expr: rast.MethodCall) -> rast.Type:
        """Type check method call."""
        # `token.next(x)`: a function reached through its module
        if self._is_module_ref(expr.expr):
            for arg in expr.args:
                self._infer_type(arg)
            sig = self.functions.get(expr.method)
            if sig is not None:
                return sig.ret_type or rast.NamedType(expr.span, 'void', [])
            return rast.NamedType(expr.span, 'unknown', [])

        receiver_type = self._infer_type(expr.expr)

        # `Color.Green(1)`: a variant constructed through its enum
        if isinstance(expr.expr, rast.Ident) and expr.expr.name in self.enums:
            enum = self.enums[expr.expr.name]
            if any(v.name == expr.method for v in enum.variants):
                self._check_payload(expr.args, enum.name, expr.method)
                return rast.NamedType(expr.span, enum.name, [])

        # Primitive and built-in-generic receivers have emitter-provided
        # methods (`x.popcnt()`, `r.unwrap()`) that no source file declares.
        receiver = self._strip_indirection(receiver_type)
        if self._is_opaque(receiver) or (isinstance(receiver, rast.NamedType) and (
                receiver.name in self.NUMERIC_TYPES
                or receiver.name in BUILTIN_GENERICS
                or receiver.name in ('bool', 'StrView'))):
            for arg in expr.args:
                self._infer_type(arg)
            return rast.NamedType(expr.span, 'unknown', [])
        type_name = self._get_type_name(receiver)

        # Look up method - try several name patterns
        fn_sig = None
        tried_names = []
        own_method = False

        # Try exact match first
        mangled = f"{type_name}_{expr.method}"
        tried_names.append(mangled)
        fn_sig = self.functions.get(mangled)
        own_method = fn_sig is not None

        if fn_sig is None:
            # For generic types like Vec<u8>, try base name (Vec_method)
            base_name = type_name.split('<')[0].split('$')[0]
            if base_name != type_name:
                mangled = f"{base_name}_{expr.method}"
                tried_names.append(mangled)
                fn_sig = self.functions.get(mangled)
                own_method = fn_sig is not None

        # What the emitter dispatches to: a looser name below doesn't reach it.
        receiver_sig = fn_sig if own_method else self.functions.get(
            find_ufcs_function(self.functions, type_name, expr.method))
        if receiver_sig is not None:
            self._check_receiver(expr, receiver_sig)

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

        # Check args (receiver is already the first implicit arg). A method
        # found by a looser name may take the receiver as an argument: its
        # params don't line up, so the slots go unjudged.
        skip = 1 if fn_sig.params and fn_sig.params[0][0] == 'self' else 0
        self._callees[id(expr)] = (fn_sig, skip)
        for i, arg in enumerate(expr.args):
            at = i + skip
            lent = at in fn_sig.lent or at >= len(fn_sig.params) or not own_method
            self._arg_depth += 1
            self._infer_into(arg, None if lent else fn_sig.params[at][1])
            self._arg_depth -= 1
            if at in fn_sig.lent:
                self._forget_local_ref(arg)
            if at in fn_sig.lent and own_method:
                self._check_addr_into_mut(arg)
                self._check_lent_referent(arg, self._quiet_type(arg), fn_sig.params[at][1])

        return fn_sig.ret_type or rast.NamedType(expr.span, 'void', [])

    def _check_field_access(self, expr: rast.Field) -> rast.Type:
        """Type check field access."""
        # `token.KIND`: a name reached through its module
        if self._is_module_ref(expr.expr):
            ty = self._lookup_var(expr.field)
            if ty is None and expr.field in self.variant_to_enum:
                ty = rast.NamedType(expr.span, self.variant_to_enum[expr.field], [])
            return ty or rast.NamedType(expr.span, 'unknown', [])

        # `RepoError.NotFound` is a `RepoError`, though `ServiceError` has a
        # variant `RepoError(RepoError)` and a `NotFound` too (AGAST #2534):
        # a bare name looked up as a value finds that variant first. As
        # `Color.Green(1)` does in _check_method_call.
        if isinstance(expr.expr, rast.Ident) and expr.expr.name in self.enums:
            enum = self.enums[expr.expr.name]
            if any(v.name == expr.field for v in enum.variants):
                return rast.NamedType(expr.span, enum.name, [])

        base_type = self._infer_type(expr.expr)

        # Unwrap pointers/refs for field access
        inner_type = self._strip_indirection(base_type)
        if self._is_opaque(inner_type) or (
                isinstance(inner_type, rast.NamedType)
                and inner_type.name in BUILTIN_GENERICS):
            return rast.NamedType(expr.span, 'unknown', [])

        # `Errno.Fault`: a variant named through its enum
        if isinstance(inner_type, rast.NamedType) and inner_type.name in self.enums:
            if any(v.name == expr.field for v in self.enums[inner_type.name].variants):
                return inner_type

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

        # `p[1..3]` is a slice of it, not an element.
        if isinstance(expr.index, rast.Range):
            return rast.NamedType(expr.span, 'unknown', [])

        # Index must be integer
        if not self._is_int_or_opaque(index_type):
            self._error(f"index must be integer, got {self._type_str(index_type)}",
                      expr.index.span)

        # Get element type
        if isinstance(base_type, rast.ArrayType):
            return base_type.inner
        elif isinstance(base_type, (rast.PtrType, rast.RefType)):
            return self._element_behind(base_type)
        elif isinstance(base_type, rast.NamedType):
            # A Vec or Span gives its element (#2443: `(*p)[i].m()` and
            # `v[i].m()` reach M's receiver check). Anything else could be a
            # String etc - allow indexing. In full implementation, would look
            # up Index trait
            named = self._resolve_alias(base_type)
            held = self._mangled_buffer_element(named.name) if isinstance(named, rast.NamedType) else None
            if held is not None:
                return held
            return rast.NamedType(expr.span, 'unknown', [])
        else:
            self._error(f"cannot index into {self._type_str(base_type)}", expr.span)
            return rast.NamedType(expr.span, 'unknown', [])

    def _element_behind(self, pointer: rast.Type) -> rast.Type:
        """What `p[i]` is for `p: pointer`. `[]` sees through to an indexable T
        (AGAST #2440, LARB R9); a `*T` over anything else is a raw buffer of T.
        The emitter refuses a reference to anything else (_index_through)."""
        inner = self._resolve_alias(pointer.inner)
        if isinstance(inner, rast.ArrayType):
            # `*[N]T` too since #2330: element i at stride T, in every position.
            return inner.inner
        if isinstance(inner, rast.NamedType):
            if inner.name == 'String':
                return rast.NamedType(inner.span, 'u8', [])
            if inner.name in ('Vec', 'Span') and inner.args:
                return inner.args[0]
            held = self._mangled_buffer_element(inner.name)
            if held is not None:
                return held
        return pointer.inner

    def _mangled_buffer_element(self, name: str) -> Optional[rast.Type]:
        """T for a monomorphized `Vec$T` or `Span$T`: what its buffer field
        (`data`, `ptr`) points at. Without it `p[i]` on a `@Vec$M` typed as the
        Vec, so `p[i].m()` missed M's methods and their receiver check (#2443)."""
        buffer = {'Vec': 'data', 'Span': 'ptr'}.get(name.split('$', 1)[0])
        info = self.structs.get(name) if '$' in name else None
        if buffer is None or info is None:
            return None
        for field_name, field_type in info.fields:
            if field_name == buffer and isinstance(field_type, rast.PtrType):
                return field_type.inner
        return None

    def _check_if(self, expr: rast.If) -> rast.Type:
        """Type check if expression."""
        slot = self._take_tail_slot()
        cond_type = self._infer_type(expr.cond)
        if not self._is_bool_or_opaque(cond_type):
            self._error(f"if condition must be bool, got {self._type_str(cond_type)}",
                      expr.cond.span)

        self._push_scope()
        then_type = rast.NamedType(expr.span, 'void', [])
        for stmt in expr.then_block.stmts:
            self._check_stmt(stmt)
        if expr.then_block.expr:
            then_type = self._infer_into(expr.then_block.expr, slot)
        self._pop_scope()

        if expr.else_block:
            self._push_scope()
            else_type = rast.NamedType(expr.span, 'void', [])
            for stmt in expr.else_block.stmts:
                self._check_stmt(stmt)
            if expr.else_block.expr:
                else_type = self._infer_into(expr.else_block.expr, slot)
            self._pop_scope()

            # Both branches should have same type
            if self._value_fits(expr.else_block.expr, else_type, then_type):
                return then_type
            if self._value_fits(expr.then_block.expr, then_type, else_type):
                return else_type
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
                value_type = self._infer_into(value, expected_fields[name])
                if not self._value_fits(value, value_type, expected_fields[name]):
                    self._error(f"field '{name}': expected {self._type_str(expected_fields[name])}, "
                              f"got {self._type_str(value_type)}", value.span)

        return rast.NamedType(expr.span, expr.name, list(expr.type_args) if expr.type_args else [])

    def _check_match(self, expr: rast.Match) -> rast.Type:
        """Type check match expression."""
        slot = self._take_tail_slot()
        match_type = self._infer_type(expr.expr)

        result_type = None
        for arm in expr.arms:
            self._push_scope()
            self._check_pattern(arm.pattern, match_type)
            if arm.guard:
                guard_type = self._infer_type(arm.guard)
                if not self._is_bool_or_opaque(guard_type):
                    self._error(f"match guard must be bool", arm.guard.span)

            arm_type = self._infer_into(arm.body, slot)
            if result_type is None:
                result_type, result_body = arm_type, arm.body
            elif self._value_fits(arm.body, arm_type, result_type):
                pass
            elif self._value_fits(result_body, result_type, arm_type):
                result_type, result_body = arm_type, arm.body
            else:
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
            self.locals[pattern.name] = copy.copy(expected_type)
        elif isinstance(pattern, rast.VariantPattern):
            # Look up variant - use qualifier if provided, otherwise fall back to lookup
            enum_name = None
            if pattern.qualifier:
                # Qualified pattern: Type.Variant - use the qualifier as enum name
                enum_name = pattern.qualifier
            elif pattern.name in self.variant_to_enum:
                # Unqualified pattern: look up which enum this variant belongs to
                enum_name = self.variant_to_enum[pattern.name]
                # Every instance of Option has a `Some`, and that's the last
                # one registered: it says nothing about this scrutinee's.
                if '$' in enum_name and self._type_str(
                        self._strip_indirection(expected_type)) != enum_name:
                    enum_name = None

            if enum_name:
                enum_info = self.enums.get(enum_name)
                if enum_info:
                    for variant in enum_info.variants:
                        if variant.name == pattern.name:
                            # Bind sub-patterns to variant field types
                            for sub_pat, field_type in zip(pattern.fields, variant.fields):
                                self._check_pattern(sub_pat, field_type)
                            break
                    return
            # An emitter-instantiated variant (`Err(e)`): payload type untracked
            for sub_pat in pattern.fields:
                self._check_pattern(sub_pat, rast.NamedType(pattern.span, 'unknown', []))
        elif isinstance(pattern, rast.StructPattern):
            struct_info = self.structs.get(pattern.name)
            if struct_info:
                field_types = {name: ty for name, ty in struct_info.fields}
                for field_name, sub_pat in pattern.fields:
                    if field_name in field_types:
                        self._check_pattern(sub_pat, field_types[field_name])

    # By-value slots (LANGUAGE_SPEC §13.2, AGAST #2336)

    def _ret_slot(self) -> Optional[rast.Type]:
        return self.current_fn.ret_type if self.current_fn else None

    def _take_tail_slot(self) -> Optional[rast.Type]:
        slot, self._tail_slot = self._tail_slot, None
        return slot

    def _infer_into(self, expr: rast.Expr, slot: Optional[rast.Type]) -> rast.Type:
        """The type of `expr`, whose value lands in a `slot`-typed place.
        `if`, `match` and block tails land there too, each in its own scope,
        as do the parts of a literal the slot types."""
        if isinstance(expr, rast.Grouped):
            return self._infer_into(expr.expr, slot)
        if isinstance(expr, (rast.If, rast.Match, rast.Block)):
            self._tail_slot = slot
            ty = self._infer_type(expr)
            self._tail_slot = None
            return ty
        ty = self._infer_type(expr)
        self._check_ref_slot(expr, ty, slot)
        self._check_array_slot(expr, ty, slot)
        self._check_parts(expr, slot)
        if slot is not None and slot is self._ret_slot():
            self._check_return(expr)
        self._check_other_referent(expr, ty, slot)
        return ty

    def _check_parts(self, expr: rast.Expr, slot: Optional[rast.Type]) -> None:
        """The elements of a literal or the payload of a variant landing in
        `slot`, which says what each part is."""
        slot = self._resolve_alias(slot) if slot is not None else None
        if isinstance(expr, rast.ArrayLit) and isinstance(slot, rast.ArrayType):
            for element in expr.elements:
                self._infer_into(element, slot.inner)
        elif isinstance(expr, rast.ArrayFill) and isinstance(slot, rast.ArrayType):
            self._infer_into(expr.value, slot.inner)
        elif isinstance(expr, rast.TupleLit) and isinstance(slot, rast.TupleType):
            for element, part in zip(expr.elements, slot.elements):
                self._infer_into(element, part)
        elif isinstance(slot, rast.NamedType) and slot.name in self.enums:
            if isinstance(expr, rast.Call) and isinstance(expr.func, rast.Ident):
                self._check_payload(expr.args, slot.name, expr.func.name)
            elif isinstance(expr, rast.MethodCall):
                self._check_payload(expr.args, slot.name, expr.method)
        elif isinstance(slot, rast.NamedType) and isinstance(expr, rast.Call) \
                and isinstance(expr.func, rast.Ident) and len(expr.args) == 1:
            # The emitter's own Option and Result: the slot names the payload.
            part = {'Some': 0, 'Ok': 0, 'Err': 1}.get(expr.func.name)
            if slot.name in ('Option', 'Result') and part is not None and part < len(slot.args):
                self._infer_into(expr.args[0], slot.args[part])

    def _check_payload(self, args: List[rast.Expr], enum_name: Optional[str],
                       variant: str) -> None:
        """The arguments of `enum_name`'s `variant`, or of an unknown enum's."""
        enum = self.enums.get(enum_name) if enum_name else None
        found = next((v for v in enum.variants if v.name == variant), None) if enum else None
        fields = found.fields if found is not None else []
        for i, arg in enumerate(args):
            self._infer_into(arg, fields[i] if i < len(fields) else None)

    def _check_ref_slot(self, expr: rast.Expr, actual: rast.Type,
                        slot: Optional[rast.Type]) -> None:
        """An `@T`, `@&T` or `*T` doesn't fit a by-value `T` slot, and a `T`
        doesn't fit a reference to one. `@a` of an array fits a Span; `a` doesn't."""
        if slot is None or actual is None or id(expr) in self._slot_reported:
            return
        actual = self._resolve_alias(actual)
        slot = self._resolve_alias(slot)
        if isinstance(slot, rast.RefType) and slot.mutable:
            self._check_addr_into_mut(expr)
            self._check_shared_into_mut(expr, actual)
        if isinstance(slot, (rast.PtrType, rast.RefType)):
            self._check_value_into_ref(expr, actual, slot)
            return
        if self._is_span(slot) and isinstance(actual, rast.ArrayType):
            self._report_value_into_ref(expr, slot)
            return
        if not isinstance(actual, (rast.PtrType, rast.RefType)) or self._is_opaque(slot):
            return
        if self._type_str(self._resolve_alias(actual.inner)) != self._type_str(slot):
            return
        self._slot_reported.add(id(expr))
        addr = isinstance(expr, rast.UnaryOp) and expr.op in ('&', '@', '&mut', '@&')
        self._slot_error(ref_rules.ADDR_INTO_VALUE if addr else ref_rules.REF_INTO_VALUE,
                         expr.span)

    def _check_value_into_ref(self, expr: rast.Expr, actual: rast.Type,
                              slot: rast.Type) -> None:
        """A `T` doesn't fit an `@T`, `@&T` or `*T`: a reference is written.

        Nothing but a reference fits an `@T` or `@&T`, and nothing but a pointer
        a `*T` for a `:&` param, which is a `T` too. A plain integer into `*U`
        of another `U` is a pointer as an integer, a different question.
        """
        inner = self._resolve_alias(slot.inner)
        if self._is_opaque(inner) or self._is_opaque(actual):
            return
        same = self._type_str(inner) == self._type_str(actual)
        pointer = isinstance(actual, (rast.PtrType, rast.RefType))
        if pointer and isinstance(slot, rast.RefType) and isinstance(inner, rast.PtrType):
            held = self._resolve_alias(actual.inner)
            if isinstance(held, rast.PtrType) and self._type_str(held) != self._type_str(inner):
                self._slot_reported.add(id(expr))
                self._slot_error(ref_rules.REF_TO_OTHER_POINTER, expr.span)
                return
        if not same and (pointer or self._is_null(actual)):
            return
        lent = (isinstance(expr, rast.Ident) and expr.name in self.lent_locals
                and self._lookup_var(expr.name) is self.lent_locals[expr.name])
        if same or lent or isinstance(slot, rast.RefType):
            self._report_value_into_ref(expr, slot)

    def _check_other_referent(self, expr: rast.Expr, actual: Optional[rast.Type],
                              slot: Optional[rast.Type]) -> None:
        """`@x` or `@&x` lands in an `@U`, `@&U` or `*U` of another `U`: the
        reference would be reinterpreted. Exactly the same type, not the same
        width (Aaron's ruling on AGAST #2368). After the return check, as
        ritz1's ref_into does, so a reference to a local says that first.
        A `*T` value into a `*U` isn't judged here: that's still open."""
        if slot is None or actual is None or not self._is_written_ref(expr):
            return
        actual = self._resolve_alias(actual)
        slot = self._resolve_alias(slot)
        if not isinstance(slot, (rast.PtrType, rast.RefType)) \
                or not isinstance(actual, (rast.PtrType, rast.RefType)):
            return
        # A struct for another struct at a call is #1948's "argument N of `f`
        # has the wrong type", which ritz1 says too; this doesn't pre-empt it.
        if self._arg_depth and self._is_struct(actual.inner) and self._is_struct(slot.inner):
            return
        # `@&h` of a `*C` into `@&*D` was REF_TO_OTHER_POINTER, said first.
        if self._other_referent(actual.inner, slot.inner):
            self._report_once(expr, ref_rules.REF_TO_OTHER_TYPE)

    def _check_lent_referent(self, arg: rast.Expr, actual: Optional[rast.Type],
                             referent: rast.Type) -> None:
        """`@x` or `@&x` goes to a `name:& T` param, whose referent is `referent`:
        of another type, it would be reinterpreted (#2367, #2368). A bare place
        is the emitter's "argument N has the wrong type"."""
        if actual is None or not self._is_written_ref(arg):
            return
        actual = self._resolve_alias(actual)
        if isinstance(actual, (rast.PtrType, rast.RefType)) \
                and self._other_referent(actual.inner, referent):
            self._report_once(arg, ref_rules.REF_TO_OTHER_TYPE)

    def _is_struct(self, ty: rast.Type) -> bool:
        ty = self._resolve_alias(ty)
        return isinstance(ty, rast.NamedType) and self._referent_key(ty) is not None \
            and (ty.args != [] or ty.name in self.structs or '$' in ty.name)

    def _other_referent(self, held: rast.Type, inner: rast.Type) -> bool:
        """`held` is known not to be `inner`: exactly, not by width. What the
        checker can't name stays unjudged."""
        a, b = self._referent_key(held), self._referent_key(inner)
        return a is not None and b is not None and a != b

    def _referent_key(self, ty: rast.Type) -> Optional[str]:
        """`ty` spelled one way, whatever its aliases, with a generic struct as
        monomorphisation names it (`Box<i32>` is `Box$i32`). A pointer inside is
        `*` whatever its kind: `@T` fits `*T`, so `@@C` fits `**C`. None if any
        part of it is opaque or a type this doesn't spell."""
        ty = self._resolve_alias(ty)
        if ty is None or self._is_opaque(ty):
            return None
        if isinstance(ty, (rast.PtrType, rast.RefType)):
            inner = self._referent_key(ty.inner)
            return None if inner is None else f"*{inner}"
        if isinstance(ty, rast.ArrayType):
            inner = self._referent_key(ty.inner)
            size = ty.size.value if isinstance(ty.size, rast.IntLit) else ty.size
            if inner is None or not isinstance(size, int):
                return None
            return f"[{size}]{inner}"
        if isinstance(ty, rast.TupleType):
            parts = [self._referent_key(part) for part in ty.elements]
            return None if None in parts else f"({', '.join(parts)})"
        if not isinstance(ty, rast.NamedType):
            return None
        if ty.args:
            if any(self._referent_key(arg) is None for arg in ty.args):
                return None
            return mangle_generic_name(ty.name, ty.args)
        return ty.name

    @staticmethod
    def _is_written_ref(expr: rast.Expr) -> bool:
        """`@x` or `@&x`, written where the slot is."""
        while isinstance(expr, rast.Grouped):
            expr = expr.expr
        return isinstance(expr, rast.UnaryOp) and expr.op in ('&', '@', '&mut', '@&')

    def _report_value_into_ref(self, expr: rast.Expr, slot: rast.Type) -> None:
        self._slot_reported.add(id(expr))
        mutable = isinstance(slot, rast.RefType) and slot.mutable
        self._slot_error(ref_rules.VALUE_INTO_MUT_REF if mutable
                         else ref_rules.VALUE_INTO_SHARED_REF, expr.span)

    # `@T` is read-only (LANGUAGE_SPEC §3.2, §13.3, AGAST #2338)

    def _quiet_type(self, expr: rast.Expr) -> rast.Type:
        """The type of `expr`, which has already had its say."""
        mark = len(self.errors)
        ty = self._infer_type(expr)
        del self.errors[mark:]
        return self._resolve_alias(ty)

    def _check_write(self, target: rast.Expr) -> None:
        """`target` is written."""
        self._forget_local_ref(target)
        if self._behind_shared(target):
            self._report_once(target, ref_rules.WRITE_THROUGH_SHARED)

    def _report_once(self, expr: rast.Expr, message: str) -> None:
        if id(expr) not in self._slot_reported:
            self._slot_reported.add(id(expr))
            self._slot_error(message, expr.span)

    def _behind_shared(self, target: rast.Expr) -> bool:
        """Walk the place `target` from itself to its root: an `@T` on the way
        means it's read-only, whatever is behind it, and a `*T` ends the walk,
        since what it points at is the pointer's business. So is anything the
        checker can't type, which stays unjudged."""
        place = target
        while True:
            if isinstance(place, rast.Grouped):
                place = place.expr
                continue
            if isinstance(place, (rast.Field, rast.Index)):
                base = place.expr
            elif isinstance(place, rast.UnaryOp) and place.op == '*':
                base = place.operand
            else:
                return False
            ty = self._quiet_type(base)
            # `.` reads through every level, so the one nearest the place counts.
            while isinstance(place, rast.Field) and isinstance(ty, (rast.PtrType, rast.RefType)) \
                    and isinstance(self._resolve_alias(ty.inner), (rast.PtrType, rast.RefType)):
                ty = self._resolve_alias(ty.inner)
            if isinstance(ty, rast.RefType) and not ty.mutable:
                return True
            if isinstance(ty, rast.PtrType) or self._is_opaque(ty):
                return False
            place = base

    def _as_let(self, ty: rast.Type) -> rast.Type:
        """`ty`, for a `let` to hold."""
        held = copy.copy(ty)
        self._let_types.append(held)
        return held

    def _own_storage(self, place: rast.Expr) -> Optional[str]:
        """The local whose own storage `place` is, reached with no pointer or
        reference on the path."""
        if isinstance(place, rast.Grouped):
            return self._own_storage(place.expr)
        if isinstance(place, rast.Ident):
            return place.name if place.name in self.locals else None
        if isinstance(place, (rast.Field, rast.Index)):
            if isinstance(place, rast.Index) and isinstance(place.index, rast.Range):
                return None
            base = self._quiet_type(place.expr)
            if isinstance(base, rast.ArrayType if isinstance(place, rast.Index)
                          else (rast.NamedType, rast.TupleType)) and not self._is_opaque(base):
                return self._own_storage(place.expr)
        return None

    def _is_let(self, name: str) -> bool:
        held = self.locals.get(name)
        return any(held is ty for ty in self._let_types)

    def _let_root(self, place: rast.Expr) -> Optional[str]:
        """The `let` whose own storage `place` is. The emitter's _let_place, ahead
        of LLVM types."""
        name = self._own_storage(place)
        return name if name is not None and self._is_let(name) else None

    def _check_addr_into_mut(self, expr: rast.Expr) -> None:
        """`expr` lands in an `@&T` or a `:&` param, which `@x` never does. Of a
        `let`, or of a place behind an `@T`, `@&x` wouldn't do either, so those
        say what would."""
        if isinstance(expr, rast.UnaryOp) and expr.op in ('&', '@'):
            name = self._let_root(expr.operand)
            if name is not None:
                self._report_once(expr, ref_rules.let_into_mut(name))
            elif self._behind_shared(expr.operand):
                self._report_once(expr, ref_rules.BORROW_THROUGH_SHARED)
            else:
                self._report_once(expr, ref_rules.ADDR_INTO_MUT)

    # An `@T` doesn't become an `@&T` (LANGUAGE_SPEC §3.2, §13.3, AGAST #2374)

    def _check_borrow(self, expr: rast.UnaryOp) -> None:
        """`expr` is a mutable borrow of its operand."""
        if self._behind_shared(expr.operand):
            self._report_once(expr, ref_rules.BORROW_THROUGH_SHARED)

    def _check_shared_into_mut(self, expr: rast.Expr, actual: rast.Type) -> None:
        """`expr`, of type `actual`, lands in an `@&T`. `@x` is
        _check_addr_into_mut's."""
        written = isinstance(expr, rast.UnaryOp) and expr.op in ('&', '@')
        if isinstance(actual, rast.RefType) and not actual.mutable and not written:
            self._report_once(expr, ref_rules.SHARED_INTO_MUT)

    def _check_receiver(self, expr: rast.MethodCall, sig) -> None:
        """A method taking `self: @&T` writes what its receiver reaches, as
        `recv.f = v` would: `.` finds the receiver the same way. A standalone
        function takes it as its first param, whatever that's called."""
        if not sig.params:
            return
        slot = self._resolve_alias(sig.params[0][1])
        mutable = 0 in sig.lent or (isinstance(slot, rast.RefType) and slot.mutable)
        if mutable and self._behind_shared(rast.Field(expr.span, expr.expr, expr.method)):
            self._report_once(expr.expr, ref_rules.SHARED_INTO_MUT)

    # A reference to a local doesn't leave its fn (LANGUAGE_SPEC §13.5, LARB ruling
    # R2, AGAST #2340). A check for the definite case: what can't be told stays
    # unjudged. ritz1's twins are in ref_check.ritz, and
    # ritz0/test_return_local_ref.py holds all three compilers to them.

    def _local_root(self, place: rast.Expr) -> Optional[str]:
        """The local root `place` is in: its own storage, and not the caller's,
        which a `:&` param is. A by-value `self` is a local root (#2393)."""
        name = self._own_storage(place)
        if name is None:
            return None
        held = self.locals[name]
        if held is self.lent_locals.get(name):
            return None
        return name

    def _referent(self, expr: rast.Expr) -> Optional[str]:
        """The local root `expr` definitely refers to: `@x` of one, or a binding
        that holds such a reference."""
        if isinstance(expr, rast.Grouped):
            return self._referent(expr.expr)
        if isinstance(expr, rast.UnaryOp) and expr.op in ('&', '@', '&mut', '@&'):
            return self._local_root(expr.operand)
        if not isinstance(expr, rast.Ident):
            return None
        held = self._local_refs.get(id(self.locals.get(expr.name)))
        if held is None:
            return None
        _, root, depth = held
        # A loop can reach a `var`'s later write before this read.
        return root if self._is_let(expr.name) or self._loop_depth <= depth else None

    def _note_local_ref(self, name: str, root: Optional[str]) -> None:
        """`name` was just bound to a reference to `root`, if there's a root."""
        held = self.locals[name]
        if root is not None and isinstance(self._resolve_alias(held),
                                           (rast.PtrType, rast.RefType)):
            self._local_refs[id(held)] = (held, root, self._loop_depth)

    def _forget_local_ref(self, place: rast.Expr) -> None:
        """`place` is written, or its address may let it be: if it's a `var`, what
        it holds is no longer definite."""
        if isinstance(place, rast.Grouped):
            self._forget_local_ref(place.expr)
        elif isinstance(place, rast.Ident) and not self._is_let(place.name):
            self._local_refs.pop(id(self.locals.get(place.name)), None)

    def _gives_referent(self, arg: rast.Expr, lent: bool, pointee: rast.Type) -> Optional[str]:
        """The local root `arg` refers to, if it has pointee `pointee`. A `:&`
        param or a receiver borrows `arg` itself when it's that `T`."""
        ty = self._quiet_type(arg)
        root = self._referent(arg)
        if root is not None and isinstance(ty, (rast.PtrType, rast.RefType)):
            ty = self._resolve_alias(ty.inner)
        elif lent:
            root = self._local_root(arg)
        wanted = self._resolve_alias(pointee)
        if root is None or self._is_opaque(ty) or self._is_opaque(wanted) \
                or self._type_str(ty) != self._type_str(wanted):
            return None
        return root

    def _call_referent(self, call: rast.Expr) -> Optional[str]:
        """The local root a call returning `@U` or `@&U` was given a reference to,
        with pointee `U`: the result may be that reference, so a raw `*U` return,
        which no reference has to live through, isn't asked."""
        callee = self._callees.get(id(call))
        ret = self._resolve_alias(callee[0].ret_type) if callee and callee[0].ret_type else None
        if not isinstance(ret, rast.RefType):
            return None
        sig, skip = callee
        given = [(arg, i + skip in sig.lent) for i, arg in enumerate(call.args)]
        if isinstance(call, rast.MethodCall):
            given.insert(0, (call.expr, True))
        roots = (self._gives_referent(arg, lent, ret.inner) for arg, lent in given)
        return next((root for root in roots if root is not None), None)

    def _check_return(self, expr: rast.Expr) -> None:
        """`expr` is a return value or a tail of one."""
        root = self._referent(expr)
        if root is None and isinstance(expr, (rast.Call, rast.MethodCall)):
            root = self._call_referent(expr)
        if root is not None and isinstance(self._resolve_alias(self._ret_slot()),
                                           (rast.PtrType, rast.RefType)):
            self._report_once(expr, ref_rules.returns_local(root))

    @staticmethod
    def _is_null(ty: rast.Type) -> bool:
        return isinstance(ty, rast.NamedType) and ty.name == 'null'

    @staticmethod
    def _is_span(ty: rast.Type) -> bool:
        return isinstance(ty, rast.NamedType) and (
            ty.name == 'Span' or ty.name.startswith('Span$'))

    def _check_array_slot(self, expr: rast.Expr, actual: Optional[rast.Type],
                          slot: Optional[rast.Type]) -> None:
        """A non-literal `[N]T1` fits `[N]T2` only if T1 is T2 (LARB R5). A
        literal takes the slot's element type, and its parts land one by one."""
        if (slot is None or actual is None or id(expr) in self._slot_reported
                or isinstance(expr, (rast.ArrayLit, rast.ArrayFill, rast.TupleLit))
                or self._arrays_fit(actual, slot)):
            return
        self._slot_reported.add(id(expr))
        self._slot_error(array_rules.ELEMENT_MISMATCH, expr.span)

    def _arrays_fit(self, actual: rast.Type, slot: rast.Type) -> bool:
        """False if an array in `actual` lands on another element type in `slot`.
        The length is judged elsewhere."""
        actual = self._resolve_alias(actual)
        slot = self._resolve_alias(slot)
        if isinstance(actual, rast.ArrayType) and isinstance(slot, rast.ArrayType):
            return self._same_type(actual.inner, slot.inner)
        if (isinstance(actual, rast.TupleType) and isinstance(slot, rast.TupleType)
                and len(actual.elements) == len(slot.elements)):
            return all(self._arrays_fit(a, s) for a, s in zip(actual.elements, slot.elements))
        return True

    def _same_type(self, a: rast.Type, b: rast.Type) -> bool:
        """`a` and `b` are one type, through aliases and module qualifiers. An
        opaque type can't be judged, so it isn't refused."""
        a = self._resolve_alias(a)
        b = self._resolve_alias(b)
        if self._is_opaque(a) or self._is_opaque(b):
            return True
        if isinstance(a, rast.ArrayType) and isinstance(b, rast.ArrayType):
            return (getattr(a.size, 'value', a.size) == getattr(b.size, 'value', b.size)
                    and self._same_type(a.inner, b.inner))
        if isinstance(a, (rast.PtrType, rast.RefType)) and type(a) is type(b):
            return a.mutable == b.mutable and self._same_type(a.inner, b.inner)
        return self._type_str(a) == self._type_str(b)

    # Helper methods

    def _resolve_alias(self, ty: rast.Type) -> rast.Type:
        """Follow `type X = Y`, and drop a module qualifier (`token.Kind`)."""
        seen = set()
        while isinstance(ty, rast.NamedType) and ty.name not in seen:
            seen.add(ty.name)
            qualifier, dot, name = ty.name.rpartition('.')
            if dot and qualifier.rpartition('.')[2] in self.module_names:
                ty = rast.NamedType(ty.span, name, ty.args)
            elif ty.name in self.type_aliases:
                ty = self.type_aliases[ty.name]
            else:
                break
        return ty

    def _is_module_ref(self, expr: rast.Expr) -> bool:
        """An identifier naming an imported module, not a shadowing value."""
        return (isinstance(expr, rast.Ident) and expr.name in self.module_names
                and self._lookup_var(expr.name) is None)

    def _strip_indirection(self, ty: rast.Type) -> rast.Type:
        """The type under any pointers, references and aliases."""
        ty = self._resolve_alias(ty)
        while isinstance(ty, (rast.PtrType, rast.RefType)):
            ty = self._resolve_alias(ty.inner)
        return ty

    def _is_type_param(self, ty: rast.Type) -> bool:
        """A generic parameter: declared in scope, or by the single-capital
        convention (a generic struct's field type reaches here unsubstituted)."""
        if not isinstance(ty, rast.NamedType):
            return False
        if ty.name in self.current_type_params:
            return True
        return (len(ty.name) == 1 and ty.name.isupper()
                and ty.name not in self.structs and ty.name not in self.enums
                and ty.name not in self.type_aliases)

    def _is_opaque(self, ty: rast.Type) -> bool:
        """A type that can't be judged: `unknown` was either reported where it
        arose or is outside what this checker infers, and a type parameter
        stands for whatever it is instantiated with."""
        return (isinstance(ty, rast.NamedType) and ty.name in ('unknown', 'Self')) \
            or self._is_type_param(ty)

    def _is_bool_type(self, ty: rast.Type) -> bool:
        """Check if type is bool."""
        ty = self._resolve_alias(ty)
        return isinstance(ty, rast.NamedType) and ty.name == 'bool'

    def _is_integer_type(self, ty: rast.Type) -> bool:
        """Check if type is an integer type."""
        ty = self._resolve_alias(ty)
        if isinstance(ty, rast.NamedType):
            return ty.name in self.INT_TYPES
        return False

    def _is_numeric_type(self, ty: rast.Type) -> bool:
        """Check if type is numeric (integer or float)."""
        ty = self._resolve_alias(ty)
        if isinstance(ty, rast.NamedType):
            return ty.name in self.NUMERIC_TYPES
        return False

    def _is_bool_or_opaque(self, ty: rast.Type) -> bool:
        return self._is_bool_type(ty) or self._is_opaque(self._resolve_alias(ty))

    def _is_int_or_opaque(self, ty: rast.Type) -> bool:
        return self._is_integer_type(ty) or self._is_opaque(self._resolve_alias(ty))

    def _is_numeric_or_opaque(self, ty: rast.Type) -> bool:
        return self._is_numeric_type(ty) or self._is_opaque(self._resolve_alias(ty))

    def _check_integer_type(self, ty: rast.Type, span: Optional[rast.Span]):
        """Check that type is an integer, error if not."""
        if not self._is_int_or_opaque(ty):
            self._error(f"expected integer type, got {self._type_str(ty)}", span)

    def _value_fits(self, value: Optional[rast.Expr], actual: rast.Type,
                    expected: rast.Type) -> bool:
        """`value`, of type `actual`, in an `expected` slot. A string literal has
        no fixed type: it is `*u8` in a `*u8` slot (LARB R3), and nothing else
        is, so a StrView or String stays a mismatch."""
        if self._types_compatible(actual, expected):
            return True
        if value is None:
            return False
        tails = list(slot_tails(expected, value))
        if not any(isinstance(tail, rast.StringLit) for tail, _ in tails):
            return False
        return all(self._is_u8_ptr(slot) if isinstance(tail, rast.StringLit)
                   else self._types_compatible(self._infer_type(tail), slot)
                   for tail, slot in tails)

    @staticmethod
    def _is_u8_ptr(ty: rast.Type) -> bool:
        return (isinstance(ty, rast.PtrType) and isinstance(ty.inner, rast.NamedType)
                and ty.inner.name == 'u8')

    def _types_compatible(self, actual: rast.Type, expected: rast.Type) -> bool:
        """Check if actual type is compatible with expected type."""
        # Handle None/unknown
        if actual is None or expected is None:
            return True

        actual = self._resolve_alias(actual)
        expected = self._resolve_alias(expected)

        # Nothing to judge against, and `null` may instantiate a type parameter
        if self._is_opaque(actual) or self._is_opaque(expected):
            return True

        # A float literal is whichever float its context wants
        for lit, other in ((actual, expected), (expected, actual)):
            if isinstance(lit, FloatLitType) and isinstance(other, rast.NamedType) \
                    and other.name in ('f32', 'f64'):
                return True

        # A union takes itself and each of its members
        if isinstance(expected, rast.UnionType):
            if isinstance(actual, rast.UnionType):
                return all(self._types_compatible(m, expected) for m in actual.variants)
            return any(self._types_compatible(actual, m) for m in expected.variants)

        # Null is compatible with any pointer type
        if isinstance(actual, rast.NamedType) and actual.name == 'null':
            return isinstance(expected, (rast.PtrType, rast.RefType)) or \
                   (isinstance(expected, rast.NamedType) and expected.name == 'null')

        if isinstance(expected, rast.NamedType) and expected.name == 'null':
            return isinstance(actual, (rast.PtrType, rast.RefType)) or \
                   (isinstance(actual, rast.NamedType) and actual.name == 'null')

        # Same named type
        if isinstance(actual, rast.NamedType) and isinstance(expected, rast.NamedType):
            if actual.name == expected.name:
                return True
            # Integer literal coercion: i64 literal can be used where smaller int expected
            if actual.name == 'i64' and expected.name in self.INT_TYPES:
                return True
            if actual.name in self.INT_TYPES and expected.name in self.INT_TYPES:
                return True  # Allow integer type coercion for now
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

        return False

    def _type_implements_trait(self, type_name: str, trait_name: str) -> bool:
        """Check if a type implements a given trait."""
        if trait_name in self.trait_impls:
            return type_name in self.trait_impls[trait_name]
        return False

    def _promote_numeric_types(self, t1: rast.Type, t2: rast.Type) -> rast.Type:
        """Get the common type for two numeric types."""
        # Simplified: the first type, unless it's a literal the other one fixes.
        # Full implementation would return the "wider" type
        return t2 if isinstance(t1, FloatLitType) else t1

    def _get_iterator_element_type(self, iter_type: rast.Type) -> rast.Type:
        """Get element type from an iterator type."""
        if isinstance(iter_type, rast.NamedType):
            if iter_type.name == 'Range':
                return rast.NamedType(iter_type.span, 'i64', [])
        resolved = self._resolve_alias(iter_type)
        if isinstance(resolved, rast.ArrayType):
            return resolved.inner
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
        if not self.slots_only:
            self.errors.append(TypeError(message, span))

    def _slot_error(self, message: str, span: Optional[rast.Span]):
        self.errors.append(TypeError(message, span))


def check_ref_slots(module: rast.Module, emits_body,
                    module_names: Optional[Set[str]] = None) -> List[TypeError]:
    """The slot rules over a monomorphised module, for the fns
    `emits_body` says this compile emits. `--check-types` is off by default and
    sees generic bodies with `T` opaque, so this runs on every compile, after
    monomorphisation, with the checker's other complaints switched off."""
    checker = TypeChecker(module_names, slots_only=True)
    return checker.check(module, emits_body)
