# Squeeze Development Guide

## Project Overview

Squeeze is a compression library for Ritz, implementing Deflate (RFC 1951), Gzip (RFC 1952), and Zlib (RFC 1950). The primary use case is HTTP compression for the Valet webserver.

## Directory Structure

```
squeeze/
├── lib/              # Library modules (production code)
│   ├── crc32.ritz    # CRC-32 checksum
│   ├── bits.ritz     # Bit stream reader/writer
│   ├── huffman.ritz  # Huffman coding
│   ├── inflate.ritz  # Deflate decompression
│   └── ...           # Future: deflate.ritz, gzip.ritz, zlib.ritz
├── test/             # Test files (@test functions)
│   ├── test_crc32.ritz
│   ├── test_bits.ritz
│   ├── test_huffman.ritz
│   └── test_inflate.ritz
├── ritz/             # Ritz compiler (submodule)
├── ritzlib -> ritz/ritzlib  # Symlink to standard library
├── ritzunit/         # Test framework (submodule)
├── run_tests.sh      # Build and run tests with ritzunit
├── build.sh          # Build library (placeholder)
├── TODO.md           # Development roadmap (phases, tasks)
├── DONE.md           # Completed work
├── README.md         # Public documentation
└── CLAUDE.md         # This file
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

Tests are automatically discovered via ELF symbol table scanning. Any function marked with `@test` that returns `i32` will be found and run:

```ritz
@test
fn test_crc32_empty() -> i32
    let result: u32 = crc32(c"", 0)
    if result != 0x00000000
        print(c"FAIL: test_crc32_empty\n")
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

@test
fn test_crc32_empty() -> i32
    # CRC32("") = 0x00000000
    let result: u32 = crc32("" as *u8, 0)
    if result != 0x00000000
        return 1
    0

@test
fn test_crc32_known_vector() -> i32
    # CRC32("123456789") = 0xCBF43926
    let result: u32 = crc32("123456789" as *u8, 9)
    if result != 0xCBF43926
        return 1
    0
```

### 2. Follow Ritz Style Guide

See `ritz/STYLE.md` for full details. Key points:

| Item | Convention | Example |
|------|------------|---------|
| Functions | snake_case | `crc32_update`, `huffman_decode` |
| Variables | snake_case | `bit_offset`, `code_length` |
| Types/Structs | PascalCase | `BitReader`, `HuffmanTable` |
| Constants | SCREAMING_SNAKE | `CRC32_POLYNOMIAL`, `MAX_CODE_LENGTH` |
| Indent | 4 spaces | (no tabs) |

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
```

### Deflate Block Types

```
Type 0: Stored (uncompressed) - LEN + NLEN + data
Type 1: Fixed Huffman codes
Type 2: Dynamic Huffman codes (code length tree + literal/distance trees)
```

## Common Patterns

### Test Vector Comparison

```ritz
# Helper for comparing against hex strings (from cryptosec)
fn hex_char_to_val(c: u8) -> u8
    if c >= '0' && c <= '9'
        return c - '0'
    if c >= 'a' && c <= 'f'
        return c - 'a' + 10
    if c >= 'A' && c <= 'F'
        return c - 'A' + 10
    return 0

fn bytes_eq_hex(bytes: *u8, len: i64, hex: *u8) -> i32
    for i in 0..len
        let hi: u8 = hex_char_to_val(hex[i * 2])
        let lo: u8 = hex_char_to_val(hex[i * 2 + 1])
        let expected: u8 = (hi << 4) | lo
        if bytes[i] != expected
            return 0
    return 1
```

### Bit Manipulation

```ritz
# Bit rotation (from sha256)
fn rotr32(x: u32, n: u32) -> u32
    return (x >> n) | (x << (32 - n))

# Read big-endian u32 from bytes
fn read_be32(ptr: *u8) -> u32
    let b0: u32 = ptr[0] as u32
    let b1: u32 = ptr[1] as u32
    let b2: u32 = ptr[2] as u32
    let b3: u32 = ptr[3] as u32
    return (b0 << 24) | (b1 << 16) | (b2 << 8) | b3

# Write little-endian u32 to bytes (for gzip trailer)
fn write_le32(ptr: *u8, val: u32)
    ptr[0] = (val & 0xFF) as u8
    ptr[1] = ((val >> 8) & 0xFF) as u8
    ptr[2] = ((val >> 16) & 0xFF) as u8
    ptr[3] = ((val >> 24) & 0xFF) as u8
```

### Lookup Tables

```ritz
# Generate CRC32 table (call once at init or use const when supported)
fn crc32_make_table(table: *u32)
    for i in 0..256
        var crc: u32 = i as u32
        for j in 0..8
            if (crc & 1) != 0
                crc = (crc >> 1) ^ CRC32_POLYNOMIAL
            else
                crc = crc >> 1
        table[i] = crc
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

See `TODO.md` for detailed tasks. The phases are:

1. **Foundations** - CRC32, Adler32, BitReader/Writer
2. **Huffman** - Decoding tables, encoding tables, code generation
3. **Deflate** - Inflate (decompress), then Deflate (compress)
4. **Containers** - Gzip format, Zlib format
5. **HTTP** - Accept-Encoding parsing, Valet integration
6. **Optimization** - SIMD, memory pools, profiling

## Related Projects

- **ritz/** - Ritz compiler (submodule)
- **ritzunit/** - Test framework (submodule)
- **../valet** - HTTP server that will use squeeze
- **../cryptosec** - Cryptographic library (similar structure, good reference)
- **ritz/ritzlib/** - Standard library modules

## Notes

- Binaries go in `build/`, not `/tmp` (noexec mount)
- All code should be valgrind-clean
- Clear `.ritz-cache` if you see stale constant values
- Use `c"string"` for C-string literals, `"string"` for String type

---

*Last updated: 2026-02-12*
