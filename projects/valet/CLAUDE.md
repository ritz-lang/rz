# Valet - Claude Code Context

## Project Overview

**Valet** is a high-performance async HTTP/1.1 server written in Ritz, demonstrating systems programming with io_uring.

## Quick Reference

```bash
# Environment setup
export RITZ_PATH=/home/aaron/dev/nevelis/langdev

# Build
./build.sh              # Release (-O2)
./build.sh --debug      # Debug (-O0)
./build.sh --profile    # Profile (-O2 -g)

# Run
./valet                 # Default: port 8080, single worker
./valet -p 3000         # Custom port
./valet -w 4            # 4 worker processes
./valet -m              # Multishot accept (kernel 5.19+)
./valet -w 4 -m         # Combined: 4 workers + multishot

# Test
./tests/run_all.sh      # Run test suite
wrk -t4 -c100 -d10s http://localhost:8080/  # Benchmark
```

## Architecture

```
src/main.ritz           Entry point, CLI parsing, route registration
lib/valet.ritz          High-level Valet API, connection handler, global context
lib/router.ritz         URL routing (exact, prefix, parameter patterns)
lib/request.ritz        Zero-copy HTTP request parser
lib/response.ritz       Response builder (buffer + vectored I/O)
```

### Dependencies (from ritzlib)

| Module | Purpose |
|--------|---------|
| `async_tasks.ritz` | TaskPool, TaskServer, event loop |
| `uring.ritz` | io_uring syscall wrappers |
| `async_net.ritz` | TCP socket helpers |
| `iovec.ritz` | Vectored I/O builder |
| `args.ritz` | CLI argument parsing |

## Routing Framework

Routes are registered via the Valet API:

```ritz
var app: Valet
valet_init(&app, 8080)
valet_get(&app, "/", handle_index)              # Exact match
valet_get(&app, "/users/:id", handle_user)      # Parameter capture
valet_get(&app, "/static/*", handle_static)     # Prefix match
valet_run(&app)
```

### Route Handlers

Handlers have signature `fn(path: *u8, path_len: i32) -> i32` and use context helpers:

```ritz
fn handle_user(path: *u8, path_len: i32) -> i32
    var id_buf: [64]u8
    ctx_param(0, &id_buf[0], 64)   # Get captured :id
    return ctx_ok("User found")    # Send 200 OK

fn handle_json(path: *u8, path_len: i32) -> i32
    return ctx_json(200, json_ptr, json_len)
```

### Context Helpers

| Function | Description |
|----------|-------------|
| `ctx()` | Get handler context pointer |
| `ctx_param(idx, buf, len)` | Get captured route parameter |
| `ctx_ok(body)` | Send 200 OK with text body |
| `ctx_text(status, body)` | Send text response with status |
| `ctx_json(status, json, len)` | Send JSON response |
| `ctx_not_found()` | Send 404 Not Found |

## Connection State Machine

```
CONN_STATE_RECV (0)  →  Read request into buffer
CONN_STATE_PARSE (1) →  Parse HTTP, route, call handler
CONN_STATE_SEND (2)  →  Send response, then:
                        - Keep-alive: back to RECV
                        - Max requests: shutdown
```

## Current Endpoints (Default)

| Path | Response | Notes |
|------|----------|-------|
| `/` | "Hello, World!" | Benchmark endpoint |
| `/hello` | "Hello from Valet!" | Text response |
| `/json` | `{"msg":"Hello Valet"}` | JSON response |
| `/users/:id` | "User ID: {id}" | Parameter capture |
| `/echo/:msg` | "{msg}" | Echo parameter |
| `*` | 404 Not Found | Default |

## Ritz Language Notes

```ritz
# Imports
import ritzlib.io
import lib.valet

# Structs
struct Request
    method_ptr: *u8
    method_len: i32

# Functions (no null global pointer init)
var g_ptr: i64 = 0  # Use i64 and cast
fn get_ptr() -> *T
    return g_ptr as *T

# Handler pattern
fn handler(path: *u8, path_len: i32) -> i32
    return ctx_ok("Hello!")
```

## Build System

`build.sh` uses the Ritz compiler pipeline:

1. `list_deps.py` - Resolve import graph
2. `ritz0.py` - Compile `.ritz` → `.ll` (LLVM IR)
3. `clang-19` - Compile `.ll` → `.o`
4. `clang` - Link with `-nostdlib -no-pie` (Ritz provides `_start`)

Object files cached in `.build/`, metadata in `.ritz-cache/`.

## Performance Features

- **io_uring**: Kernel async I/O, no syscall overhead per operation
- **Multishot accept**: Single SQE generates multiple CQEs (kernel 5.19+)
- **SO_REUSEPORT**: Multiple workers share listening socket
- **TCP_NODELAY**: Disable Nagle for low latency
- **Keep-alive**: Up to 100 requests per connection
- **Zero-copy responses**: Vectored I/O points to .rodata strings
- **~250k+ req/s**: Single worker benchmark on localhost

## Profiling

```bash
# Build with symbols
./build.sh --profile

# Callgrind
valgrind --tool=callgrind ./valet &
wrk -t1 -c10 -d5s http://localhost:8080/
pkill valet
kcachegrind callgrind.out.*
```

## Next Steps (Roadmap)

1. ~~**Routing framework**~~ ✅ Pattern matching, route handlers
2. **Static file serving** - Async file I/O, MIME types
3. **Request body parsing** - Content-Length, chunked encoding
4. **Middleware** - Logging, compression hooks
5. **Graceful shutdown** - Signal handling

## Related Projects

- **langdev** (`/home/aaron/dev/nevelis/langdev`) - Ritz compiler and stdlib
- **TLS library** (planned) - Separate Ritz project for crypto/TLS
