# Ritz Language Review

**LARB Document** | **Status:** Draft | **Date:** 2026-02-13

This document evaluates Ritz for usability, security, consistency, and aesthetic appeal. The goal: make Ritz sexy and safe—a language you *want* to play with.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Usability Review](#2-usability-review)
3. [String System Design](#3-string-system-design) ⭐ **Major Redesign**
4. [Pointer vs Reference Philosophy](#4-pointer-vs-reference-philosophy) ⭐ **Major Redesign**
5. [Security Review](#5-security-review)
6. [Syntax Consistency](#6-syntax-consistency)
7. [Aesthetics & Polish](#7-aesthetics--polish)
8. [Error Messages](#8-error-messages)
9. [Optimization Opportunities](#9-optimization-opportunities)
10. [Recommendations](#10-recommendations)

---

## 1. Executive Summary

### What's Working Well

| Aspect | Strengths |
|--------|-----------|
| **Syntax** | Clean, Python-like indentation. No semicolons. Reads naturally. |
| **Types** | Rust-like type system with better ergonomics. |
| **Ownership** | Simplified borrowing without lifetime annotations. |
| **Error handling** | `?` operator for propagation. Result/Option pattern. |
| **`let`/`var`** | Cleaner than Rust's `let`/`let mut` |

### Areas for Improvement (Major Redesigns)

| Aspect | Concerns | See Section |
|--------|----------|-------------|
| **Strings** ⭐ | `c""` and `s""` prefixes are awkward. Need proper type hierarchy. | §3 |
| **Pointers** ⭐ | Overuse of `*T` where `&T` is appropriate. Wrong defaults. | §4 |
| **Keywords** | Inconsistencies (`and`/`or` vs `&&`/`||`). | §6 |
| **Nullability** | `null` exists but union types blur semantics. | §5 |
| **Match** | Limited pattern matching (no guards, no nested destructuring). | — |

### Sexiness Rating: **7/10** → Target **9/10**

Ritz is clean and approachable, but has two fundamental design issues (strings and pointers) that need addressing before 1.0. With the redesigns in this document, Ritz will be genuinely inviting.

---

## 2. Usability Review

### 2.1 Learning Curve

**Good:** The syntax is immediately readable to Python/Rust programmers.

```ritz
fn factorial(n: i32) -> i32
    if n <= 1
        return 1
    return n * factorial(n - 1)
```

**Concern:** Newcomers may be confused by:

1. **Two variable keywords:** `let` (immutable) vs `var` (mutable)
   - Swift uses this pattern, but Rust uses `let` and `let mut`
   - Recommendation: Keep it. `let`/`var` is more intuitive than `let`/`let mut`.

2. **Pointer vs Reference distinction:**
   ```ritz
   &T      # Reference (safe, non-null)
   *T      # Pointer (unsafe, nullable)
   ```
   - This is good! But documentation should emphasize when to use which.

3. **Multiple string types:**
   ```ritz
   "hello"    # String (owned, heap)
   c"hello"   # *u8 (C-compatible)
   s"hello"   # Span<u8> (slice)
   ```
   - Power users love this. Beginners will trip.
   - Recommendation: Default `"hello"` should be a span (zero-copy), use `String::from("hello")` for heap.

### 2.2 Ergonomics Issues

#### Issue: Verbose Enum Construction

**Current:**
```ritz
let opt = Option::Some(42)
let res = Result::Ok("success")
```

**Better (type inference):**
```ritz
let opt: Option<i32> = Some(42)
let res = Ok("success")  # infer Result type from context
```

**Recommendation:** Allow bare variant names when type is inferrable.

#### Issue: No Method Chaining on Primitives

**Current:**
```ritz
let s = int_to_string(42)
let len = string_len(s)
```

**Better:**
```ritz
let len = 42.to_string().len()
```

**Recommendation:** Support methods on primitive types via `impl`.

#### Issue: No String Interpolation Escaping

How to include a literal `{` in an interpolated string?

**Recommendation:** Use `{{` and `}}` for literal braces.

### 2.3 Type Inference Gaps

#### Ambiguous Literals

```ritz
let x = 42      # What type? i32? i64?
let y = 3.14    # f32 or f64?
```

**Current behavior:** Default to `i32` and `f64`.

**Concern:** Magic defaults can surprise.

**Recommendation:** Require type annotation when ambiguous in non-trivial contexts. Allow bare literals in simple cases.

#### Generic Inference

```ritz
let v = vec_new()  # What's T?
```

**Recommendation:** Error if T cannot be inferred. Require `vec_new::<i32>()` turbofish syntax.

---

## 3. String System Design

> ⭐ **MAJOR REDESIGN NEEDED** — The current `c""` and `s""` prefixes are awkward. Strings should be designed for Ritz developers first, with FFI as a secondary concern.

### 3.1 Current State (Problematic)

```ritz
"hello"     # String (heap-allocated, owned)
c"hello"    # *u8 (C-string, null-terminated)
s"hello"    # Span<u8> (slice with length)
```

**Problems:**
1. Prefixes `c` and `s` are cryptic and ugly
2. Default `"hello"` allocates — wasteful for literals
3. No clear hierarchy or relationship between types
4. Ownership semantics unclear

### 3.2 Prior Art: Zeus/Stingray StringBase

The Zeus/Stingray Traffic Manager had an elegant string hierarchy:

```
StringBase (abstract)
├── ConstString      # Zero-copy view (immutable window into any string)
├── MutableString    # Heap-allocated, growable
│   └── String       # The common "owned string"
├── FixedString<N>   # Stack-allocated, fixed capacity (template/generic)
└── StringV          # Vectored string for readv/writev (minimizes syscalls)
```

**Key Insight:** Ownership was implied by the type name, not sigils or prefixes. You could take a `ConstString` window into any `StringBase`.

### 3.3 Proposed Ritz String Hierarchy

```
Str (trait)
├── StrView          # Zero-copy slice (ptr + len), immutable
├── String           # Owned, heap-allocated, growable
├── StrBuf<N>        # Fixed-capacity buffer (stack or inline)
└── CStr             # Null-terminated C string (for FFI only)
```

#### Type Details

| Type | Ownership | Mutable | Allocation | Use Case |
|------|-----------|---------|------------|----------|
| `StrView` | Borrowed | No | None | Function parameters, string literals |
| `String` | Owned | Yes | Heap | Building strings, return values |
| `StrBuf<N>` | Owned | Yes | Stack/Inline | Fixed-size buffers, small strings |
| `CStr` | Borrowed | No | None | FFI interop only |

### 3.4 Literal Syntax (Proposed)

**Drop the prefixes entirely:**

```ritz
# Default: zero-copy view (most common case)
let greeting = "hello"          # StrView (zero-copy, points to static data)

# Explicit owned string when you need it
let name = String.from("world") # String (heap-allocated)

# Fixed buffer for performance
var buf: StrBuf<64>             # 64-byte inline buffer
buf.push_str("prefix: ")
buf.push_str(input)

# C strings only for FFI
extern fn puts(s: CStr) -> i32
puts("hello".as_cstr())         # Explicit conversion
```

### 3.5 Conversion Rules

```ritz
# StrView can be created from anything (zero-cost borrow)
fn log(msg: StrView)
    # ...

let s = String.from("hello")
log(s.view())       # String → StrView
log("literal")      # Literal → StrView (automatic)

# String requires explicit construction
let owned = "hello".to_string()   # Allocates, copies

# CStr requires explicit conversion (safety)
let cstr = "hello".as_cstr()      # Returns CStr (ensures null terminator)
```

### 3.6 String Builders

For efficient string construction:

```ritz
var builder = StringBuilder.new()
builder.push_str("Hello, ")
builder.push_str(name)
builder.push('!')
let result: String = builder.build()

# Or with capacity hint
var builder = StringBuilder.with_capacity(1024)
```

### 3.7 Vectored Strings (Future)

For high-performance I/O without copying:

```ritz
# Collect string fragments without copying
var parts = StringVec.new()
parts.push("HTTP/1.1 200 OK\r\n")
parts.push(headers)
parts.push("\r\n")
parts.push(body)

# Write all at once with writev
socket.write_vectored(parts)
```

### 3.8 Migration Path

| Current | Proposed | Notes |
|---------|----------|-------|
| `"hello"` | `"hello"` | Now returns `StrView` instead of `String` |
| `c"hello"` | `"hello".as_cstr()` | Explicit, intentional |
| `s"hello"` | `"hello"` | Default is now zero-copy |
| `String::from(...)` | `String.from(...)` | Same |

### 3.9 Design Principles

1. **Zero-copy by default** — Literals don't allocate
2. **Explicit allocation** — `String.from()` or `.to_string()` when you need ownership
3. **FFI is secondary** — C interop requires explicit `as_cstr()`, not a prefix
4. **Type names imply ownership** — No cryptic sigils
5. **Builders for construction** — Don't concatenate strings in loops

---

## 4. Pointer vs Reference Philosophy

> ⭐ **MAJOR REDESIGN NEEDED** — Ritz has drifted toward C-style pointer usage. The original vision was references by default, pointers only for kernel/FFI.

### 10.1 The Problem

The current codebase is littered with raw pointers:

```ritz
# Current (bad)
fn get_user(id: i64) -> *User
fn process(data: *u8, len: i64)
fn callback(ctx: *mut Context)
type Handler = fn(*Request, *mut Response) -> i32
```

This happened because:
1. Claude (the AI) confused Ritz with C/Rust
2. Early examples established pointer patterns
3. No clear guidance on when to use what

### 10.2 Original Vision

The original intent was:

| Concept | Syntax | Nullable | Arithmetic | When to Use |
|---------|--------|----------|------------|-------------|
| **Immutable borrow** | `&T` | No | No | Read-only access, most function params |
| **Mutable borrow** | `&mut T` | No | No | Modification without ownership transfer |
| **Move** | `T` | — | — | Transfer ownership |
| **Raw pointer** | `*T` | Yes | Yes | Kernel dev, FFI, unsafe code only |

### 10.3 Correct Usage Patterns

#### Function Parameters

```ritz
# GOOD: References for normal code
fn print_user(user: &User)
fn update_score(player: &mut Player, delta: i32)

# BAD: Pointers in normal code
fn print_user(user: *User)           # Why nullable?
fn update_score(player: *mut Player) # Why pointer arithmetic?
```

#### Return Values

```ritz
# GOOD: Return owned or Option
fn find_user(id: i64) -> Option<User>
fn find_user_ref(id: i64) -> Option<&User>  # If user lives in collection

# BAD: Return nullable pointer
fn find_user(id: i64) -> *User       # Caller must null-check manually
```

#### Collections

```ritz
# GOOD: References into collections
fn first(items: &Vec<T>) -> Option<&T>
fn get(map: &HashMap<K, V>, key: &K) -> Option<&V>

# BAD: Raw pointers
fn first(items: *Vec<T>) -> *T       # Double unsafe
```

### 10.4 When Pointers ARE Appropriate

Pointers should only appear in:

1. **FFI declarations**
   ```ritz
   extern fn malloc(size: u64) -> *u8
   extern fn free(ptr: *u8)
   ```

2. **Kernel/low-level code**
   ```ritz
   fn write_to_mmio(addr: *mut u32, value: u32)
       *addr = value
   ```

3. **Unsafe optimizations** (with `unsafe` block)
   ```ritz
   unsafe
       let raw = vec.as_mut_ptr()
       # ... pointer arithmetic for performance
   ```

4. **Self-referential structures** (rare)
   ```ritz
   struct Node<T>
       value: T
       next: *Node<T>  # Can't use &Node (lifetime issues)
   ```

### 4.5 Linting Rules (Proposed)

| Pattern | Severity | Message |
|---------|----------|---------|
| `*T` in function param | Warning | "Consider using `&T` instead of `*T`" |
| `*T` return type | Warning | "Consider using `Option<&T>` instead of `*T`" |
| `*mut T` outside `unsafe` | Error | "Mutable pointers require unsafe block" |
| Pointer arithmetic outside `unsafe` | Error | "Pointer arithmetic requires unsafe block" |

### 4.6 Migration Examples

**Before (pointer-heavy):**
```ritz
fn read_config(path: *u8) -> *Config
    let fd = open(path, O_RDONLY)
    if fd < 0
        return null
    let config = parse_config(fd)
    close(fd)
    return config

fn process_users(users: *Vec<User>, count: i64)
    var i: i64 = 0
    while i < count
        let user = vec_get(users, i)
        if user != null
            print_user(user)
        i += 1
```

**After (reference-based):**
```ritz
fn read_config(path: StrView) -> Result<Config, Error>
    let fd = open(path, O_RDONLY)?
    let config = parse_config(fd)?
    close(fd)
    Ok(config)

fn process_users(users: &Vec<User>)
    for user in users
        print_user(&user)
```

### 4.7 Type Signatures Cheat Sheet

| Intent | Use This | Not This |
|--------|----------|----------|
| Read data | `&T` | `*T` |
| Modify data | `&mut T` | `*mut T` |
| Transfer ownership | `T` | `*T` |
| Maybe return something | `Option<T>` | `*T` that might be null |
| Error or value | `Result<T, E>` | Return code + out param |
| String parameter | `StrView` | `*u8` |
| Pass to C | `*u8` (in FFI block) | — |

### 4.8 Standard Library Audit Needed

The ritzlib modules need review to replace pointer-based APIs with reference-based ones:

| Module | Current | Should Be |
|--------|---------|-----------|
| `io` | `read(fd, buf: *u8, len)` | `read(fd, buf: &mut [u8])` |
| `str` | `strlen(s: *u8)` | `s.len()` method on StrView |
| `memory` | `memcpy(dst: *u8, src: *u8, n)` | `dst.copy_from(src)` method |
| `gvec` | `vec_get(v: *Vec, i) -> *T` | `v.get(i) -> Option<&T>` |

---

## 5. Security Review

### 9.1 Memory Safety

| Feature | Status | Notes |
|---------|--------|-------|
| Use-after-free | ✅ Prevented | Ownership + borrow checker |
| Double-free | ✅ Prevented | Single owner rule |
| Null dereference | ⚠️ Partial | `*T` can be null, `&T` cannot |
| Buffer overflow | ⚠️ Runtime | Array bounds checked at runtime |
| Integer overflow | ❌ Unchecked | Wraps silently in release mode |

### 9.2 Footguns Identified

#### Footgun 1: Nullable Pointers Are Easy to Forget

```ritz
fn get_user(id: i64) -> *User
    # ...
    return null  # Easy to write

let user = get_user(42)
user.name  # CRASH if null
```

**Mitigation:** Prefer `Option<&User>` over `*User`. Lint for `*T` return types.

#### Footgun 2: Union Types with `null`

```ritz
type Nullable<T> = T | null
```

This is fine, but:

```ritz
type Confused = i32 | String | null
```

What happens on pattern match failure? Silent null?

**Recommendation:** Require exhaustive matching. Compiler error on unhandled variants.

#### Footgun 3: Raw Pointer Arithmetic

```ritz
let p: *u8 = buffer
let q = p + 1000000  # No bounds check
*q = 42  # Buffer overflow
```

**Recommendation:**
- Require `unsafe` block for pointer arithmetic
- Or use `Span<T>` with bounds checking

#### Footgun 4: Integer Overflow

```ritz
let x: u8 = 255
let y = x + 1  # Wraps to 0 silently
```

**Recommendation:**
- Debug mode: Panic on overflow
- Release mode: Wrap (with explicit opt-in)
- Add `wrapping_add()`, `saturating_add()`, `checked_add()` methods

#### Footgun 5: Uninitialized Arrays

```ritz
var buffer: [1024]u8  # Contains garbage
```

**Recommendation:** Either:
- Require initialization: `var buffer: [1024]u8 = [0; 1024]`
- Or zero-initialize by default (slight perf cost)
- At minimum, lint for use of uninitialized arrays

### 9.3 Missing Safety Features

| Feature | Importance | Notes |
|---------|------------|-------|
| Lifetime annotations | Low | Implicit lifetimes work for simple cases |
| Const generics | Medium | `[N]T` works, but can't parameterize N |
| Bounds checking bypass | High | Need `unsafe` for unchecked access |
| Thread safety | High | No Send/Sync traits yet |

---

## 6. Syntax Consistency

### 10.1 Operator Keywords vs Symbols

**Inconsistency:** Logical operators have two forms:

```ritz
# Keywords (in LANGUAGE_SPEC)
a and b
a or b
not a

# Symbols (in GRAMMAR)
a && b
a || b
!a
```

**Question:** Which is canonical? Pick one.

**Recommendation:** Use symbols (`&&`, `||`, `!`) for consistency with C-family languages. Reserve keywords for future features.

### 10.2 Method Definition Syntax

**Current (two forms):**

```ritz
# Form 1: Inside impl block
impl Point
    fn distance(self: &Point) -> i32
        # ...

# Form 2: Associated function syntax
fn Point.distance(self: &Point) -> i32
    # ...
```

**Recommendation:** Deprecate Form 2. Methods belong in `impl` blocks.

### 10.3 Loop Inconsistency

**Current:**
```ritz
while condition
    # ...

for i in range
    # ...

loop
    # ...
```

**Issue:** `loop` is in the language spec but not the grammar.

**Recommendation:** Add `loop` to grammar. It's useful and expected.

### 10.4 Closure Syntax

**Functions:**
```ritz
fn add(a: i32, b: i32) -> i32
    a + b
```

**Closures:**
```ritz
let add = |a: i32, b: i32| -> i32
    a + b
```

**Issue:** Different syntax for same concept.

**Alternative (more uniform):**
```ritz
let add = fn(a: i32, b: i32) -> i32
    a + b
```

**Recommendation:** Keep `|...|` for closures. It's established (Rust) and visually distinct. But ensure closure bodies follow same indentation rules.

---

## 7. Aesthetics & Polish

### 9.1 Visual Noise Analysis

**Low noise (good):**
```ritz
fn greet(name: *u8)
    print("Hello, ")
    print(name)
    print("\n")
```

**Higher noise:**
```ritz
fn process<T, E>(items: Vec<T>) -> Result<Vec<T>, E>
    var results: Vec<T> = vec_new::<T>()
    for item in items
        let processed = transform::<T>(item)?
        results.push(processed)
    Ok(results)
```

**Pain points:**
- Turbofish `::<T>` is visually noisy
- Generic bounds would add more

**Recommendation:** Improve type inference to reduce turbofish usage.

### 9.2 Keyword Choice

| Keyword | Assessment | Alternative? |
|---------|------------|--------------|
| `fn` | ✅ Good | Short, clear |
| `let` | ✅ Good | Standard |
| `var` | ✅ Good | Clear mutability |
| `struct` | ✅ Good | Familiar |
| `enum` | ✅ Good | Familiar |
| `impl` | ✅ Good | Rust standard |
| `trait` | ✅ Good | Rust standard |
| `pub` | ✅ Good | Short, clear |
| `extern` | ✅ Good | Familiar |
| `match` | ✅ Good | Familiar |
| `mut` | 🤔 Mixed | Only used in `&mut`, `*mut` |

### 9.3 Sigil Usage

| Sigil | Meaning | Clarity |
|-------|---------|---------|
| `*` | Pointer / Dereference / Multiply | ⚠️ Overloaded |
| `&` | Reference / Address-of / Bitwise AND | ⚠️ Overloaded |
| `@` | Attribute prefix | ✅ Clear |
| `?` | Try operator | ✅ Clear |
| `!` | Not (logical) | ✅ Clear |
| `~` | Bitwise NOT | ✅ Clear |

**Concern:** `*` and `&` are context-dependent. This is inherited from C/Rust, but can confuse.

**Recommendation:** Accept this as standard. Good error messages help.

### 7.4 Code Samples That Look Good

```ritz
# Clean struct with impl
struct Point
    x: i32
    y: i32

impl Point
    fn new(x: i32, y: i32) -> Point
        Point { x: x, y: y }

    fn distance(self: &Point) -> f64
        let sq = self.x * self.x + self.y * self.y
        sqrt(sq as f64)

# Clean error handling
fn read_config(path: *u8) -> Result<Config, Error>
    let content = read_file(path)?
    let parsed = parse_json(content)?
    Ok(parsed)

# Clean match
match result
    Ok(value) => process(value)
    Err(e) => log_error(e)
```

### 7.5 Code Samples That Need Work

```ritz
# Verbose generics
fn map<T, U, F: Fn(T) -> U>(items: Vec<T>, f: F) -> Vec<U>
    # This doesn't exist yet, but would be verbose

# Unclear type relationships
type Handler = fn(*Request, *mut Response) -> Result<(), *Error>
```

---

## 8. Error Messages

### 10.1 Current State

Error messages are generated by ritz0 (Python). Quality varies.

### 10.2 Required Error Categories

| Category | Example |
|----------|---------|
| Syntax | "Expected `:` after parameter name" |
| Type | "Cannot assign `String` to variable of type `i32`" |
| Ownership | "Cannot borrow `x` as mutable, already borrowed as immutable" |
| Undefined | "Unknown function `foo`" |
| Import | "Module `bar` not found" |

### 10.3 Best Practices

1. **Point to the problem:**
   ```
   Error: Type mismatch
     --> src/main.ritz:10:5
      |
   10 |     x = "hello"
      |         ^^^^^^^ expected i32, found String
      |
      = note: variable x declared as i32 at line 5
   ```

2. **Suggest fixes:**
   ```
   Error: Unknown variable `count`
     --> src/main.ritz:15:10
      |
   15 |     print(count)
      |           ^^^^^ not found in this scope
      |
      = help: did you mean `counter`?
   ```

3. **Explain ownership:**
   ```
   Error: Cannot move out of borrowed reference
     --> src/main.ritz:20:5
      |
   18 |     let r = &s
      |             -- borrow of `s` starts here
   19 |
   20 |     consume(s)
      |             ^ cannot move `s` while borrowed
      |
      = note: consider cloning: `consume(s.clone())`
   ```

### 10.4 Recommendations

- [ ] Implement error codes (E0001, E0002, ...)
- [ ] Add `--explain E0001` for detailed explanations
- [ ] Color-code output (errors red, warnings yellow, help blue)
- [ ] Test error messages as part of CI

---

## 9. Optimization Opportunities

### 9.1 Language Features That Enable Optimization

| Feature | Optimization Enabled |
|---------|---------------------|
| Immutable by default (`let`) | Safe to cache, parallelize |
| No aliasing (ownership) | Aggressive dead store elimination |
| Static dispatch (monomorphization) | Inline everything |
| No GC | Predictable latency |
| Value types (structs) | Stack allocation, no indirection |

### 9.2 Missing Features for Optimization

| Feature | Benefit | Priority |
|---------|---------|----------|
| `const fn` | Compile-time evaluation | High |
| SIMD intrinsics | Vector math | Medium |
| `#[cold]`/`#[hot]` | Branch prediction hints | Low |
| Profile-guided optimization | Data-driven inlining | Low |

### 9.3 Performance Traps to Document

1. **String concatenation in loops** — Use a builder
2. **Vec growth** — Pre-size with capacity
3. **Deep recursion** — No tail call optimization (yet)
4. **Hash map iteration order** — Not guaranteed

---

## 10. Recommendations

### 10.1 Critical (Blocking 1.0)

| # | Recommendation | Impact | Section |
|---|----------------|--------|---------|
| 1 | **Redesign string system** | Drop `c""`/`s""` prefixes. Use type hierarchy (`StrView`, `String`, `StrBuf<N>`, `CStr`). Zero-copy by default. | §3 |
| 2 | **Establish reference-first culture** | `&T` and `&mut T` for normal code. `*T` only for FFI/kernel. Lint for pointer misuse. | §4 |
| 3 | **Audit ritzlib for pointer removal** | Replace `*T` params/returns with references throughout standard library. | §4.8 |

### 10.2 High Priority (Before 1.0)

| # | Recommendation | Impact |
|---|----------------|--------|
| 4 | **Standardize logical operators** | Pick `&&`/`||` OR `and`/`or`, not both |
| 5 | **Add integer overflow checks in debug** | Catch bugs early |
| 6 | **Require exhaustive match** | No silent null matches |
| 7 | **Add `loop` keyword** | Document says it exists, grammar doesn't |

### 10.3 Medium Priority (Quality of Life)

| # | Recommendation | Impact |
|---|----------------|--------|
| 8 | Allow bare enum variants | `Some(x)` instead of `Option::Some(x)` |
| 9 | Methods on primitives | `42.to_string()` |
| 10 | Better error messages | Add codes, colors, suggestions |
| 11 | Zero-initialize arrays by default | Prevent use of uninitialized memory |
| 12 | Add `{{` escape in string interpolation | Complete the feature |
| 13 | Add `StringBuilder` to stdlib | Efficient string building |

### 10.4 Low Priority (Future)

| # | Recommendation | Impact |
|---|----------------|--------|
| 14 | Trait bounds syntax | For generic constraints |
| 15 | `const fn` | Compile-time evaluation |
| 16 | SIMD support | Performance |
| 17 | Async cleanup | Structured concurrency |
| 18 | `StringVec` for vectored I/O | High-performance network code |

### 10.5 Non-Goals

- **Don't add:** Exceptions (keep Result/Option)
- **Don't add:** Garbage collection (ownership is working)
- **Don't add:** Inheritance (traits are sufficient)
- **Don't add:** Null coalescing operator (use match)

---

## Summary

Ritz has strong foundations but needs two major redesigns before 1.0:

### Critical Path to Sexy

1. **String System Redesign (§3)**
   - Drop awkward `c""`/`s""` prefixes
   - Type hierarchy: `StrView` (default), `String`, `StrBuf<N>`, `CStr`
   - Zero-copy by default, explicit allocation
   - FFI is secondary, not primary

2. **Reference-First Culture (§4)**
   - `&T` and `&mut T` for normal Ritz code
   - `*T` only for FFI/kernel/unsafe
   - Audit entire ritzlib to remove unnecessary pointers
   - Add lints to discourage pointer usage

### Secondary Improvements

3. **Consistency** — Pick one form for operators (`&&` vs `and`)
4. **Safety defaults** — Integer overflow checks in debug, zero-init arrays
5. **Ergonomics** — Reduce turbofish, better inference

### The Vision

Ritz should feel like **Python's syntax** meets **Rust's safety** with **better defaults**. When you write Ritz, you shouldn't feel like you're fighting the language or memorizing cryptic sigils. The happy path should be obvious and safe.

With these changes, Ritz goes from 7/10 to 9/10—a language that makes you *want* to play with it.

---

*This review is maintained by LARB. Feedback welcome.*
