# LARB Review: Squeeze

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** PASS

## Summary

Squeeze is a well-structured pure-Ritz compression library implementing DEFLATE (RFC 1951), GZIP (RFC 1952), and ZLIB (RFC 1950) with both one-shot and streaming APIs, plus SIMD-accelerated variants for CRC32, Adler-32, and hash-chain operations. The project has already completed a RERITZ migration (documented in `RERITZ_MIGRATION.md`, dated 2026-02-14) and is largely compliant with the v0.2.0 specification. The main findings are a pervasive but contextually appropriate use of raw pointer types (`*T`) in all function signatures, a handful of minor stale comments, and one recurring code-organization issue (duplicated constant tables across modules).

## Statistics

- **Files Reviewed:** 30 (15 lib, 15 test)
- **Total SLOC:** ~7,934
- **Issues Found:** 8 (Critical: 0, Major: 3, Minor: 5)

## Critical Issues

None.

## Major Issues

### MAJOR-1: Raw Pointer Parameters Used Everywhere Instead of Ownership Modifiers

All function signatures use `*T` raw pointer types for their parameters, where the Ritz ownership system calls for `x: T` (const borrow), `x:& T` (mutable borrow), or `x:= T` (move). Every function that mutates state through a pointer (e.g., `bits_read`, `inflate_stored`, `gzip_writer_write`) should use `:&` mutable borrow. Every read-only callee (e.g., `crc32_update`, `adler32_update`, `huffman_encode`) should use `: T` const borrow.

The instructions acknowledge that `*T` is acceptable in FFI/unsafe contexts. However, this codebase is application-level compression logic with no FFI boundary - it is entirely Ritz-to-Ritz. The pervasive use of `*T` instead of the ownership modifier system bypasses the borrow checker and safety guarantees that the language is designed to provide.

**Affected files (all lib files):**

- `/home/aaron/dev/ritz-lang/rz/projects/squeeze/lib/bits.ritz` - e.g., `fn bits_read(reader: *BitReader, n: i32) -> u32` should be `fn bits_read(reader:& BitReader, n: i32) -> u32`
- `/home/aaron/dev/ritz-lang/rz/projects/squeeze/lib/huffman.ritz` - e.g., `pub fn huffman_build_decode_table(table: *HuffmanTable, lengths: *u8, num_symbols: i32)` should use `:&` for `table` and `: u8` for `lengths`
- `/home/aaron/dev/ritz-lang/rz/projects/squeeze/lib/inflate.ritz` - All helper functions (`inflate_stored`, `inflate_huff`, `read_code_lens`, etc.)
- `/home/aaron/dev/ritz-lang/rz/projects/squeeze/lib/deflate.ritz` - `deflate_compressed`, `limit_code_lengths`, `rle_encode_lengths`, etc.
- `/home/aaron/dev/ritz-lang/rz/projects/squeeze/lib/gzip_stream.ritz` - `GzipWriter`/`GzipReader` API functions
- `/home/aaron/dev/ritz-lang/rz/projects/squeeze/lib/zlib_stream.ritz` - `ZlibWriter`/`ZlibReader` API functions
- `/home/aaron/dev/ritz-lang/rz/projects/squeeze/lib/crc32.ritz`, `adler32.ritz`, `crc32_simd.ritz`, `adler32_simd.ritz`, `gzip.ritz`, `zlib.ritz`, `bytes.ritz`
- All 15 test files pass raw pointers to every function call

**Example - CURRENT (wrong):**
```ritz
pub fn bits_read(reader: *BitReader, n: i32) -> u32
pub fn huffman_decode(table: *HuffmanTable, reader: *BitReader) -> i32
pub fn gzip_writer_write(w: *GzipWriter, data: *u8, len: i64, out: *u8, out_cap: i64) -> i64
```

**Example - CORRECT:**
```ritz
pub fn bits_read(reader:& BitReader, n: i32) -> u32
pub fn huffman_decode(table: HuffmanTable, reader:& BitReader) -> i32
pub fn gzip_writer_write(w:& GzipWriter, data: u8, len: i64, out:& u8, out_cap: i64) -> i64
```

