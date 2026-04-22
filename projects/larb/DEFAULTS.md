# Ritz Defaults & Least-Syntax Principle

> LARB-0014: Language Default Semantics
>
> Status: AUTHORITATIVE
> Author: Aaron Sinclair
> Date: 2026-04-22

## Core Principle

**The most common operation should have the least syntax.**

Ritz optimizes for the common case at every level — parameters, types, strings,
attributes, operators. If you're doing the normal thing, you write less. If
you're doing something unusual (mutation, ownership transfer, unsafe), you write
more. The syntax makes intent visible by its *deviation* from the default.

---

## 1. Parameter Passing

The colon modifier determines ownership semantics. The bare colon (`:`) is the
default — immutable borrow — which is what you want 90% of the time.

```ritz
# DEFAULT: immutable borrow (const ref) — bare colon, zero noise
fn process(data: Vec<u8>) -> i32
    # data is borrowed immutably
    # you can read it, but not modify or consume it
    return data.len() as i32

# MUTATION: mutable borrow — one character extra (:&)
fn sort(data:& Vec<u8>) -> i32
    # :& says "I WILL modify this"
    # caller still owns it, gets it back modified
    data.reverse()
    return 0

# OWNERSHIP: move/transfer — two characters extra (:=)
fn consume(data:= Vec<u8>) -> i32
    # := says "I'm TAKING this — caller can't use it after"
    # the value is moved into this function
    free(data)
    return 0
```

### Why This Works

| Operation | Frequency | Syntax | Extra chars |
|-----------|-----------|--------|-------------|
| Read (immutable borrow) | ~70% | `x: T` | 0 |
| Mutate (mutable borrow) | ~20% | `x:& T` | 1 (`&`) |
| Take ownership (move) | ~10% | `x:= T` | 2 (`:=`) |

The syntax cost scales with the risk:
- Reading is safe → free
- Mutation can cause bugs → 1 char tax
- Ownership transfer can cause use-after-free → 2 char tax

### Return Values

Returns are always owned. No annotation needed — the function produces a value
and the caller takes ownership. This is the only sensible default.

```ritz
fn create() -> Vec<u8>
    # No ownership annotation on return — always owned
    var result: Vec<u8> = Vec::new()
    result.push(42)
    return result  # ownership transfers to caller
```

---

## 2. Reference Types

The `@` operator replaces `&` for references. Bare `@` is immutable (the
default). `@&` is mutable.

```ritz
# DEFAULT: immutable reference type
fn len(s: @Vec<u8>) -> i64
    return s.len

# MUTATION: mutable reference type
fn push(s: @&Vec<u8>, val: u8)
    # ...

# Address-of operator
let ptr: @Vec<u8> = @my_vec        # immutable ref
let mut_ptr: @&Vec<u8> = @&my_vec  # mutable ref
```

### Why `@` Instead of `&`

`&` is bitwise AND. Period. No overloading, no ambiguity. `@` is visually
distinct and doesn't conflict with any operator. The ampersand doing double
duty (bitwise AND and reference) in C/C++/Rust is a constant source of
parsing ambiguity and reader confusion.

---

## 3. Pointer Types

```ritz
*T      # immutable raw pointer (default)
*&T     # mutable raw pointer
```

Same pattern: bare is immutable, `&` suffix means mutable.

---

## 4. String Literals

```ritz
"hello"     # StrView (zero-copy, compile-time length) — THE DEFAULT
c"hello"    # *u8 null-terminated C string (FFI interop)
s"hello"    # Span/slice (when you need it)
```

The default `"hello"` is a StrView — a pointer + length pair with the length
computed at compile time. No heap allocation, no null terminator scanning.
This is what you want 95% of the time.

C strings (`c"..."`) are explicit opt-in for interop. You pay for what you use.

---

## 5. Attributes

```ritz
[[test]]                            # Test function
[[inline]]                          # Inline hint
[[target_os = "linux"]]             # Conditional compilation
[[cfg(all(debug, target_arch = "x86_64"))]]  # Complex conditions
[[packed]]                          # No struct padding
[[naked]]                           # No function prologue/epilogue
```

