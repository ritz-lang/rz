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
├── tools/                  # Helper scripts
├── ritz.toml               # Build configuration (test_only = true)
├── README.md               # Public documentation
├── RERITZ_MIGRATION.md     # Migration notes
├── REVIEW.md               # Review notes
└── CLAUDE.md               # This file
```

There is no `build/` directory and no `run_tests.sh`; earlier revisions of this
file documented both. squeeze is `test_only = true` with no `[[bin]]`, so
`./rz build squeeze` correctly reports "nothing to build".

## Building and Testing

Run from the **monorepo root**. `rz` sets `RITZ_PATH` itself.

```bash
# Run all tests — 15 .ritz test files, 199 [[test]] functions.
# Takes several minutes; budget for it.
./rz test squeeze
```

`rz test` has no `--filter`, `--verbose`, `--list` or `--timeout` options:

```
usage: rz test [-h] [--all] [--compiler {ritz0,ritz1,ritz1_selfhosted}] [project]
```

Those flags belong to the **ritzunit** binary, which is what consumes a compiled
test executable. squeeze's tests are compiled and run by `build.py` rather than
handed to `ritzunit`, so there is currently no supported way to filter a subset
of squeeze's tests from the command line. If you need one, the honest options
are to add filtering to `rz test` or to wire squeeze's tests through the
`ritzunit` binary — not to re-add a shell script that drifts.

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

See `projects/ritz/docs/STYLE.md` for full details. Key points:

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

`build.py` has a `-g/--debug` flag documented as "Keep intermediate files
(.ll, .o) in build/ for debugging". There is no `ritz/ritz` script — the form
`python3 ritz/ritz build -g lib/crc32` documented here previously exits 2.

**`-g` does not currently produce artifacts for squeeze.** Both of these exit 0
and print `📁 Debug artifacts kept in build/`, yet
`projects/squeeze/build/` is never created and no `.ll` or `.o` file appears
anywhere (verified 2026-09-12):

```bash
cd projects/ritz
export RITZ_PATH=$PWD           # only needed for direct build.py use
python3 build.py build -g ../squeeze   # exit 0 — "test-only, nothing to build"
python3 build.py test  -g ../squeeze   # exit 0 — message printed, no files kept
```

So the message is a lie and `-g` is not a usable route to inspectable IR for a
`test_only` package yet. If you need the IR, compile a module directly with
`ritz0.py`:

```bash
cd projects/ritz
RITZ_PATH=$PWD python3 ritz0/ritz0.py ../squeeze/lib/crc32.ritz -o /tmp/crc32.ll
# exit 0: "Compiled ../squeeze/lib/crc32.ritz -> /tmp/crc32.ll" (15 KB of IR)
```

### Compare with Reference

```bash
cd /tmp
printf '123456789' > test.txt
gzip -c test.txt > test.txt.gz
xxd test.txt.gz | tail -1       # CRC32 sits in the gzip trailer
```

Then check squeeze's own value against it. The expected constant is already
asserted in `test/test_crc32.ritz`:
`crc32("123456789") == 0xCBF43926`. Run `./rz test squeeze` from the monorepo
root to evaluate it.

### GDB Debugging

There are **no standalone per-module test binaries** — no `build/test_crc32`
exists, and neither `./build/test_crc32` nor `gdb ./build/test_crc32` can work
(both exit 127). `rz test` compiles each `test/test_*.ritz` into a temporary
executable, runs it, and discards it.

`-g` is no help here either (see above — it keeps nothing). To get a debuggable
binary today you have to drive the pipeline by hand: emit IR with `ritz0.py` for
the module under test plus a small `main()` that calls it, `clang -c -g` each
`.ll`, then link with `-nostdlib -no-pie` against the runtime object in
`projects/ritz/runtime/`, and run `gdb` on the result.

If per-module test binaries are wanted as a first-class feature, that is a
`build.py` change — and fixing `-g` to actually keep its artifacts is the
prerequisite. Do not document either as if it already works.

## Phase Progression

All six planned phases are complete — squeeze's public README described phases 3
and 4 as "in progress" long after this list said otherwise; the README has been
corrected to match. (`TODO.md`, referenced here previously, no longer exists;
work tracking is in AGAST.)

1. **Foundations** - CRC32, Adler32, BitReader/Writer ✅
2. **Huffman** - Decoding tables, encoding tables, code generation ✅
3. **Deflate** - Inflate (decompress), Deflate (compress), Dynamic Huffman ✅
4. **Containers** - Gzip format, Zlib format ✅
5. **Streaming** - GzipReader/Writer, ZlibReader/Writer ✅
6. **SIMD** - CRC32, Adler-32, hashchain acceleration ✅

## Related Projects

- **ritz** — Ritz compiler (`projects/ritz`)
- **ritzunit** — Test framework (`projects/ritzunit`, **not**
  `projects/ritz/ritzunit`, which does not exist)
- **valet** — HTTP server that uses squeeze (`projects/valet`)
- **cryptosec** — Cryptographic library (`projects/cryptosec`; similar structure,
  good reference)
- **ritzlib** — Standard library modules (`projects/ritz/ritzlib`; also reachable
  as `projects/ritzlib`, which is a symlink)

## Notes

- All code should be valgrind-clean
- The dependency cache lives at `projects/ritz/.ritz-cache/` (and a sibling per
  compiler). Clear it if you see stale constant values; `./rz clean squeeze` is
  the supported way.
- Use `"string"` for StrView literals (not `c"string"`)
- Use `[[test]]` attribute syntax (not `@test`)
