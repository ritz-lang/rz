# Squeeze Code Review

Code review findings from 2026-02-13. Identifies code smells, language limitations, and improvement opportunities.

---

## Summary

| Category | Count |
|----------|-------|
| Code Smells (Squeeze) | 7 |
| Ritz Language Issues | 6 |
| Performance Opportunities | 4 |

---

## Code Smells in Squeeze

### 1. Global Mutable State for Tables

**Files:** `lib/crc32.ritz`, `lib/inflate.ritz`, `lib/deflate.ritz`

```ritz
var g_crc32_table: [256]u32
var g_table_initialized: i32 = 0
```

**Issue:** Using global mutable state with lazy initialization. Not thread-safe.

**Recommendation:**
- Use compile-time table generation (requires Ritz comptime support)
- Or document thread-safety requirements clearly
- Or use `const` tables with initializer expressions (if Ritz supports complex const initializers)

---

### 2. Duplicated Length/Distance Tables

**Files:** `lib/inflate.ritz`, `lib/deflate.ritz`

Both files define identical `LENGTH_BASE`, `LENGTH_EXTRA`, `DIST_BASE`, `DIST_EXTRA` tables.

**Recommendation:** Create a shared `lib/deflate_tables.ritz` module and import from both.

---

### 3. Magic Numbers in Bit Operations

**Files:** `lib/bits.ritz`, `lib/huffman.ritz`

```ritz
let bits_in_byte: i32 = 8 - reader.bit_pos
```

**Issue:** The number `8` appears frequently without named constant.

**Recommendation:** Add `const BITS_PER_BYTE: i32 = 8` for clarity.

---

### 4. ~~Unused Import~~ ✅ FIXED

**Files:** `lib/adler32.ritz`

```ritz
import ritzlib.io  # Not used
```

**Status:** Removed in code review (2026-02-13).

---

### 5. Error Code Inconsistency

**Files:** `lib/gzip.ritz`, `lib/zlib.ritz`

Gzip uses `-7` for `INFLATE_FAILED`, zlib uses `-7` for the same. But `DEFLATE_ERR_OUTPUT_FULL` is `-1` in deflate.ritz while `GZIP_ERR_OUTPUT_FULL` is `-9`.

**Recommendation:** Create shared error code module or use consistent numbering.

---

### 6. ~~Verbose Byte Extraction Pattern~~ ✅ FIXED

**Files:** `lib/gzip.ritz`, `lib/zlib.ritz`

```ritz
let crc_b0: u32 = input[trailer_pos] as u32
let crc_b1: u32 = input[trailer_pos + 1] as u32
let crc_b2: u32 = input[trailer_pos + 2] as u32
let crc_b3: u32 = input[trailer_pos + 3] as u32
let expected_crc: u32 = crc_b0 | (crc_b1 << 8) | (crc_b2 << 16) | (crc_b3 << 24)
```

**Status:** Created `lib/bytes.ritz` with helper functions (2026-02-13):
```ritz
pub fn read_u16_le/be(data: *u8, pos: i64) -> u16
pub fn read_u32_le/be(data: *u8, pos: i64) -> u32
pub fn write_u16_le/be(data: *u8, pos: i64, value: u16)
pub fn write_u32_le/be(data: *u8, pos: i64, value: u32)
```

---

### 7. ~~Inefficient get_distance_code() Linear Search~~ ✅ FIXED

**File:** `lib/deflate.ritz`

**Status:** Refactored to O(log n) binary search (2026-02-13):
```ritz
fn get_distance_code(dist: i32) -> i32
    var lo: i32 = 0
    var hi: i32 = 29
    while lo < hi
        let mid: i32 = (lo + hi + 1) / 2
        if DIST_BASE[mid] <= dist
            lo = mid
        else
            hi = mid - 1
    return lo
```

---

## Ritz Language Issues

### 1. No Qualified Import Resolution (Known Issue)

**Status:** Issue #99 filed

```ritz
import ritzlib.sys as sys
sys::write(...)  # Parser supports, name resolver doesn't
```

---

### 2. No Compile-Time Table Generation

**Status:** Issue #101 filed

**Impact:** Cannot generate CRC32/Huffman tables at compile time.

```ritz
# Would like:
const CRC32_TABLE: [256]u32 = comptime {
    # Generate table at compile time
}
```

---

### 3. No Static Assert

**Status:** Issue #103 filed

**Impact:** Cannot verify table sizes or constants at compile time.

```ritz
# Would like:
static_assert(LENGTH_BASE.len == 29, "LENGTH_BASE must have 29 entries")
```

---

### 4. No Inline Hint

**Status:** Issue #104 filed

**Impact:** Cannot hint that small functions should be inlined.

```ritz
# Would like:
@inline
fn reverse_bits(code: u32, len: i32) -> u32
```

---

### 5. Limited Const Expression Support

**Status:** Issue #105 filed

**Impact:** Cannot use expressions in const array sizes.

