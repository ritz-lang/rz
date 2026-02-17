# LARB Review: HTTP Library

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

The HTTP library is a substantial, well-structured implementation covering HTTP/1.x, HTTP/2, HTTP/3, QUIC transport primitives, HPACK/QPACK compression, chunked encoding, and async I/O — approximately 16,500 lines across 45 files. The code follows Ritz idioms reasonably well in the areas of ownership modifiers, reference syntax, attributes, and string types. The primary systematic issue is pervasive use of `&&` and `||` (C-style logical operators) instead of the required `and`, `or`, and `not` keywords; this appears in nearly every file and constitutes a major compliance failure.

## Statistics

- **Files Reviewed:** 45 (23 lib, 22 test)
- **Total SLOC:** ~16,500
- **Issues Found:** ~340+ (Critical: 0, Major: ~340+, Minor: 5)

---

## Critical Issues

None identified. No Rust-style `&T` / `&mut T` parameter sigils, no `@test` / `@inline` old-attribute syntax, and no dangerous unchecked memory patterns beyond the expected low-level pointer arithmetic in this library type.

---

## Major Issues

### 1. Logical Operators — `&&` and `||` used everywhere (Major, ~340 occurrences)

The entire codebase uses C-style `&&` and `||` instead of the required `and` and `or` keywords. This is the single largest compliance issue. It affects every library file and every test file.

**Examples from `lib/h1_utils.ritz`:**
```ritz
# Line 31 - WRONG
if *(s.ptr + i) == '\r' && *(s.ptr + i + 1) == '\n'

# Line 38 - WRONG
if c == ' ' || c == '\t'
```

**Examples from `lib/types.ritz`:**
```ritz
# Line 43 - WRONG
if *(s.ptr + 1) == 'E' && *(s.ptr + 2) == 'T'

# Line 137 - WRONG
if *(s.ptr) != 'H' || *(s.ptr + 1) != 'T' || ...
```

**Examples from `lib/h2_stream.ritz`:**
```ritz
# Lines 86, 97, 104, 113, 121, 129, 285, 299, 324 - WRONG
if event == H2_EVENT_SEND_HEADERS || event == H2_EVENT_RECV_HEADERS
if mgr.count >= mgr.max_concurrent || mgr.count >= H2_MAX_STREAMS
```

**Correct form:**
```ritz
if *(s.ptr + i) == '\r' and *(s.ptr + i + 1) == '\n'
if c == ' ' or c == '\t'
if event == H2_EVENT_SEND_HEADERS or event == H2_EVENT_RECV_HEADERS
```

The `!` (bang) operator is used for inequality/boolean negation in one test file instance (`test_h1_utils.ritz:254`) but all other uses of `!` in the codebase are part of `!=` comparisons, which are correct.

**Files affected (all of them):**
- `lib/types.ritz` (multiple)
- `lib/h1_utils.ritz` (multiple)
- `lib/h1_request.ritz` (via imported utils)
- `lib/h1_response.ritz` (multiple)
- `lib/h2_stream.ritz` (10+ occurrences)
- `lib/quic_pn.ritz` (multiple)
- `lib/quic_varint.ritz` (1)
- `lib/quic_cid.ritz` (1)
- `lib/quic_migration.ritz` (10+)
- `lib/quic_loss.ritz` (multiple)
- `lib/hpack.ritz` (multiple)
- `lib/qpack.ritz` (multiple)
- `lib/qpack_static.ritz` (1)
- `lib/chunked.ritz` (1)
- `lib/h3_stream.ritz` (1)
- All 22 test files (multiple per file)

### 2. Raw Pointer Parameters as Standard API (Major, ~262 occurrences)

All public functions take `*T` raw pointer parameters for struct mutation rather than the idiomatic `:&` mutable borrow modifier. This is pervasive throughout the entire library. While raw pointers are acceptable in low-level FFI/kernel contexts, this is an application-level HTTP library and should use the Ritz ownership modifier syntax.

