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
import bool_rules
from builtin_types import PRIMITIVES
import float_rules
import future_rules
import ref_rules
import ritz_ast as rast
from instance_site import add_notes
from monomorph import bind_type_params, mangle_generic_name, TypeSubstitution
from monomorph_core import display_generic_name, instance_display_name
from name_resolver import BUILTIN_GENERICS, BUILTIN_VARIANTS, INTRINSICS, NameResolver
from tail_value import arm_diverges
from typed import Typed
from type_queries import FloatLitType, TypeQueriesMixin
from type_refs import RefChecksMixin
from type_slots import SlotInferMixin

# `sizeof(v)` operands typed as values, for the emitter (#3555, #4066): the
# kinds that can't spell a type.  MethodCall is here because the emitter reads
# its type from the table, which it must have for `sizeof(recv.method())`
# (#4066); a Call's stays the emitter's rule.
SIZEOF_VALUE_OPERANDS = (
    rast.IntLit, rast.FloatLit, rast.BoolLit, rast.CharLit,
    rast.CStringLit, rast.NullLit,
    rast.Cast, rast.StructLit, rast.TupleLit,
    rast.MethodCall,
)


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
    # An impl method's impl type params (`impl<T> W<T>`): a call through a
    # `W<i32>` receiver returns its type at T = i32.
    owner_params: List[str] = field(default_factory=list)


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


