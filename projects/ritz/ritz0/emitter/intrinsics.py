"""SIMD, crypto (AES-NI / SHA-NI) and BitOps intrinsics, table-driven (AGAST #1826).

These used to be two long if/elif chains on LLVMEmitter: a 139-branch
`_try_emit_simd_builtin` and `_try_emit_bitops_intrinsic`.  Each builtin is now
one handler, and SIMD_BUILTINS / BITOPS_METHODS map a name to its handler.  The
emitter methods only look the name up and call it.

A handler takes the LLVMEmitter (`em`) as its first argument and uses its
public-in-practice surface: `em.builder`, `em.module`, `em._emit_expr`,
`em._err`, `em.i8` .. `em.i64`, `em.simd_expected_type`.  The handlers emit the
same instructions in the same order as the chains did; the IR is byte-identical.

SIMD builtins (fn-call syntax):
- simd_load(ptr: *T) -> vec<N, T>: Aligned vector load (16/32-byte)
- simd_loadu(ptr: *T) -> vec<N, T>: Unaligned vector load
- simd_store(ptr: *T, val: vec<N, T>): Aligned vector store
- simd_storeu(ptr: *T, val: vec<N, T>): Unaligned vector store
- simd_extract(vec: vec<N, T>, idx: i32) -> T: Extract element
- simd_insert(vec: vec<N, T>, idx: i32, val: T) -> vec<N, T>: Insert element
- simd_shuffle(a: vec<N, T>, b: vec<N, T>, mask: ...) -> vec<N, T>: Shuffle elements
- simd_sad(a: vec<16, i8>, b: vec<16, i8>) -> vec<2, i64>: Sum of absolute differences
- simd_clmul(a: v2i64, b: v2i64, imm8) -> v2i64: Carryless multiply (PCLMULQDQ)
- simd_add / simd_xor(a: vec<N, T>, b: vec<N, T>) -> vec<N, T>
- simd_rotl(v: vec<N, T>, n: i32) -> vec<N, T>: Vector rotate left (constant n)
- xgetbv(xcr: u32) -> u64
- AES-NI (ritz#119): aesenc, aesenclast, aesdec, aesdeclast, aesimc, aeskeygenassist
- SHA-NI (ritz#119): sha256rnds2, sha256msg1, sha256msg2

BitOps methods on a primitive integer receiver:
- rotl(n) / rotr(n) -> Self: rotate (llvm.fshl / llvm.fshr with a == b)
- clz() / ctz() / popcnt() -> u8: count leading / trailing zeros, population count
- swap_bytes() -> Self: byte swap (endianness conversion)
"""

from typing import Callable, Dict, Optional

from llvmlite import ir

import ritz_ast as rast


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _vec_types(em) -> Dict[str, ir.VectorType]:
    """The SSE2 (128-bit) and AVX2 (256-bit) integer vector types by Ritz name."""
    return {
        # SSE2 128-bit
        'v16i8': ir.VectorType(em.i8, 16), 'v8i16': ir.VectorType(em.i16, 8),
        'v4i32': ir.VectorType(em.i32, 4), 'v2i64': ir.VectorType(em.i64, 2),
        # AVX2 256-bit
        'v32i8': ir.VectorType(em.i8, 32), 'v16i16': ir.VectorType(em.i16, 16),
        'v8i32': ir.VectorType(em.i32, 8), 'v4i64': ir.VectorType(em.i64, 4),
    }


_AVX2_NAMES = ('v32i8', 'v16i16', 'v8i32', 'v4i64')


def _v4i32(em) -> ir.VectorType:
    return ir.VectorType(em.i32, 4)


def _v2i64(em) -> ir.VectorType:
    return ir.VectorType(em.i64, 2)


def _intrinsic(em, name: str, ret: ir.Type, params: list) -> ir.Function:
    """Get `name` from the module, or declare it as ret(params)."""
    if name in em.module.globals:
        return em.module.globals[name]
    return ir.Function(em.module, ir.FunctionType(ret, params), name=name)


def _require_arity(em, fname: str, args: list, n: int, what: str) -> None:
    if len(args) != n:
        raise em._err(f"{fname}() requires {what}")


