# The Ritz Standard

**What this is.** The one normative document for *how Ritz is written*: the
idioms a library or program must use, and the conventions it follows. What the
language *is* (syntax, types, what compiles) is
[`LANGUAGE_SPEC.md`](LANGUAGE_SPEC.md). Where the two disagree, the spec wins
and the disagreement is a bug in this document.

It replaces two style guides: the root `STYLE.md` and `docs/STYLE.md`. Both
are now pointers here (AGAST #1344). Nothing else in the tree is normative
about style. A review that cites a rule cites it by its ID, as in "S-PTR-2".

## How to read a rule

Every rule has an ID, a one-line statement, and a status. The status says what
stands behind the rule, and nothing stronger:

| Status | Meaning | What proves it |
|---|---|---|
| **ENFORCED** | A tool refuses a violation. You can't merge one. | An `expect-error` block in the rule that every compiler must keep refusing, or the `make` target that fails |
| **CHECKED** | The construct the rule asks for works. A violation still compiles. | A compiled block in the rule |
| **ADVISORY** | Human judgement, at review. A violation still compiles. | Where it can be counted, a `Report:` key (below) |

Every fenced `ritz` block in this file is compiled by
`tools/check_doc_examples.py` (`make check-doc-examples`) on ritz0 in every
build, and on ritz1 and ritz1_selfhosted by `make check-doc-examples-ritz1`. A
block that stops compiling, or an `expect-error` block the compilers start
accepting, fails the build. This file has no `no-compile` sketches: a rule
waits for its compiler work rather than running ahead of it (LARB R8).
`tools/test_standard_doc.py` holds each rule to its status: an ENFORCED rule
without a refusal, or a CHECKED rule without a compiled block, fails
`make tools-unit`.

### The conformance report

The ADVISORY idiom rules in Part I each name a counting rule, so "how many
violations does ritzlib have?" is a command, not an argument:

```bash
python3 tools/standard_report.py                    # ritzlib, one row per rule
python3 tools/standard_report.py --list raw-alloc   # every site of one rule
python3 tools/standard_report.py --json path/to/pkg # any tree
```

The exact counting rules are in the script's docstring and pinned by
`tools/test_standard_report.py`. The report always exits 0. It measures, it
doesn't gate. When a rule becomes ENFORCED, a compiler or a gate target is
what enforces it, not this script.

**Exemptions.** A justified exception is written next to the code, naming the
counting rules it excuses and why:

```text
# standard-exempt: raw-ptr-param, ptr-len-param: the write(2) syscall ABI
pub fn sys_write(fd: i32, buf: *u8, n: i64) -> i64
```

It goes in the comment block directly above the `fn`. For a whole module,
`# standard-exempt-file: <keys>: <reason>` goes in the file's leading comments.
An exempt site is still listed and counted, in its own column. An exemption
with an unknown key, or with a reason under 12 characters, is counted as
`exempt-malformed`.

---

# Part I: Idioms

These answer the questions the old style guides didn't: when `bool`, `Result`,
`Option`, a reference or a span is required, where behaviour lives, who frees
what, and what a library may abort on. #1347 converts ritzlib to them.

## 1. Truth values

#### S-BOOL-1 A condition is a `bool`

**Status: ENFORCED**

`if`, `while`, `assert`, `and`, `or` and `not` take a `bool`. Nothing is truthy:
test an integer with `n != 0` and a pointer with `p != null` (LARB R4, #2342;
all three compilers).

```ritz body expect-error="if condition must be bool, got an integer: write `x != 0`"
let n = 1
if n
    print("non-zero\n")
```

#### S-BOOL-2 A predicate returns `bool`

**Status: ADVISORY**

A function that answers a yes/no question returns `bool`, never an `i32` 0/1.
That includes `is_*`, `has_*`, `can_*`, `contains`, `*_eq`, `starts_with` and
`valid`. An integer return means a quantity. A function that can *fail* to
answer returns a `Result` (S-RESULT-1), not a third integer value.

Report: `bool-return`. Counts API fns with an integer return and a predicate
name, including the C ctype spelling `is<letters>` (`isdigit`, `isspace`).

```ritz
fn is_digit(c: u8) -> bool
    c >= '0' and c <= '9'

fn all_digits(s: StrView) -> bool
    for i in 0..s.len
        if not is_digit(*(s.ptr + i))
            return false
    true
```

#### S-BOOL-3 A `bool` is not an integer

**Status: ENFORCED**

A `bool` doesn't fit an integer slot, and an integer doesn't fit a `bool` slot.
Write `b as i32` or `x != 0`. `x as bool` is removed (R4, #2342).

```ritz expect-error="cannot use bool as an integer: write `b as i32`"
fn same(a: i64, b: i64) -> i32
    return a == b

fn main() -> i32
    same(1, 1)
```

## 2. Failure: `Result`

#### S-RESULT-1 A fallible function returns `Result<T, E>`

**Status: ADVISORY**

A function that can fail in a way its caller must act on returns
`Result<T, E>`. It doesn't return a sentinel such as `-1`, `0` or `null` in the
success type. Use a sentinel only where the value is genuinely not an error,
such as "index of the first match, or the length when there is none", and say so
in the doc comment.

Report: `sentinel-return`. Counts API fns with an integer return that
`return -<n>` somewhere.

```ritz
import ritzlib.result

enum ParseError
    Empty
    BadDigit

fn parse_u32(s: StrView) -> Result<u32, ParseError>
    if s.len == 0
        return Err(ParseError.Empty)
    var v: u32 = 0
    for i in 0..s.len
        let c = *(s.ptr + i)
        if c < '0' or c > '9'
            return Err(ParseError.BadDigit)
        v = v * 10 + (c - '0') as u32
    Ok(v)
```

#### S-RESULT-2 An error type names its failures

**Status: ADVISORY**

`E` is an `enum` with one variant per failure the caller might treat
differently, or a struct carrying one. It isn't a bare `i32` code. A
syscall's negative errno is converted at the wrapper that made the syscall.
Qualify a variant with `.`: `ParseError.Empty`.

The raw `sys_*` syscall wrappers are that boundary, so they return the raw
result and are exempt (`standard-exempt-file(sys_*)` in `sys`, `net` and
`uring`). Everything above them converts.

Report: `status-return`. Counts API fns with an integer return that
`return -NAME` (a named code such as `-EINVAL`) or return a `syscallN(` or
`sys_*(` result unconverted.

#### S-RESULT-3 A result is returned, not written through a parameter

**Status: ADVISORY**

A function hands back what it computed in its return value: a struct, an
`Option` or a `Result`. It doesn't write a scalar, a `StrView`, a `String` or
a pointer into a caller's `x:& T`, `@&T` or `*T` and return a status beside
it. `@&T` is for a callee that *updates* a value the caller owns, such as a
`Vec` it appends to (S-PTR-1), not a second return slot. The kernel ABI's own
out-pointers (`pipe(2)`'s fds, `accept(2)`'s `addrlen`) are exempt at the
`sys_*` layer, and converted above it.

Report: `out-param`. Counts each `:&`, `@&` or `*` parameter of a scalar,
`StrView`, `String` or pointer pointee that the body assigns or passes to a
`sys_*(`/`syscallN(` call. A `*u8` byte buffer is S-PTR-1/S-PTR-2's.

```ritz
import ritzlib.option

struct Split
    before: StrView
    after: StrView

fn split_once(s: StrView, delim: u8) -> Option<Split>
    for i in 0..s.len
        if *(s.ptr + i) == delim
            let before = StrView { ptr: s.ptr, len: i }
            let after = StrView { ptr: s.ptr + i + 1, len: s.len - i - 1 }
            return Some(Split { before: before, after: after })
    None
```

## 3. Propagating errors

#### S-ERR-1 Propagate a `Result` or `Option` with `?`

**Status: CHECKED**

`expr?` yields the `Ok` value and returns the `Err` from the enclosing function
(LANGUAGE_SPEC §14.2). Write that, rather than a `match` whose `Err` arm only
returns `Err(e)`. The enclosing function returns a `Result` with the same `E`.

```ritz
import ritzlib.result

struct Config
    port: i64

enum LoadError
    Missing
    Bad

fn read_port(raw: i64) -> Result<i64, LoadError>
    if raw < 0
        return Err(LoadError.Missing)
    Ok(raw)

fn check_port(p: i64) -> Result<i64, LoadError>
    if p > 65535
        return Err(LoadError.Bad)
    Ok(p)

fn load(raw: i64) -> Result<Config, LoadError>
    let p = read_port(raw)?
    let q = check_port(p)?
    Ok(Config { port: q })
```

`?` works on an `Option` too: `expr?` yields the `Some` payload and returns
`None` from the enclosing function, which must return an `Option`
(LANGUAGE_SPEC §14.2). This is specified, not incidental — all three compilers
accept it, so relying on it is the same as relying on the `Result` form.

#### S-ERR-2 A `[[must_use]]` result is not thrown away

**Status: ENFORCED**

A function whose result the caller must look at, such as a status, a count
written or a handle, carries `[[must_use]]`, and both compilers refuse a call
that discards it (LANGUAGE_SPEC §17.8). Whether to put the attribute on is
judgement; the refusal once it's there is not. A discarded `Result` is not
refused today.

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

#### S-ERR-3 A library doesn't end the program

**Status: ADVISORY**

Library code returns its failure to the caller. Only a program's `main` path
decides to exit. A library may end the process in two cases only, each marked
`standard-exempt` with its reason:

- **No caller to return to.** In a forked child before `exec`, `sys_exit(127)` is
  the only report (`spawn_fork`).
- **The language says so.** `m[k]` on a missing key must not return (LARB R15,
  LANGUAGE_SPEC §7.8), so `index` ends the program with status 101.

An `env_must`-style "get or die" helper belongs in the program, not the library.

Report: `lib-exit`. Counts every `sys_exit(` outside `main`.

#### S-ERR-4 `assert` is for tests

**Status: ENFORCED**

`assert` is allowed only in `[[test]]` and `[[test_helper]]` functions
(LANGUAGE_SPEC §19.2). Library code checks the condition and returns a
`Result` or an `Option`.

```ritz expect-error="assert is only allowed in [[test]] and [[test_helper]] functions, not in 'nth'"
fn nth(xs: Span<i32>, i: i64) -> i32
    assert i < xs.len
    xs[i]
```

## 4. Absence: `Option`

#### S-OPTION-1 An absent value is `Option<T>`, not `null`

**Status: ADVISORY**

A function that may have nothing to return, such as a lookup, a search or the
next item, returns `Option<T>` and not a null pointer. The caller `match`es it,
and the compiler makes the `match` cover `None` (S-MATCH-1).

`null` is still right in two places: a raw pointer passed to or from a syscall
or other foreign ABI (S-PTR-1), and the private fields of a type that owns raw
memory, where `null` means "not allocated yet".

Report: `null-return`. Counts API fns returning a pointer or reference that
`return null`.

```ritz
import ritzlib.option

fn find(xs: Span<i64>, want: i64) -> Option<i64>
    for i in 0..xs.len
        if xs[i] == want
            return Some(i)
    None

fn position_or_end(xs: Span<i64>, want: i64) -> i64
    match find(xs, want)
        Some(i) => i
        None => xs.len
```

## 5. Parameters, references and spans

#### S-PTR-1 A parameter is a value, a reference or a span, not a raw `*T`

**Status: ADVISORY**

Choose a parameter's type by what the function does with it:

| The function | Parameter |
|---|---|
| reads a small copy value | `x: T` |
| reads a struct it doesn't keep | `x: @T` |
| writes the caller's value | `x: @&T`, or `x:& T` for a bare place |
| takes ownership of a move-only value | `x: T` (it moves, §13.2) |
| reads or writes a run of elements | `xs: Span<T>` / `[T]`, or `s: StrView` for text (S-PTR-2) |

A raw `*T` parameter is right only at a boundary that is raw by nature: a
syscall or foreign ABI, an allocator, or the private functions of a type that
owns raw memory. Mark it `standard-exempt` with that reason. The `:=`
parameter modifier (`x:= T`) is accepted and lowers exactly as `x: T`: the
sigil records ownership intent but adds nothing, so write `x: T` (§13.2,
AGAST #4062).

Report: `raw-ptr-param`. Counts each `*T` parameter of an API fn.

```ritz
struct Point
    x: i32
    y: i32

fn norm1(p: @Point) -> i32
    p.x + p.y

fn scale(p: @&Point, k: i32)
    p.x = p.x * k
    p.y = p.y * k

fn bump(n:& i32)
    n += 1

fn main() -> i32
    var p = Point { x: 1, y: 2 }
    scale(@&p, 3)
    var total = norm1(@p)
    bump(total)
    total
```

#### S-PTR-2 A pointer and a length are a `Span<T>` or a `StrView`

**Status: ADVISORY**

A `*T` followed by its element count is one parameter: `Span<T>` (written
`[T]`) for elements and `StrView` for text. A span carries its own length, so
the two can't disagree, and `@array` fits a `Span<T>` slot directly.

Report: `ptr-len-param`. Counts a `*T` parameter followed by an integer named
`len`, `n`, `size`, `count`, `cap`, `nbytes`, `length` or `*_len`.

```ritz
fn sum(xs: [i64]) -> i64
    var total: i64 = 0
    for i in 0..xs.len
        total += xs[i]
    total

fn main() -> i32
    let a: [4]i64 = [1, 2, 3, 4]
    sum(@a) as i32
```

#### S-PTR-3 A callee that writes is given `@&x`

**Status: ENFORCED**

`@x` is a shared borrow. It fits `@T` and `*T`, never `@&T` or `:&`, so a call
that mutates shows `@&x` at the call site (LARB R1, #2339).

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

#### S-PTR-4 An `@T` is read-only

**Status: ENFORCED**

No write goes through an `@T`, directly or through a chain of fields
(#2338). A function that writes takes `@&T`.

```ritz expect-error="cannot write through an `@T`: make it `@&T`"
struct Point
    x: i32
    y: i32

fn reset(p: @Point)
    p.x = 0
```

#### S-PTR-5 Text crosses to `*u8` explicitly

**Status: ENFORCED**

Only a string literal fits a `*u8` slot. A `StrView` or a `String` is passed
to a C-string API as `.ptr` or `s.as_ptr()`, which makes its NUL
assumption visible (LARB R3, #2341).

```ritz body expect-error="a StrView is not a `*u8`"
let s: StrView = "hello"
let p: *u8 = s
```

#### S-PTR-6 A reference never outlives its local

**Status: ENFORCED**

A function doesn't return a reference to its own local. Return the value, or
take the destination as `@&T` (LARB R2, #2340).

```ritz expect-error="cannot return a reference to local `c`: it ends with the fn"
struct Counter
    n: i32

fn make() -> @Counter
    var c = Counter { n: 1 }
    return @c
```

## 6. Behaviour: methods

#### S-IMPL-1 A type's behaviour is in its `impl`

**Status: ADVISORY**

A public operation on a type the module declares is a method in `impl Type`,
called as `x.verb()`. It isn't a free function `type_verb(x: @Type)`. A free
function is right for what isn't one type's behaviour: an operation over
several types, or a module's entry point.

ritzlib's `string_*`, `vec_*` and `option_*` free functions predate this rule.
LARB R66 (#3252) replaced the compiler's UFCS name table with `pub` methods
(#3495; #3496 and #3497 deleted the table). `impl String`, `impl<T> Vec<T>`,
`impl<T> Option<T>`, `impl<T> Span<T>` and `impl StrView` hold them (#3495,
#4231): method syntax on a ritzlib type reaches only those.

Report: `free-fn-method`. Counts public module-level fns whose first parameter
is a struct or enum the same file declares.

```ritz
struct Counter
    n: i64

impl Counter
    pub fn new() -> Counter
        Counter { n: 0 }
    pub fn is_zero(self: @Counter) -> bool
        self.n == 0
    pub fn bump(self:&)
        self.n += 1

fn main() -> i32
    var c = Counter.new()
    c.bump()
    if c.is_zero()
        return 1
    0
```

#### S-IMPL-2 Method syntax reaches only methods

**Status: ENFORCED**

`x.m()` calls an `m` declared in an `impl` for `x`'s type. A free function
that happens to be named `<type>_m` is not reached (AGAST #3244).

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

#### S-IMPL-3 The receiver says what the method does to `self`

**Status: CHECKED**

Use `self: @Type` to read, and `self:&` (or `self: @&Type`) to change the
caller's value. Use a bare `self`, which is by value, only to consume it or to
work on a copy (LANGUAGE_SPEC §5.4, LARB R10). A constructor has no `self`, is
named `new` or `with_<what>`, and is called as `Type.new()`.

```ritz
struct Range
    lo: i64
    hi: i64

impl Range
    pub fn with_len(lo: i64, n: i64) -> Range
        Range { lo: lo, hi: lo + n }
    pub fn len(self: @Range) -> i64
        self.hi - self.lo
    pub fn shift(self:&, by: i64)
        self.lo += by
        self.hi += by
    pub fn shifted(self, by: i64) -> Range
        self.lo += by
        self.hi += by
        self

fn main() -> i32
    var r = Range.with_len(2, 3)
    r.shift(1)
    let s = r.shifted(10)
    (r.len() + s.lo) as i32
```

## 7. Ownership: who frees what

#### S-OWN-1 The owner frees, exactly once

**Status: ADVISORY**

A value that owns memory or a handle has one owner: the binding, field or
by-value parameter holding it (LANGUAGE_SPEC §13.1). The owner releases it,
and nothing else does. A function that only uses it borrows it (`@x`, `@&x`) and
doesn't free it. A function that returns it hands ownership to the caller.

`String` and `Vec<T>` implement `Drop` (AGAST #2159, LANGUAGE_SPEC §13.6), so
they are move-only and S-OWN-3 enforces this: the compiler frees the buffer
at the owner's scope end. Don't call `s.deinit()` / `v.deinit()` on an owning
binding; `String.deinit` and `Vec.deinit` remain for a value reached through a
raw pointer, which the compiler never drops.

```ritz
import ritzlib.string

fn greeting_len() -> i64
    var s = string_from("hello")
    s.push_str(", world")
    s.len()                  # freed once, when the function returns
```

#### S-OWN-2 Raw allocation stays inside the owning type

**Status: ADVISORY**

`malloc`, `free`, `realloc`, `heap_*` and `mmap` are called only by the
functions of the type that owns the memory: its constructor, its growth
functions and its `drop`. Everyone else asks that type, or uses `String`,
`Vec<T>`, `Box<T>` or an `Arena`. A module that *is* an allocator says so
with `standard-exempt-file: raw-alloc`.

Report: `raw-alloc`. Counts allocator calls in fns that are not methods and
whose first parameter or return type isn't a struct the same file declares.

#### S-OWN-3 A resource type implements `Drop`, and is moved

**Status: ENFORCED**

A struct that owns something that must be released implements `Drop`. That
makes it move-only (LANGUAGE_SPEC §13.1): passing it by value moves it, the
compiler drops it at the end of its owner's scope, and a use after the move is
refused (#1854).

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
    consume(r)
    r.handle
```

#### S-OWN-4 Cleanup without a `Drop` type is a `defer`

**Status: CHECKED**

Put a release that has no `Drop` type to do it in a `defer` placed
immediately after the acquire. It then runs on every exit, early returns
included, in reverse order (LANGUAGE_SPEC §13.7). Don't repeat it before each
`return`.

```ritz
import ritzlib.memory

fn scratch_used(size: i64, fail: bool) -> i64
    var arena = arena_new(size)
    defer arena.destroy()
    if fail
        return -1
    let p = arena.alloc(64)
    arena.used()
```

## 8. Branching

#### S-MATCH-1 A `match` covers its scrutinee

**Status: ENFORCED**

Every `match` names every variant, or has a catch-all, and an arm that can
never run is an error too (LARB R6, #2344). Prefer naming the variants to
`_`, so a new variant is a compile error at every `match` that has to handle
it.

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

#### S-MATCH-2 Branch on an enum with `match`

**Status: ADVISORY**

Several-way branching on an enum is a `match`, not an `if`/`else if` chain of
`==` tests: the chain has no exhaustiveness check. A `match` arm names the
variant bare (`Ident =>`), and an equality test qualifies it
(`k == TokenKind.Ident`).

```ritz
enum TokenKind
    Ident
    Number
    Eof

fn weight(k: TokenKind) -> i32
    match k
        Ident => 1
        Number => 2
        Eof => 0
```

---

# Part II: Conventions

How code looks and where it goes. The compilers check little of this, so most
of it is ADVISORY. It is still the standard: a review may ask for it.

## 9. Names

#### S-NAME-1 Functions, variables and modules are `snake_case`

**Status: ADVISORY**

Name it for what it means (`token_count`, not `tc`). A module file is short and
has no redundant suffix: `json.ritz`, not `json_parser.ritz`. An unused binding
starts with `_`.

#### S-NAME-2 Types and variants are `PascalCase`

**Status: ADVISORY**

Structs are nouns (`Parser`, `Arena`); enums are nouns or adjectives
(`TokenKind`, `State`); variants are `PascalCase` too (`Some`, `Ok`).
LANGUAGE_SPEC §11 relies on it: a single uppercase letter or a `PascalCase`
name in a type position is read as a type.

```ritz
struct HashEntry
    key: i64
    value: i64

enum TokenKind
    Identifier
    Number
    LeftParen
```

#### S-NAME-3 Constants are `SCREAMING_SNAKE_CASE`

**Status: ADVISORY**

Replace a magic number with a named constant, and keep related constants
together.

#### S-NAME-4 A constant declares its type

**Status: ENFORCED**

A `const` without a type annotation doesn't parse, on any of the three
compilers (LARB R38 for globals).

```ritz expect-error="Expected COLON, got EQ"
const MAX_DEPTH = 64
```

#### S-NAME-5 Type parameters are single capitals

**Status: ADVISORY**

`T` and `U` for elements, `K` and `V` for keys and values, `E` for an error,
`N` for a size. A longer name is fine when one letter would be ambiguous.

```ritz
struct Pair<K, V>
    key: K
    value: V

fn swap<T>(a: @&T, b: @&T)
    let tmp: T = *a
    *a = *b
    *b = tmp
```

## 10. Layout

#### S-FMT-1 Indentation is spaces, never tabs

**Status: ENFORCED**

The lexer refuses a tab in indentation (LANGUAGE_SPEC §2.2).

```ritz expect-error="Tabs not allowed for indentation"
fn tabbed() -> i32
	let x = 1
	return x
```

#### S-FMT-2 One indent level is 4 spaces

**Status: ADVISORY**

The compiler accepts any consistent width. The tree uses 4.

#### S-FMT-3 Lines are at most 100 characters

**Status: ADVISORY**

Break a long expression after a binary operator (the next line continues at
the same indent, LANGUAGE_SPEC §2.2), and a long signature one parameter per
line.

```ritz
struct Config
    verbose: bool
    retries: i32

fn should_retry(
    cfg: @Config,
    attempt: i32,
    last_status: i32
) -> bool
    cfg.retries > attempt and
    last_status != 0
```

#### S-FMT-4 Two blank lines between top-level items

**Status: ADVISORY**

Two blank lines go between top-level items, and one between logical steps
inside a function. Never put more than two in a row.

#### S-FMT-5 Spaces around binary operators and after commas

**Status: ADVISORY**

Write `a + b * c` and `f(1, 2)`, not `a+b*c` or `f( 1,2 )`. Put no space
after a unary operator (`-x`, `*p`, `@v`, `not done`).

#### S-FMT-6 Logic is spelled `and`, `or`, `not`

**Status: ADVISORY**

The symbol forms `&&`, `||` and `!` mean the same, but the word forms are
house style. In ritzlib, ritz1 and examples they outnumbered the symbols
1,678 to 2 (2026-09-12).

```ritz
fn in_window(x: i64, lo: i64, hi: i64, closed: bool) -> bool
    if x > lo and x < hi
        return true
    closed and (x == lo or x == hi)
```

## 11. Files

#### S-ORG-1 Imports come in three groups

**Status: ADVISORY**

`ritzlib.*` comes first, then other packages, then sibling modules, with one
blank line between groups and each group sorted.

#### S-ORG-2 A module reads top-down

**Status: ADVISORY**

A module starts with a header comment saying what it is for, then its imports,
constants, types, `impl` blocks (constructors, then accessors, then mutators,
then conversions) and free functions, with private helpers last. Separate the
major sections with a banner:

```ritz
# ============================================================================
# Parsing
# ============================================================================
```

#### S-ORG-3 Split a module before it passes 500 lines

**Status: ADVISORY**

Split it into a directory of modules, one per component, when the parts can
be named separately.

## 12. Comments

#### S-DOC-1 Every `pub` item says what it promises

**Status: ADVISORY**

A `#` comment block directly above each `pub` fn, struct and enum says what it
does, what it returns on each path (which `Err`, when `None`), and who owns
what it returns. A comment explains *why*, not what the next line plainly
does.

```ritz
import ritzlib.option

# The index of the first `want` in `xs`, or None. Borrows `xs`; allocates nothing.
pub fn index_of(xs: [u8], want: u8) -> Option<i64>
    for i in 0..xs.len
        if xs[i] == want
            return Some(i)
    None
```

## 13. Tests

#### S-TEST-1 A test is a `[[test]]` fn with no parameters

**Status: CHECKED**

A test function is any function marked `[[test]]`, whatever its name. It takes
no parameters and returns an integer (0 is a pass) or nothing
(LANGUAGE_SPEC §17.1). It checks with `assert`, giving a message that names the
expectation.

```ritz
fn add(a: i64, b: i64) -> i64
    a + b

[[test]]
fn test_add_carries_into_the_next_digit()
    assert add(9, 1) == 10, "9 + 1"
```

#### S-TEST-2 Tests are named for the behaviour and live in `tests/`

**Status: ADVISORY**

Name a test `test_<unit>_<behaviour>`, for example
`test_vec_push_grows_when_full`. Tests for `ritzlib/<m>.ritz` go in
`ritzlib/tests/test_<m>.ritz`, and a package's tests go in its `test/`
directory. See [`TESTING.md`](TESTING.md) for the harness.

## 14. Bindings

#### S-INIT-1 A `var` is initialised where it is declared

**Status: ADVISORY**

`var x: i32` with no initialiser compiles, so this is up to review. Use
`[0; N]` for an array: ritz0 lowers a large fill to a `memset`, so it costs no
more than leaving the array uninitialised. Use `let` unless the binding is
reassigned.

```ritz body
var count: i64 = 0
var buf: [256]u8 = [0; 256]
buf[0] = 'a'
count += 1
```

#### S-INIT-2 An integer narrows only with `as`

**Status: ENFORCED**

An unannotated integer binding is `i64`: `var i = 0` holds an `i64`, not an
`i32`. Putting an `i64` in a narrower integer slot is an error unless the value
is provably lossless (LANGUAGE_SPEC §7.5, #1393). Annotate the binding,
`var i: i32 = 0`, or narrow on purpose with `<expr> as i32`.

ritz0 and ritz1 refuse it in a typed `let` or `var` initialiser. ritz1 doesn't
yet refuse an *unannotated* source like `var i = 0` (#1688). Both also refuse
it in an assignment (`=` and `op=`), a call argument, a `return` or function
tail (#1444, #4081) and a struct literal field (#4157, #4218).

```ritz body expect-error="implicit narrowing: `n` is declared `i32` but its initialiser has type `i64`"
var i: i64 = 0
i += 1
let n: i32 = i
```

---

## Changing this standard

A rule moves from ADVISORY to ENFORCED when a compiler or a gate target
refuses its violation. The commit that adds the refusal also replaces the
rule's `Report:` line with an `expect-error` block, or adds
`Enforced by: \`make <target>\``. These are queued:

- **S-OWN-1** becomes ENFORCED with `String` and `Vec` `Drop` (#2159).
- **S-IMPL-1**: the free-function surface is replaced by methods (#3495 to #3497).
- **Part I's ADVISORY rules**: ritzlib is converted against the report (#1347).

Propose any other change as an AGAST ticket under #1343.
