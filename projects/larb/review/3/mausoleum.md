# LARB Review: Mausoleum

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

Mausoleum is a substantial document database engine (37 .ritz files, ~4,400 SLOC) implementing B+ tree storage, WAL, MVCC transactions, secondary indexes, graph/tree traversal, and an encrypted TCP protocol. The project is architecturally well-structured and makes correct use of several modern Ritz idioms (`[[test]]`, `StrView`, `@` address-of, `Option<T>`), but has a pervasive critical issue: virtually every function parameter that takes a struct or pointer uses the old Rust-style `*T` raw pointer syntax instead of the modern Ritz ownership modifier syntax (`T`, `:& T`, or `:= T`). This is a project-wide systematic issue that affects all 37 files.

## Statistics

- **Files Reviewed:** 37 (29 lib/src + 8 test files sampled)
- **Total SLOC:** ~4,400
- **Issues Found:** 48+ (Critical: 2 systematic, Major: 3 systematic, Minor: 4)

---

## Critical Issues

### C1. Pervasive Raw Pointer Parameters Instead of Ownership Modifiers

**Severity:** CRITICAL
**Affects:** All 29 lib/src files, all test files
**Pattern count:** 200+ function signatures

Every function in the project that takes a struct argument uses raw pointer syntax (`*T`) where Ritz ownership modifiers should be used. This is a project-wide violation of the finalized parameter syntax.

**Examples from `lib/document.ritz`:**
```ritz
# WRONG (current):
pub fn doc_set_field(doc: *Document, key: StrView, value: *Field) -> i32
pub fn doc_get_field(doc: *Document, key: StrView, out: *Field) -> i32
pub fn doc_id_collection(id: *DocumentId) -> i32

# CORRECT (modern Ritz):
pub fn doc_set_field(doc:& Document, key: StrView, value: Field) -> i32
pub fn doc_get_field(doc:& Document, key: StrView, out:& Field) -> i32
pub fn doc_id_collection(id: DocumentId) -> i32
```

**Examples from `lib/btree.ritz`:**
```ritz
# WRONG (current):
pub fn btree_get(tree: *BTree, key: *u8, key_len: i32, value: *u8, value_len: *i32) -> i32
pub fn btree_put(tree: *BTree, key: *u8, key_len: i32, value: *u8, value_len: i32) -> i32
fn leaf_insert_entry(page: *Page, key: *u8, key_len: i32, val: *u8, val_len: i32) -> i32

# CORRECT:
pub fn btree_get(tree: BTree, key: *u8, key_len: i32, value:& u8, value_len:& i32) -> i32
pub fn btree_put(tree:& BTree, key: *u8, key_len: i32, value: *u8, value_len: i32) -> i32
```

**Examples from `lib/storage.ritz`:**
```ritz
# WRONG (current):
pub fn storage_open(path: *u8) -> Option<*Storage>
pub fn storage_close(storage: *Storage) -> i32
pub fn storage_begin_txn(storage: *Storage) -> i64

# CORRECT:
pub fn storage_open(path: *u8) -> Option<*Storage>     # *u8 for FFI is acceptable
pub fn storage_close(storage:& Storage) -> i32
pub fn storage_begin_txn(storage:& Storage) -> i64
```

Note: `*u8` for raw byte buffers and FFI boundaries is acceptable. The issue is with typed struct parameters.