class TypeChecker(SlotInferMixin, RefChecksMixin, TypeQueriesMixin):
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
        # The carrier ctor _infer_into is typing into its own slot, which
        # no user enum's same-named variant makes ambiguous (AGAST #4945).
        self._carrier_in_slot: Optional[rast.Expr] = None
        # The `if`, `match` or block next inferred is dropped (_infer_discarded).
        self._discarding = False
        # id() of each untyped let / var's value: a generic variant there
        # takes the fn's return type when that's its enum's (AGAST #4057).
        self._untyped_let_values: Set[int] = set()
        # Names an untyped `let t = (1, 2)` binds in the current fn: a tuple
        # literal binds no type param (#3064), as monomorph has it.
        self._tuple_lit_names: Set[str] = set()
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
        # `Future` has no size: a by-value slot of one (LARB R79).
        for message, span in future_rules.by_value_errors(module, wanted):
            self._slot_error(message, span)
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
            lent=self._lent_params(method),
            owner_params=list(impl.type_params or []),
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
        self._tuple_lit_names = set()

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
        first_error = len(self.errors)
        self._check_block(fn.body, fn.ret_type)
        # An instance's errors name where it was instantiated (AGAST #4844).
        for error in self.errors[first_error:]:
            add_notes(error, fn)

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
                self._misfit(block.expr, expr_type, expected_ret,
                             f"block expression has type {self._type_str(expr_type)}, "
                             f"expected {self._type_str(expected_ret)}", block.expr.span)

    def _check_stmt(self, stmt: rast.Stmt):
        """Type check a statement."""
        if isinstance(stmt, (rast.VarStmt, rast.LetStmt)) and stmt.type is None \
                and stmt.value is not None:
            self._untyped_let_values.add(id(stmt.value))
        if isinstance(stmt, rast.VarStmt):
            if stmt.value:
                init_type = self._infer_into(stmt.value, stmt.type)
                self._check_local_array_length(stmt, stmt.value, init_type, stmt.type)
                root = self._referent(stmt.value)
                self._note_refused_literal(stmt)
                if stmt.type:
                    if not self._value_fits(stmt.value, init_type, stmt.type):
                        self._misfit(stmt.value, init_type, stmt.type,
                                     f"cannot initialize {self._type_str(stmt.type)} "
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
                        self._misfit(stmt.value, init_type, stmt.type,
                                     f"cannot initialize {self._type_str(stmt.type)} "
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
                        self._misfit(stmt.value, ret_type, self.current_fn.ret_type,
                                     f"return type {self._type_str(ret_type)} doesn't match "
                                     f"expected {self._type_str(self.current_fn.ret_type)}", stmt.span)

        elif isinstance(stmt, rast.AssignStmt):
            target_type = self._infer_type(stmt.target)
            self._check_write(stmt.target)
            value_type = self._infer_into(stmt.value, target_type)
            if isinstance(stmt.target, rast.Ident) and stmt.target.name in self.locals:
                self._check_local_array_length(stmt, stmt.value, value_type, target_type)
            if not self._value_fits(stmt.value, value_type, target_type):
                self._misfit(stmt.value, value_type, target_type,
                             f"cannot assign {self._type_str(value_type)} "
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
            # which judges them itself.
            for o in stmt.operands:
                if o.direction in ('out', 'inout') and o.name in self.locals:
                    self._check_write(rast.Ident(o.span, o.name))

        elif isinstance(stmt, rast.AssertStmt):
            cond_type = self._infer_type(stmt.condition)
            if not self._is_bool_or_opaque(cond_type):
                self._error(f"assert condition must be bool, got {self._type_str(cond_type)}",
                          stmt.condition.span)

        if isinstance(stmt, (rast.VarStmt, rast.LetStmt)):
            self._note_tuple_lit_let(stmt)

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
                    self._check_variant_unambiguous(expr, expr.name, expr.span)
                    return self._variant_type(expr, expr.name, [], [])
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

        # An integer literal (`2`, `-1`, `1 * 2`) opposite a float operand is
        # that float (§7.5, AGAST #4285): `x != 2` compares two f64s, `1 + y`
        # with `y: f32` is an f32.  The emitter makes it a float constant.
        if float_rules.int_literal_only(expr.left) and self._is_float(right_type):
            left_type = right_type
        elif float_rules.int_literal_only(expr.right) and self._is_float(left_type):
            right_type = left_type

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
            # Through an alias of one (`type IP = *i32`, AGAST #4260)
            pointer = self._resolve_alias(operand_type)
            if isinstance(pointer, (rast.PtrType, rast.RefType)):
                return pointer.inner
            elif self._is_opaque(operand_type):
                return rast.NamedType(expr.span, 'unknown', [])
            else:
                self._error(f"cannot dereference non-pointer type {self._type_str(operand_type)}",
                          expr.span)
                return rast.NamedType(expr.span, 'unknown', [])

        return operand_type

    def _print_value_type(self, span) -> rast.Type:
        """`Result<(), Errno>`, a print builtin's value (AGAST #4962).

        It is ritzlib.errno's `errno_check`'s return, which the lowering
        calls. A self-contained program without it has no Errno to build, so
        there the call is a procedure (the emitter's `_resolved_to_procedure`).
        """
        sig = self.functions.get('errno_check')
        if sig is not None and sig.ret_type is not None:
            return sig.ret_type
        return rast.NamedType(span, 'void', [])

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
                # never looked there, so it reports nothing new.
                elif isinstance(expr.args[0], SIZEOF_VALUE_OPERANDS):
                    self._quiet_type(expr.args[0])
                return rast.NamedType(expr.span, 'i64', [])

            # future_poll(f: @&Future) -> bool (LARB R79): `f` is typed and
            # held to an `@&Future` slot like any argument.
            if fn_name == future_rules.POLL and fn_name not in self.functions:
                for arg in expr.args:
                    self._check_ref_slot(arg, self._infer_type(arg), future_rules.POLL_PARAM)
                return rast.NamedType(expr.span, 'bool', [])

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

            # The print builtins: print(str) / eprint(str) (AGAST #1641), and
            # println / eprintln / write / writeln when the literal holds a
            # placeholder (AGAST #202; otherwise they keep their ordinary
            # signature). The lowering (_emit_interp_string_print) is the call
            # whatever fn of the name is in scope, and its value is
            # Result<(), Errno>: the first failing piece's errno, or Ok
            # (LANGUAGE_SPEC §2.6, AGAST #4962). format_into(sink, str)
            # appends and has no value (AGAST #1824).
            interp_line = (fn_name in ('println', 'eprintln')
                           and any(isinstance(a, rast.InterpString)
                                   for a in expr.args))
            interp_writer = (fn_name in ('write', 'writeln')
                             and len(expr.args) == 2
                             and isinstance(expr.args[1], rast.InterpString))
            if (fn_name in ('print', 'eprint', 'format_into')
                    or interp_line or interp_writer):
                for arg in expr.args:
                    self._infer_type(arg)
                if fn_name == 'format_into':
                    return rast.NamedType(expr.span, 'void', [])
                return self._print_value_type(expr.span)

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
                self._check_variant_unambiguous(expr, fn_name, expr.func.span)
                enum_name = self.variant_to_enum[fn_name]
                # A bare `V(x)` of a name several enums declare says nothing
                # about which: _check_parts knows when a slot does.
                only = self.variant_owners[fn_name] == 1 and '$' not in enum_name
                arg_types = self._check_payload(expr.args, enum_name if only else None, fn_name)
                return self._variant_type(expr, fn_name, expr.args, arg_types)

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
            # Every one of the callee's own params is opaque in its slots, not
            # just a single capital's (`T0`..`T11`, AGAST #4260).
            self.current_type_params = caller_params | captured | set(fn_sig.type_params)
            try:
                arg_types = self._check_call_args(expr, fn_name, fn_sig)
            finally:
                self.current_type_params = caller_params

            if fn_sig.is_async:
                # The call makes a `<fn>$Future`; only `.await` gives ret_type.
                return rast.NamedType(expr.span, 'unknown', [])
            if fn_sig.ret_type is None:
                return rast.NamedType(expr.span, 'void', [])
            # A generic fn's return type at the call's type args (AGAST
            # #3554): `vec_new<u64>()` is a Vec<u64>, and `id(3)` an i64.
            mapping = self._call_type_args(expr, fn_sig, arg_types)
            for tp in captured:
                mapping.setdefault(tp, rast.NamedType(expr.span, 'unknown', []))
            if mapping:
                return TypeSubstitution(mapping).apply(fn_sig.ret_type)
            return fn_sig.ret_type

        else:
            # Indirect call: type the callee for the table, since the emitter
            # reads a `(p as EfiFn2)(...)` cast's callconv off it (#3555),
            # and the args.
            self._quiet_type(expr.func)
            for arg in expr.args:
                self._infer_type(arg)
            return rast.NamedType(expr.span, 'unknown', [])

    def _check_call_args(self, expr: rast.Call, fn_name: str, fn_sig) -> List[rast.Type]:
        """The arity and each argument of a direct call to `fn_sig`; returns
        the arguments' types (none on an arity error)."""
        arg_types: List[rast.Type] = []
        if len(expr.args) != len(fn_sig.params):
            self._error(f"function '{fn_name}' expects {len(fn_sig.params)} arguments, "
                      f"got {len(expr.args)}", expr.span)
        else:
            # Check argument types
            for i, (arg, (param_name, param_type)) in enumerate(zip(expr.args, fn_sig.params)):
                if i in fn_sig.lent:
                    arg_type = self._check_lent_arg(arg, param_type)
                    arg_types.append(arg_type)
                    if isinstance(self._resolve_alias(arg_type),
                                  (rast.PtrType, rast.RefType)):
                        continue
                else:
                    self._arg_depth += 1
                    arg_type = self._infer_into(arg, param_type)
                    self._arg_depth -= 1
                    arg_types.append(arg_type)
                if not self._value_fits(arg, arg_type, param_type):
                    self._misfit(arg, arg_type, param_type,
                                 f"argument {i+1} ('{param_name}'): expected {self._type_str(param_type)}, "
                                 f"got {self._type_str(arg_type)}", arg.span)
        return arg_types

    def _call_type_args(self, expr: rast.Call, fn_sig, arg_types) -> Dict[str, rast.Type]:
        """The type args a call to generic `fn_sig` instantiates it at: its
        written ones, else those its arguments bind (§4.4, as monomorph binds
        them).  A param no argument binds, or two bind differently, is left
        out: monomorph reports it."""
        params = fn_sig.type_params
        if not params:
            return {}
        if expr.type_args:
            if len(expr.type_args) != len(params):
                return {}
            return dict(zip(params, expr.type_args))
        if len(arg_types) != len(expr.args):
            return {}
        pairs = [(param_type, arg, None if self._is_unknown(ty) else self._plain(ty))
                 for (_name, param_type), arg, ty in zip(fn_sig.params, expr.args, arg_types)]
        bound, conflict = bind_type_params(params, pairs, self._resolve_alias)
        return {tp: ty for tp, ty in bound.items() if tp not in conflict}

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

        # `Color.Green(1)`: a variant constructed through its enum, unless a
        # local shadows the enum (`var Opt: S`, AGAST #4260)
        if self._type_receiver_name(expr.expr) in self.enums:
            enum = self.enums[expr.expr.name]
            if any(v.name == expr.method for v in enum.variants):
                self._check_payload(expr.args, enum.name, expr.method)
                return rast.NamedType(expr.span, enum.name, [])

        # Primitive and built-in-generic receivers have emitter-provided
        # methods (`x.popcnt()`, `r.unwrap()`) that no source file declares.
        receiver = self._strip_indirection(receiver_type)
        payload = self._instance_unwrap_ret(receiver, expr.method)
        if payload is not None:
            return payload
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
            if self._is_strview_as_bytes(receiver, expr):
                return self._span_of_u8(expr.span)
            return (self._builtin_generic_method_ret(receiver, expr.method)
                    or self._source_method_ret(receiver, expr.method)
                    or rast.NamedType(expr.span, 'unknown', []))
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
        receiver_sig = fn_sig if own_method else None

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
            # Named as ritz1 names it, not by its linked name (AGAST #4266).
            instance = (display_generic_name(receiver.name, receiver.args)
                        if receiver.args else instance_display_name(receiver.name))
            self._slot_error(ref_rules.no_method(expr.method, instance),
                expr.name_span or expr.span)
            return rast.NamedType(expr.span, 'unknown', [])

        if fn_sig is None:
            # Try just the method name
            tried_names.append(expr.method)
            fn_sig = self.functions.get(expr.method)

        if fn_sig is None:
            dispatched = self._emitter_dispatched(receiver, expr)
            if dispatched is not None:
                for arg in expr.args:
                    self._infer_type(arg)
                return dispatched

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

        if fn_sig.ret_type is None:
            return rast.NamedType(expr.span, 'void', [])
        return self._method_ret(fn_sig, receiver, own_method)

    # `o.is_some()` and kin: bool, lowered by the emitter itself.
    BUILTIN_PREDICATES = {'Option': ('is_some', 'is_none'), 'Result': ('is_ok', 'is_err')}

    def _method_ret(self, fn_sig, receiver: rast.Type, own_method: bool) -> rast.Type:
        """`fn_sig`'s return type for a method call on `receiver` (AGAST
        #3554): `Self` is the receiver, and a generic receiver's type args
        substitute the impl's type params (an impl method)."""
        ret = fn_sig.ret_type
        if isinstance(ret, rast.NamedType) and ret.name == 'Self' and not ret.args:
            return receiver
        if not isinstance(receiver, rast.NamedType):
            return ret
        if own_method:
            params = [] if fn_sig.type_params else fn_sig.owner_params
        else:
            params = []
        if params and len(params) == len(receiver.args):
            return TypeSubstitution(dict(zip(params, receiver.args))).apply(ret)
        return ret

    def _builtin_generic_method_ret(self, receiver: rast.Type,
                                    method: str) -> Optional[rast.Type]:
        """`r.m()`'s type on an Option, Result or Span instance: its impl's
        method, else for `unwrap` and kin the payload; None when none says.
        Not a free `option_<m>`: method syntax reaches only impls (R66)."""
        if not (isinstance(receiver, rast.NamedType) and receiver.args
                and receiver.name in BUILTIN_GENERICS):
            return None
        if method in self.BUILTIN_PREDICATES.get(receiver.name, ()):
            # The emitter's own predicates, ahead of ritzlib's i32 fns.
            return rast.NamedType(receiver.span, 'bool', [])
        sig = self.functions.get(f"{receiver.name}_{method}")
        if sig is not None and sig.ret_type is not None:
            return self._method_ret(sig, receiver, True)
        if method in ('unwrap', 'expect', 'unwrap_or', 'unwrap_or_default') \
                and receiver.name in ('Result', 'Option'):
            return receiver.args[0]
        return None

    def _instance_unwrap_ret(self, receiver: rast.Type, method: str) -> Optional[rast.Type]:
        """`o.unwrap()`'s type on a monomorphised `Option$G` or `Result$G$E`:
        the `Some` / `Ok` payload, as the emitter's _try_emit_enum_unwrap_method
        gives it. Imported from ritzlib, Option and Result are declared enums,
        instantiated before the checker runs; untyped, a field of the binding
        was let into an `@T` slot (AGAST #3982). None for anything else."""
        if method != 'unwrap' or not isinstance(receiver, rast.NamedType) or receiver.args:
            return None
        variant = {'Option': 'Some', 'Result': 'Ok'}.get(receiver.name.split('$', 1)[0])
        enum = self.enums.get(receiver.name) if '$' in receiver.name else None
        if variant is None or enum is None:
            return None
        for v in enum.variants:
            if v.name == variant and len(v.fields) == 1:
                return v.fields[0]
        return None

    def _is_user_type_without(self, receiver: rast.Type, type_name: str, method: str) -> bool:
        """Is `receiver` a non-generic struct or enum the emitter would find
        no `method` on? Its impl methods (`Foo_cmp`) were looked
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
                and f"StrView_{method}" not in self.functions)

    @staticmethod
    def _is_strview_as_bytes(receiver: rast.Type, expr: rast.MethodCall) -> bool:
        """Is `expr` the emitter's built-in `s.as_bytes()` on a StrView (by
        value or through a pointer, `receiver` already stripped)? It is a
        `Span<u8>` of the view's bytes (LANGUAGE_SPEC §3.5, AGAST #3599).
        With arguments the emitter refuses it, so it gets no type here."""
        return (isinstance(receiver, rast.NamedType) and receiver.name == 'StrView'
                and expr.method == 'as_bytes' and not expr.args)

    @staticmethod
    def _span_of_u8(span) -> rast.Type:
        return rast.NamedType(span, 'Span', [rast.NamedType(span, 'u8', [])])

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

    def _source_method_ret(self, receiver: rast.Type, method: str) -> Optional[rast.Type]:
        """What a non-generic built-in receiver's source method returns:
        ritzlib's `impl StrView` declares `parse_i64` (`StrView_parse_i64`)
        `-> Option<i64>`. None for a generic receiver, whose `T` this can't
        substitute, or no such method.  Untyped, `s.parse_i64().unwrap_or(0)`
        named no instance, so monomorph wanted `unwrap_or` on every Result
        too, and a move-only one was refused (AGAST #4928)."""
        if not isinstance(receiver, rast.NamedType) or receiver.args:
            return None
        if receiver.name in BUILTIN_GENERICS:
            return None
        sig = self.functions.get(f"{self._get_type_name(receiver)}_{method}")
        if sig is None or sig.ret_type is None:
            return None
        return sig.ret_type

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
        sig = self.functions.get(f"{type_name}_{expr.method}")
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
        if self._type_receiver_name(expr.expr) in self.enums:
            enum = self.enums[expr.expr.name]
            if any(v.name == expr.field for v in enum.variants):
                return rast.NamedType(expr.span, enum.name, [])

        base_type = self._infer_type(expr.expr)

        # Unwrap pointers/refs for field access
        inner_type = self._strip_indirection(base_type)
        if self._is_opaque(inner_type) or (
                isinstance(inner_type, rast.NamedType)
                and inner_type.name in BUILTIN_GENERICS
                and inner_type.name not in self.structs):
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

        if self._refuse_unknown_struct_member(expr, base_type):
            return rast.NamedType(expr.span, 'unknown', [])

        if self._refuse_primitive_member(expr, base_type, inner_type):
            return rast.NamedType(expr.span, 'unknown', [])

        struct_info = self.structs.get(inner_type.name)
        if struct_info is None:
            self._error(f"type {inner_type.name} has no fields", expr.span)
            return rast.NamedType(expr.span, 'unknown', [])

        # Find field: a generic struct's at the receiver's type args (#3554).
        for field_name, field_type in struct_info.fields:
            if field_name == expr.field:
                if struct_info.type_params and \
                        len(inner_type.args) == len(struct_info.type_params):
                    return TypeSubstitution(dict(zip(
                        struct_info.type_params, inner_type.args))).apply(field_type)
                return field_type

        # Not S's own: through `Deref`, its target's (§7.7). The emitter words
        # rule 5's errors (deref_rules.py), a write through only `Deref` too.
        target = self._deref_field(inner_type, expr.field)
        if target is not None:
            return target

        self._error(f"struct '{struct_info.name}' has no field '{expr.field}'", expr.span)
        return rast.NamedType(expr.span, 'unknown', [])

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

    def _refuse_primitive_member(self, expr: rast.Field, base_type: rast.Type,
                                 inner_type: rast.NamedType) -> bool:
        """`p.len` where `p` is a `*i32`, or `x.len` where `x` is an `i64`
        (AGAST #4155): a scalar has no fields, so one located error at the
        base, naming it and its type, in ritz1's words (emitter_expr_access.ritz,
        primitive_member_refused).  The emitter raised a ValueError traceback.
        True when `expr` is that case."""
        resolved = self._resolve_alias(inner_type)
        if (not isinstance(resolved, rast.NamedType) or resolved.args
                or resolved.name not in PRIMITIVES or resolved.name in self.structs):
            return False
        what = (f"`{expr.expr.name}`" if isinstance(expr.expr, rast.Ident)
                else "this")
        self._slot_error(f"{what} has type `{self._type_str(base_type)}`, which is not a "
                         f"struct: it has no field `{expr.field}`", expr.expr.span)
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

        # `p[1..3]` is a slice of it, not an element: of a Vec<T>, through
        # any pointers, a Vec<T> (vec_slice<T>, AGAST #2451).
        if isinstance(expr.index, rast.Range):
            vec = self._strip_indirection(base_type)
            if isinstance(vec, rast.NamedType) and vec.name == 'Vec' and vec.args:
                return vec
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
            if isinstance(named, rast.NamedType):
                if named.name in ('Vec', 'Span') and len(named.args) == 1:
                    return named.args[0]
                if named.name == 'String' and not named.args:
                    return rast.NamedType(named.span, 'u8', [])
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
            # A struct with an `impl Index`: `mk()[2]` on a `*Tally` is the
            # pointee's `index`, as the emitter dispatches it (AGAST #4260)
            index = self.functions.get(f"{inner.name}_index")
            if index is not None and index.ret_type is not None:
                return self._strip_indirection(index.ret_type)
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
            # Its values are typed still: a built-in (`Span`) is a struct
            # monomorph knows, and binds its args from them (AGAST #3554).
            for _, value in expr.fields:
                self._infer_type(value)
            return rast.NamedType(expr.span, expr.name, [])

        # Check all fields are provided and have correct types
        provided_fields = {name: value for name, value in expr.fields}
        expected_fields = {name: ty for name, ty in struct_info.fields}
        # A spelled-out `Box2<u8> { v: .. }`: its fields at those args, so `v`
        # is a u8 and a T in it is that field's error (AGAST #3424).
        params = struct_info.type_params or []
        if params and expr.type_args and len(expr.type_args) == len(params):
            subst = TypeSubstitution(dict(zip(params, expr.type_args)))
            expected_fields = {name: subst.apply(ty) for name, ty in expected_fields.items()}

        for field_name in provided_fields:
            if field_name not in expected_fields:
                self._error(f"struct '{expr.name}' has no field '{field_name}'", expr.span)

        pairs = []
        for name, value in expr.fields:
            if name in expected_fields:
                value_type = self._infer_into(value, expected_fields[name])
                pairs.append((expected_fields[name], value,
                              None if self._is_unknown(value_type) else self._plain(value_type)))
                if not self._value_fits(value, value_type, expected_fields[name]):
                    self._misfit(value, value_type, expected_fields[name],
                                 f"field '{name}': expected {self._type_str(expected_fields[name])}, "
                                 f"got {self._type_str(value_type)}", value.span)

        if expr.type_args:
            return rast.NamedType(expr.span, expr.name, list(expr.type_args))
        # An args-less generic literal is the instance its fields bind (§9.2
        # rule 2, as monomorph infers it; AGAST #3554); unbound, it's left bare
        # for monomorph to report.
        bound, conflict = bind_type_params(params, pairs, self._resolve_alias)
        if params and all(tp in bound and tp not in conflict for tp in params):
            return rast.NamedType(expr.span, expr.name, [bound[tp] for tp in params])
        return rast.NamedType(expr.span, expr.name, [])

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

        result_type, result_leaves = None, False
        for arm in expr.arms:
            self._push_scope()
            self._check_pattern(arm.pattern, match_type)
            if arm.guard:
                guard_type = self._infer_type(arm.guard)
                if not self._is_bool_or_opaque(guard_type):
                    self._error(f"match guard must be bool", arm.guard.span)

            arm_type = self._infer_arm(arm.body, slot, discarded)
            # The first arm that yields a known type decides (as the
            # emitter's _note_match_result_type did, #4068): an `unknown` arm
            # (`s[1..3]` of a generic's Span) or one that leaves (a block
            # ending in `return`, typed void) says nothing.
            leaves = arm_diverges(arm.body)
            if result_type is None or (
                    (self._is_unknown(result_type) or result_leaves)
                    and not self._is_unknown(arm_type) and not leaves):
                result_type, result_body, result_leaves = arm_type, arm.body, leaves
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
            elif self._declares_variant(expected_type, pattern.name):
                # The scrutinee's own enum, as the emitter takes it: not the
                # last one registered with a variant of the name, a unit
                # `SlugVerdict.Ok` beside a Result's `Ok(v)` (AGAST #3556).
                enum_name = self._strip_indirection(expected_type).name
            elif self._builtin_variant_payload(pattern, expected_type) is not None:
                enum_name = None
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
                    # A generic enum's payload at the scrutinee's type args:
                    # `Some(x)` of an Option<Vec<i32>> binds a Vec<i32>, not
                    # a `T` (AGAST #3554).
                    scrut = self._strip_indirection(expected_type)
                    subst = None
                    if (enum_info.type_params and isinstance(scrut, rast.NamedType)
                            and scrut.name == enum_name
                            and len(scrut.args) == len(enum_info.type_params)):
                        subst = TypeSubstitution(dict(zip(enum_info.type_params, scrut.args)))
                    for variant in enum_info.variants:
                        if variant.name == pattern.name:
                            # Bind sub-patterns to variant field types
                            for sub_pat, field_type in zip(pattern.fields, variant.fields):
                                self._check_pattern(
                                    sub_pat, subst.apply(field_type) if subst else field_type)
                            break
                    return
            # An emitter-instantiated Option / Result (undeclared here): its
            # payload is the scrutinee's type arg all the same, `Err(x)` of a
            # Result<T, E> an E.  Monomorph reads it from the table: it has
            # no binding types of its own to fall back on (AGAST #4099).
            payload = self._builtin_variant_payload(pattern, expected_type)
            for sub_pat in pattern.fields:
                self._check_pattern(
                    sub_pat, payload or rast.NamedType(pattern.span, 'unknown', []))
        elif isinstance(pattern, rast.StructPattern):
            struct_info = self.structs.get(pattern.name)
            if struct_info:
                field_types = {name: ty for name, ty in struct_info.fields}
                for field_name, sub_pat in pattern.fields:
                    if field_name in field_types:
                        self._check_pattern(sub_pat, field_types[field_name])




    # A built-in variant's payload: the index of its scrutinee's type arg.
    BUILTIN_VARIANT_PAYLOADS = {('Option', 'Some'): 0, ('Result', 'Ok'): 0,
                                ('Result', 'Err'): 1}

    def _builtin_variant_payload(self, pattern: rast.VariantPattern,
                                 expected_type: rast.Type) -> Optional[rast.Type]:
        """`pattern`'s payload type when the scrutinee is a built-in Option /
        Result with its type args (`Ok(x)` of Result<T, E> is T), else None."""
        scrut = self._strip_indirection(expected_type)
        if not isinstance(scrut, rast.NamedType):
            return None
        idx = self.BUILTIN_VARIANT_PAYLOADS.get((scrut.name, pattern.name))
        if idx is None or idx >= len(scrut.args):
            return None
        return copy.copy(scrut.args[idx])

    def _error(self, message: str, span: Optional[rast.Span]):
        """Record a type error (ritz0._check_types reports it)."""
        self.errors.append(TypeError(message, span))

    def _slot_error(self, message: str, span: Optional[rast.Span],
                    after_moves: bool = False):
        """Record a slot error (reported on every compile)."""
        self.errors.append(TypeError(message, span, after_moves, slot=True))
