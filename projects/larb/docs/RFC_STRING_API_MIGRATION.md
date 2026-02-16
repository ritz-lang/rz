# RFC: Deprecate Raw Pointer String APIs in ritzlib

**LARB Document** | **Status:** Draft | **Date:** 2026-02-16

---

## Summary

Deprecate the `*u8` (raw C pointer) string functions in `ritzlib/str.ritz` in favor of the idiomatic `StrView` and `String` types. Raw pointer APIs should only be used at FFI boundaries.

---

## Motivation

### The Problem

The current `ritzlib/str.ritz` module contains C-style string functions that use raw pointers:

```ritz
# Current API (C-style, non-idiomatic)
pub fn strlen(s: *u8) -> i64
pub fn streq(a: *u8, b: *u8) -> i32
pub fn strcmp(a: *u8, b: *u8) -> i32
pub fn strcpy(dest: *u8, src: *u8) -> *u8
pub fn strcat(dest: *u8, src: *u8) -> *u8
pub fn memcpy(dest: *u8, src: *u8, n: i64) -> *u8
pub fn memset(dest: *u8, c: u8, n: i64) -> *u8
```

These APIs have several issues:

1. **Ambiguous Ownership**: `*u8` doesn't communicate whether the string is borrowed, owned, or who is responsible for freeing it
2. **No Length Information**: Relies on null termination, enabling buffer overflows
3. **C Aesthetic**: Looks like C code, not idiomatic Ritz
4. **Type Confusion**: `*u8` could be a string, a byte buffer, or raw memory - no type safety

### Why These Exist

These functions were written during early Ritz bootstrap when:
- Ritz used direct Linux syscalls (no libc)
- Proper string types (`StrView`, `String`) didn't exist yet
- Raw pointers were the only option

Now that Ritz has a proper string type hierarchy, these should be deprecated.

---

## Proposed Solution

### 1. String Type Hierarchy (Already Exists)

Ritz already has the correct types in `ritzlib`:

| Type | Module | Ownership | Allocation | Use Case |
|------|--------|-----------|------------|----------|
| `StrView` | `strview.ritz` | Borrowed | None | String literals, slices, zero-copy |
| `String` | `string.ritz` | Owned | Heap | Mutable, growable strings |
| `*u8` | — | Ambiguous | Unknown | FFI only |

### 2. Idiomatic Replacements

| Deprecated (`*u8`) | Replacement | Notes |
|--------------------|-------------|-------|
| `strlen(s)` | `s.len()` | StrView has length built-in |
| `streq(a, b)` | `strview_eq(a, b)` | Or `a.eq(b)` with method syntax |
| `strcmp(a, b)` | `strview_cmp(a, b)` | **New function needed** |
| `strcpy(d, s)` | `string_from(s)` | Creates owned copy |
| `strcat(d, s)` | `string_push_str(d, s)` | Append to String |
| `memcpy(d, s, n)` | Keep for byte buffers | Not a string function |
| `memset(d, c, n)` | Keep for byte buffers | Not a string function |

### 3. New Functions Needed in `strview.ritz`

```ritz
# Lexicographic comparison (-1, 0, 1)
pub fn strview_cmp(a: @StrView, b: @StrView) -> i32

# Compare StrView to C string (for FFI interop)
pub fn strview_cmp_cstr(s: @StrView, cstr: *u8) -> i32
```

### 4. FFI Boundary Pattern

For system calls and external libraries that require `*u8`:

```ritz
# FFI function that needs null-terminated C string
extern fn open(path: *u8, flags: i32) -> i32

# Idiomatic Ritz wrapper
pub fn file_open(path: StrView, flags: i32) -> Result<FileHandle, Error>
    # String literals are null-terminated in the string pool
    let result = open(path.as_ptr(), flags)
    if result < 0
        return Err(Error.from_errno())
    Ok(FileHandle { fd: result })
```

