# Squeeze Development Guide

## Project Overview

Squeeze is a compression library for Ritz, implementing Deflate (RFC 1951), Gzip (RFC 1952), and Zlib (RFC 1950). The primary use case is HTTP compression for the Valet webserver.

## Directory Structure

```
squeeze/
├── lib/                    # Library modules (production code)
│   ├── adler32.ritz        # Adler-32 checksum
│   ├── adler32_simd.ritz   # SIMD-accelerated Adler-32
│   ├── bits.ritz           # Bit stream reader/writer
│   ├── bytes.ritz          # Byte manipulation utilities
│   ├── crc32.ritz          # CRC-32 checksum
│   ├── crc32_simd.ritz     # SIMD-accelerated CRC32 (PCLMULQDQ)
│   ├── deflate.ritz        # Deflate compression (RFC 1951)
│   ├── deflate_simd.ritz   # SIMD-accelerated deflate
│   ├── gzip.ritz           # Gzip container format (RFC 1952)
│   ├── gzip_stream.ritz    # Streaming gzip (GzipReader/GzipWriter)
│   ├── huffman.ritz        # Huffman coding
│   ├── inflate.ritz        # Deflate decompression
│   ├── squeeze.ritz        # Main module (re-exports)
│   ├── zlib.ritz           # Zlib container format (RFC 1950)
│   └── zlib_stream.ritz    # Streaming zlib (ZlibReader/ZlibWriter)
├── test/                   # Test files ([[test]] functions)
│   ├── test_adler32.ritz
│   ├── test_adler32_simd.ritz
│   ├── test_bits.ritz
│   ├── test_crc32.ritz
│   ├── test_crc32_simd.ritz
│   ├── test_crossval.ritz  # Cross-validation against system gzip/zlib
│   ├── test_deflate.ritz
│   ├── test_gzip.ritz
│   ├── test_gzip_stream.ritz
│   ├── test_hashchain_simd.ritz
│   ├── test_huffman.ritz
│   ├── test_inflate.ritz
│   ├── test_squeeze.ritz
│   ├── test_zlib.ritz
│   └── test_zlib_stream.ritz
├── ritz.toml               # Build configuration
├── run_tests.sh            # Build and run tests with ritzunit
├── TODO.md                 # Development roadmap
├── DONE.md                 # Completed work
├── README.md               # Public documentation
└── CLAUDE.md               # This file
```

## Building and Testing

Tests run using **ritzunit**, the standard Ritz test framework:

```bash
# Run all tests
./run_tests.sh

# Filter by test name (substring match)
./run_tests.sh --filter crc32
./run_tests.sh --filter inflate

# Verbose output (shows each test as it runs)
./run_tests.sh --verbose

# List tests without running
./run_tests.sh --list

# Set timeout (default 5000ms)
./run_tests.sh --timeout 10000
```

### Test Discovery

Tests are automatically discovered via ELF symbol table scanning. Any function marked with `[[test]]` that returns `i32` will be found and run:

```ritz
[[test]]
fn test_crc32_empty() -> i32
    let result: u32 = crc32("", 0)
    if result != 0x00000000
        print("FAIL: test_crc32_empty\n")
        return 1
    0
```

No manual test registration or main() required.

## Development Principles

### 1. Test-Driven Development (TDD)

**Always write tests first.** Follow the pattern from cryptosec:

```ritz
# test/test_crc32.ritz - Tests for CRC-32 implementation
#
# Test vectors from:
# - ISO 3309 examples
# - IEEE 802.3 Ethernet FCS
# - Known CRC32 values from gzip files

import ritzlib.sys
import ritzlib.io

import lib.crc32

[[test]]
fn test_crc32_empty() -> i32
    # CRC32("") = 0x00000000
    let result: u32 = crc32("", 0)
    if result != 0x00000000
        return 1
    0

[[test]]
fn test_crc32_known_vector() -> i32
    # CRC32("123456789") = 0xCBF43926
    let result: u32 = crc32("123456789", 9)
    if result != 0xCBF43926
        return 1
    0
```

### 2. Follow Ritz Style Guide

See `projects/larb/docs/STYLE.md` for full details. Key points:

| Item | Convention | Example |
|------|------------|---------|
| Functions | snake_case | `crc32_update`, `huffman_decode` |
| Variables | snake_case | `bit_offset`, `code_length` |
| Types/Structs | PascalCase | `BitReader`, `HuffmanTable` |
| Constants | SCREAMING_SNAKE | `CRC32_POLYNOMIAL`, `MAX_CODE_LENGTH` |
| Indent | 4 spaces | (no tabs) |
| Strings | `"string"` | Plain StrView literals |
| Attributes | `[[test]]` | New attribute syntax |

### 3. Code Organization Pattern

Follow the cryptosec pattern for each module:

```ritz
# lib/crc32.ritz - CRC-32 checksum implementation
#
# Implements CRC-32 (ISO 3309) as used by Gzip, PNG, and Ethernet.
#
# API:
# - crc32_init(): Initialize CRC state
# - crc32_update(state, data, len): Process data chunk
# - crc32_final(state): Get final checksum
# - crc32(data, len): One-shot convenience function

import ritzlib.sys

# ============================================================================
# Constants
# ============================================================================

const CRC32_POLYNOMIAL: u32 = 0xEDB88320

# ============================================================================
# CRC-32 State
# ============================================================================

struct Crc32
    state: u32

# ============================================================================
# Core Implementation
# ============================================================================

fn crc32_init() -> u32
    return 0xFFFFFFFF

fn crc32_update(state: u32, data: *u8, len: i64) -> u32
    # ... implementation
```

