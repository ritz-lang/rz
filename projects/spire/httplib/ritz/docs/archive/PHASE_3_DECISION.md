# Phase 3 Decision: Self-Hosted Ritz Compiler

## Current Status
- ✅ Phase 1G Complete: 116/116 tests passing
- ✅ All 10 example programs working
- ✅ Ready to begin Phase 3

## The Decision Point

For Phase 3 (self-hosting the compiler in Ritz), we need to decide how to handle TokenType for the lexer.

### Option A: Implement Full Enum Support First
Enhance ritz0 to emit enums, then use idiomatic Rust-like enums in ritz1.

**Implementation**: 6-8 hours
- Add enum type lowering in emitter (tagged unions)
- Generate variant constructor functions
- Support pattern matching on enums
- Create test/test_enum.ritz

**Timeline Impact**: Delays Phase 3 by 1 week
**Benefit**: Complete type system, idiomatic Ritz code

### Option B: Use Integer Constants (Recommended)
Define TokenType as i32 constants, start Phase 3 immediately.

**Implementation**: 0 hours
```ritz
const TOKEN_INT: i32 = 0
const TOKEN_STRING: i32 = 1
const TOKEN_IDENT: i32 = 2
// ... etc

struct Token
  kind: i32
  value: *i8
  line: i32
  col: i32
```

**Timeline Impact**: Start immediately
**Benefit**: Fast bootstrap, can add enums in Phase 4

---

## Recommendation: Option B

**Why**:
1. **TDD Philosophy**: Add features when they're evolutionarily necessary
2. **Bootstrap Focus**: Phase 3 is about getting self-hosting to work, not type system completeness
3. **Constants Work Fine**: i32 constants are perfectly adequate for lexer token types
4. **Phase 4 Improvement**: Once ritz1 compiles itself, implement proper enums in ritz2
5. **Faster Iteration**: Get bootstrap working this week, not next

**Risk Assessment**:
- ❌ Less ergonomic (if/else chains vs pattern matching)
- ✅ No blocking issues for bootstrap
- ✅ Easy to migrate to enums later
- ✅ All current examples work without enums

---

## What Needs to Happen Next (Path B)

### 1. Plan ritz1 Implementation
Identify what language features we need from ritz0:
- ✅ Structs (we have these)
- ✅ Arrays (we have fixed-size arrays)
- ✅ Pointers (we have these)
- ✅ String handling (we have this)
- ✅ Functions (we have these)
- ✅ Loops and conditionals (we have these)
- ❓ HashMap or similar (for symbol tables)
- ❓ Dynamic arrays/vectors (for token storage)

### 2. Start ritz1 Lexer
Rewrite the Python lexer in Ritz:
- Token type constants (i32)
- Token struct (kind, value, line, col)
- Tokenization logic
- Whitespace/indent handling

### 3. Bootstrap Test
```bash
python ritz0.py ritz1/lexer.ritz -o lexer.ll
# lexer.ll is LLVM IR
# Compile it and verify it can tokenize
```

### 4. Complete Compiler Stack
- ritz1/parser.ritz
- ritz1/emitter.ritz
- Build bootstrap: ritz0 → ritz1 → ritz1 (self-hosting)

---

## Enum Support Timeline (Deferred to Phase 4)

**Phase 4** (after bootstrap works):
1. Implement full enum support in ritz2
2. Add pattern matching to ritz2
3. Rewrite ritz2's lexer using idiomatic enums
4. Achieve self-hosting with complete type system

This is the pragmatic approach: get bootstrap working first, improve type system later.

---

## Ready to Proceed?

**If Option A (Enums Now)**: I can implement enum support in 6-8 hours
**If Option B (Constants)**: We can start Phase 3 lexer planning immediately

Which path would you like to take?
