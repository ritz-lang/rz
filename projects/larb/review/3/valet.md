# LARB Review: Valet

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

Valet is a high-performance async HTTP server with TLS 1.3 support, static file serving, routing, compression, and connection pooling. The codebase is well-organized and functionally mature, but it systematically uses pre-specification syntax throughout: `c"..."` string literals (should be `"...".as_cstr()`), `&&`/`||` logical operators (should be `and`/`or`), and `*T` raw pointer parameters everywhere application-layer borrows are intended (should use `:&`/`:=`/undecorated borrow modifiers). Tests correctly use `[[test]]` attributes, which is the one area fully compliant with the spec.

## Statistics

- **Files Reviewed:** 21
- **Total SLOC:** ~3,800
- **Issues Found:** ~180+ (Critical: 0, Major: ~180+, Minor: ~15)

---

## Critical Issues

None. The syntax deviations are consistent with older Ritz idioms and do not represent unsafe patterns beyond what the language currently supports. The `*T` usage is pervasive but the code was evidently written before the ownership modifier syntax was finalized.

---

## Major Issues

### 1. Pervasive `c"..."` String Literal Prefix (MAJOR)

Every file in the project uses the old `c"..."` C-string prefix syntax. Per the finalized spec, application code should use `"hello".as_cstr()` for FFI calls and plain `"hello"` (which gives `StrView`) for general use.

**Affected files: ALL 21 files**

Selected examples:

`src/main.ritz`:
```ritz
# Line 35, 36, 55, 60, 68, 75, etc. - ALL string literals
log_info(c"Request: ")
return ctx_ok(c"Hello, World!")
return ctx_text(400, c"Missing user ID\n")
let prefix = c"User ID: "
```

`lib/valet.ritz`:
```ritz
# Line 244, 247-252, 331, 345, 360, etc.
valet_use_named(@app, c"logging", logging_middleware)
valet_get(@app, c"/", handle_index)
response_header(c.res, c"Content-Type", c"text/plain")
return ctx_text(404, c"404 Not Found\n")
```

`lib/log.ritz`:
```ritz
# Line 233, 237, 241, 245
log_write(LOG_DEBUG, c"DEBUG", msg)
log_write(LOG_INFO, c"INFO", msg)
```

`lib/static.ritz`:
```ritz
# Lines 31-103, hundreds of occurrences
return c"text/html"
return c"application/javascript"
log_error(c"sendfile failed")
```

**Scope:** Approximately 150+ occurrences across all 21 files. The `c"..."` prefix is used for every string literal without exception.

---

### 2. Symbolic Logical Operators `&&` and `||` (MAJOR)

The finalized spec requires keyword operators `and`, `or`, `not` instead of `&&`, `||`, `!`. The codebase uses the old symbols in multiple files.

**Affected files:** `src/main.ritz`, `lib/valet.ritz`, `lib/request.ritz`, `lib/static.ritz`, `lib/compress.ritz`, `lib/pool.ritz`, `lib/config.ritz`

Examples:

`src/main.ritz` line 183:
```ritz
if config_path != null && *config_path != 0
```
Should be:
```ritz
if config_path != null and *config_path != 0
```

`src/main.ritz` line 209:
```ritz
if cfg.port <= 0 || cfg.port > 65535
```
Should be:
```ritz
if cfg.port <= 0 or cfg.port > 65535
```

`lib/valet.ritz` line 403:
```ritz
if selected != ENCODING_IDENTITY && body_len >= COMPRESS_MIN_SIZE && body_len <= COMPRESS_MAX_INPUT
```
Should be:
```ritz
if selected != ENCODING_IDENTITY and body_len >= COMPRESS_MIN_SIZE and body_len <= COMPRESS_MAX_INPUT
```

`lib/valet.ritz` line 456:
```ritz
if compressed_len > 0 && compressed_len < body_len
```

`lib/request.ritz` line 114:
```ritz
if *(buf + pos) != '\r' || *(buf + pos + 1) != '\n'
```