def _const_int_arg(arg) -> Optional[int]:
    """An int literal, or a cast of one; None for anything else."""
    if isinstance(arg, rast.IntLit):
        return arg.value
    if isinstance(arg, rast.Cast) and isinstance(arg.expr, rast.IntLit):
        return arg.expr.value
    return None


# ---------------------------------------------------------------------------
# Loads and stores
# ---------------------------------------------------------------------------

def _load_vec_type(em, fname: str, ptr: ir.Value):
    """(vector type, is_avx2) for a simd_load/simd_loadu of `ptr`.

    The declared type of the `let` (em.simd_expected_type) wins; otherwise the
    pointer's element type picks the 128-bit SSE2 vector.
    """
    vecs = _vec_types(em)
    expected = em.simd_expected_type
    if expected and isinstance(expected, rast.NamedType):
        vec_type = vecs.get(expected.name)
        if vec_type is None:
            raise em._err(f"{fname}: unsupported expected type {expected.name}")
        return vec_type, expected.name in _AVX2_NAMES
    by_elem = {em.i8: 'v16i8', em.i16: 'v8i16', em.i32: 'v4i32', em.i64: 'v2i64'}
    elem_type = ptr.type.pointee
    for ty, name in by_elem.items():
        if elem_type == ty:
            return vecs[name], False
    raise em._err(f"{fname}: unsupported element type {elem_type}")


def _simd_load_common(em, fname: str, args: list, aligned: bool) -> ir.Value:
    _require_arity(em, fname, args, 1, "exactly 1 argument (pointer)")
    ptr = em._emit_expr(args[0])
    if not isinstance(ptr.type, ir.PointerType):
        raise em._err(f"{fname}() requires a pointer argument")
    vec_type, is_avx2 = _load_vec_type(em, fname, ptr)
    vec_ptr = em.builder.bitcast(ptr, ir.PointerType(vec_type))
    load_instr = em.builder.load(vec_ptr)
    # Aligned: 16-byte for SSE2, 32-byte for AVX2.  Unaligned: 1.
    load_instr.align = (32 if is_avx2 else 16) if aligned else 1
    return load_instr


def _simd_load(em, fname, args):
    return _simd_load_common(em, fname, args, aligned=True)


def _simd_loadu(em, fname, args):
    return _simd_load_common(em, fname, args, aligned=False)


def _simd_store_common(em, fname: str, args: list, align: int) -> ir.Value:
    _require_arity(em, fname, args, 2, "2 arguments (pointer, value)")
    ptr = em._emit_expr(args[0])
    val = em._emit_expr(args[1])
    if isinstance(ptr.type, ir.PointerType) and isinstance(val.type, ir.VectorType):
        vec_ptr = em.builder.bitcast(ptr, ir.PointerType(val.type))
        store_instr = em.builder.store(val, vec_ptr)
        store_instr.align = align
        return store_instr
    raise em._err(f"{fname}() requires (pointer, vector) arguments")


def _simd_store(em, fname, args):
    return _simd_store_common(em, fname, args, 16)


def _simd_storeu(em, fname, args):
    return _simd_store_common(em, fname, args, 1)


# ---------------------------------------------------------------------------
# Lane access and shuffles
# ---------------------------------------------------------------------------

def _simd_extract(em, fname, args):
    _require_arity(em, fname, args, 2, "2 arguments (vector, index)")
    vec = em._emit_expr(args[0])
    idx = em._emit_expr(args[1])
    if isinstance(vec.type, ir.VectorType):
        return em.builder.extract_element(vec, idx)
    raise em._err(f"{fname}() requires a vector argument")


def _simd_insert(em, fname, args):
    _require_arity(em, fname, args, 3, "3 arguments (vector, index, value)")
    vec = em._emit_expr(args[0])
    idx = em._emit_expr(args[1])
    val = em._emit_expr(args[2])
    if isinstance(vec.type, ir.VectorType):
        return em.builder.insert_element(vec, val, idx)
    raise em._err(f"{fname}() requires a vector argument")