### 4. Use Streaming APIs

Design APIs that support both one-shot and streaming modes:

```ritz
# One-shot (convenience)
fn crc32(data: *u8, len: i64) -> u32
    var state: u32 = crc32_init()
    state = crc32_update(state, data, len)
    return crc32_final(state)

# Streaming (for large files)
fn crc32_init() -> u32
fn crc32_update(state: u32, data: *u8, len: i64) -> u32
fn crc32_final(state: u32) -> u32
```

### 5. Stack-First Memory

Prefer stack allocation over heap:

```ritz
# GOOD: Stack allocation
var buffer: [4096]u8
var table: [256]u32

# AVOID: Heap allocation in hot paths
# Only use malloc when size is runtime-determined
```

### 6. Reference Implementations

When implementing algorithms, cross-reference with:
- **zlib** - Mark Adler's reference implementation
- **zlib-ng** - Optimized fork with SIMD
- **puff.c** - Mark Adler's minimal inflate tutorial

## Algorithm Implementation Notes

### CRC-32

```
Polynomial: 0xEDB88320 (reflected form of 0x04C11DB7)
Initial value: 0xFFFFFFFF
Final XOR: 0xFFFFFFFF

Table-driven for speed (256-entry lookup table)
SIMD: PCLMULQDQ folding + Barrett reduction
```

### Adler-32

```
s1 = sum of bytes, s2 = sum of s1 values
Combined: (s2 << 16) | s1
Modulo: 65521 (largest prime < 2^16)

SIMD: PSADBW for vectorized accumulation
```

### Bit Stream

```
Deflate uses LSB-first bit ordering (little-endian bits)
Read bits from low to high within each byte
```

### Huffman Coding

```
Deflate fixed codes:
- Literals 0-143: 8 bits (00110000 - 10111111)
- Literals 144-255: 9 bits (110010000 - 111111111)
- Literals 256-279: 7 bits (0000000 - 0010111)
- Literals 280-287: 8 bits (11000000 - 11000111)

Maximum code length: 15 bits
Decode table: 9-bit lookup for fast resolution
```

### Deflate Block Types

```
Type 0: Stored (uncompressed) - LEN + NLEN + data
Type 1: Fixed Huffman codes
Type 2: Dynamic Huffman codes (code length tree + literal/distance trees)
```

## Streaming API

The streaming API (`gzip_stream.ritz`, `zlib_stream.ritz`) is designed for:
- **Large files** - Process data in chunks without loading entire file
- **HTTP responses** - Valet uses this for chunked transfer compression
- **Fixed memory** - No dynamic allocation after initialization

### GzipWriter Example

```ritz
var writer: GzipWriter
gzip_writer_init(@writer, 6)  # Compression level 6

# Write chunks
var out: [65536]u8
let n1 = gzip_writer_write(@writer, chunk1, len1, @out[0], 65536)
let n2 = gzip_writer_write(@writer, chunk2, len2, @out[0], 65536)

# Finish and get trailer
let final = gzip_writer_finish(@writer, @out[0], 65536)
```

## Debugging Tips

### Preserve Build Artifacts

```bash
# Build with debug info
python3 ritz/ritz build -g lib/crc32
# Creates build/*.ll files for inspection
```

### Compare with Reference

```bash
# Create test file
echo -n "123456789" > test.txt

# Get reference CRC32 from gzip
gzip -c test.txt > test.txt.gz
hexdump -C test.txt.gz | tail -1  # CRC32 in trailer

# Compare with squeeze output
./build/test_crc32
```

### GDB Debugging

```bash
gdb ./build/test_crc32
(gdb) break crc32_update
(gdb) run
(gdb) print/x state
```

## Phase Progression

See `TODO.md` for detailed tasks. Completed phases:

1. **Foundations** - CRC32, Adler32, BitReader/Writer ✅
2. **Huffman** - Decoding tables, encoding tables, code generation ✅
3. **Deflate** - Inflate (decompress), Deflate (compress), Dynamic Huffman ✅
4. **Containers** - Gzip format, Zlib format ✅
5. **Streaming** - GzipReader/Writer, ZlibReader/Writer ✅
6. **SIMD** - CRC32, Adler-32, hashchain acceleration ✅

## Related Projects

- **ritz/** - Ritz compiler (monorepo: `projects/ritz`)
- **ritzunit/** - Test framework (monorepo: `projects/ritz/ritzunit`)
- **valet** - HTTP server that uses squeeze (monorepo: `projects/valet`)
- **cryptosec** - Cryptographic library (similar structure, good reference)
- **ritzlib** - Standard library modules (monorepo: `projects/ritz/ritzlib`)

## Notes

- Binaries go in `build/`, not `/tmp` (noexec mount)
- All code should be valgrind-clean
- Clear `.ritz-cache` if you see stale constant values
- Use `"string"` for StrView literals (not `c"string"`)
- Use `[[test]]` attribute syntax (not `@test`)

---

*Last updated: 2026-02-16*