`lib/request.ritz` line 124:
```ritz
if *(buf + pos) == '\r'
    if pos + 1 < len && *(buf + pos + 1) == '\n'
```

`lib/request.ritz` line 202:
```ritz
if *(buf + pos) == '\r' && *(buf + pos + 1) == '\n'
```

`lib/static.ritz` line 169-172 (multiple conditions):
```ritz
if *(range_hdr + 0) != 'b' || *(range_hdr + 1) != 'y' || *(range_hdr + 2) != 't'
    return result
if *(range_hdr + 3) != 'e' || *(range_hdr + 4) != 's' || *(range_hdr + 5) != '='
    return result
```

`lib/pool.ritz` line 62:
```ritz
if block_count <= 0 || block_count > POOL_MAX_BLOCKS
```

`lib/config.ritz` line 120:
```ritz
if max_size > 0 && len > max_size
```

`lib/static.ritz` line 554-555:
```ritz
if if_none_match != null && if_none_match_len > 0
    if etag_matches(...) != 0
```

`lib/static.ritz` line 566:
```ritz
if range_hdr != null && range_len > 0
```

**Total occurrences:** Approximately 25+ across 7 files.

---

### 3. Ownership Modifiers - Raw `*T` Pointers Instead of Borrow Syntax (MAJOR)

Every function in the project uses raw pointer syntax `*T` for parameters that should use the finalized colon-modifier borrow syntax. For an application-layer project (not kernel/FFI), this is a major idiom violation.

**Affected files: ALL 21 files**

The spec says:
- `x: T` — const borrow (or copy for primitives)
- `x:& T` — mutable borrow
- `x:= T` — move ownership
- `*T` — raw pointer (FFI/unsafe only)

Examples in `lib/valet.ritz`:
```ritz
# WRONG - using raw pointers for application-level parameters
pub fn valet_init(app: *Valet, port: i32)
pub fn valet_get(app: *Valet, pattern: *u8, handler: fn(*u8, i32) -> i32) -> i32
pub fn ctx_text(status: i32, body: *u8) -> i32
pub fn valet_tls(app: *Valet, cert_pem: *u8, cert_pem_len: i64, ...) -> i32
```

Should be:
```ritz
pub fn valet_init(app:& Valet, port: i32)
pub fn valet_get(app:& Valet, pattern: StrView, handler: fn(StrView) -> i32) -> i32
pub fn ctx_text(status: i32, body: StrView) -> i32
```

Examples in `lib/request.ritz`:
```ritz
# WRONG
pub fn request_parse(req: *Request, buf: *u8, len: i32) -> i32
pub fn request_find_header(buf: *u8, buf_len: i32, name: *u8, name_len: i32) -> HeaderResult
```

Examples in `lib/router.ritz`:
```ritz
# WRONG
pub fn router_init(r: *Router)
pub fn router_add(r: *Router, method: *u8, pattern: *u8, handler: fn(*u8, i32) -> i32) -> i32
pub fn route_match_get_param(result: *RouteMatch, idx: i32, buf: *u8, buf_len: i32) -> i32
```

Examples in `lib/log.ritz`:
```ritz
# WRONG - msg could be StrView, not raw pointer
pub fn log_write(level: i32, level_str: *u8, msg: *u8)
pub fn log_debug(msg: *u8)
pub fn log_info(msg: *u8)
```

Examples in `lib/static.ritz`:
```ritz
# WRONG
pub fn path_is_safe(path: *u8, path_len: i32) -> i32
pub fn static_serve_file(fd: i32, path: *u8) -> i64
pub fn static_build_path(buf: *u8, buf_len: i32, root: *u8, ...) -> i32
```

**Scope:** Every public function across all 21 files. This is the single largest systematic issue in the codebase. The entire public API needs to be migrated to borrow syntax once the compiler supports it broadly.

---

### 4. Old `fn Type.method()` Style vs `impl` Blocks (MAJOR)

All method-like functions use the free-standing `fn module_action(obj: *Type)` pattern instead of `impl Type` blocks. This is deprecated but tolerated per the instructions, so logged as major rather than critical.

**Affected files: ALL library files**