def _simd_shuffle(em, fname, args):
    # Variadic: constant mask indices follow the two vectors, e.g.
    # simd_shuffle(a, b, 0, 1, 2, 3) is the identity.
    if len(args) < 3:
        raise em._err("simd_shuffle() requires at least 3 arguments (vec, vec, mask...)")
    vec_a = em._emit_expr(args[0])
    vec_b = em._emit_expr(args[1])
    if not isinstance(vec_a.type, ir.VectorType):
        raise em._err("simd_shuffle() first argument must be a vector")
    mask_vals = []
    for i, mask_arg in enumerate(args[2:]):
        mask_val = em._emit_expr(mask_arg)
        if not isinstance(mask_val, ir.Constant):
            raise em._err(f"simd_shuffle() mask index {i} must be a constant")
        mask_vals.append(int(mask_val.constant))
    mask = ir.Constant(ir.VectorType(em.i32, len(mask_vals)), mask_vals)
    return em.builder.shuffle_vector(vec_a, vec_b, mask)


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------

def _simd_sad(em, fname, args):
    # psadbw: two 64-bit sums of absolute differences (low and high halves).
    _require_arity(em, fname, args, 2, "2 arguments (vec<16, i8>, vec<16, i8>)")
    vec_a = em._emit_expr(args[0])
    vec_b = em._emit_expr(args[1])
    v16i8 = ir.VectorType(em.i8, 16)
    if vec_a.type != v16i8 or vec_b.type != v16i8:
        raise em._err("simd_sad() requires vec<16, i8> arguments")
    intrinsic = _intrinsic(em, 'llvm.x86.sse2.psad.bw', _v2i64(em), [v16i8, v16i8])
    return em.builder.call(intrinsic, [vec_a, vec_b])


def _simd_clmul(em, fname, args):
    # Carryless multiply (PCLMULQDQ, for CRC32).  imm8 picks the 64-bit halves:
    #   0x00 lo*lo, 0x01 hi(a)*lo(b), 0x10 lo(a)*hi(b), 0x11 hi*hi.
    # imm8 is an `immarg`: it must be a compile-time constant, read off the AST.
    _require_arity(em, fname, args, 3, "3 arguments (v2i64, v2i64, imm8)")
    vec_a = em._emit_expr(args[0])
    vec_b = em._emit_expr(args[1])
    imm_value = _const_int_arg(args[2])
    if imm_value is None:
        raise em._err("simd_clmul() imm8 must be a compile-time constant integer literal")
    if imm_value < 0 or imm_value > 255:
        raise em._err(f"simd_clmul() imm8 must be 0-255, got {imm_value}")
    imm = ir.Constant(em.i8, imm_value)
    v2i64 = _v2i64(em)
    if vec_a.type != v2i64 or vec_b.type != v2i64:
        raise em._err("simd_clmul() requires v2i64 arguments")
    intrinsic = _intrinsic(em, 'llvm.x86.pclmulqdq', v2i64, [v2i64, v2i64, em.i8])
    return em.builder.call(intrinsic, [vec_a, vec_b, imm])


def _vector_binop(op: str) -> Callable:
    """simd_add / simd_xor: one LLVM instruction on two same-typed vectors."""
    def handler(em, fname, args):
        _require_arity(em, fname, args, 2, "2 arguments (vector, vector)")
        vec_a = em._emit_expr(args[0])
        vec_b = em._emit_expr(args[1])
        if not isinstance(vec_a.type, ir.VectorType) or not isinstance(vec_b.type, ir.VectorType):
            raise em._err(f"{fname}() requires vector arguments")
        if vec_a.type != vec_b.type:
            raise em._err(f"{fname}() requires vectors of the same type")
        return getattr(em.builder, op)(vec_a, vec_b)
    return handler


