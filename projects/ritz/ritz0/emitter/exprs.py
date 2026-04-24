"""
Expression emission mixin for the LLVM emitter.

Contains: _emit_expr, _emit_index, _emit_slice, _emit_string_slice,
          _emit_vec_slice, _emit_lvalue_addr, _emit_unary, _emit_field_access,
          _emit_struct_lit, _emit_closure, _emit_lambda, _emit_heap_expr,
          _emit_await, _emit_await_poll_loop, _find_free_variables
"""

from typing import Optional, List, Tuple
from llvmlite import ir
import ritz_ast as rast


class ExprEmitterMixin:
    """Mixin providing expression emission methods for LLVMEmitter."""

    def _emit_expr(self, expr: rast.Expr) -> ir.Value:
        """Emit an expression."""
        if isinstance(expr, rast.IntLit):
            return ir.Constant(self.i64, expr.value)

        elif isinstance(expr, rast.FloatLit):
            return ir.Constant(self.f64, expr.value)

        elif isinstance(expr, rast.BoolLit):
            return ir.Constant(self.i1, 1 if expr.value else 0)

        elif isinstance(expr, rast.StringLit):
            # "hello" -> StrView (zero-copy view)
            return self._emit_strview_string_literal(expr)

        elif isinstance(expr, rast.CStringLit):
            # C-string literal: c"hello" -> *u8 (null-terminated)
            gvar = self._get_string_constant(expr.value)
            # Get pointer to first element
            zero = ir.Constant(self.i64, 0)
            return self.builder.gep(gvar, [zero, zero])

        # Note: SpanStringLit (s"...") was removed in AGAST #98 — bare
        # StringLit now emits a StrView aggregate of the same shape.

        elif isinstance(expr, rast.InterpString):
            # Interpolated strings are currently only supported as expression statements
            # where they get desugared to print calls. When used as a value, error.
            raise ValueError(f"Interpolated strings cannot be used as values (line {expr.span.line}). "
                           "Use them as expression statements for printing, or build a String manually.")

        elif isinstance(expr, rast.CharLit):
            # Character literal is a u8 constant
            return ir.Constant(self.i8, expr.value)

        elif isinstance(expr, rast.NullLit):
            # Null pointer literal - type must be inferred from context
            # Default to *u8 (i8*) which is compatible with most pointer casts
            return ir.Constant(self.i8.as_pointer(), None)

        elif isinstance(expr, rast.Ident):
            name = expr.name

            # Check constants
            if name in self.constants:
                val, ty = self.constants[name]
                return ir.Constant(ty, val)

            # Check locals (var bindings) FIRST - mutable vars shadow let bindings
            # This is critical because the same name may appear as both 'var' and 'let'
            # in different branches of if-else, and we need to use the correct one.
            if name in self.locals:
                alloca, ty = self.locals[name]
                return self.builder.load(alloca)

            # Check params (let bindings and function params)
            if name in self.params:
                val, _ = self.params[name]
                return val

            # Check module-level globals (var at top level)
            if name in self.globals:
                gvar, ty = self.globals[name]
                return self.builder.load(gvar)

            # Handle nil keyword (null pointer literal)
            if name == "nil":
                # Return a null pointer of i8* type
                return ir.Constant(ir.IntType(8).as_pointer(), None)

            # Check if this is a unit variant (enum variant without parentheses)
            if name in self.variant_to_enum:
                # Get the variant and check if it's a unit variant (no fields)
                enum_name = self.variant_to_enum[name]
                variant = self._get_enum_variant(enum_name, name)
                if not variant.fields:
                    # Unit variant - construct it with no args
                    return self._emit_enum_variant_constructor(name, [])

            # Check if this is a function name - return function pointer
            if name in self.functions:
                fn, fn_def = self.functions[name]
                # Return the function as a pointer value
                return fn

            raise ValueError(f"Unknown identifier: {name}")

        elif isinstance(expr, rast.BinOp):
            op = expr.op

            # Handle short-circuit operators BEFORE evaluating right operand
            if op in ('&&', 'and'):
                return self._emit_short_circuit_and(expr)
            elif op in ('||', 'or'):
                return self._emit_short_circuit_or(expr)

            left = self._emit_expr(expr.left)
            right = self._emit_expr(expr.right)

            # Ensure same type
            if left.type != right.type:
                if isinstance(left.type, ir.IntType) and isinstance(right.type, ir.IntType):
                    # Determine signedness for proper extension
                    left_unsigned = self._infer_unsigned_expr(expr.left)
                    right_unsigned = self._infer_unsigned_expr(expr.right)

                    if left.type.width < right.type.width:
                        # Use zext for i1 (boolean) or unsigned types
                        if left.type.width == 1 or left_unsigned:
                            left = self.builder.zext(left, right.type)
                        else:
                            left = self.builder.sext(left, right.type)
                    else:
                        if right.type.width == 1 or right_unsigned:
                            right = self.builder.zext(right, left.type)
                        else:
                            right = self.builder.sext(right, left.type)

            op = expr.op

            # Handle pointer comparison with integer 0 (null pointer check)
            # Only for comparison operators, not arithmetic
            if op in ('==', '!=', '<', '<=', '>', '>='):
                if isinstance(left.type, ir.PointerType) and isinstance(right.type, ir.IntType):
                    # Convert integer 0 to null pointer for comparison
                    if isinstance(expr.right, rast.IntLit) and expr.right.value == 0:
                        right = ir.Constant(left.type, None)  # null pointer
                elif isinstance(right.type, ir.PointerType) and isinstance(left.type, ir.IntType):
                    # Convert integer 0 to null pointer for comparison
                    if isinstance(expr.left, rast.IntLit) and expr.left.value == 0:
                        left = ir.Constant(right.type, None)  # null pointer

            # Check if this is a floating-point operation
            is_float = self._is_float_type(left.type) or self._is_float_type(right.type)

            if op == '+':
                # Handle pointer arithmetic: ptr + int -> GEP
                if isinstance(left.type, ir.PointerType) and isinstance(right.type, ir.IntType):
                    return self.builder.gep(left, [right])
                elif isinstance(right.type, ir.PointerType) and isinstance(left.type, ir.IntType):
                    return self.builder.gep(right, [left])
                if is_float:
                    return self.builder.fadd(left, right)
                return self.builder.add(left, right)
            elif op == '-':
                # Handle pointer arithmetic: ptr - int -> GEP with negated offset
                if isinstance(left.type, ir.PointerType) and isinstance(right.type, ir.IntType):
                    neg_right = self.builder.neg(right)
                    return self.builder.gep(left, [neg_right])
                if is_float:
                    return self.builder.fsub(left, right)
                return self.builder.sub(left, right)
            elif op == '*':
                if is_float:
                    return self.builder.fmul(left, right)
                return self.builder.mul(left, right)
            elif op == '/':
                if is_float:
                    return self.builder.fdiv(left, right)
                # Use unsigned division for unsigned types
                if self._infer_unsigned_expr(expr.left) or self._infer_unsigned_expr(expr.right):
                    return self.builder.udiv(left, right)
                return self.builder.sdiv(left, right)
            elif op == '%':
                if is_float:
                    return self.builder.frem(left, right)
                # Use unsigned remainder for unsigned types
                if self._infer_unsigned_expr(expr.left) or self._infer_unsigned_expr(expr.right):
                    return self.builder.urem(left, right)
                return self.builder.srem(left, right)
            elif op == '==':
                if is_float:
                    return self.builder.fcmp_ordered('==', left, right)
                # Equality is sign-agnostic
                return self.builder.icmp_signed('==', left, right)
            elif op == '!=':
                if is_float:
                    return self.builder.fcmp_ordered('!=', left, right)
                # Inequality is sign-agnostic
                return self.builder.icmp_signed('!=', left, right)
            elif op == '<':
                if is_float:
                    return self.builder.fcmp_ordered('<', left, right)
                # Use unsigned comparison for unsigned types
                if self._infer_unsigned_expr(expr.left) or self._infer_unsigned_expr(expr.right):
                    return self.builder.icmp_unsigned('<', left, right)
                return self.builder.icmp_signed('<', left, right)
            elif op == '<=':
                if is_float:
                    return self.builder.fcmp_ordered('<=', left, right)
                if self._infer_unsigned_expr(expr.left) or self._infer_unsigned_expr(expr.right):
                    return self.builder.icmp_unsigned('<=', left, right)
                return self.builder.icmp_signed('<=', left, right)
            elif op == '>':
                if is_float:
                    return self.builder.fcmp_ordered('>', left, right)
                if self._infer_unsigned_expr(expr.left) or self._infer_unsigned_expr(expr.right):
                    return self.builder.icmp_unsigned('>', left, right)
                return self.builder.icmp_signed('>', left, right)
            elif op == '>=':
                if is_float:
                    return self.builder.fcmp_ordered('>=', left, right)
                if self._infer_unsigned_expr(expr.left) or self._infer_unsigned_expr(expr.right):
                    return self.builder.icmp_unsigned('>=', left, right)
                return self.builder.icmp_signed('>=', left, right)
            elif op == '&':
                # Bitwise AND: left & right
                return self.builder.and_(left, right)
            elif op == '|':
                # Bitwise OR: left | right
                return self.builder.or_(left, right)
            elif op == '^':
                # Bitwise XOR: left ^ right
                return self.builder.xor(left, right)
            elif op == '<<':
                # Left shift: left << right
                return self.builder.shl(left, right)
            elif op == '>>':
                # Right shift: use logical shift (lshr) for unsigned, arithmetic (ashr) for signed
                if self._infer_unsigned_expr(expr.left):
                    return self.builder.lshr(left, right)
                return self.builder.ashr(left, right)
            else:
                raise ValueError(f"Unknown operator: {op}")

        elif isinstance(expr, rast.Call):
            return self._emit_call(expr)

        elif isinstance(expr, rast.Index):
            return self._emit_index(expr)

        elif isinstance(expr, rast.If):
            # If used as expression - returns phi value from branches
            result = self._emit_if(expr)
            if result is not None:
                return result
            # If no value (shouldn't happen for well-formed if expressions), return 0
            return ir.Constant(self.i32, 0)

        elif isinstance(expr, rast.UnaryOp):
            return self._emit_unary(expr)

        elif isinstance(expr, rast.StructLit):
            return self._emit_struct_lit(expr)

        elif isinstance(expr, rast.ArrayLit):
            return self._emit_array_lit(expr)

        elif isinstance(expr, rast.ArrayFill):
            return self._emit_array_fill(expr)

        elif isinstance(expr, rast.Field):
            return self._emit_field_access(expr)

        elif isinstance(expr, rast.Cast):
            return self._emit_cast(expr)

        elif isinstance(expr, rast.Match):
            return self._emit_match(expr)

        elif isinstance(expr, rast.MethodCall):
            return self._emit_method_call(expr)

        elif isinstance(expr, rast.TryOp):
            return self._emit_try_op(expr)

        elif isinstance(expr, rast.SliceExpr):
            return self._emit_slice(expr)

        elif isinstance(expr, rast.Await):
            return self._emit_await(expr)

        elif isinstance(expr, rast.Closure):
            return self._emit_closure(expr)

        elif isinstance(expr, rast.Lambda):
            return self._emit_lambda(expr)

        elif isinstance(expr, rast.HeapExpr):
            return self._emit_heap_expr(expr)

        else:
            raise NotImplementedError(f"Expression: {type(expr)}")


    def _emit_index(self, expr: rast.Index) -> ir.Value:
        """Emit an indexing operation: base[index]."""
        index = self._emit_expr(expr.index)

        # Special handling for identifiers that are arrays
        if isinstance(expr.expr, rast.Ident):
            name = expr.expr.name
            if name in self.locals:
                alloca, ty = self.locals[name]
                if isinstance(ty, ir.ArrayType):
                    # Array type - use two-level GEP [0, index] on the alloca
                    zero = ir.Constant(self.i32, 0)
                    ptr = self.builder.gep(alloca, [zero, index])
                    return self.builder.load(ptr)
            elif name in self.const_arrays:
                # Const array - use two-level GEP [0, index] on the global
                gvar, ty = self.const_arrays[name]
                if isinstance(ty, ir.ArrayType):
                    zero = ir.Constant(self.i32, 0)
                    ptr = self.builder.gep(gvar, [zero, index])
                    return self.builder.load(ptr)
            elif name in self.globals:
                gvar, ty = self.globals[name]
                if isinstance(ty, ir.ArrayType):
                    # Global array - use two-level GEP [0, index] on the global
                    zero = ir.Constant(self.i32, 0)
                    ptr = self.builder.gep(gvar, [zero, index])
                    return self.builder.load(ptr)

        # Special handling for struct field that is an array (e.g., buf.data[0])
        if isinstance(expr.expr, rast.Field):
            # Get the address of the array field, then index into it
            field_addr = self._emit_lvalue_addr(expr.expr)
            if isinstance(field_addr.type, ir.PointerType):
                pointee = field_addr.type.pointee
                if isinstance(pointee, ir.ArrayType):
                    # GEP with [0, index] to get element address
                    zero = ir.Constant(self.i32, 0)
                    ptr = self.builder.gep(field_addr, [zero, index])
                    return self.builder.load(ptr)

        # Special handling for nested array indexing (e.g., arr[i][j] where arr is [N][M]T)
        if isinstance(expr.expr, rast.Index):
            # Get pointer to inner array element using lvalue_addr
            inner_addr = self._emit_lvalue_addr(expr.expr)
            if isinstance(inner_addr.type, ir.PointerType):
                pointee = inner_addr.type.pointee
                if isinstance(pointee, ir.ArrayType):
                    # Inner is array - GEP with [0, index] to get element address
                    zero = ir.Constant(self.i32, 0)
                    ptr = self.builder.gep(inner_addr, [zero, index])
                    return self.builder.load(ptr)

        # Check if this is a Vec or String type - provide index sugar
        # v[i] becomes vec_get(&v, i), s[i] becomes string_get(&s, i)
        if isinstance(expr.expr, rast.Ident):
            name = expr.expr.name
            if name in self.ritz_types:
                base_ritz_type = self.ritz_types[name]
                if isinstance(base_ritz_type, rast.NamedType):
                    type_name = base_ritz_type.name

                    # Handle Vec<T> / Vec$T indexing
                    if type_name.startswith('Vec$') or type_name == 'Vec':
                        # Get element type from Vec$T name
                        if type_name.startswith('Vec$'):
                            elem_type_name = type_name[4:]  # Strip "Vec$"
                        else:
                            # Try to get from type args
                            if base_ritz_type.type_args:
                                elem_ty = base_ritz_type.type_args[0]
                                elem_type_name = self._type_to_mangled_name(elem_ty)
                            else:
                                raise ValueError("Vec type without element type")

                        # Build vec_get call: vec_get$T(&v, i)
                        fn_name = f"vec_get${elem_type_name}"
                        if fn_name not in self.functions:
                            raise ValueError(f"Vec indexing requires {fn_name} to be defined")

                        fn, _ = self.functions[fn_name]
                        # Get pointer to vec
                        vec_ptr = self._emit_lvalue_addr(expr.expr)
                        # Ensure index is i64
                        if index.type != self.i64:
                            index = self.builder.sext(index, self.i64)
                        return self.builder.call(fn, [vec_ptr, index])

                    # Handle String indexing: s[i] -> string_get(&s, i)
                    elif type_name == 'String':
                        fn_name = "string_get"
                        if fn_name not in self.functions:
                            raise ValueError(f"String indexing requires {fn_name} to be defined")

                        fn, _ = self.functions[fn_name]
                        # Get pointer to string
                        str_ptr = self._emit_lvalue_addr(expr.expr)
                        # Ensure index is i64
                        if index.type != self.i64:
                            index = self.builder.sext(index, self.i64)
                        return self.builder.call(fn, [str_ptr, index])

                    # Handle HashMapI64 indexing: m[k] -> hashmap_i64_get(&m, k)
                    elif type_name == 'HashMapI64':
                        fn_name = "hashmap_i64_get"
                        if fn_name not in self.functions:
                            raise ValueError(f"HashMapI64 indexing requires {fn_name} to be defined")

                        fn, _ = self.functions[fn_name]
                        # Get pointer to hashmap
                        map_ptr = self._emit_lvalue_addr(expr.expr)
                        # Ensure key is i64
                        if index.type != self.i64:
                            index = self.builder.sext(index, self.i64)
                        return self.builder.call(fn, [map_ptr, index])

        # General case
        base = self._emit_expr(expr.expr)

        # Get element type
        if isinstance(base.type, ir.PointerType):
            elem_type = base.type.pointee
            # GEP to get pointer to element
            ptr = self.builder.gep(base, [index])
            # Load the element
            return self.builder.load(ptr)
        else:
            raise ValueError(f"Cannot index type: {base.type}")


    def _emit_slice(self, expr: rast.SliceExpr) -> ir.Value:
        """Emit a slice operation: a[start:end].

        This is zero-cost syntax sugar that translates to method/function calls:
        - String: s[1:5] → string_slice(&s, 1, 5)
        - Vec<T>: v[1:5] → vec_slice_T(&v, 1, 5)

        For missing bounds:
        - [:end] → slice(0, end)
        - [start:] → slice(start, len)
        - [:] → clone()
        """
        # Determine the type of the base expression
        if isinstance(expr.expr, rast.Ident):
            name = expr.expr.name
            if name in self.ritz_types:
                base_ritz_type = self.ritz_types[name]
                if isinstance(base_ritz_type, rast.NamedType):
                    type_name = base_ritz_type.name

                    # Handle String slicing
                    if type_name == 'String':
                        return self._emit_string_slice(expr)

                    # Handle Vec<T> slicing
                    if type_name.startswith('Vec$') or type_name == 'Vec':
                        return self._emit_vec_slice(expr, type_name, base_ritz_type)

        raise ValueError(f"Slice operation not supported for this type. "
                         f"Only String and Vec types support slicing.")


    def _emit_string_slice(self, expr: rast.SliceExpr) -> ir.Value:
        """Emit string slice: s[1:5] → string_slice(&s, 1, 5)."""
        fn_name = "string_slice"
        if fn_name not in self.functions:
            raise ValueError(f"String slicing requires {fn_name} to be defined "
                             "(import ritzlib.string)")

        fn, _ = self.functions[fn_name]
        str_ptr = self._emit_lvalue_addr(expr.expr)

        # Emit start index (default to 0)
        if expr.start is not None:
            start = self._emit_expr(expr.start)
            if start.type != self.i64:
                start = self.builder.sext(start, self.i64)
        else:
            start = ir.Constant(self.i64, 0)

        # Emit end index (default to len)
        if expr.end is not None:
            end = self._emit_expr(expr.end)
            if end.type != self.i64:
                end = self.builder.sext(end, self.i64)
        else:
            # Get length via string_len
            len_fn_name = "string_len"
            if len_fn_name not in self.functions:
                raise ValueError(f"String slicing requires {len_fn_name} to be defined")
            len_fn, _ = self.functions[len_fn_name]
            end = self.builder.call(len_fn, [str_ptr])

        return self.builder.call(fn, [str_ptr, start, end])


    def _emit_vec_slice(self, expr: rast.SliceExpr, type_name: str,
                        base_ritz_type: rast.NamedType) -> ir.Value:
        """Emit vec slice: v[1:5] → vec_slice_T(&v, 1, 5)."""
        # Get element type from Vec$T name
        if type_name.startswith('Vec$'):
            elem_type_name = type_name[4:]  # Strip "Vec$"
        else:
            # Try to get from type args
            if base_ritz_type.args:
                elem_ty = base_ritz_type.args[0]
                elem_type_name = self._type_to_mangled_name(elem_ty)
            else:
                raise ValueError("Vec type without element type")

        fn_name = f"vec_slice${elem_type_name}"
        if fn_name not in self.functions:
            raise ValueError(f"Vec slicing requires {fn_name} to be defined")

        fn, _ = self.functions[fn_name]
        vec_ptr = self._emit_lvalue_addr(expr.expr)

        # Emit start index (default to 0)
        if expr.start is not None:
            start = self._emit_expr(expr.start)
            if start.type != self.i64:
                start = self.builder.sext(start, self.i64)
        else:
            start = ir.Constant(self.i64, 0)

        # Emit end index (default to len)
        if expr.end is not None:
            end = self._emit_expr(expr.end)
            if end.type != self.i64:
                end = self.builder.sext(end, self.i64)
        else:
            # Get length via vec_len$T
            len_fn_name = f"vec_len${elem_type_name}"
            if len_fn_name not in self.functions:
                raise ValueError(f"Vec slicing requires {len_fn_name} to be defined")
            len_fn, _ = self.functions[len_fn_name]
            end = self.builder.call(len_fn, [vec_ptr])

        return self.builder.call(fn, [vec_ptr, start, end])


    def _emit_lvalue_addr(self, expr: rast.Expr) -> ir.Value:
        """
        Get the address of an lvalue expression (for assignment purposes).
        Returns a pointer to the storage location, not the loaded value.
        """
        if isinstance(expr, rast.Ident):
            name = expr.name
            if name in self.locals:
                alloca, _ = self.locals[name]
                return alloca
            elif name in self.globals:
                gvar, _ = self.globals[name]
                return gvar
            elif name in self.params:
                # For params/let bindings that are SSA values, create a temp alloca
                # This allows borrowing of immutable bindings (for RERITZ @ and call-site borrows)
                val, ty = self.params[name]
                temp_alloca = self.builder.alloca(ty, name=f"{name}.addr")
                self.builder.store(val, temp_alloca)
                return temp_alloca
            else:
                raise ValueError(f"Unknown variable: {name}")
        elif isinstance(expr, rast.UnaryOp) and expr.op == '*':
            # *ptr -> return ptr itself
            return self._emit_expr(expr.operand)
        elif isinstance(expr, rast.Index):
            # arr[i] -> GEP to element
            index = self._emit_expr(expr.index)
            if isinstance(expr.expr, rast.Ident):
                name = expr.expr.name
                if name in self.locals:
                    alloca, ty = self.locals[name]
                    if isinstance(ty, ir.ArrayType):
                        zero = ir.Constant(self.i32, 0)
                        return self.builder.gep(alloca, [zero, index])
                elif name in self.globals:
                    gvar, ty = self.globals[name]
                    if isinstance(ty, ir.ArrayType):
                        # Global array - use two-level GEP [0, index] on the global
                        zero = ir.Constant(self.i32, 0)
                        return self.builder.gep(gvar, [zero, index])
            # Handle struct field that is an array (e.g., buf.data[0] = x)
            if isinstance(expr.expr, rast.Field):
                field_addr = self._emit_lvalue_addr(expr.expr)
                if isinstance(field_addr.type, ir.PointerType):
                    pointee = field_addr.type.pointee
                    if isinstance(pointee, ir.ArrayType):
                        zero = ir.Constant(self.i32, 0)
                        return self.builder.gep(field_addr, [zero, index])
            # Handle nested array indexing (e.g., arr[i][j] where arr is [N][M]T)
            if isinstance(expr.expr, rast.Index):
                inner_addr = self._emit_lvalue_addr(expr.expr)
                if isinstance(inner_addr.type, ir.PointerType):
                    pointee = inner_addr.type.pointee
                    if isinstance(pointee, ir.ArrayType):
                        # Inner is array - GEP with [0, index] to get element
                        zero = ir.Constant(self.i32, 0)
                        return self.builder.gep(inner_addr, [zero, index])
                    else:
                        # Inner is pointer to element - GEP with [index]
                        return self.builder.gep(inner_addr, [index])
            base = self._emit_expr(expr.expr)
            if isinstance(base.type, ir.PointerType):
                return self.builder.gep(base, [index])
            raise ValueError(f"Cannot index type: {base.type}")
        elif isinstance(expr, rast.Field):
            # struct.field -> GEP to field
            # There are several cases:
            # 1. Base is a local struct variable: buf.data -> GEP from alloca
            # 2. Base is a pointer to struct: p.data where p: *Struct -> load p, then GEP

            if isinstance(expr.expr, rast.Ident):
                name = expr.expr.name
                if name in self.locals:
                    alloca, ty = self.locals[name]
                    # Check if this is a pointer-to-struct (e.g., b: *StackBuffer)
                    if isinstance(ty, ir.PointerType):
                        pointee = ty.pointee
                        if isinstance(pointee, ir.BaseStructType):
                            # Load the pointer first, then GEP into the struct
                            struct_ptr = self.builder.load(alloca)
                            struct_name = self._get_struct_name_from_type(pointee)
                            if struct_name:
                                idx = self._get_struct_field_index(struct_name, expr.field)
                                return self.builder.gep(struct_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                    # Regular struct local: GEP directly from alloca
                    if isinstance(ty, ir.BaseStructType):
                        struct_name = self._get_struct_name_from_type(ty)
                        if struct_name:
                            idx = self._get_struct_field_index(struct_name, expr.field)
                            return self.builder.gep(alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                elif name in self.params:
                    ptr_val, ptr_ty = self.params[name]
                    # If it's a pointer to a struct, use the pointer directly
                    if isinstance(ptr_ty, ir.PointerType):
                        pointee = ptr_ty.pointee
                        if isinstance(pointee, ir.BaseStructType):
                            struct_name = self._get_struct_name_from_type(pointee)
                            if struct_name:
                                idx = self._get_struct_field_index(struct_name, expr.field)
                                return self.builder.gep(ptr_val, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])

            # General case: get address of struct then GEP to field
            struct_addr = self._emit_lvalue_addr(expr.expr)
            if isinstance(struct_addr.type, ir.PointerType):
                pointee = struct_addr.type.pointee
                if isinstance(pointee, ir.BaseStructType):
                    struct_name = self._get_struct_name_from_type(pointee)
                    if struct_name:
                        idx = self._get_struct_field_index(struct_name, expr.field)
                        return self.builder.gep(struct_addr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                # Handle pointer-to-pointer case: if the field is a pointer type,
                # we need to load it first then GEP into the struct it points to.
                # e.g., lex.defs.defs where lex.defs is *TokenDefs
                if isinstance(pointee, ir.PointerType):
                    inner_pointee = pointee.pointee
                    if isinstance(inner_pointee, ir.BaseStructType):
                        # Load the pointer value
                        ptr_val = self.builder.load(struct_addr)
                        struct_name = self._get_struct_name_from_type(inner_pointee)
                        if struct_name:
                            idx = self._get_struct_field_index(struct_name, expr.field)
                            return self.builder.gep(ptr_val, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
            raise ValueError(f"Cannot access field on type: {struct_addr.type}")
        else:
            raise ValueError(f"Cannot get address of: {type(expr)}")


    def _find_free_variables(self, expr: rast.Expr, bound_vars: set) -> set:
        """Find free variables in an expression (referenced but not locally bound).

        Args:
            expr: Expression to analyze
            bound_vars: Set of variable names that are locally bound

        Returns:
            Set of free variable names
        """
        free_vars = set()

        if isinstance(expr, rast.Ident):
            name = expr.name
            # Only consider it free if not bound locally and not a global/function
            if name not in bound_vars:
                free_vars.add(name)

        elif isinstance(expr, rast.BinOp):
            free_vars |= self._find_free_variables(expr.left, bound_vars)
            free_vars |= self._find_free_variables(expr.right, bound_vars)

        elif isinstance(expr, rast.UnaryOp):
            free_vars |= self._find_free_variables(expr.operand, bound_vars)

        elif isinstance(expr, rast.Call):
            if isinstance(expr.func, rast.Ident):
                # Check if this is a variable (function pointer) vs a defined function
                # If it's not a known function, it might be a captured variable
                func_name = expr.func.name
                if func_name not in self.functions and func_name not in bound_vars:
                    # Could be a captured function pointer variable
                    free_vars.add(func_name)
            else:
                free_vars |= self._find_free_variables(expr.func, bound_vars)
            for arg in expr.args:
                free_vars |= self._find_free_variables(arg, bound_vars)

        elif isinstance(expr, rast.Index):
            free_vars |= self._find_free_variables(expr.expr, bound_vars)
            free_vars |= self._find_free_variables(expr.index, bound_vars)

        elif isinstance(expr, rast.Field):
            free_vars |= self._find_free_variables(expr.expr, bound_vars)

        elif isinstance(expr, rast.If):
            free_vars |= self._find_free_variables(expr.cond, bound_vars)
            for stmt in expr.then_block.stmts:
                free_vars |= self._find_free_variables_stmt(stmt, bound_vars)
            if expr.then_block.expr:
                free_vars |= self._find_free_variables(expr.then_block.expr, bound_vars)
            if expr.else_block:
                for stmt in expr.else_block.stmts:
                    free_vars |= self._find_free_variables_stmt(stmt, bound_vars)
                if expr.else_block.expr:
                    free_vars |= self._find_free_variables(expr.else_block.expr, bound_vars)

        elif isinstance(expr, rast.Cast):
            free_vars |= self._find_free_variables(expr.expr, bound_vars)

        elif isinstance(expr, rast.StructLit):
            for _, val in expr.fields:
                free_vars |= self._find_free_variables(val, bound_vars)

        elif isinstance(expr, rast.ArrayLit):
            for elem in expr.elements:
                free_vars |= self._find_free_variables(elem, bound_vars)

        elif isinstance(expr, rast.Closure):
            # Nested closure - add its params to bound vars
            inner_bound = bound_vars | {p.name for p in expr.params}
            free_vars |= self._find_free_variables(expr.body, inner_bound)

        # Literals don't have free variables
        elif isinstance(expr, (rast.IntLit, rast.FloatLit, rast.StringLit,
                               rast.CStringLit, rast.CharLit,
                               rast.BoolLit, rast.NullLit)):
            pass

        return free_vars


    def _find_free_variables_stmt(self, stmt: rast.Stmt, bound_vars: set) -> set:
        """Find free variables in a statement."""
        free_vars = set()

        if isinstance(stmt, rast.ExprStmt):
            free_vars |= self._find_free_variables(stmt.expr, bound_vars)
        elif isinstance(stmt, (rast.LetStmt, rast.VarStmt)):
            free_vars |= self._find_free_variables(stmt.value, bound_vars)
        elif isinstance(stmt, rast.ReturnStmt):
            if stmt.value:
                free_vars |= self._find_free_variables(stmt.value, bound_vars)
        elif isinstance(stmt, rast.AssignStmt):
            free_vars |= self._find_free_variables(stmt.value, bound_vars)
            free_vars |= self._find_free_variables(stmt.target, bound_vars)

        return free_vars


    def _emit_await(self, await_expr: rast.Await) -> ir.Value:
        """Emit an await expression.

        Behavior depends on context:
        1. Inside async fn: Handled by async_transform, should not reach here
        2. Outside async fn: Generate poll loop for async function calls

        For non-async calls, just evaluate the inner expression (synchronous MVP).
        """
        inner_expr = await_expr.expr

        # Check if this is a call to an async function
        if isinstance(inner_expr, rast.Call) and isinstance(inner_expr.func, rast.Ident):
            fn_name = inner_expr.func.name
            if fn_name in self.async_functions:
                # Async function call outside async context - generate poll loop
                return self._emit_await_poll_loop(fn_name, inner_expr.args)

        # Non-async call: just evaluate the inner expression (MVP behavior)
        return self._emit_expr(inner_expr)


    def _emit_await_poll_loop(self, fn_name: str, args: list) -> ir.Value:
        """Generate a poll loop for awaiting an async function outside async context.

        Equivalent to:
            var future = fn_name(args)
            while true
                let result = fn_name_poll(&future)
                if result >= 0
                    return result
        """
        future_type_name = f"{fn_name}_Future"
        poll_fn_name = f"{fn_name}_poll"

        # Get LLVM types
        future_llvm_type = self.struct_types.get(future_type_name)
        if future_llvm_type is None:
            raise ValueError(f"Unknown Future type: {future_type_name}")

        # Get the poll function
        if poll_fn_name not in self.functions:
            raise ValueError(f"Unknown poll function: {poll_fn_name}")
        poll_fn, _ = self.functions[poll_fn_name]

        # Get the constructor function
        if fn_name not in self.functions:
            raise ValueError(f"Unknown async function: {fn_name}")
        constructor_fn, _ = self.functions[fn_name]

        # Emit arguments with type conversion (int literals default to i64)
        emit_args = []
        for i, arg in enumerate(args):
            val = self._emit_expr(arg)
            expected_type = constructor_fn.function_type.args[i]
            val = self._convert_type(val, expected_type)
            emit_args.append(val)

        # Create the future: var future = fn_name(args)
        future_alloca = self.builder.alloca(future_llvm_type, name="future")
        future_val = self.builder.call(constructor_fn, emit_args, name="future_init")
        self.builder.store(future_val, future_alloca)

        # Create loop blocks
        loop_block = self.current_fn.append_basic_block("poll_loop")
        done_block = self.current_fn.append_basic_block("poll_done")

        # Jump to loop
        self.builder.branch(loop_block)

        # Poll loop body
        self.builder.position_at_end(loop_block)

        # Call poll: result = fn_name_poll(&future)
        poll_result = self.builder.call(poll_fn, [future_alloca], name="poll_result")

        # Check if ready: result >= 0
        pending = ir.Constant(self.i32, -1)
        is_pending = self.builder.icmp_signed('==', poll_result, pending, name="is_pending")
        self.builder.cbranch(is_pending, loop_block, done_block)

        # Done block - return the result
        self.builder.position_at_end(done_block)

        return poll_result


    def _emit_heap_expr(self, heap_expr: rast.HeapExpr) -> ir.Value:
        """Emit a heap expression: heap expr.

        Compiles to inline heap allocation:
            1. Evaluate expression to get value
            2. malloc(sizeof(T))
            3. Store value at allocated address
            4. Return *T pointer to heap memory

        The heap keyword provides syntactic sugar for heap allocation:
            let p = heap 42
            // allocates i64 on heap, returns *i64
        """
        # Emit the inner expression
        inner_val = self._emit_expr(heap_expr.expr)
        llvm_type = inner_val.type

        # Calculate size of the value type
        size = self._type_size_bytes(llvm_type)
        size_val = ir.Constant(self.i64, size)

        # Call malloc - look in functions first, then extern_fns
        malloc_fn = None
        if "malloc" in self.functions:
            malloc_fn, _ = self.functions["malloc"]
        elif "malloc" in self.extern_fns:
            malloc_fn_type, _ = self.extern_fns["malloc"]
            # Declare the function if not already in module
            malloc_fn = self.module.globals.get("malloc")
            if malloc_fn is None:
                malloc_fn = ir.Function(self.module, ir.FunctionType(
                    ir.PointerType(ir.IntType(8)), [self.i64]), name="malloc")
        if malloc_fn is None:
            raise ValueError("heap requires ritzlib.memory (malloc not found)")
        raw_ptr = self.builder.call(malloc_fn, [size_val], name="heap_ptr")

        # Cast to *T
        ptr_type = ir.PointerType(llvm_type)
        typed_ptr = self.builder.bitcast(raw_ptr, ptr_type, name="typed_ptr")

        # Store the value
        self.builder.store(inner_val, typed_ptr)

        # Return the typed pointer directly
        # Usage: let p = heap 42  // p is *i64
        #        *p = 100        // modify value
        #        free(p as *u8)  // manual cleanup
        return typed_ptr


    def _emit_closure(self, closure: rast.Closure) -> ir.Value:
        """Emit a closure expression: |params| body.

        Closures compile to anonymous functions. If the closure captures
        variables from the enclosing scope, they are passed as additional
        parameters and the closure is wrapped in a partial application struct.

        For closures without captures, returns a direct function pointer.
        For closures with captures, returns a "fat pointer" struct containing
        the function pointer and captured values.

        The closure's types are inferred from:
        1. Explicit parameter types in the closure
        2. The expected type from context (e.g., let x: fn(i32) -> i32 = |x| ...)

        Returns a function pointer to the anonymous function.
        """
        # Get expected type for type inference
        expected_type = self.closure_expected_type

        if expected_type is None:
            raise ValueError(
                f"Cannot infer closure type - must be assigned to a typed variable. "
                f"Use: let f: fn(T) -> R = |x| ..."
            )

        # Find captured variables
        param_names = {p.name for p in closure.params}
        free_vars = self._find_free_variables(closure.body, param_names)

        # Filter to only variables that exist in the enclosing scope
        # (not globals, functions, or unknown names)
        captures = []
        capture_values = []
        capture_llvm_types = []
        capture_ritz_types = []

        for name in sorted(free_vars):  # Sort for deterministic ordering
            # Check if it's a local or parameter in the enclosing scope
            if name in self.locals:
                alloca, ty = self.locals[name]
                val = self.builder.load(alloca)
                captures.append(name)
                capture_values.append(val)
                capture_llvm_types.append(ty)
                capture_ritz_types.append(self.ritz_types.get(name))
            elif name in self.params:
                val, ty = self.params[name]
                captures.append(name)
                capture_values.append(val)
                capture_llvm_types.append(ty)
                capture_ritz_types.append(self.ritz_types.get(name))
            # Globals, functions, and constants are accessible without capture

        # Generate unique name for the anonymous function
        self.closure_counter += 1
        closure_name = f"__closure_{self.closure_counter}"

        # Build parameter types from expected type PLUS captured variables
        param_types = [self._ritz_type_to_llvm(p) for p in expected_type.params]
        # Add capture types at the end
        param_types.extend(capture_llvm_types)

        ret_type = self._ritz_type_to_llvm(expected_type.ret) if expected_type.ret else self.void

        # Create the function type and function
        fn_type = ir.FunctionType(ret_type, param_types)
        fn = ir.Function(self.module, fn_type, name=closure_name)
        fn.linkage = 'private'  # Not visible outside this module

        # Save current state
        saved_builder = self.builder
        saved_fn = self.current_fn
        saved_locals = self.locals.copy()
        saved_params = self.params.copy()
        saved_ritz_types = self.ritz_types.copy()
        saved_has_returned = self.has_returned

        # Set up new function context
        self.current_fn = fn
        self.locals = {}
        self.params = {}
        self.has_returned = False

        # Create entry block
        block = fn.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)

        # Set up regular parameters
        num_regular_params = len(closure.params)
        for i, (arg, param) in enumerate(zip(fn.args[:num_regular_params], closure.params)):
            param_name = param.name
            arg.name = f"{param_name}.arg"

            # Allocate storage for the parameter (so it can be used like a local)
            alloca = self.builder.alloca(arg.type, name=param_name)
            self.builder.store(arg, alloca)
            self.locals[param_name] = (alloca, arg.type)

            # Store Ritz type
            if i < len(expected_type.params):
                self.ritz_types[param_name] = expected_type.params[i]

        # Set up captured variables as parameters
        for i, (cap_name, cap_ritz_type) in enumerate(zip(captures, capture_ritz_types)):
            arg = fn.args[num_regular_params + i]
            arg.name = f"{cap_name}.cap"

            # Allocate storage for the captured value
            alloca = self.builder.alloca(arg.type, name=cap_name)
            self.builder.store(arg, alloca)
            self.locals[cap_name] = (alloca, arg.type)

            # Store Ritz type
            if cap_ritz_type:
                self.ritz_types[cap_name] = cap_ritz_type

        # Emit closure body expression
        result = self._emit_expr(closure.body)

        # Emit return
        if ret_type == self.void:
            self.builder.ret_void()
        else:
            # Convert result type if needed
            result = self._convert_type(result, ret_type)
            self.builder.ret(result)

        # Restore previous state
        self.builder = saved_builder
        self.current_fn = saved_fn
        self.locals = saved_locals
        self.params = saved_params
        self.ritz_types = saved_ritz_types
        self.has_returned = saved_has_returned

        # If there are no captures, return the function pointer directly
        if not captures:
            return fn

        # With captures, we use a "capture by value" approach:
        # The closure function takes extra parameters for captured values.
        # We generate a unique thunk per closure INSTANCE that passes the
        # captured values.
        #
        # To handle multiple instances of the same closure (e.g., calling
        # make_adder(5) and make_adder(10)), we use an array of environment
        # slots. Each closure instance gets its own slot.
        #
        # This is a simplified implementation for the bootstrap compiler.
        # A production implementation would use heap-allocated environments.

        # Create the environment struct type (same for all instances of this closure)
        env_struct_name = f"__closure_env_{self.closure_counter}"
        if env_struct_name not in self._closure_env_types:
            env_struct_type = self.module.context.get_identified_type(env_struct_name)
            env_struct_type.set_body(*capture_llvm_types)
            self._closure_env_types[env_struct_name] = env_struct_type
        else:
            env_struct_type = self._closure_env_types[env_struct_name]

        # Create an array of environment slots for this closure (max 16 instances)
        # This is a hack - proper impl would use heap allocation
        MAX_CLOSURE_INSTANCES = 16
        env_array_name = f"__closure_env_{self.closure_counter}_array"
        if env_array_name not in self._closure_env_arrays:
            env_array_type = ir.ArrayType(env_struct_type, MAX_CLOSURE_INSTANCES)
            env_array = ir.GlobalVariable(self.module, env_array_type, name=env_array_name)
            env_array.linkage = 'private'
            # Initialize with zeros
            zero_env = ir.Constant(env_struct_type, [ir.Constant(ty, None) for ty in capture_llvm_types])
            env_array.initializer = ir.Constant(env_array_type, [zero_env] * MAX_CLOSURE_INSTANCES)
            self._closure_env_arrays[env_array_name] = env_array

            # Create a counter for instance allocation
            counter_name = f"__closure_env_{self.closure_counter}_idx"
            counter = ir.GlobalVariable(self.module, self.i32, name=counter_name)
            counter.linkage = 'private'
            counter.initializer = ir.Constant(self.i32, 0)
            self._closure_env_counters[env_array_name] = counter

        env_array = self._closure_env_arrays[env_array_name]
        env_counter = self._closure_env_counters[env_array_name]

        # Allocate a new environment slot
        current_idx = self.builder.load(env_counter)
        # Store captured values into the allocated slot
        for i, (cap_name, cap_val, cap_ty) in enumerate(zip(captures, capture_values, capture_llvm_types)):
            ptr = self.builder.gep(env_array, [ir.Constant(self.i32, 0), current_idx, ir.Constant(self.i32, i)])
            self.builder.store(cap_val, ptr)

        # Increment the counter for next allocation (with wraparound)
        next_idx = self.builder.add(current_idx, ir.Constant(self.i32, 1))
        wrapped_idx = self.builder.urem(next_idx, ir.Constant(self.i32, MAX_CLOSURE_INSTANCES))
        self.builder.store(wrapped_idx, env_counter)

        # Generate a thunk for each environment slot (we only need one per slot actually used)
        # For simplicity, we generate MAX_CLOSURE_INSTANCES thunks statically
        thunk_array_name = f"__closure_thunks_{self.closure_counter}"
        if thunk_array_name not in self._closure_thunk_arrays:
            thunk_param_types = [self._ritz_type_to_llvm(p) for p in expected_type.params]
            thunk_fn_type = ir.FunctionType(ret_type, thunk_param_types)

            thunks = []
            for slot_idx in range(MAX_CLOSURE_INSTANCES):
                thunk_name = f"__closure_thunk_{self.closure_counter}_{slot_idx}"
                thunk_fn = ir.Function(self.module, thunk_fn_type, name=thunk_name)
                thunk_fn.linkage = 'private'

                # Build thunk body
                thunk_block = thunk_fn.append_basic_block(name="entry")
                thunk_builder = ir.IRBuilder(thunk_block)

                # Gather arguments: regular params + captured values from this slot
                call_args = list(thunk_fn.args)
                for i in range(len(captures)):
                    ptr = thunk_builder.gep(env_array, [
                        ir.Constant(self.i32, 0),
                        ir.Constant(self.i32, slot_idx),
                        ir.Constant(self.i32, i)
                    ])
                    cap_val = thunk_builder.load(ptr)
                    call_args.append(cap_val)

                # Call the real closure function
                result = thunk_builder.call(fn, call_args)

                if ret_type == self.void:
                    thunk_builder.ret_void()
                else:
                    thunk_builder.ret(result)

                thunks.append(thunk_fn)

            # Create array of thunk function pointers
            thunk_ptr_type = ir.PointerType(thunk_fn_type)
            thunk_array_type = ir.ArrayType(thunk_ptr_type, MAX_CLOSURE_INSTANCES)
            thunk_array = ir.GlobalVariable(self.module, thunk_array_type, name=thunk_array_name)
            thunk_array.linkage = 'private'
            thunk_array.initializer = ir.Constant(thunk_array_type, thunks)
            self._closure_thunk_arrays[thunk_array_name] = thunk_array

        thunk_array = self._closure_thunk_arrays[thunk_array_name]

        # Look up the thunk for this instance's slot
        thunk_ptr_ptr = self.builder.gep(thunk_array, [ir.Constant(self.i32, 0), current_idx])
        thunk_ptr = self.builder.load(thunk_ptr_ptr)

        return thunk_ptr


    def _emit_lambda(self, lambda_expr: rast.Lambda) -> ir.Value:
        """Emit a lambda expression: fn(params) -> RetType expr.

        Lambda is the older form of closure with explicit parameters.
        We convert it to a Closure and delegate to _emit_closure.
        """
        # Convert Lambda parameters to ClosureParams
        closure_params = [
            rast.ClosureParam(p.name, p.type)
            for p in lambda_expr.params
        ]

        # Create a Closure AST node and delegate
        closure = rast.Closure(
            lambda_expr.span,
            closure_params,
            lambda_expr.body,
            captures=[]
        )

        return self._emit_closure(closure)


    def _emit_unary(self, expr: rast.UnaryOp) -> ir.Value:
        """Emit a unary operation: -x, !x, *x, @x, @&x."""
        # Handle address-of operators: @, @&
        # RERITZ syntax: @ = immutable ref, @& = mutable ref
        # Legacy & and &mut are still accepted here for backward compat with existing AST
        # All map to the same LLVM IR: taking a pointer to the operand
        if expr.op in ('&', '@', '&mut', '@&'):
            if isinstance(expr.operand, rast.Ident):
                name = expr.operand.name
                if name in self.locals:
                    alloca, _ = self.locals[name]
                    return alloca  # Return the alloca pointer
                elif name in self.globals:
                    gvar, _ = self.globals[name]
                    return gvar  # Return the global variable pointer
                elif name in self.params:
                    # For params/let bindings that are SSA values, create a temp alloca
                    # This allows taking address of immutable bindings (for @ operator in RERITZ)
                    val, ty = self.params[name]
                    temp_alloca = self.builder.alloca(ty, name=f"{name}.addr")
                    self.builder.store(val, temp_alloca)
                    return temp_alloca
                else:
                    raise ValueError(f"Unknown variable: {name}")
            elif isinstance(expr.operand, rast.Index):
                # For &arr[i] or &arr[i][j], use _emit_lvalue_addr which handles all cases
                # including nested array indexing
                return self._emit_lvalue_addr(expr.operand)
            elif isinstance(expr.operand, rast.Field):
                # For &struct.field, use _emit_lvalue_addr to get the field's address
                return self._emit_lvalue_addr(expr.operand)
            else:
                # For more complex expressions, emit the value (might be a pointer already)
                operand = self._emit_expr(expr.operand)
                return operand

        operand = self._emit_expr(expr.operand)

        if expr.op == '-':
            # Negation
            if isinstance(operand.type, ir.IntType):
                return self.builder.neg(operand)
            else:
                return self.builder.fneg(operand)

        elif expr.op in ('!', 'not'):
            # Logical not - compare with zero
            zero = ir.Constant(operand.type, 0)
            return self.builder.icmp_unsigned('==', operand, zero)

        elif expr.op == '*':
            # Dereference
            if isinstance(operand.type, ir.PointerType):
                return self.builder.load(operand)
            else:
                raise ValueError(f"Cannot dereference non-pointer: {operand.type}")

        elif expr.op == '~':
            # Bitwise NOT: ~x = xor x, -1
            all_ones = ir.Constant(operand.type, -1)
            return self.builder.xor(operand, all_ones)

        else:
            raise ValueError(f"Unknown unary operator: {expr.op}")


    def _emit_struct_lit(self, expr: rast.StructLit) -> ir.Value:
        """Emit a struct literal: MyStruct { field1: value1, field2: value2 }."""
        struct_name = expr.name
        if struct_name not in self.struct_types:
            raise ValueError(f"Unknown struct: {struct_name}")

        struct_type = self.struct_types[struct_name]
        field_defs = self.struct_fields[struct_name]

        # Create a map of field name -> index
        field_indices = {name: i for i, (name, _) in enumerate(field_defs)}

        # Build an array of field values in the correct order
        field_values = [None] * len(field_defs)

        # Fill in the field values as provided in the struct literal
        for field_name, field_expr in expr.fields:
            if field_name not in field_indices:
                raise ValueError(f"Unknown field {field_name} in struct {struct_name}")

            idx = field_indices[field_name]
            field_val = self._emit_expr(field_expr)

            # Get the expected type for this field
            _, expected_type = field_defs[idx]
            expected_llvm_type = self._ritz_type_to_llvm(expected_type)

            # Convert if needed
            field_val = self._convert_type(field_val, expected_llvm_type)

            field_values[idx] = field_val

        # Check that all fields are provided
        for i, val in enumerate(field_values):
            if val is None:
                field_name, _ = field_defs[i]
                raise ValueError(f"Field {field_name} not provided in struct literal")

        # Build struct using insert_value
        # Start with undef then insert each field
        result = ir.Constant(struct_type, ir.Undefined)
        for i, val in enumerate(field_values):
            result = self.builder.insert_value(result, val, i)

        return result


    def _get_local_alloca(self, expr: rast.Expr) -> Optional[ir.AllocaInstr]:
        """Get the alloca for a local variable expression, if applicable.

        Returns the alloca pointer if expr is an identifier that's a local variable,
        otherwise returns None.
        """
        if isinstance(expr, rast.Ident):
            name = expr.name
            if name in self.locals:
                alloca, _ = self.locals[name]
                return alloca
        return None


    def _emit_field_access(self, expr: rast.Field) -> ir.Value:
        """Emit field access: struct_val.field or struct_ptr->field.

        Supports implicit deref for Box<T> types:
          If b: Box<Point>, then b.x is equivalent to (*b.ptr).x

        For local variables, uses GEP directly on the alloca to avoid loading
        the entire struct into a register (which can crash LLVM for large structs).
        """
        # Optimization: if the inner expression is a local variable, use GEP directly
        # instead of loading the entire struct then extracting a field.
        local_alloca = self._get_local_alloca(expr.expr)
        if local_alloca is not None:
            pointee_type = local_alloca.type.pointee
            if isinstance(pointee_type, ir.BaseStructType):
                struct_name = self._get_struct_name_from_type(pointee_type)
                if struct_name:
                    # Check for Box implicit deref
                    if self._is_box_type(struct_name) and not self._struct_has_field(struct_name, expr.field):
                        inner_type_name = self._get_box_inner_type_name(struct_name)
                        if inner_type_name and self._struct_has_field(inner_type_name, expr.field):
                            ptr_field_ptr = self.builder.gep(local_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
                            inner_ptr = self.builder.load(ptr_field_ptr)
                            idx = self._get_struct_field_index(inner_type_name, expr.field)
                            field_ptr = self.builder.gep(inner_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                            return self.builder.load(field_ptr)

                    idx = self._get_struct_field_index(struct_name, expr.field)
                    field_ptr = self.builder.gep(local_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                    return self.builder.load(field_ptr)

        struct_val = self._emit_expr(expr.expr)

        # Determine if we're accessing through a pointer or value
        if isinstance(struct_val.type, ir.PointerType):
            # Pointer to struct: load the struct first
            pointee_type = struct_val.type.pointee
            if isinstance(pointee_type, ir.BaseStructType):
                # This is a pointer to a struct type - we need to GEP to the field, then load
                struct_name = self._get_struct_name_from_type(pointee_type)
                if struct_name:
                    # Check for Box implicit deref: if field not on Box, deref through ptr
                    if self._is_box_type(struct_name) and not self._struct_has_field(struct_name, expr.field):
                        inner_type_name = self._get_box_inner_type_name(struct_name)
                        if inner_type_name and self._struct_has_field(inner_type_name, expr.field):
                            # Load the ptr field (index 0 in Box), then access field on pointee
                            ptr_field_ptr = self.builder.gep(struct_val, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
                            inner_ptr = self.builder.load(ptr_field_ptr)
                            # Now access the field on the inner struct
                            idx = self._get_struct_field_index(inner_type_name, expr.field)
                            field_ptr = self.builder.gep(inner_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                            return self.builder.load(field_ptr)

                    idx = self._get_struct_field_index(struct_name, expr.field)
                    # GEP to field
                    field_ptr = self.builder.gep(struct_val, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                    # Load the field value
                    return self.builder.load(field_ptr)
                else:
                    raise ValueError(f"Cannot determine struct type for pointer")
            elif isinstance(pointee_type, ir.PointerType):
                # Pointer to pointer - this means we have a RefType that needs one more deref
                # struct_val is **T, we need to load once to get *T, then GEP into the struct
                inner_pointee = pointee_type.pointee
                if isinstance(inner_pointee, ir.BaseStructType):
                    # Load to get *T from **T
                    struct_ptr = self.builder.load(struct_val)
                    struct_name = self._get_struct_name_from_type(inner_pointee)
                    if struct_name:
                        idx = self._get_struct_field_index(struct_name, expr.field)
                        field_ptr = self.builder.gep(struct_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                        return self.builder.load(field_ptr)
                raise ValueError(f"Cannot access field on double pointer: {pointee_type}")
            else:
                raise ValueError(f"Cannot access field on non-struct pointer: {pointee_type}")
        elif isinstance(struct_val.type, ir.BaseStructType):
            # Value of struct type: extract the field
            struct_name = self._get_struct_name_from_type(struct_val.type)
            if struct_name:
                # Check for Box implicit deref: if field not on Box, deref through ptr
                if self._is_box_type(struct_name) and not self._struct_has_field(struct_name, expr.field):
                    inner_type_name = self._get_box_inner_type_name(struct_name)
                    if inner_type_name and self._struct_has_field(inner_type_name, expr.field):
                        # Extract the ptr field (index 0 in Box)
                        inner_ptr = self.builder.extract_value(struct_val, 0)
                        # Now access the field on the inner struct via the pointer
                        idx = self._get_struct_field_index(inner_type_name, expr.field)
                        field_ptr = self.builder.gep(inner_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                        return self.builder.load(field_ptr)

                idx = self._get_struct_field_index(struct_name, expr.field)
                return self.builder.extract_value(struct_val, idx)
            else:
                raise ValueError(f"Cannot determine struct type for value")
        else:
            raise ValueError(f"Cannot access field on non-struct type: {struct_val.type}")


