# Ritz Style Guide

**LARB Document** | **Status:** Approved | **Version:** 1.0 | **Date:** 2026-02-14

This document defines the canonical coding style for Ritz programs across the ecosystem. Following these conventions ensures consistency, readability, and maintainability.

---

## Table of Contents

1. [Naming Conventions](#1-naming-conventions)
2. [Formatting](#2-formatting)
3. [Code Organization](#3-code-organization)
4. [Documentation](#4-documentation)
5. [Ownership and Safety](#5-ownership-and-safety)
6. [Testing](#6-testing)
7. [Best Practices](#7-best-practices)

---

## 1. Naming Conventions

### 1.1 Functions and Variables

Use **snake_case** for functions and variables:

```ritz
fn calculate_hash(input: StrView) -> u64
    let hash_value: u64 = 0
    var current_byte: u8 = 0
    # ...
```

**Guidelines:**
- Use descriptive names that convey purpose
- Prefer `is_` prefix for boolean-returning functions: `is_empty()`, `is_valid()`
- Use `_` prefix for unused variables: `let _unused = compute()`

### 1.2 Types, Structs, and Enums

Use **PascalCase** for type names:

```ritz
struct HashMapEntry
    key: i64
    value: i64
    state: i32

enum TokenKind
    Identifier
    Number
    StringLiteral
    LeftParen
    RightParen

struct Parser<T>
    tokens: Vec<T>
    current: i64
```

**Guidelines:**
- Structs should be nouns: `Parser`, `Connection`, `Arena`
- Enums should be nouns or adjectives: `Color`, `State`, `TokenKind`
- Enum variants are also PascalCase: `Some`, `None`, `Ok`, `Err`

### 1.3 Constants

Use **SCREAMING_SNAKE_CASE** for constants:

```ritz
const MAX_BUFFER_SIZE: i64 = 4096
const ARENA_DEFAULT_SIZE: i64 = 1048576
const TOK_EOF: i32 = 0
const PROT_READ: i32 = 1
const PROT_WRITE: i32 = 2
```

**Guidelines:**
- Constants must have explicit types
- Group related constants together
- Use constants for magic numbers and configuration values

### 1.4 Generic Type Parameters

Use single uppercase letters following these conventions:

| Parameter | Common Usage |
|-----------|--------------|
| `T` | Primary type parameter |
| `U` | Secondary type parameter |
| `K` | Key type (in maps) |
| `V` | Value type (in maps) |
| `E` | Error type (in Result) |
| `A`, `B` | Pair types |
| `N` | Numeric/size parameter |

```ritz
fn swap<T>(a: @&T, b: @&T)
    # ...

struct HashMap<K, V>
    entries: *HashMapEntry<K, V>
    len: i64

enum Result<T, E>
    Ok(T)
    Err(E)
```

### 1.5 Module Names

Use **snake_case** for module and file names:

```
ritzlib/
    memory.ritz
    hash_map.ritz
    async_tasks.ritz
    io.ritz
```

**Guidelines:**
- Module names should be short but descriptive
- Use underscores to separate words: `async_runtime`, not `asyncruntime`
- Avoid redundant prefixes: `json.ritz`, not `json_parser.ritz`

---

## 2. Formatting

### 2.1 Indentation

Use **4 spaces** for indentation. Tabs are prohibited.

```ritz
fn example(x: i32) -> i32
    if x > 0
        let result: i32 = x * 2
        return result
    else
        return 0
```

### 2.2 Line Length

- Maximum **100 characters** per line
- Break long expressions at operators or after commas
- Break function signatures after the return type arrow if needed

```ritz
# Good: fits on one line
fn add(a: i32, b: i32) -> i32

# Good: long signature broken appropriately
fn process_complex_data(
    input: DataSet,
    config: ProcessConfig,
    options: ProcessOptions
) -> Result<Output, ProcessError>
    # ...
```

### 2.3 Blank Lines

- **Two blank lines** between top-level items (functions, structs, impl blocks)
- **One blank line** to separate logical sections within functions
- **No more than 2 consecutive blank lines**

```ritz
struct Point
    x: i32
    y: i32


fn point_new(x: i32, y: i32) -> Point
    Point { x: x, y: y }


fn point_distance(p: @Point) -> f64
    let x_sq: f64 = (p.x * p.x) as f64
    let y_sq: f64 = (p.y * p.y) as f64

    sqrt(x_sq + y_sq)
```

### 2.4 Spacing

**Around operators:**
```ritz
# Good
let result = a + b * c
if x == 0 && y > 10
mask = flags & 0xFF

# Bad
let result=a+b*c
if x==0&&y>10
```

**After commas:**
```ritz
# Good
fn foo(a: i32, b: i32, c: i32)
let arr = [1, 2, 3, 4]

# Bad
fn foo(a: i32,b: i32,c: i32)
```

**No space inside parentheses or brackets:**
```ritz
# Good
foo(x, y)
arr[i]

# Bad
foo( x, y )
arr[ i ]
```

**No space after unary operators:**
```ritz
# Good
-x
!flag
*ptr
@value

# Bad
- x
! flag
```

### 2.5 Alignment

Align struct fields and related declarations when it improves readability:

```ritz
struct Arena
    base:   *u8     # Base pointer from mmap
    size:   i64     # Total size of arena
    offset: i64     # Current allocation offset

const TOK_IDENT:  i32 = 1
const TOK_NUMBER: i32 = 2
const TOK_STRING: i32 = 3
const TOK_EOF:    i32 = 4
```

---

## 3. Code Organization

### 3.1 Import Ordering and Grouping

Group imports by category, sorted alphabetically within each group:

```ritz
# Standard library imports (ritzlib)
import ritzlib.io
import ritzlib.memory
import ritzlib.sys
import ritzlib.str

# External package imports
import cryptosec.aes
import squeeze.gzip

# Local/sibling module imports
import parser
import tokens
import types
```

### 3.2 File Structure

Organize files in this order:

1. **Module documentation** (header comment)
2. **Imports**
3. **Constants**
4. **Type definitions** (structs, enums)
5. **Trait implementations**
6. **Constructors** (e.g., `_new`, `_default`)
7. **Core functions** (primary functionality)
8. **Helper functions** (internal utilities)
9. **Tests** (if in the same file)

```ritz
# ritzlib/vec.ritz - Generic dynamic array
#
# Vec<T> provides a growable array for any type T.

import ritzlib.memory

# ============================================================================
# Constants
# ============================================================================

const DEFAULT_CAPACITY: i64 = 8


# ============================================================================
# Vec<T> - Generic Dynamic Array
# ============================================================================

struct Vec<T>
    data: *T
    len: i64
    cap: i64


# ============================================================================
# Drop trait implementation
# ============================================================================

impl<T> Drop for Vec<T>
    fn drop(self:& Vec<T>)
        if self.data != null
            free(self.data as *u8)


# ============================================================================
# Constructors
# ============================================================================

pub fn vec_new<T>() -> Vec<T>
    # ...


# ============================================================================
# Core Operations
# ============================================================================

pub fn vec_push<T>(v:& Vec<T>, item: T) -> i32
    # ...
```

### 3.3 Section Headers

Use comment banners to separate major sections:

```ritz
# ============================================================================
# Section Name
# ============================================================================
```

### 3.4 Function Ordering Within Modules

1. **Constructors** first: `new()`, `with_capacity()`, `default()`
2. **Accessors**: `len()`, `cap()`, `is_empty()`, `get()`
3. **Mutators**: `push()`, `pop()`, `insert()`, `remove()`
4. **Converters**: `as_ptr()`, `as_slice()`, `into_iter()`
5. **Internal helpers** last (non-pub functions)

### 3.5 Struct Field Ordering

Order struct fields by:

1. **Pointers** first (data, next, parent)
2. **Sizes/lengths** second (len, cap, size)
3. **State/flags** third (state, flags, initialized)
4. **Metadata** last (name, id)

```ritz
struct Vec<T>
    data: *T       # Pointer first
    len: i64       # Sizes second
    cap: i64

struct HashMapEntry
    key: i64       # Data fields
    value: i64
    state: i32     # State last
```

### 3.6 When to Split into Multiple Files

Split a module into multiple files when:

- A single file exceeds **500 lines**
- There are distinct logical components
- Tests are extensive

Use a directory structure:

```
async/
    mod.ritz       # Re-exports, main interface
    executor.ritz  # Async executor
    task.ritz      # Task definition
    io.ritz        # Async I/O operations
```

---

## 4. Documentation

### 4.1 Comment Style

Ritz uses `#` for comments:

```ritz
# Single-line comment

# Multi-line comments
# use multiple single-line
# comment markers
```

### 4.2 When to Document

**Always document:**
- All `pub` functions
- All `pub` structs and enums
- Complex algorithms or non-obvious logic
- Module-level purpose (file header)

**Documentation not required for:**
- Private helper functions with obvious purpose
- Trivial getters/setters
- Test functions (the test name should be self-documenting)

### 4.3 Documentation Format

**File headers:**
```ritz
# ritzlib/json.ritz - JSON parsing and serialization
#
# Provides RFC 8259 compliant JSON parsing with streaming support.
# Allocates using the provided arena; no global state.
#
# Usage:
#   var arena = Arena.new()
#   let result = json_parse(arena, input, len)
#   match result
#       Ok(value) => process(value)
#       Err(e) => handle_error(e)
```

**Function documentation:**
```ritz
# Allocate `size` bytes from the arena.
# Returns pointer to allocated memory, or null on failure.
# Memory is 8-byte aligned.
pub fn arena_alloc(a:& Arena, size: i64) -> *u8
    # ...
```

**Struct documentation:**
```ritz
# Arena allocator for fast bump allocation.
# Memory is freed all at once via reset() or destroy().
# Ideal for parsers, compilers, and request-scoped allocations.
struct Arena
    base: *u8       # Base pointer from mmap
    size: i64       # Total size of arena
    offset: i64     # Current allocation offset (next free byte)
```

### 4.4 Comment Placement

- Place comments **above** the item they describe
- Use inline comments sparingly, only for brief clarifications
- Never use comments to explain bad code; rewrite the code instead

```ritz
# Good: comment explains why
# Use multiplication by golden ratio for better hash distribution
let hash = (key * 0x9E3779B97F4A7C15) >> (64 - bits)

# Good: inline comment for magic number
buf[0] = 45  # '-' character

# Bad: comment explains what (obvious from code)
# Add one to i
i += 1
```

---

## 5. Ownership and Safety

### 5.1 Colon-Modifier Syntax

Ritz uses colon-modifiers in function **signatures** to express ownership:

| Syntax | Meaning | Frequency |
|--------|---------|-----------|
| `x: T` | Const borrow (immutable reference) | ~70% |
| `x:& T` | Mutable borrow (can modify) | ~20% |
| `x:= T` | Move ownership (caller gives up ownership) | ~10% |

**The Golden Rule:** The common case (const borrow) has zero syntax overhead.

```ritz
# Const borrow - just read the data
fn calculate_hash(data: StrView) -> u64
    # data is borrowed immutably

# Mutable borrow - modify in place
fn increment(counter:& i32)
    *counter += 1

# Move ownership - caller gives up the value
fn consume_connection(conn:= Connection)
    # conn is now owned by this function
```

**Call sites are always clean:**
```ritz
# No sigils at call sites - Ritz, not Rust
increment(n)           # Not: increment(&mut n)
calculate_hash(data)   # Not: calculate_hash(&data)
consume(conn)          # Not: consume(conn) (same, but ownership transfers)
```

### 5.2 Address-Of Operators

Use `@` for taking addresses (references):

```ritz
let ptr = @x          # Immutable reference to x (type: @T)
let mptr = @&x        # Mutable reference to x (type: @&T)
```

### 5.3 Resource Cleanup with `defer`

Use `defer` for cleanup operations that must run at scope exit:

```ritz
fn read_config(path: StrView) -> Result<Config, Error>
    let fd = sys_open(path.as_cstr(), O_RDONLY)?
    defer sys_close(fd)     # Always close, even on error

    let arena = Arena.new()
    defer arena.destroy()   # Clean up arena

    # ... read and parse ...
    Ok(config)
```

**Guidelines:**
- Place `defer` immediately after acquiring a resource
- Multiple defers execute in **reverse order** (LIFO)
- Prefer `defer` over manual cleanup at each return point

### 5.4 Error Handling: Result vs Panic

**Use `Result<T, E>` for:**
- Operations that can fail (I/O, parsing, allocation)
- Errors that callers should handle
- Library functions

```ritz
fn parse_int(s: StrView) -> Result<i64, ParseError>
    if s.is_empty()
        return Err(ParseError::EmptyInput)
    # ...
    Ok(value)
```

**Use panic (via `assert`) for:**
- Programming errors (logic bugs, invariant violations)
- Unrecoverable states
- Debug-only checks

```ritz
fn vec_get<T>(v: @Vec<T>, idx: i64) -> T
    assert idx >= 0 && idx < v.len   # Panic if out of bounds
    *(v.data + idx)
```

### 5.5 The `?` Operator

Propagate errors with `?`:

```ritz
fn load_and_parse(path: StrView) -> Result<Data, Error>
    let content = read_file(path)?      # Returns Err if read fails
    let parsed = parse_json(content)?   # Returns Err if parse fails
    Ok(parsed)
```

### 5.6 Initialization Patterns

**Always initialize variables:**
```ritz
# Good: explicit initialization
var count: i64 = 0
var ptr: *u8 = null

# Use zeroed() or uninit() for arrays
var buffer: [1024]u8 = zeroed()      # Zero-initialized
var scratch: [256]u8 = uninit()      # Explicit uninitialized (for performance)
```

---

## 6. Testing

### 6.1 Test Naming

Use descriptive names that explain **what is being tested** and **expected outcome**:

```ritz
[[test]]
fn test_arena_alloc_returns_aligned_pointer() -> i32
    # ...

[[test]]
fn test_vec_push_grows_capacity_when_full() -> i32
    # ...

[[test]]
fn test_parse_invalid_json_returns_error() -> i32
    # ...
```

**Naming pattern:** `test_<unit>_<behavior>` or `test_<action>_<expected_result>`

### 6.2 Test Organization

**For ritzlib modules:**
- Place tests in `ritzlib/tests/test_<module>.ritz`
- One test file per module

```
ritzlib/
    memory.ritz
    gvec.ritz
    tests/
        test_memory.ritz
        test_gvec.ritz
```

**For applications:**
- Place tests in `test/` directory adjacent to `src/`

```
myapp/
    src/
        main.ritz
    test/
        test_main.ritz
```

### 6.3 Test File Structure

```ritz
# Test suite for ritzlib/memory.ritz
#
# Tests the Arena allocator and heap functions.

import ritzlib.memory
import ritzlib.sys

# ============================================================================
# Arena Tests
# ============================================================================

[[test]]
fn test_arena_new() -> i32
    var a = arena_new(4096)
    assert arena_valid(@a) == 1
    assert arena_used(@a) == 0
    arena_destroy(@a)
    0


[[test]]
fn test_arena_alloc() -> i32
    var a = arena_new(4096)

    let p = arena_alloc(@a, 100)
    assert p != null

    arena_destroy(@a)
    0


# ============================================================================
# Heap Tests
# ============================================================================

[[test]]
fn test_heap_alloc_free() -> i32
    # ...
```

### 6.4 Test Return Values

Tests return `i32`:
- `0` = **PASS**
- Non-zero = **FAIL**

```ritz
[[test]]
fn test_addition() -> i32
    if 2 + 2 == 4
        return 0    # Pass
    return 1        # Fail
```

### 6.5 Assertion Usage

Use `assert` for test conditions:

```ritz
[[test]]
fn test_vec_operations() -> i32
    var v = vec_new<i32>()

    vec_push(@v, 42)
    assert vec_len(@v) == 1
    assert vec_get(@v, 0) == 42

    vec_push(@v, 100)
    assert vec_len(@v) == 2
    assert vec_last(@v) == 100

    vec_drop(@v)
    0
```

### 6.6 Testing Patterns

**Setup-Execute-Verify:**
```ritz
[[test]]
fn test_hashmap_insert_and_get() -> i32
    # Setup
    var m = hashmap_new()

    # Execute
    hashmap_insert(@m, "key", 42)

    # Verify
    assert hashmap_contains(@m, "key") == 1
    assert hashmap_get(@m, "key") == 42

    # Cleanup
    hashmap_drop(@m)
    0
```

**Error case testing:**
```ritz
[[test]]
fn test_parse_invalid_returns_error() -> i32
    let result = json_parse("invalid{", 8)
    assert result.ok == 0   # Should fail
    0
```

---

## 7. Best Practices

### 7.1 Idiomatic Patterns to Prefer

**Use modern syntax:**
```ritz
# Prefer: character literals
if c == '\n'

# Avoid: magic numbers
if c == 10


# Prefer: for loops with ranges
for i in 0..len
    process(items[i])

# Avoid: while loop with manual counter
var i = 0
while i < len
    process(items[i])
    i += 1


# Prefer: compound assignment
count += 1

# Avoid: redundant assignment
count = count + 1


# Prefer: null keyword
if ptr == null

# Avoid: casting zero
if ptr == 0 as *u8


# Prefer: match for multi-way branching
match token.kind
    Ident => handle_ident(token)
    Number => handle_number(token)
    _ => error("unexpected token")

# Avoid: chained if/else if for enums
if token.kind == Ident
    handle_ident(token)
else if token.kind == Number
    handle_number(token)
else
    error("unexpected token")
```

**Use type inference where clear:**
```ritz
# Good: type is obvious from RHS
let fd = sys_open(path, O_RDONLY)
let result = parse_json(input)

# Good: explicit type when not obvious or needed
let count: i64 = 0
var buffer: [4096]u8 = zeroed()
```

### 7.2 Anti-Patterns to Avoid

**Avoid raw pointer arithmetic when borrows suffice:**
```ritz
# Bad: manual pointer math
fn get_element(arr: *i32, idx: i64) -> i32
    *(arr + idx)

# Good: use slice/span with bounds checking in debug
fn get_element(arr: Span<i32>, idx: i64) -> i32
    arr.get(idx)
```

**Avoid nested error handling without `?`:**
```ritz
# Bad: nested matches
fn process() -> Result<Data, Error>
    let r1 = step1()
    match r1
        Ok(v1) =>
            let r2 = step2(v1)
            match r2
                Ok(v2) => Ok(v2)
                Err(e) => Err(e)
        Err(e) => Err(e)

# Good: use ? operator
fn process() -> Result<Data, Error>
    let v1 = step1()?
    let v2 = step2(v1)?
    Ok(v2)
```

**Avoid premature optimization:**
```ritz
# Bad: unreadable bit manipulation when not needed
let is_power_of_two = (n & (n - 1)) == 0

# Good: clear code with optimization as needed
fn is_power_of_two(n: i64) -> bool
    n > 0 && (n & (n - 1)) == 0
```

### 7.3 Performance Considerations

**Minimize allocations:**
```ritz
# Good: pre-allocate when size is known
var v = vec_with_cap<i32>(expected_size)
for i in 0..expected_size
    vec_push(@v, compute(i))

# Bad: grow incrementally from zero
var v = vec_new<i32>()
for i in 0..expected_size
    vec_push(@v, compute(i))  # Multiple reallocations
```

**Use arenas for batch allocations:**
```ritz
# Good: arena for request-scoped allocations
fn handle_request(req: Request) -> Response
    var arena = arena_new(64 * 1024)
    defer arena.destroy()

    let parsed = parse_body(@arena, req.body)
    let result = process(@arena, parsed)
    render(result)
```

**Avoid unnecessary copies:**
```ritz
# Good: borrow instead of copy
fn process(data: DataSet)       # Const borrow
    for item in data.items
        validate(item)

# Bad: unnecessary ownership transfer
fn process(data:= DataSet)      # Takes ownership when not needed
    for item in data.items
        validate(item)
```

### 7.4 Common Patterns

**Builder pattern:**
```ritz
struct Config
    host: String
    port: i32
    timeout: i64

fn config_default() -> Config
    Config {
        host: String.from("localhost"),
        port: 8080,
        timeout: 30000
    }

fn config_with_host(c:& Config, host: String) -> Config
    c.host = host
```

**Factory functions:**
```ritz
# Prefer Type_new() convention for constructors
pub fn arena_new(size: i64) -> Arena
    # ...

pub fn vec_new<T>() -> Vec<T>
    # ...

pub fn hashmap_new() -> HashMap
    # ...
```

**Result transformation:**
```ritz
fn fetch_user(id: i64) -> Result<User, DbError>
    let row = db_query(id)?
    let user = User {
        id: row.get_i64("id"),
        name: row.get_string("name")
    }
    Ok(user)
```

---

## Appendix: Quick Reference

### Naming Summary

| Item | Convention | Example |
|------|------------|---------|
| Functions | snake_case | `vec_push`, `arena_alloc` |
| Variables | snake_case | `token_count`, `buffer_size` |
| Types/Structs | PascalCase | `HashMapEntry`, `Parser` |
| Enums | PascalCase | `TokenKind`, `Option` |
| Enum Variants | PascalCase | `Some`, `None`, `Ok`, `Err` |
| Constants | SCREAMING_SNAKE | `MAX_SIZE`, `TOK_EOF` |
| Type Parameters | Single uppercase | `T`, `K`, `V`, `E` |
| Modules | snake_case | `async_tasks`, `hash_map` |

### Ownership Modifiers

| Signature | Meaning |
|-----------|---------|
| `x: T` | Const borrow (read-only) |
| `x:& T` | Mutable borrow (can modify) |
| `x:= T` | Move ownership |

### Reference Types

| Type | Meaning |
|------|---------|
| `@T` | Immutable reference |
| `@&T` | Mutable reference |
| `*T` | Raw pointer (unsafe) |

---

*This style guide is maintained by the LARB project. For questions or proposed changes, open an issue in the LARB repository.*
