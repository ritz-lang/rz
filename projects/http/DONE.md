# HTTP Library - Completed

## 2026-02-13: HTTP/1.x Codec Complete

### Phase 1: Foundation
- Created project structure (lib/, test/, src/, build/, logs/)
- Added ritz.toml package manifest
- Added ritz and ritzunit as git submodules
- Created build.sh and build_tests.sh scripts

### Phase 2: Core Types (lib/types.ritz)
- HTTP methods: GET, POST, PUT, DELETE, HEAD, OPTIONS, PATCH, CONNECT, TRACE
- HTTP versions: HTTP/1.0, HTTP/1.1, HTTP/2, HTTP/3
- Status codes with reason phrases (1xx-5xx)
- Zero-copy parsing with Span<u8>

### Phase 3: HTTP/1.x Request Parser (lib/h1_request.ritz)
- Request line parsing (method, path, version)
- Header parsing (case-insensitive, zero-copy)
- Content-Length extraction
- Connection keep-alive detection
- Max 64 headers per request

### Phase 4: HTTP/1.x Response Parser (lib/h1_response.ritz)
- Status line parsing (version, code, reason)
- Header parsing with special header detection
- Transfer-Encoding: chunked detection
- Content-Length body extraction

### Phase 5: Chunked Transfer Encoding (lib/chunked.ritz)
- Hex chunk size parsing
- ChunkDecoder state machine
- Chunk size encoding
- Last chunk marker encoding

### Phase 6: HTTP/1.x Serialization (lib/h1_writer.ritz)
- Status line writing
- Request line writing
- Header writing
- Content-Length header writing
- H1ResponseBuilder fluent API

### Test Coverage
- 86 tests passing
- Types: 35 tests
- Request parser: 17 tests
- Response parser: 11 tests
- Chunked encoding: 13 tests
- Writer: 10 tests

### Known Issues
- Ritz type aliases don't export across modules properly - use explicit i32 types
- All function parameters using "Status" or "Method" type need explicit i32

## 2026-02-13: HTTP/2 Frame Types & HPACK Complete

### HTTP/2 Frame Types (lib/h2_frames.ritz)
- All 10 frame types per RFC 7540: DATA, HEADERS, PRIORITY, RST_STREAM, SETTINGS, PUSH_PROMISE, PING, GOAWAY, WINDOW_UPDATE, CONTINUATION
- Frame flags (END_STREAM, END_HEADERS, PADDED, PRIORITY)
- 9-byte frame header parsing and serialization
- Frame payload parsing for all types
- Frame building helpers

### HPACK Header Compression (lib/hpack.ritz)
- Static table with 61 pre-defined entries per RFC 7541
- Dynamic table with FIFO eviction and configurable max size
- Integer encoding/decoding (variable-length prefix encoding)
- String encoding/decoding (literal strings, Huffman not yet implemented)
- Header field representations:
  - Indexed header field
  - Literal with incremental indexing
  - Literal without indexing
  - Literal never indexed
  - Dynamic table size update
- Full encoder with automatic index selection
- Full decoder with combined static+dynamic table lookup

### Test Coverage
- 156 tests passing (total)
- HTTP/2 frames: 14 tests
- HPACK: 25 tests (static table, dynamic table, encoder, decoder, roundtrip)

### Known Issues
- Large struct sizes (HpackDecoder ~10KB) can cause LLVM codegen crashes; reduced array sizes as workaround
- Huffman encoding not implemented (literal strings only)

## 2026-02-13: HTTP/2 Stream Management Complete

### Stream State Machine (lib/h2_stream.ritz)
- All stream states per RFC 7540 Section 5.1: IDLE, RESERVED_LOCAL, RESERVED_REMOTE, OPEN, HALF_CLOSED_LOCAL, HALF_CLOSED_REMOTE, CLOSED
- All stream events: SEND_HEADERS, RECV_HEADERS, SEND_END_STREAM, RECV_END_STREAM, SEND_RST_STREAM, RECV_RST_STREAM, SEND_PUSH_PROMISE, RECV_PUSH_PROMISE
- State transition functions with validation
- State query helpers (is_idle, is_open, can_send, can_recv, etc.)

