# Ritz Language Specification

**Version:** 0.2.0 (February 2026)
**Status:** Draft

This document is the authoritative specification for the Ritz programming language.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Lexical Structure](#2-lexical-structure)
3. [Types](#3-types)
4. [Variables](#4-variables)
5. [Functions](#5-functions)
6. [Control Flow](#6-control-flow)
7. [Expressions](#7-expressions)
8. [Pattern Matching](#8-pattern-matching)
9. [Structs](#9-structs)
10. [Enums](#10-enums)
11. [Generics](#11-generics)
12. [Traits](#12-traits)
13. [Ownership and Borrowing](#13-ownership-and-borrowing)
14. [Error Handling](#14-error-handling)
15. [Modules](#15-modules)
16. [Async/Await](#16-asyncawait)
17. [Attributes](#17-attributes)
18. [Memory Model](#18-memory-model)
19. [Standard Library](#19-standard-library)
20. [Appendices](#20-appendices)

---

## 1. Introduction

### 1.1 Design Philosophy

Ritz is a systems programming language with five core design pillars:

1. **Minimal syntax, big library** - Python-style indentation, no semicolons or braces
2. **Type-safe with inference** - Static types with extensive type inference
3. **Ownership without annotations** - Rust semantics with simpler surface syntax
4. **One language for everything** - From kernel to script, same syntax
5. **Bootstrappable** - Self-hosting compiler shipped as LLVM IR

### 1.2 Target Environment

- **Architecture:** x86-64 (primary), ARM64 (planned)
- **Operating System:** Linux (primary), other POSIX (planned)
- **Runtime:** None. No garbage collector, no libc dependency
- **Backend:** LLVM IR

### 1.3 Hello World

```ritz
fn main() -> i32
    print("Hello, World!\n")
    0
```

---

## 2. Lexical Structure

### 2.1 Source Encoding

Source files are UTF-8 encoded. All keywords and identifiers use ASCII.

### 2.2 Indentation

Ritz uses indentation for block structure. The canonical indentation is **4 spaces**.

```ritz
fn example()
    if condition
        statement1()
        statement2()
    else
        statement3()
```

Tabs are not permitted. Mixed indentation is an error.

### 2.3 Comments

```ritz
# Single-line comment (to end of line)
```

Block comments are not currently supported.

### 2.4 Keywords

```
and       as        async     await     break     const
continue  else      enum      extern    false     fn
for       if        import    in        let       loop
match     mut       not       or        pub       return
self      Self      struct    trait     true      type
var       while
```

### 2.5 Identifiers

Identifiers begin with a letter or underscore, followed by letters, digits, or underscores.

```
identifier := [a-zA-Z_][a-zA-Z0-9_]*
```

### 2.6 Literals

#### Integer Literals

```ritz
42          # Decimal
0xFF        # Hexadecimal
0o77        # Octal
0b1010      # Binary
-42         # Negative
```

#### Float Literals

```ritz
3.14
2.0e10
1e-5
```

#### Character Literals

```ritz
'A'         # Character (u8)
'\n'        # Escape sequence
'\t'        # Tab
'\\'        # Backslash
'\''        # Single quote
'\0'        # Null byte
```

#### String Literals

Three forms of string literals exist:

```ritz
"hello"     # String (heap-allocated, owned)
c"hello"    # *u8 (C-string, null-terminated)
s"hello"    # Span<u8> (zero-copy slice)
```

**Escape sequences:** `\n`, `\t`, `\r`, `\\`, `\"`, `\'`, `\0`

**String interpolation:**
```ritz
let name = "World"
let x = 42
"Hello, {name}! x = {x}\n"
```

### 2.7 Operators

| Category | Operators |
|----------|-----------|
| Arithmetic | `+`, `-`, `*`, `/`, `%` |
| Comparison | `==`, `!=`, `<`, `<=`, `>`, `>=` |
| Logical | `and`, `or`, `not` |
| Bitwise | `&`, `\|`, `^`, `~`, `<<`, `>>` |
| Assignment | `=`, `+=`, `-=`, `*=`, `/=`, `%=`, `&=`, `\|=`, `^=`, `<<=`, `>>=` |
| Pointer | `&`, `*`, `&mut` |
| Cast | `as` |
| Try | `?` |
| Member | `.`, `::` |
| Index | `[]` |
| Range | `..`, `..=` |

---

## 3. Types

### 3.1 Primitive Types

#### Integer Types

| Type | Size | Range |
|------|------|-------|
| `i8` | 8-bit signed | -128 to 127 |
| `i16` | 16-bit signed | -32,768 to 32,767 |
| `i32` | 32-bit signed | -2^31 to 2^31-1 |
| `i64` | 64-bit signed | -2^63 to 2^63-1 |
| `u8` | 8-bit unsigned | 0 to 255 |
| `u16` | 16-bit unsigned | 0 to 65,535 |
| `u32` | 32-bit unsigned | 0 to 2^32-1 |
| `u64` | 64-bit unsigned | 0 to 2^64-1 |

Signedness affects:
- Comparisons (signed vs unsigned)
- Division and modulo
- Extension when widening

#### Boolean Type

```ritz
let flag: bool = true
let done: bool = false
```

#### Float Types

```ritz
let f: f32 = 3.14
let d: f64 = 2.718281828
```

### 3.2 Pointer Types

```ritz
*T          # Raw pointer to T
*mut T      # Raw mutable pointer to T
&T          # Immutable borrow
&mut T      # Mutable borrow
```

The `null` keyword represents a null pointer:
```ritz
let p: *u8 = null
```

### 3.3 Array Types

Fixed-size, stack-allocated arrays:

```ritz
[N]T        # Array of N elements of type T
```

Examples:
```ritz
let arr: [10]i32 = [0; 10]    # Initialize all to 0
let buf: [1024]u8             # Uninitialized
arr[0] = 42                   # Index access
```

### 3.4 Slice Types

```ritz
Span<T>     # Fat pointer: (*T, len)
```

### 3.5 String Types

| Type | Description |
|------|-------------|
| `String` | Owned, heap-allocated, UTF-8 |
| `Span<u8>` | Borrowed byte slice with length |
| `*u8` | C-style null-terminated string |

### 3.6 Compound Types

See sections on [Structs](#9-structs) and [Enums](#10-enums).

### 3.7 Generic Types

See section on [Generics](#11-generics).

### 3.8 Type Aliases

```ritz
type IntPtr = *i32
type Result<T> = Result<T, Error>
```

---

## 4. Variables

### 4.1 Immutable Bindings (let)

```ritz
let x: i32 = 42       # Explicit type
let y = 100           # Type inferred
```

Immutable bindings cannot be reassigned:
```ritz
let x = 42
x = 43                # ERROR: cannot assign to immutable
```

### 4.2 Mutable Bindings (var)

```ritz
var count: i32 = 0
count = count + 1     # OK
count += 1            # OK (compound assignment)
```

### 4.3 Constants

Module-level constants:
```ritz
const MAX_SIZE: i64 = 1024
const PI: f64 = 3.14159265358979
```

Constants must have explicit types and compile-time values.

### 4.4 Type Inference

Local variable types can be inferred:
```ritz
let x = 42            # i32
let s = "hello"       # String
let v = vec_new()     # Vec<T> (may need annotation)
```

---

## 5. Functions

### 5.1 Function Declarations

```ritz
fn name(param1: Type1, param2: Type2) -> ReturnType
    body
```

No return type means the function returns nothing:
```ritz
fn greet(name: *u8)
    print("Hello, ")
    print(name)
```

### 5.2 Return

```ritz
fn add(a: i32, b: i32) -> i32
    return a + b

# Implicit return (last expression)
fn mul(a: i32, b: i32) -> i32
    a * b
```

### 5.3 External Functions

```ritz
extern fn syscall3(n: i64, a1: i64, a2: i64, a3: i64) -> i64
```

### 5.4 Methods

Methods are functions with a `self` parameter:

```ritz
fn Point.distance(self: &Point) -> i32
    self.x * self.x + self.y * self.y

fn Vec.push<T>(self: &mut Vec<T>, value: T)
    # implementation
```

Method syntax for calling:
```ritz
let d = point.distance()
vec.push(42)
```

### 5.5 Function Pointers

```ritz
type BinaryOp = fn(i32, i32) -> i32

fn apply(f: BinaryOp, a: i32, b: i32) -> i32
    f(a, b)
```

### 5.6 Closures

```ritz
let add_one = |x: i32| -> i32
    x + 1

let result = add_one(5)  # 6
```

---

## 6. Control Flow

### 6.1 If/Else

```ritz
if condition
    then_block
else if other_condition
    else_if_block
else
    else_block
```

### 6.2 While Loop

```ritz
while condition
    body
```

### 6.3 For Loop

Range-based for loops:
```ritz
for i in 0..10         # 0 to 9 (exclusive)
    print_int(i)

for i in 0..=10        # 0 to 10 (inclusive)
    print_int(i)
```

Iterator for loops:
```ritz
for item in collection
    process(item)
```

### 6.4 Loop (Infinite)

```ritz
loop
    if done
        break
    work()
```

### 6.5 Break and Continue

```ritz
while true
    if should_stop
        break
    if should_skip
        continue
    process()
```

---

## 7. Expressions

### 7.1 Arithmetic

```ritz
a + b       # Addition
a - b       # Subtraction
a * b       # Multiplication
a / b       # Division
a % b       # Modulo
```

### 7.2 Comparison

```ritz
a == b      # Equal
a != b      # Not equal
a < b       # Less than
a <= b      # Less or equal
a > b       # Greater than
a >= b      # Greater or equal
```

### 7.3 Logical

```ritz
a and b     # Logical AND (short-circuit)
a or b      # Logical OR (short-circuit)
not a       # Logical NOT
```

### 7.4 Bitwise

```ritz
a & b       # Bitwise AND
a | b       # Bitwise OR
a ^ b       # Bitwise XOR
~a          # Bitwise NOT
a << n      # Left shift
a >> n      # Right shift
```

### 7.5 Type Casting

```ritz
value as TargetType
```

Examples:
```ritz
let x: i64 = 42 as i64
let p: *u8 = null as *u8
let addr: i64 = ptr as i64
```

### 7.6 Pointer Operations

```ritz
&x          # Address of x
*p          # Dereference p
&mut x      # Mutable reference to x
```

### 7.7 Field Access

```ritz
point.x             # Field access
point.distance()    # Method call
ptr.field           # Auto-deref for pointers
```

### 7.8 Array Indexing

```ritz
arr[i]              # Index access
arr[i] = value      # Index assignment
```

### 7.9 Sizeof

```ritz
sizeof(Type)        # Size of type in bytes
sizeof(expression)  # Size of expression's type
```

---

## 8. Pattern Matching

### 8.1 Match Expression

```ritz
match value
    pattern1 => expression1
    pattern2 => expression2
    _ => default_expression
```

### 8.2 Patterns

#### Literal Patterns
```ritz
match n
    0 => "zero"
    1 => "one"
    _ => "many"
```

#### Enum Patterns
```ritz
match opt
    Some(x) => use(x)
    None => default()
```

#### Wildcard Pattern
```ritz
_ => ...            # Matches anything
```

---

## 9. Structs

### 9.1 Definition

```ritz
struct Point
    x: i32
    y: i32

struct Person
    name: String
    age: u32
```

### 9.2 Instantiation

```ritz
let p = Point { x: 10, y: 20 }
```

### 9.3 Field Access

```ritz
p.x
p.y = 30            # If mutable
```

### 9.4 Methods

```ritz
fn Point.new(x: i32, y: i32) -> Point
    Point { x: x, y: y }

fn Point.distance(self: &Point) -> i32
    self.x * self.x + self.y * self.y
```

---

## 10. Enums

### 10.1 Definition

```ritz
enum Color
    Red
    Green
    Blue

enum Option<T>
    Some(T)
    None

enum Result<T, E>
    Ok(T)
    Err(E)
```

### 10.2 Usage

```ritz
let c = Color::Red
let opt = Option::Some(42)
let res = Result::Ok("success")
```

### 10.3 Pattern Matching

```ritz
match opt
    Some(value) => print_int(value)
    None => print("none\n")
```

---

## 11. Generics

### 11.1 Generic Functions

```ritz
fn identity<T>(x: T) -> T
    x

fn swap<T>(a: &mut T, b: &mut T)
    let tmp = *a
    *a = *b
    *b = tmp
```

### 11.2 Generic Structs

```ritz
struct Vec<T>
    data: *T
    len: i64
    cap: i64

struct Pair<A, B>
    first: A
    second: B
```

### 11.3 Generic Enums

```ritz
enum Option<T>
    Some(T)
    None

enum Result<T, E>
    Ok(T)
    Err(E)
```

### 11.4 Monomorphization

Generics are monomorphized at compile time. Each instantiation generates specialized code.

---

## 12. Traits

### 12.1 Definition

```ritz
trait Printable
    fn print(self: &Self)

trait Drop
    fn drop(self: &mut Self)
```

### 12.2 Implementation

```ritz
impl Printable for Point
    fn print(self: &Point)
        print("Point({self.x}, {self.y})\n")

impl Drop for Vec<T>
    fn drop(self: &mut Vec<T>)
        free(self.data)
```

---

## 13. Ownership and Borrowing

### 13.1 Ownership

Each value has a single owner. When the owner goes out of scope, the value is dropped.

```ritz
let s = String::from("hello")   # s owns the string
# s goes out of scope, string is dropped
```

### 13.2 Move Semantics

By default, assignment moves ownership:

```ritz
let s1 = String::from("hello")
let s2 = s1                     # s1 moved to s2
# s1 is no longer valid
```

### 13.3 Borrowing

Borrowing creates references without taking ownership:

```ritz
let s = String::from("hello")
let r: &String = &s             # Immutable borrow
```

### 13.4 Mutable Borrowing

```ritz
let mut s = String::from("hello")
let r: &mut String = &mut s     # Mutable borrow
```

Rules:
- Many immutable borrows OR one mutable borrow
- Borrows must not outlive the owner

### 13.5 Drop Trait

Implement `Drop` for custom cleanup:

```ritz
impl Drop for Resource
    fn drop(self: &mut Resource)
        close(self.handle)
```

---

## 14. Error Handling

### 14.1 Result Type

```ritz
enum Result<T, E>
    Ok(T)
    Err(E)
```

### 14.2 Try Operator (?)

The `?` operator propagates errors:

```ritz
fn read_file(path: *u8) -> Result<String, Error>
    let fd = open(path)?        # Returns Err if failed
    let content = read_all(fd)?
    Ok(content)
```

### 14.3 Pattern Matching

```ritz
match result
    Ok(value) => use(value)
    Err(e) => handle_error(e)
```

---

## 15. Modules

### 15.1 Import

```ritz
import ritzlib.io               # Import all pub items
import ritzlib.sys as sys       # Import with alias
import ritzlib.io { read, write }  # Import specific items
```

### 15.2 Visibility

```ritz
pub fn exported()               # Public
    pass

fn private()                    # Private (default)
    pass

pub struct PublicStruct         # Public struct
    field: i32
```

### 15.3 Qualified Access

```ritz
import ritzlib.sys as sys
sys::write(fd, buf, len)
```

### 15.4 Re-exports

```ritz
pub import ritzlib.io           # Re-export all
pub import ritzlib.io { read }  # Re-export specific
```

---

## 16. Async/Await

### 16.1 Async Functions

```ritz
async fn fetch(url: *u8) -> Result<Vec<u8>, Error>
    let sock = await connect(url)?
    await read_all(sock)
```

### 16.2 Await

```ritz
let data = await fetch("http://example.com")?
```

### 16.3 Runtime

The async runtime uses io_uring for efficient async I/O on Linux.

---

## 17. Attributes

### 17.1 Test Attribute

```ritz
@test
fn test_addition() -> i32
    if 2 + 2 == 4
        return 0    # Pass
    return 1        # Fail
```

### 17.2 Inline Attribute

```ritz
@inline
fn hot_path() -> i32
    42
```

### 17.3 Future Attributes

- `@ignore` - Skip test
- `@slow` - Mark slow test
- `@deprecated` - Mark deprecated

---

## 18. Memory Model

### 18.1 Stack Allocation

Local variables and fixed-size arrays are stack-allocated:

```ritz
var buffer: [4096]u8    # Stack allocated
```

### 18.2 Heap Allocation

Heap allocation uses mmap/munmap directly (no malloc/free):

```ritz
let ptr = mmap(0, size, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0)
munmap(ptr, size)
```

### 18.3 No Garbage Collection

Ritz has no garbage collector. Memory is managed through:
- Stack allocation (automatic)
- RAII via Drop trait
- Explicit heap management

---

## 19. Standard Library

### 19.1 Core Modules (ritzlib)

| Module | Purpose |
|--------|---------|
| `sys` | System calls |
| `io` | I/O helpers |
| `memory` | Memory allocation |
| `str` | String utilities |
| `gvec` | Generic Vec<T> |
| `hashmap` | Hash table |
| `fs` | Filesystem |
| `args` | Argument parsing |
| `json` | JSON parsing |
| `process` | Process spawning |
| `uring` | io_uring bindings |
| `async_tasks` | Async runtime |

### 19.2 Built-in Functions

| Function | Description |
|----------|-------------|
| `print(s)` | Print string to stdout |
| `print_int(n)` | Print integer to stdout |
| `sizeof(T)` | Size of type in bytes |

---

## 20. Appendices

### A. Grammar (Simplified)

```
program      := item*
item         := fn_def | struct_def | enum_def | trait_def | const_def | import

fn_def       := 'fn' IDENT '(' params ')' ('->' type)? NEWLINE INDENT stmt+ DEDENT
struct_def   := 'struct' IDENT NEWLINE INDENT field+ DEDENT
enum_def     := 'enum' IDENT NEWLINE INDENT variant+ DEDENT
trait_def    := 'trait' IDENT NEWLINE INDENT fn_sig+ DEDENT

stmt         := let_stmt | var_stmt | if_stmt | while_stmt | for_stmt | return_stmt | expr_stmt
expr         := binary | unary | call | field | index | literal | IDENT
```

### B. Compilation

```bash
# Compile single file
./ritz run file.ritz

# Build package
./ritz build package_name

# Test package
./ritz test package_name
```

### C. Project Configuration (ritz.toml)

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

---

*This specification is maintained by the LARB project. For implementation details, see the ritz compiler documentation.*
