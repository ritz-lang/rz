# Squeeze - Completed Work

## Project Setup (2026-01-15)

- [x] Created project structure (lib/, test/, fixtures/)
- [x] Added ritz compiler as submodule
- [x] Created build.sh script
- [x] Created README.md with API overview and integration docs
- [x] Created CLAUDE.md with development guide
- [x] Created TODO.md with phased development roadmap

---

## Phase 1: Foundations

### 1.1 CRC32 (2026-01-15)
- [x] `crc32_init()` - Initialize CRC state (0xFFFFFFFF)
- [x] `crc32_update(state, data, len)` - Process data chunk (table-driven)
- [x] `crc32_final(state)` - Get final checksum (XOR 0xFFFFFFFF)
- [x] `crc32(data, len)` - One-shot convenience function
- [x] Lookup table generation (256-entry)
- [x] Tests with known vectors (17 tests)
  - Standard check value: "123456789" = 0xCBF43926
  - Empty input, single bytes, ASCII strings
  - Streaming API (multi-chunk updates)
  - Binary data verification
  - All vectors verified against Python binascii.crc32

### 1.2 Bit Stream Reader/Writer (2026-01-15)
- [x] `BitReader` struct (data pointer, length, byte/bit position)
- [x] `bits_reader_init(data, len)` - Initialize reader
- [x] `bits_read(reader, n)` - Read n bits (1-32), LSB-first
- [x] `bits_peek(reader, n)` - Peek without advancing position
- [x] `bits_skip(reader, n)` - Skip n bits efficiently
- [x] `bits_available(reader)` - Return remaining bits
- [x] `BitWriter` struct (data pointer, capacity, byte/bit position, current byte)
- [x] `bits_writer_init(data, cap)` - Initialize writer
- [x] `bits_write(writer, value, n)` - Write n bits (1-32), LSB-first
- [x] `bits_flush(writer)` - Flush partial byte to buffer
- [x] `bits_written(writer)` - Return bytes written
- [x] Tests for bit manipulation (19 tests)
  - Single bit, full byte, cross-byte reads
  - LSB-first ordering (Deflate-compatible)
  - Peek without advancing, skip operations
  - Writer with flush and round-trip verification
  - Edge cases (zero bits, available count)

---

## Phase 2: Huffman Coding

### 2.1 Huffman Decoding (2026-01-15)
- [x] `HuffmanTable` struct (9-bit lookup table, overflow for longer codes)
- [x] `huffman_build_decode_table(lengths, num_symbols)` - Build canonical Huffman decode table
- [x] `huffman_decode(table, reader)` - Decode single symbol using lookup table
- [x] Canonical Huffman code generation from code lengths
- [x] Bit reversal for LSB-first ordering (Deflate-compatible)
- [x] Tests with simple codes (4-symbol table)
- [x] Tests with Deflate fixed Huffman codes (EOB, literals)

### 2.2 Huffman Encoding (2026-01-15)
- [x] `HuffmanEncodeTable` struct (code and length per symbol)
- [x] `huffman_build_encode_table(lengths, num_symbols)` - Build encode table
- [x] `huffman_encode(table, symbol, writer)` - Encode symbol to bit stream
- [x] `huffman_count_frequencies(data, len, freqs)` - Count byte occurrences
- [x] Round-trip tests (encode then decode)
- [x] 13 tests total, all passing

---

## Phase 3: Deflate (RFC 1951)

### 3.1 Deflate Decompression (2026-01-15)
- [x] `inflate(input, len, output, cap)` - Main decompression entry point
- [x] Block header parsing (BFINAL, BTYPE)
- [x] Type 0 (Stored): Uncompressed blocks with LEN/NLEN validation
- [x] Type 1 (Fixed Huffman): Pre-defined canonical Huffman tables
  - Literal/length codes (0-287): 8/9/7/8 bits per RFC 1951 Section 3.2.6
  - Distance codes (0-29): 5 bits each
- [x] Type 2 (Dynamic Huffman): Self-describing Huffman tables
  - Code length code decoding (HLIT, HDIST, HCLEN)
  - Run-length encoding (codes 16, 17, 18)
  - Custom literal/length and distance table construction