def _simd_rotl(em, fname, args):
    # rotl(v, n) = (v << n) | (v >> (bits - n)), n a compile-time constant
    # (ChaCha20 quarter round).
    _require_arity(em, fname, args, 2, "2 arguments (vector, shift)")
    vec = em._emit_expr(args[0])
    if not isinstance(vec.type, ir.VectorType):
        raise em._err("simd_rotl() requires a vector argument")
    shift_amount = _const_int_arg(args[1])
    if shift_amount is None:
        raise em._err("simd_rotl() shift amount must be a compile-time constant")
    elem_type = vec.type.element
    bits = {em.i32: 32, em.i64: 64, em.i16: 16, em.i8: 8}.get(elem_type)
    if bits is None:
        raise em._err(f"simd_rotl() unsupported element type {elem_type}")
    num_elems = vec.type.count
    left_shift_val = ir.Constant(vec.type, [shift_amount] * num_elems)
    right_shift_val = ir.Constant(vec.type, [bits - shift_amount] * num_elems)
    left = em.builder.shl(vec, left_shift_val)
    right = em.builder.lshr(vec, right_shift_val)
    return em.builder.or_(left, right)


def _xgetbv(em, fname, args):
    # XGETBV: ecx = xcr number in, edx:eax out, combined into one u64.
    _require_arity(em, fname, args, 1, "1 argument (xcr)")
    xcr = em._emit_expr(args[0])
    if xcr.type != em.i32:
        xcr = em.builder.trunc(xcr, em.i32) if xcr.type.width > 32 else em.builder.zext(xcr, em.i32)
    constraints = "={ax},={dx},{cx},~{dirflag},~{fpsr},~{flags}"
    result_type = ir.LiteralStructType([em.i32, em.i32])
    asm_func_ty = ir.FunctionType(result_type, [em.i32])
    asm_ir = ir.InlineAsm(asm_func_ty, "xgetbv", constraints, side_effect=True)
    result = em.builder.call(asm_ir, [xcr])
    eax = em.builder.extract_value(result, 0)
    edx = em.builder.extract_value(result, 1)
    eax_64 = em.builder.zext(eax, em.i64)
    edx_64 = em.builder.zext(edx, em.i64)
    edx_shifted = em.builder.shl(edx_64, ir.Constant(em.i64, 32))
    return em.builder.or_(eax_64, edx_shifted)


# ---------------------------------------------------------------------------
# AES-NI (ritz#119).  Each takes v4i32 or v2i64 (both 128-bit), calls the
# v2i64 intrinsic, and returns the input's type.
# ---------------------------------------------------------------------------

def _as_v2i64(em, value: ir.Value, input_type: ir.Type) -> ir.Value:
    return em.builder.bitcast(value, _v2i64(em)) if input_type == _v4i32(em) else value


def _from_v2i64(em, result: ir.Value, input_type: ir.Type) -> ir.Value:
    return em.builder.bitcast(result, _v4i32(em)) if input_type == _v4i32(em) else result


def _is_aes_type(em, ty: ir.Type) -> bool:
    return ty == _v4i32(em) or ty == _v2i64(em)


def _aes_round(llvm_name: str) -> Callable:
    """aesenc / aesenclast / aesdec / aesdeclast(state, key) -> state's type."""
    def handler(em, fname, args):
        _require_arity(em, fname, args, 2, "2 arguments (state, key)")
        state = em._emit_expr(args[0])
        key = em._emit_expr(args[1])
        input_type = state.type
        if not _is_aes_type(em, input_type):
            raise em._err(f"{fname}() requires v4i32 or v2i64 arguments")
        state_i64 = _as_v2i64(em, state, input_type)
        key_i64 = _as_v2i64(em, key, input_type)
        v2i64 = _v2i64(em)
        intrinsic = _intrinsic(em, llvm_name, v2i64, [v2i64, v2i64])
        result = em.builder.call(intrinsic, [state_i64, key_i64])
        return _from_v2i64(em, result, input_type)
    return handler


def _aesimc(em, fname, args):
    # AES Inverse MixColumns, for computing decryption round keys.
    _require_arity(em, fname, args, 1, "1 argument (key)")
    key = em._emit_expr(args[0])
    input_type = key.type
    if not _is_aes_type(em, input_type):
        raise em._err("aesimc() requires v4i32 or v2i64 argument")
    key_i64 = _as_v2i64(em, key, input_type)
    v2i64 = _v2i64(em)
    intrinsic = _intrinsic(em, 'llvm.x86.aesni.aesimc', v2i64, [v2i64])
    result = em.builder.call(intrinsic, [key_i64])
    return _from_v2i64(em, result, input_type)


