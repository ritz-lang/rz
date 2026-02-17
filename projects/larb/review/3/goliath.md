# LARB Review: Goliath

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** CRITICAL

## Summary

Goliath is a content-addressable filesystem/VFS library implementing SHA-256-addressed blob storage with a path namespace layer and VirtIO persistent storage backend. The codebase shows strong use of `[[test]]` attributes and `and`/`not` logical operators, but has pervasive critical issues: raw pointer types (`*T`) are used throughout all application-layer function signatures where ownership modifiers (`@T`, `@&T`) should be used, and the test suite contains old `c"..."` string prefix syntax that must be replaced.

## Statistics

- **Files Reviewed:** 13 (8 src, 5 test)
- **Total SLOC:** ~850
- **Issues Found:** 31 (Critical: 12, Major: 9, Minor: 10)

## Critical Issues

### C1 - Pervasive `*T` parameters in non-FFI application code

Every module uses raw pointer types (`*T`) for function parameters that are not FFI boundaries. Per the Ritz spec, `*T` is reserved for FFI/unsafe contexts. Application-layer functions that take a read-only view should use `@T` (immutable reference type), and functions that mutate should use `@&T` (mutable reference type). This affects dozens of signatures across the project.

**blob_id.ritz** (lines 73, 82, 91, 95, 104):
```ritz
# WRONG - raw pointers in pure application logic
pub fn blob_id_eq(a: *BlobId, b: *BlobId) -> bool
pub fn blob_id_is_zero(id: *BlobId) -> bool
pub fn blob_id_bytes(id: *BlobId) -> *u8
pub fn blob_id_compute(data: *u8, len: u64) -> BlobId
pub fn blob_id_copy(src: *BlobId) -> BlobId

# CORRECT
pub fn blob_id_eq(a: @BlobId, b: @BlobId) -> bool
pub fn blob_id_is_zero(id: @BlobId) -> bool
pub fn blob_id_copy(src: @BlobId) -> BlobId
```

**path.ritz** (line 149):
```ritz
# WRONG - iterator mutation via raw pointers
pub fn path_iter_next(iter: *PathIter, out: *StrView) -> bool

# CORRECT - mutable borrows for mutation, regular borrow for output
pub fn path_iter_next(iter:& PathIter, out:& StrView) -> bool
```

**namespace.ritz** - All top-level public functions take `*Namespace`:
```ritz
# WRONG
pub fn namespace_new(store: *MemoryBlobStore) -> Namespace
pub fn namespace_resolve(ns: *Namespace, path: @StrView) -> BlobId
pub fn namespace_exists(ns: *Namespace, path: @StrView) -> bool
pub fn namespace_read(ns: *Namespace, path: @StrView) -> Span<u8>
pub fn namespace_write(ns: *Namespace, path: @StrView, data: @Span<u8>) -> ErrorCode
pub fn namespace_mkdir(ns: *Namespace, path: @StrView) -> ErrorCode
pub fn namespace_list(ns: *Namespace, path: @StrView, entries: *DirEntry, max_entries: i32) -> i32

# CORRECT
pub fn namespace_new(store:& MemoryBlobStore) -> Namespace
pub fn namespace_resolve(ns: @Namespace, path: @StrView) -> BlobId
pub fn namespace_exists(ns: @Namespace, path: @StrView) -> bool
pub fn namespace_read(ns: @Namespace, path: @StrView) -> Span<u8>
pub fn namespace_write(ns:& Namespace, path: @StrView, data: @Span<u8>) -> ErrorCode
pub fn namespace_mkdir(ns:& Namespace, path: @StrView) -> ErrorCode
pub fn namespace_list(ns: @Namespace, path: @StrView, entries:& DirEntry, max_entries: i32) -> i32
```