Examples from `lib/valet.ritz`:
```ritz
# Current (deprecated)
pub fn valet_init(app: *Valet, port: i32)
pub fn valet_run(app: *Valet) -> i32
pub fn valet_get(app: *Valet, ...) -> i32
```

Preferred:
```ritz
impl Valet
    pub fn init(self:& Valet, port: i32)
    pub fn run(self:& Valet) -> i32
    pub fn get(self:& Valet, ...) -> i32
```

This affects `Router`, `Request`, `Response`, `MemPool`, `ValetConfig`, `TlsServer`, `TlsServerConfig`, `JsonBuilder`, `StreamCompressor`, etc. — every struct in the project.

---

### 5. Missing `defer` for Resource Cleanup (MAJOR)

Several functions open file descriptors and close them manually, rather than using `defer` immediately after acquisition.

`lib/valet.ritz`, `valet_tls_files` (lines 188-216):
```ritz
# WRONG - manual close, no defer
let cert_fd: i32 = sys_open(cert_path, 0)
if cert_fd < 0
    return -1
let cert_len: i64 = sys_read(cert_fd, @cert_buf[0], 8192)
sys_close(cert_fd)      # Manual close - no defer
if cert_len <= 0
    return -2           # Would leak fd if cert_fd was open

let key_fd: i32 = sys_open(key_path, 0)
...
let key_len: i64 = sys_read(key_fd, @key_buf[0], 4096)
sys_close(key_fd)       # Manual close - no defer
```

Preferred:
```ritz
let cert_fd: i32 = sys_open(cert_path, 0)?
defer sys_close(cert_fd)

let cert_len: i64 = sys_read(cert_fd, @cert_buf[0], 8192)
if cert_len <= 0
    return -2
```

`lib/config.ritz`, `config_load` (lines 240-289): Same pattern — fd opened, reads performed, closed manually. No `defer`.

`lib/static.ritz`, `static_serve_file` and `static_serve_file_full`: Same pattern. File fd opened without defer, manually closed in multiple paths.

---

### 6. Nested `if` Chains Instead of `?` Operator (MAJOR)

Several functions perform repeated error checks that could use the `?` operator for cleaner propagation.

`lib/response.ritz`, `response_status` (lines 189-208):
```ritz
# Deeply nested if-else chains instead of cleaner patterns
if code == 200
    response_append_span(res, S_200_OK())
else
    if code == 404
        response_append_span(res, S_404_NOT_FOUND())
    else
        if code == 400
            ...
            else
                if code == 500
                    ...
```

`lib/tls/handshake.ritz`, `client_hello_parse`: Many error-returning checks that could use `?`.

---

## Minor Issues

### 1. Naming Conventions - Minor Deviations

`lib/valet.ritz` global variables use a `g_` prefix which is acceptable but non-standard:
```ritz
var g_app_ptr: i64 = 0
var g_ctx_ptr: i64 = 0
var g_tls_pool_ptr: i64 = 0
```
This is a reasonable pattern for globals and is acceptable, but worth noting.

### 2. Code Organization - Module Headers

All files have good header documentation comments. File organization generally follows the recommended order (imports, constants, types, functions). This is well done.

### 3. Missing `pub` on Some Internal Helpers

`lib/tls/handshake.ritz` has functions marked without `pub` (`fn handshake_parse_header`, `fn handshake_write_header`, `fn client_hello_parse`, etc.) which is correct for internal helpers. However `lib/static.ritz` marks `format_hex64` and `format_int64` as `pub` when they appear to be internal utilities only. Minor visibility scope issue.

### 4. `test_tls.ritz` Uses `ritzunit.assertions` Import Style

`tests/test_tls.ritz` imports `ritzunit.assertions` and `ritzunit.types` and uses `assert_eq_i32()` style assertions, while the other test files (`test_router.ritz`, `test_compress.ritz`, `test_config.ritz`, `test_pool.ritz`) use manual `if ... return error_code` patterns. This inconsistency across tests is a minor style issue — the ritzunit assertion style is preferred and should be adopted consistently.

