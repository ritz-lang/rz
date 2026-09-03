# Ritz Language Specification

**Version:** 0.4.0 (September 2026)
**Status:** Living document — describes the language the reference compiler
(`ritz0`) accepts *today*, post-RERITZ.

This document specifies the Ritz programming language. It is not a wish list:
every fenced ` ```ritz ` block below is compiled by
`tools/check_doc_examples.py` against `ritz0` on every build (`make
check-doc-examples`). A block that stops compiling fails the build, so the
syntax you read here is the syntax the compiler currently accepts.

Fences carry their own contract:

- ` ```ritz ` — top-level items; must compile.
- ` ```ritz body ` — statements; wrapped in a function and compiled.
- ` ```ritz expect-error="..." ` — an example the compiler **rejects**; the
  checker asserts it keeps failing with exactly that diagnostic. This is how
  removed syntax is documented: the removal itself is a test.

The previous edition of this file was stamped "0.2.0, February 2026" and sat
unchanged through the entire RERITZ migration while teaching syntax the
compiler had started rejecting. Sections describing features that were removed
now say so, next to a block proving the compiler rejects them.

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
13. [Ownership and References](#13-ownership-and-references)
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
3. **References without lifetimes** - `@T` / `@&T`, no borrow annotations
4. **One language for everything** - From kernel to script, same syntax
5. **Bootstrappable** - Self-hosting compiler shipped as LLVM IR

### 1.2 Target Environment

- **Architecture:** x86-64 (primary), ARM64 (planned)
- **Operating System:** Linux (primary), other POSIX (planned)
- **Runtime:** None. No garbage collector, no libc dependency
- **Backend:** LLVM IR

### 1.3 Hello World

```ritz
import ritzlib.io

fn main() -> i32
    prints("Hello, World!\n")
    0
```

`prints` takes a `StrView`, which is what a bare `"..."` literal produces. See
[§19](#19-standard-library) for the printing surface.

---

## 2. Lexical Structure

### 2.1 Source Encoding

Source files are UTF-8 encoded. All keywords and identifiers use ASCII.

### 2.2 Indentation

Ritz uses indentation for block structure. The canonical indentation is **4 spaces**.

```ritz
fn first()
    pass

fn second()
    pass

fn third()
    pass

fn example(condition: bool)
    if condition
        first()
        second()
    else
        third()
```

Tabs are not permitted for indentation; the lexer rejects them outright:

```ritz expect-error="Tabs not allowed for indentation"
fn tabbed() -> i32
	let x = 1
	return x
```

### 2.3 Comments

```ritz
# Single-line comment (to end of line)
```

Block comments are not supported.

### 2.4 Keywords

The reserved words recognised by the lexer:

```
and       as        assert    async     await     break
const     continue  dyn       else      enum      extern
false     fn        for       heap      if        impl
import    in        let       loop      match     mut
not       null      or        pub       return    static_assert
struct    then      trait     true      type      unsafe
var       while
```

`self` and `pass` are **not** keywords — they are ordinary identifiers with
special meaning by convention (`self` as a method receiver name, `pass` as a
no-op expression that evaluates to `0`). `mut` is reserved but only valid in
`*mut T`; `let mut` was removed by RERITZ (see [§4.2](#42-mutable-bindings-var)).

### 2.5 Identifiers

Identifiers begin with a letter or underscore, followed by letters, digits, or underscores.

```
identifier := [a-zA-Z_][a-zA-Z0-9_]*
```

### 2.6 Literals

#### Integer Literals

```ritz body
let dec = 42            # Decimal
let hex = 0xFF          # Hexadecimal
let bin = 0b1010        # Binary
let neg = -42           # Negative
let sized = 100u16      # Typed suffix
```

There is no octal literal form. `0o77` lexes as `0` followed by the identifier
`o77` and fails at name resolution.

#### Float Literals

```ritz body
let a = 3.14
let b = 2.0e10
let c = 1e-5
```

A float literal needs digits on both sides of the dot: `.5` and `5.` are not
accepted, because both are ambiguous with method dispatch and range syntax.

#### Character Literals

Character literals have type `u8`.

```ritz body
let a: u8 = 'A'         # Character
let nl: u8 = '\n'       # Escape sequence
let tab: u8 = '\t'      # Tab
let bs: u8 = '\\'       # Backslash
let q: u8 = '\''        # Single quote
let nul: u8 = '\0'      # Null byte
```

#### String Literals

Two forms of string literal exist:

```ritz body
let s: StrView = "hello"        # StrView: a { ptr, len } pair, no allocation
let c: *u8 = c"hello"           # *u8: NUL-terminated C string
```

**Removed in RERITZ:** the `s"..."` prefix. Bare `"..."` now produces exactly
the `{ ptr, len }` value that `s"..."` used to, so the prefix was redundant
(AGAST #98). `s"hello"` now lexes as the identifier `s` next to a string:

```ritz body expect-error="Unknown identifier: s"
let bad = s"hello"
```

`make check-no-s-strings` fails the build if one reappears in the tree.

**Escape sequences:** `\n`, `\t`, `\r`, `\\`, `\"`, `\'`, `\0`

**String interpolation:** `{name}` inside a string literal passed to the
`print` builtin substitutes the named variable.

```ritz body
let x = 42
print("x = {x}\n")
```

Interpolation is an integer-formatting facility: interpolating a `StrView`
fails with `Cannot print value of type {i8*, i64}`. To compose strings, call
`prints` more than once, or build a `String` with `string_push_strview`.

### 2.7 Operators

| Category | Operators |
|----------|-----------|
| Arithmetic | `+`, `-`, `*`, `/`, `%` |
| Comparison | `==`, `!=`, `<`, `<=`, `>`, `>=` |
| Logical | `and` / `&&`, `or` / `\|\|`, `not` / `!` |
| Bitwise | `&`, `\|`, `^`, `~`, `<<`, `>>` |
| Assignment | `=`, `+=`, `-=`, `*=`, `/=` |
| Reference | `@x` (immutable), `@&x` (mutable), `*p` (dereference) |
| Cast | `as` |
| Try | `?` |
| Member | `.` |
| Index | `[]` |
| Range | `..`, `..=` |

`&` is bitwise-AND only. `::` is not an operator in Ritz — see
[§15.3](#153-qualified-access).

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

An unannotated integer literal binding infers `i64`. Annotate when you need a
narrower type: `let x: i32 = 1`.

#### Boolean Type

```ritz body
let flag: bool = true
let done: bool = false
```

#### Float Types

```ritz body
let f: f32 = 3.14
let d: f64 = 2.718281828
```

### 3.2 Pointer and Reference Types

| Form | Meaning |
|------|---------|
| `*T` | Raw pointer to `T` |
| `*mut T` | Raw mutable pointer to `T` |
| `@T` | Immutable reference to `T` |
| `@&T` | Mutable reference to `T` |
| `name:& T` | Mutable-borrow parameter (equivalent to `name: @&T`) |

```ritz
struct Point
    x: i32
    y: i32

fn read(p: @Point) -> i32
    p.x

fn scale(p: @&Point, k: i32)
    p.x = p.x * k

fn raw(p: *mut i32)
    pass
```

**Removed in RERITZ:** `&T` and `&mut T` reference types. The compiler emits a
migration diagnostic rather than a generic parse error:

```ritz expect-error="Legacy `&T` reference syntax is no longer supported"
struct Point
    x: i32
    y: i32

fn dist(self: &Point) -> i32
    0
```

```ritz expect-error="Legacy `&mut T` syntax is no longer supported"
fn bump(x: &mut i32)
    pass
```

The `null` keyword represents a null pointer:

```ritz body
let p: *u8 = null
```

### 3.3 Array Types

Fixed-size, stack-allocated arrays are written `[N]T`. Declare them with `var`
if you intend to index-assign; a `let`-bound array is a value, not a place.

```ritz body
var arr: [10]i32
arr[0] = 42
var buf: [1024]u8
buf[0] = 'x'
```

`[value; N]` is an array-fill literal:

```ritz body
let zeros = [0; 10]
let first = zeros[0]
```

### 3.4 Slice Types

```ritz
import ritzlib.span

fn total(xs: Span<u8>) -> i64
    0
```

`Span<T>` is a fat pointer: `(*T, len)`.

### 3.5 String Types

| Type | Description |
|------|-------------|
| `String` | Owned, heap-allocated, growable |
| `StrView` | Borrowed `{ ptr, len }` view — the type of a `"..."` literal |
| `*u8` | C-style NUL-terminated string — the type of a `c"..."` literal |
| `Span<u8>` | Borrowed byte slice with length |

```ritz
import ritzlib.string
import ritzlib.strview

fn main() -> i32
    let s: String = string_from("hello")
    let n = string_len(@s)
    string_drop(@&s)
    n as i32
```

### 3.6 Compound Types

See sections on [Structs](#9-structs) and [Enums](#10-enums).

### 3.7 Generic Types

See section on [Generics](#11-generics).

### 3.8 Type Aliases

```ritz
type IntPtr = *i32
```

Two limitations in ritz0 today, both worth knowing before you reach for `type`:

- Generic aliases (`type Res<T> = Result<T, Error>`) do not parse — the parser
  wants `=` where the `<` is.
- An alias is accepted at its declaration but is not resolved at use sites, so
  a variable annotated `IntPtr` does not behave as `*i32`. Prefer spelling the
  underlying type until this is fixed.

---

## 4. Variables

### 4.1 Immutable Bindings (let)

```ritz body
let x: i32 = 42       # Explicit type
let y = 100           # Type inferred (i64)
```

Immutable bindings cannot be reassigned. The current diagnostic is terse — a
`let` binding is simply not registered as an assignable variable:

```ritz body expect-error="Unknown variable: x"
let x = 42
x = 43
```

### 4.2 Mutable Bindings (var)

```ritz body
var count: i32 = 0
count = count + 1     # OK
count += 1            # OK (compound assignment)
```

**Removed in RERITZ:** `let mut`. Mutability is spelled `var`:

```ritz body expect-error="Expected IDENT, got MUT"
let mut x = 5
```

Compound assignment operators are `+=`, `-=`, `*=`, `/=`. There is no `%=`,
`&=`, `|=`, `^=`, `<<=` or `>>=`.

### 4.3 Constants

Module-level constants:

```ritz
const MAX_SIZE: i64 = 1024
const PI: f64 = 3.14159265358979
```

Constants must have explicit types and compile-time values.

### 4.4 Type Inference

Local variable types are inferred from the initializer:

```ritz body
let x = 42            # i64
let n: i32 = 42       # i32, because it is annotated
let s = "hello"       # StrView
let c = c"hello"      # *u8
```

Generic calls need their type argument spelled out; there is no inference from
the binding's annotation:

```ritz
import ritzlib.gvec

fn main() -> i32
    var v = vec_new<i32>()
    vec_push<i32>(@&v, 42)
    let first = vec_get<i32>(@v, 0)
    vec_drop<i32>(@&v)
    first
```

---

## 5. Functions

### 5.1 Function Declarations

```ritz
fn add(a: i32, b: i32) -> i32
    a + b
```

No return type means the function returns nothing:

```ritz
import ritzlib.io

fn greet(name: *u8)
    prints("Hello, ")
    prints_cstr(name)
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

Methods live in `impl` blocks. The receiver is named `self`, either bare or
annotated `@Type` (read-only) / `@&Type` (mutating).

```ritz
struct Point
    x: i32
    y: i32

impl Point
    fn distance_squared(self) -> i32
        self.x * self.x + self.y * self.y

    fn scale(self: @&Point, k: i32)
        self.x = self.x * k
        self.y = self.y * k

fn main() -> i32
    var p = Point { x: 3, y: 4 }
    p.scale(2)
    p.distance_squared()
```

**Removed in RERITZ:** the free-standing `fn Type.method(...)` declaration
form. It is a parse error today:

```ritz expect-error="Expected LPAREN, got DOT"
struct Point
    x: i32
    y: i32

fn Point.distance(self) -> i32
    self.x
```

### 5.5 Function Pointer Types

`fn(A, B) -> C` is accepted as a type, most usefully as a struct field:

```ritz
struct Task
    handler: fn(*Task) -> i32
    id: i32
```

Function pointers lower to opaque LLVM `ptr`, and ritz0 cannot yet *call*
through a function-typed binding — `fn apply(f: BinaryOp, ...)` followed by
`f(a, b)` fails with `Unknown function: f`. Dispatch through an `impl` method
or a `match` in the meantime.

### 5.6 Closures

**Not implemented.** There is no closure or lambda syntax; the `|...|` form the
0.2.0 spec described never existed in the compiler:

```ritz body expect-error="Expected type name"
let add_one = |x: i32| -> i32
    x + 1
```

---

## 6. Control Flow

### 6.1 If/Else

```ritz body
let a = 1
if a == 0
    print("zero\n")
else if a == 1
    print("one\n")
else
    print("many\n")
```

`if` is a statement, not an expression. Use `match` where you want a value.

### 6.2 While Loop

```ritz body
var i = 0
while i < 10
    i += 1
```

### 6.3 For Loop

Range-based for loops:

```ritz
import ritzlib.io

fn main() -> i32
    for i in 0..10          # 0 to 9 (exclusive)
        print_int(i)
    for j in 0..=10         # 0 to 10 (inclusive)
        print_int(j)
    0
```

Iterator for loops walk a `Vec<T>`:

```ritz
import ritzlib.gvec
import ritzlib.io

fn main() -> i32
    let v = vec_new<i32>()
    for item in v
        print_int(item as i64)
    0
```

### 6.4 Loop (Infinite)

```ritz body
var i = 0
loop
    if i > 3
        break
    i += 1
```

### 6.5 Break and Continue

```ritz body
var n = 0
while true
    if n > 10
        break
    if n == 5
        n += 2
        continue
    n += 1
```

---

## 7. Expressions

### 7.1 Arithmetic

```ritz body
let a = 7
let b = 3
let sum = a + b
let diff = a - b
let prod = a * b
let quot = a / b
let rem = a % b
```

### 7.2 Comparison

```ritz body
let a = 1
let b = 2
let e = a == b
let n = a != b
let lt = a < b
let le = a <= b
let gt = a > b
let ge = a >= b
```

### 7.3 Logical

```ritz body
let a = true
let b = false
let both = a and b      # short-circuit AND
let either = a or b     # short-circuit OR
let neither = not a     # NOT
```

### 7.4 Bitwise

```ritz body
let a = 6
let b = 3
let and_ = a & b
let or_ = a | b
let xor = a ^ b
let inv = ~a
let shl = a << 1
let shr = a >> 1
```

### 7.5 Type Casting

```ritz body
let x: i64 = 42 as i64
let p: *u8 = null as *u8
let addr: i64 = p as i64
```

### 7.6 Reference Operations

```ritz body
var x: i32 = 1
let p = @x              # Immutable reference to x
let v = *p              # Dereference

var y: i32 = 2
let q = @&y             # Mutable reference to y
*q = 3                  # Assign through it
```

`@` binds tighter than `as`, so `@x as i64` parses as `(@x) as i64`.

**Removed in RERITZ:** `&x` address-of.

```ritz body expect-error="Legacy `&x` syntax is no longer supported"
var x: i32 = 1
let p = &x
```

### 7.7 Field Access

```ritz
struct Point
    x: i32
    y: i32

impl Point
    fn get_x(self) -> i32
        self.x

fn read(p: *Point) -> i32
    p.x                 # Auto-deref for pointers

fn main() -> i32
    let p = Point { x: 1, y: 2 }
    p.x + p.get_x()
```

### 7.8 Array Indexing

```ritz body
var arr: [4]i32
arr[0] = 7              # Index assignment
let v = arr[0]          # Index access
```

### 7.9 Sizeof

```ritz body
let a = sizeof(i32)         # Size of type in bytes
let n = 0
let b = sizeof(n)           # Size of expression's type
```

---

## 8. Pattern Matching

### 8.1 Match Expression

`match` works both as a statement and as the right-hand side of a binding.

```ritz
import ritzlib.io

fn describe(n: i64) -> i64
    match n
        0 => 10
        1 => 20
        _ => 30

fn main() -> i32
    let x = match 2
        0 => 1
        _ => 2
    describe(x) as i32
```

### 8.2 Patterns

#### Literal Patterns

```ritz
import ritzlib.io

fn main() -> i32
    match 2
        0 => prints("zero\n")
        1 => prints("one\n")
        _ => prints("many\n")
    0
```

#### Enum Patterns

```ritz
import ritzlib.option

fn find(x: i32) -> Option<i32>
    if x > 0
        return Some(x)
    return None

fn main() -> i32
    match find(5)
        Some(v) => v
        None => 0
```

#### Wildcard Pattern

`_` matches anything and binds nothing. `pass` is a valid arm body for arms
that should do nothing:

```ritz body
match 3
    0 => pass
    _ => pass
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
struct Point
    x: i32
    y: i32

fn main() -> i32
    let p = Point { x: 10, y: 20 }
    p.x + p.y
```

### 9.3 Field Access

```ritz
struct Point
    x: i32
    y: i32

fn main() -> i32
    var p = Point { x: 10, y: 20 }
    p.y = 30            # Requires a `var` binding
    p.x + p.y
```

### 9.4 Methods

Constructors are ordinary free functions; there is no `Type::new` path syntax.

```ritz
struct Point
    x: i32
    y: i32

fn point_new(x: i32, y: i32) -> Point
    Point { x: x, y: y }

impl Point
    fn distance_squared(self) -> i32
        self.x * self.x + self.y * self.y

fn main() -> i32
    point_new(3, 4).distance_squared()
```

---

## 10. Enums

### 10.1 Definition

```ritz
enum Color
    Red
    Green
    Blue

enum Shape
    Circle(i32)
    Square(i32)
```

`Option<T>` and `Result<T, E>` are defined in `ritzlib.option` and
`ritzlib.result` respectively; import them rather than redeclaring them.

### 10.2 Usage

Qualified variants use `.`, not `::`:

```ritz
enum Color
    Red
    Green
    Blue

fn main() -> i32
    let c = Color.Red
    match c
        Red => 1
        _ => 0
```

**Removed in RERITZ:** the `::` path separator, everywhere. `Color::Red`,
`String::from(...)` and `sys::write(...)` all parse into a qualified
identifier that no longer lowers:

```ritz body expect-error="Expression: <class 'ritz_ast.QualifiedIdent'>"
let c = Color::Red
```

Use free functions instead: `string_from(sv)`, `strview_from_cstr(p)`,
`vec_new<T>()`.

### 10.3 Pattern Matching

```ritz
import ritzlib.option
import ritzlib.io

fn get(flag: i32) -> Option<i64>
    if flag == 1
        return Some(42)
    return None

fn main() -> i32
    match get(1)
        Some(value) => print_int(value)
        None => prints("none\n")
    0
```

---

## 11. Generics

### 11.1 Generic Functions

```ritz
fn identity<T>(x: T) -> T
    x

fn swap<T>(a: @&T, b: @&T)
    let tmp = *a
    *a = *b
    *b = tmp

fn main() -> i32
    var x: i32 = 1
    var y: i32 = 2
    swap<i32>(@&x, @&y)
    identity<i32>(x)
```

Type arguments are explicit at the call site (`identity<i32>(x)`), including
pointer arguments (`option_is_none<*Page>(@p)`).

### 11.2 Generic Structs

```ritz
struct MyVec<T>
    data: *T
    len: i64
    cap: i64

struct Pair<A, B>
    first: A
    second: B
```

### 11.3 Generic Enums

```ritz
enum Maybe<T>
    Present(T)
    Absent

enum Either<T, E>
    Left(T)
    Right(E)
```

### 11.4 Monomorphization

Generics are monomorphized at compile time; each instantiation generates
specialized code. Only the *first* type argument participates in name
mangling: `Result<i32, StrView>` mangles to `Result$i32`.

---

## 12. Traits

### 12.1 Definition

```ritz
trait Printable
    fn show(self: @Self)

trait Drop
    fn drop(self: @&Self)
```

### 12.2 Implementation

```ritz
import ritzlib.io

struct Point
    x: i32
    y: i32

trait Printable
    fn show(self: @Self)

impl Printable for Point
    fn show(self: @Point)
        prints("Point(")
        print_int(self.x as i64)
        prints(", ")
        print_int(self.y as i64)
        prints(")\n")

fn main() -> i32
    let p = Point { x: 1, y: 2 }
    p.show()
    0
```

Traits are structural in ritz0: an `impl Trait for Type` block is checked for
shape and its methods are emitted, but there is no dynamic dispatch, no trait
bound on a generic parameter, and no `dyn Trait`. Methods are resolved
statically from the receiver's concrete type.

---

## 13. Ownership and References

### 13.1 Ownership

Each heap-owning value has a single owner. Ritz has no destructor insertion
today: owners are released by calling the type's `_drop` function explicitly.

```ritz
import ritzlib.string

fn main() -> i32
    let s = string_from("hello")    # s owns the buffer
    string_drop(@&s)                # released explicitly
    0
```

### 13.2 Move Semantics

Assignment of a struct copies its fields. For an owning type such as `String`
that means both bindings name the same buffer, and only one of them may drop
it — the compiler does not track this for you.

```ritz
import ritzlib.string

fn main() -> i32
    let s1 = string_from("hello")
    let s2 = s1                     # shares s1's buffer
    string_drop(@&s2)               # drop exactly once
    0
```

### 13.3 Borrowing

`@x` takes an immutable reference without taking ownership:

```ritz
import ritzlib.string

fn main() -> i32
    let s = string_from("hello")
    let n = string_len(@s)          # borrow for the call
    string_drop(@&s)
    n as i32
```

### 13.4 Mutable Borrowing

`@&x` takes a mutable reference. In a parameter list, `name:& T` is an
equivalent spelling.

```ritz
import ritzlib.string

fn append(s: @&String) -> i32
    string_push_strview(s, " world")

fn main() -> i32
    var s = string_from("hello")
    append(@&s)
    let n = string_len(@s)
    string_drop(@&s)
    n as i32
```

### 13.5 Borrow Rules

The rules are Rust's, minus the lifetimes:

- any number of `@` (shared) borrows of a value, **or** exactly one `@&`
  (mutable) borrow;
- a borrow must not outlive the owner.

The first rule is checked. Taking `@&x` while an `@x` is live is an error:

```ritz body expect-error="cannot borrow `x` as mutable - already borrowed as immutable"
var x: i32 = 1
let p = @x
let q = @&x
```

There are no lifetime annotations and no generic lifetime parameters; escape
analysis is not performed, so returning a reference to a local is not caught.

### 13.6 Drop

`Drop` is an ordinary trait, and implementing it does not cause the compiler to
call `drop` for you at scope exit:

```ritz
struct Resource
    handle: i32

trait Drop
    fn drop(self: @&Self)

impl Drop for Resource
    fn drop(self: @&Resource)
        self.handle = 0

fn main() -> i32
    var r = Resource { handle: 3 }
    r.drop()
    r.handle
```

`defer` is reserved in the ritz1 grammar but is not implemented in ritz0:

```ritz body expect-error="Unknown identifier: defer"
defer print("bye\n")
```

---

## 14. Error Handling

### 14.1 Result Type

`Result<T, E>` comes from `ritzlib.result`:

```ritz
import ritzlib.result

fn go(x: i32) -> Result<i32, i32>
    if x > 0
        return Ok(x)
    return Err(1)
```

`Ok` and `Err` are resolved against the enclosing function's declared return
type, so a `Result`-returning signature is required to construct one.

### 14.2 Try Operator (?)

`?` unwraps an `Ok` and returns early on `Err`:

```ritz
import ritzlib.result

fn parse(x: i32) -> Result<i32, i32>
    if x > 0
        return Ok(x)
    return Err(1)

fn double(x: i32) -> Result<i32, i32>
    let v = parse(x)?
    Ok(v + v)
```

The operand must be a `Result`-typed call; applying `?` to anything else fails
with `Try operator requires a Result type`.

### 14.3 Pattern Matching

```ritz
import ritzlib.result

fn go(x: i32) -> Result<i32, i32>
    if x > 0
        return Ok(x)
    return Err(1)

fn main() -> i32
    match go(5)
        Ok(value) => value
        Err(e) => e
```

---

## 15. Modules

### 15.1 Import

```ritz
import ritzlib.io                  # Import the module's pub items
import ritzlib.sys as sys          # Import with alias
import ritzlib.gvec { vec_new }    # Selective import
```

The selective form is recognised but does not currently filter: the whole
module is imported either way. The alias form is likewise parsed and recorded
but unused, because there is no qualified-access syntax to use it with (see
[§15.3](#153-qualified-access)).

### 15.2 Visibility

```ritz
pub fn exported() -> i32
    0

fn private() -> i32              # Private (default)
    0

pub struct PublicStruct
    field: i32

pub const LIMIT: i64 = 16
```

### 15.3 Qualified Access

**Removed in RERITZ.** There is no `module::item` or `module.item` access
form. Imported names land in a single flat namespace, which is why the standard
library uses long, prefixed free-function names (`strview_find`,
`vec_push`, `string_from`) instead of short names behind a module path.

```ritz body expect-error="Expression: <class 'ritz_ast.QualifiedIdent'>"
let n = sys::write(1, c"hi\n", 3)
```

### 15.4 Re-exports

```ritz
pub import ritzlib.io           # Re-export the module's pub items
```

---

## 16. Async/Await

### 16.1 Async Functions

`async fn` lowers each function to a state-machine struct; `await` drives an
inner future.

```ritz
async fn fetch(x: i32) -> i32
    x

async fn go(x: i32) -> i32
    await fetch(x)

fn main() -> i32
    0
```

### 16.2 Await

`await` is supported in tail position. Binding an awaited value
(`let v = await fetch(x)`) currently fails to lower — the transform does not
add the temporary to the generated future struct, so it reports `Unknown field
v in struct go_Future`. Keep `await` as the arm/tail expression until that is
fixed.

### 16.3 Runtime

The async runtime uses io_uring for asynchronous I/O on Linux; see
`ritzlib/uring.ritz` and `ritzlib/async_runtime.ritz`.

---

## 17. Attributes

Attributes use double-bracket syntax on the line before the item.

### 17.1 Test Attribute

```ritz
[[test]]
fn test_addition() -> i32
    assert 2 + 2 == 4
    0
```

### 17.2 Target Attribute

```ritz
[[target_os = "linux"]]
fn platform_id() -> i32
    1
```

### 17.3 The `@` Attribute Syntax Was Removed

`@` is the reference operator now, so `@test` / `@inline` no longer parse as
attributes:

```ritz expect-error="Expected item, got AT"
@test
fn test_addition() -> i32
    0
```

`@inline` in particular has no replacement: there is no inlining attribute.

---

## 18. Memory Model

### 18.1 Stack Allocation

Local variables and fixed-size arrays are stack-allocated:

```ritz body
var buffer: [4096]u8
buffer[0] = 0
```

### 18.2 Heap Allocation

Heap allocation goes through `mmap`/`munmap` directly (no `malloc`/`free`),
either raw via `ritzlib.sys` or through the size-binned allocator in
`ritzlib.memory`:

```ritz
import ritzlib.sys

fn main() -> i32
    let size: i64 = 4096
    let p = sys_mmap(0, size, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0)
    sys_munmap(p, size)
    0
```

```ritz
import ritzlib.memory

fn main() -> i32
    let p = heap_alloc(64)
    heap_free(p, 64)
    0
```

### 18.3 No Garbage Collection

Ritz has no garbage collector. Memory is managed through:
- Stack allocation (automatic)
- Explicit `*_drop` calls on owning types
- Explicit heap management (`heap_alloc` / `heap_free`, arenas)

---

## 19. Standard Library

### 19.1 Core Modules (ritzlib)

| Module | Purpose |
|--------|---------|
| `sys` | System calls |
| `io` | I/O helpers |
| `memory` | Arena and size-binned heap allocation |
| `str` / `strview` / `string` | String utilities |
| `span` | `Span<T>` slices |
| `gvec` | Generic `Vec<T>` |
| `hashmap` | Hash table |
| `option` / `result` | `Option<T>`, `Result<T, E>` |
| `fs` | Filesystem |
| `args` / `env` | Argument and environment access |
| `json` | JSON parsing |
| `process` | Process spawning |
| `uring` | io_uring bindings |
| `async_runtime` / `async_tasks` | Async runtime |

See `docs/STDLIB_REFERENCE.md` for the function-level reference.

### 19.2 Built-in Functions

| Function | Description |
|----------|-------------|
| `print(literal)` | Print a string literal, with `{var}` interpolation |
| `sizeof(T)` / `sizeof(expr)` | Size in bytes |
| `assert cond` | Runtime check; exits non-zero on failure |

`print` is the only builtin that takes a string, and it requires a literal:

```ritz body expect-error="print() requires a single string literal argument"
let s = "hi"
print(s)
```

Everything else is a library function that must be imported. The printing
surface in `ritzlib.io` is:

```ritz
import ritzlib.io

fn main() -> i32
    prints("StrView\n")             # prints(s: StrView)
    prints_cstr(c"C string\n")      # prints_cstr(s: *u8)
    print_int(42)                   # print_int(n: i64)
    print_char('!')                 # print_char(c: u8)
    newline()
    0
```

---

## 20. Appendices

### A. Grammar (Simplified)

The machine-readable ground truth is `grammars/ritz1.grammar`, from which the
self-hosted parser is generated. A sketch:

```
program      := item*
item         := attrs? (fn_def | extern_fn | struct_def | enum_def
                        | const_def | global_var | import | impl_block)

attr         := '[[' IDENT ']]' | '[[' IDENT '=' STRING ']]'
fn_def       := 'pub'? 'fn' IDENT generic_params? '(' params? ')'
                ('->' type)? block
struct_def   := 'pub'? 'struct' IDENT generic_params? NEWLINE INDENT field+ DEDENT
enum_def     := 'pub'? 'enum' IDENT generic_params? NEWLINE INDENT variant+ DEDENT
impl_block   := 'impl' generic_params? (IDENT 'for')? IDENT NEWLINE
                INDENT fn_def* DEDENT

type         := 'i8'|'i16'|'i32'|'i64'|'u8'|'u16'|'u32'|'u64'|'bool'
              | '*' type | '@' type | '@' '&' type | '[' NUMBER ']' type
              | 'fn' '(' type_list? ')' ('->' type)?
              | IDENT ('<' type_list '>')?

stmt         := let_stmt | var_stmt | return_stmt | if_stmt | while_stmt
              | for_stmt | loop_stmt | match_stmt | assert_stmt
              | break_stmt | continue_stmt | assign_stmt | expr_stmt
expr         := binary | unary | cast | call | field | index | try | match
              | literal | struct_lit | array_lit | IDENT
```

`trait` blocks are accepted by ritz0 but have no production in
`ritz1.grammar` yet — the self-hosted compiler does not parse them.

### B. Compilation

```bash
# Compile and run a single file
python3 build.py run file.ritz

# Build a package (by directory name under examples/, or a path)
python3 build.py build 21_ls

# Test a package
python3 build.py test 21_ls

# Compile one file with the reference compiler directly
RITZ_PATH=$PWD python3 ritz0/ritz0.py file.ritz -o file.ll
```

### C. Project Configuration (ritz.toml)

```toml
[package]
name = "ritz1"
version = "0.1.0"
description = "Self-hosted Ritz compiler"

[[bin]]
name = "ritz1"
path = "src/main.ritz"
entry = "main::main"
```

Note that `entry` uses a `module::function` string — that is a build-system
key, not Ritz syntax, and is unaffected by the removal of `::` from the
language.

---

*Maintained in `projects/ritz/docs/`. Every ` ```ritz ` block here is compiled
by `make check-doc-examples`; if you change the language, this file fails
until you change it too.*
