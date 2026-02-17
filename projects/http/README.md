# http

HTTP protocol implementation for Ritz - wire protocol, parsing, and framing for HTTP/1.x, HTTP/2, and HTTP/3.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

The `http` library provides the mechanism layer for HTTP: parsing request and response messages, encoding/decoding headers, managing connection framing, and implementing the protocol state machines for HTTP/1.1, HTTP/2, and HTTP/3. It deliberately handles only the wire protocol, leaving policy decisions (routing, middleware, server configuration) to higher-level libraries like Valet.

HTTP/2 support includes the full binary framing layer with stream multiplexing, HPACK header compression, and flow control. HTTP/3 implements QUIC transport from scratch alongside QPACK header compression and 0-RTT session resumption. The library uses cryptosec for TLS 1.3 and squeeze for content compression.

## Features

- HTTP/1.0 and HTTP/1.1 request/response parsing
- Chunked transfer encoding
- Keep-alive connection management
- HTTP pipelining support
- HTTP/2 binary framing and stream multiplexing
- HPACK header compression (HTTP/2)
- HTTP/2 flow control and server push
- HTTP/3 over QUIC transport
- QPACK header compression (HTTP/3)
- QUIC connection migration and 0-RTT resumption
- TLS 1.3 integration via cryptosec
- Content-Encoding via squeeze

## Installation

```bash
# As a dependency in ritz.toml:
# [dependencies]
# http = { path = "../http" }

# Build from source
export RITZ_PATH=/path/to/ritz
./ritz build .
```

## Usage

```ritz
import lib.h1 { parse_request, RequestParser }
import lib.h2 { Frame, FrameType }

# Parse HTTP/1.1 request from buffer
let parser = RequestParser.new(buffer, buffer_len)
let req = parser.parse()

# Build HTTP/1.1 response
let resp = Response.new()
    .status(200)
    .header("Content-Type", "text/plain")
    .body("Hello, world!")
let bytes = resp.encode()
```

```ritz
import lib.h2 { Connection, StreamId }

# HTTP/2 connection
let conn = Connection.new(socket, Role.Server)
conn.send_settings()

# Handle incoming frames
let frame = conn.read_frame()
match frame.frame_type
    FrameType.Headers => handle_headers(frame)
    FrameType.Data    => handle_data(frame)
    FrameType.GoAway  => close_connection()
```

## Dependencies

- `ritzlib` - Standard library
- `cryptosec` - TLS 1.3 support
- `squeeze` - Content-Encoding compression

## Status

**Alpha** - Core type definitions, HTTP/1.1 parser, and basic response building are in progress. HTTP/2 framing, HTTP/3/QUIC, and full TLS integration are planned in subsequent phases.

## License

MIT License - see LICENSE file
