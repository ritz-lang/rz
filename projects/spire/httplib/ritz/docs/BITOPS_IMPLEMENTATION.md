# BitOps Trait Implementation Plan

**Issue**: #97 - Feature: Bit manipulation trait methods on primitive integer types
**Approach**: Synthetic trait with compiler-recognized intrinsic methods

## Overview

Add a `BitOps` trait that provides bit manipulation methods on all integer primitives. The trait is "real" (visible to users, documentable, extensible) but the compiler emits LLVM intrinsics directly for primitive implementations.

```ritz
// User code
let x: u32 = 0xDEADBEEF
let rotated = x.rotl(16)      // compiles to llvm.fshl.i32
let zeros = x.clz()           // compiles to llvm.ctlz.i32
```

## Phase 1: Type Checker Support

### 1.1 Add Primitive Method Registry

In `type_checker.py`, add a registry of methods available on primitive types:

```python
# After INT_TYPES definition
PRIMITIVE_METHODS = {
    # method_name: (param_types, return_type_fn)
    # return_type_fn takes the receiver type and returns result type
    'rotl': (['u8'], lambda recv: recv),        # Self -> Self
    'rotr': (['u8'], lambda recv: recv),        # Self -> Self
    'clz': ([], lambda recv: 'u8'),             # Self -> u8
    'ctz': ([], lambda recv: 'u8'),             # Self -> u8
    'popcnt': ([], lambda recv: 'u8'),          # Self -> u8
    'swap_bytes': ([], lambda recv: recv),      # Self -> Self
    'reverse_bits': ([], lambda recv: recv),    # Self -> Self
}
```

### 1.2 Update `_check_method_call`

Modify to check for primitive methods before looking up user-defined impls:

```python
def _check_method_call(self, expr: rast.MethodCall) -> rast.Type:
    receiver_type = self._infer_type(expr.expr)
    type_name = self._get_type_name(receiver_type)

    # NEW: Check for primitive intrinsic methods first
    if type_name in self.INT_TYPES and expr.method in self.PRIMITIVE_METHODS:
        param_types, ret_type_fn = self.PRIMITIVE_METHODS[expr.method]
        # Validate argument count
        if len(expr.args) != len(param_types):
            self._error(f"'{expr.method}' expects {len(param_types)} args, got {len(expr.args)}", expr.span)
        # Infer arg types
        for arg in expr.args:
            self._infer_type(arg)
        # Return type
        ret = ret_type_fn(type_name)
        if ret == receiver_type:
            return receiver_type
        return rast.NamedType(expr.span, ret, [])

    # ... existing method lookup logic ...
```

## Phase 2: LLVM Intrinsic Declarations

### 2.1 Add Intrinsic Function Cache

In `emitter_llvmlite.py` `__init__`:

```python
# Bit manipulation intrinsics (declared on-demand)
self.bit_intrinsics = {}  # (intrinsic_name, type) -> ir.Function
```

### 2.2 Intrinsic Declaration Helper

