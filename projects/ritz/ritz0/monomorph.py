"""
Ritz Monomorphization Pass

This pass transforms generic code into specialized (monomorphized) code.
Each instantiation of a generic type or function with concrete type arguments
results in a specialized version being generated.

Example:
    struct Pair<T>
        first: T
        second: T

    fn swap<T>(p: *Pair<T>) -> i32
        ...

    # Usage:
    var p: Pair<i32> = Pair<i32> { first: 1, second: 2 }
    swap<i32>(&p)

After monomorphization:
    struct Pair_i32
        first: i32
        second: i32

    fn swap_i32(p: *Pair_i32) -> i32
        ...

    var p: Pair_i32 = Pair_i32 { first: 1, second: 2 }
    swap_i32(&p)
"""

from typing import Dict, List, Set, Tuple, Optional
import copy
import dataclasses
import ritz_ast as rast
from typed import Typed, typed_of, type_bodies
from monomorph_core import (  # noqa: F401 -- re-exported: monomorph's public names
    GenericInferError, InstantiationRecursionError, MAX_INSTANCE_DEPTH,
    TypeSubstitution, bind_type_params, map_child_nodes, mangle_generic_name,
    mangle_type_name, note_instance_display, resolve_alias_in, type_aliases)
from monomorph_infer import MonoInferMixin
from trait_bounds import TraitImpls, bound_error
from monomorph_rewrite import MonoRewriteMixin


