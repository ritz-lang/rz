# Squeeze

High-performance compression library for Ritz - gzip, deflate, and zlib implemented in pure Ritz.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Squeeze provides RFC-compliant compression and decompression for the Ritz ecosystem. It implements the Deflate algorithm (RFC 1951) with LZ77 match finding and Huffman coding, wrapped in the Gzip (RFC 1952) and Zlib (RFC 1950) container formats.

The primary use case is HTTP Content-Encoding compression in the Valet web server, where squeeze handles `gzip` and `deflate` transfer encodings. The streaming API allows processing data incrementally without buffering entire payloads in memory.

Squeeze is a pure Ritz implementation with no C dependencies, targeting both correctness (full RFC conformance) and performance (zero-copy streaming, future SIMD acceleration).

## Features

- Deflate compression and decompression (RFC 1951)
- Gzip container format with CRC-32 checksums (RFC 1952)
- Zlib container format with Adler-32 checksums (RFC 1950)
- Streaming API for incremental processing of large data
- Multiple compression levels (0=store, 1=fast, 6=balanced, 9=best)
- LZ77 with hash chain match finding
- Fixed and dynamic Huffman coding
- HTTP Content-Encoding integration (Accept-Encoding parsing)
- No external dependencies - pure Ritz

## Installation

```bash
# As a dependency in ritz.toml:
# [dependencies]
# squeeze = { path = "../squeeze" }

# Build from source
export RITZ_PATH=/path/to/ritz
./ritz build .
```

## Usage

```ritz
import lib.gzip
import lib.crc32

# One-shot gzip compression
var out_len: i64 = 0
let compressed: *u8 = gzip_compress(data, len, &out_len)

# Streaming decompression
var inflater: Inflater
gzip_init(&inflater, compressed, compressed_len)
while gzip_read(&inflater, buf, buf_size) > 0
    # process decompressed chunk
```

```ritz
import lib.deflate

# Compression with explicit level
var deflater: Deflater
deflate_init(&deflater, DEFLATE_LEVEL_6)  # balanced
deflate(&deflater, input, input_len, output, &output_len)
deflate_finish(&deflater)
```

```ritz
import lib.crc32

# Incremental CRC-32 checksum
var state: u32 = crc32_init()
state = crc32_update(state, chunk1, len1)
state = crc32_update(state, chunk2, len2)
let checksum: u32 = crc32_final(state)
```

## Dependencies

- `ritzlib` - Standard library

## Status

**Active development** - CRC-32, Adler-32, bit stream I/O, and Huffman tables are implemented. Deflate compression/decompression and Gzip/Zlib container support are in progress as part of Valet HTTP integration.

## License

MIT License - see LICENSE file