```python
def _get_bit_intrinsic(self, name: str, int_type: ir.Type) -> ir.Function:
    """Get or declare a bit manipulation intrinsic."""
    key = (name, int_type)
    if key in self.bit_intrinsics:
        return self.bit_intrinsics[key]

    # Map Ritz method to LLVM intrinsic
    width = int_type.width
    type_suffix = f"i{width}"

    if name == 'rotl':
        # llvm.fshl.iN(a, a, b) = (a << b) | (a >> (N - b))
        intrinsic_name = f"llvm.fshl.{type_suffix}"
        fn_type = ir.FunctionType(int_type, [int_type, int_type, int_type])
    elif name == 'rotr':
        # llvm.fshr.iN(a, a, b) = (a >> b) | (a << (N - b))
        intrinsic_name = f"llvm.fshr.{type_suffix}"
        fn_type = ir.FunctionType(int_type, [int_type, int_type, int_type])
    elif name == 'clz':
        # llvm.ctlz.iN(x, is_zero_poison) -> iN
        intrinsic_name = f"llvm.ctlz.{type_suffix}"
        fn_type = ir.FunctionType(int_type, [int_type, ir.IntType(1)])
    elif name == 'ctz':
        intrinsic_name = f"llvm.cttz.{type_suffix}"
        fn_type = ir.FunctionType(int_type, [int_type, ir.IntType(1)])
    elif name == 'popcnt':
        intrinsic_name = f"llvm.ctpop.{type_suffix}"
        fn_type = ir.FunctionType(int_type, [int_type])
    elif name == 'swap_bytes':
        intrinsic_name = f"llvm.bswap.{type_suffix}"
        fn_type = ir.FunctionType(int_type, [int_type])
    elif name == 'reverse_bits':
        intrinsic_name = f"llvm.bitreverse.{type_suffix}"
        fn_type = ir.FunctionType(int_type, [int_type])
    else:
        raise ValueError(f"Unknown bit intrinsic: {name}")

    fn = ir.Function(self.module, fn_type, name=intrinsic_name)
    self.bit_intrinsics[key] = fn
    return fn
```

## Phase 3: Method Call Emission

### 3.1 Update `_emit_method_call`

Add early intercept for primitive methods:

```python
def _emit_method_call(self, expr: rast.MethodCall) -> ir.Value:
    # ... existing receiver type detection code ...

    # NEW: Check for primitive intrinsic methods
    if type_name in {'i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64'}:
        intrinsic_methods = {'rotl', 'rotr', 'clz', 'ctz', 'popcnt', 'swap_bytes', 'reverse_bits'}
        if expr.method in intrinsic_methods:
            return self._emit_bit_intrinsic(expr, type_name)

    # ... existing method lookup and emission ...
```

### 3.2 Add Intrinsic Emission Helper

```python
def _emit_bit_intrinsic(self, expr: rast.MethodCall, type_name: str) -> ir.Value:
    """Emit a bit manipulation intrinsic call."""
    # Determine LLVM type
    width = {'i8': 8, 'u8': 8, 'i16': 16, 'u16': 16,
             'i32': 32, 'u32': 32, 'i64': 64, 'u64': 64}[type_name]
    int_type = ir.IntType(width)

    # Emit receiver value
    receiver = self._emit_expr(expr.expr)

    # Get intrinsic function
    intrinsic = self._get_bit_intrinsic(expr.method, int_type)

    if expr.method in ('rotl', 'rotr'):
        # fshl/fshr take (a, a, shift) for rotate
        shift = self._emit_expr(expr.args[0])
        # Shift amount needs to match receiver width
        shift = self.builder.zext(shift, int_type) if shift.type.width < width else shift
        return self.builder.call(intrinsic, [receiver, receiver, shift])

    elif expr.method in ('clz', 'ctz'):
        # ctlz/cttz take (x, is_zero_poison=false)
        # is_zero_poison=false means clz(0) returns bitwidth, not UB
        result = self.builder.call(intrinsic, [receiver, ir.Constant(ir.IntType(1), 0)])
        # Truncate result to u8
        return self.builder.trunc(result, ir.IntType(8))

    elif expr.method == 'popcnt':
        result = self.builder.call(intrinsic, [receiver])
        return self.builder.trunc(result, ir.IntType(8))

    elif expr.method in ('swap_bytes', 'reverse_bits'):
        return self.builder.call(intrinsic, [receiver])

    raise ValueError(f"Unknown bit intrinsic: {expr.method}")
```

## Phase 4: Documentation (ritzlib/ops.ritz)

Create documentation file that describes the trait (even if compiler-implemented):