class Monomorphizer(MonoInferMixin, MonoRewriteMixin):
    """
    Monomorphizes generic code.

    Process:
    1. Collect all generic struct and function definitions
    2. Walk the AST to find all instantiations
    3. Generate specialized versions for each unique instantiation
    4. Rewrite the AST to use the specialized versions
    """

    def __init__(self):
        # Generic definitions: name -> definition
        self.generic_structs: Dict[str, rast.StructDef] = {}
        self.generic_enums: Dict[str, rast.EnumDef] = {}
        self.generic_functions: Dict[str, rast.FnDef] = {}
        # Generic impl blocks: type_name -> list of impl blocks
        # e.g., "Box" -> [ImplBlock(trait_name="Drop", ...)]
        self.generic_impls: Dict[str, List[rast.ImplBlock]] = {}

        # Instantiations found: (base_name, tuple of type_args as strings) -> mangled name
        self.struct_instantiations: Dict[Tuple[str, Tuple[str, ...]], str] = {}
        self.enum_instantiations: Dict[Tuple[str, Tuple[str, ...]], str] = {}
        self.function_instantiations: Dict[Tuple[str, Tuple[str, ...]], str] = {}

        # Generated specialized items
        self.specialized_structs: List[rast.StructDef] = []
        self.specialized_enums: List[rast.EnumDef] = []
        self.specialized_functions: List[rast.FnDef] = []
        self.specialized_impls: List[rast.ImplBlock] = []

        # AGAST #3617: an inherent generic impl's method is specialised for an
        # instance only once a call names it there, as a generic fn is.
        # `_impl_instances`: base -> [(type_args_key, mangled)] seen so far;
        # `_wanted_methods`: (base, type_args_key, method) a call names, in
        # discovery order; `_wild_methods`: methods named on a receiver whose
        # type is unknown, wanted on every instance; `_impl_shells`: the
        # specialised block per (generic impl, instance), made at its first
        # method.  Trait impls are still specialised whole: the compiler
        # calls their methods itself (drop, index, ...).
        self._impl_instances: Dict[str, List[Tuple[Tuple[str, ...], str]]] = {}
        self._wanted_methods: Dict[Tuple[str, Tuple[str, ...], str], None] = {}
        self._wild_methods: Dict[str, None] = {}
        self._impl_shells: Dict[Tuple[int, str], rast.ImplBlock] = {}
        self._done_methods: Set[Tuple[str, Tuple[str, ...], str]] = set()

        # Variable type tracking for slice/index syntax
        # Maps variable name -> declared type (for current scope)
        self.var_types: Dict[str, rast.Type] = {}

        # Which types implement which traits, for bound checks (§11.5).
        self.trait_impls: Optional[TraitImpls] = None
        # (kind, generic, args key) -> the type args at the instance's first
        # use, as written: a failed bound is located there (AGAST #3468).
        self._first_use: Dict[Tuple[str, str, Tuple[str, ...]], List[rast.Type]] = {}

        # Mangled type key -> the actual type it was mangled from.
        # Mangling is lossy, so keep the originals for _parse_type_args_key.
        self.type_args_by_key: Dict[str, rast.Type] = {}

        # Non-generic function name -> definition (a call's literal slots).
        self.fn_signatures: Dict[str, rast.FnDef] = {}

        # All struct definitions by name (for field-type inference).
        self.struct_defs: Dict[str, rast.StructDef] = {}

        # All enum definitions by name, generic or not: a match arm's
        # `Hit(x)` binds x at Hit's payload type (AGAST #2725).
        self.enum_defs: Dict[str, rast.EnumDef] = {}

        # Non-generic impl methods: type name -> method name -> definition
        # (a method call's literal slots).
        self.impl_methods: Dict[str, Dict[str, rast.FnDef]] = {}

        # Expected type of the value currently being visited (return type or
        # `let` annotation). Resolves associated calls like `Span.empty()`
        # whose type argument is only implied by context.
        self.expected_type: Optional[rast.Type] = None
        self.current_ret_type: Optional[rast.Type] = None

        # The slot of each args-less generic struct literal, by id (§9.2).
        self._lit_slots: Dict[int, rast.Type] = {}
        self._infer_ret_type: Optional[rast.Type] = None

        # Each expression's type comes from the typing pass's table (AGAST
        # #3554).  An instance's body is a copy: `_origin` maps each node
        # _specialize_expr built to the template node it copies (a leaf is
        # shared, not copied), and `_instance_subst` is the instance's
        # substitution while _scan_for_new_instantiations walks it.
        self._typed: Optional[Typed] = None
        self._origin: Dict[int, Tuple[rast.Expr, rast.Expr]] = {}
        self._instance_subst: Optional['TypeSubstitution'] = None
        # Names an untyped `let t = (1, 2)` binds: a tuple literal is
        # untyped to inference (#3064), as ritz1 has it, though the table
        # types it.  Per fn, as var_types is.
        self._tuple_lit_names: Set[str] = set()

    def _type_to_key(self, ty: rast.Type) -> str:
        """Convert a type to a string key for deduplication."""
        key = mangle_type_name(ty)
        # Remember the type behind the mangled key. Reconstructing a type from
        # its mangled name is lossy: `Span<u8>` mangles to "Span_u8", which
        # parses back as an *opaque* NamedType called "Span_u8" with no type
        # arguments. Downstream that looks like an unknown struct, so e.g. a
        # `Span<u8>` payload bound out of `Result<Span<u8>, E>` lost its
        # spanness and could no longer be indexed or sliced.
        if key not in self.type_args_by_key:
            self.type_args_by_key[key] = copy.deepcopy(ty)
        return key

    def _type_args_to_key(self, type_args: List[rast.Type]) -> Tuple[str, ...]:
        """Convert type arguments to a tuple key for deduplication."""
        return tuple(self._type_to_key(arg) for arg in type_args)

    def monomorphize(self, module: rast.Module) -> rast.Module:
        """Monomorphize a module, returning a new module with generics specialized."""
        self._typed = typed_of(module)

        # Phase 0: Collect trait implementations for bound checking
        self.trait_impls = TraitImpls(module.items)

        # Phase 1: Collect generic definitions
        self._collect_generics(module)

        # Phase 1b: `f(args)` to a generic `f<T>` gets its type args from its
        # arguments (LANGUAGE_SPEC section 4.4, AGAST #1982), so every later
        # phase sees the call as if it were written `f<T>(args)`.
        self._infer_call_type_args(module)

        # Phase 2: Find all instantiations
        self._find_instantiations(module)

        # Phase 3: Generate specialized versions (iterative until fixpoint)
        # This is needed because generic functions may call other generic functions
        # e.g., vec_push<T> calls vec_ensure_cap<T> -> vec_push<i32> calls vec_ensure_cap<i32>
        self._generate_specializations_iterative()

        # Phase 4: Rewrite the AST
        new_items = self._rewrite_items(module.items)

        return rast.Module(module.span, new_items)

    def _note_use(self, kind: str, name: str, key: Tuple[str, ...],
                  type_args: List[rast.Type]) -> None:
        """Remember the type args an instance is first named with: a failed
        bound is reported at the one that misses it (§11.5)."""
        self._first_use.setdefault((kind, name, key), list(type_args))

    def _check_bounds(self, kind: str, generic: str, params: List[str],
                      key: Tuple[str, ...], type_args: List[rast.Type],
                      bounds: dict, owner: Optional[str] = None) -> None:
        """Raise TraitBoundError when `type_args` miss one of `bounds` (§11.5,
        LARB R55).  `owner` names the generic in the message when it isn't
        `generic` itself (an impl's bounds are reported on its type)."""
        err = bound_error(self.trait_impls, owner or generic, params, type_args, bounds,
                          self._first_use.get((kind, generic, key)))
        if err is not None:
            raise err

    def _collect_generics(self, module: rast.Module) -> None:
        """Collect all generic struct, enum, function, and impl block definitions."""
        for item in module.items:
            if isinstance(item, rast.StructDef) and item.is_generic():
                self.generic_structs[item.name] = item
                self.struct_defs[item.name] = item
            elif isinstance(item, rast.StructDef):
                self.struct_defs[item.name] = item
            elif isinstance(item, rast.EnumDef) and item.is_generic():
                self.generic_enums[item.name] = item
                self.enum_defs[item.name] = item
            elif isinstance(item, rast.EnumDef):
                self.enum_defs[item.name] = item
            elif isinstance(item, rast.FnDef) and item.is_generic():
                self.generic_functions[item.name] = item
            elif isinstance(item, rast.FnDef):
                # Non-generic signatures still matter: they let us infer the
                # type of `let x = f()` and so register instantiations for the
                # generic machinery x is later used with (`x[i]` -> vec_get<T>).
                self.fn_signatures[item.name] = item
            elif isinstance(item, rast.ImplBlock) and item.type_params:
                # Generic impl block like `impl<T> Drop for Box<T>`
                if item.type_name not in self.generic_impls:
                    self.generic_impls[item.type_name] = []
                self.generic_impls[item.type_name].append(item)
            elif isinstance(item, rast.ImplBlock):
                methods = self.impl_methods.setdefault(item.type_name, {})
                for method in item.methods:
                    methods.setdefault(method.name, method)


    def _find_instantiations(self, module: rast.Module) -> None:
        """Walk the AST to find all generic instantiations."""
        if self._typed is None:
            # Called without monomorphize() (a unit test of this phase).
            self._typed = typed_of(module)
        for item in module.items:
            self._visit_item(item)

    def _visit_item(self, item: rast.Item, impl_type_name: Optional[str] = None) -> None:
        """Visit an item to find instantiations."""
        if isinstance(item, rast.FnDef):
            # Skip generic functions - they contain calls like vec_grow<T>
            # which are not concrete instantiations. These calls only become
            # concrete during specialization (e.g., vec_grow<i32>).
            if item.is_generic():
                return
            # Clear variable types for new function scope
            self.var_types = {}
            self._tuple_lit_names = set()
            # Register parameter types
            for param in item.params:
                self._visit_type(param.type)
                param_type = param.type
                if param_type is None and param.name == 'self' and impl_type_name:
                    # `fn m(self)` in an impl block: self is the impl type.
                    param_type = rast.NamedType(item.span, impl_type_name, [])
                self.var_types[param.name] = param_type
            # Visit return type
            self.current_ret_type = item.ret_type
            if item.ret_type:
                self._visit_type(item.ret_type)
            # Visit body
            self._visit_block(item.body)
        elif isinstance(item, rast.StructDef):
            # Visit field types
            for _, field_type in item.fields:
                self._visit_type(field_type)
        elif isinstance(item, rast.VarDef):
            # A module-level `var gb: Box<H>` instantiates Box<H> even when no
            # fn names it; unvisited, the global fell back to `i8` (AGAST #3016).
            if item.type is not None:
                self._visit_type(item.type)
        elif isinstance(item, rast.ImplBlock):
            # Skip generic impl blocks - they're handled during specialization
            if item.type_params:
                return
            # Visit non-generic impl blocks to find generic calls in their methods
            # e.g., impl Drop for String { fn drop() { vec_drop<u8>(...) } }
            for method in item.methods:
                self._visit_item(method, impl_type_name=item.type_name)

    def _visit_type(self, ty: rast.Type) -> None:
        """Visit a type to find instantiations."""
        if isinstance(ty, rast.NamedType):
            if ty.args and ty.name in self.generic_structs:
                # This is a generic struct instantiation
                key = (ty.name, self._type_args_to_key(ty.args))
                self._note_use('struct', *key, ty.args)
                if key not in self.struct_instantiations:
                    mangled = mangle_generic_name(ty.name, ty.args)
                    self.struct_instantiations[key] = mangled
            elif ty.args and ty.name in self.generic_enums:
                # This is a generic enum instantiation
                key = (ty.name, self._type_args_to_key(ty.args))
                self._note_use('enum', *key, ty.args)
                if key not in self.enum_instantiations:
                    mangled = mangle_generic_name(ty.name, ty.args)
                    self.enum_instantiations[key] = mangled
            # Visit type arguments
            for arg in ty.args:
                self._visit_type(arg)
        elif isinstance(ty, rast.PtrType):
            self._visit_type(ty.inner)
        elif isinstance(ty, rast.RefType):
            self._visit_type(ty.inner)
        elif isinstance(ty, rast.ArrayType):
            self._visit_type(ty.inner)
        elif isinstance(ty, rast.FnType):
            for p in ty.params:
                self._visit_type(p)
            if ty.ret:
                self._visit_type(ty.ret)
        elif isinstance(ty, rast.TupleType):
            for e in ty.elements:
                self._visit_type(e)
        elif isinstance(ty, rast.VectorType):
            self._visit_type(ty.inner)

    def _visit_block(self, block: rast.Block) -> None:
        """Visit a block to find instantiations."""
        for stmt in block.stmts:
            self._visit_stmt(stmt)
        if block.expr:
            self._visit_expr(block.expr)

    def _visit_stmt(self, stmt: rast.Stmt) -> None:
        """Visit a statement to find instantiations."""
        if isinstance(stmt, rast.LetStmt):
            if stmt.type:
                self._visit_type(stmt.type)
                self._tuple_lit_names.discard(stmt.name)
                # Track variable type
                self.var_types[stmt.name] = stmt.type
                self.expected_type = stmt.type
            elif stmt.value is not None:
                # No explicit type — try to infer from the rhs so that subsequent
                # method calls (`v.push(...)`) can want their impl methods.
                self._note_tuple_lit_let(stmt)
                inferred = self._type_of(stmt.value)
                if inferred is not None:
                    self.var_types[stmt.name] = inferred
                    # Treat the inferred type like a real annotation so that
                    # generic struct/enum payloads get registered for monomorph.
                    self._visit_type(inferred)
            if stmt.value:
                self._visit_expr(stmt.value)
            self.expected_type = None
        elif isinstance(stmt, rast.VarStmt):
            if stmt.type:
                self._visit_type(stmt.type)
                self._tuple_lit_names.discard(stmt.name)
                # Track variable type
                self.var_types[stmt.name] = stmt.type
            elif stmt.value is not None:
                self._note_tuple_lit_let(stmt)
                inferred = self._type_of(stmt.value)
                if inferred is not None:
                    self.var_types[stmt.name] = inferred
                    self._visit_type(inferred)
            if stmt.value:
                self._visit_expr(stmt.value)
        elif isinstance(stmt, rast.LetTupleStmt):
            # `let (a, b) = mk<i16>(...)`: the initialiser's generic calls
            # must be registered like a `let`'s, or no `mk$i16` is ever
            # specialised and the emitter refuses the call (AGAST #2593).
            self._visit_expr(stmt.value)
        elif isinstance(stmt, rast.ExprStmt):
            self._visit_expr(stmt.expr)
        elif isinstance(stmt, rast.AssignStmt):
            self._visit_expr(stmt.target)
            self._visit_expr(stmt.value)
        elif isinstance(stmt, rast.ReturnStmt):
            if stmt.value:
                saved = self.expected_type
                self.expected_type = self.current_ret_type
                self._visit_expr(stmt.value)
                self.expected_type = saved
        elif isinstance(stmt, rast.WhileStmt):
            self._visit_expr(stmt.cond)
            self._visit_block(stmt.body)
        elif isinstance(stmt, (rast.DeferStmt, rast.UnsafeBlock)):
            # An `unsafe` body's generic calls were never registered, so
            # one called only there was never specialised (AGAST #2248).
            self._visit_block(stmt.body)
        elif isinstance(stmt, rast.ForStmt):
            self._visit_expr(stmt.iter)
            self._visit_block(stmt.body)
        elif isinstance(stmt, rast.AssertStmt):
            self._visit_expr(stmt.condition)

    def _visit_expr(self, expr: rast.Expr) -> None:
        """Visit an expression to find instantiations."""
        if isinstance(expr, rast.Call):
            self._visit_expr(expr.func)
            for arg in expr.args:
                self._visit_expr(arg)
            # Check for generic function call
            if expr.type_args and isinstance(expr.func, rast.Ident):
                fn_name = expr.func.name
                if fn_name in self.generic_functions:
                    key = (fn_name, self._type_args_to_key(expr.type_args))
                    self._note_use('fn', *key, expr.type_args)
                    if key not in self.function_instantiations:
                        mangled = mangle_generic_name(fn_name, expr.type_args)
                        self.function_instantiations[key] = mangled
            # AGAST #1824: format_into(sink, "...") appends through
            # `sink.push_bytes(..)`, so a generic sink (`*Vec<u8>`) wants
            # that impl method (Vec$u8.push_bytes, and through it
            # vec_push_bytes<u8>) even when nothing else calls it (#4303).
            if (isinstance(expr.func, rast.Ident) and expr.func.name == 'format_into'
                    and expr.args):
                self._want_called_method(
                    rast.MethodCall(expr.span, expr.args[0], 'push_bytes', []))
        elif isinstance(expr, rast.StructLit):
            for _, field_expr in expr.fields:
                self._visit_expr(field_expr)
            # Check for generic struct instantiation
            if expr.type_args and expr.name in self.generic_structs:
                key = (expr.name, self._type_args_to_key(expr.type_args))
                self._note_use('struct', *key, expr.type_args)
                if key not in self.struct_instantiations:
                    mangled = mangle_generic_name(expr.name, expr.type_args)
                    self.struct_instantiations[key] = mangled
        elif isinstance(expr, rast.BinOp):
            self._visit_expr(expr.left)
            self._visit_expr(expr.right)
        elif isinstance(expr, rast.UnaryOp):
            self._visit_expr(expr.operand)
        elif isinstance(expr, rast.Index):
            self._visit_expr(expr.expr)
            self._visit_expr(expr.index)
            # Register vec_get<T> for Vec<T> indexing sugar, and vec_slice<T>
            # for `v[lo..hi]`, which lowers as `v[lo:hi]` does (AGAST #2451).
            self._register_index_instantiation(expr)
            if isinstance(expr.index, rast.Range):
                self._register_slice_instantiation(expr)
        elif isinstance(expr, rast.Field):
            self._visit_expr(expr.expr)
        elif isinstance(expr, rast.MethodCall):
            self._visit_expr(expr.expr)
            for arg in expr.args:
                self._visit_expr(arg)
            # `v.pop()` names the impl method Vec<T>.pop; specialising it
            # instantiates the vec_pop<T> its body calls (AGAST #4303).
            self._want_called_method(expr)
        elif isinstance(expr, rast.If):
            self._visit_expr(expr.cond)
            self._visit_block(expr.then_block)
            if expr.else_block:
                self._visit_block(expr.else_block)
        elif isinstance(expr, rast.Match):
            self._visit_expr(expr.expr)
            if expr.ctor_type is not None:
                self._visit_type(expr.ctor_type)   # its instance (#2437)
            for arm in expr.arms:
                # `Some(x) => x[1..3]`: the table types `x` at the payload's
                # type, per arm (AGAST #2725, #4099).
                if arm.guard:
                    self._visit_expr(arm.guard)
                self._visit_expr(arm.body)
        elif isinstance(expr, rast.Block):
            self._visit_block(expr)
        elif isinstance(expr, rast.ArrayLit):
            for elem in expr.elements:
                self._visit_expr(elem)
        elif isinstance(expr, rast.ArrayFill):
            self._visit_expr(expr.value)
        elif isinstance(expr, rast.Cast):
            self._visit_expr(expr.expr)
            self._visit_type(expr.target)
        elif isinstance(expr, rast.HeapExpr):
            # `heap W<P> { .. }` (AGAST #3664): unvisited, W<P> was never
            # instantiated, the rewrite left the literal's bare `W`, and the
            # emitter raised "Unknown struct: W".
            self._visit_expr(expr.expr)
        elif isinstance(expr, rast.TypeExpr):
            # `sizeof(Box<i64>)` (AGAST #3268) may be Box<i64>'s only use:
            # unvisited, it was never instantiated and the rewrite left a
            # bare `Box`, which sized as the unspecialized template.
            self._visit_type(expr.ty)
        elif isinstance(expr, rast.Range):
            if expr.start:
                self._visit_expr(expr.start)
            if expr.end:
                self._visit_expr(expr.end)
        elif isinstance(expr, rast.SliceExpr):
            # Visit the base expression and indices
            self._visit_expr(expr.expr)
            if expr.start:
                self._visit_expr(expr.start)
            if expr.end:
                self._visit_expr(expr.end)
            # If base is an identifier with known Vec<T> type, register vec_slice<T>
            self._register_slice_instantiation(expr)
        else:
            # Every other kind (TupleLit, TryOp, Grouped, ReturnExpr,
            # AssignExpr, InterpString, Await, ...) is walked generically, as
            # _rewrite_expr and _specialize_expr walk theirs (#1937).  Without
            # this, `(W<i64> { .. }, 3)` or `pass<W<i64>>(..)?` named an
            # instance that was never found: the rewrite left the bare `W`
            # and the emitter raised "Unknown struct: W" (AGAST #3676).
            # The visitors return their input, so nothing is rebuilt.
            map_child_nodes(expr, self._visit_expr_child,
                            self._visit_stmt_child, self._visit_type_child)

    def _visit_expr_child(self, expr: rast.Expr) -> rast.Expr:
        self._visit_expr(expr)
        return expr

    def _visit_stmt_child(self, stmt: rast.Stmt) -> rast.Stmt:
        self._visit_stmt(stmt)
        return stmt

    def _visit_type_child(self, ty: rast.Type) -> rast.Type:
        self._visit_type(ty)
        return ty

    def _register_slice_instantiation(self, expr: rast.SliceExpr) -> None:
        """Register vec_slice<T> instantiation for slice expressions on Vec types."""
        var_type = self._type_of(expr.expr)
        while isinstance(var_type, (rast.PtrType, rast.RefType)):
            var_type = var_type.inner
        if not isinstance(var_type, rast.NamedType):
            return

        # Check if it's a Vec<T> type
        if var_type.name == 'Vec' and var_type.args:
            # Need vec_slice<T> and vec_len<T>
            type_args = var_type.args
            for fn_name in ['vec_slice', 'vec_len']:
                if fn_name in self.generic_functions:
                    key = (fn_name, self._type_args_to_key(type_args))
                    if key not in self.function_instantiations:
                        mangled = mangle_generic_name(fn_name, type_args)
                        self.function_instantiations[key] = mangled

    def _register_index_instantiation(self, expr: rast.Index) -> None:
        """Register vec_get<T> instantiation for Vec<T> indexing sugar.

        `v[i]` on a Vec<T> desugars to `vec_get<T>(&v, i)` in the emitter — so
        the monomorphizer needs to specialize vec_get<T> alongside the call.
        """
        var_type = self._type_of(expr.expr)
        while isinstance(var_type, (rast.PtrType, rast.RefType)):
            var_type = var_type.inner
        if not isinstance(var_type, rast.NamedType):
            return

        if var_type.name == 'Vec' and var_type.args:
            type_args = var_type.args
            if 'vec_get' in self.generic_functions:
                key = ('vec_get', self._type_args_to_key(type_args))
                if key not in self.function_instantiations:
                    mangled = mangle_generic_name('vec_get', type_args)
                    self.function_instantiations[key] = mangled

    def _note_tuple_lit_let(self, stmt) -> None:
        """Track whether `stmt` binds its name to an untyped tuple literal."""
        value = stmt.value
        while isinstance(value, rast.Grouped):
            value = value.expr
        if stmt.type is None and isinstance(value, rast.TupleLit):
            self._tuple_lit_names.add(stmt.name)
        else:
            self._tuple_lit_names.discard(stmt.name)

    def _type_of(self, expr: rast.Expr) -> Optional[rast.Type]:
        """`expr`'s type, from the typing pass's table (module.typed, AGAST
        #3554), or None where the table has none or says `unknown`.

        In an instance's body (_scan_for_new_instantiations) a node is a copy
        of, or shared with, the template's, and the template's type is taken
        at the instance's type args.  Two answers are the node's own:
        - a struct literal is the instance its args name; an args-less one's
          are only filled in after the table was made (§9.2);
        - `@x` / `@&x` is a pointer, which `T` binds as `*X` and mangles
          `ptr_` (the emitter's spelling, AGAST #2335), not the `@X` the
          table has.
        """
        if isinstance(expr, rast.StructLit):
            struct_def = self.struct_defs.get(expr.name)
            if struct_def is None or len(struct_def.type_params or []) != len(expr.type_args):
                return None
            return rast.NamedType(expr.span, expr.name, list(expr.type_args))
        if isinstance(expr, rast.Grouped):
            return self._type_of(expr.expr)
        if isinstance(expr, rast.TupleLit) or (
                isinstance(expr, rast.Ident) and expr.name in self._tuple_lit_names):
            return None
        if isinstance(expr, rast.UnaryOp) and expr.op in ('@', '&', '@&', '&mut'):
            inner = self._type_of(expr.operand)
            if inner is None:
                return None
            return rast.PtrType(expr.span, inner, mutable=expr.op in ('@&', '&mut'),
                                shared=expr.op == '@')
        entry = self._origin.get(id(expr))
        node = entry[1] if entry is not None and entry[0] is expr else expr
        ty = self._typed.type_of(node) if self._typed is not None else None
        if ty is None or (isinstance(ty, rast.NamedType) and ty.name == 'unknown'):
            return None
        if self._instance_subst is not None:
            ty = self._instance_subst.apply(ty)
        return ty

    def _generate_specializations_iterative(self) -> None:
        """Generate specialized versions iteratively until no new instantiations are found.

        This is needed because generic functions may call other generic functions.
        For example, vec_push<T> calls vec_ensure_cap<T>. When we specialize
        vec_push<i32>, we discover vec_ensure_cap<i32> which also needs specialization.
        """
        # Track which instantiations we've already processed
        processed_structs: set = set()
        processed_enums: set = set()
        processed_functions: set = set()

        # Iterate until no new instantiations are found.  Everything found in
        # round g is specialised in round g + 1, so the round is the
        # generation (MAX_INSTANCE_DEPTH).  This loop used to stop silently
        # after 100 rounds and leave the emitter to die on an instance nobody
        # had specialised (AGAST #3330).
        generation = 0
        while True:
            # Find new instantiations.
            #
            # These MUST be lists, not sets (AGAST #1286). The keys are
            # `(base_name, type_args_key)` string tuples, so a set comprehension
            # would iterate in `PYTHONHASHSEED`-dependent order — and that order
            # escapes all the way into the emitted IR: the loops below append to
            # `specialized_structs` / `specialized_enums` / `specialized_functions`
            # / `specialized_impls`, which are spliced into the module item list
            # in `_apply_specializations`, which is the order the emitter walks.
            # Same tree, different process, different `.ll` byte-for-byte.
            #
            # A list comprehension inherits the instantiation dicts' insertion
            # order, which is deterministic (driven by module item order and the
            # scan order of `_scan_for_new_instantiations`) and more meaningful
            # than sorting: specializations are emitted in discovery order.
            new_structs = [k for k in self.struct_instantiations if k not in processed_structs]
            new_enums = [k for k in self.enum_instantiations if k not in processed_enums]
            new_functions = [k for k in self.function_instantiations if k not in processed_functions]
            new_methods = self._pending_methods()

            if not new_structs and not new_enums and not new_functions and not new_methods:
                # Fixpoint reached
                break
            if generation == MAX_INSTANCE_DEPTH:
                raise self._recursion_error(new_structs + new_enums + new_functions)
            generation += 1

            # Build struct_manglings lookup for substitution (includes both structs and enums)
            struct_manglings: Dict[str, Dict[Tuple[str, ...], str]] = {}
            for (base_name, type_args_key), mangled_name in self.struct_instantiations.items():
                if base_name not in struct_manglings:
                    struct_manglings[base_name] = {}
                struct_manglings[base_name][type_args_key] = mangled_name
            for (base_name, type_args_key), mangled_name in self.enum_instantiations.items():
                if base_name not in struct_manglings:
                    struct_manglings[base_name] = {}
                struct_manglings[base_name][type_args_key] = mangled_name

            # Generate specialized structs for new instantiations
            for key in new_structs:
                base_name, type_args_key = key
                mangled_name = self.struct_instantiations[key]
                generic_def = self.generic_structs[base_name]
                type_args = self._parse_type_args_key(type_args_key, generic_def.type_params)

                # Check trait bounds before specializing (§11.5)
                self._check_bounds('struct', base_name, generic_def.type_params,
                                   type_args_key, type_args, generic_def.type_param_bounds)

                mapping = dict(zip(generic_def.type_params, type_args))
                # A generic struct named in a field (`a: [2]Box<T>`) is an
                # instance only once T is substituted: register `Box<i32>`
                # before W<i32>'s fields are mangled, or the field keeps the
                # unmangled name and lowers as i8 (AGAST #3080).  Box<i32>'s own
                # fields are specialised next iteration, so nesting recurses.
                self._register_field_instances(generic_def, mapping, struct_manglings)
                subst = TypeSubstitution(mapping, struct_manglings)
                specialized = self._specialize_struct(generic_def, mangled_name, subst)
                self.specialized_structs.append(specialized)
                processed_structs.add(key)

                self._instantiate_impls('struct', base_name, type_args_key, type_args,
                                        mangled_name, struct_manglings)


            # Generate specialized enums for new instantiations
            for key in new_enums:
                base_name, type_args_key = key
                mangled_name = self.enum_instantiations[key]
                generic_def = self.generic_enums[base_name]
                type_args = self._parse_type_args_key(type_args_key, generic_def.type_params)

                # Check trait bounds before specializing (§11.5)
                self._check_bounds('enum', base_name, generic_def.type_params,
                                   type_args_key, type_args, generic_def.type_param_bounds)

                subst = TypeSubstitution(dict(zip(generic_def.type_params, type_args)), struct_manglings)
                specialized = self._specialize_enum(generic_def, mangled_name, subst)
                self.specialized_enums.append(specialized)
                processed_enums.add(key)

                self._instantiate_impls('enum', base_name, type_args_key, type_args,
                                        mangled_name, struct_manglings)


            # Generate specialized functions for new instantiations
            for key in new_functions:
                base_name, type_args_key = key
                mangled_name = self.function_instantiations[key]
                generic_def = self.generic_functions[base_name]
                type_args = self._parse_type_args_key(type_args_key, generic_def.type_params)

                # Check trait bounds before specializing (§11.5)
                self._check_bounds('fn', base_name, generic_def.type_params,
                                   type_args_key, type_args, generic_def.type_param_bounds)

                subst = TypeSubstitution(dict(zip(generic_def.type_params, type_args)), struct_manglings)
                specialized = self._specialize_function(generic_def, mangled_name, subst)
                self.specialized_functions.append(specialized)
                processed_functions.add(key)

                # CRITICAL: Scan the specialized function body for new instantiations
                # This discovers transitive generic calls like vec_ensure_cap<i32>
                self._scan_for_new_instantiations(specialized)

            # Methods calls named last generation (AGAST #3617).
            for base_name, type_args_key, mangled_name, method in new_methods:
                self._specialize_wanted_method(base_name, type_args_key, mangled_name,
                                               method, struct_manglings)

    def _instantiate_impls(self, kind: str, base_name: str, type_args_key: Tuple[str, ...],
                           type_args: List[rast.Type], mangled_name: str,
                           struct_manglings: Dict[str, Dict[Tuple[str, ...], str]]) -> None:
        """A new instance `mangled_name` of `base_name`: specialise its trait
        impls whole, and make its inherent impls' methods available to the
        calls that name them (AGAST #3617)."""
        lazy = False
        for generic_impl in self.generic_impls.get(base_name, ()):
            # An impl's bounds are on its type's args (§11.5).
            self._check_bounds(kind, base_name, generic_impl.type_params,
                               type_args_key, type_args,
                               generic_impl.type_param_bounds,
                               owner=f"impl {base_name}")
            if generic_impl.trait_name is None:
                lazy = True
                continue
            impl_subst = TypeSubstitution(dict(zip(generic_impl.type_params, type_args)),
                                          struct_manglings)
            specialized_impl = self._specialize_impl(generic_impl, mangled_name, impl_subst)
            self.specialized_impls.append(specialized_impl)
            for method in specialized_impl.methods:
                self._scan_for_new_instantiations(method)
        if lazy:
            self._impl_instances.setdefault(base_name, []).append((type_args_key, mangled_name))

    def _inherent_method(self, base_name: str, method: str) -> bool:
        """Whether an inherent generic impl of `base_name` defines `method`."""
        return any(generic_impl.trait_name is None
                   and any(m.name == method for m in generic_impl.methods)
                   for generic_impl in self.generic_impls.get(base_name, ()))

    def _want_called_method(self, expr: rast.MethodCall) -> None:
        """`x.m()` / `T.m()` names inherent method `m` of x's / the slot's
        instance (AGAST #3617)."""
        if not self._impl_instances and not any(
                g.trait_name is None for impls in self.generic_impls.values() for g in impls):
            return
        recv = expr.expr
        if isinstance(recv, rast.TypeExpr):
            self._want_method(recv.ty, expr.method)
            return
        if (isinstance(recv, rast.Ident) and recv.name in self.generic_impls
                and recv.name not in self.var_types):
            # `T.m()`: the instance of the slot the call fills (§11.3).
            expected = self.expected_type
            while isinstance(expected, (rast.PtrType, rast.RefType)):
                expected = expected.inner
            if isinstance(expected, rast.NamedType):
                expected = self._instance_of_mangled(expected)
                if expected.name == recv.name and expected.args:
                    self._want_method(expected, expr.method)
                    return
            self._want_method(None, expr.method)
            return
        self._want_method(self._type_of(recv), expr.method)

    def _want_method(self, receiver: Optional[rast.Type], method: str) -> None:
        """A call names `method` on `receiver`, a type (None: unknown)."""
        while isinstance(receiver, (rast.RefType, rast.PtrType)):
            receiver = receiver.inner
        if receiver is None or (isinstance(receiver, rast.NamedType)
                                and receiver.name == 'unknown'):
            # Its receiver can't be told: wanted on every instance, so a
            # call the scan can't type still finds its method.
            if any(self._inherent_method(b, method) for b in self.generic_impls):
                self._wild_methods.setdefault(method, None)
            return
        if not isinstance(receiver, rast.NamedType):
            return
        receiver = self._instance_of_mangled(receiver)
        if not receiver.args or not self._inherent_method(receiver.name, method):
            return
        key = (receiver.name, self._type_args_to_key(receiver.args), method)
        self._wanted_methods.setdefault(key, None)

    def _instance_of_mangled(self, ty: rast.Type) -> rast.Type:
        """`W<Cell<i32>>` for a mangled `W$Cell_i32` or `W<Cell$i32>`: the
        generic spelling the instance keys are made from.  Any other type
        unchanged."""
        if not isinstance(ty, rast.NamedType):
            return ty
        if ty.args:
            return rast.NamedType(ty.span, ty.name,
                                  [self._instance_of_mangled(a) for a in ty.args])
        if '$' not in ty.name:
            return ty
        for instances in (self.struct_instantiations, self.enum_instantiations):
            for (base_name, type_args_key), mangled in instances.items():
                if mangled == ty.name:
                    generic_def = (self.generic_structs.get(base_name)
                                   or self.generic_enums.get(base_name))
                    params = generic_def.type_params if generic_def else []
                    return rast.NamedType(ty.span, base_name,
                                          self._parse_type_args_key(type_args_key, params))
        return ty

    def _pending_methods(self) -> List[Tuple[str, Tuple[str, ...], str, str]]:
        """(base, type_args_key, mangled, method) wanted on a known instance
        and not yet specialised, in discovery order."""
        pending = []
        seen = set()

        def add(base_name, type_args_key, mangled, method):
            key = (base_name, type_args_key, method)
            if key in self._done_methods or key in seen:
                return
            seen.add(key)
            pending.append((base_name, type_args_key, mangled, method))

        for base_name, type_args_key, method in self._wanted_methods:
            for key, mangled in self._impl_instances.get(base_name, ()):
                if key == type_args_key:
                    add(base_name, type_args_key, mangled, method)
        for method in self._wild_methods:
            for base_name, instances in self._impl_instances.items():
                if self._inherent_method(base_name, method):
                    for type_args_key, mangled in instances:
                        add(base_name, type_args_key, mangled, method)
        return pending

    def _specialize_wanted_method(self, base_name: str, type_args_key: Tuple[str, ...],
                                  mangled_name: str, method: str,
                                  struct_manglings: Dict[str, Dict[Tuple[str, ...], str]]) -> None:
        """Specialise inherent method `method` of `base_name` at one instance,
        then scan it for the instances and methods it names."""
        self._done_methods.add((base_name, type_args_key, method))
        for generic_impl in self.generic_impls.get(base_name, ()):
            if generic_impl.trait_name is not None:
                continue
            for template in generic_impl.methods:
                if template.name != method:
                    continue
                type_args = self._parse_type_args_key(type_args_key, generic_impl.type_params)
                subst = TypeSubstitution(dict(zip(generic_impl.type_params, type_args)),
                                         struct_manglings)
                specialized = self._specialize_function_for_impl(template, subst)
                shell_key = (id(generic_impl), mangled_name)
                shell = self._impl_shells.get(shell_key)
                if shell is None:
                    shell = rast.ImplBlock(generic_impl.span, None, mangled_name, [],
                                           type_params=[], impl_type=None)
                    self._impl_shells[shell_key] = shell
                    self.specialized_impls.append(shell)
                shell.methods.append(specialized)
                self._scan_for_new_instantiations(specialized)

    def _recursion_error(self, pending: List[Tuple[str, Tuple[str, ...]]]) -> InstantiationRecursionError:
        """The error for instances still pending after MAX_INSTANCE_DEPTH rounds.

        Names the first pending type with a generic impl, at that impl: its
        methods are what name the deeper instance.  Pending lists are in
        discovery order, structs first, as ritz1 walks them.  Without such an
        impl, a pending generic fn is the likelier culprit (`f<T>` calling
        `f<Cell<T>>`); failing that, the first pending item.  Either is
        reported at its definition."""
        names = [name for name, _ in pending]
        base = next((n for n in names if self.generic_impls.get(n)), None)
        if base is not None:
            where = self.generic_impls[base][0].span
            shape = f"{base}<{base}<...>> names a deeper instance at every level"
        else:
            base = next((n for n in names if n in self.generic_functions), names[0])
            if base in self.generic_functions:
                where = self.generic_functions[base].span
            else:
                where = (self.generic_structs.get(base) or self.generic_enums.get(base)).span
            shape = "each instance names a deeper one"
        return InstantiationRecursionError(
            f"instantiating `{base}` recurses: {shape} "
            f"(stopped after {MAX_INSTANCE_DEPTH})",
            where)

    def _register_field_instances(self, generic_def: rast.StructDef,
                                  mapping: Dict[str, rast.Type],
                                  struct_manglings: Dict[str, Dict[Tuple[str, ...], str]]) -> None:
        """Register each generic instance a field names once `mapping` is applied.

        `struct_manglings` is updated in place so the caller's substitution of
        this struct's fields already finds the new mangled names.
        """
        bare = TypeSubstitution(mapping)
        for _, field_type in generic_def.fields:
            self._visit_type(bare.apply(field_type))
        for (base_name, type_args_key), mangled in self.struct_instantiations.items():
            struct_manglings.setdefault(base_name, {}).setdefault(type_args_key, mangled)

    def _register_body_instances(self, fn: rast.FnDef, subst: TypeSubstitution) -> None:
        """Register each generic instance a type in `fn` names under `subst`.

        `subst.struct_manglings` is the generation's snapshot, and a body can
        be the first to name an instance: mid<Cell<i32>>'s
        `let c: Cell<T> = leaf<Cell<T>>(Cell<T> { .. })` names Cell<Cell<i32>>.
        Its struct literal registered it as `Cell$Cell_i32` mid-walk, but the
        annotation had missed the snapshot and kept `Cell<Cell$i32>`, which the
        emitter spells `Cell$Cell$i32` (AGAST #3356).  Registering every
        instance first gives both one name, as _register_field_instances does
        for a struct's fields.
        """
        if subst.struct_manglings is None:
            return
        bare = TypeSubstitution(subst.mapping)

        def walk(node):
            return map_child_nodes(node, walk, walk, visit)

        def visit(ty):
            self._visit_type(bare.apply(ty))
            return ty

        walk(fn)
        for instances in (self.struct_instantiations, self.enum_instantiations):
            for (base_name, type_args_key), mangled in instances.items():
                subst.struct_manglings.setdefault(base_name, {}).setdefault(
                    type_args_key, mangled)

    def _scan_for_new_instantiations(self, fn: rast.FnDef) -> None:
        """Scan a specialized function for new generic instantiations.

        When specializing vec_push<i32>, it calls vec_ensure_cap<i32>.
        The call has been rewritten to use the mangled name, but we also need to
        check if the instantiation exists and add it if not.
        """
        saved, self._instance_subst = self._instance_subst, fn.instance_subst
        try:
            self._visit_item(fn)
        finally:
            self._instance_subst = saved

    def _generate_specializations(self) -> None:
        """Generate specialized versions for all found instantiations."""
        # Build struct_manglings lookup: struct_name -> {args_key -> mangled_name}
        struct_manglings: Dict[str, Dict[Tuple[str, ...], str]] = {}
        for (base_name, type_args_key), mangled_name in self.struct_instantiations.items():
            if base_name not in struct_manglings:
                struct_manglings[base_name] = {}
            struct_manglings[base_name][type_args_key] = mangled_name

        # Generate specialized structs
        for (base_name, type_args_key), mangled_name in self.struct_instantiations.items():
            generic_def = self.generic_structs[base_name]
            # Build type substitution
            type_args = self._parse_type_args_key(type_args_key, generic_def.type_params)
            subst = TypeSubstitution(dict(zip(generic_def.type_params, type_args)), struct_manglings)
            specialized = self._specialize_struct(generic_def, mangled_name, subst)
            self.specialized_structs.append(specialized)

        # Generate specialized functions
        for (base_name, type_args_key), mangled_name in self.function_instantiations.items():
            generic_def = self.generic_functions[base_name]
            # Build type substitution
            type_args = self._parse_type_args_key(type_args_key, generic_def.type_params)
            subst = TypeSubstitution(dict(zip(generic_def.type_params, type_args)), struct_manglings)
            specialized = self._specialize_function(generic_def, mangled_name, subst)
            self.specialized_functions.append(specialized)

        # Generate specialized impl blocks for each struct instantiation
        # e.g., if Box<i32> is instantiated and there's `impl<T> Drop for Box<T>`,
        # we generate `impl Drop for Box_i32` with specialized methods
        for (base_name, type_args_key), mangled_struct_name in self.struct_instantiations.items():
            if base_name in self.generic_impls:
                for generic_impl in self.generic_impls[base_name]:
                    # Build type substitution from impl's type_params to the concrete args
                    type_args = self._parse_type_args_key(type_args_key, generic_impl.type_params)
                    subst = TypeSubstitution(dict(zip(generic_impl.type_params, type_args)), struct_manglings)
                    specialized = self._specialize_impl(generic_impl, mangled_struct_name, subst)
                    self.specialized_impls.append(specialized)

    def _parse_type_args_key(self, type_args_key: Tuple[str, ...], type_params: List[str]) -> List[rast.Type]:
        """Parse a type args key back to types.

        This is a simplification - in practice we store the original type args.
        For now, we'll handle simple cases.
        """
        # This is a limitation - we can't perfectly reconstruct complex types from strings
        # In a full implementation, we'd store the original type args
        result = []
        for key in type_args_key:
            # Preferred path: the exact type this key was mangled from.
            remembered = self.type_args_by_key.get(key)
            if remembered is not None:
                result.append(copy.deepcopy(remembered))
                continue
            # Fallback: recover what we can from the mangled name.
            # Handle pointer types
            if key.startswith("ptr_"):
                inner_name = key[4:]
                inner = rast.NamedType(None, inner_name, [])
                result.append(rast.PtrType(None, inner, False))
            # Handle reference types
            elif key.startswith("ref_"):
                inner_name = key[4:]
                inner = rast.NamedType(None, inner_name, [])
                result.append(rast.RefType(None, inner, False))
            elif key.startswith("refmut_"):
                inner_name = key[7:]
                inner = rast.NamedType(None, inner_name, [])
                result.append(rast.RefType(None, inner, True))
            else:
                result.append(rast.NamedType(None, key, []))
        return result

    def _specialize_struct(self, generic_def: rast.StructDef, new_name: str,
                           subst: TypeSubstitution) -> rast.StructDef:
        """Generate a specialized struct definition."""
        new_fields = []
        for field_name, field_type in generic_def.fields:
            new_type = subst.apply(field_type)
            new_fields.append((field_name, new_type))

        note_instance_display(new_name, generic_def.name,
                              [subst.mapping[p] for p in generic_def.type_params])
        return rast.StructDef(
            generic_def.span,
            new_name,
            new_fields,
            type_params=[],  # No longer generic
            attrs=generic_def.attrs  # Preserve [[packed]] and other attrs
        )

    def _specialize_enum(self, generic_def: rast.EnumDef, new_name: str,
                         subst: TypeSubstitution) -> rast.EnumDef:
        """Generate a specialized enum definition.

        For Option<i32>, transforms:
            Some(T) -> Some(i32)
            None -> None
        """
        new_variants = []
        for variant in generic_def.variants:
            new_fields = [subst.apply(field_type) for field_type in variant.fields]
            # Field names are independent of the type substitution, so
            # they carry through specialization unchanged.
            new_variants.append(rast.Variant(variant.span, variant.name, new_fields,
                                             field_names=list(variant.field_names),
                                             discriminant=variant.discriminant))

        note_instance_display(new_name, generic_def.name,
                              [subst.mapping[p] for p in generic_def.type_params])
        return rast.EnumDef(
            generic_def.span,
            new_name,
            new_variants,
            type_params=[]  # No longer generic
        )

    def _specialize_function(self, generic_def: rast.FnDef, new_name: str,
                             subst: TypeSubstitution) -> rast.FnDef:
        """Generate a specialized function definition."""
        self._register_body_instances(generic_def, subst)
        # Specialize parameters
        new_params = []
        for param in generic_def.params:
            new_type = subst.apply(param.type)
            new_params.append(rast.Param(param.span, param.name, new_type, borrow=param.borrow))

        # Specialize return type
        new_ret = subst.apply(generic_def.ret_type) if generic_def.ret_type else None

        # Deep copy and specialize body
        new_body = self._specialize_block(generic_def.body, subst)

        new_fn = rast.FnDef(
            generic_def.span,
            new_name,
            new_params,
            new_ret,
            new_body,
            generic_def.attrs,
            type_params=[],  # No longer generic
            is_async=generic_def.is_async,  # Preserve async
            is_pub=generic_def.is_pub  # Preserve visibility
        )
        # Mark as monomorphized - these should be emitted locally in each consuming module
        # Don't preserve source_file so _should_emit_body returns True
        new_fn.is_monomorphized = True
        new_fn.instance_args = list(subst.mapping.values())
        new_fn.instance_subst = subst
        return new_fn

    def _specialize_impl(self, generic_impl: rast.ImplBlock, mangled_type_name: str,
                         subst: TypeSubstitution) -> rast.ImplBlock:
        """Generate a specialized impl block.

        Example: impl<T> Drop for Box<T> -> impl Drop for Box_i32

        Like specialized generic functions, specialized impl methods are
        emitted in each compilation unit that uses them. We don't preserve
        source_file so _should_emit_body returns True.
        """
        # Specialize each method
        new_methods = []
        for method in generic_impl.methods:
            # Methods need their types specialized
            # Don't pass source_file - methods should be emitted locally
            specialized = self._specialize_function_for_impl(method, subst)
            new_methods.append(specialized)

        return rast.ImplBlock(
            generic_impl.span,
            generic_impl.trait_name,
            mangled_type_name,  # e.g., "Box_i32"
            new_methods,
            type_params=[],  # No longer generic
            impl_type=None   # Type is now concrete
        )

    def _specialize_function_for_impl(self, fn: rast.FnDef,
                                       subst: TypeSubstitution) -> rast.FnDef:
        """Specialize a method within an impl block (keeps original name).

        Like monomorphized generic functions, these are emitted locally
        in each compilation unit. Don't preserve source_file.
        """
        self._register_body_instances(fn, subst)
        # Specialize parameters
        new_params = []
        for param in fn.params:
            new_type = subst.apply(param.type)
            new_params.append(rast.Param(param.span, param.name, new_type, borrow=param.borrow))

        # Specialize return type
        new_ret = subst.apply(fn.ret_type) if fn.ret_type else None

        # Deep copy and specialize body
        new_body = self._specialize_block(fn.body, subst)

        new_fn = rast.FnDef(
            fn.span,
            fn.name,  # Keep original method name (e.g., "drop")
            new_params,
            new_ret,
            new_body,
            fn.attrs,
            type_params=[],  # No longer generic
            is_async=fn.is_async,  # Preserve async
            is_pub=fn.is_pub  # Preserve visibility
        )
        # Mark as monomorphized - emit locally in each consuming module
        # Don't preserve source_file so _should_emit_body returns True
        new_fn.is_monomorphized = True
        new_fn.instance_args = list(subst.mapping.values())
        new_fn.instance_subst = subst
        return new_fn

    def _specialize_block(self, block: rast.Block, subst: TypeSubstitution) -> rast.Block:
        """Specialize a block by substituting types."""
        new_stmts = [self._specialize_stmt(s, subst) for s in block.stmts]
        new_expr = self._specialize_expr(block.expr, subst) if block.expr else None
        return rast.Block(block.span, new_stmts, new_expr)

    def _specialize_stmt(self, stmt: rast.Stmt, subst: TypeSubstitution) -> rast.Stmt:
        """Specialize a statement by substituting types."""
        if isinstance(stmt, rast.LetStmt):
            new_type = subst.apply(stmt.type) if stmt.type else None
            new_value = self._specialize_expr(stmt.value, subst) if stmt.value else None
            return rast.LetStmt(stmt.span, stmt.name, new_type, new_value)
        elif isinstance(stmt, rast.VarStmt):
            new_type = subst.apply(stmt.type) if stmt.type else None
            new_value = self._specialize_expr(stmt.value, subst) if stmt.value else None
            return rast.VarStmt(stmt.span, stmt.name, new_type, new_value)
        elif isinstance(stmt, rast.LetTupleStmt):
            # `let (a, b) = init`: the initialiser can mention T (e.g.
            # sizeof(T)), so it must be specialized too (AGAST #1928).
            return rast.LetTupleStmt(stmt.span, stmt.names,
                                     self._specialize_expr(stmt.value, subst),
                                     stmt.name_spans, stmt.paren_span)
        elif isinstance(stmt, rast.ExprStmt):
            return rast.ExprStmt(stmt.span, self._specialize_expr(stmt.expr, subst))
        elif isinstance(stmt, rast.AssignStmt):
            return rast.AssignStmt(stmt.span,
                                   self._specialize_expr(stmt.target, subst),
                                   self._specialize_expr(stmt.value, subst),
                                   stmt.op)
        elif isinstance(stmt, rast.ReturnStmt):
            new_value = self._specialize_expr(stmt.value, subst) if stmt.value else None
            return rast.ReturnStmt(stmt.span, new_value)
        elif isinstance(stmt, rast.WhileStmt):
            return rast.WhileStmt(stmt.span,
                                  self._specialize_expr(stmt.cond, subst),
                                  self._specialize_block(stmt.body, subst))
        elif isinstance(stmt, rast.ForStmt):
            return rast.ForStmt(stmt.span, stmt.var,
                               self._specialize_expr(stmt.iter, subst),
                               self._specialize_block(stmt.body, subst))
        elif isinstance(stmt, rast.AssertStmt):
            return rast.AssertStmt(stmt.span,
                                   self._specialize_expr(stmt.condition, subst),
                                   stmt.message)
        else:
            # Every other kind (UnsafeBlock, AsmStmt, Break/Continue, ...):
            # walk its fields generically so nothing nested is skipped
            # (AGAST #1937).
            return map_child_nodes(stmt,
                                   lambda e: self._specialize_expr(e, subst),
                                   lambda s: self._specialize_stmt(s, subst),
                                   subst.apply)

    def _specialize_expr(self, expr: rast.Expr, subst: TypeSubstitution) -> rast.Expr:
        """Specialize an expression by substituting types and rewriting names;
        a copy remembers the template node it copies (_type_of)."""
        new = self._specialize_expr_node(expr, subst)
        if new is not expr and new is not None:
            entry = self._origin.get(id(expr))
            origin = entry[1] if entry is not None and entry[0] is expr else expr
            self._origin[id(new)] = (new, origin)
        return new

    def _specialize_expr_node(self, expr: rast.Expr, subst: TypeSubstitution) -> rast.Expr:
        if expr is None:
            return None

        if isinstance(expr, rast.Call):
            new_func = self._specialize_expr(expr.func, subst)
            new_args = [self._specialize_expr(arg, subst) for arg in expr.args]

            # Special case: sizeof(T) where T is a type parameter
            # The argument to sizeof is a type name (Ident), not a value expression,
            # so we need to substitute type parameters in the argument
            if isinstance(expr.func, rast.Ident) and expr.func.name == 'sizeof':
                if len(expr.args) == 1 and isinstance(expr.args[0], rast.Ident):
                    type_param_name = expr.args[0].name
                    if type_param_name in subst.mapping:
                        # Substitute the type parameter with the concrete type name
                        # The concrete type itself, not its mangled name: a
                        # name like `ptr_u8` is no type the emitter knows,
                        # and an unknown sizeof name is an error (#2124).
                        concrete_type = subst.apply(
                            rast.NamedType(expr.args[0].span, type_param_name, []))
                        new_args = [rast.TypeExpr(expr.args[0].span, concrete_type)]

            # If this is a generic call, rewrite to use mangled name
            if expr.type_args and isinstance(expr.func, rast.Ident):
                fn_name = expr.func.name
                if fn_name in self.generic_functions:
                    # Key on the bare substituted args (T -> i32), as every path does (#3342)
                    substituted_type_args = [subst.bare(arg) for arg in expr.type_args]
                    key = (fn_name, self._type_args_to_key(substituted_type_args))
                    self._note_use('fn', *key, expr.type_args)
                    # If this instantiation doesn't exist yet, add it
                    # This handles transitive generic calls discovered during specialization
                    if key not in self.function_instantiations:
                        mangled_name = mangle_generic_name(fn_name, substituted_type_args)
                        self.function_instantiations[key] = mangled_name
                    else:
                        mangled_name = self.function_instantiations[key]
                    new_func = rast.Ident(expr.func.span, mangled_name)
                    return rast.Call(expr.span, new_func, new_args, type_args=[])

            return rast.Call(expr.span, new_func, new_args, type_args=expr.type_args)

        elif isinstance(expr, rast.StructLit):
            new_fields = [(name, self._specialize_expr(val, subst))
                          for name, val in expr.fields]

            # If this is a generic struct, rewrite to use mangled name
            struct_name = expr.name
            if expr.type_args and struct_name in self.generic_structs:
                # Key on the bare substituted args (T -> i32), as every path does (#3342)
                substituted_type_args = [subst.bare(arg) for arg in expr.type_args]
                key = (struct_name, self._type_args_to_key(substituted_type_args))
                self._note_use('struct', *key, expr.type_args)
                # If this instantiation doesn't exist yet, add it
                if key not in self.struct_instantiations:
                    struct_name = mangle_generic_name(struct_name, substituted_type_args)
                    self.struct_instantiations[key] = struct_name
                else:
                    struct_name = self.struct_instantiations[key]
                return rast.StructLit(expr.span, struct_name, new_fields, type_args=[])

            return rast.StructLit(expr.span, struct_name, new_fields, type_args=expr.type_args)

        elif isinstance(expr, rast.BinOp):
            return rast.BinOp(expr.span, expr.op,
                             self._specialize_expr(expr.left, subst),
                             self._specialize_expr(expr.right, subst),
                             wrapping=expr.wrapping)
        elif isinstance(expr, rast.UnaryOp):
            return rast.UnaryOp(expr.span, expr.op,
                               self._specialize_expr(expr.operand, subst))
        elif isinstance(expr, rast.Index):
            return rast.Index(expr.span,
                             self._specialize_expr(expr.expr, subst),
                             self._specialize_expr(expr.index, subst),
                             expr.bracket)
        elif isinstance(expr, rast.Field):
            return rast.Field(expr.span,
                             self._specialize_expr(expr.expr, subst),
                             expr.field, expr.name_span)
        elif isinstance(expr, rast.MethodCall):
            return rast.MethodCall(expr.span,
                                   self._specialize_expr(expr.expr, subst),
                                   expr.method,
                                   [self._specialize_expr(arg, subst) for arg in expr.args],
                                   expr.name_span)
        elif isinstance(expr, rast.If):
            return rast.If(expr.span,
                          self._specialize_expr(expr.cond, subst),
                          self._specialize_block(expr.then_block, subst),
                          self._specialize_block(expr.else_block, subst) if expr.else_block else None)
        elif isinstance(expr, rast.Block):
            return self._specialize_block(expr, subst)
        elif isinstance(expr, rast.ArrayLit):
            return rast.ArrayLit(expr.span,
                                [self._specialize_expr(e, subst) for e in expr.elements])
        elif isinstance(expr, rast.ArrayFill):
            return rast.ArrayFill(expr.span,
                                 self._specialize_expr(expr.value, subst),
                                 expr.count)
        elif isinstance(expr, rast.Cast):
            return rast.Cast(expr.span,
                            self._specialize_expr(expr.expr, subst),
                            subst.apply(expr.target), expr.as_span)
        elif isinstance(expr, rast.TryOp):
            # `operand?`: the operand can mention T (AGAST #1928).
            return rast.TryOp(expr.span, self._specialize_expr(expr.expr, subst))
        elif isinstance(expr, rast.Range):
            return rast.Range(expr.span,
                             self._specialize_expr(expr.start, subst) if expr.start else None,
                             self._specialize_expr(expr.end, subst) if expr.end else None,
                             expr.inclusive)
        else:
            # Every other kind (Match, Grouped, TupleLit, ...): walk
            # its fields generically.  Returning it unchanged left sizeof(T),
            # casts and generic calls nested inside on the template's T
            # (AGAST #1937).  Leaves (literals, identifiers) come back as-is.
            return map_child_nodes(expr,
                                   lambda e: self._specialize_expr(e, subst),
                                   lambda s: self._specialize_stmt(s, subst),
                                   subst.apply)