**Examples from `lib/h1_request.ritz`:**
```ritz
# CURRENT (raw pointers throughout)
pub fn h1_request_init(req: *H1Request)
pub fn h1_parse_request_line(req: *H1Request, input: *Span<u8>) -> i32
pub fn h1_parse_request(req: *H1Request, input: *Span<u8>) -> i32
pub fn h1_request_get_header(req: *H1Request, name: *u8) -> Span<u8>
pub fn h1_request_is_keep_alive(req: *H1Request) -> i32
```

**Idiomatic form:**
```ritz
pub fn h1_request_init(req:& H1Request)
pub fn h1_parse_request_line(req:& H1Request, input: Span<u8>) -> i32
pub fn h1_parse_request(req:& H1Request, input: Span<u8>) -> i32
pub fn h1_request_get_header(req: H1Request, name: StrView) -> Span<u8>
pub fn h1_request_is_keep_alive(req: H1Request) -> i32
```

This pattern repeats in every file: `lib/h1_response.ritz`, `lib/h1_writer.ritz`, `lib/h2_frame.ritz`, `lib/h2_stream.ritz`, `lib/h3_frame.ritz`, `lib/h3_stream.ritz`, `lib/hpack.ritz`, `lib/qpack.ritz`, `lib/chunked.ritz`, `lib/quic_*.ritz` (all), `lib/async_http.ritz`.

### 3. `c"..."` String Literals in Application Code (Major, extensive)

The `c"..."` prefix form is used extensively throughout both library and test code for passing strings to span helpers and comparison functions. Per spec, the `c"..."` prefix is only acceptable in compiler-internal or FFI contexts. Application code should use `"..."` (StrView) with `.as_cstr()` only at the FFI boundary.

**Examples from `lib/types.ritz`:**
```ritz
# WRONG (application-level)
return span_literal(c"GET", 3)
return span_literal(c"HTTP/1.1", 8)
return span_literal(c"Continue", 8)
```

**Examples from `lib/h2_frame.ritz`:**
```ritz
# WRONG
let preface: *u8 = c"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
```

**Examples from test files (`test/test_h1_request.ritz`):**
```ritz
# WRONG
var input: Span<u8> = span_from_cstr(c"GET / HTTP/1.1\r\n")
var expected_path: Span<u8> = span_from_cstr(c"/")
```

This issue is present in all 23 library files and all 22 test files. The correct approach for string literals passed to span utilities would be `"GET".as_cstr()` or, preferably, redesigning the span utilities to accept `StrView` directly.

### 4. Missing `impl` Blocks — Free Functions Instead of Methods (Major)

The library uses the free-function style for all struct operations (`h1_request_init`, `h2_stream_apply_event`, etc.) rather than `impl` blocks. While the `fn Type.method()` syntax is deprecated but tolerated, the full free-function approach without any `impl` block is not idiomatic.

**Example — current pattern in `lib/h2_stream.ritz`:**
```ritz
pub fn h2_stream_init(stream: *H2Stream, id: i32)
pub fn h2_stream_is_idle(stream: *H2Stream) -> i32
pub fn h2_stream_can_send(stream: *H2Stream) -> i32
pub fn h2_stream_apply_event(stream: *H2Stream, event: i32) -> i32
```

**Preferred:**
```ritz
impl H2Stream
    fn init(self:& H2Stream, id: i32)
    fn is_idle(self: H2Stream) -> i32
    fn can_send(self: H2Stream) -> i32
    fn apply_event(self:& H2Stream, event: i32) -> i32
```

All 23 library files exhibit this pattern.

---

## Minor Issues

### 1. Boolean Returns as `i32` Instead of `bool`

All predicate functions return `i32` (0/1) instead of `bool`. Examples: `h2_stream_is_open`, `h2_stream_can_send`, `status_is_success`, `is_whitespace`, `span_eq_cstr_ci`. This is not a spec violation but is non-idiomatic for application-level code.

### 2. Missing Module Documentation Completeness

Some modules have good header doc comments (`h1_request.ritz`, `hpack.ritz`) but several modules (`limits.ritz`, `h1_utils.ritz`, `quic_varint.ritz`) have minimal or no overview documentation.

### 3. Error Constants as `i32` Return Codes Instead of `Result<T, E>`

All functions return `i32` error codes (e.g., `H1_ERR_INCOMPLETE = -1`, `H2_ERR_INVALID = -2`) rather than using `Result<T, E>`. This makes error propagation verbose and prevents use of the `?` operator for clean composition. The test files reflect this with manual comparisons like `if result < 0`.

