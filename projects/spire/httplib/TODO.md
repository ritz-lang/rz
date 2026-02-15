# HTTP Library - TODO

## Phase 1: Foundation ✓

- [x] Project scaffolding (directories, ritz.toml, build scripts)
- [x] Add ritz and ritzunit as git submodules
- [x] Core types: Method, Status, Version (lib/types.ritz)
- [x] Request/Response types

## Phase 2: HTTP/1.x Codec ✓

- [x] Request parser (method, path, version, headers) - lib/h1_request.ritz
- [x] Response parser (status, headers, body) - lib/h1_response.ritz
- [x] Chunked transfer encoding (decode/encode) - lib/chunked.ritz
- [x] Keep-alive detection
- [x] Request/Response serialization - lib/h1_writer.ritz

## Phase 3: HTTP/2 Codec ✓

- [x] Frame types (DATA, HEADERS, PRIORITY, RST_STREAM, SETTINGS, PUSH_PROMISE, PING, GOAWAY, WINDOW_UPDATE, CONTINUATION) - lib/h2_frame.ritz
- [x] Frame parser - lib/h2_frame.ritz
- [x] Frame serializer - lib/h2_frame.ritz
- [x] HPACK static table - lib/hpack.ritz
- [x] HPACK dynamic table - lib/hpack.ritz
- [x] HPACK encoder - lib/hpack.ritz
- [x] HPACK decoder - lib/hpack.ritz
- [x] Stream state machine - lib/h2_stream.ritz
- [x] Flow control - lib/h2_stream.ritz
- [x] Settings negotiation - lib/h2_frame.ritz

## Phase 4: QUIC Transport ✓

- [x] QUIC variable-length integers (RFC 9000 Section 16)
- [x] QUIC packet types (Initial, Handshake, 0-RTT, 1-RTT, Short Header)
- [x] QUIC frame types (PADDING, PING, ACK, CRYPTO, STREAM, MAX_DATA, etc.)
- [x] Connection ID management (CidManager, local/remote CIDs)
- [x] Packet number encoding/decoding (truncation, reconstruction)
- [x] Packet number spaces (Initial, Handshake, Application)
- [x] Loss detection (RFC 9002 time/packet thresholds) - lib/quic_loss.ritz
- [x] Congestion control (CWND, slow start, recovery) - lib/quic_loss.ritz
- [x] Connection migration (path validation, anti-amplification) - lib/quic_migration.ritz

## Phase 5: HTTP/3 Codec ✓

- [x] HTTP/3 frame types (DATA, HEADERS, SETTINGS, GOAWAY, etc.) - lib/h3_frame.ritz
- [x] QPACK static table (99 entries per RFC 9204) - lib/qpack_static.ritz
- [x] QPACK encoder/decoder with dynamic table - lib/qpack.ritz
- [x] QPACK encoder/decoder stream instructions - lib/qpack.ritz
- [x] Stream management (request, control, QPACK streams) - lib/h3_stream.ritz
- [x] Settings (QPACK_MAX_TABLE_CAPACITY, MAX_FIELD_SECTION_SIZE, etc.)

## Integration

- [ ] TLS 1.3 integration (cryptosec) - awaiting library
- [ ] Compression integration (squeeze) - awaiting library
- [x] io_uring async helpers - lib/async_http.ritz

## Infrastructure Notes

### json_stub.ritz
The `lib/json_stub.ritz` file provides no-op stub functions for JSON reporting.
This is intentional to avoid symbol conflicts with ritzunit's `json_reporter.ritz`,
which defines a local `print_char` function that conflicts with `ritzlib/io.ritz`.
The build script excludes `json_reporter.ritz` and uses our stub instead.
This workaround can be removed when ritzunit fixes the symbol conflict.

## RERITZ Migration (Partial)

### Completed
- [x] Convert @test → [[test]] in all 21 test files (513 tests)
- [x] Convert &x → @x address-of operators in lib/*.ritz
- [x] Convert &x → @x address-of operators in test/*.ritz
- [x] Enable RITZ_SYNTAX=reritz in build_tests.sh

### Blocked - Waiting on ritzunit
- [ ] String redesign: `c"..."` stays as-is (ritz supports both `c"..."` for `*u8` and `"..."` for `StrView`)
- [ ] Update to latest ritz (7d6885d) - blocked until ritzunit completes String migration
  - ritzunit uses `prints(c"...")` which fails with new String API (`prints` expects `StrView`)
  - Pinned to ritz@bd52511 (pre-String-redesign) for now
  - Track: https://github.com/ritz-lang/ritzunit String migration
