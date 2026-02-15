# LARB Review Brief: Mausoleum Database Engine

**Project:** Mausoleum - A database server library written in Ritz
**Phase:** 1 Complete (Core Storage Engine)
**Date:** 2026-02-13
**Tests:** 150 passing (239ms)

---

## Overview

Mausoleum is a from-scratch database engine implementing:
- 4KB page-based storage with checksums
- LRU buffer pool with pin counting
- B+ tree indexing with node splitting
- Write-ahead logging (WAL) for durability
- ARIES-style crash recovery
- MVCC transactions with snapshot isolation

This review covers ~3,500 lines of Ritz code across 7 modules.

---

## Files to Review

| File | Lines | Purpose |
|------|-------|---------|
| `lib/m7m_types.ritz` | ~200 | Core types: PageId, LSN, TxnId, Span, error codes |
| `lib/page.ritz` | ~300 | 4KB page structure, headers, checksums |
| `lib/buffer_pool.ritz` | ~500 | LRU cache, frame management, dirty tracking |
| `lib/wal.ritz` | ~600 | Write-ahead log writer/reader |
| `lib/btree.ritz` | ~800 | B+ tree with variable-length keys |
| `lib/recovery.ritz` | ~400 | WAL replay, checkpoints |
| `lib/txn.ritz` | ~350 | MVCC transaction manager |

---

## Known Issues & Areas for Review

### 1. Memory Management

**Location:** All files
**Issue:** Manual malloc/free throughout. No RAII or defer patterns.

```ritz
# Example from buffer_pool.ritz
pub fn buffer_pool_new(num_frames: i32) -> *BufferPool
    let pool: *BufferPool = malloc(96) as *BufferPool
    if pool == null
        return null
    # ... more allocations ...
    # On error, must manually free everything allocated so far
```

**Questions for LARB:**
- Should Ritz have `defer` for cleanup?
- What's the idiomatic pattern for resource cleanup chains?
- Are there plans for RAII-style destructors?

---

### 2. Error Handling Verbosity

**Location:** All files
**Issue:** Every function has repetitive null checks and error propagation.

```ritz
# Example from txn.ritz - repeated pattern everywhere
pub fn txn_commit(txn: *Txn) -> i32
    if txn == null
        return ERR_INVALID
    if txn.state != TXN_ACTIVE
        return ERR_INVALID
    let mgr: *TxnManager = txn.mgr
    if mgr == null
        return ERR_INVALID
    # ... actual logic ...
```

**Questions for LARB:**
- Is there a Result type pattern coming?
- Should we use `?` operator for early returns?
- How do other Ritz projects handle this?

---

### 3. Struct Size Hardcoding

**Location:** `buffer_pool.ritz`, `recovery.ritz`, `txn.ritz`
**Issue:** Magic numbers for struct sizes in malloc calls.

```ritz
# From txn.ritz
let mgr: *TxnManager = malloc(128) as *TxnManager  # Why 128?
let active_size: i64 = MAX_ACTIVE_TXNS * 48  # sizeof(Txn) ~ 48 bytes
```

**Questions for LARB:**
- Is there a `sizeof()` operator?
- Should struct sizes be computed or defined as constants?
- What if struct layout changes?

---

### 4. PageId Type Confusion

**Location:** `m7m_types.ritz`, various callers
**Issue:** `PageId` is a struct wrapping `i64`, but many functions take raw `i64`.

```ritz
# In m7m_types.ritz
struct PageId
    value: i64

# But page_init takes i64 directly
pub fn page_init(page: *Page, magic: i32, page_id: i64)

# Callers must extract .value
var pid: PageId = page_id_new(0, 1)
page_init_heap(&test_page, pid.value)
```

**Questions for LARB:**
- Should we use `PageId` consistently everywhere?
- Or drop the struct wrapper entirely?
- Is there implicit conversion for single-field structs?

---

### 5. Visibility Function Complexity

**Location:** `lib/txn.ritz`, `txn_is_visible()` and `is_committed_before()`
**Issue:** MVCC visibility logic is complex and may have edge cases.

```ritz
pub fn txn_is_visible(txn: *Txn, write_ts: i64, delete_ts: i64) -> i32
    # Multiple conditions, negations, early returns
    # Hard to verify correctness
```

**Questions for LARB:**
- Is the visibility logic correct for all edge cases?
- Should we add more test cases for MVCC corner cases?
- Is there a cleaner way to express these rules?

---

### 6. For Loop Range Limitations

**Location:** `lib/btree.ritz`
**Issue:** Had to use `while` loops because Ritz only supports literal ranges.

