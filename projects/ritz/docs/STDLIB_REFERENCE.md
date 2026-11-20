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
   - [iovec](#iovec) - Vectored I/O for scatter/gather writes
7. [Networking](#networking)
   - [net](#net) - TCP/IP socket operations
   - [async_net](#async_net) - Async TCP networking
8. [Async Runtime](#async-runtime)
   - [async.runtime](#asyncruntime) - Drive one future with `block_on`
   - [async.tasks](#asynctasks) - Multi-task executor
   - [async.blocking_fs](#asyncblocking_fs) - Blocking file calls behind `async fn`
   - [uring](#uring) - io_uring bindings
9. [Process Management](#process-management)
   - [process](#process) - Subprocess spawning
   - [argspec](#argspec) - Argument parsing
   - [os.env](#osenv) - Environment variables
10. [Utilities](#utilities)
    - [timer](#timer) - High-precision timing
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
    while i < vec_len<i32>(items)
        if vec_get<i32>(items, i) == target
            return Some(i as i32)
        i += 1
    return None
```

`vec_len` and `vec_get` are generic and ritz0 does not infer the type argument
at the call site, so it must be written out: `vec_len<i32>(items)`.

---

### result

**Module**: `ritzlib.result`

Represents either a success value or an error value. Essential for error handling.

```ritz
enum Result<T, E>
    Ok(T)
    Err(E)
```

**Functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `result_is_ok` | `fn<T, E>(res: *Result<T, E>) -> i32` | Returns 1 if Ok |
| `result_is_err` | `fn<T, E>(res: *Result<T, E>) -> i32` | Returns 1 if Err |
| `result_unwrap_or` | `fn<T, E>(res: *Result<T, E>, default: T) -> T` | Returns value or default |
| `result_ok` | `fn<T, E>(res: *Result<T, E>) -> Option<T>` | Convert to Option, discarding error |
| `result_err` | `fn<T, E>(res: *Result<T, E>) -> Option<E>` | Convert to Option of error |

**Example**:
```ritz
import ritzlib.option
import ritzlib.result
import ritzlib.strview

fn parse_int(s: StrView) -> Result<i64, i32>
    match strview_parse_i64(s)
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
| `arena_alloc` | `fn(a: *Arena, size: i64) -> *u8` | Allocate bytes (8-byte aligned) |
| `arena_alloc_zero` | `fn(a: *Arena, size: i64) -> *u8` | Allocate and zero-initialize |
| `arena_alloc_array` | `fn(a: *Arena, count: i64, elem_size: i64) -> *u8` | Allocate array |
| `arena_reset` | `fn(a: *Arena)` | Reset arena (free all, keep memory) |
| `arena_destroy` | `fn(a: *Arena)` | Free underlying memory |
| `arena_used` | `fn(a: *Arena) -> i64` | Get current usage |
| `arena_remaining` | `fn(a: *Arena) -> i64` | Get remaining capacity |
| `arena_valid` | `fn(a: *Arena) -> i32` | Check if arena is valid |

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
    let prev: PageSource = page_source_set(PageSource { map: no_pages, unmap: give_back })
    let p: *u8 = malloc(8192)  # null: the source had no pages
    page_source_set(prev)
    if p == null
        return 0
    return 1
```

| Function | Signature | Description |
|----------|-----------|-------------|
| `page_source_set` | `fn(src: PageSource) -> PageSource` | Install `src`; returns the source it replaces |
| `page_source_get` | `fn() -> PageSource` | The installed source (the platform hooks until set) |
| `mmap_failed` | `fn(p: *u8) -> bool` | True for null and `-errno` (any `p <= 0`) |

Install a source before the first allocation, or restore the previous one
before anything allocated under it is freed. To give one subsystem its own
pages instead, build its collections on a `heap_allocator` or `pages_allocator`
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

fn arena_vec() -> i64
    var ar: Arena = arena_new(65536)
    var a: Allocator = arena_allocator(@ar)
    var v: Vec<i64> = vec_new_in<i64>(@a)   # every grow comes from `ar`
    vec_push<i64>(@&v, 7)
    let x: i64 = vec_get<i64>(@v, 0)
    vec_drop<i64>(@&v)                      # back to `a`, not the global heap
    arena_destroy(@ar)
    x
```

`malloc_in(a, n)` takes `n + 16` bytes from `a`, and the block's header names
`a` as its owner. Plain `free` and `realloc` read that header, so collection
code is unchanged and a block never goes back to the wrong allocator. A null
owner is the global heap. The `Allocator` must stay at its address while any
block it handed out is live, because the header points at it.

| Function | Signature | Description |
|----------|-----------|-------------|
| `malloc_in` | `fn(a: *Allocator, size: i64) -> *u8` | `size` bytes owned by `a` (null `a`: `malloc`) |
| `allocator_of` | `fn(p: *u8) -> *Allocator` | `p`'s owner; null for the global heap and for null |
| `arena_allocator` | `fn(arena: *Arena) -> Allocator` | Bump from `arena`; `free` gives nothing back until reset/destroy |
| `pages_allocator` | `fn(src: *PageSource) -> Allocator` | Each block its own whole-page mapping from `src`, unmapped there |
| `heap_init` | `fn(h: *Heap, src: PageSource)` | Fill `h` as a size-class heap whose slabs and large blocks map from `src` |
| `heap_allocator` | `fn(h: *Heap) -> Allocator` | Small blocks from `h`'s 64 KiB slabs, freed into its bins; over 2 KiB, its own mapping |
| `heap_destroy` | `fn(h: *Heap)` | Unmap every slab and live large block of `h` to its source; `h` is empty again |

A `Heap` (AGAST #4326) is the global heap's size classes over a source of its
own: `pages_allocator` costs a page per block, a `heap_allocator` packs small
blocks into slabs. The global heap is itself a `Heap` that follows the
installed source. The `Heap` must stay at its address while its allocator or
any block from it is live, and `heap_destroy` frees every block at once:

```ritz
import ritzlib.memory
import ritzlib.gvec

fn heap_vec() -> i64
    var h: Heap
    heap_init(@h, page_source_get())           # keeps this source
    var a: Allocator = heap_allocator(@h)
    var v: Vec<u8> = vec_new_in<u8>(@a)        # a slab block, not a page
    vec_push<u8>(@&v, 7)
    let x: i64 = vec_get<u8>(@v, 0) as i64
    vec_drop<u8>(@&v)                          # back to h's bins
    heap_destroy(@h)                           # every slab back to the source
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

**Functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `box_new` | `fn<T>(value: T) -> Box<T>` | Create box containing value |
| `box_new_in` | `fn<T>(a: *Allocator, value: T) -> Box<T>` | `box_new` with the value in memory from `a`; empty if `a` is out of memory |
| `box_get` | `fn<T>(b: @Box<T>) -> T` | Get value (returns copy) |
| `box_as_ptr` | `fn<T>(b: @Box<T>) -> *T` | Get pointer to value |
| `box_set` | `fn<T>(b: @&Box<T>, value: T)` | Set new value |
| `box_drop` | `fn<T>(b: @&Box<T>)` | Free the box |
| `box_valid` | `fn<T>(b: @Box<T>) -> i32` | Check if valid |

**Methods** (via impl):
- `get`, `as_ptr`, `set`, `valid`

**The `heap` keyword is not a `Box`.** `heap 42` is a raw allocation
expression of type `*i64`: dereference it with `*p` and free it with
`free(p as *u8)`. `box_new<i64>(42)` returns a `Box<i64>`, which is what
`box_get` / `box_set` / `box_drop` and the `Drop` impl operate on. Passing a
`heap`-keyword pointer to `box_get` is a type error.

```ritz
import ritzlib.box

fn heap_vs_box() -> i64
    var p = heap 42            # `heap` keyword: a bare *i64, deref with `*p`
    var q = box_new<i64>(42)   # constructor: a Box<i64> wrapper
    *p + box_get<i64>(@q)
```

ritzlib once also had `ritzlib.heap`, a `Heap<T>` identical to `Box<T>` with a
`heap_` prefix; it was folded into `box` (AGAST #3916).

---

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

**Core Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `vec_push` | `fn<T>(v: @&Vec<T>, item: T) -> i32` | Push element (0 on success) |
| `vec_pop` | `fn<T>(v: @&Vec<T>) -> T` | Pop last element |
| `vec_get` | `fn<T>(v: @Vec<T>, idx: i64) -> T` | Get element by index |
| `vec_get_ptr` | `fn<T>(v: @&Vec<T>, idx: i64) -> *T` | Get pointer to element |
| `vec_set` | `fn<T>(v: @&Vec<T>, idx: i64, item: T) -> i32` | Set element |
| `vec_len` | `fn<T>(v: @Vec<T>) -> i64` | Get length |
| `vec_cap` | `fn<T>(v: @Vec<T>) -> i64` | Get capacity |
| `vec_is_empty` | `fn<T>(v: @Vec<T>) -> i32` | Check if empty |
| `vec_clear` | `fn<T>(v: @&Vec<T>)` | Clear (keeps capacity) |
| `vec_drop` | `fn<T>(v: @&Vec<T>)` | Free the Vec |

A zero-size element (a field-less struct) allocates nothing: `len` and `cap`
count elements as usual, and `data` is a non-null dangling pointer that
`vec_drop` never frees.

**Utilities**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `vec_first` | `fn<T>(v: @Vec<T>) -> T` | Get first element |
| `vec_last` | `fn<T>(v: @Vec<T>) -> T` | Get last element |
| `vec_as_ptr` | `fn<T>(v: @Vec<T>) -> *T` | Get raw pointer |
| `vec_slice` | `fn<T>(v: @Vec<T>, start: i64, end: i64) -> Vec<T>` | Create slice copy |
| `vec_clone` | `fn<T>(v: @Vec<T>) -> Vec<T>` | Copy every element (`v.clone()`); shallow, so a heap-owning `T` ends up owned twice |
| `vec_swap` | `fn<T>(v: @&Vec<T>, i: i64, j: i64) -> i32` | Swap elements |
| `vec_push_bytes` | `fn<T>(v: @&Vec<T>, data: *T, len: i64) -> i32` | Push multiple |
| `vec_push_str` | `fn(v: @&Vec<u8>, s: *u8) -> i32` | Push C string |
| `vec_as_str` | `fn(v: @&Vec<u8>) -> *u8` | Get null-terminated string |

**Line Utilities** (to read a whole fd into a `Vec<u8>`, use `vec_read_all_fd` in [io](#io)):

```ritz
struct LineBounds
    start: i64      # Start offset in buffer
    length: i64     # Length in bytes
```

| Function | Signature | Description |
|----------|-----------|-------------|
| `vec_find_lines` | `fn(buf: @Vec<u8>, lines: @&Vec<LineBounds>) -> i32` | Find line boundaries |

---

### string

**Module**: `ritzlib.string`

Owned, growable UTF-8 string. Always null-terminated for C interop.

```ritz
import ritzlib.gvec

struct String
    data: Vec<u8>    # Underlying byte storage
```

**Constructors**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `string_new` | `fn() -> String` | Create empty string |
| `string_with_cap` | `fn(cap: i64) -> String` | Create with capacity |
| `string_from` | `fn(sv: StrView) -> String` | Create from a StrView (`"text"` literal) |
| `string_from_bytes` | `fn(bytes: *u8, len: i64) -> String` | Create from raw bytes |

**Accessors**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `string_len` | `fn(s: @String) -> i64` | Get length |
| `string_cap` | `fn(s: @String) -> i64` | Get capacity |
| `string_is_empty` | `fn(s: @String) -> bool` | Check if empty |
| `string_as_ptr` | `fn(s: @&String) -> *u8` | Get null-terminated C string |
| `string_as_view` | `fn(s: @String) -> StrView` | Borrow the bytes as a StrView (no copy), valid until `s` is modified or dropped; how a String prints in `print`/`eprint` interpolation or reaches a StrView API |
| `string_get` | `fn(s: @String, idx: i64) -> u8` | Get byte at index |
| `string_char_at` | `fn(s: @String, idx: i64) -> u8` | Get char at index |

**Modification**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `string_push` | `fn(s: @&String, b: u8) -> i32` | Push byte |
| `string_push_str` | `fn(s: @&String, sv: StrView) -> i32` | Push StrView (a `"..."` literal) |
| `string_push_cstr` | `fn(s: @&String, cstr: *u8) -> i32` | Push NUL-terminated C string |
| `string_push_string` | `fn(s: @&String, other: @String) -> i32` | Push String |
| `string_push_bytes` | `fn(s: @&String, bytes: *u8, len: i64) -> i32` | Push bytes; what `format_into(@&s, "...")` appends through (AGAST #1824) |
| `string_push_i64` | `fn(s: @&String, n: i64) -> i32` | Push an integer in decimal (all of i64); replaces `itoa` |
| `string_clear` | `fn(s: @&String)` | Clear string |
| `string_pop` | `fn(s: @&String) -> u8` | Pop last byte |
| `string_set_char` | `fn(s: @&String, idx: i64, c: u8) -> i32` | Set char at index |
| `string_drop` | `fn(s: @&String)` | Free string |

**Comparison**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `string_eq` | `fn(s: @String, other: StrView) -> bool` | Compare to a StrView (a `"..."` literal) |
| `string_eq_string` | `fn(a: @String, b: @String) -> bool` | Compare two Strings |
| `string_eq_strview` | `fn(s: @String, sv: StrView) -> bool` | Same as `string_eq` |
| `string_eq_cstr` | `fn(s: @String, cstr: *u8) -> bool` | Compare to C string |
| `string_hash` | `fn(s: @String) -> u64` | Hash the string |

**Search/Slice**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `string_starts_with` | `fn(s: @String, prefix: StrView) -> bool` | Check prefix |
| `string_ends_with` | `fn(s: @String, suffix: StrView) -> bool` | Check suffix |
| `string_contains` | `fn(s: @String, needle: StrView) -> bool` | Check contains |
| `string_find` | `fn(s: @String, needle: @String) -> i64` | Find substring (-1 if not found) |
| `string_slice` | `fn(s: @String, start: i64, end: i64) -> String` | Extract substring |
| `string_clone` | `fn(s: @String) -> String` | Deep copy |

**Conversion**:

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
| `hashmap_insert<K, V>` | `fn(m: @&HashMap<K, V>, key: K, value: V)` | Insert or overwrite |
| `hashmap_get<K, V>` | `fn(m: @HashMap<K, V>, key: K) -> Option<V>` | The value, or `None` |
| `hashmap_remove<K, V>` | `fn(m: @&HashMap<K, V>, key: K) -> bool` | Remove key (true if it was there) |
| `hashmap_len<K, V>` | `fn(m: @HashMap<K, V>) -> i64` | The number of keys |
| `hashmap_cap<K, V>` | `fn(m: @HashMap<K, V>) -> i64` | The number of slots (a power of 2) |
| `hashmap_slot_state<K, V>` | `fn(m: @HashMap<K, V>, i: i64) -> Slot` | Slot `i`'s state: `Empty`, `Full` or `Tomb` |
| `hashmap_slot_value<K, V>` | `fn(m: @HashMap<K, V>, i: i64) -> V` | Slot `i`'s value (read it when `Full`) |
| `hashmap_clear<K, V>` | `fn(m: @&HashMap<K, V>)` | Remove every key, keeping the table allocated |
| `hashmap_drop<K, V>` | `fn(m: @&HashMap<K, V>)` | Free the table |

**Iteration** walks the slots: `for i in 0..hashmap_cap(@m)` and
`hashmap_slot_state(@m, i) == Slot.Full`. `Tomb` is a removed key's slot; a
probe chain still steps over it. The map never frees a value, so drop what
the values own before `hashmap_clear` or `hashmap_drop`, and do not insert
or remove during a walk.

**Methods**: `len`, `insert`, `get`, `contains`, `remove`. The map has no
`Drop` impl yet (its `Vec` hasn't either, #3614): free it with `hashmap_drop`.

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
    hashmap_drop(@&m)
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

**Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `hashmap_i64_insert` | `fn(m: @&HashMapI64, key: i64, value: i64)` | Insert or update |
| `hashmap_i64_get` | `fn(m: @HashMapI64, key: i64) -> i64` | Get value (0 if not found) |
| `hashmap_i64_find` | `fn(m: @HashMapI64, key: i64) -> i64` | Index of key's slot (-1 if not found) |
| `hashmap_i64_contains` | `fn(m: @HashMapI64, key: i64) -> bool` | Check if key exists |
| `hashmap_i64_remove` | `fn(m: @&HashMapI64, key: i64) -> i32` | Remove key (1 if removed) |
| `hashmap_i64_len` | `fn(m: @HashMapI64) -> i64` | Get entry count |
| `hashmap_i64_cap` | `fn(m: @HashMapI64) -> i64` | Get capacity |
| `hashmap_i64_is_empty` | `fn(m: @HashMapI64) -> bool` | Check if empty |
| `hashmap_i64_drop` | `fn(m: @&HashMapI64)` | Free the map |
| `hashmap_i64_value_ptr` | `fn(m: @HashMapI64, key: i64) -> *i64` | The value's slot (null if not found) |
| `hashmap_i64_missing_key` | `fn(key: i64)` | Exit 101: `HashMapI64: key not found: <key>` |

**Methods** (via impl): `len`, `cap`, `is_empty`, `insert`, `get`, `contains`, `remove`

**Indexing** (LANGUAGE_SPEC §7.8): `HashMapI64` implements `Index`, `IndexMut` and
`IndexSet` at `K` = `V` = `i64`. `m[k] = v` inserts or replaces; `m[k]`, `@m[k]`,
`@&m[k]` and `m[k] += x` end the program through `hashmap_i64_missing_key` when `k`
is missing. Test for a key with `hashmap_i64_contains` or `hashmap_i64_get`.

```ritz
import ritzlib.hashmap

fn main() -> i32
    var m: HashMapI64 = hashmap_i64_new()
    m[7] = 1
    m[7] += 2
    if not hashmap_i64_contains(@m, 8)
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
| `span_from_vec` | `fn<T>(v: *Vec<T>) -> Span<T>` | From Vec |
| `span_from_cstr` | `fn(cstr: *u8) -> Span<u8>` | From C string |
| `span_literal` | `fn(ptr: *u8, len: i64) -> Span<u8>` | From literal with known length |

**Accessors**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `span_len` | `fn<T>(s: *Span<T>) -> i64` | Get length |
| `span_is_empty` | `fn<T>(s: *Span<T>) -> bool` | Check if empty |
| `span_get` | `fn<T>(s: *Span<T>, idx: i64) -> T` | Get element |
| `span_as_ptr` | `fn<T>(s: *Span<T>) -> *T` | Get raw pointer |

**Slicing**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `span_slice` | `fn<T>(s: *Span<T>, start: i64, end: i64) -> Span<T>` | Sub-span |
| `span_from` | `fn<T>(s: *Span<T>, start: i64) -> Span<T>` | From start to end |
| `span_to` | `fn<T>(s: *Span<T>, end: i64) -> Span<T>` | From beginning to end |
| `span_take` | `fn(s: *Span<u8>, n: i64) -> Span<u8>` | First n bytes |
| `span_skip` | `fn(s: *Span<u8>, n: i64) -> Span<u8>` | Skip first n bytes |

**String Operations** (for `Span<u8>`):

`Span<u8>` has StrView's layout; these delegate to the `strview_*` function of
the same name, and `span_as_strview` / `span_from_strview` convert between the two.

| Function | Signature | Description |
|----------|-----------|-------------|
| `span_as_strview` | `fn(s: *Span<u8>) -> StrView` | View the same bytes as a StrView |
| `span_eq` | `fn(a: *Span<u8>, b: *Span<u8>) -> bool` | Compare equality |
| `span_eq_cstr` | `fn(s: *Span<u8>, cstr: *u8) -> bool` | Compare to C string |
| `span_contains` | `fn(haystack: *Span<u8>, needle: *Span<u8>) -> bool` | Contains check |
| `span_starts_with` | `fn(s: *Span<u8>, prefix: *Span<u8>) -> bool` | Prefix check |
| `span_ends_with` | `fn(s: *Span<u8>, suffix: *Span<u8>) -> bool` | Suffix check |
| `span_find` | `fn(haystack: *Span<u8>, needle: *Span<u8>) -> i64` | Find substring |
| `span_find_byte` | `fn(s: *Span<u8>, c: u8) -> i64` | Find byte |

---

## String Utilities

### strview

**Module**: `ritzlib.strview`

`StrView` is a borrowed `{ ptr: *u8, len: i64 }` view of UTF-8 bytes, and the
type of a bare `"..."` literal. It never allocates or frees, is not
NUL-terminated, and must not outlive the bytes it points at. Use `String`
(`ritzlib.string`) when you need to own or grow the text. Every function takes
the view by value; slicing returns a new view of the same bytes.

**Construction / Access**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `strview_empty` | `fn() -> StrView` | Empty view (`ptr` null, `len` 0) |
| `strview_from_ptr` | `fn(ptr: *u8, len: i64) -> StrView` | View `len` bytes at `ptr` |
| `strview_from_cstr` | `fn(cstr: *u8) -> StrView` | View a NUL-terminated string, without the NUL |
| `strview_len` | `fn(s: StrView) -> i64` | Length in bytes |
| `strview_is_empty` | `fn(s: StrView) -> bool` | `len == 0` |
| `strview_get` | `fn(s: StrView, idx: i64) -> u8` | Byte at `idx` (unchecked) |
| `strview_as_ptr` | `fn(s: StrView) -> *u8` | Pointer to the first byte |

**Comparison**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `strview_eq` | `fn(a: StrView, b: StrView) -> bool` | Same length and bytes |
| `strview_eq_cstr` | `fn(s: StrView, cstr: *u8) -> bool` | Equal to a C string |
| `strview_cmp` | `fn(a: StrView, b: StrView) -> i32` | Bytewise order: -1, 0 or 1; a prefix sorts first |
| `strview_cmp_cstr` | `fn(s: StrView, cstr: *u8) -> i32` | `strview_cmp` against a C string |

**Slicing** (no allocation):

| Function | Signature | Description |
|----------|-----------|-------------|
| `strview_slice` | `fn(s: StrView, start: i64, end: i64) -> StrView` | Bytes `[start, end)`, bounds clamped to `[0, len]`; empty if `start >= end` |
| `strview_take` | `fn(s: StrView, n: i64) -> StrView` | First `n` bytes (all if `n >= len`) |
| `strview_skip` | `fn(s: StrView, n: i64) -> StrView` | Everything after the first `n` bytes |
| `strview_trim_start` | `fn(s: StrView) -> StrView` | Drop leading space, `\t`, `\n`, `\r` |
| `strview_trim_end` | `fn(s: StrView) -> StrView` | Drop trailing whitespace |
| `strview_trim` | `fn(s: StrView) -> StrView` | Both ends |
| `strview_split_once` | `fn(s: StrView, delim: u8, before:& StrView, after:& StrView) -> i32` | Split at the first `delim` (excluded): 1 if found; 0 and `before = s`, `after` empty if not. Call as `strview_split_once(s, '=', @&k, @&v)` |

**Search**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `strview_starts_with` | `fn(s: StrView, prefix: StrView) -> bool` | Prefix test |
| `strview_starts_with_cstr` | `fn(s: StrView, prefix: *u8) -> bool` | Prefix test against a C string |
| `strview_ends_with` | `fn(s: StrView, suffix: StrView) -> bool` | Suffix test |
| `strview_contains` | `fn(haystack: StrView, needle: StrView) -> bool` | Substring test; an empty needle is always found |
| `strview_find` | `fn(haystack: StrView, needle: StrView) -> i64` | First index of `needle`, or -1 (0 for an empty needle) |
| `strview_rfind` | `fn(haystack: StrView, needle: StrView) -> i64` | Last index of `needle`, or -1 (`len` for an empty needle) |
| `strview_find_byte` | `fn(s: StrView, c: u8) -> i64` | First index of byte `c`, or -1 |

**Conversion**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `strview_parse_i64` | `fn(s: StrView) -> Option<i64>` | The whole view as decimal, optional `+`/`-`: `None` for empty, a bare sign, whitespace, junk or overflow. Trim first if needed |
| `strview_to_cstr` | `fn(s: StrView) -> *u8` | `malloc`ed NUL-terminated copy; caller `free`s it |
| `strview_as_cstr_unchecked` | `fn(s: StrView) -> *u8` | The pointer as a C string. Only sound if the bytes after the view hold a NUL, as they do for a whole literal; a slice usually doesn't |

**Methods** (`impl StrView`; each calls the `strview_*` function of the same name):

| Method | Function |
|--------|----------|
| `s.len()`, `s.is_empty()`, `s.get(i)`, `s.as_ptr()` | `strview_len`, `strview_is_empty`, `strview_get`, `strview_as_ptr` |
| `s.eq(t)`, `s.eq_cstr(c)`, `s.cmp(t)`, `s.cmp_cstr(c)` | `strview_eq`, `strview_eq_cstr`, `strview_cmp`, `strview_cmp_cstr` |
| `s.slice(start, end)`, `s.take(n)`, `s.skip(n)` | `strview_slice`, `strview_take`, `strview_skip` |
| `s.trim()`, `s.trim_start()`, `s.trim_end()` | `strview_trim`, `strview_trim_start`, `strview_trim_end` |
| `s.starts_with(p)`, `s.ends_with(p)`, `s.contains(t)` | `strview_starts_with`, `strview_ends_with`, `strview_contains` |
| `s.find(t)`, `s.rfind(t)`, `s.find_byte(c)` | `strview_find`, `strview_rfind`, `strview_find_byte` |
| `s.to_cstr()`, `s.as_cstr_unchecked()` | `strview_to_cstr`, `strview_as_cstr_unchecked` |
| `s.parse_i64()` | `strview_parse_i64` |

Method syntax reaches only these: a `strview_*` function with no method here
(`strview_from_cstr`, `strview_empty`) is called as a function (LARB R66).

`s.as_bytes()` is not in this table: it is a compiler built-in, with no
`strview_*` function behind it, and works without importing this module. It is
a `Span<u8>` of the view's bytes, with no copy (LANGUAGE_SPEC §3.5).

**Example**:
```ritz
import ritzlib.option
import ritzlib.strview

# "key = value" -> the value as an i64, or None
fn config_int(line: StrView, key: StrView) -> Option<i64>
    var k: StrView = strview_empty()
    var v: StrView = strview_empty()
    if strview_split_once(line, '=', @&k, @&v) == 0
        return None
    if not k.trim().eq(key)
        return None
    strview_parse_i64(v.trim())

[[test]]
fn test_strview_example() -> i32
    let port = match config_int("  port = 8080 ", "port")
        Some(n) => n
        None => -1
    assert port == 8080
    assert config_int("port = 80x", "port").is_none()
    let path = strview_from_cstr(c"/usr/lib/libc.so")
    let base = strview_skip(path, path.rfind("/") + 1)
    assert base.eq("libc.so")
    assert path.starts_with("/usr") and path.ends_with(".so")
    assert strview_cmp("abc", "abd") < 0
    assert strview_find_byte(path, 'l') == 5
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
| `strlen` | `strview_len` / `string_len` |
| `streq`, `strneq` | `strview_eq`, `strview_eq_cstr`; `strview_take` then `strview_eq` |
| `strcmp` | `strview_cmp` |
| `strchr` | `strview_find_byte` |
| `strrchr` | `strview_rfind` |
| `strstr` | `strview_find`, `strview_contains` |
| `strcpy`, `strncpy` | `string_from` (a `String` owns its copy); `strview_take` to bound it |
| `strcat` | `string_push_str`, `string_push_string` |
| `atoi` | `strview_parse_i64(s: StrView) -> Option<i64>`: `None` for empty, junk or overflow, where `atoi` returns 0 or a prefix |
| `itoa` | `string_push_i64(s: @&String, n: i64) -> i32` / `string_from_i64`: no caller-sized buffer |

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
| `strrchr` | `fn(s: *u8, c: u8) -> *u8` | Find last char |
| `strstr` | `fn(haystack: *u8, needle: *u8) -> *u8` | Find substring |

**Copy/Concatenate**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `strcpy` | `fn(dest: *u8, src: *u8) -> *u8` | Copy string |
| `strncpy` | `fn(dest: *u8, src: *u8, n: i64) -> *u8` | Copy up to n chars |
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
`eprint_int`, `print_hex`, `itoa`, `string_push_i64`, `string_from_hex`,
`iovec_append_int`/`_uint`, `ritzlib.fmt`'s Display) calls it, so all of them
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
| `writer_write` | `fn(w: @&Writer, data: *u8, len: i64) -> i64` | `len` bytes |
| `writer_write_str` | `fn(w: @&Writer, s: StrView) -> i64` | A view's bytes |
| `writer_write_byte` | `fn(w: @&Writer, b: u8) -> i64` | One byte |
| `writer_write_fill` | `fn(w: @&Writer, b: u8, n: i64) -> i64` | `b`, `n` times |
| `writer_len` | `fn(w: @Writer) -> i64` | Bytes accepted so far |
| `writer_view` | `fn(w: @Writer) -> StrView` | What a `span_writer` holds |
| `write` / `writeln` | `fn(w: @&Writer, s: StrView) -> i64` | `s` (and a newline) to `w` |
| `format` | `fn(s: StrView) -> String` | `s` copied into a new String |

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
    (writer_len(@w) - 16) as i32
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
`bool`. Receivers are `@Buffer` (read-only) or `@&Buffer` (moves the cursor);
a local passes as `@b` either way.

```ritz
import ritzlib.buf
import ritzlib.strview

fn key_of(line: StrView) -> StrView
    var b: Buffer = buf_new(line)
    buf_skip_whitespace(@&b)
    let key: StrView = buf_take_ident(@&b)
    buf_skip_whitespace(@&b)
    if not buf_match_char(@&b, '=')
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
| `buf_from_str` | `fn(buf: @&Buffer, s: StrView) -> i32` | Re-point an existing cursor at `s` |
| `buf_init` | `fn(buf: @&Buffer, data: *u8, len: i64) -> i32` | From pointer + length (C interop) |

**Position**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_pos` | `fn(buf: @Buffer) -> i64` | Current position |
| `buf_len` | `fn(buf: @Buffer) -> i64` | Total length |
| `buf_remaining` | `fn(buf: @Buffer) -> i64` | Remaining bytes |
| `buf_eof` | `fn(buf: @Buffer) -> bool` | At end? |
| `buf_rest` | `fn(buf: @Buffer) -> StrView` | Unread bytes, as a slice |
| `buf_save` | `fn(buf: @Buffer) -> i64` | Save position |
| `buf_restore` | `fn(buf: @&Buffer, pos: i64) -> i32` | Restore position |

**Peek (Don't Advance)**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_peek` | `fn(buf: @Buffer) -> u8` | Peek current byte (0 at end) |
| `buf_peek_at` | `fn(buf: @Buffer, offset: i64) -> u8` | Peek at offset (0 out of range) |
| `buf_peek_view` | `fn(buf: @Buffer, n: i64) -> StrView` | Up to `n` bytes, as a slice |

**Consume (Advance)**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_advance` | `fn(buf: @&Buffer) -> u8` | Read and advance |
| `buf_advance_n` | `fn(buf: @&Buffer, n: i64) -> i64` | Advance n bytes (clamped) |
| `buf_skip` | `fn(buf: @&Buffer, n: i64) -> i32` | Skip n bytes (clamped) |

**Pattern Matching**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_match_char` | `fn(buf: @&Buffer, c: u8) -> bool` | Consume `c` if next |
| `buf_match_str` | `fn(buf: @&Buffer, s: StrView) -> bool` | Consume `s` if next |
| `buf_starts_with` | `fn(buf: @Buffer, s: StrView) -> bool` | Check prefix (no advance) |

**Skip Utilities**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_skip_whitespace` | `fn(buf: @&Buffer) -> i64` | Skip space/tab/CR/LF |
| `buf_skip_until` | `fn(buf: @&Buffer, c: u8) -> i64` | Skip until char |
| `buf_skip_while` | `fn(buf: @&Buffer, pred: fn(u8) -> bool) -> i64` | Skip a run matching `pred`; returns the count |

**Zero-Copy Reads** (each returns a slice of the buffer's bytes):

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_take_until` | `fn(buf: @&Buffer, c: u8) -> StrView` | Up to (not including) `c`, or to the end |
| `buf_take_digits` | `fn(buf: @&Buffer) -> StrView` | Run of `[0-9]` |
| `buf_take_ident` | `fn(buf: @&Buffer) -> StrView` | Run of `[A-Za-z0-9_]` |
| `buf_take_while` | `fn(buf: @&Buffer, pred: fn(u8) -> bool) -> StrView` | Run matching `pred` |
| `buf_take_quoted` | `fn(buf: @&Buffer, quote: u8, out: @&String) -> bool` | Decode a quoted string, appending to `out`; false if not at `quote` or unterminated |

**Byte Predicates** (for `buf_take_while` / `buf_skip_while`):

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_is_digit` | `fn(c: u8) -> bool` | `[0-9]` |
| `buf_is_ident` | `fn(c: u8) -> bool` | `[A-Za-z0-9_]` |
| `buf_is_space` | `fn(c: u8) -> bool` | space, tab, CR, LF |

**Deprecated** (kept for one release after AGAST #1478). The out-buffer forms
copy into a caller-sized `out`, NUL-terminate within `max_len` (so `max_len`
4 yields at most 3 bytes) and silently truncate:

| Function | Signature | Use instead |
|----------|-----------|-------------|
| `buf_peek_n` | `fn(buf: @Buffer, out: *u8, n: i64) -> i64` | `buf_peek_view` |
| `buf_read_until` | `fn(buf: @&Buffer, c: u8, out: *u8, max_len: i64) -> i64` | `buf_take_until` |
| `buf_read_while_digit` | `fn(buf: @&Buffer, out: *u8, max_len: i64) -> i64` | `buf_take_digits` |
| `buf_read_while_alnum` | `fn(buf: @&Buffer, out: *u8, max_len: i64) -> i64` | `buf_take_ident` |
| `buf_read_quoted` | `fn(buf: @&Buffer, quote: u8, out: *u8, max_len: i64) -> i64` | `buf_take_quoted` |

**Location Tracking**:

```ritz
struct BufLoc
    line: i32
    col: i32
    offset: i64
```

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_get_loc` | `fn(buf: @Buffer, loc: @&BufLoc) -> i32` | Get line/column |

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
automatically depends on the compiler (#1854), so `growbuf_free` remains for
explicit release. To read a whole file descriptor, use `vec_read_all_fd`
(io) and point a `Buffer` at the bytes.

| Function | Signature | Description |
|----------|-----------|-------------|
| `growbuf_new` | `fn() -> GrowBuf` | Create empty |
| `growbuf_with_cap` | `fn(cap: i64) -> GrowBuf` | Create with capacity |
| `growbuf_free` | `fn(b: @&GrowBuf) -> i32` | Free (deprecated, use Drop) |
| `growbuf_grow` | `fn(b: @&GrowBuf, new_cap: i64) -> i32` | Grow capacity |
| `growbuf_ensure_cap` | `fn(b: @&GrowBuf, needed: i64) -> i32` | Ensure capacity |
| `growbuf_append` | `fn(b: @&GrowBuf, data: *u8, len: i64) -> i32` | Append bytes |
| `growbuf_append_view` | `fn(b: @&GrowBuf, s: StrView) -> i32` | Append a StrView |
| `growbuf_append_byte` | `fn(b: @&GrowBuf, byte: u8) -> i32` | Append single byte |
| `growbuf_push_bytes` | `fn(b: @&GrowBuf, data: *u8, len: i64) -> i32` | `growbuf_append` under the `push_bytes` name `format_into(@&b, "...")` appends through (AGAST #1824) |
| `growbuf_clear` | `fn(b: @&GrowBuf) -> i32` | Clear (keep capacity) |
| `growbuf_len` | `fn(b: @GrowBuf) -> i64` | Get length |
| `growbuf_cap` | `fn(b: @GrowBuf) -> i64` | Get capacity |
| `growbuf_get` | `fn(b: @GrowBuf, idx: i64) -> u8` | Byte at index (0 out of range) |
| `growbuf_is_empty` | `fn(b: @GrowBuf) -> bool` | Empty? |
| `growbuf_view` | `fn(b: @GrowBuf) -> StrView` | Contents as a slice (invalidated by the next append) |
| `growbuf_data` | `fn(b: @GrowBuf) -> *u8` | Data pointer (C interop) |

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
| `sys_stat2` | `fn(path: *u8, statbuf: *Stat) -> i32` | Typed stat |
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
| `vec_read_all_fd` | `fn(fd: i32, v: @&Vec<u8>) -> i64` | Append everything `fd` yields to `v`; bytes read, or -1. Here rather than in gvec, which is core |

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
| `errno_code` | `fn(e: Errno) -> i32` | The positive number (`NoEnt` -> 2, `Other(n)` -> n) |
| `errno_name` | `fn(e: Errno) -> StrView` | `"ENOENT"`, ...; `"EUNKNOWN"` for `Other` |
| `errno_message` | `fn(e: Errno) -> StrView` | strerror(3)'s text (`"No such file or directory"`); `"Unknown error"` for `Other` |
| `errno_write` | `fn(fd: i32, e: Errno) -> i64` | Write the message to `fd`, no newline; `Other(n)` gives `"Unknown error <n>"` |

`Errno` carries data, so `e as i32` is an error: use `errno_code`.

```ritz
import ritzlib.fs
import ritzlib.io
import ritzlib.string

# 0 if `path` was read or is simply missing; otherwise report why and return 1.
fn read_if_present(path: StrView) -> i32
    match read_file(path)
        Ok(s) =>
            var text: String = s
            string_drop(@&text)
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
already a StrView; a `String` passes `string_as_view(@s)`; a C string passes
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
| `dir_next` | `fn(dir: *DirIter) -> bool` | Advance; true if an entry is available, false at the end |
| `dir_close` | `fn(dir: *DirIter)` | Close the iterator |
| `dir_entry` | `fn(dir: @DirIter) -> DirEntry` | Current entry after `dir_next` returns true |
| `dir_next_entry` | `fn(dir: @&DirIter) -> Option<DirEntry>` | Advance and return the next entry, `None` at the end |
| `dir_entry_type` | `fn(dir: *DirIter) -> Option<u8>` | Type of the current entry (`DT_REG`, `DT_DIR`, ...), `None` if there is none |
| `dir_entry_is_dir` | `fn(dir: *DirIter) -> bool` | Is the current entry a directory? |
| `dir_entry_is_file` | `fn(dir: *DirIter) -> bool` | Is the current entry a regular file? |
| `dir_entry_is_link` | `fn(dir: *DirIter) -> bool` | Is the current entry a symlink? |
| `dirent_entry` | `fn(entry: *u8) -> DirEntry` | Decode one raw `linux_dirent64` record |

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
    while dir_next(@dir)
        let e: DirEntry = dir_entry(@dir)    # e.ino, e.kind, e.name: StrView
        if e.kind == DT_REG
            n += 1
    dir_close(@dir)
    n
```

`DirEntry.name` points into the iterator's buffer and doesn't include the NUL.
It is valid until the next `dir_next`/`dir_next_entry` or `dir_close` call.

**Stat Buffer Accessors** (legacy; use `stat`/`lstat` and the `Stat` fields):

| Function | Signature | Description |
|----------|-----------|-------------|
| `stat_get_mode` | `fn(statbuf: *u8) -> i32` | Get mode from stat |
| `stat_get_size` | `fn(statbuf: *u8) -> i64` | Get size from stat |
| `stat_get_uid` | `fn(statbuf: *u8) -> i32` | Get UID |
| `stat_get_gid` | `fn(statbuf: *u8) -> i32` | Get GID |

These and `stat_get_dev/ino/nlink/blksize/blocks` read through `*Stat`, so
the field offsets are defined only in `ritzlib.sys`.

**Dirent Helpers** (legacy; use `DirEntry`):

```ritz
struct Dirent64
    d_ino: i64
    d_off: i64
    d_reclen: u16
    d_type: u8
```

**Dirent Types**: `DT_UNKNOWN`, `DT_FIFO`, `DT_CHR`, `DT_DIR`, `DT_BLK`, `DT_REG`, `DT_LNK`, `DT_SOCK`

| Function | Signature | Description |
|----------|-----------|-------------|
| `dirent_get_ino` | `fn(entry: *u8) -> i64` | Get inode |
| `dirent_get_reclen` | `fn(entry: *u8) -> i32` | Get record length |
| `dirent_get_type` | `fn(entry: *u8) -> u8` | Get type |
| `dirent_get_name` | `fn(entry: *u8) -> *u8` | Get name pointer |

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
            Err(e) => return errno_code(e)
    var path: String = path_join(dir, name)
    var r: Result<i64, Errno> = write_file(string_as_view(@path), text)
    string_drop(@&path)
    match r
        Ok(_) => 0
        Err(e) => errno_code(e)
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

**Builder Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `iovec_builder_init` | `fn(b: *IoVecBuilder)` | Initialize builder |
| `iovec_builder_reset` | `fn(b: *IoVecBuilder)` | Reset for reuse |
| `iovec_ptr` | `fn(b: *IoVecBuilder) -> *Iovec` | Get iovec array |
| `iovec_count` | `fn(b: *IoVecBuilder) -> i32` | Get count |

**Append Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `iovec_append_span` | `fn(b: *IoVecBuilder, s: Span<u8>) -> i32` | Append span (zero-copy) |
| `iovec_append_static` | `fn(b: *IoVecBuilder, s: *u8) -> i32` | Append C string |
| `iovec_append_bytes` | `fn(b: *IoVecBuilder, data: *u8, len: i32) -> i32` | Append bytes |
| `iovec_append_copy` | `fn(b: *IoVecBuilder, s: *u8) -> i32` | Append (copy to pool) |
| `iovec_append_int` | `fn(b: *IoVecBuilder, n: i64) -> i32` | Append integer |
| `iovec_append_uint` | `fn(b: *IoVecBuilder, n: u64) -> i32` | Append unsigned int |
| `iovec_append_crlf` | `fn(b: *IoVecBuilder) -> i32` | Append CRLF |

**Utilities**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `iovec_total_len` | `fn(b: *IoVecBuilder) -> i64` | Total bytes |
| `iovec_debug_print` | `fn(b: *IoVecBuilder)` | Debug output |

---

## Networking

### net

**Module**: `ritzlib.net`

TCP/IP socket operations. Every fallible function returns a `Result` whose
`Err` is a `ritzlib.errno` `Errno` (AGAST #4298; it was a positive `i32`
errno), and `net` re-exports `ritzlib.errno`. Compare with the raw numbers
via `errno_code(e) == EINVAL`, or match the variant:

```ritz
import ritzlib.net

# A listener on 127.0.0.1:`port`, or the errno that stopped it.
fn open_listener(port: i32) -> Result<Socket, Errno>
    var sock: Socket = socket_tcp()?
    match socket_bind(@&sock, "127.0.0.1", port)
        Ok(_) => pass
        Err(e) =>
            socket_close(@&sock)
            return Err(e)
    socket_listen(@&sock, 128)?
    Ok(sock)

# Whether something else already holds `port`.
fn port_taken(port: i32) -> bool
    match open_listener(port)
        Ok(s) =>
            var t: Socket = s
            socket_close(@&t)
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
| `socket_valid` | `fn(sock: @Socket) -> bool` | Holds an open fd (false once closed) |
| `socket_close` | `fn(sock: @&Socket) -> Result<(), Errno>` | Close and set `fd = -1`; `Ok(())` if already closed, else `Err(errno)` from close(2) |

**Socket Options**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `socket_set_opt_int` | `fn(sock: @&Socket, level: i32, optname: i32, value: i32) -> Result<(), Errno>` | setsockopt with an int; `Err(errno)` |
| `socket_set_reuseaddr` | `fn(sock: @&Socket) -> Result<(), Errno>` | Enable SO_REUSEADDR |
| `socket_set_reuseport` | `fn(sock: @&Socket) -> Result<(), Errno>` | Enable SO_REUSEPORT |
| `socket_set_nodelay` | `fn(sock: @&Socket) -> Result<(), Errno>` | Disable Nagle |
| `socket_set_io_timeout` | `fn(sock: @&Socket, timeout_ms: i32) -> Result<(), Errno>` | SO_RCVTIMEO + SO_SNDTIMEO; 0 clears |

**Server Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `socket_bind` | `fn(sock: @&Socket, addr: StrView, port: i32) -> Result<(), Errno>` | Bind; `Err(Inval)` for a bad address, else `Err(errno)` |
| `socket_listen` | `fn(sock: @&Socket, backlog: i32) -> Result<(), Errno>` | Start listening; `Err(errno)` |
| `socket_accept` | `fn(sock: @&Socket) -> Result<Socket, Errno>` | Accept (blocking); `Err(errno)`, e.g. `Inval` if not listening |
| `socket_accept_nonblock` | `fn(sock: @&Socket) -> Result<Socket, Errno>` | Accept without blocking (peer is non-blocking too); `Err(Again)` if none pending |

**Client Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `socket_connect` | `fn(sock: @&Socket, addr: StrView, port: i32) -> Result<(), Errno>` | Connect; `Err(Inval)` for a bad address, else `Err(errno)` |
| `socket_connect_timeout` | `fn(sock: @&Socket, addr: StrView, port: i32, timeout_ms: i32) -> Result<(), Errno>` | Connect within `timeout_ms`; `Err(Inval)` bad address, `Err(TimedOut)`, else `Err(errno)` |
| `socket_send_all` | `fn(sock: @&Socket, data: Span<u8>) -> Result<i64, Errno>` | Send every byte (retries short writes and EINTR) |
| `socket_send_str` | `fn(sock: @&Socket, s: StrView) -> Result<i64, Errno>` | `socket_send_all` for text |
| `socket_recv_into` | `fn(sock: @&Socket, buf: @&Vec<u8>, max: i64) -> Result<i64, Errno>` | Append up to `max` bytes; `Ok(0)` at EOF |

**Epoll Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `epoll_create` | `fn() -> Result<i32, Errno>` | A new epoll instance's fd |
| `epoll_add` | `fn(epfd: i32, fd: i32, events: u32) -> Result<(), Errno>` | Watch fd; `Err(Exist)` if already watched |
| `epoll_del` | `fn(epfd: i32, fd: i32) -> Result<(), Errno>` | Stop watching fd; `Err(NoEnt)` if not watched |
| `epoll_mod` | `fn(epfd: i32, fd: i32, events: u32) -> Result<(), Errno>` | Change events; `Err(NoEnt)` if not watched |
| `epoll_wait_events` | `fn(epfd: i32, events: *EpollEvent, maxevents: i32, timeout_ms: i32) -> Result<i32, Errno>` | Wait: `Ok(ready fds)`, `Ok(0)` on timeout, `Err(errno)` e.g. `Intr` |

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
| `runtime_accept` | `fn(rt: *Runtime, server_fd: i32) -> i32` | Async accept |
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

**Constants**:
- `POLL_PENDING`: -1. A poll function returns this while it is suspended; any other value is Ready.

```ritz
import ritzlib.uring

struct Runtime
    ring: IoUring
    initialized: i32
    next_user_data: i64
    waker_user_data: i64
    waker_io_result: i32
    waker_io_ready: i32
    waker_active: i32
    took_pending_code: i32
```

`waker_io_ready`, not the value of `waker_io_result`, says whether a completion
is waiting, so a read at EOF returns 0 rather than being resubmitted. A poll
function that returns an -EPERM result it was handed is Ready(-1): `block_on`
returns -1 instead of reading it as Pending (AGAST #2328).

| Function | Signature | Description |
|----------|-----------|-------------|
| `runtime_init` | `fn(rt: *Runtime) -> i32` | Initialize runtime |
| `runtime_destroy` | `fn(rt: *Runtime)` | Destroy runtime |
| `runtime_read` | `fn(rt: *Runtime, fd: i32, buf: *u8, count: i32, offset: i64) -> i64` | Read, waiting for the result |
| `runtime_write` | `fn(rt: *Runtime, fd: i32, buf: *u8, count: i32, offset: i64) -> i64` | Write, waiting for the result |
| `runtime_close` | `fn(rt: *Runtime, fd: i32) -> i32` | Close, waiting for the result |
| `block_on` | `fn(rt: *Runtime, future_ptr: *u8, poll_fn: fn(*u8) -> i32) -> i32` | Poll a future to completion; -EINVAL if it is Pending with nothing to wake it |
| `runtime_poll_read` | `fn(rt: *Runtime, fd: i32, buf: *u8, len: i32, offset: i64) -> i32` | Inside a poll function: submit a read and return Pending, then return its result |
| `runtime_poll_write` | `fn(rt: *Runtime, fd: i32, buf: *u8, len: i32, offset: i64) -> i32` | Inside a poll function: submit a write and return Pending, then return its result |
| `runtime_wait_for_io` | `fn(rt: *Runtime) -> i32` | Wait for a completion and record it for the waker |
| `runtime_waker_register` | `fn(rt: *Runtime, user_data: i64)` | Suspend on an operation submitted by hand |
| `runtime_waker_clear` | `fn(rt: *Runtime)` | Stop waiting for that operation |
| `get_runtime` | `fn() -> *Runtime` | Get global runtime |
| `cleanup_runtime` | `fn()` | Cleanup global runtime |

A `runtime_poll_*` result of 0 cannot be told from "no result yet", so a read at
EOF is submitted again (AGAST #2328).

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

| Function | Signature | Description |
|----------|-----------|-------------|
| `task_pool_init` | `fn(pool: *TaskPool, ring: *IoUring)` | Initialize pool |
| `spawn_task` | `fn(pool: *TaskPool, fd: i32, handler: fn(*Task) -> i32) -> i32` | Spawn task |
| `task_complete` | `fn(pool: *TaskPool, task: *Task)` | Complete task |
| `run_tasks` | `fn(pool: *TaskPool) -> i32` | Run all tasks |

**Task I/O Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `task_recv` | `fn(task: *Task) -> i32` | Submit recv |
| `task_send` | `fn(task: *Task, len: i32) -> i32` | Submit send |
| `task_sendv` | `fn(task: *Task, iov: *u8, iovcnt: i32) -> i32` | Submit writev |
| `task_sendv_builder` | `fn(task: *Task) -> i32` | Send from IoVecBuilder |
| `task_send_zc` | `fn(task: *Task, len: i32) -> i32` | Zero-copy send |
| `task_splice` | `fn(task: *Task, fd_in: i32, off_in: i64, len: u32, splice_flags: i32) -> i32` | Splice |
| `task_reset_for_recv` | `fn(task: *Task) -> i32` | Reset for keep-alive |

**Server Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `task_server_init` | `fn(srv: *TaskServer, listen_fd: i32) -> i32` | Initialize server |
| `task_server_destroy` | `fn(srv: *TaskServer)` | Destroy server |
| `task_server_run` | `fn(srv: *TaskServer, handler: fn(*Task) -> i32) -> i32` | Run server |
| `task_server_run_multishot` | `fn(srv: *TaskServer, handler: fn(*Task) -> i32) -> i32` | Run with multishot accept |
| `task_server_stop` | `fn(srv: *TaskServer)` | Stop server |
| `task_server_set_shutdown_hook` | `fn(srv: *TaskServer, hook: fn() -> i32)` | Set shutdown hook |
| `task_server_set_idle_timeout` | `fn(srv: *TaskServer, timeout_secs: i32)` | Set idle timeout |
| `task_server_set_max_connections` | `fn(srv: *TaskServer, max_conns: i32)` | Set max connections |

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

| Function | Signature | Description |
|----------|-----------|-------------|
| `uring_init` | `fn(ring: *IoUring, entries: i32) -> i32` | Initialize ring |
| `uring_destroy` | `fn(ring: *IoUring)` | Destroy ring |
| `uring_get_sqe` | `fn(ring: *IoUring) -> *IoUringSqe` | Get SQE |
| `uring_sqe_submit` | `fn(ring: *IoUring)` | Advance SQ tail |
| `uring_submit` | `fn(ring: *IoUring) -> i32` | Submit pending SQEs |
| `uring_submit_and_wait` | `fn(ring: *IoUring, min_complete: i32) -> i32` | Submit and wait |
| `uring_peek_cqe` | `fn(ring: *IoUring) -> *IoUringCqe` | Peek CQE |
| `uring_wait_cqe` | `fn(ring: *IoUring) -> *IoUringCqe` | Wait for CQE |
| `uring_cqe_seen` | `fn(ring: *IoUring, cqe: *IoUringCqe)` | Mark CQE consumed |

**SQE Preparation**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `uring_prep_read` | `fn(sqe: *IoUringSqe, fd: i32, buf: *u8, len: i32, offset: i64, user_data: i64)` | Prepare read |
| `uring_prep_write` | `fn(sqe: *IoUringSqe, fd: i32, buf: *u8, len: i32, offset: i64, user_data: i64)` | Prepare write |
| `uring_prep_accept` | `fn(sqe: *IoUringSqe, fd: i32, addr: *u8, addrlen: *i32, flags: i32, user_data: i64)` | Prepare accept |
| `uring_prep_accept_multishot` | `fn(sqe: *IoUringSqe, fd: i32, addr: *u8, addrlen: *i32, flags: i32, user_data: i64)` | Multishot accept (5.19+) |
| `uring_prep_close` | `fn(sqe: *IoUringSqe, fd: i32, user_data: i64)` | Prepare close |
| `uring_prep_recv` | `fn(sqe: *IoUringSqe, fd: i32, buf: *u8, len: u64, flags: i32, user_data: i64)` | Prepare recv |
| `uring_prep_send` | `fn(sqe: *IoUringSqe, fd: i32, buf: *u8, len: u64, flags: i32, user_data: i64)` | Prepare send |
| `uring_prep_send_zc` | `fn(sqe: *IoUringSqe, fd: i32, buf: *u8, len: u64, flags: i32, user_data: i64)` | Zero-copy send (6.0+) |
| `uring_prep_readv` | `fn(sqe: *IoUringSqe, fd: i32, iov: *u8, nr_vecs: i32, offset: i64, user_data: i64)` | Vectored read |
| `uring_prep_writev` | `fn(sqe: *IoUringSqe, fd: i32, iov: *u8, nr_vecs: i32, offset: i64, user_data: i64)` | Vectored write |
| `uring_prep_splice` | `fn(sqe: *IoUringSqe, fd_out: i32, off_out: i64, fd_in: i32, off_in: i64, len: u32, splice_flags: i32, user_data: i64)` | Splice |
| `uring_prep_timeout` | `fn(sqe: *IoUringSqe, ts: *KernelTimespec, count: u32, flags: u32, user_data: i64)` | Timeout |

**Safety Note**: Zero-copy operations (`IORING_OP_SEND_ZC`) require the buffer to remain valid until the CQE is received.

---

## Process Management

### process

**Module**: `ritzlib.process`

Subprocess spawning with connected pipes. Every fn on a live `Process` takes
`@&Process` (they close fds and record the wait); `process_valid` only reads
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
| `process_valid` | `fn(p: @Process) -> i32` | 1 if the spawn gave a live pid |

**I/O Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `process_write_all` | `fn(p: @&Process, data: StrView) -> Result<i64, Errno>` | Write all of `data` to stdin (retries short writes and EINTR); `Ok(data.len)`, `Err(BadF)` once stdin is closed, `Err(Pipe)` once the child closed it |
| `process_close_stdin` | `fn(p: @&Process)` | Close stdin (EOF) |
| `process_read_stdout` | `fn(p: @&Process, buf: *u8, max: i64) -> Result<i64, Errno>` | Read up to `max` bytes of stdout: `Ok(n)`, `Ok(0)` at EOF, `Err(BadF)` once the pipe is closed |
| `process_read_stdout_all` | `fn(p: @&Process) -> Vec<u8>` | Read all stdout |
| `process_read_line` | `fn(p: @&Process) -> Vec<u8>` | Read line |
| `process_read_stderr` | `fn(p: @&Process, buf: *u8, max: i64) -> Result<i64, Errno>` | `process_read_stdout` for stderr |
| `process_read_stderr_all` | `fn(p: @&Process) -> Vec<u8>` | Read all stderr |

**Lifecycle**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `process_wait` | `fn(p: @&Process) -> Result<ProcessResult, Errno>` | Close stdin and block until exit; `Err(Child)` if nothing is left to wait for (already waited), else `Err` from wait4 |
| `process_kill` | `fn(p: @&Process)` | Kill process |
| `process_close_pipes` | `fn(p: @&Process)` | Close all pipes |
| `process_cleanup` | `fn(p: @&Process)` | Full cleanup |

**Result Helpers**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `result_success` | `fn(r: @ProcessResult) -> bool` | Exited normally with code 0? The code itself is `r.exit_code` |

**PATH Search**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `find_command` | `fn(name: StrView) -> Option<String>` | Search `$PATH`, or the standard dirs if it is unset or empty |
| `find_command_in` | `fn(name: StrView, path: StrView) -> Option<String>` | Search a `:`-separated dir list: first executable `dir/name`; an empty component is `.`; a name with `/` comes back as is |

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

| Function | Signature | Description |
|----------|-----------|-------------|
| `argspec_new` | `fn(program: StrView, about: StrView) -> ArgSpec` | Empty spec |
| `argspec_switch` | `fn(spec: @&ArgSpec, short: u8, long: StrView, help: StrView)` | Boolean option (`short` 0 / `long` `""` to omit a form) |
| `argspec_option` | `fn(spec: @&ArgSpec, short: u8, long: StrView, value_name: StrView, help: StrView, default: Option<StrView>)` | Option taking a value |
| `argspec_positionals` | `fn(spec: @&ArgSpec, name: StrView, help: StrView, min: i64, max: i64)` | Accept min..max positionals (`ARGS_UNLIMITED` = no max); none without this call |
| `argspec_find` | `fn(spec: @ArgSpec, name: StrView) -> Option<i64>` | Index of an option |
| `argspec_parse` | `fn(spec: @ArgSpec, args: Span<StrView>) -> Result<ParsedArgs, ArgError>` | Parse |
| `argspec_print_help` | `fn(spec: @ArgSpec)` | Usage, options and arguments on stdout |
| `argspec_drop` | `fn(spec: @&ArgSpec)` | Release the spec |

**Result** (a `ParsedArgs` shares the spec's storage; drop it first):

| Function | Signature | Description |
|----------|-----------|-------------|
| `parsed_switch` | `fn(p: @ParsedArgs, name: StrView) -> bool` | Switch given? (false for value options) |
| `parsed_is_set` | `fn(p: @ParsedArgs, name: StrView) -> bool` | Option given at all? |
| `parsed_value` | `fn(p: @ParsedArgs, name: StrView) -> Option<StrView>` | Given value, else default, else None |
| `parsed_int` | `fn(p: @ParsedArgs, name: StrView) -> Result<i64, ArgError>` | `parsed_value` as an i64 |
| `parsed_positional` | `fn(p: @ParsedArgs, i: i64) -> Option<StrView>` | i-th positional |
| `parsed_positionals` | `fn(p: @ParsedArgs) -> Span<StrView>` | All positionals |
| `parsed_drop` | `fn(p: @&ParsedArgs)` | Release the result |

**Errors**: `ArgError` is a struct `{ kind: ArgErrorKind, text: StrView, limit: i64 }`
with kinds `UnknownOption`, `MissingValue`, `UnexpectedValue`,
`MissingPositional`, `TooManyPositionals`, `NotANumber` and `NotSet`.
`arg_error_print(spec, @e)` writes `"<program>: <message>"` to stderr, and
`arg_parse_i64(s: StrView) -> Result<i64, ArgError>` is the strict decimal
parser `parsed_int` uses (sign, digits, range-checked).

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
    if parsed_switch(@parsed, "verbose")
        prints("verbose\n")
    let count: i64 = match parsed_int(@parsed, "count")
        Ok(n) => n
        Err(e) => -1
    parsed_drop(@&parsed)
    count as i32

fn fail(spec: @ArgSpec, e: ArgError) -> i32
    arg_error_print(spec, @e)
    2

fn main(argc: i32, argv: **u8) -> i32
    var all = args_from_argv(argc, argv)
    var spec = argspec_new("myprogram", "Description")
    argspec_switch(@&spec, 'v', "verbose", "Enable verbose output")
    argspec_option(@&spec, 'n', "count", "NUM", "Number of items", Some("10"))
    argspec_positionals(@&spec, "FILE", "Input file(s)", 0, ARGS_UNLIMITED)
    let status: i32 = match argspec_parse(@spec, args_tail(@all))
        Ok(p) => run(p)
        Err(e) => fail(@spec, e)
    argspec_drop(@&spec)
    vec_drop<StrView>(@&all)
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
| `env_must` | `fn(name: StrView) -> StrView` | Value of `name`; exits 1 with an error if unset |
| `env_iter` | `fn() -> Span<StrView>` | Every `"KEY=VALUE"` entry, in order |
| `env_raw_envp` | `fn() -> **u8` | The same entries as a NULL-terminated C `envp`, for `sys_execve` only |

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

| Function | Signature | Description |
|----------|-----------|-------------|
| `timer_init` | `fn(t: *Timer) -> i32` | Initialize |
| `timer_start` | `fn(t: *Timer) -> i32` | Start timer |
| `timer_stop` | `fn(t: *Timer) -> i32` | Stop timer |
| `timer_elapsed_nanos` | `fn(t: *Timer) -> i64` | Get elapsed ns |
| `timer_elapsed_micros` | `fn(t: *Timer) -> i64` | Get elapsed us |
| `timer_elapsed_millis` | `fn(t: *Timer) -> i64` | Get elapsed ms |
| `timer_print` | `fn(t: *Timer) -> i32` | Print human-readable |

**Stopwatch** (cumulative timing):

| Function | Signature | Description |
|----------|-----------|-------------|
| `stopwatch_init` | `fn(sw: *Stopwatch) -> i32` | Initialize |
| `stopwatch_start` | `fn(sw: *Stopwatch) -> i32` | Start |
| `stopwatch_stop` | `fn(sw: *Stopwatch) -> i32` | Stop |
| `stopwatch_reset` | `fn(sw: *Stopwatch) -> i32` | Reset |
| `stopwatch_total_nanos` | `fn(sw: *Stopwatch) -> i64` | Total ns |
| `stopwatch_avg_nanos` | `fn(sw: *Stopwatch) -> i64` | Average ns |
| `stopwatch_count` | `fn(sw: *Stopwatch) -> i64` | Number of samples |
| `stopwatch_print` | `fn(sw: *Stopwatch) -> i32` | Print stats |

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
| `json_free` | `fn(v: *JsonValue)` | Free JSON tree |

Strings are decoded to UTF-8: `\n \t \r \b \f \/ \" \\` and `\uXXXX`, with a
surrogate pair (`😀`) combined into one 4-byte sequence. Bad hex
digits, a short `\u`, a surrogate without its other half, or any other
escape (`\q`, `\x41`) fail with `JSON_ERR_INVALID_ESCAPE` at the escape's
backslash. `\u0000` is kept in a string value (`str_len` and
`json_get_string` count it) but rejected in an object key, which is stored as
a NUL-terminated `*u8`. A raw control character (U+0000–U+001F) inside a
string, key or value, fails with `JSON_ERR_CONTROL_CHAR` at that byte: RFC
8259 requires them escaped. Tabs and newlines between tokens are whitespace
and stay legal.

**Value Access**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `json_get_field` | `fn(obj: *JsonValue, key: StrView) -> Option<*JsonValue>` | Object field; None if missing or not an object |
| `json_get_index` | `fn(arr: *JsonValue, idx: i64) -> Option<*JsonValue>` | Array element; None if out of range or not an array |
| `json_get_string` | `fn(v: *JsonValue) -> Option<StrView>` | String value, borrowed from `v`; None if not a string |
| `json_get_number` | `fn(v: *JsonValue) -> Option<i64>` | Number value; None if not a number |
| `json_get_bool` | `fn(v: *JsonValue) -> Option<bool>` | Bool value; None if not a bool |
| `json_is_null` | `fn(v: *JsonValue) -> i32` | Check if null |
| `json_array_len` | `fn(v: *JsonValue) -> i64` | Get array length |
| `json_object_len` | `fn(v: *JsonValue) -> i64` | Get object size |

**Serialization**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `json_emit_value` | `fn(v: *JsonValue, buf: *Vec<u8>) -> i32` | Emit to buffer |
| `json_emit_bytes` | `fn(s: *u8, len: i64, buf: *Vec<u8>) -> i32` | Emit `s[0..len)` as a string; control characters as `\b \f \n \r \t` or `\u00XX` |
| `json_emit_string` | `fn(s: *u8, buf: *Vec<u8>) -> i32` | `json_emit_bytes` up to the first NUL |
| `json_to_string` | `fn(v: *JsonValue) -> String` | JSON text; caller owns (`string_drop`) |

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
| `elf_init` | `fn(reader: *ElfReader, data: *u8, size: i64) -> i32` | Initialize |
| `elf_parse_sections` | `fn(reader: *ElfReader) -> i32` | Parse sections |
| `elf_get_symbol_name` | `fn(reader: *ElfReader, sym_index: i64) -> *u8` | Get symbol name |
| `elf_get_symbol_info` | `fn(reader: *ElfReader, sym_index: i64) -> u8` | Get symbol info |
| `elf_is_function` | `fn(info: u8) -> i32` | Is function? |
| `elf_is_global` | `fn(info: u8) -> i32` | Is global? |
| `elf_symbol_count` | `fn(reader: *ElfReader) -> i64` | Get symbol count |
| `elf_find_test_functions` | `fn(reader: *ElfReader, callback: *u8, user_data: *u8) -> i32` | Find test_* functions |
| `elf_print_test_functions` | `fn(reader: *ElfReader)` | Print test functions |

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
            string_drop(@&content)
            0
        Err(e) => errno_code(e)
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
    vec_push<i32>(@&v, 42)
    let val: i32 = vec_get<i32>(@v, 0)
    vec_drop<i32>(@&v)
    val
```

**Async server with io_uring**:
```ritz
import ritzlib.async.tasks

fn handle_connection(task: *Task) -> i32
    0

fn run_server(listen_fd: i32) -> i32
    var srv: TaskServer
    task_server_init(@srv, listen_fd)
    task_server_run(@srv, handle_connection)
    task_server_destroy(@srv)
    0
```

---

*This documentation covers ritzlib as of 2026-09-03. Every fenced `ritz` block
above is compiled against the real ritzlib by `tools/check_doc_examples.py` on
every build, so the examples cannot silently rot; the signature tables are
hand-checked against `ritzlib/*.ritz` and are not machine-verified, so the
source files remain the final authority.*
