# Squeeze RERITZ Migration Plan

**Status:** ✅ Complete
**Date:** 2026-02-14
**Based on:** ritz/RERITZ.md
**Completed:** 2026-02-14

---

## Executive Summary

Squeeze needs to be modernized for the RERITZ language overhaul. This document tracks the migration from old Ritz syntax to new RERITZ syntax.

### Scope Analysis

| Category | Count | Notes |
|----------|-------|-------|
| Library files | 15 | `lib/*.ritz` |
| Test files | 15 | `test/*.ritz` |
| Total lines | ~11,300 | Core compression library |
| `@test` attributes | 199 | → `[[test]]` |
| Address-of (`&x`) | 528+ | → `@x` |
| C-string literals (`c"..."`) | 595 | → `"...".as_cstr()` |
| Pointer params (`*T`) | 188+ | May need `unsafe` blocks |

---

## Key Transformations

### 1. Attributes: `@test` → `[[test]]`

**Before:**
```ritz
@test
fn test_adler32_empty() -> i32
```

**After:**
```ritz
[[test]]
fn test_adler32_empty() -> i32
```

**Count:** 199 occurrences across test files

---

### 2. Address-of: `&x` → `@x`

**Before:**
```ritz
let result = deflate(&input[0], 256, &output[0], 512, 6)
```

**After:**
```ritz
let result = deflate(@input[0], 256, @output[0], 512, 6)
```

**Count:** 528+ occurrences

**Note:** Must distinguish from bitwise AND (`a & b` stays the same)

---

### 3. C-string Literals: `c"..."` → `"...".as_cstr()`

**Before:**
```ritz
print(c"FAIL: test failed\n")
```

**After:**
```ritz
print("FAIL: test failed\n".as_cstr())
```

**Count:** 595 occurrences

**Migration Strategy:** This is a significant change. Consider:
1. Wait for ritzlib to provide `print()` that accepts `StrView` natively
2. Or use `.as_cstr()` temporarily until print is updated

---

### 4. Pointer Parameters

**Current squeeze uses raw pointers extensively:**
```ritz
fn inflate(input: *u8, input_len: i64, output: *u8, output_cap: i64) -> i64
```

**Options for RERITZ:**

**Option A: Keep pointers (requires unsafe for calling code)**
```ritz
fn inflate(input: *u8, input_len: i64, output: *u8, output_cap: i64) -> i64
    # Implementation uses pointers internally
```

**Option B: Use slices/spans (preferred for safe API)**
```ritz
fn inflate(input: StrView, output:& [u8]) -> i64
    # Zero-copy, bounds-checked
```

**Recommendation:** Keep raw pointers in implementation but consider adding safe wrapper APIs later.

---

### 5. Reference Types (if needed)

**Before:**
```ritz
fn process(data: &T)
fn modify(data: &mut T)
```

**After:**
```ritz
fn process(data: @T)
fn modify(data: @&T)
```

**Note:** Squeeze currently uses raw pointers (`*T`) rather than references (`&T`), so this change has minimal impact.

---

## Migration Order

### Phase 1: Mechanical Transformations (Low Risk)

1. **Attributes** - Simple regex replacement
   ```bash
   sed -i 's/^@test$/[[test]]/' test/*.ritz
   ```

2. **Address-of** - Careful replacement (avoid bitwise AND)
   ```
   &var[  → @var[
   &var)  → @var)
   &var,  → @var,
   = &var → = @var
   ```

### Phase 2: String Literals (Medium Risk)

Wait for ritzlib update or use `.as_cstr()` shim.

### Phase 3: API Review (Future)

Consider safe wrapper APIs using `StrView` and `Span<u8>`.

---

## File-by-File Checklist

### Library Files (`lib/`)

| File | `@attr` | `&x` | `c"..."` | `*T` params | Status |
|------|---------|------|----------|-------------|--------|
| adler32.ritz | 0 | 2 | 0 | 4 | Pending |
| adler32_simd.ritz | 0 | 10 | 0 | 2 | Pending |
| bits.ritz | 0 | 10 | 0 | 15 | Pending |
| bytes.ritz | 0 | 0 | 0 | 4 | Pending |
| crc32.ritz | 0 | 5 | 0 | 4 | Pending |
| crc32_simd.ritz | 0 | 15 | 0 | 2 | Pending |
| deflate.ritz | 0 | 80 | 0 | 20 | Pending |
| deflate_simd.ritz | 0 | 5 | 0 | 2 | Pending |
| gzip.ritz | 0 | 30 | 0 | 10 | Pending |
| gzip_stream.ritz | 0 | 40 | 0 | 20 | Pending |
| huffman.ritz | 0 | 25 | 0 | 15 | Pending |
| inflate.ritz | 0 | 35 | 0 | 15 | Pending |
| squeeze.ritz | 0 | 5 | 0 | 5 | Pending |
| zlib.ritz | 0 | 20 | 0 | 10 | Pending |
| zlib_stream.ritz | 0 | 45 | 0 | 25 | Pending |

