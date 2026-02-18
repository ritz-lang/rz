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
from dataclasses import dataclass
import copy
import ritz_ast as rast


@dataclass
class TypeSubstitution:
    """A mapping from type parameter names to concrete types."""
    mapping: Dict[str, rast.Type]
    # Optional: generic struct names -> mangled names after substitution
    struct_manglings: Dict[str, Dict[Tuple[str, ...], str]] = None

    def apply(self, ty: rast.Type) -> rast.Type:
        """Apply substitution to a type, returning a new type."""
        if isinstance(ty, rast.NamedType):
            # Check if this is a type parameter
            if ty.name in self.mapping and not ty.args:
                return copy.deepcopy(self.mapping[ty.name])
            # Otherwise, apply to any type arguments
            new_args = [self.apply(arg) for arg in ty.args]

            # If this is a generic struct with type args, mangle the name
            if new_args and self.struct_manglings and ty.name in self.struct_manglings:
                # Create a key from the substituted type args
                args_key = tuple(mangle_type_name(arg) for arg in new_args)
                mangled = self.struct_manglings[ty.name].get(args_key)
                if mangled:
                    return rast.NamedType(ty.span, mangled, [])

            return rast.NamedType(ty.span, ty.name, new_args)
        elif isinstance(ty, rast.PtrType):
            return rast.PtrType(ty.span, self.apply(ty.inner), ty.mutable)
        elif isinstance(ty, rast.RefType):
            return rast.RefType(ty.span, self.apply(ty.inner), ty.mutable)
        elif isinstance(ty, rast.ArrayType):
            return rast.ArrayType(ty.span, ty.size, self.apply(ty.inner))
        elif isinstance(ty, rast.SliceType):
            return rast.SliceType(ty.span, self.apply(ty.inner))
        elif isinstance(ty, rast.FnType):
            new_params = [self.apply(p) for p in ty.params]
            new_ret = self.apply(ty.ret) if ty.ret else None
            return rast.FnType(ty.span, new_params, new_ret)
        else:
            return ty


def mangle_type_name(ty: rast.Type) -> str:
    """Generate a mangled name component for a type.

    Examples:
        i32 -> "i32"
        *u8 -> "ptr_u8"
        *mut i32 -> "ptrmut_i32"
        Vec<i32> -> "Vec_i32"
    """
    if isinstance(ty, rast.NamedType):
        if ty.args:
            arg_names = "_".join(mangle_type_name(arg) for arg in ty.args)
            return f"{ty.name}_{arg_names}"
        return ty.name
    elif isinstance(ty, rast.PtrType):
        if ty.mutable:
            return f"ptrmut_{mangle_type_name(ty.inner)}"
        return f"ptr_{mangle_type_name(ty.inner)}"
    elif isinstance(ty, rast.RefType):
        if ty.mutable:
            return f"refmut_{mangle_type_name(ty.inner)}"
        return f"ref_{mangle_type_name(ty.inner)}"
    elif isinstance(ty, rast.ArrayType):
        return f"arr{ty.size}_{mangle_type_name(ty.inner)}"
    elif isinstance(ty, rast.SliceType):
        return f"slice_{mangle_type_name(ty.inner)}"
    else:
        return "unknown"


def mangle_generic_name(base_name: str, type_args: List[rast.Type]) -> str:
    """Generate a mangled name for a generic instantiation.

    Uses '$' separator between function name and type args to avoid collisions.
    For example, vec_get<*u8> becomes vec_get$ptr_u8, not vec_get_ptr_u8
    (which would collide with vec_get_ptr<u8>).

    Examples:
        Pair<i32> -> "Pair$i32"
        Vec<*u8> -> "Vec$ptr_u8"
        Map<i32, *u8> -> "Map$i32_ptr_u8"
    """
    if not type_args:
        return base_name
    arg_names = "_".join(mangle_type_name(arg) for arg in type_args)
    return f"{base_name}${arg_names}"


