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
./rz test valet         # .ritz files under test/ — exit 0, several minutes
# Shell suites are not wired into `rz test` (#1403); run them by hand, e.g.
#   cd projects/valet && VALET=./build/debug/valet bash test/test_workers.sh
# Each picks a free port via test/lib_ports.sh, never a fixed one: valet's
# SO_REUSEPORT would let two runs share a port and split connections (#3694).
# PORT=... pins one; a port that already has a listener is refused.

# Benchmark
$V -p 8080 &
wrk -t4 -c100 -d10s http://localhost:8080/
```

With no `valet.json` present the server prints `config: cannot open valet.json`
and continues with defaults; that warning is not an error.

### `./test/run_all.sh`

Runs `test_basic.sh`, `test_multishot.sh`, `test_workers.sh` and `test_cli.sh`
against `build/debug/valet` (override with `VALET=`). The first three need
`ab` (apache2-utils) and `wrk` on PATH; without them they stop at their first
load test and the run reports them failed. Until AGAST #1495 the script exited
1 right after the first suite passed (`set -e` with `((PASSED++))` when
`PASSED` was 0) and pointed at a `projects/valet/valet` that no longer exists.

`test_cli.sh` (also a `build-all` step in CI) pins the command line: a
non-numeric `--port` / `--workers` is a usage error (`valet: invalid number
'abc'`, exit 1) rather than the silent 0 the old ArgParser produced.

## Architecture

Paths relative to `projects/valet/`:

```
src/main.ritz           Entry point, CLI parsing, route registration
lib/valet.ritz          High-level Valet API, connection handler, global context
lib/router.ritz         URL routing (exact, prefix, parameter patterns)
lib/request.ritz        Zero-copy HTTP request parser
lib/response.ritz       Response builder (fixed buffer)
lib/static.ritz         Static file serving
lib/compress.ritz       gzip/deflate response compression (via squeeze)
lib/config.ritz         valet.json config loading
lib/log.ritz            Request logging
lib/pool.ritz           Connection/buffer pooling
lib/json_builder.ritz   JSON response construction
lib/tls.ritz            TLS 1.3 termination (via cryptosec)
```

`src/` holds only `main.ritz` — the earlier claim that `src/compress.ritz` and
`src/handler.ritz` exist was wrong; both live (or lived) under `lib/`.

### Dependencies (from ritzlib)

| Module | Purpose |
|--------|---------|
| `async/tasks.ritz` | TaskPool, TaskServer, event loop |
| `uring.ritz` | io_uring syscall wrappers |
| `async_net.ritz` | TCP socket helpers |
| `argspec.ritz` | CLI argument parsing (`build_spec` in `src/main.ritz`) |

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
| `/bytes/:n` | n bytes of "0123456789…" | n ≤ 3500; short-send tests: HTTPS (#2197), plain HTTP `test_short_send.sh` (#3678) |
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
- **Static response constants**: `S_*` spans with precomputed lengths, no strlen

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
   `test_dirlist.sh`); every static response, 403 and 416 included,
   says the Connection valet will honour (#2117, #3899,
   `test/test_static_conn.sh`)
3. ~~**Middleware**~~ ✅ `valet_use()` / named middleware and before-interceptors
   in `lib/valet.ritz`; `test/test_middleware.sh`
4. ~~**Compression**~~ ✅ `lib/compress.ritz` via squeeze
5. ~~**Config file**~~ ✅ `lib/config.ritz`, `-c/--config`
6. ~~**Reverse proxy**~~ ✅ `-z/--zeus-socket`
7. ~~**TLS**~~ ✅ `lib/tls.ritz` via cryptosec; `test/test_tls_socket.sh`
   runs HTTPS against OpenSSL over a real socket in CI's `build-all` job
8. ~~**Request body framing**~~ ✅ `request_frame` in `lib/request.ritz`, over
   http's `lib/h1_framing.ritz` (AGAST #1865): Content-Length (i64) and
   chunked bodies, decoded in place; pipelined requests; 400 for CL with TE
   or a duplicate or invalid CL, 501 for other Transfer-Encodings;
   `test/test_framing.sh`. `POST /mirror` (stand-alone mode) returns the
   body whole through the proxy's continuation path, so a >8 KB request
   gets a >8 KB response; requests and responses have separate heap
   buffers (AGAST #3900, `test/test_large_echo.sh`). `POST /echo` answers
   "<body length> <body>" for these tests.

Still open:

- **Graceful shutdown** — signal handling

## Related Projects

All in this monorepo (`~/dev/ritz-lang/rz`). The old standalone
`/home/aaron/dev/nevelis/langdev` tree referenced here previously does not exist;
it was consolidated in February 2026.

- **ritz** (`projects/ritz`) — compiler and `ritzlib` stdlib
- **cryptosec** (`projects/cryptosec`) — crypto and TLS 1.3, already integrated
- **squeeze** (`projects/squeeze`) — gzip/deflate, already integrated
- **zeus** (`projects/zeus`) — process runner valet reverse-proxies to
