# GitHub Issues for ritz1 Cleanup

Create these issues at: https://github.com/ritz-lang/ritz/issues

---

## Issue #8: Multi-argument function calls not supported

**Labels:** bug, priority:high, ritz1

**Description:**

The ritz1 parser currently only supports single-argument function calls. Multi-argument calls cause crashes.

**Current State:**
```ritz
# ritz1/src/parser.ritz:95-99
var args: *Expr = 0
if (*p).current.kind != TOK_RPAREN
  args = parser_parse_expr(p)
  # TODO: Handle multiple arguments separated by commas
```

**Impact:**
- Can't compile `add(10, 32)` with 2+ arguments
- Blocks A/B testing of Tier 1 examples

**Solution:**
- Parse comma-separated argument list
- Build linked list via `Expr.next` pointer
- IR emitter already handles multiple args (lines 314-352)

**Estimated Effort:** 1 hour

**Acceptance Criteria:**
- [ ] Parser accepts `foo(a, b, c)` syntax
- [ ] IR emitter receives full argument list
- [ ] A/B test passes for multi-arg functions

---

## Issue #9: Assignment statements not implemented in IR emitter

**Labels:** bug, priority:high, ritz1

**Description:**

Parser can parse assignments but IR emitter has no code generation for them.

**Current State:**
- `STMT_ASSIGN` exists in AST (ast.ritz:35)
- Parser handles `x = expr` syntax (parser.ritz:242-269)
- NO case for `STMT_ASSIGN` in `emit_stmt()` (main_new.ritz:364-490)

**Impact:**
- Variable mutations don't compile
- Loops with counters fail: `i = i + 1`

**Solution:**
```ritz
if kind == STMT_ASSIGN
  let var_reg: i32 = varmap_lookup(vm, (*stmt).assign_target, (*stmt).assign_target_len)
  let value_reg: i32 = emit_expr(buf, pos_ptr, (*stmt).assign_value, reg_counter, vm)
  ir_emit_str(buf, pos_ptr, "  store i32 ")
  ir_emit_reg(buf, pos_ptr, value_reg)
  ir_emit_str(buf, pos_ptr, ", ptr ")
  ir_emit_reg(buf, pos_ptr, var_reg)
  ir_emit_str(buf, pos_ptr, "\n")
```

**Estimated Effort:** 30 minutes

**Acceptance Criteria:**
- [ ] `x = expr` compiles to valid LLVM IR
- [ ] Loops with mutation work correctly
- [ ] A/B test passes for assignments

---

## Issue #10: Parser has no operator precedence

**Labels:** bug, priority:high, ritz1

**Description:**

Binary expression parser uses simple left-to-right evaluation with no precedence rules.

**Current Behavior:**
```ritz
2 + 3 * 4  →  (2 + 3) * 4  =  20   # WRONG!
```

**Expected:**
```ritz
2 + 3 * 4  →  2 + (3 * 4)  =  14   # RIGHT
```

**Impact:**
- Arithmetic expressions evaluate incorrectly
- Blocks correctness testing

**Solution:**
- Implement precedence climbing or Pratt parsing
- Precedence levels:
  1. `*`, `/`, `%` (highest)
  2. `+`, `-`
  3. `<`, `>`, `<=`, `>=`
  4. `==`, `!=`
  5. `&&`
  6. `||` (lowest)

**Estimated Effort:** 3 hours

**Acceptance Criteria:**
- [ ] `2 + 3 * 4` evaluates to 14
- [ ] `x < 10 && y > 0` parses correctly
- [ ] All operator precedence tests pass

---

## Issue #11: Comparison results incompatible with logical operators

**Labels:** bug, priority:medium, ritz1

**Description:**

Comparisons return `i1` (boolean) which is immediately extended to `i32`, but logical operators (`&&`, `||`) expect `i1` operands.

**Current Code:**
```ritz
# Comparison returns i32 (lines 299-310)
let bool_reg: i32 = result_reg
let extended_reg: i32 = *reg_counter
ir_emit_str(buf, pos_ptr, " = zext i1 ")
# ... convert i1 to i32

# Logical operators expect i1 (lines 285-288)
else if op == OP_AND
  ir_emit_str(buf, pos_ptr, "and i1 ")
```

**Impact:**
```ritz
if x > 0 && y < 10  # BROKEN: && gets i32, expects i1
```

