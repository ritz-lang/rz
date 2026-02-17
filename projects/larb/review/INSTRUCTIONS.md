# LARB Code Review Instructions - Phase 3

**Review Date:** 2026-02-17
**Version:** Ritz Language Specification v0.2.0

This document provides comprehensive instructions for conducting LARB code reviews across all Ritz ecosystem projects.

---

## Overview

You are conducting a **LARB (Language Architecture Review Board) code review** of a Ritz project. Your task is to evaluate the code against the finalized language specification and design decisions.

**Important:** This is a *syntax and idiom* review, not a functionality review. We're checking if the code follows Ritz idioms and modern syntax.

---

## Review Output

Write your review to: `projects/larb/review/3/<project-name>.md`

Use this template:

```markdown
# LARB Review: <Project Name>

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** [PASS | NEEDS WORK | CRITICAL]

## Summary

<2-3 sentence summary of the project and overall compliance>

## Statistics

- **Files Reviewed:** X
- **Total SLOC:** ~Y
- **Issues Found:** Z (Critical: A, Major: B, Minor: C)

## Critical Issues

<Issues that MUST be fixed - wrong syntax, dangerous patterns>

## Major Issues

<Issues that SHOULD be fixed - non-idiomatic patterns, old syntax>

## Minor Issues

<Style nitpicks, suggestions for improvement>

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | OK/ISSUE | |
| Reference Types (@) | OK/ISSUE | |
| Attributes ([[...]]) | OK/ISSUE | |
| Logical Operators | OK/ISSUE | |
| String Types | OK/ISSUE | |
| Error Handling | OK/ISSUE | |
| Naming Conventions | OK/ISSUE | |
| Code Organization | OK/ISSUE | |

## Files Needing Attention

<List specific files with issues>

## Recommendations

<Prioritized list of what to fix>
```

---

## What to Check

### 1. Ownership Modifiers (CRITICAL)

The colon-modifier syntax is **finalized**:

| Syntax | Meaning | Frequency |
|--------|---------|-----------|
| `x: T` | Const borrow (or copy for primitives) | ~70% |
| `x:& T` | Mutable borrow | ~20% |
| `x:= T` | Move ownership | ~10% |

**Check for:**
- ❌ Old Rust-style `&T` or `&mut T` in function parameters
- ❌ Using `*T` or `*mut T` where borrows should be used
- ✅ Clean parameters with no sigils for const borrow
- ✅ `:&` for mutation, `:=` for ownership transfer

**Example - WRONG:**
```ritz
fn process(data: &Data)           # Wrong: Rust-style borrow
fn update(player: &mut Player)    # Wrong: Rust-style mut borrow
```

**Example - CORRECT:**
```ritz
fn process(data: Data)            # Const borrow - no sigil
fn update(player:& Player)        # Mutable borrow - :& modifier
fn consume(conn:= Connection)     # Move ownership - := modifier
```

---

### 2. Address-Of & Reference Types (CRITICAL)

The `@` syntax is **finalized**:

| Syntax | Meaning |
|--------|---------|
| `@x` | Immutable reference to x |
| `@&x` | Mutable reference to x |
| `@T` | Immutable reference type |
| `@&T` | Mutable reference type |
| `*T` | Raw pointer (FFI/unsafe only) |

**Check for:**
- ❌ Using `&x` for address-of (should be `@x`)
- ❌ Using `&mut x` for mutable ref (should be `@&x`)
- ✅ `@` for all reference operations
- ✅ `*T` only in FFI/unsafe contexts

**Example - WRONG:**
```ritz
let ptr = &data              # Wrong: should be @data
let mptr = &mut data         # Wrong: should be @&data
```

**Example - CORRECT:**
```ritz
let ptr = @data              # Immutable reference
let mptr = @&data            # Mutable reference
```

---

### 3. Attributes (CRITICAL)

Double-bracket syntax is **finalized**:

**Check for:**
- ❌ Old `@test` syntax
- ❌ Old `@inline` syntax
- ✅ `[[test]]` for tests
- ✅ `[[inline]]` for inlining hints

**Example - WRONG:**
```ritz
@test
fn test_foo() -> i32
```

**Example - CORRECT:**
```ritz
[[test]]
fn test_foo() -> i32
```

---

### 4. Logical Operators (MAJOR)

Use keywords, NOT symbols:

| Correct | Wrong |
|---------|-------|
| `and` | `&&` |
| `or` | `\|\|` |
| `not` | `!` |

**Example - WRONG:**
```ritz
if a && b || !c
```

**Example - CORRECT:**
```ritz
if a and b or not c
```

---

### 5. String Types (MAJOR)

String literals are `StrView` by default (zero-copy):

