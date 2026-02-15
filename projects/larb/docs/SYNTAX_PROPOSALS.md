# Ritz Syntax Proposals

**LARB Document** | **Status:** Draft | **Date:** 2026-02-13

This document explores syntax alternatives for core Ritz concepts, focusing on making the language feel native rather than derivative.

---

## Table of Contents

1. [Address-Of Operator](#1-address-of-operator)
2. [Ownership & Borrowing Syntax](#2-ownership--borrowing-syntax)
3. [Sigil Budget](#3-sigil-budget)
4. [Comparison Matrix](#4-comparison-matrix)
5. [Recommendations](#5-recommendations)
6. [Memory Allocation APIs](#6-memory-allocation-apis)

---

## 1. Address-Of Operator

### 1.1 Current State

The `&` symbol is overloaded:

| Context | Meaning |
|---------|---------|
| `&x` | Take address of / borrow x |
| `a & b` | Bitwise AND |
| `&T` | Reference type |
| `&mut T` | Mutable reference type |

This creates parsing ambiguity and cognitive load.

### 1.2 Proposal: `@` for Address-Of

Use `@` to mean "at this address":

```ritz
# Take address of x (where is x "at"?)
let ptr = @x

# Types
fn read(data: @i32)           # Pointer to i32
fn read(data: @const i32)     # Const pointer? Or...
```

**Mnemonic:** "at" → `@` → "where is it at?"

### 1.3 Analysis

| Aspect | `&` (Current) | `@` (Proposed) |
|--------|---------------|----------------|
| Familiar to C/Rust devs | ✅ Yes | ❌ Learning curve |
| Disambiguates from bitwise AND | ❌ No | ✅ Yes |
| Visual distinctiveness | Medium | High |
| Already used in Ritz | For attributes `@test` | Conflict! |

**Problem:** `@` is already used for attributes (`@test`, `@inline`).

### 1.4 Alternative: Keep `&` but Require Spaces for Bitwise

```ritz
# Address-of (no space)
let ptr = &x

# Bitwise AND (requires spaces)
let mask = a & b    # Bitwise AND
let bad = a&b       # Error: ambiguous, use spaces
```

This is how Rust handles it implicitly.

### 1.5 Decision Point

| Option | Pros | Cons |
|--------|------|------|
| A: Keep `&` | Familiar, no migration | Overloaded |
| B: Use `@` for address | Clear, distinct | Conflicts with attributes |
| C: Use `@` for attributes AND address | Works if context differs | May confuse |
| D: Change attribute syntax | Frees `@` | Breaking change |

**If we go with `@` for address-of**, we'd need to change attribute syntax:

```ritz
# Alternative attribute syntaxes:
#[test]           # Rust-style (uses # which is comment)
[[test]]          # C++-style
@[test]           # Bracketed @
#:test            # Reader macro style
```

---

## 2. Ownership & Borrowing Syntax

### 2.1 Current State (Rust-like)

```ritz
fn process(data: T)           # Move (takes ownership)
fn read(data: &T)             # Immutable borrow
fn modify(data: &mut T)       # Mutable borrow
```

**Concerns raised:**
- Feels like a Rust rip-off
- `&mut` is verbose
- Not immediately intuitive what `&` means

### 2.2 Proposal A: Colon-Modifier Syntax (Recommended)

```ritz
fn read(data: T)              # Const borrow (default, most common)
fn modify(data:& T)           # Mutable borrow (colon-ampersand, no space)
fn consume(data:= T)          # Move (colon-equals, no space)
```

**Rationale:**
- Most function params are "just reading" → make that the default (`:`)
- Mutation is special → mark it with `:&`
- Ownership transfer is rare → mark it with `:=`
- No space between colon and modifier makes it a single token/glyph

**Syntax breakdown:**

| Modifier | Meaning | Mnemonic |
|----------|---------|----------|
| `:`  | Const borrow | Plain colon = "just looking" |
| `:&` | Mutable borrow | Ampersand = "reference you can change" |
| `:=` | Move ownership | Assignment = "becomes yours" |

**Analysis:**

| Aspect | Assessment |
|--------|------------|
| Default is borrow | ✅ Matches common case (70% of params) |
| `:&` for mutable | ✅ Distinct from plain borrow |
| `:=` for move | ✅ Evokes assignment/transfer |
| Parsing | ✅ `:&` and `:=` are distinct two-char tokens |
| Learning curve | ✅ Three simple modifiers to learn |

**Advantage:** The `&` in `:&` means "mutable reference" which aligns with Rust/C++ mental models—you're passing a mutable reference, not a const one.

### 2.2.1 The Copy Type Alignment (Happy Accident!)

For `Copy` types (`i32`, `f64`, `bool`, etc.), `:` (const borrow) has identical semantics to pass-by-value:

```ritz
fn add(a: i32, b: i32) -> i32    # Just works — no sigils needed
    a + b
```

This means **90% of code has zero syntactic overhead**:

| Type Kind | `x: T` means | Effect |
|-----------|--------------|--------|
| Copy types | Pass by value | Copied (cheap, it's just bytes) |
| Non-Copy types | Const borrow | Caller retains ownership, callee gets read-only view |

The minimalist syntax (`:`) is also the most common case. Sigils (`:&`, `:=`) only appear when you're doing something special:

```ritz
# Common case — clean, no ceremony
fn calculate(x: i32, y: i32) -> i32
fn print_user(user: User)
fn format(msg: StrView) -> String

# Special cases — sigils signal intent
fn update(player:& Player, delta: i32)    # Mutation
fn consume(conn:= Connection)              # Ownership transfer
```

**Result:** Ritz code looks cleaner than Rust because the common path (read-only access) is unmarked.

### 2.2.2 The Semantic Triangle (Three Happy Accidents)

The colon-modifier syntax has elegant emergent properties for both Copy and non-Copy types:

| Syntax | Copy Types | Non-Copy Types | Intent |
|--------|------------|----------------|--------|
| `x: T` | Pass by value | Immutable borrow | "Just looking" |
| `x:& T` | **Pass by reference!** | Mutable borrow | "You can change this" |
| `x:= T` | Pass by value + liveness hint | Move ownership | "It's yours now" |

**Accident 1: `:&` is pass-by-reference for primitives**

```ritz
fn increment(x:& i32)
    x += 1

var n = 5
increment(n)      # Just pass n — compiler knows fn takes :&, passes by reference
# n is now 6
```

This is C-style pass-by-reference, but the call site is clean! The function signature declares the intent (`:&`), and the compiler handles the mechanics. No `&n` at the call site.

**Accident 2: `:=` on Copy types signals "I'm done with this"**

```ritz
fn process(x:= i32)
    # ...

var counter = 42
process(counter)   # Just pass counter — compiler sees := and can optimize
# Compiler hint: counter isn't used past this point
```

Even though `i32` is Copy and *could* be used again, the `:=` in the function signature signals programmer intent: "this variable is conceptually handed off." Useful for:
- Readability (reviewer knows counter won't be used later)
- Optimization (compiler can reuse stack slot)
- Linting ("you marked counter as moved but used it again")

**Accident 3: Complete disambiguation of `&`**

With `@` for address-of, `&` is *only* bitwise AND:

```ritz
let addr = @n           # Address-of (where is n "at"?)
let mask = a & b        # Bitwise AND (unambiguous!)
increment(n)            # Just pass n — fn signature says :&
```

Three concepts, three distinct syntaxes, zero overloading.

**The killer feature: Clean call sites**

In Rust, you write `&x` or `&mut x` at every call site. In Ritz, call sites are always just `foo(x)`:

```ritz
# Rust
increment(&mut n);
read(&data);
consume(conn);

# Ritz — always clean
increment(n)
read(data)
consume(conn)
```

The function signature tells the whole story. The call site is uncluttered.

### 2.3 Proposal B: Keyword-Based

```ritz
fn read(data: T)              # Const borrow (default)
fn modify(mut data: T)        # Mutable borrow
fn consume(own data: T)       # Move (takes ownership)
```

Or with `ref`:

```ritz
fn read(ref data: T)          # Const borrow
fn modify(ref mut data: T)    # Mutable borrow
fn consume(data: T)           # Move (default? or explicit `move`?)
```

### 2.4 Proposal C: Explicit Keywords for Everything

```ritz
fn read(borrow data: T)       # Immutable borrow
fn modify(borrow mut data: T) # Mutable borrow
fn consume(move data: T)      # Move

# Or shorter:
fn read(ref data: T)          # Immutable borrow
fn modify(mut data: T)        # Mutable borrow
fn consume(own data: T)       # Move
```

### 2.5 Proposal D: Different Sigils

What if we use completely different symbols?

```ritz
fn read(data: ~T)             # Borrow (tilde = "approximately T")
fn modify(data: ~mut T)       # Mutable borrow
fn consume(data: T)           # Move (no sigil = owned)

# Or with arrows:
fn read(data: ->T)            # Borrow (pointing at T)
fn modify(data: <->T)         # Mutable borrow (bidirectional)
fn consume(data: T)           # Move
```

### 2.6 Proposal E: Context-Dependent (Swift-like)

```ritz
fn read(data: T)              # Borrow by default for structs
fn modify(data: inout T)      # Mutable borrow (Swift keyword)
fn consume(data: consuming T) # Move (explicit)
```

### 2.7 Proposal F: Let Type System Infer

```ritz
fn read(data: T)
    # Compiler sees only reads → immutable borrow

fn modify(data: T)
    data.x = 5                # Compiler sees mutation → mutable borrow

fn consume(data: T)
    let other = data          # Compiler sees move → ownership transfer
```

**Problem:** This makes function signatures lie about their behavior. Caller can't know without reading the body.

### 2.8 The "Most Common Case" Analysis

In real codebases, what's the frequency?

| Pattern | Frequency | Current Syntax | Proposed A |
|---------|-----------|----------------|------------|
| Read-only access | ~70% | `&T` | `T` |
| Mutation | ~20% | `&mut T` | `&T` |
| Ownership transfer | ~10% | `T` | `:= T` |

If 70% of params are read-only, making that the shortest/default makes sense.

---

## 3. Sigil Budget

Ritz should have a small, memorable set of sigils:

### 3.1 Current Sigil Usage

| Sigil | Meaning(s) |
|-------|------------|
| `&` | Address-of, reference type, bitwise AND |
| `*` | Dereference, pointer type, multiplication |
| `@` | Attribute prefix |
| `?` | Try/propagate error |
| `!` | Logical NOT |
| `~` | Bitwise NOT |
| `:` | Type annotation |
| `::` | Path separator |
| `->` | Return type, pointer member access |
| `=>` | Match arm |

### 3.2 Proposed Sigil Reassignment

| Sigil | New Meaning | Notes |
|-------|-------------|-------|
| `@` | Address-of | "at" mnemonic |
| `&` | Bitwise AND only | Disambiguated |
| `#[...]` | Attributes | Rust-style |
| `:=` | Move assignment/param | Distinct |
| `~` | Bitwise NOT | Keep |

### 3.3 Attribute Syntax Options

If we free `@` for address-of:

```ritz
# Option 1: Rust-style (but # is comment!)
#[test]
fn test_foo()

# Option 2: Double brackets
[[test]]
fn test_foo()

# Option 3: Bang prefix
!test
fn test_foo()

# Option 4: Backtick
`test
fn test_foo()

# Option 5: Dollar (unused)
$test
fn test_foo()
```

**Recommendation:** `[[test]]` - visually distinct, doesn't conflict with anything.

---

## 4. Comparison Matrix

### 4.1 Address-Of Syntax

| Code | Current | Proposal (@ for addr) |
|------|---------|----------------------|
| Take address | `&x` | `@x` |
| Bitwise AND | `a & b` | `a & b` |
| Reference type | `&T` | `@T` |
| Mut ref type | `&mut T` | `@&T` |
| Attributes | `@test` | `[[test]]` |

### 4.2 Parameter Passing

| Intent | Current | Proposal A (Recommended) | Proposal B |
|--------|---------|--------------------------|------------|
| Read-only | `data: &T` | `data: T` | `ref data: T` |
| Mutable | `data: &mut T` | `data:& T` | `mut data: T` |
| Move | `data: T` | `data:= T` | `own data: T` |

### 4.3 Full Example: Current vs Proposed

**Current (Rust-like):**
```ritz
@test
fn test_connection()
    var conn = Connection.new()
    let addr = &conn.address       # Address-of
    let mask = flags & 0xFF        # Bitwise AND
    process(&conn)                 # Borrow
    modify(&mut conn)              # Mutable borrow
    consume(conn)                  # Move
```

**Proposed (colon-modifier syntax, `@` for address):**
```ritz
[[test]]
fn test_connection()
    var conn = Connection.new()
    let addr = @conn.address       # Address-of (clear!)
    let mask = flags & 0xFF        # Bitwise AND (unambiguous!)
    process(conn)                  # Borrow (default, fn takes `data: T`)
    modify(conn)                   # Mutable borrow (fn takes `data:& T`)
    consume(conn)                  # Move (fn takes `data:= T`)
```

**Proposed (keyword-based):**
```ritz
[[test]]
fn test_connection()
    var conn = Connection.new()
    let addr = @conn.address       # Address-of
    let mask = flags & 0xFF        # Bitwise AND
    process(ref conn)              # Borrow
    modify(mut conn)               # Mutable borrow
    consume(move conn)             # Move
```

---

## 5. Recommendations

### 5.1 High Confidence

| Change | Rationale |
|--------|-----------|
| **Use `@` for address-of** | Clear "at" mnemonic, disambiguates from `&` |
| **Change attributes to `[[name]]`** | Frees `@`, visually distinct |
| **Keep `&` for bitwise AND only** | Single meaning, familiar |

### 5.2 Needs Discussion

| Change | Options | Trade-offs |
|--------|---------|------------|
| **Borrow syntax** | A: `T`/`&T`/`:= T` | Compact but `&` = mutable is backwards |
| | B: Keywords | Verbose but clear |
| | C: Infer from usage | Signatures don't tell the story |

### 5.3 Concrete Proposal for Discussion

**Option A (Colon-modifier syntax — Recommended):**

```ritz
# Types
T           # Owned value
@T          # Immutable reference (can't modify through this)
@&T      # Mutable reference (can modify)
*T          # Raw pointer (FFI/kernel only)

# Parameters (note: no space between colon and modifier)
fn read(data: T)              # Immutable borrow (`:` = const borrow)
fn modify(data:& T)           # Mutable borrow (`:&` = mutable borrow)
fn consume(data:= T)          # Move (`:=` = take ownership)

# Taking address
let ptr = @x                  # Address of x
let mptr = @&x                # Mutable reference to x

# Attributes
[[test]]
[[inline]]
```

**How the compiler knows:**
- `:` (colon-space) means const borrow — caller retains ownership, callee gets read-only view
- `:&` (colon-ampersand) means mutable borrow — caller retains ownership, callee can modify
- `:=` (colon-equals) means move — ownership transfers to callee

**Copy types:** Primitives (`i32`, `f64`, etc.) are `Copy` and passed by value regardless. The borrow semantics apply to non-Copy types.

**Option B (Keyword-based, clearer):**

```ritz
# Parameters
fn read(data: @T)             # Immutable borrow
fn modify(data: @&T)       # Mutable borrow
fn consume(data: T)           # Move (default = ownership)

# This is more explicit:
fn consume(move data: T)      # Move (keyword makes it clear)
fn read(ref data: T)          # Borrow
fn modify(ref mut data: T)    # Mutable borrow
```

### 5.4 What Other Languages Do

| Language | Borrow | Mut Borrow | Move | Address |
|----------|--------|------------|------|---------|
| **Rust** | `&T` | `&mut T` | `T` | `&x` |
| **C++** | `const T&` | `T&` | `T` | `&x` |
| **Swift** | `T` (inout for mut) | `inout T` | consuming | (no pointers) |
| **Zig** | `*const T` | `*T` | owned | `&x` |
| **D** | `in T` | `ref T` | move | `&x` |

### 5.5 Final Recommendation

**Adopt these changes:**

1. **`@` for address-of** — `let ptr = @x`
2. **`[[name]]` for attributes** — `[[test]]`
3. **Keep `&` for bitwise AND only**
4. **`@T` for immutable reference type**
5. **`@&T` for mutable reference type**
6. **`*T` for raw pointers (FFI/unsafe only)**

**For parameter passing, choose one:**

| Option | Syntax | Assessment |
|--------|--------|------------|
| **A** | `data: T`, `data:& T`, `data:= T` | **Recommended** — compact, explicit, learnable |
| B | `ref data: T`, `mut data: T`, `move data: T` | Verbose but crystal clear |
| C | `data: @T` = borrow, `data: T` = move | Explicit everywhere |

**My recommendation:** **Option A** — colon-modifier syntax.

```ritz
fn read(data: Connection)               # Const borrow (`:`)
fn modify(data:& Connection)            # Mutable borrow (`:&`)
fn consume(data:= Connection)           # Move (`:=`)
```

This:
- Uses three distinct colon-modifiers: `:`, `:&`, `:=`
- Default (`:`) is the most common case (read-only access)
- `:&` mirrors the `&` symbol for mutability
- `:=` evokes assignment/transfer of ownership
- No call-site annotation needed — the function signature tells the story

**Call sites (clean, no annotations):**
```ritz
let conn = Connection.new()
read(conn)                               # Borrows (const)
modify(conn)                             # Borrows (mutable)
consume(conn)                            # Moves ownership
```

**Note:** The compiler knows what to do from the function signature. The call site is clean and uncluttered.

---

## Open Questions

1. **Call-site inference:** With colon-modifier syntax, the call site is clean:
   ```ritz
   read(conn)    # Compiler knows `read` takes `data: T` (const borrow)
   modify(conn)  # Compiler knows `modify` takes `data:& T` (mutable borrow)
   consume(conn) # Compiler knows `consume` takes `data:= T` (move)
   ```
   This is the recommended approach — no call-site clutter.

2. **What about return types?**
   ```ritz
   fn get_ref() -> @T        # Return a reference
   fn get_owned() -> T       # Return owned value
   ```

3. **Lifetime elision?** How long does `@T` live? Ritz aims to avoid explicit lifetimes, so we need clear rules.

4. **Lexer changes:** The lexer needs to recognize `:&` and `:=` as distinct tokens (not `:` followed by `&` or `=`).

---

## Summary: Recommended Syntax

| Concept | Current (Rust-like) | Proposed (Ritz) |
|---------|---------------------|-----------------|
| Address-of | `&x` | `@x` |
| Bitwise AND | `a & b` | `a & b` (unchanged) |
| Ref type | `&T` | `@T` |
| Mut ref type | `&mut T` | `@&T` |
| Attributes | `@test` | `[[test]]` |
| Const borrow param | `data: &T` | `data: T` |
| Mutable borrow param | `data: &mut T` | `data:& T` |
| Move param | `data: T` | `data:= T` |

**Complete example:**

```ritz
[[test]]
fn test_connection()
    var conn = Connection.new()

    # Address-of uses @
    let addr = @conn.address

    # Bitwise AND is unambiguous
    let mask = flags & 0xFF

    # Parameter passing (call sites are clean)
    read(conn)      # fn read(data: Connection) — const borrow
    modify(conn)    # fn modify(data:& Connection) — mutable borrow
    consume(conn)   # fn consume(data:= Connection) — move
```

---

## 6. Memory Allocation APIs

### 6.1 The Allocation Landscape

Ritz supports multiple allocation strategies:

| Allocator | Use Case | Lifetime | Cleanup |
|-----------|----------|----------|---------|
| **Stack** | Local variables | Scope-bound | Automatic (stack unwind) |
| **Box** | Single heap object | Ownership-based | When owner drops |
| **Vec** | Dynamic arrays | Ownership-based | When owner drops |
| **Arena** | Bulk allocations | Scope-bound | All freed at once |
| **Pool** | Reusable objects | Bounded, recycled | Returned to pool |

### 6.2 Reference Types in Allocation APIs

Functions returning references use `@T` (immutable) or `@&T` (mutable):

```ritz
@T          # Immutable reference — can read, cannot modify
@&T         # Mutable reference — can read and modify
```

This mirrors the signature syntax — `&` always means "mutable":

| Context | Immutable | Mutable |
|---------|-----------|---------|
| **Signatures** | `x: T` | `x:& T` |
| **Reference types** | `@T` | `@&T` |
| **Taking reference** | `@x` | `@&x` |

### 6.3 Box API (Heap Allocation)

```ritz
struct Box<T>
    # Create a new boxed value
    fn new(value:= T) -> Box<T>

    # Access the contained value
    fn get(self: Box) -> @T
    fn get_mut(self:& Box) -> @&T
```

Usage:

```ritz
var b: Box<User> = Box.new(User { name: "Alice", age: 30 })

# Immutable access
let user = b.get()          # user: @T
print(user.name)            # OK

# Mutable access
let user_mut = b.get_mut()  # user_mut: @&User
user_mut.age = 31           # OK
```

### 6.4 Arena API (Scoped Bulk Allocation)

Arenas allocate many objects that all share the same lifetime. When the arena drops, everything inside it is freed at once.

```ritz
struct Arena
    fn new() -> Arena
    fn alloc<T>(self:& Arena, value:= T) -> @&T
    fn alloc_slice<T>(self:& Arena, count: i32) -> @&[T]
```

**Type inference from LHS** (no turbofish needed):

```ritz
var arena = Arena.new()

# Type inferred from what you're allocating
let user: @&User = arena.alloc(User { name: "Bob", age: 25 })
let buffer: @&[u8] = arena.alloc_slice(1024)

# Arena owns the memory — references valid until arena drops
user.age = 26               # OK, user is @&User
```

### 6.5 Pool API (Bounded Reusable Objects)

Pools pre-allocate a fixed number of objects for reuse, avoiding repeated allocation/deallocation.

```ritz
struct Pool<T>
    fn new(capacity: i32) -> Pool<T>
    fn get(self: Pool) -> Option<@T>
    fn get_mut(self:& Pool) -> Option<@&T>
    fn release(self:& Pool, item:= T)
```

**Type inference from LHS:**

```ritz
var pool: Pool<Connection> = Pool.new(64)

# Get a mutable reference to a pooled connection
let conn: Option<@&Connection> = pool.get_mut()
match conn
    Some(c)
        c.timeout = 30      # OK, c is @&Connection
        send_query(c)
        pool.release(c)     # Return to pool
    None
        print("Pool exhausted")
```

### 6.6 The `using` Keyword (Scoped Resource Access)

For cleaner pool/arena usage, the `using` keyword provides scoped access with automatic cleanup:

```ritz
# Immutable borrow from pool
using conn from CONN_POOL
    query(conn)                 # conn: @Connection
# conn automatically returned to pool

# Mutable borrow from pool
using &conn from CONN_POOL
    conn.timeout = 30           # conn: @&Connection
    query(conn)
# conn automatically returned to pool
```

The `&` modifier mirrors the signature syntax:

| Syntax | Type of binding |
|--------|-----------------|
| `using x from pool` | `x: @T` (immutable reference) |
| `using &x from pool` | `x: @&T` (mutable reference) |

### 6.7 Vec API (Dynamic Arrays)

```ritz
struct Vec<T>
    fn new() -> Vec<T>
    fn push(self:& Vec, value:= T)
    fn pop(self:& Vec) -> Option<T>
    fn get(self: Vec, index: i32) -> Option<@T>
    fn get_mut(self:& Vec, index: i32) -> Option<@&T>
    fn len(self: Vec) -> i32
```

Usage:

```ritz
var items: Vec<User> = Vec.new()
items.push(User { name: "Alice", age: 30 })
items.push(User { name: "Bob", age: 25 })

# Immutable access
let first = items.get(0)        # first: Option<@User>

# Mutable access
let first_mut = items.get_mut(0)  # first_mut: Option<@&User>
match first_mut
    Some(u)
        u.age = 31              # OK
    None
        pass
```

### 6.8 Summary: Reference Types

| Syntax | Meaning | Usage |
|--------|---------|-------|
| `@T` | Immutable reference | Read-only access to borrowed data |
| `@&T` | Mutable reference | Read-write access to borrowed data |
| `*T` | Raw pointer | FFI/kernel code only (requires `unsafe`) |

The `&` is consistent throughout:

| Context | Immutable | Mutable |
|---------|-----------|---------|
| **Param signatures** | `x: T` | `x:& T` |
| **Reference types** | `@T` | `@&T` |
| **Taking reference** | `@x` | `@&x` |
| **Scoped binding** | `using x from` | `using &x from` |

**Return types:**

```ritz
fn get_ref(self: Container) -> @T        # Returns immutable reference
fn get_mut(self:& Container) -> @&T      # Returns mutable reference
fn take(self:& Container) -> T           # Returns owned value
```

---

*This document is a working proposal. Feedback drives the final design.*
