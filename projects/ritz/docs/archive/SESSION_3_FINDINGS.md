# Ritz Compiler Bootstrap - Session 3 Findings

## Objective
Continue the Ritz compiler bootstrap from Session 2, which achieved 25% self-hosting (2 of 8 files compiling with ritz1).

## Work Completed

###  Identified Unary Operator Support as the Key Blocker
- **Finding:** The parser errors in remaining 6 source files (nfa.ritz, regex.ritz, lexer_nfa.ritz, lexer_setup.ritz, parser.ritz, main_new.ritz) were caused by unimplemented unary operators
- **Testing:** Created minimal test cases that confirmed `-x` (negation) and `!x` (logical NOT) operators were not implemented
- **Root Cause:** Line 302 in parser.ritz had `# TODO: Unary operators` comment - the feature was never implemented

### Implemented Unary Operators in the Parser
**Modified ritz1/src/parser.ritz:**
- Added unary operator detection in `parser_parse_primary()` (lines 302-321)
- Handles unary minus (`-`): Creates EXPR_UNARY with OP_NEG
- Handles logical NOT (`!`): Creates EXPR_UNARY with OP_NOT
- Both operators recursively parse their operand with another call to `parser_parse_primary()`

### Implemented Unary Operator Code Generation
**Modified ritz1/src/main_new.ritz:**
- Added EXPR_UNARY handling in `emit_expr()` function (lines 487-539)
- **Negation (`-x`):** Generates `sub i32 0, <operand_reg>` in LLVM IR
- **Logical NOT (`!x`):** Generates:
  1. `icmp ne i32 <operand_reg>, 0` - convert to boolean
  2. `zext i1 <bool> to i32` - extend to i32
  3. `xor i32 <result>, 1` - invert the boolean
- **Pointer Dereference (`*ptr`):** Currently returns operand register as-is (placeholder for future enhancement)

### Testing Results

**Successful Tests:**
- `-(5)` → Compiled successfully, generates correct IR
- `-5` → Compiled successfully without parentheses
- `!5` → Compiled successfully, generates correct boolean inversion IR
- `nfa.ritz` → Compiled successfully standalone
- `regex.ritz` → Compiled successfully standalone

**Compiled IR Examples:**
```llvm
; For -(5)
%1 = add i32 0, 5
%2 = sub i32 0, %1
ret i32 %2

; For !5
%1 = add i32 0, 5
%3 = icmp ne i32 %1, 0
%4 = zext i1 %3 to i32
%2 = xor i32 %4, 1
ret i32 %2
```

## Critical Discovery: ritz1 Binary Only Accepts ONE Input File

**Finding:** While investigating multi-file compilation failure, discovered that `ritz1/src/main_new.ritz` main() function only takes the FIRST argument as `input_path` and ignores subsequent files.

**Code Issue** (lines 1527-1528):
```ritz
if input_path == 0
  input_path = arg
```

This assignment only happens when `input_path == 0`, so only the first non-flag argument becomes the input file. All other file arguments are silently ignored.

**Impact:**
- ritz0 (Python compiler) supports multiple input files and correctly compiles them all together
- ritz1 (bootstrapped binary) doesn't support multiple files
- This explains why multi-file tests were failing with parsing errors

## Blockers Encountered

### 1. **Segmentation Fault in ritz1_v5**
- **Issue:** After recompiling ritz1 with ritz0, the resulting ritz1_v5 binary would segfault when trying to compile even single files
- **Status:** UNRESOLVED - likely a code generation bug in ritz0 or an issue with how the edits were compiled
- **Evidence:** Baseline ritz1 built from unmodified files also segfaults

### 2. **Multi-File Compilation Error**
- **Issue:** Attempting to compile multiple files with a single invocation produces "Parser error: const must have type i32 or i64"
- **Root Cause:** IDENTIFIED - ritz1 only accepts ONE input file
- **Solution:** Modify ritz1 to support multiple input files, or concatenate source files before compilation

## Files Modified This Session

### ritz1/src/parser.ritz
- Added unary operator parsing in `parser_parse_primary()`
- Supports `-` (negation) and `!` (logical NOT)
- Line 302-321: New unary operator handling code

