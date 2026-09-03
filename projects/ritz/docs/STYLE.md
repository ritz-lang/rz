# Ritz Style Guide

**Scope:** naming, formatting, file organization, documentation, ownership, testing
and everyday idioms for Ritz programs across the ecosystem. |
**Last revised:** 2026-09-03

Every fenced ` ```ritz ` block in this document is compiled by
`tools/check_doc_examples.py` against the reference compiler (`ritz0`) on every
build. A block that no longer compiles fails the build, so what you read here is
what the compiler currently accepts — not what it accepted when the paragraph was
written. Blocks whose fence carries `expect-error="..."` are examples that the
compiler *rejects*, and the checker asserts that they keep failing with exactly
the quoted diagnostic. Blocks marked `no-compile="..."` are the (few) sketches of
things ritz0 does not implement yet; each one says so in the prose next to it.

This document defines the canonical coding style for Ritz programs across the ecosystem. Following these conventions ensures consistency, readability, and maintainability. Style rules are advisory; where a rule coincides with something the compiler actually enforces, the text says so explicitly.

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
struct HashMapEntry<K, V>
    key: K
    value: V


fn swap<T>(a: @&T, b: @&T)
    let tmp: T = *a
    *a = *b
    *b = tmp


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
import ritzlib.result


struct DataSet
    n: i64

struct ProcessConfig
    verbose: i32

struct ProcessOptions
    retries: i32

struct Output
    n: i64

struct ProcessError
    code: i32


# Good: fits on one line
fn add(a: i32, b: i32) -> i32
    a + b


# Good: long signature broken appropriately
fn process_complex_data(
    input: DataSet,
    config: ProcessConfig,
    options: ProcessOptions
) -> Result<Output, ProcessError>
    if config.verbose == 1 && options.retries > 0
        return Ok(Output { n: input.n })
    Err(ProcessError { code: 1 })
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


fn point_norm_squared(p: @Point) -> i64
    let x_sq: i64 = (p.x * p.x) as i64
    let y_sq: i64 = (p.y * p.y) as i64

    x_sq + y_sq
```

### 2.4 Spacing

Both halves of each pair below compile: spacing is a readability rule, not
something the compiler enforces.

**Around operators:**
```ritz body
let a = 1
let b = 2
let c = 3
let x = 0
let y = 20
let flags = 0xFFFF

# Good
let result = a + b * c
let in_range = x == 0 && y > 10
let mask = flags & 0xFF

# Bad
let result2=a+b*c
let in_range2=x==0&&y>10
```

**After commas:**
```ritz
# Good
fn sum3(a: i32, b: i32, c: i32) -> i32
    let arr = [1, 2, 3, 4]
    a + b + c + arr[0]


# Bad
fn sum3_cramped(a: i32,b: i32,c: i32) -> i32
    let arr = [1,2,3,4]
    a + b + c + arr[0]
```

**No space inside parentheses or brackets:**
```ritz
fn foo(x: i32, y: i32) -> i32
    x + y


fn call_sites(arr: *i32, i: i64) -> i32
    # Good
    let good = foo(1, 2) + arr[i]

    # Bad
    let bad = foo( 1, 2 ) + arr[ i ]

    good + bad
```

**No space after unary operators:**
```ritz body
let x = 1
var target: i32 = 7
let value = 9
let flag = false
let ptr: *i32 = @&target

# Good
let neg = -x
let inv = !flag
let deref = *ptr
let addr = @value

# Bad
let neg2 = - x
let inv2 = ! flag
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

### 2.6 Boolean Operators: `and` / `or` / `not`

Ritz accepts both spellings of each logical operator — `and` and `&&`, `or` and
`||`, `not` and `!` — and they mean exactly the same thing. **House style is the
word form.** In `ritzlib`, `ritz1` and `examples` the word form outnumbers the
symbol form by roughly 700 uses to 2; a `&&` in new code reads as an import from
another language.

```ritz
fn in_window(x: i64, lo: i64, hi: i64, closed: bool) -> bool
    # Good: word form, house style
    if x >= lo and x <= hi
        return true
    if not closed and (x == lo or x == hi)
        return true

    # Legal, but not house style
    if x < lo && x > hi
        return false
    false
