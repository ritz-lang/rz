# Zeus

Zero-copy process runner for Ritz - shared memory ring buffer IPC between Valet and isolated worker processes.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

## Overview

Zeus provides secure process isolation for Ritz web applications. Rather than running application code in the same process as the HTTP server, Zeus spawns isolated worker processes that communicate with Valet via shared memory ring buffers. Request and response data never leaves shared memory - only pointers and offsets cross the process boundary, achieving zero-copy data transfer.

This architecture means a crashing worker process cannot take down the HTTP server. Zeus handles worker restarts, load balancing across multiple workers, and resource limits. It is the process management and IPC layer that sits between Valet (HTTP) and Spire (application framework) in the full Ritz stack.

Named as a hat tip to the OG homies.

## Features

- Zero-copy IPC using shared memory SPSC ring buffers
- Worker process isolation - crashes don't affect Valet
- Automatic worker restarts on failure
- Multiple workers with round-robin or least-connections load balancing
- Request/response correlation via 64-bit IDs
- Data arena for body and header storage (bump allocator)
- Futex-based signaling with spin-then-block strategy
- No serialization overhead - data stays in shared memory
- Resource limits per worker process

## Installation

```bash
# As a dependency in ritz.toml:
# [dependencies]
# zeus = { path = "../zeus" }

# Build from source (run from the monorepo root; `rz` sets RITZ_PATH itself)
./rz build zeus
# Produces projects/zeus/build/debug/zeus and .../test_client
```

## Usage

```ritz
import zeus { Worker }

# In your Ritz application worker process
fn main() -> i32
    let worker = Worker.connect()
    worker.serve(fn(req: *Request) -> Response
        Response.new()
            .status(200)
            .body("Hello from Zeus!\n")
    )
    0
```

## Memory Layout

```
Shared Memory Region (configurable, default 64MB)
+---------------------------+
|  Control Block (4KB)      |  Indices, flags, worker PID
+---------------------------+
|  Request Ring (N slots)   |  Valet -> Worker
+---------------------------+
|  Response Ring (N slots)  |  Worker -> Valet
+---------------------------+
|  Data Arena               |  Request/response bodies and headers
+---------------------------+
```

## Dependencies

- `ritzunit` - Test framework

## Status

**Active development**, further along than "Alpha — design defined", which is
what this README said while the binary was already building and running.

Measured 2026-09-12: `./rz build zeus` exits 0, producing `zeus` and
`test_client`; `zeus --help` prints its full option list. `lib/` holds 15
modules and the project carries 178 `[[test]]` markers across 17 test files.
Run `./rz test zeus` for the current pass count.

zeus is also the **only** application project that is green in all three
compiler columns: ritz0, ritz1 and ritz1_selfhosted each build it at exit 0
(after `./rz clean zeus`, which is required — see
[docs/STACK_MATRIX.md](../../docs/STACK_MATRIX.md) and AGAST #1360). valet
reverse-proxies to zeus via `valet -z <socket>`.

## License

MIT License - see LICENSE file
