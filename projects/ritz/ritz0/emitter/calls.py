"""
Call emission mixin for the LLVM emitter.

Contains: _emit_call, _emit_method_call, _emit_dyn_method_call,
          _emit_syscall, _emit_generic_syscall, _emit_write_syscall,
          _try_emit_simd_builtin, _try_emit_bitops_intrinsic
"""

from typing import Optional, List
from llvmlite import ir
import ritz_ast as rast


class CallEmitterMixin:
    """Mixin providing call emission methods for LLVMEmitter."""

    def _emit_call(self, call: rast.Call) -> ir.Value:
        """Emit a function call.

        Supports:
        - Direct calls: foo(x, y)
        - Indirect calls through function pointer: fn_ptr(x, y)
        """
        # Handle indirect calls through function pointer variable or parameter
        if isinstance(call.func, rast.Ident):
            fname = call.func.name

            # Check if this is a function pointer (local, parameter, or let binding)
            # The Ritz type is stored in ritz_types, which tells us if it's a FnType
            if fname in self.ritz_types:
                ritz_type = self.ritz_types[fname]
                if isinstance(ritz_type, rast.FnType):
                    # This is a function pointer - indirect call
                    # Get the function pointer value
                    if fname in self.locals:
                        var_ptr, _ = self.locals[fname]
                        fn_ptr = self.builder.load(var_ptr)
                    elif fname in self.params:
                        fn_ptr, _ = self.params[fname]
                    else:
                        raise ValueError(f"Function pointer '{fname}' not found in locals or params")

                    # Emit and convert arguments
                    args = [self._emit_expr(arg) for arg in call.args]
                    converted_args = []
                    for arg_val, param_type in zip(args, ritz_type.params):
                        expected_llvm = self._ritz_type_to_llvm(param_type)
                        converted_args.append(self._convert_type(arg_val, expected_llvm))
                    return self.builder.call(fn_ptr, converted_args)
        else:
            # Non-identifier function expression (e.g., field access returning fn ptr)
            fn_ptr = self._emit_expr(call.func)
            args = [self._emit_expr(arg) for arg in call.args]
            return self.builder.call(fn_ptr, args)

        fname = call.func.name

        # Handle enum variant constructors: Some(x), None, Ok(v), Err(e)
        if fname in self.variant_to_enum:
            return self._emit_enum_variant_constructor(fname, call.args)

        # Handle __builtin_alloca
        if fname == '__builtin_alloca':
            size = self._emit_expr(call.args[0])
            if isinstance(size, ir.Constant):
                return self.builder.alloca(self.i8, size.constant)
            else:
                return self.builder.alloca(self.i8, size)

        # Handle SIMD builtin functions
        simd_result = self._try_emit_simd_builtin(fname, call.args)
        if simd_result is not None:
            return simd_result

        # Handle sizeof builtin - sizeof(Type) -> compile-time size in bytes
        # Usage: sizeof(MyStruct), sizeof(i64), sizeof(*u8)
        if fname == 'sizeof':
            if len(call.args) != 1:
                raise ValueError("sizeof() requires exactly 1 type argument")

            # The argument should be a type expression, parsed as an identifier
            # For sizeof(i32), call.args[0] is Ident("i32")
            # For sizeof(MyStruct), call.args[0] is Ident("MyStruct")
            arg = call.args[0]

            # Try to interpret the argument as a type
            if isinstance(arg, rast.Ident):
                type_name = arg.name
                # Check primitives
                primitives = {
                    'i8': 1, 'u8': 1,
                    'i16': 2, 'u16': 2,
                    'i32': 4, 'u32': 4,
                    'i64': 8, 'u64': 8,
                    'bool': 1,
                }
                if type_name in primitives:
                    return ir.Constant(self.i64, primitives[type_name])

                # Check struct types via registry
                layout = self.struct_registry.get_layout(type_name)
                if layout:
                    return ir.Constant(self.i64, layout.size)

                # Fallback: unknown type, return 8 (pointer size)
                return ir.Constant(self.i64, 8)

            # For more complex type expressions, use the type resolver
            elif hasattr(arg, 'span'):
                # Try to create a NamedType from the identifier
                ritz_ty = rast.NamedType(span=arg.span, name=str(arg))
                size, _ = self._ritz_type_size_and_align(ritz_ty)
                return ir.Constant(self.i64, size)

            raise ValueError(f"sizeof() argument must be a type name, got: {type(arg)}")

        # Handle print builtin - print(string_literal) -> write(1, ptr, len)
        if fname == 'print':
            if len(call.args) == 1:
                arg = call.args[0]
                if isinstance(arg, (rast.StringLit, rast.CStringLit)):
                    s = arg.value
                    # Get or create the string constant
                    str_const = self._get_string_constant(s)
                    # GEP to get i8* pointer to string data
                    ptr = self.builder.gep(str_const, [ir.Constant(self.i64, 0), ir.Constant(self.i64, 0)])
                    length = len(s)
                    # Call write(1, ptr, length) via syscall
                    return self._emit_write_syscall(ir.Constant(self.i64, 1), ptr, ir.Constant(self.i64, length))
                elif isinstance(arg, rast.InterpString):
                    # Handle interpolated string - desugar to print calls
                    return self._emit_interp_string_print(arg)
            raise ValueError("print() requires a single string literal argument")

        # Handle named syscalls
        if fname in ('write', 'read', 'open', 'close', 'nanosleep'):
            return self._emit_syscall(fname, call.args)

        # Handle generic syscallN(num, args...) builtins
        # ONLY match exact builtin names: syscall0-syscall6, __syscall0-__syscall6
        # Don't match other functions that happen to start with "syscall" (e.g., syscall_init)
        syscall_builtins = {'syscall0', 'syscall1', 'syscall2', 'syscall3', 'syscall4', 'syscall5', 'syscall6',
                           '__syscall0', '__syscall1', '__syscall2', '__syscall3', '__syscall4', '__syscall5', '__syscall6'}
        if fname in syscall_builtins:
            return self._emit_generic_syscall(fname, call.args)

        # Look up user-defined function
        if fname in self.functions:
            fn, fn_def = self.functions[fname]

            # Check argument count BEFORE processing
            if len(call.args) != len(fn.function_type.args):
                raise ValueError(f"Function '{fname}' called with {len(call.args)} args but defined with {len(fn.function_type.args)} params")

            # Emit arguments with type conversion and String -> *u8 coercion
            # Also handle RERITZ Borrow semantics - borrowed params need addresses
            args = []
            for i, arg in enumerate(call.args):
                param_def = fn_def.params[i]
                expected_type = fn.function_type.args[i]

                # Check if this parameter is a reference type (@T or @&T in RERITZ, or :& borrow)
                # References pass by pointer - we need to pass the address of the argument
                is_mutable_borrow = hasattr(param_def, 'borrow') and param_def.borrow == rast.Borrow.MUTABLE
                is_ref_type = isinstance(param_def.type, rast.RefType)

                # Check if the argument is already a RefType, PtrType, or explicit address-of
                arg_ritz_type = self._infer_ritz_type(arg)
                arg_is_ref = isinstance(arg_ritz_type, rast.RefType) if arg_ritz_type else False
                # PtrType is compatible with RefType at LLVM level (both are pointers)
                arg_is_ptr = isinstance(arg_ritz_type, rast.PtrType) if arg_ritz_type else False
                # Also check if argument is explicit &x or @x (address-of expression)
                arg_is_addr_of = isinstance(arg, rast.UnaryOp) and arg.op in ('&', '@', '@&', '&mut')

                if is_mutable_borrow or is_ref_type:
                    if arg_is_ref or arg_is_ptr or arg_is_addr_of:
                        # Argument is already a pointer type - just emit it
                        val = self._emit_expr(arg)
                    else:
                        # Reference parameter: emit address of the argument
                        val = self._emit_lvalue_addr(arg)
                else:
                    # Moved/value parameter: emit value normally
                    val = self._emit_expr(arg)

                    # Check for String -> *u8 implicit coercion (Issue #89)
                    arg_ritz_type = self._infer_ritz_type(arg)
                    if (arg_ritz_type and isinstance(arg_ritz_type, rast.NamedType)
                        and arg_ritz_type.name == 'String'
                        and isinstance(expected_type, ir.PointerType)
                        and expected_type.pointee == self.i8):
                        val = self._coerce_string_to_u8_ptr(val, arg)
                    # Check for StrView -> *u8 implicit coercion (RERITZ string literals)
                    elif (arg_ritz_type and isinstance(arg_ritz_type, rast.NamedType)
                          and arg_ritz_type.name == 'StrView'
                          and isinstance(expected_type, ir.PointerType)
                          and expected_type.pointee == self.i8):
                        # Extract ptr field from StrView struct
                        val = self.builder.extract_value(val, 0, name='strview.ptr')
                    else:
                        val = self._convert_type(val, expected_type)
                args.append(val)

            return self.builder.call(fn, args)

        # Look up extern function
        if fname in self.extern_fns:
            fn_type, extern_def = self.extern_fns[fname]

            # Check argument count
            expected_arg_count = len(fn_type.args)
            if extern_def.varargs:
                # For varargs, at least the fixed params must be provided
                if len(call.args) < expected_arg_count:
                    raise ValueError(f"Extern function '{fname}' requires at least {expected_arg_count} args, got {len(call.args)}")
            else:
                if len(call.args) != expected_arg_count:
                    raise ValueError(f"Extern function '{fname}' called with {len(call.args)} args but declared with {expected_arg_count} params")

            # Declare the extern function in LLVM if not already done
            if fname not in self.module.globals:
                fn = ir.Function(self.module, fn_type, name=fname)
            else:
                fn = self.module.globals[fname]

            # Emit arguments with type conversion and String -> *u8 coercion
            args = []
            for i, arg in enumerate(call.args):
                val = self._emit_expr(arg)
                if i < len(fn_type.args):
                    expected_type = fn_type.args[i]
                    # Check for String -> *u8 implicit coercion (Issue #89)
                    arg_ritz_type = self._infer_ritz_type(arg)
                    if (arg_ritz_type and isinstance(arg_ritz_type, rast.NamedType)
                        and arg_ritz_type.name == 'String'
                        and isinstance(expected_type, ir.PointerType)
                        and expected_type.pointee == self.i8):
                        val = self._coerce_string_to_u8_ptr(val, arg)
                    # Check for StrView -> *u8 implicit coercion (RERITZ string literals)
                    elif (arg_ritz_type and isinstance(arg_ritz_type, rast.NamedType)
                          and arg_ritz_type.name == 'StrView'
                          and isinstance(expected_type, ir.PointerType)
                          and expected_type.pointee == self.i8):
                        # Extract ptr field from StrView struct
                        val = self.builder.extract_value(val, 0, name='strview.ptr')
                    else:
                        val = self._convert_type(val, expected_type)
                args.append(val)

            return self.builder.call(fn, args)

        raise ValueError(f"Unknown function: {fname}")


    def _try_emit_simd_builtin(self, fname: str, args: list) -> Optional[ir.Value]:
        """Try to emit a SIMD builtin function.

        Returns the IR value if this is a SIMD builtin, or None otherwise.

        SIMD Builtins:
        - simd_load(ptr: *T) -> vec<N, T>: Aligned vector load (16/32-byte)
        - simd_loadu(ptr: *T) -> vec<N, T>: Unaligned vector load
        - simd_store(ptr: *T, val: vec<N, T>): Aligned vector store
        - simd_storeu(ptr: *T, val: vec<N, T>): Unaligned vector store
        - simd_extract(vec: vec<N, T>, idx: i32) -> T: Extract element
        - simd_insert(vec: vec<N, T>, idx: i32, val: T) -> vec<N, T>: Insert element
        - simd_shuffle(a: vec<N, T>, b: vec<N, T>, mask: ...) -> vec<N, T>: Shuffle elements
        - simd_sad(a: vec<16, i8>, b: vec<16, i8>) -> vec<2, i64>: Sum of absolute differences
        - simd_add(a: vec<N, T>, b: vec<N, T>) -> vec<N, T>: Vector integer addition
        - simd_xor(a: vec<N, T>, b: vec<N, T>) -> vec<N, T>: Vector XOR
        - simd_rotl(v: vec<N, T>, n: i32) -> vec<N, T>: Vector rotate left (constant n)
        """
        # Mark current function as using SIMD if this is a SIMD builtin
        # SIMD functions need alignstack(16) to ensure proper stack alignment
        # for SIMD operations (e.g., movaps requires 16-byte aligned memory)
        if fname.startswith('simd_') and self.current_fn_def:
            self.simd_functions.add(self.current_fn_def.name)

        # Common SIMD vector types for SSE2 (128-bit)
        v16i8 = ir.VectorType(self.i8, 16)
        v8i16 = ir.VectorType(self.i16, 8)
        v4i32 = ir.VectorType(self.i32, 4)
        v2i64 = ir.VectorType(self.i64, 2)
        # AVX2 vector types (256-bit)
        v32i8 = ir.VectorType(self.i8, 32)
        v16i16 = ir.VectorType(self.i16, 16)
        v8i32 = ir.VectorType(self.i32, 8)
        v4i64 = ir.VectorType(self.i64, 4)

        if fname == 'simd_load':
            # simd_load(ptr: *T) -> vec<N, T>
            # Aligned load (16-byte for SSE2, 32-byte for AVX2)
            if len(args) != 1:
                raise ValueError("simd_load() requires exactly 1 argument (pointer)")
            ptr = self._emit_expr(args[0])
            # Determine vector type from pointer element type
            if isinstance(ptr.type, ir.PointerType):
                elem_type = ptr.type.pointee
                # Check if we have an expected type from declaration
                expected = self.simd_expected_type
                is_avx2 = False
                if expected and isinstance(expected, rast.NamedType):
                    type_map = {
                        # SSE2 128-bit
                        'v16i8': v16i8, 'v8i16': v8i16, 'v4i32': v4i32, 'v2i64': v2i64,
                        # AVX2 256-bit
                        'v32i8': v32i8, 'v16i16': v16i16, 'v8i32': v8i32, 'v4i64': v4i64,
                    }
                    vec_type = type_map.get(expected.name)
                    if vec_type is None:
                        raise ValueError(f"simd_load: unsupported expected type {expected.name}")
                    is_avx2 = expected.name in ('v32i8', 'v16i16', 'v8i32', 'v4i64')
                else:
                    # Default to 128-bit vectors (SSE2)
                    if elem_type == self.i8:
                        vec_type = v16i8
                    elif elem_type == self.i16:
                        vec_type = v8i16
                    elif elem_type == self.i32:
                        vec_type = v4i32
                    elif elem_type == self.i64:
                        vec_type = v2i64
                    else:
                        raise ValueError(f"simd_load: unsupported element type {elem_type}")
                # Cast pointer to vector pointer type
                vec_ptr = self.builder.bitcast(ptr, ir.PointerType(vec_type))
                # Aligned load (16-byte for SSE2, 32-byte for AVX2)
                load_instr = self.builder.load(vec_ptr)
                load_instr.align = 32 if is_avx2 else 16
                return load_instr
            raise ValueError("simd_load() requires a pointer argument")

        elif fname == 'simd_loadu':
            # simd_loadu(ptr: *T) -> vec<N, T>
            # Unaligned load (align=1)
            # Determines SSE2 (128-bit) vs AVX2 (256-bit) from expected type context
            if len(args) != 1:
                raise ValueError("simd_loadu() requires exactly 1 argument (pointer)")
            ptr = self._emit_expr(args[0])
            if isinstance(ptr.type, ir.PointerType):
                elem_type = ptr.type.pointee
                # Check if we have an expected type from declaration (e.g., let v: v8i32 = ...)
                expected = self.simd_expected_type
                if expected and isinstance(expected, rast.NamedType):
                    # Use the declared type directly
                    type_map = {
                        # SSE2 128-bit
                        'v16i8': v16i8, 'v8i16': v8i16, 'v4i32': v4i32, 'v2i64': v2i64,
                        # AVX2 256-bit
                        'v32i8': v32i8, 'v16i16': v16i16, 'v8i32': v8i32, 'v4i64': v4i64,
                    }
                    vec_type = type_map.get(expected.name)
                    if vec_type is None:
                        raise ValueError(f"simd_loadu: unsupported expected type {expected.name}")
                else:
                    # Default to SSE2 128-bit vectors based on element type
                    if elem_type == self.i8:
                        vec_type = v16i8
                    elif elem_type == self.i16:
                        vec_type = v8i16
                    elif elem_type == self.i32:
                        vec_type = v4i32
                    elif elem_type == self.i64:
                        vec_type = v2i64
                    else:
                        raise ValueError(f"simd_loadu: unsupported element type {elem_type}")
                vec_ptr = self.builder.bitcast(ptr, ir.PointerType(vec_type))
                load_instr = self.builder.load(vec_ptr)
                load_instr.align = 1  # Unaligned
                return load_instr
            raise ValueError("simd_loadu() requires a pointer argument")

        elif fname == 'simd_store':
            # simd_store(ptr: *T, val: vec<N, T>)
            # Aligned 16-byte store
            if len(args) != 2:
                raise ValueError("simd_store() requires 2 arguments (pointer, value)")
            ptr = self._emit_expr(args[0])
            val = self._emit_expr(args[1])
            if isinstance(ptr.type, ir.PointerType) and isinstance(val.type, ir.VectorType):
                vec_ptr = self.builder.bitcast(ptr, ir.PointerType(val.type))
                store_instr = self.builder.store(val, vec_ptr)
                store_instr.align = 16
                return store_instr
            raise ValueError("simd_store() requires (pointer, vector) arguments")

        elif fname == 'simd_storeu':
            # simd_storeu(ptr: *T, val: vec<N, T>)
            # Unaligned store
            if len(args) != 2:
                raise ValueError("simd_storeu() requires 2 arguments (pointer, value)")
            ptr = self._emit_expr(args[0])
            val = self._emit_expr(args[1])
            if isinstance(ptr.type, ir.PointerType) and isinstance(val.type, ir.VectorType):
                vec_ptr = self.builder.bitcast(ptr, ir.PointerType(val.type))
                store_instr = self.builder.store(val, vec_ptr)
                store_instr.align = 1  # Unaligned
                return store_instr
            raise ValueError("simd_storeu() requires (pointer, vector) arguments")

        elif fname == 'simd_extract':
            # simd_extract(vec: vec<N, T>, idx: i32) -> T
            if len(args) != 2:
                raise ValueError("simd_extract() requires 2 arguments (vector, index)")
            vec = self._emit_expr(args[0])
            idx = self._emit_expr(args[1])
            if isinstance(vec.type, ir.VectorType):
                return self.builder.extract_element(vec, idx)
            raise ValueError("simd_extract() requires a vector argument")

        elif fname == 'simd_insert':
            # simd_insert(vec: vec<N, T>, idx: i32, val: T) -> vec<N, T>
            if len(args) != 3:
                raise ValueError("simd_insert() requires 3 arguments (vector, index, value)")
            vec = self._emit_expr(args[0])
            idx = self._emit_expr(args[1])
            val = self._emit_expr(args[2])
            if isinstance(vec.type, ir.VectorType):
                return self.builder.insert_element(vec, val, idx)
            raise ValueError("simd_insert() requires a vector argument")

        elif fname == 'simd_shuffle':
            # simd_shuffle(a: vec<N, T>, b: vec<N, T>, mask_vals...)
            # Variadic: mask indices follow the two vectors
            # Example: simd_shuffle(a, b, 0, 1, 2, 3) for identity shuffle
            if len(args) < 3:
                raise ValueError("simd_shuffle() requires at least 3 arguments (vec, vec, mask...)")
            vec_a = self._emit_expr(args[0])
            vec_b = self._emit_expr(args[1])
            if not isinstance(vec_a.type, ir.VectorType):
                raise ValueError("simd_shuffle() first argument must be a vector")
            # Build mask from remaining args (must be constants)
            mask_vals = []
            for i, mask_arg in enumerate(args[2:]):
                mask_val = self._emit_expr(mask_arg)
                if isinstance(mask_val, ir.Constant):
                    mask_vals.append(int(mask_val.constant))
                else:
                    raise ValueError(f"simd_shuffle() mask index {i} must be a constant")
            # Create mask as constant vector
            mask_type = ir.VectorType(self.i32, len(mask_vals))
            mask = ir.Constant(mask_type, mask_vals)
            return self.builder.shuffle_vector(vec_a, vec_b, mask)

        elif fname == 'simd_sad':
            # simd_sad(a: vec<16, i8>, b: vec<16, i8>) -> vec<2, i64>
            # Sum of absolute differences: psadbw intrinsic
            # Returns two 64-bit sums (low and high halves)
            if len(args) != 2:
                raise ValueError("simd_sad() requires 2 arguments (vec<16, i8>, vec<16, i8>)")
            vec_a = self._emit_expr(args[0])
            vec_b = self._emit_expr(args[1])
            # Ensure both are v16i8
            if vec_a.type != v16i8 or vec_b.type != v16i8:
                raise ValueError("simd_sad() requires vec<16, i8> arguments")
            # Get or declare llvm.x86.sse2.psad.bw intrinsic
            intrinsic_name = 'llvm.x86.sse2.psad.bw'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v2i64, [v16i8, v16i8])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            return self.builder.call(intrinsic, [vec_a, vec_b])

        elif fname == 'simd_clmul':
            # simd_clmul(a: v2i64, b: v2i64, imm: i8) -> v2i64
            # Carryless multiply: PCLMULQDQ intrinsic for CRC32 acceleration
            #
            # The imm8 selects which 64-bit halves to multiply:
            #   0x00: a[63:0]   * b[63:0]   (low * low)
            #   0x01: a[127:64] * b[63:0]   (high * low)
            #   0x10: a[63:0]   * b[127:64] (low * high)
            #   0x11: a[127:64] * b[127:64] (high * high)
            #
            # IMPORTANT: imm8 MUST be a compile-time constant (immarg constraint)
            # Result is 128-bit carryless product in v2i64.
            if len(args) != 3:
                raise ValueError("simd_clmul() requires 3 arguments (v2i64, v2i64, imm8)")
            vec_a = self._emit_expr(args[0])
            vec_b = self._emit_expr(args[1])

            # The imm8 must be a compile-time constant for PCLMULQDQ
            # Extract the constant value from the AST node directly
            imm_arg = args[2]
            imm_value = None
            if isinstance(imm_arg, rast.IntLit):
                imm_value = imm_arg.value
            elif isinstance(imm_arg, rast.Cast) and isinstance(imm_arg.expr, rast.IntLit):
                imm_value = imm_arg.expr.value
            else:
                raise ValueError("simd_clmul() imm8 must be a compile-time constant integer literal")

            # Validate range
            if imm_value < 0 or imm_value > 255:
                raise ValueError(f"simd_clmul() imm8 must be 0-255, got {imm_value}")

            imm = ir.Constant(self.i8, imm_value)

            # Ensure vectors are v2i64
            if vec_a.type != v2i64 or vec_b.type != v2i64:
                raise ValueError("simd_clmul() requires v2i64 arguments")

            # Get or declare llvm.x86.pclmulqdq intrinsic
            intrinsic_name = 'llvm.x86.pclmulqdq'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v2i64, [v2i64, v2i64, self.i8])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            return self.builder.call(intrinsic, [vec_a, vec_b, imm])

        elif fname == 'simd_add':
            # simd_add(a: vec<N, T>, b: vec<N, T>) -> vec<N, T>
            # Vector integer addition (works for both SSE2 and AVX2)
            if len(args) != 2:
                raise ValueError("simd_add() requires 2 arguments (vector, vector)")
            vec_a = self._emit_expr(args[0])
            vec_b = self._emit_expr(args[1])
            if not isinstance(vec_a.type, ir.VectorType) or not isinstance(vec_b.type, ir.VectorType):
                raise ValueError("simd_add() requires vector arguments")
            if vec_a.type != vec_b.type:
                raise ValueError("simd_add() requires vectors of the same type")
            # LLVM add instruction works on vectors
            return self.builder.add(vec_a, vec_b)

        elif fname == 'simd_xor':
            # simd_xor(a: vec<N, T>, b: vec<N, T>) -> vec<N, T>
            # Vector XOR (works for both SSE2 and AVX2)
            if len(args) != 2:
                raise ValueError("simd_xor() requires 2 arguments (vector, vector)")
            vec_a = self._emit_expr(args[0])
            vec_b = self._emit_expr(args[1])
            if not isinstance(vec_a.type, ir.VectorType) or not isinstance(vec_b.type, ir.VectorType):
                raise ValueError("simd_xor() requires vector arguments")
            if vec_a.type != vec_b.type:
                raise ValueError("simd_xor() requires vectors of the same type")
            # LLVM xor instruction works on vectors
            return self.builder.xor(vec_a, vec_b)

        elif fname == 'simd_rotl':
            # simd_rotl(v: vec<N, T>, n: i32) -> vec<N, T>
            # Vector rotate left by constant amount (for ChaCha20 quarter round)
            # Implemented as: (v << n) | (v >> (bits - n))
            # Note: n must be a compile-time constant for optimal codegen
            if len(args) != 2:
                raise ValueError("simd_rotl() requires 2 arguments (vector, shift)")
            vec = self._emit_expr(args[0])
            if not isinstance(vec.type, ir.VectorType):
                raise ValueError("simd_rotl() requires a vector argument")

            # Extract shift amount (must be constant for efficient codegen)
            shift_arg = args[1]
            if isinstance(shift_arg, rast.IntLit):
                shift_amount = shift_arg.value
            elif isinstance(shift_arg, rast.Cast) and isinstance(shift_arg.expr, rast.IntLit):
                shift_amount = shift_arg.expr.value
            else:
                raise ValueError("simd_rotl() shift amount must be a compile-time constant")

            # Determine element bit width
            elem_type = vec.type.element
            if elem_type == self.i32:
                bits = 32
            elif elem_type == self.i64:
                bits = 64
            elif elem_type == self.i16:
                bits = 16
            elif elem_type == self.i8:
                bits = 8
            else:
                raise ValueError(f"simd_rotl() unsupported element type {elem_type}")

            # Create broadcast vectors for shift amounts
            num_elems = vec.type.count
            left_shift_val = ir.Constant(vec.type, [shift_amount] * num_elems)
            right_shift_val = ir.Constant(vec.type, [bits - shift_amount] * num_elems)

            # rotl(v, n) = (v << n) | (v >> (bits - n))
            left = self.builder.shl(vec, left_shift_val)
            right = self.builder.lshr(vec, right_shift_val)
            return self.builder.or_(left, right)

        elif fname == 'cpuid_raw':
            # cpuid_raw(leaf: u32, subleaf: u32, out_eax: *u32, out_ebx: *u32, out_ecx: *u32, out_edx: *u32) -> void
            # Uses inline assembly to execute CPUID instruction
            # Writes results to the provided output pointers
            if len(args) != 6:
                raise ValueError("cpuid_raw() requires 6 arguments (leaf, subleaf, out_eax, out_ebx, out_ecx, out_edx)")
            leaf = self._emit_expr(args[0])
            subleaf = self._emit_expr(args[1])
            out_eax = self._emit_expr(args[2])
            out_ebx = self._emit_expr(args[3])
            out_ecx = self._emit_expr(args[4])
            out_edx = self._emit_expr(args[5])

            # Convert to i32 if needed
            if leaf.type != self.i32:
                leaf = self.builder.trunc(leaf, self.i32) if leaf.type.width > 32 else self.builder.zext(leaf, self.i32)
            if subleaf.type != self.i32:
                subleaf = self.builder.trunc(subleaf, self.i32) if subleaf.type.width > 32 else self.builder.zext(subleaf, self.i32)

            # Define the result struct type: {i32, i32, i32, i32} for eax, ebx, ecx, edx
            result_type = ir.LiteralStructType([self.i32, self.i32, self.i32, self.i32])

            # CPUID inline asm:
            # Input: eax = leaf, ecx = subleaf
            # Output: eax, ebx, ecx, edx
            # The asm string uses AT&T syntax (cpuid clobbers eax, ebx, ecx, edx)
            asm_str = "cpuid"
            # Constraints: ={eax},={ebx},={ecx},={edx},{eax},{ecx}
            # Output: eax, ebx, ecx, edx (in order)
            # Input: eax (leaf), ecx (subleaf)
            constraints = "={ax},={bx},={cx},={dx},{ax},{cx},~{dirflag},~{fpsr},~{flags}"

            asm_func_ty = ir.FunctionType(result_type, [self.i32, self.i32])
            asm_ir = ir.InlineAsm(asm_func_ty, asm_str, constraints, side_effect=True)
            result = self.builder.call(asm_ir, [leaf, subleaf])

            # Extract and store each register value
            eax = self.builder.extract_value(result, 0)
            ebx = self.builder.extract_value(result, 1)
            ecx = self.builder.extract_value(result, 2)
            edx = self.builder.extract_value(result, 3)

            self.builder.store(eax, out_eax)
            self.builder.store(ebx, out_ebx)
            self.builder.store(ecx, out_ecx)
            self.builder.store(edx, out_edx)

            # Return void (no value)
            return ir.Constant(self.i32, 0)

        elif fname == 'xgetbv':
            # xgetbv(xcr: u32) -> u64
            # Uses inline assembly to execute XGETBV instruction
            # Returns XCR register value (edx:eax combined as u64)
            if len(args) != 1:
                raise ValueError("xgetbv() requires 1 argument (xcr)")
            xcr = self._emit_expr(args[0])

            # Convert to i32 if needed
            if xcr.type != self.i32:
                xcr = self.builder.trunc(xcr, self.i32) if xcr.type.width > 32 else self.builder.zext(xcr, self.i32)

            # XGETBV returns edx:eax as a 64-bit value
            # Input: ecx = xcr number
            # Output: edx:eax (high:low 32-bit parts)
            asm_str = "xgetbv"
            # Use =A constraint to get edx:eax as a single 64-bit value
            constraints = "={ax},={dx},{cx},~{dirflag},~{fpsr},~{flags}"

            # Returns two i32 values that we combine into i64
            result_type = ir.LiteralStructType([self.i32, self.i32])
            asm_func_ty = ir.FunctionType(result_type, [self.i32])
            asm_ir = ir.InlineAsm(asm_func_ty, asm_str, constraints, side_effect=True)
            result = self.builder.call(asm_ir, [xcr])

            # Extract eax (low) and edx (high) and combine into i64
            eax = self.builder.extract_value(result, 0)
            edx = self.builder.extract_value(result, 1)
            eax_64 = self.builder.zext(eax, self.i64)
            edx_64 = self.builder.zext(edx, self.i64)
            edx_shifted = self.builder.shl(edx_64, ir.Constant(self.i64, 32))
            return self.builder.or_(eax_64, edx_shifted)

        # =====================================================================
        # AES-NI: Advanced Encryption Standard New Instructions (ritz#119)
        # =====================================================================

        elif fname == 'aesenc':
            # aesenc(state, key) -> same type as input
            # One round of AES encryption (ShiftRows, SubBytes, MixColumns, AddRoundKey)
            # Accepts v4i32 or v2i64 (both are 128-bit vectors)
            if len(args) != 2:
                raise ValueError("aesenc() requires 2 arguments (state, key)")
            state = self._emit_expr(args[0])
            key = self._emit_expr(args[1])

            # Determine input type and convert to v2i64 for LLVM intrinsic
            input_type = state.type
            if input_type == v4i32:
                state_i64 = self.builder.bitcast(state, v2i64)
                key_i64 = self.builder.bitcast(key, v2i64)
            elif input_type == v2i64:
                state_i64 = state
                key_i64 = key
            else:
                raise ValueError("aesenc() requires v4i32 or v2i64 arguments")

            intrinsic_name = 'llvm.x86.aesni.aesenc'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v2i64, [v2i64, v2i64])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            result = self.builder.call(intrinsic, [state_i64, key_i64])
            # Return same type as input
            if input_type == v4i32:
                return self.builder.bitcast(result, v4i32)
            return result

        elif fname == 'aesenclast':
            # aesenclast(state, key) -> same type as input
            # Final round of AES encryption (ShiftRows, SubBytes, AddRoundKey - no MixColumns)
            if len(args) != 2:
                raise ValueError("aesenclast() requires 2 arguments (state, key)")
            state = self._emit_expr(args[0])
            key = self._emit_expr(args[1])

            input_type = state.type
            if input_type == v4i32:
                state_i64 = self.builder.bitcast(state, v2i64)
                key_i64 = self.builder.bitcast(key, v2i64)
            elif input_type == v2i64:
                state_i64 = state
                key_i64 = key
            else:
                raise ValueError("aesenclast() requires v4i32 or v2i64 arguments")

            intrinsic_name = 'llvm.x86.aesni.aesenclast'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v2i64, [v2i64, v2i64])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            result = self.builder.call(intrinsic, [state_i64, key_i64])
            if input_type == v4i32:
                return self.builder.bitcast(result, v4i32)
            return result

        elif fname == 'aesdec':
            # aesdec(state, key) -> same type as input
            # One round of AES decryption (InvShiftRows, InvSubBytes, InvMixColumns, AddRoundKey)
            if len(args) != 2:
                raise ValueError("aesdec() requires 2 arguments (state, key)")
            state = self._emit_expr(args[0])
            key = self._emit_expr(args[1])

            input_type = state.type
            if input_type == v4i32:
                state_i64 = self.builder.bitcast(state, v2i64)
                key_i64 = self.builder.bitcast(key, v2i64)
            elif input_type == v2i64:
                state_i64 = state
                key_i64 = key
            else:
                raise ValueError("aesdec() requires v4i32 or v2i64 arguments")

            intrinsic_name = 'llvm.x86.aesni.aesdec'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v2i64, [v2i64, v2i64])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            result = self.builder.call(intrinsic, [state_i64, key_i64])
            if input_type == v4i32:
                return self.builder.bitcast(result, v4i32)
            return result

        elif fname == 'aesdeclast':
            # aesdeclast(state, key) -> same type as input
            # Final round of AES decryption (InvShiftRows, InvSubBytes, AddRoundKey - no InvMixColumns)
            if len(args) != 2:
                raise ValueError("aesdeclast() requires 2 arguments (state, key)")
            state = self._emit_expr(args[0])
            key = self._emit_expr(args[1])

            input_type = state.type
            if input_type == v4i32:
                state_i64 = self.builder.bitcast(state, v2i64)
                key_i64 = self.builder.bitcast(key, v2i64)
            elif input_type == v2i64:
                state_i64 = state
                key_i64 = key
            else:
                raise ValueError("aesdeclast() requires v4i32 or v2i64 arguments")

            intrinsic_name = 'llvm.x86.aesni.aesdeclast'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v2i64, [v2i64, v2i64])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            result = self.builder.call(intrinsic, [state_i64, key_i64])
            if input_type == v4i32:
                return self.builder.bitcast(result, v4i32)
            return result

        elif fname == 'aesimc':
            # aesimc(key) -> same type as input
            # AES Inverse MixColumns (for computing decryption round keys)
            # Accepts v4i32 or v2i64 (both are 128-bit vectors)
            if len(args) != 1:
                raise ValueError("aesimc() requires 1 argument (key)")
            key = self._emit_expr(args[0])

            input_type = key.type
            if input_type == v4i32:
                key_i64 = self.builder.bitcast(key, v2i64)
            elif input_type == v2i64:
                key_i64 = key
            else:
                raise ValueError("aesimc() requires v4i32 or v2i64 argument")

            intrinsic_name = 'llvm.x86.aesni.aesimc'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v2i64, [v2i64])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            result = self.builder.call(intrinsic, [key_i64])
            if input_type == v4i32:
                return self.builder.bitcast(result, v4i32)
            return result

        # =====================================================================
        # SHA-NI: SHA Extensions for hardware SHA-256 (ritz#119)
        # =====================================================================

        elif fname == 'sha256rnds2':
            # sha256rnds2(cdgh: v4i32, abef: v4i32, wk: v4i32) -> v4i32
            # Perform two SHA-256 rounds
            # cdgh = state words c,d,g,h; abef = state words a,b,e,f
            # wk = message schedule word + round constant (only low 64 bits used)
            if len(args) != 3:
                raise ValueError("sha256rnds2() requires 3 arguments (cdgh, abef, wk)")
            cdgh = self._emit_expr(args[0])
            abef = self._emit_expr(args[1])
            wk = self._emit_expr(args[2])
            if cdgh.type != v4i32 or abef.type != v4i32 or wk.type != v4i32:
                raise ValueError("sha256rnds2() requires v4i32 arguments")

            intrinsic_name = 'llvm.x86.sha256rnds2'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v4i32, [v4i32, v4i32, v4i32])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            return self.builder.call(intrinsic, [cdgh, abef, wk])

        elif fname == 'sha256msg1':
            # sha256msg1(w0: v4i32, w1: v4i32) -> v4i32
            # SHA-256 message schedule transformation (part 1)
            # Computes sigma0 and adds to message words
            if len(args) != 2:
                raise ValueError("sha256msg1() requires 2 arguments (w0, w1)")
            w0 = self._emit_expr(args[0])
            w1 = self._emit_expr(args[1])
            if w0.type != v4i32 or w1.type != v4i32:
                raise ValueError("sha256msg1() requires v4i32 arguments")

            intrinsic_name = 'llvm.x86.sha256msg1'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v4i32, [v4i32, v4i32])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            return self.builder.call(intrinsic, [w0, w1])

        elif fname == 'sha256msg2':
            # sha256msg2(w0: v4i32, w1: v4i32) -> v4i32
            # SHA-256 message schedule transformation (part 2)
            # Computes sigma1 and completes message expansion
            if len(args) != 2:
                raise ValueError("sha256msg2() requires 2 arguments (w0, w1)")
            w0 = self._emit_expr(args[0])
            w1 = self._emit_expr(args[1])
            if w0.type != v4i32 or w1.type != v4i32:
                raise ValueError("sha256msg2() requires v4i32 arguments")

            intrinsic_name = 'llvm.x86.sha256msg2'
            if intrinsic_name in self.module.globals:
                intrinsic = self.module.globals[intrinsic_name]
            else:
                fnty = ir.FunctionType(v4i32, [v4i32, v4i32])
                intrinsic = ir.Function(self.module, fnty, name=intrinsic_name)
            return self.builder.call(intrinsic, [w0, w1])

        # Not a SIMD builtin
        return None


    def _try_emit_bitops_intrinsic(self, expr: rast.MethodCall, type_name: str) -> ir.Value:
        """Try to emit a BitOps intrinsic for primitive integer types.

        Returns the IR value if this is a BitOps method on a primitive,
        or None if it should be handled as a normal method call.

        BitOps methods:
        - rotl(n: u8) -> Self: rotate left
        - rotr(n: u8) -> Self: rotate right
        - clz() -> u8: count leading zeros
        - ctz() -> u8: count trailing zeros
        - popcnt() -> u8: population count (hamming weight)
        - swap_bytes() -> Self: byte swap (endianness conversion)
        """
        # Check if type is a primitive integer
        int_types = {'u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32', 'i64'}
        if type_name not in int_types:
            return None

        method = expr.method
        bitops_methods = {'rotl', 'rotr', 'clz', 'ctz', 'popcnt', 'swap_bytes'}
        if method not in bitops_methods:
            return None

        # Emit the receiver value
        receiver = self._emit_expr(expr.expr)

        # Get the LLVM type for this integer
        type_bits = {
            'u8': 8, 'i8': 8,
            'u16': 16, 'i16': 16,
            'u32': 32, 'i32': 32,
            'u64': 64, 'i64': 64,
        }
        bits = type_bits[type_name]
        llvm_type = getattr(self, f'i{bits}')

        if method == 'rotl':
            # llvm.fshl.i32(a, a, b) = funnel shift left = rotate left when a == a
            if len(expr.args) != 1:
                raise ValueError(f"rotl() requires exactly 1 argument")
            shift_amount = self._emit_expr(expr.args[0])
            # Convert shift amount to same type as receiver
            shift_amount = self.builder.zext(shift_amount, llvm_type) if shift_amount.type.width < bits else shift_amount
            shift_amount = self.builder.trunc(shift_amount, llvm_type) if shift_amount.type.width > bits else shift_amount
            # Declare and call llvm.fshl intrinsic (need to specify fnty for correct signature)
            fn_type = ir.FunctionType(llvm_type, [llvm_type, llvm_type, llvm_type])
            intrinsic = self.module.declare_intrinsic('llvm.fshl', [llvm_type], fnty=fn_type)
            return self.builder.call(intrinsic, [receiver, receiver, shift_amount])

        elif method == 'rotr':
            # llvm.fshr.i32(a, a, b) = funnel shift right = rotate right when a == a
            if len(expr.args) != 1:
                raise ValueError(f"rotr() requires exactly 1 argument")
            shift_amount = self._emit_expr(expr.args[0])
            shift_amount = self.builder.zext(shift_amount, llvm_type) if shift_amount.type.width < bits else shift_amount
            shift_amount = self.builder.trunc(shift_amount, llvm_type) if shift_amount.type.width > bits else shift_amount
            fn_type = ir.FunctionType(llvm_type, [llvm_type, llvm_type, llvm_type])
            intrinsic = self.module.declare_intrinsic('llvm.fshr', [llvm_type], fnty=fn_type)
            return self.builder.call(intrinsic, [receiver, receiver, shift_amount])

        elif method == 'clz':
            # llvm.ctlz.i32(x, is_zero_poison) -> count leading zeros
            if len(expr.args) != 0:
                raise ValueError(f"clz() takes no arguments")
            fn_type = ir.FunctionType(llvm_type, [llvm_type, ir.IntType(1)])
            intrinsic = self.module.declare_intrinsic('llvm.ctlz', [llvm_type], fnty=fn_type)
            # is_zero_poison = false (return bit width for zero input)
            result = self.builder.call(intrinsic, [receiver, ir.Constant(ir.IntType(1), 0)])
            # Truncate to u8
            return self.builder.trunc(result, self.i8)

        elif method == 'ctz':
            # llvm.cttz.i32(x, is_zero_poison) -> count trailing zeros
            if len(expr.args) != 0:
                raise ValueError(f"ctz() takes no arguments")
            fn_type = ir.FunctionType(llvm_type, [llvm_type, ir.IntType(1)])
            intrinsic = self.module.declare_intrinsic('llvm.cttz', [llvm_type], fnty=fn_type)
            result = self.builder.call(intrinsic, [receiver, ir.Constant(ir.IntType(1), 0)])
            return self.builder.trunc(result, self.i8)

        elif method == 'popcnt':
            # llvm.ctpop.i32(x) -> population count
            if len(expr.args) != 0:
                raise ValueError(f"popcnt() takes no arguments")
            fn_type = ir.FunctionType(llvm_type, [llvm_type])
            intrinsic = self.module.declare_intrinsic('llvm.ctpop', [llvm_type], fnty=fn_type)
            result = self.builder.call(intrinsic, [receiver])
            return self.builder.trunc(result, self.i8)

        elif method == 'swap_bytes':
            # llvm.bswap.i32(x) -> byte swap
            if len(expr.args) != 0:
                raise ValueError(f"swap_bytes() takes no arguments")
            if bits < 16:
                # bswap not defined for i8, just return the value
                return receiver
            fn_type = ir.FunctionType(llvm_type, [llvm_type])
            intrinsic = self.module.declare_intrinsic('llvm.bswap', [llvm_type], fnty=fn_type)
            return self.builder.call(intrinsic, [receiver])

        return None


    def _emit_method_call(self, expr: rast.MethodCall) -> ir.Value:
        """Emit a method call: receiver.method(args...).

        Method calls are desugared to static function calls using name mangling:
        - Type_method(receiver, args...) for inherent methods
        - Trait method calls look up the impl and use Type_method

        With monomorphization, we determine the receiver type at compile time
        and call the appropriate mangled function.

        If the method expects *Self and receiver is a value, we auto-borrow.

        For dyn Trait, we use dynamic dispatch through the vtable.
        """
        # Check if this is a method call on a dyn Trait (dynamic dispatch)
        receiver_type = self._infer_ritz_type(expr.expr)
        if isinstance(receiver_type, rast.DynType):
            return self._emit_dyn_method_call(expr, receiver_type)
        # Also handle reference to dyn Trait
        if isinstance(receiver_type, (rast.RefType, rast.PtrType)):
            if isinstance(receiver_type.inner, rast.DynType):
                return self._emit_dyn_method_call(expr, receiver_type.inner)

        # First, check if the receiver is an lvalue (identifier, field, index)
        # If so, get its address for auto-borrowing when method expects *Self
        receiver_is_lvalue = isinstance(expr.expr, (rast.Ident, rast.Field, rast.Index))

        # Determine receiver type first by peeking at the expression
        # For identifiers, we can look up the type directly
        type_name = None
        if isinstance(expr.expr, rast.Ident):
            name = expr.expr.name
            # First check ritz_types for the original Ritz type (preserves signedness)
            if name in self.ritz_types:
                ritz_type = self.ritz_types[name]
                if isinstance(ritz_type, rast.NamedType):
                    type_name = ritz_type.name
            # Fall back to LLVM type inspection for struct types
            if type_name is None:
                if name in self.locals:
                    alloca, ty = self.locals[name]
                    type_name = self._get_struct_name_from_type(ty)
                elif name in self.params:
                    val, ty = self.params[name]
                    type_name = self._get_struct_name_from_type(ty)

        # Look up the mangled function name (need type_name first)
        if type_name is None:
            # Fall back to emitting the expression and checking its type
            receiver_val = self._emit_expr(expr.expr)
            receiver_type = receiver_val.type
            if isinstance(receiver_type, ir.PointerType):
                type_name = self._get_struct_name_from_type(receiver_type.pointee)
            else:
                type_name = self._get_struct_name_from_type(receiver_type)
                # Also check for primitive integer types (for BitOps support)
                if type_name is None and isinstance(receiver_type, ir.IntType):
                    bits = receiver_type.width
                    # Default to unsigned for BitOps (both signed/unsigned work the same)
                    type_name = f'u{bits}'

        if type_name is None:
            raise ValueError(f"Cannot call method '{expr.method}' on unknown type")

        # Check for BitOps intrinsics on primitive integer types
        bitops_result = self._try_emit_bitops_intrinsic(expr, type_name)
        if bitops_result is not None:
            return bitops_result

        method_key = (type_name, expr.method)
        if method_key in self.method_lookup:
            mangled_name = self.method_lookup[method_key]
        else:
            # Fallback: look for standalone functions with naming convention
            # Vec$u8.len() -> vec_len$u8(&self)
            # String.len() -> string_len(&self)
            # Span$u8.len() -> span_len$u8(&self)
            mangled_name = self._find_method_fallback(type_name, expr.method)
            if mangled_name is None:
                raise ValueError(f"No method '{expr.method}' found for type '{type_name}'")

        if mangled_name not in self.functions:
            raise ValueError(f"Method function '{mangled_name}' not found")

        fn, fn_def = self.functions[mangled_name]
        first_param_type = fn.function_type.args[0]

        # Determine whether to pass by value or by pointer (auto-borrow)
        # If method expects pointer and receiver is lvalue, get address
        receiver_val = None
        if receiver_is_lvalue and isinstance(first_param_type, ir.PointerType):
            # Try to get address of the receiver
            # For `var` bindings, this is the alloca
            # For `let` bindings with struct values, we need special handling
            if isinstance(expr.expr, rast.Ident):
                name = expr.expr.name
                if name in self.locals:
                    # var binding - get the alloca
                    alloca, ty = self.locals[name]
                    # If the local is already a pointer, use it directly
                    if isinstance(ty, ir.PointerType):
                        receiver_val = self.builder.load(alloca)
                    else:
                        receiver_val = alloca
                elif name in self.globals:
                    # global var - get the global variable pointer
                    gvar, ty = self.globals[name]
                    if isinstance(ty, ir.PointerType):
                        receiver_val = self.builder.load(gvar)
                    else:
                        receiver_val = gvar
                elif name in self.params:
                    val, ty = self.params[name]
                    # If param is already a pointer, use it directly
                    if isinstance(ty, ir.PointerType):
                        receiver_val = val
                    else:
                        # let binding with struct value - create temporary storage
                        tmp = self.builder.alloca(ty, name=f"{name}.tmp")
                        self.builder.store(val, tmp)
                        receiver_val = tmp
                else:
                    raise ValueError(f"Unknown variable: {name}")
            else:
                # For other lvalues (field, index), use normal lvalue_addr
                receiver_val = self._emit_lvalue_addr(expr.expr)
        else:
            # Emit as normal expression
            receiver_val = self._emit_expr(expr.expr)

        # Build arguments: receiver first, then explicit args
        all_args = [receiver_val]
        for arg in expr.args:
            all_args.append(self._emit_expr(arg))

        # Convert argument types as needed
        converted_args = []
        for i, arg in enumerate(all_args):
            expected_type = fn.function_type.args[i]
            converted = self._convert_type(arg, expected_type)
            converted_args.append(converted)

        return self.builder.call(fn, converted_args)


    def _emit_dyn_method_call(self, expr: rast.MethodCall, dyn_type: rast.DynType) -> ir.Value:
        """Emit a method call on a dyn Trait using dynamic dispatch.

        Dynamic dispatch works through the vtable:
        1. Extract data pointer and vtable pointer from fat pointer
        2. Look up method function pointer in vtable
        3. Call through function pointer with data as self
        """
        trait_name = dyn_type.trait_name

        # Emit receiver (the fat pointer)
        fat_ptr = self._emit_expr(expr.expr)

        # If fat_ptr is a pointer to dyn struct, load it
        dyn_struct_type = self.dyn_types.get(trait_name)
        if dyn_struct_type and isinstance(fat_ptr.type, ir.PointerType):
            if fat_ptr.type.pointee == dyn_struct_type:
                fat_ptr = self.builder.load(fat_ptr, name='dyn.loaded')

        # Extract data and vtable pointers
        data_ptr = self._extract_data_ptr(fat_ptr)
        vtable_ptr = self._extract_vtable_ptr(fat_ptr)

        # Get method index in vtable
        method_index = self._get_trait_method_index(trait_name, expr.method)

        # Get vtable type for GEP
        vtable_type = self.vtable_types[trait_name]

        # Load method function pointer from vtable
        # vtable_ptr is *vtable.Trait, we need to GEP to get the method slot
        method_ptr_ptr = self.builder.gep(
            vtable_ptr,
            [ir.Constant(self.i32, 0), ir.Constant(self.i32, method_index)],
            name=f'dyn.method.{expr.method}.ptr_ptr'
        )
        method_ptr = self.builder.load(method_ptr_ptr, name=f'dyn.method.{expr.method}.ptr')

        # Build arguments: data_ptr as opaque self, then explicit args
        all_args = [data_ptr]
        for arg in expr.args:
            all_args.append(self._emit_expr(arg))

        # Call through function pointer
        return self.builder.call(method_ptr, all_args, name=f'dyn.call.{expr.method}')


    def _emit_syscall(self, name: str, args: List[rast.Expr]) -> ir.Value:
        """Emit an inline syscall."""
        syscall_nums = {
            'read': SYSCALL_READ,
            'write': SYSCALL_WRITE,
            'open': SYSCALL_OPEN,
            'close': SYSCALL_CLOSE,
            'nanosleep': SYSCALL_NANOSLEEP,
        }
        syscall_num = syscall_nums[name]

        # Emit arguments
        arg_vals = [self._emit_expr(arg) for arg in args]

        # Convert all args to i64
        arg_vals_64 = []
        for val in arg_vals:
            arg_vals_64.append(self._to_i64(val))

        # Build inline asm based on arg count
        if len(arg_vals_64) == 1:
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64])
            asm_args = [ir.Constant(self.i64, syscall_num), arg_vals_64[0]]
        elif len(arg_vals_64) == 2:
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64, self.i64])
            asm_args = [ir.Constant(self.i64, syscall_num), arg_vals_64[0], arg_vals_64[1]]
        elif len(arg_vals_64) == 3:
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64, self.i64, self.i64])
            asm_args = [ir.Constant(self.i64, syscall_num)] + arg_vals_64
        else:
            raise ValueError(f"Syscall with {len(arg_vals_64)} args not supported")

        asm_ir = ir.InlineAsm(asm_func_ty, asm_str, constraints, side_effect=True)
        result = self.builder.call(asm_ir, asm_args)

        # Truncate result if needed (e.g., open returns i32)
        if name in ('open', 'close'):
            result = self.builder.trunc(result, self.i32)

        return result


    def _emit_generic_syscall(self, fname: str, args: List[rast.Expr]) -> ir.Value:
        """Emit a generic syscallN(num, arg1, ...) call.

        syscall1(num, arg1) - 1 arg syscall
        syscall2(num, arg1, arg2) - 2 arg syscall
        syscall3(num, arg1, arg2, arg3) - 3 arg syscall
        syscall4(num, arg1, arg2, arg3, arg4) - 4 arg syscall
        """
        # Emit all arguments
        arg_vals = [self._emit_expr(arg) for arg in args]

        # First arg is the syscall number
        if not arg_vals:
            raise ValueError(f"{fname} requires at least a syscall number")

        syscall_num = self._to_i64(arg_vals[0])

        # Remaining args are the syscall arguments
        syscall_args = [self._to_i64(v) for v in arg_vals[1:]]

        if len(syscall_args) == 0:
            # syscall with no args (just the number)
            asm_str = "syscall"
            constraints = "=&{rax},{rax},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64])
            asm_args = [syscall_num]
        elif len(syscall_args) == 1:
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64])
            asm_args = [syscall_num, syscall_args[0]]
        elif len(syscall_args) == 2:
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64, self.i64])
            asm_args = [syscall_num, syscall_args[0], syscall_args[1]]
        elif len(syscall_args) == 3:
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64, self.i64, self.i64])
            asm_args = [syscall_num] + syscall_args
        elif len(syscall_args) == 4:
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},{rsi},{rdx},{r10},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64, self.i64, self.i64, self.i64])
            asm_args = [syscall_num] + syscall_args
        elif len(syscall_args) == 5:
            # 5 args: rdi, rsi, rdx, r10, r8
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},{rsi},{rdx},{r10},{r8},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64, self.i64, self.i64, self.i64, self.i64])
            asm_args = [syscall_num] + syscall_args
        elif len(syscall_args) == 6:
            # 6 args: rdi, rsi, rdx, r10, r8, r9 (e.g., mmap)
            asm_str = "syscall"
            constraints = "=&{rax},{rax},{rdi},{rsi},{rdx},{r10},{r8},{r9},~{rcx},~{r11},~{memory}"
            asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64, self.i64, self.i64, self.i64, self.i64, self.i64])
            asm_args = [syscall_num] + syscall_args
        else:
            raise ValueError(f"Syscall with {len(syscall_args)} args not supported (max 6)")

        asm_ir = ir.InlineAsm(asm_func_ty, asm_str, constraints, side_effect=True)
        return self.builder.call(asm_ir, asm_args)


    def _emit_write_syscall(self, fd: ir.Value, buf: ir.Value, count: ir.Value) -> ir.Value:
        """Emit a write syscall (fd, buf, count) -> bytes written."""
        # Convert args to i64
        fd_64 = self._to_i64(fd)
        buf_64 = self._to_i64(buf)
        count_64 = self._to_i64(count)

        asm_str = "syscall"
        constraints = "=&{rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"
        asm_func_ty = ir.FunctionType(self.i64, [self.i64, self.i64, self.i64, self.i64])
        asm_args = [ir.Constant(self.i64, SYSCALL_WRITE), fd_64, buf_64, count_64]

        asm_ir = ir.InlineAsm(asm_func_ty, asm_str, constraints, side_effect=True)
        return self.builder.call(asm_ir, asm_args)