```

The one exception is `!` used as part of a comparison you are reading as a unit
(`!=`), which is unrelated to logical negation.

---

## 3. Code Organization

### 3.1 Import Ordering and Grouping

Group imports into three blocks, in this order, sorted alphabetically within
each group and separated by one blank line:

1. **Standard library imports** (`ritzlib.*`)
2. **External package imports**
3. **Local/sibling module imports**

```ritz
# Standard library imports (ritzlib)
import ritzlib.io
import ritzlib.memory
import ritzlib.str
import ritzlib.sys

# External package imports
#     import cryptosec.aes
#     import squeeze.gzip

# Local/sibling module imports
#     import parser
#     import tokens
#     import types
```

(The second and third groups are shown commented out because this document's
examples are really compiled, and those packages do not exist in this
repository. In a real file they are plain `import` lines.)

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
    Vec<T> { data: null as *T, len: 0, cap: 0 }


# ============================================================================
# Core Operations
# ============================================================================

pub fn vec_push<T>(v:& Vec<T>, item: T) -> i32
    if v.len >= v.cap
        return 1
    *(v.data + v.len) = item
    v.len += 1
    0
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
struct Arena
    base: *u8
    size: i64
    offset: i64


# Allocate `size` bytes from the arena.
# Returns pointer to allocated memory, or null on failure.
# Memory is 8-byte aligned.
pub fn arena_alloc(a:& Arena, size: i64) -> *u8
    let aligned = (size + 7) & -8
    if a.offset + aligned > a.size
        return null as *u8
    let p = a.base + a.offset
    a.offset += aligned
    p
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

```ritz body
let key: u64 = 12345
let bits: u64 = 16
var buf: [16]u8 = [0; 16]
var i: i64 = 0

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
import ritzlib.strview


struct Connection
    fd: i32


# Const borrow - just read the data
fn calculate_hash(data: StrView) -> u64
    var h: u64 = 1469598103934665603
    var i: i64 = 0
    while i < data.len
        h = h * 1099511628211
        i += 1
    h


# Mutable borrow - modify in place
fn increment(counter:& i32)
    counter += 1


# Move ownership - caller gives up the value
fn consume_connection(conn:= Connection) -> i32
    conn.fd
```

Note the mutable-borrow parameter is written `counter:& i32`, and the body writes
`counter += 1`, not `*counter += 1`: a `:&` parameter is already the value, not a
pointer to it. Write `*p` only when the parameter is a raw pointer (`*T`, `*&T`).

**Call sites are always clean:**
```ritz
struct Connection
    fd: i32


fn increment(counter:& i32)
    counter += 1

fn calculate_hash(data: i64) -> u64
    data as u64

fn consume_connection(conn:= Connection) -> i32
    conn.fd


fn call_sites(data: i64) -> i32
    var n: i32 = 0
    let conn = Connection { fd: 3 }

    # No sigils at call sites - Ritz, not Rust
    increment(n)                  # Not: increment(&mut n)
    let h = calculate_hash(data)  # Not: calculate_hash(&data)
    consume_connection(conn)      # Same spelling; ownership transfers
```

### 5.2 Address-Of Operators

Use `@` for taking addresses (references):

```ritz body
let x: i32 = 1
var y: i32 = 2

let ptr = @x           # Immutable reference to x (type: @T)
let mptr = @&y         # Mutable reference to y (type: @&T)
```

Take at most one of the two per variable in a scope: ritz0's ownership checker
rejects `@x` on a value already borrowed as `@&x`.

### 5.3 Resource Cleanup with `defer`

Use `defer` for cleanup operations that must run at scope exit:

**`defer` is not implemented in ritz0.** The block below is the intended style,
and the checker asserts that ritz0 still rejects it with
`Unknown identifier: defer`; when the compiler grows `defer`, this block starts
compiling and the build tells us to drop this caveat.

```ritz expect-error="Unknown identifier: defer"
import ritzlib.memory


fn read_config(size: i64) -> i64
    var arena = arena_new(size)
    defer arena_destroy(@arena)   # Always destroy, even on early return

    arena_used(@arena)
```

Until then, write the cleanup out at each exit point:

```ritz
import ritzlib.memory


fn read_config(size: i64) -> i64
    var arena = arena_new(size)
    if arena_valid(@arena) == 0
        arena_destroy(@arena)
        return -1

    let used = arena_used(@arena)
    arena_destroy(@arena)
    used
