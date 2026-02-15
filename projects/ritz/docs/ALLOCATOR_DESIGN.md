# Ritz Allocator Design

## Overview

This document specifies a jemalloc-inspired allocator for Ritz, designed to provide:
- Fast allocation/deallocation for common sizes
- Low fragmentation
- Simple interface hiding complexity from user code

## Goals

1. **Simple API** - `malloc(size) -> *u8`, `free(ptr)`, `realloc(ptr, new_size) -> *u8`
2. **No size tracking by caller** - Unlike mmap-based approach, caller doesn't need to remember allocation sizes
3. **Size class optimization** - Fast paths for common sizes (8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096 bytes)
4. **Large allocation fallback** - Direct mmap for >4KB allocations
5. **Ownership semantics** - Enable Vec and other containers to properly manage memory

## Design

### Size Classes

Following jemalloc's approach, allocations are binned by size class:

| Class | Size Range | Block Size | Blocks per 4KB Page |
|-------|------------|------------|---------------------|
| 0 | 1-8 | 8 | 512 |
| 1 | 9-16 | 16 | 256 |
| 2 | 17-32 | 32 | 128 |
| 3 | 33-64 | 64 | 64 |
| 4 | 65-128 | 128 | 32 |
| 5 | 129-256 | 256 | 16 |
| 6 | 257-512 | 512 | 8 |
| 7 | 513-1024 | 1024 | 4 |
| 8 | 1025-2048 | 2048 | 2 |
| 9 | 2049-4096 | 4096 | 1 |
| 10+ | >4096 | mmap direct | N/A |

### Data Structures

```ritz
# Block header (8 bytes, stored before each allocation)
# For size-class allocations: stores size class index
# For large allocations: stores actual size
struct BlockHeader
    size_or_class: i64   # If < NUM_SIZE_CLASSES: class index, else: actual size

# Free list node (embedded in free blocks)
struct FreeNode
    next: *FreeNode

# Size class bin
struct SizeBin
    free_list: *FreeNode  # Head of free list for this size class
    block_size: i64       # Size of blocks in this bin (including header)
    pages: *u8            # Current page(s) being carved from
    page_offset: i64      # Offset into current page
    page_cap: i64         # Total capacity of current pages

# Global allocator state
struct Allocator
    bins: [10]SizeBin     # One bin per size class
    initialized: i32      # Has init been called?
```

### Algorithm

**malloc(size):**
1. If size > 4096: mmap directly, store size in header
2. Else: find size class for requested size
3. If free list non-empty: pop from free list, return
4. Else: carve from page, if page exhausted: mmap new page

**free(ptr):**
1. Read header at (ptr - 8)
2. If size > 4096: munmap directly
3. Else: push to free list for that size class

**realloc(ptr, new_size):**
1. If ptr == null: return malloc(new_size)
2. Read old size from header
3. If new_size fits in same size class: return ptr (no-op)
4. Else: malloc(new_size), copy data, free(ptr)

### Memory Layout

```
[BlockHeader (8 bytes)][User Data (N bytes)]
^                      ^
|                      `-- returned pointer
`-- actual allocation start
```

For a 32-byte size class:
- BlockHeader: 8 bytes
- User data: 24 bytes usable (32 - 8)

This means size class 2 (32-byte blocks) handles allocations up to 24 bytes.

### Adjusted Size Classes

| Class | Block Size | Usable Size | Blocks per 4KB |
|-------|------------|-------------|----------------|
| 0 | 16 | 8 | 256 |
| 1 | 24 | 16 | 170 |
| 2 | 40 | 32 | 102 |
| 3 | 72 | 64 | 56 |
| 4 | 136 | 128 | 30 |
| 5 | 264 | 256 | 15 |
| 6 | 520 | 512 | 7 |
| 7 | 1032 | 1024 | 3 |
| 8 | 2056 | 2048 | 1 |
| 9+ | mmap | 2049+ | N/A |

### Initialization

The allocator auto-initializes on first use (lazy init). Global state is zero-initialized at startup.

## API

```ritz
import ritzlib.memory

# Core allocation
fn malloc(size: i64) -> *u8
fn free(ptr: *u8)
fn realloc(ptr: *u8, new_size: i64) -> *u8

# Convenience
fn calloc(count: i64, size: i64) -> *u8  # Zero-initialized
fn malloc_aligned(size: i64, align: i64) -> *u8  # Aligned allocation (future)
```

## Vec Integration

With proper free(), Vec can own its memory:

```ritz
struct Vec<T>
    data: *T
    len: i64
    cap: i64

fn vec_new<T>() -> Vec<T>
    var v: Vec<T>
    v.data = 0 as *T
    v.len = 0
    v.cap = 0
    return v

fn vec_drop<T>(v: *Vec<T>)
    if v.data != 0 as *T
        free(v.data as *u8)
    v.data = 0 as *T
    v.len = 0
    v.cap = 0

fn vec_push<T>(v: *Vec<T>, item: T)
    if v.len >= v.cap
        vec_grow(v)
    *(v.data + v.len) = item
    v.len = v.len + 1

fn vec_grow<T>(v: *Vec<T>)
    let new_cap: i64 = if v.cap == 0 then 8 else v.cap * 2
    let new_data: *T = realloc(v.data as *u8, new_cap * sizeof(T)) as *T
    v.data = new_data
    v.cap = new_cap
```

## Implementation Notes

1. **Thread safety** - Single-threaded for now; add locks or thread-local bins later
2. **Fragmentation** - Size classes minimize internal fragmentation
3. **Page retention** - Don't immediately munmap freed pages; reuse in future allocations
4. **Debug mode** - Add guards, fill patterns, double-free detection (future)

## Testing Strategy

1. **Unit tests** - Each size class, edge cases, realloc scenarios
2. **Stress tests** - Many allocations/frees, random patterns
3. **Integration** - Use in Vec, then in ritz1 parser

## Migration Path

1. Implement allocator in ritzlib/memory.ritz
2. Add tests using @test functions
3. Update Vec to use malloc/free instead of mmap
4. Update ritz1 parser to use Vec/malloc
5. Remove heap_base/heap_offset pattern from ritz1
