# http

HTTP protocol implementation for Ritz - the mechanism layer for HTTP/1.0, HTTP/1.1, HTTP/2, and HTTP/3.

## Overview

`http` is the wire protocol library that handles parsing, framing, and codec operations for all HTTP versions. It provides the low-level mechanism bits while leaving policy decisions to higher-level libraries like [Valet](https://github.com/ritz-lang/valet).

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  http (this crate)                  │
├─────────────────────────────────────────────────────┤
│     h1 codec    │    h2 codec    │    h3 codec     │
├─────────────────┼────────────────┼─────────────────┤
│       TCP       │      TCP       │      QUIC       │
├─────────────────┴────────────────┴─────────────────┤
│              cryptosec  │  squeeze                 │
└────────────────────────────────────────────────────┘
```

## Features

### HTTP/1.0 & HTTP/1.1
- Request/response parsing
- Chunked transfer encoding
- Keep-alive connection management
- Pipelining support

### HTTP/2
- Binary framing layer
- Stream multiplexing
- HPACK header compression
- Flow control
- Server push
- Priority handling

### HTTP/3
- QUIC transport (implemented from scratch)
- QPACK header compression
- Connection migration
- 0-RTT resumption
- Per-stream flow control

## Dependencies

- [`cryptosec`](https://github.com/ritz-lang/cryptosec) - TLS 1.3 and cryptographic primitives
- [`squeeze`](https://github.com/ritz-lang/squeeze) - Compression algorithms

## Design Philosophy

This library is **mechanism, not policy**:

| Layer | Library | Role |
|-------|---------|------|
| Mechanism | `http` | Wire protocol, parsing, framing |
| Policy | `Valet` | Routing, middleware, server config |
| Runtime | `Zeus` | Process isolation, zero-copy IPC |

## Usage

```ritz
use http::{Request, Response, Version}
use http::h1::parse_request
use http::h2::Frame

// Parse HTTP/1.1 request
let req = parse_request(buffer)?

// Build response
let resp = Response::new()
    .status(200)
    .header("Content-Type", "text/plain")
    .body("Hello, world!")
```

## Status

**Early Development** - Core types and H1 codec in progress.

## License

MIT