**Solution:**
- Delay i1→i32 conversion until value is used in i32 context
- Keep comparisons as i1 for logical operators
- Convert to i32 only when storing/returning

**Estimated Effort:** 4 hours

**Acceptance Criteria:**
- [ ] `x > 0 && y < 10` compiles correctly
- [ ] Nested boolean expressions work
- [ ] A/B test passes for complex conditions

---

## Issue #12: No error reporting in parser

**Labels:** enhancement, priority:high, ritz1

**Description:**

All parse errors are silent failures - compiler produces wrong IR or crashes instead of helpful error messages.

**Current Code:**
```ritz
fn parser_expect(p: *Parser, kind: i32) -> i32
  if (*p).current.kind == kind
    parser_advance(p)
    return 1
  # TODO: Error handling
  0
```

**Impact:**
- Debugging is extremely difficult
- Silent failures lead to confusing crashes

**Solution:**
- Add error buffer to Parser struct
- Collect errors with line/column info
- Print errors to stderr before returning
- Return error codes from `compile()`

**Example Error:**
```
error: expected ')', found ';'
  --> test.ritz:5:12
   |
 5 |   foo(x, y;
   |            ^ expected ')'
```

**Estimated Effort:** 8 hours

**Acceptance Criteria:**
- [ ] Syntax errors print helpful messages
- [ ] Errors include line/column info
- [ ] Compiler exits with non-zero on parse error
- [ ] Error messages match Rust/Clang quality

---

## Issue #13: Incomplete NEWLINE handling

**Labels:** bug, priority:medium, ritz1

**Description:**

Parser only skips NEWLINE tokens in some places, causing hangs/crashes on valid code with extra blank lines.

**Current Handling:**
- ✅ Between statements in function body (parser.ritz:372)
- ✅ After if condition (parser.ritz:208)
- ✅ After while condition (parser.ritz:232)

**Missing Cases:**
- ❌ After function signature before body
- ❌ After `else` keyword
- ❌ Between function definitions at module level
- ❌ After type annotations

**Solution:**
Audit all parser functions and ensure NEWLINE is skipped wherever syntactically allowed.

**Estimated Effort:** 2 hours

**Acceptance Criteria:**
- [ ] Parser handles arbitrary newlines without hanging
- [ ] All valid Ritz programs with extra newlines compile
- [ ] Fuzzing test with random newlines passes

---

## Issue #14: VarMap has fixed 64-variable limit with no bounds checking

**Labels:** bug, priority:medium, ritz1

**Description:**

Variable map uses fixed-size arrays with no overflow protection.

**Current Code:**
```ritz
struct VarMap
  var_names: [64]*i8
  var_name_lens: [64]i32
  var_regs: [64]i32
  count: i32
```

**Impact:**
- Functions with >64 variables silently corrupt memory
- No error message, just crashes

**Solution:**
```ritz
fn varmap_add(vm: *VarMap, name: *i8, name_len: i32, reg: i32)
  if (*vm).count >= 64
    # TODO: Print error and exit
    return  # For now, just fail silently
  # ... rest of function
```

**Better Long-Term:**
- Use linked list (unbounded, slower lookup)
- Use hash table (bounded, fast lookup)

**Estimated Effort:** 1 hour (bounds check only)

**Acceptance Criteria:**
- [ ] Compiler errors instead of crashing on 65th variable
- [ ] Error message is helpful
- [ ] Consider dynamic resizing for future

---

## Issue #15: Token array has fixed 1024-token limit

**Labels:** bug, priority:low, ritz1

**Description:**

Source files with >1024 tokens fail to compile.

**Current Code:**
```ritz
var tokens: [1024]Token
var token_count: i32 = 0
while token_count < 1024
  let tok: Token = lexer_next(&lex)
  tokens[token_count] = tok
  # ...
```

**Impact:**
- Large files fail silently
- No error message

**Solutions:**
1. **Quick fix:** Increase to 4096 or 8192 tokens
2. **Better:** Dynamic resizing with realloc
3. **Best:** Stream tokens to parser (no buffering)

**Estimated Effort:**
- Quick fix: 5 minutes
- Dynamic: 2 hours
- Streaming: 8 hours

**Acceptance Criteria:**
- [ ] Files with >1024 tokens compile
- [ ] Error message if limit exceeded (if keeping limit)

---