```ritz
# This doesn't work:
# for i in mid..num_keys
#     ...

# Must use:
var i: i64 = mid
while i < num_keys
    # ...
    i += 1
```

**Questions for LARB:**
- Will computed range bounds be supported?
- Is there an iterator pattern we should use instead?

---

### 7. Boolean Type Usage

**Location:** `lib/txn.ritz`
**Issue:** Using `bool` type but returning `i32` for compatibility.

```ritz
# In txn_is_visible
let is_committed: bool = entry != null && entry.state == TXN_STATE_COMMITTED

# But function returns i32
pub fn txn_is_visible(txn: *Txn, write_ts: i64, delete_ts: i64) -> i32
```

**Questions for LARB:**
- Should boolean functions return `bool` or `i32`?
- What's the convention for predicate functions?

---

### 8. String Literals and C Interop

**Location:** All files
**Issue:** Using `c"string"` syntax for C-style null-terminated strings.

```ritz
let suffix: *u8 = c".wal.000000"
memcpy(&path_buf[base_len], suffix, 12)  # Magic number 12 = strlen + 1
```

**Questions for LARB:**
- Is there a `strlen()` that works at compile time?
- Should we have a `String` type for safer handling?
- What's the long-term plan for string handling in Ritz?

---

### 9. Test Helper Duplication

**Location:** `test/test_*.ritz`
**Issue:** Each test file has its own `make_test_path()` and `cleanup_test_files()`.

```ritz
# Repeated in test_recovery.ritz, test_txn.ritz, etc.
fn make_test_path(suffix: *u8) -> *u8
    var path: *u8 = malloc(64)
    let base: *u8 = c"/tmp/m7m_recovery_test_"
    # ...
```

**Questions for LARB:**
- Should we have a shared test utilities module?
- How do other Ritz projects handle test fixtures?

---

### 10. Buffer Pool Page ID Tracking

**Location:** `lib/buffer_pool.ritz`
**Issue:** The relationship between `Page*` and `page_id` requires extra lookup.

```ritz
# After allocating, must get ID separately
let page: *Page = buffer_pool_alloc(mgr.pool, PAGE_MAGIC_HEAP)
let alloc_page_id: i64 = buffer_pool_page_id(mgr.pool, page)
buffer_pool_unpin(mgr.pool, alloc_page_id, 1)
```

**Questions for LARB:**
- Should `buffer_pool_alloc` return both page and ID?
- Or should unpin take `*Page` directly?
- What's the cleanest API here?

---

## Architecture Questions

### A. Module Dependencies

Current dependency graph:
```
txn → wal → page → m7m_types
    ↘ buffer_pool ↗
recovery → wal
         ↘ buffer_pool
btree → buffer_pool → page
```

**Questions:**
- Is this dependency structure reasonable?
- Should there be a facade/engine module that ties everything together?

### B. Integration Testing

Currently all tests are unit tests per module.

**Questions:**
- Should we add integration tests that use multiple modules together?
- Example: Create B-tree, insert data, crash, recover, verify data?

### C. Public API Surface

Many internal functions are `pub` for testing.

**Questions:**
- Should we have a `pub(test)` visibility?
- How should internal vs external APIs be distinguished?

---

## Suggested Review Order

1. **`lib/m7m_types.ritz`** - Foundation types, review naming and design
2. **`lib/page.ritz`** - Page structure, checksum approach
3. **`lib/buffer_pool.ritz`** - Memory management, LRU correctness
4. **`lib/wal.ritz`** - Record format, durability guarantees
5. **`lib/btree.ritz`** - Algorithm correctness, edge cases
6. **`lib/recovery.ritz`** - ARIES implementation, crash safety
7. **`lib/txn.ritz`** - MVCC correctness, isolation level

---

## Running the Code

```bash
# Ensure submodules are initialized
git submodule update --init --recursive

# Create ritzlib symlink (points to main ritz repo)
ln -sf /home/aaron/dev/ritz-lang/ritz ritzlib

# Build and run tests
./build_tests.sh

# Expected output: 150 tests: 150 passed
```

---

## Notes for After Language Changes

This review should be revisited after upcoming Ritz language changes. Specific areas likely to change:

1. **Error handling** - If Result types or `?` operator added
2. **Memory management** - If RAII/defer patterns added
3. **Range expressions** - If computed bounds supported
4. **String handling** - If String type added

Please tag issues with `[PENDING-LANG]` if they depend on language features not yet available.

---

*Prepared by Adele for LARB review*
