# LARB Review: Sage

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

Sage is a JavaScript parser/template engine project (~1,100 SLOC across 7 files) implementing a full ES6+ lexer, recursive descent + Pratt parser, and an arena-based AST. The project uses modern Ritz idioms well in most areas — ownership modifiers, `@` syntax, `[[test]]` attributes, and keyword logical operators are all correct — but has a pervasive and systemic use of the old `c"..."` string prefix throughout the lexer's keyword dispatch table, which the spec classifies as old syntax in application-level code.

## Statistics

- **Files Reviewed:** 7
- **Total SLOC:** ~1,100
- **Issues Found:** 35 (Critical: 0, Major: 33, Minor: 2)

## Critical Issues

None.

## Major Issues

### 1. Pervasive `c"..."` String Prefix in Lexer (lexer.ritz, check_keyword function)

The `check_keyword` function (lines 183–302 of `lexer.ritz`) uses the old `c"..."` prefix on every single keyword comparison string — 32 instances in total. Per the spec, application-level code should use `"hello".as_cstr()` instead of `c"hello"`.

The instructions do note: "The compiler may still use `c"..."` internally for FFI — this is acceptable in low-level code. Focus on application code." Sage is an application (JavaScript engine), not a low-level FFI layer, so this must be updated.

**Affected file:** `/home/aaron/dev/ritz-lang/rz/projects/sage/src/lexer.ritz`

**All 32 occurrences, representative sample:**
```ritz
# WRONG (current):
if strview_eq_cstr(@text, c"if")
if strview_eq_cstr(@text, c"let")
if strview_eq_cstr(@text, c"function")
# ... 29 more

# CORRECT (idiomatic):
if strview_eq_cstr(@text, "if".as_cstr())
if strview_eq_cstr(@text, "let".as_cstr())
if strview_eq_cstr(@text, "function".as_cstr())
```

There is also one occurrence in `test_parser.ritz` (line 731):
```ritz
# WRONG:
var p = parse(strview_from_cstr(c"x = {a: 1}"))

# CORRECT:
var p = parse(strview_from_cstr("x = {a: 1}".as_cstr()))
```

**Total: 33 instances across 2 files.**

### 2. Raw Pointer Type `**u8` in main() Signatures

Both `main.ritz` (line 7), `test_parser.ritz` (line 1183), and `test_lexer.ritz` (line 256) use `**u8` for argv:

```ritz
fn main(argc: i32, argv: **u8) -> i32
```

While `*T` raw pointers are acceptable in FFI/unsafe contexts, main entry points that don't actually use `argv` (all three do nothing with it) could simply omit it. More importantly, the parameter is accepted but never used in any of the three files, which is a minor cleanliness issue.

## Minor Issues

### 1. Missing `impl` Blocks for Struct Methods

All struct-associated functions (`lexer_new`, `parser_new`, `ast_new`, etc.) follow the freestanding `fn type_verb(...)` pattern rather than `impl Type` blocks. The spec notes the old `fn Type.method()` syntax is "deprecated, tolerated for now," and `impl` blocks are preferred. The freestanding `fn lexer_*` approach used here is not technically the deprecated dot-syntax, but migration toward `impl Lexer { fn new(...) }` etc. would be more idiomatic.

### 2. `while 1 == 1` Idiom

Several files use `while 1 == 1` as an infinite loop idiom (e.g., `lexer.ritz` line 492, `parser.ritz` lines 448, 631, 716). If the language supports `loop` or `while true`, those would be preferred. This is purely stylistic if no better construct exists.

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | OK | Correct use of `x: T` (const borrow), `x:& T` (mut borrow) throughout. No Rust-style `&T` or `&mut T`. |
| Reference Types (@) | OK | `@x` and `@&x` used consistently and correctly. No bare `&x` address-of. |
| Attributes ([[...]]) | OK | All 50+ test functions use `[[test]]`. No old `@test` syntax found. |
| Logical Operators | OK | `and`, `or`, `not` keywords used in Ritz code. No `&&`, `\|\|`, `!` in Ritz logic. |
| String Types | ISSUE | 33 instances of old `c"..."` prefix in application-level code (lexer.ritz, test_parser.ritz). |
| Error Handling | OK | No error handling patterns required for this project type; parse errors printed inline, acceptable. |
| Naming Conventions | OK | snake_case functions/variables, PascalCase types (Lexer, Parser, Token, Ast, AstNode), SCREAMING_SNAKE for constants (TOKEN_*, AST_*, OP_*). |
| Code Organization | OK | Good header comments, logical grouping with section banners, imports grouped. |

## Files Needing Attention

1. `/home/aaron/dev/ritz-lang/rz/projects/sage/src/lexer.ritz` — 32 `c"..."` occurrences in `check_keyword` (lines 189–299)
2. `/home/aaron/dev/ritz-lang/rz/projects/sage/test/test_parser.ritz` — 1 `c"..."` occurrence (line 731)

## Recommendations

**Priority 1 (Major) — Update `c"..."` to `.as_cstr()` in application code:**
The `check_keyword` function in `lexer.ritz` is the single biggest compliance gap. A mechanical find-and-replace of `c"` with `"` + appending `.as_cstr()` to each literal (adjusting the closing quote position) will resolve all 32 instances. One additional fix needed in `test_parser.ritz` line 731.

**Priority 2 (Minor) — Consider migrating to `impl` blocks:**
Over time, grouping `lexer_*`, `parser_*`, `ast_*`, and `token_*` functions into `impl Lexer`, `impl Parser`, `impl Ast`, `impl Token` blocks would align better with modern Ritz idioms. Not urgent, but recommended for the next refactor cycle.

**Priority 3 (Minor) — Unused `argv` in main functions:**
All three `main` functions accept `argv: **u8` but never use it. Consider removing or marking it.
