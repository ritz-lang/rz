# Squeeze - Compression Library for Ritz

A high-performance compression library for the Ritz programming language.

## Design Principles

1. **TDD** - Tests written first using `[[test]]` framework (ritzunit)
2. **Zero-copy where possible** - Minimize allocations in hot paths
3. **Streaming support** - Process data in chunks for large files
4. **Standards compliant** - RFC conformance with test vectors
5. **SIMD acceleration** - AVX2/AVX-512 for bulk operations

## Test Status

**199 tests passing** via ritzunit:

| Module | Tests |
|--------|-------|
| Adler-32 | 12 |
| Adler-32 SIMD | 10 |
| Bit Stream | 33 |
| CRC32 | 17 |
| CRC32 SIMD | 13 |
| Cross-validation | 13 |
| Deflate | 17 |
| Gzip | 13 |
| Gzip Stream | 10 |
| Hashchain SIMD | 6 |
| Huffman | 13 |
| Inflate | 11 |
| Squeeze | 8 |
| Zlib | 13 |
| Zlib Stream | 10 |

Run with: `./run_tests.sh`

---

## Completed Features

### Phase 1: Foundations ✅
- **CRC32** - Table-driven checksum with streaming API
- **Bit Streams** - LSB-first reader/writer for Deflate compatibility

### Phase 2: Huffman Coding ✅
- **Decoding** - 9-bit lookup table for fast symbol resolution
- **Encoding** - Canonical Huffman code generation

### Phase 3: Deflate (RFC 1951) ✅
- **Decompression** - All block types (stored, fixed, dynamic Huffman)
- **Compression** - Stored blocks, fixed Huffman, and dynamic Huffman with LZ77 hash chains

### Phase 4: Container Formats ✅
- **Gzip (RFC 1952)** - Full header/trailer with CRC32 validation
- **Zlib (RFC 1950)** - CMF/FLG header with Adler-32 validation

### Phase 5: Streaming API ✅
- **GzipWriter** - Incremental compression with persistent LZ77 state
- **GzipReader** - Incremental decompression with buffering
- **ZlibWriter** - Streaming zlib compression with Adler-32
- **ZlibReader** - Streaming zlib decompression with checksum verification
- **Fixed memory footprint** - No dynamic allocation after init
- **Valet integration** - Used for HTTP chunked transfer compression

### Phase 6: SIMD Acceleration ✅
- **SIMD CRC32** - PCLMULQDQ folding + Barrett reduction (13 tests)
- **SIMD Adler-32** - Vectorized sum accumulation using PSADBW (10 tests)
- **Hashchain SIMD** - Vectorized hash chain operations (6 tests)

---

## Future Enhancements

### Compression Quality
- [ ] Lazy matching for better compression ratios
- [ ] Optimal parsing (advanced)

### Performance Optimizations
- [ ] **Multi-symbol Huffman decode** - Process multiple symbols per iteration
- [ ] Runtime CPU feature detection (CPUID-based dispatch)

### Memory Optimizations
- [ ] Reusable compressor/decompressor state pools
- [ ] Memory pool for hash chain allocations
- [ ] Configurable window sizes (16K/32K/64K)

### Optional Features
- [ ] Zlib dictionary support (FDICT)
- [ ] Gzip multi-member support
- [ ] Raw deflate API (no container)

---

## Test Vectors

- RFC 1951 (Deflate) examples
- RFC 1952 (Gzip) examples
- zlib test suite
- Cross-validation against system gzip/zlib
- Corpus files (Calgary, Silesia, Canterbury)
- Fuzzing with AFL/libFuzzer

---

## References

- [RFC 1951 - DEFLATE](https://tools.ietf.org/html/rfc1951)
- [RFC 1952 - GZIP](https://tools.ietf.org/html/rfc1952)
- [RFC 1950 - ZLIB](https://tools.ietf.org/html/rfc1950)
- [zlib source](https://github.com/madler/zlib)
- [zlib-ng (optimized)](https://github.com/zlib-ng/zlib-ng)
- [An Explanation of the Deflate Algorithm](https://zlib.net/feldspar.html)

---

*Last updated: 2026-02-16*