### Flow Control (lib/h2_stream.ritz)
- Per-stream window tracking (local and remote)
- Window consumption and increment functions
- Overflow detection for window updates
- Default window size: 65535 bytes

### Stream Priority (lib/h2_stream.ritz)
- Stream dependency tracking
- Weight management (1-256, clamped)
- Exclusive dependency flag

### Stream Manager (lib/h2_stream.ritz)
- Manages up to 128 concurrent streams
- Client-initiated (odd) and server-initiated (even) stream ID allocation
- Stream lookup by ID
- Get-or-create semantics for incoming requests
- Active stream counting
- Window update application

### Settings Tests (test/test_h2_settings.ritz)
- Settings parsing (header table size, max frame size, concurrent streams)
- Settings serialization
- Connection preface write/verify
- Roundtrip tests

### Bug Fixes
- Fixed u8 to i64 sign extension in settings parsing (need & 0xFF mask)

### Test Coverage
- 210 tests passing (total)
- Stream state machine: 41 tests
- Settings: 13 tests

## 2026-02-13: QUIC Variable-Length Integers

### QUIC Varint Encoding (lib/quic_varint.ritz)
- RFC 9000 Section 16 compliant variable-length integer encoding
- 1/2/4/8 byte encodings based on value range (0-2^62-1)
- Parse and encode functions with error handling
- Length calculation for encoding

### Build Infrastructure
- Created runtime LLVM IR files (ritz_start*.ll) for linking
- Extracted shared helpers to lib/h1_utils.ritz to fix duplicate symbol errors

### Test Coverage
- 236 tests passing (total)
- QUIC varint: 26 tests (encoding length, parsing, encoding, roundtrip)

## 2026-02-13: QUIC Packet and Frame Types

### QUIC Packet Headers (lib/quic_packet.ritz)
- Long header parsing (Initial, 0-RTT, Handshake, Retry)
- Short header parsing with configurable DCID length
- Header form detection and packet type extraction
- Connection ID extraction (up to 20 bytes per RFC 9000)
- Token field for Initial packets
- Payload length parsing (except Retry)
- Long header serialization with roundtrip support

### QUIC Frame Types (lib/quic_frame.ritz)
- Frame type constants (PADDING through HANDSHAKE_DONE)
- PADDING frame parsing (with consecutive count)
- ACK frame parsing (with optional ECN counters and ranges)
- CRYPTO frame parsing (offset, length, data reference)
- STREAM frame parsing (all flag combinations: FIN, LEN, OFF)
- MAX_DATA, MAX_STREAM_DATA frame parsing
- CONNECTION_CLOSE frame parsing (transport and app error variants)
- Stream frame flag helpers (is_stream_frame, stream_frame_flags)

### Test Coverage
- 282 tests passing (total)
- QUIC packet: 20 tests (long/short header parsing, roundtrip)
- QUIC frame: 26 tests (frame type detection, all frame parsers)

## 2026-02-13: QUIC Connection IDs and Packet Numbers

### Connection ID Management (lib/quic_cid.ritz)
- ConnectionId struct (up to 20 bytes per RFC 9000)
- CID initialization, copy, comparison
- CidEntry with sequence numbers and reset tokens
- CidManager for local and remote CIDs
- Local CID operations: add, find, retire
- Remote CID operations: add with retire_prior_to, get active, switch
- Active CID counting

### Packet Number Encoding (lib/quic_pn.ritz)
- Encoded length calculation based on delta from largest acked
- 1/2/3/4 byte encoding and parsing
- Truncation and reconstruction per RFC 9000 Appendix A
- PnSpace for per-space tracking (next_pn, largest_acked, largest_recv)
- PnManager for all three spaces (Initial, Handshake, Application)

