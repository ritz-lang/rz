"""
Literal and constructor emission mixin for the LLVM emitter.

Contains: _get_string_constant, _emit_string_from_literal, _emit_span_string_literal,
          _emit_strview_string_literal, _coerce_string_to_u8_ptr,
          _emit_array_lit, _emit_array_fill, _emit_array_fill_to_alloca,
          _emit_memset, _emit_fill_loop, _emit_array_convert_loop,
          _emit_enum_variant_constructor, _emit_enum_variant_with_type,
          _emit_enum_variant_constructor_for_type
"""

from typing import Optional, List, Tuple
from llvmlite import ir
import ritz_ast as rast


class LiteralEmitterMixin:
    """Mixin providing literal and constructor emission methods for LLVMEmitter."""

    def _get_string_constant(self, value: str) -> ir.GlobalVariable:
        """Create a global string constant."""
        name = f".str.{self.string_counter}"
        self.string_counter += 1

        # Create null-terminated byte array
        byte_data = bytearray(value.encode('utf-8')) + bytearray([0])
        arr_type = ir.ArrayType(self.i8, len(byte_data))
        const = ir.Constant(arr_type, byte_data)

        gvar = ir.GlobalVariable(self.module, arr_type, name=name)
        gvar.global_constant = True
        gvar.linkage = "private"
        gvar.initializer = const

        return gvar


    def _emit_string_from_literal(self, expr: rast.StringLit) -> ir.Value:
        """Emit a String from a string literal via string_from_bytes().

        Converts "hello" -> string_from_bytes(ptr, 5), using compile-time known length.
        This avoids the runtime strlen() that string_from() would do.
        """
        if "string_from_bytes" not in self.functions:
            raise ValueError("String literal to String conversion requires string_from_bytes() to be defined. "
                             "Import ritzlib.string to use String type.")

        fn, _ = self.functions["string_from_bytes"]

        # Get the C string pointer
        gvar = self._get_string_constant(expr.value)
        zero = ir.Constant(self.i64, 0)
        cstr_ptr = self.builder.gep(gvar, [zero, zero])

        # Use compile-time known length instead of runtime strlen
        length = ir.Constant(self.i64, len(expr.value))

        # Call string_from_bytes(cstr_ptr, length)
        return self.builder.call(fn, [cstr_ptr, length])


    def _emit_span_string_literal(self, expr: rast.SpanStringLit) -> ir.Value:
        """Emit a Span<u8> from a span string literal.

        Converts s"hello" -> Span<u8> { ptr: @.str.0, len: 5 }
        Zero allocation - static data with compile-time known length.
        """
        # Get the string constant pointer
        gvar = self._get_string_constant(expr.value)
        zero = ir.Constant(self.i64, 0)
        ptr = self.builder.gep(gvar, [zero, zero])

        # Compile-time length
        length = ir.Constant(self.i64, len(expr.value))

        # Get the Span<u8> struct type (monomorphized as Span$u8)
        # Span<u8> is: { ptr: *u8, len: i64 }
        span_type_name = "Span$u8"
        if span_type_name in self.struct_types:
            span_type = self.struct_types[span_type_name]
        else:
            # Create inline literal struct type if Span$u8 not defined
            # This allows span strings to work without importing ritzlib.span
            span_type = ir.LiteralStructType([self.i8.as_pointer(), self.i64])

        # Build the Span struct value
        span = self.builder.insert_value(ir.Constant(span_type, ir.Undefined), ptr, 0)
        span = self.builder.insert_value(span, length, 1)

        return span


    def _emit_strview_string_literal(self, expr: rast.StringLit) -> ir.Value:
        """Emit a StrView from a string literal (RERITZ mode).

        Converts "hello" -> StrView { ptr: @.str.0, len: 5 }
        Zero allocation - static data with compile-time known length.

        In RERITZ mode, "hello" returns a StrView (ptr + len) instead of *u8.
        This provides zero-copy string handling by default.
        """
        # Get the string constant pointer
        gvar = self._get_string_constant(expr.value)
        zero = ir.Constant(self.i64, 0)
        ptr = self.builder.gep(gvar, [zero, zero])

        # Compile-time length
        length = ir.Constant(self.i64, len(expr.value))

        # Get the StrView struct type
        # StrView is: { ptr: *u8, len: i64 }
        if "StrView" in self.struct_types:
            strview_type = self.struct_types["StrView"]
        else:
            # Create inline literal struct type if StrView not defined
            # This allows string literals to work without importing ritzlib.strview
            strview_type = ir.LiteralStructType([self.i8.as_pointer(), self.i64])

        # Build the StrView struct value
        sv = self.builder.insert_value(ir.Constant(strview_type, ir.Undefined), ptr, 0)
        sv = self.builder.insert_value(sv, length, 1)

        return sv


    def _coerce_string_to_u8_ptr(self, string_val: ir.Value, arg_expr: rast.Expr) -> ir.Value:
        """Coerce a String value to *u8 by calling string_as_ptr().

        Issue #89 Phase 2: Implicit String -> *u8 coercion in function calls.

        Args:
            string_val: The LLVM value of the String (struct type)
            arg_expr: The original AST expression (used to find lvalue address)

        Returns:
            The *u8 pointer from string_as_ptr()
        """
        if "string_as_ptr" not in self.functions:
            raise ValueError("String to *u8 coercion requires string_as_ptr() to be defined. "
                             "Import ritzlib.string to use String type.")

        fn, _ = self.functions["string_as_ptr"]

        # string_as_ptr expects &mut String (pointer to String)
        # If arg_expr is an lvalue (variable), we can get its address
        # Otherwise, we need to store the temporary String on the stack

        string_ptr = None

        if isinstance(arg_expr, rast.Ident):
            name = arg_expr.name
            if name in self.locals:
                # var binding - the alloca IS the pointer
                string_ptr, _ = self.locals[name]
            elif name in self.globals:
                # global var - the global IS the pointer
                string_ptr, _ = self.globals[name]

        if string_ptr is None:
            # Temporary - allocate stack space and store the String there
            # Get String type from struct registry
            if "String" not in self.struct_types:
                raise ValueError("String struct not defined. Import ritzlib.string.")
            string_type = self.struct_types["String"]
            string_ptr = self.builder.alloca(string_type, name="string_temp")
            self.builder.store(string_val, string_ptr)

        # Call string_as_ptr(&mut string)
        return self.builder.call(fn, [string_ptr])


    def _emit_enum_variant_constructor(self, variant_name: str, args: List[rast.Expr]) -> ir.Value:
        """Emit code to construct an enum variant value.

        For Some(42):
            1. Get the enum type (Option_i32)
            2. Get the tag for Some (0)
            3. Allocate stack space for the enum
            4. Store the tag
            5. Store the payload data
            6. Return the enum value

        For None:
            1. Get the enum type
            2. Get the tag for None (1)
            3. Create enum value with just the tag
        """
        enum_name = self.variant_to_enum[variant_name]
        enum_type, variants = self.enum_types[enum_name]
        tag = self._get_enum_variant_tag(enum_name, variant_name)
        variant = self._get_enum_variant(enum_name, variant_name)

        # Allocate stack space for the enum
        enum_alloca = self.builder.alloca(enum_type, name=f"{variant_name}.alloca")

        # Store the tag (index 0)
        tag_ptr = self.builder.gep(enum_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
        self.builder.store(ir.Constant(self.i8, tag), tag_ptr)

        # Store payload data if any
        if variant.fields and args:
            # Get pointer to data buffer (index depends on alignment padding)
            data_index = self._get_enum_data_index(enum_name)
            data_ptr = self.builder.gep(enum_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, data_index)])

            # For each field in the variant, store the corresponding arg
            offset = 0
            for i, (field_type, arg) in enumerate(zip(variant.fields, args)):
                arg_val = self._emit_expr(arg)
                llvm_field_type = self._ritz_type_to_llvm(field_type)

                # Convert arg to field type (e.g., i64 literal -> i32)
                arg_val = self._convert_type(arg_val, llvm_field_type)

                # Cast data buffer to pointer to field type
                field_ptr = self.builder.bitcast(
                    self.builder.gep(data_ptr, [ir.Constant(self.i32, offset)]),
                    ir.PointerType(llvm_field_type)
                )
                self.builder.store(arg_val, field_ptr)
                offset += self._type_size_bytes(llvm_field_type)

        # Load and return the enum value
        return self.builder.load(enum_alloca)


    def _is_enum_variant_call(self, expr: rast.Expr) -> bool:
        """Check if expression is an enum variant constructor call."""
        if isinstance(expr, rast.Call):
            if isinstance(expr.func, rast.Ident):
                return expr.func.name in self.variant_to_enum
        elif isinstance(expr, rast.Ident):
            # Unit variant without parens
            return expr.name in self.variant_to_enum
        return False


    def _emit_enum_variant_with_type(self, expr: rast.Expr, enum_type_name: str) -> ir.Value:
        """Emit an enum variant constructor with explicit type context.

        This handles cases like `var opt: Option<i64> = Some(42)` where
        we need to construct the variant using the declared type, not
        the first registered enum with that variant name.
        """
        if isinstance(expr, rast.Call) and isinstance(expr.func, rast.Ident):
            variant_name = expr.func.name
            return self._emit_enum_variant_constructor_for_type(variant_name, expr.args, enum_type_name)
        elif isinstance(expr, rast.Ident):
            # Unit variant without parens
            return self._emit_enum_variant_constructor_for_type(expr.name, [], enum_type_name)
        else:
            # Fallback to regular expression emission
            return self._emit_expr(expr)


    def _emit_enum_variant_constructor_for_type(self, variant_name: str, args: List[rast.Expr], enum_name: str) -> ir.Value:
        """Emit code to construct an enum variant for a specific enum type.

        This is like _emit_enum_variant_constructor but uses the specified
        enum type rather than looking up variant_to_enum.
        """
        if enum_name not in self.enum_types:
            raise ValueError(f"Unknown enum type: {enum_name}")

        enum_type, variants = self.enum_types[enum_name]
        tag = self._get_enum_variant_tag(enum_name, variant_name)
        variant = self._get_enum_variant(enum_name, variant_name)

        # Allocate stack space for the enum
        enum_alloca = self.builder.alloca(enum_type, name=f"{variant_name}.alloca")

        # Store the tag (index 0)
        tag_ptr = self.builder.gep(enum_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)])
        self.builder.store(ir.Constant(self.i8, tag), tag_ptr)

        # Store payload data if any
        if variant.fields and args:
            # Get pointer to data buffer (index depends on alignment padding)
            data_index = self._get_enum_data_index(enum_name)
            data_ptr = self.builder.gep(enum_alloca, [ir.Constant(self.i32, 0), ir.Constant(self.i32, data_index)])

            # For each field in the variant, store the corresponding arg
            offset = 0
            for i, (field_type, arg) in enumerate(zip(variant.fields, args)):
                arg_val = self._emit_expr(arg)
                llvm_field_type = self._ritz_type_to_llvm(field_type)

                # Convert arg to field type (e.g., i64 literal -> i32)
                arg_val = self._convert_type(arg_val, llvm_field_type)

                # Cast data buffer to pointer to field type
                field_ptr = self.builder.bitcast(
                    self.builder.gep(data_ptr, [ir.Constant(self.i32, offset)]),
                    ir.PointerType(llvm_field_type)
                )
                self.builder.store(arg_val, field_ptr)
                offset += self._type_size_bytes(llvm_field_type)

        # Load and return the enum value
        return self.builder.load(enum_alloca)


    def _emit_array_lit(self, expr: rast.ArrayLit) -> ir.Value:
        """Emit an array literal: [a, b, c]."""
        if not expr.elements:
            raise ValueError("Empty array literals not supported")

        # Emit all elements and infer type from first element
        values = [self._emit_expr(e) for e in expr.elements]
        elem_type = values[0].type

        # Convert all values to same type
        converted = []
        for val in values:
            converted.append(self._convert_type(val, elem_type))

        # Create array type
        arr_type = ir.ArrayType(elem_type, len(converted))

        # Build array aggregate
        result = ir.Constant(arr_type, ir.Undefined)
        for i, val in enumerate(converted):
            result = self.builder.insert_value(result, val, i)

        return result


    def _emit_array_fill(self, expr: rast.ArrayFill) -> ir.Value:
        """Emit an array fill expression: [value; count].

        Creates an array with `count` copies of `value`.

        Optimizations:
        - For zero fills: Use LLVM zeroinitializer (O(1) IR)
        - For small arrays (N <= 64): Use insertvalue chain
        - For large arrays: Use memset for byte fills, or store loop for others
        """
        if expr.count <= 0:
            raise ValueError("Array fill count must be positive")

        # Emit the value once
        val = self._emit_expr(expr.value)
        elem_type = val.type

        # Create array type
        arr_type = ir.ArrayType(elem_type, expr.count)

        # Optimization: Check if this is a zero fill
        is_zero_fill = self._is_zero_constant(val)

        # For small arrays, we can use zeroinitializer or insertvalue chain
        if expr.count <= 64:
            if is_zero_fill:
                # Use zeroinitializer for small zero fills
                return ir.Constant(arr_type, None)
            # Use insertvalue chain for small arrays (generates N instructions but N is small)
            result = ir.Constant(arr_type, ir.Undefined)
            for i in range(expr.count):
                result = self.builder.insert_value(result, val, i)
            return result

        # For large arrays, allocate on stack and use memset/loop.
        # We can't use zeroinitializer for large arrays because:
        # 1. `store [65536 x i32] zeroinitializer, ptr` causes LLVM SelectionDAG to crash
        # 2. Even if it didn't crash, it would generate a huge store operation
        # Instead, we allocate and use memset which generates efficient code.
        arr_alloca = self.builder.alloca(arr_type)

        if is_zero_fill:
            # Use memset to zero the array (efficient O(1) IR)
            ptr = self.builder.bitcast(arr_alloca, self.i8.as_pointer())
            elem_size = self._sizeof_type(elem_type)
            total_bytes = elem_size * expr.count
            byte_val = ir.Constant(self.i8, 0)
            count = ir.Constant(self.i64, total_bytes)
            self._emit_memset(ptr, byte_val, count)
        else:
            # Get element size
            elem_size = self._sizeof_type(elem_type)

            # For single-byte fills, use memset
            if elem_size == 1 and isinstance(val, ir.Constant):
                # memset(ptr, val, count)
                ptr = self.builder.bitcast(arr_alloca, self.i8.as_pointer())
                byte_val = val
                if byte_val.type != self.i8:
                    byte_val = self.builder.trunc(val, self.i8)
                count = ir.Constant(self.i64, expr.count)
                self._emit_memset(ptr, byte_val, count)
            else:
                # For multi-byte fills or non-constant values, use a store loop
                # Generate: for i in 0..count: arr[i] = val
                self._emit_fill_loop(arr_alloca, arr_type, val, expr.count)

        # Load and return the filled array
        return self.builder.load(arr_alloca)


    def _emit_array_fill_to_alloca(self, expr: rast.ArrayFill, alloca: ir.AllocaInstr,
                                    target_type: ir.Type) -> None:
        """Emit array fill directly to an existing alloca.

        This is an optimization for large array fills assigned to variables.
        Instead of:
            1. Create temp alloca
            2. Fill temp
            3. Load temp (huge value!)
            4. Store to target (huge value!)
        We do:
            1. Fill target alloca directly

        This avoids the massive load/store that crashes LLVM SelectionDAG.
        """
        # Emit the fill value
        val = self._emit_expr(expr.value)
        is_zero_fill = self._is_zero_constant(val)

        # Get target element type
        if isinstance(target_type, ir.ArrayType):
            target_elem_type = target_type.element
        else:
            # Should be array type, but fall back to value type if not
            target_elem_type = val.type

        # Convert value to target element type if needed
        if val.type != target_elem_type:
            val = self._convert_type(val, target_elem_type)

        if is_zero_fill:
            # Use memset for zero fills (efficient O(1) IR)
            ptr = self.builder.bitcast(alloca, self.i8.as_pointer())
            elem_size = self._sizeof_type(target_elem_type)
            total_bytes = elem_size * expr.count
            byte_val = ir.Constant(self.i8, 0)
            count = ir.Constant(self.i64, total_bytes)
            self._emit_memset(ptr, byte_val, count)
        else:
            elem_size = self._sizeof_type(target_elem_type)
            # For single-byte fills, use memset
            if elem_size == 1 and isinstance(val, ir.Constant):
                ptr = self.builder.bitcast(alloca, self.i8.as_pointer())
                byte_val = val
                if byte_val.type != self.i8:
                    byte_val = self.builder.trunc(val, self.i8)
                count = ir.Constant(self.i64, expr.count)
                self._emit_memset(ptr, byte_val, count)
            else:
                # Use fill loop for multi-byte non-zero fills
                arr_type = ir.ArrayType(target_elem_type, expr.count)
                self._emit_fill_loop(alloca, arr_type, val, expr.count)


    def _is_zero_constant(self, val: ir.Value) -> bool:
        """Check if a value is a compile-time zero constant."""
        if not isinstance(val, ir.Constant):
            return False

        # Check for integer zero
        if isinstance(val.type, ir.IntType):
            return val.constant == 0

        # Check for float zero
        if isinstance(val.type, (ir.FloatType, ir.DoubleType)):
            return val.constant == 0.0

        # Check for null pointer
        if isinstance(val.type, ir.PointerType):
            return val.constant is None

        return False


    def _sizeof_type(self, ty: ir.Type) -> int:
        """Get the size in bytes of an LLVM type."""
        if isinstance(ty, ir.IntType):
            return ty.width // 8
        elif isinstance(ty, ir.FloatType):
            return 4
        elif isinstance(ty, ir.DoubleType):
            return 8
        elif isinstance(ty, ir.PointerType):
            return 8  # 64-bit pointers
        elif isinstance(ty, ir.ArrayType):
            return self._sizeof_type(ty.element) * ty.count
        elif isinstance(ty, ir.LiteralStructType):
            return sum(self._sizeof_type(e) for e in ty.elements)
        else:
            # Default to pointer size for unknown types
            return 8


    def _emit_memset(self, ptr: ir.Value, byte_val: ir.Value, count: ir.Value) -> None:
        """Emit a call to llvm.memset intrinsic."""
        # Declare memset if not already done
        if not hasattr(self, '_memset_fn'):
            # llvm.memset.p0i8.i64(i8* dest, i8 val, i64 len, i1 isvolatile)
            memset_ty = ir.FunctionType(self.void, [
                self.i8.as_pointer(),  # dest
                self.i8,               # val
                self.i64,              # len
                self.i1                # isvolatile
            ])
            self._memset_fn = ir.Function(self.module, memset_ty, name="llvm.memset.p0i8.i64")

        is_volatile = ir.Constant(self.i1, 0)
        self.builder.call(self._memset_fn, [ptr, byte_val, count, is_volatile])


    def _emit_fill_loop(self, arr_alloca: ir.Value, arr_type: ir.ArrayType,
                        val: ir.Value, count: int) -> None:
        """Emit a loop to fill an array with a value.

        Generates:
            for (i64 i = 0; i < count; i++) {
                arr[i] = val;
            }
        """
        # Create basic blocks
        loop_header = self.builder.append_basic_block("fill_header")
        loop_body = self.builder.append_basic_block("fill_body")
        loop_end = self.builder.append_basic_block("fill_end")

        # Initialize counter
        counter_alloca = self.builder.alloca(self.i64)
        self.builder.store(ir.Constant(self.i64, 0), counter_alloca)
        self.builder.branch(loop_header)

        # Loop header: check if i < count
        self.builder.position_at_end(loop_header)
        i = self.builder.load(counter_alloca)
        cond = self.builder.icmp_signed('<', i, ir.Constant(self.i64, count))
        self.builder.cbranch(cond, loop_body, loop_end)

        # Loop body: arr[i] = val; i++
        self.builder.position_at_end(loop_body)
        i = self.builder.load(counter_alloca)
        elem_ptr = self.builder.gep(arr_alloca, [ir.Constant(self.i32, 0), i])
        self.builder.store(val, elem_ptr)
        next_i = self.builder.add(i, ir.Constant(self.i64, 1))
        self.builder.store(next_i, counter_alloca)
        self.builder.branch(loop_header)

        # Continue after loop
        self.builder.position_at_end(loop_end)


    def _emit_array_convert_loop(self, src_alloca: ir.Value, dst_alloca: ir.Value,
                                  src_type: ir.ArrayType, dst_type: ir.ArrayType) -> None:
        """Emit a loop to convert array elements from src to dst type.

        Generates:
            for (i64 i = 0; i < count; i++) {
                dst[i] = convert(src[i], target_elem_type);
            }
        """
        count = src_type.count

        # Create basic blocks
        loop_header = self.builder.append_basic_block("convert_header")
        loop_body = self.builder.append_basic_block("convert_body")
        loop_end = self.builder.append_basic_block("convert_end")

        # Initialize counter
        counter_alloca = self.builder.alloca(self.i64)
        self.builder.store(ir.Constant(self.i64, 0), counter_alloca)
        self.builder.branch(loop_header)

        # Loop header: check if i < count
        self.builder.position_at_end(loop_header)
        i = self.builder.load(counter_alloca)
        cond = self.builder.icmp_signed('<', i, ir.Constant(self.i64, count))
        self.builder.cbranch(cond, loop_body, loop_end)

        # Loop body: dst[i] = convert(src[i]); i++
        self.builder.position_at_end(loop_body)
        i = self.builder.load(counter_alloca)

        # Load source element
        src_elem_ptr = self.builder.gep(src_alloca, [ir.Constant(self.i32, 0), i])
        src_elem = self.builder.load(src_elem_ptr)

        # Convert to target type
        converted = self._convert_type(src_elem, dst_type.element)

        # Store to destination
        dst_elem_ptr = self.builder.gep(dst_alloca, [ir.Constant(self.i32, 0), i])
        self.builder.store(converted, dst_elem_ptr)

        # Increment counter
        next_i = self.builder.add(i, ir.Constant(self.i64, 1))
        self.builder.store(next_i, counter_alloca)
        self.builder.branch(loop_header)

        # Continue after loop
        self.builder.position_at_end(loop_end)


