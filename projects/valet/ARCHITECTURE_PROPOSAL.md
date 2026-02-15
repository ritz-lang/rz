# Architecture Proposal: Valet/Zeus/HTTP Layer Separation

Based on the architecture discussion in the http README and LARB conversations, this document proposes the clean separation of concerns across the Ritz web stack.

## Current Architecture (from http README)

| Layer | Library | Role |
|-------|---------|------|
| Mechanism | `http` | Wire protocol, parsing, framing |
| Policy | `Valet` | Routing, middleware, server config |
| Runtime | `Zeus` | Process isolation, zero-copy IPC |

## Analysis

### What Each Layer Should Own

#### http (Mechanism Layer)
- HTTP/1.0, HTTP/1.1 request/response parsing
- HTTP/2 binary framing, HPACK compression
- HTTP/3 QUIC frames, QPACK compression
- Chunked transfer encoding
- Header parsing and serialization
- **NOT**: routing, middleware, server lifecycle

#### Valet (Policy Layer)
- Route registration and matching
- Middleware pipeline (before/after hooks)
- Request/response context helpers
- Static file serving policy
- Server configuration (ports, workers, timeouts)
- Handler registration and dispatch
- **NOT**: wire protocol details, process management

#### Zeus (Runtime Layer)
- Process isolation (worker processes)
- Zero-copy IPC via shared memory rings
- File descriptor passing (SCM_RIGHTS)
- Worker lifecycle (spawn, respawn, hot reload)
- Futex-based signaling
- Resource limits and backpressure
- **NOT**: HTTP protocol, routing logic

## Current State in Valet

Valet currently has:
- `lib/router.ritz` - Route matching with patterns, params, middleware ✅
- `lib/request.ritz` - HTTP request parsing (should use http library)
- `lib/response.ritz` - HTTP response building (should use http library)
- `lib/valet.ritz` - Server core, handler context ✅
- `lib/pool.ritz` - Connection pooling (could move to Zeus)

## Proposed Changes

### Phase 1: Valet → http Migration

Move HTTP parsing/building to the http library:
1. Replace `lib/request.ritz` with imports from `http.h1_request`
2. Replace `lib/response.ritz` with imports from `http.h1_response`
3. Keep routing and middleware in Valet

### Phase 2: Valet → Zeus Integration

Integrate Zeus for runtime concerns:
1. Use `zeus_client` for connecting to Zeus daemon
2. Move worker process management to Zeus
3. Move connection pooling to Zeus shared memory

### Phase 3: Clean Interface Boundaries

Define clean APIs:
- `http`: `Request`, `Response`, `parse_request()`, `write_response()`
- `valet`: `Router`, `Middleware`, `Context`, `valet_run()`
- `zeus`: `ZeusClient`, `Worker`, `SharedMemory`

## Benefits

1. **Reusability**: http library usable by other servers
2. **Testability**: Each layer testable in isolation
3. **Performance**: Zeus handles zero-copy IPC, Valet focuses on routing
4. **Maintainability**: Clear ownership boundaries

## Implementation Notes

The current routing/middleware code in Valet is well-designed:
- `router.ritz` supports exact, prefix, param, and catch-all patterns
- Middleware pipeline with before/after hooks
- Per-route middleware support

This should remain in Valet as it's clearly **policy** (how to dispatch requests) not **mechanism** (how to parse HTTP).

## Questions for LARB

1. Should Valet depend on http as a submodule, or should they be siblings?
2. Should Zeus provide a "valet worker" mode that handles HTTP directly?
3. Should compression (gzip/brotli) be in http (mechanism) or Valet (policy)?
