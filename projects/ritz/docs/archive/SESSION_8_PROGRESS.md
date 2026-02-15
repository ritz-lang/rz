# Session 8: Self-Hosting Bootstrap Investigation

## Status: In Progress

Continuing from Session 7 with focus on completing self-hosting and fixing remaining issues.

## What Works

- ✅ ritz0 (Python) → ritz1 bootstrap (45 KB binary) - fully functional
- ✅ ritz1.prev (bootstrap-compiled) can compile test programs correctly
- ✅ String literal lexer pattern added to ritz_tokens.ritz
- ✅ Bootstrap compiler handles complex programs with variables and string literals

## Current Issues

### Self-Hosted Binary Crash (CRITICAL)

**Problem**: The self-hosted ritz1 binary crashes on ANY input, even minimal programs.

Example:
```ritz
fn main(argc: i32, argv: **u8) -> i32
  return 42
```

Result: `Segmentation fault (core dumped)` when using ./ritz1 to compile

**Bootstrap Version Works**: ritz1.prev (compiled by ritz0) works fine with the same test

**Root Cause (Suspected)**:
The prescan changes to emitter.ritz may have introduced a subtle bug that manifests when:
1. ritz1.prev (which includes prescan code) compiles the modified emitter.ritz
2. The resulting IR (ritz1.ll) is assembled and linked into a binary
3. That binary (./ritz1) is used - it crashes

This suggests a logic error in:
- `prescan_stmt_allocas()` function
- `prescan_fn_allocas()` function
- `ast_lookup_local_ptr()` function
- How prescan interacts with the rest of emit_ast_stmt()

## Investigation Findings

1. **Binary Comparison**:
   - ritz1.prev (bootstrap): 56 KB, works perfectly
   - ritz1 (self-hosted): 35 KB, crashes immediately
   - Both built from same source (prescan-enabled emitter.ritz)

2. **IR Generation**:
   - ritz1.prev generates valid IR: test_minimal_prev.ll (35 lines, compiles fine)
   - ritz1 never generates output (crashes before completion)
   - This happens even for trivial programs with no variables

3. **Scope of Issue**:
   - Not limited to struct field access
   - Not limited to specific statement types
   - Occurs at startup/early in compilation
   - Likely issue in parameter passing or initialization

## Files Modified (This Session)

1. **ritz1/src/ritz_tokens.ritz**:
   - String literal pattern already added: `"[ -!#-~]*"`

2. **ritz1/src/emitter.ritz**:
   - Added prescan functions (from previous session context)
   - Added ast_lookup_local_ptr() function
   - Modified emit_ast_fn() to call prescan before body emission
   - Modified STMT_VAR/STMT_LET handlers to use prescan allocas

3. **ritz1/src/main.ritz**:
   - Updated IRBuilder initialization (from previous session)

## Next Steps

1. **Debug the Crash**:
   - Add diagnostic output to emitter functions
   - Trace execution path of minimal test case
   - Identify exact point of segfault

2. **Fix Prescan Issues**:
   - Review pointer arithmetic in ast_lookup_local_ptr
   - Check boundary conditions in prescan loops
   - Verify ASTLOCAL_SIZE calculations

3. **Alternative Approach**:
   - Consider reverting prescan changes temporarily
   - Test if self-hosting works without prescan
   - Then reimplement prescan with proper testing

4. **Struct Field Access** (Secondary Issue):
   - EXPR_FIELD handler currently hardcodes offset 0
   - Needs proper struct field offset lookup
   - Track struct definitions to resolve field positions

## Test Cases

**Passing**:
- ritz1.prev can compile test_bootstrap.ritz with string literals ✓
- ritz1.prev can compile test_minimal.ritz ✓
- Bootstrap IR assembles and executes correctly ✓

**Failing**:
- ritz1 crashes on test_minimal.ritz ✗
- ritz1 crashes on test_bootstrap.ritz ✗
- No diagnostic output before crash ✗

## Code Review Checklist

- [ ] Verify prescan_stmt_allocas() handles NULL statements
- [ ] Check offset calculations in ast_lookup_local_ptr() line 1010
- [ ] Confirm ASTLOCAL_SIZE definition (should be 32 bytes)
- [ ] Review how prescan variables integrate with emit_ast_stmt()
- [ ] Test prescan with nested if/while blocks
- [ ] Verify boundary checks in prescan loops
- [ ] Check if issue is specific to self-hosted compilation

## Architecture Notes

The prescan approach is sound for LLVM dominance requirements:
- All allocas must dominate their uses
- Pre-scanning ensures allocas are emitted at function entry
- Then statements can be emitted normally

But implementation details matter. Any pointer arithmetic error could cause:
- Reading from wrong memory locations
- Buffer overflow in locals array
- Invalid function calls with bad pointers

## Conclusion

Session 8 started with the string literal fix from previous session (already in place), and is now focused on diagnosing why the self-hosted binary crashes. The bootstrap compiler works perfectly, indicating the source code is valid. The issue is in how the self-hosted binary executes, most likely related to the prescan functionality added in the previous session.

This is a critical blocker for self-hosting. Once resolved, the compiler should be fully self-hosted and capable of compiling itself reliably.