## Issue #16: Inefficient constant loading in IR

**Labels:** enhancement, priority:low, ritz1

**Description:**

Integer literals are loaded via `add i32 0, 42` instead of being used directly.

**Current IR:**
```llvm
%1 = add i32 0, 42
ret i32 %1
```

**Better IR:**
```llvm
ret i32 42
```

**Impact:**
- Bloated IR (harmless - LLVM optimizes it away)
- Makes IR harder to read/debug

**Solution:**
- Change `emit_expr` to return both SSA register AND constant value
- Use constant directly when valid (function args, store values, ret)
- Only allocate register when needed (phi nodes, etc.)

**Estimated Effort:** 2 hours (requires API refactoring)

**Acceptance Criteria:**
- [ ] Literals used directly in IR where possible
- [ ] Generated IR is more readable
- [ ] A/B tests still pass (behavior unchanged)

---

## Issue #17: Unreachable code emitted after return statements

**Labels:** bug, priority:low, ritz1

**Description:**

If-then blocks with return statements still emit unconditional branch to end label.

**Current IR:**
```llvm
L1:  # then block
  ret i32 42
  br label %L3  # unreachable!
```

**Solution:**
Track whether block ends in terminator (ret/br), skip unconditional branch if already terminated.

**Impact:**
- Ugly IR (harmless - LLVM removes dead code)

**Estimated Effort:** 1 hour

**Acceptance Criteria:**
- [ ] No unreachable branches after returns
- [ ] IR is cleaner
- [ ] A/B tests pass

---

## Issue #18: Magic numbers for allocation sizes

**Labels:** code-quality, priority:low, ritz1

**Description:**

AST node allocation uses hardcoded sizes instead of constants.

**Current Code:**
```ritz
let e: *Expr = parser_alloc(p, 256) as *Expr     # Why 256?
let s: *Stmt = parser_alloc(p, 256) as *Stmt     # Why 256?
let param: *Param = parser_alloc(p, 128) as *Param  # Why 128?
```

**Better:**
```ritz
const EXPR_SIZE: i64 = 256
const STMT_SIZE: i64 = 256
const PARAM_SIZE: i64 = 128

let e: *Expr = parser_alloc(p, EXPR_SIZE) as *Expr
```

**Best (if ritz1 supports it):**
```ritz
let e: *Expr = parser_alloc(p, sizeof(Expr)) as *Expr
```

**Estimated Effort:** 30 minutes

**Acceptance Criteria:**
- [ ] All allocation sizes are named constants
- [ ] Code is more maintainable

---

## Issue #19: Missing function documentation

**Labels:** documentation, priority:low, ritz1

**Description:**

No function-level comments explaining parameters, return values, or side effects.

**Example:**
```ritz
# Current: no doc
fn emit_expr(buf: *i8, pos_ptr: *i64, expr: *Expr, reg_counter: *i32, vm: *VarMap) -> i32

# Better: documented
# Emit LLVM IR for expression, return SSA register holding result
#
# Args:
#   buf: Output buffer for IR text
#   pos_ptr: Current position in buffer (updated)
#   expr: Expression AST node to emit
#   reg_counter: Next available SSA register number (updated)
#   vm: Variable mapping context
# Returns: SSA register number containing expression result
fn emit_expr(buf: *i8, pos_ptr: *i64, expr: *Expr, reg_counter: *i32, vm: *VarMap) -> i32
```

**Estimated Effort:** 4 hours

**Acceptance Criteria:**
- [ ] All public functions have doc comments
- [ ] Comments explain non-obvious logic
- [ ] Examples included for complex functions

---

## Issue #20: No high-level architecture documentation

**Labels:** documentation, priority:medium, ritz1

**Description:**

Missing overview of compiler pipeline and design decisions.

**Needed:**
`docs/ARCHITECTURE.md` explaining:
1. Compiler pipeline (lex → parse → emit → write)
2. Data structures (AST, VarMap, etc.)
3. Memory management (parser heap allocator)
4. IR generation strategy (tree walk, SSA registers)
5. Design decisions (why NFA lexer? why no type checker yet?)

**Estimated Effort:** 2 hours

**Acceptance Criteria:**
- [ ] New contributors can understand codebase
- [ ] Design rationale is documented
- [ ] Data flow is clear

---

## Issue #21: No negative test suite

**Labels:** testing, priority:medium, ritz1