**dir_entry.ritz** (lines 34, 60, 86, 90, 94, 102, 124, 161):
```ritz
# WRONG
pub fn dir_entry_file(name: @StrView, blob_id: *BlobId, size: u64) -> DirEntry
pub fn dir_entry_is_file(entry: *DirEntry) -> bool
pub fn dir_entry_is_dir(entry: *DirEntry) -> bool
pub fn dir_entry_name(entry: *DirEntry) -> StrView
pub fn dir_entry_name_eq(entry: *DirEntry, name: @StrView) -> bool
pub fn dir_entry_serialize(entry: *DirEntry, out: *u8)
pub fn dir_entry_deserialize(data: *u8) -> DirEntry

# CORRECT
pub fn dir_entry_file(name: @StrView, blob_id: @BlobId, size: u64) -> DirEntry
pub fn dir_entry_is_file(entry: @DirEntry) -> bool
pub fn dir_entry_is_dir(entry: @DirEntry) -> bool
pub fn dir_entry_name(entry: @DirEntry) -> StrView
pub fn dir_entry_name_eq(entry: @DirEntry, name: @StrView) -> bool
pub fn dir_entry_serialize(entry: @DirEntry, out: *u8)   # out: *u8 is acceptable - raw write buffer
```

**blob_store.ritz** - Legacy API wrappers (lines 267-296): All take `*MemoryBlobStore` and `*BlobId` where `@` types should be used.

### C2 - Old `c"..."` string prefix syntax in tests

**test_namespace.ritz** (lines 166, 213, 214, 236):
```ritz
# WRONG - old c"..." prefix
let file_data: Span<u8> = span_from_ptr<u8>(c"data", 4)
let rel_data: Span<u8> = span_from_ptr<u8>(c"x", 1)
let data: Span<u8> = span_from_ptr<u8>(c"x", 1)

# CORRECT - use .as_cstr() or pass a string literal directly
let file_data: Span<u8> = span_from_ptr<u8>("data".as_cstr(), 4)
```

Note: There are 4 occurrences on lines 166, 213, 214, and 236.

## Major Issues

### M1 - Flag combination using `+` instead of `or`/`|`

`PROT_READ + PROT_WRITE` and `MAP_PRIVATE + MAP_ANONYMOUS` use arithmetic addition to combine bitmask constants. While this happens to produce the correct value for these specific constants, it is semantically incorrect and misleading. Bitwise OR should be used for flag combination.

**blob_store.ritz** (lines 114-115, 196-197):
```ritz
# WRONG - arithmetic addition of flags
let prot: i32 = PROT_READ + PROT_WRITE
let flags: i32 = MAP_PRIVATE + MAP_ANONYMOUS

# CORRECT - bitwise OR
let prot: i32 = PROT_READ or PROT_WRITE
let flags: i32 = MAP_PRIVATE or MAP_ANONYMOUS
```

This pattern appears in: `blob_store.ritz` (3 occurrences), `namespace.ritz` (1 occurrence), `virtio_store.ritz` (2 occurrences). Total: 6 occurrences across 3 files.

### M2 - `fn Type.method()` style not used; missing `impl` blocks

All functions are module-level free functions. While the instructions note this is "deprecated but tolerated," the namespace/blob_store/dir_entry types are mature enough that grouping methods under `impl` blocks would significantly improve readability. This is particularly true for `MemoryBlobStore` which has 9 associated functions.

Recommended for: `BlobId`, `MemoryBlobStore`, `Namespace`, `DirEntry`, `PathIter`.

### M3 - Missing `defer` for resource cleanup in test functions

Test functions in `test_blob_store.ritz` and `test_namespace.ritz` call `memory_store_free(@store)` at every early return and at the end of the function instead of using `defer`. This creates maintenance risk (a missed free on a new early return path).

**test_blob_store.ritz** (e.g. `test_store_get_retrieves`, lines 45-78):
```ritz
# WRONG - manual cleanup at multiple return points
fn test_store_get_retrieves() -> i32
    var store: MemoryBlobStore = memory_store_new()
    # ... 4 separate memory_store_free(@store) calls ...

# CORRECT
fn test_store_get_retrieves() -> i32
    var store: MemoryBlobStore = memory_store_new()
    defer memory_store_free(@store)
    # ... single path, no manual frees needed ...
```

