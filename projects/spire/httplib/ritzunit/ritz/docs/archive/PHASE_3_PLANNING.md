# Phase 3 Planning: Self-Hosted Ritz Compiler

## Current Status

**Phase 1G Complete**: 116/116 tests passing
- 49 executable ritz language tests (test_level1-6)
- 67 Python unit tests (lexer/parser)
- All example programs working

**At Decision Point**: Ready to begin Phase 3 (self-hosting)

## What is Phase 3?

Write the Ritz compiler in Ritz itself:
- ritz1/lexer.ritz - Tokenizer in Ritz
- ritz1/parser.ritz - Parser in Ritz
- ritz1/emitter.ritz - LLVM IR emitter in Ritz
- ritz0 compiles ritz1.ritz → ritz1.ll
- ritz1 compiles itself → ritz1 binary (bootstrap complete)

## Critical Discovery: Enum Status

### Current State
- ✅ Lexer recognizes `enum` keyword
- ✅ Parser fully parses enum definitions
- ✅ AST nodes (EnumDef, Variant) defined
- ❌ **Emitter DOES NOT emit enums** - no LLVM generation

### Why This Matters for Phase 3

The ritz1 lexer will need TokenType:

```ritz
enum TokenType
  INT, STRING, IDENT,
  LPAREN, RPAREN, LBRACE, RBRACE,
  NEWLINE, INDENT, DEDENT, EOF
  // ... 30+ more token types
```

## Two Path Options

### Path A: Implement Enum Support Now
**Decision**: Add full enum support to ritz0 before starting Phase 3

**Time**: 6-8 hours
**Scope**:
- Enum type lowering to LLVM (tagged unions)
- Variant constructors
- Pattern matching
- Create test/test_enum.ritz with 5-10 tests

**Advantages**:
- ritz1 can use idiomatic Rust-like enums
- Type system is semantically complete
- Proper enum support for future phases

**Disadvantages**:
- Delays Phase 3 by a week
- Complex implementation (tagged unions)
- Not strictly necessary for bootstrap

### Path B: Use Integer Constants (Pragmatic)
**Decision**: Use `i32` constants for TokenType, defer enum support to Phase 4

**Time**: Immediate (no implementation needed)
**Scope**:
```ritz
// Instead of: enum TokenType { INT, STRING, ... }
const TOKEN_INT: i32 = 0
const TOKEN_STRING: i32 = 1
const TOKEN_IDENT: i32 = 2
// ... etc

struct Token
  kind: i32        # Token type (as constant)
  value: *i8       # Token text
  line: i32
  col: i32
```

**Advantages**:
- Start Phase 3 immediately
- Constants work fine for lexer
- Enums are syntactic sugar for discriminated unions
- Follows TDD: add when needed

**Disadvantages**:
- Less ergonomic than enums
- Need if/else chains instead of match
- Type unsafety with i32
- Enums still incomplete in ritz0

## Recommendation: Path B (Pragmatic)

**Rationale**:
1. **TDD Philosophy**: Implement features when they're evolutionarily necessary
2. **Lexer doesn't require enums** - constants work fine
3. **Phase 3 is about self-hosting, not type system completeness**
4. **Phase 4 (ritz2)** is when we implement proper enums in the self-hosted compiler
5. **Faster iteration**: Get to bootstrap in days, not weeks

**Timeline**:
- Phase 3 (this week): Get ritz1 self-hosting working with constants
- Phase 4 (next week): Implement full enums in ritz2, can use them in ritz2 code

## Implementation Comparison

### Path A TokenType Example
```ritz
enum TokenType
  Int(i64)
  String(*i8)
  Ident(*i8)
  Keyword(*i8)
  Operator(u8)

fn token_type_to_string(t: TokenType) -> *i8
  match t
    case TokenType.Int(val) -> "INT"
    case TokenType.String(s) -> "STRING"
    // ... etc
```

### Path B TokenType Example
```ritz
const TOKEN_INT: i32 = 0
const TOKEN_STRING: i32 = 1
const TOKEN_IDENT: i32 = 2
const TOKEN_KEYWORD: i32 = 3
const TOKEN_OPERATOR: i32 = 4

struct Token
  kind: i32
  value: *i8

fn token_kind_to_string(kind: i32) -> *i8
  if kind == TOKEN_INT
    return "INT"
  if kind == TOKEN_STRING
    return "STRING"
  // ... etc
```

Both work. Path B is simpler for bootstrap phase.

## Future Enum Implementation Plan

### Phase 4: Enums in ritz2
Once ritz1 can compile ritz2, we can:
1. Implement proper enum lowering in ritz2
2. Rewrite ritz2's lexer using idiomatic enums
3. Full tagged union support with pattern matching

### Why Defer?
- ritz2 compiler will be written in ritz (using ritz1 to compile it)
- Once we have a working bootstrap, we can improve incrementally
- Enums are a type system feature that's orthogonal to bootstrap success

## Code Changes Needed (if Path A)

**If we choose enum support now**, here's what's needed:

1. **emitter_llvmlite.py** (150 lines):
   - Add enum type lowering in `_ritz_type_to_llvm()`
   - Register enums in first pass (like structs)
   - Generate constructor functions for variants
   - Support match expressions on enum values

2. **test/test_enum.ritz** (50 lines):
   - Basic enum definition
   - Variant construction
   - Pattern matching
   - Multiple variants

3. **Update unit tests** (10 lines):
   - Add enum emission tests

4. **Parser enhancement**: None needed (already complete!)

## Decision

**Recommendation**: Use **Path B (Integer Constants)**

This enables us to:
1. ✅ Start Phase 3 immediately
2. ✅ Get self-hosting working this week
3. ✅ Defer enum complexity to Phase 4
4. ✅ Iterate faster with self-hosted compiler
5. ✅ Implement better enums with ritz2

## Next Steps (Path B)

1. **Plan ritz1 lexer in Ritz**
   - Identify what language features we need
   - Can we use what we have (structs, arrays, pointers)?
   - What's the minimum viable subset?

2. **Start ritz1/lexer.ritz**
   - Copy Python lexer's logic to Ritz
   - Use TokenType as i32 constants
   - Test token generation with bootstrap tests

3. **Complete ritz1 compiler layers**
   - Parser (rewrite parser.py in Ritz)
   - Emitter (rewrite emitter_llvmlite.py in Ritz)

4. **Bootstrap**: ritz0 compiles ritz1 → ritz1 compiles itself

---

## Risk Assessment

### If we choose Path A (Enum Support First):
- **Risk**: Takes too long, loses momentum on Phase 3
- **Benefit**: Cleaner type system now
- **Mitigation**: Set time limit (6 hours), use minimal unit-variant enums

### If we choose Path B (Constants):
- **Risk**: ritz1 is less ergonomic
- **Benefit**: Fast bootstrap, can iterate on Phase 4
- **Mitigation**: Well-documented constant approach, quick port to ritz2

**Recommended**: Path B has lower risk and faster payoff.

---

## Questions for Stakeholder

1. **Priority**: Is getting self-hosting working more important than type system completeness?
2. **Timeline**: Do you want ritz1 working this week, or next week?
3. **Ergonomics**: Is using i32 constants acceptable for bootstrap phase?

**My Vote**: Path B - pragmatic bootstrap, improve type system in Phase 4.
