# Ritzlib Standard Library Reference

The Ritz Standard Library (ritzlib) provides essential functionality for Ritz programs. Unlike traditional standard libraries that wrap libc, ritzlib interfaces directly with the Linux kernel through syscalls, resulting in smaller binaries and eliminating C runtime dependencies.

---

## Philosophy

**No libc, No Dependencies**

Ritzlib is built on three core principles:

1. **Direct Syscalls**: All system interaction goes through Linux syscalls, with no libc dependency. This means Ritz binaries are truly standalone.

2. **Zero-Cost Abstractions**: High-level types like `String`, `Vec<T>`, and `HashMap` compile down to efficient machine code with no runtime overhead.

3. **Explicit Resource Management**: Resources are managed through the `Drop` trait for automatic cleanup, or explicit `*_drop()` functions for manual control.

**Target Platform**: Linux x86-64 (kernel 5.1+ for io_uring features)

---

## Table of Contents

1. [Core Types](#core-types)
   - [option](#option) - Optional values
   - [result](#result) - Error handling
   - [drop](#drop) - Automatic cleanup trait
   - [eq](#eq) - Equality comparison
   - [hash](#hash) - Hashing utilities
2. [Memory Management](#memory-management)
   - [memory](#memory) - Allocators (Arena, Heap, malloc/free)
   - [box](#box) - Heap-allocated single values
   - [heap](#heap) - Heap keyword support
3. [Collections](#collections)
   - [gvec](#gvec) - Generic dynamic array (`Vec<T>`)
   - [string](#string) - Owned UTF-8 strings
   - [hashmap](#hashmap) - Hash map for i64 keys
   - [span](#span) - Non-owning memory views
4. [String Utilities](#string-utilities)
   - [str](#str) - C-style string operations
   - [buf](#buf) - Buffer and parsing utilities
5. [System Interface](#system-interface)
   - [sys](#sys) - Raw syscall wrappers
   - [crt0](#crt0) - Program entry point
6. [I/O Operations](#io-operations)
   - [io](#io) - Console I/O
   - [fs](#fs) - Filesystem operations
   - [iovec](#iovec) - Vectored I/O for scatter/gather writes
7. [Networking](#networking)
   - [net](#net) - TCP/IP socket operations
   - [async_net](#async_net) - Async TCP networking
8. [Async Runtime](#async-runtime)
   - [async](#async) - Async primitives (Poll, Waker, Context)
   - [async_runtime](#async_runtime) - io_uring-backed runtime
   - [async_tasks](#async_tasks) - Multi-task executor
   - [async_fs](#async_fs) - Async filesystem operations
   - [executor](#executor) - Simple async executor
   - [uring](#uring) - io_uring bindings
9. [Process Management](#process-management)
   - [process](#process) - Subprocess spawning
   - [args](#args) - Argument parsing
   - [env](#env) - Environment variables
10. [Utilities](#utilities)
    - [timer](#timer) - High-precision timing
    - [json](#json) - JSON parsing
    - [elf](#elf) - ELF binary parsing
    - [meta](#meta) - Module metadata
    - [testing](#testing) - Test framework

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

fn find_first(items: *Vec<i32>, target: i32) -> Option<i32>
    var i: i64 = 0
    while i < vec_len(items)
        if vec_get(items, i) == target
            return Some(i as i32)
        i += 1
    return None
```

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
import ritzlib.result

fn parse_int(s: *u8) -> Result<i32, i32>
    if strlen(s) == 0
        return Err(1)  # Error code for empty string
    # ... parsing logic ...
    return Ok(value)
```

---

### drop

**Module**: `ritzlib.drop`

The Drop trait enables automatic cleanup when values go out of scope.

```ritz
trait Drop
    fn drop(self: &mut Self)
```

The compiler automatically inserts drop calls at:
- End of block scope
- Before return statements
- Before break/continue in loops

Drop is called in reverse declaration order (LIFO).

---

### eq

**Module**: `ritzlib.eq`

Equality comparison functions for primitive types.

| Function | Signature | Description |
|----------|-----------|-------------|
| `eq_i32` | `fn(a: i32, b: i32) -> i32` | Returns 1 if equal, 0 otherwise |
| `eq_i64` | `fn(a: i64, b: i64) -> i32` | Returns 1 if equal, 0 otherwise |
| `eq_u64` | `fn(a: u64, b: u64) -> i32` | Returns 1 if equal, 0 otherwise |

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

---

## Memory Management

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
| `calloc` | `fn(count: i64, size: i64) -> *u8` | Allocate and zero-initialize |

**Utility**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `memzero` | `fn(dst: *u8, n: i64)` | Zero n bytes at dst |

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
| `box_get` | `fn<T>(b: &Box<T>) -> T` | Get value (returns copy) |
| `box_as_ptr` | `fn<T>(b: &Box<T>) -> *T` | Get pointer to value |
| `box_set` | `fn<T>(b: &mut Box<T>, value: T)` | Set new value |
| `box_drop` | `fn<T>(b: &mut Box<T>)` | Free the box |
| `box_valid` | `fn<T>(b: &Box<T>) -> i32` | Check if valid |

**Methods** (via impl):
- `get`, `as_ptr`, `set`, `valid`

---

### heap

**Module**: `ritzlib.heap`

Alternative to Box using the `heap` keyword.

```ritz
struct Heap<T>
    ptr: *T
```

**Usage**:
```ritz
var p = heap 42           # Using heap keyword (preferred)
var p = heap_new<i64>(42) # Explicit constructor
```

**Functions**: Same as `box` module with `heap_` prefix.

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
| `vec_push` | `fn<T>(v: &mut Vec<T>, item: T) -> i32` | Push element (0 on success) |
| `vec_pop` | `fn<T>(v: &mut Vec<T>) -> T` | Pop last element |
| `vec_get` | `fn<T>(v: &Vec<T>, idx: i64) -> T` | Get element by index |
| `vec_get_ptr` | `fn<T>(v: &mut Vec<T>, idx: i64) -> *T` | Get pointer to element |
| `vec_set` | `fn<T>(v: &mut Vec<T>, idx: i64, item: T) -> i32` | Set element |
| `vec_len` | `fn<T>(v: &Vec<T>) -> i64` | Get length |
| `vec_cap` | `fn<T>(v: &Vec<T>) -> i64` | Get capacity |
| `vec_is_empty` | `fn<T>(v: &Vec<T>) -> i32` | Check if empty |
| `vec_clear` | `fn<T>(v: &mut Vec<T>)` | Clear (keeps capacity) |
| `vec_drop` | `fn<T>(v: &mut Vec<T>)` | Free the Vec |

**Utilities**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `vec_first` | `fn<T>(v: &Vec<T>) -> T` | Get first element |
| `vec_last` | `fn<T>(v: &Vec<T>) -> T` | Get last element |
| `vec_as_ptr` | `fn<T>(v: &Vec<T>) -> *T` | Get raw pointer |
| `vec_slice` | `fn<T>(v: &Vec<T>, start: i64, end: i64) -> Vec<T>` | Create slice copy |
| `vec_swap` | `fn<T>(v: &mut Vec<T>, i: i64, j: i64) -> i32` | Swap elements |
| `vec_push_bytes` | `fn<T>(v: &mut Vec<T>, data: *T, len: i64) -> i32` | Push multiple |
| `vec_push_str` | `fn(v: &mut Vec<u8>, s: *u8) -> i32` | Push C string |
| `vec_as_str` | `fn(v: &mut Vec<u8>) -> *u8` | Get null-terminated string |

**File/Line Utilities**:

```ritz
struct LineBounds
    start: i64      # Start offset in buffer
    length: i64     # Length in bytes
```

| Function | Signature | Description |
|----------|-----------|-------------|
| `vec_read_all_fd` | `fn(fd: i32, v: &mut Vec<u8>) -> i64` | Read file into Vec |
| `vec_find_lines` | `fn(buf: &Vec<u8>, lines: &mut Vec<LineBounds>) -> i32` | Find line boundaries |

---

### string

**Module**: `ritzlib.string`

Owned, growable UTF-8 string. Always null-terminated for C interop.

```ritz
struct String
    data: Vec<u8>    # Underlying byte storage
```

**Constructors**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `string_new` | `fn() -> String` | Create empty string |
| `string_with_cap` | `fn(cap: i64) -> String` | Create with capacity |
| `string_from` | `fn(cstr: *u8) -> String` | Create from C string |
| `string_from_bytes` | `fn(bytes: *u8, len: i64) -> String` | Create from bytes |

**Accessors**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `string_len` | `fn(s: &String) -> i64` | Get length |
| `string_cap` | `fn(s: &String) -> i64` | Get capacity |
| `string_is_empty` | `fn(s: &String) -> i32` | Check if empty |
| `string_as_ptr` | `fn(s: &mut String) -> *u8` | Get null-terminated C string |
| `string_get` | `fn(s: &String, idx: i64) -> u8` | Get byte at index |
| `string_char_at` | `fn(s: &String, idx: i64) -> u8` | Get char at index |

**Modification**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `string_push` | `fn(s: &mut String, b: u8) -> i32` | Push byte |
| `string_push_str` | `fn(s: &mut String, cstr: *u8) -> i32` | Push C string |
| `string_push_string` | `fn(s: &mut String, other: &String) -> i32` | Push String |
| `string_push_bytes` | `fn(s: &mut String, bytes: *u8, len: i64) -> i32` | Push bytes |
| `string_push_i64` | `fn(s: &mut String, n: i64) -> i32` | Push integer |
| `string_clear` | `fn(s: &mut String)` | Clear string |
| `string_pop` | `fn(s: &mut String) -> u8` | Pop last byte |
| `string_set_char` | `fn(s: &mut String, idx: i64, c: u8) -> i32` | Set char at index |
| `string_drop` | `fn(s: &mut String)` | Free string |

**Comparison**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `string_eq` | `fn(a: &String, b: &String) -> i32` | Compare for equality |
| `string_eq_cstr` | `fn(s: &String, cstr: *u8) -> i32` | Compare to C string |
| `string_hash` | `fn(s: &String) -> u64` | Hash the string |

**Search/Slice**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `string_starts_with` | `fn(s: &String, prefix: *u8) -> i32` | Check prefix |
| `string_ends_with` | `fn(s: &String, suffix: *u8) -> i32` | Check suffix |
| `string_contains` | `fn(s: &String, needle: *u8) -> i32` | Check contains |
| `string_find` | `fn(s: &String, needle: &String) -> i64` | Find substring (-1 if not found) |
| `string_slice` | `fn(s: &String, start: i64, end: i64) -> String` | Extract substring |
| `string_clone` | `fn(s: &String) -> String` | Deep copy |

**Conversion**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `string_from_i64` | `fn(n: i64) -> String` | Integer to String |
| `string_from_hex` | `fn(n: u64) -> String` | Integer to hex String |

---

### hashmap

**Module**: `ritzlib.hashmap`

Hash map for i64 keys and i64 values using open addressing with linear probing.

```ritz
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

**Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `hashmap_i64_insert` | `fn(m: &mut HashMapI64, key: i64, value: i64)` | Insert or update |
| `hashmap_i64_get` | `fn(m: &HashMapI64, key: i64) -> i64` | Get value (0 if not found) |
| `hashmap_i64_contains` | `fn(m: &HashMapI64, key: i64) -> i32` | Check if key exists |
| `hashmap_i64_remove` | `fn(m: &mut HashMapI64, key: i64) -> i32` | Remove key (1 if removed) |
| `hashmap_i64_len` | `fn(m: &HashMapI64) -> i64` | Get entry count |
| `hashmap_i64_cap` | `fn(m: &HashMapI64) -> i64` | Get capacity |
| `hashmap_i64_is_empty` | `fn(m: &HashMapI64) -> i32` | Check if empty |
| `hashmap_i64_drop` | `fn(m: &mut HashMapI64)` | Free the map |

**Methods** (via impl): `len`, `cap`, `is_empty`, `insert`, `get`, `contains`, `remove`

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
| `span_is_empty` | `fn<T>(s: *Span<T>) -> i32` | Check if empty |
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

| Function | Signature | Description |
|----------|-----------|-------------|
| `span_eq` | `fn(a: *Span<u8>, b: *Span<u8>) -> i32` | Compare equality |
| `span_eq_cstr` | `fn(s: *Span<u8>, cstr: *u8) -> i32` | Compare to C string |
| `span_contains` | `fn(haystack: *Span<u8>, needle: *Span<u8>) -> i32` | Contains check |
| `span_starts_with` | `fn(s: *Span<u8>, prefix: *Span<u8>) -> i32` | Prefix check |
| `span_ends_with` | `fn(s: *Span<u8>, suffix: *Span<u8>) -> i32` | Suffix check |
| `span_find` | `fn(haystack: *Span<u8>, needle: *Span<u8>) -> i64` | Find substring |
| `span_find_byte` | `fn(s: *Span<u8>, c: u8) -> i64` | Find byte |

**Pre-computed HTTP Constants**:

| Function | Returns |
|----------|---------|
| `http_200_ok` | `"HTTP/1.1 200 OK\r\n"` |
| `http_404_not_found` | `"HTTP/1.1 404 Not Found\r\n"` |
| `http_400_bad_request` | `"HTTP/1.1 400 Bad Request\r\n"` |
| `http_content_type_text` | `"Content-Type: text/plain\r\n"` |
| `http_content_type_html` | `"Content-Type: text/html\r\n"` |
| `http_content_type_json` | `"Content-Type: application/json\r\n"` |
| `http_crlf` | `"\r\n"` |
| `http_hello_world` | `"Hello, World!"` |

---

## String Utilities

### str

**Module**: `ritzlib.str`

C-style null-terminated string operations.

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

### buf

**Module**: `ritzlib.buf`

Buffer utilities for parsing.

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
| `buf_init` | `fn(buf: *Buffer, data: *u8, len: i64) -> i32` | Initialize |
| `buf_from_str` | `fn(buf: *Buffer, s: *u8) -> i32` | From C string |

**Position**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_pos` | `fn(buf: *Buffer) -> i64` | Current position |
| `buf_len` | `fn(buf: *Buffer) -> i64` | Total length |
| `buf_remaining` | `fn(buf: *Buffer) -> i64` | Remaining bytes |
| `buf_eof` | `fn(buf: *Buffer) -> i32` | At end? |
| `buf_save` | `fn(buf: *Buffer) -> i64` | Save position |
| `buf_restore` | `fn(buf: *Buffer, pos: i64) -> i32` | Restore position |

**Peek (Don't Advance)**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_peek` | `fn(buf: *Buffer) -> u8` | Peek current byte |
| `buf_peek_at` | `fn(buf: *Buffer, offset: i64) -> u8` | Peek at offset |
| `buf_peek_n` | `fn(buf: *Buffer, out: *u8, n: i64) -> i64` | Peek n bytes |

**Consume (Advance)**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_advance` | `fn(buf: *Buffer) -> u8` | Read and advance |
| `buf_advance_n` | `fn(buf: *Buffer, n: i64) -> i64` | Advance n bytes |
| `buf_skip` | `fn(buf: *Buffer, n: i64) -> i32` | Skip n bytes |

**Pattern Matching**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_match_char` | `fn(buf: *Buffer, c: u8) -> i32` | Match and consume char |
| `buf_match_str` | `fn(buf: *Buffer, s: *u8) -> i32` | Match and consume string |
| `buf_starts_with` | `fn(buf: *Buffer, s: *u8) -> i32` | Check prefix |

**Skip Utilities**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_skip_whitespace` | `fn(buf: *Buffer) -> i64` | Skip whitespace |
| `buf_skip_until` | `fn(buf: *Buffer, c: u8) -> i64` | Skip until char |

**Read Utilities**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_read_until` | `fn(buf: *Buffer, c: u8, out: *u8, max: i64) -> i64` | Read until char |
| `buf_read_while_digit` | `fn(buf: *Buffer, out: *u8, max: i64) -> i64` | Read digits |
| `buf_read_while_alnum` | `fn(buf: *Buffer, out: *u8, max: i64) -> i64` | Read alphanumeric |
| `buf_read_quoted` | `fn(buf: *Buffer, quote: u8, out: *u8, max: i64) -> i64` | Read quoted string |

**Location Tracking**:

```ritz
struct BufLoc
    line: i32
    col: i32
    offset: i64
```

| Function | Signature | Description |
|----------|-----------|-------------|
| `buf_get_loc` | `fn(buf: *Buffer, loc: *BufLoc) -> i32` | Get line/column |

#### GrowBuf (Growable Buffer)

```ritz
struct GrowBuf
    data: *u8
    len: i64
    cap: i64
```

**Has automatic `Drop` implementation.**

| Function | Signature | Description |
|----------|-----------|-------------|
| `growbuf_new` | `fn() -> GrowBuf` | Create empty |
| `growbuf_with_cap` | `fn(cap: i64) -> GrowBuf` | Create with capacity |
| `growbuf_free` | `fn(b: *GrowBuf) -> i32` | Free (deprecated, use Drop) |
| `growbuf_grow` | `fn(b: *GrowBuf, new_cap: i64) -> i32` | Grow capacity |
| `growbuf_ensure_cap` | `fn(b: *GrowBuf, needed: i64) -> i32` | Ensure capacity |
| `growbuf_append` | `fn(b: *GrowBuf, data: *u8, len: i64) -> i32` | Append bytes |
| `growbuf_append_byte` | `fn(b: *GrowBuf, byte: u8) -> i32` | Append single byte |
| `growbuf_clear` | `fn(b: *GrowBuf) -> i32` | Clear (keep capacity) |
| `growbuf_len` | `fn(b: *GrowBuf) -> i64` | Get length |
| `growbuf_data` | `fn(b: *GrowBuf) -> *u8` | Get data pointer |
| `read_all_fd` | `fn(fd: i32, b: *GrowBuf) -> i64` | Read file descriptor |

---

## System Interface

### sys

**Module**: `ritzlib.sys`

Low-level syscall wrappers for Linux x86-64.

#### Raw Syscall Interface

| Function | Signature |
|----------|-----------|
| `syscall0` | `extern fn(n: i64) -> i64` |
| `syscall1` | `extern fn(n: i64, a1: i64) -> i64` |
| `syscall2` | `extern fn(n: i64, a1: i64, a2: i64) -> i64` |
| `syscall3` | `extern fn(n: i64, a1: i64, a2: i64, a3: i64) -> i64` |
| `syscall4` | `extern fn(n: i64, a1: i64, a2: i64, a3: i64, a4: i64) -> i64` |
| `syscall5` | `extern fn(n: i64, a1: i64, a2: i64, a3: i64, a4: i64, a5: i64) -> i64` |
| `syscall6` | `extern fn(n: i64, a1: i64, a2: i64, a3: i64, a4: i64, a5: i64, a6: i64) -> i64` |

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

### crt0

**Module**: `ritzlib.crt0`

Reference documentation for the `_start` entry point. The actual entry point is generated by the compiler.

**Main Function Variants**:
```ritz
fn main() -> i32                         # 0-arg
fn main(argc: i32, argv: **u8) -> i32    # 2-arg
fn main(argc: i32, argv: **u8, envp: **u8) -> i32  # 3-arg
```

The `_start` function:
1. Aligns stack to 16 bytes
2. Extracts argc, argv, envp from stack
3. Calls main()
4. Passes return value to exit syscall

---

## I/O Operations

### io

**Module**: `ritzlib.io`

High-level console I/O functions.

**Output to stdout**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `prints` | `fn(s: *u8)` | Print C string |
| `println` | `fn(s: *u8)` | Print with newline |
| `print_char` | `fn(c: u8)` | Print character |
| `print_int` | `fn(n: i64)` | Print integer |
| `print_hex` | `fn(n: i64)` | Print hex with 0x prefix |
| `print_size_human` | `fn(size: i64)` | Print human-readable size (K/M/G/T) |
| `newline` | `fn()` | Print newline |

**Output to stderr**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `eprints` | `fn(s: *u8)` | Print to stderr |
| `eprintln` | `fn(s: *u8)` | Print to stderr with newline |
| `eprint_char` | `fn(c: u8)` | Print char to stderr |
| `eprint_int` | `fn(n: i64)` | Print int to stderr |

**String Type Output**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `print_string` | `fn(s: *String)` | Print String |
| `println_string` | `fn(s: *String)` | Print String with newline |
| `print_i64` | `fn(n: i64)` | Print i64 as String |
| `println_i64` | `fn(n: i64)` | Print i64 with newline |
| `print_hex64` | `fn(n: u64)` | Print hex |

---

### fs

**Module**: `ritzlib.fs`

High-level filesystem operations.

**Path Checking**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `path_exists` | `fn(path: *u8) -> i32` | Check if path exists |
| `is_directory` | `fn(path: *u8) -> i32` | Is directory? |
| `is_regular_file` | `fn(path: *u8) -> i32` | Is regular file? |
| `is_symlink` | `fn(path: *u8) -> i32` | Is symlink? |
| `file_size` | `fn(path: *u8) -> i64` | Get file size |

**Mode Helpers**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `mode_is_dir` | `fn(mode: i32) -> i32` | Check mode is directory |
| `mode_is_file` | `fn(mode: i32) -> i32` | Check mode is regular file |
| `mode_is_link` | `fn(mode: i32) -> i32` | Check mode is symlink |

**Stat Buffer Accessors** (legacy):

| Function | Signature | Description |
|----------|-----------|-------------|
| `stat_get_mode` | `fn(statbuf: *u8) -> i32` | Get mode from stat |
| `stat_get_size` | `fn(statbuf: *u8) -> i64` | Get size from stat |
| `stat_get_uid` | `fn(statbuf: *u8) -> i32` | Get UID |
| `stat_get_gid` | `fn(statbuf: *u8) -> i32` | Get GID |

**Dirent Helpers**:

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

**Path Utilities**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `path_join` | `fn(dir: *u8, name: *u8, buf: *u8) -> i64` | Join paths |
| `path_basename` | `fn(path: *u8) -> *u8` | Get filename |
| `path_dirname` | `fn(path: *u8, buf: *u8) -> *u8` | Get directory |

**String-based Path Utilities**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `path_join_string` | `fn(dir: *String, name: *String) -> String` | Join paths |
| `path_basename_string` | `fn(path: *String) -> String` | Get filename |
| `path_dirname_string` | `fn(path: *String) -> String` | Get directory |
| `path_extension_string` | `fn(path: *String) -> String` | Get extension |
| `path_stem_string` | `fn(path: *String) -> String` | Strip extension |

**File Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `copy_file` | `fn(src: *u8, dest: *u8, mode: i32) -> i32` | Copy file |

**String-based File Operations with Result**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `path_exists_string` | `fn(path: *String) -> i32` | Check exists |
| `is_directory_string` | `fn(path: *String) -> i32` | Is directory |
| `file_size_string` | `fn(path: *String) -> Result<i64, i32>` | Get size |
| `read_file_string` | `fn(path: *String, out: &mut String) -> i32` | Read file |
| `write_file_string` | `fn(path: *String, content: *String) -> Result<i64, i32>` | Write file |
| `mkdir_string` | `fn(path: *String, mode: i32) -> i32` | Create directory |
| `unlink_string` | `fn(path: *String) -> i32` | Remove file |
| `rmdir_string` | `fn(path: *String) -> i32` | Remove directory |
| `copy_file_string` | `fn(src: *String, dest: *String, mode: i32) -> Result<i64, i32>` | Copy file |

**Error Codes**: `FS_ERR_NOT_FOUND`, `FS_ERR_PERMISSION`, `FS_ERR_IO`, `FS_ERR_NOT_DIR`, `FS_ERR_IS_DIR`, `FS_ERR_EXISTS`

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

TCP/IP socket operations.

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
| `parse_ipv4` | `fn(addr_str: *u8) -> u32` | Parse "127.0.0.1" |

**Socket Creation**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `socket_tcp` | `fn() -> Socket` | Create TCP socket |
| `socket_tcp_nonblock` | `fn() -> Socket` | Create non-blocking TCP |
| `socket_udp` | `fn() -> Socket` | Create UDP socket |
| `socket_valid` | `fn(sock: *Socket) -> i32` | Check if valid |
| `socket_close` | `fn(sock: *Socket) -> i32` | Close socket |

**Socket Options**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `socket_set_reuseaddr` | `fn(sock: *Socket) -> i32` | Enable SO_REUSEADDR |
| `socket_set_reuseport` | `fn(sock: *Socket) -> i32` | Enable SO_REUSEPORT |
| `socket_set_nodelay` | `fn(sock: *Socket) -> i32` | Disable Nagle |

**Server Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `socket_bind` | `fn(sock: *Socket, addr: *u8, port: i32) -> i32` | Bind to address |
| `socket_bind_any` | `fn(sock: *Socket, port: i32) -> i32` | Bind to 0.0.0.0 |
| `socket_listen` | `fn(sock: *Socket, backlog: i32) -> i32` | Start listening |
| `socket_accept` | `fn(sock: *Socket) -> Socket` | Accept (blocking) |
| `socket_accept_nonblock` | `fn(sock: *Socket) -> Socket` | Accept (non-blocking) |

**Client Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `socket_connect` | `fn(sock: *Socket, addr: *u8, port: i32) -> i32` | Connect |
| `socket_send` | `fn(sock: *Socket, buf: *u8, len: i64) -> i64` | Send data |
| `socket_recv` | `fn(sock: *Socket, buf: *u8, len: i64) -> i64` | Receive data |
| `socket_send_string` | `fn(sock: *Socket, s: *String) -> i64` | Send String |

**Epoll Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `epoll_create` | `fn() -> i32` | Create epoll instance |
| `epoll_add` | `fn(epfd: i32, fd: i32, events: u32) -> i32` | Add fd |
| `epoll_del` | `fn(epfd: i32, fd: i32) -> i32` | Remove fd |
| `epoll_mod` | `fn(epfd: i32, fd: i32, events: u32) -> i32` | Modify events |
| `epoll_wait_events` | `fn(epfd: i32, events: *EpollEvent, max: i32, timeout: i32) -> i32` | Wait |

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

### async

**Module**: `ritzlib.async`

Core async/await primitives.

```ritz
enum Poll<T>
    Ready(T)
    Pending

struct Waker
    task_ptr: *u8
    wake_fn: *u8

struct Context
    waker: *Waker

struct Task
    id: i64
    future_ptr: *u8
    poll_fn: *u8
    drop_fn: *u8
    completed: i32
```

| Function | Signature | Description |
|----------|-----------|-------------|
| `poll_is_ready` | `fn<T>(p: *Poll<T>) -> i32` | Check if Ready |
| `poll_is_pending` | `fn<T>(p: *Poll<T>) -> i32` | Check if Pending |
| `waker_wake` | `fn(w: *Waker)` | Wake the task |
| `waker_clone` | `fn(w: *Waker) -> Waker` | Clone waker |
| `context_waker` | `fn(cx: *Context) -> *Waker` | Get waker from context |

---

### async_runtime

**Module**: `ritzlib.async_runtime`

io_uring-backed async runtime.

```ritz
struct Runtime
    ring: IoUring
    initialized: i32
    next_user_data: i64
```

| Function | Signature | Description |
|----------|-----------|-------------|
| `runtime_init` | `fn(rt: *Runtime) -> i32` | Initialize runtime |
| `runtime_destroy` | `fn(rt: *Runtime)` | Destroy runtime |
| `runtime_read` | `fn(rt: *Runtime, fd: i32, buf: *u8, count: i32, offset: i64) -> i64` | Async read |
| `runtime_write` | `fn(rt: *Runtime, fd: i32, buf: *u8, count: i32, offset: i64) -> i64` | Async write |
| `runtime_close` | `fn(rt: *Runtime, fd: i32) -> i32` | Async close |
| `get_runtime` | `fn() -> *Runtime` | Get global runtime |
| `cleanup_runtime` | `fn()` | Cleanup global runtime |

---

### async_tasks

**Module**: `ritzlib.async_tasks`

Multi-task async executor with io_uring for concurrent servers.

**Constants**:
- `MAX_TASKS`: 256
- `TASK_BUFFER_SIZE`: 8192

**Task States**: `TASK_IDLE`, `TASK_WAITING`, `TASK_READY`

```ritz
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
    iov_builder: IoVecBuilder
    request_count: i32
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
    running: i32
    shutdown_hook: fn() -> i32
    idle_timeout: i32
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
| `task_splice` | `fn(task: *Task, fd_in: i32, off_in: i64, len: u32, flags: i32) -> i32` | Splice |
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
| `task_server_set_max_connections` | `fn(srv: *TaskServer, max: i32)` | Set max connections |

---

### async_fs

**Module**: `ritzlib.async_fs`

Async filesystem operations.

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

### executor

**Module**: `ritzlib.executor`

Simple async executor with io_uring.

```ritz
struct Executor
    ring: IoUring
    initialized: i32
    next_user_data: i64
    waker_user_data: i64
    waker_io_result: i32
    waker_active: i32
```

| Function | Signature | Description |
|----------|-----------|-------------|
| `executor_init` | `fn(exec: *Executor) -> i32` | Initialize |
| `executor_destroy` | `fn(exec: *Executor)` | Destroy |
| `block_on` | `fn(exec: *Executor, future_ptr: *u8, poll_fn: fn(*u8) -> i32) -> i32` | Run future to completion |
| `exec_async_read` | `fn(exec: *Executor, fd: i32, buf: *u8, len: i32, offset: i64) -> i32` | Async read |
| `exec_async_write` | `fn(exec: *Executor, fd: i32, buf: *u8, len: i32, offset: i64) -> i32` | Async write |
| `exec_async_accept` | `fn(exec: *Executor, server_fd: i32) -> i32` | Async accept |
| `exec_async_recv` | `fn(exec: *Executor, fd: i32, buf: *u8, len: i32, flags: i32) -> i32` | Async recv |
| `exec_async_send` | `fn(exec: *Executor, fd: i32, buf: *u8, len: i32, flags: i32) -> i32` | Async send |
| `exec_async_close` | `fn(exec: *Executor, fd: i32) -> i32` | Async close |

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
    sqes: *IoUringSqe
    cq_head: *i32
    cq_tail: *i32
    cq_mask: i32
    cqes: *IoUringCqe
    # ...
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
| `uring_prep_accept_multishot` | `fn(sqe: *IoUringSqe, ...)` | Multishot accept (5.19+) |
| `uring_prep_close` | `fn(sqe: *IoUringSqe, fd: i32, user_data: i64)` | Prepare close |
| `uring_prep_recv` | `fn(sqe: *IoUringSqe, fd: i32, buf: *u8, len: u64, flags: i32, user_data: i64)` | Prepare recv |
| `uring_prep_send` | `fn(sqe: *IoUringSqe, fd: i32, buf: *u8, len: u64, flags: i32, user_data: i64)` | Prepare send |
| `uring_prep_send_zc` | `fn(sqe: *IoUringSqe, fd: i32, buf: *u8, len: u64, flags: i32, user_data: i64)` | Zero-copy send (6.0+) |
| `uring_prep_readv` | `fn(sqe: *IoUringSqe, fd: i32, iov: *u8, nr_vecs: i32, offset: i64, user_data: i64)` | Vectored read |
| `uring_prep_writev` | `fn(sqe: *IoUringSqe, fd: i32, iov: *u8, nr_vecs: i32, offset: i64, user_data: i64)` | Vectored write |
| `uring_prep_splice` | `fn(sqe: *IoUringSqe, fd_out: i32, off_out: i64, fd_in: i32, off_in: i64, len: u32, flags: i32, user_data: i64)` | Splice |
| `uring_prep_timeout` | `fn(sqe: *IoUringSqe, ts: *KernelTimespec, count: u32, flags: u32, user_data: i64)` | Timeout |

**Safety Note**: Zero-copy operations (`IORING_OP_SEND_ZC`) require the buffer to remain valid until the CQE is received.

---

## Process Management

### process

**Module**: `ritzlib.process`

Subprocess spawning with connected pipes.

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
| `spawn` | `fn(cmd: *u8) -> Process` | Spawn command |
| `spawn_args` | `fn(cmd: *u8, argv: **u8) -> Process` | Spawn with args |
| `spawn_full` | `fn(cmd: *u8, argv: **u8, envp: **u8) -> Process` | Spawn with env |
| `process_valid` | `fn(p: *Process) -> i32` | Check if valid |

**I/O Operations**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `process_write` | `fn(p: *Process, data: *u8, len: i64) -> i64` | Write to stdin |
| `process_write_str` | `fn(p: *Process, s: *u8) -> i64` | Write string to stdin |
| `process_close_stdin` | `fn(p: *Process)` | Close stdin (EOF) |
| `process_read_stdout` | `fn(p: *Process, buf: *u8, max: i64) -> i64` | Read from stdout |
| `process_read_stdout_all` | `fn(p: *Process) -> Vec<u8>` | Read all stdout |
| `process_read_line` | `fn(p: *Process) -> Vec<u8>` | Read line |
| `process_read_stderr` | `fn(p: *Process, buf: *u8, max: i64) -> i64` | Read stderr |
| `process_read_stderr_all` | `fn(p: *Process) -> Vec<u8>` | Read all stderr |

**Lifecycle**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `process_wait` | `fn(p: *Process) -> ProcessResult` | Wait for exit |
| `process_kill` | `fn(p: *Process)` | Kill process |
| `process_close_pipes` | `fn(p: *Process)` | Close all pipes |
| `process_cleanup` | `fn(p: *Process)` | Full cleanup |

**Result Helpers**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `result_success` | `fn(r: *ProcessResult) -> i32` | Exited with code 0? |
| `result_code` | `fn(r: *ProcessResult) -> i32` | Get exit code |

**PATH Search**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `find_command_in_path` | `fn(name: *u8, buf: *u8, bufsize: i64) -> *u8` | Find command |

---

### args

**Module**: `ritzlib.args`

Declarative argument parsing.

```ritz
struct ArgParser
    program_name: *u8
    description: *u8
    options: [32]OptDef
    option_count: i32
    pos_defs: [8]PosDef
    pos_def_count: i32
    positionals: [256]*u8
    positional_count: i32
```

**Setup**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `args_init` | `fn(parser: *ArgParser, program: *u8, desc: *u8)` | Initialize |
| `args_flag` | `fn(parser: *ArgParser, short: u8, long: *u8, desc: *u8)` | Add flag |
| `args_option` | `fn(parser: *ArgParser, short: u8, long: *u8, value_name: *u8, desc: *u8, default: *u8)` | Add option |
| `args_positional` | `fn(parser: *ArgParser, name: *u8, desc: *u8, min: i32, max: i32)` | Add positional |

**Parsing**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `args_parse` | `fn(parser: *ArgParser, argc: i32, argv: **u8) -> i32` | Parse arguments |

**Value Retrieval**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `args_get_flag` | `fn(parser: *ArgParser, short: u8) -> i32` | Get flag by short name |
| `args_get_flag_long` | `fn(parser: *ArgParser, long: *u8) -> i32` | Get flag by long name |
| `args_get_str` | `fn(parser: *ArgParser, short: u8) -> *u8` | Get string option |
| `args_get_str_long` | `fn(parser: *ArgParser, long: *u8) -> *u8` | Get string by long name |
| `args_get_int` | `fn(parser: *ArgParser, short: u8) -> i64` | Get integer option |
| `args_get_int_long` | `fn(parser: *ArgParser, long: *u8) -> i64` | Get integer by long name |
| `args_get_positional` | `fn(parser: *ArgParser, idx: i32) -> *u8` | Get positional arg |
| `args_is_set` | `fn(parser: *ArgParser, short: u8) -> i32` | Check if option was provided |

**Help**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `args_print_usage` | `fn(parser: *ArgParser)` | Print usage |
| `args_print_help` | `fn(parser: *ArgParser)` | Print full help |

**Example**:
```ritz
import ritzlib.args

fn main(argc: i32, argv: **u8) -> i32
    var parser: ArgParser
    args_init(&parser, "myprogram", "Description")
    args_flag(&parser, 'v', "verbose", "Enable verbose output")
    args_option(&parser, 'n', "count", "NUM", "Number of items", "10")
    args_positional(&parser, "FILE", "Input file(s)", 0, -1)

    if args_parse(&parser, argc, argv) != 0
        return 1

    let verbose: i32 = args_get_flag(&parser, 'v')
    let count: i64 = args_get_int(&parser, 'n')
    # ...
```

---

### env

**Module**: `ritzlib.env`

Environment variable access.

**Usage**: Use 3-argument main to receive envp.

| Function | Signature | Description |
|----------|-----------|-------------|
| `getenv` | `fn(envp: **u8, name: *u8) -> *u8` | Get env variable value |
| `env_count` | `fn(envp: **u8) -> i32` | Count env variables |
| `env_get` | `fn(envp: **u8, index: i32) -> *u8` | Get entry at index |
| `env_get_name` | `fn(entry: *u8, buf: *u8, bufsize: i64) -> i64` | Extract name from "NAME=VALUE" |
| `env_get_value` | `fn(entry: *u8) -> *u8` | Get value from "NAME=VALUE" |

**Example**:
```ritz
import ritzlib.env

fn main(argc: i32, argv: **u8, envp: **u8) -> i32
    let path: *u8 = getenv(envp, "PATH")
    if path != null
        prints(path)
    0
```

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
| `json_parse2` | `fn(input: *u8, len: i64) -> Result<*JsonValue, JsonError>` | Parse JSON (modern) |
| `json_parse` | `fn(input: *u8, len: i64) -> JsonResult` | Parse JSON (legacy) |
| `json_free` | `fn(v: *JsonValue)` | Free JSON tree |

**Value Access**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `json_get_field` | `fn(obj: *JsonValue, key: *u8) -> *JsonValue` | Get object field |
| `json_get_index` | `fn(arr: *JsonValue, idx: i64) -> *JsonValue` | Get array element |
| `json_get_string` | `fn(v: *JsonValue) -> *u8` | Get string value |
| `json_get_number` | `fn(v: *JsonValue) -> i64` | Get number value |
| `json_get_bool` | `fn(v: *JsonValue) -> i32` | Get bool value |
| `json_is_null` | `fn(v: *JsonValue) -> i32` | Check if null |
| `json_array_len` | `fn(v: *JsonValue) -> i64` | Get array length |
| `json_object_len` | `fn(v: *JsonValue) -> i64` | Get object size |

**Serialization**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `json_emit_value` | `fn(v: *JsonValue, buf: *Vec<u8>) -> i32` | Emit to buffer |
| `json_emit_string` | `fn(s: *u8, buf: *Vec<u8>) -> i32` | Emit string |
| `json_to_string` | `fn(v: *JsonValue) -> *u8` | Convert to string |

**Error Messages**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `json_error_message` | `fn(code: i32) -> *u8` | Get error message |

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
struct ElfReader
    data: *u8
    size: i64
    ehdr: *Elf64_Ehdr
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

### meta

**Module**: `ritzlib.meta`

Module metadata parser for .ritz-meta JSON files (incremental compilation).

**Structures**: `ParamMeta`, `FnSignature`, `StructMeta`, `EnumMeta`, `ConstMeta`, `TypeAliasMeta`, `TraitMeta`, `ModuleMetadata`

| Function | Signature | Description |
|----------|-----------|-------------|
| `meta_alloc` | `fn() -> *ModuleMetadata` | Allocate metadata |
| `meta_free` | `fn(m: *ModuleMetadata)` | Free metadata |
| `meta_from_json` | `fn(json_str: *u8, len: i64) -> *ModuleMetadata` | Parse from JSON |
| `meta_load_file` | `fn(path: *u8) -> *ModuleMetadata` | Load from file |
| `meta_is_valid` | `fn(m: *ModuleMetadata, source_path: *u8) -> i32` | Check cache validity |
| `meta_find_function` | `fn(m: *ModuleMetadata, name: *u8) -> *FnSignature` | Find function |
| `meta_find_struct` | `fn(m: *ModuleMetadata, name: *u8) -> *StructMeta` | Find struct |
| `meta_find_enum` | `fn(m: *ModuleMetadata, name: *u8) -> *EnumMeta` | Find enum |
| `meta_find_constant` | `fn(m: *ModuleMetadata, name: *u8) -> *ConstMeta` | Find constant |
| `meta_find_type_alias` | `fn(m: *ModuleMetadata, name: *u8) -> *TypeAliasMeta` | Find type alias |
| `meta_find_trait` | `fn(m: *ModuleMetadata, name: *u8) -> *TraitMeta` | Find trait |

---

### testing

**Module**: `ritzlib.testing`

Native test framework.

**Architecture**:
1. Test files are compiled with `--no-runtime`
2. Build system reads .o symbol tables to find `test_*` functions
3. Build system generates registration stub
4. This module provides `_start` and test runner

```ritz
struct TestEntry
    name: *i8
    func: *u8
```

**Global State**:
- `g_tests: [1024]TestEntry`
- `g_test_count: i32`

**Functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `register_test` | `fn(name: *i8, func: *u8)` | Register a test |
| `run_all_tests` | `fn() -> i32` | Run all tests |

**Assertions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `assert_msg` | `fn(condition: i32, msg: *i8)` | Assert with message |
| `assert_eq_i64` | `fn(actual: i64, expected: i64, msg: *i8)` | Assert i64 equality |
| `assert_eq_i32` | `fn(actual: i32, expected: i32, msg: *i8)` | Assert i32 equality |
| `assert_not_null` | `fn(ptr: *u8, msg: *i8)` | Assert not null |
| `assert_null` | `fn(ptr: *u8, msg: *i8)` | Assert null |

**Example**:
```ritz
@test
fn test_addition() -> i32
    assert 1 + 1 == 2
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
import ritzlib.async_tasks # Async server
```

### Common Patterns

**Reading a file**:
```ritz
var content: String = string_new()
if read_file_string(&path, &content) == 0
    # use content
string_drop(&content)
```

**Creating a TCP server**:
```ritz
let fd: i32 = tcp_socket()
set_reuseaddr(fd)
tcp_bind(fd, 0, 8080)
tcp_listen(fd, 128)
let client: i32 = tcp_accept(fd)
```

**Using Vec**:
```ritz
var v: Vec<i32> = vec_new<i32>()
vec_push<i32>(&v, 42)
let val: i32 = vec_get<i32>(&v, 0)
vec_drop<i32>(&v)
```

**Async server with io_uring**:
```ritz
var srv: TaskServer
task_server_init(&srv, listen_fd)
task_server_run(&srv, handle_connection)
task_server_destroy(&srv)
```

---

*This documentation covers ritzlib as of February 2026. For the latest updates, refer to the source files in the `ritzlib/` directory.*