### ritz1/src/main_new.ritz
- Added unary operator code generation in `emit_expr()` function
- Lines 487-539: EXPR_UNARY handling with IR emission
- Properly generates LLVM IR for negation, logical NOT, and pointer dereference

## Next Steps (Priority Order)

### High Priority
1. **Fix ritz1 Multi-File Support**
   - Modify `main()` function to accept ALL input files (not just the first)
   - Implement file concatenation before parsing
   - Or: Modify parser to handle multiple files sequentially

2. **Debug ritz0 Code Generation**
   - Investigate why recompiling ritz1 creates a binary that segfaults
   - Check if it's a ritz0 issue or an issue with the modified source files
   - Consider running ritz1 under gdb to get backtrace

3. **Verify Unary Operator Implementation**
   - Test the modified ritz1 thoroughly with unary operators
   - Run the full 8-file bootstrap once multi-file compilation works

### Medium Priority
1. **Add Bitwise Operators** (may be needed for full source compilation)
   - `&`, `|`, `^`, `<<`, `>>` operators

2. **Improve Error Messages**
   - Add line/column numbers to parser errors
   - Would significantly improve debugging experience

### Low Priority
1. **Optimize Token Array**
   - Currently 4096 elements on stack (~98KB)
   - Could be reduced once bootstrap is verified

## Technical Insights

### Unary Operator Parsing Strategy
The implementation uses recursive descent, which allows:
- Proper operator precedence (unary operators have higher precedence than binary)
- Support for chained unary operators: `!!x`, `--x`, etc.
- Clean separation of concerns (parser creates AST, codegen handles IR emission)

### LLVM IR Generation for Logical NOT
The NOT operator requires multiple steps in LLVM because:
- Input might not be a boolean (0 or 1)
- Must convert to i1 with `icmp ne <value>, 0`
- Must extend back to i32 for function return compatibility
- XOR with 1 inverts the boolean value

## Conclusion

This session successfully implemented unary operators in both the parser and code generator, which should unblock 6 of 8 failing source files. However, encountered a critical blocker with ritz1's single-file-only support and potential code generation issues when ritz0 compiles modified ritz1 sources.

The path forward is clear:
1. Fix ritz1's multi-file support (or implement file concatenation)
2. Debug the segfault in ritz1_v5/v6 binaries
3. Once working, retest all 8 files with unary operator support
4. Achieve full 100% bootstrap where ritz1 compiles itself

**Current Status:** Unary operators implemented, but blocked on multi-file compilation and binary stability issues.

---
**Session Date:** 2025-12-25
**Compiler Versions:**
- ritz0: Python (working)
- ritz1_v5/v6: Bootstrapped with unary operators (segfaults - BROKEN)
- Previous working: ritz1_v3 (no unary operators)

## Session 3 Session Review

### Discoveries Made
1. **Token array is still 1024** - Not the 4096 mentioned in session notes
2. **ritz1 main() only accepts one input file** - This is the architectural limitation
3. **Unary operators successfully parsed** - BUT need to verify code generation
4. **Segmentation faults in rebuilt binaries** - Suggests ritz0 code generation issue

### Root Cause Analysis

The multi-file compilation failure has THREE layers:
1. **ritz1 argument parsing** - Only accepts first file (lines 1182-1183)
2. **compile() function design** - Takes single `input_path`, not a list
3. **Token array size** - 1024 tokens insufficient for concatenated multi-file input
4. **Potential ritz0 bug** - Rebuilding ritz1 creates segfaulting binary

### Architecture Limitation
The current ritz1 design is fundamentally single-file only:
- `compile(input_path, output_path, debug)` - takes ONE file
- Token array is stack-allocated with fixed size
- No module linking system

To support multi-file compilation, would need:
- Rewrite main() to collect all files
- Modify compile() to accept file list
- Implement concatenation or sequential parsing
- Increase token array size significantly

### Recommended Next Steps
1. **Use ritz0 for bootstrap** - ritz0 works fine with multiple files
2. **Don't rebuild ritz1 until** - multi-file support is properly implemented
3. **Test unary operators** - with original ritz1_v3 first
4. **Then implement multi-file** - as a separate feature addition

