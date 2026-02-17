# Zeus

Zero-copy process runner for Ritz - shared memory ring buffer IPC between Valet and isolated worker processes.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

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

# Build from source
export RITZ_PATH=/path/to/ritz
./ritz build .
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

**Alpha** - Ring buffer design and shared memory protocol are defined. Core IPC primitives and worker lifecycle management are being implemented. The full integration with Valet and Spire is in progress.

## License

MIT License - see LICENSE file