**Description:**

All tests check valid programs compile correctly, but we don't test error cases.

**Missing Tests:**
- Syntax errors (malformed code should fail gracefully)
- Type errors (when type checker exists)
- Undefined variable errors
- Stack overflow (deeply nested expressions)

**Example Test:**
```ritz
# test/negative/syntax_error.ritz
fn foo()
  return 42;  # Semicolon is syntax error in Ritz

# Expected: "error: unexpected token ';'"
```

**Estimated Effort:** 4 hours

**Acceptance Criteria:**
- [ ] 20+ negative test cases
- [ ] Tests verify error messages match expected
- [ ] Tests run in CI

---

## Issue #22: No IR validation in tests

**Labels:** testing, priority:medium, ritz1

**Description:**

A/B testing only compares exit codes, not IR correctness.

**Current:**
```bash
./test_ab.sh test.ritz
# Only checks if exit codes match
```

**Better:**
```bash
# Validate IR is well-formed
llc --verify-machineinstrs /tmp/test_a.ll
opt -verify /tmp/test_a.ll -o /dev/null

# Check for undefined behavior
opt -lint /tmp/test_a.ll -o /dev/null
```

**Estimated Effort:** 1 hour

**Acceptance Criteria:**
- [ ] All generated IR passes LLVM verification
- [ ] No undefined behavior warnings
- [ ] Tests catch IR bugs early

---

## Issue #23: Linear search in VarMap (performance)

**Labels:** performance, priority:low, ritz1

**Description:**

Variable lookup is O(n) for every reference.

**Current:**
```ritz
fn varmap_lookup(vm: *VarMap, name: *i8, name_len: i32) -> i32
  var i: i32 = 0
  while i < (*vm).count
    if (*vm).var_name_lens[i] == name_len
      var found: i32 = 1
      var j: i32 = 0
      while j < name_len
        if *((*vm).var_names[i] + j) != *(name + j)
          found = 0
          break
        j = j + 1
      if found != 0
        return (*vm).var_regs[i]
    i = i + 1
  0
```

**Impact:**
- O(n²) for n variable references
- Negligible for <64 variables
- Could matter for large functions

**Solution:**
- Hash table (O(1) lookup)
- Requires hash function and collision handling

**Estimated Effort:** 8 hours

**Acceptance Criteria:**
- [ ] Lookup is O(1) average case
- [ ] Large functions compile faster
- [ ] A/B tests still pass

---

## Issue #24: No type checking pass

**Labels:** enhancement, priority:critical, ritz2

**Description:**

ritz1 has NO type checker - produces invalid LLVM IR for type mismatches.

**Current State:**
- Parser doesn't track types
- IR emitter assumes all expressions are `i32`
- No validation of function call arguments
- No validation of binary operators (e.g., `42 + "hello"`)

**Impact:**
- Type errors produce cryptic LLVM errors
- No helpful error messages
- Hard to debug

**Solution (for ritz2):**
1. Add `type` field to Expr nodes
2. Implement type inference/checking pass
3. Validate function signatures
4. Check binary operator types

**Estimated Effort:** 16+ hours (major architecture change)

**Acceptance Criteria:**
- [ ] Type errors caught before IR generation
- [ ] Helpful error messages with location
- [ ] All examples type-check correctly

---

## Summary Table

| Issue | Priority | Effort | Status |
|-------|----------|--------|--------|
| #8  Multi-arg calls | 🔴 High | 1h | Blocks A/B testing |
| #9  Assignment stmt | 🔴 High | 30m | Blocks loops |
| #10 Precedence | 🔴 High | 3h | Correctness bug |
| #11 Bool/i32 types | 🟡 Medium | 4h | Blocks complex conditions |
| #12 Error reporting | 🔴 High | 8h | UX critical |
| #13 NEWLINE handling | 🟡 Medium | 2h | Parser robustness |
| #14 VarMap bounds | 🟡 Medium | 1h | Safety |
| #15 Token limit | 🟢 Low | 5m | Quick fix |
| #16 Constant loading | 🟢 Low | 2h | Code quality |
| #17 Unreachable code | 🟢 Low | 1h | Code quality |
| #18 Magic numbers | 🟢 Low | 30m | Maintainability |
| #19 Function docs | 🟢 Low | 4h | Documentation |
| #20 Architecture doc | 🟡 Medium | 2h | Documentation |
| #21 Negative tests | 🟡 Medium | 4h | Test coverage |
| #22 IR validation | 🟡 Medium | 1h | Test quality |
| #23 VarMap perf | 🟢 Low | 8h | Performance |
| #24 Type checker | 🔴 ritz2 | 16h+ | Future work |
| #25 String literals | ✅ Done | 4-8h | `s"..."` → `Span<u8>` |

