# Ritzlib Standard Library Reference

The Ritz Standard Library (ritzlib) provides essential functionality for Ritz programs. Unlike traditional standard libraries that wrap libc, ritzlib interfaces directly with the Linux kernel through syscalls, resulting in smaller binaries and eliminating C runtime dependencies.

**Status**: covers ritzlib as it stands on **2026-09-03**, after the RERITZ syntax
migration. Every fenced ` ```ritz ` block below is compiled against the real
ritzlib by `tools/check_doc_examples.py` on every build, and the signatures in
the tables were checked against `ritzlib/*.ritz` on that date. If an example
here stops compiling, the build fails.

**Reference syntax reminder** (RERITZ): `@x` takes an immutable reference (the
old `&x` is rejected with a migration diagnostic), `@T` is an immutable
reference *type* and `@&T` a mutable one (the old `&T` / `&mut T`), `var` is a
mutable binding and `let` an immutable one, and a bare `"text"` literal is a
`StrView`, not a `*u8` — use `c"text"` where a C string is wanted.

---

## Philosophy

**No libc, No Dependencies**

Ritzlib is built on three core principles:

1. **Direct Syscalls**: All system interaction goes through Linux syscalls, with no libc dependency. This means Ritz binaries are truly standalone.

2. **Plain Data, No Runtime**: `String`, `Vec<T>` and `HashMapI64` are ordinary structs over memory from `ritzlib.memory`; their functions compile to direct code, with no garbage collector, reference counting or runtime type information behind them.

3. **Explicit Resource Management**: Resources are managed through the `Drop` trait for automatic cleanup, or explicit `*_drop()` functions for manual control.

**Target Platform**: Linux x86-64 (kernel 5.1+ for io_uring features)

### Core and hosted

ritzlib has two layers (AGAST #4119). The **core** (`str`, `strview`, `span`,
`option`, `result`, `gvec`, `string`, `hashmap`, `memory`, and `fmt.digits`,
`drop` and `hash`, which they use) builds for a freestanding target, such as a kernel
with no syscalls: no core module imports a module outside the core, so
`ritzlib.sys` is never in its import closure. Everything else (`sys`, `io`,
`fs`, `net`, `uring`, `process`, `os.env`, ...) is **hosted**. The list lives
in `tools/ritzlib_layers.py`, whose check (`make tools-unit`) fails when a
core module imports a hosted one.

Inside the core, the **bare** modules (`strview`, `option`, `fmt.digits`)
import only each other, so they reach no allocator: a target with no heap at
all, such as harland's UEFI loader, imports them (AGAST #4601). The same check
fails when a bare module imports one that is not bare.

The core reaches the platform only through three hooks it declares
`extern fn`:

| Hook | Signature | Used by |
|------|-----------|---------|
| `ritz_platform_page_map` | `fn(len: i64) -> *u8` | `memory`'s default page source |
| `ritz_platform_page_unmap` | `fn(p: *u8, len: i64) -> i32` | `memory`'s default page source |
| `ritz_platform_fatal` | `fn(msg: *u8, len: i64, status: i32)` | `hashmap`'s missing key (status 101) |

`ritzlib.sys` defines them (anonymous mmap; `msg` and a newline on stderr, then
exit). Every hosted `_start` (`runtime/ritz_start*.ll`, and the one ritz0 or
ritz1 emits) also carries weak copies, so a program that imports only core
modules links without sys. A freestanding program defines all three itself.

---

## Table of Contents

1. [Core Types](#core-types)
   - [option](#option) - Optional values
   - [result](#result) - Error handling
   - [drop](#drop) - Automatic cleanup trait
   - [hash](#hash) - Hashing utilities
2. [Memory Management](#memory-management)
   - [ptr](#ptr) - Taking a value out of raw memory
   - [memory](#memory) - Allocators (Arena, Heap, malloc/free)
   - [box](#box) - Heap-allocated single values
3. [Collections](#collections)
   - [gvec](#gvec) - Generic dynamic array (`Vec<T>`)
   - [string](#string) - Owned UTF-8 strings
   - [hashmap](#hashmap) - Hash map for i64 keys
   - [span](#span) - Non-owning memory views
4. [String Utilities](#string-utilities)
   - [strview](#strview) - Borrowed string views (`StrView`)
   - [str](#str) - C-string interop
   - [fmt.digits](#fmtdigits) - Integer-to-text digit routines
   - [fmt](#fmt) - Writer, Display / Debug, format specs
   - [ct](#ct) - Constant-time comparison of secrets
   - [buf](#buf) - Buffer and parsing utilities
5. [System Interface](#system-interface)
   - [sys](#sys) - Raw syscall wrappers
   - [Program entry](#program-entry) - `_start` and the `main` signatures
6. [I/O Operations](#io-operations)
   - [io](#io) - Console I/O
   - [fs](#fs) - Filesystem operations
   - [fd](#fd) - Owned file descriptors, pipes
   - [iovec](#iovec) - Vectored I/O for scatter/gather writes
7. [Networking](#networking)
   - [net](#net) - TCP/IP socket operations
   - [async_net](#async_net) - Async TCP networking
8. [Async Runtime](#async-runtime)
   - [async.runtime](#asyncruntime) - Drive one future with `rt.block_on`
   - [async.tasks](#asynctasks) - Multi-task executor
   - [async.blocking_fs](#asyncblocking_fs) - Blocking file calls behind `async fn`
   - [uring](#uring) - io_uring bindings
9. [Process Management](#process-management)
   - [process](#process) - Subprocess spawning
   - [argspec](#argspec) - Argument parsing
   - [os.env](#osenv) - Environment variables
10. [Utilities](#utilities)
    - [timer](#timer) - High-precision timing
    - [time](#time) - Duration, sleep, wall clock
    - [json](#json) - JSON parsing
    - [elf](#elf) - ELF binary parsing
    - [endian](#endian) - Big- and little-endian integers in a byte buffer
    - [testing](#testing) - Removed; use `assert`

---

## Core Types

### option

**Module**: `ritzlib.option`

Represents a value that may or may not be present.

```ritz
enum Option<T>
    Some(T)
    None
```

**Functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `option_is_some` | `fn<T>(opt: *Option<T>) -> i32` | Returns 1 if Some, 0 if None |
| `option_is_none` | `fn<T>(opt: *Option<T>) -> i32` | Returns 1 if None, 0 if Some |
| `option_unwrap_or` | `fn<T>(opt: *Option<T>, default: T) -> T` | Returns value or default |

**Example**:
```ritz
import ritzlib.option
import ritzlib.gvec

fn find_first(items: @Vec<i32>, target: i32) -> Option<i32>
    var i: i64 = 0
    while i < items.len()
        if items.get(i) == target
            return Some(i as i32)
        i += 1
    return None
```

`Vec`'s accessors are methods, so their element type comes from the receiver:
`items.len()`, `items.get(i)` (AGAST #4537).

---

### result

**Module**: `ritzlib.result`

Represents either a success value or an error value. Essential for error handling.

```ritz
enum Result<T, E>
    Ok(T)
    Err(E)
```

**Methods** (`impl<T, E> Result<T, E>`, AGAST #4445):

| Method | Signature | Description |
|--------|-----------|-------------|
| `r.is_ok()` | `fn() -> bool` | Whether it is `Ok` |
| `r.is_err()` | `fn() -> bool` | Whether it is `Err` |
| `r.unwrap_or(default)` | `fn(default: T) -> T` | The `Ok` value, or `default` |
| `r.ok()` | `fn() -> Option<T>` | The `Ok` value as an Option, discarding the error |
| `r.err()` | `fn() -> Option<E>` | The `Err` value as an Option |

**Example**:
```ritz
import ritzlib.option
import ritzlib.result
import ritzlib.strview

fn parse_int(s: StrView) -> Result<i64, i32>
    match s.parse_i64()
        Some(n) => Ok(n)
        None => Err(1)             # error code: not a whole decimal number
```

---

### drop

**Module**: `ritzlib.drop`

The Drop trait enables automatic cleanup when values go out of scope.

```ritz
trait Drop
    fn drop(self: @&Self)
```

Note: `ritzlib/drop.ritz` holds this declaration as a comment, not live code.
The `impl Drop for T` blocks in `box.ritz`, `hashmap.ritz` and `buf.ritz` are
live. `String` and `Vec<T>` don't implement `Drop` yet
(AGAST #2159).

The rules are in LANGUAGE_SPEC §13. In short, a type that implements `Drop`,
or contains a field that does, is move-only, and every other type copies. The
compiler calls `drop` on each binding that still owns such a value:
- at the end of its block;
- before `return`;
- on `break`/`continue`, for bindings declared inside the loop;
- before assigning a new value to the binding.

Drops run in reverse declaration order (LIFO). A moved-from binding is not
dropped. Don't call `drop` yourself.

ritz0 (AGAST #2157) and ritz1 (AGAST #2158) don't implement all of this yet.
`ritz0/test_ownership_free_count.py` lists each compiler's gaps.

---

### hash

**Module**: `ritzlib.hash`

FNV-1a hash functions for use in HashMap and other data structures.

**Constants**:
- FNV offset basis: 14695981039346656037
- FNV prime: 1099511628211

**Functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `fnv1a_init` | `fn() -> u64` | Initialize hash state |
| `fnv1a_byte` | `fn(h: u64, b: u8) -> u64` | Hash a single byte |
| `fnv1a_i32` | `fn(h: u64, val: i32) -> u64` | Hash an i32 into state |
| `fnv1a_i64` | `fn(h: u64, val: i64) -> u64` | Hash an i64 into state |
| `fnv1a_u64` | `fn(h: u64, val: u64) -> u64` | Hash a u64 into state |
| `hash_i32` | `fn(val: i32) -> u64` | Standalone hash for i32 |
| `hash_i64` | `fn(val: i64) -> u64` | Standalone hash for i64 |
| `hash_u64` | `fn(val: u64) -> u64` | Standalone hash for u64 |

**Traits**: what `HashMap<K, V>` needs of `K` (LANGUAGE_SPEC §11.5). `StrView`
implements both, here in the traits' file (LARB R65).

```ritz
trait Hash
    fn hash(self: @Self) -> u64

trait Eq
    fn equals(self: @Self, other: @Self) -> bool
```

`Eq`'s method is `equals`, not `eq`: a type has one method per name, and
`StrView` already has a by-value `s.eq(t)`. A primitive can implement either
now, but only in the trait's file (LARB R36's revisit, #4294). This file is
that file, so it carries `impl Hash for i64` and `impl Eq for i64`, and
`HashMap<i64, V>` is legal.

---

## Memory Management

### ptr

**Module**: `ritzlib.ptr`

`*p` of a move-only value is an error (LANGUAGE_SPEC §13.2), so code that keeps
values in raw memory reads them with `ptr_read`.

```ritz
import ritzlib.ptr

fn main() -> i32
    var n: i32 = 3
    ptr_read<i32>(@n)
```

`ptr_read<T>(p: *T) -> T` is a bitwise read. The caller owns the result, and the
memory at `p` no longer holds a value: reading it again or dropping it is a
double drop.

### memory

**Module**: `ritzlib.memory`

Provides allocation primitives: Arena allocator for batch allocations and a jemalloc-style malloc/free.

#### Arena Allocator

Fast bump allocator where allocations just increment an offset. Memory is freed all at once. Perfect for compilers, parsers, and temporary allocations.

```ritz
struct Arena
    base: *u8       # Base pointer from mmap
    size: i64       # Total size of arena
    offset: i64     # Current allocation offset
```

**Constants**:
- `ARENA_DEFAULT_SIZE`: 1048576 (1 MB)

**Functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `arena_new` | `fn(size: i64) -> Arena` | Create arena with given capacity |
| `arena_default` | `fn() -> Arena` | Create 1 MB arena |

**Methods** (`impl Arena`):

| Method | Signature | Description |
|--------|-----------|-------------|
| `a.alloc(size)` | `fn(size: i64) -> *u8` | Allocate bytes (8-byte aligned) |
| `a.alloc_zero(size)` | `fn(size: i64) -> *u8` | Allocate and zero-initialize |
| `a.alloc_array(count, elem_size)` | `fn(count: i64, elem_size: i64) -> *u8` | Allocate array |
| `a.reset()` | `fn()` | Reset arena (free all, keep memory) |
| `a.destroy()` | `fn()` | Free underlying memory |
| `a.used()` | `fn() -> i64` | Get current usage |
| `a.remaining()` | `fn() -> i64` | Get remaining capacity |
| `a.valid()` | `fn() -> bool` | Check if arena is valid |

#### Process Heap (Simple)

Simple mmap-based heap for when you need per-allocation free.

| Function | Signature | Description |
|----------|-----------|-------------|
| `heap_alloc` | `fn(size: i64) -> *u8` | Allocate from heap |
| `heap_free` | `fn(ptr: *u8, size: i64) -> i32` | Free (requires size) |
| `heap_realloc` | `fn(ptr: *u8, old_size: i64, new_size: i64) -> *u8` | Reallocate |

#### jemalloc-style Allocator

Proper malloc/free with size classes (no need to track sizes when freeing).

**Size Classes**:
- Class 0: 16 bytes usable
- Class 1: 32 bytes usable
- Class 2: 64 bytes usable
- Class 3: 128 bytes usable
- Class 4: 256 bytes usable
- Class 5: 512 bytes usable
- Class 6: 1024 bytes usable
- Class 7: 2048 bytes usable
- Class 8+: Direct mmap

| Function | Signature | Description |
|----------|-----------|-------------|
| `malloc` | `fn(size: i64) -> *u8` | Allocate size bytes |
| `free` | `fn(ptr: *u8)` | Free pointer (no size needed) |
| `realloc` | `fn(ptr: *u8, new_size: i64) -> *u8` | Reallocate to new size |
| `calloc` | `fn(count: i64, size: i64) -> *u8` | Allocate and zero-initialize; null if `count * size` overflows |

#### Page Source

Every allocator above gets its pages from one page source and returns them
there. The default is the platform hooks `ritz_platform_page_map` /
`ritz_platform_page_unmap` (see [Core and hosted](#core-and-hosted)): anonymous
mmap on a hosted target. A kernel, which has no mmap, defines the hooks over its
frame allocator or installs a source, and a test can install one that fails. `map(len)` returns `len` zeroed
read-write bytes, or a value `mmap_failed` accepts (null or `-errno`); every
allocator then returns null.

```ritz
import ritzlib.memory

fn no_pages(len: i64) -> *u8
    return -12 as *u8          # -ENOMEM

fn give_back(p: *u8, len: i64) -> i32
    return 0

fn main() -> i32
    var src: PageSource = PageSource { map: no_pages, unmap: give_back }
    let prev: PageSource = src.set()
    let p: *u8 = malloc(8192)  # null: the source had no pages
    prev.set()
    if p == null
        return 0
    return 1
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `src.set()` | `fn() -> PageSource` | Install `src`; returns the source it replaces |

| Function | Signature | Description |
|----------|-----------|-------------|
| `page_source_get` | `fn() -> PageSource` | The installed source (the platform hooks until set) |
| `mmap_failed` | `fn(p: *u8) -> bool` | True for null and `-errno` (any `p <= 0`) |

Install a source before the first allocation, or restore the previous one
before anything allocated under it is freed. To give one subsystem its own
pages instead, build its collections on `h.allocator()` or `src.allocator()`
(below): those blocks go back to their own source whatever is installed.

#### Allocator

`malloc`/`free`/`realloc` are one global heap. An `Allocator` is any other
memory source (an Arena, a subsystem's own pages, a kernel heap) that a `Vec`,
`String` or `HashMap` can be built on (AGAST #4120). It has the shape
goliath's allocator had (AGAST #1881) plus a `ctx`, and goliath now uses it:

```text
pub struct Allocator
    ctx: *u8                       # the allocator's state
    alloc: fn(*u8, i64) -> *u8     # alloc(ctx, len): len bytes, 8-aligned, or null
    free: fn(*u8, *u8, i64) -> i32 # free(ctx, p, len): what one alloc(ctx, len) returned
```

```ritz
import ritzlib.memory
import ritzlib.gvec

# The Vec's drop at the end of this function returns its block to `a`; only
# then is the arena safe to destroy (a Vec owns its buffer, AGAST #2159).
fn use_arena_vec(a: *Allocator) -> i64
    var v: Vec<i64> = vec_new_in<i64>(a)    # every grow comes from the arena
    v.push(7)
    v.get(0)

fn arena_vec() -> i64
    var ar: Arena = arena_new(65536)
    var a: Allocator = ar.allocator()
    let x: i64 = use_arena_vec(@a)
    ar.destroy()
    x
```

`a.malloc(n)` takes `n + 16` bytes from `a`, and the block's header names
`a` as its owner. Plain `free` and `realloc` read that header, so collection
code is unchanged and a block never goes back to the wrong allocator. A null
owner is the global heap. The `Allocator` must stay at its address while any
block it handed out is live, because the header points at it.

| Function | Signature | Description |
|----------|-----------|-------------|
| `allocator_of` | `fn(p: *u8) -> *Allocator` | `p`'s owner; null for the global heap and for null |

| Method | Signature | Description |
|--------|-----------|-------------|
| `a.malloc(size)` | `fn(size: i64) -> *u8` | `size` bytes owned by `a` (null `a`: `malloc`) |
| `ar.allocator()` | `fn() -> Allocator` | Bump from `ar`; `free` gives nothing back until reset/destroy |
| `src.allocator()` | `fn() -> Allocator` | Each block its own whole-page mapping from `src`, unmapped there |
| `h.init(src)` | `fn(src: PageSource)` | Fill `h` as a size-class heap whose slabs and large blocks map from `src` |
| `h.allocator()` | `fn() -> Allocator` | Small blocks from `h`'s 64 KiB slabs, freed into its bins; over 2 KiB, its own mapping |
| `h.destroy()` | `fn()` | Unmap every slab and live large block of `h` to its source; `h` is empty again |

A `Heap` (AGAST #4326) is the global heap's size classes over a source of its
own: `src.allocator()` costs a page per block, `h.allocator()` packs small
blocks into slabs. The global heap is itself a `Heap` that follows the
installed source. The `Heap` must stay at its address while its allocator or
any block from it is live, and `h.destroy()` frees every block at once:

```ritz
import ritzlib.memory
import ritzlib.gvec

fn use_heap_vec(a: *Allocator) -> i64
    var v: Vec<u8> = vec_new_in<u8>(a)         # a slab block, not a page
    v.push(7)
    v.get(0) as i64                            # drop returns it to h's bins

fn heap_vec() -> i64
    var h: Heap
    h.init(page_source_get())           # keeps this source
    var a: Allocator = h.allocator()
    let x: i64 = use_heap_vec(@a)
    h.destroy()                           # every slab back to the source
    x
```

The collections' `_in` constructors take one: `vec_new_in` / `vec_with_cap_in`
(`ritzlib.gvec`), `string_new_in` / `string_with_cap_in` (`ritzlib.string`) and
`hashmap_new_in` / `hashmap_with_cap_in` and `hashmap_i64_new_in` /
`hashmap_i64_with_cap_in` (`ritzlib.hashmap`), whose grows build the bigger
table in the same allocator, and `box_new_in` (`ritzlib.box`). An empty Vec remembers nothing, so
`vec_new_in` reserves 8 elements. A slice or clone, and a push after a drop,
use the global heap.

The `heap e` expression (see [heap](#heap)) allocates with this `malloc`, so a
module using it needs `ritzlib.memory` loaded, imported directly or not. ritz1
lowers `heap e` to `__heap_new(e)`, a generic `fn<T>(value: T) -> *T` here;
it is the compiler's, not for direct use.

**Utility**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `memzero` | `fn(dst: *u8, n: i64)` | Zero n bytes at dst |
| `secure_zero` | `fn(dst: *u8, n: i64)` | Zero n bytes at dst with volatile stores the optimiser cannot remove; use it to wipe secrets (LANGUAGE_SPEC §18.4) |

---

### box

**Module**: `ritzlib.box`

Heap-allocated container for a single value with automatic cleanup.

```ritz
struct Box<T>
    ptr: *T    # Pointer to heap-allocated T
```

**Constructors**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `box_new` | `fn<T>(value: T) -> Box<T>` | Create box containing value |
| `box_new_in` | `fn<T>(a: *Allocator, value: T) -> Box<T>` | `box_new` with the value in memory from `a`; empty if `a` is out of memory |

**Operations** are methods (AGAST #4445):

| Method | Signature | Description |
|--------|-----------|-------------|
| `b.get()` | `fn() -> T` | Get value (returns copy) |
| `b.as_ptr()` | `fn() -> *T` | Get pointer to value |
| `b.set(value)` | `fn(value: T)` | Set new value |
| `b.valid()` | `fn() -> bool` | Check if valid |
| `b.drop()` | `fn()` | Free the box now (`Box` implements `Drop`: it also runs at scope end) |

**The `heap` keyword is not a `Box`.** `heap 42` is a raw allocation
expression of type `*i64`: dereference it with `*p` and free it with
`free(p as *u8)`. `box_new<i64>(42)` returns a `Box<i64>`, which is what
`b.get` / `b.set` / `b.drop()` and the `Drop` impl operate on. Passing a
`heap`-keyword pointer to `b.get` is a type error.

```ritz
import ritzlib.box

fn heap_vs_box() -> i64
    var p = heap 42            # `heap` keyword: a bare *i64, deref with `*p`
    var q = box_new<i64>(42)   # constructor: a Box<i64> wrapper
    *p + q.get()
```

ritzlib once also had `ritzlib.heap`, a `Heap<T>` identical to `Box<T>` with a
`heap_` prefix; it was folded into `box` (AGAST #3916).

---

## Collections

### gvec

**Module**: `ritzlib.gvec`

Generic dynamic array (growable vector).

```ritz
struct Vec<T>
    data: *T       # Pointer to heap-allocated array
    len: i64       # Current number of elements
    cap: i64       # Allocated capacity
```

**Constructors**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `vec_new` | `fn<T>() -> Vec<T>` | Create empty Vec |
| `vec_with_cap` | `fn<T>(cap: i64) -> Vec<T>` | Create with pre-allocated capacity |
| `vec_new_in` | `fn<T>(a: *Allocator) -> Vec<T>` | Empty, every grow from `a` (reserves 8 elements) |
| `vec_with_cap_in` | `fn<T>(a: *Allocator, cap: i64) -> Vec<T>` | With capacity, from `a` |

**Core Operations** are methods (`impl<T> Vec<T>`, AGAST #4445):

| Method | Signature | Description |
|--------|-----------|-------------|
| `v.push(item)` | `fn(item: T) -> bool` | Push element (false only if the growth allocation fails) |
| `v.pop()` | `fn() -> T` | Pop last element (caller ensures non-empty) |
| `v.get(idx)` | `fn(idx: i64) -> T` | Get element by index (caller ensures in range) |
| `v.get_ptr(idx)` | `fn(idx: i64) -> *T` | Get pointer to element |
| `v.set(idx, item)` | `fn(idx: i64, item: T) -> i32` | Set element (caller ensures in range); returns 0 |
| `v.len()` | `fn() -> i64` | Get length |
| `v.cap()` | `fn() -> i64` | Get capacity |
| `v.is_empty()` | `fn() -> bool` | Check if empty |
| `v.valid()` | `fn() -> bool` | Always true: an empty Vec with null data is valid |
| `v.grow(new_cap)` | `fn(new_cap: i64) -> bool` | Grow to `new_cap`; true when the Vec has the capacity |
| `v.ensure_cap(needed)` | `fn(needed: i64) -> bool` | Ensure at least `needed` capacity; true on success |
| `v.clear()` | `fn()` | Clear (keeps capacity) |
| `v.deinit()` | `fn()` | Free the Vec now, for one in raw memory; an owned Vec is freed by its `Drop` impl at scope end (AGAST #2159) |

A zero-size element (a field-less struct) allocates nothing: `len` and `cap`
count elements as usual, and `data` is a non-null dangling pointer that
`v.deinit()` never frees.

**Utilities**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `v.first()` | `fn() -> T` | Get first element |
| `v.last()` | `fn() -> T` | Get last element |
| `v.as_ptr()` | `fn() -> *T` | Get raw pointer |
| `v.slice(start, end)` | `fn(start: i64, end: i64) -> Vec<T>` | Copy of `[start, end)`, bounds clamped |
| `v.clone()` | `fn() -> Vec<T>` | Copy every element; shallow, so a heap-owning `T` ends up owned twice |
| `v.swap(i, j)` | `fn(i: i64, j: i64) -> bool` | Swap elements; false if either index is out of range |
| `v.push_bytes(data, len)` | `fn(data: *T, len: i64) -> bool` | Push `len` elements (the print-sink protocol, LANGUAGE_SPEC §2.6) |
| `v.push_span(data)` | `fn(data: Span<T>) -> bool` | Push every element of a span |
| `v.push_str(s)` | `fn(s: *T) -> bool` | Push a NUL-terminated C string, without the NUL |
| `v.as_str()` | `fn() -> Option<*T>` | NUL-terminate (not counted in `len`) and return the data pointer; `None` if that can't be allocated |

**Line Utilities** (to read a whole fd into a `Vec<u8>`, use `vec_read_all_fd` in [io](#io)):

```ritz
struct LineBounds
    start: i64      # Start offset in buffer
    length: i64     # Length in bytes
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `v.find_lines(lines)` | `fn(lines: @&Vec<LineBounds>) -> bool` | Append each line's bounds (trailing newline included) to `lines`; `Vec<u8>` only; false if a push fails |

---

### string

**Module**: `ritzlib.string`

Owned, growable UTF-8 string. Always null-terminated for C interop.

```ritz
import ritzlib.gvec

struct String
    data: Vec<u8>    # Underlying byte storage
```

**Constructors** (free fns; also reachable as `String.new(...)`, `String.from(...)`, ...):

| Function | Signature | Description |
|----------|-----------|-------------|
| `string_new` | `fn() -> String` | Create empty string |
| `string_with_cap` | `fn(cap: i64) -> String` | Create with capacity |
| `string_from` | `fn(sv: StrView) -> String` | Create from a StrView (`"text"` literal) |
| `string_from_bytes` | `fn(bytes: Span<u8>) -> String` | Create from a byte span |

**Methods** (`impl String`; call `s.method(...)`):

Accessors:

| Method | Signature | Description |
|--------|-----------|-------------|
| `s.len()` | `fn() -> i64` | Get length |
| `s.cap()` | `fn() -> i64` | Get capacity |
| `s.is_empty()` | `fn() -> bool` | Check if empty |
| `s.as_ptr()` | `fn() -> *u8` | Get null-terminated C string |
| `s.as_view()` | `fn() -> StrView` | Borrow the bytes as a StrView (no copy), valid until `s` is modified or dropped; how a String prints in `print`/`eprint` interpolation or reaches a StrView API |
| `s.get(idx)` | `fn(idx: i64) -> u8` | Get byte at index |
| `s.char_at(idx)` | `fn(idx: i64) -> u8` | Get char at index |

Modification:

| Method | Signature | Description |
|--------|-----------|-------------|
| `s.push(b)` | `fn(b: u8) -> bool` | Push byte |
| `s.push_str(sv)` | `fn(sv: StrView) -> bool` | Push StrView (a `"..."` literal) |
| `s.push_cstr(cstr)` | `fn(cstr: *u8) -> bool` | Push NUL-terminated C string |
| `s.push_string(other)` | `fn(other: @String) -> bool` | Push String |
| `s.push_span(bytes)` | `fn(bytes: Span<u8>) -> bool` | Push a byte span |
| `s.push_bytes(bytes)` | `fn(bytes: Span<u8>) -> bool` | Append a byte span; the print-sink protocol `format_into(@&s, "...")` appends through (AGAST #4555) |
| `s.push_i64(n)` | `fn(n: i64) -> bool` | Push an integer in decimal (all of i64); replaces `itoa` |
| `s.clear()` | `fn()` | Clear string |
| `s.pop()` | `fn() -> u8` | Pop last byte |
| `s.set_char(idx, c)` | `fn(idx: i64, c: u8) -> bool` | Set char at index |
| `s.deinit()` | `fn()` | Free the string now, for one in raw memory; an owned String is freed by its `Drop` impl at scope end (AGAST #2159) |

Comparison:

| Method | Signature | Description |
|--------|-----------|-------------|
| `s.eq(other)` | `fn(other: StrView) -> bool` | Compare to a StrView (a `"..."` literal) |
| `s.eq_string(b)` | `fn(b: @String) -> bool` | Compare two Strings |
| `s.eq_strview(sv)` | `fn(sv: StrView) -> bool` | Same as `s.eq` |
| `s.eq_cstr(cstr)` | `fn(cstr: *u8) -> bool` | Compare to C string |
| `s.hash()` | `fn() -> u64` | Hash the string |

Search/Slice:

| Method | Signature | Description |
|--------|-----------|-------------|
| `s.starts_with(prefix)` | `fn(prefix: StrView) -> bool` | Check prefix |
| `s.starts_with_string(prefix)` | `fn(prefix: @String) -> bool` | Check prefix String |
| `s.ends_with(suffix)` | `fn(suffix: StrView) -> bool` | Check suffix |
| `s.ends_with_string(suffix)` | `fn(suffix: @String) -> bool` | Check suffix String |
| `s.contains(needle)` | `fn(needle: StrView) -> bool` | Check contains |
| `s.contains_string(needle)` | `fn(needle: @String) -> bool` | Check contains String |
| `s.find(needle)` | `fn(needle: @String) -> i64` | Find substring; index, or `len` when absent |
| `s.slice(start, end)` | `fn(start: i64, end: i64) -> String` | Extract substring |
| `s.clone()` | `fn() -> String` | Deep copy |

Conversion:

| Method | Signature | Description |
|--------|-----------|-------------|
| `s.to_lower()` | `fn() -> String` | ASCII lowercase copy |

Free conversion constructors:

| Function | Signature | Description |
|----------|-----------|-------------|
| `string_from_i64` | `fn(n: i64) -> String` | Integer to String |
| `string_from_hex` | `fn(n: u64) -> String` | Integer to hex String |

---

### hashmap

**Module**: `ritzlib.hashmap`

Hash maps using open addressing with linear probing: the generic
`HashMap<K: Hash + Eq, V>`, and `HashMapI64` for i64 keys and values.

**`HashMap<K, V>`** (AGAST #1858) keeps its slots in a `Vec`. `K` needs
`Hash` and `Eq` from `ritzlib.hash`; a key type without them is an error at
the type argument. `ritzlib.hash` provides both for `StrView` and `i64` (the
latter only there, the trait's file, #4294). `get` returns `Option<V>`, so a
missing key is `None`.

| Function | Signature | Description |
|----------|-----------|-------------|
| `hashmap_new<K, V>` | `fn() -> HashMap<K, V>` | Create with 16 slots |
| `hashmap_with_cap<K, V>` | `fn(cap: i64) -> HashMap<K, V>` | Create with `cap` slots, rounded up to a power of 2 |
| `hashmap_new_in<K, V>` | `fn(a: *Allocator) -> HashMap<K, V>` | 16 slots, every grow from `a` |
| `hashmap_with_cap_in<K, V>` | `fn(a: *Allocator, cap: i64) -> HashMap<K, V>` | With capacity, from `a` |

Operations are methods (AGAST #4445):

| Method | Signature | Description |
|--------|-----------|-------------|
| `m.insert(key, value)` | `fn(key: K, value: V)` | Insert or overwrite |
| `m.get(key)` | `fn(key: K) -> Option<V>` | The value, or `None` |
| `m.get_ptr(key)` | `fn(key: K) -> Option<*V>` | The value, borrowed (for a move-only `V`), or `None` |
| `m.contains(key)` | `fn(key: K) -> bool` | Whether the key is present |
| `m.remove(key)` | `fn(key: K) -> bool` | Remove key (true if it was there) |
| `m.len()` | `fn() -> i64` | The number of keys |
| `m.cap()` | `fn() -> i64` | The number of slots (a power of 2) |
| `m.slot_state(i)` | `fn(i: i64) -> Slot` | Slot `i`'s state: `Empty`, `Full` or `Tomb` |
| `m.slot_value(i)` | `fn(i: i64) -> V` | Slot `i`'s value (read it when `Full`) |
| `m.clear()` | `fn()` | Remove every key, keeping the table allocated |
| `m.free()` | `fn()` | Free the table |

**Iteration** walks the slots: `for i in 0..m.cap()` and
`m.slot_state(i) == Slot.Full`. `Tomb` is a removed key's slot; a
probe chain still steps over it. The map never frees a value, so drop what
the values own before `m.clear()` or `m.free()`, and do not insert
or remove during a walk.

The map's slot table is a `Vec`, so an owned map is move-only and the
compiler drops the table at scope end (AGAST #2159). `m.free()` remains for
a map in raw memory. The map never drops its keys or values.

```ritz
import ritzlib.hash
import ritzlib.hashmap
import ritzlib.option
import ritzlib.strview

fn main() -> i32
    var m: HashMap<StrView, i64> = hashmap_new<StrView, i64>()
    m.insert("one", 1)
    m.insert("one", 2)
    let one: i64 = match m.get("one")
        Some(v) => v
        None => -1
    let two: i64 = match m.get("two")
        Some(v) => v
        None => 0
    m.free()
    (one + two - 2) as i32
```

**`HashMapI64`**:

```ritz
enum Slot
    Empty   # never used
    Full    # holds a live key/value
    Tomb    # held a key that was removed

struct HashMapEntryI64
    key: i64
    value: i64
    state: Slot

struct HashMapI64
    entries: *HashMapEntryI64
    cap: i64
    len: i64
    tombstones: i64
```

**Constructors**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `hashmap_i64_new` | `fn() -> HashMapI64` | Create with default capacity (16) |
| `hashmap_i64_with_cap` | `fn(cap: i64) -> HashMapI64` | Create with capacity |
| `hashmap_i64_new_in` | `fn(a: *Allocator) -> HashMapI64` | Table (and every grow) from `a` |
| `hashmap_i64_with_cap_in` | `fn(a: *Allocator, cap: i64) -> HashMapI64` | With capacity, from `a`; empty if `a` is out of memory |

**Operations** are methods (AGAST #4445):

| Method | Signature | Description |
|--------|-----------|-------------|
| `m.insert(key, value)` | `fn(key: i64, value: i64)` | Insert or update |
| `m.get(key)` | `fn(key: i64) -> i64` | Get value (0 if not found) |
| `m.find(key)` | `fn(key: i64) -> Option<i64>` | The key's slot index, or `None` |
| `m.contains(key)` | `fn(key: i64) -> bool` | Check if key exists |
| `m.remove(key)` | `fn(key: i64) -> i32` | Remove key (1 if removed) |
| `m.len()` | `fn() -> i64` | Get entry count |
| `m.cap()` | `fn() -> i64` | Get capacity |
| `m.is_empty()` | `fn() -> bool` | Check if empty |
| `m.clear()` | `fn()` | Remove every key, keeping the table allocated |
| `m.free()` | `fn()` | Free the map |
| `m.value_ptr(key)` | `fn(key: i64) -> Option<*i64>` | The value's slot (None if not found) |
| `hashmap_i64_missing_key` | `fn(key: i64)` | Exit 101: `HashMapI64: key not found: <key>` |

**Indexing** (LANGUAGE_SPEC §7.8): `HashMapI64` implements `Index`, `IndexMut` and
`IndexSet` at `K` = `V` = `i64`. `m[k] = v` inserts or replaces; `m[k]`, `@m[k]`,
`@&m[k]` and `m[k] += x` end the program through `hashmap_i64_missing_key` when `k`
is missing. Test for a key with `m.contains` or `m.get`.

```ritz
import ritzlib.hashmap

fn main() -> i32
    var m: HashMapI64 = hashmap_i64_new()
    m[7] = 1
    m[7] += 2
    if not m.contains(8)
        m[8] = 0
    (m[7] + m[8] - 3) as i32
```

---

### span

**Module**: `ritzlib.span`

Non-owning view into contiguous memory. Zero-cost abstraction.

```ritz
struct Span<T>
    ptr: *T        # Pointer to first element (not owned)
    len: i64       # Number of elements
```

**Constructors**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `span_empty` | `fn<T>() -> Span<T>` | Create empty span |
| `span_from_ptr` | `fn<T>(ptr: *T, len: i64) -> Span<T>` | From raw pointer |
| `span_from_vec` | `fn<T>(v: @Vec<T>) -> Span<T>` | From Vec |
| `span_from_cstr` | `fn(cstr: *u8) -> Span<u8>` | From C string |
| `span_literal` | `fn(ptr: *u8, len: i64) -> Span<u8>` | From literal with known length |

**Methods** (`impl<T> Span<T>`, AGAST #4445):

| Method | Signature | Description |
|--------|-----------|-------------|
| `s.len()` | `fn() -> i64` | Get length |
| `s.is_empty()` | `fn() -> bool` | Check if empty |
| `s.get(idx)` | `fn(idx: i64) -> T` | Get element |
| `s.get_ptr(idx)` | `fn(idx: i64) -> *T` | Pointer to element `idx` |
| `s.as_ptr()` | `fn() -> *T` | Get raw pointer |
| `s.slice(start, end)` | `fn(start: i64, end: i64) -> Span<T>` | Sub-span `[start, end)` |
| `s.from(start)` | `fn(start: i64) -> Span<T>` | From `start` to the end |
| `s.to(end)` | `fn(end: i64) -> Span<T>` | From the beginning to `end` |

**Slicing** (free functions):

| Function | Signature | Description |
|----------|-----------|-------------|
| `span_slice` | `fn<T>(s: @Span<T>, start: i64, end: i64) -> Span<T>` | Sub-span |
| `span_take` | `fn(s: @Span<u8>, n: i64) -> Span<u8>` | First n bytes |
| `span_skip` | `fn(s: @Span<u8>, n: i64) -> Span<u8>` | Skip first n bytes |

**String Operations** (for `Span<u8>`):

`Span<u8>` has StrView's layout; these delegate to the `StrView` method of
the same name (`span_eq` calls `.eq`), and `span_as_strview` / `span_from_strview` convert between the two.

| Function | Signature | Description |
|----------|-----------|-------------|
| `span_as_strview` | `fn(s: @Span<u8>) -> StrView` | View the same bytes as a StrView |
| `span_eq` | `fn(a: @Span<u8>, b: @Span<u8>) -> bool` | Compare equality |
| `span_eq_cstr` | `fn(s: @Span<u8>, cstr: *u8) -> bool` | Compare to C string |
| `span_contains` | `fn(haystack: @Span<u8>, needle: @Span<u8>) -> bool` | Contains check |
| `span_starts_with` | `fn(s: @Span<u8>, prefix: @Span<u8>) -> bool` | Prefix check |
| `span_ends_with` | `fn(s: @Span<u8>, suffix: @Span<u8>) -> bool` | Suffix check |
| `span_find` | `fn(haystack: @Span<u8>, needle: @Span<u8>) -> i64` | Find substring |
| `span_find_byte` | `fn(s: @Span<u8>, c: u8) -> i64` | Find byte |

---

## String Utilities

### strview

**Module**: `ritzlib.strview`

`StrView` is a borrowed `{ ptr: *u8, len: i64 }` view of UTF-8 bytes, and the
type of a bare `"..."` literal. It never allocates or frees, is not
NUL-terminated, and must not outlive the bytes it points at. Use `String`
(`ritzlib.string`) when you need to own or grow the text. Every method takes
the view by value; slicing returns a new view of the same bytes. The module
is bare (no allocator in its imports); for a `malloc`ed NUL-terminated copy,
`ritzlib.string`'s `strview_to_cstr(sv)` (the caller `free`s it).

**Construction** (free fns; no method form):

| Function | Signature | Description |
|----------|-----------|-------------|
| `strview_empty` | `fn() -> StrView` | Empty view (`ptr` null, `len` 0) |
| `strview_from_ptr` | `fn(ptr: *u8, len: i64) -> StrView` | View `len` bytes at `ptr` |
| `strview_from_cstr` | `fn(cstr: *u8) -> StrView` | View a NUL-terminated string, without the NUL |

**Methods** (`impl StrView`; call `s.method(...)`, the view by value):

Access / conversion:

| Method | Signature | Description |
|--------|-----------|-------------|
| `s.len()` | `fn() -> i64` | Length in bytes |
| `s.is_empty()` | `fn() -> bool` | `len == 0` |
| `s.get(idx)` | `fn(idx: i64) -> u8` | Byte at `idx` (unchecked) |
| `s.as_ptr()` | `fn() -> *u8` | Pointer to the first byte |
| `s.as_cstr_unchecked()` | `fn() -> *u8` | The pointer as a C string. Only sound if the bytes after the view hold a NUL, as they do for a whole literal; a slice usually doesn't |
| `s.parse_i64()` | `fn() -> Option<i64>` | The whole view as decimal, optional `+`/`-`: `None` for empty, a bare sign, whitespace, junk or overflow. Trim first if needed |

Comparison:

| Method | Signature | Description |
|--------|-----------|-------------|
| `s.eq(t)` | `fn(t: StrView) -> bool` | Same length and bytes |
| `s.eq_cstr(c)` | `fn(c: *u8) -> bool` | Equal to a C string |
| `s.cmp(t)` | `fn(t: StrView) -> i32` | Bytewise order: -1, 0 or 1; a prefix sorts first |
| `s.cmp_cstr(c)` | `fn(c: *u8) -> i32` | `s.cmp` against a C string |

Slicing (no allocation):

| Method | Signature | Description |
|--------|-----------|-------------|
| `s.slice(start, end)` | `fn(start: i64, end: i64) -> StrView` | Bytes `[start, end)`, bounds clamped to `[0, len]`; empty if `start >= end` |
| `s.take(n)` | `fn(n: i64) -> StrView` | First `n` bytes (all if `n >= len`) |
| `s.skip(n)` | `fn(n: i64) -> StrView` | Everything after the first `n` bytes |
| `s.trim_start()` | `fn() -> StrView` | Drop leading space, `\t`, `\n`, `\r` |
| `s.trim_end()` | `fn() -> StrView` | Drop trailing whitespace |
| `s.trim()` | `fn() -> StrView` | Both ends |
| `s.split_once(delim, before, after)` | `fn(delim: u8, before:& StrView, after:& StrView) -> i32` | Split at the first `delim` (excluded): 1 if found; 0 and `before = s`, `after` empty if not. Call as `s.split_once('=', @&k, @&v)` |

Search:

| Method | Signature | Description |
|--------|-----------|-------------|
| `s.starts_with(p)` | `fn(p: StrView) -> bool` | Prefix test |
| `s.starts_with_cstr(p)` | `fn(p: *u8) -> bool` | Prefix test against a C string |
| `s.ends_with(p)` | `fn(p: StrView) -> bool` | Suffix test |
| `s.contains(t)` | `fn(t: StrView) -> bool` | Substring test; an empty needle is always found |
| `s.find(t)` | `fn(t: StrView) -> i64` | First index of `t`, or `len` when absent (0 for an empty needle) |
| `s.rfind(t)` | `fn(t: StrView) -> i64` | Last index of `t`, or `len` when absent |
| `s.find_byte(c)` | `fn(c: u8) -> i64` | First index of byte `c`, or `len` when absent |

The constructors stay free functions: they have no method form (LARB R66).

**Example**:
```ritz
import ritzlib.option
import ritzlib.strview

# "key = value" -> the value as an i64, or None
fn config_int(line: StrView, key: StrView) -> Option<i64>
    var k: StrView = strview_empty()
    var v: StrView = strview_empty()
    if line.split_once('=', @&k, @&v) == 0
        return None
    if not k.trim().eq(key)
        return None
    (v.trim()).parse_i64()

[[test]]
fn test_strview_example() -> i32
    let port = match config_int("  port = 8080 ", "port")
        Some(n) => n
        None => -1
    assert port == 8080
    assert config_int("port = 80x", "port").is_none()
    let path = strview_from_cstr(c"/usr/lib/libc.so")
    let base = path.skip(path.rfind("/") + 1)
    assert base.eq("libc.so")
    assert path.starts_with("/usr") and path.ends_with(".so")
    assert ("abc").cmp("abd") < 0
    assert path.find_byte('l') == 5
    assert path.len() == 16
    0
```

---

### str

**Module**: `ritzlib.str`

C-string interop only: NUL-terminated `*u8`, for argv, syscalls and C APIs.
New code uses `StrView` (`ritzlib.strview`, borrowed) and `String`
(`ritzlib.string`, owned); get a view of a C string with `strview_from_cstr`.

| `str` | Use instead |
|-------|-------------|
| `strlen` | `s.len()` on a `StrView` or `String` |
| `streq`, `strneq` | `s.eq(t)` / `s.eq_cstr(c)`; `s.take(n)` then `s.eq(t)` |
| `strcmp` | `s.cmp(t)` |
| `strchr` | `s.find_byte(c)` |
| `strrchr` | `s.rfind(t)` |
| `strstr` | `s.find(t)`, `s.contains(t)` |
| `strcpy`, `strncpy` | `string_from` (a `String` owns its copy); `s.take(n)` to bound it |
| `strcat` | `s.push_str(v)`, `s.push_string(other)` |
| `atoi` | `s.parse_i64() -> Option<i64>`: `None` for empty, junk or overflow, where `atoi` returns 0 or a prefix |
| `itoa` | `s.push_i64(n) -> bool` / `string_from_i64`: no caller-sized buffer |

The byte predicates (`isdigit` .. `tolower`) take a `u8`, not a C string, and
are fine to use. `memset`/`memcpy`/`memcmp`/`bcmp`/`memmove` stay here because
the compiler emits calls to those symbols.

**Length/Comparison**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `strlen` | `fn(s: *u8) -> i64` | String length |
| `streq` | `fn(a: *u8, b: *u8) -> i32` | Equality check |
| `strneq` | `fn(a: *u8, b: *u8, n: i64) -> i32` | First n chars equal |
| `strcmp` | `fn(a: *u8, b: *u8) -> i32` | Lexicographic compare |

**Search**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `strchr` | `fn(s: *u8, c: u8) -> *u8` | Find first char |
| `strstr` | `fn(haystack: *u8, needle: *u8) -> *u8` | Find substring |

**Copy/Concatenate**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `strcpy` | `fn(dest: *u8, src: *u8) -> *u8` | Copy string |
| `strcat` | `fn(dest: *u8, src: *u8) -> *u8` | Concatenate |

**Conversion**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `atoi` | `fn(s: *u8) -> i64` | String to integer |
| `itoa` | `fn(n: i64, buf: *u8) -> *u8` | Integer to string |

**Character Classification**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `isdigit` | `fn(c: u8) -> i32` | Is digit (0-9) |
| `isalpha` | `fn(c: u8) -> i32` | Is letter |
| `isalnum` | `fn(c: u8) -> i32` | Is alphanumeric |
| `isspace` | `fn(c: u8) -> i32` | Is whitespace |
| `isupper` | `fn(c: u8) -> i32` | Is uppercase |
| `islower` | `fn(c: u8) -> i32` | Is lowercase |
| `toupper` | `fn(c: u8) -> u8` | To uppercase |
| `tolower` | `fn(c: u8) -> u8` | To lowercase |

**Memory Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `memset` | `fn(dest: *u8, c: u8, n: i64) -> *u8` | Fill memory |
| `memcpy` | `fn(dest: *u8, src: *u8, n: i64) -> *u8` | Copy memory |
| `memcmp` | `fn(a: *u8, b: *u8, n: i64) -> i32` | Compare memory |

---

### fmt.digits

**Module**: `ritzlib.fmt.digits` (core)

The one integer digit routine. Every ritzlib integer formatter (`print_int`,
`eprint_int`, `print_hex`, `itoa`, `String.push_i64`, `string_from_hex`,
`IoVecBuilder.append_int`/`append_uint`, `ritzlib.fmt`'s Display) calls it, so all of them
handle i64's minimum (AGAST #1856). Each writes into a caller buffer, returns
the byte count, and writes no NUL. It has no imports, so freestanding code can
use it too. It was `ritzlib.fmt` until AGAST #201 made that name the hosted
formatting surface below.

| Function | Signature | Description |
|----------|-----------|-------------|
| `fmt_i64_into` | `fn(buf: *u8, n: i64) -> i64` | Decimal with `-` when negative; needs 20 bytes |
| `fmt_u64_into` | `fn(buf: *u8, n: u64) -> i64` | Unsigned decimal; needs 20 bytes |
| `fmt_u64_hex_into` | `fn(buf: *u8, n: u64) -> i64` | Lowercase hex, no `0x`, no leading zeros; needs 16 bytes |
| `fmt_u64_radix_into` | `fn(buf: *u8, n: u64, radix: u64, upper: i32) -> i64` | Base 2..16, `upper != 0` for `A`..`F`; needs 64 bytes |

```ritz
import ritzlib.fmt.digits

fn fmt_example() -> i64
    var buf: [20]u8
    fmt_i64_into(@buf[0], -9223372036854775807 - 1)  # "-9223372036854775808", returns 20
```

---

### fmt

**Module**: `ritzlib.fmt` (hosted)

Formatting and printing, in one import (AGAST #201, docs/V1_ABI_CLEANUP.md
Phase 2). It `pub import`s `ritzlib.fmt.digits`, `.spec`, `.writer`,
`.impls`, `.display` and `ritzlib.io` (for `println` / `eprintln`); `print`
and `eprint` are builtins ([LANGUAGE_SPEC §2.6](LANGUAGE_SPEC.md)).

**Writer** (`ritzlib.fmt.writer`). A byte sink: a fn pointer and the state it
needs. Every write returns the bytes accepted, or a negative value (a -errno
from an fd, -1 from a full span). `w.len` counts every byte accepted. A Writer
is a `format_into` sink: it has `push_bytes`.

| Function | Signature | Description |
|----------|-----------|-------------|
| `stdout_writer` / `stderr_writer` | `fn() -> Writer` | fd 1 / fd 2 |
| `fd_writer` | `fn(fd: i32) -> Writer` | Any fd; short writes are retried |
| `string_writer` | `fn(s: @&String) -> Writer` | Appends to `*s` |
| `span_writer` | `fn(buf: Span<u8>) -> Writer` | Fills `buf`; a write that doesn't fit is -1 and writes nothing |
| `null_writer` | `fn() -> Writer` | Discards; `w.len` measures |
| `write` / `writeln` | `fn(w: @&Writer, s: StrView) -> i64` | `s` (and a newline) to `w` |
| `format` | `fn(s: StrView) -> String` | `s` copied into a new String |

**Methods** (`impl Writer`, AGAST #4445):

| Method | Signature | Description |
|--------|-----------|-------------|
| `w.write(data, len)` | `fn(data: *u8, len: i64) -> i64` | `len` bytes |
| `w.write_str(s)` | `fn(s: StrView) -> i64` | A view's bytes |
| `w.write_byte(b)` | `fn(b: u8) -> i64` | One byte |
| `w.write_fill(b, n)` | `fn(b: u8, n: i64) -> i64` | `b`, `n` times |
| `w.push_bytes(data)` | `fn(data: Span<u8>) -> i32` | The `format_into` sink: 0 if every byte was accepted, else -1 |
| `w.len()` | `fn() -> i64` | Bytes accepted so far |
| `w.view()` | `fn() -> StrView` | What a `span_writer` holds |

**Display and Debug** (`ritzlib.fmt.display`). `{v}` is Display and `{v:?}`
is Debug. A user type opts in with an impl; the methods need no `pub`
(§15.2). The generics `fmt_show`, `fmt_show_debug` and `fmt_show_with` call
them, and `fmt_show_with` pads any Display type to a spec's width.

```ritz
# ritzlib/fmt/display.ritz
import ritzlib.fmt.writer

pub trait Display
    fn show(self: @Self, w: @&Writer) -> i64

pub trait Debug
    fn show_debug(self: @Self, w: @&Writer) -> i64
```

```ritz
import ritzlib.fmt
import ritzlib.span

struct Point
    x: i64
    y: i64

impl Display for Point
    fn show(self: @Point, w: @&Writer) -> i64
        let before: i64 = w.len
        format_into(w, "({self.x}, {self.y})")
        w.len - before

fn main() -> i32
    var buf: [32]u8
    var w: Writer = span_writer(span_from_ptr<u8>(@buf[0], 32))
    let p = Point { x: 3, y: 4 }
    fmt_show_with(@p, @&w, ">8")          # "  (3, 4)"
    fmt_show_i64_with(255, @&w, "08x")    # "000000ff"
    (w.len() - 16) as i32
```

**The built-in types** (`ritzlib.fmt.impls`). R36's revisit (#4294) lets
`ritzlib.fmt.display` — the trait's file — carry the real impls: `impl
Display` and `impl Debug` for `i8`..`i64`, `u8`..`u64`, `bool`, `StrView`,
`*u8` and `Span<u8>`, each body one of the fns below. The fns remain for the
`_with` spec forms: for each of `i8`..`i64`, `u8`..`u64`, `bool`, `strview`,
`string` (`@String`), `cstr` (`*u8`) and `bytes` (`Span<u8>`) there are three
fns: `fmt_show_T(v, w)`, `fmt_show_T_with(v, w, spec)` and
`fmt_debug_T(v, w)`. `String` also has the real `impl Display` and `impl
Debug`. Debug quotes text and escapes `"`, `\`, `\n`, `\t`, `\r` and other
bytes outside `' '`..`'~'` as `\xNN`; `Span<u8>` is `[1, 2, 255]`; integers
and `bool` are as Display.

**Specs** (`ritzlib.fmt.spec`). `fmt_spec_parse(spec: StrView) -> FmtSpec`
reads the v1 set: `x` `X` `b` `o`, a width before them with an optional
`0` for zero padding (`08x`), `<N` `>N` `^N`, and `?`. Anything else has
`ok == false`, and the `_with` fns then write nothing and return -1. Under
`x` `X` `b` `o` a negative signed value prints its two's complement at its own
width (`-1 as i8` is `ff`). A width never truncates.

### ct

**Module**: `ritzlib.ct`

Constant-time comparison for secrets such as passwords and tokens (AGAST #1863).
`strcmp`/`memcmp` stop at the first differing byte, so their timing reveals
how much of a guess was right. `ct_eq` examines every byte of `a`, never
branches on the contents, and reports a length mismatch without an early exit.
Pass the untrusted input as `a` and the secret as `b`: the running time depends
only on `a.len`. Lengths, not NUL terminators, bound the comparison. tome's
`AUTH` uses it.

| Function | Signature | Description |
|----------|-----------|-------------|
| `ct_eq` | `fn(a: StrView, b: StrView) -> bool` | Equal length and contents, in constant time |

```ritz
import ritzlib.ct
import ritzlib.strview

fn password_ok(given: StrView) -> bool
    ct_eq(given, "hunter2")
```

---

### buf

**Module**: `ritzlib.buf`

Buffer utilities for parsing.

Text goes in as a `StrView` (a `"..."` literal) and comes out as a `StrView`
slice of the buffer's own bytes: zero-copy, never truncated. Predicates return
`bool`. Buffer and GrowBuf operations are impl methods: `@Buffer` is read-only,
`@&Buffer` moves the cursor; a method call on a local takes the receiver
automatically.

```ritz
import ritzlib.buf
import ritzlib.strview

fn key_of(line: StrView) -> StrView
    var b: Buffer = buf_new(line)
    b.skip_whitespace()
    let key: StrView = b.take_ident()
    b.skip_whitespace()
    if not b.match_char('=')
        return strview_empty()
    return key
```

#### Buffer (Read-Only View)

```ritz
struct Buffer
    data: *u8       # Pointer to data (not owned)
    len: i64        # Length of data
    pos: i64        # Current read position
```

**Initialization**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_new` | `fn(s: StrView) -> Buffer` | Cursor at the start of `s` (borrows its bytes) |

| Method | Signature | Description |
|--------|-----------|-------------|
| `b.from_str(s)` | `fn(s: StrView) -> i32` | Re-point an existing cursor at `s` |
| `b.init(data)` | `fn(data: Span<u8>) -> i32` | From a `Span<u8>` |

**Position**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `b.pos()` | `fn() -> i64` | Current position |
| `b.len()` | `fn() -> i64` | Total length |
| `b.remaining()` | `fn() -> i64` | Remaining bytes |
| `b.eof()` | `fn() -> bool` | At end? |
| `b.rest()` | `fn() -> StrView` | Unread bytes, as a slice |
| `b.save()` | `fn() -> i64` | Save position |
| `b.restore(pos)` | `fn(pos: i64) -> i32` | Restore position |

**Peek (Don't Advance)**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `b.peek()` | `fn() -> u8` | Peek current byte (0 at end) |
| `b.peek_at(offset)` | `fn(offset: i64) -> u8` | Peek at offset (0 out of range) |
| `b.peek_view(n)` | `fn(n: i64) -> StrView` | Up to `n` bytes, as a slice |

**Consume (Advance)**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `b.advance()` | `fn() -> u8` | Read and advance |
| `b.advance_n(n)` | `fn(n: i64) -> i64` | Advance n bytes (clamped) |
| `b.skip(n)` | `fn(n: i64) -> i32` | Skip n bytes (clamped) |

**Pattern Matching**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `b.match_char(c)` | `fn(c: u8) -> bool` | Consume `c` if next |
| `b.match_str(s)` | `fn(s: StrView) -> bool` | Consume `s` if next |
| `b.starts_with(s)` | `fn(s: StrView) -> bool` | Check prefix (no advance) |

**Skip Utilities**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `b.skip_whitespace()` | `fn() -> i64` | Skip space/tab/CR/LF |
| `b.skip_until(c)` | `fn(c: u8) -> i64` | Skip until char |
| `b.skip_while(pred)` | `fn(pred: fn(u8) -> bool) -> i64` | Skip a run matching `pred`; returns the count |

**Zero-Copy Reads** (each returns a slice of the buffer's bytes):

| Method | Signature | Description |
|--------|-----------|-------------|
| `b.take_until(c)` | `fn(c: u8) -> StrView` | Up to (not including) `c`, or to the end |
| `b.take_digits()` | `fn() -> StrView` | Run of `[0-9]` |
| `b.take_ident()` | `fn() -> StrView` | Run of `[A-Za-z0-9_]` |
| `b.take_while(pred)` | `fn(pred: fn(u8) -> bool) -> StrView` | Run matching `pred` |
| `b.take_quoted(quote, out)` | `fn(quote: u8, out: @&String) -> bool` | Decode a quoted string, appending to `out`; false if not at `quote` or unterminated |

**Byte Predicates** (for `b.take_while` / `b.skip_while`):

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_is_digit` | `fn(c: u8) -> bool` | `[0-9]` |
| `buf_is_ident` | `fn(c: u8) -> bool` | `[A-Za-z0-9_]` |
| `buf_is_space` | `fn(c: u8) -> bool` | space, tab, CR, LF |

**Deprecated** (kept for one release after AGAST #1478). The out-buffer forms
copy into a caller-sized `out`, NUL-terminate within `max_len` (so `max_len`
4 yields at most 3 bytes) and silently truncate:

| Method | Signature | Use instead |
|--------|-----------|-------------|
| `b.peek_n(out)` | `fn(out: Span<u8>) -> i64` | `b.peek_view(n)` |
| `b.read_until(c, out)` | `fn(c: u8, out: Span<u8>) -> i64` | `b.take_until(c)` |
| `b.read_while_digit(out)` | `fn(out: Span<u8>) -> i64` | `b.take_digits()` |
| `b.read_while_alnum(out)` | `fn(out: Span<u8>) -> i64` | `b.take_ident()` |
| `b.read_quoted(quote, out)` | `fn(quote: u8, out: Span<u8>) -> Result<i64, BufQuoteError>` | `b.take_quoted(quote, out)` |

**Location Tracking**:

```ritz
struct BufLoc
    line: i32
    col: i32
    offset: i64
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `b.get_loc(loc)` | `fn(loc: @&BufLoc) -> i32` | Get line/column |

#### GrowBuf (Growable Buffer)

```ritz
struct GrowBuf
    data: *u8
    len: i64
    cap: i64
```

A standalone struct, not an alias of `Vec<u8>`: the fields match `Vec<u8>`'s
in name and layout, but the types are distinct: every compiler rejects a
`GrowBuf` passed to a `Vec<u8>` function (#1948). It has
an `impl Drop` (`Vec<T>` does not); whether that drop is inserted
automatically depends on the compiler (#1854), so `b.free()` remains for
explicit release. To read a whole file descriptor, use `vec_read_all_fd`
(io) and point a `Buffer` at the bytes.

| Function | Signature | Description |
|----------|-----------|-------------|
| `growbuf_new` | `fn() -> GrowBuf` | Create empty |
| `growbuf_with_cap` | `fn(cap: i64) -> GrowBuf` | Create with capacity |

| Method | Signature | Description |
|--------|-----------|-------------|
| `b.free()` | `fn() -> i32` | Free (deprecated, use Drop) |
| `b.grow(new_cap)` | `fn(new_cap: i64) -> bool` | Grow capacity |
| `b.ensure_cap(needed)` | `fn(needed: i64) -> bool` | Ensure capacity |
| `b.append(data)` | `fn(data: Span<u8>) -> bool` | Append bytes |
| `b.append_view(s)` | `fn(s: StrView) -> bool` | Append a StrView |
| `b.append_byte(byte)` | `fn(byte: u8) -> bool` | Append single byte |
| `b.push_bytes(data)` | `fn(data: Span<u8>) -> bool` | Append a byte span; the sink `format_into(@&b, "...")` appends through (AGAST #4555) |
| `b.clear()` | `fn() -> i32` | Clear (keep capacity) |
| `b.len()` | `fn() -> i64` | Get length |
| `b.cap()` | `fn() -> i64` | Get capacity |
| `b.get(idx)` | `fn(idx: i64) -> u8` | Byte at index (0 out of range) |
| `b.is_empty()` | `fn() -> bool` | Empty? |
| `b.view()` | `fn() -> StrView` | Contents as a slice (invalidated by the next append) |
| `b.data()` | `fn() -> *u8` | Data pointer (C interop) |

---

## System Interface

### sys

**Module**: `ritzlib.sys`

Low-level syscall wrappers for Linux x86-64.

#### Raw Syscall Interface

`syscallN(n, a1..aN)` executes the x86-64 `syscall` instruction: the number in
rax, the arguments in rdi, rsi, rdx, r10, r8, r9, the result from rax. Each is
an `[[inline]]` `asm` fn (LANGUAGE_SPEC §18.6); no compiler knows the names.

| Function | Signature |
|----------|-----------|
| `syscall0` | `fn(n: i64) -> i64` |
| `syscall1` | `fn(n: i64, a1: i64) -> i64` |
| `syscall2` | `fn(n: i64, a1: i64, a2: i64) -> i64` |
| `syscall3` | `fn(n: i64, a1: i64, a2: i64, a3: i64) -> i64` |
| `syscall4` | `fn(n: i64, a1: i64, a2: i64, a3: i64, a4: i64) -> i64` |
| `syscall5` | `fn(n: i64, a1: i64, a2: i64, a3: i64, a4: i64, a5: i64) -> i64` |
| `syscall6` | `fn(n: i64, a1: i64, a2: i64, a3: i64, a4: i64, a5: i64, a6: i64) -> i64` |

#### Stat Structure

```ritz
struct Stat
    st_dev: i64       # device ID
    st_ino: i64       # inode number
    st_nlink: i64     # number of hard links
    st_mode: i32      # file mode
    st_uid: i32       # user ID
    st_gid: i32       # group ID
    __pad0: i32
    st_rdev: i64      # device ID (if special)
    st_size: i64      # total size in bytes
    st_blksize: i64   # block size
    st_blocks: i64    # 512B blocks allocated
    st_atime: i64     # last access time
    st_atime_ns: i64
    st_mtime: i64     # last modification time
    st_mtime_ns: i64
    st_ctime: i64     # last status change time
    st_ctime_ns: i64
    __reserved: i64
    __reserved2: i64
    __reserved3: i64
```

#### File I/O Syscalls

| Function | Signature | Description |
|----------|-----------|-------------|
| `sys_read` | `fn(fd: i32, buf: *u8, count: i64) -> i64` | Read from fd |
| `sys_write` | `fn(fd: i32, buf: *u8, count: i64) -> i64` | Write to fd |
| `sys_open` | `fn(path: *u8, flags: i32) -> i32` | Open file |
| `sys_open3` | `fn(path: *u8, flags: i32, mode: i32) -> i32` | Open with mode |
| `sys_close` | `fn(fd: i32) -> i32` | Close fd |
| `sys_lseek` | `fn(fd: i32, offset: i64, whence: i32) -> i64` | Seek |
| `sys_ftruncate` | `fn(fd: i32, length: i64) -> i32` | Truncate file |

#### File Metadata

| Function | Signature | Description |
|----------|-----------|-------------|
| `sys_stat` | `fn(path: *u8, statbuf: *u8) -> i32` | Get file status |
| `sys_stat2` | `fn(path: *u8, statbuf: @&Stat) -> i32` | Typed stat |
| `sys_fstat` | `fn(fd: i32, statbuf: *u8) -> i32` | fstat |
| `sys_lstat` | `fn(path: *u8, statbuf: *u8) -> i32` | lstat (no follow) |
| `sys_chmod` | `fn(path: *u8, mode: i32) -> i32` | Change mode |
| `sys_chown` | `fn(path: *u8, uid: i32, gid: i32) -> i32` | Change owner |
| `sys_access` | `fn(path: *u8, mode: i32) -> i32` | Check access |

#### Directory Operations

| Function | Signature | Description |
|----------|-----------|-------------|
| `sys_mkdir` | `fn(path: *u8, mode: i32) -> i32` | Create directory |
| `sys_rmdir` | `fn(path: *u8) -> i32` | Remove directory |
| `sys_getcwd` | `fn(buf: *u8, size: i64) -> i64` | Get CWD |
| `sys_chdir` | `fn(path: *u8) -> i32` | Change directory |
| `sys_getdents64` | `fn(fd: i32, dirp: *u8, count: i64) -> i64` | Read directory |

#### File Operations

| Function | Signature | Description |
|----------|-----------|-------------|
| `sys_unlink` | `fn(path: *u8) -> i32` | Remove file |
| `sys_rename` | `fn(oldpath: *u8, newpath: *u8) -> i32` | Rename |
| `sys_link` | `fn(oldpath: *u8, newpath: *u8) -> i32` | Create hard link |
| `sys_symlink` | `fn(target: *u8, linkpath: *u8) -> i32` | Create symlink |
| `sys_readlink` | `fn(path: *u8, buf: *u8, size: i64) -> i64` | Read symlink |

#### Memory Operations

| Function | Signature | Description |
|----------|-----------|-------------|
| `sys_mmap` | `fn(addr: i64, length: i64, prot: i32, flags: i32, fd: i32, offset: i64) -> *u8` | Map memory |
| `sys_munmap` | `fn(addr: *u8, length: i64) -> i32` | Unmap memory |
| `sys_mprotect` | `fn(addr: *u8, length: i64, prot: i32) -> i32` | Change protection |

**Memory Protection Flags**: `PROT_NONE`, `PROT_READ`, `PROT_WRITE`, `PROT_EXEC`

**Map Flags**: `MAP_SHARED`, `MAP_PRIVATE`, `MAP_ANONYMOUS`, `MAP_FIXED`

#### Process Operations

| Function | Signature | Description |
|----------|-----------|-------------|
| `sys_exit` | `fn(status: i32)` | Exit process |
| `sys_getpid` | `fn() -> i32` | Get PID |
| `sys_getppid` | `fn() -> i32` | Get parent PID |
| `sys_getuid` | `fn() -> i32` | Get UID |
| `sys_getgid` | `fn() -> i32` | Get GID |
| `sys_fork` | `fn() -> i32` | Fork process |
| `sys_execve` | `fn(path: *u8, argv: **u8, envp: **u8) -> i32` | Execute program |
| `sys_wait4` | `fn(pid: i32, status: *i32, options: i32, rusage: *u8) -> i32` | Wait for child |
| `sys_kill` | `fn(pid: i32, sig: i32) -> i32` | Send signal |

#### Pipe/Dup Operations

| Function | Signature | Description |
|----------|-----------|-------------|
| `sys_pipe` | `fn(pipefd: *i32) -> i32` | Create pipe |
| `sys_dup` | `fn(oldfd: i32) -> i32` | Duplicate fd |
| `sys_dup2` | `fn(oldfd: i32, newfd: i32) -> i32` | Duplicate to specific fd |

#### Time Operations

| Function | Signature | Description |
|----------|-----------|-------------|
| `sys_nanosleep` | `fn(req: *i64, rem: *i64) -> i32` | Sleep |
| `sys_gettimeofday` | `fn(tv: *Timeval, tz: *u8) -> i32` | Get time |

#### Signal Constants

`SIGHUP`, `SIGINT`, `SIGQUIT`, `SIGILL`, `SIGABRT`, `SIGKILL`, `SIGSEGV`, `SIGPIPE`, `SIGTERM`, `SIGCHLD`, `SIGSTOP`

#### Standard File Descriptors

`STDIN` (0), `STDOUT` (1), `STDERR` (2)

#### Open Flags

`O_RDONLY`, `O_WRONLY`, `O_RDWR`, `O_CREAT`, `O_EXCL`, `O_TRUNC`, `O_APPEND`, `O_NONBLOCK`, `O_DIRECTORY`, `O_CLOEXEC`

#### File Mode Constants

`S_IFDIR`, `S_IFREG`, `S_IFLNK`, `S_IRUSR`, `S_IWUSR`, `S_IXUSR`, etc.

#### Error Codes

`EPERM`, `ENOENT`, `EINTR`, `EIO`, `EAGAIN`, `ENOMEM`, `EACCES`, `EEXIST`, `ENOTDIR`, `EISDIR`, `EINVAL`, `ENOSPC`, `EPIPE`

---

### Program entry

No ritzlib module is involved. There is one entry path
(`docs/V1_ABI_CLEANUP.md`): one `_start` calls `main(argc, argv, envp)`. A
package built by `build.py` links it as `runtime/ritz_start.<arch>.o`, built
from the `.ll` of the same name, and a single file compiled by ritz0 gets the
same `_start` inline.

**`main`**: pick one shape. Each is a complete program because each block
here is compiled:

```ritz
pub fn main()                                       # returns 0
    let x: i32 = 1
```

```ritz
pub fn main(args: Span<StrView>) -> i32             # args[0] is the program
    args.len as i32
```

```ritz
pub fn main(args: Span<StrView>, env: Span<StrView>) -> i32   # env is "KEY=VALUE"
    env.len as i32
```

`-> i32` is optional on each: without it `main` returns 0. A `main` taking
`Span<StrView>` must be `pub`. Most code reads the environment with
`ritzlib.os.env` (`env_get`, `env_get_or`) and doesn't take `env` at all.
The compiler adds a small adapter `main(argc, argv, envp)`, written in Ritz,
that builds the spans and calls yours, and refuses any other parameter list
or return type.

The C shapes `main(argc: i32, argv: **u8) -> i32` and
`main(argc: i32, argv: **u8, envp: **u8) -> i32` are still accepted while the
workspace migrates (AGAST #203). They are removed in #204.

`_start`:
1. Extracts argc, argv, envp from the stack, and stores envp in `__ritz_envp`
   (which `ritzlib.os.env` reads)
2. Aligns the stack to 16 bytes
3. Calls `main(argc, argv, envp)`
4. Passes its return value to the exit syscall

---

## I/O Operations

### io

**Module**: `ritzlib.io`

High-level console I/O functions.

**Output to stdout**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `prints` | `fn(s: StrView)` | Print a StrView (`"text"` literal) |
| `println` | `fn(s: StrView)` | Print a StrView with newline |
| `prints_cstr` | `fn(s: *u8)` | C interop: print a NUL-terminated C string (`c"text"`, argv). Prefer `prints` |
| `println_cstr` | `fn(s: *u8)` | C interop: print a C string with newline. Prefer `println` |
| `print_char` | `fn(c: u8)` | Print character |
| `print_int` | `fn(n: i64)` | Print integer |
| `print_hex` | `fn(n: i64)` | Print hex with 0x prefix (a negative prints its two's-complement bits) |
| `print_size_human` | `fn(size: i64)` | Print human-readable size (K/M/G/T) |
| `newline` | `fn()` | Print newline |

**Output to stderr**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `eprints` | `fn(s: StrView)` | Print a StrView to stderr |
| `eprintln` | `fn(s: StrView)` | Print a StrView to stderr with newline |
| `eprints_cstr` | `fn(s: *u8)` | C interop: print a C string to stderr. Prefer `eprints` |
| `eprintln_cstr` | `fn(s: *u8)` | C interop: print a C string to stderr with newline. Prefer `eprintln` |
| `eprint_char` | `fn(c: u8)` | Print char to stderr |
| `eprint_int` | `fn(n: i64)` | Print int to stderr |

**String Type Output**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `print_string` | `fn(s: @String)` | Print String |
| `println_string` | `fn(s: @String)` | Print String with newline |
| `eprint_string` | `fn(s: @String)` | Print String to stderr |
| `eprintln_string` | `fn(s: @String)` | Print String to stderr with newline |
| `print_i64` | `fn(n: i64)` | Print i64 as String |
| `println_i64` | `fn(n: i64)` | Print i64 with newline |
| `eprint_i64` | `fn(n: i64)` | Print i64 to stderr |
| `eprintln_i64` | `fn(n: i64)` | Print i64 to stderr with newline |
| `print_hex64` | `fn(n: u64)` | Print hex |
| `println_hex64` | `fn(n: u64)` | Print hex with newline |

**Reading a whole fd**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `vec_read_all_fd` | `fn(fd: i32, v: @&Vec<u8>) -> Result<i64, Errno>` | Append everything `fd` yields to `v`; `Ok(bytes)`, or `Err(errno)`. Here rather than in gvec, which is core |

---

### errno

**Module**: `ritzlib.errno`

`Errno`, a typed kernel error code: the `Err` payload of ritzlib's fallible
syscall wrappers (`ritzlib.fs`, `ritzlib.net` and `ritzlib.process`, which
each re-export it). One variant per errno those modules return, numbered as on Linux x86_64, and `Other(n)` for any other code, so no
number is lost. The variant names follow Harland's kernel `Errno`; the raw
`i32` constants (`ENOENT`, ...) stay in `ritzlib.sys`.

```ritz
pub enum Errno
    Perm            # EPERM 1
    NoEnt           # ENOENT 2
    Intr            # EINTR 4
    Io              # EIO 5
    BadF            # EBADF 9
    Child           # ECHILD 10
    Again           # EAGAIN 11
    NoMem           # ENOMEM 12
    Acces           # EACCES 13
    Exist           # EEXIST 17
    NotDir          # ENOTDIR 20
    IsDir           # EISDIR 21
    Inval           # EINVAL 22
    NoSpc           # ENOSPC 28
    Pipe            # EPIPE 32
    NameTooLong     # ENAMETOOLONG 36
    NotEmpty        # ENOTEMPTY 39
    AddrInUse       # EADDRINUSE 98
    ConnReset       # ECONNRESET 104
    TimedOut        # ETIMEDOUT 110
    ConnRefused     # ECONNREFUSED 111
    Other(i32)      # any other errno, by its positive number
```

| Function | Signature | Description |
|----------|-----------|-------------|
| `errno_from_raw` | `fn(code: i32) -> Errno` | The Errno for `code`; either sign, so a raw `-errno` syscall return converts directly |
| `errno_write` | `fn(fd: i32, e: Errno) -> i64` | Write the message to `fd`, no newline; `Other(n)` gives `"Unknown error <n>"` |

**Methods** (`impl Errno`, AGAST #4445):

| Method | Signature | Description |
|--------|-----------|-------------|
| `e.code()` | `fn() -> i32` | The positive number (`NoEnt` -> 2, `Other(n)` -> n) |
| `e.name()` | `fn() -> StrView` | `"ENOENT"`, ...; `"EUNKNOWN"` for `Other` |
| `e.message()` | `fn() -> StrView` | strerror(3)'s text (`"No such file or directory"`); `"Unknown error"` for `Other` |

`Errno` carries data, so `e as i32` is an error: use `e.code()`.

```ritz
import ritzlib.fs
import ritzlib.io
import ritzlib.string

# 0 if `path` was read or is simply missing; otherwise report why and return 1.
fn read_if_present(path: StrView) -> i32
    match read_file(path)
        Ok(s) =>
            var text: String = s
            0
        Err(e) => match e
            NoEnt => 0
            _ =>
                eprint("cannot read file: ")
                errno_write(2, e)
                eprint("\n")
                1
```

---

### fs

**Module**: `ritzlib.fs`

High-level filesystem operations.

There is one path API, and every path is a `StrView`. A `"..."` literal is
already a StrView; a `String` passes `s.as_view()`; a C string passes
`strview_from_cstr(p)`. Every `Err` is an `Errno` (see [errno](#errno), which
fs re-exports): `NoEnt`, `Exist`, ..., or `Other(n)`; no fs function returns
a `-1` / `null` sentinel. A path of 4096 bytes or more fails with
`NameTooLong` without making a syscall.

**Path Checking** (lstat: a symlink is reported as itself, so `is_dir` of a
link to a directory is `false`):

| Function | Signature | Description |
|----------|-----------|-------------|
| `path_exists` | `fn(path: StrView) -> bool` | Anything exists at `path` (including a dangling symlink) |
| `is_dir` | `fn(path: StrView) -> bool` | Is directory? |
| `is_file` | `fn(path: StrView) -> bool` | Is regular file? |
| `is_symlink` | `fn(path: StrView) -> bool` | Is symlink? |
| `file_size` | `fn(path: StrView) -> Result<i64, Errno>` | Size in bytes (a symlink's own size) |

**Mode Helpers**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `mode_is_dir` | `fn(mode: i32) -> bool` | Check mode is directory |
| `mode_is_file` | `fn(mode: i32) -> bool` | Check mode is regular file |
| `mode_is_link` | `fn(mode: i32) -> bool` | Check mode is symlink |
| `mode_is_char` | `fn(mode: i32) -> bool` | Check mode is a character device |
| `mode_is_block` | `fn(mode: i32) -> bool` | Check mode is a block device |
| `mode_is_fifo` | `fn(mode: i32) -> bool` | Check mode is a FIFO |
| `mode_is_socket` | `fn(mode: i32) -> bool` | Check mode is a socket |

**stat / lstat**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `stat` | `fn(path: StrView) -> Result<Stat, Errno>` | Status of `path`, following symlinks |
| `lstat` | `fn(path: StrView) -> Result<Stat, Errno>` | Status of `path`; a symlink is reported as itself |

`Stat` is the kernel's x86_64 `struct stat`, defined once in `ritzlib.sys`
(`st_dev`, `st_ino`, `st_nlink`, `st_mode`, `st_uid`, `st_gid`, `st_size`,
`st_blksize`, `st_blocks`, timestamps). The path is a `StrView` and needn't be
NUL-terminated, because it's copied into a terminated buffer first. A missing
file is `Err(NoEnt)`; a path of 4096 bytes or more gives `Err(NameTooLong)`
without making a syscall.

```ritz
import ritzlib.fs
import ritzlib.sys     # Stat
import ritzlib.result

fn size_or_minus_one(path: StrView) -> i64
    var r: Result<Stat, Errno> = lstat(path)
    match r
        Ok(st) => st.st_size
        Err(_) => -1
```

**Directory entries**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `dir_open` | `fn(path: StrView) -> Result<DirIter, Errno>` | Open a directory (`Err(NoEnt)`, `Err(NotDir)`, ...) |

**Methods** (`impl DirIter`, AGAST #4445):

| Method | Signature | Description |
|--------|-----------|-------------|
| `d.next()` | `fn() -> bool` | Advance; true if an entry is available, false at the end |
| `d.close()` | `fn()` | Close the iterator |
| `d.entry()` | `fn() -> DirEntry` | Current entry after `d.next()` returns true |
| `d.next_entry()` | `fn() -> Option<DirEntry>` | Advance and return the next entry, `None` at the end |
| `d.entry_type()` | `fn() -> Option<u8>` | Type of the current entry (`DT_REG`, `DT_DIR`, ...), `None` if there is none |
| `d.entry_is_dir()` | `fn() -> bool` | Is the current entry a directory? |
| `d.entry_is_file()` | `fn() -> bool` | Is the current entry a regular file? |
| `d.entry_is_link()` | `fn() -> bool` | Is the current entry a symlink? |

```ritz
import ritzlib.sys
import ritzlib.fs
import ritzlib.strview

# Count regular files in `path` (0 if it can't be opened).
fn count_files(path: StrView) -> i64
    var dir: DirIter = match dir_open(path)
        Ok(d) => d
        Err(_) => return 0
    var n: i64 = 0
    while dir.next()
        let e: DirEntry = dir.entry()    # e.ino, e.kind, e.name: StrView
        if e.kind == DT_REG
            n += 1
    dir.close()
    n
```

`DirEntry.name` points into the iterator's buffer and doesn't include the NUL.
It is valid until the next `d.next()`/`d.next_entry()` or `d.close()` call.

**The raw `linux_dirent64` record** (what `DirIter` decodes):

```ritz
struct Dirent64
    d_ino: i64
    d_off: i64
    d_reclen: u16
    d_type: u8
```

**Dirent Types**: `DT_UNKNOWN`, `DT_FIFO`, `DT_CHR`, `DT_DIR`, `DT_BLK`, `DT_REG`, `DT_LNK`, `DT_SOCK`

**Path Utilities** (pure string work, no syscalls):

| Function | Signature | Description |
|----------|-----------|-------------|
| `path_join` | `fn(dir: StrView, name: StrView) -> String` | Join with exactly one `/`; an empty `dir` yields `name` |
| `path_basename` | `fn(path: StrView) -> StrView` | Final component (`"/a/b.txt"` -> `"b.txt"`) |
| `path_dirname` | `fn(path: StrView) -> StrView` | Before the last `/` (`"/a"`); `"/"` at top level, `"."` with no `/` |
| `path_extension` | `fn(path: StrView) -> StrView` | Extension without the dot (`"txt"`), or empty |
| `path_stem` | `fn(path: StrView) -> StrView` | `path` without its extension (`"/a/b"`) |

`path_basename`, `path_dirname`, `path_extension` and `path_stem` return views
into the input and don't allocate. A leading dot (`".gitignore"`) isn't an
extension.

**File Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `read_file` | `fn(path: StrView) -> Result<String, Errno>` | Whole contents of a file |
| `write_file` | `fn(path: StrView, content: StrView) -> Result<i64, Errno>` | Create/truncate (0644) and write; `Ok` = bytes written |
| `copy_file` | `fn(src: StrView, dest: StrView, mode: i32) -> Result<i64, Errno>` | Copy; `Ok` = bytes copied |
| `mkdir` | `fn(path: StrView, mode: i32) -> Result<i32, Errno>` | Create directory (`Ok(0)`; `Err(Exist)` if it exists) |
| `unlink` | `fn(path: StrView) -> Result<i32, Errno>` | Remove a non-directory (`Ok(0)`) |
| `rmdir` | `fn(path: StrView) -> Result<i32, Errno>` | Remove an empty directory (`Ok(0)`) |

```ritz
import ritzlib.fs
import ritzlib.string
import ritzlib.result

# Write `text` to dir/name; 0 on success, else the errno's number.
fn save(dir: StrView, name: StrView, text: StrView) -> i32
    if not is_dir(dir)
        var made: Result<i32, Errno> = mkdir(dir, 493)    # 0755
        match made
            Ok(_) => pass
            Err(e) => return e.code()
    var path: String = path_join(dir, name)
    var r: Result<i64, Errno> = write_file(path.as_view(), text)
    match r
        Ok(_) => 0
        Err(e) => e.code()
```

**Paths, permissions, cwd** (AGAST #4637):

| Function | Signature | Description |
|----------|-----------|-------------|
| `access` | `fn(path: StrView, mode: i32) -> Result<(), Errno>` | `path` permits `mode`: `F_OK` (exists), or `R_OK` + `W_OK` + `X_OK` summed (real uid, as access(2)) |
| `chdir` | `fn(path: StrView) -> Result<(), Errno>` | Change the working directory |
| `cwd` | `fn() -> Result<String, Errno>` | The working directory, absolute |
| `rename` | `fn(from: StrView, to: StrView) -> Result<(), Errno>` | Move `from` to `to`, replacing a file there; `Err(Other(18))` (EXDEV) across filesystems |
| `chmod` | `fn(path: StrView, mode: i32) -> Result<(), Errno>` | Set permission bits (`493` = 0755) |
| `symlink` | `fn(target: StrView, link: StrView) -> Result<(), Errno>` | Create `link` pointing at `target` (which need not exist) |
| `read_link` | `fn(path: StrView) -> Result<String, Errno>` | A symlink's contents; `Err(Inval)` if `path` is not a symlink |
| `set_times` | `fn(path: StrView, atime: FileTime, mtime: FileTime) -> Result<(), Errno>` | Set access/modification times (follows symlinks) |
| `remove_dir_all` | `fn(path: StrView) -> Result<(), Errno>` | Remove a directory and everything under it; symlinks are removed, never followed. `Err(NotDir)` for a file; the first other error stops the walk |

`FileTime` is `Now`, `Omit` (leave it unchanged) or `At(ns)`, nanoseconds since
the Unix epoch; `touch` is `set_times(path, FileTime.Now, FileTime.Now)`.

```ritz
import ritzlib.fs
import ritzlib.string
import ritzlib.result

# Run in `dir`, then come back: 0, or the errno's number.
fn in_dir(dir: StrView) -> i32
    match cwd()
        Ok(home) =>
            match chdir(dir)
                Ok(_) => pass
                Err(e) => return e.code()
            # ... work relative to `dir` ...
            match chdir(home.as_view())
                Ok(_) => 0
                Err(e) => e.code()
        Err(e) => e.code()
```

---

### fd

**Module**: `ritzlib.fd`

`Fd`, an owned file descriptor whose every fallible operation returns
`Result<_, Errno>` (AGAST #4637). Programs hold an `Fd`, never a bare `i32`
and a negative errno; the raw `sys_*` fd calls are the kernel-ABI layer under
it. `ritzlib.fd` re-exports `ritzlib.errno`, the `O_*` open flags, `LOCK_*`
and `Stat` from `ritzlib.sys`, and defines `SEEK_SET`, `SEEK_CUR`, `SEEK_END`.

```ritz
struct Fd
    fd: i32            # -1 once closed

struct Pipe
    read: Fd
    write: Fd
```

**Ownership.** An `Fd` from `fd_open`, `pipe`, `dup` or `fd_adopt` owns its
descriptor; close it once with `close()`, which marks it closed (`raw()` is
`-1`), so a second close is `Ok(())` and closes nothing. An `impl Drop` will
close it automatically once Drop lands (#1854). `fd_stdin` / `fd_stdout` /
`fd_stderr` borrow the standard streams, and `fd_borrow` any number owned
elsewhere: never close those. A read or write
interrupted by a signal is retried, so `Err(Intr)` never escapes.

| Function | Signature | Description |
|----------|-----------|-------------|
| `fd_open` | `fn(path: StrView, flags: i32, mode: i32) -> Result<Fd, Errno>` | open(2): `O_RDONLY`, `O_WRONLY + O_CREAT + O_TRUNC`, ...; `mode` when created (`420` = 0644). `NameTooLong` at 4096 bytes, no syscall |
| `pipe` | `fn() -> Result<Pipe, Errno>` | A new pipe; both ends owned by the caller |
| `fd_stdin` / `fd_stdout` / `fd_stderr` | `fn() -> Fd` | The standard streams, borrowed |
| `fd_adopt` | `fn(raw: i32) -> Fd` | Own a raw descriptor (a socket, an inherited fd); `-1` gives a closed Fd |
| `fd_borrow` | `fn(raw: i32) -> Fd` | Use a raw descriptor someone else owns and closes (a `Socket`'s fd, a caller's number): never close it |

| Method | Signature | Description |
|--------|-----------|-------------|
| `f.read(buf)` | `fn(buf: Span<u8>) -> Result<i64, Errno>` | Up to `buf.len` bytes; `Ok(0)` at EOF |
| `f.read_exact(buf)` | `fn(buf: Span<u8>) -> Result<(), Errno>` | Fill all of `buf` across short reads; `Err(Io)` if EOF comes first |
| `f.read_to_end(out)` | `fn(out: @&String) -> Result<i64, Errno>` | Append everything to EOF; `Ok` = bytes appended |
| `f.write(data)` | `fn(data: Span<u8>) -> Result<i64, Errno>` | One write(2); may be short |
| `f.write_all(data)` | `fn(data: Span<u8>) -> Result<(), Errno>` | Retry short writes; `Err(Pipe)` once the reader is gone (SIGPIPE ignored) |
| `f.write_str(s)` | `fn(s: StrView) -> Result<(), Errno>` | `write_all` of a StrView |
| `f.close()` | `fn() -> Result<(), Errno>` | Close and mark closed; a second close is `Ok(())` |
| `f.dup()` | `fn() -> Result<Fd, Errno>` | A new owned descriptor for the same open file |
| `f.dup_to(target)` | `fn(target: i32) -> Result<(), Errno>` | dup2(2): make descriptor `target` (e.g. `1`) this file; `f` stays open |
| `f.seek(offset, whence)` | `fn(offset: i64, whence: i32) -> Result<i64, Errno>` | lseek(2); `Ok` = new offset |
| `f.stat()` | `fn() -> Result<Stat, Errno>` | fstat(2) |
| `f.truncate(len)` | `fn(len: i64) -> Result<(), Errno>` | ftruncate(2) |
| `f.chmod(mode)` | `fn(mode: i32) -> Result<(), Errno>` | fchmod(2) |
| `f.lock(op)` | `fn(op: i32) -> Result<(), Errno>` | flock(2): `LOCK_SH`, `LOCK_EX`, `LOCK_UN`, `+ LOCK_NB` |
| `f.raw()` | `fn() -> i32` | The number, for a kernel-ABI hand-off (poll, io_uring); ownership stays |
| `f.valid()` | `fn() -> bool` | Open? |
| `p.close()` (Pipe) | `fn() -> Result<(), Errno>` | Close both ends |

Every method on a closed `Fd` is `Err(BadF)` without a syscall.

```ritz
import ritzlib.fd
import ritzlib.string
import ritzlib.result

# The contents of `path` with a trailing line added, written back.
fn append_line(path: StrView, line: StrView) -> Result<(), Errno>
    match fd_open(path, O_RDWR + O_CREAT, 420)
        Ok(f) =>
            var file: Fd = f
            match file.seek(0, SEEK_END)
                Ok(_) => pass
                Err(e) =>
                    file.close()
                    return Err(e)
            let w: Result<(), Errno> = file.write_str(line)
            file.close()
            w
        Err(e) => Err(e)
```

---

### iovec

**Module**: `ritzlib.iovec`

Vectored I/O for efficient scatter/gather writes (zero-copy where possible).

```ritz
struct Iovec
    base: *u8      # Pointer to buffer
    len: u64       # Length of buffer

struct IoVecBuilder
    iovecs: [32]Iovec
    pool: [512]u8
    count: i32
    pool_used: i32
```

The builder's operations are methods (`impl IoVecBuilder`, AGAST #4445).
Every append returns `Result<i32, IovecError>`, written `R` below;
`IovecError` is `TooManyVecs` or `PoolFull`.

**Builder Operations**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `b.init()` | `fn()` | Initialize builder |
| `b.reset()` | `fn()` | Reset for reuse |
| `b.ptr()` | `fn() -> *Iovec` | Get iovec array |
| `b.count()` | `fn() -> i32` | Get count |

**Append Operations**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `b.append_span(s)` | `fn(s: Span<u8>) -> R` | Append span (zero-copy) |
| `b.append_static(s)` | `fn(s: StrView) -> R` | Append a view's bytes (zero-copy) |
| `b.append_bytes(data)` | `fn(data: Span<u8>) -> R` | Append bytes (zero-copy) |
| `b.append_str(s)` | `fn(s: Span<u8>) -> R` | Append a slice (zero-copy) |
| `b.append_copy(s)` | `fn(s: StrView) -> R` | Append (copy to pool) |
| `b.append_int(n)` | `fn(n: i64) -> R` | Append integer |
| `b.append_uint(n)` | `fn(n: u64) -> R` | Append unsigned int |
| `b.append_crlf()` | `fn() -> R` | Append CRLF |

**Utilities**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `b.total_len()` | `fn() -> i64` | Total bytes |
| `b.debug_print()` | `fn()` | Debug output |

---

## Networking

### net

**Module**: `ritzlib.net`

TCP/IP socket operations. Every fallible function returns a `Result` whose
`Err` is a `ritzlib.errno` `Errno` (AGAST #4298; it was a positive `i32`
errno), and `net` re-exports `ritzlib.errno`. Compare with the raw numbers
via `e.code() == EINVAL`, or match the variant:

```ritz
import ritzlib.net

# A listener on 127.0.0.1:`port`, or the errno that stopped it.
fn open_listener(port: i32) -> Result<Socket, Errno>
    var sock: Socket = socket_tcp()?
    match sock.bind("127.0.0.1", port)
        Ok(_) => pass
        Err(e) =>
            sock.close()
            return Err(e)
    sock.listen(128)?
    Ok(sock)

# Whether something else already holds `port`.
fn port_taken(port: i32) -> bool
    match open_listener(port)
        Ok(s) =>
            var t: Socket = s
            t.close()
            false
        Err(e) => match e
            AddrInUse => true
            _ => false
```

**Constants**:
- Address families: `AF_INET` (2), `AF_INET6` (10)
- Socket types: `SOCK_STREAM` (TCP), `SOCK_DGRAM` (UDP), `SOCK_NONBLOCK`, `SOCK_CLOEXEC`
- Options: `SOL_SOCKET`, `SO_REUSEADDR`, `SO_REUSEPORT`, `TCP_NODELAY`
- Epoll: `EPOLLIN`, `EPOLLOUT`, `EPOLLERR`, `EPOLLHUP`, `EPOLLET`

**Structures**:

```ritz
struct SockAddrIn
    family: i16
    port: u16
    addr: u32
    zero: [8]u8

struct Socket
    fd: i32
    family: i32
    socktype: i32

# The kernel's packed epoll_event: 12 bytes, data at offset 4.
[[packed]]
struct EpollEvent
    events: u32
    data: u64
```

**Byte Order**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `htons` | `fn(val: i32) -> u16` | Host to network (16-bit) |
| `ntohs` | `fn(val: u16) -> i32` | Network to host (16-bit) |
| `htonl` | `fn(val: i64) -> u32` | Host to network (32-bit) |
| `parse_ipv4` | `fn(s: StrView) -> Option<u32>` | Parse "127.0.0.1" (network order); `None` unless exactly four octets 0-255 |

**Socket Creation**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `socket_tcp` | `fn() -> Result<Socket, Errno>` | A TCP socket, or `Err(errno)` from socket(2) (e.g. `Other(24)`, EMFILE) |
| `socket_tcp_nonblock` | `fn() -> Result<Socket, Errno>` | A non-blocking TCP socket, or `Err(errno)` |
| `socket_udp` | `fn() -> Result<Socket, Errno>` | A UDP socket, or `Err(errno)` |

| Method | Signature | Description |
|--------|-----------|-------------|
| `s.valid()` | `fn() -> bool` | Holds an open fd (false once closed) |
| `s.close()` | `fn() -> Result<(), Errno>` | Close and set `fd = -1`; `Ok(())` if already closed, else `Err(errno)` from close(2) |

**Socket Options**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `s.set_opt_int(level, optname, value)` | `fn(level: i32, optname: i32, value: i32) -> Result<(), Errno>` | setsockopt with an int; `Err(errno)` |
| `s.set_reuseaddr()` | `fn() -> Result<(), Errno>` | Enable SO_REUSEADDR |
| `s.set_reuseport()` | `fn() -> Result<(), Errno>` | Enable SO_REUSEPORT |
| `s.set_nodelay()` | `fn() -> Result<(), Errno>` | Disable Nagle |
| `s.set_io_timeout(timeout_ms)` | `fn(timeout_ms: i32) -> Result<(), Errno>` | SO_RCVTIMEO + SO_SNDTIMEO; 0 clears |

**Server Operations**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `s.bind(addr, port)` | `fn(addr: StrView, port: i32) -> Result<(), Errno>` | Bind; `Err(Inval)` for a bad address, else `Err(errno)` |
| `s.listen(backlog)` | `fn(backlog: i32) -> Result<(), Errno>` | Start listening; `Err(errno)` |
| `s.accept()` | `fn() -> Result<Socket, Errno>` | Accept (blocking); `Err(errno)`, e.g. `Inval` if not listening |
| `s.accept_nonblock()` | `fn() -> Result<Socket, Errno>` | Accept without blocking (peer is non-blocking too); `Err(Again)` if none pending |

**Client Operations**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `s.connect(addr, port)` | `fn(addr: StrView, port: i32) -> Result<(), Errno>` | Connect; `Err(Inval)` for a bad address, else `Err(errno)` |
| `s.connect_timeout(addr, port, timeout_ms)` | `fn(addr: StrView, port: i32, timeout_ms: i32) -> Result<(), Errno>` | Connect within `timeout_ms`; `Err(Inval)` bad address, `Err(TimedOut)`, else `Err(errno)` |
| `s.send_all(data)` | `fn(data: Span<u8>) -> Result<i64, Errno>` | Send every byte (retries short writes and EINTR) |
| `s.send_str(s)` | `fn(s: StrView) -> Result<i64, Errno>` | `s.send_all` for text |
| `s.recv_into(buf, max)` | `fn(buf: @&Vec<u8>, max: i64) -> Result<i64, Errno>` | Append up to `max` bytes; `Ok(0)` at EOF |
| `s.send(data)` | `fn(data: Span<u8>) -> Result<i64, Errno>` | Alias for `s.send_all(data)` |
| `s.recv(buf, max)` | `fn(buf: @&Vec<u8>, max: i64) -> Result<i64, Errno>` | Alias for `s.recv_into(buf, max)` |

**Epoll Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `epoll_create` | `fn() -> Result<i32, Errno>` | A new epoll instance's fd |
| `epoll_add` | `fn(epfd: i32, fd: i32, events: u32) -> Result<(), Errno>` | Watch fd; `Err(Exist)` if already watched |
| `epoll_del` | `fn(epfd: i32, fd: i32) -> Result<(), Errno>` | Stop watching fd; `Err(NoEnt)` if not watched |
| `epoll_mod` | `fn(epfd: i32, fd: i32, events: u32) -> Result<(), Errno>` | Change events; `Err(NoEnt)` if not watched |
| `epoll_wait_events` | `fn(epfd: i32, events: @&EpollEvent, maxevents: i32, timeout_ms: i32) -> Result<i32, Errno>` | Wait: `Ok(ready fds)`, `Ok(0)` on timeout, `Err(errno)` e.g. `Intr` |

---

### async_net

**Module**: `ritzlib.async_net`

Async TCP networking using io_uring.

**Socket Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `tcp_socket` | `fn() -> i32` | Create TCP socket |
| `tcp_socket_nonblock` | `fn() -> i32` | Create non-blocking |
| `set_reuseaddr` | `fn(fd: i32) -> i32` | Enable SO_REUSEADDR |
| `set_reuseport` | `fn(fd: i32) -> i32` | Enable SO_REUSEPORT |
| `set_nodelay` | `fn(fd: i32) -> i32` | Disable Nagle |
| `tcp_bind` | `fn(fd: i32, ip: i32, port: i32) -> i32` | Bind socket |
| `tcp_listen` | `fn(fd: i32, backlog: i32) -> i32` | Start listening |
| `tcp_accept` | `fn(fd: i32) -> i32` | Accept (blocking) |
| `tcp_connect` | `fn(fd: i32, ip: i32, port: i32) -> i32` | Connect |

**Runtime-based Async Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `runtime_accept` | `fn(rt: *Runtime, server_fd: i32) -> Result<i32, Errno>` | Async accept |
| `runtime_send` | `fn(rt: *Runtime, fd: i32, buf: *u8, len: i32) -> i64` | Async send |
| `runtime_recv` | `fn(rt: *Runtime, fd: i32, buf: *u8, len: i32) -> i64` | Async receive |

**IP Helpers**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `ipv4` | `fn(a: i32, b: i32, c: i32, d: i32) -> i32` | Create IPv4 address |
| `localhost` | `fn() -> i32` | 127.0.0.1 |
| `inaddr_any` | `fn() -> i32` | 0.0.0.0 |

---

## Async Runtime

### async.runtime

**Module**: `ritzlib.async.runtime`

Drives one future, or one blocking operation at a time, on an io_uring of its
own. For many concurrent tasks, use [async.tasks](#asynctasks).

**Poll sources**: `rt.poll_read(fd, buf, offset)` and `rt.poll_write(fd, buf, offset)` return `Option<i32>`, the type `await` reads in an async fn (LANGUAGE_SPEC §16.1): `None` while the operation is in flight (the future is suspended on it), then `Some(result)`, whatever the result is: 0 at EOF, -1 for -EPERM, -12 if no SQE was free (AGAST #4558).

```ritz
import ritzlib.uring

struct SpawnTask
    f: @&Future
    user_data: i64
    state: i32
    io_result: i32
    io_ready: i32

struct Runtime
    ring: IoUring
    initialized: i32
    next_user_data: i64
    waker_user_data: i64
    waker_io_result: i32
    waker_io_ready: i32
    waker_active: i32
    spawn_tasks: [64]SpawnTask
    spawn_count: i32
    current_task: i32
```

`waker_io_ready`, not the value of `waker_io_result`, says whether a completion
is waiting, so a read at EOF returns `Some(0)` rather than being resubmitted
(AGAST #2328). A hand-written poll function returns `None` while Pending and
`Some(v)` when Ready, so an -EPERM result it was handed is `Some(-1)`, never
read as Pending (AGAST #4558).

`rt.spawn`/`rt.run_spawned` queue several held futures on one runtime (LARB R79).
Each queued task has its own waker slot (`SpawnTask`): while a task's poll
runs, `current_task` names it, so `runtime_poll_*` records the operation's
`user_data` and result in that task rather than the runtime's single waker.
With `current_task` at -1 — `rt.block_on` and the legacy poll-fn drivers — the
single waker behaves exactly as before. `rt.run_spawned` fails loudly (exit 101),
as `rt.block_on` does, when a poll reports Pending without suspending on the ring
(LARB R78).

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_runtime` | `fn() -> *Runtime` | Get global runtime |
| `cleanup_runtime` | `fn()` | Cleanup global runtime |

| Method | Signature | Description |
|--------|-----------|-------------|
| `rt.init()` | `fn() -> i32` | Initialize runtime |
| `rt.destroy()` | `fn()` | Destroy runtime |
| `rt.read(fd, buf_sv, offset)` | `fn(fd: i32, buf_sv: Span<u8>, offset: i64) -> Result<i64, Errno>` | Read, waiting for the result |
| `rt.write(fd, buf_sv, offset)` | `fn(fd: i32, buf_sv: Span<u8>, offset: i64) -> Result<i64, Errno>` | Write, waiting for the result |
| `rt.close(fd)` | `fn(fd: i32) -> Result<(), Errno>` | Close, waiting for the result |
| `rt.block_on(f)` | `fn(f: @&Future)` | Poll a future to completion; read the result with `await p` (LARB R79) |
| `rt.spawn(f)` | `fn(f: @&Future)` | Queue a held future for `rt.run_spawned()`; the caller keeps it alive until the drain returns |
| `rt.run_spawned()` | `fn() -> i32` | Poll every spawned future until finished, waiting on the ring; 0 once the queue is drained |
| `rt.poll_read(fd, buf_sv, offset)` | `fn(fd: i32, buf_sv: Span<u8>, offset: i64) -> Option<i32>` | Inside a poll function: submit a read; `None` while it is in flight, then `Some(result)` |
| `rt.poll_write(fd, buf_sv, offset)` | `fn(fd: i32, buf_sv: Span<u8>, offset: i64) -> Option<i32>` | Inside a poll function: submit a write; `None` while it is in flight, then `Some(result)` |
| `rt.wait_for_io()` | `fn() -> i32` | Wait for a completion and record it for the waker |
| `rt.waker_register(user_data)` | `fn(user_data: i64)` | Suspend on an operation submitted by hand |
| `rt.waker_clear()` | `fn()` | Stop waiting for that operation |

`rt.poll_read` / `rt.poll_write` use the waker's ready flag, not its result value, so a read at
EOF (0) or a -EPERM completion (-1) is returned as a result rather than
resubmitted (AGAST #2328, #4485).

---

### async.tasks

**Module**: `ritzlib.async.tasks`

Multi-task async executor with io_uring for concurrent servers.

**Constants**:
- `MAX_TASKS`: 256
- `TASK_BUFFER_SIZE`: 8192

**Task States**: `TASK_IDLE`, `TASK_WAITING`, `TASK_READY`

```ritz
import ritzlib.uring
import ritzlib.iovec

struct Task
    id: i64
    state: i32
    fd: i32
    io_result: i32
    handler: fn(*Task) -> i32
    handler_state: i32
    read_buf: [8192]u8
    write_buf: [8192]u8
    read_len: i32
    write_len: i32
    write_pos: i32
    user_data: *u8
    request_count: i32
    iov_builder: IoVecBuilder
    last_activity: i64

struct TaskPool
    tasks: [256]Task
    next_id: i64
    active_count: i32
    ring: *IoUring

struct TaskServer
    listen_fd: i32
    pool: TaskPool
    ring: IoUring
    accept_user_data: i64
    running: i32
    shutdown_hook: fn() -> i32
    idle_timeout: i32
    timeout_user_data: i64
    timeout_ts: KernelTimespec
    max_connections: i32
```

**Task Pool Operations**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `pool.init(ring)` | `fn(ring: @&IoUring)` | Initialize pool |
| `pool.spawn(fd, handler)` | `fn(fd: i32, handler: fn(*Task) -> i32) -> bool` | Spawn task |
| `pool.complete(task)` | `fn(task: @&Task)` | Complete task |
| `pool.run()` | `fn() -> i32` | Run all tasks |
| `pool.alloc()` | `fn() -> Option<*Task>` | A free task slot, or `None` if the pool is full |
| `pool.find(task_id)` | `fn(task_id: i64) -> Option<*Task>` | A live task by its ID (`user_data`), or `None` |
| `pool.submit_recv(task)` | `fn(task: @&Task) -> bool` | Queue a recv into `task.read_buf`; false if no SQE was free |
| `pool.submit_send(task, len)` | `fn(task: @&Task, len: i32) -> bool` | Queue a send of `len` bytes of `task.write_buf` |
| `pool.submit_timeout(task, ts)` | `fn(task: @&Task, ts: @&KernelTimespec) -> bool` | Queue a relative timeout that wakes `task` (`io_result` is the kernel's code, e.g. -ETIME) |
| `pool.submit_nop(task)` | `fn(task: @&Task) -> bool` | Queue a NOP that wakes `task` on the next batch (a cooperative yield) |
| `pool.submit_send_buf(task, buf_sv)` | `fn(task: @&Task, buf_sv: Span<u8>) -> bool` | Send from an external buffer, valid until the CQE; short sends are the caller's to resume |
| `pool.submit_recv_buf(task, buf_sv)` | `fn(task: @&Task, buf_sv: Span<u8>) -> bool` | Recv into an external buffer, valid until the CQE |
| `pool.submit_sendv(task, iov)` | `fn(task: @&Task, iov: Span<Iovec>) -> bool` | Queue a vectored send |
| `pool.submit_send_zc(task, len)` | `fn(task: @&Task, len: i32) -> bool` | Zero-copy send from `task.write_buf`, valid until completion |
| `pool.submit_send_zc_buf(task, buf_sv)` | `fn(task: @&Task, buf_sv: Span<u8>) -> bool` | Zero-copy send from an external buffer, valid until the CQE |
| `pool.submit_splice(task, fd_out, fd_in, off_in, len, splice_flags)` | `fn(task: @&Task, fd_out: i32, fd_in: i32, off_in: i64, len: u32, splice_flags: i32) -> bool` | Splice `len` bytes from `fd_in` (offset `off_in`, -1 for the file position) to `fd_out` |

**Task I/O Operations**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `t.recv()` | `fn() -> bool` | Submit recv |
| `t.send(len)` | `fn(len: i32) -> bool` | Submit send |
| `t.sendv(iov)` | `fn(iov: Span<Iovec>) -> bool` | Submit writev |
| `t.sendv_builder()` | `fn() -> bool` | Send from IoVecBuilder |
| `t.send_zc(len)` | `fn(len: i32) -> bool` | Zero-copy send |
| `t.splice(fd_in, off_in, len, splice_flags)` | `fn(fd_in: i32, off_in: i64, len: u32, splice_flags: i32) -> bool` | Splice |
| `t.reset_for_recv()` | `fn() -> bool` | Reset for keep-alive |
| `t.timeout(ts)` | `fn(ts: @&KernelTimespec) -> bool` | `pool.submit_timeout` for this task |
| `t.yield()` | `fn() -> bool` | `pool.submit_nop` for this task |
| `t.send_buf(buf)` | `fn(buf: Span<u8>) -> bool` | `pool.submit_send_buf` for this task |
| `t.recv_buf(buf)` | `fn(buf: Span<u8>) -> bool` | `pool.submit_recv_buf` for this task |
| `t.send_zc_buf(buf)` | `fn(buf: Span<u8>) -> bool` | `pool.submit_send_zc_buf` for this task |

**Server Operations**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `srv.init(listen_fd)` | `fn(listen_fd: i32) -> i32` | Initialize server |
| `srv.destroy()` | `fn()` | Destroy server |
| `srv.run(handler)` | `fn(handler: fn(*Task) -> i32) -> i32` | Run server |
| `srv.run_multishot(handler)` | `fn(handler: fn(*Task) -> i32) -> i32` | Run with multishot accept |
| `srv.stop()` | `fn()` | Stop server |
| `srv.set_shutdown_hook(hook)` | `fn(hook: fn() -> i32)` | Set shutdown hook |
| `srv.set_idle_timeout(timeout_secs)` | `fn(timeout_secs: i32)` | Set idle timeout |
| `srv.set_max_connections(max_conns)` | `fn(max_conns: i32)` | Set max connections |
| `srv.free()` | `fn()` | Free a heap-allocated TaskServer |
| `srv.submit_accept()` | `fn() -> bool` | Queue an accept |
| `srv.submit_accept_multishot()` | `fn() -> bool` | Queue one multishot accept (5.19+) that yields a CQE per connection |
| `srv.submit_idle_timeout()` | `fn() -> i32` | Queue the periodic idle-check timeout (currently disabled: EINVAL on some kernels) |
| `srv.poll_tasks()` | `fn()` | Run the handler of every READY task |
| `srv.handle_accept(client_fd, handler)` | `fn(client_fd: i32, handler: fn(*Task) -> i32)` | Start a task for a new connection |
| `srv.wake_task(task_id, result)` | `fn(task_id: i64, result: i32)` | Wake a task with an I/O result |
| `srv.check_idle()` | `fn() -> i32` | Close idle connections; returns how many |

---

### async.blocking_fs

**Module**: `ritzlib.async.blocking_fs`

File calls with an `async fn` signature. Every one blocks the thread in a plain
syscall, so nothing overlaps. For I/O that suspends, use
[async.runtime](#asyncruntime) or [async.tasks](#asynctasks).

| Function | Signature | Description |
|----------|-----------|-------------|
| `async_open` | `async fn(path: *u8, flags: i32) -> i32` | Open file |
| `async_open3` | `async fn(path: *u8, flags: i32, mode: i32) -> i32` | Open with mode |
| `async_read` | `async fn(fd: i32, buf: *u8, count: i64) -> i64` | Read from fd |
| `async_write` | `async fn(fd: i32, buf: *u8, count: i64) -> i64` | Write to fd |
| `async_close` | `async fn(fd: i32) -> i32` | Close fd |
| `async_read_file` | `async fn(path: *u8, buf: *u8, buf_size: i64) -> i64` | Read entire file |
| `async_write_file` | `async fn(path: *u8, buf: *u8, count: i64) -> i64` | Write file |

---

### uring

**Module**: `ritzlib.uring`

Low-level io_uring bindings (Linux 5.1+).

**Opcodes**: `IORING_OP_NOP`, `IORING_OP_READV`, `IORING_OP_WRITEV`, `IORING_OP_READ`, `IORING_OP_WRITE`, `IORING_OP_ACCEPT`, `IORING_OP_CONNECT`, `IORING_OP_CLOSE`, `IORING_OP_SEND`, `IORING_OP_RECV`, `IORING_OP_SEND_ZC`, `IORING_OP_SPLICE`, `IORING_OP_TIMEOUT`

**Structures**:

```ritz
struct IoUringSqe
    opcode: u8
    flags: u8
    ioprio: u16
    fd: i32
    off: i64
    addr: i64
    len: i32
    rw_flags: i32
    user_data: i64
    # ... (64 bytes total)

struct IoUringCqe
    user_data: i64
    res: i32
    flags: i32

struct IoUring
    ring_fd: i32
    sq_head: *i32
    sq_tail: *i32
    sq_mask: i32
    sq_entries: i32
    sq_array: *i32
    sqes: *IoUringSqe
    cq_head: *i32
    cq_tail: *i32
    cq_mask: i32
    cq_entries: i32
    cqes: *IoUringCqe
    # ... plus the six mmap bookkeeping fields (sq_ring_ptr/size,
    #     cq_ring_ptr/size, sqes_ptr/size)
```

**Ring Operations**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `ring.init(entries)` | `fn(entries: i32) -> i32` | Initialize ring |
| `ring.destroy()` | `fn()` | Destroy ring |
| `ring.get_sqe()` | `fn() -> Option<*IoUringSqe>` | Get SQE (None when the ring is full) |
| `ring.sqe_submit()` | `fn()` | Advance SQ tail |
| `ring.submit()` | `fn() -> Result<i32, Errno>` | Submit pending SQEs: `Ok(count)`, `Ok(0)` with none pending (no syscall) |
| `ring.submit_and_wait(min_complete)` | `fn(min_complete: i32) -> Result<i32, Errno>` | Submit and wait for `min_complete` CQEs |
| `ring.peek_cqe()` | `fn() -> Option<*IoUringCqe>` | Peek CQE (None when none is ready) |
| `ring.wait_cqe()` | `fn() -> Option<*IoUringCqe>` | Wait for CQE |
| `ring.cqe_seen(cqe)` | `fn(cqe: @IoUringCqe)` | Mark CQE consumed |
| `ring.cleanup()` | `fn()` | Alias for `ring.destroy()` |

**SQE Preparation**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `sqe.prep_read(fd, buf, offset, user_data)` | `fn(fd: i32, buf: Span<u8>, offset: i64, user_data: i64)` | Prepare read |
| `sqe.prep_write(fd, buf, offset, user_data)` | `fn(fd: i32, buf: Span<u8>, offset: i64, user_data: i64)` | Prepare write |
| `sqe.prep_accept(fd, flags, user_data)` | `fn(fd: i32, flags: i32, user_data: i64)` | Prepare accept (no peer address) |
| `sqe.prep_accept_from(fd, peer, flags, user_data)` | `fn(fd: i32, peer: @&SockAddrStorage, flags: i32, user_data: i64)` | Accept, the kernel writing the peer's address and length into `peer` |
| `sqe.prep_accept_multishot(fd, flags, user_data)` | `fn(fd: i32, flags: i32, user_data: i64)` | Multishot accept (5.19+) |
| `sqe.prep_close(fd, user_data)` | `fn(fd: i32, user_data: i64)` | Prepare close |
| `sqe.prep_recv(fd, buf, flags, user_data)` | `fn(fd: i32, buf: Span<u8>, flags: i32, user_data: i64)` | Prepare recv |
| `sqe.prep_send(fd, buf, flags, user_data)` | `fn(fd: i32, buf: Span<u8>, flags: i32, user_data: i64)` | Prepare send |
| `sqe.prep_send_zc(fd, buf, flags, user_data)` | `fn(fd: i32, buf: Span<u8>, flags: i32, user_data: i64)` | Zero-copy send (6.0+) |
| `sqe.prep_readv(fd, iov, offset, user_data)` | `fn(fd: i32, iov: Span<Iovec>, offset: i64, user_data: i64)` | Vectored read |
| `sqe.prep_writev(fd, iov, offset, user_data)` | `fn(fd: i32, iov: Span<Iovec>, offset: i64, user_data: i64)` | Vectored write |
| `sqe.prep_splice(fd_out, off_out, fd_in, off_in, len, splice_flags, user_data)` | `fn(fd_out: i32, off_out: i64, fd_in: i32, off_in: i64, len: u32, splice_flags: i32, user_data: i64)` | Splice |
| `sqe.prep_timeout(ts, count, flags, user_data)` | `fn(ts: @KernelTimespec, count: u32, flags: u32, user_data: i64)` | Timeout |
| `sqe.prep_connect(fd, addr, user_data)` | `fn(fd: i32, addr: @SockAddrStorage, user_data: i64)` | Prepare connect to `addr` (`addr.len` bytes) |
| `sqe.prep_nop(user_data)` | `fn(user_data: i64)` | An immediate CQE with no work (a cooperative yield) |
| `sqe.prep_send_zc_report(fd, buf, flags, user_data)` | `fn(fd: i32, buf: Span<u8>, flags: i32, user_data: i64)` | `prep_send_zc` that asks the kernel to report whether zero-copy was used |

| Method | Signature | Description |
|--------|-----------|-------------|
| `cqe.get_data64()` | `fn() -> i64` | The CQE's `user_data` |

**Lifetimes**: every `prep_*` that takes a buffer, iovec span, address or
timespec hands the kernel its address; the kernel reads or writes it after the
call returns. Keep it valid (not freed, not reused, not a stack temporary that
goes out of scope) until that SQE's CQE arrives. The span form makes the
length travel with the pointer; it can't check this lifetime (S-PTR-6).
`SockAddrStorage` (`ritzlib.net`) is 128 bytes plus its `len`;
`sockaddr_storage_new()` gives one ready for `prep_accept_from`.

---

## Process Management

### process

**Module**: `ritzlib.process`

Subprocess spawning with connected pipes. Every fn on a live `Process` takes
`@&Process` (they close fds and record the wait); `p.valid()` only reads
it (AGAST #3750). Every fallible fn returns `Result<T, Errno>` (`ritzlib.errno`,
which `ritzlib.process` re-exports), never `-1` or a negative errno (#4298).

```ritz
struct Process
    pid: i32
    stdin_fd: i32
    stdout_fd: i32
    stderr_fd: i32
    waited: i32

struct ProcessResult
    exit_code: i32
    signaled: i32
    signal: i32
```

**Spawning**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `spawn` | `fn(cmd: StrView, args: Span<StrView>) -> Result<Process, Errno>` | Spawn `cmd` (found by `find_command`) with `args` as argv[1..]; argv[0] is `cmd` as given. `Err` is an `Errno`: `NoEnt` not found, `Acces` not executable, `NoMem`, or a pipe/fork failure |
| `spawn_env` | `fn(cmd: StrView, args: Span<StrView>, env: Span<StrView>) -> Result<Process, Errno>` | `spawn`, but the child's environment is exactly `env` (`"KEY=VALUE"` views, nothing of ours merged in; an empty span is empty). `spawn` inherits ours |
| `spawn_env_merged` | `fn(cmd: StrView, args: Span<StrView>, env: Span<StrView>, stdin_fd: i32) -> Result<Process, Errno>` | `spawn_env`, but the child reads stdin from `stdin_fd` (dup'd; the caller still closes it; negative is `Err(BadF)`) and its stderr goes down the stdout pipe (`2>&1`), so `read_stdout_all` gets both in order. The `Process` has no stdin or stderr pipe. For test harnesses: `ritzlib.testlib`'s `exec_capture` |

| Method | Signature | Description |
|--------|-----------|-------------|
| `p.valid()` | `fn() -> bool` | Whether the spawn gave a live pid |

**I/O Operations**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `p.write_all(data)` | `fn(data: StrView) -> Result<i64, Errno>` | Write all of `data` to stdin (retries short writes and EINTR); `Ok(data.len)`, `Err(BadF)` once stdin is closed, `Err(Pipe)` once the child closed it |
| `p.close_stdin()` | `fn()` | Close stdin (EOF) |
| `p.read_stdout(buf)` | `fn(buf: Span<u8>) -> Result<i64, Errno>` | Read up to `buf.len` bytes of stdout into `buf`: `Ok(n)`, `Ok(0)` at EOF, `Err(BadF)` once the pipe is closed |
| `p.read_stdout_all()` | `fn() -> Vec<u8>` | Read all stdout |
| `p.read_line()` | `fn() -> Vec<u8>` | Read line |
| `p.read_stderr(buf)` | `fn(buf: Span<u8>) -> Result<i64, Errno>` | `p.read_stdout` for stderr |
| `p.read_stderr_all()` | `fn() -> Vec<u8>` | Read all stderr |

**Lifecycle**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `p.wait()` | `fn() -> Result<ProcessResult, Errno>` | Close stdin and block until exit; `Err(Child)` if nothing is left to wait for (already waited), else `Err` from wait4 |
| `p.try_wait()` | `fn() -> Option<ProcessResult>` | The result if the child has exited (reaping it), else `None`; never blocks |
| `p.kill()` | `fn()` | Kill process |
| `p.close_pipes()` | `fn()` | Close all pipes |
| `p.cleanup()` | `fn()` | Full cleanup |

**Result Helpers**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `r.success()` | `fn() -> bool` | Exited normally with code 0? The code itself is `r.exit_code` |

**PATH Search**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `find_command` | `fn(name: StrView) -> Option<String>` | Search `$PATH`, or the standard dirs if it is unset or empty |
| `find_command_in` | `fn(name: StrView, path: StrView) -> Option<String>` | Search a `:`-separated dir list: first executable `dir/name`; an empty component is `.`; a name with `/` comes back as is |

**fork / exec / wait / kill** (AGAST #4637). The bare primitives, for a caller
that needs the child itself (a daemon, a worker, a redirect `spawn` doesn't
cover). To run a program and read its output, use `spawn`.

| Function | Signature | Description |
|----------|-----------|-------------|
| `fork` | `fn() -> Result<ForkResult, Errno>` | `Ok(Child)` in the new process, `Ok(Parent(pid))` in this one |
| `exec` | `fn(path: StrView, args: Span<StrView>) -> Errno` | execve(2) `path` (no `$PATH` search) with argv[0] = `path`, argv[1..] = `args`, our environment. Returns only on failure, with why |
| `wait_pid` | `fn(pid: i32) -> Result<ProcessResult, Errno>` | Block until child `pid` exits; `Err(Child)` if it isn't ours or was already reaped |
| `try_wait_pid` | `fn(pid: i32) -> Result<Option<ProcessResult>, Errno>` | `wait_pid` without blocking: `Ok(None)` while it runs |
| `kill` | `fn(pid: i32, sig: i32) -> Result<(), Errno>` | Send `sig` (0 checks the pid exists); `Err(Other(3))` (ESRCH) if there's no such process |

```ritz
import ritzlib.process
import ritzlib.fd
import ritzlib.sys { sys_exit }
import ritzlib.span
import ritzlib.result

# Run /bin/true with stdout redirected to `out`; its exit code, or -errno.
fn run_true_into(out: @Fd) -> i32
    match fork()
        Ok(fr) =>
            match fr
                Child =>
                    out.dup_to(1)
                    exec("/bin/true", span_empty<StrView>())
                    sys_exit(127)
                    0
                Parent(pid) =>
                    match wait_pid(pid)
                        Ok(r) => r.exit_code
                        Err(e) => -e.code()
        Err(e) => -e.code()
```

---

### argspec

**Module**: `ritzlib.argspec`

Command-line parsing, the idiomatic way (AGAST #1448).  It replaced the
`ritzlib.args` ArgParser API, deleted in #4046.  `examples/tier2_stdlib/77_args`
exercises every function.

Arguments are `StrView`s pointing into argv (nothing is copied), the spec is a
struct holding a `Vec<ArgFlag>`, lookups return `Option`, and parse failures
come back as `Result<_, ArgError>` rather than being printed by the parser.
A lookup `name` matches an option's long name, or its short name if it is one
byte (`"count"` or `"n"`).

**argv**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `args_from_argv` | `fn(argc: i32, argv: **u8) -> Vec<StrView>` | Every argv entry, argv[0] included |
| `args_tail` | `fn(all: @Vec<StrView>) -> Span<StrView>` | The arguments after the program name |
| `args_get` | `fn(args: @Span<StrView>, i: i64) -> Option<StrView>` | Bounds-checked element |

**Spec**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `argspec_new` | `fn(program: StrView, about: StrView) -> ArgSpec` | Empty spec (free: it builds one) |
| `spec.switch` | `fn(short: u8, long: StrView, help: StrView)` | Boolean option (`short` 0 / `long` `""` to omit a form) |
| `spec.option` | `fn(short: u8, long: StrView, value_name: StrView, help: StrView, default: Option<StrView>)` | Option taking a value |
| `spec.positionals` | `fn(name: StrView, help: StrView, min: i64, max: i64)` | Accept min..max positionals (`ARGS_UNLIMITED` = no max); none without this call |
| `spec.find` | `fn(name: StrView) -> Option<i64>` | Index of an option |
| `spec.parse` | `fn(args: Span<StrView>) -> Result<ParsedArgs, ArgError>` | Parse |
| `spec.print_help` | `fn()` | Usage, options and arguments on stdout |
| `spec.deinit` | `fn()` | Leave the spec empty; the compiler frees its slots at scope end (AGAST #2159) |

**Result** (a `ParsedArgs` shares the spec's storage; drop it first):

| Method | Signature | Description |
|--------|-----------|-------------|
| `p.switch` | `fn(name: StrView) -> bool` | Switch given? (false for value options) |
| `p.is_set` | `fn(name: StrView) -> bool` | Option given at all? |
| `p.value` | `fn(name: StrView) -> Option<StrView>` | Given value, else default, else None |
| `p.int` | `fn(name: StrView) -> Result<i64, ArgError>` | `p.value(name)` as an i64 |
| `p.positional` | `fn(i: i64) -> Option<StrView>` | i-th positional |
| `p.positionals` | `fn() -> Span<StrView>` | All positionals |
| `p.deinit` | `fn()` | Leave the result empty; the compiler frees its Vecs at scope end (AGAST #2159) |

**Errors**: `ArgError` is a struct `{ kind: ArgErrorKind, text: StrView, limit: i64 }`
with kinds `UnknownOption`, `MissingValue`, `UnexpectedValue`,
`MissingPositional`, `TooManyPositionals`, `NotANumber` and `NotSet`.
`spec.error_print(e)` writes `"<program>: <message>"` to stderr, and
`arg_parse_i64(s: StrView) -> Result<i64, ArgError>` is the strict decimal
parser `p.int` uses (sign, digits, range-checked).

**Example**:
```ritz
import ritzlib.io
import ritzlib.option
import ritzlib.result
import ritzlib.strview
import ritzlib.gvec
import ritzlib.argspec

fn run(p: ParsedArgs) -> i32
    var parsed = p
    if parsed.switch("verbose")
        prints("verbose\n")
    let count: i64 = match parsed.int("count")
        Ok(n) => n
        Err(e) => -1
    count as i32

fn fail(spec: @ArgSpec, e: ArgError) -> i32
    spec.error_print(@e)
    2

fn main(argc: i32, argv: **u8) -> i32
    var all = args_from_argv(argc, argv)
    var spec = argspec_new("myprogram", "Description")
    spec.switch('v', "verbose", "Enable verbose output")
    spec.option('n', "count", "NUM", "Number of items", Some("10"))
    spec.positionals("FILE", "Input file(s)", 0, ARGS_UNLIMITED)
    let status: i32 = match spec.parse(args_tail(@all))
        Ok(p) => run(p)
        Err(e) => fail(@spec, e)
    status
```

ritz1 compiles this module: `77_args` and the tier2 examples ported to it in
#1490 build and pass under ritz1 and ritz1_selfhosted.

---

### os.env

**Module**: `ritzlib.os.env`

Environment variable access from any function, whatever `main`'s signature.
The first call reads `/proc/self/environ` once and caches it; every key and
value is a zero-copy `StrView` into that cache.

| Function | Signature | Description |
|----------|-----------|-------------|
| `env_get` | `fn(name: StrView) -> Option<StrView>` | Value of `name`, or `None` if unset |
| `env_get_p` | `fn(name: *StrView) -> Option<StrView>` | `env_get` taking the name by pointer |
| `env_get_or` | `fn(name: StrView, default: StrView) -> StrView` | Value of `name`, or `default` |
| `env_iter` | `fn() -> Span<StrView>` | Every `"KEY=VALUE"` entry, in order |
| `env_raw_envp` | `fn() -> **u8` | The same entries as a NULL-terminated C `envp`, for `sys_execve` only |

A get-or-die `env_must` helper deliberately does *not* live here: S-ERR-3 says
a library returns its failure to the caller, so only a program decides to
exit. A program that wants one writes it on top of `env_get` (see
`examples/tier4_applications/41_osenv`).

**Example**:
```ritz
import ritzlib.sys
import ritzlib.io
import ritzlib.option
import ritzlib.strview
import ritzlib.span
import ritzlib.os.env

fn show(o: Option<StrView>) -> i32
    match o
        Some(v) => prints(v)
        None => prints("(unset)")
    prints("\n")
    0

fn main() -> i32
    show(env_get("HOME"))
    let port: StrView = env_get_or("PORT", "8080")
    prints(port)
    prints("\n")
    let entries: Span<StrView> = env_iter()
    print_int(entries.len)
    prints(" variables\n")
    0
```

To run a child with the current environment, pass `env_raw_envp()` as
`sys_execve`'s third argument. It is the only raw-pointer accessor, kept for
that interop; the strings are the cached entries, so it costs no copying.

---

## Utilities

### timer

**Module**: `ritzlib.timer`

High-precision timing with nanosecond resolution.

**Clock Types**: `CLOCK_REALTIME`, `CLOCK_MONOTONIC`, `CLOCK_PROCESS_CPUTIME_ID`, `CLOCK_THREAD_CPUTIME_ID`

```ritz
struct Timespec
    tv_sec: i64
    tv_nsec: i64

struct Timer
    start: Timespec
    end: Timespec

struct Stopwatch
    total_ns: i64
    count: i64
    running: i32
    start_ns: i64
```

**Time Functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `now_nanos` | `fn() -> i64` | Current time in nanoseconds |
| `now_micros` | `fn() -> i64` | Current time in microseconds |
| `now_millis` | `fn() -> i64` | Current time in milliseconds |

**Timer**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `t.init()` | `fn() -> i32` | Initialize |
| `t.start()` | `fn() -> i32` | Start timer |
| `t.stop()` | `fn() -> i32` | Stop timer |
| `t.elapsed_nanos()` | `fn() -> i64` | Get elapsed ns |
| `t.elapsed_micros()` | `fn() -> i64` | Get elapsed us |
| `t.elapsed_millis()` | `fn() -> i64` | Get elapsed ms |
| `t.elapsed_secs_x1000()` | `fn() -> i64` | Elapsed seconds x1000 (3 decimal places), truncated: the same value as `elapsed_millis()` |
| `t.print()` | `fn() -> i32` | Print human-readable |

**Stopwatch** (cumulative timing):

| Method | Signature | Description |
|--------|-----------|-------------|
| `sw.init()` | `fn() -> i32` | Initialize |
| `sw.start()` | `fn() -> bool` | Start (false if already running) |
| `sw.stop()` | `fn() -> bool` | Stop (false if not running) |
| `sw.reset()` | `fn() -> i32` | Reset |
| `sw.total_nanos()` | `fn() -> i64` | Total ns |
| `sw.avg_nanos()` | `fn() -> i64` | Average ns |
| `sw.count()` | `fn() -> i64` | Number of samples |
| `sw.print()` | `fn() -> i32` | Print stats |

---

### time

**Module**: `ritzlib.time`

`Duration`, `sleep` and the wall clock (AGAST #4637), so a program never
builds a nanosleep timespec array by hand. For elapsed-time measurement use
[timer](#timer)'s monotonic clock: the wall clock can jump.

| Function | Signature | Description |
|----------|-----------|-------------|
| `duration_ns` / `duration_us` / `duration_ms` / `duration_secs` | `fn(n: i64) -> Duration` | A Duration (held as nanoseconds) |
| `sleep` | `fn(d: Duration)` | Block at least `d`; a signal doesn't cut it short; `<= 0` returns at once |
| `sleep_ms` | `fn(ms: i64)` | `sleep(duration_ms(ms))` |
| `now` | `fn() -> Timeval` | Wall clock: `tv_sec`, `tv_usec` since the Unix epoch |
| `now_unix_ms` | `fn() -> i64` | `now()` in milliseconds |

| Method | Signature | Description |
|--------|-----------|-------------|
| `d.as_nanos()` / `as_micros()` / `as_millis()` / `as_secs()` | `fn() -> i64` | Converted, truncating toward zero |

```ritz
import ritzlib.time

# Poll `ready` every 10 ms for up to `limit`; whether it became ready.
fn wait_until(ready: fn() -> bool, limit: Duration) -> bool
    var waited: i64 = 0
    while waited < limit.as_millis()
        if ready()
            return true
        sleep_ms(10)
        waited += 10
    ready()
```

---

### json

**Module**: `ritzlib.json`

JSON parsing and serialization.

**Value Types**: `JSON_NULL`, `JSON_BOOL`, `JSON_NUMBER`, `JSON_STRING`, `JSON_ARRAY`, `JSON_OBJECT`

```ritz
struct JsonValue
    kind: i32
    bool_val: i32
    num_val: i64
    float_val: i64   # reserved; unused until float support lands
    str_val: *u8
    str_len: i64
    items: **JsonValue
    count: i64
    keys: **u8

struct JsonError
    code: i32
    pos: i64
```

**Parsing**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `json_parse` | `fn(input: StrView) -> Result<*JsonValue, JsonError>` | Parse the first JSON value in `input` |
| `json_parse2` | `fn(input: *u8, len: i64) -> Result<*JsonValue, JsonError>` | Deprecated wrapper: `json_parse(strview_from_ptr(input, len))` |

| Method | Signature | Description |
|--------|-----------|-------------|
| `v.free()` | `fn()` | Free JSON tree |

Strings are decoded to UTF-8: `\n \t \r \b \f \/ \" \\` and `\uXXXX`, with a
surrogate pair (`😀`) combined into one 4-byte sequence. Bad hex
digits, a short `\u`, a surrogate without its other half, or any other
escape (`\q`, `\x41`) fail with `JSON_ERR_INVALID_ESCAPE` at the escape's
backslash. `\u0000` is kept in a string value (`str_len` and
`v.get_string()` count it) but rejected in an object key, which is stored as
a NUL-terminated `*u8`. A raw control character (U+0000–U+001F) inside a
string, key or value, fails with `JSON_ERR_CONTROL_CHAR` at that byte: RFC
8259 requires them escaped. Tabs and newlines between tokens are whitespace
and stay legal.

**Value Access**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `v.get_field(key)` | `fn(key: StrView) -> Option<*JsonValue>` | Object field; None if missing or not an object |
| `v.get_index(idx)` | `fn(idx: i64) -> Option<*JsonValue>` | Array element; None if out of range or not an array |
| `v.get_string()` | `fn() -> Option<StrView>` | String value, borrowed from `v`; None if not a string |
| `v.get_number()` | `fn() -> Option<i64>` | Number value; None if not a number |
| `v.get_bool()` | `fn() -> Option<bool>` | Bool value; None if not a bool |
| `v.is_null()` | `fn() -> bool` | Check if null |
| `v.array_len()` | `fn() -> i64` | Get array length |
| `v.object_len()` | `fn() -> i64` | Get object size |

**Serialization**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `json_emit_bytes` | `fn(s: *u8, len: i64, buf: *Vec<u8>) -> i32` | Emit `s[0..len)` as a string; control characters as `\b \f \n \r \t` or `\u00XX` |
| `json_emit_string` | `fn(s: *u8, buf: *Vec<u8>) -> i32` | `json_emit_bytes` up to the first NUL |

| Method | Signature | Description |
|--------|-----------|-------------|
| `v.emit(buf)` | `fn(buf: @&Vec<u8>) -> i32` | Emit to buffer |
| `v.to_string()` | `fn() -> String` | JSON text; the caller owns it, and its `Drop` impl frees it at scope end |

**Error Messages**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `json_error_message` | `fn(code: i32) -> StrView` | Get error message |

---

### elf

**Module**: `ritzlib.elf`

ELF binary format parser for extracting symbols.

**Constants**:
- `ELFCLASS64`, `ELFDATA2LSB`
- `SHT_SYMTAB`, `SHT_STRTAB`, `SHT_DYNSYM`
- `STB_LOCAL`, `STB_GLOBAL`, `STB_WEAK`
- `STT_NOTYPE`, `STT_FUNC`

```ritz
struct Elf64_Ehdr
    e_ident: [16]u8
    e_type: i16
    e_machine: i16
    e_version: i32
    e_entry: i64
    e_phoff: i64
    e_shoff: i64
    e_flags: i32
    e_ehsize: i16
    e_phentsize: i16
    e_phnum: i16
    e_shentsize: i16
    e_shnum: i16
    e_shstrndx: i16

struct Elf64_Shdr
    sh_name: i32
    sh_type: i32
    sh_flags: i64
    sh_addr: i64
    sh_offset: i64
    sh_size: i64
    sh_link: i32
    sh_info: i32
    sh_addralign: i64
    sh_entsize: i64

struct Elf64_Sym
    st_name: i32
    st_info: u8
    st_other: u8
    st_shndx: i16
    st_value: i64
    st_size: i64

struct ElfReader
    data: *u8
    size: i64
    ehdr: *Elf64_Ehdr
    shdr: *Elf64_Shdr
    symtab: *Elf64_Sym
    symtab_count: i64
    strtab: *u8
```

| Function | Signature | Description |
|----------|-----------|-------------|
| `elf_is_function` | `fn(info: u8) -> i32` | Is function? |
| `elf_is_global` | `fn(info: u8) -> i32` | Is global? |

| Method | Signature | Description |
|--------|-----------|-------------|
| `elf.init(data_sv)` | `fn(data_sv: Span<u8>) -> Result<(), ElfError>` | Initialize |
| `elf.parse_sections()` | `fn() -> Result<(), ElfError>` | Parse sections |
| `elf.get_symbol_name(sym_index)` | `fn(sym_index: i64) -> Option<*u8>` | Get symbol name |
| `elf.get_symbol_info(sym_index)` | `fn(sym_index: i64) -> u8` | Get symbol info |
| `elf.symbol_count()` | `fn() -> i64` | Get symbol count |
| `elf.find_test_functions(callback, user_data)` | `fn(callback: *u8, user_data: *u8) -> i32` | Find test_* functions |
| `elf.print_test_functions()` | `fn()` | Print test functions |

---

### endian

**Module**: `ritzlib.endian`

Reads and writes multi-byte integers in a caller-owned byte buffer, in the byte
order a wire or file format chose (AGAST #1858). The pointer is byte-addressed,
so it need not be aligned (packed headers, ELF and MADT records). There is no
bounds check: the caller owns the buffer, as with `*u8` everywhere.

| Function | Signature | Description |
|----------|-----------|-------------|
| `endian_read_u16_be` / `_le` | `fn(p: *u8) -> u16` | Read a u16 in big / little endian |
| `endian_read_u32_be` / `_le` | `fn(p: *u8) -> u32` | Read a u32 in big / little endian |
| `endian_read_u64_be` / `_le` | `fn(p: *u8) -> u64` | Read a u64 in big / little endian |
| `endian_write_u16_be` / `_le` | `fn(p: *u8, v: u16)` | Write a u16 in big / little endian |
| `endian_write_u32_be` / `_le` | `fn(p: *u8, v: u32)` | Write a u32 in big / little endian |
| `endian_write_u64_be` / `_le` | `fn(p: *u8, v: u64)` | Write a u64 in big / little endian |

```ritz
import ritzlib.endian

fn main() -> i32
    var b: [4]u8 = [0, 0, 0, 0]
    endian_write_u32_be(@b[0], 0xdeadbeef)
    if endian_read_u32_be(@b[0]) == 0xdeadbeef
        0
    else
        1
```

Swapping the bytes of an integer value is the language's `x.swap_bytes()`
(`ritzlib/tests/test_bitops.ritz`), not this module.

---

### testing

`ritzlib.testing` was removed by AGAST #1869. Its helpers (`assert_msg`,
`assert_eq_i64`, `assert_eq_i32`, `assert_not_null`, `assert_null`) are all the
`assert` statement now: a failing `assert a == b` prints both operands, and
`assert` works in any `[[test_helper]]` fn, reporting the calling test's line
(LANGUAGE_SPEC §17.1, §19.2). Tests are run by ritzunit.

```ritz
[[test_helper]]
fn expect_not_null(p: *u8)
    assert p != null, "want ptr"

[[test]]
fn test_addition() -> i32
    let got: i64 = 1 + 1
    assert got == 2, "sum"
    expect_not_null(c"x")
    0
```

---

## Quick Reference

### Import Patterns

```ritz
import ritzlib.sys         # Syscalls
import ritzlib.io          # Console I/O
import ritzlib.string      # String type
import ritzlib.gvec        # Vec<T>
import ritzlib.memory      # malloc/free, Arena
import ritzlib.fs          # Filesystem
import ritzlib.net         # Networking
import ritzlib.async.tasks # Async server
```

### Common Patterns

**Reading a file**:
```ritz
import ritzlib.fs
import ritzlib.string
import ritzlib.io
import ritzlib.result

fn show_file(path: StrView) -> i32
    var r: Result<String, Errno> = read_file(path)
    match r
        Ok(content) =>
            print_string(@content)
            0
        Err(e) => e.code()
```

**Creating a TCP server**:
```ritz
import ritzlib.async_net

fn serve() -> i32
    let fd: i32 = tcp_socket()
    set_reuseaddr(fd)
    tcp_bind(fd, inaddr_any(), 8080)
    tcp_listen(fd, 128)
    let client: i32 = tcp_accept(fd)
    client
```

**Using Vec**:
```ritz
import ritzlib.gvec

fn vec_demo() -> i32
    var v: Vec<i32> = vec_new<i32>()
    v.push(42)
    let val: i32 = v.get(0)
    val
```

**Async server with io_uring**:
```ritz
import ritzlib.async.tasks

fn handle_connection(task: *Task) -> i32
    0

fn run_server(listen_fd: i32) -> i32
    var srv: TaskServer
    srv.init(listen_fd)
    srv.run(handle_connection)
    srv.destroy()
    0
```

---

*This documentation covers ritzlib as of 2026-09-03. Every fenced `ritz` block
above is compiled against the real ritzlib by `tools/check_doc_examples.py` on
every build, so the examples cannot silently rot; the signature tables are
hand-checked against `ritzlib/*.ritz` and are not machine-verified, so the
source files remain the final authority.*
