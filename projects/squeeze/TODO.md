# Squeeze - Compression Library for Ritz

A high-performance compression library for the Ritz programming language.

## Design Principles

1. **TDD** - Tests written first using `@test` framework (ritzunit)
2. **Zero-copy where possible** - Minimize allocations in hot paths
3. **Streaming support** - Process data in chunks for large files
4. **Standards compliant** - RFC conformance with test vectors
5. **SIMD acceleration** - AVX2/AVX-512 for bulk operations (future)

## Test Status

**132 tests passing** via ritzunit:
- Adler-32: 12 tests
- Adler-32 SIMD: 10 tests
- Bit Stream: 19 tests
- CRC32: 17 tests
- CRC32 SIMD: 13 tests
- Deflate: 11 tests
- Gzip: 13 tests
- Huffman: 13 tests
- Inflate: 11 tests
- Zlib: 13 tests

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
- **Compression** - Stored blocks + fixed Huffman with LZ77 hash chains

### Phase 4: Container Formats ✅
- **Gzip (RFC 1952)** - Full header/trailer with CRC32 validation
- **Zlib (RFC 1950)** - CMF/FLG header with Adler-32 validation

---

## Future Enhancements

### Compression Quality
- [ ] Dynamic Huffman encoding (Type 2 blocks)
- [ ] Lazy matching for better compression ratios
- [ ] Optimal parsing (advanced)

### Streaming API
- [ ] `GzipReader` / `GzipWriter` for large files
- [ ] `ZlibReader` / `ZlibWriter` for large files
- [ ] Fixed memory footprint streaming

### Performance Optimizations
- [x] **SIMD CRC32** - PCLMULQDQ folding + Barrett reduction (13 tests passing)
- [x] **SIMD Adler-32** - Vectorized sum accumulation using PSADBW (10 tests passing)
- [ ] **Vectorized hash chains** - Parallel match finding
- [ ] **Multi-symbol Huffman decode** - Process multiple symbols per iteration
- [ ] Runtime CPU feature detection

### Memory Optimizations
- [ ] Reusable compressor/decompressor state
- [ ] Memory pool for hash chain allocations
- [ ] Configurable window sizes

### Optional Features
- [ ] Zlib dictionary support (FDICT)
- [ ] Gzip multi-member support
- [ ] Raw deflate API (no container)

---

## Test Vectors

- RFC 1951 (Deflate) examples
- RFC 1952 (Gzip) examples
- zlib test suite
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

*Last updated: 2026-02-12*
