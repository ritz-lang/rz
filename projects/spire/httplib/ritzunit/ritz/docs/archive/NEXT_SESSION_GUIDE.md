# Next Session Guide: Parser Implementation

**Prepared for**: Session 3 (Parser Implementation)
**Status**: Ready to begin
**Duration Estimate**: 3-4 days of focused work
**Blocker Status**: None - all prerequisites complete

---

## Quick Start

### Current State
- ✅ Lexer: Complete and tested (6/6 tests)
- ✅ NFA Engine: Complete and tested (12/12 tests)
- ✅ Bootstrap compiler (ritz0): Stable and working
- ⏳ Parser: Ready to implement
- ⏳ Emitter: Blocked on parser
- ⏳ Bootstrap: Blocked on emitter

### What You'll Do This Session
1. Design parser test suite (2-3 hours)
2. Implement recursive descent parser in Ritz (6-8 hours)
3. Incrementally test and verify (4-6 hours)
4. Documentation and polish (1-2 hours)

### Success Criteria
- ✅ All parser tests passing
- ✅ Handles expressions, statements, functions
- ✅ Clean recursive descent implementation
- ✅ Ready to hand off to emitter implementation

---

## Reference Material

### Files to Review First
1. **ritz0/parser.py** - Python reference implementation
   - Line 1-100: Lexer integration, token stream
   - Line 100-200: Parser initialization, precedence
   - Line 200-500: Expression parsing (Pratt parsing)
   - Line 500-800: Statement parsing
   - Line 800-1000: Function/struct definitions

2. **CURRENT_STATUS.md** - Current project status
   - See "Phase 3" section for context
   - See "Critical Path" for timeline

3. **PHASE_3_LEXER_ANALYSIS.md** - Decision framework
   - Explains why manual lexer chosen over DSL
   - Shows critical path thinking

### Documentation
- `docs/DESIGN.md` - Language design and syntax
- `docs/BOOTSTRAP.md` - Bootstrap strategy overview
- `ritz1/test/test_lexer.ritz` - How lexer tests are structured

---

## Architecture Decision

### Parser Structure (Recursive Descent + Pratt)
```ritz
# Main entry point
fn parse_module(lex: *Lexer) -> Module

# Expression parsing (Pratt algorithm)
fn parse_expr(lex: *Lexer, min_prec: i32) -> Expr
fn parse_primary(lex: *Lexer) -> Expr
fn parse_infix(lex: *Lexer, left: Expr, op: i32) -> Expr

# Statement parsing
fn parse_stmt(lex: *Lexer) -> Stmt
fn parse_if_stmt(lex: *Lexer) -> Stmt
fn parse_while_stmt(lex: *Lexer) -> Stmt
fn parse_fn_def(lex: *Lexer) -> FnDef

# AST nodes
struct Expr
  kind: i32  # BIN_OP, CALL, etc.
  ...

struct Stmt
  kind: i32  # VAR, LET, EXPR, etc.
  ...

struct Module
  fns: *FnDef
  structs: *StructDef
  count: i32
```

### Why Recursive Descent + Pratt
- Simple to understand and implement
- Proven to work (ritz0 uses it)
- Handles operator precedence naturally
- Easy to translate to Ritz from Python

---

## Implementation Stages

### Stage 1: Parser Skeleton & Tests (2 hours)
**Goal**: Set up test infrastructure

**Create**: `ritz1/test/test_parser.ritz`
```ritz
@test
fn test_parse_integer() -> i32
  # Create lexer with source "42"
  # Parse one expression
  # Verify it's an INT_LITERAL with value 42
  0

@test
fn test_parse_addition() -> i32
  # Parse "1 + 2"
  # Verify it's BIN_OP with left=1, op=PLUS, right=2
  0

@test
fn test_parse_function() -> i32
  # Parse "fn add(a: i32, b: i32) -> i32  a + b"
  # Verify FnDef structure
  0

# ... more tests covering:
# - Expression precedence
# - If/while statements
# - Variable declarations
# - Function definitions
# - Struct definitions
```

**Create**: `ritz1/src/parser.ritz` (stub)
```ritz
fn parse_module(lex: *Lexer) -> Module
  # TODO
  0

fn parse_expr(lex: *Lexer, min_prec: i32) -> Expr
  # TODO
  0
```

### Stage 2: Primary Expression Parsing (3 hours)
**Goal**: Parse atoms - literals, identifiers, parenthesized expressions

**Implement**:
- Integer literals (42, 0x10, 0b101)
- String literals ("hello")
- Identifiers (x, foo)
- Boolean literals (true, false)
- Parenthesized expressions ((1 + 2))

**Test targets**:
- test_parse_integer
- test_parse_identifier
- test_parse_string
- test_parse_paren_expr