**Key Insight**: RERITZ string literals (`"hello"`) are `StrView` values that ARE null-terminated (stored in compiler's string pool). Use `.as_ptr()` to get `*u8` for FFI.

---

## Migration Guide

### For Library Authors

**Before (C-style):**
```ritz
fn process_name(name: *u8) -> i32
    if streq(name, c"admin")
        return 1
    return 0
```

**After (Idiomatic Ritz):**
```ritz
fn process_name(name: StrView) -> i32
    if name.eq("admin")
        return 1
    return 0
```

### For Owned Strings

**Before:**
```ritz
fn build_greeting(name: *u8) -> *u8
    let buf: *u8 = malloc(256)
    strcpy(buf, c"Hello, ")
    strcat(buf, name)
    return buf  # Who frees this? Unclear!
```

**After:**
```ritz
fn build_greeting(name: StrView) -> String
    var s = string_from("Hello, ")
    s.push_str(name)
    return s  # Ownership transferred to caller
```

### For Command Line Arguments

`argv` comes from the kernel as `*u8`. Convert at the boundary:

```ritz
fn main(argc: i32, argv: **u8) -> i32
    # Convert at FFI boundary
    let cmd = strview_from_cstr(*(argv + 1))

    # Now use idiomatic Ritz
    if cmd.eq("help")
        print_help()
    else if cmd.eq("version")
        print_version()
```

---

## Deprecation Schedule

### Phase 1: Documentation (Immediate)
- Mark `ritzlib/str.ritz` functions as `[[deprecated]]` in docs
- Update STDLIB_REFERENCE.md with migration guidance
- Add compiler warnings for `c"..."` literal usage

### Phase 2: Ecosystem Migration (2 weeks)
- Migrate all ritz-lang projects to use `StrView`/`String`
- Update ritzlib.net to accept `StrView` for hostname/address
- Update ritzlib.io for file paths

### Phase 3: Compiler Support (1 month)
- Emit deprecation warnings for `*u8` string function usage
- Suggest idiomatic replacements in error messages

### Phase 4: Removal (ritz 2.0)
- Move `*u8` functions to `ritzlib/ffi/cstr.ritz`
- Remove from default namespace

---

## Impact Analysis

### Projects Affected

| Project | `c"..."` Count | `*u8` String Functions | Effort |
|---------|----------------|------------------------|--------|
| mausoleum | 295 | ~50 calls | Medium |
| valet | ~100 | ~30 calls | Small |
| cryptosec | ~20 | ~10 calls | Small |
| zeus | ~150 | ~40 calls | Medium |
| spire | ~200 | ~60 calls | Medium |

### Benefits

1. **Type Safety**: `StrView` and `String` are distinct types with clear semantics
2. **No Buffer Overflows**: Length is always known
3. **Clear Ownership**: `StrView` = borrowed, `String` = owned
4. **Idiomatic Code**: Ritz code looks like Ritz, not C
5. **Method Syntax**: `s.len()`, `s.eq(other)`, `s.contains(needle)`

### Risks

1. **Breaking Change**: Existing code must be updated
2. **FFI Friction**: Extra `.as_ptr()` calls at boundaries
3. **Learning Curve**: Developers familiar with C strings must adapt

---

## Alternatives Considered

### 1. Keep Both APIs
**Rejected**: Creates confusion about which to use. "One way to do it" is better.

### 2. Auto-coercion `StrView` <-> `*u8`
**Rejected**: Hides ownership semantics. Explicit is better.

### 3. Make `*u8` "safe" with reference counting
**Rejected**: Adds runtime overhead. Ritz is zero-cost.

---

## Compatibility

### Backward Compatibility

During migration period:
- `c"string"` literals continue to work (with warning)
- `*u8` functions remain available (marked deprecated)
- New code should use `StrView`/`String`

### Forward Compatibility

After ritz 2.0:
- `c"string"` syntax removed
- `*u8` string functions moved to `ritzlib/ffi/cstr.ritz`
- All ecosystem code uses idiomatic types

---

## Implementation

### Mausoleum Reference Implementation

The mausoleum project will serve as the reference implementation for this migration:

1. Replace `c"..."` with `"..."` (StrView literals)
2. Update function signatures to use `StrView` instead of `*u8`
3. Use `strview_eq()` instead of `streq()`
4. Use `String` for owned, heap-allocated strings
5. Only use `*u8` at FFI boundaries (socket, syscall)

### Checklist for Each Project

- [ ] Replace `c"..."` with `"..."`
- [ ] Update public APIs to use `StrView`/`String`
- [ ] Replace `streq()` with `strview_eq()`
- [ ] Replace `strlen()` with `.len()`
- [ ] Add `.as_ptr()` only at FFI boundaries
- [ ] Update tests
- [ ] Update documentation

---

## Open Questions

1. Should `strview_cmp()` return `Ordering` enum instead of `i32`?
2. Should we add `StrView::from_argv(argv: **u8, idx: i32)` helper?
3. Should network functions accept `StrView` or keep `*u8` (since they pass to syscalls)?

---

## References

- `ritzlib/strview.ritz` - StrView implementation
- `ritzlib/string.ritz` - String implementation
- `ritzlib/str.ritz` - Legacy C-style functions (to be deprecated)
- `docs/DESIGN_DECISIONS.md` - Section 4: String System

---

*This RFC requires LARB approval before implementation begins.*