This affects all 6 test functions in `test_blob_store.ritz` and 8 test functions in `test_namespace.ritz`.

### M4 - Namespace struct stores `*MemoryBlobStore` as raw pointer

**namespace.ritz** (line 20-22):
```ritz
pub struct Namespace
    store: *MemoryBlobStore   # raw pointer - should be typed reference
    root: BlobId
```

The `store` field being `*MemoryBlobStore` breaks the ownership model. The struct should either own the store (`:= MemoryBlobStore`) or hold a reference (`@&MemoryBlobStore`). As currently written there is no ownership clarity.

### M5 - BlobStoreOps vtable uses erased `*u8` self pointer pattern

**blob_store.ritz** (lines 27-36): The vtable pattern erases the concrete type to `*u8`. While necessary for polymorphism before traits are finalized, the internal `_impl` functions (lines 151-260) that take `self: *u8` and immediately cast to `*MemoryBlobStore` should at minimum be documented as unsafe and grouped in an `unsafe` block.

### M6 - `path.ritz` functions accept `@StrView` but internally dereference with `*` operator

**path.ritz** (lines 14-15):
```ritz
pub fn path_is_absolute(path: @StrView) -> bool
    path.len > 0 and *(path.ptr) == PATH_SEP
```

The `*(path.ptr)` dereference is a raw pointer dereference on `StrView.ptr`. The `@StrView` borrow correctly gives an immutable reference to the StrView, but the raw pointer dereference inside is unsafe. This pattern repeats throughout `path.ritz`. These derefs should be encapsulated behind a `strview_get_byte()` accessor from ritzlib rather than inline raw dereferences.

### M7 - `path_iter_new` and `path_iter_next` are not exported from `main.ritz`

**src/main.ritz** (line 24): The `path` module re-export only exports `path_is_absolute`, `path_is_root`, `path_validate` - it does not export `PathIter`, `path_iter_new`, or `path_iter_next`. However, these are used extensively in `namespace.ritz` (via direct import). The re-export should be complete.

### M8 - `namespace_write` does not return the result of `update_dir_entry`

**namespace.ritz** (line 161):
```ritz
# Missing return keyword - implicitly falls through to update_dir_entry's return
update_dir_entry(ns, @parent_id, @base_name, @file_id, data.len as u64, false)
```

The function signature is `-> ErrorCode` but the final expression is the call to `update_dir_entry` without `return`. This may be intentional (last expression as return value) but is inconsistent with the explicit `return ERR_INVALID_PATH` etc. earlier in the same function. Use explicit `return` for clarity.

Same issue in `namespace_mkdir` (line 201).

### M9 - `blob_id.ritz` imports `ritzlib.sys { write }` but never uses it

**blob_id.ritz** (line 6):
```ritz
import ritzlib.sys { write }   # UNUSED - remove this import
```

Same dead import in `error.ritz` (line 5): `import ritzlib.sys { write }` - never used.

## Minor Issues

### N1 - `error.ritz` uses i32 constants instead of an enum ADT

The error module defines 12 separate `pub const ERR_*: i32` constants and a `type ErrorCode = i32` alias. An enum ADT would be more idiomatic and type-safe:
```ritz
pub enum FsError
    Ok
    NotFound
    AlreadyExists
    InvalidPath
    # ...
```

The comment "as constants since ritz enums are ADTs" suggests this was a workaround - if ADT enums are now available, this should be migrated.

### N2 - Magic number comment is misleading

**virtio_store.ritz** (line 38):
```ritz
pub const GOLIATH_MAGIC: u64 = 0x0048544149494C4F  # "OLIATH\0\0" - adjust as needed
```

The comment says "adjust as needed" next to a magic number constant - magic numbers should be fixed. Also the comment says `"OLIATH\0\0"` but the field is supposed to be `"GOLIATH\0"`. The value appears incorrect and the comment acknowledges this.

