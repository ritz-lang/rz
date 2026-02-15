# Parser Implementation Status

**Session**: Phase 3 Parser Implementation
**Date**: 2025 (Continuation)
**Status**: Foundation Laid, Technical Challenges Identified

---

## Summary

Started implementation of the Phase 3 self-hosted parser in Ritz. The parser skeleton has been created with core structures and functions, but identified key language limitations that affect full implementation.

**Test Status**:
- ✅ `test_parser_minimal.ritz`: 3/3 tests passing (AST structure tests)
- ❌ `test_parser_functions.ritz`: 0/3 tests passing (parser + lexer integration tests - blocked on allocation issues)
- ✅ All Phase 1/2 tests: 157/157 tests passing (no regression)

---

## What Was Accomplished

### 1. Parser Skeleton Created
**File**: `ritz1/src/parser.ritz` (488 lines)

Implemented:
- AST node kind constants (expressions, statements, definitions)
- AST structure definitions:
  - `struct Expr` - Expression nodes with kind and operands
  - `struct Stmt` - Statement nodes
  - `struct FnDef` - Function definition nodes
  - `struct Module` - Module/program structure
- Parser state management:
  - `parser_init()` - Initialize parser from lexer
  - `parser_current()` - Get current token
  - `parser_advance()` - Consume next token
  - `parser_at()` - Check current token type
- Operator precedence system:
  - `get_infix_precedence()` - Get precedence for binary operators
  - `get_prefix_precedence()` - Get precedence for unary operators
  - Full operator precedence table (1-10 levels)
- Expression parsing (Pratt algorithm):
  - `parse_primary()` - Parse atoms (literals, identifiers, parens, unary ops)
  - `parse_expr()` - Pratt precedence climbing algorithm
  - Binary operator handling
  - Unary operator handling
  - Function calls, array indexing, field access (postfix operators)
- Statement parsing:
  - `parse_stmt()` - Parse individual statements
  - Variable declarations (`var x: i32 = 5`)
  - Let bindings (`let x = 5`)
  - Return statements
  - Block statements
  - Expression statements
  - If/while/for/break/continue (stubs)
- Definition parsing:
  - `parse_fn_def()` - Parse function definitions
  - Parameter and return type parsing (stubs)
  - Module parsing

### 2. AST Structure Tests Created
**File**: `ritz1/test/test_parser_minimal.ritz` (76 lines)

Tests verify:
- ✅ Expression structure allocation and initialization
- ✅ Binary operation structure
- ✅ Unary operation structure
- ✅ Statement structure allocation
- ✅ All statement kinds can be created

**Result**: 3/3 tests passing ✅

### 3. Parser Function Tests Created
**File**: `ritz1/test/test_parser_functions.ritz` (245 lines)

Tests designed for:
- Parsing simple integer literals
- Parsing addition with multiplication (precedence test)
- Parsing unary minus operators

**Status**: Blocked on Ritz language limitations (see below)

### 4. Type System Updates
- Changed `Expr` and `Stmt` to use `*i32` pointers instead of typed pointers
- This avoids self-referential struct issues
- Requires runtime casting (type-unsafe but necessary workaround)

---

## Technical Challenges Encountered

### Challenge 1: Self-Referential Structs
**Problem**: The original design had `struct Expr` with fields like `left: *Expr`, creating a forward reference to itself.

**Solution**: Changed to use void pointers (`*i32`) to break the circularity. All child references are stored as `*i32` and cast as needed.

**Impact**: Type safety reduced, but language limitation forces this approach.

### Challenge 2: Dynamic Allocation and Casting
**Problem**: Using `__builtin_alloca()` returns `*i8`, but Ritz doesn't support casting to typed struct pointers and assigning through them:
```ritz
let expr: *Expr = __builtin_alloca(256)  # Allocation
(*expr).kind = EXPR_INT_LIT              # ERROR: Cannot assign field on non-struct pointer
```

**Root Cause**: Ritz's type system treats allocated memory as raw bytes, not structured. Without proper generic/void pointer support in expressions, can't assign through them.

**Current Workaround**: Use stack-allocated structs with `var expr: Expr = Expr { ... }` instead of dynamic allocation. Works for tests but limits parser design.

**Impact**:
- Parser functions can't dynamically allocate expression nodes
- Must use stack allocation or array-based storage
- Limits parser flexibility

### Challenge 3: Operator Precedence Verification
Tests can't easily verify AST structure because of allocation limitations above.

---

## What Still Needs to Be Done

### Immediate Next Steps

1. **Fix Allocation Pattern**
   - Option A: Implement array-based AST storage (allocate array once, use indices)
   - Option B: Use stack-allocated temporary structs during parsing, then serialize
   - Option C: Wait for better generic/void pointer support in Ritz emitter

2. **Complete Parser Function Tests**
   Once allocation issue resolved:
   - test_parse_simple_integer ← simple case
   - test_parse_addition_precedence ← operator precedence
   - test_parse_unary_minus ← unary operators
   - Add tests for function/struct parsing