### MAJOR-2: Massive Code Duplication of Length/Distance Tables

The Deflate length base and extra-bits tables (DEFLATE RFC 1951 Tables 3.2.5 and 3.2.6) are copy-pasted across 5 separate files with only a name prefix changed:

- `deflate.ritz`: `DEF_LENGTH_BASE`, `DEF_DIST_BASE`, etc.
- `inflate.ritz`: `LENGTH_BASE`, `DIST_BASE`, etc.
- `gzip_stream.ritz`: `GS_LENGTH_BASE`, `GS_DIST_BASE`, etc.
- `zlib_stream.ritz`: `ZS_LENGTH_BASE`, `ZS_DIST_BASE`, etc.
- `deflate_simd.ritz`: `SIMD_LENGTH_BASE`, `SIMD_DIST_BASE`, etc.

Similarly, fixed Huffman table initialization code (`init_*_encode_tables`) is duplicated across `deflate.ritz`, `gzip_stream.ritz`, `zlib_stream.ritz`, and `deflate_simd.ritz`. This creates maintenance risk (a table correction must be applied in 5 places) and significantly inflates the SLOC count. These tables belong in a shared `deflate_tables.ritz` module and should be imported.

### MAJOR-3: Stale Comment Text References Old `@test` Syntax

Seven test files contain a comment at the end referencing the old attribute syntax:

```
# Each @test function is found via ELF symbol table scanning.
```

This is a post-migration artifact. The comment should be updated to reference `[[test]]`:

```
# Each [[test]] function is found via ELF symbol table scanning.
```

**Affected files:**
- `/home/aaron/dev/ritz-lang/rz/projects/squeeze/test/test_inflate.ritz` (line 467)
- `/home/aaron/dev/ritz-lang/rz/projects/squeeze/test/test_deflate.ritz` (line 648)
- `/home/aaron/dev/ritz-lang/rz/projects/squeeze/test/test_crc32.ritz` (line 274)
- `/home/aaron/dev/ritz-lang/rz/projects/squeeze/test/test_bits.ritz` (line 629)
- `/home/aaron/dev/ritz-lang/rz/projects/squeeze/test/test_huffman.ritz` (line 545)
- `/home/aaron/dev/ritz-lang/rz/projects/squeeze/test/test_crossval.ritz` (line 580)
- `/home/aaron/dev/ritz-lang/rz/projects/squeeze/test/test_squeeze.ritz` (line 260)

## Minor Issues

### MINOR-1: Trailing `return` on Void Functions

Many void functions end with a bare `return` statement that adds no value. Examples: `bits_skip` (line 119), `bits_flush` (line 252), `huffman_count_frequencies` (line 444), `write_u16_le` (line 39), `hashchain_insert_scalar` (line 193). These should be removed for cleanliness; Ritz functions return at the end of their body implicitly.

### MINOR-2: `HuffTables` Struct Uses `@HuffmanTable` Reference Fields

In `inflate.ritz`, the `HuffTables` struct is defined as:
```ritz
struct HuffTables
    litlen: @HuffmanTable
    dist: @HuffmanTable
```

The `@T` type in a struct field means the struct stores a reference (pointer) rather than an owned value. While technically correct, this pattern means the `HuffTables` struct has a lifetime dependency on the pointed-to tables. If the intent is a lightweight "view" pair, this is acceptable; but if ownership is intended, the fields should be value types: `litlen: HuffmanTable`. Document the intent with a comment.

### MINOR-3: `gzip_stream.ritz` Passes `w.out_buf`/`w.out_pos` by Mutation but Sets Them Twice

In `gzip_writer_write` (lines 343-353), the function sets `w.out_buf`, `w.out_pos`, and `w.out_cap` inside the `STATE_INIT` branch, then unconditionally sets them again immediately after. The first assignment inside the `if` block is overwritten. This is a logic clarity issue (the code works because both assignments are identical for the `STATE_INIT` path, but it looks like dead code). Consolidate the initialization.