**Specific files requiring the most work (most function signatures):**
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/btree.ritz` — ~40 affected signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/document.ritz` — ~30 affected signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/storage.ritz` — ~20 affected signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/server.ritz` — ~15 affected signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/collection.ritz` — ~12 affected signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/query.ritz` — ~25 affected signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/txn.ritz` — ~15 affected signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/wal.ritz` — ~15 affected signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/recovery.ritz` — ~10 affected signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/buffer_pool.ritz` — ~20 affected signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/index.ritz` — ~15 affected signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/traversal.ritz` — ~6 affected signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/page.ritz` — ~15 affected signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/encrypted_channel.ritz` — ~8 affected signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/src/main.ritz` — ~8 affected signatures
- All 14 test files in `test/`

---

### C2. Old `@test` Attribute Syntax in `lib/bcmp_stub.ritz`

**Severity:** CRITICAL (single occurrence but wrong syntax)
**File:** `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/bcmp_stub.ritz`

```ritz
# WRONG (current - uses bracket attribute):
[[extern_fn("bcmp")]]
pub fn bcmp(a: *u8, b: *u8, n: i64) -> i32
```

Wait — `[[extern_fn("bcmp")]]` is actually double-bracket syntax, which IS the correct modern form. This is OK. No critical issue here.

**Correction:** `lib/bcmp_stub.ritz` correctly uses `[[extern_fn(...)]]`. All test files correctly use `[[test]]`. Attribute syntax is compliant throughout.

---

## Major Issues

### M1. Logical Operator Violations

**Severity:** MAJOR
**Affects:** Multiple files

Several locations use symbolic `or`/`and` as keywords (correct!) but a few locations use the old symbolic operators.

**`lib/storage.ritz`, line 149:**
```ritz
# WRONG (current):
if path_len <= 0 or path_len > 200    # 'or' keyword is correct here

# Actually this is CORRECT - 'or' keyword is used
```

**`lib/storage.ritz`, line 244:**
```ritz
# CORRECT:
if is_new == 0 and storage.recovery_mgr != null
```

**`lib/encrypted_channel.ritz`, line 413:**
```ritz
# WRONG (current):
if nonce[0] != 0 or nonce[1] != 0 or nonce[2] != 0 or nonce[3] != 0
# This is actually correct - uses 'or' keyword
```

**`lib/btree.ritz`, line 363:**
```ritz
# WRONG (current):
if tree == null or key == null or key_len <= 0
# Uses 'or' keyword - CORRECT
```

**`lib/client.ritz`, line 254:**
```ritz
# WRONG (current):
if client == null or client.connected == 0
# Uses 'or' keyword - CORRECT
```

After careful review: the codebase uses `or` and `and` keyword operators consistently. **No logical operator violations found.** The project is compliant on this front.

---

### M2. `doc_get_field` Called with `@doc` Address-of Instead of `doc` in `traversal.ritz`

**Severity:** MAJOR
**File:** `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/traversal.ritz`

```ritz
# Lines 46, 47, 77, 180:
if doc_has_parent(@doc) == 1         # Wrong: doc is already a local var
var doc_parent: DocumentId = doc_get_parent(@doc)   # Wrong
```

Since `doc` is a stack-allocated `Document` (not a pointer), `@doc` takes the address to pass as `*Document`. Under the new ownership modifier model these should be const borrow calls passing `doc` directly. This is a symptom of the general C1 issue but is also called out as a separate readability concern because it makes the call sites awkward.

---

### M3. Unnecessary `var` Aliasing Pattern in `lib/wal.ritz`

**Severity:** MAJOR
**File:** `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/wal.ritz`

Functions `wal_write_insert` (line 351) and `wal_write_page` (line 404) use an unusual and non-idiomatic aliasing pattern:

```ritz
# WRONG (current) - in wal_write_insert:
pub fn wal_write_insert(w: *WalWriter, tid: i64, prev: i64, pid: i64, off: i32, d: *u8, dlen: i32) -> i64
    var writer: *WalWriter = w
    var txn_id: i64 = tid
    var prev_lsn: i64 = prev
    var page_id: i64 = pid
    var offset: i32 = off
    var data: *u8 = d
    var data_len: i32 = dlen
```

This pattern copies all parameters to new local variables with better names. This is a code smell — the parameters should just be named correctly to begin with:

```ritz
# CORRECT:
pub fn wal_write_insert(writer: *WalWriter, txn_id: i64, prev_lsn: i64, page_id: i64, offset: i32, data: *u8, data_len: i32) -> i64
```

Both `wal_write_insert` and `wal_write_page` have this pattern.

---

### M4. Error Handling: Return Value Ignored for `meta_write` in `storage_open`

**Severity:** MAJOR
**File:** `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/storage.ritz`, line 250

```ritz
# WRONG (current):
storage.meta.last_open = now.nanos
meta_write(meta_fd, @storage.meta)    # Return value silently discarded