One syntax: `[[name]]` or `[[name = value]]` or `[[name(expr)]]`. No `@`
prefix (that's address-of), no `#[...]` (that's ambiguous with array indexing
in some contexts). Double brackets are unambiguous and visually distinct.

---

## 6. Logical Operators

```ritz
if x > 0 and y > 0        # not &&
if x > 0 or y > 0         # not ||
if not done                # not !
```

English words are the canonical form. `&&`/`||`/`!` are accepted for
familiarity but `and`/`or`/`not` are preferred and documented.

Why: `!` is easy to miss in code review. `not` is unmissable. `&&`/`||` are
visual noise. `and`/`or` read like prose.

---

## 7. Blocks

Indentation-based. No braces, no `end`, no `do`.

```ritz
fn example(x: i32) -> i32
    if x > 0
        return x * 2
    else
        return 0
```

The indentation IS the structure. Like Python, but with static types and
ownership. No ceremony.

---

## 8. Variable Bindings

```ritz
let x: i32 = 42           # immutable binding (default)
var y: i32 = 42            # mutable binding (explicit)
const Z: i32 = 42          # compile-time constant
```

`let` is the default. `var` signals "this will change." The naming follows
the principle: the common case (immutable) uses the shorter, simpler keyword.

---

## 9. Visibility

```ritz
fn internal_helper()       # private (default) — no annotation
    pass

pub fn api_function()      # public — explicit opt-in
    pass
```

Private by default. You explicitly choose to expose things. This is the safe
default — accidental exposure is worse than accidental hiding.

---

## 10. Error Handling

```ritz
# The ? operator propagates errors with zero syntax overhead
fn read_config(path: StrView) -> Result<Config, Error>
    let data: Vec<u8> = read_file(path)?     # propagate on error
    let config: Config = parse(data)?         # propagate on error
    return Ok(config)
```

`?` is the default error handling. No try/catch, no exceptions, no panics
for recoverable errors. The type system (Result<T, E>) encodes fallibility.

---

## 11. Summary: The Syntax Tax Table

| What you're doing | Syntax | Tax | Justification |
|-------------------|--------|-----|---------------|
| Immutable borrow | `x: T` | 0 | Most common, safest |
| Mutable borrow | `x:& T` | +1 | Mutation is notable |
| Ownership transfer | `x:= T` | +2 | Ownership change is significant |
| Immutable ref type | `@T` | 0 | Most common ref |
| Mutable ref type | `@&T` | +1 | Mutation is notable |
| Immutable pointer | `*T` | 0 | Most common pointer |
| Mutable pointer | `*&T` | +1 | Mutation is notable |
| Immutable binding | `let` | 0 | Most common |
| Mutable binding | `var` | 0 | Different keyword signals intent |
| Private function | `fn` | 0 | Safe default |
| Public function | `pub fn` | +3 | Explicit exposure |
| Normal string | `"..."` | 0 | StrView, zero-copy |
| C interop string | `c"..."` | +1 | Explicit FFI |
| Logical AND | `and` | 0 | Reads like prose |
| Error propagation | `?` | +1 | Minimal, visible |

**The pattern: safety is free, risk costs characters.**

---

## 12. What We Cut (No Backward Compat)

These syntaxes are **dead**. The compiler rejects them with no migration path:

| Dead Syntax | Replacement | Status |
|-------------|-------------|--------|
| `&x` (reference) | `@x` | Error |
| `&mut x` | `@&x` | Error |
| `&T` (ref type) | `@T` | Error |
| `&mut T` | `@&T` | Error |
| `*mut T` | `*&T` | Error |
| `@test` (attribute) | `[[test]]` | Error |
| `@inline` | `[[inline]]` | Error |
| `let mut x` | `var x` | Error |
| `&&` / `||` / `!` | `and` / `or` / `not` | Accepted but not canonical |

No deprecation warnings. No migration helpers. No backward compatibility.
The old syntax is gone. Cut with prejudice.