### 5. `compress.ritz` Uses `pub struct` Syntax

`lib/compress.ritz` uses `pub struct StreamCompressor` (line 387) while all other struct definitions across the project use plain `struct` without `pub`. This inconsistency should be resolved one way or the other.

---

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | ISSUE | All parameters use `*T` raw pointer syntax instead of `:`, `:&`, `:=` borrow modifiers |
| Reference Types (@) | OK | `@x` syntax for address-of is used correctly throughout |
| Attributes ([[...]]) | OK | Tests correctly use `[[test]]`, no old `@test` syntax found |
| Logical Operators | ISSUE | `&&` and `\|\|` used in ~25+ places across 7 files; should be `and`/`or` |
| String Types | ISSUE | `c"..."` prefix used on every string literal in all 21 files; should use `"..."` or `"...".as_cstr()` |
| Error Handling | ISSUE | No use of `?` operator; manual fd cleanup without `defer` in multiple places |
| Naming Conventions | OK | snake_case functions/variables, PascalCase types, SCREAMING_SNAKE constants all followed |
| Code Organization | OK | Files well-structured with header comments, grouped imports, constants before types |

---

## Files Needing Attention

**High priority (most `&&`/`||` violations):**
- `/home/aaron/dev/ritz-lang/rz/projects/valet/lib/request.ritz` — 6+ `&&`/`||` in parser
- `/home/aaron/dev/ritz-lang/rz/projects/valet/lib/static.ritz` — 5+ `&&`/`||` in range/ETag logic
- `/home/aaron/dev/ritz-lang/rz/projects/valet/lib/valet.ritz` — 4+ `&&`/`||` in compression helpers
- `/home/aaron/dev/ritz-lang/rz/projects/valet/src/main.ritz` — 3 `&&`/`||` in arg validation

**High priority (missing defer):**
- `/home/aaron/dev/ritz-lang/rz/projects/valet/lib/valet.ritz` — `valet_tls_files`
- `/home/aaron/dev/ritz-lang/rz/projects/valet/lib/config.ritz` — `config_load`
- `/home/aaron/dev/ritz-lang/rz/projects/valet/lib/static.ritz` — `static_serve_file`, `static_serve_file_full`, `static_serve_directory`

**High priority (c"..." strings - start here for incremental migration):**
- `/home/aaron/dev/ritz-lang/rz/projects/valet/lib/log.ritz` — simplest file, 10 occurrences, good first target
- `/home/aaron/dev/ritz-lang/rz/projects/valet/lib/json_builder.ritz` — 10 occurrences, simple helpers

**For ownership modifier migration (longer term):**
- All 21 files require API changes once compiler borrow syntax is fully supported

---

## Recommendations

**Priority 1 (Fix immediately - quick wins):**
1. Replace all `&&` with `and` and all `||` with `or` across 7 files (~25 occurrences). Purely mechanical change, no semantic impact.
2. Add `defer sys_close(fd)` in `valet_tls_files`, `config_load`, and the static file serving functions. Reduces resource leak risk.

**Priority 2 (Fix in next sprint):**
3. Migrate `c"..."` string literals to `"..."` (StrView) where the string is not being passed to a C FFI function, and to `"...".as_cstr()` where FFI is required. Start with `log.ritz` and `json_builder.ritz` as the simplest files.
4. Standardize test assertion style: adopt `ritzunit.assertions` (as seen in `test_tls.ritz`) consistently across all test files.

**Priority 3 (Longer term - requires compiler support):**
5. Migrate function signatures from `*T` pointer parameters to the borrow modifier syntax (`:`, `:&`, `:=`). This should be done module by module, starting with the higher-level API layer (`valet.ritz`, `router.ritz`) and working down.
6. Convert free-standing functions to `impl` blocks per struct.

**Do not change:**
- The `[[test]]` attribute usage — already correct.
- The `@x` reference syntax — already correct throughout.
- The `*T` usage in `lib/tls/` sub-modules and `lib/pool.ritz` — these interact with raw memory and are closer to system-level code where raw pointer usage is more justifiable.