| Usage | Type |
|-------|------|
| `"hello"` | StrView (zero-copy, default) |
| `String.from("hello")` | String (heap-allocated) |
| `"hello".as_cstr()` | CStr for FFI |

**Check for:**
- ❌ Old `c"hello"` prefix (should be `"hello".as_cstr()`)
- ❌ Old `s"hello"` prefix (just use `"hello"`)
- ⚠️ Unnecessary String allocations where StrView suffices

**Note:** The compiler may still use `c"..."` internally for FFI - this is acceptable in low-level code. Focus on application code.

---

### 6. Error Handling (MAJOR)

Check for proper use of Result and `?` operator:

**Check for:**
- ❌ Nested match statements that could use `?`
- ❌ Ignoring errors silently
- ✅ Using `?` for error propagation
- ✅ Proper `Result<T, E>` return types
- ✅ Using bare variant names (`Ok`, `Err`, `Some`, `None`)

**Example - WRONG:**
```ritz
fn process() -> Result<Data, Error>
    match step1()
        Ok(v1) =>
            match step2(v1)
                Ok(v2) => Ok(v2)
                Err(e) => Err(e)
        Err(e) => Err(e)
```

**Example - CORRECT:**
```ritz
fn process() -> Result<Data, Error>
    let v1 = step1()?
    let v2 = step2(v1)?
    Ok(v2)
```

---

### 7. Methods Syntax (MAJOR)

Methods should be in `impl` blocks:

**Check for:**
- ⚠️ Old `fn Type.method()` syntax (deprecated, but tolerated for now)
- ✅ `impl Type` blocks with methods inside

**Example - DEPRECATED:**
```ritz
fn Point.distance(self: Point) -> f64
    # ...
```

**Example - PREFERRED:**
```ritz
impl Point
    fn distance(self: Point) -> f64
        # ...
```

---

### 8. Resource Cleanup (MAJOR)

Use `defer` for cleanup:

**Check for:**
- ❌ Manual cleanup at multiple return points
- ❌ Forgetting to close file descriptors
- ✅ `defer` immediately after resource acquisition
- ✅ LIFO cleanup order

**Example - CORRECT:**
```ritz
fn read_file(path: StrView) -> Result<String, Error>
    let fd = sys_open(path)?
    defer sys_close(fd)

    let content = read_all(fd)?
    Ok(content)
```

---

### 9. Naming Conventions (MINOR)

| Item | Convention |
|------|------------|
| Functions | snake_case |
| Variables | snake_case |
| Types/Structs | PascalCase |
| Enums | PascalCase |
| Enum Variants | PascalCase |
| Constants | SCREAMING_SNAKE_CASE |
| Type Parameters | Single uppercase (T, K, V, E) |
| Modules | snake_case |

---

### 10. Code Organization (MINOR)

Check file structure:
1. Module documentation (header comment)
2. Imports (grouped: ritzlib, external, local)
3. Constants
4. Type definitions
5. Trait implementations
6. Constructors
7. Core functions
8. Helper functions
9. Tests

---

## Special Considerations by Project Type

### Kernel/Low-Level (harland)
- Raw pointers (`*T`) are acceptable
- Manual memory management is expected
- Focus on correct unsafe block usage

### Standard Library (ritzlib)
- Should be the gold standard of idioms
- Extra scrutiny on API design
- Must use all modern syntax

### Applications (valet, zeus, mausoleum, etc.)
- Should follow all idioms strictly
- No excuse for old syntax
- Clean, readable code expected

### Compiler (ritz)
- May have some legacy patterns
- Still should modernize over time
- Focus on critical issues first

---

## Severity Guidelines

### CRITICAL
- Code that won't compile with new syntax
- Dangerous memory safety issues
- Security vulnerabilities

### MAJOR
- Old syntax that should be updated
- Non-idiomatic patterns that hurt readability
- Missing error handling

### MINOR
- Style issues
- Naming inconsistencies
- Documentation gaps
- Suggestions for improvement

---

## Review Process

1. **Scan all `.ritz` files** in the project
2. **Identify patterns** - look for systematic issues, not one-offs
3. **Check against compliance matrix** - each category above
4. **Document specific files** that need attention
5. **Provide recommendations** prioritized by severity
6. **Assign overall status:**
   - **PASS** - Minor issues only, follows idioms well
   - **NEEDS WORK** - Major issues present, needs attention
   - **CRITICAL** - Critical issues, must be fixed before merge

---

## Notes for Reviewers

- **Be thorough but fair** - some legacy code exists
- **Focus on patterns** - if you see an issue once, search for it everywhere
- **Prioritize safety** - ownership issues are more important than style
- **Consider context** - kernel code has different needs than web apps
- **Document everything** - future reviewers will thank you

---

*LARB Review Instructions v3.0 - February 2026*
