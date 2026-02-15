# Ritz Design Decisions

**LARB Document** | **Status:** Approved | **Date:** 2026-02-13

This document captures the finalized design decisions for Ritz, prioritizing **sexiness, ergonomics, performance, efficiency, and overall goodness**.

---

## Design Philosophy

### The Hierarchy of Concerns

1. **Sexiness** — Does it look good? Does it feel right? Would you *want* to write this?
2. **Ergonomics** — Is the common case easy? Is intent clear from syntax?
3. **Performance** — Zero-cost abstractions. No hidden allocations.
4. **Efficiency** — Developer productivity. Minimal ceremony.
5. **Safety** — Memory safety by default, escape hatches when needed.

### The Golden Rule

> **The 90% case should be the cleanest.** Special cases earn sigils.

---

## 1. Ownership & Borrowing (Finalized)

### 1.1 Colon-Modifier Syntax

The most ergonomic and visually clean approach:

| Syntax | Meaning | Frequency |
|--------|---------|-----------|
| `x: T` | Const borrow (or copy for primitives) | ~70% |
| `x:& T` | Mutable borrow | ~20% |
| `x:= T` | Move ownership | ~10% |

**Why this is sexy:**

```ritz
# Clean — no ceremony for the common case
fn calculate(a: i32, b: i32) -> i32
fn print_user(user: User)
fn format(msg: StrView) -> String

# Sigils only when doing something special
fn update(player:& Player, delta: i32)    # Mutation
fn consume(conn:= Connection)              # Ownership transfer
```

### 1.2 Clean Call Sites (Zero Annotation)

Unlike Rust, Ritz call sites are always clean:

```ritz
# Rust — cluttered
increment(&mut n);
read(&data);
consume(conn);

# Ritz — clean
increment(n)
read(data)
consume(conn)
```

The function signature tells the story. The call site is uncluttered.

### 1.3 Copy Type Harmony

For `Copy` types (`i32`, `f64`, `bool`), the const borrow (`:`) has identical semantics to pass-by-value. This means **primitive code has zero syntactic overhead**:

```ritz
fn add(a: i32, b: i32) -> i32
    a + b
```

No sigils. No ceremony. Just math.

---

## 2. Address-Of & Reference Types (Finalized)

### 2.1 `@` for Address-Of

The `@` symbol means "at this address":

```ritz
let ptr = @x          # Where is x "at"?
let mptr = @&x        # Mutable reference to x
```

**Mnemonic:** "at" → `@` → "where is it at?"

### 2.2 Reference Type Syntax

| Syntax | Meaning |
|--------|---------|
| `@T` | Immutable reference (read-only) |
| `@&T` | Mutable reference (read-write) |
| `*T` | Raw pointer (FFI/unsafe only) |

**Consistency:** The `&` always means "mutable":

| Context | Immutable | Mutable |
|---------|-----------|---------|
| Parameters | `x: T` | `x:& T` |
| Reference types | `@T` | `@&T` |
| Taking reference | `@x` | `@&x` |

### 2.3 Bitwise AND is Unambiguous

With `@` for address-of, `&` is *only* bitwise AND:

```ritz
let addr = @n           # Address-of
let mask = a & b        # Bitwise AND — no ambiguity!
```

---

## 3. Attributes (Finalized)

### 3.1 Double-Bracket Syntax

Attributes use `[[name]]` to free `@` for address-of:

```ritz
[[test]]
fn test_connection()
    # ...

[[inline]]
fn hot_path(data: Packet)
    # ...

[[cold]]
fn error_handler(err: Error)
    # ...
```

**Why double brackets:**
- Visually distinct from code
- Doesn't conflict with any other syntax
- Allows nested attributes: `[[derive(Debug, Clone)]]`

---

## 4. String System (Finalized)

### 4.1 Type Hierarchy

```
Str (trait)
├── StrView          # Zero-copy slice (ptr + len), immutable
├── String           # Owned, heap-allocated, growable
├── StrBuf<N>        # Fixed-capacity buffer (stack or inline)
└── CStr             # Null-terminated C string (FFI only)
```