def _aeskeygenassist(em, fname, args):
    # AES key expansion helper.  rcon is an i8 `immarg`: LLVM's verifier wants
    # a literal ConstantInt, not an instruction (no trunc/zext in front of it).
    # A constant-folded value or an AST int literal is accepted; anything else
    # is a Ritz-level error rather than IR that LLVM refuses to assemble.
    _require_arity(em, fname, args, 2, "2 arguments (key, rcon)")
    key = em._emit_expr(args[0])
    input_type = key.type
    if not _is_aes_type(em, input_type):
        raise em._err("aeskeygenassist() requires v4i32 or v2i64 first argument")
    key_i64 = _as_v2i64(em, key, input_type)
    rcon_val = em._emit_expr(args[1])
    i8 = ir.IntType(8)
    if isinstance(rcon_val, ir.Constant) and isinstance(rcon_val.type, ir.IntType):
        rcon_const = ir.Constant(i8, rcon_val.constant & 0xFF)
    else:
        lit = getattr(args[1], "value", None)
        if not isinstance(lit, int):
            raise em._err(
                "aeskeygenassist() second arg (rcon) must be a compile-time integer constant; "
                "LLVM's @llvm.x86.aesni.aeskeygenassist requires an i8 immediate."
            )
        rcon_const = ir.Constant(i8, lit & 0xFF)
    v2i64 = _v2i64(em)
    intrinsic = _intrinsic(em, 'llvm.x86.aesni.aeskeygenassist', v2i64, [v2i64, i8])
    result = em.builder.call(intrinsic, [key_i64, rcon_const])
    return _from_v2i64(em, result, input_type)


# ---------------------------------------------------------------------------
# SHA-NI (ritz#119): every operand and the result are v4i32.
# ---------------------------------------------------------------------------

def _sha256(llvm_name: str, operands: str) -> Callable:
    """sha256rnds2(cdgh, abef, wk) / sha256msg1(w0, w1) / sha256msg2(w0, w1)."""
    n = operands.count(",") + 1

    def handler(em, fname, args):
        _require_arity(em, fname, args, n, f"{n} arguments ({operands})")
        vals = [em._emit_expr(a) for a in args]
        v4i32 = _v4i32(em)
        if any(v.type != v4i32 for v in vals):
            raise em._err(f"{fname}() requires v4i32 arguments")
        intrinsic = _intrinsic(em, llvm_name, v4i32, [v4i32] * n)
        return em.builder.call(intrinsic, vals)
    return handler


SIMD_BUILTINS: Dict[str, Callable] = {
    'simd_load': _simd_load,
    'simd_loadu': _simd_loadu,
    'simd_store': _simd_store,
    'simd_storeu': _simd_storeu,
    'simd_extract': _simd_extract,
    'simd_insert': _simd_insert,
    'simd_shuffle': _simd_shuffle,
    'simd_sad': _simd_sad,
    'simd_clmul': _simd_clmul,
    'simd_add': _vector_binop('add'),
    'simd_xor': _vector_binop('xor'),
    'simd_rotl': _simd_rotl,
    'xgetbv': _xgetbv,
    'aesenc': _aes_round('llvm.x86.aesni.aesenc'),
    'aesenclast': _aes_round('llvm.x86.aesni.aesenclast'),
    'aesdec': _aes_round('llvm.x86.aesni.aesdec'),
    'aesdeclast': _aes_round('llvm.x86.aesni.aesdeclast'),
    'aesimc': _aesimc,
    'aeskeygenassist': _aeskeygenassist,
    'sha256rnds2': _sha256('llvm.x86.sha256rnds2', 'cdgh, abef, wk'),
    'sha256msg1': _sha256('llvm.x86.sha256msg1', 'w0, w1'),
    'sha256msg2': _sha256('llvm.x86.sha256msg2', 'w0, w1'),
}


