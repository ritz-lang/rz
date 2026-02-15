# ritz1 Compiler Roadmap - Path to Self-Hosting

## Current Status (2024-12-25)

✅ **MILESTONE 1: Basic Compiler Working**
- NFA lexer: 100% functional (44 patterns)
- Parser: Working (handles indentation, NEWLINE tokens)
- IR emitter: Basic functionality (return statements)
- Test: `fn main() -> i32 { return 42 }` compiles and runs

## Critical Path to A/B Testing

### Phase 1: Fix Known Blockers (HIGH PRIORITY)

1. **Fix ritz0 Struct Assignment Bug**
   - Issue: `stmt.next` pointer contains garbage
   - Impact: Can only emit first statement
   - Approach: Investigate ritz0 LLVM IR generation
   - Alternative: Work around by manually zeroing memory
   - **BLOCKING**: Multi-statement functions

2. **Fix Negation + Kleene Star Hang**
   - Issue: Pattern `[^"]*` causes infinite loop
   - Impact: No string literal support
   - Approach: Add cycle detection or simplify negation
   - **BLOCKING**: String literal patterns

### Phase 2: Expand IR Emission (MEDIUM PRIORITY)

3. **Multi-Statement Functions**
   - Depends on: Fix #1 (struct bug)
   - Emit multiple statements in function body
   - Test: Functions with 2+ statements

4. **Variable Declarations**
   - Emit `alloca` for local variables
   - Track variable SSA IDs
   - Test: `var x: i32 = 42`

5. **Binary Operators**
   - Emit arithmetic: `+`, `-`, `*`, `/`, `%`
   - Emit comparisons: `==`, `!=`, `<`, `>`, `<=`, `>=`
   - Test: `return a + b`

6. **Function Calls**
   - Emit `call` instructions
   - Handle arguments
   - Test: `return fib(5)`

### Phase 3: Tier 1 Examples (TEST READINESS)

7. **Test fibonacci.ritz**
   - Recursive function calls
   - Arithmetic operators
   - Control flow (if/else)

8. **Test file_io.ritz**
   - System calls
   - String literals (depends on fix #2)
   - Multiple statements

9. **Test struct_example.ritz**
   - Struct definitions
   - Field access
   - Pointer operations

### Phase 4: A/B Test Harness

10. **Create Test Infrastructure**
    - Script: compile same source with ritz0 and ritz1
    - Compare: Generated LLVM IR
    - Verify: Both produce identical output
    - Metrics: Compilation time, IR size

11. **Run A/B Tests**
    - All Tier 1 examples
    - Document differences
    - Fix discrepancies

### Phase 5: Self-Hosting Bootstrap

12. **Compile ritz1 with ritz1**
    - Source: ritz1/src/*.ritz (8 files)
    - Output: ritz1_stage2.ll
    - Verify: ritz1_stage2 matches ritz1_stage1

13. **Verify Stability**
    - Compile ritz1_stage2 → ritz1_stage3
    - Compare: stage2 == stage3 (convergence)

## Estimated Timeline

**Phase 1 (Blockers)**: 1-2 days
- Struct bug is critical, may need deep dive
- Negation hang is well-isolated

**Phase 2 (IR Expansion)**: 2-3 days
- Incremental feature additions
- Well-understood LLVM IR patterns

**Phase 3 (Testing)**: 1 day
- Run existing examples
- Fix edge cases

**Phase 4 (A/B)**: 1 day
- Infrastructure + testing
- Comparison analysis

**Phase 5 (Bootstrap)**: 1 day
- Self-compilation
- Verification

**Total: ~1 week to self-hosting**

## Success Criteria

1. ✅ All Tier 1 examples compile with ritz1
2. ✅ A/B tests show equivalent IR output (ritz0 vs ritz1)
3. ✅ ritz1 compiles itself (bootstrap)
4. ✅ Bootstrap is stable (stage2 == stage3)

## Risk Mitigation

- **Struct bug**: If unfixable in ritz0, implement workaround in ritz1
- **Negation hang**: String literals can use simpler pattern or manual parsing
- **IR differences**: Document and accept if semantically equivalent
- **Bootstrap failure**: Fall back to partial bootstrap (compile subset)