### 4.2 Zero-Copy by Default

String literals are `StrView` — no allocation:

```ritz
let greeting = "hello"          # StrView (zero-copy)
let name = String.from("world") # String (heap-allocated)
```

### 4.3 No Prefixes

Drop the awkward `c""` and `s""` prefixes:

| Old (Ugly) | New (Sexy) |
|------------|------------|
| `c"hello"` | `"hello".as_cstr()` |
| `s"hello"` | `"hello"` (default is StrView) |
| `"hello"` (allocating) | `String.from("hello")` |

### 4.4 String Builder

For efficient construction:

```ritz
var builder = StringBuilder.new()
builder.push_str("Hello, ")
builder.push_str(name)
builder.push('!')
let result = builder.build()
```

---

## 5. Missing Features (From Mausoleum Review)

### 5.1 `sizeof` Operator

Critical for allocator-heavy code:

```ritz
let size = sizeof(Page)           # Size of Page struct in bytes
let array_size = sizeof([64]u8)   # Size of fixed array
let ptr_size = sizeof(*T)         # Size of pointer (platform-dependent)
```

**Implementation:** Compile-time constant, no runtime cost.

### 5.2 `alignof` Operator

For memory-aligned allocations:

```ritz
let align = alignof(CacheLine)    # Alignment requirement
```

### 5.3 Computed Range Bounds

Allow variables in range expressions:

```ritz
# Current (broken for variables)
for i in 0..10
    # ...

# Proposed (works with expressions)
for i in start..end
    process(i)

for i in 0..vec.len()
    vec.get(i)
```

### 5.4 `defer` for Cleanup

RAII-style cleanup without verbose drop implementations:

```ritz
fn read_file(path: StrView) -> Result<String, Error>
    let fd = open(path, O_RDONLY)?
    defer close(fd)                    # Runs at scope exit

    let content = read_all(fd)?
    Ok(content)                        # fd closed automatically
```

**Stacking:** Multiple defers execute in reverse order (LIFO):

```ritz
fn complex_operation()
    let a = acquire_resource_a()
    defer release(a)

    let b = acquire_resource_b()
    defer release(b)

    # ... work ...

    # On exit: release(b) runs first, then release(a)
```

---

## 6. Logical Operators (Finalized)

### 6.1 Keywords, Not Symbols

Use `and`, `or`, `not` — not `&&`, `||`, `!`:

```ritz
if a and b or not c
    # ...
```