def try_emit_simd_builtin(em, fname: str, args: list) -> Optional[ir.Value]:
    """The IR value of SIMD builtin `fname`, or None if it is not one."""
    # SIMD functions need alignstack(16): movaps wants 16-byte aligned memory.
    if fname.startswith('simd_') and em.current_fn_def:
        em.simd_functions.add(em.current_fn_def.name)
    handler = SIMD_BUILTINS.get(fname)
    return None if handler is None else handler(em, fname, args)


# ---------------------------------------------------------------------------
# BitOps methods on primitive integers
# ---------------------------------------------------------------------------

_INT_BITS = {
    'u8': 8, 'i8': 8,
    'u16': 16, 'i16': 16,
    'u32': 32, 'i32': 32,
    'u64': 64, 'i64': 64,
}


def _bitop_rotate(llvm_name: str) -> Callable:
    """rotl / rotr: a funnel shift of the value with itself."""
    def handler(em, expr, receiver, llvm_type, bits):
        if len(expr.args) != 1:
            raise em._err(f"{expr.method}() requires exactly 1 argument")
        shift_amount = em._emit_expr(expr.args[0])
        # The shift amount takes the receiver's type.
        shift_amount = em.builder.zext(shift_amount, llvm_type) if shift_amount.type.width < bits else shift_amount
        shift_amount = em.builder.trunc(shift_amount, llvm_type) if shift_amount.type.width > bits else shift_amount
        fn_type = ir.FunctionType(llvm_type, [llvm_type, llvm_type, llvm_type])
        intrinsic = em.module.declare_intrinsic(llvm_name, [llvm_type], fnty=fn_type)
        return em.builder.call(intrinsic, [receiver, receiver, shift_amount])
    return handler


def _bitop_count(llvm_name: str, zero_poison_arg: bool) -> Callable:
    """clz / ctz (with is_zero_poison = false) and popcnt; the result is a u8."""
    def handler(em, expr, receiver, llvm_type, bits):
        if len(expr.args) != 0:
            raise em._err(f"{expr.method}() takes no arguments")
        params = [llvm_type, ir.IntType(1)] if zero_poison_arg else [llvm_type]
        fn_type = ir.FunctionType(llvm_type, params)
        intrinsic = em.module.declare_intrinsic(llvm_name, [llvm_type], fnty=fn_type)
        call_args = [receiver, ir.Constant(ir.IntType(1), 0)] if zero_poison_arg else [receiver]
        result = em.builder.call(intrinsic, call_args)
        return em.builder.trunc(result, em.i8)
    return handler


def _bitop_swap_bytes(em, expr, receiver, llvm_type, bits):
    if len(expr.args) != 0:
        raise em._err("swap_bytes() takes no arguments")
    if bits < 16:
        return receiver  # bswap is not defined for i8: a no-op
    fn_type = ir.FunctionType(llvm_type, [llvm_type])
    intrinsic = em.module.declare_intrinsic('llvm.bswap', [llvm_type], fnty=fn_type)
    return em.builder.call(intrinsic, [receiver])


BITOPS_METHODS: Dict[str, Callable] = {
    'rotl': _bitop_rotate('llvm.fshl'),
    'rotr': _bitop_rotate('llvm.fshr'),
    'clz': _bitop_count('llvm.ctlz', zero_poison_arg=True),
    'ctz': _bitop_count('llvm.cttz', zero_poison_arg=True),
    'popcnt': _bitop_count('llvm.ctpop', zero_poison_arg=False),
    'swap_bytes': _bitop_swap_bytes,
}


def try_emit_bitops_intrinsic(em, expr: rast.MethodCall, type_name: str) -> Optional[ir.Value]:
    """The IR value of BitOps method `expr` on a primitive integer, or None
    if it is not one (it is then handled as a normal method call)."""
    bits = _INT_BITS.get(type_name)
    handler = BITOPS_METHODS.get(expr.method)
    if bits is None or handler is None:
        return None
    receiver = em._emit_expr(expr.expr)
    llvm_type = getattr(em, f'i{bits}')
    return handler(em, expr, receiver, llvm_type, bits)
