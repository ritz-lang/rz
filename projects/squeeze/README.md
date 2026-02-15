# Squeeze

A high-performance compression library for [Ritz](./ritz), targeting HTTP compression for the [Valet](../valet) webserver.

## Goals

- **Deflate/Gzip support** for HTTP Content-Encoding
- **Pure Ritz implementation** - no C dependencies
- **Streaming API** - process data in chunks for large files
- **RFC compliant** - full conformance with RFC 1950/1951/1952
- **Zero-copy where possible** - minimize allocations in hot paths
- **SIMD acceleration** - AVX2/AVX-512 for bulk operations (future)

## Supported Formats

### Compression Algorithms
- Deflate (RFC 1951) - core compression
- LZ77 with hash chains for match finding
- Huffman coding (fixed and dynamic)

### Container Formats
- Gzip (RFC 1952) - standard `.gz` format with CRC32
- Zlib (RFC 1950) - wrapper with Adler-32 checksum

### HTTP Integration
- Content-Encoding: gzip, deflate
- Accept-Encoding header parsing
- Quality value (q=) handling

## Requirements

- Linux (uses Linux syscalls directly)
- Ritz compiler (sibling `ritz/` directory or `langdev`)
- x86-64 CPU (AVX2 for accelerated paths, future)

## Building

```bash
export RITZ_PATH=/path/to/langdev
./build.sh
```

## Testing

```bash
ritz test
```

## Project Structure

```
squeeze/
├── lib/              # Library modules
│   ├── crc32.ritz    # CRC-32 checksum (ISO 3309)
│   ├── adler32.ritz  # Adler-32 checksum
│   ├── bits.ritz     # Bit stream reader/writer
│   ├── huffman.ritz  # Huffman coding tables
│   ├── inflate.ritz  # Deflate decompression
│   ├── deflate.ritz  # Deflate compression
│   ├── gzip.ritz     # Gzip container format
│   └── zlib.ritz     # Zlib container format
├── test/             # Test files
├── fixtures/         # Test vectors (gzip files, corpus)
├── src/              # Example programs
│   └── main.ritz     # Demo/CLI entry point
├── build.sh
├── TODO.md           # Development roadmap
├── DONE.md           # Completed work
└── README.md
```

## API Overview

### CRC-32 (for Gzip)

```ritz
import lib.crc32

# One-shot
var checksum: u32 = crc32(data, len)

# Streaming
var state: u32 = crc32_init()
state = crc32_update(state, chunk1, len1)
state = crc32_update(state, chunk2, len2)
let final: u32 = crc32_final(state)
```

### Gzip Compression

```ritz
import lib.gzip

# One-shot compression
var out_len: i64 = 0
let compressed: *u8 = gzip_compress(data, len, &out_len)

# Streaming decompression
var inflater: Inflater
gzip_init(&inflater, compressed, compressed_len)
while gzip_read(&inflater, buf, buf_size) > 0
    # process decompressed data
```

### Deflate (Low-Level)

```ritz
import lib.deflate

# Compression with level
var deflater: Deflater
deflate_init(&deflater, DEFLATE_LEVEL_6)  # balanced
deflate(&deflater, input, input_len, output, &output_len)
deflate_finish(&deflater)

# Decompression
var inflater: Inflater
inflate_init(&inflater)
inflate(&inflater, compressed, comp_len, output, &out_len)
```

## Compression Levels

| Level | Strategy | Hash Chain Depth | Use Case |
|-------|----------|------------------|----------|
| 0 | Store only | N/A | No compression, just wrap |
| 1 | Fast | 4 | Speed priority |
| 6 | Default | 32 | Balanced speed/ratio |
| 9 | Best | 4096 | Maximum compression |

## Valet Integration

Squeeze will be integrated with Valet as a submodule for HTTP compression:

```bash
cd /path/to/valet
git submodule add git@github.com:ritz-lang/squeeze.git squeeze
```

### Compression Middleware

```ritz
import squeeze.gzip
import valet.middleware

# Automatic response compression
fn compression_middleware(req: *Request, res: *Response) -> i32
    let encoding: *u8 = accept_encoding_select(req)
    if encoding != null
        res.body = gzip_compress(res.body, res.body_len, &res.body_len)
        response_header(res, "Content-Encoding", "gzip")
    return MW_CONTINUE
```

**If additional functionality is needed:**
1. **File an issue**: https://github.com/ritz-lang/squeeze/issues
2. **Submit a PR**: Make changes in `./squeeze/` and submit to ritz-lang/squeeze

## Status

**Current Phase:** 1 - Foundations (CRC32, Bit Streams)

See [TODO.md](TODO.md) for detailed progress.

## References

- [RFC 1951 - DEFLATE](https://tools.ietf.org/html/rfc1951)
- [RFC 1952 - GZIP](https://tools.ietf.org/html/rfc1952)
- [RFC 1950 - ZLIB](https://tools.ietf.org/html/rfc1950)
- [An Explanation of the Deflate Algorithm](https://zlib.net/feldspar.html)
- [zlib source](https://github.com/madler/zlib)
- [zlib-ng (optimized)](https://github.com/zlib-ng/zlib-ng)

## License

TBD