**Rationale:**
- Reads like prose, not line noise
- Consistent with Python (Ritz's aesthetic inspiration)
- Encourages clear expression of logic over clever encoding
- Matches Ritz's "readability over brevity" philosophy

---

## 7. Integer Overflow (Finalized)

### 7.1 Debug Mode: Panic

```ritz
let x: u8 = 255
let y = x + 1    # PANIC in debug mode
```

### 7.2 Release Mode: Wrap (Opt-In)

Default: panic. To opt into wrapping:

```ritz
let y = x.wrapping_add(1)   # Wraps to 0
```

### 7.3 Explicit Methods

| Method | Behavior |
|--------|----------|
| `wrapping_add()` | Wraps on overflow |
| `saturating_add()` | Clamps to max |
| `checked_add()` | Returns `Option<T>` |

---

## 8. Array Initialization (Finalized)

### 8.1 Uninitialized Arrays Require Explicit Marker

```ritz
var buffer: [1024]u8 = zeroed()     # Zero-initialized
var buffer: [1024]u8 = uninit()     # Explicit uninitialized (unsafe intent)
```

**Rationale:** Prevent accidental use of garbage data. The `uninit()` marker signals "I know what I'm doing."

---

## 9. Match Exhaustiveness (Finalized)

### 9.1 All Variants Must Be Handled

```ritz
match result
    Ok(value) => process(value)
    Err(e) => log_error(e)
    # No implicit fallthrough. If you add a new variant, compiler errors.
```

### 9.2 Wildcard for Intentional Ignore

```ritz
match value
    Specific(x) => handle(x)
    _ => ()    # Explicit "I don't care about other variants"
```

---

## 10. Loop Keyword (Finalized)

### 10.1 Infinite Loop

```ritz
loop
    if should_exit()
        break
    process()
```

**Why not `while true`:** `loop` is clearer intent, and the compiler can optimize knowing there's no condition to check.

---

## 11. Method Syntax (Finalized)

### 11.1 Methods in `impl` Blocks Only

```ritz
# Good
impl Point
    fn distance(self: Point) -> f64
        # ...

# Deprecated (will be removed)
fn Point.distance(self: Point) -> f64
    # ...
```

---

## 12. Error Handling (Finalized)

### 12.1 `?` Operator

Propagate errors cleanly:

```ritz
fn load_config() -> Result<Config, Error>
    let content = read_file("config.json")?
    let parsed = parse_json(content)?
    Ok(parsed)
```

### 12.2 Result and Option

```ritz
enum Result<T, E>
    Ok(T)
    Err(E)

enum Option<T>
    Some(T)
    None
```

### 12.3 Bare Variant Names

Allow `Ok(x)` instead of `Result::Ok(x)` when type is inferrable:

```ritz
fn fetch() -> Result<Data, Error>
    Ok(data)       # Not Result::Ok(data)

let opt: Option<i32> = Some(42)   # Not Option::Some(42)
```

---

## 13. Closure Syntax (Finalized)

### 13.1 Pipe Syntax

```ritz
let add = |a: i32, b: i32| -> i32
    a + b

let double = |x: i32| x * 2    # Single-expression (no newline)
```

### 13.2 Capture Semantics

Closures capture by reference by default. Use `move` for ownership:

```ritz
let x = String.from("hello")
let closure = move || consume(x)   # x moved into closure
```

---

## 14. Methods on Primitives (Finalized)

### 14.1 Allow `impl` for Primitive Types

```ritz
impl i32
    fn to_string(self: i32) -> String
        # ...

let s = 42.to_string()
```

---

## 15. `const fn` (Planned)

### 15.1 Compile-Time Evaluation

```ritz
const fn fibonacci(n: i32) -> i32
    if n <= 1
        n
    else
        fibonacci(n - 1) + fibonacci(n - 2)

const FIB_10: i32 = fibonacci(10)   # Computed at compile time
```

---

## 16. Unsafe Blocks (Finalized)

### 16.1 Raw Pointer Operations Require `unsafe`

```ritz
let ptr: *u8 = get_buffer()

unsafe
    *ptr = 42                    # Dereference raw pointer
    let next = ptr + 1           # Pointer arithmetic
```

### 16.2 What Requires `unsafe`

| Operation | Requires `unsafe` |
|-----------|-------------------|
| Dereference `*T` | Yes |
| Pointer arithmetic | Yes |
| Call `extern` functions | Yes |
| Access mutable statics | Yes |

---

## Summary: The Ritz Aesthetic

Ritz code should look like this:

```ritz
[[test]]
fn test_user_creation()
    var arena = Arena.new()
    defer arena.destroy()

    let user = arena.alloc(User { name: "Alice", age: 30 })

    assert(user.name == "Alice")
    assert(sizeof(User) == 24)

    for i in 0..user.friends.len()
        print(user.friends.get(i).name)

    match user.status
        Active => log("User is active")
        Inactive(reason) => log("Inactive: " + reason)

fn process_data(data: DataSet)              # Const borrow
    for item in data.items
        validate(item)

fn transform(data:& DataSet)                # Mutable borrow
    for item in data.items
        item.processed = true

fn consume_data(data:= DataSet)             # Move ownership
    let archived = archive(data)
    store(archived)
```

**This is sexy.** Clean, readable, intent-revealing code with safety guarantees and zero hidden costs.

---

*This document represents the finalized design decisions for Ritz 1.0.*
