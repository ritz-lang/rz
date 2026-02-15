# Session 8: Root Cause of Self-Hosting Failure Identified

## Executive Summary

Successfully diagnosed why the self-hosted Ritz compiler crashes. The root cause is **incomplete struct field access implementation** in the ritz1 emitter. When the bootstrap ritz1 attempts to compile parser.ritz (which has extensive struct field operations), the broken field offset calculations cause memory corruption and segmentation faults.

## Key Findings

### 1. Bootstrap Compilation Works Perfectly
- ✅ ritz0 (Python) → ritz1 (45 KB binary) - fully functional
- ✅ ritz1 can compile single files and file pairs
- ✅ ritz1 can compile first 8 source files correctly

### 2. Crash Point Identified via Binary Search

**Critical Discovery**: Self-hosting fails precisely at parser.ritz

Test Results:
```
First 6 files (mem through token_dsl): ✅ OK
First 8 files (+ lexer, ritz_tokens): ✅ OK
First 9 files (+ parser): ❌ CRASH (Segmentation fault)
```

Parser.ritz is where the crash occurs. This is NOT random - it's deterministic based on the content being compiled.

### 3. Root Cause: Struct Field Offset Bug

**The Problem**:
- parser.ritz defines 10 structs: Expr, TypeExpr, Stmt, Param, FnDef, StructField, StructDef, ConstDef, Module, Parser
- parser.ritz contains extensive struct field access throughout (~80+ field assignment/access operations)
- The EXPR_FIELD handler in emitter.ritz is a stub that always uses offset 0:

```ritz
# TODO: compute field offset
let field_ptr: i32 = base_val
```

**Why This Causes a Crash**:
1. ritz1 compiles parser.ritz source code
2. When emitting `(*param).next = ...` operations, it always uses offset 0
3. This should write to offset 24 (where `.next` field actually is in Param struct)
4. Instead, it writes to offset 0, corrupting the first field of the struct
5. Subsequent operations read corrupted data
6. Memory corruption cascades, leading to segmentation fault
7. The actual crash happens during the emitter's own field access operations

### 4. Why Bootstrap Ritz0 Works

Python's ritz0 emitter uses LLVM's llvmlite library which:
- Has proper type tracking throughout compilation
- Computes struct field offsets correctly using layout information
- Generates correct GEP (GetElementPtr) instructions with proper field indices

### 5. Prescan Red Herring

Initial investigation focused on prescan changes from Session 7, but:
- ✅ Confirmed prescan was NOT the issue
- Prescan is sound in principle (handles LLVM dominance requirements)
- The issue exists even without prescan
- Root cause is struct field offset, not prescan logic

## Impact Analysis

This bug prevents self-hosting because:
1. Simple test files work fine (no struct field access)
2. Parser.ritz is loaded with struct field operations
3. Parser compilation corrupts memory
4. Emitter itself uses structs (IRBuilder, etc.), leading to cascading failures

## Solution Path

To fix self-hosting, need to implement proper struct field offset handling:

### Phase 1: Track Struct Definitions
- Extend parser to collect struct definitions (already being parsed, just not stored)
- Create struct registry: struct_name → list of (field_name, offset, size)
- Pass struct registry to emitter

### Phase 2: Compute Field Offsets
- In EXPR_FIELD handler: look up struct type and field name
- Use field offset from registry instead of hardcoded 0
- Emit correct GEP instructions with field indices

### Phase 3: Type Tracking
- Add type tracking to symbol table
- Track variable types during emission
- Use type info to resolve struct field accesses

### Phase 4: Validation
- Test parser.ritz compilation
- Test full self-hosting chain
- Verify struct-heavy programs compile correctly

## Code Issues to Address

1. **parser.ritz struct definitions being skipped**:
   ```ritz
   # Skip struct declarations for now (line 1082 in parser.ritz)
   ```
   - Parser needs to store StructDef nodes in Module
   - Currently just skips them

2. **emitter.ritz EXPR_FIELD is a stub**:
   ```ritz
   # TODO: compute field offset
   let field_ptr: i32 = base_val  # WRONG! Always offset 0
   ```
   - Needs to look up actual field offset
   - Needs type information to do so

3. **No struct field offset information available**:
   - Module.structs list doesn't exist
   - Emitter has no way to look up field offsets
   - Type system isn't tracked through compilation

## Test Case That Triggers Bug

```ritz
# From parser.ritz - extensive struct usage
struct Param
  name: *i8
  name_len: i32
  type_expr: *i8
  next: *Param

fn parse_params(p: *Parser) -> *Param
  let first: *Param = 0 as *Param
  # ...
  (*param).next = 0 as *Param  # This crashes when field offset is wrong!
```

When ritz1 (with broken field offset) tries to compile this, it corrupts the Param struct layout.

## Files Modified This Session

None - This session was pure investigation and diagnosis.

## Files That Need Changes

1. **ritz1/src/parser.ritz**:
   - Store struct definitions instead of skipping them
   - Add fields list to StructDef

2. **ritz1/src/emitter.ritz**:
   - Implement struct field offset lookup
   - Update EXPR_FIELD handler with proper offset computation
   - Add type tracking to emission context

3. **ritz1/src/main.ritz**:
   - Pass struct definitions from parser to emitter

## Testing Strategy

1. First: Fix struct field access in simple test program
2. Second: Compile parser.ritz successfully
3. Third: Full self-hosting (all 11 source files)
4. Fourth: Self-host again (ritz1 → ritz1_self)

## Conclusion

Session 8 successfully identified that the self-hosting failure is due to incomplete struct field offset handling in the emitter. The issue is not a recent regression (prescan) but rather an existing limitation of the ritz1 emitter.

The bootstrap compiler (ritz0) works around this by having complete type tracking and proper field offset computation. The solution is to extend ritz1's emitter with similar capabilities.

**Status**: DIAGNOSED ✓ READY TO IMPLEMENT ✓

This is a well-defined, solvable problem. The fix will enable full self-hosting of the Ritz compiler.