### MINOR-4: Missing `pub` on Constants Used Across Module Boundaries

Several constants defined in `inflate.ritz` and `deflate.ritz` (e.g., `INFLATE_OK`, `INFLATE_ERR_*`, `DEFLATE_OK`, `DEFLATE_ERR_*`) lack `pub` visibility but their numeric values are re-exported through the `SQUEEZE_ERR_*` constants in `squeeze.ritz`. The mapping between the internal error codes and the public unified codes is implicit and fragile. Consider making internal codes `pub` and having the unified module re-export them directly, or at minimum add a comment documenting the mapping.

### MINOR-5: `deflate_simd.ritz` Imports Use `lib.` Prefix Inconsistently

`deflate_simd.ritz` uses `import lib.bits`, `import lib.huffman`, `import lib.deflate` (with `lib.` prefix), while all other files in `lib/` use bare `import bits`, `import huffman` (without the prefix). This inconsistency suggests the file was written or migrated under different import root assumptions.

**Affected file:** `/home/aaron/dev/ritz-lang/rz/projects/squeeze/lib/deflate_simd.ritz` (lines 22-24)

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | ISSUE | Pervasive `*T` raw pointers in all function signatures instead of `:`, `:&`, `:=` modifiers. Acceptable in FFI but this is pure Ritz code. |
| Reference Types (@) | OK | `@x` address-of and `@T` type syntax used correctly throughout. No old `&x` patterns found. |
| Attributes ([[...]]) | OK | All 199 test functions correctly use `[[test]]`. No `@test` or `@inline` found in code. (Stale comments in trailing notes, see MAJOR-3.) |
| Logical Operators | OK | No `&&`, `\|\|`, or `!` operators found. All boolean logic uses `and`, `or`, `not` correctly. |
| String Types | OK | No `c"..."` or `s"..."` prefix strings found in source. No string literals of any kind (this is a binary data library). |
| Error Handling | OK | Consistent use of negative return codes as an explicit error-handling convention (appropriate for this low-level library). No Result/`?` patterns needed at this abstraction level. |
| Naming Conventions | OK | snake_case functions, PascalCase structs/types, SCREAMING_SNAKE_CASE constants. Consistent throughout. |
| Code Organization | ISSUE | Significant table/code duplication across modules (see MAJOR-2). File structure otherwise follows the recommended order. |

## Files Needing Attention

| File | Issues |
|------|--------|
| All 30 `.ritz` files | MAJOR-1: Raw pointer parameters throughout |
| `deflate.ritz`, `inflate.ritz`, `gzip_stream.ritz`, `zlib_stream.ritz`, `deflate_simd.ritz` | MAJOR-2: Duplicated length/distance tables |
| 7 test files (see MAJOR-3) | MAJOR-3: Stale `@test` reference in trailing comment |
| `deflate_simd.ritz` | MINOR-5: Inconsistent `lib.` import prefix |
| `inflate.ritz` | MINOR-2: `HuffTables` reference field intent unclear |

## Recommendations

1. **(MAJOR-1, deferred)** Migrate all function signatures from `*T` raw pointers to ownership modifiers (`: T`, `:& T`). This is a large change (~200+ functions) and should be done as a dedicated migration pass with tooling support. The RERITZ migration tooling already in `tools/migrate_reritz.py` could be extended for this. Given the scale, this is marked as a planned migration rather than an immediate blocker.

2. **(MAJOR-2, should fix)** Extract shared Deflate constants into a new `lib/deflate_tables.ritz` module. Remove the 5 sets of duplicated tables and replace with a single import. This reduces maintenance risk and SLOC by approximately 250 lines.

3. **(MAJOR-3, quick fix)** Update the 7 stale end-of-file comments from "Each `@test` function" to "Each `[[test]]` function". This is a 5-minute find-and-replace.

4. **(MINOR-1, quick fix)** Remove bare trailing `return` statements from void functions across the codebase.

5. **(MINOR-5, quick fix)** Fix the `lib.` import prefix in `deflate_simd.ritz` to match all other files in the directory.