### Test Coverage
- 331 tests passing (total)
- Connection IDs: 24 tests
- Packet numbers: 25 tests

## 2026-02-13: QUIC Loss Detection and Congestion Control

### RTT Estimation (lib/quic_loss.ritz)
- EWMA smoothed RTT calculation per RFC 9002
- RTT variance tracking
- Minimum RTT tracking
- ACK delay adjustment (capped at max_ack_delay)
- PTO (Probe Timeout) calculation
- Loss delay threshold calculation

### Congestion Controller (lib/quic_loss.ritz)
- Initial CWND: 10 packets × 1200 bytes
- Slow start: CWND increases by sent_bytes on ACK
- Congestion avoidance: CWND increases by MSS per RTT
- Recovery mode: halves CWND and ssthresh on loss
- Minimum CWND: 2 packets
- Recovery exit when post-recovery packets ACKed

### Sent Packet Tracker (lib/quic_loss.ritz)
- Track up to 256 in-flight packets
- Record sent time, bytes, ack-eliciting status
- Process ACKs and update largest_acked
- Loss detection via packet threshold (kPacketThreshold=3)
- Loss detection via time threshold (9/8 × max(latest_rtt, smoothed_rtt))
- In-flight packet counting
- Earliest sent time tracking for PTO

### Test Coverage
- 356 tests passing (total)
- Loss detection: 25 tests (RTT, CC, tracker)

## 2026-02-13: QUIC Connection Migration

### Address Management (lib/quic_migration.ritz)
- Address struct for IPv4/IPv6 (up to 16 bytes + port)
- Address comparison, copy, empty detection
- IPv4 address initialization helper

### Path Management (lib/quic_migration.ritz)
- Path struct with local/remote addresses
- Path states: UNUSED, VALIDATING, VALIDATED, FAILED
- PathManager for up to 4 concurrent paths
- Active path tracking and switching
- Path lookup by remote address

### Path Validation (lib/quic_migration.ritz)
- PATH_CHALLENGE/PATH_RESPONSE handling per RFC 9000 Section 8.2
- 8-byte challenge data storage and verification
- Validation timeout detection
- Challenge attempt tracking

### Anti-Amplification (lib/quic_migration.ritz)
- Bytes sent/received tracking per path
- 3x amplification limit for unvalidated paths
- Validated paths have no send limits

### Migration Detection (lib/quic_migration.ritz)
- Detect address changes from incoming packets
- Create new paths automatically on migration
- Distinguish same-path vs existing-inactive vs new-path cases

### Test Coverage
- 388 tests passing (total)
- Connection migration: 32 tests (address, path, validation, detection)

## 2026-02-13: HTTP/3 Codec Complete

### HTTP/3 Frame Types (lib/h3_frame.ritz)
- All HTTP/3 frame types: DATA, HEADERS, CANCEL_PUSH, SETTINGS, PUSH_PROMISE, GOAWAY, MAX_PUSH_ID
- Frame header parsing (type + length as varints)
- Frame header serialization
- Settings parsing/serialization with identifier lookup
- Stream type constants (control, push, QPACK encoder/decoder)
- Error codes per RFC 9114 Section 8.1
- Reserved frame/setting detection (grease)

