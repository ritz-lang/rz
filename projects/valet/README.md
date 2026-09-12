# Valet

High-performance async HTTP server for Ritz, built on Linux io_uring for minimal syscall overhead.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

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
# Requires Linux 5.1+ (io_uring) and clang.
# Run from the monorepo root; `rz` sets RITZ_PATH itself.
./rz build valet
# Produces projects/valet/build/debug/valet

# Release build
./rz build valet --release

# Run the test suite (5 .ritz test files, 99 [[test]] functions;
# takes several minutes)
./rz test valet
```

There is no `build.sh`; earlier revisions of this README documented one.

## Usage

```bash
# Single worker on default port 8080
./projects/valet/build/debug/valet

# Custom port
./projects/valet/build/debug/valet -p 3000

# 4 workers for multi-core throughput
./projects/valet/build/debug/valet -w 4

# 4 workers with multishot accept (kernel 5.19+)
./projects/valet/build/debug/valet -m -w 4
```

With no `valet.json` present the server prints `config: cannot open valet.json`
and continues with defaults — that warning is not an error.

```
Options (./projects/valet/build/debug/valet --help):
  -h, --help                 Show this help message
  -c, --config=FILE          Load configuration from JSON file
  -p, --port=PORT            Listen port (overrides config)
  -w, --workers=N            Number of worker processes (overrides config)
  -m, --multishot            Use multishot accept (kernel 5.19+)
  -z, --zeus-socket=PATH     Reverse-proxy mode: dispatch to a zeus daemon
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

**Active development** - Core server loop, HTTP/1.1 parsing, io_uring
integration, multi-process workers, routing (`lib/router.ritz`), static file
serving (`valet_static`), middleware (`valet_use`) and gzip/deflate compression
(`lib/compress.ritz`) are all implemented and present in `lib/`. A local smoke
test (`valet -p 8099`, then `curl`) returns HTTP 200. TLS lives in `lib/tls.ritz`
and `lib/tls/`; end-to-end HTTPS has not been measured here.

Throughput: `test/test_basic.sh` drives `wrk` against a single worker and
reported **28,108** and **34,850 req/s** across two runs on this machine on
2026-09-12 — single-digit-thousands of variance between runs, so treat any single
figure as indicative only. Do not quote numbers from older docs:
`projects/larb/README.md` carried an unsourced "1.47M req/sec" that nothing in
this repo reproduces, and `CLAUDE.md` claims "~250k+ req/s" with no recorded
measurement behind it either.

## License

MIT License - see LICENSE file