```

**Guidelines (for when `defer` lands):**
- Place `defer` immediately after acquiring a resource
- Multiple defers execute in **reverse order** (LIFO)
- Prefer `defer` over manual cleanup at each return point

### 5.4 Error Handling: Result vs Panic

**Use `Result<T, E>` for:**
- Operations that can fail (I/O, parsing, allocation)
- Errors that callers should handle
- Library functions

Qualify enum variants with `.`, not `::`: `ParseError.EmptyInput`.

```ritz
import ritzlib.result
import ritzlib.strview


enum ParseError
    EmptyInput
    BadDigit


fn parse_int(s: StrView) -> Result<i64, ParseError>
    if strview_is_empty(@s) == 1
        return Err(ParseError.EmptyInput)

    var value: i64 = 0
    var i: i64 = 0
    while i < s.len
        let c = *(s.ptr + i)
        if c < 48 || c > 57
            return Err(ParseError.BadDigit)
        value = value * 10 + (c as i64 - 48)
        i += 1
    Ok(value)
```

**Use panic (via `assert`) for:**
- Programming errors (logic bugs, invariant violations)
- Unrecoverable states
- Debug-only checks

`assert` is a **compiler-enforced** restriction, not a style preference: ritz0
permits `assert` only inside `[[test]]` functions. Using it anywhere else is an
error, not merely bad style:

```ritz expect-error="assert is only allowed in @test functions"
struct Vec32
    data: *i32
    len: i64


fn vec_get(v: @Vec32, idx: i64) -> i32
    assert idx >= 0 && idx < v.len   # Rejected: not a [[test]] function
    *(v.data + idx)
```

In library code, check the invariant explicitly and return a sentinel or a
`Result`; keep `assert` for the tests that pin the invariant down:

```ritz
struct Vec32
    data: *i32
    len: i64


fn vec_get(v: @Vec32, idx: i64) -> i32
    if idx < 0 || idx >= v.len
        return 0
    *(v.data + idx)


[[test]]
fn test_vec_get_rejects_out_of_range_index() -> i32
    var storage: [4]i32 = [0; 4]
    storage[0] = 7
    let v = Vec32 { data: @&storage[0], len: 4 }
    assert vec_get(@v, 0) == 7, "in-range read"
    assert vec_get(@v, 99) == 0, "out-of-range read is clamped"
    0
```

### 5.5 The `?` Operator

Propagate errors with `?`:

```ritz
import ritzlib.result
import ritzlib.strview


struct Data
    n: i64

struct Error
    code: i32


fn read_file(path: StrView) -> Result<StrView, Error>
    if strview_is_empty(@path) == 1
        return Err(Error { code: 2 })
    Ok(path)


fn parse_json(content: StrView) -> Result<Data, Error>
    Ok(Data { n: content.len })


fn load_and_parse(path: StrView) -> Result<Data, Error>
    let content = read_file(path)?      # Returns Err if read fails
    let parsed = parse_json(content)?   # Returns Err if parse fails
    Ok(parsed)
```

### 5.6 Initialization Patterns

**Always initialize variables:**
```ritz body
# Good: explicit initialization
var count: i64 = 0
var ptr: *u8 = null

# Arrays: use the repeat literal [value; length]
var buffer: [1024]u8 = [0; 1024]     # Zero-initialized
var scratch: [256]u8 = [0; 256]      # Same form, any element type
```

There is no `zeroed()` or `uninit()` in ritzlib; `[0; N]` is the zero-fill form,
and ritz0 lowers a large zero fill to a `memset`, so it costs no more than an
"uninitialized" declaration would.

---

## 6. Testing

### 6.1 Test Naming

Use descriptive names that explain **what is being tested** and **expected outcome**:

```ritz
import ritzlib.memory
import ritzlib.gvec
import ritzlib.json


[[test]]
fn test_arena_alloc_returns_aligned_pointer() -> i32
    var a = arena_new(4096)
    let p = arena_alloc(@a, 100)
    assert (p as i64) % 8 == 0, "alignment"
    arena_destroy(@a)
    0


[[test]]
fn test_vec_push_grows_capacity_when_full() -> i32
    var v: Vec<i32> = vec_with_cap<i32>(1)
    v.push(1)
    v.push(2)
    assert v.cap() >= 2, "capacity grew"
    v.drop()
    0


[[test]]
fn test_parse_invalid_json_returns_error() -> i32
    let r = json_parse(c"{ not json", 10)
    assert r.ok == 0, "malformed input must not parse"
    0
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
    let p = heap_alloc(64)
    assert p != null
    heap_free(p, 64)
    0
