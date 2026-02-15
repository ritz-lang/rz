# A/B Testing: ritz0 vs ritz1 IR Generation

## Overview

Phase 2.9 introduces an A/B testing approach to validate the ritz1 IR emitter before attempting self-hosting. This ensures IR generation correctness BEFORE we tackle the complex struct layout and offset problems.

## The Two Paths

### Path A: ritz0 (Python + llvmlite)
- **Compiler**: ritz0.py (Python)
- **IR Generation**: llvmlite library (well-tested, production-quality)
- **Status**: ✅ Proven correct on all Tier 1 examples (123 tests passing)
- **Purpose**: Reference implementation / ground truth

### Path B: ritz1 (Ritz + text IR)
- **Compiler**: ritz1 IR emitter compiled by ritz0
- **IR Generation**: ritz1/ir/ir_builder.ritz (text-based)
- **Status**: 🚧 In development, 16 IR builder tests passing
- **Purpose**: Self-hosting target, validates we can generate correct IR in Ritz

## Why A/B Testing?

During previous self-hosting attempts, we encountered:
1. **Struct layout bugs**: Magic byte offsets in emitter.ritz accessing parser AST
2. **Field access errors**: GEP indices wrong due to alignment/padding mismatches
3. **Debugging challenges**: Hard to tell if bugs were in parser, emitter, or both

A/B testing solves this by:
- **Isolating IR generation**: Test ONLY the IR emitter, not the full compiler
- **Incremental validation**: Prove each piece correct before integration
- **Clear failure modes**: Mismatches point directly to IR generation bugs
- **Confidence building**: Validate approach before committing to self-hosting

## Test Harness: tools/ab_test.py

### Usage

```bash
# Test a single file
python3 tools/ab_test.py examples/01_hello/src/main.ritz

# Test multiple files
python3 tools/ab_test.py examples/*/src/main.ritz

# Test all Tier 1 examples
python3 tools/ab_test.py examples/0*/src/*.ritz
```

### What It Tests

1. **IR Structure**: Normalize and compare LLVM IR from both paths
   - Strip SSA IDs (%1, %2 → %VAL)
   - Strip label IDs (L1, L2 → LABEL)
   - Strip string IDs (@.str.0 → @.str.N)
   - Compare line-by-line structure

2. **Binary Behavior**: Compile both IRs and compare execution
   - Exit codes must match
   - Stdout must match
   - Stderr must match

### Example Output

```
======================================================================
A/B Testing: main.ritz
======================================================================

Path A: ritz0 (llvmlite)
✓ Generated 734 bytes of IR

Path B: ritz1 IR emitter (text)
✓ Generated 741 bytes of IR

Comparing IR structure...
✓ IR structures match

Compiling to binaries...
✓ Path A binary compiled
✓ Path B binary compiled

Running binaries...
  Path A: exit=0, stdout=13 bytes, stderr=0 bytes
  Path B: exit=0, stdout=13 bytes, stderr=0 bytes
✓ Binary behavior matches (exit=0)

======================================================================
✓ A/B test PASSED for main.ritz
======================================================================
```

## IR Builder Components (ritz1/ir/)

### ir_builder.ritz (575 lines)

Core IR text generation:
- `IRBuffer`: Growable string buffer
- `IRBuilder`: Stateful IR generator with SSA tracking
- Type emission: All primitive types (i8-i64, u8-u64, ptr, void, bool)
- Module: headers, footers, target triple
- Functions: definitions, parameters, basic blocks
- Instructions: alloca, load, store, binop, icmp, br, call, ret, gep
- Structs: type definitions, field access
- Strings: constants with proper escaping

**Tests**: 16 passing (test_ir_builder.ritz)

### simple_codegen.ritz (100 lines)

Minimal code generator for initial A/B testing:
- `SimpleFunction`: Representation for basic functions
- `codegen_simple_function()`: Generate function IR
- `codegen_simple_module()`: Complete module with _start
- Inline assembly for syscalls

**Tests**: 1 passing (validates "fn main() -> i32 { return 42 }")

## Current Status

### Phase 2.9A: ✅ COMPLETE
- [x] IR builder infrastructure (575 lines, 16 tests)
- [x] Simple code generator (100 lines, 1 test)
- [x] A/B test harness (Python)
- [x] Path A validated on all examples

### Phase 2.9B: 🚧 NEXT
- [ ] Struct layout algorithm (alignment, padding, size)
- [ ] Field offset computation
- [ ] A/B test struct-heavy examples (10_sleep, test_level12.ritz)

### Phase 2.9C-G: ⏳ PLANNED
- Expression IR generation
- Statement IR generation
- Function IR generation
- Full program IR generation
- All Tier 1 examples compile identically

## Integration with ritz1

Once A/B testing proves the IR emitter correct:

1. **Replace emitter.ritz**: Drop magic offset code, use ir_builder.ritz
2. **Add struct layout**: Compute offsets at compile time (no magic numbers)
3. **Full bootstrap**: ritz0 → ritz1 → ritz1_self with identical output

## Key Insights

### What We Learned

1. **Text IR is sufficient**: Don't need llvmlite for self-hosting
2. **Test infrastructure matters**: A/B testing prevents regressions
3. **Incremental wins**: Prove each piece correct before integration
4. **Separation of concerns**: IR generation independent of parsing

### What's Next

The struct layout problem (Phase 2.9B) is the critical piece:
- Must match LLVM's layout algorithm exactly
- Alignment rules: each field aligned to natural alignment
- Padding: inserted between fields as needed
- Struct size: rounded up to largest field alignment
- GEP indices: based on computed offsets

Once struct layout works, the rest is straightforward IR emission.

## References

- **IR Builder Tests**: ritz1/ir/test_ir_builder.ritz
- **Simple Codegen Test**: ritz1/ir/simple_codegen.ritz (test at bottom)
- **A/B Harness**: tools/ab_test.py
- **LLVM IR Spec**: https://llvm.org/docs/LangRef.html
- **Struct Layout Rules**: https://llvm.org/docs/LangRef.html#structure-type

---

**Last Updated**: 2024-12-24
**Status**: Phase 2.9A complete, ready for 2.9B (struct layout)