### Stage 3: Binary Operators (3 hours)
**Goal**: Handle operator precedence with Pratt parsing

**Precedence levels** (from ritz0/parser.py):
```
Level 0 (lowest): Assignment (=)
Level 1: Logical OR (||)
Level 2: Logical AND (&&)
Level 3: Equality (==, !=)
Level 4: Comparison (<, >, <=, >=)
Level 5: Bitwise OR (|)
Level 6: Bitwise XOR (^)
Level 7: Bitwise AND (&)
Level 8: Addition (+, -)
Level 9: Multiplication (*, /, %)
Level 10: Unary (!, -, *)
```

**Implement**:
- `get_infix_precedence(op)` - lookup precedence
- `parse_expr(min_prec)` - Pratt algorithm
- Binary operator handling

**Test targets**:
- test_parse_addition
- test_parse_precedence
- test_parse_comparison

### Stage 4: Unary Operators & Function Calls (2 hours)
**Goal**: Prefix operators and postfix call syntax

**Implement**:
- Unary operators (-, !, *, &)
- Function calls (f(a, b, c))
- Array indexing (arr[i])
- Field access (obj.field)

**Test targets**:
- test_parse_unary_minus
- test_parse_deref
- test_parse_function_call
- test_parse_array_index

### Stage 5: Statements (3 hours)
**Goal**: Parse statements (not expressions)

**Implement**:
- Variable declarations (var x: i32 = 5)
- Let bindings (let x = 5)
- If statements (if cond { ... } else { ... })
- While loops (while cond { ... })
- Expression statements (x = 5)
- Return statements (return x)
- Block statements ({ ... })

**Test targets**:
- test_parse_var_decl
- test_parse_if_stmt
- test_parse_while_loop
- test_parse_return

### Stage 6: Definitions (2 hours)
**Goal**: Parse function and struct definitions

**Implement**:
- Function definitions (fn name(params) -> type { body })
- Parameter parsing (name: type)
- Struct definitions (struct Name { field: type })
- Module-level statements

**Test targets**:
- test_parse_function_def
- test_parse_function_params
- test_parse_struct_def
- test_parse_module

### Stage 7: Integration & Polish (1 hour)
**Goal**: Clean up, optimize, document

- Remove debug code
- Add error messages
- Document complex sections
- Verify all tests pass

---

## Testing Strategy

### Test Organization
```
ritz1/test/test_parser.ritz (single file, ~500 lines)
├─ Expression tests (50 tests)
│  ├─ Literals
│  ├─ Operators
│  └─ Precedence
├─ Statement tests (30 tests)
│  ├─ Variable declarations
│  ├─ Control flow
│  └─ Return statements
├─ Definition tests (20 tests)
│  ├─ Functions
│  ├─ Structs
│  └─ Modules
└─ Error cases (10 tests)
```

### Test Pattern
```ritz
@test
fn test_parse_FEATURE() -> i32
  # 1. Create lexer with test input
  let src: *i8 = "test source code"
  var lex: Lexer = lexer_new(src, strlen(src))

  # 2. Parse
  let expr: Expr = parse_expr(&lex, 0)

  # 3. Verify
  assert expr.kind == EXPECTED_KIND
  assert expr.value == EXPECTED_VALUE

  # 4. Return 0 for success
  0
```

### Running Tests
```bash
# Test parser while developing
make test-ritz1-parser

# Quick check
python ritz0/ritz0.py --test ritz1/src/parser.ritz ritz1/test/test_parser.ritz

# With library dependencies
python ritz0/ritz0.py --test ritz1/src/*.ritz ritz1/test/test_parser.ritz
```

---

## Common Pitfalls to Avoid

1. **Operator Precedence Confusion**
   - ✅ DO: Reference ritz0/parser.py for correct levels
   - ❌ DON'T: Make up precedence values
   - Check: (1 + 2 * 3) should parse as (1 + (2 * 3))

2. **Token Consumption**
   - ✅ DO: Always consume tokens after parsing them
   - ❌ DON'T: Forget to advance past expected token
   - Verify: After parse_expr, lexer position moves forward

3. **Left Recursion**
   - ✅ DO: Use Pratt/precedence climbing, not left recursion
   - ❌ DON'T: Implement recursive descent naively
   - Check: parse_expr calls don't directly call themselves on same input

4. **Error Recovery**
   - ✅ DO: Panic on unexpected token with clear message
   - ❌ DON'T: Silently skip tokens
   - Add: Print token expected vs received

5. **AST Structure**
   - ✅ DO: Ensure AST matches what emitter expects
   - ❌ DON'T: Invent new node types
   - Reference: Check emitter expectations before parsing

