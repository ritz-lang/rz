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

**Line continuation.** A line ends its statement, except when its last
token is a binary operator (`and`, `or`, `&&`, `||`, `|`, `^`, `&`, a
comparison, `<<`, `>>`, `+`, `-`, `*`, `/`, `%`) or `as`: the expression then
continues on the next line, at the **same** indent (AGAST #2954). Blank and
comment-only lines between the two are skipped.

```ritz
fn inside(x: i32, lo: i32, hi: i32) -> bool
    x >= lo and
    x < hi

fn pack(r: u8, g: u8) -> u32
    ((r as u32) << 8) |
    (g as u32)
```

**One statement per line.** Ritz has no `;` statement separator: a
statement ends its line, and the next one starts on a new line. A second
statement on the same line is an error at its first token (AGAST #4283), so
`let a = 1U32` is refused at the `U32` (§2.6: a suffix is lowercase) rather
than read as `let a = 1` and a stray `U32`:

```ritz expect-error="unexpected 'g'"
fn g() -> i32
    0

fn two() -> i32
    let a = 1 g()
    a
```

A line that does not end in an operator ends the statement, even when the
next line could carry on the expression: `x = x + 1` followed by `-x` is two
statements. Inside `(`, `[` or `{` line breaks and indentation are ignored
altogether. So no block can open there: a multi-line `if` or `match` inside
brackets is an error; bind it to a `let` first (LARB R46a). The error names
the bracket and points at the `if` or `match`. A one-line
`if c then a else b` is not a block, and stays legal inside brackets:

```ritz expect-error="a block can't open inside `(`"
fn id(v: i32) -> i32
    v

fn pick(n: i32) -> i32
    id(match n
        1 => 10
        _ => 20
    )
```

```ritz
fn id(v: i32) -> i32
    v

fn pick(n: i32) -> i32
    let t: i32 = match n
        1 => 10
        _ => 20
    id(t) + id(if n == 1 then 1 else 2)
```

A continuation may also be indented *deeper* than the statement's first line,
so it can line up under what it continues (LARB R46, AGAST #2193). After a
line that ends in an operator, the next line opens no block and closes none:
its indent only has to be at least the statement's own. A continuation
indented *less* than the statement is an error at that line. The line after
the expression ends is measured against the statement's first line as usual.

```ritz
fn mixed(a: bool, b: bool, c: bool, d: bool) -> bool
    let h = (a or b) and
            c and d          # deeper continuation: one expression
    h
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
no-op statement with no value: see [§6.1](#61-ifelse)). `mut` is reserved but only valid in
`*mut T`; `let mut` was removed by RERITZ (see [§4.2](#42-mutable-bindings-var)).

`asm` starts an inline assembly block ([§18.6](#186-inline-assembly)), so it
can't be used as an identifier:

```ritz body expect-error="unexpected 'asm'"
let asm = 1
```

### 2.5 Identifiers

Identifiers begin with a letter or underscore, followed by letters, digits, or underscores.

```
identifier := [a-zA-Z_][a-zA-Z0-9_]*
```

`$` is never part of an identifier. Compilers use it inside generated names
(`W$i32_bump`, a monomorph), and those names can't be written in source; a `$`
outside an `asm` body is a located error (LARB R37, AGAST #3285).

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

A type suffix is lowercase: `u8`, `u16`, `u32`, `u64`, `usize`, `i8`, `i16`,
`i32`, `i64`, `isize` (and `f32`, `f64` on a float). `1U32` is no typed
literal: it lexes as `1` followed by the identifier `U32`, and is refused at
the `U` (AGAST #4273).

#### Digit Separators

A `_` may separate two digits of a numeric literal, decimal, hex or binary:
`1_000_000`, `0xFFFF_FFFF`. It has no value. It may not start or end the
digits, follow the `0x`/`0b` prefix, stand next to another `_`, or touch a
`.`, exponent or type suffix (LARB R73).

```ritz body
let million = 1_000_000         # 1000000
let mask = 0xFFFF_FFFF as u64   # 4294967295
let bits = 0b1010_0101          # 165
let big = 1_000u64              # before a suffix: digits, then the suffix
let f = 1_000.2_5e1_0           # each digit run of a float may be grouped
```

A misplaced `_` is a lexical error at that `_`: `1_`, `1__0`, `0x_FF`, `1_.5`,
`1._5`, `1_e5`, `1e_5`, `1_u8`, and `0b1_2` (`2` is no binary digit). A `_`
must also have a digit of the literal's own base on each side.

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
(AGAST #98). `s"hello"` now lexes as the identifier `s` next to a string,
and that string is a second statement on the line ([§2.2](#22-indentation)),
refused at its opening quote:

```ritz body expect-error=".ritz:2:16: unexpected '"
let bad = s"hello"
```

`make check-no-s-strings` fails the build if one reappears in the tree.

**Escape sequences:** `\n`, `\t`, `\r`, `\\`, `\"`, `\'`, `\0`, `\e` (ESC,
0x1B), `\xNN`, and `\{` / `\}` for a literal brace anywhere. They mean the same
in `"..."`, `c"..."` and `'.'` literals (AGAST #1872).

`\xNN` is exactly two hex digits, in either case, and gives that byte. The byte
must be ASCII, at most `\x7F`: a literal is UTF-8 text, and a lone byte above
that would be half a character, so a non-ASCII character is written as itself.

```ritz body
let clear: *u8 = c"\e[2J\e[H"   # ANSI clear screen, cursor home
let esc: u8 = '\x1B'            # the same byte as '\e'
let del: u8 = '\x7f'
let csi: StrView = "\x1b["
```

Anything else after `\x` is an error at the `x`, as an unknown escape is:

```ritz body expect-error="Hex escape '\x' needs exactly two hex digits"
let bad: u8 = '\x1'
```

```ritz body expect-error="is above '\x7F'"
let half: *u8 = c"\xC3"
```

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

- `write(buf, "...")` reads well, but `write` belongs to programs: the
  workspace defines it as an `extern fn` and as methods. A builtin of that
  name would take the call away from them. That is why `write`, `read`,
  `open`, `close` and `nanosleep` are ordinary identifiers with no built-in
  meaning (AGAST #3243): a call to one resolves like any other call, and
  the syscalls are ritzlib.sys's `sys_write`, `sys_read`, `sys_open`,
  `sys_close` and `sys_nanosleep`.
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

`usize` is another name for `u64`, and `isize` for `i64`: the same types, not
new ones. Every Ritz target is 64-bit. So a `usize` is unsigned for every
operator, takes any `u64` literal, and `Vec<usize>` is `Vec<u64>` (LARB R53):

```ritz
import ritzlib.gvec

fn first(v: @Vec<u64>) -> u64
    return *v.data

fn main() -> i32
    let b: usize = 18446744073709551608    # u64's range
    let top = b >> 60                       # 15: a logical shift
    var d: [1]usize = [7]
    var v = Vec<usize> { data: @d[0], len: 1, cap: 1 }
    let x: u64 = first(@v)                  # a Vec<usize> is a Vec<u64>
    0
```

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
| `*mut T` | The same type as `*T`, spelled differently: a write through `*T` is already allowed, so `Vec<*mut i32>` is `Vec<*i32>` (LARB R74) |
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

Read-only reaches everything behind an `@T`, an `@&T` field too. With `h: @H`
and `m: @&C` a field of `H`, `h.m` doesn't fit an `@&T` slot either, as an
argument or in `let m: @&C = h.m`, though an `@&T` held in a value, in another
`@&T`, or behind a raw `*T` still does.

```ritz expect-error="an `@T` doesn't fit an `@&T` slot: make it `@&T`"
struct Point
    x: i32

struct Holder
    m: @&Point

fn reset(p: @&Point)
    p.x = 0

fn clear(h: @Holder)
    reset(h.m)

fn main() -> i32
    var q = Point { x: 1 }
    var h = Holder { m: @&q }
    clear(@h)
    q.x
```

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

A reference refers to exactly one type. `@x` or `@&x` fits an `@U`, `@&U` or
`*U` slot only when `x` is a `U`: the same type, not one of the same width, so
`@&n` of a `u32` doesn't fit `@&i32`, and `@&a` of a `[2]u32` doesn't fit
`a:& [2]i32`. A place passed to a `name:& U` parameter is held to the same rule.
To reinterpret, cast: `@&n as *i32`.

A pointer or reference *value* is held to the same rule wherever it lands: a
`let` or `var`, an assignment, an argument or a `return` (LARB R71). A `*T`,
`@T` or `@&T` fits a `*U`, `@U` or `@&U` slot only when `T` is `U`, so a
`*[4]i32` doesn't fit `*[3]i32`, a `*[3]i64` doesn't fit `*[3]i32`, and a `*C`
doesn't fit `*D`. The byte pointer is the way between: any `*T` or `@T` fits a
`*u8`, a `*u8` fits any `*T`, and `null` fits any pointer.

```ritz expect-error="a reference to one type doesn't fit a reference to another: cast it with `as`"
fn widen(n:& i32) -> i32
    let p: @&i64 = @&n
    *p = 3
    0

fn main() -> i32
    var n: i32 = 1
    widen(@&n)
```

```ritz
fn bits(n:& u32) -> i32
    let p: *i32 = @&n as *i32
    *p = 3
    0

fn main() -> i32
    var n: u32 = 1
    bits(@&n)
    n as i32
```

```ritz expect-error="a reference to one type doesn't fit a reference to another: cast it with `as`"
fn first(p: *[3]i32) -> i32
    p[0]

fn main() -> i32
    var g: [4]i32
    let q: *[4]i32 = @g
    first(q)
```

```ritz
fn first(p: *[3]i32) -> i32
    p[0]

fn main() -> i32
    var g: [4]i32
    g[0] = 7
    let q: *[4]i32 = @g
    let bytes: *u8 = q
    first(bytes) + first(q as *[3]i32) - 14
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

The value is copied into every element, so a move-only value fills at most one
(§13.2).

An array literal or fill has no element type of its own until a slot gives it
one, so it takes the element type of the array it lands in, element by element
under §7.5:

```ritz body
var bytes: [4]u8 = [1, 2, 3, 200]
var words: [4]i32 = [0; 4]
```

The literal's length must be the slot's `N` exactly, for a list and a fill
alike. A shorter or longer one is an error at the literal; nothing is
zero-filled (LARB R42, AGAST #3315). Write `[0; N]` and then store the
elements you mean. ritz0 and ritz1 both refuse it (AGAST #3383):

```text
let a: [3]i64 = [1, 2]       # error: an array literal of 2 elements for a `[3]i64`
let b: [3]i64 = [7; 2]       # error: the same
```

An array whose element type has drop glue (§13.6) must be initialised where it is
declared: `var a: [2]S` with no `=` is an error at the name (LARB R39, AGAST
#3305). Storing an element drops the old one, so every element must always hold
a value.

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

#### Constant tables

A lookup table is a module-level `const` array literal, not a chain of `if`s
(AGAST #1866). It lives in read-only data and indexes like any array: `T[i]`
with a run-time `i`, `for x in T`, `let x = T[i]` and `@T[i]` (§4.3). Its
element type is one of:

- an integer (`[N]u32`, `[N]u64`, ...), each element a constant expression
  (§4.3), hex literals with the top bit set included;
- `StrView`, each element a `"..."`;
- `*u8`, each element a `"..."`, a `c"..."` or `null`; either string points at
  its NUL-terminated bytes;
- a struct `S`, each element an `S { ... }` literal whose fields are constants of
  the field's type: an integer, a `bool`, a float, `null`, a `"..."` into a
  `StrView` or `Span<u8>` field, a string into a `*u8` field, or a nested struct
  literal.

```ritz
import ritzlib.span

struct Status
    code: i32
    reason: StrView

const STATUSES: [3]Status = [
    Status { code: 200, reason: "OK" },
    Status { code: 404, reason: "Not Found" },
    Status { code: 503, reason: "Service Unavailable" }
]

struct Header
    name: Span<u8>
    value: Span<u8>

const HEADERS: [2]Header = [
    Header { name: ":path", value: "/" },
    Header { name: "age", value: "" }
]

const DAYS: [2]StrView = ["Mon", "Tue"]
const ARGV0: [3]*u8 = ["ls", c"cat", null]
const K: [2]u32 = [0x428a2f98, 0xb5c0fbcf]

fn reason(code: i32) -> StrView
    for s in STATUSES
        if s.code == code
            return s.reason
    ""

fn main() -> i32
    let h = HEADERS[1]
    reason(404).len as i32 + h.name.len as i32 + (K[1] >> 31) as i32 - 13
```

An integer, `*u8` or `StrView` table can also be a fill, `[v; N]`; a `StrView`
fill's `v` is a `"..."`, and every element views the same bytes. Any other
struct table can't be a fill: write its elements out.

```ritz
const BLANK: [4]StrView = ["-"; 4]

fn main() -> i32
    var i: i32 = 3
    BLANK[i].len as i32 - 1
```

A `*u8` element that is not a string or `null` is an error at the element. A
pointer is `null`, never the integer `0` (§3.2):

```ritz expect-error="const 'NAMES' element 1 is not a string literal or null"
const NAMES: [2]*u8 = ["a", 0]
```

### 3.4 Slice Types

```ritz
import ritzlib.span

fn total(xs: Span<u8>) -> i64
    0
```

`Span<T>` is a fat pointer: `(*T, len)`.

`[T]` is sugar for `Span<T>`. It names the same type, not a second one with the
same shape, so either spelling fits wherever the other does: a parameter, a
return type, a local, a struct field, or a type argument (`Option<[u8]>`,
`Result<[u8], E>`). The size is what tells the two bracket forms apart: `[N]T` is
an array (§3.3), `[T]` a span.

```ritz
import ritzlib.span

fn head(s: [u8], n: i64) -> Span<u8>
    s[0..n]

fn first(s: Span<u8>) -> Option<[u8]>
    if s.len == 0
        return None
    Some(head(s, 1))

fn main() -> i32
    let a: [3]u8 = [7, 8, 9]
    let h: [u8] = head(@a, 2)
    match first(h)
        Some(f) => f[0] as i32
        None => 0
```

`a[lo..hi]` slices a `Vec`, `Span` or `String`: elements `lo` up to but not
including `hi`, and `a[lo..=hi]` includes `hi`. A slice of a `Span` is a `Span`
over the same elements, so a write through it lands in `a`. A slice of a `Vec` or
`String` is a new `Vec` or `String`, a copy (`vec_slice`, `string_slice`), unless a
`Span` is expected, where it is a view like a `Span`'s: a `Span<T>` (or `[T]`)
`let`, return value, argument, or variant payload (`Some(v[0..1])` into an
`Option<[T]>`).

```ritz
import ritzlib.gvec

fn main() -> i32
    var v: Vec<i32> = vec_new<i32>()
    v.push(10)
    v.push(20)
    v.push(30)
    let t = v[1..3]
    let u = v[0..=1]
    t[1] + u.len as i32
```

Through a `*T`, `@T` or `@&T` to a `Vec`, `Span` or `String`, `p[lo..hi]` slices what
`p` points at: it's `(*p)[lo..hi]`, as `p[i]` is `(*p)[i]` (§7.8). An array doesn't
slice, so neither does a pointer to one.

```ritz
import ritzlib.gvec

fn middle(p: @Vec<i32>) -> Vec<i32>
    p[1..=2]

fn main() -> i32
    var v: Vec<i32> = vec_new<i32>()
    v.push(10)
    v.push(20)
    v.push(30)
    v.push(40)
    let t = middle(@v)
    t[1] + t.len as i32 - 32
```

### 3.5 String Types

| Type | Description |
|------|-------------|
| `String` | Owned, heap-allocated, growable |
| `StrView` | Borrowed `{ ptr, len }` view — the default type of a `"..."` literal |
| `*u8` | C-style NUL-terminated string — the type of a `c"..."` literal, and of a `"..."` literal in a `*u8` slot |
| `Span<u8>` | Borrowed byte slice with length — also the type of a `"..."` literal in a `Span<u8>` slot |

```ritz
import ritzlib.string
import ritzlib.strview

fn main() -> i32
    var s: String = string_from("hello")
    let n = string_len(@s)
    string_drop(@&s)
    n as i32
```

A literal doesn't fit a `String` slot either: `let s: String = "abc"` is an
error at the literal, and you write `string_from("abc")` (LARB R49, AGAST #3361,
#3393). A `String` allocates, and that should be visible in the source:

```ritz expect-error='a string literal is not a `String`: write `string_from("abc")`'
import ritzlib.string

fn main() -> i32
    let s: String = "abc"
    0
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

In a `Span<u8>` slot a `"..."` literal is a `Span<u8>` of its bytes; a `StrView`
value, a `c"..."` literal and a `String` don't convert (LARB R62, AGAST #3483).
The slot may be a `let`, an argument or a return value. Escapes are decoded, so
`"a\tc"` is three bytes:

```ritz
fn count(s: Span<u8>) -> i64
    s.len

fn tab() -> Span<u8>
    return "a\tc"

fn main() -> i32
    let s: Span<u8> = "abc"
    let t = tab()
    if s.len != 3 or s[0] != 97 or s[2] != 99
        return 1
    if t.len != 3 or t[1] != 9
        return 2
    if count("hello") != 5
        return 3
    0
```

Only the literal converts. A `StrView` value is refused (AGAST #3441), and so
is a `c"..."` literal, which is a bare `*u8` with no length (AGAST #3440), and a `String`:

```ritz body expect-error="its initialiser is a `StrView`"
let v: StrView = "abc"
let s: Span<u8> = v
```

```ritz body expect-error='a `c"..."` literal is a `*u8`, not a `Span<u8>`'
let s: Span<u8> = c"abc"
```

```ritz expect-error="its initialiser is a `String`"
import ritzlib.string

fn main() -> i32
    var t: String = string_from("abc")
    let s: Span<u8> = t
    0
```

Ask for the conversion by name: `span_from_strview` for a `StrView` (via
`string_as_view` for a `String`) and `span_from_cstr` for a `*u8`:

```ritz
import ritzlib.span
import ritzlib.string
import ritzlib.strview

fn main() -> i32
    let v: StrView = "abc"
    let a: Span<u8> = span_from_strview(v)
    let b: Span<u8> = span_from_cstr(c"abc")
    var t: String = string_from("abc")
    let c: Span<u8> = span_from_strview(string_as_view(@t))
    let n = a.len + b.len + c.len
    string_drop(@&t)
    if n == 9
        return 0
    1
```

A `StrView` also has the built-in method `as_bytes()`, which needs no import:
`s.as_bytes()` is a `Span<u8>` of the same bytes, with no copy, valid as long
as `s`'s bytes are (AGAST #3599). It takes no arguments. The receiver may
be a borrow: on `s: @StrView` or `s: @&StrView`, `s.as_bytes()` is the same
`Span<u8>` (AGAST #3699, #4176). The result is a
`Span<u8>` value, so pass it as itself: `@bytes` is an `@Span<u8>`, and a
`Span<u8>` slot refuses it (no auto-deref, LARB R1):

```ritz
fn first(b: Span<u8>) -> i32
    b[0] as i32

fn main() -> i32
    let text: StrView = "A"
    let bytes = text.as_bytes()
    if bytes.len != 1
        return 1
    first(bytes) - 65
```

```ritz expect-error="doesn't fit a by-value slot: drop the `@`"
fn first(b: Span<u8>) -> i32
    b[0] as i32

fn main() -> i32
    let text: StrView = "A"
    let bytes = text.as_bytes()
    first(@bytes) - 65
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

An `impl` can't target an alias. `type Id = Foo` then `impl Id` is an error at
`Id`: "`Id` is a type alias for `Foo`: write `impl Foo`" (LARB R35, AGAST
#3287). A type's methods live under the one name it was declared with.

An alias names one type. `A | B` isn't a type, and a type name isn't a pattern
(LARB R52, AGAST #1622). ritz0 accepted an untagged-looking `type V = i64 | bool`
whose members were read out with an unchecked `v as i64`. For a value that is
one of several kinds, write an enum with payloads and `match` it; each variant
names its kind, so two kinds of the same type stay apart:

```ritz
enum Value
    Int(i64)
    Flag(bool)
    Ref(i64)

fn weight(v: Value) -> i64
    match v
        Int(n) => n
        Flag(b) => if b then 1 else 0
        Ref(id) => id * 10

fn main() -> i32
    let r = weight(Ref(4)) + weight(Flag(true))
    (r - 41) as i32
```

---

## 4. Variables

### 4.1 Immutable Bindings (let)

```ritz body
let x: i32 = 42       # Explicit type
let y = 100           # Type inferred (i64)
```

A `(…)` pattern destructures a tuple, one name per element, in order; `_`
binds nothing:

```ritz body
let (a, _, c) = (1, 2, 3)   # a is 1, c is 3
```

It destructures tuples only. A named struct is read by its fields: binding
them by position would silently rebind every name after a field added to the
struct (LARB R67). There is no named-field pattern yet.

```ritz expect-error="`Bounds` is a struct, not a tuple: read its fields"
struct Bounds
    x_min: i32
    y_min: i32
    x_max: i32
    y_max: i32

fn main() -> i32
    let b = Bounds { x_min: 0, y_min: 1, x_max: 2, y_max: 3 }
    let (_, y_min, _, y_max) = b    # write `let y_min = b.y_min`
    y_max - y_min
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

So must a global `var` or `let`: `var g = true` at module level is an error at
`=`, "a global needs a type: write `var g: bool = ...`" (LARB R38, AGAST #3039).
A global is shared by every function, so its type is written where it is
declared rather than read off a literal (§7.4 would make `var g = 5` an `i64`).

`@A[i]` and `@A` of a `const` array are shared references, `@T` and `@[N]T`,
into its read-only data (LARB R48, AGAST #3359). `@&A[i]` stays an error, since
a const is never a place you can write. A `const` scalar has no storage, so
`@N` of one is an error.

#### Constant initialisers

Module-level values are `const` and `var`; there is no module-level `let`
(`let g: i64 = 1` at module level is an error at the `let`). A global `var`
needs its type (above), and its initialiser, like a const's, is a *constant
initialiser* (LARB R60, R75; AGAST #3479):

- a literal: an integer, float, bool or char, `"…"` (a `StrView`, or a `*u8`
  in a `*u8` slot), `c"…"`, or `null` in a pointer slot;
- a const;
- arithmetic or a cast of constant initialisers (`K * 2 + 1`, `F * 2.0`,
  `(1 + 2) as i64`, `4096 as *u8`);
- a unit enum variant (`Color.Blue`); a variant with a payload is an error;
- an array literal (`[a, b, c]`, exactly `N` elements) or fill (`[v; N]`), or
  a struct literal (every field), of constant initialisers.

Each part is typed against its slot (§13.2), as a `let`'s would be, and each
float literal is the `f64` nearest it. No call runs before `main`: an
initialiser that calls a fn, or reads a global `var`, is an error at it. A
global with no initialiser is zeroed.

```ritz
struct Limits
    lo: i64
    hi: f64
    name: StrView

enum Mode
    Fast
    Safe

const K: i64 = 4
const SCALE: f64 = 1.5
const DEFAULT: Limits = Limits { lo: K * 2, hi: SCALE * 2.0, name: "std" }
const MODE: Mode = Mode.Safe

var counter: i64 = K * 2 + 1
var weights: [3]f64 = [0.5, SCALE, 1.0e3]
var limits: Limits = DEFAULT
var mode: Mode = Mode.Fast

fn main() -> i32
    counter = counter + limits.lo     # 9 + 8
    match MODE
        Mode.Fast => 1
        Mode.Safe => (counter - 17) as i32
```

A struct or enum const is read-only data, like a const array: `C.f` and `C`
read it, `@C` is an `@S` into it, and `@&C`, `C.f = v` and a borrow of it
through a `self:&` method are errors. A const isn't a pattern: an arm naming
a struct or enum const is refused as any binder taking a const's name is
(below); match the variant itself.

A const of a type with `Drop`, or one holding a type with `Drop`, is an error
at the `const`: nothing would ever drop it. The same rule for a global `var`
is pending AGAST #4079, which first migrates the globals that have one.

#### One meaning per name

A local binding can't take the name of a module-level value that a bare read
would reach: a `const`, a global `var` or an enum variant (§10), declared in
the module or imported. "Local binding" is a `let`, a `var`, a parameter, a
`for` variable, a match arm's name and a variant payload's name (§8.2). It is
a compile error at the binding's name, whatever the types (AGAST #2407, LARB
R12):

```ritz expect-error="a local can't take the name of a const: 'LIMIT' — rename the local"
const LIMIT: i32 = 7

fn main() -> i32
    let LIMIT: i32 = 3
    LIMIT
```

So a bare `LIMIT` always reads the const, and adding a `pub const` to a module
can't silently change what a local downstream reads: it stops that local
compiling instead. `_` binds nothing and takes no name.

A **fn** name is free: a local named like a fn is the local, since a call says
it wants a fn. Calling a local that holds no fn value is an error at the call:

```ritz expect-error="'size' is a local, not a fn: it can't be called"
fn size() -> i32
    7

fn main() -> i32
    let size: i32 = 3
    size()
```

A local of fn type still calls (`let f: fn() -> i32 = size` then `f()`).

#### No shadowing

A binding can't reuse a name that is still in scope in its fn. That covers a
`let` or `var` in a nested block over an enclosing one, a second `let` of the
same name in the same block, a `let` over a parameter, a `for` variable over a
local, and a match arm's name or a payload's name over a local. It's a compile
error at the new name, naming where the first binding is (AGAST #2395):

```ritz expect-error="a local can't reuse a name bound earlier in its fn: 'r' (at 2:9) — rename the local"
fn pick(b: i32) -> i32
    let r: i32 = 1
    if b > 0
        let r: i32 = 2
        return r
    r

fn main() -> i32
    pick(1)
```

So a name means one thing for as long as it's in scope, and no compiler has a
scope rule to get wrong. A binding's scope is the block that declares it, from
the binding on; a `for` variable's is the loop body, and an arm's names are the
arm's. Once that scope ends, the name is free again: the other arm of an `if`,
the next arm of a `match` and the next loop can each bind it. `_` binds
nothing, so it can come any number of times.

```ritz
fn total(r: Result<i32, i32>) -> i32
    var s: i32 = 0
    for i in 0..3
        s = s + i as i32
    for i in 0..2
        s = s + i as i32
    match r
        Ok(v) => s + v
        Err(v) => s - v

fn main() -> i32
    total(Ok(4)) - 8
```

### 4.4 Type Inference

Local variable types are inferred from the initializer:

```ritz body
let x = 42            # i64
let n: i32 = 42       # i32, because it is annotated
let s = "hello"       # StrView
let c = c"hello"      # *u8
```

A generic call takes its type arguments from its arguments. A call `f(args)` to a
generic `f<T...>` binds each `T` by matching each parameter's type against its
argument's type, structurally: `T`, `@T`, `@&T`, `*T`, `Vec<T>`, `@Vec<T>`, and
so on. An explicit `f<T>(...)` still works and wins. An integer literal argument
to a bare `T` parameter binds `T` to the literal's default type, `i64` (as
`let x = 3` would), unless another argument binds `T`. Then the literal takes
that type, so `vec_push(@&v, 42)` on a `Vec<i32>` is `vec_push<i32>`:

```ritz
import ritzlib.gvec

fn twice<T>(x: T) -> T
    x

fn main() -> i32
    var v = vec_new<i32>()     # nothing binds T here: it is spelled out
    vec_push(@&v, 42)          # T = i32, from `@&Vec<T>`
    let first = vec_get(@v, 0)
    let p = vec_as_ptr(@v)     # *i32
    let n = twice(3)           # T = i64
    vec_drop(@&v)
    first + p[0] + n as i32 - 87
```

A `T` that no argument binds (one that appears only in the return type, as in
`vec_new`), or that two arguments bind differently, is a compile error at the
call: ``can't infer `T` for `f`: write `f<T>(...)` ``. There is no inference
from the binding's annotation: `let v: Vec<i32> = vec_new()` is that error.
Inside a generic fn, `f(x)` with `x: T` is `f<T>(x)`.

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
reject any use of that value: a `let`, a `var`, an assignment, an argument, an
operand, or a `return` from a function that declares a value. A call through a
fn pointer typed with no return, such as `fn(i64)`, is judged the same way. A
procedure may still `return` a call to another procedure, because nothing uses a
value there.

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
extern fn memcpy(dst: *u8, src: *u8, n: i64) -> *u8
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

`.` goes through every level of pointer and reference to the receiver's type, as
it does for a field (§7.7): `p.m()` with `p: @*C`, `**C` or `***C` is `C.m`, and
`self` is the `C`, not a pointer to it. A method whose `self` is itself a pointer
(`self: **C`) takes the levels it asks for. A place one level short of it is lent,
as `@&q` (`@q` for `self: @*C`), the way a `*U` place is lent to `name:& *U`
(§13.4), so `*self = n` re-aims the caller's pointer. Nothing else is borrowed for
it: a call result, or a `C` where `self` is a `**C`, is refused.

```ritz
struct Node
    v: i32

impl Node
    fn aim(self: **Node, to: *Node)
        *self = to

fn demo_aim() -> i32
    var a = Node { v: 1 }
    var b = Node { v: 2 }
    var cur: *Node = @&a
    cur.aim(@&b)            # lends `cur`, as `@&cur`
    cur.v                   # 2
```

```ritz expect-error="a receiver of a pointer `self` must be a place one level short of it, or have its levels"
struct Node
    v: i32

impl Node
    fn read(self: **Node) -> i32
        self.v

fn main() -> i32
    var a = Node { v: 1 }
    a.read()
```

```ritz
struct Tally
    n: i32

impl Tally
    fn bump(self: @&Tally)
        self.n = self.n + 1

fn bump_twice(p: ***Tally)
    p.bump()
    p.bump()

fn demo_levels() -> i32
    var t = Tally { n: 1 }
    var a: *Tally = @&t
    var b: **Tally = @&a
    bump_twice(@&b)
    t.n                     # 3
```

A method's mangled name `Type_method` is a name a program may call, with the receiver as its first argument: `c.after()` and `Counter_after(c)` mean the same thing (LARB R10).

That holds for a non-generic `impl` only. A method of a generic `impl<T> W<T>` has no free name: `W_bump(w)` is an error, "`bump` is a method of generic `W<T>`: call it as `w.bump()`", and the compiler's internal instance name (`W$i32_bump`) can't be written, since `$` isn't an identifier character (§2.5; LARB R37, AGAST #3285).

`Type.m()` is for a method without `self`, such as a constructor `Reader.new(@data)`. A type isn't a receiver, so `Type.m(...)` of a method with `self` is an error however `self` is spelled. Write `c.m()` or `Type_m(@&c)` instead (`Type_m(c)` for a by-value `self`).

```ritz expect-error="Static method call Type.method() but method 'get' expects 'self' parameter: write `c.get()` or `C_get(@&c)`"
struct C
    x: i32

impl C
    fn get(self: @&C) -> i32
        self.x

fn main() -> i32
    var c = C { x: 3 }
    C.get(@&c)
```

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

Function pointers lower to opaque LLVM `ptr`, so `null` ([§3.2](#32-pointer-and-reference-types))
fits a fn-pointer slot, and a fn pointer compares with `null` by `==` / `!=`
(AGAST #3601): `h.handler = null`, `if h.handler != null`. A parameter whose type is written
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

A struct field of function type is called like a method (LARB R41, AGAST #2218):
`h.f(1)` calls the method `f` if the type has one, and otherwise the field `f` if
it is a `fn(...)`. `h` isn't passed; the arguments are exactly those written. If
the type has both a method and a fn field named `f`, `h.f(1)` is an error,
"`f` is both a method and a field of `H`: write `(h.f)(1)` for the field".
`(h.f)(1)` always calls the field. ritz0 (#3380), ritz1 and ritz1_selfhosted
(#3381) implement this:

```ritz
struct H
    f: fn(i32) -> i32

fn call(h: H) -> i32
    h.f(1)                  # calls the field
```

### 5.6 Closures

Ritz has no closures (LARB R56). `|x| e`, `|| e`, `|x: T| e` and an anonymous
`fn(…) e` used as an expression are each an error at the `|` or `fn` that opens
them: closures aren't supported: write a named fn and pass it by name
([§5.5](#55-function-pointer-types)).

```ritz body expect-error="closures aren't supported: write a named fn and pass it by name (§5.5)"
let add_one: fn(i32) -> i32 = |x| x + 1
```

```ritz body expect-error="closures aren't supported: write a named fn and pass it by name (§5.5)"
let add_one: fn(i32) -> i32 = fn(x: i32) -> i32 x + 1
```

State a closure would have captured goes in a struct next to a fn field, and
the fn takes it as a parameter: `s.f(s.k, x)` (LARB R41,
[§5.5](#55-function-pointer-types)). `examples/tier5_async/58_closures` shows
both forms.

### 5.7 The Entry Point: `main`

A program starts at its `pub fn main`, in one of three shapes (AGAST #198):

```ritz
pub fn main()
    let greeting: StrView = "hello"
```

```ritz
pub fn main(args: Span<StrView>) -> i32
    if args.len < 2
        return 1
    0
```

```ritz
pub fn main(args: Span<StrView>, env: Span<StrView>) -> i32
    env.len as i32
```

`args[0]` is the program's name. Each `env` element is one `KEY=VALUE`.
Most programs read the environment through `ritzlib.os.env` instead and
never take `env`. With `-> i32` the value is the exit status; without it,
`main` returns 0.

Any other parameter list or return type is an error, at `main`:

```ritz expect-error="`main` must take `()`, `(args: Span<StrView>)` or `(args: Span<StrView>, env: Span<StrView>)`"
pub fn main(n: i64) -> i32
    0
```

```ritz expect-error="`main` must return `i32` or nothing"
pub fn main() -> i64
    0
```

```ritz expect-error="`main` taking `Span<StrView>` must be `pub`: write `pub fn main(...)`"
fn main(args: Span<StrView>) -> i32
    0
```

There is one entry path. The runtime's `_start` calls the C symbol
`main(argc, argv, envp)`. For a `main` that takes spans or returns nothing,
the compiler names the fn `__ritz_main` and adds that `main` as an adapter
written in Ritz. It builds the spans once and calls the fn.
`docs/V1_ABI_CLEANUP.md` has the design.

`main` is the entry point, not a fn to call. A call to a `main` that takes
spans or returns nothing is an error, at the call:

```ritz expect-error="`main` is the program's entry point and cannot be called"
pub fn main(args: Span<StrView>) -> i32
    if args.len > 5
        return main(args)
    0
```

*Transitional:* the C shapes `main(argc: i32, argv: **u8) -> i32` and
`main(argc: i32, argv: **u8, envp: **u8) -> i32` are still accepted, and so is
a `main` without `pub` in a C shape, until the workspace migrates (AGAST #203).
Both are removed in #204.

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

It applies equally to an operand, such as the operand of an operator. An
operand's value is always used, so this is rejected even when the enclosing
expression is itself a statement (AGAST #1435; before it, the `if` evaluated to
`0`). A block `if` can't be a call argument, an index or a struct-literal
field, because no block opens inside brackets (§2.2):

```ritz expect-error="an `if` with no `else` has no value"
fn pick(c: i32) -> i32
    return 5 + if c == 1
        1
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

`pass` has no value either. It is a statement that does nothing, so it can
stand as a statement or as an arm of an `if` or `match` used as a statement,
but not where a value is wanted: an arm of an `if` or `match` whose value is
used, a `let` or `var` initialiser, an assignment, a `return` from a function
that declares a value, an argument or an operand. All three compilers report
it at the `pass` (AGAST #3759; before it, `pass` there was a silent `0`, and
an all-zero struct). If you mean `0`, write `0`:

```ritz body expect-error="`pass` has no value, so it can't be used where a value is wanted"
let n = 3
let c: i64 = if n > 0 then 5 else pass
```

```ritz body
let n = 3
let c: i64 = if n > 0 then 5 else 0
if n > 0
    pass
```

The arms of an `if`/`else` or `match` whose value is used must agree on
integer versus float. With no float annotation to give the merge its type, an
arm that yields an integer next to one that yields a float is an error, in
either order (AGAST #2094; before it ritz0 merged `if c then 0 else 1.5` at
`i64` and truncated `1.5` to `1`). Write the integer arm as a float, or
annotate the binding, and the integer arm converts:

```ritz body expect-error="match arms yield both an integer and a float value"
let c = true
let a = if c then 0 else 1.5
```

```ritz body
let c = true
let a = if c then 0.0 else 1.5
let b: f64 = if c then 0 else 1.5
```

The rule is the same whichever arm comes first (LARB R43, AGAST #3312). Every
typed slot gives the merge its type, not only an annotated binding: a
`return` or tail in a `-> f64` function, and an argument for an `f64`
parameter. In a float slot an integer arm converts as it would into a typed
`let` (§7.5, LARB R43a): a literal always, a non-literal only when its type is
exact in the slot (`i32` or `u32` into `f64`, by its own signedness). Any other
integer arm (`i64`, `u64`) is refused as lossy: write `n as f64`.

As with the else-less `if`, an `if` or `match` used as a statement has no
merged value, so its arms may end in values of any types.

A function that declares a return type is different. It is an error for such
a function to be able to reach its end without producing a value, whether its
last statement is an `if`, a loop, an assignment, a `pass` arm or a call to a
procedure. There is no implicit `0`. An `if`/`else` whose arms all return, or a
`loop` with no `break`, never reaches the end and needs nothing after it, and
may have nothing after it. The
condition of a `while` counts as always true only when it is the literal
`true`. `-> void` declares no value, so it follows the rules for a procedure.

A statement that can never run is an error, "unreachable code", located at the
first such statement of its block (LARB, AGAST #2520). That is any statement
that follows, in the same block, a `return`, `break` or `continue`; an
`if`/`else` or a `match` whose every arm diverges; or a `loop` (or `while
true`) with no `break` that leaves it. It extends R13, which requires every
`match` arm to be reachable, to statements:

```ritz expect-error="unreachable code"
fn sign(b: i32) -> i32
    if b > 0
        return 1
    else
        return -1
    0
```

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

A range's variable has its bounds' integer type (AGAST #4080, the ruling of
record):

- A lone untyped integer literal bound is the other bound's type when it fits
  there, as a binary operator's literal operand is (§7.1, LARB R21). With
  `n: i32`, `for i in 0..n`, `1..n` and `1..(n + 1)` all bind an `i32`, and
  `k..10` with `k: i32` does too.
- A literal that doesn't fit widens the loop to an `i64` (`-129..m` with
  `m: i8`). Two literals (`1..=5`) are an `i64`, as a lone literal is.
- Otherwise the wider bound's width, unsigned when a bound is unsigned (only a
  `u64` counts at 64 bits). That range compares unsigned (AGAST #1636 / #3328).
  So `-1..m` with `m: u32` is an `i64` range that compares signed and runs
  from `-1` (AGAST #4261), as does `a..m` with `a: i64`.

The variable's arithmetic is at that width: with `m: u32`, `i - 2` in
`for i in 1..m` wraps as a `u32` does.

```ritz
fn take(v: i32) -> i32
    v

fn sum_to(n: i32) -> i32
    var s: i32 = 0
    for i in 1..(n + 1)     # i: i32, so take(i) narrows nothing
        s = s + take(i)
    s

fn main() -> i32
    sum_to(4) - 10
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
  element doesn't change the binding. Over an array of any rank the element is the
  array one rank down: `for plane in g` with `g: [2][2][3]u8` binds a `[2][3]u8`,
  which indexes (`plane[1][2]`) and iterates like any local of that type (LARB R40,
  AGAST #3307, #3379).
- Only an rvalue gets a temporary: a call's by-value result (`for x in mk()`, or
  `mk().a`), or a literal. Nothing else can reach it, so nothing can write to it.
- A place reached *through* a `Vec`'s element, such as `vs[0].a`, is an address
  into that `Vec`'s buffer, as `@vs[0]` is. So when the iterable's path crosses an
  index into anything but an array (a `Vec`, a `Span` or a pointer), the loop holds
  an `@` of the place that index is into, the last one on the path (`vs` in
  `vs[0].a`, `s.vs` in `s.vs[0].a`), for its whole body (LARB R11). A mutable
  borrow of that place, or of one holding it, is §13.5's located error in the
  body: `vs.push(h)`, `@&vs`, `vs` bare into a `:&` param, `vs = w`. A use
  *inside* it can't move the buffer and stays legal, and the loop sees it:
  `vs[0].a[2] = 50`, `@&vs[1]`. `for x in vs` walks the `Vec` itself and holds
  nothing (a push is safe, above), nor does a path through arrays alone
  (`h.a`, `hs[0].a`), whose storage can't move.

  ```ritz expect-error="cannot borrow `vs` as mutable - `vs` is already borrowed as immutable"
  import ritzlib.gvec

  struct H
      a: [3]i32

  fn main() -> i32
      var vs: Vec<H> = vec_new<H>()
      var h: H
      vs.push(h)
      for x in vs[0].a
          vs[0].a[2] = 50     # fine: inside `vs`, and seen
          vs.push(h)          # refused: may move the buffer the loop walks
      0
  ```
- That's a definite-case check, as §13.5's are. A push through another path,
  such as a pointer to `vs` or a callee that reaches it, isn't seen, and nor is
  `let p: *H = @vs[0]` (a `*T` isn't a borrow). If such a push moves the buffer,
  the address the loop walks is no longer valid.

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

#### Literal operands

An integer literal has no type until its context gives it one (LARB R1). In an
arithmetic or bitwise operation that context is the other operand (LARB R21):
with `m: u32`, `m + 1` is a `u32`, exactly as `m + o` is with `o: u32`, so it
wraps at 32 bits and `var n = m + 1` is a `u32`. Two literals are an `i64`. A
literal that doesn't fit the other operand's type is an error, as it is in a
slot. A shift is the exception (§7.4): its count has no say, and a literal on its
left is an `i64`.

An operation over literals only, such as `0 - 1`, `~63` or `1 << 26`, is a
constant. Its value is computed as the `i64` it would be, and the operand is then
one literal of that value (AGAST #4082). So with `w: i32`, `w ^ (0 - 1)` is an
`i32`, exactly as `w ^ -1` is. If the value doesn't fit the other operand's type,
or computing it leaves `i64`, the operand stays an `i64`. That is not an error,
because nothing about it was written as a literal of the wrong type.

`+`, `-` and `*` wrap on overflow at their type, except in a wider slot.

#### Wider slots

An integer operation used directly in a slot of a *wider* integer type is
computed in the slot's type (AGAST #3225): each operand is widened first, by its
own signedness, and the operation runs there. A slot is a typed `let` or `var`,
an `=` or `op=` target, a return or a function's tail, an argument, a field, an
element, or an `if`/`match` arm landing in one of those. "Directly" means through
`+ - * / % << & | ^` and unary `-`, to any depth: in `let w: i64 = x * y + 1`
both `x` and `y` are widened. `/` and `%` take the slot's signedness. A call,
index, cast, `>>` or `~` reads its operand at the operand's own type, so the walk
stops there and R21's type applies below it. Widening is silent; wrapping isn't
done behind your back. Where there is no wider slot, as in `var n = m + 1`, the
operation stays at its operands' type.

```ritz body
let m: u32 = 4294967295
let big: i64 = m * 1000           # 4294967295000: an i64 multiply
let sum: i64 = m + 1              # 4294967296
let neg: i64 = (m - m) - 1        # -1: subtracted in the i64
let n = m + 1                     # 0: no wider slot, a u32
let cast = (m + 1) as i64         # 0: a cast isn't a slot
let x: u8 = 200
let w: u16 = x * x                # 40000: a u16 multiply
```

```ritz body
let m: u32 = 4294967295
let o: u32 = 1
let n = m + 1               # 0, a u32
let p = m + o               # 0
let wide = (m as i64) + 1   # 4294967296
let x: u8 = 200
let y = x * 2               # 144
let z = 4294967295 + 1      # 4294967296: two literals are an i64
```

```ritz body expect-error="`300` does not fit in `u8`"
let x: u8 = 200
let y = x + 300
```

#### Wrapping operators

`+%`, `-%` and `*%` add, subtract and multiply, wrapping on overflow at their
operands' type (LARB R63). Write them where wrapping is the point: hashes, crypto
rounds, PRNGs. Each has an `op=` form: `x +%= y` is `x = x +% y`. They bind as
`+`, `-` and `*` do, and type as `+` does (R21): the operands and the result are
the operand type, and a literal takes the other operand's type. Unlike `+`, they
aren't widened by a wider slot: `let w: u16 = a +% b` with `a, b: u8` wraps at 8
bits, as you asked. They take integers only, so a float or a pointer operand is
an error.

```ritz body
let a: u8 = 200
let b: u8 = 100
let s = a +% b                     # 44, a u8
let w: u16 = a +% b                # 44: a wider slot doesn't widen it
let d = b -% a                     # 156
var h: u32 = 2166136261
h = (h ^ 97) *% 16777619           # one FNV-1a step
h +%= 1
let k: i32 = 2147483647
let m = k +% 1                     # -2147483648
```

```ritz expect-error="`+%` wraps an integer, and `f64` isn't one"
fn f(x: f64) -> f64
    x +% 1.0
```

#### `f32` meeting `f64`

When an `f32` and an `f64` meet in `+ - * / %`, the `f32` widens to `f64`
silently and the result is an `f64`. Nothing is lost, because every `f32` is
exact as an `f64`. A float literal has no width of its own: it takes the other
operand's, so `y * 2.0` with `y: f32` is an `f32`. So does an expression of
literals alone, such as `0.0 - 7.0`; on its own it's an `f64`.
Comparing the two widths is different: see §7.2.

```ritz body
let y: f32 = 3.0
let x: f64 = 2.5
let z = y * x                     # 7.5, an f64: y widens
let w: f64 = z
let h = y * 2.0                   # 6.0, an f32: the literal is an f32
```

To get an `f32` back from `z`, write `z as f32`: without the `as`,
`let n: f32 = z` is an error (§7.5, "Float narrowing").

#### Pointer difference

`p + n` and `p - n` on a `*T` step by whole elements of `T`. `q - p` on two pointers
to the same `T` is the inverse: their distance in elements of `T`, an `i64`, so
`(p + n) - p == n`. It's negative when `q` comes before `p`. Two pointers to
different types have no common element to count in, and ritz0 refuses them.

```ritz body
var a: [8]i32
let s: *i32 = @a[0]
let p: *i32 = s + 5
let n = p - s         # 5 elements, not 20 bytes
let back = s - p      # -5
```

A reference is one value, not a buffer (LARB R9, R16): `+`, `-`, `+=`, `-=` and
`q - p` are errors on an `@T` or `@&T` whose `T` isn't an array, because `p + 1`
names a value the reference never lent, which the loan check (§13.5) can't see.
On a reference, cast first: `(p as *T) + n`. The row walk on an `@[N]T` or
`@&[N]T` stays legal (§7.8).

```ritz expect-error="a reference is one value, not a buffer: `+` needs a `*T`; write `(p as *i32) + 1`"
fn f(p: @&i32) -> i32
    let q: *i32 = p + 1
    *q
```

For a struct `T` the element is `sizeof(T)`, padding included. Before AGAST #2928
ritz0 emitted `sub` on two pointers, which clang rejected, and ritz1 gave
`q - p * sizeof(T)`, except for an element of a `[N]*T` array, which gave bytes.

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

`/`, `%`, `<`, `<=`, `>` and `>=` are unsigned when either operand is unsigned,
and signed otherwise. An operand that is itself an expression has the type of its
operands, by the rule `>>` uses (§7.4): the wider operand wins, and at equal
width the unsigned one does. A literal operand is the other operand's type
(§7.1); a lone one is an `i64` unless only a `u64` holds it.
A narrow operand is a value of its type, so with `s: u8 = 7`, `~s` is `248` here
too:

```ritz body
let a: u64 = 0xFFFFFFFFFFFFFFF8
let z: u64 = 0
let s: u8 = 7
let big = (a ^ z) > 1      # true: `a ^ z` is a u64
let half = (a ^ z) / 2     # 9223372036854775804
let third = (~s) / 3       # 82
```

#### NaN

Float comparisons follow IEEE 754, as C's do. A NaN is unordered: `==`, `<`,
`<=`, `>` and `>=` are false when either side is NaN, and `!=` is true, so
`!=` is always the negation of `==` and `x != x` tests for NaN (AGAST #3836):

```ritz body
let n: f64 = 0.0 / 0.0
let is_nan = n != n         # true
let differs = n != 1.0      # true
let same = n == n           # false
let below = n < 1.0         # false
```

#### `f32` against `f64`

Comparing an `f32` with an `f64` (`== != < <= > >=`) is an error on every
compiler (AGAST #3607). Each value would widen correctly, but the answer is
rarely what the writer meant: with `a: f32 = 0.1` and `b: f64 = 0.1`, `a == b`
is false and `a > b` is true, because `0.1` rounds differently in each width.
Write `as` to choose the precision the comparison runs in:

```ritz body expect-error="cannot compare `f32` with `f64`: write `as` to choose the precision"
let a: f32 = 0.1
let b: f64 = 0.1
let same = a == b
```

```ritz body
let a: f32 = 0.1
let b: f64 = 0.1
let in_f32 = a == b as f32        # true: b rounds to a's f32
let in_f64 = a as f64 == b        # false: a's error shows in f64
let y: f32 = 0.1
let lit = y == 0.1                # true: the literal is an f32 here
```

A float literal, or an expression of literals alone, is never refused, because
it takes the other operand's type (§7.1). The result of an arithmetic operation has the width §7.1 gives it, so
`y * x > y`, with `y: f32` and `x: f64`, compares an `f64` with an `f32` and is
an error too.

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
signedness. So with `h: u64`, `(h ^ 1) >> 33` is logical. A literal operand is
the other operand's type (§7.1), and a literal count leaves the left operand's
type alone: `a >> 1` and `a << 4` keep the type of `a`. A literal on the left of a
shift is an `i64`, unless its value only fits a `u64`:
`0xF000000000000000 >> 60` is `15`. A constant expression shifts by the same rule.

The left operand is a value of its type, so with `a: u8` the sums in
`(a + a) >> 1` and `(a + 1) >> 1` wrap at 8 bits first, and in `(a << 4) >> 4`
the high nibble is gone before the `>>`: at `a = 248` the result is `8`. A wider
slot (§7.1) widens `<<` but stops at `>>`, which reads its left operand at that
operand's type, so `let w: i64 = (a << 4) >> 4` is `8` too. Say a wider width
with a cast:

```ritz body
let a: u8 = 248
let narrow: u8 = (a << 4) >> 4                    # 8: shifted at 8 bits
let wide: u8 = (((a as u16) << 4) >> 4) as u8     # 248: shifted at 16 bits
let half: u8 = a >> 1                             # 124
```

An `i64` below a narrower slot is a narrowing, a shift's result included:

```ritz body expect-error="implicit narrowing: `r` is declared `u8` but its initialiser has type `i64`"
let a: i64 = 248
let r: u8 = (a << 4) >> 4
```

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

`as` binds tighter than every binary operator, and its type ends at the first
token that can't continue a type. `|` never continues one (§3.8), so
`x as u64 | 1` is `(x as u64) | 1`, and `a + b as i64` is `a + (b as i64)`.
Parenthesise to cast a whole expression: `(a + b) as i64` (LARB R52a).

`as` doesn't convert between two struct types, by value or through a reference,
even when their fields match: build the other struct from the fields (LARB R72).
`r as C` with `r` an `@C` or `*C` reads a copy of the referent (§13), and
`@c as *D` is a pointer cast, so both stay legal.

```ritz expect-error="cannot cast `C` to `D`: `as` doesn't convert between structs: build a `D` from the fields"
struct C
    x: i32

struct D
    x: i32

fn f(r: @C) -> i32
    let d: D = r as D                # error: write `D { x: r.x }`
    d.x

fn main() -> i32
    let c = C { x: 4 }
    f(@c)
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

#### Integer and float conversions

`x as f32` / `x as f64` converts by the integer's own type: an unsigned value
is never read as negative.

```ritz body
let b: u8 = 255
let f = b as f32                 # 255.0, not -1.0
let big: u64 = 13835058055282163712
let d = big as f64               # 1.3835058055282164e19
```

A float → integer `as` rounds toward zero and **saturates**: a value below the
target's range gives its minimum, a value above gives its maximum, and NaN
gives 0. Every float converts to every integer type; nothing is undefined.

```ritz body
let x: f64 = 300.0
let y: f64 = 0.0 - 1.5
let a = x as u8                  # 255
let b = y as u8                  # 0
let c = y as i32                 # -1
let d = x as i8                  # 127
```

This is LLVM's `fptoui.sat` / `fptosi.sat`, and it's the same rule on all three
compilers (`ritz0/test_unsigned_float_cast.py`, AGAST #2192). A bare
`fptosi` gives poison out of range, and the optimiser is then free to delete
code that depends on the result.

Without `as`, an integer converts into a float slot (a `let` or `var`
initialiser, an assignment, an argument, a `return`, a field) only when every
value of its type is exact in the float. It converts by its own signedness,
so an unsigned value is never read as negative:

| Slot | Converts implicitly from |
|---|---|
| `f64` | `i8` `i16` `i32` `u8` `u16` `u32` |
| `f32` | `i8` `i16` `u8` `u16` |

For an `f32` meeting an `f64`, see §7.1 (arithmetic widens to `f64`) and §7.2
(a comparison needs `as`).

```ritz body
let x: u32 = 4000000000
let d: f64 = x                   # 4000000000.0
let h: u16 = 40000
let f: f32 = h                   # 40000.0
let n: i64 = 5
let e: f64 = n as f64            # i64 needs `as`
```

Every other pair is an error. Write `as` to accept the rounding:

```ritz body expect-error="implicit conversion from `i64` to `f64` can lose precision: write `<expr> as f64`"
let n: i64 = 9007199254740993
let d: f64 = n                   # would round to 9007199254740992.0
```

Integer literals are exempt: `let d: f64 = 4000000000` and `let f: f32 = -3`
need no `as`. This follows Rust's `From` conversions: f64 has a 53-bit
significand and f32 has a 24-bit one. It's the same rule on all three
compilers (`ritz0/test_implicit_int_to_float.py`, AGAST #2945). ritz1 works
out the integer's type from its Ritz types. Where it can't, for example for an
unannotated local, it converts without checking rather than guess.

A pointer never converts into a float slot, as the whole initialiser or as an
`if` / `match` arm (AGAST #2093, `ritz0/test_let_float_pointer.py`). Neither
does a `bool` (above):

```ritz body expect-error="cannot use a pointer as a float"
let p: *u8 = c"x"
let a: f64 = p
```

#### Float narrowing

An `f32` converts into an `f64` slot silently: every `f32` is exact as an
`f64`. The other way loses precision, so an `f64` value into an `f32` slot (a
`let` or `var` initialiser, an assignment, an argument, a `return`, a field,
an array element) needs `as f32` (LARB R70):

```ritz body expect-error="implicit conversion from `f64` to `f32` can lose precision: write `<expr> as f32`"
let x: f64 = 2.0
let n: f32 = x
```

That includes an `f32` meeting an `f64` in arithmetic, whose result is an
`f64` (§7.1):

```ritz body expect-error="implicit conversion from `f64` to `f32` can lose precision: write `<expr> as f32`"
let x: f64 = 2.0
let y: f32 = 3.0
let n: f32 = y * x
```

A float literal is exempt, and so is a constant expression of float literals:
it's evaluated as an `f64` and rounded to `f32` once. So is an `if` / `match`
whose every arm is one of these. An `if` with an `f32` arm and a literal arm is
an `f32`, since the literal takes the other arm's width.

```ritz body
let x: f64 = 2.0
let y: f32 = 3.0
let a: f32 = 0.1
let b: f32 = 1.0 / 3.0
let c: f32 = if y > 0.0 then 1.5 else 2.5
let d = if y > 0.0 then y else 0.0     # an f32
let e: f32 = d
let n: f32 = x as f32
```

ritz0 enforces this (`ritz0/test_f64_into_f32.py`, AGAST #3802); ritz1 still
narrows silently until AGAST #3998.

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

A literal arm of an `if` or `match` takes the declared type, as the whole
initialiser would, so it never widens its other arm: with `n: i32`,
`let m: i32 = if n < 255 then n else 255` is an `i32` and narrows nothing
(AGAST #1445). Only the arms that are the initialiser's own value count: an
`if` that is an operand, as in `2 * (if c then n else 0)`, keeps its literal
arms `i64`.

An arm may itself be an `if`/`match`, so an `else if` chain whose every arm
fits is accepted at any depth. The rule does no range analysis beyond that:
with `w: i64`, `if w < 255 then w else 255` is rejected even though it is
safe, and needs an `as`.

Arms are judged only where the `if`/`match` is written. Bound to a name, it is
that name's type, as any initialiser is: an unannotated `let a = if c then x
else 0` makes `a` an `i64`, so `a` narrows into an `i32` like any `i64` does:

```ritz expect-error="implicit narrowing: `n` is declared `i32` but its initialiser has type `i64`"
fn f(x: i32) -> i32
    let a = if x > 0 then x else 0
    let n: i32 = a
    return n
```

The same rule, with the same exemptions, holds wherever a value converts to a
declared integer type: an assignment `n = e` (the slot is `n`'s type, and
`n += e` is `n = n + e`), a call argument (the parameter's type), and a
`return` or a function's tail value (the return type):

```ritz expect-error="implicit narrowing: argument 1 of `take` is `i32` but this value has type `i64`"
fn big() -> i64
    return 4294967301

fn take(v: i32) -> i32
    return v

fn main() -> i32
    return take(big())      # would silently pass 5
```

A struct literal's field initialiser is a slot of the same kind, whose type is
the field's:

```ritz expect-error="implicit narrowing: field `v` of `S` is `u8` but this value has type `u16`"
struct S
    v: u8

fn main() -> i32
    let x: u16 = 300
    let s = S { v: x }      # would silently store 44
    return s.v as i32
```

A procedure's tail value is discarded, so it converts to nothing and isn't
checked. An `async fn`'s result is checked at its declared type, like any
other fn's: only its poll fn's own answer, the poll ABI's `bool` (LARB R78),
is not a return the user wrote.

```ritz expect-error="implicit narrowing: `f` returns `i32` but this value has type `i64`"
fn big() -> i64
    return 4294967301

async fn f() -> i32
    return big()            # would silently resolve to 5
```

A non-literal array element is held to the same rule, against the element type:

```ritz body expect-error="implicit narrowing: this element of a `u8` array has type `i64`"
let k: i64 = 300
let a: [2]u8 = [1, k]
```

ritz0 and ritz1 both enforce this rule at every slot above (a struct literal
field since AGAST #4157 / #4218). `ritz0/test_ritz1_implicit_narrowing.py` checks that they
give the same verdict on every case in `ritz0/test_implicit_narrowing.py` (a
`let`/`var` initialiser), and `ritz0/test_ritz1_implicit_narrowing_slots.py`
does the same for `ritz0/test_implicit_narrowing_slots.py` (an assignment, an
argument, a `return` and a struct literal field, AGAST #1444 / #4081 / #4218). ritz1 infers the value's type from its
Ritz types. Where that inference is unsure, for example for an unannotated
local, ritz1 accepts the value rather than guess (#1364).

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

**`*p` is a place** (LARB R9): it names the pointee itself, not a copy of it.
`(*p).f = v`, `*p = v`, `@*p`, `@(*p).f` and `(*p)` passed to a `:&` param all
act on the pointee. A method call on it is the call on `p`: `(*p).m()` means
`p.m()`, so a `self: *T`, `@T`, `@&T` or `:&` method runs on the pointee, and
mutability follows §3.2 (an `@&T` method through an `@T` is refused).

```ritz
struct Res
    w: u64

impl Res
    fn bump(self: *Res, n: u64)
        self.w = self.w + n

pub fn main() -> i32
    var r: Res = Res { w: 40 }
    let p: *Res = @r
    (*p).bump(2)            # r.w is now 42: the method ran on r
    var c = *p              # a by-value read copies
    c.bump(100)             # ... so this leaves r alone
    return r.w as i32       # 42
```

Only a by-value use of `*p` copies: `var c = *p`, `f(*p)`, or a method whose
`self` is by value. For a move-only type that copy is "cannot move out of a
reference" (§13.2), as `r.m()` would be:

```ritz expect-error="cannot move out of a reference"
struct T
    id: i32

impl Drop for T
    fn drop(self: @&T)
        pass

impl T
    fn burn(self: T) -> i32
        self.id

fn f(r: *T) -> i32
    (*r).burn()
```

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

`.` on a pointer or reference to a struct reaches the struct, as above, **through
every level**: with `p: @*W`, `**W` or `***W`, `p.f` is `W`'s field `f` for a read,
a store, `op=` and `@`/`@&`, and so is each step of a chain like `p.c.x` or
`p.a[1]`. `*` takes off one level and `.` the rest, so `(*p).f` means `p.f`.

```ritz
struct Inner
    x: i32

struct Outer
    c: Inner
    a: [2]i32

fn poke(p: ***Outer) -> i32
    p.c.x = 3
    p.a[1] += 7
    let e: @i32 = @p.a[1]
    p.c.x * 10 + *e
```

It reaches through a struct itself only when the struct opts in (LARB R17), through two
compiler-known traits, resolved statically like `Drop` and `Index` (§7.8):

```text
impl Deref for S                    fn deref(self: @S) -> @T
impl DerefMut for S                 fn deref_mut(self: @&S) -> @&T
```

The impl chooses `T` through its return type. `DerefMut`'s `T` must be `Deref`'s, and
`DerefMut` without `Deref` is an error at the impl.

For `s.f`, where `s` has struct type `S` (after the auto-deref above):

1. `S`'s own field or method `f`;
2. otherwise, if `S` implements `Deref`, `T`'s field or method `f`, through the trait;
3. otherwise, an error at `f`.

This is one step only: on a `Box<Box<H>>`, `b.k` doesn't reach `H`. **The own field
wins**, and that isn't an error: `b.ptr` on a `Box<T>` is always the Box's own `ptr`,
even when `T` has one, and `T`'s is `b.ptr.ptr`.

`s.f` reached through the trait is a place, and each use goes through one method:

| Use of `s.f` | Means |
|---|---|
| read by value, `s.f.g`, an `s.f[i]` read, `@s.f`, `for x in s.f`, a `self: @T` call | `(*deref(@s)).f` |
| `s.f = v`, `s.f op= v`, `s.f[i] = v`, `@&s.f`, a `:&` argument, a mutating `self` call | `(*deref_mut(@&s)).f` |

- **A read is a read through a reference.** By value it's a copy, and for a move-only
  field it's "cannot move out of a reference" (§13.2).
- **A mutable use needs `s` to be mutable**, as `@&s` does.
- **`s.f op= v` evaluates `s` once** and calls `deref_mut` once (AGAST #2529).
- **For §13.5, a step through the trait is a path step `*`.** Two `*` steps on one root
  are the same step, and the paths are compared on after them, so `@b.a` beside
  `b.k = 2` is fine and beside `b.a[0] = 2` is refused. A `*` step overlaps every own
  field of the root, since writing one (`b.ptr = q`) may re-aim it.

`Box<T>` implements both (ritzlib/box.ritz). Here a user wrapper keeps its `T`
inline:

```ritz
struct Point
    x: i32
    y: i32

impl Point
    fn bump(self: @&Point)
        self.x += 1

struct Tagged<T>
    tag: i32
    value: T

impl<T> Deref for Tagged<T>
    fn deref(self: @Tagged<T>) -> @T
        @self.value

impl<T> DerefMut for Tagged<T>
    fn deref_mut(self: @&Tagged<T>) -> @&T
        @&self.value

fn main() -> i32
    var t: Tagged<Point>
    t.tag = 7                   # Tagged's own field
    t.x = 1                     # deref_mut
    t.y += 2                    # deref_mut, once
    t.bump()                    # Point's method, through deref_mut
    let p: @i32 = @t.y          # deref
    t.x + *p + t.tag - 11       # 2 + 2 + 7 - 11
```

The errors are located at the field name. A struct with no such field and no `Deref`:

```ritz expect-error="`Wrap<Point>` has no field `x`: it points at one: `w.ptr.x`, or implement `Deref`"
struct Point
    x: i32

struct Wrap<T>
    ptr: *T

fn main() -> i32
    var p: Point
    var w: Wrap<Point>
    w.ptr = @p
    w.x
```

A struct with `Deref`, where neither it nor its target has the field:

```ritz expect-error="neither `Tagged<Point>` nor `Point` has a field `z`"
struct Point
    x: i32

struct Tagged<T>
    tag: i32
    value: T

impl<T> Deref for Tagged<T>
    fn deref(self: @Tagged<T>) -> @T
        @self.value

fn main() -> i32
    var t: Tagged<Point>
    t.z
```

A mutable use through a struct with only `Deref`:

```ritz expect-error="`t.x = …` needs `DerefMut`, and `Tagged<Point>` implements only `Deref`"
struct Point
    x: i32

struct Tagged<T>
    tag: i32
    value: T

impl<T> Deref for Tagged<T>
    fn deref(self: @Tagged<T>) -> @T
        @self.value

fn main() -> i32
    var t: Tagged<Point>
    t.x = 1
    0
```

### 7.8 Array Indexing

```ritz body
var arr: [4]i32
arr[0] = 7              # Index assignment
let v = arr[0]          # Index access
```

`[]` sees through one level. `p[i]` means `(*p)[i]` when `p` is a `*T`, `@T` or `@&T`
and `T` is a Vec, Span or String, and `(*p)[i]` is the same place. An element is a
place in every position: read, store, `+=`, `@`, `@&` and `.f`. Read by value, it's a
read through a reference: a copy, or for a move-only element "cannot move out of a
reference" (§13.2), as `p[i].f` and a by-value `self` on `p[i]` are. A Vec has no
`Drop`, so a `Vec<Vec<i32>>`'s element is a copy.

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

An array behind a pointer is the same. `p[i]` on a `*[N]T`, `@[N]T` or `@&[N]T` is
element `i` of the array, at stride `T`, in every position, and by value it's a
copy. So for a pointer to an array, `p[i]` is not `*(p + i)`: `p + i` steps by the
pointee, a whole `[N]T`, and is how to walk rows. On an `@[N]T` or `@&[N]T` the
row walk is the only arithmetic a reference allows (§7.1, LARB R16, R18).

```ritz
struct Point
    x: i32
    y: i64

fn bump(p: *[3]i32, i: i64)
    p[i] += 1
    let q: *i32 = @p[2]
    *q = 9

fn shift(p: @&[3]Point) -> i32
    p[1].x = 7
    let s: Point = p[1]
    s.x

fn second_row(p: *[3]i32) -> i32
    let r = p + 1
    r[0]

fn main() -> i32
    var g: [2][3]i32
    g[0][1] = 0
    g[1][0] = 4
    bump(@g[0], 1)
    var pts: [3]Point
    shift(@&pts) + second_row(@g[0]) + g[0][1] + g[0][2] - 21
```

The element is a `T`, so a whole `[N]T` doesn't fit it. `*p = a` stores the array.

```ritz expect-error="`p[i]` is one element of the array behind `p`"
fn put(p: *[3]i32)
    var b: [3]i32 = [1, 2, 3]
    p[1] = b

fn main() -> i32
    var a: [3]i32
    put(@a)
    0
```

`*p` is a place, so `(*p)[i]` is element `i` of the array in every position, and
means exactly `p[i]` (LARB R9). It's the only spelling one pointer level further
out: for `pp: **[3]i32` or `q: @*[3]i32` it's `(*pp)[i]` and `(*q)[i]`, since
`pp[i]` is a raw buffer of `*[3]i32` and `q[i]` a located error (a reference is one
value). The same holds one level out from a Vec, Span or String: `(*q)[i]` for
`q: **Vec<T>` or `@*Vec<T>`.

```ritz
import ritzlib.gvec

fn fill(p: *[3]i32)
    (*p)[0] = 1
    (*p)[1] += 2
    let e: *i32 = @(*p)[2]
    *e = 3

fn second(q: @*[3]i32) -> i32
    (*q)[1]

fn last(q: **Vec<i32>) -> i32
    (*q)[2]

fn main() -> i32
    var a: [3]i32 = [0, 0, 0]
    fill(@a)
    var p: *[3]i32 = @a
    var v: Vec<i32> = vec_new<i32>()
    v.push(4)
    v.push(5)
    v.push(6)
    var pv: *Vec<i32> = @v
    second(@p) + last(@pv) + a[0] + a[2] - 12
```

The base can be any expression of that type, not only a name: a field, a global or a
call's result. It's evaluated once each time it's used.

```ritz
struct Grid
    row: @&[3]i32

var cursor: *[3]i32 = null

fn pick(p: *[3]i32) -> *[3]i32
    p

fn main() -> i32
    var a: [3]i32 = [10, 20, 30]
    var g: Grid
    g.row = @&a
    g.row[0] = 1
    cursor = @a
    cursor[1] += 2
    pick(@a)[2] = 3
    a[0] + a[1] + a[2] - 26
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

#### Indexing a struct

*Ruled by LARB on 2026-11-12 (AGAST #2803), implemented by AGAST #1635.*

Arrays, pointers, Vec, Span and String index as described above, and stay built in. Any
other struct opts into `[]` by implementing up to three traits. Like `Drop`, the
compiler knows these traits by name. Their methods are resolved statically from the
concrete type (§12.2), so they need no trait bounds and no dynamic dispatch. An impl
chooses its key type `K` and element type `V`:

```ritz
struct Cell
    v: i32

struct M
    cells: [4]Cell

impl Index for M                                # m[k] read: a shared place
    fn index(self: @M, key: i64) -> @Cell
        @self.cells[key]
impl IndexMut for M                             # m[k] as a mutable place
    fn index_mut(self: @&M, key: i64) -> @&Cell
        @&self.cells[key]
impl IndexSet for M                             # m[k] = v, which may insert
    fn index_set(self: @&M, key: i64, value: Cell)
        self.cells[key] = value

fn main() -> i32
    var m: M
    m[0] = Cell { v: 2 }                        # index_set
    m[1].v = 3                                  # index_mut
    m[0].v + m[1].v - 5                         # index
```

Here `K` is `i64` and `V` is `Cell`; an impl chooses its own.

`m[k]` is a place, like a Vec element, and each position uses one method:

| Use | Means |
|---|---|
| `m[k]` read by value, `m[k].f`, `@m[k]`, `for x in m[k]` | `*index(@m, k)` |
| `@&m[k]`, `m[k].f = x`, `m[k] += x`, a `:&` argument, a mutating `self` call | `*index_mut(@&m, k)` |
| `m[k] = v` | `index_set(@&m, k, v)`, or `*index_mut(@&m, k) = v` without `IndexSet` |

- **A read is a read through a reference.** `m[k]` by value is a copy, and for a
  move-only `V` it's "cannot move out of a reference" (§13.2).
- **A missing key is the impl's to handle, and `index` and `index_mut` must not return
  for one.** A reference can't be empty, so ritzlib's maps end the program with a
  message. To test for a key, call a method such as `contains` or one that returns
  `Option`. Only `index_set` adds keys.
- **`m[k] op= x` evaluates `m`'s place and `k` once** and calls `index_mut` once
  (AGAST #2529). It never reads through `index` and then calls `index_set`.
- **The key is an ordinary argument**, so the rules for any argument apply and nothing is
  converted implicitly. A literal key fits `K` as a literal argument would. An `i32`
  variable doesn't fit an `i64` key; write `k as i64`.
- **`[]` sees through one level.** `p[k]` on an `@M`, `@&M` or `*M` is `(*p)[k]`, and
  writing needs `IndexMut` or `IndexSet` and a mutable `p`, as above.
- **For §13.5, `m[k]` is an index step on `m`.** It overlaps every other `m[j]` and `m`
  itself, so `let r = @m[1]` followed by `m[2] = 5` or `m[2].f = 5` is refused (R11a).
- **The built-in types can't opt in.** An `impl Index` for an array, pointer, Vec, Span
  or String is an error, so `[]` on those types keeps one meaning.

```ritz
import ritzlib.hashmap

fn main() -> i32
    var m: HashMapI64 = hashmap_i64_new()
    m[1] = 10                       # index_set inserts
    m[1] += 5                       # index_mut, m and 1 evaluated once
    let p: @i64 = @m[1]             # index
    let v: i64 = *p - 15            # 0
    v as i32
```

Indexing a struct that doesn't implement the trait a use needs is an error, located at
the `[`:

```ritz expect-error="`Point` can't be indexed: it doesn't implement `Index` (§7.8)"
struct Point
    x: i32

fn main() -> i32
    var p: Point
    p[0]
```

`StrView` isn't one of the built-ins, so `s[i]` on one is the same error (read a byte
with `s.ptr[i]`):

```ritz expect-error="`StrView` can't be indexed: it doesn't implement `Index` (§7.8)"
fn count_spaces(s: StrView) -> i64
    var n: i64 = 0
    for i in 0..s.len
        if s[i] == ' '
            n += 1
    n

fn main() -> i32
    count_spaces("a b c") as i32
```

```ritz expect-error="`m[k] = v` needs `IndexSet` or `IndexMut`, and `Lookup` implements only `Index`"
struct Lookup
    n: [2]i64

impl Index for Lookup
    fn index(self: @Lookup, key: i64) -> @i64
        @self.n[key]

fn main() -> i32
    var m: Lookup
    m[0] = 1
    0
```

```ritz expect-error="`@&m[k]` needs `IndexMut`, and `Lookup` implements only `Index` and `IndexSet`"
struct Lookup
    n: [2]i64

impl Index for Lookup
    fn index(self: @Lookup, key: i64) -> @i64
        @self.n[key]

impl IndexSet for Lookup
    fn index_set(self: @&Lookup, key: i64, value: i64)
        self.n[key] = value

fn main() -> i32
    var m: Lookup
    let r: @&i64 = @&m[0]
    0
```

The other mutable uses name themselves the same way (`` `m[k] op= x` ``,
`` `m[k].f = x` ``), and an impl for a built-in type is refused at its name:

```ritz expect-error="`String` is indexed by the language: it can't implement `Index` (§7.8)"
import ritzlib.string

impl Index for String
    fn index(self: @String, key: i64) -> @u8
        @self.data.data[key]

fn main() -> i32
    0
```

`HashMapI64` implements all three in `ritzlib.hashmap`, at `K` = `V` = `i64`. Its
`index` and `index_mut` end the program on a missing key (status 101, with
`HashMapI64: key not found: <k>` on stderr), and `index_set` is
`hashmap_i64_insert`. A generic `HashMap<K, V>` (AGAST #1858) implements them with
`impl<K, V> Index for HashMap<K, V>`, the same way `ritzlib.box` writes
`impl<T> Drop for Box<T>`.

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
- for a `bool`, both `true` and `false`.

An integer or `StrView` scrutinee needs a catch-all. A guarded arm never counts
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

Arms are tried top to bottom, and the first that matches wins. Every arm must
also be reachable: an arm that no value can reach is a compile error at that
arm, naming the line of the arm that covers it. An arm is unreachable when it
comes after:

- an unguarded catch-all, `_` or a binding;
- an arm with the same literal or the same `const` value (`K =>` then `5 =>`,
  where `K` is 5);
- an arm for the same variant, whatever its payload binds; or
- arms that already cover the scrutinee, so a `_` after every variant, or after
  `true` and `false`, is an error too.

A guarded arm covers nothing, as for coverage, but it can itself be
unreachable. Since no arm hides behind another, reordering the arms of a match
that compiles never changes which arm a value takes.

```ritz expect-error="unreachable match arm: the arm at line 3 covers it"
fn f(n: i64) -> i64
    match n
        _ => 1
        5 => 2

fn main() -> i32
    f(5) as i32
```

A misspelt `const` is a binding, so it takes every value, and the arm after it
is the one in error:

```ritz expect-error="unreachable match arm: the arm at line 5 covers it"
const KK: i64 = 1

fn f(n: i64) -> i64
    match n
        KX => 1
        KK => 2

fn main() -> i32
    f(1) as i32
```

A repeated variant names the first arm for it, and a catch-all after every
variant names the arm that completed the coverage:

```ritz expect-error="unreachable match arm: the arm at line 5 covers it"
import ritzlib.option

fn f(o: Option<i64>) -> i64
    match o
        Some(v) => v
        None => 0
        Some(w) => w

fn main() -> i32
    f(None) as i32
```

```ritz expect-error="unreachable match arm: the arm at line 10 covers it"
enum Color
    Red
    Green
    Blue

fn f(c: Color) -> i32
    match c
        Red => 1
        Green => 2
        Blue => 3
        _ => 4

fn main() -> i32
    f(Color.Red)
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

A string literal pattern compares a `StrView` scrutinee, byte for byte: the
lengths are equal and so is every byte (AGAST #1876). Like an integer, a
`StrView` needs a catch-all, and a repeated literal is an unreachable arm
(§8.1). A name in an arm always binds the `StrView`, since an integer `const`
compares only an integer.

```ritz
enum Tag
    Html
    Body
    Unknown

fn tag_from_name(name: StrView) -> Tag
    match name
        "html" => Tag.Html
        "body" => Tag.Body
        _ => Tag.Unknown

fn main() -> i32
    match tag_from_name("body")
        Tag.Body => 0
        _ => 1
```

Only a `StrView` takes a string pattern. A `*u8` or a `String` scrutinee is
a compile error at the pattern: convert it first, with `strview_from_cstr(p)`
or `string_as_view(@s)`. A `StrView` takes no integer, `bool` or variant
pattern.

```ritz expect-error="a string pattern needs a StrView scrutinee"
fn f(p: *u8) -> i32
    match p
        "html" => 1
        _ => 0

fn main() -> i32
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

A variant's payload pattern is a name or `_`. A nested variant pattern
(`Ok(Simple(x))`) or a literal payload pattern (`Some(0)`) is an error: match
the inner value in its own `match`. The arm is chosen by the variant alone, so
the error is at the inner pattern (LARB R76). A type there is no pattern
either (§3.8). A name only binds, so one named like a `const`, a global or a
variant is the binder error of §4.3, whatever the payload's type.

```ritz expect-error="a variant's payload pattern is a name or `_`: match the inner value in its own `match`"
fn f(o: Option<Option<i32>>) -> i32
    match o
        Some(Some(x)) => x
        _ => 0

fn main() -> i32
    f(Some(Some(5)))
```

Bind the payload and match it, or test it, in the arm body:

```ritz
fn f(o: Option<Option<i32>>) -> i32
    match o
        Some(inner) =>
            match inner
                Some(x) => x
                None => 0
        None => 0

fn main() -> i32
    f(Some(Some(5)))
```

A variant pattern with a field list lists every field of its variant, in
order: `Two(a, b)` on `Two(i32, i32)`, `_` for one it doesn't bind. Any other
count, including a field on a variant that has none, is a compile error at the
pattern naming both counts (AGAST #2408), reported before a missing arm. A bare
`Two` tests the variant alone.

```ritz expect-error="variant 'None' has 0 fields, but this pattern lists 1"
fn f(o: Option<i32>) -> i32
    match o
        Some(v) => v
        None(k) => 0

fn main() -> i32
    f(Some(5))
```

A variant declared with named fields (§10.1) may instead be matched by name:
`SetViewport { height, width }` binds each field to a local of its own name.
Every field is named exactly once, in any order (AGAST #4187); there is no
`..` rest pattern yet. A named pattern on a variant declared without field
names, a field the variant doesn't declare, one named twice and one left out
are each a compile error at the pattern. The named literal
`SetViewport { width: 640, height: 480 }` builds the variant under the same
rule (§10.3).

```ritz expect-error="missing field `height` of variant `SetViewport`"
enum Msg
    Stop
    SetViewport
        width: i32
        height: i32

fn f(m: Msg) -> i32
    match m
        SetViewport { width } => width
        Stop => 0

fn main() -> i32
    f(Msg.Stop)
```

A variant pattern, qualified (`E.V`, `E.V(x)`) or not (`V(x)`), names a
variant of the scrutinee's enum. One of any other enum is a compile error at
the pattern, naming the enum as declared (AGAST #2431); a missing arm is
reported first. A bare `V` of another enum is a binding, and so the binder
error of §4.3.

```ritz expect-error="Unknown variant Ok in enum Option"
fn f(o: Option<i32>) -> i32
    match o
        Ok(v) => 1
        _ => 2

fn main() -> i32
    f(Some(5))
```

A variant pattern needs an enum scrutinee. On an integer or a `bool` it is a
compile error at the pattern (AGAST #2409), as `true` and `false` are on an
integer: no value of the scrutinee is a variant, so the arm could never run.

```ritz expect-error="a variant pattern needs an enum scrutinee"
fn f(n: i64) -> i64
    match n
        Some(v) => v
        _ => 2

fn main() -> i32
    0
```

#### Constant Patterns

A bare identifier pattern that names an integer `const` (declared in the
module or imported) compares an integer scrutinee with the constant. Any other
identifier binds the scrutinee to a new name, which also makes it a
catch-all (AGAST #1880), and like any binding it can't take the name of a
const, global or variant (§4.3). So a non-integer const, or an integer const
against a scrutinee that isn't an integer, is that error.

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
`match`. Qualified by its module (`instructions.POP =>` after `import
hinting.instructions`), an integer const compares the same way, as
`instructions.POP` reads in an expression; it is not a variant pattern. Constant patterns compare integers only: against an enum
scrutinee, a bare name is a variant (§10.2).

```ritz expect-error="a local can't take the name of a const: 'NAME' — rename the local"
const NAME: StrView = "ritz"

fn f(n: i32) -> i32
    match n
        0 => 1
        NAME => 2

fn main() -> i32
    f(5)
```

#### Wildcard Pattern

`_` matches anything and binds nothing. `pass` is a valid arm body for arms
that should do nothing:

```ritz body
match 3
    0 => pass
    _ => pass
```

A `pass` arm has no value, so it can't be an arm of a `match` whose value is
used (§6.1). Write the value the arm should give:

```ritz body expect-error="`pass` has no value, so it can't be used where a value is wanted"
let n = 3
let c: i64 = match n
    0 => 5
    _ => pass
```

---

## 9. Structs

### 9.1 Definition

A field's type is a type in scope: `String` comes from `ritzlib.string`, and a
type name that names nothing is "unknown type `Nope`" at the name (AGAST #3932).

```ritz
import ritzlib.string

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

A literal is the only way to make a struct value. Nothing converts to a struct,
even one with a single field: `f(1)` for `fn f(s: S)` with `struct S { x: i32 }`
is "argument 1 of `f` has the wrong type", and you write `f(S { x: 1 })` (LARB
R47, AGAST #3336; ritz0 wraps the integer today).

A field the literal leaves out is zero, and so is every element and field
inside it: `S { count: 3 }` for `struct S { a: [64]i64, count: i32 }` has
every `a[i] == 0` (AGAST #1749).

A generic struct's literal may leave out its type arguments, as a bare enum
constructor does (§11.3). They come from the slot the literal fills: a typed
`let` or `var`, a parameter, a field, the fn's return type. With no slot (an
untyped `let`, a `match` scrutinee), they come from the field values, by §4.4's
rule for a generic call. The slot wins: in a `Box2<u8>` slot, `Box2 { v: 1 }`
is a `Box2<u8>` and its `1` is a `u8`, and a field value of another type is
that field's type error. A type parameter that neither the slot nor any field
binds is an error at the literal. Writing the arguments out, `Box2<u8> { .. }`,
is always allowed (LARB R51, AGAST #3314):

```ritz
struct Box2<T>
    v: T

fn wrap(x: u8) -> Box2<u8>
    Box2 { v: x }                  # the return type: Box2<u8>

fn main() -> i32
    let x: u16 = 7
    let a = Box2 { v: x }          # the field: Box2<u16>
    let b = Box2 { v: 1 }          # the literal rule: Box2<i64>, as Present(1)
    let c: Box2<u8> = Box2 { v: 1 }   # the slot: Box2<u8>
    0
```

A field whose declared type is fully known is a slot even in an args-less
literal, as a generic fn's concrete parameter is for its argument: fully known
means it names none of the outer struct's parameters (or the outer literal has
its arguments, from its slot or written out); a field naming one still being
inferred, even in part (`Pair<u8, A>`), is no slot, and its value infers on its
own and then binds the outer parameter (LARB R51a, AGAST #3430):

```ritz
struct Box2<T>
    v: T

struct Tagged<T>
    n: i32

struct W<A>
    a: A
    t: Tagged<u8>
    b: Box2<A>

fn g<U>(x: U, t: Tagged<u8>) -> i32
    t.n

fn main() -> i32
    let x: u16 = 2
    let w = W { a: x, t: Tagged { n: 4 }, b: Box2 { v: x } }   # t: Tagged<u8>; W<u16>
    g(1, Tagged { n: 3 }) + w.t.n           # the param: Tagged<u8>
```

```ritz expect-error="can't infer `T` for `Tagged`: write its type arguments, `Tagged<T> { .. }`"
struct Tagged<T>
    n: i32

fn main() -> i32
    let t = Tagged { n: 1 }    # error: can't infer `T` for `Tagged`: write its type arguments, `Tagged<T> { .. }`
    0
```

Unlike a bare constructor, an untyped `let` doesn't look at the fn's return
type: it has no slot, so its literal takes the field values' types. ritz0
(#3407) and ritz1 (#3408) implement this; before them, each refused an
args-less literal (#3311).

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

Method syntax reaches only methods: `x.m(...)` on a user type calls an `m`
declared in an `impl` for that type, or in a trait impl for it. A free function
whose name happens to be `<type>_<m>` is not a method. Without an `m`, the
call is a compile error located at the method name (AGAST #3244). The ritzlib
types in the UFCS table (`String`, `GrowBuf`, `Buffer`, and the
`Vec`/`Span`/`Option`/`Result`/`Box` helpers) are the exception: `s.len()` on
a `String` calls `string_len(@s)`, until AGAST #3252 decides the table's future.

```ritz expect-error="no method `cmp` on `Foo`: declare it in `impl Foo`, or call `foo_cmp(a, b)`"
struct Foo
    x: i32

fn foo_cmp(a: Foo, b: Foo) -> i32
    a.x - b.x

fn main() -> i32
    let a = Foo { x: 1 }
    let b = Foo { x: 2 }
    a.cmp(b)
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
`String::from(...)` and `sys::write(...)` are each a located error:

```ritz body expect-error="`Color::Red`: `::` was removed in RERITZ"
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
against an `S` is `S.B`. An enum reached twice through an import cycle is
still one enum.

A local or parameter can't be named like a variant (§4.3), so a bare `B` is
never a local. Until AGAST #2407 the local won; a name with two meanings is
now an error at the binding:

```ritz expect-error="a local can't take the name of a variant: 'B' — rename the local"
enum S
    A
    B

fn main() -> i32
    let B: i32 = 9
    B
```

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

Fields bind **positionally**, for tuple and named-field variants alike:

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

A named-field variant may also be matched and built **by name** (AGAST
#4187). Every field is named exactly once, in any order; the names map to
positions, so `SetViewport { height: 480, width: 640 }` is
`SetViewport(640, 480)`, its values evaluated in field order, and
`SetViewport { height, width }` binds what `SetViewport(width, height)` does.
Qualified patterns (`Msg.SetViewport { width, height }`, §8.2) and literals
(`Msg.SetViewport { width: 640, height: 480 }`, AGAST #4275) follow the same
rule:

```ritz
enum Msg
    Stop
    SetViewport
        width: i32
        height: i32

fn area(m: Msg) -> i32
    match m
        Msg.SetViewport { height, width } => width * height
        Stop => 0

fn main() -> i32
    let m = SetViewport { height: 480, width: 640 }
    let q = Msg.SetViewport { width: 2, height: 3 }
    if area(m) == 307200 and area(q) == 6 then 0 else 1
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

**`e as E`**, with `e` already an `E`, is `e` itself, for every enum,
including one that carries data (AGAST #3041):

```ritz
enum B
    V
    Q(i32)

fn main() -> i32
    let b: B = B.Q(4)
    match b as B
        V => 1
        Q(x) => x
```

**`n as E`**, an integer to an enum, is an error for every enum, fieldless,
with a representation type or carrying data, located at the `as`: an
integer may name no variant (LARB R19, AGAST #3040). `match` on the integer
instead, or use `E.from(n)` below for an enum with a representation type:

```ritz expect-error="an integer can't be converted to enum `Dir` with `as`: it may name no variant; `match` on it"
enum Dir
    North
    South

fn main() -> i32
    let n: i32 = 1
    let d: Dir = n as Dir
    0
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
lowercase identifier: by naming convention (`docs/STANDARD.md` S-NAME-1, S-NAME-2: types are
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

A bare constructor builds the instance its slot names: a typed `let`'s, a
parameter's, a field's, the fn's return type. An untyped `let` or `var` has no
slot. It takes the fn's return type when that is an instance of the variant's
enum. Otherwise it takes the instance its payload binds, by §4.4's rule for a
generic call: `Present(5)` is a `Maybe<i64>`, and `Present(x)` with `x: u8`
is a `Maybe<u8>` (AGAST #2927). A `match` scrutinee has no slot either, and
isn't the fn's value: `match Present(5)` matches a `Maybe<i64>` (AGAST #2437):

```ritz
enum Maybe<T>
    Present(T)
    Absent

fn main() -> i32
    let a = Present(5)               # Maybe<i64>
    let b: Maybe<i64> = Absent       # nothing binds T: the binding says it
    match a
        Present(v) => v as i32 - 5
        Absent => 1
```

A type parameter the payload leaves unbound is an error at the constructor.
That includes every parameter of a unit variant's enum:

```ritz expect-error="can't infer `T` for `Absent`: give the binding a type"
enum Maybe<T>
    Present(T)
    Absent

fn main() -> i32
    let b = Absent
    0
```

A method without `self` on a generic type's impl, `Type.m(..)` (§5.4), spells
no type argument either. It takes the instance of the slot the call fills, as
a bare constructor does: a typed `let`'s, a parameter's, the fn's return type.
That holds for a generic struct's impl too. Its arguments don't supply one, so
with no such slot, or a slot of another type, it's an error at the call
(AGAST #2185; ritz1 is AGAST #3309):

```ritz
enum Maybe<T>
    Present(T)
    Absent

impl<T> Maybe<T>
    fn of(x: T) -> Maybe<T>
        Present(x)

fn main() -> i32
    let a: Maybe<i32> = Maybe.of(5)  # Maybe<i32>.of
    match a
        Present(v) => v - 5
        Absent => 1
```

```ritz expect-error="can't infer the type arguments of `Maybe` for `Maybe.of`: give the binding a type"
enum Maybe<T>
    Present(T)
    Absent

impl<T> Maybe<T>
    fn of(x: T) -> Maybe<T>
        Present(x)

fn main() -> i32
    let a = Maybe.of(5)
    0
```

### 11.4 Monomorphization

Generics are monomorphized at compile time; each instantiation generates
specialized code. *Every* type argument participates in name mangling, joined
by `_`: `Result<i32, StrView>` mangles to `Result$i32_StrView`, and
`Result<i32, i32>` to `Result$i32_i32`. Only the first `$` survives: a
nested generic argument is joined the same way, so `Box<Pair<i32, u8>>` is
`Box$Pair_i32_u8` and `first<i64, Vec<i64>>` is `first$i64_Vec_i64`. You can
read the mangled names straight out of the emitted IR:

```bash
RITZ_PATH=$PWD python3 ritz0/ritz0.py prog.ritz -o prog.ll --no-runtime
grep -o 'Result\$[A-Za-z0-9_]*' prog.ll | sort -u
```

This document claimed until 2026-09-12 that only the first type argument
mangled — which would have made `Result<i32, StrView>` and `Result<i32, i64>`
collide. They do not.

A method of a generic inherent impl (`impl<T> Cell<T>`) is specialised, and
type- and move-checked, only at the instances a call names it at, as a
generic fn is: `x.m()` on that instance, `T.m()` filling a slot of it, or a
call from another method so specialised. A method nothing calls at
`Vec<Res>` is never checked there, so it may do what only some `T` allow
(move a `T` out of a reference, say), and its callees are never linked. A
trait impl (`impl<T> Drop for Box<T>`) is specialised whole for every
instance: the compiler calls its methods itself. Below, `wrap` at `Cell<i32>`
names `Cell<Cell<i32>>`, whose own `wrap` nobody calls (AGAST #3617):

```ritz
struct Cell<T>
    v: T

impl<T> Cell<T>
    fn wrap(self: @Cell<T>) -> Cell<Cell<T>>
        Cell<Cell<T>> { v: Cell<T> { v: self.v } }

fn main() -> i32
    let c = Cell<i32> { v: 9 }
    c.wrap().v.v - 9
```

### 11.5 Trait Bounds

A type parameter of a fn, struct, enum or impl may name the traits it needs:
`<T: Area>`, `<K: Hash + Eq>`. There is no `where` clause. A bound is a check,
made when the generic is instantiated: each type argument needs an impl of each
trait, exact (`impl Area for Sq`) or through a generic impl (`impl<T> Drop for
Box<T>` covers every `Box<..>`, §12.2).

```ritz
trait Area
    fn area(self: @Self) -> i64

struct Sq
    s: i64

impl Area for Sq
    fn area(self: @Sq) -> i64
        self.s * self.s

fn total<T: Area>(a: @T, b: @T) -> i64
    a.area() + b.area()

fn main() -> i32
    let a = Sq { s: 2 }
    let b = Sq { s: 3 }
    (total(@a, @b) - 13) as i32
```

A type argument without the impl is an error at the type argument, or at the
call when the argument is inferred:

```ritz expect-error=".ritz:9:5: `Nope` doesn't implement `Area`, which `T` of `total` requires"
trait Area
    fn area(self: @Self) -> i64
struct Nope
    x: i64
fn total<T: Area>(a: @T) -> i64
    a.area()
fn main() -> i32
    let n = Nope { x: 1 }
    total(@n) as i32
```

A bound naming no trait is an error at the bound, used or not: "unknown trait
`Nonesuch` in the bound on `T`". A bound doesn't change how a method on `T` is
found: that happens after substitution (§11.4), so `a.area()` on an unbounded
`T` compiles too, and fails at an instance whose type has no `area` (LARB R55).

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
shape and its methods are emitted, but there is no dynamic dispatch and no `dyn
Trait`. Methods are resolved statically from the receiver's concrete type. A
generic parameter's trait bound is a check at instantiation (§11.5).

An `impl` targets a struct or enum declared in Ritz source. A primitive is a
built-in type, closed like `Span` (LARB R26), so `impl u8` and `impl Speak for
i32` are errors at the type: "`i32` is a built-in type; it can't have an
`impl`" (LARB R36, AGAST #3288). Trait impls on primitives come back with
trait bounds (#1621) and cross-module impls (#3256).

Where an `impl` lives (LARB R65, AGAST #3493). An inherent `impl T` is in the
file that declares `T`. A trait impl is in the type's file or the trait's file;
a trait the compiler knows (`Drop`, `Index`…) counts as the type's file.
Anywhere else it is an error at the impl's type name: "`Foo` is declared in
a.ritz: its `impl` must be there (§12.2)". All files share one namespace
(§15.3), so nothing could say which file's method a call means, and adding an
import could change it.

An impl covers every instantiation of its type: `impl<T> G<T>`, never
`impl G<u8>`, and not `impl<T> P<T, T>` or `impl<K> P<K, i32>` either. Each
type argument is one of the impl's own parameters, each used once:

```ritz expect-error=".ritz:4:6: an impl covers every instantiation of `G`: write `impl<T> G<T>`"
struct G<T>
    v: T

impl G<u8>
    fn get(self: @G<u8>) -> u8
        self.v
```

A generic impl declares its parameters (LARB R81, AGAST #1390). In
`impl Box<T>`, written without `<T>`, `T` is an ordinary type name; if no type
`T` exists, it is an error at the `T`: "unknown type `T`: a generic impl
declares it, `impl<T> Box<T>`" (ritz0; ritz1's half is #4002).

`dyn` stays a reserved keyword (§2.4). Every use of it, in any type position
or after `as`, is an error located at the `dyn` token, from ritz0, ritz1 and
ritz1_selfhosted alike (AGAST #1620; runtime polymorphism is AGAST #3251):

```ritz expect-error=".ritz:4:13: `dyn Trait` is not supported (AGAST #1620)"
trait Speak
    fn say(self: @Self) -> i32

fn loud(s: @dyn Speak) -> i32
    return s.say()
```

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

An array fill `[v; n]` moves `v` into the array and copies it into each of the
`n` elements. For a move-only `v` those copies would be `n` owners of one value,
each dropping it, so a fill of a move-only value has a count of at most 1. That
holds whether `v` is a binding, a field or a temporary such as `[make(); 2]`,
and in a generic body at each move-only `T` it's instantiated with. `[r; 1]`
moves `r` into the one element. To fill more, build each element separately:
`[make(), make()]`.

```ritz expect-error="`[v; n]` copies `v` into every element: a move-only value fills one, `[v; 1]`"
struct Resource
    handle: i32

impl Drop for Resource
    fn drop(self: @&Resource)
        self.handle = 0

fn main() -> i32
    let r = Resource { handle: 3 }
    let a: [2]Resource = [r; 2]     # error: two owners of r
    0
```

An array owns its elements and drops every one of them: it can't track one that
moved out. So using a move-only `a[i]`, or a move-only field of one such as
`a[i].r`, by value is an error, whether `a` is a local, a by-value parameter, a
field or a call's result. Reading a copy field of an element, borrowing it with
`@a[i]`, calling a method that lends it, `match`ing it and storing into it are
fine. A generic body is judged at each type it's instantiated with, as for a
reference below.

```ritz expect-error="cannot move out of an array element: the array still drops it; borrow it with `@a[i]`"
struct Resource
    handle: i32

impl Drop for Resource
    fn drop(self: @&Resource)
        self.handle = 0

fn consume(r: Resource) -> i32
    r.handle

fn main() -> i32
    var a: [2]Resource = [Resource { handle: 3 }, Resource { handle: 4 }]
    consume(a[0])                   # error: `a` still drops a[0]
```

A global `var` is never dropped, and nothing can track what moved out of it,
since any function may read it. So a move-only value can't be moved out of a
global, or out of a field of one: `var x = G.t` is an error at `G.t`, "cannot
move out of global `G`: borrow it with `@G.t`" (LARB R34, AGAST #3280). Reads
of copyable values, borrows and stores into the global are unaffected. Both
compilers refuse it (ritz0 since #3366, ritz1 since #3367).

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

A call's by-value result is a temporary, not a place (LARB R9, AGAST #2518). It
can be read: `mk().x`, `mk().n[1]`, and a method whose `self` is `@T` or by value.
A store into it would be lost with it, so `mk().x = 1`, `mk().n[1] = 3`,
`mk().x += 1`, and a method whose `self` is `@&T` or `:& T` (`mk().bump()`, the
same store by its auto-borrow), are errors. A call returning `*T` gives the place it
points at, which may be written. An element of a call's array result reads like a
field of a call's struct result (AGAST #3234): `mka()[1].x`, `mka()[1].get()` and
`mv().a[1].get()` read it, and `mka()[1].x = 3` or a `self: @&T` method on it is
the same error.

```ritz expect-error="a store into a call's temporary is lost: bind the call to a local first"
struct Counter
    n: i32

fn make() -> Counter
    Counter { n: 1 }

fn main() -> i32
    make().n = 2
    0
```

`@` or `@&` of a temporary, or of a field or element in it, is allowed in one
place: passed straight to a call as an argument, `look(@make())`. The temporary
lives until that call returns and is dropped then (§13.6), so the reference never
outlives it. Anywhere else (a `let`, a `return`, a field, a struct literal) the
reference would outlive the statement, so it's an error: bind the call to a local
first.

```ritz
struct Counter
    n: i32

fn make() -> Counter
    Counter { n: 1 }

fn look(c: @Counter) -> i32
    c.n

fn main() -> i32
    look(@make()) - 1
```

```ritz expect-error="`@` of a call's temporary outlives it: bind the call to a local first, or pass it straight to a call"
struct Counter
    n: i32

fn make() -> Counter
    Counter { n: 1 }

fn main() -> i32
    let c: @Counter = @make()
    c.n
```

A call whose result is a reference or pointer (`@T`, `@&T`, `*T`, or a struct,
tuple or enum holding one) can't take a lent temporary at all: the temporary is
dropped as the call returns, so the result would point at a dropped value. This
holds even when the result points into a different argument (`find(@make_key(),
@table) -> @Entry`); binding the temporary to a local first is always the fix.

```ritz expect-error="this call returns a reference, and `@make()` lends a temporary that's dropped when the call returns: bind it to a local first"
struct Counter
    n: i32

fn make() -> Counter
    Counter { n: 1 }

fn id(c: @Counter) -> @Counter
    c

fn main() -> i32
    id(@make()).n
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
A `Vec<T>` is too: `@v` (or `@&v`) is a `Span<T>` of its elements, and `v` itself
doesn't fit. Either way the element must be `T` (AGAST #3595).

```ritz expect-error="a value doesn't fit a reference slot: write `@x` to borrow it"
import ritzlib.span

fn total(s: Span<i32>) -> i64
    s.len

fn main() -> i32
    var a: [2]i32 = [1, 2]
    total(a) as i32                 # error: write total(@a)
```

```ritz
import ritzlib.gvec

fn total(s: Span<u8>) -> i64
    s.len

fn main() -> i32
    var a: [2]u8 = [1, 2]
    var v = vec_new<u8>()
    v.push(3)
    (total(@a) + total(@v) - 3) as i32
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

The first rule is checked, on places. A **place** is a root binding followed by
field (`.f`) and index (`[i]`) steps. Two places **overlap** when one's path is a
prefix of the other's: field names must match exactly, and any two indexes count
as equal, since which element an index names isn't known until it runs. Taking
`@&x` while an `@x` is live is an error, and the error names both places:

```ritz body expect-error="cannot borrow `x` as mutable - `x` is already borrowed as immutable"
var x: i32 = 1
let p = @x
let q = @&x
```

A mutable borrow of a place `p` is any of: `@&p`; `p` passed bare to a `:&`
parameter; a method call on `p` that takes `self: @&T` or `self:& T`; and a write
(`p = v`, or a write inside `p` such as `p.f = v` or an array element
`p[i] = v`). Each is an error on any place that overlaps one a binding holds an
`@` of, or one an earlier argument of the same call borrows (LARB rulings R11 and
R11a). The binding holds that loan to the end of the block it's declared in.
`@x` held in a `*T` isn't a borrow, and nor is a `self: *T` receiver.

Moving a place, or a part of it, is refused the same way while an `@` of an
overlapping place is live (LARB R57): what moved would leave the reference behind.

```ritz expect-error="cannot move out of `t` - `t` is already borrowed as immutable"
struct T
    x: i32

impl Drop for T
    fn drop(self: @&T)
        self.x = 0

fn main() -> i32
    let t = T { x: 1 }
    let p = @t
    let w = t
    p.x
```

A `Span<T>` made from a local root is an `@` of that root, for this rule and for
the one below (LARB R57): `v[a..b]` of a Vec or String in a `Span` slot, which is
a view of `v` there rather than a copy (§7.8), and `@x` in a `Span` slot. A slice
of a `Span` views what that Span does, so it lends nothing:

```ritz expect-error="cannot borrow `v` as mutable - `v` is already borrowed as immutable"
import ritzlib.gvec

fn main() -> i32
    var v: Vec<i32> = vec_new<i32>()
    v.push(1)
    let s: Span<i32> = v[0..1]
    v.push(2)                       # error: the push may move what s views
    s[0]
```

Disjoint fields of one root don't overlap, so they're free while the other is
borrowed, and two of them can be lent mutably to one call:

```ritz
struct C
    x: i32
    y: i32

fn swap(a: @&i32, b: @&i32)
    let t: i32 = *a
    *a = *b
    *b = t

fn main() -> i32
    var c = C { x: 1, y: 2 }
    swap(@&c.x, @&c.y)      # x is 2, y is 1
    let p = @c.x
    c.y = 5                 # `c.y` doesn't overlap `c.x`
    c.y - *p
```

Two indexes always overlap, whatever their values:

```ritz body expect-error="cannot assign to `a[_]` - `a[_]` is already borrowed as immutable"
var a: [3]i32 = [1, 2, 3]
let p = @a[1]
a[2] = 5
```

So a push can't move a Vec's buffer out from under a reference to its element:
`let p: @H = @vs[0]` is a loan of `vs[_]`, which overlaps `vs`, so `vs.push(h)`
is refused. A `for` over a place reached through a Vec's element (`for x in
vs[0].a`) holds an `@` of `vs` for its body in the same way (§6.3). A write
through a field or element that's itself overlapped
(`let e = @c.x` then `c.x.k = 2`, or `c.up()`) is refused just the same.

The arguments of one call are live together, so a read of `x` can't sit beside
`@&x` in them. Read it into a binding first:

```ritz expect-error="cannot borrow `x` as immutable - `x` is already borrowed as mutable"
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
- a `Span<T>` of a local root: `@x` or a view `v[a..b]` of a Vec or String, as a
  `Span<T>` (LARB R57);
- a local reference or `Span<T>` binding initialised from one of those, over any
  number of hops;
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

```ritz expect-error="cannot return a reference to local `a`: it ends with the fn"
fn view() -> Span<i32>
    var a: [3]i32 = [1, 2, 3]
    return @a                       # error: a Span of a local array
```

A slice of a `Span` parameter views the caller's storage, so it returns:

```ritz
fn tail(s: Span<i32>) -> Span<i32>
    return s[1..s.len]

fn main() -> i32
    let a: [3]i32 = [1, 2, 3]
    let t = tail(@a)
    t[0]
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

- a reference or a `Span<T>` stored in a field or a global, or a reference in a
  value such as an `Option<@T>`;
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

Storing an array element (`a[i] = v`, `g[i][j] = v`, `h.a[i] = v`) drops the
element's old value in the same order: after `v` and the index have been
evaluated, before `v` is stored (LARB R39, AGAST #3305). That is why an array of
a type with drop glue must be initialised where it's declared (§3.3): every
element always holds a value. An array of any rank is dropped element by element
in index order (`g[0][0]`, `g[0][1]`, … `g[1][0]`), as a rank-1 array is. Both
compilers do all of this (AGAST #3376, #3377).

A store through an `@&T`, a `:&` parameter, or a place reached through one
(`p.t = v`, `p.a[i] = v`, `*p = v`, `h = v` on `h:& T`), drops the old value
in the same order: after `v`, before the store. A mutable borrow always refers
to a live owned value, so there is no flag to consult. A store through a `*T`
is a raw write and drops nothing: a raw pointer may point at uninitialised
memory, as `box_new`'s `*b.ptr = value` into fresh `malloc` does. To replace a
live value through a `*T`, lend it as `@&T` (LARB R58). ritz0 does this
(AGAST #3474); ritz1 is AGAST #3475.

An assignment evaluates its place before its value, whatever the place is: a
binding, a field, an element or a dereference. Every call in the place runs
first, once each, left to right; `v` runs after them. That covers an
`index_mut` or `deref_mut` the place goes through (§7.7, §7.8). It runs after
its own operands, so `g[k()] = v` through `IndexMut` runs `k()`, then
`index_mut`, then `v`. `a[i] = v` evaluates `a`, then `i`, then `v`, and
`g[i][j] = v` evaluates `i` before `j` (LARB R61, AGAST #3482). `f().x = v`
calls `f` once, then evaluates `v`, and so does `*f() = v`. `ps[i()].x = v`
calls `i` once, then evaluates `v` (AGAST #1740). Then any old value drops and
`v` is stored, as above.

`m[k] = v` through `IndexSet` is `index_set(@&m, k, v)`. `v` is one of its
arguments, so the order is `m`, `k`, `v`, then `index_set`.

```ritz
var D: i64 = 0

fn idx(i: i64) -> i64
    D = D * 10 + 7
    return i

fn val(x: i64) -> i64
    D = D * 10 + 8
    return x

fn main() -> i32
    var a: [2]i64 = [0, 0]
    a[idx(1)] = val(5)             # idx, then val: D is 78
    var g: [2][2]i64 = [ [0, 0], [0, 0] ]
    g[idx(0)][idx(1)] = val(5)     # i, then j, then val: D is 78778
    return (D - 78778) as i32      # 0
```

A field of a call's result and a store through a call's pointer go the same
way: the call in the place runs first, once.

```ritz
var D: i64 = 0

struct P
    x: i64

fn at(p: *P) -> *P
    D = D * 10 + 7
    return p

fn cell(p: *i64) -> *i64
    D = D * 10 + 7
    return p

fn val(x: i64) -> i64
    D = D * 10 + 8
    return x

fn main() -> i32
    var p = P { x: 0 }
    at(@p).x = val(5)              # at, then val: D is 78
    var n: i64 = 0
    *cell(@n) = val(6)             # cell, then val: D is 7878
    return (D - 7878 + p.x + n - 11) as i32   # 0
```

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
dropped at the end of the statement that creates it, except one lent straight to
a call, `look(@make())` (§13.3): it is dropped as soon as that call returns, so
`look(@make(1)) + DROPS` already counts it. A `return` drops it
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
(AGAST #2165), and it has no tuple literals yet (AGAST #1526). Like ritz0, ritz1
tracks every movable path of a binding, however many it has (AGAST #2319).
`ritz0/test_ownership_free_count.py` counts the drops for each rule on all
three compilers, with today's gaps marked as expected failures.

### 13.7 Defer

*Ruled by LARB on 2026-11-12 (AGAST #2802, R14); implemented by ritz0, ritz1 and
ritz1_selfhosted (AGAST #1625).*

`defer` schedules a statement to run when the enclosing block exits. It's for cleanup
that has no `Drop` type of its own, such as a raw fd, a lock or a buffer from `alloc`.

```ritz
import ritzlib.sys
import ritzlib.memory
import ritzlib.str

fn read_header(path: *u8, out: *u8) -> i64
    let fd: i32 = sys_open(path, O_RDONLY)
    if fd < 0
        return -1
    defer sys_close(fd)
    let buf: *u8 = malloc(4096)
    defer free(buf)                 # runs before sys_close: LIFO
    let n: i64 = sys_read(fd, buf, 4096)
    if n < 16
        return -1                   # free(buf), then sys_close(fd)
    memcpy(out, buf, 16)
    16                              # 16 is evaluated, then free, then sys_close
```

- **Form.** `defer` is followed by one statement on the same line, or by an indented
  block on the lines below it. The statement is an expression statement, an
  assignment or a compound assignment. Any value it produces is discarded.
- **Scope.** A deferred statement belongs to the innermost block containing the
  `defer`. That covers a function body, an `if` or `else` arm, a `match` arm, and a loop
  body, where it runs at the end of every pass. It never waits for the end of the
  function.
- **Order.** At a block's exit, its deferred statements and its bindings' drops (§13.6)
  run in reverse order of where they appear. A binding declared after a `defer` is
  dropped before that statement runs. One declared before it is still alive, so
  everything a deferred statement can name is alive when it runs.
- **Evaluated at exit.** Nothing is evaluated at the `defer` line. The whole statement,
  operands included, runs at exit, so it sees the values its names hold then. It
  isn't a closure and it doesn't capture anything: it behaves as if it were written
  at each exit. `defer counter = x` followed by `x = 20` stores 20.
- **Every exit runs it,** using the same exits as §13.6's drops:
  - falling off the end of the block, after the block's tail value is evaluated;
  - `return` and `?`, after the return value is evaluated, for every block being
    left, innermost first;
  - `break` and `continue`, for every block left inside the loop, innermost first.

  A `defer` that hasn't been reached registers nothing. Ending the process with
  `sys_exit` runs nothing.
- **Checked as if written at each exit.** Moves, borrows and types are checked as if
  the statement appeared at each exit it runs on. A name moved before one of those
  exits makes the statement an error ("`x` may be moved before the deferred statement
  runs", located at the `defer`). A deferred statement may move a binding: it's the
  binding's last use, so the binding isn't dropped afterwards. A deferred statement
  holds no loan between the `defer` line and the exit.

```ritz expect-error="`x` may be moved before the deferred statement runs"
struct Fd
    n: i32

impl Drop for Fd
    fn drop(self: @&Fd)
        self.n = -1

fn take(f: Fd) -> i32
    f.n

fn main() -> i32
    let x = Fd { n: 3 }
    defer take(x)                   # runs at exit, but x is gone by then
    take(x)
```

These are errors, located at the `defer`:
- a `return`, `?`, `break` or `continue` that would leave the deferred statement.
  A loop wholly inside a deferred block may still `break` out of itself;
- a deferred `let` or `var`, whose binding would die at once;
- a `defer` with no statement after it.

```ritz body expect-error="`return` can't leave a deferred statement"
defer
    return 1
```

```ritz body expect-error="`break` can't leave a deferred statement"
while true
    defer break
```

```ritz body expect-error="a deferred `let` or `var` would die at once"
defer let x = 1
```

```ritz body expect-error="`defer` needs a statement"
defer
```

A `defer` inside a deferred block belongs to that block, and runs when that block
finishes.

```ritz
import ritzlib.sys

fn drain(fds: [4]i32) -> i32
    var closed: i32 = 0
    for fd in fds
        defer closed += 1               # once per pass, `continue` included
        if fd < 0
            continue
        sys_close(fd)
    closed                              # 4
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

A fn or method declared without `pub` may be called only from the file that
declares it. A call from another file is an error at the call. Make it `pub`
to export it. The error names the declaring file, for example "`helper` is
private to a.ritz; mark it `pub`", and a note gives the declaration's
location. An `extern fn`, a `fn ... = extern` declaration and a generic's
instances are not checked (ritz0: AGAST #3418; ritz1: #3419).
A method of a trait impl (`impl Trait for T`) needs no `pub`: it is reachable
wherever the trait is, including calls the compiler inserts, such as a `Drop`
impl's `drop` at the end of a scope in another file (AGAST #3386).

### 15.3 Qualified Access

**Removed in RERITZ.** There is no `module::item` or `module.item` access
form. Imported names land in a single flat namespace, which is why the standard
library uses long, prefixed free-function names (`strview_find`,
`vec_push`, `string_from`) instead of short names behind a module path.

```ritz body expect-error="`sys::write`: `::` was removed in RERITZ"
let n = sys::write(1, c"hi\n", 3)
```

The `.` form is refused the same way, as a type at the type and as a value,
call or `match` arm at the use (AGAST #2215). An imported const's bare name
in an arm compares against it; it doesn't bind a fresh name.

```ritz expect-error="`m.K`: there is no `module.item` access (LANGUAGE_SPEC §15.3). Imported names share one namespace, so write `K`"
const K: i32 = 7

fn main() -> i32
    m.K
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

A plain `import` is private to the file that writes it. `import b` brings in
what `b` declares and what `b` re-exports with `pub import`, transitively. It
does not bring in what `b` reaches through its own plain `import c`. A name
that would reach a file only that way is an error at the use, for example
"`c_val` is undefined (#3891): it comes from `c`; import it, or have `b` `pub
import` it" (AGAST #3891; LARB R54 is the same rule for a selective import's
list). A local of the same name is the local. The built-ins (`StrView`,
`Option`, `Result`, `Span` and their variants) are everywhere, so they are
never hidden. An enum's or a type alias's name is hidden as a struct's is,
at an annotation, at `E.V` and as a pattern's qualifier. A static call `T.m()`
uses `T`, and the method's mangled name `T_m` is hidden when `T` is. A method
call on a value, `x.m()`, uses no name: method syntax reaches no free fn
(§9.4), so it can't reach a hidden one (#3907).

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

**The poll contract** (LARB R78, AGAST #3728).  An `async fn f` with params
`P` and declared result type `T` becomes three items:

- `struct f_Future`, which starts with `__state: i32` and then `__result: T`.
  A unit fn's future has no `__result`.  Next come the params, and then
  whatever the body keeps across an `await`.
- `fn f(P) -> f_Future`, which builds the future in its first state and runs
  none of the body.
- `fn f_poll(self: *f_Future) -> bool`, which runs the body until it either
  suspends or finishes.  It answers `false` while Pending.  Once the body has
  finished it writes the result into `__result` and answers `true`.

An executor polls a future through a pointer, with no knowledge of `T`, until
the poll answers `true`, and then reads `__result` if it wants the value.
The result is kept whole whatever its type: an `i64` above 2^31, a pointer, a
struct, or a `-1` that is a genuine answer and not Pending.

```ritz
async fn neg() -> i32
    0 - 1

async fn big() -> i64
    5000000000

fn main() -> i32
    var f: neg_Future = neg()
    while !neg_poll(@f)
        pass
    let b: i64 = await big()
    if b != 5000000000
        return 1
    f.__result + 1
```

### 16.2 Await

**Calling an `async fn` requires `await`, whatever its body does** (decided
2026-09-09, AGAST #1395).  An `async fn` with no suspension point is not
callable synchronously.  A bare call `f(args)` evaluates to the fn's future, a
value of type `f_Future`, and runs none of the body.  `await f(args)` runs the
body and is the call's result.  This holds for any `async fn`, unit or valued,
empty-bodied or not.  `await` is allowed outside an `async fn` too, where it
drives the future to completion in place.

```ritz
async fn ready() -> i32
    42

async fn nothing()
    pass

fn main() -> i32
    await nothing()
    let v: i32 = await ready()
    v - 42
```

Two uses of a bare call are refused at the call:

- As a statement, whose future would be built and dropped:

```ritz expect-error="calling async fn `nothing` without `await` builds its future and drops it; its body never runs"
async fn nothing()
    pass

fn main() -> i32
    nothing()
    0
```

- Where the fn's result type is expected: `let`, an argument, `return`, an
  operand.

```ritz expect-error="is an async fn call, which without `await` is its future `ready_Future`"
async fn ready() -> i32
    42

fn main() -> i32
    let v: i32 = ready()
    v
```

Keeping the future is still allowed.  `var p: f_Future = f(args)` hands it to
an executor that polls it with `f_poll(@p)` until that is `true`, then reads
`p.__result` (see the poll contract in §16.1, and `examples/tier5_async/64_async_io`).

An awaited value may be bound without a type (AGAST #1318).  Inside an
`async fn` the binding lives in the fn's future, with the awaited fn's
declared result type (LARB R78):

```ritz
async fn fetch(x: i32) -> i32
    x

async fn go(x: i32) -> i32
    let v = await fetch(x)
    v + 1

fn main() -> i32
    let r: i32 = await go(4)
    r - 5
```

Any other untyped local in an `async fn` that awaits also lives in its future,
so its type is inferred from its value before the fn is lowered (AGAST #3762).
The value may be a literal (an integer literal is `i64`, as for any untyped
`let`), a parameter or earlier local, an operator over those (a comparison,
`&&`, `||` or `!` is `bool`; arithmetic takes its left operand's type, or the
right's when the left is a bare literal), a cast, an `await` of an `async fn`
(that fn's result type), a call to
a declared non-generic fn (its return type), or a bare call to an `async fn`
(its future):

```ritz
async fn fetch(x: i32) -> i32
    x

async fn go(x: i32) -> i32
    let y = x + 1
    let small = x as u8
    let v: i32 = await fetch(y)
    v + 1

fn main() -> i32
    let r: i32 = await go(4)
    r - r
```

A value whose type needs more than that, such as a struct field or a method
call, is refused at the `let`; give such a local a type:

```ritz expect-error="cannot infer the type of `a`, which `go`'s future holds across an `await`: give `a` a type"
struct Pair
    a: i32
    b: i32

async fn fetch(x: i32) -> i32
    x

async fn go(p: Pair) -> i32
    let a = p.a
    let v: i32 = await fetch(a)
    v

fn main() -> i32
    let r: i32 = await go(Pair { a: 1, b: 2 })
    r - 1
```

An `async fn` that awaits runs as written: its body is lowered to a state
machine over its control flow (AGAST #3727), and each `await` is a point the
fn suspends at (its poll answers `false`) and resumes at on the next poll,
wherever it is.  An `await` in a loop runs on every pass, only the taken arm
of an `if` runs its awaits, and every statement between them runs once:

```ritz
async fn dbl(x: i32) -> i32
    x * 2

async fn sum_doubles(n: i32) -> i32
    var sum: i32 = 0
    var i: i32 = 0
    while i < n
        if i == 2
            i += 1
            continue
        sum += await dbl(i)
        i += 1
    sum

fn main() -> i32
    let r: i32 = await sum_doubles(4)   # 0 + 2 + 6
    r - 8
```

The right operand of `&&` / `||` runs, with its awaits, only when the left
one doesn't decide the value.  A `for` over a range may await in its body or its
bounds (AGAST #4188): the loop variable and the end live in the future, the end
evaluated once, and `continue` goes on to the next value:

```ritz
async fn dbl(x: i32) -> i32
    x * 2

async fn go(n: i32) -> i32
    var s: i32 = 0
    for i in 0..n
        if i == 1
            continue
        s += await dbl(i)
    s

fn main() -> i32
    let r: i32 = await go(3)   # 0 + 4
    r - 4
```

The loop variable's type is its bounds', as a local's is its value's: a bound
whose type needs more than that, such as a struct field, is refused at the
`for`; cast it (`0..(p.n as i32)`).

A `match` arm may await, or `break` / `continue` the loop the `match` is in
(AGAST #4189); only the taken arm's awaits run.  An arm's names live across
its awaits: when an arm binds one, the scrutinee is kept in the future, so its
type is told as a local's is.  A scrutinee whose type needs more, such as a
struct field, is refused at the scrutinee; match a typed local instead:

```ritz
enum Job
    Double(i32)
    Skip

async fn dbl(x: i32) -> i32
    x * 2

async fn run(j: Job) -> i32
    match j
        Double(n) => n + await dbl(n)
        Skip => 0

fn main() -> i32
    let r: i32 = await run(Job.Double(3))   # 3 + 6
    r - 9
```

A value `if` with an `else` may await as an operand, too (AGAST #4190): only
the taken arm's awaits run, and its value is kept in the future, of the type
of the first arm whose value isn't a bare literal.  One that tells no type,
such as a struct field, is refused at the `if`; cast an arm (`p.n as i32`):

```ritz
async fn dbl(x: i32) -> i32
    x * 2

async fn pick(c: bool) -> i32
    1 + if c then 7 else await dbl(5)

fn main() -> i32
    let r: i32 = await pick(false)   # 1 + 10
    r - 11
```

A `defer` among the statements the machine splits into states is refused at
the `defer`, until it is lowered (AGAST #4013):

```ritz expect-error="`defer` in an async fn that awaits is not supported yet (AGAST #4013)"
async fn dbl(x: i32) -> i32
    x * 2

async fn go(n: i32) -> i32
    defer n = 0
    await dbl(n)

fn main() -> i32
    let r: i32 = await go(1)
    r - 2
```

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

`[[a, b]]` means `[[a]]` and `[[b]]`, and a trailing comma is allowed. Each
entry is checked on its own, and an error is located at that entry
(AGAST #1919):

```ritz
[[packed, target_os = "linux"]]
struct Wire
    tag: u8
    len: u32
```

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

A `fn` or `struct` name may have one `[[target_os]]` variant per target.
Two definitions gated to the same target are an error naming both
locations, whatever the target being compiled. The compiler never silently
picks one of them. Two such fns conflict even if they are identical. Two
such structs conflict unless their fields are identical, in which case the
repeat is dropped, as for ungated structs. How a gated variant relates to
an ungated definition of the same name is set out in
[§15.3](#153-qualified-access) for fns. A struct gated variant may stand
beside an ungated struct only if the two are identical, and this is checked
only on the variant's own target.

```ritz expect-error="Conflicting function definition for 'get_platform_id'"
[[target_os = "linux"]]
fn get_platform_id() -> i32
    1

[[target_os = "linux"]]
fn get_platform_id() -> i32
    2

fn main() -> i32
    get_platform_id()
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

Both compilers emit a naked function as LLVM `naked noinline`: its `asm`
blocks, then `unreachable`. It is never inlined, because the block's own `ret`
would return from the caller.

A generic function may be `[[naked]]`; every instance of it is naked. The
`asm` is the same text for each instance, so it must suit every type the
function is instantiated at.

```ritz
[[naked]]
fn ident<T>(a: T) -> T
    asm x86_64:
        movq %rdi, %rax
        retq

fn use_ident() -> i64
    ident(7)
```

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
discarded when it is an expression statement that is not its block's value,
and a block has a value only when it is used as one (LARB R69): any statement
but the last of a block, the last statement of a fn that returns nothing, and
the last line of an arm of a statement `match`, a branch of a statement `if`
or a loop body. A statement `match` or `if` is one whose own value is not
used. Both compilers reject it, located at the call (AGAST #2137; ritz1 does
not yet see the arm, branch and loop-body cases, AGAST #3997):

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

The arm `3 => check(3)` below is discarded: the `match` is a statement, so
its arms have no value (AGAST #3796).

```
fn main() -> i32
    var n: i32 = 3
    match n
        3 => check(3)     # error: result of [[must_use]] fn 'check' is discarded
        _ => n = 0
    0
```

Binding, assigning, returning or testing the result uses it, as does making
the call a value-returning block's last line, including the last line of an
arm of a `match` or `if` whose value is used:

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

#### Wiping secrets

Zeroing a key that is never read again is a dead store, and the optimiser
deletes it: at -O2 in the same module, or across modules under LTO, a plain
`*p = 0` loop, or a `memzero` inlined beside the dead buffer, disappears and
leaves the key in memory. A volatile store is never removed, so a wipe built
from `volatile_store` always reaches memory. ritzlib provides it as
`secure_zero(p, n)` in `ritzlib.memory` (AGAST #1864). It writes each of the
`n` bytes at `p` with a volatile store: byte stores up to the first 8-byte
boundary, aligned `u64` stores, then byte stores for the tail. Use it for
every secret wipe. Use plain `memzero` for zeroing that only initialises.

```ritz
import ritzlib.memory

fn derive(seed: u8, out: *u8) -> i32
    var key: [32]u8
    for i in 0..32
        key[i] = seed + i as u8
    out[0] = key[0] ^ key[31]
    secure_zero(@key[0], 32)     # stays at -O2: key is dead, the wipe is not
    0
```

*Why a library function, not an intrinsic:* `volatile_store` already says
"this write happens", in both compilers. `secure_zero` is that store in a
loop, so it needs no compiler support of its own. An `llvm.memset` with
`volatile` set would allow wider stores, but nothing needs that yet.

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

### 18.6 Inline Assembly

An `asm` block is a statement that places machine instructions in a function
(LARB R7, AGAST #1825; this section is LARB R50, AGAST #1619). It is the escape
hatch for what Ritz has no builtin for: port I/O, control registers, `syscall`,
a compiler barrier.

```text
asm_stmt    := 'asm' ARCH asm_clauses? ':' NEWLINE INDENT asm_line+ DEDENT
asm_clauses := '(' asm_clause (',' asm_clause)* ')'
asm_clause  := ('in' | 'out' | 'inout') IDENT (':' REGISTER)?
             | 'clobber' REGISTER
```

```ritz
fn inb(port: u16) -> u8
    var result: u8 = 0
    asm x86_64 (out result):
        movw {port}, %dx
        inb %dx, %al
        movb %al, {result}
    return result

fn write1(fd: i64, buf: *u8, n: i64) -> i64
    var ret: i64 = 1                     # syscall number in, result out
    asm x86_64 (inout ret: rax, in fd: rdi, in buf: rsi, in n: rdx, clobber rcx, clobber r11):
        syscall
    return ret
```

Both compilers accept every form here (ritz1: AGAST #3395, ritz0: #3396). The
compiler barrier cryptosec uses to keep a zeroing loop from being removed:

```ritz
fn wipe(ptr: *u8, len: i64)
    for i in 0..len
        *(ptr + i) = 0
    asm x86_64:
        nopl ({ptr})
```

**Architecture.** `ARCH` names the instruction set, and only `x86_64` is
defined. A block whose `ARCH` isn't the target's is an error at the name. A
function that needs several architectures uses `[[target(...)]]` (§17.2) to pick
one.

**Lines are text.** Each indented line is passed to the assembler as written,
not tokenised as Ritz. x86_64 is AT&T syntax. The compiler changes the text in
only three ways:
- `{name}` is replaced by the operand's register (below). `{{` and `}}` are a
  literal `{` and `}`.
- From `#` to the end of the line is a comment and is dropped, as in Ritz and
  the GNU assembler. So no `{name}` is substituted inside a comment.
- Lines are joined with newlines. Indentation beyond the block's is dropped.
`$` and `%` are literal: `movq $3, %rcx` means what it says, and the compiler
escapes them for LLVM.

**Labels.** Only numeric local labels (`1:`, jumped to as `1b` or `1f`). A named
label is an error at the line: the function may be inlined into several callers,
and each copy would define the label again (#1371).

**Operands.** `{name}` names a local, a parameter or a global; an expression is
an error. Its type must be an integer or a pointer (`*T`, `@T`, `@&T`; `bool` is
an `i1`, which no register constraint takes), and the type sets the register width (`{port}` of a `u16` is `%dx`, not
`%rdx`). Every operand is an **input** unless a clause says otherwise:
- `out x`: the block writes `x` and doesn't read it. Its value afterwards is
  what the block left in the register.
- `inout x`: the block reads and writes `x`.
- `x: rax` pins the operand to a register; otherwise the compiler picks a
  general register. A pinned operand needn't appear in the text (`syscall` reads
  `rax` and `rdi` itself); an unpinned one in a clause must.
Direction is declared, never guessed from mnemonics. `out` and `inout` need a
place you can assign (a `var`, a field of one, or a global `var`), and count
as an assignment of it for the borrow rules (§13.5). A name may appear in at
most one clause. A register may be pinned at most once, and `rsp` and `rbp`
can't be pinned or clobbered.

**Clobbers.** Every x86_64 general register named in the text (`%rax`, `%eax`,
`%ax`, `%al`, `%r8d`, …) is clobbered, counted as its 64-bit register. `clobber
r11` adds one the text doesn't name, such as those `syscall` overwrites. A
register pinned to an output isn't also clobbered. Memory
and flags are always clobbered, and the block always counts as having side
effects: it is never removed, merged with another, or moved across a memory
access. A block with no outputs is still kept.

**Control.** Control is assumed to leave the block at its end. A block that
jumps away for good (into a kernel, say) should be followed by a `loop` so the
function's end isn't reachable (§6.1).

**`[[naked]]`.** In a naked function (§17.5) an `asm` block takes no clauses and
no `{name}`: there is no frame, so parameters are found in the calling
convention's registers.

**Lowering.** Both compilers emit one LLVM `call asm sideeffect` per block, in
AT&T dialect:
- the template is the text with each `{name}` replaced by `${N}` and every
  literal `$` written as `$$`;
- constraints list the outputs first, `=&r` (early-clobber: the block may write
  one before it has read every input) or `={reg}` when pinned; then the inputs,
  `r` or `{reg}`, with each `inout` tied to its output by number (`0`); then
  `~{reg}` for every clobber, and `~{memory},~{dirflag},~{fpsr},~{flags}`.
  `rsp` and `rbp` are never listed, nor is a register pinned to an output:
  LLVM would drop an `inout`'s tie to its input (AGAST #3425);
- no outputs gives a `void` call, one output that type, several a literal
  struct; each output is stored back to its place after the call.

**Errors**, each located: unknown or wrong `ARCH`; `{name}` not in scope, or not
an integer or pointer; `{` not closed or followed by a non-name; `out`
or `inout` on something that isn't an assignable place; a name in two clauses;
an unpinned clause operand missing from the text; a register pinned twice or not
a general register; `rsp`/`rbp` pinned or clobbered; a named label; a clause or
`{name}` in a `[[naked]]` function.

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

The message is a `"..."` literal: a `StrView`, like every Ritz string. A
`c"..."` message is C in Ritz clothing, and every compiler refuses it with a
located error at the literal:

```ritz expect-error='an assert message is a "..." literal: drop the `c`'
[[test]]
fn test_it() -> i32
    assert 1 == 1, c"one is one"
    0
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
              | break_stmt | continue_stmt | defer_stmt | assign_stmt | expr_stmt
defer_stmt   := 'defer' (stmt | NEWLINE INDENT stmt+ DEDENT)
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