```

(A function body may not be empty: `# ...` on its own is a parse error, so every
test above has a real body.)

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
import ritzlib.gvec


[[test]]
fn test_vec_operations() -> i32
    var v: Vec<i32> = vec_new<i32>()

    v.push(42)
    assert v.len() == 1
    assert v.get(0) == 42

    v.push(100)
    assert v.len() == 2
    assert v.last() == 100

    v.drop()
    0
```

Prefer the method form `v.push(x)` over the free-function form
`vec_push<i32>(@&v, x)`: it is shorter, and it infers the element type.

### 6.6 Testing Patterns

**Setup-Execute-Verify:**
```ritz
import ritzlib.hashmap


[[test]]
fn test_hashmap_insert_and_get() -> i32
    # Setup
    var m = hashmap_i64_new()

    # Execute
    hashmap_i64_insert(@&m, 7, 42)

    # Verify
    assert hashmap_i64_contains(@m, 7) == 1
    assert hashmap_i64_get(@m, 7) == 42

    # Cleanup
    hashmap_i64_drop(@&m)
    0
```

**Error case testing:**
```ritz
import ritzlib.result


enum ParseError
    Syntax


fn parse(input: i64) -> Result<i64, ParseError>
    if input < 0
        return Err(ParseError.Syntax)
    Ok(input)


[[test]]
fn test_parse_invalid_returns_error() -> i32
    let result = parse(-1)
    assert result.is_err() == 1   # Should fail
    0
```

---

## 7. Best Practices

### 7.1 Idiomatic Patterns to Prefer

**Use modern syntax.** Both halves of each pair below compile; the difference is
readability, not legality.

Character literals over magic numbers:
```ritz body
let c: u8 = 10
var n: i32 = 0

# Prefer: character literals
if c == '\n'
    n += 1

# Avoid: magic numbers
if c == 10
    n += 1
```

`for` over a range, rather than a hand-rolled counter:
```ritz
fn process(x: i32) -> i32
    x


fn walk(items: *i32, len: i64) -> i32
    # Prefer: for loops with ranges
    for i in 0..len
        process(items[i])

    # Avoid: while loop with manual counter
    var i: i64 = 0
    while i < len
        process(items[i])
        i += 1
    0
```

Compound assignment, and the `null` keyword over a cast zero:
```ritz body
var count: i64 = 0
var ptr: *u8 = null

# Prefer: compound assignment
count += 1

# Avoid: redundant assignment
count = count + 1

# Prefer: null keyword
if ptr == null
    count += 1

# Avoid: casting zero
if ptr == 0 as *u8
    count += 1
```

`match` over a chain of `if`/`else if` on an enum. Note that match arms name the
variant bare (`Ident =>`), while an equality test must qualify it
(`token.kind == TokenKind.Ident`):
```ritz
enum TokenKind
    Ident
    Number


struct Token
    kind: TokenKind


fn handle_ident(t: Token) -> i32
    1

fn handle_number(t: Token) -> i32
    2

fn unexpected_token() -> i32
    -1


# Prefer: match for multi-way branching
fn dispatch(token: Token) -> i32
    match token.kind
        Ident => handle_ident(token)
        Number => handle_number(token)
        _ => unexpected_token()


# Avoid: chained if/else if for enums
fn dispatch_chained(token: Token) -> i32
    if token.kind == TokenKind.Ident
        return handle_ident(token)
    else if token.kind == TokenKind.Number
        return handle_number(token)
    else
        return unexpected_token()
```

**Use type inference where clear:**
```ritz
import ritzlib.sys


const O_RDONLY: i32 = 0


fn read_something(path: *u8) -> i32
    # Good: type is obvious from RHS
    let fd = sys_open(path, O_RDONLY)

    # Good: explicit type when not obvious or needed
    let count: i64 = 0
    var buffer: [4096]u8 = [0; 4096]

    let n = sys_read(fd, @&buffer[0], count)
    sys_close(fd)
    n as i32
```

### 7.2 Anti-Patterns to Avoid

**Avoid raw pointer arithmetic when borrows suffice:**
```ritz
import ritzlib.span


# Bad: manual pointer math
fn get_element_raw(arr: *i32, idx: i64) -> i32
    *(arr + idx)


# Good: use a Span, which carries its own length
fn get_element(arr: Span<i32>, idx: i64) -> i32
    if idx < 0 || idx >= arr.len
        return 0
    arr.get(idx)