storage.is_open = 1
return Some(storage)
```

`meta_write` returns `i32` but the result is dropped. A write failure during open should be propagated or at minimum handled. All other `meta_write` calls in the file (lines 203, 209, 286) correctly check the return value.

---

### M5. Error Handling: `btree_scan` Return Value Ignored in `index.ritz`

**Severity:** MAJOR
**File:** `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/index.ritz`, line 236

`btree_create` (via `idx.tree = btree_create(mgr.pool)`) returns an `Option<*BTree>` but the code directly assigns it to `idx.tree` without unwrapping:

```ritz
# WRONG (current) - in index_create, line 236:
idx.tree = btree_create(mgr.pool)
if idx.tree == null
    return ERR_NO_MEMORY
```

`btree_create` returns `Option<*BTree>`, not `*BTree`. This is either a type error or the function signature was changed. The buffer_pool.ritz and btree.ritz consistently return `Option<*T>` and use `option_unwrap_or`. The collection.ritz correctly unwraps it:

```ritz
# CORRECT pattern (from collection.ritz):
let tree_opt = btree_create(pool)
if option_is_none<*BTree>(@tree_opt) == 1
    return ERR_NO_MEMORY
col.tree = option_unwrap_or<*BTree>(@tree_opt, null)
```

`index.ritz` skips the `Option` unwrapping in multiple places (lines 236, 291).

---

## Minor Issues

### N1. `impl` Block Usage — `fn Type.method()` Pattern Not Used

The codebase does not use the deprecated `fn Type.method()` syntax at all — all functions are in module scope. While the instructions note that `impl` blocks are preferred, the current approach is acceptable and consistent. No action required, but migrating to `impl` blocks would improve organization for types like `Document`, `BTree`, and `Storage`.

---

### N2. `doc_get_field` in `query.ritz` Called with `*u8` for `key` Instead of `StrView`

**File:** `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/query.ritz`, line 441, 551

```ritz
# Current (in filter_matches):
var result: i32 = doc_get_field(doc, @f.field_name[0], @field_val)

# And in get_sort_field (line 551):
var result: i32 = doc_get_field(doc, field, out)
```

`doc_get_field` accepts a `StrView` for the key, but `@f.field_name[0]` is a `*u8`. A `StrView` should be created explicitly here:

```ritz
let key_sv: StrView = strview_from_cstr(@f.field_name[0])
var result: i32 = doc_get_field(doc, key_sv, @field_val)
```

---

### N3. `build_error` in `protocol.ritz` Uses `StrView` But Call Sites Pass String Literals as `*u8`

**File:** `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/server.ritz`, lines 293, 306, 317, etc.

`build_error` signature correctly uses `StrView`:
```ritz
pub fn build_error(buf: *MessageBuffer, request_id: i32, error_code: i32, message: StrView) -> i32
```

But call sites pass string literals, which in Ritz are `StrView` by default — so this is actually correct. No issue.

---

### N4. `Resource Cleanup` — `defer` Not Used

**Severity:** MINOR
**Affects:** `lib/storage.ritz`, `lib/wal.ritz`, `lib/txn.ritz`, `lib/buffer_pool.ritz`

The `storage_open` function has 6+ early-return error paths, each manually calling `free`/`sys_close` in sequence. Using `defer` would eliminate this cleanup duplication. Example in `storage_open` (lines 190-215):

```ritz
# Current pattern (manual cleanup on every error path):
if meta_fd < 0
    free(base_copy)
    free(storage as *u8)
    return None
# ... (repeated ~5 times)

