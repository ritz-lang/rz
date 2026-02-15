# Zeus

Zero-copy process runner for Ritz applications. Shared memory ring buffer IPC between Valet and isolated worker processes.

## Overview

Zeus provides secure process isolation for Ritz web applications. Instead of running user code in the same process as Valet, Zeus spawns isolated worker processes that communicate via shared memory ring buffers - achieving zero-copy data transfer for maximum performance.

Named as a hat tip to the OG homies.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Valet (Policy)                    │
│            routing, TLS, load balancing             │
└───────────────────────┬─────────────────────────────┘
                        │
            ┌───────────▼───────────┐
            │    Shared Memory      │
            │  ┌─────────────────┐  │
            │  │  Request Ring   │  │  Valet → Worker
            │  └─────────────────┘  │
            │  ┌─────────────────┐  │
            │  │  Response Ring  │  │  Worker → Valet
            │  └─────────────────┘  │
            │  ┌─────────────────┐  │
            │  │   Data Arena    │  │  Bodies, headers
            │  └─────────────────┘  │
            └───────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                  Zeus Worker                        │
│           Your Ritz app (isolated)                  │
└─────────────────────────────────────────────────────┘
```

## Features

### Zero-Copy IPC
- Shared memory ring buffers (SPSC)
- Request/response data stays in place
- Only pointers/offsets cross the boundary
- No serialization overhead

### Process Isolation
- Worker crashes don't take down Valet
- Security boundary between server and app code
- Resource limits per worker
- Graceful worker restarts

### Multi-Worker Scaling
- N workers with dedicated ring pairs
- Round-robin or least-connections load balancing
- Work stealing (optional)
- Hot reload support

## Memory Layout

```
Shared Memory Region (configurable, e.g., 64MB)
┌─────────────────────────────────────────────────────┐
│  Control Block (4KB)                                │
│    req_write_idx, req_read_idx                      │
│    resp_write_idx, resp_read_idx                    │
│    flags, worker_pid, ...                           │
├─────────────────────────────────────────────────────┤
│  Request Ring (N slots)                             │
├─────────────────────────────────────────────────────┤
│  Response Ring (N slots)                            │
├─────────────────────────────────────────────────────┤
│  Data Arena                                         │
│    Request bodies, response bodies, headers         │
│    Bump allocator, freed on request completion      │
└─────────────────────────────────────────────────────┘
```

## Slot Structures

```ritz
struct RequestSlot {
    id: u64,              // Request correlation ID
    method: u8,           // HTTP method enum
    path_offset: u32,     // Offset into data arena
    path_len: u16,
    headers_offset: u32,
    headers_len: u16,
    body_offset: u32,
    body_len: u32,
    flags: u8,            // Streaming, keep-alive, etc.
}

struct ResponseSlot {
    id: u64,              // Correlates to request
    status: u16,          // HTTP status code
    headers_offset: u32,
    headers_len: u16,
    body_offset: u32,
    body_len: u32,
    flags: u8,            // Chunked, complete, error
}
```

## Signaling

| Platform | Wake Mechanism |
|----------|----------------|
| Linux | `futex` on control word |
| macOS | `dispatch_semaphore` / `pthread_cond` |
| Windows | `WaitOnAddress` / named semaphore |

Strategy: Spin briefly, then block. Most requests complete fast enough that spinning wins.

## Usage

```ritz
use zeus::{Worker, Config}

// In your Ritz app
pub fn main() {
    let worker = Worker::connect()?

    worker.serve(|req| {
        Response::new()
            .status(200)
            .body("Hello from Zeus!")
    })
}
```

## Status

**Early Development** - Ring buffer primitives and protocol design in progress.

## License

MIT
