# Valet Development TODO

## Architecture Alignment

Per the http README and LARB discussions, the Ritz web stack has three layers:

| Layer | Library | Role |
|-------|---------|------|
| Mechanism | `http` | Wire protocol, parsing, framing |
| Policy | `Valet` | Routing, middleware, server config |
| Runtime | `Zeus` | Process isolation, zero-copy IPC |

**Current architecture is correct:** Routing and middleware belong in Valet (policy layer).

### Future Integration

- [ ] Use `http` library for H1/H2/H3 parsing (currently duplicated in `lib/request.ritz`)
- [ ] Integrate with `Zeus` for worker process management via `zeus_client`
- [ ] Move connection pooling to Zeus shared memory rings

See: `ARCHITECTURE_PROPOSAL.md` and [zeus#1](https://github.com/ritz-lang/zeus/issues/1)

---

## Current Status

Valet is a high-performance async HTTP server achieving **1.47M req/sec** with
HTTP keep-alive on a 14-core machine with CPU pinning, **10.7x faster than nginx**.

**Recent improvements (Feb 12, 2026):**
- Phase 5 Compression enhancements:
  - `ctx_text_compressed()` and `ctx_json_compressed()` now support deflate fallback
  - `encoding_select()` picks best encoding (gzip > deflate > identity)
  - Streaming compression for very large responses (>1MB):
    - `ctx_body_streaming_compressed()` with chunked transfer encoding
    - `StreamCompressor` with 256KB chunks, reusable compression buffer
    - `stream_compress_chunk()` for independent chunk compression
  - All response helpers now use unified `encoding_select()` logic
- 85 unit tests, all passing

**Previous improvements (Feb 12, 2026):**
- Phase 1 Performance infrastructure complete:
  - `IORING_OP_SEND_ZC` (opcode 53) for zero-copy network sends
  - `IORING_OP_SPLICE` (opcode 15) for zero-copy fd-to-fd transfer
  - `uring_prep_send_zc()` and `uring_prep_splice()` helpers
  - `task_send_zc()` / `task_send_zc_buf()` for async zero-copy sends
  - `task_splice()` for async splice operations
  - Memory pool infrastructure (`lib/pool.ritz`) with O(1) alloc/free
  - Connection buffer pool for efficient buffer reuse
- Phase 4 Middleware complete:
  - Per-route interceptors (`valet_before()`, `valet_after()`)
  - Before interceptors run after global middleware, before handler
  - After interceptors run after handler (in reverse registration order)
  - Route-specific auth, validation, CORS, metrics patterns enabled

**Previous improvements (Feb 12, 2026):**
- Phase 5 Compression support (gzip via Squeeze submodule)
- `ctx_text_compressed()` and `ctx_json_compressed()` for auto-compression
- Accept-Encoding header parsing with quality value support
- Content-Encoding negotiation with proper Vary headers

**Previous improvements (Feb 12, 2026):**
- Migrated tests to ritzunit framework (28 unit tests, all passing)
- Fixed unsafe `pkill` patterns in integration tests (PID-based cleanup)
- Proper test isolation with fork-based runner

**Previous improvements (Jan 15, 2026):**
- JSON builder pattern (`lib/json_builder.ritz`) - clean JSON construction
- Middleware pipeline - run custom code before route handlers
- Catch-all wildcard routes (`/api/**` matches `/api/anything/nested`)
- Logging middleware example in `main.ritz`

**Previous improvements (Jan 13, 2026):**
- Request size limits with 413 response for oversized requests
- Error logging with timestamps (`lib/log.ritz`)
- Static file serving infrastructure (`lib/static.ritz`)
- `sys_sendfile` syscall for zero-copy file transfer
- JSON configuration file support (`valet.json`)
- Configuration loading with command-line overrides
- Graceful shutdown and idle timeout infrastructure

**Performance notes (Jan 12, 2026):**
- Pre-computed string approach: **1.47M req/sec** (optimal for static responses)
- Vectored I/O approach: **1.26M req/sec** with zero write errors (14% overhead)
- CPU pinning (server on 0-13, client on 14-27) improves throughput significantly

---

## Phase 1: Performance Optimizations

- [x] **`send_zc` (zero-copy send)** - avoid kernel copy on send
  - Added `IORING_OP_SEND_ZC` (opcode 53) to io_uring bindings
  - `uring_prep_send_zc()` and `uring_prep_send_zc_report()` helpers
  - `task_send_zc()` and `task_send_zc_buf()` in async_tasks
  - Buffer must remain valid until CQE received
  - **Wired into Valet**: `use_send_zc` config option in valet.json
  - `valet_task_send()` helper switches between regular/ZC send
  - Note: Requires native Linux kernel 6.0+ (WSL2 doesn't support SEND_ZC)
- [x] **`sendfile` via io_uring** - IORING_OP_SPLICE for fd transfer
  - Added `IORING_OP_SPLICE` (opcode 15) to io_uring bindings
  - `uring_prep_splice()` with full splice flag support
  - `task_splice()` for async file-to-socket transfer
  - Supports SPLICE_F_MOVE, SPLICE_F_NONBLOCK, SPLICE_F_MORE
  - Note: Current static file serving still uses `sys_sendfile()` (blocking but zero-copy)
  - Full async integration would require pipe management for splice semantics
- [x] **Memory pool** for request/response buffers (`lib/pool.ritz`)
  - Fixed-size block allocator with O(1) alloc/free
  - Pre-allocated contiguous memory via mmap
  - `MemPool` for generic use, `ConnBufferPool` for connections
  - Pool statistics: capacity, available, used, contains
  - Bulk reset for batch processing scenarios
- [ ] Profile-guided optimization (PGO) - requires Ritz compiler support

---

## Phase 2: Production Features

- [x] **Configuration files** - JSON config with runtime reload support
- [x] **Graceful shutdown** - Shutdown hook in event loop
- [x] **Connection idle timeouts** - Infrastructure implemented
- [x] **Request size limits** - Returns 413 for oversized requests
  - `max_request_size` config field
  - Check in connection handler before parsing
  - Logs warning on oversized requests
- [x] **Error logging with timestamps** - `lib/log.ritz` module
  - Log levels: DEBUG, INFO, WARN, ERROR
  - Timestamps: YYYY-MM-DD HH:MM:SS format
  - Functions: `log_debug()`, `log_info()`, `log_warn()`, `log_error()`
  - Formatted logging: `log_info_i()`, `log_error_i()` with integer values
- [x] Max connections limit
  - `task_server_set_max_connections()` enforces limit in TaskServer
  - Rejects new connections when at limit
  - Configured via `limits.max_connections` in valet.json

---

## Phase 3: Static File Serving

- [x] **MIME type detection** - `lib/static.ritz`
  - Supports: HTML, CSS, JS, JSON, images, fonts, media, archives
  - Extension-based detection
- [x] **sendfile support** - `sys_sendfile()` in ritzlib/sys.ritz
  - Zero-copy file transfer to socket
- [x] **Path security** - Directory traversal prevention
  - Rejects paths containing ".." or null bytes
- [x] **Wire up static serving to valet routes**
  - `valet_try_static()` checks requests before routing
  - Configured via `static.prefix` and `static.root` in valet.json
- [x] **Directory listing** - HTML directory index for directories
  - `static_is_directory()` detects directories
  - `static_serve_directory()` generates HTML listing
  - Shows files and subdirectories with navigation
- [x] **Range requests (partial content)** - HTTP 206 support
  - `parse_range()` parses Range header (bytes=start-end, bytes=start-, bytes=-suffix)
  - `static_serve_file_range()` serves partial content with sendfile offset
  - Returns `Content-Range` header for partial responses
  - Adds `Accept-Ranges: bytes` header to all file responses
- [x] **ETag/If-None-Match caching** - HTTP 304 support
  - `generate_etag()` creates ETag from file inode-size-mtime (hex format)
  - `etag_matches()` compares If-None-Match header with generated ETag
  - `static_serve_file_full()` serves file with Range AND ETag support
  - `static_send_304()` returns 304 Not Modified for matching ETags
  - ETag header included in all file responses (200, 206, 304)

---

## Phase 4: Middleware & Routing

- [x] Path-based routing with parameters (`:id`)
- [x] **Prefix wildcard routes** (`/static/*`) - matches single level
- [x] **Catch-all wildcard routes** (`/api/**`) - matches all nested paths
  - Captures remainder as param[0]
  - Handles exact prefix match (`/api` matches `/api/**`)
- [x] **Middleware pipeline** (`lib/router.ritz`)
  - `router_use()` / `valet_use()` to register middleware
  - Middleware runs before route handlers on every request
  - Return `MW_CONTINUE` (0) to continue, `MW_HANDLED` (1) to stop
  - Named middleware via `router_use_named()` for debugging
  - Max 16 middleware functions
- [x] **Request/response interceptors** (per-route middleware)
  - `router_route_before()` / `valet_before()` - before handler
  - `router_route_after()` / `valet_after()` - after handler
  - `route_run_before()` runs before interceptors in registration order
  - `route_run_after()` runs after interceptors in reverse order
  - Max 4 interceptors per route (before + after combined)
  - Enables route-specific auth, validation, CORS, metrics
- [x] **JSON response helpers** (`lib/json_builder.ritz`)
  - Builder pattern for constructing JSON responses
  - `json_init()`, `json_object_start/end()`, `json_array_start/end()`
  - `json_key_str()`, `json_key_int()`, `json_key_bool()` for adding fields
  - `json_str()`, `json_int()`, `json_bool()`, `json_null()` for array values
  - `json_len()`, `json_ptr()` to get result

---

## Phase 5: Compression

- [x] **Gzip compression** via Squeeze submodule (`lib/compress.ritz`)
  - `compress_gzip()` compresses data using gzip format
  - `compress_if_beneficial()` smart compression with thresholds
- [x] **Accept-Encoding parsing** - `accept_encoding_parse()`
  - Handles gzip, deflate, identity, wildcards
  - Quality value support (e.g., `gzip;q=1.0, deflate;q=0.5`)
  - Case-insensitive header matching
- [x] **Content-Encoding negotiation**
  - `encoding_select()` picks best encoding from accepted list
  - `encoding_header_value()` returns correct header value
  - Prefers gzip > deflate > identity
- [x] **Compression-aware response helpers**
  - `ctx_text_compressed()` - auto-compress text responses >256 bytes
  - `ctx_json_compressed()` - auto-compress JSON responses >256 bytes
  - Adds `Content-Encoding: gzip` header when compressed
  - Adds `Vary: Accept-Encoding` for proper caching
- [x] **MIME type filtering** - `should_compress_mime()`
  - Compresses: text/*, application/json, application/javascript, application/xml, image/svg
  - Skips: images, video, audio, archives (already compressed)
- [x] **Deflate compression** - `compress_deflate()`, `compress_deflate_level()`
  - Uses squeeze.lib.deflate for RFC 1951 raw deflate
  - Compression levels 0-9 supported
  - `compress_if_beneficial()` now supports deflate as fallback
- [x] **Large response compression** - `compress_large()`, `ctx_body_large_compressed()`
  - Heap-allocated compression for responses up to 1MB
  - Uses less strict threshold (5% improvement) for large files
  - Stack-based compression remains for responses <64KB
- [x] **Streaming compression** for very large responses (>1MB)
  - `ctx_body_streaming_compressed()` - chunked transfer with per-chunk compression
  - `StreamCompressor` state for reusable compression buffer
  - `stream_compressor_init()` / `stream_compressor_free()` lifecycle
  - `stream_compress_chunk()` compresses 256KB chunks independently
  - `format_chunk_header()` for HTTP chunked encoding hex format
  - Falls back to `ctx_body_chunked_uncompressed()` on allocation failure
- [ ] True streaming compression (future - requires squeeze streaming deflate API)

---

## Phase 6: TLS Support

### TLS 1.3 Implementation Status

**Cryptosec Phase 5 COMPLETE!** All primitives and TLS 1.3 protocol support ready:

| Component | Status | Location |
|-----------|--------|----------|
| Record Layer | ✅ | `cryptosec/lib/tls13_record.ritz` |
| Key Schedule | ✅ | `cryptosec/lib/tls13_kdf.ritz` |
| Handshake Messages | ✅ | `cryptosec/lib/tls13_handshake.ritz` |
| Client State Machine | ✅ | `cryptosec/lib/tls13_client.ritz` |
| AES-GCM / ChaCha20-Poly1305 | ✅ | `cryptosec/lib/aes_gcm.ritz`, `chacha20_poly1305.ritz` |
| X25519 Key Exchange | ✅ | `cryptosec/lib/x25519.ritz` |
| Ed25519 Signatures | ✅ | `cryptosec/lib/ed25519.ritz` |
| RSA Signature Verification | ✅ | `cryptosec/lib/rsa.ritz` |
| X.509 Certificate Parsing | ✅ | `cryptosec/lib/x509.ritz`, `asn1.ritz` |
| Certificate Chain Validation | ✅ | `cryptosec/lib/x509_verify.ritz` |

**Cryptosec API for Valet integration:**
```ritz
# Initialize TLS client
tls_client_init(client: *TlsClient, config: *TlsConfig)
tls_client_start(client: *TlsClient, out: *u8, out_cap: i64) -> i64  # Returns ClientHello

# Process handshake (non-blocking for io_uring)
tls_client_process(client: *TlsClient, data: *u8, len: i64, out: *u8, out_cap: i64, out_len: *i64) -> i32

# Application data (after handshake complete)
tls_client_write(client: *TlsClient, data: *u8, len: i64, out: *u8, out_cap: i64) -> i64
tls_client_read(client: *TlsClient, data: *u8, len: i64, out: *u8, out_cap: i64) -> i64

# Close connection
tls_client_close(client: *TlsClient, out: *u8, out_cap: i64) -> i64
```

**Valet integration work:**
- [ ] Update cryptosec submodule (pending push to origin/main)
- [ ] Create `lib/tls.ritz` wrapper for cryptosec TLS client
- [ ] Add TLS listener support to TaskServer
- [ ] `valet_listen_tls(port, cert_path, key_path)` API
- [ ] Certificate/key loading (PEM parsing)
- [ ] ALPN negotiation for h2/http1.1
- [ ] TLS connection handler in event loop
- [ ] Configuration: `tls.enabled`, `tls.cert`, `tls.key` in valet.json
- [ ] HTTP/2 multiplexing (stretch goal)

### Cryptosec Integration

Cryptosec (`./cryptosec`) is included as a git submodule providing cryptographic primitives.

**Available primitives (370 tests):**
| Category | Primitives |
|----------|------------|
| Hashing | SHA-256, SHA-384, SHA-512 |
| Key Derivation | HMAC, HKDF |
| Symmetric Encryption | AES-128/256-GCM, ChaCha20-Poly1305 |
| Key Exchange | X25519 |
| Signatures | Ed25519, RSA PKCS#1 v1.5 (verify only) |
| Certificates | X.509 parsing, chain validation, hostname verification |
| TLS 1.3 | Record layer, key schedule, handshake, client state machine |

**Update submodule:**
```bash
cd cryptosec && git pull origin main && cd ..
git add cryptosec && git commit -m "Update cryptosec submodule"
```

---

## Code Quality Improvements

### Identified Issues (Not Blocking)

- [ ] **JSON literal workaround** (valet)
  - Issue: Building JSON byte-by-byte due to Ritz string escape limitations
  - Solution: Add string escape support to Ritz compiler
  - Tracked: https://github.com/ritz-lang/ritz/issues/90
  - Priority: Low (works as-is, cosmetic)

- [ ] **Manual state machine pattern**
  - Issue: Custom event loops instead of async/await
  - Solution: Ritz async/await support (in progress)
  - Priority: Medium (awaiting Ritz compiler update)

---

*Last updated: 2026-02-14*