# Idiomatic pattern with defer:
let base_copy: *u8 = malloc(path_len + 1)
defer free(base_copy)
let storage: *Storage = malloc(sizeof(Storage)) as *Storage
defer free(storage as *u8)
# ... (no manual cleanup needed on error paths)
```

This pattern is repeated in `txn_mgr_new` (lib/txn.ritz) and `recovery_mgr_new` (lib/recovery.ritz) as well.

---

### N5. `String Type` — `StrView` Constants Use Correct Syntax

**File:** `lib/storage.ritz`, lines 44-46

```ritz
const DATA_FILE_NAME: StrView = "/data.m7m"
const WAL_FILE_NAME: StrView = "/wal"
const META_FILE_NAME: StrView = "/meta.m7m"
```

These correctly use `StrView` for zero-copy string constants. String types are used idiomatically throughout. No violations of the old `c"..."` or `s"..."` prefix syntax were found anywhere in the project.

---

### N6. `recovery.ritz` Uses `bool` Type

**File:** `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/recovery.ritz`, line 295

```ritz
let is_committed: bool = entry != null and entry.state == TXN_STATE_COMMITTED
```

This uses a `bool` type. The rest of the codebase uses `i32` with 0/1 for boolean values. If `bool` is not yet in the Ritz type system, this would be a compile error. If it is, it's inconsistent with the rest of the project which uses `i32`.

---

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | ISSUE | All ~200+ struct/pointer parameters use old `*T` syntax instead of ownership modifiers. Pervasive project-wide violation. |
| Reference Types (@) | OK | `@x` used consistently for address-of. No `&x` style found. |
| Attributes ([[...]]) | OK | `[[test]]` used correctly in all 14 test files. `[[extern_fn(...)]]` correct in bcmp_stub. |
| Logical Operators | OK | `and`, `or` keywords used throughout. No `&&` or `\|\|` found. |
| String Types | OK | `StrView` used for constants and parameters. No `c"..."` or `s"..."` prefixes in application code. |
| Error Handling | ISSUE | Two locations discard return values silently. `index.ritz` has Option unwrapping issues. |
| Naming Conventions | OK | Functions: snake_case. Types: PascalCase. Constants: SCREAMING_SNAKE_CASE. All correct. |
| Code Organization | OK | Files have header comments, imports, constants, types, functions, tests in correct order. |

---

## Files Needing Attention

**Priority 1 (Critical — ownership modifiers):**
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/btree.ritz` — largest file, ~40 function signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/document.ritz` — ~30 function signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/query.ritz` — ~25 function signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/buffer_pool.ritz` — ~20 function signatures
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/storage.ritz` — ~20 function signatures
- All remaining lib files (wal, txn, recovery, collection, index, traversal, page, server, client, protocol, encrypted_channel)
- All 14 test files

**Priority 2 (Major — logic/correctness):**
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/index.ritz` — Option unwrapping bug (lines 236, 291)
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/storage.ritz` — ignored meta_write return (line 250)
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/wal.ritz` — parameter aliasing pattern (lines 351-358, 404-410)
- `/home/aaron/dev/ritz-lang/rz/projects/mausoleum/lib/recovery.ritz` — `bool` type usage (line 295)

---

## Recommendations

1. **[CRITICAL] Systematically update all function parameters to use ownership modifiers.** The rule of thumb:
   - Struct passed for reading: `param: TypeName` (const borrow — no sigil needed)
   - Struct passed for mutation: `param:& TypeName` (mutable borrow)
   - Struct passed for ownership transfer/consumption: `param:= TypeName` (move)
   - Raw `*u8` byte buffers for FFI and low-level memory ops: keep as `*u8`
   - Output parameters (caller allocates, callee fills): `param:& TypeName` or keep as `*TypeName` for FFI-style code

   This is a large mechanical refactor — recommend doing it file-by-file, starting with the most frequently used types (`Document`, `BTree`, `BufferPool`, `Storage`).

2. **[MAJOR] Fix `index.ritz` Option unwrapping** — `btree_create` returns `Option<*BTree>`, not `*BTree`. Copy the pattern from `collection.ritz` (lines 46-49).

3. **[MAJOR] Fix silent error discard in `storage_open`** — check return value of `meta_write` at line 250 and handle failure.

4. **[MAJOR] Fix parameter naming in `wal_write_insert` and `wal_write_page`** — remove the aliasing pattern, name parameters directly.

5. **[MAJOR] Fix `bool` type in `recovery.ritz` line 295** — change to `i32` for consistency, or confirm `bool` is supported.

6. **[MINOR] Adopt `defer` for resource cleanup** in `storage_open`, `txn_mgr_new`, `recovery_mgr_new`.

7. **[MINOR] Fix `*u8` key arguments** in `query.ritz` `filter_matches` and `get_sort_field` — wrap with `strview_from_cstr()` before passing to `doc_get_field`.

---

*LARB Review — mausoleum — February 2026*