### N3 - `ENTRY_SYMLINK` constant defined but symlinks not implemented

**dir_entry.ritz** (line 12): `pub const ENTRY_SYMLINK: u8 = 2` is defined but no symlink-related functions exist and `EntryKind` in the DirEntry struct never uses it. Either implement symlinks or remove the constant.

### N4 - Hardcoded struct size assumptions

**blob_store.ritz** (line 110): `let entry_size: u64 = 56  # sizeof(BlobEntry) - approximate`

The comment itself says "approximate." This is fragile. The actual size depends on compiler alignment decisions. If Ritz provides a `sizeof()` builtin it should be used; otherwise this should be a compile-time assertion.

Similarly in `memory_store_free_impl` (line 253): same hardcoded `56`.

### N5 - `namespace.ritz` uses `not` correctly but inconsistently

Most boolean negation uses `not` (correct), but some numeric comparisons that could use `not` instead use `!= 0` or `== 0` idioms. This is acceptable but slightly inconsistent.

### N6 - `dir_serialized_size` uses a magic `320` with only a comment

**dir_entry.ritz** (line 121):
```ritz
pub fn dir_serialized_size(entry_count: u32) -> u64
    4 + (entry_count as u64 * 320)  # sizeof(DirEntry) ~ 320 bytes
```

The `320` is the assumed serialized size of `DirEntry`, but it is hardcoded and marked approximate (`~`). A constant `ENTRY_SERIALIZED_SIZE: u64 = 320` should be defined and referenced.

### N7 - Test file `test_blob_id.ritz` has no imports for ritzunit/[[test]] harness

**test_blob_id.ritz** (line 1-5): There is no import of a test harness. The `[[test]]` attribute works, but it is unclear how test results are reported. Other test files (`test_main.ritz`) import `ritzlib.sys { write }` - the pattern should be consistent.

### N8 - `VirtIOBlobStore` `virtio_store_new` uses `@store` to pass address of local variable

**virtio_store.ritz** (line 166):
```ritz
virtio_store_format(@store)
```

`store` is a local `VirtIOBlobStore` (value type) and `@store` takes its address. This is correct usage of `@`, but the function `virtio_store_format` takes `*VirtIOBlobStore` - mixing `@` address-of with raw pointer receipt is the very inconsistency the ownership system is meant to resolve. `virtio_store_format` should accept `@&VirtIOBlobStore`.

### N9 - Module code organization is inverted in `blob_store.ritz`

The "Legacy API" section (lines 262-297) comes after the implementation functions. Per the code organization guidelines, the public API should come before internal implementation details. The vtable setup functions should be at the bottom, not the middle.

### N10 - `test_namespace.ritz` passes `@store` where `*MemoryBlobStore` is expected

**test_namespace.ritz** (line 15):
```ritz
let ns: Namespace = namespace_new(@store)
```

`namespace_new` takes `*MemoryBlobStore`. `@store` produces `@MemoryBlobStore` (immutable ref). These are different types. This pattern appears throughout tests and in `namespace.ritz` itself. The type mismatch is a symptom of the pervasive C1 issue - once C1 is fixed (moving to `@` types), the call sites will naturally align.

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | ISSUE | `*T` used pervasively in application code; `:&` and `:=` never used in function params |
| Reference Types (@) | ISSUE | `@` used correctly at call sites but function signatures take `*T` instead of `@T`/`@&T` |
| Attributes ([[...]]) | OK | `[[test]]` used correctly throughout all test files; no old `@test` syntax found |
| Logical Operators | OK | `and`, `or`, `not` used consistently; no `&&`, `||`, `!` found |
| String Types | ISSUE | `c"..."` prefix used in test_namespace.ritz (4 occurrences); should be `"...".as_cstr()` |
| Error Handling | ISSUE | No `?` operator used; no `Result<T,E>` return types; raw `i32` error codes throughout |
| Naming Conventions | OK | snake_case functions, PascalCase types, SCREAMING_SNAKE constants - all correct |
| Code Organization | ISSUE | No `impl` blocks; legacy API ordering in blob_store; dead imports |

