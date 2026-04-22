"""
Statement emission mixin for the LLVM emitter.

Contains: _emit_stmt, _emit_if, _emit_while, _emit_for, _emit_assert,
          _emit_unsafe_block, _emit_asm, _emit_short_circuit_and/or,
          _emit_interp_string_print, _emit_print_value, _emit_print_int_inline,
          _emit_write_str, _emit_deferred_stmts
"""

from typing import Union, Optional, List, Tuple
from llvmlite import ir
import ritz_ast as rast


class StmtEmitterMixin:
    """Mixin providing statement emission methods for LLVMEmitter."""

    def _emit_deferred_stmts(self):
        """Emit all deferred statements in LIFO order (last defer first).

        Called before every scope exit (return, end of function).
        Deferred statements execute with the current scope's variables
        still alive, so they can reference local variables by pointer.
        """
        if not hasattr(self, 'defer_stack') or not self.defer_stack:
            return
        # LIFO — emit in reverse order
        for deferred_stmt in reversed(self.defer_stack):
            if not self.builder.block.is_terminated:
                self._emit_stmt(deferred_stmt)


    def _emit_stmt(self, stmt: rast.Stmt) -> Union[bool, ir.Value, None]:
        """Emit a statement. Returns True if block terminated."""
        # Set debug location for source-level debugging
        self._set_debug_loc(stmt)

        if isinstance(stmt, rast.ReturnStmt):
            ret_type = self.current_fn.function_type.return_type
            if stmt.value:
                # Check if we're returning a local variable - it should be moved, not dropped
                exclude_var = None
                if isinstance(stmt.value, rast.Ident):
                    var_name = stmt.value.name
                    if var_name in self.locals:
                        # This is a local variable being returned - treat as move
                        exclude_var = var_name

                # Set expected type for closure inference if return type is a function type
                if self.current_fn_def and isinstance(self.current_fn_def.ret_type, rast.FnType):
                    self.closure_expected_type = self.current_fn_def.ret_type
                val = self._emit_expr(stmt.value)
                self.closure_expected_type = None  # Clear context
                val = self._convert_type(val, ret_type)
                # Emit deferred stmts before drops (defer runs before Drop)
                self._emit_deferred_stmts()
                # Emit drops for all scopes before return (excluding moved variable)
                self._emit_drop_for_all_scopes(exclude_var)
                self.builder.ret(val)
            else:
                # Emit deferred stmts before drops
                self._emit_deferred_stmts()
                # Emit drops for all scopes before return
                self._emit_drop_for_all_scopes()
                if ret_type == self.void:
                    self.builder.ret_void()
                else:
                    self.builder.ret(ir.Constant(ret_type, 0))
            self.has_returned = True
            return True

        elif isinstance(stmt, rast.VarStmt):
            ritz_type = stmt.type  # May be None if type is inferred
            # Get line number for debug info
            stmt_span = getattr(stmt, 'span', None)
            stmt_line = stmt_span.line if stmt_span else 1

            if stmt.type:
                ty = self._ritz_type_to_llvm(stmt.type)
                self.ritz_types[stmt.name] = stmt.type  # Store Ritz type for signedness
            elif stmt.value:
                # Infer from value - emit first to get LLVM type
                val = self._emit_expr(stmt.value)
                ty = val.type
                # Also infer Ritz type for Drop tracking
                inferred_ritz_type = self._infer_ritz_type(stmt.value, val)
                if inferred_ritz_type:
                    ritz_type = inferred_ritz_type
                    self.ritz_types[stmt.name] = ritz_type
                # Always allocate in entry block to prevent stack leaks in loops
                alloca = self._alloca_in_entry_block(ty, f"{stmt.name}.addr")
                self.builder.store(val, alloca)
                self.locals[stmt.name] = (alloca, ty)
                # Register for Drop if type was inferred and implements Drop
                if ritz_type:
                    self._register_drop_variable(stmt.name, alloca, ritz_type)
                    self._mark_drop_variable_initialized(alloca)
                return None
            else:
                ty = self.i64  # Default

            # Always allocate in entry block to prevent stack leaks in loops
            # and to ensure allocas dominate all uses (required for mem2reg).
            alloca = self._alloca_in_entry_block(ty, f"{stmt.name}.addr")

            if stmt.value:
                # Handle String literal inference: "hello" -> string_from("hello")
                if (stmt.type and isinstance(stmt.type, rast.NamedType)
                    and stmt.type.name == 'String'
                    and isinstance(stmt.value, rast.StringLit)):
                    val = self._emit_string_from_literal(stmt.value)
                    val = self._convert_type(val, ty)
                    self.builder.store(val, alloca)
                # Special case: large array fill - initialize alloca directly with memset
                # This avoids loading/storing huge arrays which crashes LLVM SelectionDAG
                elif isinstance(stmt.value, rast.ArrayFill) and stmt.value.count > 64:
                    self._emit_array_fill_to_alloca(stmt.value, alloca, ty)
                # Check if this is an enum variant constructor that needs type context
                elif self._is_enum_variant_call(stmt.value) and stmt.type and isinstance(stmt.type, rast.NamedType):
                    # Use declared enum type to construct the correct variant
                    val = self._emit_enum_variant_with_type(stmt.value, stmt.type.name)
                    val = self._convert_type(val, ty)
                    self.builder.store(val, alloca)
                else:
                    # Set SIMD expected type context for var statements too
                    if stmt.type and isinstance(stmt.type, rast.NamedType):
                        if stmt.type.name in ('v8i32', 'v4i64', 'v16i16', 'v32i8',
                                              'v4i32', 'v2i64', 'v8i16', 'v16i8'):
                            self.simd_expected_type = stmt.type
                    val = self._emit_expr(stmt.value)
                    self.simd_expected_type = None  # Clear SIMD context
                    val = self._convert_type(val, ty)
                    self.builder.store(val, alloca)
            self.locals[stmt.name] = (alloca, ty)
            # Register for Drop if type is known and implements Drop
            if ritz_type:
                self._register_drop_variable(stmt.name, alloca, ritz_type)
                # Mark as initialized if we just assigned a value
                if stmt.value:
                    self._mark_drop_variable_initialized(alloca)
            # Emit debug info for variable (requires ritz_type for proper type info)
            if ritz_type:
                self._emit_dbg_declare(alloca, stmt.name, ritz_type, stmt_line)
            return None

        elif isinstance(stmt, rast.LetStmt):
            # Handle String literal inference: "hello" -> string_from("hello")
            if (stmt.type and isinstance(stmt.type, rast.NamedType)
                and stmt.type.name == 'String'
                and isinstance(stmt.value, rast.StringLit)):
                # Convert string literal to String via string_from
                val = self._emit_string_from_literal(stmt.value)
            else:
                # Set expected type context for closure type inference
                if stmt.type and isinstance(stmt.type, rast.FnType):
                    self.closure_expected_type = stmt.type
                # Set expected type context for SIMD type inference (e.g., v8i32 vs v4i32)
                if stmt.type and isinstance(stmt.type, rast.NamedType):
                    if stmt.type.name in ('v8i32', 'v4i64', 'v16i16', 'v32i8',
                                          'v4i32', 'v2i64', 'v8i16', 'v16i8'):
                        self.simd_expected_type = stmt.type
                val = self._emit_expr(stmt.value)
                self.closure_expected_type = None  # Clear context
                self.simd_expected_type = None  # Clear SIMD context
            if stmt.type:
                # Use declared type and convert value if needed
                declared_ty = self._ritz_type_to_llvm(stmt.type)
                val = self._convert_type(val, declared_ty)
                self.params[stmt.name] = (val, declared_ty)
                self.ritz_types[stmt.name] = stmt.type  # Store Ritz type for signedness
                # Note: let bindings don't get allocas, they're just SSA values
                # For Drop to work, the variable needs to be addressable (use var instead of let)
            else:
                # Infer Ritz type from expression for signedness tracking
                inferred_ritz_type = self._infer_ritz_type(stmt.value, val)
                self.params[stmt.name] = (val, val.type)
                if inferred_ritz_type:
                    self.ritz_types[stmt.name] = inferred_ritz_type
            return None

        elif isinstance(stmt, rast.AssignStmt):
            val = self._emit_expr(stmt.value)
            if isinstance(stmt.target, rast.Ident):
                name = stmt.target.name
                if name in self.locals:
                    alloca, ty = self.locals[name]
                    val = self._convert_type(val, ty)
                    self.builder.store(val, alloca)
                elif name in self.globals:
                    gvar, ty = self.globals[name]
                    val = self._convert_type(val, ty)
                    self.builder.store(val, gvar)
                else:
                    raise ValueError(f"Unknown variable: {name}")
            elif isinstance(stmt.target, rast.Index):
                # Assignment to indexed location: arr[i] = val
                index = self._emit_expr(stmt.target.index)

                # Special handling for identifiers that are arrays
                if isinstance(stmt.target.expr, rast.Ident):
                    name = stmt.target.expr.name
                    if name in self.locals:
                        alloca, ty = self.locals[name]
                        if isinstance(ty, ir.ArrayType):
                            # Array type - use two-level GEP [0, index] on the alloca
                            zero = ir.Constant(self.i32, 0)
                            ptr = self.builder.gep(alloca, [zero, index])
                            val = self._convert_type(val, ty.element)
                            self.builder.store(val, ptr)
                            return None
                    elif name in self.globals:
                        gvar, ty = self.globals[name]
                        if isinstance(ty, ir.ArrayType):
                            # Global array - use two-level GEP [0, index] on the global
                            zero = ir.Constant(self.i32, 0)
                            ptr = self.builder.gep(gvar, [zero, index])
                            val = self._convert_type(val, ty.element)
                            self.builder.store(val, ptr)
                            return None

                # Special handling for struct field that is an array (e.g., buf.data[0] = val)
                if isinstance(stmt.target.expr, rast.Field):
                    field_addr = self._emit_lvalue_addr(stmt.target.expr)
                    if isinstance(field_addr.type, ir.PointerType):
                        pointee = field_addr.type.pointee
                        if isinstance(pointee, ir.ArrayType):
                            zero = ir.Constant(self.i32, 0)
                            ptr = self.builder.gep(field_addr, [zero, index])
                            val = self._convert_type(val, pointee.element)
                            self.builder.store(val, ptr)
                            return None

                # Special handling for nested array indexing (e.g., arr[i][j] = val)
                if isinstance(stmt.target.expr, rast.Index):
                    inner_addr = self._emit_lvalue_addr(stmt.target.expr)
                    if isinstance(inner_addr.type, ir.PointerType):
                        pointee = inner_addr.type.pointee
                        if isinstance(pointee, ir.ArrayType):
                            zero = ir.Constant(self.i32, 0)
                            ptr = self.builder.gep(inner_addr, [zero, index])
                            val = self._convert_type(val, pointee.element)
                            self.builder.store(val, ptr)
                            return None

                # Special handling for HashMapI64 indexed assignment: m[k] = v -> hashmap_i64_insert(&m, k, v)
                if isinstance(stmt.target.expr, rast.Ident):
                    name = stmt.target.expr.name
                    if name in self.ritz_types:
                        base_ritz_type = self.ritz_types[name]
                        if isinstance(base_ritz_type, rast.NamedType):
                            if base_ritz_type.name == 'HashMapI64':
                                fn_name = "hashmap_i64_insert"
                                if fn_name not in self.functions:
                                    raise ValueError(f"HashMapI64 indexed assignment requires {fn_name} to be defined")
                                fn, _ = self.functions[fn_name]
                                # Get pointer to hashmap
                                map_ptr = self._emit_lvalue_addr(stmt.target.expr)
                                # Ensure key is i64
                                if index.type != self.i64:
                                    index = self.builder.sext(index, self.i64)
                                # Ensure value is i64
                                if val.type != self.i64:
                                    val = self.builder.sext(val, self.i64)
                                self.builder.call(fn, [map_ptr, index, val])
                                return None

                # General case - pointer indexing
                base = self._emit_expr(stmt.target.expr)
                if isinstance(base.type, ir.PointerType):
                    ptr = self.builder.gep(base, [index])
                    val = self._convert_type(val, base.type.pointee)
                    self.builder.store(val, ptr)
                else:
                    raise ValueError(f"Cannot index type: {base.type}")
            elif isinstance(stmt.target, rast.UnaryOp) and stmt.target.op == '*':
                # Assignment to dereferenced pointer: *ptr = val
                ptr = self._emit_expr(stmt.target.operand)
                if isinstance(ptr.type, ir.PointerType):
                    val = self._convert_type(val, ptr.type.pointee)
                    self.builder.store(val, ptr)
                else:
                    raise ValueError(f"Cannot dereference non-pointer: {ptr.type}")
            elif isinstance(stmt.target, rast.Field):
                # Assignment to struct field: obj.field = val
                # First, try to get the value of the expression
                # If it's already a pointer to a struct, use it directly
                # Otherwise, try to get its address
                struct_val = self._emit_expr(stmt.target.expr)

                if isinstance(struct_val.type, ir.PointerType):
                    # Expression evaluates to a pointer - use it directly
                    pointee_type = struct_val.type.pointee
                    if isinstance(pointee_type, ir.BaseStructType):
                        struct_name = self._get_struct_name_from_type(pointee_type)
                        if struct_name:
                            idx = self._get_struct_field_index(struct_name, stmt.target.field)
                            _, field_type = self.struct_fields[struct_name][idx]
                            field_llvm_type = self._ritz_type_to_llvm(field_type)
                            field_ptr = self.builder.gep(struct_val, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                            val = self._convert_type(val, field_llvm_type)
                            self.builder.store(val, field_ptr)
                        else:
                            raise ValueError(f"Cannot determine struct type for field assignment")
                    elif isinstance(pointee_type, ir.PointerType) and isinstance(pointee_type.pointee, ir.BaseStructType):
                        # Double pointer (**Struct) - load once to get *Struct, then GEP
                        inner_ptr = self.builder.load(struct_val)
                        inner_pointee = pointee_type.pointee
                        struct_name = self._get_struct_name_from_type(inner_pointee)
                        if struct_name:
                            idx = self._get_struct_field_index(struct_name, stmt.target.field)
                            _, field_type = self.struct_fields[struct_name][idx]
                            field_llvm_type = self._ritz_type_to_llvm(field_type)
                            field_ptr = self.builder.gep(inner_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                            val = self._convert_type(val, field_llvm_type)
                            self.builder.store(val, field_ptr)
                        else:
                            raise ValueError(f"Cannot determine struct type for field assignment")
                    else:
                        raise ValueError(f"Cannot assign field on non-struct pointer: {pointee_type}")
                elif isinstance(struct_val.type, ir.BaseStructType):
                    # Value-type struct - need to get address from lvalue
                    struct_ptr = self._emit_lvalue_addr(stmt.target.expr)
                    struct_name = self._get_struct_name_from_type(struct_val.type)
                    if struct_name:
                        idx = self._get_struct_field_index(struct_name, stmt.target.field)
                        _, field_type = self.struct_fields[struct_name][idx]
                        field_llvm_type = self._ritz_type_to_llvm(field_type)
                        field_ptr = self.builder.gep(struct_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)])
                        val = self._convert_type(val, field_llvm_type)
                        self.builder.store(val, field_ptr)
                    else:
                        raise ValueError(f"Cannot determine struct type for field assignment")
                else:
                    raise ValueError(f"Invalid type for field assignment: {struct_val.type}")
            else:
                raise NotImplementedError(f"Assignment to: {type(stmt.target)}")
            return None

        elif isinstance(stmt, rast.ExprStmt):
            # Check if this is an If expression used as statement
            if isinstance(stmt.expr, rast.If):
                return self._emit_if(stmt.expr)
            # Interpolated strings get desugared to print calls
            if isinstance(stmt.expr, rast.InterpString):
                return self._emit_interp_string_print(stmt.expr)
            return self._emit_expr(stmt.expr)

        elif isinstance(stmt, rast.WhileStmt):
            return self._emit_while(stmt)

        elif isinstance(stmt, rast.ForStmt):
            return self._emit_for(stmt)

        elif isinstance(stmt, rast.AssertStmt):
            return self._emit_assert(stmt)

        elif isinstance(stmt, rast.BreakStmt):
            if not self.loop_stack:
                raise RuntimeError("break statement outside of loop")
            _, break_block = self.loop_stack[-1]
            self.builder.branch(break_block)
            return True  # Terminates this block

        elif isinstance(stmt, rast.ContinueStmt):
            if not self.loop_stack:
                raise RuntimeError("continue statement outside of loop")
            continue_block, _ = self.loop_stack[-1]
            self.builder.branch(continue_block)
            return True  # Terminates this block

        elif isinstance(stmt, rast.DeferStmt):
            # Don't emit now — push onto defer stack for LIFO execution at scope exit
            self.defer_stack.append(stmt.body)
            return None

        elif isinstance(stmt, rast.AsmStmt):
            return self._emit_asm(stmt)

        elif isinstance(stmt, rast.UnsafeBlock):
            return self._emit_unsafe_block(stmt)

        else:
            raise NotImplementedError(f"Statement: {type(stmt)}")

    def _emit_interp_string_print(self, expr: rast.InterpString):
        """Emit print calls for an interpolated string.

        Desugars "x = {x}, y = {y}" to:
            prints("x = ")
            print_int(x)  # or appropriate print function based on type
            prints(", y = ")
            print_int(y)
        """
        for i, part in enumerate(expr.parts):
            # Print string literal part (if non-empty)
            if part:
                str_const = self._get_string_constant(part)
                ptr = self.builder.gep(str_const, [ir.Constant(self.i64, 0), ir.Constant(self.i64, 0)])
                self._emit_write_syscall(ir.Constant(self.i64, 1), ptr, ir.Constant(self.i64, len(part)))

            # Print expression (if not past the last part)
            if i < len(expr.exprs):
                value = self._emit_expr(expr.exprs[i])
                self._emit_print_value(value, expr.exprs[i])

        # Return the byte count of the last write (or 0 if no parts)
        return ir.Constant(self.i64, 0)

    def _emit_print_value(self, value: ir.Value, expr: rast.Expr):
        """Emit code to print a value based on its type.

        Handles: integers, pointers (as strings), booleans.
        Always uses inline printing (syscalls) for self-contained output.
        """
        ty = value.type

        # Integer types - print using inline itoa + write
        if ty in (self.i8, self.i16, self.i32, self.i64):
            # Extend to i64 if needed
            if ty != self.i64:
                value = self.builder.sext(value, self.i64)
            self._emit_print_int_inline(value)

        # Pointer types (assume *u8 = string) - use strlen + write
        elif isinstance(ty, ir.PointerType):
            self._emit_write_str(value)

        # Boolean - print "true" or "false"
        elif ty == self.i1:
            true_str = self._get_string_constant("true")
            false_str = self._get_string_constant("false")
            true_ptr = self.builder.gep(true_str, [ir.Constant(self.i64, 0), ir.Constant(self.i64, 0)])
            false_ptr = self.builder.gep(false_str, [ir.Constant(self.i64, 0), ir.Constant(self.i64, 0)])
            ptr = self.builder.select(value, true_ptr, false_ptr)
            length = self.builder.select(value, ir.Constant(self.i64, 4), ir.Constant(self.i64, 5))
            self._emit_write_syscall(ir.Constant(self.i64, 1), ptr, length)

        else:
            # For other types, try to print as integer
            if hasattr(ty, 'width'):
                value = self.builder.zext(value, self.i64) if ty.width < 64 else value
                self._emit_print_int_inline(value)
            else:
                raise ValueError(f"Cannot print value of type {ty}")

    def _emit_print_int_inline(self, value: ir.Value):
        """Inline integer printing using itoa and write syscall.

        Algorithm: Extract digits in reverse order, store in buffer from end,
        then write the filled portion of the buffer.
        """
        # Allocate buffer at end of 21-byte array and work backwards
        buf = self.builder.alloca(ir.ArrayType(self.i8, 21))
        buf_start = self.builder.gep(buf, [ir.Constant(self.i64, 0), ir.Constant(self.i64, 0)])
        buf_end = self.builder.gep(buf, [ir.Constant(self.i64, 0), ir.Constant(self.i64, 20)])

        # Working pointer (starts at end, moves backwards)
        ptr_ptr = self.builder.alloca(self.i8.as_pointer())
        self.builder.store(buf_end, ptr_ptr)

        val_ptr = self.builder.alloca(self.i64)
        self.builder.store(value, val_ptr)

        # Check if negative
        is_neg = self.builder.icmp_signed('<', value, ir.Constant(self.i64, 0))
        neg_block = self.current_fn.append_basic_block("print_int.neg")
        check_zero = self.current_fn.append_basic_block("print_int.check_zero")
        self.builder.cbranch(is_neg, neg_block, check_zero)

        # Negative: negate value (we'll add '-' at the end)
        self.builder.position_at_end(neg_block)
        neg_val = self.builder.sub(ir.Constant(self.i64, 0), self.builder.load(val_ptr))
        self.builder.store(neg_val, val_ptr)
        self.builder.branch(check_zero)

        # Check for zero special case
        self.builder.position_at_end(check_zero)
        curr_val = self.builder.load(val_ptr)
        is_zero_val = self.builder.icmp_signed('==', curr_val, ir.Constant(self.i64, 0))
        zero_block = self.current_fn.append_basic_block("print_int.zero")
        digit_loop = self.current_fn.append_basic_block("print_int.digits")
        self.builder.cbranch(is_zero_val, zero_block, digit_loop)

        # Zero: just store '0'
        self.builder.position_at_end(zero_block)
        curr_ptr = self.builder.load(ptr_ptr)
        new_ptr = self.builder.gep(curr_ptr, [ir.Constant(self.i64, -1)])
        self.builder.store(ir.Constant(self.i8, ord('0')), new_ptr)
        self.builder.store(new_ptr, ptr_ptr)
        write_block = self.current_fn.append_basic_block("print_int.write")
        self.builder.branch(write_block)

        # Extract digits in reverse
        self.builder.position_at_end(digit_loop)
        val = self.builder.load(val_ptr)
        val_done = self.builder.icmp_signed('==', val, ir.Constant(self.i64, 0))
        digit_done = self.current_fn.append_basic_block("print_int.digit_done")
        digit_body = self.current_fn.append_basic_block("print_int.digit_body")
        self.builder.cbranch(val_done, digit_done, digit_body)

        # Store one digit
        self.builder.position_at_end(digit_body)
        digit = self.builder.srem(self.builder.load(val_ptr), ir.Constant(self.i64, 10))
        char_val = self.builder.add(digit, ir.Constant(self.i64, ord('0')))
        char_byte = self.builder.trunc(char_val, self.i8)

        curr_ptr2 = self.builder.load(ptr_ptr)
        new_ptr2 = self.builder.gep(curr_ptr2, [ir.Constant(self.i64, -1)])
        self.builder.store(char_byte, new_ptr2)
        self.builder.store(new_ptr2, ptr_ptr)

        new_val = self.builder.sdiv(self.builder.load(val_ptr), ir.Constant(self.i64, 10))
        self.builder.store(new_val, val_ptr)
        self.builder.branch(digit_loop)

        # Add minus sign if negative
        self.builder.position_at_end(digit_done)
        add_minus = self.current_fn.append_basic_block("print_int.minus")
        skip_minus = self.current_fn.append_basic_block("print_int.skip_minus")
        self.builder.cbranch(is_neg, add_minus, skip_minus)

        self.builder.position_at_end(add_minus)
        curr_ptr3 = self.builder.load(ptr_ptr)
        new_ptr3 = self.builder.gep(curr_ptr3, [ir.Constant(self.i64, -1)])
        self.builder.store(ir.Constant(self.i8, ord('-')), new_ptr3)
        self.builder.store(new_ptr3, ptr_ptr)
        self.builder.branch(skip_minus)

        self.builder.position_at_end(skip_minus)
        self.builder.branch(write_block)

        # Write the result
        self.builder.position_at_end(write_block)
        final_ptr = self.builder.load(ptr_ptr)
        # Length = buf_end - final_ptr
        ptr_int = self.builder.ptrtoint(final_ptr, self.i64)
        end_int = self.builder.ptrtoint(buf_end, self.i64)
        length = self.builder.sub(end_int, ptr_int)
        self._emit_write_syscall(ir.Constant(self.i64, 1), final_ptr, length)

        done_block = self.current_fn.append_basic_block("print_int.done")
        self.builder.branch(done_block)
        self.builder.position_at_end(done_block)

    def _emit_write_str(self, ptr: ir.Value):
        """Write a null-terminated string using strlen + write."""
        # Calculate length with loop
        len_loop = self.current_fn.append_basic_block("strlen.loop")
        len_body = self.current_fn.append_basic_block("strlen.body")
        len_done = self.current_fn.append_basic_block("strlen.done")

        # Initialize length counter
        len_ptr = self.builder.alloca(self.i64)
        self.builder.store(ir.Constant(self.i64, 0), len_ptr)
        self.builder.branch(len_loop)

        # Loop check: while *(ptr + len) != 0
        self.builder.position_at_end(len_loop)
        curr_len = self.builder.load(len_ptr)
        char_ptr = self.builder.gep(ptr, [curr_len])
        char_val = self.builder.load(char_ptr)
        is_zero = self.builder.icmp_unsigned('==', char_val, ir.Constant(self.i8, 0))
        self.builder.cbranch(is_zero, len_done, len_body)

        # Loop body: increment and continue
        self.builder.position_at_end(len_body)
        curr_len2 = self.builder.load(len_ptr)
        new_len = self.builder.add(curr_len2, ir.Constant(self.i64, 1))
        self.builder.store(new_len, len_ptr)
        self.builder.branch(len_loop)

        # Done: call write
        self.builder.position_at_end(len_done)
        final_len = self.builder.load(len_ptr)
        self._emit_write_syscall(ir.Constant(self.i64, 1), ptr, final_len)

    def _emit_unsafe_block(self, stmt: rast.UnsafeBlock):
        """Emit an unsafe block.

        Unsafe blocks allow raw pointer operations that would otherwise be
        forbidden. The in_unsafe flag tracks whether we're in such a block.

        Syntax:
            unsafe
                *ptr = value    # Raw pointer deref (write)
                let x = *ptr    # Raw pointer deref (read)
                ptr.cast::<T>() # Raw pointer cast
        """
        # Save previous unsafe state (for nested unsafe blocks)
        prev_unsafe = self.in_unsafe
        self.in_unsafe = True

        try:
            # Emit body statements
            for body_stmt in stmt.body.stmts:
                if self._emit_stmt(body_stmt):
                    break  # Block terminated (return/break/continue)
        finally:
            # Restore previous state
            self.in_unsafe = prev_unsafe

        return False  # Unsafe block doesn't terminate control flow

    def _emit_asm(self, stmt: rast.AsmStmt):
        """Emit inline assembly using LLVM inline asm.

        Converts Ritz inline assembly syntax to LLVM IR inline asm.

        Supports both input and output operands. Output operands are detected
        by analyzing the assembly template for write patterns (e.g., mov to operand).

        Example Ritz (input only):
            asm x86_64:
                movw {port}, %dx
                outb %al, %dx

        Example Ritz (with output):
            asm x86_64:
                movw {port}, %dx
                inb %dx, %al
                movb %al, {result}

        For outputs, the value is returned from the asm and stored back.
        """
        import re

        template = stmt.template

        # Detect which operands are outputs by analyzing the template.
        # In AT&T syntax, the destination is the LAST operand of mov/store instructions.
        # Pattern: movX <src>, {operand} means {operand} is an output
        output_operands = set()
        for operand in stmt.operands:
            # Check for patterns where this operand is a destination
            # AT&T syntax: instruction source, destination
            patterns = [
                rf'mov[bwlq]?\s+[^,]+,\s*\{{{operand.name}\}}',  # movb %al, {result}
                rf'xchg[bwlq]?\s+[^,]+,\s*\{{{operand.name}\}}',  # xchg
                rf'lea[bwlq]?\s+[^,]+,\s*\{{{operand.name}\}}',  # lea
                rf'pop[bwlq]?\s+\{{{operand.name}\}}',  # pop {result}
                rf'in[bwl]?\s+[^,]*,?\s*\{{{operand.name}\}}',  # in %dx, {result}
            ]
            for pattern in patterns:
                if re.search(pattern, template, re.IGNORECASE):
                    output_operands.add(operand.name)
                    break

        # Separate outputs and inputs for LLVM constraint ordering
        # LLVM requires outputs first, then inputs, in the constraint string
        outputs = []
        inputs = []
        output_addrs = {}  # Map operand name -> LLVM address to store result

        for operand in stmt.operands:
            if operand.name in output_operands:
                outputs.append(operand)
                # For outputs, we need the address to store to, not the value
                # The operand.expr should be an Ident referencing a variable
                if isinstance(operand.expr, rast.Ident):
                    var_name = operand.expr.name
                    if var_name in self.locals:
                        output_addrs[operand.name], _ = self.locals[var_name]
                    elif var_name in self.globals:
                        output_addrs[operand.name], _ = self.globals[var_name]
                    else:
                        raise ValueError(f"Unknown variable for asm output: {var_name}")
                else:
                    raise ValueError(f"Asm output operand must be a variable, got: {type(operand.expr)}")
            else:
                inputs.append(operand)

        # Build constraint string and operand lists
        # Outputs come first in both the constraint string and operand lists
        constraints = []
        input_values = []
        output_types = []
        operand_map = {}  # Maps {name} -> $N

        # Add output constraints first (=r for each output)
        for i, operand in enumerate(outputs):
            operand_map[operand.name] = f"${i}"
            constraints.append("=r")
            # Get the type for the output
            addr = output_addrs[operand.name]
            if isinstance(addr.type, ir.PointerType):
                output_types.append(addr.type.pointee)
            else:
                output_types.append(addr.type)

        # Then add input constraints
        for i, operand in enumerate(inputs):
            operand_map[operand.name] = f"${len(outputs) + i}"
            # Emit the operand expression to get its value
            val = self._emit_expr(operand.expr)
            input_values.append(val)
            # Input constraint based on type
            ty = val.type
            if ty in (self.i8, self.i16, self.i32, self.i64):
                constraints.append("r")
            elif isinstance(ty, ir.PointerType):
                constraints.append("r")
            else:
                constraints.append("r")

        # Replace {name} with $N in template
        # First, escape literal $ for LLVM
        template_escaped = template.replace('$', '$$')

        # Now replace {name} with temporary markers
        operand_markers = {}
        def replace_with_marker(match):
            name = match.group(1)
            if name in operand_map:
                idx = operand_map[name]
                marker = f'\x00{idx[1:]}\x00'
                operand_markers[marker] = idx
                return marker
            else:
                raise ValueError(f"Unknown asm operand: {{{name}}}")

        llvm_template = re.sub(r'\{(\w+)\}', replace_with_marker, template_escaped)

        # Replace markers back to $N
        for marker, idx in operand_markers.items():
            llvm_template = llvm_template.replace(marker, idx)

        llvm_template = llvm_template.replace('\n', '\\0A')

        # Auto-detect register clobbers from the template
        x86_64_regs = {
            'rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rbp', 'rsp',
            'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15',
            'eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp', 'esp',
            'ax', 'bx', 'cx', 'dx', 'si', 'di', 'bp', 'sp',
            'al', 'ah', 'bl', 'bh', 'cl', 'ch', 'dl', 'dh',
            'sil', 'dil', 'bpl', 'spl',
        }

        detected_clobbers = set()
        template_lower = template.lower()
        for reg in x86_64_regs:
            if re.search(rf'\b{reg}\b', template_lower):
                reg_map = {
                    'eax': 'rax', 'ax': 'rax', 'al': 'rax', 'ah': 'rax',
                    'ebx': 'rbx', 'bx': 'rbx', 'bl': 'rbx', 'bh': 'rbx',
                    'ecx': 'rcx', 'cx': 'rcx', 'cl': 'rcx', 'ch': 'rcx',
                    'edx': 'rdx', 'dx': 'rdx', 'dl': 'rdx', 'dh': 'rdx',
                    'esi': 'rsi', 'si': 'rsi', 'sil': 'rsi',
                    'edi': 'rdi', 'di': 'rdi', 'dil': 'rdi',
                    'ebp': 'rbp', 'bp': 'rbp', 'bpl': 'rbp',
                    'esp': 'rsp', 'sp': 'rsp', 'spl': 'rsp',
                }
                canonical = reg_map.get(reg, reg)
                detected_clobbers.add(canonical)

        if stmt.clobbers:
            for clobber in stmt.clobbers:
                detected_clobbers.add(clobber)

        for clobber in sorted(detected_clobbers):
            constraints.append(f"~{{{clobber}}}")

        if stmt.volatile:
            constraints.append("~{memory}")

        constraint_str = ','.join(constraints) if constraints else ""

        # Determine return type based on outputs
        if len(outputs) == 0:
            ret_type = self.void
        elif len(outputs) == 1:
            ret_type = output_types[0]
        else:
            # Multiple outputs -> return a struct
            ret_type = ir.LiteralStructType(output_types)

        # Build function type
        if input_values:
            param_types = [v.type for v in input_values]
            asm_fn_type = ir.FunctionType(ret_type, param_types)
        else:
            asm_fn_type = ir.FunctionType(ret_type, [])

        # Create inline asm value
        asm_val = ir.InlineAsm(
            asm_fn_type,
            llvm_template,
            constraint_str,
            side_effect=stmt.volatile
        )

        # Call the inline asm
        if input_values:
            result = self.builder.call(asm_val, input_values)
        else:
            result = self.builder.call(asm_val, [])

        # Store output values back to variables
        if len(outputs) == 1:
            addr = output_addrs[outputs[0].name]
            self.builder.store(result, addr)
        elif len(outputs) > 1:
            for i, operand in enumerate(outputs):
                val = self.builder.extract_value(result, i)
                addr = output_addrs[operand.name]
                self.builder.store(val, addr)

        return None


    def _emit_short_circuit_and(self, expr: rast.BinOp):
        """Emit short-circuit AND: left && right.

        Evaluates left first. If left is false, returns false without
        evaluating right. Only evaluates right if left is true.
        """
        # Evaluate left operand
        left = self._emit_expr(expr.left)

        # Convert to i1 if needed
        if left.type != self.i1:
            left_bool = self.builder.icmp_signed('!=', left, ir.Constant(left.type, 0))
        else:
            left_bool = left

        # Create blocks
        eval_right_block = self.current_fn.append_basic_block("and.right")
        merge_block = self.current_fn.append_basic_block("and.merge")

        # Remember entry block for phi
        entry_block = self.builder.block

        # If left is false, short-circuit to merge (result is false)
        # If left is true, evaluate right
        self.builder.cbranch(left_bool, eval_right_block, merge_block)

        # Evaluate right operand
        self.builder.position_at_end(eval_right_block)
        right = self._emit_expr(expr.right)

        # Convert to i1 if needed
        if right.type != self.i1:
            right_bool = self.builder.icmp_signed('!=', right, ir.Constant(right.type, 0))
        else:
            right_bool = right

        right_exit_block = self.builder.block
        self.builder.branch(merge_block)

        # Merge block with phi node
        self.builder.position_at_end(merge_block)
        result = self.builder.phi(self.i1)
        result.add_incoming(ir.Constant(self.i1, 0), entry_block)  # false from short-circuit
        result.add_incoming(right_bool, right_exit_block)          # right result if evaluated

        return result


    def _emit_short_circuit_or(self, expr: rast.BinOp):
        """Emit short-circuit OR: left || right.

        Evaluates left first. If left is true, returns true without
        evaluating right. Only evaluates right if left is false.
        """
        # Evaluate left operand
        left = self._emit_expr(expr.left)

        # Convert to i1 if needed
        if left.type != self.i1:
            left_bool = self.builder.icmp_signed('!=', left, ir.Constant(left.type, 0))
        else:
            left_bool = left

        # Create blocks
        eval_right_block = self.current_fn.append_basic_block("or.right")
        merge_block = self.current_fn.append_basic_block("or.merge")

        # Remember entry block for phi
        entry_block = self.builder.block

        # If left is true, short-circuit to merge (result is true)
        # If left is false, evaluate right
        self.builder.cbranch(left_bool, merge_block, eval_right_block)

        # Evaluate right operand
        self.builder.position_at_end(eval_right_block)
        right = self._emit_expr(expr.right)

        # Convert to i1 if needed
        if right.type != self.i1:
            right_bool = self.builder.icmp_signed('!=', right, ir.Constant(right.type, 0))
        else:
            right_bool = right

        right_exit_block = self.builder.block
        self.builder.branch(merge_block)

        # Merge block with phi node
        self.builder.position_at_end(merge_block)
        result = self.builder.phi(self.i1)
        result.add_incoming(ir.Constant(self.i1, 1), entry_block)  # true from short-circuit
        result.add_incoming(right_bool, right_exit_block)          # right result if evaluated

        return result


    def _emit_if(self, if_expr: rast.If):
        """Emit an if expression/statement. Returns phi value if if-expr has value, else None."""
        cond = self._emit_expr(if_expr.cond)

        # Ensure condition is i1
        if cond.type != self.i1:
            cond = self.builder.icmp_signed('!=', cond, ir.Constant(cond.type, 0))

        # Create blocks
        then_block = self.current_fn.append_basic_block("if.then")
        else_block = self.current_fn.append_basic_block("if.else") if if_expr.else_block else None
        end_block = self.current_fn.append_basic_block("if.end")

        # Branch
        if else_block:
            self.builder.cbranch(cond, then_block, else_block)
        else:
            self.builder.cbranch(cond, then_block, end_block)

        # Then block
        self.builder.position_at_end(then_block)
        saved_returned = self.has_returned
        self.has_returned = False

        for s in if_expr.then_block.stmts:
            result = self._emit_stmt(s)
            if result is True:
                break

        # Handle trailing expression in then block - capture value for phi
        then_value = None
        if not self.builder.block.is_terminated and if_expr.then_block.expr:
            if isinstance(if_expr.then_block.expr, rast.If):
                then_value = self._emit_if(if_expr.then_block.expr)
            else:
                then_value = self._emit_expr(if_expr.then_block.expr)

        # DON'T branch yet - we may need to add type conversion first
        then_exit_block = self.builder.block  # Remember where we are after then block
        then_terminated = self.builder.block.is_terminated
        then_returned = self.has_returned

        # Else block
        else_value = None
        else_exit_block = None
        else_returned = False
        if if_expr.else_block:
            self.builder.position_at_end(else_block)
            self.has_returned = False

            for s in if_expr.else_block.stmts:
                result = self._emit_stmt(s)
                if result is True:
                    break

            # Handle trailing expression in else block - capture value for phi
            if not self.builder.block.is_terminated and if_expr.else_block.expr:
                if isinstance(if_expr.else_block.expr, rast.If):
                    else_value = self._emit_if(if_expr.else_block.expr)
                else:
                    else_value = self._emit_expr(if_expr.else_block.expr)

            # DON'T branch yet
            else_exit_block = self.builder.block  # Remember where we are after else block
            else_terminated = self.builder.block.is_terminated
            else_returned = self.has_returned

        # If both branches have values with different types, convert BEFORE branching
        target_type = None
        if then_value is not None and else_value is not None:
            if then_value.type != else_value.type:
                # Pick the larger type
                if self._type_size(else_value.type) > self._type_size(then_value.type):
                    target_type = else_value.type
                else:
                    target_type = then_value.type

                # Convert then value if needed (while still in else block, go back to then)
                if then_value.type != target_type and not then_terminated:
                    self.builder.position_at_end(then_exit_block)
                    then_value = self._convert_type(then_value, target_type)
                    then_exit_block = self.builder.block

                # Convert else value if needed
                if else_value.type != target_type and not else_terminated:
                    self.builder.position_at_end(else_exit_block)
                    else_value = self._convert_type(else_value, target_type)
                    else_exit_block = self.builder.block
            else:
                # Types are already the same
                target_type = then_value.type

        # NOW add the branches
        if not then_terminated:
            self.builder.position_at_end(then_exit_block)
            self.builder.branch(end_block)

        if else_exit_block and not else_terminated:
            self.builder.position_at_end(else_exit_block)
            self.builder.branch(end_block)

        # Position at end block
        self.builder.position_at_end(end_block)

        # Restore has_returned
        self.has_returned = saved_returned or (then_returned and else_returned)

        # Create phi node if both branches have values
        if then_value is not None and else_value is not None:
            phi = self.builder.phi(then_value.type)  # Types should match now after conversion
            phi.add_incoming(then_value, then_exit_block)
            phi.add_incoming(else_value, else_exit_block)
            return phi

        return None


    def _emit_while(self, stmt: rast.WhileStmt) -> None:
        """Emit a while loop."""
        cond_block = self.current_fn.append_basic_block("while.cond")
        body_block = self.current_fn.append_basic_block("while.body")
        end_block = self.current_fn.append_basic_block("while.end")

        # Push loop context for break/continue
        self.loop_stack.append((cond_block, end_block))

        # Jump to condition
        self.builder.branch(cond_block)

        # Condition
        self.builder.position_at_end(cond_block)
        cond = self._emit_expr(stmt.cond)
        if cond.type != self.i1:
            cond = self.builder.icmp_signed('!=', cond, ir.Constant(cond.type, 0))
        self.builder.cbranch(cond, body_block, end_block)

        # Body
        self.builder.position_at_end(body_block)
        saved_returned = self.has_returned
        self.has_returned = False

        for s in stmt.body.stmts:
            result = self._emit_stmt(s)
            if result is True:
                break

        # Handle trailing expression in while body (if any)
        if not self.builder.block.is_terminated and stmt.body.expr:
            if isinstance(stmt.body.expr, rast.If):
                self._emit_if(stmt.body.expr)
            else:
                self._emit_expr(stmt.body.expr)

        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)

        self.has_returned = saved_returned

        # Pop loop context
        self.loop_stack.pop()

        # End
        self.builder.position_at_end(end_block)
        return None


    def _emit_for(self, stmt: rast.ForStmt) -> None:
        """Emit a for loop.

        Desugars `for x in start..end` to:
            var x = start
            while x < end:   # (or <= for inclusive)
                body
                x = x + 1
        """
        # For now, only support Range expressions
        if not isinstance(stmt.iter, rast.Range):
            raise NotImplementedError(f"for loop only supports range expressions, got {type(stmt.iter)}")

        range_expr = stmt.iter
        if range_expr.start is None or range_expr.end is None:
            raise NotImplementedError("for loop requires both start and end in range")

        # Emit start and end values
        start_val = self._emit_expr(range_expr.start)
        end_val = self._emit_expr(range_expr.end)

        # Determine the type of the loop variable
        # If start is 0 (default i64) but end is a different int type, use end's type
        # This handles common case: for i in 0..count where count is i32
        loop_ty = start_val.type
        if start_val.type != end_val.type:
            # Prefer the end type if start is just a constant 0
            if isinstance(range_expr.start, rast.IntLit) and range_expr.start.value == 0:
                loop_ty = end_val.type
                start_val = ir.Constant(loop_ty, 0)
            else:
                # Otherwise, widen to the larger type
                if self._type_size(start_val.type) > self._type_size(end_val.type):
                    loop_ty = start_val.type
                    if self._is_signed_type(end_val.type):
                        end_val = self.builder.sext(end_val, loop_ty)
                    else:
                        end_val = self.builder.zext(end_val, loop_ty)
                else:
                    loop_ty = end_val.type
                    if self._is_signed_type(start_val.type):
                        start_val = self.builder.sext(start_val, loop_ty)
                    else:
                        start_val = self.builder.zext(start_val, loop_ty)

        # Create the loop variable (allocate in entry block to prevent stack leaks in nested loops)
        loop_var = self._alloca_in_entry_block(loop_ty, stmt.var)
        self.builder.store(start_val, loop_var)

        # Add to local vars scope
        self.locals[stmt.var] = (loop_var, loop_ty)

        # Create basic blocks
        cond_block = self.current_fn.append_basic_block("for.cond")
        body_block = self.current_fn.append_basic_block("for.body")
        incr_block = self.current_fn.append_basic_block("for.incr")
        end_block = self.current_fn.append_basic_block("for.end")

        # Push loop context for break/continue
        # continue goes to increment block, break goes to end block
        self.loop_stack.append((incr_block, end_block))

        # Jump to condition
        self.builder.branch(cond_block)

        # Condition block
        self.builder.position_at_end(cond_block)
        current_val = self.builder.load(loop_var)

        # Compare: x < end (or x <= end for inclusive)
        if range_expr.inclusive:
            cmp_op = '<=' if self._is_signed_type(loop_ty) else '<='
            if self._is_signed_type(loop_ty):
                cond = self.builder.icmp_signed('<=', current_val, end_val)
            else:
                cond = self.builder.icmp_unsigned('<=', current_val, end_val)
        else:
            if self._is_signed_type(loop_ty):
                cond = self.builder.icmp_signed('<', current_val, end_val)
            else:
                cond = self.builder.icmp_unsigned('<', current_val, end_val)

        self.builder.cbranch(cond, body_block, end_block)

        # Body block
        self.builder.position_at_end(body_block)
        saved_returned = self.has_returned
        self.has_returned = False

        for s in stmt.body.stmts:
            result = self._emit_stmt(s)
            if result is True:
                break

        # Handle trailing expression in for body (if any)
        if not self.builder.block.is_terminated and stmt.body.expr:
            if isinstance(stmt.body.expr, rast.If):
                self._emit_if(stmt.body.expr)
            else:
                self._emit_expr(stmt.body.expr)

        # Jump to increment if not terminated
        if not self.builder.block.is_terminated:
            self.builder.branch(incr_block)

        self.has_returned = saved_returned

        # Increment block
        self.builder.position_at_end(incr_block)
        current_val = self.builder.load(loop_var)
        incremented = self.builder.add(current_val, ir.Constant(loop_ty, 1))
        self.builder.store(incremented, loop_var)
        self.builder.branch(cond_block)

        # Pop loop context
        self.loop_stack.pop()

        # End block
        self.builder.position_at_end(end_block)
        return None


    def _emit_assert(self, stmt: rast.AssertStmt) -> None:
        """Emit an assert statement (only valid in test functions)."""
        # Enforce assert only in @test functions
        if not self.in_test_fn:
            fn_name = self.current_fn_def.name if self.current_fn_def else "unknown"
            raise ValueError(f"assert is only allowed in @test functions, not in '{fn_name}'")

        # Emit the condition
        cond = self._emit_expr(stmt.condition)

        # Ensure condition is i1
        if cond.type != self.i1:
            cond = self.builder.icmp_signed('!=', cond, ir.Constant(cond.type, 0))

        # Create blocks
        pass_block = self.current_fn.append_basic_block("assert.pass")
        fail_block = self.current_fn.append_basic_block("assert.fail")

        # Branch based on condition
        self.builder.cbranch(cond, pass_block, fail_block)

        # Fail block: exit(1) via syscall
        self.builder.position_at_end(fail_block)
        # syscall 60 = exit on x86_64
        exit_code = ir.Constant(self.i64, 1)
        asm_str = "syscall"
        constraints = "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"
        asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64])
        asm_ir = ir.InlineAsm(asm_func_ty, asm_str, constraints, side_effect=True)
        self.builder.call(asm_ir, [ir.Constant(self.i64, 60), exit_code])
        self.builder.unreachable()

        # Pass block: continue
        self.builder.position_at_end(pass_block)
        return None


