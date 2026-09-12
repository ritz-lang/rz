# Self-Hosting Status: ritz1 Compiling ritz1

## Current Blocker

Attempting to compile ritz1 source with itself (`/tmp/ritz1 ritz1/src/*.ritz -o /tmp/ritz1_self.ll`) fails with:

```
Parser error: unexpected token in expression
At line
```

When compiling `ritz1/src/tokens.ritz` at line 84-90 (the `token_new` function).

## Root Cause

**ritz1 parser doesn't support struct literal expressions** - specifically the syntax:

```ritz
fn token_new(...) -> Token
  Token {        # <--- ERROR: Parser doesn't recognize Type { ... } syntax!
    kind: kind,
    start: nil,
    ...
  }
```

The parser recognizes struct literal syntax (`Type { field: value, ... }`) as an expression, but **has no code to parse it**. When it encounters `Token` followed by `{`, it tries to parse `Token` as an identifier expression, then fails when it sees `{` because that's not a valid continuation.

### Why This Matters

ritz1's own source code uses struct literals extensively in helper functions like:
- `expr_int()` in ast.ritz - returns `Expr { kind: EXPR_INT_LIT, ... }`
- `token_new()` in tokens.ritz - returns `Token { kind: kind, ... }`
- All statement constructors in ast.ritz

These were compiled successfully by ritz0 (which supports struct literals), but ritz1's parser can't parse them from source.

## Scope of the Problem

Grep results show **~94 occurrences** of `: 0` used as null pointers in struct initializers:

- **ast.ritz**: 91 cases (most in helper functions like `expr_int`, `expr_ident`, `stmt_return`, etc.)
- **tokens.ritz**: 1 case
- **lexer.ritz**: 2 cases
- **regex.ritz**: Several cases
- **main.ritz, parser.ritz, etc.**: Scattered cases

## Possible Solutions

### Option 1: Add Null Pointer Literal Support ⚡
**Add special handling for `0` in pointer contexts**

Changes needed:
- Parser: Detect when `0` is assigned to pointer-typed field
- Emitter: Emit `null` instead of `i32 0` when type is pointer

Pros:
- Minimal source changes
- Idiomatic (matches C/C++)

Cons:
- Requires type inference (ritz1 has minimal type tracking)
- Complex to implement correctly
- Ambiguous: is `0` an int or a pointer?

### Option 2: Use Explicit Casts ✅ (RECOMMENDED)
**Change all `: 0` to `: 0 as *T` for pointer fields**

Example:
```ritz
fn token_new(...) -> Token
  Token {
    kind: kind,
    start: 0 as *i8,    # <--- Explicit cast!
    len: len,
    line: line,
    col: col
  }
```

Pros:
- **Works with current ritz1** (casts already supported!)
- Explicit and unambiguous
- No new features needed

Cons:
- 94 manual changes across multiple files
- More verbose

### Option 3: Add Default Field Initialization
**New syntax for optional/default struct fields**

Example:
```ritz
struct Token
  kind: i32
  start: *i8 = null    # <--- Default value
  len: i32
  line: i32
```

Pros:
- Most ergonomic
- Reduces boilerplate

Cons:
- Major parser/emitter feature
- Syntax design needed
- Out of scope for now

## Recommendation: Option 4 (Add `nil` Keyword) ⭐ BEST

**Add a `nil` keyword for null pointers**, similar to Go, Swift, etc.

Example:
```ritz
fn token_new(...) -> Token
  Token {
    kind: kind,
    start: nil,    # <--- Clear and type-safe!
    len: len,
    line: line,
    col: col
  }
```

Pros:
- ✅ **Clearest syntax** - no confusion with integer `0`
- ✅ **Type-safe** - compiler knows it's a pointer
- ✅ **Matches modern languages** (Go, Swift, Kotlin, etc.)
- ✅ **Single keyword** fixes all 94 cases

Cons:
- Requires parser + emitter changes
- New language feature

**Fallback: Option 2 (Explicit Casts)**

If `nil` is too complex to add now, use `0 as *T`:
- ✅ Works immediately with existing ritz1
- ✅ Makes intent explicit
- ✅ Enables gradual progress (can fix file-by-file)
- ❌ Verbose and ugly

## Next Steps

1. **Fix tokens.ritz** (1 occurrence) - quick test
2. **Fix ast.ritz** (91 occurrences) - bulk of work
3. **Fix remaining files** (lexer.ritz, regex.ritz, etc.)
4. **Retry compilation** after each file
5. **Track next blocker** (likely another missing feature)

## Expected Next Blockers

After fixing null pointers, expect to hit:
- **Struct literals** with complex nesting
- **Array literals** (`[1, 2, 3]` syntax)
- **String operations** (concatenation, formatting)
- **Advanced type features** (generic functions, type aliases)

## Bootstrap Progress Estimate

**Current**: 10/10 Tier 1 examples passing (basic programs)
**Self-hosting**: Blocked at first source file (tokens.ritz:83)
**Estimate**: 3-5 more missing features to discover before ritz1 can compile itself

