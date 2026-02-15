# RERITZ: The Great Ritz Language Overhaul

**Branch:** `main` (merged)
**Status:** Phase 2 Complete - Core Syntax Implemented
**Date:** 2026-02-14
**Based on:** LARB Language Review, SYNTAX_PROPOSALS.md, ASYNC_DESIGN.md, Issue #118

---

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| `[[attr]]` attributes | ✅ Done | Works in both legacy and RERITZ modes |
| `:&` mutable borrow params | ✅ Done | Emitter generates pointer passing |
| `:=` move params | ✅ Parsed | AST supports, emitter uses MOVE enum |
| `@x` address-of | ✅ Done | Creates temp alloca for SSA values |
| `@&x` mutable address-of | ✅ Done | Works in RERITZ mode |
| `@T` reference types | ✅ Parsed | Parser creates RefType |
| `@&T` mutable ref types | ✅ Parsed | Parser creates RefType(mutable=True) |
| `asm` blocks | ✅ Done | Full parser/emitter support, Issue #118 |
| `[[packed]]` structs | ✅ Done | No alignment padding, kernel structs |
| `[[naked]]` functions | ✅ Done | No prologue/epilogue, interrupt handlers |
| `$` token for asm | ✅ Done | AT&T immediate syntax ($42) |
| String redesign | ❌ Not started | StrView, String hierarchy |
| Reference philosophy | ❌ Not started | `&T` → `@T` migration |
| `unsafe` blocks | ❌ Not started | Required for raw pointer ops |

### Conversion Progress

| Location | `@test` → `[[test]]` | Files |
|----------|---------------------|-------|
| examples/tier1_basics | ✅ Done | 10 |
| examples/tier5_async | ✅ Done | 14 |
| examples/74_async_tiers | ✅ Done | 1 |
| ritzlib/tests | ✅ Done | 13 |
| ritz0/test | ✅ Done | 48 |
| ritz1 | ✅ Done | 9 |
| **Total** | **883 tests** | **95 files** |

---

## Executive Summary

RERITZ is a comprehensive language overhaul based on LARB's (Language Architecture Review Board) analysis. The goal: make Ritz **sexy and safe** — a language you *want* to play with.

### Scope

| Category | Count | Impact |
|----------|-------|--------|
| ritz0 Python modules | 30 | Core compiler changes |
| ritzlib modules | 35 | API redesign |
| Example .ritz files | 124 | Syntax updates |
| Test .ritz files | 100+ | Verification |
| Dual compiler tests | 41 | Compatibility |
| ritzunit | External project | Test framework update |
| ritz1 (self-hosted) | 1 project | Must be updated |

### Sexiness Rating Target

**Current:** 7/10 → **Goal:** 9/10

---

## Table of Contents