class Monomorphizer:
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

        # Variable type tracking for slice/index syntax
        # Maps variable name -> declared type (for current scope)
        self.var_types: Dict[str, rast.Type] = {}

        # Trait implementations: type_name -> set of trait names
        # e.g., "String" -> {"Drop"}, "Vec$i32" -> {"Drop"}
        self.trait_impls: Dict[str, Set[str]] = {}

    def _type_to_key(self, ty: rast.Type) -> str:
        """Convert a type to a string key for deduplication."""
        return mangle_type_name(ty)

    def _type_args_to_key(self, type_args: List[rast.Type]) -> Tuple[str, ...]:
        """Convert type arguments to a tuple key for deduplication."""
        return tuple(self._type_to_key(arg) for arg in type_args)

    def monomorphize(self, module: rast.Module) -> rast.Module:
        """Monomorphize a module, returning a new module with generics specialized."""
        # Phase 0: Collect trait implementations for bound checking
        self._collect_trait_impls(module)

        # Phase 1: Collect generic definitions
        self._collect_generics(module)

        # Phase 2: Find all instantiations
        self._find_instantiations(module)

        # Phase 3: Generate specialized versions (iterative until fixpoint)
        # This is needed because generic functions may call other generic functions
        # e.g., vec_push<T> calls vec_ensure_cap<T> -> vec_push<i32> calls vec_ensure_cap<i32>
        self._generate_specializations_iterative()

        # Phase 4: Rewrite the AST
        new_items = self._rewrite_items(module.items)

        return rast.Module(module.span, new_items)

    def _collect_trait_impls(self, module: rast.Module) -> None:
        """Collect all trait implementations for bound checking.

        Records which types implement which traits, including:
        - Non-generic impls: impl Drop for String
        - Generic impls: impl<T> Drop for Box<T> (recorded during specialization)
        """
        for item in module.items:
            if isinstance(item, rast.ImplBlock) and item.trait_name:
                if not item.type_params:
                    # Non-generic impl: impl Drop for String
                    type_name = item.type_name
                    if type_name not in self.trait_impls:
                        self.trait_impls[type_name] = set()
                    self.trait_impls[type_name].add(item.trait_name)

    def _type_implements_trait(self, type_name: str, trait_name: str) -> bool:
        """Check if a type implements a trait."""
        return trait_name in self.trait_impls.get(type_name, set())

    def _check_trait_bounds(self, generic_def_name: str, type_params: List[str],
                            type_args: List[rast.Type], bounds: Dict[str, List[str]],
                            context: str = "") -> None:
        """Check that type arguments satisfy their trait bounds.

        Args:
            generic_def_name: Name of the generic being instantiated (for error messages)
            type_params: List of type parameter names
            type_args: List of concrete type arguments
            bounds: Dict mapping param names to required trait names
            context: Additional context for error messages

        Raises:
            TypeError: If a bound is not satisfied
        """
        for param, arg in zip(type_params, type_args):
            required_traits = bounds.get(param, [])
            if not required_traits:
                continue  # No bounds on this parameter

            arg_name = mangle_type_name(arg)

            for trait in required_traits:
                if not self._type_implements_trait(arg_name, trait):
                    loc = context if context else f"instantiating {generic_def_name}"
                    raise TypeError(
                        f"Type '{arg_name}' does not implement trait '{trait}' "
                        f"required by bound on type parameter '{param}' in {loc}"
                    )

    def _collect_generics(self, module: rast.Module) -> None:
        """Collect all generic struct, enum, function, and impl block definitions."""
        for item in module.items:
            if isinstance(item, rast.StructDef) and item.is_generic():
                self.generic_structs[item.name] = item
            elif isinstance(item, rast.EnumDef) and item.is_generic():
                self.generic_enums[item.name] = item
            elif isinstance(item, rast.FnDef) and item.is_generic():
                self.generic_functions[item.name] = item
            elif isinstance(item, rast.ImplBlock) and item.type_params:
                # Generic impl block like `impl<T> Drop for Box<T>`
                if item.type_name not in self.generic_impls:
                    self.generic_impls[item.type_name] = []
                self.generic_impls[item.type_name].append(item)

    def _find_instantiations(self, module: rast.Module) -> None:
        """Walk the AST to find all generic instantiations."""
        for item in module.items:
            self._visit_item(item)

    def _visit_item(self, item: rast.Item) -> None:
        """Visit an item to find instantiations."""
        if isinstance(item, rast.FnDef):
            # Skip generic functions - they contain calls like vec_grow<T>
            # which are not concrete instantiations. These calls only become
            # concrete during specialization (e.g., vec_grow<i32>).
            if item.is_generic():
                return
            # Clear variable types for new function scope
            self.var_types = {}
            # Register parameter types
            for param in item.params:
                self._visit_type(param.type)
                self.var_types[param.name] = param.type
            # Visit return type
            if item.ret_type:
                self._visit_type(item.ret_type)
            # Visit body
            self._visit_block(item.body)
        elif isinstance(item, rast.StructDef):
            # Visit field types
            for _, field_type in item.fields:
                self._visit_type(field_type)
        elif isinstance(item, rast.ImplBlock):
            # Skip generic impl blocks - they're handled during specialization
            if item.type_params:
                return
            # Visit non-generic impl blocks to find generic calls in their methods
            # e.g., impl Drop for String { fn drop() { vec_drop<u8>(...) } }
            for method in item.methods:
                self._visit_item(method)

    def _visit_type(self, ty: rast.Type) -> None:
        """Visit a type to find instantiations."""
        if isinstance(ty, rast.NamedType):
            if ty.args and ty.name in self.generic_structs:
                # This is a generic struct instantiation
                key = (ty.name, self._type_args_to_key(ty.args))
                if key not in self.struct_instantiations:
                    mangled = mangle_generic_name(ty.name, ty.args)
                    self.struct_instantiations[key] = mangled
            elif ty.args and ty.name in self.generic_enums:
                # This is a generic enum instantiation
                key = (ty.name, self._type_args_to_key(ty.args))
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
        elif isinstance(ty, rast.SliceType):
            self._visit_type(ty.inner)
        elif isinstance(ty, rast.FnType):
            for p in ty.params:
                self._visit_type(p)
            if ty.ret:
                self._visit_type(ty.ret)

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
                # Track variable type
                self.var_types[stmt.name] = stmt.type
            if stmt.value:
                self._visit_expr(stmt.value)
        elif isinstance(stmt, rast.VarStmt):
            if stmt.type:
                self._visit_type(stmt.type)
                # Track variable type
                self.var_types[stmt.name] = stmt.type
            if stmt.value:
                self._visit_expr(stmt.value)
        elif isinstance(stmt, rast.ExprStmt):
            self._visit_expr(stmt.expr)
        elif isinstance(stmt, rast.AssignStmt):
            self._visit_expr(stmt.target)
            self._visit_expr(stmt.value)
        elif isinstance(stmt, rast.ReturnStmt):
            if stmt.value:
                self._visit_expr(stmt.value)
        elif isinstance(stmt, rast.WhileStmt):
            self._visit_expr(stmt.cond)
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
                    if key not in self.function_instantiations:
                        mangled = mangle_generic_name(fn_name, expr.type_args)
                        self.function_instantiations[key] = mangled
        elif isinstance(expr, rast.StructLit):
            for _, field_expr in expr.fields:
                self._visit_expr(field_expr)
            # Check for generic struct instantiation
            if expr.type_args and expr.name in self.generic_structs:
                key = (expr.name, self._type_args_to_key(expr.type_args))
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
        elif isinstance(expr, rast.Field):
            self._visit_expr(expr.expr)
        elif isinstance(expr, rast.MethodCall):
            self._visit_expr(expr.expr)
            for arg in expr.args:
                self._visit_expr(arg)
            # Register method instantiation for UFCS on generic types
            self._register_method_instantiation(expr)
        elif isinstance(expr, rast.If):
            self._visit_expr(expr.cond)
            self._visit_block(expr.then_block)
            if expr.else_block:
                self._visit_block(expr.else_block)
        elif isinstance(expr, rast.Match):
            self._visit_expr(expr.expr)
            for arm in expr.arms:
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
        elif isinstance(expr, rast.Range):
            if expr.start:
                self._visit_expr(expr.start)
            if expr.end:
                self._visit_expr(expr.end)
        elif isinstance(expr, rast.Lambda):
            for param in expr.params:
                self._visit_type(param.type)
            if expr.ret_type:
                self._visit_type(expr.ret_type)
            self._visit_expr(expr.body)
        elif isinstance(expr, rast.SliceExpr):
            # Visit the base expression and indices
            self._visit_expr(expr.expr)
            if expr.start:
                self._visit_expr(expr.start)
            if expr.end:
                self._visit_expr(expr.end)
            # If base is an identifier with known Vec<T> type, register vec_slice<T>
            self._register_slice_instantiation(expr)

    def _register_slice_instantiation(self, expr: rast.SliceExpr) -> None:
        """Register vec_slice<T> instantiation for slice expressions on Vec types."""
        if not isinstance(expr.expr, rast.Ident):
            return

        var_name = expr.expr.name
        if var_name not in self.var_types:
            return

        var_type = self.var_types[var_name]
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

    def _register_method_instantiation(self, expr: rast.MethodCall) -> None:
        """Register UFCS function instantiation for method calls on generic types.

        When we see `v.len()` on a Vec<T>, we need to instantiate `vec_len<T>`.
        This enables method syntax on types without impl blocks by mapping:
          - Vec<T>.method() -> vec_method<T>
          - Span<T>.method() -> span_method<T>
          - Option<T>.method() -> option_method<T>
        """
        # Only handle method calls on identifiers for now
        if not isinstance(expr.expr, rast.Ident):
            return

        var_name = expr.expr.name
        if var_name not in self.var_types:
            return

        var_type = self.var_types[var_name]

        # Unwrap pointer/reference types: &Vec<T>, *Vec<T>, &mut Vec<T> -> Vec<T>
        while isinstance(var_type, rast.RefType):
            var_type = var_type.inner
        while isinstance(var_type, rast.PtrType):
            var_type = var_type.inner

        if not isinstance(var_type, rast.NamedType):
            return

        # Map type names to their function prefixes
        type_to_prefix = {
            'Vec': 'vec_',
            'Span': 'span_',
            'Option': 'option_',
            'Result': 'result_',
            'Box': 'box_',
        }

        type_name = var_type.name
        if type_name not in type_to_prefix:
            return

        prefix = type_to_prefix[type_name]
        fn_name = f"{prefix}{expr.method}"

        # Only if this is a generic function
        if fn_name not in self.generic_functions:
            return

        # Register instantiation with the type's type args
        if var_type.args:
            type_args = var_type.args
            key = (fn_name, self._type_args_to_key(type_args))
            if key not in self.function_instantiations:
                mangled = mangle_generic_name(fn_name, type_args)
                self.function_instantiations[key] = mangled

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

        # Iterate until no new instantiations are found
        max_iterations = 100  # Safety limit
        for iteration in range(max_iterations):
            # Find new instantiations
            new_structs = {k for k in self.struct_instantiations.keys() if k not in processed_structs}
            new_enums = {k for k in self.enum_instantiations.keys() if k not in processed_enums}
            new_functions = {k for k in self.function_instantiations.keys() if k not in processed_functions}

            if not new_structs and not new_enums and not new_functions:
                # Fixpoint reached
                break

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

                # Check trait bounds before specializing
                bounds = getattr(generic_def, 'type_param_bounds', {}) or {}
                if bounds:
                    self._check_trait_bounds(
                        f"struct {base_name}",
                        generic_def.type_params, type_args, bounds
                    )

                subst = TypeSubstitution(dict(zip(generic_def.type_params, type_args)), struct_manglings)
                specialized = self._specialize_struct(generic_def, mangled_name, subst)
                self.specialized_structs.append(specialized)
                processed_structs.add(key)

                # Also specialize any generic impl blocks for this struct
                if base_name in self.generic_impls:
                    for generic_impl in self.generic_impls[base_name]:
                        impl_subst = TypeSubstitution(dict(zip(generic_impl.type_params, type_args)), struct_manglings)
                        specialized_impl = self._specialize_impl(generic_impl, mangled_name, impl_subst)
                        self.specialized_impls.append(specialized_impl)

                        # Record trait impl for the specialized type
                        if generic_impl.trait_name:
                            if mangled_name not in self.trait_impls:
                                self.trait_impls[mangled_name] = set()
                            self.trait_impls[mangled_name].add(generic_impl.trait_name)

            # Generate specialized enums for new instantiations
            for key in new_enums:
                base_name, type_args_key = key
                mangled_name = self.enum_instantiations[key]
                generic_def = self.generic_enums[base_name]
                type_args = self._parse_type_args_key(type_args_key, generic_def.type_params)

                # Check trait bounds before specializing
                bounds = getattr(generic_def, 'type_param_bounds', {}) or {}
                if bounds:
                    self._check_trait_bounds(
                        f"enum {base_name}",
                        generic_def.type_params, type_args, bounds
                    )

                subst = TypeSubstitution(dict(zip(generic_def.type_params, type_args)), struct_manglings)
                specialized = self._specialize_enum(generic_def, mangled_name, subst)
                self.specialized_enums.append(specialized)
                processed_enums.add(key)

                # Also specialize any generic impl blocks for this enum
                if base_name in self.generic_impls:
                    for generic_impl in self.generic_impls[base_name]:
                        impl_subst = TypeSubstitution(dict(zip(generic_impl.type_params, type_args)), struct_manglings)
                        specialized_impl = self._specialize_impl(generic_impl, mangled_name, impl_subst)
                        self.specialized_impls.append(specialized_impl)

                        # Record trait impl for the specialized type
                        if generic_impl.trait_name:
                            if mangled_name not in self.trait_impls:
                                self.trait_impls[mangled_name] = set()
                            self.trait_impls[mangled_name].add(generic_impl.trait_name)

            # Generate specialized functions for new instantiations
            for key in new_functions:
                base_name, type_args_key = key
                mangled_name = self.function_instantiations[key]
                generic_def = self.generic_functions[base_name]
                type_args = self._parse_type_args_key(type_args_key, generic_def.type_params)

                # Check trait bounds before specializing
                bounds = getattr(generic_def, 'type_param_bounds', {}) or {}
                if bounds:
                    self._check_trait_bounds(
                        f"function {base_name}",
                        generic_def.type_params, type_args, bounds
                    )

                subst = TypeSubstitution(dict(zip(generic_def.type_params, type_args)), struct_manglings)
                specialized = self._specialize_function(generic_def, mangled_name, subst)
                self.specialized_functions.append(specialized)
                processed_functions.add(key)

                # CRITICAL: Scan the specialized function body for new instantiations
                # This discovers transitive generic calls like vec_ensure_cap<i32>
                self._scan_for_new_instantiations(specialized)

    def _scan_for_new_instantiations(self, fn: rast.FnDef) -> None:
        """Scan a specialized function for new generic instantiations.

        When specializing vec_push<i32>, it calls vec_ensure_cap<i32>.
        The call has been rewritten to use the mangled name, but we also need to
        check if the instantiation exists and add it if not.
        """
        self._visit_item(fn)

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
            # Handle pointer types
            if key.startswith("ptr_"):
                inner_name = key[4:]
                inner = rast.NamedType(None, inner_name, [])
                result.append(rast.PtrType(None, inner, False))
            elif key.startswith("ptrmut_"):
                inner_name = key[7:]
                inner = rast.NamedType(None, inner_name, [])
                result.append(rast.PtrType(None, inner, True))
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
            new_variants.append(rast.Variant(variant.span, variant.name, new_fields))

        return rast.EnumDef(
            generic_def.span,
            new_name,
            new_variants,
            type_params=[]  # No longer generic
        )

    def _specialize_function(self, generic_def: rast.FnDef, new_name: str,
                             subst: TypeSubstitution) -> rast.FnDef:
        """Generate a specialized function definition."""
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
        elif isinstance(stmt, rast.ExprStmt):
            return rast.ExprStmt(stmt.span, self._specialize_expr(stmt.expr, subst))
        elif isinstance(stmt, rast.AssignStmt):
            return rast.AssignStmt(stmt.span,
                                   self._specialize_expr(stmt.target, subst),
                                   self._specialize_expr(stmt.value, subst))
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
        elif isinstance(stmt, rast.BreakStmt):
            return stmt
        elif isinstance(stmt, rast.ContinueStmt):
            return stmt
        else:
            return stmt

    def _specialize_expr(self, expr: rast.Expr, subst: TypeSubstitution) -> rast.Expr:
        """Specialize an expression by substituting types and rewriting names."""
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
                        concrete_type = subst.mapping[type_param_name]
                        # Convert the concrete type to its mangled name for sizeof
                        concrete_name = mangle_type_name(concrete_type)
                        new_args = [rast.Ident(expr.args[0].span, concrete_name)]

            # If this is a generic call, rewrite to use mangled name
            if expr.type_args and isinstance(expr.func, rast.Ident):
                fn_name = expr.func.name
                if fn_name in self.generic_functions:
                    # Apply substitution to type args first (e.g., T -> i32)
                    substituted_type_args = [subst.apply(arg) for arg in expr.type_args]
                    key = (fn_name, self._type_args_to_key(substituted_type_args))
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
                # Apply substitution to type args first (e.g., T -> i32)
                substituted_type_args = [subst.apply(arg) for arg in expr.type_args]
                key = (struct_name, self._type_args_to_key(substituted_type_args))
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
                             self._specialize_expr(expr.right, subst))
        elif isinstance(expr, rast.UnaryOp):
            return rast.UnaryOp(expr.span, expr.op,
                               self._specialize_expr(expr.operand, subst))
        elif isinstance(expr, rast.Index):
            return rast.Index(expr.span,
                             self._specialize_expr(expr.expr, subst),
                             self._specialize_expr(expr.index, subst))
        elif isinstance(expr, rast.Field):
            return rast.Field(expr.span,
                             self._specialize_expr(expr.expr, subst),
                             expr.field)
        elif isinstance(expr, rast.MethodCall):
            return rast.MethodCall(expr.span,
                                   self._specialize_expr(expr.expr, subst),
                                   expr.method,
                                   [self._specialize_expr(arg, subst) for arg in expr.args])
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
                            subst.apply(expr.target))
        elif isinstance(expr, rast.Range):
            return rast.Range(expr.span,
                             self._specialize_expr(expr.start, subst) if expr.start else None,
                             self._specialize_expr(expr.end, subst) if expr.end else None,
                             expr.inclusive)
        else:
            # Literals and identifiers don't need specialization
            return expr

    def _rewrite_items(self, items: List[rast.Item]) -> List[rast.Item]:
        """Rewrite items, removing generics and adding specializations."""
        new_items = []

        for item in items:
            if isinstance(item, rast.StructDef) and item.is_generic():
                # Remove generic struct definition (specializations will be added)
                continue
            elif isinstance(item, rast.EnumDef) and item.is_generic():
                # Remove generic enum definition (specializations will be added)
                continue
            elif isinstance(item, rast.FnDef) and item.is_generic():
                # Remove generic function definition (specializations will be added)
                continue
            elif isinstance(item, rast.ImplBlock) and item.type_params:
                # Remove generic impl block (specializations will be added)
                continue
            elif isinstance(item, rast.FnDef):
                # Rewrite non-generic function to use specialized types/calls
                new_items.append(self._rewrite_function(item))
            elif isinstance(item, rast.StructDef):
                # Rewrite non-generic struct to use specialized field types
                new_items.append(self._rewrite_struct(item))
            elif isinstance(item, rast.EnumDef):
                # Rewrite non-generic enum to use specialized variant types
                new_items.append(self._rewrite_enum(item))
            elif isinstance(item, rast.ImplBlock):
                # Rewrite non-generic impl block methods
                new_items.append(self._rewrite_impl(item))
            else:
                new_items.append(item)

        # Add specialized structs and enums before functions that use them
        new_items = self.specialized_structs + self.specialized_enums + new_items

        # Add specialized functions
        new_items.extend(self.specialized_functions)

        # Add specialized impl blocks
        new_items.extend(self.specialized_impls)

        return new_items

    def _rewrite_struct(self, struct: rast.StructDef) -> rast.StructDef:
        """Rewrite a non-generic struct to use specialized types in fields.

        For example, if String has a field `data: Vec<u8>`, this rewrites it
        to `data: Vec_u8` after Vec<u8> has been specialized.
        """
        new_fields = []
        for field_name, field_type in struct.fields:
            new_type = self._rewrite_type(field_type)
            new_fields.append((field_name, new_type))

        new_struct = rast.StructDef(struct.span, struct.name, new_fields,
                                    type_params=struct.type_params,
                                    attrs=struct.attrs)  # Preserve [[packed]] and other attrs
        # Preserve source_file for separate compilation
        if hasattr(struct, 'source_file'):
            new_struct.source_file = struct.source_file
        return new_struct

    def _rewrite_enum(self, enum: rast.EnumDef) -> rast.EnumDef:
        """Rewrite a non-generic enum to use specialized types in variants.

        For example, if an enum variant has a field with type Vec<u8>, this
        rewrites it to Vec_u8 after Vec<u8> has been specialized.
        """
        new_variants = []
        for variant in enum.variants:
            new_fields = [self._rewrite_type(field_type) for field_type in variant.fields]
            new_variants.append(rast.Variant(variant.span, variant.name, new_fields))

        new_enum = rast.EnumDef(enum.span, enum.name, new_variants,
                                type_params=enum.type_params)
        # Preserve source_file for separate compilation
        if hasattr(enum, 'source_file'):
            new_enum.source_file = enum.source_file
        return new_enum

    def _rewrite_impl(self, impl: rast.ImplBlock) -> rast.ImplBlock:
        """Rewrite a non-generic impl block to use specialized types and calls.

        For example, if String's Drop impl calls vec_drop<u8>(), this rewrites
        the call to use the specialized vec_drop$u8 function.
        """
        new_methods = [self._rewrite_function(method) for method in impl.methods]

        new_impl = rast.ImplBlock(
            impl.span,
            impl.trait_name,
            impl.type_name,
            new_methods,
            type_params=impl.type_params,
            impl_type=impl.impl_type
        )
        # Preserve source_file for separate compilation
        if hasattr(impl, 'source_file'):
            new_impl.source_file = impl.source_file
        return new_impl

    def _rewrite_function(self, fn: rast.FnDef) -> rast.FnDef:
        """Rewrite a non-generic function to use specialized types and calls."""
        # Empty substitution - we're just rewriting generic uses
        subst = TypeSubstitution({})

        # Rewrite parameter types
        new_params = []
        for param in fn.params:
            new_type = self._rewrite_type(param.type)
            new_params.append(rast.Param(param.span, param.name, new_type, borrow=param.borrow))

        # Rewrite return type
        new_ret = self._rewrite_type(fn.ret_type) if fn.ret_type else None

        # Rewrite body
        new_body = self._rewrite_block(fn.body)

        new_fn = rast.FnDef(fn.span, fn.name, new_params, new_ret, new_body, fn.attrs,
                            type_params=fn.type_params, is_async=fn.is_async, is_pub=fn.is_pub)
        # Preserve source_file for separate compilation
        if hasattr(fn, 'source_file'):
            new_fn.source_file = fn.source_file
        return new_fn

    def _rewrite_type(self, ty: rast.Type) -> rast.Type:
        """Rewrite a type to use specialized struct/enum names."""
        if ty is None:
            return None

        if isinstance(ty, rast.NamedType):
            if ty.args and ty.name in self.generic_structs:
                # Replace with mangled struct name
                key = (ty.name, self._type_args_to_key(ty.args))
                mangled = self.struct_instantiations.get(key, ty.name)
                return rast.NamedType(ty.span, mangled, [])
            elif ty.args and ty.name in self.generic_enums:
                # Replace with mangled enum name
                key = (ty.name, self._type_args_to_key(ty.args))
                mangled = self.enum_instantiations.get(key, ty.name)
                return rast.NamedType(ty.span, mangled, [])
            # Recursively rewrite type args
            new_args = [self._rewrite_type(arg) for arg in ty.args]
            return rast.NamedType(ty.span, ty.name, new_args)
        elif isinstance(ty, rast.PtrType):
            return rast.PtrType(ty.span, self._rewrite_type(ty.inner), ty.mutable)
        elif isinstance(ty, rast.RefType):
            return rast.RefType(ty.span, self._rewrite_type(ty.inner), ty.mutable)
        elif isinstance(ty, rast.ArrayType):
            return rast.ArrayType(ty.span, ty.size, self._rewrite_type(ty.inner))
        elif isinstance(ty, rast.SliceType):
            return rast.SliceType(ty.span, self._rewrite_type(ty.inner))
        elif isinstance(ty, rast.FnType):
            new_params = [self._rewrite_type(p) for p in ty.params]
            new_ret = self._rewrite_type(ty.ret) if ty.ret else None
            return rast.FnType(ty.span, new_params, new_ret)
        else:
            return ty

    def _rewrite_block(self, block: rast.Block) -> rast.Block:
        """Rewrite a block to use specialized types and calls."""
        new_stmts = [self._rewrite_stmt(s) for s in block.stmts]
        new_expr = self._rewrite_expr(block.expr) if block.expr else None
        return rast.Block(block.span, new_stmts, new_expr)

    def _rewrite_stmt(self, stmt: rast.Stmt) -> rast.Stmt:
        """Rewrite a statement to use specialized types and calls."""
        if isinstance(stmt, rast.LetStmt):
            new_type = self._rewrite_type(stmt.type) if stmt.type else None
            new_value = self._rewrite_expr(stmt.value) if stmt.value else None
            return rast.LetStmt(stmt.span, stmt.name, new_type, new_value)
        elif isinstance(stmt, rast.VarStmt):
            new_type = self._rewrite_type(stmt.type) if stmt.type else None
            new_value = self._rewrite_expr(stmt.value) if stmt.value else None
            return rast.VarStmt(stmt.span, stmt.name, new_type, new_value)
        elif isinstance(stmt, rast.ExprStmt):
            return rast.ExprStmt(stmt.span, self._rewrite_expr(stmt.expr))
        elif isinstance(stmt, rast.AssignStmt):
            return rast.AssignStmt(stmt.span,
                                   self._rewrite_expr(stmt.target),
                                   self._rewrite_expr(stmt.value))
        elif isinstance(stmt, rast.ReturnStmt):
            new_value = self._rewrite_expr(stmt.value) if stmt.value else None
            return rast.ReturnStmt(stmt.span, new_value)
        elif isinstance(stmt, rast.WhileStmt):
            return rast.WhileStmt(stmt.span,
                                  self._rewrite_expr(stmt.cond),
                                  self._rewrite_block(stmt.body))
        elif isinstance(stmt, rast.ForStmt):
            return rast.ForStmt(stmt.span, stmt.var,
                               self._rewrite_expr(stmt.iter),
                               self._rewrite_block(stmt.body))
        elif isinstance(stmt, rast.AssertStmt):
            return rast.AssertStmt(stmt.span,
                                   self._rewrite_expr(stmt.condition),
                                   stmt.message)
        else:
            return stmt

    def _rewrite_expr(self, expr: rast.Expr) -> rast.Expr:
        """Rewrite an expression to use specialized types and calls."""
        if expr is None:
            return None

        if isinstance(expr, rast.Call):
            new_func = self._rewrite_expr(expr.func)
            new_args = [self._rewrite_expr(arg) for arg in expr.args]

            # If this is a generic call, rewrite to use mangled name
            if expr.type_args and isinstance(expr.func, rast.Ident):
                fn_name = expr.func.name
                if fn_name in self.generic_functions:
                    key = (fn_name, self._type_args_to_key(expr.type_args))
                    mangled_name = self.function_instantiations.get(key, fn_name)
                    new_func = rast.Ident(expr.func.span, mangled_name)
                    return rast.Call(expr.span, new_func, new_args, type_args=[])

            return rast.Call(expr.span, new_func, new_args, type_args=expr.type_args)

        elif isinstance(expr, rast.StructLit):
            new_fields = [(name, self._rewrite_expr(val))
                          for name, val in expr.fields]

            # If this is a generic struct, rewrite to use mangled name
            struct_name = expr.name
            if expr.type_args and struct_name in self.generic_structs:
                key = (struct_name, self._type_args_to_key(expr.type_args))
                struct_name = self.struct_instantiations.get(key, struct_name)
                return rast.StructLit(expr.span, struct_name, new_fields, type_args=[])

            return rast.StructLit(expr.span, struct_name, new_fields, type_args=expr.type_args)

        elif isinstance(expr, rast.BinOp):
            return rast.BinOp(expr.span, expr.op,
                             self._rewrite_expr(expr.left),
                             self._rewrite_expr(expr.right))
        elif isinstance(expr, rast.UnaryOp):
            return rast.UnaryOp(expr.span, expr.op,
                               self._rewrite_expr(expr.operand))
        elif isinstance(expr, rast.Index):
            return rast.Index(expr.span,
                             self._rewrite_expr(expr.expr),
                             self._rewrite_expr(expr.index))
        elif isinstance(expr, rast.Field):
            return rast.Field(expr.span,
                             self._rewrite_expr(expr.expr),
                             expr.field)
        elif isinstance(expr, rast.MethodCall):
            return rast.MethodCall(expr.span,
                                   self._rewrite_expr(expr.expr),
                                   expr.method,
                                   [self._rewrite_expr(arg) for arg in expr.args])
        elif isinstance(expr, rast.If):
            return rast.If(expr.span,
                          self._rewrite_expr(expr.cond),
                          self._rewrite_block(expr.then_block),
                          self._rewrite_block(expr.else_block) if expr.else_block else None)
        elif isinstance(expr, rast.Block):
            return self._rewrite_block(expr)
        elif isinstance(expr, rast.ArrayLit):
            return rast.ArrayLit(expr.span,
                                [self._rewrite_expr(e) for e in expr.elements])
        elif isinstance(expr, rast.ArrayFill):
            return rast.ArrayFill(expr.span,
                                 self._rewrite_expr(expr.value),
                                 expr.count)
        elif isinstance(expr, rast.Cast):
            return rast.Cast(expr.span,
                            self._rewrite_expr(expr.expr),
                            self._rewrite_type(expr.target))
        elif isinstance(expr, rast.Range):
            return rast.Range(expr.span,
                             self._rewrite_expr(expr.start) if expr.start else None,
                             self._rewrite_expr(expr.end) if expr.end else None,
                             expr.inclusive)
        else:
            return expr


def monomorphize(module: rast.Module) -> rast.Module:
    """Monomorphize a module, returning a new module with generics specialized."""
    monomorphizer = Monomorphizer()
    return monomorphizer.monomorphize(module)