---

## Files to Create/Modify

### Create
- `ritz1/src/parser.ritz` (~500 lines)
  - Complete parser implementation
  - AST node helper functions
  - Error handling utilities

- `ritz1/test/test_parser.ritz` (~300 lines)
  - Comprehensive test suite
  - Tests for each parser feature
  - Edge cases and error handling

### Modify
- Update `CURRENT_STATUS.md` with progress
- Add parser test counts to status

### Reference (Don't modify)
- `ritz0/parser.py` - Use as reference only
- `ritz1/src/lexer.ritz` - Already complete
- `ritz1/src/nfa.ritz` - Already complete

---

## Debugging Tips

### If Tests Fail

**Parser panics / crashes:**
1. Add debug output before/after suspicious code
2. Verify lexer is producing expected tokens first
3. Check token consumption - are we advancing past tokens?
4. Use simpler test cases first (single number before expressions)

**Wrong AST structure:**
1. Print the parsed AST and compare to expected
2. Verify all fields are initialized
3. Check you're using the right constant for node type
4. Compare with what ritz0 produces

**Precedence issues:**
1. Manually parse example expressions
2. Verify Pratt algorithm loop termination
3. Check precedence values match ritz0
4. Trace execution step-by-step

### Useful Debug Helpers
```ritz
# Add to parser for debugging
fn print_expr(expr: *Expr) -> i32
  # Print expression type and values
  0

fn print_ast(module: *Module) -> i32
  # Recursively print AST
  0
```

---

## Success Metrics

### Definition: Parser is "Done"
- [ ] All expression parsing tests pass
- [ ] All statement parsing tests pass
- [ ] All definition parsing tests pass
- [ ] Error cases handled gracefully
- [ ] Ready to hand off to emitter

### Validation
- [ ] `make test-ritz1-parser` shows all tests passing
- [ ] AST structure matches what emitter needs
- [ ] Code is well-commented and readable
- [ ] No compiler errors in ritz1 parser

---

## Timeline Estimate

```
Session 3 (Parser Implementation):
  Day 1 Morning:   Stages 1-2 (skeleton + primaries)
  Day 1 Afternoon: Stage 3 (binary operators)
  Day 2 Morning:   Stage 4 (unary + calls)
  Day 2 Afternoon: Stage 5 (statements)
  Day 3 Morning:   Stage 6 (definitions)
  Day 3 Afternoon: Stage 7 (polish + edge cases)
  Day 4:           Buffer + catch-up

Result: Complete, tested, ready for emitter by end of session
```

---

## Next Handoff

### After This Session Completes
- Parser is ready and tested
- Unblock emitter implementation
- Session 4: Implement emitter following same pattern

### If You Get Stuck
1. Check `ritz0/parser.py` for reference
2. Review `DESIGN.md` for language semantics
3. Look at similar tests for patterns
4. Use simpler test cases to debug

### If You Finish Early
1. Add more test cases
2. Improve error messages
3. Add documentation
4. Sketch emitter requirements
5. Start emitter skeleton

---

## Key Files Reference

### Must Read
- `ritz0/parser.py` - Implementation reference (500+ lines)
- `ritz1/test/test_lexer.ritz` - Test pattern to follow
- `docs/DESIGN.md` - Language semantics

### Should Skim
- `ritz0/ritz_ast.py` - AST structure (but we'll use Ritz structs)
- `CURRENT_STATUS.md` - Project overview
- `SESSION_2_SUMMARY.md` - Context from previous session

### Reference Only (Don't Edit)
- `ritz0/lexer.py` - Already working
- `ritz1/src/lexer.ritz` - Already working
- `ritz1/src/nfa.ritz` - Already working

---

## Git Workflow

### Before Starting
```bash
git pull              # Get latest
git status            # Verify clean
```

### While Developing
```bash
# Every few test completions
git add ritz1/src/parser.ritz ritz1/test/test_parser.ritz
git commit -m "Add parser stages 1-2"

# After each stage
git add . && git commit -m "Complete parser stage X"
```

### When Done
```bash
git log --oneline | head -5
make test            # Final verification
git status           # Verify everything committed
```

---

## Conclusion

You have everything you need to implement the parser successfully:
- ✅ Clear reference implementation (ritz0/parser.py)
- ✅ Proven test patterns (ritz1/test/test_lexer.ritz)
- ✅ Complete lexer (ritz1/src/lexer.ritz)
- ✅ Clear success criteria
- ✅ Detailed timeline

**Start with test design, implement incrementally, test continuously.**

Good luck! The parser is the key to unlocking self-hosting. 🚀

---

*Prepared: 2024-12-23*
*For: Session 3*
*Status: Ready to implement*