1. [Critical Changes](#1-critical-changes)
2. [Syntax Overhaul](#2-syntax-overhaul)
3. [String System Redesign](#3-string-system-redesign)
4. [Reference Philosophy](#4-reference-philosophy)
5. [Kernel/Unsafe Support (Issue #118)](#5-kernelunafe-support-issue-118)
6. [Grammar & Parser Changes](#6-grammar--parser-changes)
7. [Migration Strategy](#7-migration-strategy)
8. [Phase Plan](#8-phase-plan)
9. [Testing Strategy](#9-testing-strategy)
10. [Rollback Plan](#10-rollback-plan)

---

## 1. Critical Changes

### 1.1 Summary Table

| Change | Current | Proposed | Priority |
|--------|---------|----------|----------|
| Address-of operator | `&x` | `@x` | P0 |
| Attributes | `@test` | `[[test]]` | P0 |
| Reference types | `&T`, `&mut T` | `@T`, `@&T` | P0 |
| Const borrow param | `data: &T` | `data: T` | P0 |
| Mutable borrow param | `data: &mut T` | `data:& T` | P0 |
| Move param | `data: T` (implicit) | `data:= T` | P0 |
| String literal default | `String` (heap) | `StrView` (zero-copy) | P1 |
| C-string literal | `c"hello"` | `"hello".as_cstr()` | P1 |
| Span string literal | `s"hello"` | `"hello"` (default) | P1 |
| Logical operators | Both `&&`/`and` | `&&`/`||` only | P2 |

### 1.2 The Philosophy

**Three core insights from LARB:**

1. **Zero-copy by default** — Literals shouldn't allocate. `"hello"` returns a view.
2. **References by default** — `*T` only for FFI/kernel. Normal code uses `@T`.
3. **Clean call sites** — The function signature carries ownership info, not the call site.

---

## 2. Syntax Overhaul

### 2.1 Address-Of: `&` → `@`

**Rationale:** Disambiguate from bitwise AND, memorable "at" mnemonic.

```ritz
# Current
let ptr = &x           # Address-of
let mask = a & b       # Bitwise AND (same symbol!)

# Proposed
let ptr = @x           # Address-of ("at" x)
let mask = a & b       # Bitwise AND (unambiguous)
```

### 2.2 Attributes: `@name` → `[[name]]`

**Rationale:** Frees `@` for address-of, visually distinct from code.

```ritz
# Current
@test
@inline
@packed
fn my_function()

# Proposed
[[test]]
[[inline]]
[[packed]]
fn my_function()
```

**Multiple attributes:**
```ritz
[[test, inline]]
fn fast_test()

# Or stacked:
[[test]]
[[ignore("slow")]]
fn slow_test()
```

### 2.3 Reference Types: `&T` → `@T`

| Current | Proposed | Meaning |
|---------|----------|---------|
| `&T` | `@T` | Immutable reference |
| `&mut T` | `@&T` | Mutable reference |
| `*T` | `*T` | Raw pointer (unchanged) |
| `*mut T` | `*&T` | Raw mutable pointer |

**Mnemonic:** The `&` means "mutable" in the new syntax — it's the modifier.

```ritz
# Current
fn read(data: &User)
fn modify(data: &mut User)

# Proposed
fn read(data: @User)
fn modify(data: @&User)
```

### 2.4 Parameter Passing: Colon-Modifier Syntax

**The killer feature:** Clean call sites!

| Intent | Current | Proposed | Call Site |
|--------|---------|----------|-----------|
| Const borrow | `data: &T` | `data: T` | `func(x)` |
| Mutable borrow | `data: &mut T` | `data:& T` | `func(x)` |
| Move ownership | `data: T` | `data:= T` | `func(x)` |

**Note:** No space between `:` and modifier (`:&`, `:=`).

```ritz
# Current (noisy call sites)
fn read(data: &Connection)
fn modify(data: &mut Connection)
fn consume(data: Connection)

read(&conn)           # Must annotate
modify(&mut conn)     # Must annotate
consume(conn)         # Implicit move

# Proposed (clean call sites)
fn read(data: Connection)      # Const borrow (`:`)
fn modify(data:& Connection)   # Mutable borrow (`:&`)
fn consume(data:= Connection)  # Move (`:=`)

read(conn)            # Just pass it
modify(conn)          # Just pass it
consume(conn)         # Just pass it
```

### 2.5 The Semantic Triangle

For Copy types (`i32`, `f64`, `bool`, etc.):

| Syntax | Meaning |
|--------|---------|
| `x: i32` | Pass by value (copied) |
| `x:& i32` | Pass by reference (can modify) |
| `x:= i32` | Pass by value + "I'm done with this" hint |

For non-Copy types:

| Syntax | Meaning |
|--------|---------|
| `x: User` | Const borrow (caller keeps ownership) |
| `x:& User` | Mutable borrow (caller keeps ownership) |
| `x:= User` | Move (ownership transfers to callee) |

### 2.6 Taking References

```ritz
# Immutable reference
let r = @x              # r: @T

# Mutable reference
let r = @&x             # r: @&T
```

---

## 3. String System Redesign

### 3.1 Current State (Problematic)

```ritz
"hello"     # String (heap-allocated, owned)
c"hello"    # *u8 (C-string, null-terminated)
s"hello"    # Span<u8> (slice with length)
```

**Problems:**
- `c""` and `s""` prefixes are cryptic
- Default `"hello"` allocates — wasteful for literals
- No clear type hierarchy

### 3.2 Proposed Type Hierarchy

```
Str (trait)
├── StrView          # Zero-copy slice (ptr + len), immutable
├── String           # Owned, heap-allocated, growable
├── StrBuf<N>        # Fixed-capacity buffer (stack/inline)
└── CStr             # Null-terminated C string (FFI only)
```

### 3.3 New Literal Syntax

```ritz
# Default: zero-copy view (most common case)
let greeting = "hello"          # StrView (no allocation!)

# Explicit owned string when needed
let name = String.from("world") # String (heap)
let name = "world".to_string()  # Alternative

# Fixed buffer for performance
var buf: StrBuf<64>
buf.push_str("prefix: ")

# C strings only for FFI (explicit conversion)
extern fn puts(s: CStr) -> i32
puts("hello".as_cstr())
```

### 3.4 Migration Table

| Current | Proposed | Notes |
|---------|----------|-------|
| `"hello"` | `"hello"` | Now returns `StrView` |
| `c"hello"` | `"hello".as_cstr()` | Explicit FFI |
| `s"hello"` | `"hello"` | Default is now zero-copy |
| `String::from(...)` | `String.from(...)` | Same semantics |

### 3.5 String Types in Detail

```ritz
# StrView - the default, zero-copy
struct StrView
    ptr: *u8
    len: i64

impl StrView
    fn len(self: StrView) -> i64
    fn is_empty(self: StrView) -> bool
    fn as_cstr(self: StrView) -> CStr   # FFI helper
    fn to_string(self: StrView) -> String  # Allocates

# String - heap-allocated, growable
struct String
    ptr: *u8
    len: i64
    cap: i64

impl String
    fn new() -> String
    fn from(s: StrView) -> String
    fn push_str(self:& String, s: StrView)
    fn view(self: String) -> StrView

# StrBuf<N> - fixed capacity, no heap
struct StrBuf<N>
    data: [N]u8
    len: i64

# CStr - null-terminated, for FFI
struct CStr
    ptr: *u8

impl CStr
    fn as_ptr(self: CStr) -> *u8
```

---

## 4. Reference Philosophy

### 4.1 The Problem

The current codebase is littered with raw pointers:

```ritz
# Current (C-style, unsafe)
fn get_user(id: i64) -> *User
fn process(data: *u8, len: i64)
fn callback(ctx: *mut Context)
```

### 4.2 The Solution

References by default, pointers only for FFI/kernel:

```ritz
# Proposed (safe)
fn get_user(id: i64) -> Option<@User>
fn process(data: StrView)
fn callback(ctx:& Context)
```

### 4.3 When to Use What

| Concept | Syntax | When to Use |
|---------|--------|-------------|
| Immutable reference | `@T` | Read-only access (most params) |
| Mutable reference | `@&T` | Modification without ownership |
| Owned value | `T` / `:= T` | Ownership transfer |
| Raw pointer | `*T` | FFI, kernel, `unsafe` blocks |

### 4.4 ritzlib Audit Required

Every module needs review:

| Module | Current | Proposed |
|--------|---------|----------|
| `io.ritz` | `read(fd, buf: *u8, len)` | `read(fd, buf:& [u8])` |
| `gvec.ritz` | `vec_get(v: *Vec) -> *T` | `v.get(i) -> Option<@T>` |
| `str.ritz` | `strlen(s: *u8)` | `s.len()` method |
| `memory.ritz` | `memcpy(dst: *u8, src: *u8)` | `dst.copy_from(src)` |
| All 35 modules | Pointer-heavy | Reference-based |

---

## 5. Kernel/Unsafe Support (Issue #118)

Issue #118 requests features for the Harland microkernel. These fit naturally into RERITZ:

### 5.1 Attributes (New Syntax)

```ritz
# Packed structs (no padding)
[[packed]]
struct IDTEntry
    offset_low: u16
    selector: u16
    ist: u8
    type_attr: u8
    offset_mid: u16
    offset_high: u32
    zero: u32

# Naked functions (no prologue/epilogue)
[[naked]]
fn isr_stub_0()
    asm x86_64:
        push 0
        push 0
        jmp isr_common
```

### 5.2 Inline Assembly

```ritz
fn outb(port: u16, value: u8)
    asm x86_64:
        mov dx, {port}
        mov al, {value}
        out dx, al

fn inb(port: u16) -> u8
    var result: u8
    asm x86_64:
        mov dx, {port}
        in al, dx
        mov {result}, al
    return result
```

### 5.3 Unsafe Blocks

Pointers are only freely usable inside `unsafe` blocks:

```ritz
# Safe code - references only
fn process(data: StrView)
    for byte in data
        handle(byte)

# Unsafe code - raw pointers allowed
fn write_vga(char: u8)
    unsafe
        let ptr = 0xB8000 as *&u16  # *&T = mutable raw pointer
        *ptr = (0x0F << 8) | (char as u16)
```

### 5.4 Freestanding Target

```bash
ritz build --target x86_64-none-elf src/kernel.ritz
```

Compiler flags:
- No libc (already true)
- No stack protector
- No red zone
- ELF output

---

## 6. Grammar & Parser Changes

### 6.1 New Tokens Required

```python
# In ritz0/tokens.py

class TokenType(Enum):
    # ... existing ...

    # New tokens for RERITZ
    AT = auto()            # @ (address-of, was attribute prefix)
    LBRACKET2 = auto()     # [[ (attribute start)
    RBRACKET2 = auto()     # ]] (attribute end)
    COLON_AMP = auto()     # :& (mutable borrow param)
    COLON_EQ = auto()      # := (move param)
    AT_AMP = auto()        # @& (mutable reference / take mut ref)
    STAR_AMP = auto()      # *& (mutable raw pointer type)

    # Assembly support (Issue #118)
    ASM = auto()           # asm keyword
```

### 6.2 Lexer Changes

```python
# In ritz0/lexer.py

# New multi-char tokens:
# [[  -> LBRACKET2
# ]]  -> RBRACKET2
# :&  -> COLON_AMP
# :=  -> COLON_EQ
# @&  -> AT_AMP
# *&  -> STAR_AMP

# @ now means address-of (no longer attribute prefix)
# Attributes are [[name]] instead of @name
```

### 6.3 Parser Changes

```python
# Parameter parsing
def parse_param(self):
    name = self.expect(IDENT)

    if self.match(COLON_AMP):    # :& T
        typ = self.parse_type()
        return Param(name, typ, borrow=Borrow.MUTABLE)

    elif self.match(COLON_EQ):   # := T
        typ = self.parse_type()
        return Param(name, typ, borrow=Borrow.MOVE)

    else:                         # : T
        self.expect(COLON)
        typ = self.parse_type()
        return Param(name, typ, borrow=Borrow.CONST)

# Attribute parsing
def parse_attributes(self):
    attrs = []
    while self.match(LBRACKET2):  # [[
        while True:
            attr = self.parse_attribute()
            attrs.append(attr)
            if not self.match(COMMA):
                break
        self.expect(RBRACKET2)     # ]]
    return attrs

# Type parsing
def parse_type(self):
    if self.match(AT_AMP):        # @&T
        inner = self.parse_type()
        return RefType(inner, mutable=True)

    elif self.match(AT):          # @T
        inner = self.parse_type()
        return RefType(inner, mutable=False)

    elif self.match(STAR_AMP):    # *&T
        inner = self.parse_type()
        return PtrType(inner, mutable=True)

    elif self.match(STAR):        # *T
        inner = self.parse_type()
        return PtrType(inner, mutable=False)

    # ... rest of type parsing
```

### 6.4 AST Changes

```python
# In ritz0/ritz_ast.py

class Borrow(Enum):
    CONST = auto()    # : T  (default)
    MUTABLE = auto()  # :& T
    MOVE = auto()     # := T

@dataclass
class Param:
    name: str
    type: Type
    borrow: Borrow = Borrow.CONST

@dataclass
class RefType:
    inner: Type
    mutable: bool = False  # @T vs @&T

@dataclass
class AddressOf:
    expr: Expr
    mutable: bool = False  # @x vs @&x
```

---

## 7. Migration Strategy

### 7.1 Compatibility Flags

During transition, support both syntaxes:

```bash
# Phase 1: New syntax optional
ritz build --syntax=reritz src/main.ritz

# Phase 2: New syntax default, old available
ritz build src/main.ritz                    # Uses new
ritz build --syntax=legacy src/main.ritz    # Uses old

# Phase 3: Old syntax removed
ritz build src/main.ritz                    # New only
```

### 7.2 Migration Script

Create `tools/migrate_reritz.py`:

```python
# Automated transformations:
# 1. @attr -> [[attr]]
# 2. &x -> @x (address-of contexts)
# 3. &T -> @T (type contexts)
# 4. &mut T -> @&T
# 5. c"..." -> "...".as_cstr()
# 6. s"..." -> "..."
# 7. data: &T -> data: T (params)
# 8. data: &mut T -> data:& T (params)
```

### 7.3 Migration Order

```
1. ritz0 compiler (enables new syntax)
   ├── tokens.py
   ├── lexer.py
   ├── parser.py
   ├── ritz_ast.py
   ├── type_checker.py
   └── emitter_llvmlite.py

2. Core ritzlib (needed for examples)
   ├── sys.ritz
   ├── io.ritz
   ├── memory.ritz
   ├── str.ritz (+ new StrView)
   └── string.ritz

3. Tier 1 examples (basics)
   └── 01_hello through 10_sleep

4. ritzunit (test framework)
   └── Must work before running tests!

5. Remaining tiers
   ├── Tier 2: stdlib
   ├── Tier 3: coreutils
   ├── Tier 4: applications
   └── Tier 5: async

6. ritz1 self-hosted compiler

7. External projects
   ├── squeeze
   ├── valet
   ├── cryptosec
   └── harland
```

---

## 8. Phase Plan

### Phase 0: Foundation (Week 1)

**Goal:** New tokens and basic parsing

- [ ] Add new tokens to `tokens.py`
- [ ] Update lexer for `[[]]`, `:&`, `:=`, `@&`, `*&`
- [ ] Update parser for new attribute syntax
- [ ] Add `--syntax=reritz` flag
- [ ] Write unit tests for lexer/parser

**Milestone:** Can parse `[[test]]` and `:&` syntax

### Phase 1: Type System (Week 2)

**Goal:** New reference types work

- [ ] Update AST for `Borrow` enum, `RefType`
- [ ] Update type checker for `@T`, `@&T`
- [ ] Update emitter for new calling convention
- [ ] Implicit borrow at call sites

**Milestone:** Can compile functions with new param syntax

### Phase 2: Core ritzlib (Week 3)

**Goal:** Fundamental modules migrated

- [ ] Migrate `sys.ritz`
- [ ] Migrate `io.ritz`
- [ ] Migrate `memory.ritz`
- [ ] Create `strview.ritz` (new StrView type)
- [ ] Update `str.ritz` and `string.ritz`

**Milestone:** Can print "Hello, world!" with new syntax

### Phase 3: Tier 1 Examples (Week 4)

**Goal:** Basic examples work

- [ ] Migrate `01_hello`
- [ ] Migrate `02_exitcode`
- [ ] ... through `10_sleep`
- [ ] All tier 1 tests pass

**Milestone:** `make test-tier1` passes

### Phase 4: ritzunit (Week 4-5)

**Goal:** Test framework works with new syntax

- [ ] Migrate ritzunit to new syntax
- [ ] Update `[[test]]` attribute handling
- [ ] Verify test discovery works

**Milestone:** Can run Ritz tests with new syntax

### Phase 5: Full Migration (Weeks 5-8)

**Goal:** Everything migrated

- [ ] Tier 2 examples
- [ ] Tier 3 examples
- [ ] Tier 4 examples
- [ ] Tier 5 async examples
- [ ] All ritzlib modules
- [ ] All test files
- [ ] ritz1 self-hosted compiler

**Milestone:** `make test && make regression` passes

### Phase 6: Issue #118 Features (Week 8+)

**Goal:** Kernel support

- [x] `asm x86_64:` blocks ✅ DONE
- [x] `[[packed]]` attribute ✅ DONE
- [x] `[[naked]]` attribute ✅ DONE
- [ ] `unsafe` blocks
- [ ] `--target x86_64-none-elf`

**Milestone:** Harland kernel compiles

### Phase 7: Documentation & Cleanup (Ongoing)

- [ ] Update `docs/LANGUAGE.md`
- [ ] Update `STYLE.md`
- [ ] Update `CONTRIBUTING.md`
- [ ] Remove `--syntax=legacy` flag
- [ ] Final cleanup

---

## 9. Testing Strategy

### 9.1 Test Levels

| Level | Examples | Tests |
|-------|----------|-------|
| Unit | N/A | `ritz0/test_*.py` |
| Tier 1 | 01-10 | Basic functionality |
| Tier 2 | 11-20 | stdlib usage |
| Tier 3 | 21-32 | Coreutils |
| Tier 4 | 33-73 | Applications |
| Tier 5 | 74-76 | Async |
| Integration | All | `make regression` |

### 9.2 Regression Testing

```bash
# Run after each phase
make test              # Unit tests
make test-tier1        # Tier 1 examples
make test-examples     # All examples
make regression-quick  # Stages 1-3
make regression        # Full 4-stage
```

### 9.3 Parallel Testing

Two syntax modes during transition:

```bash
# Test old syntax still works
RITZ_SYNTAX=legacy make test

# Test new syntax
RITZ_SYNTAX=reritz make test
```

---

## 10. Rollback Plan

### 10.1 Git Strategy

```bash
# The reritz branch is isolated
git checkout reritz    # All changes here

# If things go wrong
git checkout main      # Back to stable

# When ready
git checkout main
git merge reritz       # Bring in changes
```

### 10.2 Feature Flags

```python
# In ritz0/ritz0.py
RERITZ_SYNTAX = os.environ.get('RITZ_SYNTAX', 'legacy') == 'reritz'

# Gradually enable:
# Phase 1: RERITZ_SYNTAX=False (default)
# Phase 2: RERITZ_SYNTAX=True (default)
# Phase 3: Remove flag, new syntax only
```

### 10.3 Compatibility Shims

For external projects, provide a compatibility layer:

```ritz
# ritzlib/compat.ritz
# Aliases for old names during transition

pub type CStr = *u8  # Temporary alias
pub fn c_str(s: StrView) -> *u8
    s.as_cstr().as_ptr()
```

---

## Appendix A: Complete Syntax Comparison

### A.1 Functions

```ritz
# Current
fn process(data: &Vec<User>, config: &Config) -> Result<(), Error>

# Proposed
fn process(data: Vec<User>, config: Config) -> Result<(), Error>
```

### A.2 Methods

```ritz
# Current
impl Vec<T>
    fn push(self: &mut Vec<T>, item: T)
    fn len(self: &Vec<T>) -> i64

# Proposed
impl Vec<T>
    fn push(self:& Vec, item:= T)
    fn len(self: Vec) -> i64
```

### A.3 Structs

```ritz
# Current
struct Node
    value: i32
    next: *Node

# Proposed (same for now, pointers OK in structs)
struct Node
    value: i32
    next: *Node
```

### A.4 Attributes

```ritz
# Current
@test
@inline
fn fast_test()

# Proposed
[[test]]
[[inline]]
fn fast_test()

# Or combined
[[test, inline]]
fn fast_test()
```

### A.5 Strings

```ritz
# Current
let s = "hello"              # String (heap)
let c = c"hello"             # *u8
let span = s"hello"          # Span<u8>

# Proposed
let s = "hello"              # StrView (zero-copy!)
let owned = "hello".to_string()  # String (explicit heap)
let cstr = "hello".as_cstr()     # CStr (explicit FFI)
```

### A.6 References

```ritz
# Current
let r: &User = &user
let mr: &mut User = &mut user

# Proposed
let r: @User = @user
let mr: @&User = @&user
```

---

## Appendix B: Error Message Examples

### B.1 Pointer in Safe Code

```
Error: Raw pointer used outside unsafe block
  --> src/main.ritz:10:5
   |
10 |     let ptr = 0xB8000 as *u16
   |               ^^^^^^^^^^^^^^^^ raw pointers require `unsafe`
   |
   = help: wrap this in an `unsafe` block:

     unsafe
         let ptr = 0xB8000 as *u16
```

### B.2 Missing Move Annotation

```
Error: Value moved without `:=` annotation
  --> src/main.ritz:15:5
   |
12 |     fn consume(data: Connection)  # Implicit move
   |                ---- function takes ownership here
   ...
15 |     consume(conn)
   |             ^^^^ value moved here
   |
   = help: if this is intentional, use `:=` in the signature:

     fn consume(data:= Connection)
```

---

## Appendix C: Checklist

### C.1 Compiler Changes

- [ ] `tokens.py`: Add new token types
- [ ] `lexer.py`: Recognize new tokens
- [ ] `parser.py`: Parse new syntax
- [ ] `ritz_ast.py`: New AST nodes
- [ ] `type_checker.py`: Handle new types
- [ ] `emitter_llvmlite.py`: Generate correct LLVM IR
- [ ] `move_checker.py`: Validate ownership
- [ ] Unit tests for all changes

### C.2 ritzlib Changes

- [ ] `sys.ritz`: Update signatures
- [ ] `io.ritz`: Update signatures
- [ ] `memory.ritz`: Update signatures
- [ ] `strview.ritz`: New module
- [ ] `str.ritz`: Update for StrView
- [ ] `string.ritz`: Update for StrView
- [ ] `gvec.ritz`: Reference-based API
- [ ] `span.ritz`: Integrate with StrView
- [ ] All 35 modules audited

### C.3 Examples

- [ ] Tier 1: 10 examples
- [ ] Tier 2: 10 examples
- [ ] Tier 3: 12 examples
- [ ] Tier 4: 41 examples
- [ ] Tier 5: 3 examples

### C.4 External Projects

- [ ] ritzunit
- [ ] squeeze
- [ ] valet
- [ ] cryptosec
- [ ] harland (Issue #118)

---

*This document is the authoritative plan for the RERITZ overhaul. All changes should reference this document.*
