# Valet

High-performance async HTTP server for Ritz, built on Linux io_uring for minimal syscall overhead.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Valet is the HTTP server layer of the Ritz ecosystem. It achieves high throughput by building directly on Linux io_uring for asynchronous I/O, eliminating per-request syscall overhead. Requests are handled with zero-copy parsing and vectored I/O responses.

Valet supports multi-process deployment with `SO_REUSEPORT` for kernel-level load balancing across worker processes. It integrates with squeeze for HTTP Content-Encoding compression and cryptosec for TLS 1.3 HTTPS support.

In the full Ritz application stack, Valet sits at the bottom as the raw HTTP/TCP layer, passing decoded requests up to Zeus (process isolation) and Spire (web framework). It can also be used standalone as a high-performance static file server or benchmark target.

## Features

- Async I/O built on Linux io_uring - minimal syscall overhead
- Zero-copy HTTP/1.1 request parsing
- Vectored I/O responses via writev
- Multi-process workers with SO_REUSEPORT load balancing
- HTTP keep-alive connection reuse
- Multishot accept for kernel 5.19+ (single syscall for all connections)
- Integration with squeeze for gzip/deflate compression
- Integration with cryptosec for TLS 1.3

## Installation

```bash
# Requires Linux 5.1+ (io_uring) and clang
export RITZ_PATH=/path/to/ritz
./ritz build .

# Or build with the included script
./build.sh
```

## Usage

```bash
# Single worker on default port 8080
./build/debug/valet

# Custom port
./build/debug/valet -p 3000

# 4 workers for multi-core throughput
./build/debug/valet -w 4

# 4 workers with multishot accept (kernel 5.19+)
./build/debug/valet -m -w 4
```

```
Options:
  -p, --port PORT     Listen port (default: 8080)
  -w, --workers N     Number of worker processes (default: 1)
  -m, --multishot     Use multishot accept (kernel 5.19+)
  -h, --help          Show help message
```

```ritz
# Example route handler
import valet.server { serve }
import valet.request { Request }
import valet.response { Response, response_ok }

fn handle_request(req: *Request) -> Response
    response_ok("Hello from Valet!\n")

fn main() -> i32
    serve(8080, handle_request)
    0
```

## Dependencies

- `squeeze` - HTTP content compression (gzip, deflate)
- `cryptosec` - TLS 1.3 support

## Status

**Active development** - Core server loop, HTTP/1.1 parsing, io_uring integration, and multi-process workers are working. Routing, static file serving, and full TLS integration are in progress.

## License

MIT License - see LICENSE file