### 4. Naming Convention: `is_*` Functions Prefixed with Type Name

Functions like `h2_stream_is_open`, `h1_request_is_keep_alive`, `status_is_success` repeat the type name in the function name, which is redundant in an `impl` block context and slightly verbose even as free functions.

### 5. Duplicate Constant Definitions

`HPACK_MAX_DYNAMIC_ENTRIES` and `HPACK_MAX_HEADERS` are defined in both `lib/hpack.ritz` and `lib/limits.ritz` (the latter intended as the canonical source). This creates potential inconsistency. Similarly, `H3_MAX_SETTINGS` is defined in both `lib/h3_frame.ritz` and `lib/limits.ritz`.

---

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | ISSUE | All functions use `*T` raw pointers; `:&` and `:=` modifiers not used |
| Reference Types (@) | OK | `@x` used correctly throughout for address-of operations |
| Attributes ([[...]]) | OK | `[[test]]` used correctly across all 22 test files; no `@test` found |
| Logical Operators | ISSUE | `&&` and `\|\|` used pervasively; `and`/`or`/`not` keywords absent |
| String Types | ISSUE | `c"..."` prefix used in application code; should use `"..."` or `.as_cstr()` at boundary |
| Error Handling | ISSUE | `i32` return codes used throughout; no `Result<T, E>` or `?` operator |
| Naming Conventions | OK | snake_case functions, PascalCase types, SCREAMING_SNAKE constants — all correct |
| Code Organization | OK | Good section separators, header comments, grouped imports |

---

## Files Needing Attention

**Highest priority (most violations):**
- `/home/aaron/dev/ritz-lang/rz/projects/http/lib/h2_stream.ritz` — 10+ `||` occurrences, all functions use `*T`
- `/home/aaron/dev/ritz-lang/rz/projects/http/lib/quic_migration.ritz` — 10+ `||`/`&&` occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/http/lib/hpack.ritz` — multiple `&&`/`||`, all `*T` params, `c"..."` everywhere
- `/home/aaron/dev/ritz-lang/rz/projects/http/lib/types.ritz` — `c"..."` for all string literals, `&&`/`||`
- `/home/aaron/dev/ritz-lang/rz/projects/http/lib/h1_utils.ritz` — `&&`/`||` in utility functions used by whole library
- `/home/aaron/dev/ritz-lang/rz/projects/http/test/test_hpack.ritz` — 56 `[[test]]` annotations; `||` in test assertions

**All test files** — `c"..."` prefix used for every string literal, `||` in multi-condition assertions.

---

## Recommendations

**Prioritized fix list:**

1. **Global find-and-replace: `&&` -> `and`, `||` -> `or`** — This is a mechanical transformation that should be done across all 45 files. It is the most impactful single change and straightforward to automate.

2. **Convert `*T` mutation parameters to `:&` mutable borrows** — Start with the most-used public APIs: `h1_request_init`, `h1_response_init`, `h2_stream_init`, `h2_stream_apply_event`, `hpack_decoder_init`, `hpack_encode_*`. This will require updating call sites (all the `@x` address-of expressions at call sites become unnecessary once the parameter is `:&`).

3. **Migrate `c"..."` literals in application code** — In string comparison and span helper calls, replace `c"foo"` with `"foo"` (StrView) where the API accepts StrView, or `"foo".as_cstr()` at FFI boundaries only. The `span_from_cstr` / `span_literal` helpers should ideally be updated to accept `StrView` directly.

4. **Introduce `Result<T, E>` error types** — Define an `HttpError` enum in `lib/types.ritz` and migrate the parsing functions to return `Result<i32, HttpError>`. This enables the `?` operator and eliminates the manual `if result < 0` checks throughout test and library code.

5. **Introduce `impl` blocks** — Group the free functions for each struct into `impl` blocks. This is a larger refactor but significantly improves readability and is the idiomatic Ritz pattern.

6. **Deduplicate constants** — Remove duplicate constant definitions from `lib/hpack.ritz` and `lib/h3_frame.ritz`; use the `lib/limits.ritz` versions as the canonical source.