- [x] LZ77 back-reference decoding
  - Length codes 257-285 with extra bits
  - Distance codes 0-29 with extra bits
  - Sliding window copy (supports overlapping RLE)
- [x] Error handling
  - Invalid block type (BTYPE=11)
  - Truncated input
  - NLEN mismatch in stored blocks
  - Invalid Huffman codes
  - Invalid distance references
- [x] Tests with zlib-generated data (11 tests)
  - Stored blocks: empty, "hello", multi-block
  - Fixed Huffman: "ab", "hello"
  - Back-references: "abcabc", "aaaaaaaa"
  - Dynamic Huffman: 65-byte sentence
  - Error cases: invalid block, truncated, NLEN mismatch

### 3.2 Deflate Compression (2026-02-12)
- [x] `deflate(input, len, output, cap, level)` - Main compression entry point
- [x] Level 0 (Stored): Uncompressed blocks with LEN/NLEN header
- [x] Levels 1-9 (Compressed): Fixed Huffman encoding
  - Type 1 block header (BFINAL=1, BTYPE=01)
  - Fixed literal/length codes (256-285)
  - Fixed distance codes (0-29)
- [x] LZ77 match finding with hash chains
  - 3-byte hash function
  - Hash table with 32K entries
  - Chain length varies by compression level (4/16/128)
  - Match lengths 3-258, distances 1-32768
- [x] Length/distance code tables with extra bits
- [x] Round-trip tests (11 tests)
  - Stored: empty, hello, block format
  - Fixed: hello, repetitive, long runs
  - Round-trip: binary (256 bytes), text (43 bytes)
  - Level comparison, error handling

---

## Infrastructure (2026-02-12)

