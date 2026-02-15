# Ritz Language Quick Reference

> Minimal context for AI agents. For full details see [LANGUAGE_SPEC.md](LANGUAGE_SPEC.md).

## Syntax Essentials

**Indentation-based blocks** (Python-style). No semicolons, no braces.

```ritz
fn main() -> i32
    print("Hello, Ritz!\n")
    0
```

## Types

| Category | Types |
|----------|-------|
| Integers | `i8`, `i16`, `i32`, `i64`, `u8`, `u16`, `u32`, `u64` |
| Floats | `f32`, `f64` |
| Boolean | `bool` (`true`, `false`) |
| Pointers | `*T` (raw), `*mut T` (raw mut), `&T` (borrow), `&mut T` (mut borrow) |
| Arrays | `[N]T` (fixed-size stack array) |
| Strings | `String` (owned), `Span<u8>` (slice), `*u8` (C-string) |

## String Literals

```ritz
"hello"    # String (heap-allocated, owned)
c"hello"   # *u8 (C-string, null-terminated)
s"hello"   # Span<u8> (zero-copy slice with length)
```

## Variables

```ritz
let x: i32 = 42      # Immutable (type optional with inference)
let x = 42           # Type inferred as i32
var y: i32 = 0       # Mutable
y = 10               # Assignment
```

## Functions

```ritz
fn add(a: i32, b: i32) -> i32
    a + b

fn Point.distance(self: &Point) -> i32    # Method
    self.x * self.x + self.y * self.y

extern fn write(fd: i32, buf: *u8, len: i64) -> i64   # External
```

## Structs & Enums

```ritz
struct Point
    x: i32
    y: i32

let p = Point { x: 10, y: 20 }
p.x                   # Field access (auto-deref for pointers)

enum Option<T>
    Some(T)
    None
```

## Control Flow

```ritz
if x > 0
    print("positive\n")
else if x < 0
    print("negative\n")
else
    print("zero\n")

while x > 0
    x = x - 1

for i in 0..10        # Range loop (exclusive end)
    print_int(i)

loop                  # Infinite loop
    if done
        break
```

## Pattern Matching

```ritz
match opt
    Some(x) => print_int(x)
    None => print("none\n")

match n
    0 => print("zero\n")
    1 => print("one\n")
    _ => print("many\n")
```

## Generics

```ritz
struct Vec<T>
    data: *T
    len: i64
    cap: i64

fn vec_new<T>() -> Vec<T>
    Vec { data: null as *T, len: 0, cap: 0 }
```

## Ownership & Borrowing

```ritz
let s = String::from("hello")   # s owns the string
let r: &String = &s             # Immutable borrow
let m: &mut String = &mut s     # Mutable borrow (exclusive)
drop(s)                         # Explicit drop
```

- Values are **moved** by default (no implicit copy)
- `&T` creates immutable borrow
- `&mut T` creates exclusive mutable borrow
- Implement `Drop` trait for RAII cleanup

## Error Handling

```ritz
fn read_file(path: *u8) -> Result<String, Error>
    let fd = open(path)?        # ? propagates Err
    Ok(content)

# Pattern match on Result
match result
    Ok(value) => use(value)
    Err(e) => handle(e)
```

## Modules & Imports

```ritz
import ritzlib.io               # Import module
import ritzlib.sys as sys       # Alias

pub fn public_function()        # Public (exported)
    pass

fn private_function()           # Private (internal linkage)
    pass
```

## Async/Await

```ritz
async fn fetch(url: *u8) -> Result<Vec<u8>, Error>
    let sock = await connect(url)?
    await read_all(sock)

# Runtime: io_uring-based task executor
```

## Operators

| Category | Operators |
|----------|-----------|
| Arithmetic | `+`, `-`, `*`, `/`, `%` |
| Comparison | `==`, `!=`, `<`, `<=`, `>`, `>=` |
| Logical | `and`, `or`, `not` |
| Bitwise | `&`, `\|`, `^`, `~`, `<<`, `>>` |
| Assignment | `=`, `+=`, `-=`, `*=`, `/=`, `%=` |
| Cast | `x as T` |
| Pointer | `&x`, `*p`, `&mut x` |

## Attributes

```ritz
@test
fn test_addition() -> i32       # Test function (discovered by ritzunit)
    if 2 + 2 == 4
        return 0
    1

@inline
fn hot_path() -> i32            # Inline hint
    42
```

## Common Patterns

```ritz
# String interpolation
let name = "world"
print("Hello, {name}!\n")

# Character literal
let c: u8 = 'A'
let newline: u8 = '\n'

# Null pointer
let p: *u8 = null

# Type cast
let x: i64 = 42 as i64

# Array indexing
let arr: [10]i32 = [0; 10]
arr[0] = 42

# Sizeof
let size = sizeof(Point)
```

## Build Commands

```bash
./ritz build <package>     # Build package
./ritz test <package>      # Build and test
./ritz run file.ritz       # Compile and run
./ritz check               # Verify tests pass
```

## Project Configuration (ritz.toml)

```toml
[package]
name = "myapp"
version = "0.1.0"

[[bin]]
name = "myapp"
entry = "main::main"
sources = ["src"]

[dependencies]
squeeze = { path = "../squeeze" }
```