### Test Files (`test/`)

| File | `@test` | `&x` | `c"..."` | Status |
|------|---------|------|----------|--------|
| test_adler32.ritz | 8 | 15 | 20 | Pending |
| test_adler32_simd.ritz | 5 | 10 | 10 | Pending |
| test_bits.ritz | 25 | 30 | 50 | Pending |
| test_crc32.ritz | 12 | 20 | 25 | Pending |
| test_crc32_simd.ritz | 8 | 15 | 15 | Pending |
| test_crossval.ritz | 10 | 25 | 20 | Pending |
| test_deflate.ritz | 25 | 50 | 60 | Pending |
| test_gzip.ritz | 12 | 25 | 25 | Pending |
| test_gzip_stream.ritz | 10 | 30 | 25 | Pending |
| test_hashchain_simd.ritz | 4 | 10 | 10 | Pending |
| test_huffman.ritz | 15 | 25 | 30 | Pending |
| test_inflate.ritz | 12 | 20 | 25 | Pending |
| test_squeeze.ritz | 18 | 30 | 40 | Pending |
| test_zlib.ritz | 15 | 25 | 30 | Pending |
| test_zlib_stream.ritz | 20 | 40 | 50 | Pending |

---

## Migration Script

A migration script will be created at `tools/migrate_reritz.py`:

```python
#!/usr/bin/env python3
"""Migrate Squeeze to RERITZ syntax."""

import re
import sys
from pathlib import Path

def migrate_attributes(content: str) -> str:
    """@test -> [[test]]"""
    return re.sub(r'^@(\w+)$', r'[[\1]]', content, flags=re.MULTILINE)

def migrate_address_of(content: str) -> str:
    """&var -> @var (carefully, avoiding bitwise AND)"""
    # Match &identifier followed by [ ) , = or whitespace
    # Avoid matching things like `a & b`
    patterns = [
        (r'&(\w+)\[', r'@\1['),      # &arr[
        (r'&(\w+)\)', r'@\1)'),      # &var)
        (r'&(\w+),', r'@\1,'),       # &var,
        (r'= &(\w+)', r'= @\1'),     # = &var
        (r'\(&(\w+)', r'(@\1'),      # (&var
    ]
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    return content

def migrate_cstrings(content: str) -> str:
    """c"..." -> "...".as_cstr()"""
    return re.sub(r'c"([^"]*)"', r'"\1".as_cstr()', content)

def migrate_file(path: Path) -> None:
    content = path.read_text()
    original = content

    content = migrate_attributes(content)
    content = migrate_address_of(content)
    # content = migrate_cstrings(content)  # Wait for ritzlib update

    if content != original:
        path.write_text(content)
        print(f"Migrated: {path}")

if __name__ == '__main__':
    for pattern in ['lib/*.ritz', 'test/*.ritz']:
        for path in Path('.').glob(pattern):
            migrate_file(path)
```

---

## Dependencies

### Waiting On:

1. **ritz compiler** - Must support `[[attr]]` syntax and `@` for address-of
2. **ritzlib** - May need updates for `StrView` and `print()` changes
3. **ritzunit** - Must support `[[test]]` attribute discovery

### Ready Now:

- Migration script can be prepared
- Documentation can be updated
- Test plan can be finalized

---

## Testing Strategy

1. **Before migration:** Ensure all 199 tests pass
2. **After each phase:** Run full test suite
3. **Final validation:** Cross-validate with system gzip/zlib

```bash
# Pre-migration baseline
./run_tests.sh  # Should be 199 passed

# Post-migration validation
./run_tests.sh  # Must still be 199 passed
```

---

## Rollback Plan

All changes will be on a `reritz` branch:

```bash
git checkout -b reritz
# ... make changes ...

# If things go wrong:
git checkout main
```

---

## Timeline

| Phase | Task | Estimate | Dependencies |
|-------|------|----------|--------------|
| 0 | Prepare migration script | 1 hour | None |
| 1 | Wait for compiler support | TBD | ritz/reritz branch |
| 2 | Migrate attributes (`@test` → `[[test]]`) | 30 min | Phase 1 |
| 3 | Migrate address-of (`&x` → `@x`) | 2 hours | Phase 2 |
| 4 | Review c-string strategy | 1 hour | ritzlib update |
| 5 | Final testing | 1 hour | All above |

**Total estimated effort:** 4-5 hours (after compiler support)

---

## Questions for LARB

1. Should squeeze keep raw pointer APIs or migrate to safe slice-based APIs?
2. Timeline for `print()` to accept `StrView` directly?
3. Should we add `unsafe` blocks around pointer operations now?
