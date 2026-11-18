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
"""

import copy
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import array_rules
import bool_rules
import enum_rules
import float_rules
import ref_rules
import ritz_ast as rast
from tail_value import slot_tails
from monomorph import mangle_generic_name, TypeSubstitution
from ufcs import find_ufcs_function
from name_resolver import BUILTIN_GENERICS, BUILTIN_VARIANTS, INTRINSICS, NameResolver
from typed import Typed
import re

_UNSIGNED_INT = re.compile(r"(?<![\w$])u(8|16|32|64|size)(?![\w$])")


def _unsigned_as_signed(key: str) -> str:
    """A _referent_key spelled as LLVM sees it: `u32` and `i32` are one `i32`."""
    return _UNSIGNED_INT.sub(r"i\1", key)

# `sizeof(v)` operands typed as values, for the emitter (#3555): the kinds
# that can't spell a type.
SIZEOF_VALUE_OPERANDS = (
    rast.IntLit, rast.FloatLit, rast.BoolLit, rast.CharLit,
    rast.CStringLit, rast.NullLit,
    rast.Cast, rast.StructLit, rast.TupleLit,
)


class FloatLitType(rast.NamedType):
    """A float literal's type: f64, unless its context makes it an f32."""


class TypeError(Exception):
    """Type checking error with source location."""
    def __init__(self, message: str, span: Optional[rast.Span] = None,
                 after_moves: bool = False, slot: bool = False):
        self.span = span
        # A slot rule's (§13.2, §13.4): reported on every compile (Typed).
        self.slot = slot
        # Doesn't explain a move error, so it's printed after one (ritz0.py):
        # a discarded whole array (#3189) beside #2949's move out of `a:&`.
        self.after_moves = after_moves
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
    INT_TYPES = {'i8', 'i16', 'i32', 'i64',
                 'u8', 'u16', 'u32', 'u64'}
    SIGNED_INT_TYPES = {'i8', 'i16', 'i32', 'i64'}
    UNSIGNED_INT_TYPES = {'u8', 'u16', 'u32', 'u64'}

    # Numeric types (integers + floats)
    NUMERIC_TYPES = INT_TYPES | {'f32', 'f64'}

    def __init__(self, module_names: Optional[Set[str]] = None,
                 typed: Optional[Typed] = None):
        self.errors: List[TypeError] = []
        # Where each expression's type goes (typed.py, the typing pass).
        self.typed = typed if typed is not None else Typed()
        self._arg_depth = 0  # >0 while a call argument is checked
        # `name:& T` params of the current fn, by name, with their `T`: `*name`
        # is the `T` itself.
        self.lent_locals: Dict[str, rast.Type] = {}
        # The slot an `if`, `match` or block's tails land in (_infer_into).
        self._tail_slot: Optional[rast.Type] = None
        # The `if`, `match` or block next inferred is dropped (_infer_discarded).
        self._discarding = False
        # id(expr) already reported: a literal's elements are inferred twice.
        self._slot_reported: Set[int] = set()
        # Undeclared struct names a `.field` was refused on, or #3347 refused
        # at a string literal: each is reported once (AGAST #3404).
        self._unknown_structs: Set[str] = set()
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
        # The concrete (non-generic) enums declaring each variant: two make a
        # bare use of it ambiguous (AGAST #2039, the emitter's
        # variant_declarers).
        self.variant_declarers: Dict[str, List[str]] = {}
        # `impl Deref for S`: S's name -> (the impl's S<..> arguments, `deref`'s
        # target T). `s.f` is T's `f` when S has none (LANGUAGE_SPEC §7.7).
        self.deref_targets: Dict[str, Tuple[List[rast.Type], rast.Type]] = {}

        # Current context
        self.locals: Dict[str, rast.Type] = {}  # local variables
        self.current_fn: Optional[FnSig] = None
        self.scope_stack: List[Dict[str, rast.Type]] = []
        self.current_type_params: Set[str] = set()  # type parameters in scope (T, E, etc.)

    def check(self, module: rast.Module, emits_body=None) -> List[TypeError]:
        """Type check a module. Returns list of errors. `emits_body`, if
        given, picks the fns whose bodies are checked."""
        self.errors = []
        self._register(module)

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

    def check_bodies(self, module: rast.Module, bodies) -> List[TypeError]:
        """Check `bodies`, (fn, its impl or None) pairs that needn't be
        `module`'s items, against `module`'s declarations."""
        self.errors = []
        self._register(module)
        for fn, impl in bodies:
            self._check_function(fn, impl)
        return self.errors

    def _register(self, module: rast.Module) -> None:
        """Every declaration in `module`: types, signatures, globals."""
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

        # Also collect impl block methods
        for item in module.items:
            if isinstance(item, rast.ImplBlock):
                # Register methods
                for method in item.methods:
                    self._register_method(item, method)

        # A global's or const's literal initialiser is a slot too (LARB R42).
        for item in module.items:
            if isinstance(item, (rast.VarDef, rast.ConstDef)) and item.value is not None:
                self._check_global_literal(item.value, item.type)
                # An untyped one is refused, naming its initialiser's type
                # (LARB R38), which the emitter reads off the table (#3555).
                # Quietly: the refusal is the error.
                if item.type is None:
                    self._quiet_type(item.value)

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
            if not enum.type_params and '$' not in enum.name:
                declarers = self.variant_declarers.setdefault(variant.name, [])
                if enum.name not in declarers:  # an import cycle registers it twice
                    declarers.append(enum.name)

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
        # DerefMut's target is Deref's (rule 1, deref_rules.impl_errors), so
        # `deref` alone answers both a read and a write of `s.f`.
        if (impl.trait_name == 'Deref' and method.name == 'deref'
                and isinstance(method.ret_type, (rast.RefType, rast.PtrType))):
            args = impl.impl_type.args if isinstance(impl.impl_type, rast.NamedType) else []
            self.deref_targets[impl.type_name] = (list(args), method.ret_type.inner)

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
        self.typed.enter(fn)
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

        self.typed.enter(None)
        self.current_fn = None
        self.current_type_params = set()

    def _check_block(self, block: rast.Block, expected_ret: Optional[rast.Type] = None):
        """Type check a block."""
        for stmt in block.stmts:
            self._check_stmt(stmt)

        # Check trailing expression matches expected return type
        if block.expr:
            if expected_ret is None or self._is_void(expected_ret):
                expr_type = self._infer_discarded(block.expr)
                self._check_discarded(block.expr, expr_type)   # #3189: a void tail
            else:
                expr_type = self._infer_into(block.expr, expected_ret)
            if expected_ret and not self._value_fits(block.expr, expr_type, expected_ret):
                self._error(f"block expression has type {self._type_str(expr_type)}, "
                          f"expected {self._type_str(expected_ret)}", block.expr.span)

    def _check_stmt(self, stmt: rast.Stmt):
        """Type check a statement."""
        if isinstance(stmt, rast.VarStmt):
            if stmt.value:
                init_type = self._infer_into(stmt.value, stmt.type)
                self._check_local_array_length(stmt, stmt.value, init_type, stmt.type)
                root = self._referent(stmt.value)
                self._note_refused_literal(stmt)
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
                self._check_local_array_length(stmt, stmt.value, init_type, stmt.type)
                root = self._referent(stmt.value)
                self._note_refused_literal(stmt)
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

        elif isinstance(stmt, (rast.UnsafeBlock, rast.DeferStmt)):
            self._push_scope()
            self._check_block(stmt.body)
            self._pop_scope()

        elif isinstance(stmt, rast.ExprStmt):
            self._check_discarded(stmt.expr, self._infer_discarded(stmt.expr))

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
            if isinstance(stmt.target, rast.Ident) and stmt.target.name in self.locals:
                self._check_local_array_length(stmt, stmt.value, value_type, target_type)
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

        elif isinstance(stmt, rast.AsmStmt):
            # §18.6: an `out` or `inout` operand is an assignment of its
            # place.  Scope, type and place are the emitter's (_emit_asm),
            # which runs whether or not --check-types does.
            for o in stmt.operands:
                if o.direction in ('out', 'inout') and o.name in self.locals:
                    self._check_write(rast.Ident(o.span, o.name))

        elif isinstance(stmt, rast.AssertStmt):
            cond_type = self._infer_type(stmt.condition)
            if not self._is_bool_or_opaque(cond_type):
                self._error(f"assert condition must be bool, got {self._type_str(cond_type)}",
                          stmt.condition.span)

    def _infer_type(self, expr: rast.Expr) -> rast.Type:
        """Infer the type of an expression, and record it (typed.py)."""
        ty = self._type_by_kind(expr)
        self.typed.record(expr, ty)
        return ty

    def _type_by_kind(self, expr: rast.Expr) -> rast.Type:
        """The type of `expr`, by its kind."""
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
                    self._check_variant_unambiguous(expr.name, expr.span)
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
                    # Its `:&` slots too (AGAST #3035): an un-annotated
                    # `let g = lb` takes for them what `lb(...)` takes.
                    return rast.FnType(expr.span, [ty for _, ty in sig.params],
                                       sig.ret_type, lent=tuple(sorted(sig.lent)))
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
            self._infer_into(expr.value, target_type)
            return rast.TupleType(expr.span, [])   # an assignment is () (#3593)

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
            slot, discarded = self._take_tail_slot(), self._take_discarding()
            self._push_scope()
            for stmt in expr.stmts:
                self._check_stmt(stmt)
            result = rast.NamedType(expr.span, 'void', [])
            if expr.expr:
                result = self._infer_arm(expr.expr, slot, discarded)
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
            source = self._infer_type(expr.expr)
            self._check_array_slot(expr.expr, source, expr.target)
            self._check_array_into_scalar(expr.expr, source, expr.target)
            self._check_cast_to_ref(expr, source)
            self._check_int_as_enum(expr, source)
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
            # A slice of a Vec, Span or String is one of the same.  Through a
            # pointer or reference, it slices what that points at (R9 rule 2,
            # AGAST #3823): `h.p[2:]` with `p: *Vec<T>` is a Vec<T>.
            if isinstance(base_type, (rast.PtrType, rast.RefType)):
                inner = self._resolve_alias(base_type.inner)
                if (isinstance(inner, rast.NamedType)
                        and inner.name.split('$', 1)[0] in ('Vec', 'Span', 'String')):
                    return inner
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

        else:
            self._error(f"cannot infer type of {type(expr).__name__}", getattr(expr, 'span', None))
            return rast.NamedType(expr.span if hasattr(expr, 'span') else None, 'unknown', [])

    def _check_binop(self, expr: rast.BinOp) -> rast.Type:
        """Type check binary operation and return result type."""
        left_type = self._infer_type(expr.left)
        right_type = self._infer_type(expr.right)

        # Comparison operators return bool
        if expr.op in bool_rules.COMPARISONS:
            mixed = self._mixed_float_widths(left_type, right_type)
            if mixed:
                # §7.2, AGAST #3607: on every compile, not just --check-types.
                self._slot_error(float_rules.mixed_float_compare(*mixed), expr.span)
            elif not self._types_compatible(left_type, right_type):
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

        # `+%` `-%` `*%` (LARB R63, AGAST #3485) wrap an integer: otherwise
        # typed as `+` is, below.  Refused on every compile, like a slot error.
        if expr.wrapping:
            for side in (left_type, right_type):
                if not self._is_int_or_opaque(side):
                    self._slot_error(f"`{expr.op}%` wraps an integer, and "
                                     f"`{self._type_str(side)}` isn't one", expr.span)
                    return side

        # Arithmetic operators
        if expr.op in ('+', '-', '*', '/', '%'):
            # Pointer difference, LANGUAGE_SPEC §7.1 (AGAST #3600): `q - p` on two
            # `*T` is their distance in elements, an i64.  A reference operand
            # (`@T`, `@&T`, or the `@x` that infers one) falls through to the
            # error below (LARB R16); two pointee types are the emitter's
            # refusal (#2957), which runs on every compile.
            if (expr.op == '-' and self._is_raw_ptr(left_type)
                    and self._is_raw_ptr(right_type)):
                return rast.NamedType(expr.span, 'i64', [])
            # Pointer/reference arithmetic: ptr + int or ptr - int
            if (expr.op in ('+', '-')
                    and isinstance(left_type, (rast.PtrType, rast.RefType))
                    and self._is_int_or_opaque(right_type)):
                # Return as pointer type for arithmetic result
                if isinstance(left_type, rast.RefType):
                    return rast.PtrType(expr.span, left_type.inner, mutable=left_type.mutable)
                return left_type
            # int + ptr; `int - ptr` names nothing, but an operand this pass
            # can't judge (a type parameter, `unknown`) may be a pointer
            if ((expr.op == '+' or self._is_opaque(self._resolve_alias(left_type)))
                    and isinstance(right_type, (rast.PtrType, rast.RefType))
                    and self._is_int_or_opaque(left_type)):
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
                # A value operand the emitter reads the type of (#3555):
                # `sizeof('a')`, `sizeof(x as u16)`.  A name may spell a
                # type, so only kinds that can't.  Quietly: the checker
                # never looked there, so --check-types reports nothing new.
                elif isinstance(expr.args[0], SIZEOF_VALUE_OPERANDS):
                    self._quiet_type(expr.args[0])
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
                lent = callee.lent if isinstance(callee, rast.FnType) else ()
                for i, arg in enumerate(expr.args):
                    if i in lent and i < len(slots):
                        self._check_lent_arg(arg, slots[i])
                    else:
                        self._infer_into(arg, slots[i] if i < len(slots) else None)
                if isinstance(callee, rast.FnType):
                    return callee.ret or rast.NamedType(expr.span, 'void', [])
                return rast.NamedType(expr.span, 'unknown', [])

            # Check if it's an enum variant constructor
            if fn_name in self.variant_to_enum:
                self._check_variant_unambiguous(fn_name, expr.func.span)
                enum_name = self.variant_to_enum[fn_name]
                # A bare `V(x)` of a name several enums declare says nothing
                # about which: _check_parts knows when a slot does.
                only = self.variant_owners[fn_name] == 1 and '$' not in enum_name
                self._check_payload(expr.args, enum_name if only else None, fn_name)
                return rast.NamedType(expr.span, enum_name, [])

            # Look up function
            fn_sig = self.functions.get(fn_name)
            if fn_sig is None and fn_name in BUILTIN_VARIANTS:
                for arg in expr.args:
                    self._infer_type(arg)
                return rast.NamedType(expr.span, 'unknown', [])
            if fn_sig is None:
                self._error(f"undefined function: {fn_name}", expr.func.span)
                return rast.NamedType(expr.span, 'unknown', [])

            self._callees[id(expr)] = (fn_sig, 0)

            # The callee's type parameters are its own, not the caller's types
            # of the same name (AGAST #2966): `take<T>(p: @T)` beside a
            # `struct T` takes an `@i32`, and returns no `struct T`.
            captured = {tp for tp in fn_sig.type_params
                        if tp not in self.current_type_params
                        and (tp in self.structs or tp in self.enums
                             or tp in self.type_aliases)}
            caller_params = self.current_type_params
            self.current_type_params = caller_params | captured
            try:
                self._check_call_args(expr, fn_name, fn_sig)
            finally:
                self.current_type_params = caller_params

            if fn_sig.is_async:
                # The call makes a `<fn>_Future`; only `.await` gives ret_type.
                return rast.NamedType(expr.span, 'unknown', [])
            if captured and fn_sig.ret_type is not None:
                return TypeSubstitution({tp: rast.NamedType(expr.span, 'unknown', [])
                                         for tp in captured}).apply(fn_sig.ret_type)
            return fn_sig.ret_type or rast.NamedType(expr.span, 'void', [])

        else:
            # Indirect call: type the callee for the table, since the emitter
            # reads a `(p as EfiFn2)(...)` cast's callconv off it (#3555),
            # and the args.
            self._quiet_type(expr.func)
            for arg in expr.args:
                self._infer_type(arg)
            return rast.NamedType(expr.span, 'unknown', [])

    def _check_call_args(self, expr: rast.Call, fn_name: str, fn_sig) -> None:
        """The arity and each argument of a direct call to `fn_sig`."""
        if len(expr.args) != len(fn_sig.params):
            self._error(f"function '{fn_name}' expects {len(fn_sig.params)} arguments, "
                      f"got {len(expr.args)}", expr.span)
        else:
            # Check argument types
            for i, (arg, (param_name, param_type)) in enumerate(zip(expr.args, fn_sig.params)):
                if i in fn_sig.lent:
                    arg_type = self._check_lent_arg(arg, param_type)
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

    def _check_lent_arg(self, arg: rast.Expr, param_type: rast.Type) -> rast.Type:
        """`arg` into a `name:& T` slot, of a direct call or one through a fn
        local (AGAST #3035). It borrows a `T` place, and takes what already
        points at one (§13.4). Returns the argument's type."""
        arg_type = self._infer_type(arg)
        self._check_addr_into_mut(arg)
        self._check_lent_referent(arg, arg_type, param_type)
        self._forget_local_ref(arg)
        return arg_type

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

        # `Color.red()` names the type `Color` even when another enum has a
        # variant `Color` (`Mode.Color`): a variant is reached qualified as a
        # receiver, a type only bare (AGAST #3618).
        type_receiver = self._type_receiver_name(expr.expr)
        if type_receiver is not None:
            receiver_type = rast.NamedType(expr.expr.span, type_receiver, [])
        else:
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
            if self._is_strview_without(receiver, expr.method):
                self._slot_error(ref_rules.no_method(expr.method, 'StrView'),
                                 expr.name_span or expr.span)
                return rast.NamedType(expr.span, 'unknown', [])
            # ritzlib's own `impl StrView` declares some (AGAST #3154).
            self._check_value_args(expr, receiver)
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

        # LARB R41 (§5.5): with no method `f`, `h.f(1)` is `(h.f)(1)` through
        # a `fn(...)` field `f`; with both, neither is picked silently.
        if self._has_fn_field(type_name, expr.method):
            if fn_sig is None and receiver_sig is None:
                callee = rast.Field(expr.span, expr.expr, expr.method, expr.name_span)
                return self._check_call(rast.Call(expr.span, callee, expr.args))
            for arg in expr.args:
                self._infer_type(arg)
            self._slot_error(ref_rules.method_and_field(
                expr.method, type_name, self._field_call_text(expr)),
                expr.name_span or expr.span)
            return rast.NamedType(expr.span, 'unknown', [])

        if receiver_sig is not None:
            self._check_receiver(expr, receiver_sig)

        if fn_sig is None:
            # A ritzlib type's free fn in the UFCS table (`s.len()` on a
            # String is `string_len(@s)`): the emitter's one fallback. Not
            # `<lowercased type>_<method>`: the emitter never dispatched to
            # that, and died on it (AGAST #3244). Unmonomorphised, a
            # `Vec<u8>` is still `Vec`: the table knows it as `Vec$u8`.
            fn_sig = receiver_sig
            if fn_sig is None and isinstance(receiver, rast.NamedType) and receiver.args:
                fn_sig = self.functions.get(find_ufcs_function(
                    self.functions, mangle_generic_name(receiver.name, receiver.args),
                    expr.method))

        if fn_sig is None and self._is_user_type_without(receiver, type_name, expr.method):
            # Method syntax reaches only impl methods (§9, AGAST #3244).
            for arg in expr.args:
                self._infer_type(arg)
            self._slot_error(ref_rules.no_method(expr.method, type_name,
                                       self._free_call(expr, type_name)),
                             expr.name_span or expr.span)
            return rast.NamedType(expr.span, 'unknown', [])

        if fn_sig is None and self._is_generic_instance_without(receiver, expr.method):
            # `w.nope()` on a `W<i32>`: ritz1's words, at the method name
            # (AGAST #3649). The instance has no `impl W$i32` to hint at.
            for arg in expr.args:
                self._infer_type(arg)
            instance = (mangle_generic_name(receiver.name, receiver.args)
                        if receiver.args else receiver.name)
            self._slot_error(ref_rules.no_method(expr.method, instance),
                expr.name_span or expr.span)
            return rast.NamedType(expr.span, 'unknown', [])

        if fn_sig is None:
            # Try just the method name
            tried_names.append(expr.method)
            fn_sig = self.functions.get(expr.method)

        if fn_sig is None:
            # A monomorphised helper (`vec_push$C`) has no name the lookups
            # above try: the emitter still dispatches to it.
            self._check_value_args(expr, receiver)
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
        if not own_method:
            self._check_value_args(expr, receiver)

        return fn_sig.ret_type or rast.NamedType(expr.span, 'void', [])

    def _is_user_type_without(self, receiver: rast.Type, type_name: str, method: str) -> bool:
        """Is `receiver` a non-generic struct or enum the emitter would find
        no `method` on? Its impl methods (`Foo_cmp`) and table fns were looked
        up already; a `Deref` type's target's methods are §7.7's, which the
        emitter reaches through `Foo_deref`, so one is never refused here."""
        if not isinstance(receiver, rast.NamedType) or receiver.args:
            return False
        # Monomorphised, `Option<P>` is the struct `Option$P`: its builtins
        # (`unwrap`, `len`, `ptr`) are the emitter's, not an impl's.
        if '$' in type_name:
            return False
        if type_name not in self.structs and type_name not in self.enums:
            return False
        if type_name == 'StrView':
            return False
        return f"{type_name}_deref" not in self.functions

    # The emitter's own methods on a receiver no source declares them for
    # (_try_emit_strview_builtin, _try_emit_len_builtin).
    STRVIEW_BUILTINS = frozenset({'len', 'as_bytes'})

    def _is_strview_without(self, receiver: rast.Type, method: str) -> bool:
        """Is `receiver` a StrView the emitter would find no `method` on?
        Its methods are ritzlib's `impl StrView` (`StrView_cmp`) and the
        emitter's builtins: anything else raised an unlocated ValueError in
        the emitter (AGAST #3649)."""
        if not (isinstance(receiver, rast.NamedType) and receiver.name == 'StrView'):
            return False
        return (method not in self.STRVIEW_BUILTINS
                and f"StrView_{method}" not in self.functions
                and find_ufcs_function(self.functions, 'StrView', method) is None)

    def _is_generic_instance_without(self, receiver: rast.Type, method: str) -> bool:
        """Is `receiver` an instance of a user generic struct or enum
        (`W<i32>`, ritzlib's `Vec<i32>`) the emitter would find no `method`
        on? Its impl methods (`W_get`) and table fns (`vec_push`) were looked
        up already. The built-in generics' methods are the emitter's, and a
        `Deref` type's target's are §7.7's: neither is refused here."""
        if not isinstance(receiver, rast.NamedType):
            return False
        # Monomorphised, `W<i32>` is the struct `W$i32`.
        name = receiver.name.split('$')[0]
        if not receiver.args and name == receiver.name:
            return False
        if name in BUILTIN_GENERICS:
            return False
        # The template before monomorphisation, the instance after it.
        if not any(n in self.structs or n in self.enums for n in (name, receiver.name)):
            return False
        if name == 'Vec' and method == 'len':  # _try_emit_len_builtin
            return False
        return (f"{name}_deref" not in self.functions
                and f"{receiver.name}_deref" not in self.functions)

    def _has_fn_field(self, type_name: str, name: str) -> bool:
        """Does struct `type_name` have a field `name` of a `fn(...)` type?"""
        info = self.structs.get(type_name)
        if info is None:
            return False
        return any(f == name and isinstance(self._resolve_alias(ty), rast.FnType)
                   for f, ty in info.fields)

    @staticmethod
    def _field_call_text(expr: rast.MethodCall) -> str:
        """`h.f(1)` as the parenthesised field call `(h.f)(1)`: the receiver
        and each argument spelled when it's a name or an integer, else `...`."""
        def text(e: rast.Expr) -> str:
            if isinstance(e, rast.Ident):
                return e.name
            if isinstance(e, rast.IntLit):
                return str(e.value)
            return "..."
        args = ", ".join(text(a) for a in expr.args)
        return f"({text(expr.expr)}.{expr.method})({args})"

    def _free_call(self, expr: rast.MethodCall, type_name: str) -> str | None:
        """The free call `a.cmp(b)` may have meant, `foo_cmp(a, b)`, when
        there is a `foo_cmp`: the receiver and arguments spelled by name, or
        `...` when one isn't a plain name."""
        name = f"{type_name.lower()}_{expr.method}"
        if name not in self.functions:
            return None
        parts = [expr.expr, *expr.args]
        if all(isinstance(p, rast.Ident) for p in parts):
            return f"{name}({', '.join(p.name for p in parts)})"
        return f"{name}(...)"

    def _check_value_args(self, expr: rast.MethodCall, receiver: rast.Type) -> None:
        """The by-value slots of the fn the emitter dispatches `expr` to when
        the loop above leaves its slots unjudged: a ritzlib type's free fn
        that takes the receiver as its first param (`v.push(x)`,
        `vec_push(v, x)`), or a built-in receiver's source method
        (`a.cmp(b)`, `StrView_cmp`). Its param 0 is the receiver, so the
        arguments line up from param 1, and `@x` or a reference into one is
        refused as in the free call (AGAST #3154). Only the by-value slots:
        the receiver, and what a reference slot takes, stay as they were."""
        if not isinstance(receiver, rast.NamedType):
            return
        type_name = self._get_type_name(receiver)
        sig = self.functions.get(f"{type_name}_{expr.method}") or self.functions.get(
            find_ufcs_function(self.functions, type_name, expr.method))
        if sig is None or len(sig.params) != len(expr.args) + 1:
            return
        for i, arg in enumerate(expr.args):
            if i + 1 in sig.lent:
                continue
            slot = self._resolve_alias(sig.params[i + 1][1])
            if isinstance(slot, (rast.PtrType, rast.RefType)) or self._is_span(slot):
                continue
            self._check_ref_slot(arg, self._quiet_type(arg), slot)

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

        # `f.__result` on an `async fn f`'s future, which the async transform
        # generates after checking: the fn's declared type (LARB R78, #3728).
        # Not an undeclared struct's member for #3404's rule.
        future_of = self._future_fn(inner_type)
        if future_of is not None:
            if expr.field == '__result' and future_of.ret_type is not None:
                return future_of.ret_type
            return rast.NamedType(expr.span, 'unknown', [])

        if self._refuse_unknown_struct_member(expr, base_type):
            return rast.NamedType(expr.span, 'unknown', [])

        struct_info = self.structs.get(inner_type.name)
        if struct_info is None:
            self._error(f"type {inner_type.name} has no fields", expr.span)
            return rast.NamedType(expr.span, 'unknown', [])

        # Find field
        for field_name, field_type in struct_info.fields:
            if field_name == expr.field:
                return field_type

        # Not S's own: through `Deref`, its target's (§7.7). The emitter words
        # rule 5's errors (deref_rules.py), a write through only `Deref` too.
        target = self._deref_field(inner_type, expr.field)
        if target is not None:
            return target

        self._error(f"struct '{struct_info.name}' has no field '{expr.field}'", expr.span)
        return rast.NamedType(expr.span, 'unknown', [])

    def _future_fn(self, ty: rast.Type):
        """The async fn whose generated `<fn>_Future` `ty` names, when it is
        one and the module declares no struct of that name; else None."""
        if not isinstance(ty, rast.NamedType) or ty.args or not ty.name.endswith('_Future'):
            return None
        if ty.name in self.structs:
            return None
        fn = self.functions.get(ty.name[:-len('_Future')])
        return fn if fn is not None and fn.is_async else None

    def _undeclared_struct(self, ty: rast.Type) -> Optional[str]:
        """The name `ty` gives, when it names no type at all: no struct, enum
        or alias of the module (an import counts), nothing built in, and no
        type parameter in scope.  None for any other type, and for a generic
        instance: a global's `Vec<T>` keeps its bare name `Vec` after monomorph
        has named the instance (the gate's rzsh build)."""
        ty = self._resolve_alias(ty)
        if (not isinstance(ty, rast.NamedType) or ty.args or '.' in ty.name
                or self._is_opaque(ty)):
            return None
        if (ty.name in self.structs or ty.name in self.enums
                or ty.name in self.type_aliases or ty.name in NameResolver.BUILTIN_TYPES):
            return None
        return ty.name

    def _note_refused_literal(self, stmt) -> None:
        """`let s: String = "abc"` with no type `String`: the emitter refuses
        the literal (AGAST #3347), and that is the mistake to report, so a
        `.field` on `s` says nothing more (as ritz1 does, #3362)."""
        if stmt.type is not None and isinstance(stmt.value, rast.StringLit):
            name = self._undeclared_struct(stmt.type)
            if name is not None:
                self._unknown_structs.add(name)

    def _refuse_unknown_struct_member(self, expr: rast.Field, base_type: rast.Type) -> bool:
        """`s.len` where the local or param `s` is a `Foo` and nothing declares
        `Foo` (AGAST #3404): one located error at `s`, in ritz1's words
        (emitter_expr_access.ritz, unknown_struct_member_refused, #3362),
        once per type name.  The emitter raised a ValueError traceback on it.
        True when `expr` is that case, reported now or before."""
        if not isinstance(expr.expr, rast.Ident) or self._lookup_var(expr.expr.name) is None:
            return False
        name = self._undeclared_struct(base_type)
        if name is None:
            return False
        if name not in self._unknown_structs:
            self._unknown_structs.add(name)
            self._slot_error(f"`{expr.expr.name}` is a `{name}`, which names no declared "
                             f"struct: it has no field `{expr.field}` (is an import missing?)",
                             expr.expr.span)
        return True

    def _deref_field(self, ty: rast.NamedType, field: str,
                     depth: int = 0) -> Optional[rast.Type]:
        """The type of `field` reached through `ty`'s `Deref` (a `Deref`
        target's own `Deref` too), or None when no target has it."""
        found = self.deref_targets.get(ty.name)
        if found is None or depth > 8:
            return None
        impl_args, target = found
        # `impl<U> Deref for W<U>` on a `W<Point>`: U is Point.
        subst = {a.name: b for a, b in zip(impl_args, ty.args)
                 if isinstance(a, rast.NamedType) and not a.args}
        target = self._strip_indirection(self._subst_type(target, subst))
        if self._is_opaque(target):
            return rast.NamedType(ty.span, 'unknown', [])
        if not isinstance(target, rast.NamedType):
            return None
        info = self.structs.get(target.name)
        for name, field_type in (info.fields if info else []):
            if name == field:
                return field_type
        return self._deref_field(target, field, depth + 1)

    @classmethod
    def _subst_type(cls, ty: rast.Type, subst: Dict[str, rast.Type]) -> rast.Type:
        """`ty` with each type parameter named in `subst` replaced."""
        if not subst:
            return ty
        if isinstance(ty, rast.NamedType):
            if not ty.args:
                return subst.get(ty.name, ty)
            return rast.NamedType(ty.span, ty.name,
                                  [cls._subst_type(a, subst) for a in ty.args])
        if hasattr(ty, 'inner'):
            out = copy.copy(ty)
            out.inner = cls._subst_type(ty.inner, subst)
            return out
        if isinstance(ty, rast.TupleType):
            return rast.TupleType(ty.span, [cls._subst_type(t, subst) for t in ty.elements])
        return ty

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
        slot, discarded = self._take_tail_slot(), self._take_discarding()
        cond_type = self._infer_type(expr.cond)
        if not self._is_bool_or_opaque(cond_type):
            self._error(f"if condition must be bool, got {self._type_str(cond_type)}",
                      expr.cond.span)

        self._push_scope()
        then_type = rast.NamedType(expr.span, 'void', [])
        for stmt in expr.then_block.stmts:
            self._check_stmt(stmt)
        if expr.then_block.expr:
            then_type = self._infer_arm(expr.then_block.expr, slot, discarded)
        self._pop_scope()

        if expr.else_block:
            self._push_scope()
            else_type = rast.NamedType(expr.span, 'void', [])
            for stmt in expr.else_block.stmts:
                self._check_stmt(stmt)
            if expr.else_block.expr:
                else_type = self._infer_arm(expr.else_block.expr, slot, discarded)
            self._pop_scope()

            # Both branches should have same type
            if self._value_fits(expr.else_block.expr, else_type, then_type):
                return then_type
            if self._value_fits(expr.then_block.expr, then_type, else_type):
                return else_type
            if not discarded:   # a dropped if's branches needn't agree (#3593)
                self._error(f"if branches have different types: {self._type_str(then_type)} "
                            f"and {self._type_str(else_type)}",
                            (expr.else_block.expr or expr).span)
            return then_type

        return then_type

    def _check_struct_lit(self, expr: rast.StructLit) -> rast.Type:
        """Type check struct literal."""
        struct_info = self.structs.get(expr.name)
        if struct_info is None:
            struct_info = self._builtin_span_struct(expr)
        if struct_info is None:
            self._error(f"undefined struct: {expr.name}", expr.span)
            # Its values are typed all the same (typed.py's readers).
            for _name, value in expr.fields:
                self._infer_type(value)
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

    @staticmethod
    def _builtin_span_struct(expr: rast.StructLit) -> Optional[StructInfo]:
        """`Span<T> { ptr, len }` with no `struct Span` in the program: the
        built-in `{ ptr: *T, len: i64 }` at the literal's own `T` (AGAST
        #3597), the struct the emitter builds for it
        (`_ensure_builtin_generic_struct_specialization`).  It needs its type
        argument, as the emitter does."""
        if expr.name != 'Span' or len(expr.type_args or []) != 1:
            return None
        elem = expr.type_args[0]
        return StructInfo('Span', [
            ('ptr', rast.PtrType(expr.span, elem, mutable=False)),
            ('len', rast.NamedType(expr.span, 'i64', [])),
        ])

    def _check_match(self, expr: rast.Match) -> rast.Type:
        """Type check match expression."""
        slot, discarded = self._take_tail_slot(), self._take_discarding()
        match_type = self._infer_type(expr.expr)

        result_type = None
        for arm in expr.arms:
            self._push_scope()
            self._check_pattern(arm.pattern, match_type)
            if arm.guard:
                guard_type = self._infer_type(arm.guard)
                if not self._is_bool_or_opaque(guard_type):
                    self._error(f"match guard must be bool", arm.guard.span)

            arm_type = self._infer_arm(arm.body, slot, discarded)
            if result_type is None:
                result_type, result_body = arm_type, arm.body
            elif self._value_fits(arm.body, arm_type, result_type):
                pass
            elif self._value_fits(result_body, result_type, arm_type):
                result_type, result_body = arm_type, arm.body
            elif not discarded:   # a dropped match's arms needn't agree (#3593)
                # At the arm: a block arm's body span is column 1 of its line.
                self._error(f"match arms have different types: {self._type_str(result_type)} "
                          f"and {self._type_str(arm_type)}", arm.span)
            self._pop_scope()

        return result_type or rast.NamedType(expr.span, 'void', [])

    def _check_try_op(self, expr: rast.TryOp) -> rast.Type:
        """Type check try operator (?)."""
        inner_type = self._infer_type(expr.expr)

        # Result<T, E> or Option<T>: the Ok / Some payload T.  The
        # emitter's drop of `var t = try_make(1)?` needs it (#2264, #3555).
        if isinstance(inner_type, rast.NamedType):
            if inner_type.name.startswith('Result') or inner_type.name == 'Option':
                if inner_type.args:
                    return inner_type.args[0]

        return rast.NamedType(expr.span, 'unknown', [])

    def _check_pattern(self, pattern: rast.Pattern, expected_type: rast.Type):
        """Type check a pattern and bind variables."""
        if isinstance(pattern, rast.IdentPattern):
            # A bare `None` parses as an IdentPattern. When the scrutinee's
            # enum declares that name it is a variant case and binds nothing,
            # as the emitter takes it; bound, it shadowed the variant in the
            # arm's body with the scrutinee's type (AGAST #3605).
            if not self._declares_variant(expected_type, pattern.name):
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

    def _take_discarding(self) -> bool:
        discarding, self._discarding = self._discarding, False
        return discarding

    def _infer_discarded(self, expr: rast.Expr) -> rast.Type:
        """The type of `expr`, whose value is dropped: an expression
        statement, the tail of a unit fn or a loop body, an arm of a dropped
        `if`/`match`.  A dropped `if` or `match` is a statement, and its arms
        needn't agree (AGAST #3593); the emitter never joins them."""
        inner = expr
        while isinstance(inner, rast.Grouped):
            inner = inner.expr
        if isinstance(inner, (rast.If, rast.Match, rast.Block)):
            self._discarding = True
            ty = self._infer_type(inner)
            self._discarding = False
            return ty
        return self._infer_type(expr)

    def _infer_arm(self, body: rast.Expr, slot: Optional[rast.Type],
                   discarded: bool) -> rast.Type:
        """An arm's or branch's value: dropped with its `if`/`match`, or
        landing in the slot that one lands in."""
        return self._infer_discarded(body) if discarded else self._infer_into(body, slot)

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
        ty = self._slot_variant_type(expr, ty, slot)
        self._check_ref_slot(expr, ty, slot)
        self._check_array_slot(expr, ty, slot)
        self._check_parts(expr, slot)
        if slot is not None and slot is self._ret_slot():
            self._check_array_into_scalar(expr, ty, slot)
            self._check_return(expr)
        self._check_other_referent(expr, ty, slot)
        return ty

    def _slot_variant_type(self, expr: rast.Expr, ty: rast.Type,
                           slot: Optional[rast.Type]) -> rast.Type:
        """A bare variant `V` or `V(..)` in a slot whose enum declares `V` is
        the slot's variant, as the emitter builds it (AGAST #3602):
        variant_to_enum holds the last enum to declare the name, so an
        `enum Display` with a `None` made every `None` Display's.  Option and
        Result are the emitter's own, so their slots declare their variants
        with or without ritzlib's enum in scope.  Anything else keeps `ty`."""
        if isinstance(expr, rast.Ident):
            name = expr.name
        elif isinstance(expr, rast.Call) and isinstance(expr.func, rast.Ident):
            name = expr.func.name
        else:
            return ty
        # No local can be named like a variant (AGAST #2407), so the name is
        # the variant.
        if slot is None or name not in self.variant_to_enum:
            return ty
        base = self._resolve_alias(slot)
        if not isinstance(base, rast.NamedType):
            return ty
        builtin = {'Option': ('Some', 'None'), 'Result': ('Ok', 'Err')}
        if name in builtin.get(base.name, ()) or self._declares_variant(base, name):
            return copy.copy(base)
        return ty

    def _check_variant_unambiguous(self, name: str, span: Optional[rast.Span]) -> None:
        """A bare variant two or more concrete user enums declare is an error
        wherever it appears (AGAST #2039), with the emitter's text: the two
        alphabetically-first declarers.  Match arms resolve against the
        scrutinee and don't come here."""
        declarers = self.variant_declarers.get(name, ())
        if len(declarers) >= 2:
            a, b = sorted(declarers)[:2]
            self._error(f"ambiguous enum variant '{name}': declared by enum '{a}' and "
                        f"enum '{b}'; qualify it, e.g. '{a}.{name}'", span)

    def _check_parts(self, expr: rast.Expr, slot: Optional[rast.Type]) -> None:
        """The elements of a literal or the payload of a variant landing in
        `slot`, which says what each part is."""
        slot = self._resolve_alias(slot) if slot is not None else None
        self._check_literal_length(expr, slot)
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
        if self._span_of_other_element(actual, slot):
            self._slot_reported.add(id(expr))
            self._slot_error(array_rules.ELEMENT_MISMATCH, expr.span)
            return
        if not isinstance(actual, (rast.PtrType, rast.RefType)) or self._is_opaque(slot):
            return
        if self._type_str(self._resolve_alias(actual.inner)) != self._type_str(slot):
            return
        self._slot_reported.add(id(expr))
        addr = isinstance(expr, rast.UnaryOp) and expr.op in ('&', '@', '&mut', '@&')
        self._slot_error(ref_rules.ADDR_INTO_VALUE if addr else ref_rules.REF_INTO_VALUE,
                         expr.span)

    def _span_of_other_element(self, actual: rast.Type, slot: rast.Type) -> bool:
        """`@a` with `a: [N]T1` into a `Span<T2>` / `[T2]` slot, T1 not T2
        (AGAST #2781, #2366). The emitter builds `Span { &a[0], N }` from it,
        which views the array at T2's stride: LARB R5's rule for an array
        store holds here too, and converting is a loop you write."""
        if not self._is_span(slot) or not isinstance(actual, (rast.PtrType, rast.RefType)):
            return False
        array = self._resolve_alias(actual.inner)
        if not isinstance(array, rast.ArrayType):
            return False
        held = self._resolve_alias(array.inner)
        return self._span_element_fits(mangle_generic_name('Span', [held]),
                                       held, slot) is False

    def _span_view_fits(self, actual: rast.Type, slot: rast.Type) -> bool:
        """`@a` / `@&a` of an array or a Vec into a `Span<T>` slot: a view of
        its elements, which the emitter builds as `Span { ptr, len }` (§13,
        AGAST #3595). Its element must be T; `a` itself is a value and
        doesn't fit, nor does another generic struct."""
        if not isinstance(actual, rast.RefType):
            return False
        held = self._resolve_alias(actual.inner)
        if isinstance(held, rast.ArrayType):
            elem = self._resolve_alias(held.inner)
            view = mangle_generic_name('Span', [elem])
        elif isinstance(held, rast.NamedType) and held.name == 'Vec' and len(held.args) == 1:
            elem = self._resolve_alias(held.args[0])
            view = mangle_generic_name('Span', [elem])
        elif isinstance(held, rast.NamedType) and held.name.startswith('Vec$'):
            elem = None                 # monomorphised: `Vec$T` names its element
            view = 'Span$' + held.name.split('$', 1)[1]
        else:
            return False
        return self._span_element_fits(view, elem, slot) is not False

    def _span_element_fits(self, view: str, elem: Optional[rast.Type],
                           slot: rast.Type) -> Optional[bool]:
        """Is `view` (the Span a reference's elements make, spelled `Span$T1`)
        the `slot`'s Span? None when either element is opaque (a type
        parameter, `unknown`): nothing to judge."""
        if elem is not None and self._is_opaque(self._resolve_alias(elem)):
            return None
        # Monomorphisation has spelled the slot `Span$T`: spell T1 the same way.
        if slot.args:
            if len(slot.args) != 1 or self._is_opaque(self._resolve_alias(slot.args[0])):
                return None
            slot_name = mangle_generic_name('Span', slot.args)
        else:
            slot_name = slot.name
        return slot_name == view

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
        elif isinstance(actual, rast.ArrayType):
            # A whole array into a `*U` of anything but itself (#2392): ritz1's
            # emitter refuses it at the array, in its words. Into an `@U`, or
            # from a `:&` param, it's the value-into-reference error above, as
            # it is in ritz1. Into a `*U` of a non-array U, `@a` is refused
            # too, so the words name `@a[0]` (#3054), as ritz1's ref_check.
            self._slot_reported.add(id(expr))
            message = (array_rules.WHOLE_ARRAY_NOT_A_VALUE if isinstance(inner, rast.ArrayType)
                       else array_rules.WHOLE_ARRAY_INTO_POINTER)
            self._slot_error(message, expr.span)

    @staticmethod
    def _is_void(ty: rast.Type) -> bool:
        return isinstance(ty, rast.NamedType) and ty.name == 'void' and not ty.args

    @classmethod
    def _is_unit(cls, ty: rast.Type) -> bool:
        """`void` or `()`: the one unit type, spelled two ways."""
        return cls._is_void(ty) or (isinstance(ty, rast.TupleType) and not ty.elements)

    def _check_discarded(self, expr: rast.Expr, actual: Optional[rast.Type]) -> None:
        """A whole array alone as a statement, or a void fn's tail: a `[N]T`
        local, an `a:& [N]T` param, an array field or `*p` of a `*[N]T`
        (AGAST #3189). It does nothing; ritz1 refuses it at the array in
        #2287's words, and so does ritz0. A call returning an array is a
        call, and its value may be dropped."""
        place = expr
        while isinstance(place, rast.Grouped):
            place = place.expr
        if not (isinstance(place, (rast.Ident, rast.Field))
                or (isinstance(place, rast.UnaryOp) and place.op == '*')):
            return
        if actual is not None and isinstance(self._resolve_alias(actual), rast.ArrayType):
            self._slot_error(array_rules.WHOLE_ARRAY_NOT_A_VALUE, place.span, after_moves=True)

    def _check_array_into_scalar(self, expr: rast.Expr, actual: Optional[rast.Type],
                                 slot: Optional[rast.Type]) -> None:
        """A whole array, literal or named, returned from a number or bool fn
        or cast to one (AGAST #3187, #3190). The emitter wrote a `ret [N x T]`
        in a scalar fn, which clang rejects; ritz1 refuses it at the array.
        Only these two sites: a `let`/`var`/assign/argument already refuses it
        as a store mismatch, and a pointer, reference or Span slot has its own
        rule (_check_value_into_ref)."""
        if slot is None or actual is None or id(expr) in self._slot_reported:
            return
        if isinstance(self._resolve_alias(actual), rast.ArrayType) and (
                self._is_numeric_type(slot) or self._is_bool_type(slot)):
            self._slot_reported.add(id(expr))
            self._slot_error(array_rules.WHOLE_ARRAY_NOT_A_VALUE, expr.span)

    def _check_cast_to_ref(self, cast: rast.Cast, source: Optional[rast.Type]) -> None:
        """`c as @&C`, `c as @C` or `c as *C` with `c` a struct or array value,
        a `:&` param's included (AGAST #2370): a cast isn't a borrow, so it's
        the bare form's error, as ritz1's ref_cast_value_to_ref. An integer
        source is the integer-to-pointer cast and stays; a string literal is a
        `*u8` already, and a StrView or String into a `*T` has LARB R3's own
        words (the emitter's _STR_AS_PTR, AGAST #2341)."""
        target = self._resolve_alias(cast.target)
        if source is None or not isinstance(target, (rast.PtrType, rast.RefType)):
            return
        operand = cast.expr
        while isinstance(operand, rast.Grouped):
            operand = operand.expr
        if isinstance(operand, rast.StringLit) or id(operand) in self._slot_reported:
            return
        source = self._resolve_alias(source)
        if isinstance(target, rast.PtrType) and isinstance(source, rast.NamedType) \
                and source.name in ('StrView', 'String'):
            return
        if isinstance(source, rast.ArrayType) or self._is_struct(source):
            self._report_value_into_ref(operand, target)

    def _check_int_as_enum(self, cast: rast.Cast, source: Optional[rast.Type]) -> None:
        """`n as E` with `n` an integer, for any enum `E`: fieldless, with a
        representation type, or carrying data (LARB R19, AGAST #3040). An
        integer may name no variant, so it's refused at the `as`; the way in
        is a `match`. A slot error, so it's reported on every compile and
        stops emission, which crashed on a data enum. `e as U` is §10.4's
        enum-to-integer and isn't judged here."""
        if source is None or not self._is_integer_type(source):
            return
        target = self._resolve_alias(cast.target)
        if not isinstance(target, rast.NamedType) or target.name not in self.enums:
            return
        self._slot_error(enum_rules.int_as_enum(target.name), cast.as_span or cast.span)

    def _check_other_referent(self, expr: rast.Expr, actual: Optional[rast.Type],
                              slot: Optional[rast.Type]) -> None:
        """`@x` or `@&x` lands in an `@U`, `@&U` or `*U` of another `U`: the
        reference would be reinterpreted. Exactly the same type, not the same
        width (Aaron's ruling on AGAST #2368). After the return check, as
        ritz1's ref_into does, so a reference to a local says that first.
        A `*T` value into a `*U` is _check_other_pointee's (LARB R71)."""
        if slot is None or actual is None:
            return
        if not self._is_written_ref(expr):
            self._check_other_pointee(expr, actual, slot)
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

    def _check_other_pointee(self, expr: rast.Expr, actual: rast.Type,
                             slot: rast.Type) -> None:
        """A pointer or reference value, not a written `@x`, lands in a
        pointer or reference slot of another pointee (LARB R71): `*[4]i32`
        into `*[3]i32`, `*C` into `*D`, `@T` into `@U`. The byte pointer is
        the way between: a `*T` or `@T` fits a `*u8`, and a `*u8` fits any
        `*T`. `null` is no pointer type here, so it fits. What the checker
        can't name (opaque, generic) stays unjudged."""
        actual = self._resolve_alias(actual)
        slot = self._resolve_alias(slot)
        if not isinstance(slot, (rast.PtrType, rast.RefType)) \
                or not isinstance(actual, (rast.PtrType, rast.RefType)):
            return
        if isinstance(slot, rast.PtrType) and (
                self._is_byte(slot.inner)
                or (isinstance(actual, rast.PtrType) and self._is_byte(actual.inner))):
            return
        # A struct for another struct at a call is #1948's "argument N of `f`
        # has the wrong type", as for `@x` (_check_other_referent).
        if self._arg_depth and self._is_struct(actual.inner) and self._is_struct(slot.inner):
            return
        if not self._other_referent(actual.inner, slot.inner):
            return
        # Into an `@U` or `@&U` param, a pointee of another LLVM type (`@i32`
        # into `@[2]i32`) is #1948's words too: the emitter compares the
        # pointer types, and ritz1 refuses it the same way. Left to R71 is
        # what passes that: a pointee differing only in an integer's sign.
        if self._arg_depth and isinstance(slot, rast.RefType) and _unsigned_as_signed(
                self._referent_key(actual.inner)) != _unsigned_as_signed(
                self._referent_key(slot.inner)):
            return
        self._report_once(expr, ref_rules.REF_TO_OTHER_TYPE)

    def _is_byte(self, ty: rast.Type) -> bool:
        ty = self._resolve_alias(ty)
        return isinstance(ty, rast.NamedType) and ty.name == 'u8' and not ty.args

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
        _check_addr_into_mut's. An `@&T` reached through an `@T`, as `h.m` of
        `h: @H` is, is read-only too (#2381): what `expr` points at is walked."""
        written = isinstance(expr, rast.UnaryOp) and expr.op in ('&', '@')
        if not isinstance(actual, rast.RefType) or written:
            return
        if not actual.mutable or self._behind_shared(rast.UnaryOp(expr.span, '*', expr)):
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
        if isinstance(expr, rast.Index) and isinstance(expr.index, rast.Range):
            # `v[a..b]` of a Vec or String: in a Span slot, a view of v (LARB
            # R57); elsewhere a copy, which no reference slot takes. A Span's
            # slice views what the Span does: a param's is the caller's.
            base = self._quiet_type(expr.expr)
            if isinstance(base, rast.NamedType) and (
                    base.name in ('Vec', 'String') or base.name.startswith('Vec$')):
                return self._local_root(expr.expr)
            return None
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
        if root is not None and self._is_ref_slot(held):
            self._local_refs[id(held)] = (held, root, self._loop_depth)

    def _is_ref_slot(self, slot: Optional[rast.Type]) -> bool:
        """Does `slot` hold a reference for R2: a pointer, a reference, or a
        Span, a view (LARB R57)?"""
        held = self._resolve_alias(slot) if slot is not None else None
        return isinstance(held, (rast.PtrType, rast.RefType)) or (
            held is not None and self._is_span(held))

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
        if root is not None and self._is_ref_slot(self._ret_slot()):
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
        literal takes the slot's element type, and its parts land one by one; its
        length is `_check_literal_length`'s."""
        if (slot is None or actual is None or id(expr) in self._slot_reported
                or isinstance(expr, (rast.ArrayLit, rast.ArrayFill, rast.TupleLit))
                or self._arrays_fit(actual, slot)):
            return
        self._slot_reported.add(id(expr))
        self._slot_error(array_rules.ELEMENT_MISMATCH, expr.span)

    def _check_literal_length(self, expr: rast.Expr, slot: Optional[rast.Type]) -> bool:
        """An array literal or fill must be its `[N]T` slot's N long (LARB R42,
        AGAST #3315): nothing is zero-filled, and a longer one is refused the
        same. Refused at the literal. True if it was. `slot` is resolved."""
        if not (isinstance(expr, (rast.ArrayLit, rast.ArrayFill))
                and isinstance(slot, rast.ArrayType)) or id(expr) in self._slot_reported:
            return False
        have = len(expr.elements) if isinstance(expr, rast.ArrayLit) else expr.count
        have = getattr(have, 'value', have)
        want = getattr(slot.size, 'value', slot.size)
        if not (isinstance(have, int) and isinstance(want, int)) or have == want:
            return False
        self._slot_reported.add(id(expr))
        self._slot_error(array_rules.literal_length(have, self._type_str(slot)), expr.span)
        return True

    def _check_global_literal(self, expr: rast.Expr, slot: Optional[rast.Type]) -> None:
        """A global's initialiser and the literals inside it, against its type:
        the only check a global's value gets here."""
        slot = self._resolve_alias(slot) if slot is not None else None
        while isinstance(expr, rast.Grouped):
            expr = expr.expr
        if self._check_literal_length(expr, slot) or not isinstance(slot, rast.ArrayType):
            return
        parts = (expr.elements if isinstance(expr, rast.ArrayLit)
                 else [expr.value] if isinstance(expr, rast.ArrayFill) else [])
        for part in parts:
            self._check_global_literal(part, slot.inner)

    def _check_local_array_length(self, stmt: rast.Stmt, value: rast.Expr,
                                  actual: Optional[rast.Type],
                                  slot: Optional[rast.Type]) -> None:
        """A non-literal `[M]T` into a local `[N]T`, M not N (AGAST #2090): a
        `let` bound the `[M x T]` value under the `[N]T` name. Refused at the
        statement, in ritz1's words. A literal's length is `_check_literal_length`'s,
        at the literal (LARB R42)."""
        if (slot is None or actual is None or id(value) in self._slot_reported
                or isinstance(value, (rast.ArrayLit, rast.ArrayFill))):
            return
        actual = self._resolve_alias(actual)
        slot = self._resolve_alias(slot)
        if not (isinstance(actual, rast.ArrayType) and isinstance(slot, rast.ArrayType)):
            return
        have = getattr(actual.size, 'value', actual.size)
        want = getattr(slot.size, 'value', slot.size)
        if isinstance(have, int) and isinstance(want, int) and have != want:
            self._slot_reported.add(id(value))
            self._slot_error(array_rules.LENGTH_MISMATCH, stmt.span)

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

    def _type_receiver_name(self, expr: rast.Expr) -> Optional[str]:
        """The struct or enum a bare receiver identifier names, if any.

        A local shadows the type; a type shadows another enum's same-named
        variant (AGAST #3618), which a receiver reaches as `Mode.Color`.
        """
        if not isinstance(expr, rast.Ident) or self._lookup_var(expr.name) is not None:
            return None
        if expr.name in self.structs or expr.name in self.enums:
            return expr.name
        # `Span.empty()`: the built-in Span, typed by the emitter from its
        # slot (AGAST #3597); its methods are the emitter's.  (A local
        # `Span` returned None above, as in _builtin_type_receiver.)
        if expr.name == 'Span':
            return expr.name
        return None

    def _declares_variant(self, ty: rast.Type, name: str) -> bool:
        """Does the enum under `ty`'s indirection declare a variant `name`?"""
        base = self._strip_indirection(ty)
        if not isinstance(base, rast.NamedType):
            return False
        info = self.enums.get(base.name)
        return info is not None and any(v.name == name for v in info.variants)

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

    def _is_raw_ptr(self, ty: rast.Type) -> bool:
        """A `*T`.  This pass types `@x` / `@&x` as a RefType; PtrType's
        `shared` / `mut_ref` marks are monomorph's and the emitter's."""
        return isinstance(self._resolve_alias(ty), rast.PtrType)

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
        no fixed type: it is `*u8` in a `*u8` slot (LARB R3) and a `Span<u8>` of
        its bytes in a `Span<u8>` slot (LARB R62, AGAST #3596), and nothing else
        is, so a StrView, a `c"…"` or a String stays a mismatch."""
        if self._types_compatible(actual, expected):
            return True
        if value is None:
            return False
        tails = list(slot_tails(expected, value))
        if not any(isinstance(tail, rast.StringLit) for tail, _ in tails):
            return False
        return all(self._is_u8_ptr(slot) or self._is_u8_span(slot)
                   if isinstance(tail, rast.StringLit)
                   else self._types_compatible(self._infer_type(tail), slot)
                   for tail, slot in tails)

    def _is_u8_span(self, ty: rast.Type) -> bool:
        """`Span<u8>`, or monomorphisation's `Span$u8` spelling of it."""
        ty = self._resolve_alias(ty)
        if not self._is_span(ty):
            return False
        if ty.args:
            return (len(ty.args) == 1 and
                    mangle_generic_name('Span', [self._resolve_alias(ty.args[0])])
                    == 'Span$u8')
        return ty.name == 'Span$u8'

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

        # `void` (a fn with no return type) and `()` are one unit type (#3594)
        if self._is_unit(actual) and self._is_unit(expected):
            return True

        # A float literal is whichever float its context wants
        for lit, other in ((actual, expected), (expected, actual)):
            if isinstance(lit, FloatLitType) and isinstance(other, rast.NamedType) \
                    and other.name in ('f32', 'f64'):
                return True

        # Null is compatible with any pointer type, a fn pointer included
        # (§5.5: a fn type lowers to an opaque `ptr`; AGAST #3601)
        if isinstance(actual, rast.NamedType) and actual.name == 'null':
            return isinstance(expected, (rast.PtrType, rast.RefType, rast.FnType)) or \
                   (isinstance(expected, rast.NamedType) and expected.name == 'null')

        if isinstance(expected, rast.NamedType) and expected.name == 'null':
            return isinstance(actual, (rast.PtrType, rast.RefType, rast.FnType)) or \
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
            if expected.name in {'i64', 'u64'}:
                return True
        if isinstance(actual, rast.NamedType) and isinstance(expected, (rast.PtrType, rast.RefType)):
            if actual.name in {'i64', 'u64'}:
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

        # `@a` of an array or a Vec views its elements: it fits their Span
        if self._is_span(expected) and self._span_view_fits(actual, expected):
            return True

        # Function pointer types
        if isinstance(actual, rast.FnType) and isinstance(expected, rast.FnType):
            if len(actual.params) != len(expected.params):
                return False
            for a, e in zip(actual.params, expected.params):
                if not self._types_compatible(a, e):
                    return False
            return self._types_compatible(actual.ret, expected.ret)

        return False

    def _promote_numeric_types(self, t1: rast.Type, t2: rast.Type) -> rast.Type:
        """Get the common type for two numeric types."""
        # Simplified: the first type, unless it's a literal the other one fixes,
        # or an f32 meets an f64, which widens it (§7.1, AGAST #3607).
        # Full implementation would return the "wider" type
        if self._mixed_float_widths(t1, t2):
            return rast.NamedType(t1.span, 'f64', [])
        return t2 if isinstance(t1, FloatLitType) else t1

    def _mixed_float_widths(self, t1: rast.Type, t2: rast.Type):
        """(`t1`'s name, `t2`'s) when one is f32 and the other f64, neither a
        literal (a literal takes the other side's type), else None."""
        if isinstance(t1, FloatLitType) or isinstance(t2, FloatLitType):
            return None
        t1, t2 = self._resolve_alias(t1), self._resolve_alias(t2)
        if not (isinstance(t1, rast.NamedType) and isinstance(t2, rast.NamedType)):
            return None
        if {t1.name, t2.name} == {'f32', 'f64'}:
            return t1.name, t2.name
        return None

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
        elif isinstance(ty, rast.FnType):
            params = ', '.join(self._type_str(p) for p in ty.params)
            return f"fn({params}) -> {self._type_str(ty.ret)}"
        elif isinstance(ty, rast.TupleType):
            elem_strs = ', '.join(self._type_str(e) for e in ty.elements)
            return f"({elem_strs})"
        return str(ty)

    def _error(self, message: str, span: Optional[rast.Span]):
        """Record a type error (reported under --check-types)."""
        self.errors.append(TypeError(message, span))

    def _slot_error(self, message: str, span: Optional[rast.Span],
                    after_moves: bool = False):
        """Record a slot error (reported on every compile)."""
        self.errors.append(TypeError(message, span, after_moves, slot=True))