```ritz
// ritzlib/ops.ritz - Operator and intrinsic traits
//
// The BitOps trait provides bit manipulation methods on integer types.
// These are compiler intrinsics that map directly to efficient CPU instructions.

/// Bit manipulation operations on integer types.
///
/// All integer types (i8, i16, i32, i64, u8, u16, u32, u64) implement BitOps.
/// Methods compile to single CPU instructions where possible.
///
/// Example:
///     let x: u32 = 0xDEADBEEF
///     let rotated = x.rotl(16)    // 0xBEEFDEAD
///     let zeros = x.clz()         // count leading zeros
trait BitOps
    /// Rotate left by n bits
    fn rotl(self, n: u8) -> Self

    /// Rotate right by n bits
    fn rotr(self, n: u8) -> Self

    /// Count leading zeros (0 to bitwidth)
    fn clz(self) -> u8

    /// Count trailing zeros (0 to bitwidth)
    fn ctz(self) -> u8

    /// Population count (number of 1 bits)
    fn popcnt(self) -> u8

    /// Swap byte order (endianness conversion)
    fn swap_bytes(self) -> Self

    /// Reverse all bits
    fn reverse_bits(self) -> Self

// Compiler auto-implements for all integer primitives
```

## Phase 5: Testing

### 5.1 Unit Tests (test/test_bitops.ritz)

```ritz
import ritzlib.sys

@test
fn test_rotl_u32() -> i32
    let x: u32 = 0x12345678
    let r = x.rotl(8)
    assert r == 0x34567812, "rotl(8) failed"
    return 0

@test
fn test_rotr_u32() -> i32
    let x: u32 = 0x12345678
    let r = x.rotr(8)
    assert r == 0x78123456, "rotr(8) failed"
    return 0

@test
fn test_clz_u32() -> i32
    assert (0x80000000 as u32).clz() == 0, "clz high bit"
    assert (0x00000001 as u32).clz() == 31, "clz low bit"
    assert (0x00000000 as u32).clz() == 32, "clz zero"
    return 0

@test
fn test_ctz_u32() -> i32
    assert (0x80000000 as u32).ctz() == 31, "ctz high bit"
    assert (0x00000001 as u32).ctz() == 0, "ctz low bit"
    assert (0x00000000 as u32).ctz() == 32, "ctz zero"
    return 0

@test
fn test_popcnt_u32() -> i32
    assert (0x00000000 as u32).popcnt() == 0, "popcnt zero"
    assert (0xFFFFFFFF as u32).popcnt() == 32, "popcnt all ones"
    assert (0x0F0F0F0F as u32).popcnt() == 16, "popcnt pattern"
    return 0

@test
fn test_swap_bytes_u32() -> i32
    let x: u32 = 0x12345678
    assert x.swap_bytes() == 0x78563412, "swap_bytes"
    return 0

@test
fn test_reverse_bits_u8() -> i32
    let x: u8 = 0b10110001
    assert x.reverse_bits() == 0b10001101, "reverse_bits"
    return 0

// Test different widths
@test
fn test_rotl_u8() -> i32
    let x: u8 = 0x12
    assert x.rotl(4) == 0x21, "rotl u8"
    return 0

@test
fn test_rotl_u64() -> i32
    let x: u64 = 0x123456789ABCDEF0
    let r = x.rotl(32)
    assert r == 0x9ABCDEF012345678, "rotl u64"
    return 0
```

## Implementation Order

1. **Phase 1**: Type checker (method recognition, return types)
2. **Phase 2**: Emitter intrinsic declarations
3. **Phase 3**: Emitter method call interception
4. **Phase 5**: Tests (TDD - write tests first, then verify they pass)
5. **Phase 4**: Documentation (after implementation works)

## Edge Cases

1. **Shift amounts > bitwidth**: LLVM intrinsics handle this (rotate wraps)
2. **Zero input to clz/ctz**: Return bitwidth (we pass `is_zero_poison=false`)
3. **Signed vs unsigned**: Same intrinsics work for both
4. **8-bit swap_bytes**: Returns same value (no-op, but still valid)

## Future Extensions

- `leading_ones()` / `trailing_ones()` - can implement via `(!x).clz()`
- `is_power_of_two()` - `x != 0 && x.popcnt() == 1`
- `next_power_of_two()` - `1 << (bitwidth - (x-1).clz())`

These could be added as additional trait methods or standalone functions.
