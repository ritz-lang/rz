# Valet - Claude Code Context

## Project Overview

**Valet** is a high-performance async HTTP/1.1 server written in Ritz, demonstrating systems programming with io_uring.

## Quick Reference

All commands run from the **monorepo root** (`~/dev/ritz-lang/rz`). There is no
`build.sh` and no `RITZ_PATH` to export — `./rz` sets it. The old
`/home/aaron/dev/nevelis/langdev` path does not exist; that tree was
consolidated into this monorepo in February 2026.

```bash
# Build
./rz build valet              # Debug  -> projects/valet/build/debug/valet
./rz build valet --release    # Release -> projects/valet/build/release/valet

# Run
V=./projects/valet/build/debug/valet
$V                      # Default: port 8080, single worker
$V -p 3000              # Custom port
$V -w 4                 # 4 worker processes
$V -m                   # Multishot accept (kernel 5.19+)
$V -w 4 -m              # Combined: 4 workers + multishot
$V -c valet.json        # Load config from JSON
$V -z /run/zeus/zeus.sock   # Reverse-proxy to a zeus daemon
$V --help               # Authoritative option list

# Test
./rz test valet         # 5 .ritz test files, 99 [[test]] fns — exit 0, several minutes

# Benchmark
$V -p 8080 &
wrk -t4 -c100 -d10s http://localhost:8080/
```

With no `valet.json` present the server prints `config: cannot open valet.json`
and continues with defaults; that warning is not an error.

### Do not use `./test/run_all.sh`

It **exits 1 while printing "All tests passed!"** — the "All tests passed!" line
comes from the inner `test_basic.sh`, and then `run_all.sh` dies before running
`test_multishot.sh` or `test_workers.sh`. Cause: the script uses `set -e`
together with `((PASSED++))`; when `PASSED` is 0 that arithmetic command's exit
status is 1, so `set -e` kills the script right after the first test *passes*.
A shell bug, not a test failure. Use `./rz test valet`, or invoke the individual
`test/test_*.sh` scripts directly:

```bash
cd projects/valet && VALET=./build/debug/valet bash test/test_basic.sh
```

## Architecture

Paths relative to `projects/valet/`:

```
src/main.ritz           Entry point, CLI parsing, route registration
lib/valet.ritz          High-level Valet API, connection handler, global context
lib/router.ritz         URL routing (exact, prefix, parameter patterns)
lib/request.ritz        Zero-copy HTTP request parser
lib/response.ritz       Response builder (buffer + vectored I/O)
lib/static.ritz         Static file serving
lib/compress.ritz       gzip/deflate response compression (via squeeze)
lib/config.ritz         valet.json config loading
lib/log.ritz            Request logging
lib/pool.ritz           Connection/buffer pooling
lib/json_builder.ritz   JSON response construction
lib/tls.ritz, lib/tls/  TLS 1.3 termination (via cryptosec)
```

`src/` holds only `main.ritz` — the earlier claim that `src/compress.ritz` and
`src/handler.ritz` exist was wrong; both live (or lived) under `lib/`.

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

`./rz build valet` delegates to `projects/ritz/build.py`, which runs the Ritz
compiler pipeline:

1. `projects/ritz/ritz0/list_deps.py` - Resolve import graph
2. `projects/ritz/ritz0/ritz0.py` - Compile `.ritz` → `.ll` (LLVM IR)
3. `clang` - Compile `.ll` → `.o`
4. `ld` / `clang` - Link with `-nostdlib -no-pie` (Ritz provides `_start`)

Artifacts land in `projects/valet/build/{debug,release}/`. The dependency cache
is per-compiler and lives under `projects/ritz/`:
`.ritz-cache/`, `.ritz-cache-ritz1/`, `.ritz-cache-ritz1_selfhosted/`.

Corrections to earlier revisions of this file: `list_deps.py` is at
`projects/ritz/ritz0/`, not in this project. `clang-19` is not installed — the
toolchain here is `clang` (21.1.8) with `clang-20` also present; pin a version
only if you have a reason to. Neither `.build/` nor a project-local
`.ritz-cache/` exists under `projects/valet/`.

## Performance Features

- **io_uring**: Kernel async I/O, no syscall overhead per operation
- **Multishot accept**: Single SQE generates multiple CQEs (kernel 5.19+)
- **SO_REUSEPORT**: Multiple workers share listening socket
- **TCP_NODELAY**: Disable Nagle for low latency
- **Keep-alive**: Up to 100 requests per connection
- **Zero-copy responses**: Vectored I/O points to .rodata strings

Throughput, measured 2026-09-12 by `test/test_basic.sh` (`wrk`, single worker,
debug build, localhost): **28,108** and **34,850 req/s** across two runs. The
"~250k+ req/s" figure this file carried has no recorded measurement behind it;
re-measure before quoting any number, and state the build profile and worker
count alongside it.

## Profiling

The debug profile already carries symbols; there is no separate `--profile`
build (and no `build.sh`).

```bash
./rz build valet
valgrind --tool=callgrind ./projects/valet/build/debug/valet &
wrk -t1 -c10 -d5s http://localhost:8080/
pkill valet
kcachegrind callgrind.out.*
```

Not verified on this machine — `valgrind` and `kcachegrind` are not assumed
installed.

## Next Steps (Roadmap)

Shipped — these were listed as "next steps" here long after they landed:

1. ~~**Routing framework**~~ ✅ `lib/router.ritz` — exact, prefix and parameter patterns
2. ~~**Static file serving**~~ ✅ `valet_static()` in `lib/valet.ritz`; ETag, range
   and directory-listing tests exist (`test/test_etag.sh`, `test_range.sh`,
   `test_dirlist.sh`)
3. ~~**Middleware**~~ ✅ `valet_use()` / named middleware and before-interceptors
   in `lib/valet.ritz`; `test/test_middleware.sh`
4. ~~**Compression**~~ ✅ `lib/compress.ritz` via squeeze
5. ~~**Config file**~~ ✅ `lib/config.ritz`, `-c/--config`
6. ~~**Reverse proxy**~~ ✅ `-z/--zeus-socket`
7. ~~**TLS**~~ ✅ `lib/tls.ritz` + `lib/tls/` via cryptosec (end-to-end HTTPS not
   measured here)

Still open:

- **Request body parsing** — Content-Length, chunked encoding
- **Graceful shutdown** — signal handling

## Related Projects

All in this monorepo (`~/dev/ritz-lang/rz`). The old standalone
`/home/aaron/dev/nevelis/langdev` tree referenced here previously does not exist;
it was consolidated in February 2026.

- **ritz** (`projects/ritz`) — compiler and `ritzlib` stdlib
- **cryptosec** (`projects/cryptosec`) — crypto and TLS 1.3, already integrated
- **squeeze** (`projects/squeeze`) — gzip/deflate, already integrated
- **zeus** (`projects/zeus`) — process runner valet reverse-proxies to