### ritzunit Integration
- [x] Added ritzunit as git submodule for consistent test framework
- [x] Created `run_tests.sh` for building and running tests
- [x] Removed manual main() runners from test files (~400 lines)
- [x] Contributed fixes upstream to ritzunit (PR #3 merged):
  - WIFEXITED/WEXITSTATUS/WIFSIGNALED/WTERMSIG macros
  - signal_name() c-string literal fix

---

## Phase 4: Container Formats

### 4.1 Gzip (RFC 1952) (2026-02-12)
- [x] `gzip_compress(input, len, output, cap)` - Compress to gzip format
- [x] `gzip_decompress(input, len, output, cap)` - Decompress gzip
- [x] Header parsing/generation (RFC 1952 compliant):
  - Magic bytes (0x1f, 0x8b)
  - Compression method (CM = 8 for deflate)
  - Flags byte (FTEXT, FHCRC, FEXTRA, FNAME, FCOMMENT)
  - Modification time (MTIME), Extra flags (XFL), OS byte
- [x] Optional header field handling:
  - FEXTRA: Skip variable-length extra fields
  - FNAME: Skip null-terminated filename
  - FCOMMENT: Skip null-terminated comment
  - FHCRC: Skip 2-byte header CRC16
- [x] Trailer validation:
  - CRC32 checksum of uncompressed data
  - ISIZE original size (mod 2^32)
- [x] Error codes:
  - GZIP_ERR_BAD_MAGIC (-1)
  - GZIP_ERR_BAD_METHOD (-2)
  - GZIP_ERR_BAD_FLAGS (-3)
  - GZIP_ERR_TRUNCATED (-4)
  - GZIP_ERR_CRC_MISMATCH (-5)
  - GZIP_ERR_SIZE_MISMATCH (-6)
  - GZIP_ERR_INFLATE_FAILED (-7)
  - GZIP_ERR_DEFLATE_FAILED (-8)
  - GZIP_ERR_OUTPUT_FULL (-9)
- [x] Tests (13 tests):
  - Decompression: hello, empty, hello_world
  - Error handling: invalid magic, invalid method, truncated, CRC mismatch, size mismatch
  - Compression: hello, empty (header verification)
  - Round-trip: hello, text (43 bytes), binary (256 bytes)

### 4.2 Adler-32 Checksum (2026-02-13)
- [x] `adler32_init()` - Initialize state (A=1, B=0 packed as u32)
- [x] `adler32_update(state, data, len)` - Process data chunk
- [x] `adler32_final(state)` - Get checksum (identity function)
- [x] `adler32(data, len)` - One-shot convenience function
- [x] Modulo 65521 (largest prime < 2^16) arithmetic
- [x] Chunked processing to avoid overflow (NMAX = 5552 bytes)
- [x] Tests (12 tests):
  - Empty input, single bytes (0x00, 0xFF)
  - Wikipedia example ("Wikipedia" = 0x11E60398)
  - Python-verified vectors (hello, abc)
  - Streaming API (multi-chunk, byte-by-byte)
  - Large inputs (256 bytes, 1000 zeros, 1000 0xFF)

### 4.3 Zlib (RFC 1950) (2026-02-13)
- [x] `zlib_compress(input, len, output, cap)` - Compress to zlib format
- [x] `zlib_decompress(input, len, output, cap)` - Decompress zlib
- [x] Header parsing/generation (RFC 1950 compliant):
  - CMF byte: CM (bits 3-0) = 8 (deflate), CINFO (bits 7-4) = 7 (32K window)
  - FLG byte: FCHECK (bits 4-0) calculated so (CMF<<8|FLG) % 31 == 0
  - FLEVEL (bits 7-6): compression level hint
  - FDICT (bit 5): preset dictionary flag (unsupported)
- [x] Trailer: Adler-32 checksum in big-endian (unlike gzip's little-endian CRC32)
- [x] Error codes:
  - ZLIB_ERR_BAD_CM (-1)
  - ZLIB_ERR_BAD_CINFO (-2)
  - ZLIB_ERR_BAD_FCHECK (-3)
  - ZLIB_ERR_DICT_UNSUPPORTED (-4)
  - ZLIB_ERR_TRUNCATED (-5)
  - ZLIB_ERR_CHECKSUM_MISMATCH (-6)
  - ZLIB_ERR_INFLATE_FAILED (-7)
  - ZLIB_ERR_DEFLATE_FAILED (-8)
  - ZLIB_ERR_OUTPUT_FULL (-9)
- [x] Tests (13 tests):
  - Decompression: hello, empty, hello_world (Python-generated)
  - Error handling: invalid CM, invalid FCHECK, truncated, checksum mismatch, FDICT set
  - Compression: hello, empty (header verification)
  - Round-trip: hello, text (43 bytes), binary (256 bytes)

---

## SIMD Acceleration (2026-02-12)

### SIMD Adler-32 Implementation
- [x] `lib/adler32_simd.ritz` - SIMD-accelerated Adler-32 checksum
  - Uses PSADBW (simd_sad) instruction for horizontal byte summation
  - Processes 16 bytes per SIMD iteration
  - Falls back to scalar for remainder bytes
  - Maintains NMAX chunking for overflow prevention
- [x] Test suite (`test/test_adler32_simd.ritz`) - 10 tests
  - Verifies SIMD results match scalar implementation
  - Tests edge cases: empty, single byte, 16/17/32/100 bytes
  - Tests all-zeros, all-ones, streaming mode

### Ritz Compiler Fixes
- [x] Added `Grouped` AST class for parenthesized constant expressions
  - Fixes `AttributeError: module 'ritz_ast' has no attribute 'Grouped'`
  - Allows expressions like `[1 << 9]u8` in array size declarations
- [x] Fixed deflate.ritz constant naming conflict
  - Renamed LENGTH_BASE/EXTRA, DIST_BASE/EXTRA to DEF_* prefix
  - Prevents collision when both inflate and deflate are imported
- [x] Fixed SIMD stack alignment crash (SIGSEGV) (2026-02-12)
  - Root cause: LLVM's `movaps` instruction requires 16-byte aligned memory
  - When SIMD registers spill to stack, unaligned stack causes crash
  - Fix: Added `alignstack(16)` attribute to functions using SIMD types/intrinsics
  - Implementation: Post-process LLVM IR to add alignstack(16) to SIMD functions
  - Tracks functions using SIMD via `simd_functions` set in emitter

---

*Last updated: 2026-02-13*
