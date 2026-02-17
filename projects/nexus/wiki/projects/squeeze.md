# Squeeze

High-performance gzip/deflate/zlib compression. 132 tests passing. Production ready.

---

## Overview

Squeeze is a pure-Ritz implementation of the gzip, deflate, and zlib compression formats. It includes SIMD-accelerated checksum implementations for maximum performance.

---

## Where It Fits

```
Valet
└── Squeeze (HTTP response compression)

Tempest
└── Squeeze (HTTP content-encoding decompression)
```

---

## Standards Support

| Algorithm | Standard | Status |
|-----------|----------|--------|
| CRC-32 | ISO 3309 | Production + SIMD |
| Adler-32 | RFC 1950 | Production + SIMD |
| DEFLATE | RFC 1951 | Production |
| GZIP | RFC 1952 | Production |
| ZLIB | RFC 1950 | Production |

All implementations are correct against the respective RFCs and validated with the 132-test suite.

---

## Performance

### SIMD Acceleration

| Operation | Instruction Set | Speedup |
|-----------|-----------------|---------|
| CRC-32 | PCLMULQDQ "carry-less multiply" folding | ~15x vs scalar |
| Adler-32 | PSADBW vectorized sum of absolute differences | ~4x vs scalar |

The SIMD paths are selected automatically at runtime based on CPU feature detection.

### CRC-32 PCLMULQDQ

The PCLMULQDQ technique processes 16 bytes at a time using the carry-less multiply instruction to compute the CRC polynomial. Multiple independent streams are folded together, hiding instruction latency.

---

## Usage

### Compress a Buffer

```ritz
import squeeze.gzip { gzip_compress, gzip_decompress }
import squeeze.deflate { deflate_compress, deflate_decompress }
import squeeze.zlib { zlib_compress, zlib_decompress }

# Gzip
let data: Vec<u8> = ...
let compressed = gzip_compress(data)
let decompressed = gzip_decompress(compressed)?

# Deflate
let compressed = deflate_compress(data)
let decompressed = deflate_decompress(compressed)?
```

### Stream Compression

```ritz
import squeeze.gzip { GzipEncoder, GzipDecoder }

# Compress incrementally
var encoder = GzipEncoder.new()
encoder.write(chunk1)
encoder.write(chunk2)
let compressed = encoder.finish()

# Decompress incrementally
var decoder = GzipDecoder.new()
decoder.write(compressed_chunk)
let decompressed = decoder.flush()?
```

### Compute Checksums

```ritz
import squeeze.crc32 { crc32 }
import squeeze.adler32 { adler32 }

let data: Vec<u8> = ...
let crc = crc32(data)
let adler = adler32(data)
```

---

## Integration with Valet

Valet automatically compresses responses when:
- The client sends `Accept-Encoding: gzip` or `Accept-Encoding: deflate`
- The response body is larger than the configured threshold (default: 1024 bytes)
- The content type is compressible (text/html, application/json, etc.)

```ritz
# In Valet's response pipeline
fn maybe_compress(resp:& Response, req: Request) -> ()
    if req.accepts_encoding("gzip") and resp.body.len() > 1024
        resp.body = gzip_compress(resp.body)
        resp.headers.set("Content-Encoding", "gzip")
        resp.headers.set("Content-Length", resp.body.len().to_string())
```

---

## DEFLATE Format

DEFLATE (RFC 1951) is the underlying compression algorithm. It combines LZ77 (a sliding window dictionary scheme) with Huffman coding:

1. **LZ77** — Finds repeated byte sequences and replaces them with (offset, length) back-references into a sliding window
2. **Huffman coding** — Encodes literals and back-references using variable-length codes optimized for the data distribution

GZIP (RFC 1952) adds a file header, trailer, and CRC-32 checksum around DEFLATE data.

ZLIB (RFC 1950) adds an Adler-32 checksum around DEFLATE data.

---

## Test Coverage

132 tests covering:

- Round-trip compression/decompression for all formats
- CRC-32 correctness (scalar and SIMD paths must agree)
- Adler-32 correctness (scalar and SIMD paths must agree)
- Edge cases: empty input, single byte, repetitive data
- Compatibility: outputs readable by system gzip/gunzip
- Streaming API correctness

---

## Current Status

Production ready. Used by Valet for HTTP compression and by Tempest for content-encoding decompression.

---

## Related Projects

- [Cryptosec](cryptosec.md) — Often deployed alongside Squeeze
- [Valet](valet.md) — Uses Squeeze for HTTP response compression
- [Tempest](tempest.md) — Uses Squeeze to decompress HTTP responses
- [Security Subsystem](../subsystems/security.md)
