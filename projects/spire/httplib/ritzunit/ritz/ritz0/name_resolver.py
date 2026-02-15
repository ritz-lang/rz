"""
Name Resolver for ritz0

After parsing and import resolution, verifies that all referenced names
(functions, types, variables) are defined. This catches errors early
before attempting IR emission.

This addresses GitHub issue #31 - the need for a type checking pass.
"""

from typing import Set, Dict, List, Optional
from dataclasses import dataclass
import ritz_ast as rast


class NameError(Exception):
    """Error for unresolved names."""
    def __init__(self, message: str, span = None):
        self.span = span
        if span:
            super().__init__(f"{span.file}:{span.line}:{span.column}: {message}")
        else:
            super().__init__(message)


@dataclass
class Scope:
    """Represents a lexical scope with local bindings."""
    parent: Optional['Scope']
    locals: Set[str]  # Local variable names

    def contains(self, name: str) -> bool:
        """Check if name is defined in this scope or any parent."""
        if name in self.locals:
            return True
        if self.parent:
            return self.parent.contains(name)
        return False


class NameResolver:
    """Verifies that all referenced names are defined."""

    # Built-in functions that don't need explicit definition
    BUILTINS = {
        '__syscall0', '__syscall1', '__syscall2', '__syscall3',
        '__syscall4', '__syscall5', '__syscall6',
        '__builtin_alloca', 'print', 'sizeof', 'typeof',
        'assert',
        # SIMD vector operations
        'simd_load', 'simd_loadu', 'simd_store', 'simd_storeu',
        'simd_shuffle', 'simd_extract', 'simd_insert',
        'simd_sad',  # Sum of absolute differences (psadbw)
        'simd_clmul',  # Carryless multiply (pclmulqdq) for CRC32
    }

    # Built-in types
    BUILTIN_TYPES = {
        'i8', 'i16', 'i32', 'i64',
        'u8', 'u16', 'u32', 'u64',
        'f32', 'f64',
        'bool', 'void',
        # SIMD vector types (SSE2 128-bit)
        'v2i64', 'v4i32', 'v8i16', 'v16i8',
        # SIMD vector types (AVX2 256-bit)
        'v4i64', 'v8i32', 'v16i16', 'v32i8',
    }

    def __init__(self):
        # Defined names at module level
        self.functions: Set[str] = set()
        self.structs: Set[str] = set()
        self.enums: Set[str] = set()
        self.enum_variants: Dict[str, Set[str]] = {}  # enum_name -> set of variant names
        self.constants: Set[str] = set()
        self.type_aliases: Set[str] = set()
        self.traits: Set[str] = set()
        self.global_vars: Set[str] = set()

        # Errors collected during resolution
        self.errors: List[NameError] = []

        # Track if we're inside an async function (for await validation)
        self.in_async_fn: bool = False

    def resolve(self, module: rast.Module) -> List[NameError]:
        """Resolve all names in a module.

        Returns a list of errors (empty if all names resolve).
        """
        self.errors = []

        # First pass: collect all defined names
        self._collect_definitions(module)

        # Second pass: check all references
        for item in module.items:
            self._check_item(item)

        return self.errors

    def _collect_definitions(self, module: rast.Module):
        """Collect all top-level definitions."""
        for item in module.items:
            if isinstance(item, rast.FnDef):
                self.functions.add(item.name)
            elif isinstance(item, rast.ExternFn):
                self.functions.add(item.name)
            elif isinstance(item, rast.StructDef):
                self.structs.add(item.name)
            elif isinstance(item, rast.EnumDef):
                self.enums.add(item.name)
                self.enum_variants[item.name] = {v.name for v in item.variants}
            elif isinstance(item, rast.ConstDef):
                self.constants.add(item.name)
            elif isinstance(item, rast.TypeAlias):
                self.type_aliases.add(item.name)
            elif isinstance(item, rast.TraitDef):
                self.traits.add(item.name)
            elif isinstance(item, rast.VarDef):
                self.global_vars.add(item.name)

    def _check_item(self, item):
        """Check an item for unresolved references."""
        if isinstance(item, rast.FnDef):
            self._check_function(item)
        elif isinstance(item, rast.StructDef):
            self._check_struct(item)
        elif isinstance(item, rast.ConstDef):
            self._check_const(item)
        elif isinstance(item, rast.VarDef):
            if item.type:
                self._check_type(item.type)
            if item.value:
                self._check_expr(item.value, Scope(None, set()))
        elif isinstance(item, rast.TraitDef):
            self._check_trait(item)
        elif isinstance(item, rast.ImplBlock):
            self._check_impl(item)

    def _check_function(self, fn: rast.FnDef):
        """Check a function definition."""
        # Check return type
        if fn.ret_type:
            self._check_type(fn.ret_type)

        # Create scope with parameters
        param_names = set()
        for param in fn.params:
            param_names.add(param.name)
            if param.type:
                self._check_type(param.type)

        scope = Scope(None, param_names)

        # Track async context for await validation
        old_in_async = self.in_async_fn
        self.in_async_fn = getattr(fn, 'is_async', False)

        # Check body
        if fn.body:
            self._check_block(fn.body, scope)

        # Restore async context
        self.in_async_fn = old_in_async

    def _check_struct(self, struct: rast.StructDef):
        """Check struct field types."""
        for name, field_type in struct.fields:
            if field_type:
                self._check_type(field_type)

    def _check_const(self, const: rast.ConstDef):
        """Check constant definition."""
        if const.type:
            self._check_type(const.type)
        if const.value:
            self._check_expr(const.value, Scope(None, set()))

    def _check_trait(self, trait: rast.TraitDef):
        """Check trait definition."""
        for method in trait.methods:
            if method.ret_type:
                self._check_type(method.ret_type)
            for param in method.params:
                if param.type:
                    self._check_type(param.type)

    def _check_impl(self, impl: rast.ImplBlock):
        """Check impl block."""
        # Check the type being implemented for
        self._check_type_name(impl.type_name, impl.span)

        # Check each method
        for method in impl.methods:
            self._check_function(method)

    def _check_block(self, block: rast.Block, scope: Scope):
        """Check a block, creating new scope for locals."""
        local_scope = Scope(scope, set())

        for stmt in block.stmts:
            self._check_stmt(stmt, local_scope)

        if block.expr:
            self._check_expr(block.expr, local_scope)

    def _check_stmt(self, stmt: rast.Stmt, scope: Scope):
        """Check a statement."""
        if isinstance(stmt, rast.LetStmt):
            # Add variable to scope after checking init
            if stmt.type:
                self._check_type(stmt.type)
            if stmt.value:
                self._check_expr(stmt.value, scope)
            scope.locals.add(stmt.name)

        elif isinstance(stmt, rast.VarStmt):
            if stmt.type:
                self._check_type(stmt.type)
            if stmt.value:
                self._check_expr(stmt.value, scope)
            scope.locals.add(stmt.name)

        elif isinstance(stmt, rast.AssignStmt):
            self._check_expr(stmt.target, scope)
            self._check_expr(stmt.value, scope)

        elif isinstance(stmt, rast.WhileStmt):
            self._check_expr(stmt.cond, scope)
            self._check_block(stmt.body, scope)

        elif isinstance(stmt, rast.ForStmt):
            # Check iterable
            self._check_expr(stmt.iter, scope)
            # Add loop variable to new scope for body
            body_scope = Scope(scope, {stmt.var})
            self._check_block(stmt.body, body_scope)

        elif isinstance(stmt, rast.ReturnStmt):
            if stmt.value:
                self._check_expr(stmt.value, scope)

        elif isinstance(stmt, rast.ExprStmt):
            self._check_expr(stmt.expr, scope)

    def _check_pattern(self, pattern: rast.Pattern, scope: Scope):
        """Check a pattern and add any bindings to scope."""
        if isinstance(pattern, rast.IdentPattern):
            scope.locals.add(pattern.name)
        elif isinstance(pattern, rast.StructPattern):
            self._check_type_name(pattern.struct_name, pattern.span)
            for field_pat in pattern.fields:
                self._check_pattern(field_pat.pattern, scope)
        elif isinstance(pattern, rast.EnumPattern):
            # Check enum type exists
            if pattern.enum_name and pattern.enum_name not in self.enums:
                self.errors.append(NameError(
                    f"Unknown enum: {pattern.enum_name}",
                    pattern.span
                ))
            # Add any bindings from the variant pattern
            if pattern.value_pattern:
                self._check_pattern(pattern.value_pattern, scope)

    def _check_expr(self, expr: rast.Expr, scope: Scope):
        """Check an expression for unresolved references."""
        if isinstance(expr, rast.Ident):
            # Check if identifier is defined
            name = expr.name
            if not (scope.contains(name) or
                    name in self.functions or
                    name in self.constants or
                    name in self.global_vars or
                    name in self.enums or
                    name in self.BUILTINS):
                self.errors.append(NameError(
                    f"Unknown identifier: {name}",
                    expr.span
                ))

        elif isinstance(expr, rast.Call):
            # Check function name if it's a simple identifier
            if isinstance(expr.func, rast.Ident):
                name = expr.func.name
                if not (name in self.functions or
                        name in self.BUILTINS):
                    self.errors.append(NameError(
                        f"Unknown function: {name}",
                        expr.span
                    ))
            else:
                # Complex expression as function (e.g., method call, field access)
                self._check_expr(expr.func, scope)

            # Check type arguments
            for type_arg in expr.type_args:
                self._check_type(type_arg)

            # Check arguments
            for arg in expr.args:
                self._check_expr(arg, scope)

        elif isinstance(expr, rast.BinOp):
            self._check_expr(expr.left, scope)
            self._check_expr(expr.right, scope)

        elif isinstance(expr, rast.UnaryOp):
            self._check_expr(expr.operand, scope)

        elif isinstance(expr, rast.Index):
            self._check_expr(expr.expr, scope)
            self._check_expr(expr.index, scope)

        elif isinstance(expr, rast.Field):
            self._check_expr(expr.expr, scope)
            # Don't check field names - need type info

        elif isinstance(expr, rast.MethodCall):
            self._check_expr(expr.expr, scope)
            for arg in expr.args:
                self._check_expr(arg, scope)

        elif isinstance(expr, rast.If):
            self._check_expr(expr.cond, scope)
            self._check_block(expr.then_block, scope)
            if expr.else_block:
                self._check_block(expr.else_block, scope)

        elif isinstance(expr, rast.Block):
            self._check_block(expr, scope)

        elif isinstance(expr, rast.Cast):
            self._check_expr(expr.expr, scope)
            if expr.target:
                self._check_type(expr.target)

        elif isinstance(expr, rast.StructLit):
            self._check_type_name(expr.name, expr.span)
            for field in expr.fields:
                self._check_expr(field.value, scope)

        elif isinstance(expr, rast.ArrayLit):
            for elem in expr.elements:
                self._check_expr(elem, scope)

        elif isinstance(expr, rast.Match):
            self._check_expr(expr.value, scope)
            for arm in expr.arms:
                arm_scope = Scope(scope, set())
                self._check_pattern(arm.pattern, arm_scope)
                if arm.body:
                    self._check_expr(arm.body, arm_scope)

        elif isinstance(expr, rast.Await):
            # await can only appear inside async functions
            if not self.in_async_fn:
                self.errors.append(NameError(
                    "await can only be used inside async functions",
                    expr.span
                ))
            self._check_expr(expr.expr, scope)

        # Literals (IntLit, FloatLit, StringLit, CharLit, BoolLit, NilLit)
        # don't need checking

    def _check_type(self, type_node: rast.Type):
        """Check that a type reference is valid."""
        if isinstance(type_node, rast.NamedType):
            self._check_type_name(type_node.name, type_node.span)
            # Check generic arguments
            for arg in type_node.args:
                self._check_type(arg)
        elif isinstance(type_node, rast.PtrType):
            self._check_type(type_node.inner)
        elif isinstance(type_node, rast.ArrayType):
            self._check_type(type_node.inner)
        elif isinstance(type_node, rast.FnType):
            for param_type in type_node.params:
                self._check_type(param_type)
            if type_node.ret:
                self._check_type(type_node.ret)
        elif isinstance(type_node, rast.UnionType):
            for member in type_node.members:
                self._check_type(member)

    def _check_type_name(self, name: str, span: Optional[rast.Span]):
        """Check that a type name is defined."""
        if name in self.BUILTIN_TYPES:
            return
        if name in self.structs:
            return
        if name in self.enums:
            return
        if name in self.type_aliases:
            return
        if name in self.traits:
            return

        self.errors.append(NameError(
            f"Unknown type: {name}",
            span
        ))


def resolve_names(module: rast.Module) -> List[NameError]:
    """Resolve all names in a module.

    Args:
        module: The parsed module after import resolution

    Returns:
        List of name resolution errors (empty if successful)
    """
    resolver = NameResolver()
    return resolver.resolve(module)
