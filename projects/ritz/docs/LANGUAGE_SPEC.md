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

The 39 reserved words recognised by the lexer (`ritz0/tokens.py:KEYWORDS`):

```
and       as        asm       assert    async     await
break     const     continue  dyn       else      enum
extern    false     fn        for       heap      if
impl      import    in        let       loop      match
mut       not       null      or        pub       return
static_assert       struct    then      trait     true
type      unsafe    var       while
```

`self` and `pass` are **not** keywords — they are ordinary identifiers with
special meaning by convention (`self` as a method receiver name, `pass` as a
no-op expression that evaluates to `0`). `mut` is reserved but only valid in
`*mut T`; `let mut` was removed by RERITZ (see [§4.2](#42-mutable-bindings-var)).

`asm` is reserved but has no syntax behind it yet; it is listed here because
using it as an identifier is an error, which is the only thing a reader needs
from this table:

```ritz body expect-error="Expected IDENT, got ASM"
let asm = 1
```

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

A literal has no fixed type until a slot gives it one, as `5`, `null` and
`[1, 2]` already behave. `"..."` is `StrView` by default and `*u8` in a `*u8`
slot, wherever that slot is: `let`, `var`, `=`, `return`, a tail, a field, an
array element, an `if` or `match` arm, an argument (LARB R3, AGAST #2341).
`c"..."` is always `*u8`, so it is what an untyped `let` needs:

```ritz
struct Name
    text: *u8

fn pick(short: bool) -> *u8
    if short
        "a"
    else
        "alpha"

fn main() -> i32
    let p: *u8 = "hello"
    let n = Name { text: "hi" }
    let names: [2]*u8 = ["x", "y"]
    (*p as i32) - 104 + (*n.text as i32) - 104 + (*names[1] as i32) - 121 + (*pick(true) as i32) - 97
```

**Every string literal is stored NUL-terminated**, `"..."` and `c"..."` alike:
the terminator follows the literal's bytes and isn't counted in a `StrView`'s
`len`.

Only the literal converts. A literal is retyped, a value isn't, so a `StrView`
that happens to hold a literal doesn't reach `*u8` (see [String
Types](#35-string-types)).

A literal that doesn't fit its slot is an error wherever it is, including in an
array element, and an integer literal is held to the slot's whole range, with
hex no exception. `as` says the truncation is meant:

```ritz body expect-error="`300` does not fit in `u8`"
var a: [2]u8 = [1, 300]
```

```ritz body expect-error="`3735928559` does not fit in `i32`"
let a: i32 = 0xDEADBEEF
```

```ritz body
let a: i32 = 0xDEADBEEF as i32
```

**Removed in RERITZ:** the `s"..."` prefix. Bare `"..."` now produces exactly
the `{ ptr, len }` value that `s"..."` used to, so the prefix was redundant
(AGAST #98). `s"hello"` now lexes as the identifier `s` next to a string:

```ritz body expect-error="Unknown identifier: s"
let bad = s"hello"
```

`make check-no-s-strings` fails the build if one reappears in the tree.

**Escape sequences:** `\n`, `\t`, `\r`, `\\`, `\"`, `\'`, `\0`, and `\{` /
`\}` for a literal brace anywhere

**String interpolation:** `{expr}` inside a **plain** string literal passed to
the `print` or `eprint` builtin substitutes the value of `expr`. `print` writes
to stdout (fd 1) and `eprint` to stderr (fd 2); otherwise the two are the same
(AGAST #1641). A placeholder is not restricted to bare variable names. Any
expression works, including a call:

```ritz
fn twice(n: i64) -> i64
    return n * 2

fn main() -> i32
    let x: i64 = 21
    let name: StrView = "--out"
    print("x = {x}\n")
    print("twice = {twice(x)}\n")
    eprint("option '{name}' needs a value\n")
    return 0
```

Interpolation is a rule of the two builtins (and of `format_into`, below),
not of the string literal. The
same `"{x}"` anywhere else, such as a `let`, an argument to any other function,
a `return` or a struct field, is the three bytes `{`, `x`, `}`. A bare
`"{x}"` statement prints nothing (AGAST #2102).

Inside a `print` or `eprint` literal, `{{` prints one `{` and `}}` one `}`.
That escape belongs to print interpolation, not to the string literal: a plain
`"..."` used anywhere else keeps both braces, so `"x{{y"` is four bytes and
`prints("{{")` writes two braces (AGAST #1913). Write `\{` / `\}` for a
literal brace that means the same thing in every context.

**Interpolation does NOT apply to `c"..."` literals** (AGAST #1374). A
c-string is opaque bytes, so `print(c"x = {x}\n")` would print the placeholder
verbatim. That used to compile clean and exit 0 with wrong output; it is now a
compile error directing you at the plain-string form.

The asymmetry is deliberate rather than an oversight. Making c-strings
interpolate would break 48 sites across the workspace that rely on `{...}`
staying opaque -- including ritz1's own emitter, which builds LLVM inline-asm
constraint strings such as `"={rax},{rax},{rdi},~{rcx}"`, where `{rax}` and
`{rdi}` are register constraints. Interpolating those corrupts every syscall
the self-hosted compiler emits. A c-string containing braces is therefore
still perfectly legal; only passing one to `print` or `eprint` is rejected.

A placeholder is `{` with a matching `}` before the end of the literal; a `{`
with no match is a literal brace, as is a lone `}`, `}}`, `\{` or `\}`.
Whitespace around the expression is ignored, and an empty or unparseable
placeholder is a compile error.

What a placeholder prints depends on the value's type:

| Type | Prints |
|------|--------|
| signed integers (`i8` … `i64`) | decimal, with a `-` when negative |
| unsigned integers (`u8` … `u64`) | unsigned decimal: never a `-` |
| `bool` | `true` or `false` |
| `StrView`, `@StrView`, `*StrView` | exactly `len` bytes from `ptr` (no NUL needed, none past `len`) |
| other pointers (`*u8`, ...) | the NUL-terminated bytes they point at |

A `String` prints through its view: `print("s = {string_as_view(@s)}\n")`
(`ritzlib.string`). Every other type, including floats and other structs, is a
compile error. ritz0 and ritz1 follow the same rules and print the same bytes
(AGAST #1521, #1641).

Signedness comes from the value's Ritz type, wherever the value comes from: a
local, a field, a call result or an `as` cast (AGAST #2128).

```ritz
fn top() -> u64
    return 18446744073709551615

fn main() -> i32
    let a: u8 = 200
    let n: i32 = -1
    print("{a} {n} {n as u32} {top()}\n")  # 200 -1 4294967295 18446744073709551615
    return 0
```

#### Formatting into a buffer: `format_into`

`format_into(sink, "...")` appends instead of printing (AGAST #1824). The
literal is `print`'s: the same placeholders, the same `{{` / `}}` and `\{` /
`\}` escapes, and the same refusal of a `c"..."` literal that holds a
placeholder. Each piece of the literal, whether text or a formatted value, is
appended to `*sink`:

```ritz
import ritzlib.string

fn emit_trunc(out: *String, r: i32, v: i32, ty: StrView)
    format_into(out, "  %{r} = trunc i64 %{v} to {ty}\n")

fn main() -> i32
    var ir: String = string_new()
    emit_trunc(@&ir, 4, 2, "i32")
    format_into(@&ir, "  ret i32 %{4}\n")
    print("{string_as_view(@ir)}")
    string_drop(@&ir)
    return 0
```

`{{` is how a literal brace goes into the buffer. That matters for text that
is full of braces, such as an LLVM inline-asm constraint, where `{rax}` names
a register rather than a placeholder:

```ritz
import ritzlib.string

fn main() -> i32
    var c: String = string_new()
    let n: i64 = 3
    format_into(@&c, "\"={{rax}},{{rax}},{{rdi}},~{{rcx}}\" ; {n} operands\n")
    print("{string_as_view(@c)}")
    string_drop(@&c)
    return 0
```

**The sink** is a pointer to a struct (`@&buf`, or a `*T` / `@&T` value)
whose method `push_bytes(data: *u8, len: i64)` resolves statically, exactly
as `sink.push_bytes(data, len)` would (§12.2). `String`, `GrowBuf` and
`Vec<u8>` provide it (`string_push_bytes`, `growbuf_push_bytes`,
`vec_push_bytes`), and any type can by implementing it:

```ritz
struct Count
    bytes: i64

impl Count
    fn push_bytes(self: @&Count, data: *u8, len: i64) -> i32
        self.bytes = self.bytes + len
        return 0

fn main() -> i32
    var c: Count = Count { bytes: 0 }
    let id: u32 = 4000000000
    format_into(@&c, "id={id}\n")
    return c.bytes as i32           # 14
```

The sink is evaluated once, before any placeholder. Placeholders are then
evaluated left to right, each once. `format_into` only appends and never
clears the buffer, and it produces no value. `push_bytes`'s result is
discarded, as `print` discards `write`'s.

A placeholder formats exactly as `print` prints it (the table above), so a
`u64` holding 2^64 - 1 appends `18446744073709551615`. Both use the same
integer formatter.

These are compile errors:

```ritz expect-error="not a value"
import ritzlib.string

fn main() -> i32
    var s: String = string_new()
    format_into(s, "x")             # a copy would get the bytes
    return 0
```

```ritz expect-error="must be a string literal"
import ritzlib.string

fn main() -> i32
    var s: String = string_new()
    let f: StrView = "{x}"
    format_into(@&s, f)             # placeholders are resolved at compile time
    return 0
```

```ritz expect-error="do not interpolate"
import ritzlib.string

fn main() -> i32
    var s: String = string_new()
    let x: i64 = 1
    format_into(@&s, c"x={x}")      # would append `{x}` verbatim
    return 0
```

A sink type without `push_bytes` is an error naming the type, and so is a
placeholder of a type with no formatted form.

**Why `format_into`.** AGAST #1824 weighed three spellings:

- `write(buf, "...")` reads well, but `write` is already taken. ritz0 lowers
  `write(fd, ptr, len)` as a syscall builtin, and the workspace defines
  `write` as an `extern fn` and as methods. A builtin of that name would
  change the meaning of existing calls.
- `String.fmt(...)` would tie formatting to one type and need an
  associated-builtin form neither compiler has. ritz1's own emitter, the
  motivating user, writes into a `Vec<u8>`, not a `String`.
- `format_into(sink, "...")` is a new name with no existing uses. It says
  what it does, and it takes any sink with `push_bytes`.

It is reserved like `print`: a call named `format_into` is always this
builtin.

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
| `name:& T` | Mutable-borrow parameter: `name` is the caller's place, of type `T` (§13.4) |

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

An `@T` is read-only. `p.f = v`, `p[i] = v` and `*p = v` through one are errors,
directly or through a chain of fields, so a place behind an `@T` stays read-only
even where an `@&T` lies between. The fix is an `@&T`. A write that reaches a
raw `*T` first isn't checked: it writes what the pointer points at, so an `@T`
to a struct says nothing about a `*T` field's pointee.

```ritz expect-error="cannot write through an `@T`: make it `@&T`"
struct Point
    x: i32
    y: i32

fn reset(p: @Point)
    p.x = 0

fn main() -> i32
    var q = Point { x: 1, y: 2 }
    reset(@q)
    q.x
```

An `@T` doesn't become an `@&T`. An `@T` value, whether held in a binding or a
field or returned by a call, doesn't fit an `@&T` slot, and a method taking
`self: @&T` can't be called on an `@T`, or on a place behind one. The other
pointer conversions stay free, so `@&T` fits `@T`, and `@T` fits `*T`.

```ritz expect-error="an `@T` doesn't fit an `@&T` slot: make it `@&T`"
struct Point
    x: i32
    y: i32

fn reset(p: @&Point)
    p.x = 0

fn clear(p: @Point)
    reset(p)

fn main() -> i32
    var q = Point { x: 1, y: 2 }
    clear(@q)
    q.x
```

`@T` and `@&T` are types: a parameter of one holds a reference, and reads as one.
`name:& T` is a mode: `name` has type `T`. The two share an ABI, and read
differently:

```ritz
struct Point
    x: i32
    y: i32

fn through(p: @&Point)
    let q: @&Point = p              # p is a reference
    q.x = 1

fn alias(p:& Point)
    let q: @&Point = @&p            # p is a Point
    q.x = 1
```

A value never fits a reference type, and a reference never fits a by-value type.
`@x` and `@&x` make a reference, `*r` reads through one (§13.2, §13.4).

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

An array literal or fill has no element type of its own until a slot gives it
one, so it takes the element type of the array it lands in, element by element
under §7.5:

```ritz body
var bytes: [4]u8 = [1, 2, 3, 200]
var words: [4]i32 = [0; 4]
```

Anything else already has its type, and fits an `[N]T2` only if it is an `[N]T2`.
That holds at every store: an argument, `let`, `var`, `=`, `*p =`, a global, a
field, a `return`, and under `as`. There's no widening, narrowing or sign change
between arrays, even where the elements have the same size:

```ritz body expect-error="an array only fits a slot of the same element type: write a loop to convert it"
var a: [4]i64 = [0, 0, 0, 3]
var b: [4]i32 = a
```

```ritz body expect-error="an array only fits a slot of the same element type: write a loop to convert it"
var a: [4]u32 = [0, 0, 0, 3]
var b: [4]i32 = a
```

A conversion is a loop you write:

```ritz body
var a: [4]i64 = [0, 0, 0, 3]
var b: [4]i32
for i in 0..4
    b[i] = a[i] as i32
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
| `StrView` | Borrowed `{ ptr, len }` view — the default type of a `"..."` literal |
| `*u8` | C-style NUL-terminated string — the type of a `c"..."` literal, and of a `"..."` literal in a `*u8` slot |
| `Span<u8>` | Borrowed byte slice with length |

```ritz
import ritzlib.string
import ritzlib.strview

fn main() -> i32
    var s: String = string_from("hello")
    let n = string_len(@s)
    string_drop(@&s)
    n as i32
```

A string literal fits a `*u8` slot ([§2.6](#26-literals)). Nothing else converts,
because a `StrView` may be a slice with no terminator and a `String` has to be
asked for one. `sv as *u8` is refused too. Write `.ptr` if you know the view is
NUL-terminated, and `string_as_ptr` for a `String`:

```ritz body expect-error="a StrView is not a `*u8`"
let s: StrView = "hello"
let p: *u8 = s
```

```ritz expect-error="a String is not a `*u8`"
import ritzlib.string

fn main() -> i32
    var s: String = string_from("hello")
    let p: *u8 = s
    0
```

```ritz
import ritzlib.string
import ritzlib.strview

fn main() -> i32
    let view: StrView = "hello"
    let a: *u8 = view.ptr              # You know this view is terminated
    var s: String = string_from("hello")
    let b: *u8 = string_as_ptr(@&s)
    let same: bool = *a == *b
    string_drop(@&s)
    if same
        return 0
    1
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

Immutable bindings cannot be reassigned, whole or with a compound operator
(`x += 1`):

```ritz body expect-error="cannot assign to `let` binding `x`; declare it `var`"
let x = 42
x = 43
```

Nor can a `let` be changed through a field or array element, or lent out
mutably with `@&`: anything that writes the binding's own storage needs a
`var`. Writing *through* a pointer held in a `let` is fine, since that
changes the pointee, not the binding.

```ritz body expect-error="cannot assign through `let` binding `a`; declare it `var`"
let a: [2]i64 = [1, 2]
a[0] = 3
```

```ritz body expect-error="cannot borrow `let` binding `k` as mutable; declare it `var`"
let k: i64 = 1
let p: *i64 = @&k
```

```ritz body
var a: [2]i64 = [1, 2]
let p: *i64 = @&a[0]
p[1] = 3              # OK: writes a[1] through the pointer
```

A binding is a place with one address for as long as it lives, `let` included.
`@x` is that address every time, so two `@x` are equal, and a receiver taken by
reference is `@x`: a `self: *T` method called on a `let` runs on the `let`, not on
a copy. A `*T` holding `@x` isn't checked (§3.2), so a write through it reaches
the `let`. That is the raw-pointer escape; `@&`, `:&` and direct writes stay
refused.

```ritz
struct C
    x: i32

impl C
    fn set(self: *C)
        self.x = 3

fn main() -> i32
    let c: C = C { x: 1 }
    let p: *C = @c
    let q: *C = @c        # p == q: one address
    p.x = 2               # c.x is 2
    c.set()               # runs on c: c.x is 3
    c.x
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

Such a function is a *procedure*, and a call to one has no value. Both compilers
reject a `let`, a `var`, or a `return` from a function that declares a value when
it would take its value from one. A procedure may still `return` a call to
another procedure, because nothing uses a value there.

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

`extern fn` is a C-style symbol: top level only, no `pub`, no attributes.

**Declaration-only fns.** A fn or method header ending in `= extern`
instead of a body declares the fn without defining it. The body lives in
another object, under the same symbol and ABI as in the module that defines
it, so a call emits exactly the `declare` that importing that module would.
The form is valid at top level and in a plain `impl` block, and takes `pub`
and attributes as a definition does. It is how a module's interface is
written as Ritz source (AGAST #1900, #1901).

```ritz
pub struct Pt
    x: i64
    y: i64

pub fn add(a: i64, b: i64) -> i64 = extern

impl Pt
    fn sum(self: *Pt) -> i64 = extern
    pub fn bump(self: *Pt, by: i64) = extern
```

A body the using module needs itself can't be declaration-only, so each of
these is a compile error naming the item: a generic fn, a method of a
generic impl (importers instantiate both), an `async fn` (its body is
transformed where it is used), a `[[test]]` fn, and a trait method (already
a signature).

```ritz expect-error="cannot be declaration-only"
pub fn ident<T>(x: T) -> T = extern
```

*Why `= extern`:* it is a tail on an unchanged header, so a definition
becomes its declaration by replacing the body and nothing else, and both
parsers see it as one extra alternative after the return type: `=` can't
start a type or a block. Two alternatives were rejected. A `[[decl]]`
attribute on a header with no INDENT needs attributes on impl methods,
which ritz1 does not parse, and it makes a forgotten body look like a
declaration. Widening `extern fn` to methods, `pub` and attributes would
blur the C-style symbol it declares today. The keyword `extern` keeps one
meaning: "defined in another object".

**External data.** `extern var NAME: T` declares a data symbol that another
object defines, as `extern fn` does for code. The usual case is a linker
symbol, whose address is the information:

```ritz
extern var __bss_start: u8
extern var __bss_end: u8
extern var boot_ticks: u64

fn bss_size() -> i64
    @__bss_end as i64 - @__bss_start as i64

fn tick()
    boot_ticks = boot_ticks + 1
```

The declaration has a type and no initializer. It is read, written and
addressed like a module `var`, and emits `@NAME = external global T` with
T's exact size and alignment: `extern var __bss_start: u8` claims one byte
at alignment 1, nothing more. It is valid at top level, takes `pub`, and
takes no attributes. An initializer is a compile error naming the symbol:

```ritz expect-error="extern var cannot have an initializer"
extern var boot_ticks: u64 = 0
```

*Why `extern var`:* the same keyword, with the same meaning, in front of the
item that would otherwise define the storage. Declaring a linker symbol as
`extern fn __bss_start()` and casting its address (what harland did,
AGAST #1879) puts data behind a fn type, and a call through it would jump
into it.

### 5.4 Methods

Methods live in `impl` blocks. The receiver is named `self`, either bare or
annotated `@Type` (read-only) / `@&Type` (mutating). A bare `self` and `self: Type`
are one thing, a by-value parameter named `self`: the method has its own storage, a
copy type is copied and a move-only type moves (§13.2). A write to it stays in the
method, and `@self` is a reference to a local (§13.5). `self:& Type` is the caller's
place, and a write to it lands there.

```ritz
struct Counter
    n: i32

impl Counter
    fn after(self) -> i32
        self.n = self.n + 1
        self.n
    fn advance(self:&)
        self.n = self.n + 1

fn demo() -> i32
    var c = Counter { n: 1 }
    let next = c.after()    # 2, and c.n is still 1
    c.advance()             # c.n is 2
    next + c.n
```

A call evaluates its receiver exactly once, before its arguments, however the
method takes `self`. That includes the operands of a place: `arr[next()].m()`
runs `next` once.

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

Function pointers lower to opaque LLVM `ptr`. A parameter whose type is written
out **inline** is callable, and passing a named function as the argument works:

```ritz
fn add(a: i32, b: i32) -> i32
    a + b

fn apply(f: fn(i32, i32) -> i32, a: i32, b: i32) -> i32
    f(a, b)

fn main() -> i32
    return apply(add, 1, 2)
```

Two spellings do *not* work, both failing with `Unknown function: f`:

- the parameter type written through a **type alias** (`type BinaryOp =
  fn(i32, i32) -> i32` then `fn apply(f: BinaryOp, ...)`). This is the alias
  resolution bug in [§3.8](#38-type-aliases), not a function-pointer
  limitation — aliases are accepted at their declaration and then not resolved
  at use sites.
- calling through a **local binding** (`let f = add` then `f(1, 2)`). ritz0 has
  no lowering for a function-valued `let`.

Until those are fixed, spell the `fn(...)` type out at the parameter, or
dispatch through an `impl` method or a `match`.

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

A condition is a `bool`. That holds for `if`, `while` and `assert`. Nothing else
is truthy, so test an integer with `n != 0` and a pointer with `p != null`:

```ritz body expect-error="if condition must be bool, got an integer: write `x != 0`"
let n = 1
if n
    print("non-zero\n")
```

```ritz body expect-error="while condition must be bool, got an integer: write `x != 0`"
while 1
    break
```

Write an endless loop as `loop`.

`if` is also an **expression**: an `if`/`else` whose branches end in a value can
initialise a binding, and it lowers to a real LLVM `phi` rather than to a
temporary:

```ritz body
let c = true
let x = if c
    1
else
    2
```

This document claimed the opposite until 2026-09-12 ("`if` is a statement, not
an expression; use `match` where you want a value"). `match` remains the better
choice when you are discriminating a tagged union, but not because `if` cannot
produce a value.

An `if`-expression **must** have its `else` arm, and ritz0 rejects one that
does not:

```ritz body expect-error="an `if` with no `else` has no value"
let c = true
let x = if c
    1
```

An `if` with no `else` has no value on the path where the condition is false,
so there is nothing for the binding to name. Before AGAST #1406 this compiled
at exit 0: no `phi` was emitted, the `1` was discarded, and `x` was silently
bound to `0` whichever way the condition went. It is rejected rather than
defaulted because synthesising a zero for the missing arm would keep those
programs compiling and merely make the wrong answer deliberate.

The rule applies wherever a `let`, `var`, assignment or `return` takes the
`if`'s value — including through the arms of an enclosing `if`/`else`, the
last line of a block, or the arm of a `match` that is itself being bound. The
diagnostic points at the `if` that lacks the `else`, which in an
`if`/`else if` chain is the innermost one.

It applies equally to an operand: the operand of an operator, a call or method
argument, an index, a cast, a field of a struct literal, a loop condition. An
operand's value is always used, so this is rejected even when the enclosing
call is itself a statement (AGAST #1435; before it, the `if` evaluated to `0`):

```ritz expect-error="an `if` with no `else` has no value"
fn id(v: i32) -> i32
    return v

fn pick(c: i32) -> i32
    return 5 + id(if c == 1
        1
    )
```

An else-less `if` used as a *statement* is ordinary code and is unaffected —
including as the last thing a procedure does, and as the last thing in an arm
of a `match` that is itself a statement:

```ritz body
var r = 0
let c = true
if c
    r = 1
```

A function that declares a return type is different. It is an error for such
a function to be able to reach its end without producing a value, whether its
last statement is an `if`, a loop, an assignment, a `pass` arm or a call to a
procedure. There is no implicit `0`. An `if`/`else` whose arms all return, or a
`loop` with no `break`, never reaches the end and needs nothing after it. The
condition of a `while` counts as always true only when it is the literal
`true`. `-> void` declares no value, so it follows the rules for a procedure.

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

A `for` iterates in place. It sees what its body writes, wherever the array, `Vec`,
`Span` or `StrView` lives (a local, a parameter, a global, a field, or behind a
pointer), and there is no hidden copy:

```ritz
struct H
    a: [3]i32

fn main() -> i32
    var h: H
    h.a[0] = 1
    h.a[1] = 2
    h.a[2] = 4
    var t: i32 = 0
    for x in h.a
        h.a[2] = 50          # seen when the loop gets there
        t = t + x
    t                        # 1 + 2 + 50
```

A `Vec`'s `len` and `data` are read on every pass, so a `push` in the body adds to
the trips, and is safe when it moves the buffer.

- The iterable is evaluated once. `for x in p.a` goes on walking the array `p`
  pointed at to begin with, whatever `p` is assigned in the body, and a call or an
  index on the way to it runs once.
- The binding is a copy of its element, taken before the body runs. A write to that
  element doesn't change the binding.
- Only an rvalue gets a temporary: a call's by-value result (`for x in mk()`, or
  `mk().a`), or a literal. Nothing else can reach it, so nothing can write to it.
- A place reached *through* a `Vec`'s element, such as `vs[0].a`, is an address
  into that `Vec`'s buffer, as `@vs[0]` is. If the body moves that buffer, the
  address is no longer valid.

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

The operands of `and`, `or` and `not` are `bool`, and so is the result. `&&`, `||`
and `!` are the same operators.

```ritz body expect-error="operand of `and` must be bool, got an integer: write `x != 0`"
let both = 2 and 1
```

```ritz body expect-error="operand of `not` must be bool, got a pointer: write `p != null`"
var n: i64 = 0
let p: *i64 = @n
let none = not p
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

Both operands are integers, and so is the operand of `~`. A `bool` is rejected,
even with another `bool`: use `and`, `or` and `not`.

`>>` is decided by the type of its left operand alone. On a signed type it is
arithmetic, filling from the sign bit, so it rounds toward negative infinity. On
an unsigned type it is logical, filling with zeros. The count's type has no say:

```ritz body
let a: i64 = -8
let b: u8 = 248
let n: u64 = 1
let c = a >> 1    # -4
let d = b >> 1    # 124
let e = a >> n    # -4: `a` is signed, whatever `n` is
```

An expression on the left has the type of its operands. The wider operand wins,
at equal width the unsigned one does, and a shift keeps its left operand's
signedness. So with `h: u64`, `(h ^ 1) >> 33` is logical. A literal is an `i64`,
unless its value only fits a `u64`: `0xF000000000000000 >> 60` is `15`. A constant
expression shifts by the same rule.

The left operand is a value of its type, so with `a: u8` the sum in `(a + a) >> 1`
wraps at 8 bits first. Where a literal operand meets a narrower declared slot,
as in `let r: u8 = (a << 4) >> 4`, the width is not yet settled (AGAST #2360).

A count that is negative, or not less than the bit width of the left operand's
type, has no defined result.

Bitwise operators bind looser than `==`, so `x & 1 == 1` is `x & (1 == 1)`, which
is an error. Parenthesise it:

```ritz body expect-error="operand of `&` must be an integer, got bool: `x & 1 == 1` is `x & (1 == 1)`: parenthesise `(x & 1) == 1`"
let x = 6
if x & 1 == 1
    print("odd\n")
```

```ritz body expect-error="operand of `&` must be an integer, got bool"
let a = true
let b = false
let c = a & b
```

### 7.5 Type Casting

```ritz body
let x: i64 = 42 as i64
let p: *u8 = null as *u8
let addr: i64 = p as i64
```

#### `bool` converts to nothing

`bool` is its own type. No `let`, `var`, `return`, tail, argument, field, element
or assignment turns a `bool` into an integer, or anything into a `bool`, and `==`
and `!=` need both sides the same kind. Arithmetic on a `bool` is an error too.

```ritz body expect-error="cannot use an integer as bool: write `x != 0`"
let b: bool = 2
```

```ritz expect-error="cannot use bool as an integer: write `b as i32`"
fn same(a: i64, b: i64) -> i32
    return a == b

fn main() -> i32
    same(1, 1)
```

```ritz body expect-error="cannot compare bool with an integer"
let b = true
if b == 1
    print("yes\n")
```

`b as i32`, or a cast to any other integer type, is 0 or 1:

```ritz body
let n = (2 > 1) as i32      # 1
```

`x as bool` is removed. Write the comparison you mean:

```ritz body expect-error="`as bool` is removed: write `x != 0`"
let b = 256 as bool
```

A `bool` has no cast to a float or a pointer.

ritz0, ritz1 and ritz1_selfhosted give the same located error for each of these,
and `ritz0/test_bool_type.py` runs one table through all three. ritz0 reads the
type off the value it just emitted. ritz1 keeps a `bool` in an `i64` register, so
it works the type out from the expression. A condition ritz1 can't type is an
error, not a guess.

#### Implicit narrowing is an error

A typed `let` or `var` whose initialiser is a wider integer is rejected, unless
the compiler can prove the value fits the declared type:

```ritz expect-error="implicit narrowing: `n` is declared `i32` but its initialiser has type `i64`"
fn big() -> i64
    return 4294967301

fn main() -> i32
    let n: i32 = big()      # would silently become 5
    return n
```

Write `as` when truncation is what you mean: `let n: i32 = big() as i32`.

Three shapes are provably lossless and need no `as`:

```ritz body
let x: i64 = 1000
let flags: i32 = 0x02 | 0x20     # a constant expression that fits
let low: u8 = x & 255            # a mask `e & K`, K >= 0, K fits the type
let bit: u8 = if x > 0 then 1 else 0   # an if/match whose every arm is one of these
```

The rule does no range analysis beyond that: `if n < 255 then n else 255`
is rejected even though it is safe, and needs an `as`. Only typed `let` and
`var` initialisers are checked. An assignment, a call argument or a `return`
still converts silently (#1444).

A non-literal array element is held to the same rule, against the element type:

```ritz body expect-error="implicit narrowing: this element of a `u8` array has type `i64`"
let k: i64 = 300
let a: [2]u8 = [1, k]
```

ritz0 and ritz1 both enforce this rule, and `ritz0/test_ritz1_implicit_narrowing.py`
checks that they give the same verdict on every case in
`ritz0/test_implicit_narrowing.py`. ritz1 infers the initialiser's type from its
Ritz types. Where that inference is unsure, for example for an unannotated
local, ritz1 accepts the initialiser rather than guess (#1364).

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

`[]` sees through one level. `p[i]` means `(*p)[i]` when `p` is a `*T`, `@T` or `@&T`
and `T` is a Vec, Span or String, and `(*p)[i]` is the same place. An element is a
place in every position: read, store, `+=`, `@`, `@&` and `.f`.

```ritz
import ritzlib.gvec

struct Point
    x: i32
    y: i32

fn third(v: @Vec<i32>) -> i32
    v[2]

fn clear(v: @&Vec<i32>, i: i64)
    v[i] = 0

fn nudge(v: *Vec<Point>)
    v[0].y += 1

fn main() -> i32
    var v: Vec<i32> = vec_new<i32>()
    v.push(1)
    v.push(2)
    v.push(3)
    clear(@&v, 0)
    third(@v)
```

The value itself is the same place: `v[i]` on a Vec, Span or String is its element
in every position, and an element that is itself one indexes in turn, so `v[i][j]`
and `p[i][j]` are places too.

```ritz
import ritzlib.gvec

fn main() -> i32
    var v: Vec<i32> = vec_new<i32>()
    v.push(10)
    v.push(20)
    v[1] = 7
    v[1] += 2
    var rows: Vec<Vec<i32>> = vec_new<Vec<i32>>()
    vec_push<Vec<i32>>(@&rows, v)
    rows[0][0] = 1
    let p: @&Vec<Vec<i32>> = @&rows
    p[0][1] += 1
    rows[0][0] + rows[0][1] - 11
```

Writes follow §3.2, so an `@T` refuses them. A `*T` over anything else is a raw
buffer: `p[i]` is `*(p + i)`, at stride `T`. Walking rows of Vecs behind a `*Vec<T>`
is `p + i`, not `p[i]`.

```ritz expect-error="cannot write through an `@T`: make it `@&T`"
import ritzlib.gvec

fn clear(v: @Vec<i32>)
    v[0] = 0

fn main() -> i32
    var v: Vec<i32> = vec_new<i32>()
    v.push(1)
    clear(@v)
    0
```

An `@T` or `@&T` over anything else is an error: a reference is one `T`, not a buffer.
That includes a pointer as the pointee, because `[]` sees through one level only, so
`q: @*Vec<i32>` is `(*q)[1]`.

```ritz expect-error="a reference is one value, not a buffer"
fn second(p: @i32) -> i32
    p[1]

fn main() -> i32
    var x: i32 = 1
    second(@x)
```

### 7.9 Sizeof

```ritz body
let a = sizeof(i32)         # Size of type in bytes
let n = 0
let b = sizeof(n)           # Size of expression's type
let c = sizeof([8]u8)       # An array type: 8
var key: [64]u8
let d = sizeof(key)         # 64: the whole array, not a pointer
```

`sizeof` is a compile-time constant of type `i64`. Its operand is either a type
or an expression. For an expression, `sizeof` measures the expression's *type*
and never evaluates it: `sizeof(f())` does not call `f`, and `sizeof(key)` does
not move or use `key`. An identifier is taken as a value when one is in scope,
and as a type name otherwise. A comparison or `and`/`or` has size 1; any other
binary operation has the size of its left operand.

A name that is neither a value nor a type, such as `sizeof(Nope)`, is a compile
error. So is an expression whose type the compiler can't determine. Neither
falls back to a guessed size.

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

Every `match`, statement or value, must cover its scrutinee, or it is a compile
error naming what is missing. A `match` covers its scrutinee when it has:

- an unguarded `_` or binding arm; or
- for an enum, generic enums included, an arm for every variant; or
- for a `bool`, both `true` and `false`; or
- for a union, an arm for every member.

An integer or string scrutinee needs a catch-all. A guarded arm never counts
towards coverage, though no guard parses yet.

```ritz expect-error="non-exhaustive match: missing a catch-all"
fn f(n: i64) -> i64
    match n
        0 => 1
        1 => 2

fn main() -> i32
    f(5) as i32
```

Missing variants are named in declaration order:

```ritz expect-error="non-exhaustive match: missing Green, Blue"
enum Color
    Red
    Green
    Blue

fn f(c: Color) -> i32
    match c
        Red => 1

fn main() -> i32
    f(Color.Red)
```

A `bool` is covered by `true` and `false`, not by the integers `1` and `0`:

```ritz expect-error="non-exhaustive match: missing false"
fn f(b: bool) -> i32
    match b
        true => 1

fn main() -> i32
    f(true)
```

A name that is an integer `const` compares (see Constant Patterns), so it is no
catch-all, and a statement `match` is held to the same rule:

```ritz expect-error="non-exhaustive match: missing a catch-all"
const A: i64 = 0

fn main() -> i32
    let n: i64 = 5
    match n
        A => pass
    0
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

A pattern inside a variant takes the payload: it is a binding or `_`. One that
would test the payload is a compile error at that pattern, because the arm is
chosen by the variant alone. That covers a literal, a type, a name that is an
integer `const` against an integer payload, and a name that is a variant of an
enum payload. Bind the payload and test it in the arm body:

```ritz expect-error="a variant payload can only be bound, not tested: '0' in 'Some(...)'"
fn f(o: Option<i32>) -> i32
    match o
        Some(0) => 1
        _ => 2

fn main() -> i32
    f(Some(5))
```

#### Constant Patterns

A bare identifier pattern that names an integer `const` (declared in the
module or imported) compares the scrutinee with the constant. Any other
identifier binds the scrutinee to a new name, which also makes it a
catch-all (AGAST #1880):

```ritz
const SYS_READ: u64 = 0
const SYS_WRITE: u64 = 1

fn dispatch(n: u64) -> i64
    match n
        SYS_READ => 10
        SYS_WRITE => 20
        other => other as i64     # not a const: binds

fn main() -> i32
    dispatch(SYS_WRITE) as i32
```

A const resolves wherever it is declared in the module, before or after the
`match`. Constant patterns compare integers only: against an enum
scrutinee, a bare name is a variant (§10.2).

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

A method has no type parameters of its own: `fn conv<T>(self: *Point, x: T)`
inside an `impl` block is a compile error located at the method, in both an
inherent `impl Point` and a generic `impl<T> W<T>` (whose methods may use the
impl's `T`). Write a free generic function instead (AGAST #1902):

```ritz
struct Point
    x: i32
    y: i32

fn point_pick<T>(p: *Point, a: T, b: T) -> T
    if p.x > 0
        a
    else
        b

fn main() -> i32
    let p = Point { x: 1, y: 0 }
    point_pick<i32>(@p, 0, 1)
```

---

## 10. Enums

An enum is a tagged union: a value is exactly one of its variants, and the
compiler tracks which one.

### 10.1 Definition

The simplest enums are C-style — variants with no payload:

```ritz
enum Color
    Red
    Green
    Blue
```

A variant can carry data. Write the payload positionally, as a tuple:

```ritz
enum Shape
    Circle(f64)
    Rect(f64, f64)
    Empty
```

...or with named fields, as an indented block. This is usually clearer once a
variant has more than two fields:

```ritz
import ritzlib.strview

pub enum Msg
    Stop

    Navigate
        url: StrView

    SetViewport
        width: u32
        height: u32
```

Named fields are **sugar**: `SetViewport` above has exactly the same tag and
memory layout as `SetViewport(u32, u32)` would. Field order is therefore
significant — reordering fields changes the layout, just as it does in a
`struct`.

`Option<T>` and `Result<T, E>` are defined in `ritzlib.option` and
`ritzlib.result` respectively; import them rather than redeclaring them.

A `match` on an enum must cover every variant (§8.1). For the full treatment —
memory layout and the design rationale — see
[`docs/ENUM_VARIANTS.md`](ENUM_VARIANTS.md).

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

**Bare variants.** A variant may be written without its enum (`Red`, `Red()`,
`Circle(1.0)`) only when **exactly one** enum in scope (declared or imported,
`Option`/`Result` aside) declares a variant of that name. If two or more do,
the bare name is an error in every value position (a `let` / `var`
initialiser, an assignment, a call argument, a `return`, an operand of `==`,
a constructor call), **whatever the expected type**: `let s: S = B` is
rejected even though only `S.B` would fit. Qualify it instead (AGAST #2039):

```ritz
enum S
    A
    B

enum T
    B
    C

fn main() -> i32
    let s: S = S.B   # qualified: fine
    let t = C        # only T declares C: fine bare
    match s
        A => 1
        B => 2       # a bare arm resolves against the scrutinee's enum
```

```ritz expect-error="ambiguous enum variant 'B': declared by enum 'S' and enum 'T'; qualify it, e.g. 'S.B'"
enum S
    A
    B

enum T
    B
    C

fn main() -> i32
    let s: S = B
    0
```

The error names the two alphabetically-first declaring enums. Bare **match
arm patterns** are the exception: the scrutinee's enum is known, so `B =>`
against an `S` is `S.B`. A local or parameter named like a variant shadows it,
and an enum reached twice through an import cycle is still one enum.

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

Fields bind **positionally**, for tuple and named-field variants alike — the
field names in the declaration do not appear in the pattern:

```ritz
import ritzlib.strview

enum Msg
    Stop

    Navigate
        url: StrView

    SetViewport
        width: u32
        height: u32

fn handle(m: Msg) -> i32
    match m
        Stop => 0
        Navigate(url) => 1
        SetViewport(width, height) => 2

fn main() -> i32
    return handle(Msg.Stop)
```

Use `_` for a field you do not need:

```ritz
enum Shape
    Circle(f64)
    Rect(f64, f64)
    Empty

fn width_ish(s: Shape) -> f64
    match s
        Rect(w, _) => w
        Circle(r) => r
        Empty => 0.0

fn main() -> i32
    let x = width_ish(Shape.Rect(3.0, 4.0))
    return 0
```

### 10.4 Discriminants and Integer Conversion

Every variant of a **fieldless** enum (no variant carries data) has a
*discriminant*, an integer. By default it is the variant's declaration index:
0, 1, 2, ... An enum can name a *representation type* after a colon, and
then give any variant an explicit discriminant with `= N` (AGAST #1880):

```ritz
enum Syscall: u64
    Read = 0
    Write         # 1: the previous discriminant + 1
    Mmap = 9
    Exit = 60

enum Errno: i64
    Fault = -14
    Inval = -22
    Range = -34

fn main() -> i32
    let s = Syscall.Exit
    let n: u64 = s as u64            # 60
    let e: i64 = Errno.Fault as i64  # -14
    (n as i64 + e) as i32            # 46
```

The rules:

- The representation type is one of `i8`, `i16`, `i32`, `i64`, `u8`,
  `u16`, `u32`, `u64`. A variant without `= N` takes the previous
  variant's discriminant plus one; the first takes 0. `N` is an integer
  literal (decimal, hex or binary), optionally negated.
- Every discriminant must fit the representation type, and no two variants
  may share one.
- `= N` needs a representation type, and an enum with one must be fieldless.
- The representation type fixes the discriminants' type, not the enum's
  layout: an enum value is still its tag (§10.1), whatever its
  discriminants. Convert explicitly to pass one as an integer: an enum
  value where an integer is expected (a return, an argument, an annotated
  `let` / `var`, an assignment) is an error.

```ritz expect-error="expected i64, found enum 'St'; convert with `as`"
enum St
    A
    B

fn f() -> i64
    return St.B                      # write `St.B as i64`

fn main() -> i32
    f() as i32
```

**`e as U`** converts a fieldless enum value to any integer type `U`: its
discriminant, extended or truncated exactly as an integer cast from the
representation type would (for an enum without one, its declaration index).
Converting an enum that carries data is an error:

```ritz expect-error="cannot convert enum 'Shape' to an integer: variant 'Circle' carries data"
enum Shape
    Circle(f64)
    Empty

fn main() -> i32
    Shape.Empty as i32
```

**`E.from(v)`** converts back: given a value of the representation type, it
returns `Some(variant)` for the variant with that discriminant, otherwise
`None`. It is generated for each enum with a representation type in a
module that imports `ritzlib.option`, and is visible wherever the enum is
(`pub` if the enum is). Its symbol is `E__from`, so a module may not declare
a fn of that name beside such an enum.

```ritz
import ritzlib.option

enum Syscall: u64
    Read = 0
    Write
    Exit = 60

fn handle(rax: u64) -> i64
    match Syscall.from(rax)
        Some(s) => match s
            Read => 1
            Write => 2
            Exit => 3
        None => -38                  # ENOSYS

fn main() -> i32
    handle(60) as i32
```

For an enum without a representation type, or one whose module does not
import `ritzlib.option`, `E.from` is an error located at the call:

```ritz expect-error="enum 'Color' has no 'from'"
import ritzlib.option

enum Color
    Red
    Green

fn main() -> i32
    let c = Color.from(1)
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
pointer arguments (`option_is_none<*Page>(@p)`). A function with several type
parameters takes one argument per parameter, in order:

```ritz
fn second<T, U>(a: T, b: U) -> U
    b

fn main() -> i32
    second<i64, i32>(100, 0)
```

`f(a < b, c > (d))` lexes exactly like a call to `a<b, c>(d)`. ritz1 reads a
list of two or more type arguments as a call only if none of them is a bare
lowercase identifier: by naming convention (`docs/STYLE.md`: types are
PascalCase, variables snake_case) such a name is a value, so
the example above stays two comparison arguments. ritz0 does not make this
distinction yet; it always reads `<...>(` as type arguments.

```
f(a < b, c > (d))          # ritz1: f((a < b), (c > (d)))
second<i64, Counter>(x, y) # a generic call under both compilers
```

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
specialized code. *Every* type argument participates in name mangling, joined
by `_`: `Result<i32, StrView>` mangles to `Result$i32_StrView`, and
`Result<i32, i32>` to `Result$i32_i32`. You can read the mangled names straight
out of the emitted IR:

```bash
RITZ_PATH=$PWD python3 ritz0/ritz0.py prog.ritz -o prog.ll --no-runtime
grep -o 'Result\$[A-Za-z0-9_]*' prog.ll | sort -u
```

This document claimed until 2026-09-12 that only the first type argument
mangled — which would have made `Result<i32, StrView>` and `Result<i32, i64>`
collide. They do not.

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

Every value has one owner: the `let` or `var` binding, by-value parameter,
field or temporary that holds it. Ownership is tracked only for **move-only**
types (AGAST #1854). A type is move-only if and only if

- it implements `Drop` (§13.6), or
- it has a field, an enum-variant payload or a generic argument that is
  move-only, checked transitively.

Every other type is a **copy type**: the integer, float and `bool` types,
pointers, references, `StrView`, and every struct, enum, tuple or array built
only from copy types. A type doesn't become move-only by holding a raw pointer
to heap memory. Only `Drop` makes it move-only.

`String` and `Vec<T>` own heap buffers but don't implement `Drop` yet
(AGAST #2159). Today they are copy types, and their owner releases them by
calling `string_drop` or `vec_drop` explicitly:

```ritz
import ritzlib.string

fn main() -> i32
    var s = string_from("hello")    # s owns the buffer
    string_drop(@&s)                # released explicitly
    0
```

### 13.2 Move Semantics

Using a value of a copy type by value copies it, and the source stays usable.
Uses by value include binding it, assigning it, passing it to a by-value
parameter, calling a method that takes `self` by value on it, returning it and
storing it in a field or an array or tuple literal:

```ritz
struct Point
    x: i32
    y: i32

fn main() -> i32
    let a = Point { x: 1, y: 2 }
    let b = a                       # copy
    let c = a                       # another copy; a is still usable
    a.x + b.x + c.y
```

The same uses of a move-only value **move** it. The destination becomes the
owner, and the source binding can't be used again until something is assigned
to it. A by-value parameter `name: T` of a move-only type takes ownership. To
lend the value instead, pass `@x` or `@&x` (§13.3, §13.4). If a value is moved
on only some paths, the binding counts as moved after those paths join. The
arms of a `match` or an `if` each start from the state before it, and paths
that leave by `return`, `break` or `continue` don't join.

Using a move-only field by value (`return h.t`, `consume(h.t)`) moves that
field out of the binding, and only that field. Afterwards `h.t` and `h` as a
whole can't be used until `h.t` (or `h`) is assigned again, but `h`'s other
fields can. A type that implements `Drop` itself can't have a field moved
out, because its `drop` would see a half-moved value. Moving a field out of
a temporary (`make().t`) takes the field, and the rest of the temporary isn't
dropped.

```ritz expect-error="use of moved value: `r`"
struct Resource
    handle: i32

impl Drop for Resource
    fn drop(self: @&Resource)
        self.handle = 0

fn consume(r: Resource) -> i32
    r.handle

fn main() -> i32
    var r = Resource { handle: 3 }
    consume(r)                      # moves r into consume
    r.handle                        # error: r was moved
```

A reference isn't its referent. An `@T`, `@&T` or `*T` doesn't fit a by-value
`T` slot: an argument, a `let` or `var` of type `T`, `=`, `return`, a function's
tail, a field, an element, a variant's payload, or an `if` or `match` arm of any
of these. There's no implicit deref, so write `*r`:

```ritz
struct Point
    x: i32
    y: i32

fn sum(p: Point) -> i32
    p.x + p.y

fn twice(r: @Point) -> i32
    sum(*r) + r.x + r.y             # `*r` and `r.x` read through r

fn main() -> i32
    let a = Point { x: 1, y: 2 }
    twice(@a)
```

```ritz expect-error="a reference or pointer doesn't fit a by-value slot"
struct Point
    x: i32
    y: i32

fn sum(p: Point) -> i32
    p.x + p.y

fn twice(r: @Point) -> i32
    sum(r)                          # error: write `*r`

fn main() -> i32
    let a = Point { x: 1, y: 2 }
    twice(@a)
```

`*r`, `r.f`, `p[i]` and a by-value `self` method read through a reference. That's
a copy for a copy type. For a move-only type it would leave the value with two
owners, so using one by value is an error, for `@T`, `@&T`, `*T` and `name:& T`
alike. Reading a copy field of it, borrowing it and `match`ing it are fine. A
generic body is judged at each type it's instantiated with: `*p` compiles at
`T = i32` and is this error at a move-only `T`.

```ritz expect-error="cannot move out of a reference"
struct Resource
    handle: i32

impl Drop for Resource
    fn drop(self: @&Resource)
        self.handle = 0

fn consume(r: Resource) -> i32
    r.handle

fn steal(r: @Resource) -> i32
    consume(*r)                     # error: the caller still owns it

fn main() -> i32
    var r = Resource { handle: 3 }
    steal(@r)
```

Raw pointers get no exception. Code that keeps values in raw memory takes them
out with `ptr_read<T>(p)` from `ritzlib.ptr`, a bitwise read whose caller becomes
the owner. The memory at `p` then no longer holds a value.

Copying a copy type that owns a buffer, such as today's `String`, gives two
bindings that name the same buffer. Only one of them may release it, and the
compiler doesn't track which one does that:

```ritz
import ritzlib.string

fn main() -> i32
    let s1 = string_from("hello")
    var s2 = s1                     # shares s1's buffer
    string_drop(@&s2)               # drop exactly once
    0
```

### 13.3 Borrowing

`@x` takes an immutable reference without taking ownership:

```ritz
import ritzlib.string

fn main() -> i32
    var s = string_from("hello")
    let n = string_len(@s)          # borrow for the call
    string_drop(@&s)
    n as i32
```

`@x` is a reference, so it goes where a reference goes. Into a by-value slot it's
the §13.2 error, and the `@` is what to remove:

```ritz expect-error="`@x` doesn't fit a by-value slot: drop the `@`"
fn double(n: i32) -> i32
    n * 2

fn main() -> i32
    let n: i32 = 4
    double(@n)
```

`@x` is shared. It fits an `@T` or a `*T`, and never an `@&T` or a `:&` parameter,
at any slot. A callee that may write is given `@&x`, or a bare place if it takes
`:&` (§13.4), so a shared borrow doesn't become a mutable one on the way in.

```ritz expect-error="`@x` is shared and doesn't fit an `@&T` or `:&` slot: write `@&x`"
struct Counter
    n: i32

fn bump(c: @&Counter)
    c.n = c.n + 1

fn main() -> i32
    var c = Counter { n: 1 }
    bump(@c)
    c.n
```

An `@x` of a `let`, or of a place in the `let`'s own storage, never reaches a
mutable slot. It doesn't fit an `@&T` or a `:&` parameter, at any slot, which is
what `@&x` of a `let` is refused for too (§4.1). A place reached through a pointer
or reference isn't the `let`'s own storage.

```ritz expect-error="cannot borrow `let` binding `c` as mutable; declare it `var`"
struct Counter
    n: i32

fn bump(c:& Counter)
    c.n = c.n + 1

fn main() -> i32
    let c = Counter { n: 1 }
    bump(@c)
    c.n
```

`@&x` of a place behind an `@T` is an error wherever it's written, by the walk
§3.2 gives for a write: a `*T` on the way ends it. `@x` of such a place is an
error where it lands in an `@&T` or a `:&` parameter.

```ritz expect-error="cannot borrow through an `@T` as mutable: make it `@&T`"
struct Counter
    n: i32

fn bump(n: @&i32)
    *n = *n + 1

fn tick(c: @Counter)
    bump(@&c.n)

fn main() -> i32
    var c = Counter { n: 1 }
    tick(@c)
    c.n
```

### 13.4 Mutable Borrowing

`@&x` takes a mutable reference. In a parameter list, `name:& T` borrows the
caller's place: `name` is an alias of it, so it has type `T` in the whole body.

```ritz
import ritzlib.string

fn append(s: @&String) -> i32
    string_push_str(s, " world")

fn main() -> i32
    var s = string_from("hello")
    append(@&s)
    let n = string_len(@s)
    string_drop(@&s)
    n as i32
```

`@x` doesn't fit either form (§13.3):

```ritz expect-error="`@x` is shared and doesn't fit an `@&T` or `:&` slot: write `@&x`"
fn set(n:& i32)
    n = 3

fn main() -> i32
    var n: i32 = 1
    set(@n)
    n
```

A place passed to a `name:& T` parameter is borrowed, as if written `@&x`. It's
the language's only implicit borrow, and it holds for every `T`, pointers
included. A place is a local, a parameter, a field, an element or a deref.

```ritz
struct Counter
    n: i32

fn bump(c:& Counter)
    c.n = c.n + 1

fn set(n:& i32)
    n = 3

fn main() -> i32
    var c = Counter { n: 1 }
    bump(c)                         # c.n is 2
    set(c.n)                        # c.n is 3
    c.n
```

The place must be mutable: a `var`, or reached through an `@&T`, a `:&` or a
`*T`. A `let` is refused, and so is an `@T`, written or inferred from `let p = @x`,
and a place behind one, the nearest indirection deciding:

```ritz expect-error="cannot borrow `let` binding `n` as mutable"
fn set(n:& i32)
    n = 3

fn main() -> i32
    let n: i32 = 1
    set(n)
    n
```

An rvalue is refused, since there's nothing for the caller to observe. An `@&T`
or `*T` isn't a place of `T`: it passes as the pointer it is, from a call or
from a place. For `name:& *U`, a `*U` place is borrowed and a `**U` passes.

```ritz expect-error="a `:&` parameter needs a place to borrow"
fn set(n:& i32)
    n = 3

fn main() -> i32
    set(1 + 2)
    0
```

The caller keeps ownership of what it lends, so a `name:& T` parameter of a
move-only type can't be moved out of, like anything behind a reference (§13.2).
Using the parameter by value, or using one of its move-only fields or `*name` by
value, is an error. Everything that leaves the caller as the only owner is
allowed: reading and writing through the parameter, lending it on, `match`ing or
iterating over it, and writing `@name` or `@&name`.

A reference is always written. `@c` and `@&c` of a `name:& T` parameter give the
caller's address, and count as `@c` or `@&c` of any place for §13.5's first rule.
They aren't local roots: the place is the caller's.

```ritz
struct Counter
    n: i32

fn bump(c:& Counter) -> @&Counter
    let p: @&Counter = @&c          # p refers to the caller's Counter
    p.n = p.n + 1
    return p                        # and so does the result

fn main() -> i32
    var c = Counter { n: 1 }
    let r = bump(@&c)
    r.n = r.n + 1
    c.n
```

A `T` never fits an `@T`, `@&T` or `*T`, for a `:&` parameter or any other
binding, at `let`, `var`, `=`, `return`, a function's tail, a field, an element,
a variant payload, an `if` or `match` arm, or an argument. Only a reference fits
an `@T` or `@&T`, and only a pointer fits a `*T` for a `:&` parameter. There's
no borrowing by destination:

```ritz expect-error="a value doesn't fit a reference slot: write `@&x` to borrow it"
struct Counter
    n: i32

fn bump(c:& Counter) -> @&Counter
    return c                        # error: c is a Counter

fn main() -> i32
    var c = Counter { n: 1 }
    bump(@&c)
    c.n
```

```ritz expect-error="a value doesn't fit a reference slot: write `@x` to borrow it"
struct Counter
    n: i32

fn read(c: @Counter) -> i32
    c.n

fn main() -> i32
    var c = Counter { n: 1 }
    read(c)                         # error: write read(@c)
```

An rvalue has no address, so `@f()` and `@"text"` are refused: bind it to a local
first. A whole array is the same for a `Span<T>`: `@a` fits and `a` doesn't.

```ritz expect-error="a value doesn't fit a reference slot: write `@x` to borrow it"
import ritzlib.span

fn total(s: Span<i32>) -> i64
    s.len

fn main() -> i32
    var a: [2]i32 = [1, 2]
    total(a) as i32                 # error: write total(@a)
```

A `name:& *U` parameter follows the same rule at `T` = `*U`: `h` is a `*U`, and
`@&h` is an `@&*U`, which doesn't fit a reference to another pointer type.

```ritz expect-error="cannot move out of a reference"
struct Resource
    handle: i32

impl Drop for Resource
    fn drop(self: @&Resource)
        self.handle = 0

fn consume(r: Resource) -> i32
    r.handle

fn steal(r:& Resource) -> i32
    consume(r)                      # error: r still belongs to the caller

fn main() -> i32
    var r = Resource { handle: 3 }
    steal(r)
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

The arguments of one call are live together, so a read of `x` can't sit beside
`@&x` in them. Read it into a binding first:

```ritz expect-error="cannot borrow `x` as immutable - already borrowed as mutable"
fn get(n: @i32) -> i32
    *n

fn put(n: @&i32, v: i32)
    *n = v

fn main() -> i32
    var x: i32 = 1
    put(@&x, get(@x) + 1)
    x
```

There are no lifetime annotations and no generic lifetime parameters, so the
second rule can't be checked in general. It stays normative, and the compiler
refuses the case it can see for certain: a reference to storage that ends with the
function, leaving it. This is a check for the definite case, not a soundness
guarantee.

A **local root** is a by-value local or parameter, reached with no pointer or
reference on the path: `x`, `x.f`, `x[i]`. That covers `let`, `var`, by-value
parameters, and match and loop bindings. A `return` or a function's tail, through
`if` and `match` arms, can't give:

- `@x`, `@&x`, `@x.f` or `@x[i]` of a local root, as an `@T`, `@&T` or `*T`;
- a local reference binding initialised from one of those, over any number of
  hops;
- a call returning `@U` or `@&U` that was given a reference to a local root with
  pointee `U`. A `:&` parameter or a receiver is given one when its place is a
  local root of type `U`.

```ritz expect-error="cannot return a reference to local `c`: it ends with the fn"
struct Counter
    n: i32

fn make() -> @Counter
    var c = Counter { n: 1 }
    return @c                       # error: c ends here
```

```ritz expect-error="cannot return a reference to local `c`: it ends with the fn"
struct Counter
    n: i32

fn first(c: Counter) -> *i32
    return @c.n                     # error: a by-value param is a local root
```

```ritz expect-error="cannot return a reference to local `a`: it ends with the fn"
fn pick(b: bool, p: @i32) -> @i32
    var a: [2]i32 = [1, 2]
    if b
        @a[0]                       # error: an arm of the tail
    else
        p
```

```ritz expect-error="cannot return a reference to local `c`: it ends with the fn"
struct Counter
    n: i32

fn make() -> @Counter
    var c = Counter { n: 1 }
    let r = @c
    let q = r
    return q                        # error: q refers to c
```

```ritz expect-error="cannot return a reference to local `c`: it ends with the fn"
struct Counter
    n: i32

fn same(c: @Counter) -> @Counter
    c

fn make() -> @Counter
    var c = Counter { n: 1 }
    return same(@c)                 # error: the result may be that reference
```

A `var` counts only while what it holds is definite. Once it's written, or has its
address taken or is lent, it's no longer followed, and nor is it in a loop it was
declared outside, because the loop can reach a later write first.

The call rule goes by type, because a function's signature doesn't say which
argument its result came from. A reference with another pointee doesn't count, so
looking something up by a local key is fine, and a raw `*U` return is exempt:

```ritz
struct Entry
    key: i32
    value: i32

fn lookup(e: @Entry, key: @i32) -> @Entry
    e

fn find(e: @Entry) -> @Entry
    var key: i32 = 3
    return lookup(e, @key)          # `key` is an i32: the result isn't it

fn main() -> i32
    var e = Entry { key: 3, value: 4 }
    let r: @Entry = find(@e)
    r.value
```

What the caller gave stays legal to return: a `name:& T`, `@T` or `@&T` parameter,
or a reference reached through one. The result refers to the caller's value, and
that value must outlive it. The same goes for a place behind any pointer, and for a
global:

```ritz
struct Counter
    n: i32

var TOTAL: Counter

fn lent(c:& Counter) -> @&Counter
    return @&c                      # the caller's Counter

fn through(p: *Counter) -> *i32
    return @p.n                     # behind a pointer

fn global() -> @Counter
    return @TOTAL

fn main() -> i32
    var c = Counter { n: 1 }
    let r = lent(c)
    r.n = 2
    let q = through(@c)
    let g = global()
    *q + g.n
```

Nothing else is checked, and each of these can still dangle:

- a reference stored in a field or a global, or in a value such as a `Span<T>` or an
  `Option<@T>`;
- a raw pointer after a cast: `@x as *u8`;
- anything through another function's stored state;
- a call's result held in a binding, or passed to another call, and a call through
  a `fn(...)` value;
- a binding initialised from an `if` or `match`, or assigned its reference after
  its declaration, and a reference taken behind such a binding: `@r.f`.

### 13.6 Drop

Implementing `Drop` for a type makes the compiler call its `drop` on every
binding that still owns a value of that type when the binding's scope ends:

- at the end of the block that declares the binding, nested blocks included;
- on `return`, for every live binding of the function, after the return
  value has been evaluated;
- on `break` and `continue`, for every binding declared inside the loop body;
- on assignment to the binding, for the old value, before the new value is
  stored.

`drop` takes `self` by reference. By value it would own a `self` of its own, which
would drop when it returned.

```ritz expect-error="`drop` can't take `self` by value"
struct Handle
    fd: i32

impl Drop for Handle
    fn drop(self)
        self.fd = 0
```

Bindings are dropped in reverse declaration order. A by-value parameter is a
binding of the callee's outermost block, so the callee drops it. A
moved-from binding is not dropped, because its new owner drops the value.
A binding with a field moved out drops its other fields only.
Returning a binding moves it to the caller. A binding moved on some paths only
is dropped only on the paths where it still owns its value. Assigning to a
moved-from binding drops nothing and makes the binding an owner again.

Assigning to a move-only field of a binding (`h.t = v`, or deeper,
`h.a.t = v`) drops the field's old value the same way: after `v` has been
evaluated, so `v` may read or move the old value, and before `v` is stored.
Nothing is dropped if the binding doesn't own a value, or if `h.t` has been
moved out. Assigning a moved-out field drops nothing and makes the binding
own the field again. A field of a moved-out field can't be assigned:
`h.a.t = v` with `h.a` moved out is a use of the moved `h.a`, as in Rust.

A move out of a nested field moves that field only, at any depth, as in Rust.
After `v.w.t` moves, `v` and `v.w` are **partly moved**:

- the other fields of `v` and `v.w` stay usable, and drop when `v` does;
- using `v` or `v.w` whole is an error, whether the use moves, lends or reads
  it, and so is using `v.w.t` or anything inside it;
- assigning `v.w.t` makes the binding own it again, as above;
- assigning a partly moved parent, `v.w = x`, drops what is left of the old
  `v.w` and makes all of `v.w` owned again.

A field can't be moved out of a value whose type has its own `drop`, because
that `drop` would see a half-moved value. This holds at every level: `v.w.t`
can't move if the type of `v` or of `v.w` implements `Drop`. A path through a
pointer or reference doesn't belong to the binding, so a move through one isn't
tracked.

```ritz expect-error="use of moved value: `v.w.t`"
struct Resource
    handle: i32

impl Drop for Resource
    fn drop(self: @&Resource)
        self.handle = 0

struct Inner
    t: Resource
    n: i32

struct Outer
    w: Inner

fn consume(r: Resource) -> i32
    r.handle

fn main() -> i32
    var v = Outer { w: Inner { t: Resource { handle: 3 }, n: 4 } }
    consume(v.w.t)
    consume(v.w.t)                  # error: v.w.t has already moved
```

```ritz expect-error="use of moved value: `v.w.t`"
struct Resource
    handle: i32

impl Drop for Resource
    fn drop(self: @&Resource)
        self.handle = 0

struct Inner
    t: Resource
    n: i32

struct Outer
    w: Inner

fn consume(r: Resource) -> i32
    r.handle

fn take(i: Inner) -> i32
    i.n

fn main() -> i32
    var v = Outer { w: Inner { t: Resource { handle: 3 }, n: 4 } }
    consume(v.w.t)
    take(v.w)                       # error: v.w is partly moved
```

```ritz
struct Resource
    handle: i32

impl Drop for Resource
    fn drop(self: @&Resource)
        self.handle = 0

struct Inner
    t: Resource
    n: i32

struct Outer
    w: Inner

fn consume(r: Resource) -> i32
    r.handle

fn main() -> i32
    var v = Outer { w: Inner { t: Resource { handle: 3 }, n: 4 } }
    consume(v.w.t)
    let n = v.w.n                   # fine: a field that didn't move
    v.w.t = Resource { handle: n }  # v owns v.w.t again
    consume(v.w.t)
```

A tuple element moves the same way, by its index: `p.0` moves out of `p`, `p.1`
stays usable, `p` is partly moved and `p`'s drop skips the element. So does an
element on a longer path, like `v.pair.0`. `(p.0).1` is an element of an
element (`p.0.1` doesn't parse yet, AGAST #2284).

```ritz expect-error="use of moved value: `p.0`"
struct Resource
    handle: i32

impl Drop for Resource
    fn drop(self: @&Resource)
        self.handle = 0

fn consume(r: Resource) -> i32
    r.handle

fn main() -> i32
    var p = (Resource { handle: 3 }, 4)
    consume(p.0)
    consume(p.0)                    # error: p.0 has already moved
```

A move-only type with no `Drop` impl of its own, such as a struct with a
`Drop` field, is dropped by dropping its move-only parts:

- a struct's move-only fields, in declaration order;
- an enum's payload, for the variant the value holds. `Option<Resource>`
  holding `Some(r)` drops `r`, and holding `None` drops nothing;
- an array's elements, in index order;
- a tuple's move-only elements, in order.

A type that has its own `drop` runs it first, then drops its move-only parts
the same way.

A move-only value that no binding, parameter or field takes ownership of is
a **temporary**. Examples are a call result used as a statement, one lent to
an `@T` parameter, or one whose field is read (`make().id`). A temporary is
dropped at the end of the statement that creates it. A `return` drops it
after the return value has been evaluated. A temporary in an `if` or `while`
condition is dropped once the condition has been evaluated, before the
branch is taken.

A binding moved inside a loop body must own a value again on every path
back to the loop head: an assignment after the move does that, and so does
leaving the loop with `break`. Otherwise the next iteration would use the
moved value, so it is an error:

```ritz expect-error="use of moved value: `r`"
struct Resource
    handle: i32

impl Drop for Resource
    fn drop(self: @&Resource)
        self.handle = 0

fn consume(r: Resource) -> i32
    r.handle

fn main() -> i32
    var r = Resource { handle: 3 }
    var i = 0
    while i < 2
        consume(r)                  # error on the second iteration
        i = i + 1
    0
```

Never call `drop` yourself: the compiler's call would release the value a
second time.

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
    r.handle                        # r is dropped after this is evaluated
```

ritz0 follows these rules (AGAST #2157, #2161, #2232, #2244), except that
`let (a, b) = p` isn't move-checked yet (AGAST #2282) and a tuple element can't
be assigned to yet (AGAST #2283). ritz1 follows them (AGAST
#2158) except for enum payloads, arrays, temporaries and moves inside loops
(AGAST #2165), and it has no tuple literals yet (AGAST #1526). ritz1 tracks 31
moved paths per binding: a move past them moves the nearest tracked parent, or
the whole binding, so the rest of it leaks (AGAST #2319).
`ritz0/test_ownership_free_count.py` counts the drops for each rule on all
three compilers, with today's gaps marked as expected failures.

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

Privacy does not give a fn its own namespace either: a fn name may be defined
at most once across a file and everything it imports, transitively, whether
the definitions are `pub` or private, and even if they are identical. A second
definition is an error naming both files, not a silent choice of one. A
`[[target_os]]` variant is never compared with an ungated fn of the same
name, and `extern fn` declarations are not definitions.

```ritz expect-error="Conflicting function definition for 'area'"
fn area() -> i32
    1

fn area() -> i32
    2

fn main() -> i32
    area()
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
`ritzlib/uring.ritz`, `ritzlib/async/runtime.ritz` and `ritzlib/async/tasks.ritz`.

---

## 17. Attributes

Attributes use double-bracket syntax on the line before the item. An item may
carry several, one per line or comma-separated in one pair of brackets.

The attributes are a closed set:

| Attribute | Applies to | Meaning |
|---|---|---|
| `[[test]]` | `fn` | a test ([§17.1](#171-test-attribute)) |
| `[[test_helper]]` | `fn` | may `assert`; a failure reports the calling test's line ([§17.1](#171-test-attribute)) |
| `[[target_os = "<os>"]]` | `fn`, `struct`, `const` | the item exists only when compiling for `<os>` ([§17.2](#172-target-attribute)) |
| `[[packed]]` | `struct` | no padding; alignment 1 ([§17.4](#174-packed-structs)) |
| `[[naked]]` | `fn` | no prologue or epilogue; the body is `asm` only ([§17.5](#175-naked-functions)) |
| `[[inline]]` | `fn` | inlining hint ([§17.6](#176-inlining-attributes)) |
| `[[always_inline]]` | `fn` | always inline |
| `[[noinline]]` | `fn` | never inline |
| `[[callconv = "<cc>"]]` | `fn`, `extern fn`, fn-type `type` | calling convention ([§17.7](#177-calling-conventions)) |
| `[[must_use]]` | `fn` | a call's result may not be discarded ([§17.8](#178-must-use-functions)) |

Any other attribute, a known attribute on an item kind it does not apply to,
a value given to an attribute that takes none, or a missing value is a
compile error located at the attribute. An attribute is never accepted and
ignored: a compiler that does not implement one rejects it (AGAST #1847).

```ritz expect-error="unknown attribute 'repr_c'"
[[repr_c]]
struct Header
    magic: u32
```

```ritz expect-error="attribute 'packed' applies to struct"
[[packed]]
fn checksum() -> u8
    0
```

ritz1 does not yet parse the comma-separated form or implement `[[naked]]`.
It rejects both with a located error.

### 17.1 Test Attribute

```ritz
[[test]]
fn test_addition() -> i32
    assert 2 + 2 == 4
    0
```

**What is a test.** A function is a test if and only if it carries `[[test]]`.
Its name does not matter: `[[test]] fn check_sum` is a test, and a helper
`fn test_setup` without the attribute is not.

**Signature.** A test takes no parameters and returns an integer type or
nothing. Anything else is a compile error in test mode.

**Result.** A test *passes* if it returns 0 (or returns nothing) and its
process exits normally. It *fails* if it returns any other value, or exits
with a non-zero status (a failed `assert` exits with status 1 after writing
its diagnostic to stderr). It *crashes* if its process is killed by a signal,
and *times out* if it runs past the runner's per-test limit. A non-zero result
is never read as a pass: a result whose low 8 bits are zero (256) fails with
status 1, and a result of a type other than `i32` fails as 1.

**Test helpers.** A function marked `[[test_helper]]` may use `assert` too
([§19.2](#192-built-in-functions)). It is an ordinary function in every other
respect: any parameters, any return type, generic or not, callable from
anywhere. When an
assert in a helper fails, the first line of the diagnostic names the line of
the **test** that called it, so the failing test is identified rather than the
shared helper; a further line names the helper and the assert's own location.
This holds through any depth of helpers calling helpers, and across modules:

```ritz expect-runtime-error=".ritz:13: assertion failed: left == right\n  left:  4\n  right: 5\n  in helper expect_sum at "
[[test_helper]]
fn expect_sum(a: i64, b: i64, want: i64)
    assert a + b == want

[[test_helper]]
fn expect_sums()
    expect_sum(1, 1, 2)
    expect_sum(2, 2, 5)

[[test]]
fn test_sums() -> i32
    expect_sum(0, 0, 0)
    expect_sums()
    0

fn main() -> i32
    test_sums()
```

The location is recorded by the test: before each call it makes, a `[[test]]`
function stores the call's file and line, and a helper's failing assert reads
them back. A helper reached without passing through a test (from `main`, say)
reports its own location.

**Test mode and the test table.** A test file is not compiled to a program of
its own. In test mode (ritz0 `--test-table`) the compiler omits the file's
`main`, if any, and emits a table of the file's tests, in source order:

| Symbol | Type | Meaning |
|---|---|---|
| `__ritz_tests` | `[N]{ name: StrView, run: fn() -> i32 }` | one entry per `[[test]]` function |
| `__ritz_tests_count` | `i64` | N |
| `__ritz_test_table` | `fn(count: *i64) -> *{ StrView, fn() -> i32 }` | stores N, returns the first entry |

`name` is the function's name, NUL-terminated (`len` excludes the NUL). `run`
calls the test and returns its result as an `i32`. A runner uses the
accessor. Only tests defined in the file being compiled are listed, not tests
in modules it imports.

**The test binary.** A test file's binary is the file in test mode, linked
with the ritzunit runner as its `main`, plus the dependencies of both.
ritzunit runs each entry in its own forked process and captures that
process's stdout and stderr. The output of a test that did not pass is shown
with its result, and `--json` includes it, so a test's output cannot corrupt
the report. The binary exits 0 if every selected test passed and 1 otherwise.
The runner's own symbols are linked privately, so a program may define names
the runner also uses.

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

`@inline` is written `[[inline]]` ([§17.6](#176-inlining-attributes)).

### 17.4 Packed Structs

A `[[packed]]` struct lays its fields out back to back in declaration order,
with no padding between them and none at the end. Its alignment is 1, so it
also adds no padding where it is embedded in another struct. `sizeof` and
field offsets follow from that, and every compiler agrees on them. This is
the layout of hardware- and firmware-defined records: GDT/IDT descriptors,
ACPI tables, UEFI structures.

```ritz
[[packed]]
struct GdtPointer
    limit: u16
    base: u64

struct Plain
    limit: u16
    base: u64

fn layout_ok() -> bool
    var p: GdtPointer
    let base_off: i64 = @p.base as i64 - @p as i64
    sizeof(GdtPointer) == 10 and sizeof(Plain) == 16 and base_off == 2
```

Every instance of a generic `[[packed]]` struct is packed. A packed struct's
fields may be misaligned. Read and write them through the struct (`p.base`);
a pointer to a misaligned field (`@p.base`) is only an address.

### 17.5 Naked Functions

A `[[naked]]` function gets no prologue or epilogue. The compiler does not
set up a frame or spill parameters, so the body cannot name its parameters or
declare locals. The body may contain only `asm` blocks. It finds its
arguments in the calling convention's registers and must return by itself.
Any other statement in the body is a compile error.

```ritz
[[naked]]
fn add_regs(a: i32, b: i32) -> i32
    asm x86_64:
        movl %edi, %eax
        addl %esi, %eax
        retq
```

```ritz expect-error="may contain only asm"
[[naked]]
fn not_asm() -> i32
    let x: i32 = 1
    x
```

ritz1 has no inline `asm` yet (AGAST #1619), so it rejects `[[naked]]`.

### 17.6 Inlining Attributes

`[[inline]]` asks for a function to be inlined, `[[always_inline]]`
requires it, and `[[noinline]]` forbids it. They are LLVM's `inlinehint`,
`alwaysinline` and `noinline`, and do not change what the function means.
A function carries at most one of them; if it is given several, the first in
the order `inline`, `always_inline`, `noinline` applies.

```ritz
[[noinline]]
fn slow_path() -> i32
    1
```

### 17.7 Calling Conventions

`[[callconv = "win64"]]` gives a function the Microsoft x64 calling
convention, LLVM's `win64cc`: the first four integer arguments in RCX, RDX,
R8 and R9, the rest on the stack above 32 bytes of shadow space, the result
in RAX. It is the convention of UEFI firmware. `[[callconv = "c"]]` names
the default, the platform C convention (System V on x86-64 Linux), and
changes nothing. Any other value is a compile error.

On a `fn` it is the convention the function is defined with and that every
direct call uses, so foreign code can call it. Every instance of a generic
`[[callconv]]` fn has it. On an `extern fn` it is the convention of the
foreign function, used by every call.

On a `type` alias of a fn type it is part of the type: a call through a
value of the alias uses it, whatever the callee expression is: a typed
local, a cast `(entry as EfiAllocatePages)(..)`, a struct field
`(table.alloc)(..)`, an array element or a fn's result. A function pointer
read from a firmware table has no declaration of its own, so the alias is
where its convention is written:

```ritz
[[callconv = "win64"]]
type EfiAllocatePages = fn(u64, u64, u64, *u64) -> u64

[[callconv = "win64"]]
extern fn efi_stall(microseconds: u64) -> u64

[[callconv = "win64"]]
pub fn efi_main(image: u64, system_table: u64) -> u64
    0

fn allocate(entry: u64, pages: u64, addr: *u64) -> u64
    efi_stall(10)
    let alloc: EfiAllocatePages = entry as EfiAllocatePages
    alloc(0, 2, pages, addr)

fn allocate_direct(entry: u64, pages: u64, addr: *u64) -> u64
    (entry as EfiAllocatePages)(0, 2, pages, addr)
```

A fn type written out, or an alias without the attribute, has the C
convention. The compiler cannot see where a pointer came from, so calling
through a type whose convention differs from the callee's is undefined
behaviour, as in C.

```ritz expect-error="unknown calling convention 'fastcall'"
[[callconv = "fastcall"]]
fn f() -> i64
    0
```

```ritz expect-error="attribute 'callconv' applies to"
[[callconv = "win64"]]
type Count = u64
```

*Why an attribute:* the convention is a property of the ABI, not of any
value, and attributes are the closed set that holds such properties, each
honoured or rejected by every compiler. Rust's `extern "win64" fn(..)` type
syntax was rejected: `extern` means "defined in another object" in Ritz
(§5.3).

### 17.8 Must-Use Functions

The result of a call to a `[[must_use]]` fn may not be thrown away. A call is
discarded when it is an expression statement that is not its block's value:
any statement but the last of a block, or the last statement of a fn that
returns nothing. Both compilers reject it, located at the call (AGAST #2137):

```
t.ritz:<line>:<col>: result of [[must_use]] fn '<fn>' is discarded
```

```ritz expect-error="result of [[must_use]] fn 'check' is discarded"
[[must_use]]
fn check(x: i32) -> i32
    if x == 0
        return 1
    0

fn main() -> i32
    check(1)
    0
```

Binding, assigning, returning or testing the result uses it, as does making
the call a value-returning block's last line:

```ritz
[[must_use]]
fn check(x: i32) -> i32
    if x == 0
        return 1
    0

fn both(a: i32, b: i32) -> i32
    let r: i32 = check(a)
    if r != 0
        return r
    check(b)
```

ritzunit's `assert_*` fns used to be `[[must_use]]`: each returned 0 or 1 for
the test to return, and a bare `assert_eq_i32(a, b)` statement made a test that
could not fail. Its integer helpers are now plain `assert`, and the string
checks it keeps (`assert_str_eq`, `assert_contains`, ...) are void
`[[test_helper]]` fns that `assert` ([§17.1](#171-test-attribute)), so a bare
call is the intended use.

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

### 18.4 Volatile Access

`volatile_load(p)` reads `*p` and `volatile_store(p, v)` writes `v` to `*p`
as volatile accesses: each is performed exactly once, at the pointee's
width, in program order with respect to the other volatile accesses. The
optimiser never removes, merges, splits or invents one. They are LLVM
`load volatile` and `store volatile`, and are how memory-mapped device
registers are read and written. A plain `*p` may be folded away or repeated.

```ritz
fn wait_tx_empty(uart_base: u64)
    let lsr: *u8 = (uart_base + 5) as *u8
    while (volatile_load(lsr) & 0x20) == 0
        pass

fn ring_doorbell(db: *u32, slot: u32)
    volatile_store(db, slot)
```

`p` must point to an integer type (`i8` to `u64`). `volatile_load` returns
the pointee type, and `v` converts to it as a call argument does (§7.5).
Any other pointee, or a wrong argument count, is a compile error:

```ritz expect-error="volatile_load needs a pointer to an integer type"
struct Regs
    status: u32

fn read(r: *Regs) -> u32
    let all: Regs = volatile_load(r)
    all.status
```

Volatile is not atomic. It orders nothing with respect to other CPUs; use
§18.5 for that.

### 18.5 Atomics and Fences

| Builtin | Effect | Returns |
|---|---|---|
| `atomic_load(p)` | reads `*p` | the value |
| `atomic_store(p, v)` | writes `v` to `*p` | nothing |
| `atomic_xchg(p, v)` | writes `v` to `*p` | the old value |
| `atomic_cmpxchg(p, expected, new)` | writes `new` to `*p` if `*p == expected` | the old value |
| `atomic_fetch_add(p, v)` | `*p = *p + v` (wrapping) | the old value |
| `atomic_fetch_sub(p, v)` | `*p = *p - v` (wrapping) | the old value |
| `atomic_fetch_and(p, v)` | `*p = *p & v` | the old value |
| `atomic_fetch_or(p, v)` | `*p = *p \| v` | the old value |
| `atomic_fetch_xor(p, v)` | `*p = *p ^ v` | the old value |
| `fence()` | orders all memory accesses before it against all after it | nothing |

Each `atomic_*` is one indivisible read-modify-write (or read, or write)
that is sequentially consistent: LLVM `atomicrmw`, `cmpxchg`,
`load atomic` and `store atomic` with `seq_cst` ordering, and `fence` is
`fence seq_cst`. `atomic_cmpxchg` stored exactly when the value it returns
equals `expected`. The pointer rules are those of §18.4, and `*p` must be
naturally aligned (its address a multiple of its size); a misaligned
atomic is undefined.

```ritz
var g_lock: u32 = 0
var g_owner: u64 = 0

fn lock()
    while atomic_xchg(@g_lock as *u32, 1) != 0
        pass

fn unlock()
    atomic_store(@g_lock as *u32, 0)

fn try_claim(me: u64) -> bool
    atomic_cmpxchg(@g_owner as *u64, 0, me) == 0

fn publish(ring_idx: *u16, idx: u16)
    fence()                      # descriptors are visible before the index
    volatile_store(ring_idx, idx)
```

```ritz expect-error="atomic_fetch_add takes 2 arguments"
fn bump(counter: *u64)
    atomic_fetch_add(counter)
```

The names in §18.4 and §18.5 are reserved, as `sizeof` is: a call always
means the builtin.

*Why builtins and seq_cst only:* in the hardware cases the access is
volatile or atomic, not the object. A register block is reached through a
pointer computed from a base address, and the same lock word is read plainly
during setup. Builtins express that and need no change to the type
system. Sequential consistency is the one ordering that is always correct.
Weaker orderings can be added when a measured need appears.

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
| `async.runtime` / `async.tasks` | Async runtime |

See `docs/STDLIB_REFERENCE.md` for the function-level reference.

### 19.2 Built-in Functions

| Function | Description |
|----------|-------------|
| `print(literal)` | Print a string literal to stdout, with `{expr}` interpolation |
| `eprint(literal)` | As `print`, to stderr |
| `format_into(sink, literal)` | Append the literal, with `print`'s interpolation, to a buffer ([§2.6](#formatting-into-a-buffer-format_into)) |
| `sizeof(T)` / `sizeof(expr)` | Size in bytes |
| `assert cond` | Runtime check; exits 1 on failure. **`[[test]]` and `[[test_helper]]` functions only** |
| `assert cond, "message"` | As above, naming what the check was for |
| `volatile_load(p)` / `volatile_store(p, v)` | Volatile access ([§18.4](#184-volatile-access)) |
| `atomic_*(p, ..)` / `fence()` | Atomic access and fences ([§18.5](#185-atomics-and-fences)) |

`assert` is legal **only inside a `[[test]]` or `[[test_helper]]` function**
([§17.1](#171-test-attribute)), and the compiler enforces it rather than leaving
it to convention — an `assert` in ordinary code is a compile error, located at
the assert, naming the offending function:

```ritz expect-error="assert is only allowed in [[test]] and [[test_helper]] functions, not in 'main'"
fn main() -> i32
    assert 1 == 1
    return 0
```

**What a failing assert prints.** It writes one diagnostic to stderr and exits
with status 1:

```text
<file>:<line>: assertion failed[: <message>]
  left:  <value>
  right: <value>
```

When the condition is a comparison `a OP b` (`==`, `!=`, `<`, `<=`, `>`, `>=`)
whose operands are integers, bools or pointers, the `left:` and `right:` lines
show both values, and without a message the first line names the operator
(`left == right`). Signed integers print in decimal, unsigned ones (`u8` …
`u64`) as unsigned decimal, bools as `true` / `false` and pointers in hex
(`0x0` for null). Each operand is evaluated once: the comparison and the report
share the value. Any other condition (`assert ok`, `assert a and b`, a float
comparison) prints only the first line. In a `[[test_helper]]`, `<file>:<line>`
is the calling test's and a final line, `  in helper <fn> at <file>:<line>`,
names the assert itself.

```ritz expect-runtime-error=".ritz:4: assertion failed: left == right\n  left:  3\n  right: 4\n"
[[test]]
fn test_sum() -> i32
    let got: i32 = 1 + 2
    assert got == 4
    0

fn main() -> i32
    test_sum()
```

Both the one- and two-argument forms work inside a test:

```ritz
[[test]]
fn test_arithmetic() -> i32
    assert 2 + 2 == 4
    assert 2 + 2 == 4, "addition is broken"
    0

fn main() -> i32
    return 0
```

`print` and `eprint` are the only builtins that take a string, and they require a literal:

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
item         := attrs (fn_def | extern_fn | struct_def | enum_def
                        | const_def | global_var | extern_var | type_alias
                        | import | impl_block)
              | trait_def

attrs        := ('[[' attr (',' attr)* ']]' NEWLINE)*     # §17
attr         := IDENT | IDENT '=' STRING
fn_def       := 'pub'? 'fn' IDENT generic_params? '(' params? ')'
                ('->' type)? (block | '=' 'extern' NEWLINE)   # §5.3
extern_fn    := 'extern' 'fn' IDENT '(' params? ')' ('->' type)? NEWLINE
extern_var   := 'pub'? 'extern' 'var' IDENT ':' type NEWLINE   # §5.3
type_alias   := 'pub'? 'type' IDENT '=' type NEWLINE
struct_def   := 'pub'? 'struct' IDENT generic_params? NEWLINE INDENT field+ DEDENT
enum_def     := 'pub'? 'enum' IDENT generic_params? NEWLINE INDENT variant+ DEDENT
impl_block   := 'impl' generic_params? (IDENT 'for')? IDENT NEWLINE
                INDENT fn_def* DEDENT
trait_def    := 'pub'? 'trait' IDENT NEWLINE INDENT trait_sig+ DEDENT
trait_sig    := 'fn' IDENT '(' params? ')' ('->' type)? NEWLINE
params       := param (',' param)* ','?
call         := expr '(' (expr (',' expr)* ','?)? ')'

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

`trait` declarations parse in both compilers. ritz1 checks only their
syntax: methods are resolved statically from the receiver's concrete type
(§12.2), so a declaration adds nothing to the emitted module.

Parameter lists and call argument lists accept one trailing comma, so a
one-item-per-line list can end each line with `,`.

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