## Files Needing Attention

| File | Priority | Issues |
|------|----------|--------|
| `/home/aaron/dev/ritz-lang/rz/projects/goliath/src/blob_id.ritz` | CRITICAL | All public functions use `*BlobId` instead of `@BlobId`; dead import |
| `/home/aaron/dev/ritz-lang/rz/projects/goliath/src/namespace.ritz` | CRITICAL | All public functions use `*Namespace`, `*MemoryBlobStore`; flag arithmetic |
| `/home/aaron/dev/ritz-lang/rz/projects/goliath/src/dir_entry.ritz` | CRITICAL | All public functions use `*DirEntry`, `*BlobId`; hardcoded size magic |
| `/home/aaron/dev/ritz-lang/rz/projects/goliath/src/blob_store.ritz` | CRITICAL | Vtable params as `*u8` (acceptable for FFI-style vtable), but legacy API wrappers should use `@`; flag arithmetic |
| `/home/aaron/dev/ritz-lang/rz/projects/goliath/test/test_namespace.ritz` | CRITICAL | 4 uses of old `c"..."` syntax |
| `/home/aaron/dev/ritz-lang/rz/projects/goliath/src/path.ritz` | MAJOR | `path_iter_next` uses raw `*PathIter`, `*StrView`; internal unsafe derefs need encapsulation |
| `/home/aaron/dev/ritz-lang/rz/projects/goliath/src/virtio_store.ritz` | MAJOR | Flag arithmetic; `@store` passed to `*` param function |
| `/home/aaron/dev/ritz-lang/rz/projects/goliath/src/error.ritz` | MAJOR | Dead import; i32 constants instead of enum ADT |
| `/home/aaron/dev/ritz-lang/rz/projects/goliath/test/test_blob_store.ritz` | MAJOR | No `defer` for cleanup; 14 manual free calls at early return points |
| `/home/aaron/dev/ritz-lang/rz/projects/goliath/test/test_namespace.ritz` | MAJOR | No `defer` for cleanup; 16 manual free calls |

## Recommendations

### Priority 1 (CRITICAL - must fix before merge)

1. **Replace all `*T` application-layer function parameters** with `@T` (immutable) or `@&T` (mutable). This is the largest change but most important. Start with `blob_id.ritz` as it is foundational, then `dir_entry.ritz`, `namespace.ritz`, and the blob_store legacy wrappers.

2. **Remove all `c"..."` string prefixes** in `test_namespace.ritz` (4 occurrences, lines 166, 213, 214, 236). Replace with `"...".as_cstr()`.

### Priority 2 (MAJOR - fix before next review cycle)

3. **Replace flag arithmetic with bitwise OR** in all three files: `PROT_READ + PROT_WRITE` -> `PROT_READ or PROT_WRITE`, `MAP_PRIVATE + MAP_ANONYMOUS` -> `MAP_PRIVATE or MAP_ANONYMOUS`.

4. **Add `defer memory_store_free(@store)` pattern** to all test functions. Remove the duplicated cleanup calls at each early return.

5. **Remove dead imports**: `import ritzlib.sys { write }` in `blob_id.ritz` and `error.ritz`.

6. **Fix `namespace_write` and `namespace_mkdir`** to use explicit `return` on the final `update_dir_entry` call, or confirm that tail-expression return is intended and document it.

### Priority 3 (MINOR - address in follow-up)

7. **Migrate error constants to an enum ADT** if ADT enums are available in the compiler.

8. **Add `impl` blocks** for `BlobId`, `MemoryBlobStore`, `Namespace`, `DirEntry`, and `PathIter`.

9. **Replace hardcoded struct size `56` and `320`** with named constants and `sizeof()` if available.

10. **Fix the GOLIATH_MAGIC constant** comment and verify the value encodes `"GOLIATH\0"` correctly.

---

*LARB Review completed 2026-02-17 - Goliath (filesystem/VFS)*
