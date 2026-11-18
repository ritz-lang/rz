"""The Monomorphizer's last step: rewrite the module to name specialized
items, dropping the generic ones.  Split out of monomorph.py (AGAST #3522)."""

from typing import List

import ritz_ast as rast
from monomorph_core import TypeSubstitution, map_child_nodes

class MonoRewriteMixin:
    """Monomorphizer methods that rewrite generic uses to their mangled
    instances.  Mixed into monomorph.Monomorphizer; reads its state."""

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
            # Field names are independent of the type substitution, so
            # they carry through specialization unchanged.
            new_variants.append(rast.Variant(variant.span, variant.name, new_fields,
                                             field_names=list(variant.field_names),
                                             discriminant=variant.discriminant))

        new_enum = rast.EnumDef(enum.span, enum.name, new_variants,
                                type_params=enum.type_params,
                                repr=enum.repr)
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
                            type_params=fn.type_params, is_async=fn.is_async, is_pub=fn.is_pub,
                            is_decl=fn.is_decl)
        # Preserve source_file for separate compilation
        if hasattr(fn, 'source_file'):
            new_fn.source_file = fn.source_file
        # A generated `E.from` returns Option<E>, so it is always rewritten;
        # the emitter gives it weak_odr linkage by this mark (#2160).
        if getattr(fn, 'generated', False):
            new_fn.generated = True
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
        elif isinstance(ty, rast.FnType):
            new_params = [self._rewrite_type(p) for p in ty.params]
            new_ret = self._rewrite_type(ty.ret) if ty.ret else None
            return rast.FnType(ty.span, new_params, new_ret, ty.callconv)
        elif isinstance(ty, rast.TupleType):
            return rast.TupleType(ty.span, [self._rewrite_type(e) for e in ty.elements])
        elif isinstance(ty, rast.VectorType):
            return rast.VectorType(ty.span, ty.count, self._rewrite_type(ty.inner))
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
                                   self._rewrite_expr(stmt.value),
                                   stmt.op)
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
            # Same generic walk as _specialize_stmt (AGAST #1937).
            return map_child_nodes(stmt, self._rewrite_expr,
                                   self._rewrite_stmt, self._rewrite_type)

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
                             self._rewrite_expr(expr.right),
                             wrapping=expr.wrapping)
        elif isinstance(expr, rast.UnaryOp):
            return rast.UnaryOp(expr.span, expr.op,
                               self._rewrite_expr(expr.operand))
        elif isinstance(expr, rast.Index):
            return rast.Index(expr.span,
                             self._rewrite_expr(expr.expr),
                             self._rewrite_expr(expr.index),
                             expr.bracket)
        elif isinstance(expr, rast.Field):
            return rast.Field(expr.span,
                             self._rewrite_expr(expr.expr),
                             expr.field, expr.name_span)
        elif isinstance(expr, rast.MethodCall):
            return rast.MethodCall(expr.span,
                                   self._rewrite_expr(expr.expr),
                                   expr.method,
                                   [self._rewrite_expr(arg) for arg in expr.args],
                                   expr.name_span)
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
                            self._rewrite_type(expr.target), expr.as_span)
        elif isinstance(expr, rast.Range):
            return rast.Range(expr.span,
                             self._rewrite_expr(expr.start) if expr.start else None,
                             self._rewrite_expr(expr.end) if expr.end else None,
                             expr.inclusive)
        elif isinstance(expr, rast.Match):
            # Match arms are ordinary expressions: a generic call in an arm
            # body must be rewritten to its mangled name like anywhere else.
            new_arms = [
                rast.MatchArm(arm.span,
                              arm.pattern,
                              self._rewrite_expr(arm.guard) if arm.guard else None,
                              self._rewrite_expr(arm.body))
                for arm in expr.arms
            ]
            return rast.Match(expr.span, self._rewrite_expr(expr.expr), new_arms,
                              self._rewrite_type(expr.ctor_type) if expr.ctor_type else None)
        elif isinstance(expr, rast.SliceExpr):
            return rast.SliceExpr(expr.span,
                                  self._rewrite_expr(expr.expr),
                                  self._rewrite_expr(expr.start) if expr.start else None,
                                  self._rewrite_expr(expr.end) if expr.end else None)
        elif isinstance(expr, rast.TryOp):
            return rast.TryOp(expr.span, self._rewrite_expr(expr.expr))
        else:
            # Grouped, TupleLit, ...: a generic call nested inside
            # must still reach its mangled name (AGAST #1937).
            return map_child_nodes(expr, self._rewrite_expr,
                                   self._rewrite_stmt, self._rewrite_type)