**Total Critical Path:** ~20 hours for must-fix items (#8-12)

---

## Issue #25: No native measured string literal syntax

**Labels:** enhancement, priority:high, language-design

**Description:**

Ritz currently only has C-style string literals (`c"hello"`) which produce null-terminated `*u8`. There's no way to create a measured string (`Span<u8>` or `String`) from a literal without manually counting bytes.

**Current State:**
```ritz
# This is the only string literal syntax
let s: *u8 = c"hello"  # null-terminated, no length

# To get a measured string, you must:
fn S_HELLO() -> Span<u8>
    return span_literal(c"hello", 5)  # manually count bytes!

# Or inline:
let msg: Span<u8> = span_literal(c"hello", 5)
```

**Problems:**
1. **Error-prone** - manually counting bytes is begging for off-by-one bugs
2. **Verbose** - every string constant requires a wrapper function or inline span_literal
3. **Not idiomatic** - Ritz isn't C, shouldn't require C patterns
4. **Still uses C-strings underneath** - `c"..."` + manual length defeats the purpose

**Proposed Solution:**

Add a native string literal syntax that produces `Span<u8>` directly:

```ritz
# Option A: New prefix for measured strings
let msg: Span<u8> = s"hello"  # compiler computes length = 5

# Option B: Make bare strings measured by default
let msg: Span<u8> = "hello"   # Span<u8> with length 5
let cstr: *u8 = c"hello"      # explicit C-string when needed

# Option C: String type with implicit conversion
let msg: String = "hello"     # String is ptr + len
let span: Span<u8> = msg.as_span()
```

**Implementation Notes:**
- Compiler knows literal length at parse time
- Could emit as static data: `@.str.0 = private constant [5 x i8] c"hello"`
- Span would be `{ ptr: @.str.0, len: 5 }`
- Consider: should strings be interned? deduplicated?

**Impact:**
- Unlocks idiomatic Ritz string handling
- Makes valet/examples much cleaner
- Removes footgun of manual byte counting
- Aligns Ritz with modern language expectations

**Example - Before vs After:**
```ritz
# BEFORE (current, gross)
fn MIME_HTML() -> Span<u8>
    return span_literal(c"text/html", 9)

fn MIME_JSON() -> Span<u8>
    return span_literal(c"application/json", 16)

response_header_span(res, HEADER_CONTENT_TYPE(), MIME_HTML())

# AFTER (proposed)
response_header_span(res, s"Content-Type", s"text/html")
# or with bare string default:
response_header_span(res, "Content-Type", "text/html")
```

**Estimated Effort:** 4-8 hours (lexer + parser + IR emit)

---

## Implementation Guide

### Background: String vs Span

Ritz now has two string-like types:

| Type | Storage | Allocation | Use Case |
|------|---------|------------|----------|
| `String` | `Vec<u8>` (heap) | Dynamic, growable | Building strings at runtime |
| `Span<u8>` | `{ptr, len}` (16 bytes) | None - just a view | Static constants, slices, zero-copy |

The recent `string_from_bytes()` change (commit 82f39a4) fixed `String` literals - `"hello"` now uses compile-time length. But `Span<u8>` still requires manual byte counting via `span_literal(c"hello", 5)`.

### Proposed Syntax: `s"..."` for Span Literals

Add `s"..."` prefix to create `Span<u8>` with compile-time computed length:

```ritz
let msg: Span<u8> = s"hello"  # Span<u8> { ptr: @.str.0, len: 5 }
```

This parallels the existing `c"..."` for C-strings:
- `c"hello"` → `*u8` (null-terminated pointer)
- `s"hello"` → `Span<u8>` (pointer + length, no null terminator needed)
- `"hello"` → `String` (heap-allocated, existing behavior)

### Implementation Steps

#### 1. Lexer Changes (`ritz0/lexer.py`)

Add `TOK_SPAN_STRING` token type. In the string literal handler, detect `s"` prefix:

```python
# In lexer.py, after handling c"..." (around line 280-300)
elif self.peek() == 's' and self.peek(1) == '"':
    self.advance()  # consume 's'
    self.advance()  # consume '"'
    value = self._read_string_contents()
    return Token(TOK_SPAN_STRING, value, line, col)
```

#### 2. Parser Changes (`ritz0/parser.py`)

Handle `TOK_SPAN_STRING` in expression parsing, create a new AST node:

```python
# In ritz_ast.py
class SpanStringLit(Expr):
    """Span string literal: s"hello" -> Span<u8>"""
    value: str  # The string content (without quotes)

# In parser.py, in parse_primary() (around line 600)
elif self.current_token.kind == TOK_SPAN_STRING:
    value = self.current_token.value
    self.advance()
    return SpanStringLit(value)
```

#### 3. Type Checker Changes (`ritz0/type_checker.py`)

Infer `Span<u8>` type for `SpanStringLit`:

```python
# In visit_expr() or type inference (around line 400)
elif isinstance(expr, SpanStringLit):
    # Span<u8> is a struct with ptr: *u8, len: i64
    return self.get_span_u8_type()
```

#### 4. Emitter Changes (`ritz0/emitter_llvmlite.py`)

Emit LLVM IR that constructs a `Span<u8>` struct with static data:

```python
def _emit_span_string_literal(self, expr: SpanStringLit) -> ir.Value:
    """Emit s"hello" as Span<u8> { ptr: @.str.0, len: 5 }"""
    # Get or create the string constant (reuse existing _get_string_constant)
    gvar = self._get_string_constant(expr.value)
    zero = ir.Constant(self.i64, 0)
    ptr = self.builder.gep(gvar, [zero, zero])

    # Create Span<u8> struct: { ptr: *u8, len: i64 }
    span_type = ir.LiteralStructType([self.i8.as_pointer(), self.i64])
    length = ir.Constant(self.i64, len(expr.value))

    # Build the struct value
    span = ir.Constant(span_type, ir.Undefined)
    span = self.builder.insert_value(span, ptr, 0)    # ptr field
    span = self.builder.insert_value(span, length, 1) # len field

    return span
```

**Key LLVM IR output:**
```llvm
@.str.0 = private constant [5 x i8] c"hello"

; s"hello" becomes:
%span = insertvalue { i8*, i64 } undef, i8* getelementptr ([5 x i8], [5 x i8]* @.str.0, i64 0, i64 0), 0
%span.1 = insertvalue { i8*, i64 } %span, i64 5, 1
```

### Test Cases

Add to `ritz0/test/`:

```ritz
# test_span_string.ritz
import ritzlib.span

fn test_span_literal_length()
    let s: Span<u8> = s"hello"
    assert(s.len == 5)

fn test_span_literal_content()
    let s: Span<u8> = s"hello"
    assert(s.ptr[0] == 'h')
    assert(s.ptr[4] == 'o')

fn test_span_literal_empty()
    let s: Span<u8> = s""
    assert(s.len == 0)

fn test_span_literal_unicode()
    let s: Span<u8> = s"héllo"  # 6 bytes (é is 2 bytes in UTF-8)
    assert(s.len == 6)

fn test_span_literal_escapes()
    let s: Span<u8> = s"line1\nline2"
    assert(s.len == 11)
```

### Migration Path for Valet

Once implemented, valet can be cleaned up:

```ritz
# BEFORE (current)
fn MIME_HTML() -> Span<u8>
    return span_literal(c"text/html", 9)

response_header_span(res, HEADER_CONTENT_TYPE(), MIME_HTML())

# AFTER (with s"..." syntax)
response_header_span(res, s"Content-Type", s"text/html")
```

This eliminates ~100 lines of boilerplate span constant functions.

---

**Acceptance Criteria:**
- [x] Lexer recognizes `s"..."` as `TOK_SPAN_STRING`
- [x] Parser creates `SpanStringLit` AST node
- [x] Type checker infers `Span<u8>` type
- [x] Emitter generates correct LLVM IR struct
- [x] String literal syntax produces `Span<u8>` with correct length
- [x] No manual byte counting required
- [x] Static strings stored efficiently (readonly data section)
- [x] C-string syntax preserved for FFI compatibility
- [x] All test cases pass
- [ ] valet can be refactored to use new syntax
