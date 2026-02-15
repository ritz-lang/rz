# Enum Support Analysis for Phase 3 Self-Hosting

## Executive Summary

**Enums are PARSED but NOT EMITTED in the current compiler stack.**

This means we can define enums in Ritz source code, but the emitter (LLVM IR generation) doesn't handle them, so enum code will fail at the emission stage.

## Current State

### ✅ What Works: Parsing

- **Lexer**: Recognizes ENUM keyword (tokens.py)
- **Parser**: `parse_enum()` method fully implemented (parser.py:736-765)
- **AST**: EnumDef and Variant nodes defined (ritz_ast.py:410-421)
- **Test Coverage**: Enum parsing test exists (test_parser.py:216)

```python
# Parser can successfully parse this:
enum Option
  Some(i32)
  None
```

### ❌ What's Missing: Emission

- **No enum handling in emitter_llvmlite.py**
  - No `emit_enum()` method
  - No enum variant constructor emission
  - No enum pattern matching support
  - No enum value representation (tag + data)

### Current Emit Pipeline Issue

In `emitter.emit_module()` (line 112-150), the item processing loop:

```python
# First pass: struct definitions
for item in module.items:
    if isinstance(item, rast.StructDef):
        self._register_struct(item)

# Second pass: constants and signatures
for item in module.items:
    if isinstance(item, rast.ConstDef):
        # handle constants
    elif isinstance(item, rast.ExternFn):
        # handle extern functions

# Third pass: function definitions
for item in module.items:
    if isinstance(item, rast.FnDef):
        self._emit_function(item)
```

**Notice**: There is NO handling for `EnumDef` items anywhere.

If you try to compile an enum, it will be silently ignored (no emission) or cause a runtime error if referenced.

## What Phase 3 Needs

For self-hosting the lexer in Ritz, we would need to define:

```ritz
enum TokenType
  INT
  STRING
  IDENT
  LPAREN
  RPAREN
  NEWLINE
  EOF
  // ... 30+ more variants

enum TokenKind
  Int(i64)
  String(*i8)
  Ident(*i8)
  Keyword(*i8)
  Operator(u8)
```

## Two Paths Forward

### Path A: Implement Full Enum Support (Strict Type System)
**Time Investment**: 6-8 hours
- Implement enum lowering to LLVM (tagged unions)
- Support enum variant construction
- Support pattern matching on enums
- Add enum tests
- Then start Phase 3 self-hosting

**Benefit**: Complete type system matches Rust-like enum semantics

### Path B: Use Constants Instead (Pragmatic)
**Time Investment**: 30 minutes
- Define TokenType as i32 constants instead of enum variants
- Use i32 to represent token types
- Pattern match with if/else on i32 values
- Works immediately, enables Phase 3 now

**Example for Path B**:
```ritz
const TOKEN_INT: i32 = 0
const TOKEN_STRING: i32 = 1
const TOKEN_IDENT: i32 = 2
// ... etc

struct Token
  kind: i32
  value: *i8
  line: i32
  column: i32
```

## Implementation Strategy for Enum Support (Path A)

If we choose full enum support, the implementation would be:

### 1. Enum Lowering Strategy

Enums are represented as tagged unions in LLVM:
- Tag field (i8 or i32) for variant discriminant
- Data field (pointer or inline) for variant data

```llvm
; Option<i32> would become:
%Option = type {i8, i64}  ; tag + i32 data
```

### 2. Variant Constructor Functions

Auto-generate constructor functions:
```ritz
fn Option_Some(value: i32) -> Option
  let result: Option = /* construct */
  result

fn Option_None() -> Option
  let result: Option = /* construct */
  result
```

### 3. Pattern Matching

Support match/case on enum values:
```ritz
match myOption
  case Option.Some(x) -> x + 1
  case Option.None -> 0
```

### 4. Code Changes Needed

**emitter_llvmlite.py**:
1. Add enum type lowering in `_ritz_type_to_llvm()`
2. Add `_register_enum()` in first pass (like structs)
3. Add `_emit_enum_constructors()` to generate helper functions
4. Update match statement handling for enum patterns

**test files**:
1. Create `test/test_enum.ritz` with 5-10 enum tests
2. Test basic enum construction
3. Test pattern matching
4. Test tag-based discrimination

## Recommendation

**For Phase 3 pragmatic path**: Use **Path B (Constants)** for now.

**Rationale**:
1. Lexer doesn't strictly need enums - constants work fine
2. Enums are syntactic sugar over tagged unions
3. Doing full enum implementation now delays Phase 3 by a week
4. Phase 4 (ritz2) can implement proper enums after self-hosting works
5. TDD philosophy: implement enums when they're evolutionarily necessary

**Plan**:
1. Use i32 constants for TokenType in ritz1 lexer
2. Commit to implementing full enums in ritz2 (Phase 4)
3. Phase 3 focuses on getting self-hosted compilation working
4. Once ritz1 → ritz2 compiles itself, add enum support

## Minimal Enum Impl If Needed Later

If we decide to implement enums now (Path A), here's the minimal version:

**Scope**: Unit variants only (no data in variants)
- Simplest case: `enum TokenType { INT, STRING, IDENT, ... }`
- Represents as i32 constants
- Requires only constant generation, no tagged union complexity
- Can be done in 2-3 hours

This gives us enum syntax without full tagged union implementation.

---

## Summary Table

| Feature | Status | Phase | Notes |
|---------|--------|-------|-------|
| Enum parsing | ✅ Complete | 1G | Parser fully works |
| Enum AST | ✅ Complete | 1G | EnumDef/Variant nodes ready |
| Enum emission | ❌ Missing | - | Needs implementation |
| Enum unit variants | ❌ Missing | 4? | Simple constants approach |
| Tagged union enums | ❌ Missing | 4? | Full enum with data |
| Pattern matching | ❌ Missing | 4? | Requires match statement work |

---

**Decision Point**: Should Phase 3 start with:
- **Option A**: Implement minimal unit-variant enums now (2-3 hours)
- **Option B**: Use constants for TokenType, implement full enums in Phase 4

Currently blocking Phase 3 decision until this is resolved.