def monomorphize(module: rast.Module) -> rast.Module:
    """Monomorphize a module, returning a new module with generics specialized."""
    with type_aliases(module):
        monomorphizer = Monomorphizer()
        return monomorphizer.monomorphize(module)


def _struct_lits(node):
    """Every StructLit under `node`, outermost first."""
    if isinstance(node, (list, tuple)):
        for child in node:
            yield from _struct_lits(child)
        return
    if not dataclasses.is_dataclass(node) or isinstance(node, (type, rast.Type)):
        return
    if isinstance(node, rast.StructLit):
        yield node
    for f in dataclasses.fields(node):
        if f.name != 'span':
            yield from _struct_lits(getattr(node, f.name))


def infer_struct_lit_args(module: rast.Module) -> None:
    """Fill in an args-less generic struct literal's type args before the
    checkers run (LANGUAGE_SPEC §9.2, LARB R51, AGAST #3407).

    monomorphize() infers them too, but it runs at emission, after the move
    checker, which reads `StructLit.type_args` (#2263): `Box2 { v: <a Drop
    T> }` must be a Box2<T> there, so a binding from it moves.  Only fns with
    such a literal are inferred, each on a copy so nothing else (call args,
    let types) changes before the checkers; the copy's literal args are moved
    onto the originals.  An inference error is left for monomorphize() to
    report, located, as before."""
    with type_aliases(module):
        mono = Monomorphizer()
        mono._collect_generics(module)
        fns = []
        for item in module.items:
            if isinstance(item, rast.FnDef):
                fns.append((item, None))
            elif isinstance(item, rast.ImplBlock):
                fns.extend((m, item) for m in item.methods)
        for fn, impl in fns:
            lits = [lit for lit in _struct_lits(fn.body)
                    if mono._argless_struct(lit) is not None]
            if not lits:
                continue
            memo: dict = {}
            twin = copy.deepcopy(fn, memo)
            # This runs before the typing pass: the twin is typed on its own.
            mono._typed = type_bodies(module, [(twin, impl)])
            try:
                mono._infer_in_fn(twin, impl.type_name if impl else None,
                                  impl.type_params if impl else None)
            except GenericInferError:
                pass
            for lit in lits:
                inferred = memo.get(id(lit))
                if inferred is not None and inferred.type_args:
                    lit.type_args = inferred.type_args