```

**Avoid nested error handling without `?`:**
```ritz
import ritzlib.result


struct Data
    n: i64

struct Error
    code: i32


fn step1() -> Result<i64, Error>
    Ok(1)

fn step2(v: i64) -> Result<Data, Error>
    Ok(Data { n: v })


# Bad: nested matches
fn process_nested() -> Result<Data, Error>
    let r1 = step1()
    match r1
        Ok(v1) => step2(v1)
        Err(e) => Err(e)


# Good: use ? operator
fn process() -> Result<Data, Error>
    let v1 = step1()?
    let v2 = step2(v1)?
    Ok(v2)
```

**Avoid premature optimization:**
```ritz
# Bad: unreadable bit manipulation inlined at the use site
fn count_powers(n: i64) -> i64
    let is_power_of_two = (n & (n - 1)) == 0
    if is_power_of_two
        return 1
    0


# Good: name it, then the trick is readable
fn is_power_of_two(n: i64) -> bool
    n > 0 && (n & (n - 1)) == 0
```

### 7.3 Performance Considerations

**Minimize allocations:**
```ritz
import ritzlib.gvec


fn compute(i: i64) -> i32
    i as i32


# Good: pre-allocate when size is known
fn build_preallocated(expected_size: i64) -> i64
    var v: Vec<i32> = vec_with_cap<i32>(expected_size)
    for i in 0..expected_size
        v.push(compute(i))
    let n = v.len()
    v.drop()
    n


# Bad: grow incrementally from zero
fn build_incremental(expected_size: i64) -> i64
    var v: Vec<i32> = vec_new<i32>()
    for i in 0..expected_size
        v.push(compute(i))    # Multiple reallocations
    let n = v.len()
    v.drop()
    n
```

**Use arenas for batch allocations.** (`defer` is not implemented yet — see
§5.3 — so the destroy is written out at the end of the function.)
```ritz
import ritzlib.memory


struct Request
    body_len: i64

struct Response
    len: i64


fn parse_body(a: *Arena, len: i64) -> *u8
    arena_alloc(a, len)


# Good: arena for request-scoped allocations
fn handle_request(req: Request) -> Response
    var arena = arena_new(64 * 1024)

    let parsed = parse_body(@arena, req.body_len)
    let used = arena_used(@arena)

    arena_destroy(@arena)
    Response { len: used }
```

**Avoid unnecessary copies:**
```ritz
import ritzlib.gvec


struct DataSet
    items: Vec<i32>


fn validate(item: i32) -> i32
    item


# Good: borrow instead of copy
fn process(data: DataSet) -> i32       # Const borrow
    for item in data.items
        validate(item)
    0


# Bad: unnecessary ownership transfer
fn process_owned(data:= DataSet) -> i32   # Takes ownership when not needed
    for item in data.items
        validate(item)
    0
```

### 7.4 Common Patterns

**Builder pattern:**
```ritz
import ritzlib.string


struct Config
    host: String
    port: i32
    timeout: i64


fn config_default() -> Config
    Config {
        host: string_from_cstr(c"localhost"),
        port: 8080,
        timeout: 30000
    }


fn config_with_host(c:& Config, host: String)
    c.host = host
```

**Factory functions:**
```ritz
import ritzlib.memory
import ritzlib.gvec
import ritzlib.hashmap


# Prefer Type_new() convention for constructors
pub fn scratch_arena_new() -> Arena
    arena_new(64 * 1024)

pub fn i32_vec_new() -> Vec<i32>
    vec_new<i32>()

pub fn counters_new() -> HashMapI64
    hashmap_i64_new()
```

**Result transformation:**
```ritz
import ritzlib.result
import ritzlib.string


struct Row
    id: i64
    name: String

struct User
    id: i64
    name: String

struct DbError
    code: i32


fn db_query(id: i64) -> Result<Row, DbError>
    if id < 0
        return Err(DbError { code: 1 })
    Ok(Row { id: id, name: string_from_cstr(c"ada") })


fn fetch_user(id: i64) -> Result<User, DbError>
    let row = db_query(id)?
    let user = User {
        id: row.id,
        name: row.name
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

*This style guide lives in `projects/ritz/docs/STYLE.md` and is validated on every
build by `tools/check_doc_examples.py`. A shorter, compiler-project-specific
style guide lives at `projects/ritz/STYLE.md`; the two have not been merged. For
questions or proposed changes, open an AGAST task against the ritz project.*