```ritz
const HUFFMAN_LOOKUP_SIZE: i32 = 512    # 2^9 entries
# Would like: const HUFFMAN_LOOKUP_SIZE: i32 = 1 << HUFFMAN_LOOKUP_BITS
```

---

### 6. No SIMD/Intrinsics Support

**Status:** Issue #102 filed

**Impact:** Cannot use PCLMULQDQ for CRC32, AVX for vectorized operations.

```ritz
# Would like:
@extern("llvm.x86.pclmulqdq")
fn pclmulqdq(a: u128, b: u128, imm: i8) -> u128

# Or Ritz-native SIMD types:
let v: simd[4]u32 = simd_load(&data[0])
```

**Research findings (2026-02-13):** See [SIMD CRC32 Research](#simd-crc32-research) below.

---

## Performance Opportunities

### 1. SIMD CRC32 (PCLMULQDQ)

Modern x86 CPUs have hardware CRC32 via PCLMULQDQ. Can achieve 10-20x speedup.

**Requires:** Intrinsics or inline assembly support in Ritz.

**See:** [SIMD CRC32 Research](#simd-crc32-research) for detailed implementation notes.

---

### 2. SIMD Adler-32

Can vectorize the sum operations using AVX2 for 4-8x speedup.

**Requires:** SIMD types or intrinsics.

---

### 3. Unrolled Byte Processing

CRC32 and Adler-32 process one byte at a time. Loop unrolling (4 or 8 bytes per iteration) can improve performance.

**Can implement now:** Manual loop unrolling in Ritz.

---

### 4. Multi-Symbol Huffman Decoding

Process multiple symbols per lookup for faster decompression.

**Complexity:** Medium. Requires larger lookup tables.

---

## Recommended Actions

### Immediate (Squeeze) - ✅ DONE

1. [x] Remove unused `import ritzlib.io` from adler32.ritz
2. [ ] Extract shared deflate tables to `lib/deflate_tables.ritz`
3. [x] Add byte read/write helpers to reduce verbosity (`lib/bytes.ritz`)
4. [x] Optimize `get_distance_code()` with binary search

### Near-term (Squeeze)

5. [ ] Add thread-safety documentation for global tables
6. [ ] Implement loop-unrolled CRC32/Adler-32 variants
7. [ ] Benchmark current implementation for baseline

### Ritz Issues Filed

8. [x] Comptime / const fn evaluation → **Issue #101**
9. [x] Static assert → **Issue #103**
10. [x] Inline attribute → **Issue #104**
11. [x] SIMD types and intrinsics → **Issue #102**
12. [x] Const expression in array sizes → **Issue #105**

---

## SIMD CRC32 Research

Detailed research on implementing SIMD-accelerated CRC32 for the IEEE polynomial (0x04C11DB7) used by gzip/PNG/ZIP.

### Key Findings

**Important distinction:** SSE4.2's `CRC32` instruction uses the **CRC32C polynomial** (0x1EDC6F41), not the IEEE polynomial. For gzip-compatible CRC32, we need **PCLMULQDQ** (carryless multiplication).

### Algorithm: Folding with Barrett Reduction

The modern approach uses PCLMULQDQ for parallel CRC computation:

1. **Initialization:** Load 64 bytes into four 128-bit XMM registers
2. **Folding:** Use carryless multiplication to fold data in parallel
3. **Reduction:** Barrett reduction to get final 32-bit CRC

### LLVM Intrinsics Required

```llvm
; 128-bit carryless multiplication
declare <2 x i64> @llvm.x86.pclmulqdq(<2 x i64>, <2 x i64>, i8) #1

; With target features
attributes #1 = { "target-features"="+pclmul,+sse4.1" }
```

### Ritz Compiler Requirements

To implement SIMD CRC32, Ritz would need:

1. **Vector types:** `<2 x i64>` or `simd[2]i64`
2. **Intrinsic declarations:**
   ```ritz
   @extern("llvm.x86.pclmulqdq")
   fn pclmulqdq(a: simd[2]i64, b: simd[2]i64, imm: i8) -> simd[2]i64
   ```
3. **Target feature attributes:** `@target("pclmul,sse4.1")`
4. **Runtime feature detection:** `if cpu_has_pclmul() { ... }`

### Performance Expectations

| Implementation | Throughput |
|----------------|------------|
| Table-driven (current) | ~400 MB/s |
| PCLMULQDQ-accelerated | ~6 GB/s |
| **Speedup** | **~15x** |

### Reference Implementations

- **Intel Paper:** "Fast CRC Computation for Generic Polynomials Using PCLMULQDQ" (2009)
- **zlib-ng:** `arch/x86/crc32_pclmulqdq.c`
- **Chromium:** `third_party/zlib/crc32_simd.c`

### Current Status

**Blocked on Ritz Issue #102** (SIMD types and intrinsics). Once Ritz supports vector types and LLVM intrinsic declarations, SIMD CRC32 can be implemented.

---

*Last updated: 2026-02-13*