3. **Implement Remaining Statement Parsing**
   - If statements
   - While loops
   - For loops
   - Match statements
   - Block statements with multiple statements

4. **Implement Definition Parsing**
   - Full function definition parsing
   - Parameter lists with types
   - Struct definitions with fields
   - Module-level organization

5. **Error Handling**
   - Add proper error messages
   - Handle unexpected tokens gracefully
   - Provide helpful error locations

### Medium-term Goals

6. **Integration Testing**
   - Parser + Lexer together
   - Test real Ritz source code
   - Verify AST structure matches emitter expectations

7. **Optimization**
   - Memoization for lookahead
   - Efficient token storage
   - Memory management for large programs

### Long-term (After Parser)

8. **Emitter Implementation**
   - LLVM IR generation for parsed AST
   - Type checking
   - Code generation

9. **Bootstrap**
   - Get ritz0 → ritz1.ll
   - Get ritz1.ll → ritz1 binary
   - Get ritz1 → ritz1 (self-hosting!)

---

## Technical Design Notes

### AST Representation

Current approach uses union-like structs where different node kinds use different fields:

```ritz
struct Expr
  kind: i32          # EXPR_INT_LIT, EXPR_BIN_OP, etc.
  val1: i32          # For literals: the value; For ident: position
  val2: i32          # For binary ops: operator token type
  left: *i32         # Left operand (cast to Expr as needed)
  right: *i32        # Right operand
  next: *i32         # Next in list (for arguments, chains)
```

Interpretation depends on `kind` field.

### Parser Flow

1. **Initialization**: Create lexer, initialize parser with first token
2. **Main parsing**: `parse_module()` → calls `parse_fn_def()` or other items
3. **Expression parsing**: Pratt algorithm with precedence climbing
4. **Statement parsing**: Pattern matching on current token type
5. **Recovery**: Currently panics on errors; should implement recovery

### Memory Management

Current challenge: How to allocate AST nodes?

Options:
1. **Array-based**: Pre-allocate large array, use indices
2. **Stack-based**: Allocate on stack, copy to storage
3. **Arena allocator**: Custom allocator for parser

Need to decide based on Ritz capabilities and parser size expectations.

---

## Ritz Language Limitations Exposed

1. **No proper void/generic pointers**: Can't cast `*i8` to struct types in expressions
2. **No self-referential struct support** (workaround: use void pointers)
3. **Limited dynamic allocation patterns**: `alloca` doesn't work well with typed pointers
4. **No implicit type conversions**: Pointer casts very rigid
5. **No union types**: Must use tagged structs with kind field

These limitations forced design compromises. Future Ritz compiler should address these to make AST-based compiler implementation more ergonomic.

---

## Comparison with ritz0 Parser

**ritz0** (Python):
- Uses native Python classes and dataclasses
- Simple recursive descent
- ~600 lines, clean code
- Flexible memory management

**ritz1** (Ritz):
- Must use struct union pattern
- Same recursive descent approach
- ~500 lines but more constrained
- Must work around allocation limitations

The Ritz parser will accomplish the same thing but with more friction due to the language limitations above.

---

## Files Modified/Created This Session

### Created
- `ritz1/src/parser.ritz` - Main parser implementation (488 lines)
- `ritz1/test/test_parser_minimal.ritz` - AST structure tests (76 lines, 3/3 passing)
- `ritz1/test/test_parser_functions.ritz` - Parser function tests (245 lines, blocked)
- `PARSER_IMPLEMENTATION_STATUS.md` - This file

### Existing (Unchanged)
- All Phase 1/2 tests (157/157 still passing)
- Lexer, NFA, Regex, Token infrastructure

---

## Recommendations

### For Next Session

1. **Decision on Allocation Strategy**
   - Decide between array-based, stack-based, or arena allocation
   - Implement chosen strategy
   - Update parser functions accordingly

2. **Get First Parser Test Passing**
   - Get `test_parse_simple_integer` working
   - Then progressively add more complex tests
   - Use simple source code first (single tokens, then expressions)

3. **Parallel Testing**
   - Create a simple Ritz program that uses the parser
   - Test with real code as early as possible
   - Don't wait for 100% completion

### For Overall Project

1. **Keep Phase 1/2 Intact**
   - All current tests passing: 157/157
   - Don't optimize prematurely
   - Focus only on parser completion

2. **Timeline**:
   - Parser: 2-3 more days
   - Emitter: 3-4 days after parser
   - Bootstrap: 1-2 days after emitter
   - **Total to self-hosting: ~8-10 days**

3. **Success Metrics**:
   - All parser tests passing
   - Parses real Ritz source code
   - AST structure matches emitter expectations
   - Ready to hand off to emitter team

---

## Conclusion

The parser foundation is solid - the structures and algorithms are in place. The remaining work is primarily about working around Ritz language limitations to implement the allocation and type system aspects. Once those are resolved, the parser will be straightforward to complete.

**Status**: Ready to continue; next decision point is allocation strategy.

---

**Last Updated**: 2025
**Session**: Phase 3 Parser (In Progress)
**Time Spent**: ~2-3 hours
**Next Milestone**: First working parser test