### QPACK Static Table (lib/qpack_static.ritz)
- All 99 entries per RFC 9204 Appendix A
- Lookup by index (0-98)
- Search by name (first match)
- Search by name+value (exact match)
- Common headers: :method, :path, :scheme, :status, :authority
- Security headers: strict-transport-security, x-frame-options, etc.
- CORS headers: access-control-allow-origin, etc.
- Content types: application/json, text/html, image/*, etc.

### QPACK Codec (lib/qpack.ritz)
- Dynamic table with configurable max size
- Entry insertion with FIFO eviction
- Prefix integer encoding/decoding
- Indexed field line encoding (static table)
- Literal with name reference encoding
- Literal without name reference encoding
- Field section prefix (Required Insert Count + Base)
- Encoder stream instructions: Set Capacity, Insert Name Ref
- Decoder stream instructions: Section Ack, Stream Cancel, Insert Count Inc

### HTTP/3 Stream Management (lib/h3_stream.ritz)
- Request stream state tracking
- Control stream management (local/remote)
- QPACK encoder/decoder stream assignment
- Connection state with settings
- Stream creation and lookup (up to 64 concurrent)
- Active stream counting
- GOAWAY handling (graceful shutdown)
- Frame validation per stream type

### Test Coverage
- 491 tests passing (total)
- HTTP/3 frames: 29 tests
- QPACK static table: 24 tests
- QPACK codec: 26 tests
- HTTP/3 streams: 24 tests

## 2026-02-14: io_uring Async HTTP Helpers

### Async HTTP Module (lib/async_http.ritz)
- AsyncHttpConn struct for managing HTTP connections
  - Read/write buffers (8KB each)
  - Embedded H1Request/H1Response for parsing
  - Connection state machine (IDLE, READING, WRITING, CLOSED)
- io_uring submission helpers:
  - async_submit_read - queue a read operation
  - async_submit_write - queue a write operation
  - async_submit_accept - queue an accept for new connections
  - async_submit_connect - queue a connect for client connections
  - async_submit_close - queue a close operation
- Completion handling:
  - async_handle_read - process read completions
  - async_handle_write - process write completions
  - async_process_completions - batch completion processing
- HTTP parsing integration:
  - async_try_parse_request - parse request from read buffer
  - async_try_parse_response - parse response from read buffer
  - async_write_response - serialize response to write buffer
- User data encoding for operation tracking:
  - Operation type tags in high bits
  - File descriptor in low bits

### Infrastructure Improvements
- Moved H1_ERR_* error codes to lib/h1_utils.ritz to avoid duplicate definition conflicts
- Fixed h1_request.ritz and h1_response.ritz to use shared error codes

### Test Coverage
- 513 tests passing (total)
- Async HTTP: 22 tests (constants, op type/fd extraction, conn init, read/write handlers, request/response parsing, response writing)

## 2026-02-14: RERITZ Syntax Migration

### Overview
Migrated entire HTTP library codebase to the new RERITZ syntax as part of the Ritz language overhaul. This is a significant language update that changes several core syntax elements.

### Syntax Changes Applied

| Change | Old Syntax | New Syntax | Files Affected |
|--------|-----------|------------|----------------|
| Test attributes | `@test` | `[[test]]` | 21 test files |
| Address-of | `&variable` | `@variable` | All lib/*.ritz, test/*.ritz |
| Address-of struct | `&struct.field` | `@struct.field` | Many files |
| Address-of array | `&array[i]` | `@array[i]` | Several files |

### Files Modified
- **21 test files**: All `@test` annotations converted to `[[test]]`
- **21 lib files**: All address-of operators converted from `&` to `@`
- **build_tests.sh**: Added `RITZ_SYNTAX=reritz` environment variable

### Migration Approach
1. Used `sed` to convert `@test` → `[[test]]` (simple pattern)
2. Used targeted `sed` patterns to convert `&x` → `@x` while preserving `&` for bitwise AND:
   - `(&var` → `(@var` (function arguments)
   - `, &var` → `, @var` (comma-separated args)
   - `= &var` → `= @var` (assignments)
   - Bitwise AND (`a & b`) preserved (has spaces around operator)

### Not Yet Migrated
- `c"..."` C-string literals: Awaiting String redesign (P1 feature, not implemented in ritz yet)
- The new `:&` mutable borrow and `:=` move parameter syntax: Not applicable to current codebase (uses pointer-based API)

### Verification
- All 513 tests pass with new syntax
- Build time unchanged (~600ms)
- No functional changes - purely syntactic migration

### Submodule Updates
- Updated `ritz` submodule to `bd52511` (has RERITZ support: `[[packed]]`, `[[naked]]`, `asm` blocks)
- Updated `ritzunit/ritz` submodule to match

## 2026-02-14: RERITZ String Redesign Status

### Assessment
The ritz compiler has completed the String redesign (commit 7d6885d), which changes:
- `"hello"` now returns `StrView` (zero-copy) instead of `String`
- `c"hello"` returns `*u8` (unchanged, for FFI)
- `prints()` now expects `StrView`, use `prints_cstr()` for `*u8`

### Blocking Issue: ritzunit Not Yet Migrated
- ritzunit uses `prints(c"...")` throughout (junit_reporter.ritz, reporter.ritz, etc.)
- This fails with the new `prints()` signature which expects `StrView`
- ritzunit needs to migrate to `prints_cstr(c"...")` or `prints("...")`

### Current State
- **Pinned** ritz and ritzunit/ritz submodules to `bd52511` (pre-String-redesign)
- All 513 HTTP library tests pass
- HTTP library code itself is compatible with the String redesign (uses `c"..."` with Span functions)

### Next Steps (when ritzunit is ready)
1. Update ritz submodule to latest (7d6885d+)
2. Update ritzunit submodule to String-migrated version
3. Optionally migrate `c"..."` to `"..."` where StrView is preferred
4. Remove `RITZ_SYNTAX=reritz` from build_tests.sh (legacy mode removed)

## 2026-02-14: LARB Code Review Fixes

### Issues Addressed (from GitHub Issue #1)

#### HIGH Priority - Fixed
- **RERITZ `&` → `@` compliance**: Fixed 10 occurrences across 4 files
  - h2_stream.ritz (4 occurrences)
  - h3_stream.ritz (3 occurrences)
  - quic_pn.ritz (1 occurrence)
  - quic_migration.ritz (2 occurrences)

#### MEDIUM Priority - Fixed

1. **Missing test_h1_utils.ritz**: Created comprehensive test file with 38 tests
   - Error code tests
   - find_byte tests (6 tests: start, end, middle, not found, offset, empty)
   - find_crlf tests (7 tests: found, start, not found, only CR, only LF, wrong order, multiple)
   - is_whitespace tests (3 tests: space, tab, non-whitespace)
   - to_lower tests (3 tests: uppercase, lowercase, non-alpha)
   - span_eq_cstr_ci tests (7 tests: exact, case-insensitive, not equal, length mismatch, real-world, empty)
   - parse_content_length tests (12 tests: zero, simple, large, leading zeros, errors)

2. **parse_content_length error handling**: Now returns -1 for errors instead of 0
   - Empty span returns -1
   - Non-numeric characters return -1
   - Distinguishes valid `Content-Length: 0` from invalid input

3. **parse_content_length overflow check**: Added bounds checking
   - Checks before multiplication to prevent overflow
   - Checks after addition to detect wrap-around
   - Maximum safe value: 922337203685477580 before multiplication

#### LOW Priority - Fixed

4. **json_stub documentation**: Added explanation in TODO.md
   - Documents purpose of stub functions
   - Explains symbol conflict with ritzunit's json_reporter.ritz
   - Notes this is a temporary workaround

5. **Magic number consolidation**: Created lib/limits.ritz
   - Consolidated protocol limits in one module
   - HTTP/1.x: H1_MAX_HEADERS
   - HTTP/2: H2_MAX_STREAMS, HPACK_MAX_*
   - HTTP/3: H3_MAX_STREAMS, H3_MAX_SETTINGS, QPACK_MAX_*
   - QUIC: QUIC_MAX_CID_LEN, QUIC_MAX_PATHS, etc.
   - Updated h1_request.ritz and h1_response.ritz to use shared limits

### Test Coverage
- 551 tests passing (38 new tests)
- All LARB review issues resolved
