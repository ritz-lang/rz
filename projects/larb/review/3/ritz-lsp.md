# LARB Review: ritz-lsp

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** CRITICAL

## Summary

ritz-lsp is a Language Server Protocol implementation that communicates over stdio using JSON-RPC 2.0. The project is pervasively using old/wrong syntax across all files: raw pointer parameters (`*T`) are used everywhere instead of ownership modifiers, `&x` address-of expressions instead of `@x`, `c"..."` string literals instead of `"...".as_cstr()`, and `||` / `&&` logical operators instead of `or` / `and`. Every source file requires substantial rework before it conforms to Ritz v0.2.0 idioms.

## Statistics

- **Files Reviewed:** 6 (src/server.ritz, src/documents.ritz, src/transport.ritz, src/protocol.ritz, src/main.ritz, test.ritz)
- **Total SLOC:** ~370
- **Issues Found:** 48+ (Critical: 30+, Major: 15+, Minor: 3)

## Critical Issues

### 1. Raw Pointer Parameters Instead of Ownership Modifiers (All Files)

Every function that takes a mutable or borrowed aggregate uses `*T` raw pointer syntax. This is the single largest systemic violation. Raw pointers belong only in FFI/unsafe contexts; ordinary borrowing must use the colon-modifier syntax.

**Affected functions (representative sample):**

`src/server.ritz`:
```ritz
pub fn server_drop(s: *Server)                               # should be s:& Server
fn handle_initialize(s: *Server, msg: *LspMessage)           # s:& Server, msg: LspMessage
fn handle_initialized(s: *Server, msg: *LspMessage)
fn handle_shutdown(s: *Server, msg: *LspMessage)
fn handle_exit(s: *Server, msg: *LspMessage) -> i32
fn handle_did_open(s: *Server, msg: *LspMessage)
fn handle_did_change(s: *Server, msg: *LspMessage)
fn handle_did_close(s: *Server, msg: *LspMessage)
fn handle_hover(s: *Server, msg: *LspMessage)
fn handle_definition(s: *Server, msg: *LspMessage)
pub fn dispatch_message(s: *Server, msg: *LspMessage) -> i32
pub fn server_run(s: *Server) -> i32
```

`src/documents.ritz`:
```ritz
pub fn document_store_drop(store: *DocumentStore)
pub fn document_find(store: *DocumentStore, uri: *u8) -> i32
pub fn document_open(store: *DocumentStore, uri: *u8, content: *u8, version: i64) -> i32
pub fn document_change(store: *DocumentStore, uri: *u8, content: *u8, version: i64) -> i32
pub fn document_close(store: *DocumentStore, uri: *u8) -> i32
pub fn document_get(store: *DocumentStore, uri: *u8) -> *Document
```

`src/transport.ritz`:
```ritz
pub fn transport_drop(t: *Transport)
pub fn read_exact(buf: *u8, n: i64) -> i32
pub fn write_message_vec(buf: *Vec<u8>)
```

`src/protocol.ritz`:
```ritz
pub fn lsp_message_free(msg: *LspMessage)
pub fn build_response(id: i64, result_json: *u8, buf: *Vec<u8>)
pub fn build_error_response(id: i64, code: i32, message: *u8, buf: *Vec<u8>)
pub fn build_notification(method: *u8, params_json: *u8, buf: *Vec<u8>)
```

`src/main.ritz`:
```ritz
let exit_code: i32 = server_run(&s)
server_drop(&s)
```

**Correct form example:**
```ritz
pub fn server_drop(s:& Server)
fn handle_initialize(s:& Server, msg: LspMessage)
pub fn dispatch_message(s:& Server, msg: LspMessage) -> i32
```

### 2. `&x` Address-Of Instead of `@x` (Multiple Files)

Every call site uses `&x` to take an address. This should be `@x` (immutable ref) or `@&x` (mutable ref).

`src/server.ritz` (lines 35-36, 50, 65, 164, 170, 207, 227, 229, 232):
```ritz
document_store_drop(&s.documents)      # should be @&s.documents
vec_drop<u8>(&s.response_buf)          # should be @&s.response_buf
build_response(msg.id, result, &s.response_buf)    # @&s.response_buf
```

`src/documents.ritz` (line 151):
```ritz
return &store.docs[idx]                # should be @store.docs[idx]
```

`src/transport.ritz` (lines 39, 52, 56, 63-65, 74, 77, 81, 86):
```ritz
let n: i64 = sys_read(STDIN, &buf[0], 1)    # @buf[0] or @&buf[0]
vec_clear<u8>(&line_buf)                     # @&line_buf
vec_drop<u8>(&line_buf)                      # @&line_buf
vec_push<u8>(&line_buf, ch as u8)            # @&line_buf
```

`src/main.ritz` (lines 15-16):
```ritz
let exit_code: i32 = server_run(&s)     # @&s
server_drop(&s)                          # @&s
```

### 3. `c"..."` String Literals Instead of `"...".as_cstr()` (All Files)

The old `c"..."` prefix is used pervasively in every file for all C-string literals passed to FFI functions.

`src/server.ritz` - 20+ occurrences:
```ritz
eprints_cstr(c"[ritz-lsp] Handling initialize\n")   # should be "[ritz-lsp] Handling initialize\n".as_cstr()
let result: *u8 = c"{\"capabilities\":..."            # should be "{...}".as_cstr()
build_response(msg.id, c"null", &s.response_buf)     # "null".as_cstr()
if streq(msg.method, c"initialize") != 0             # "initialize".as_cstr()
```

`src/transport.ritz`:
```ritz
if strneq(line_buf.data, c"Content-Length:", 15) != 0
prints_cstr(c"Content-Length: ")
prints_cstr(c"\r\n\r\n")
```

`src/protocol.ritz` - many occurrences:
```ritz
eprints_cstr(c"[ritz-lsp] JSON parse error at position ")
vec_push_str(buf, c"{\"jsonrpc\":\"2.0\",\"id\":")
```

`src/main.ritz`:
```ritz
eprints_cstr(c"[ritz-lsp] Ritz Language Server v0.1.0\n")
```

`test.ritz`:
```ritz
prints(c"\n")   # "\n".as_cstr()
```

### 4. `||` Logical OR Instead of `or` (server.ritz, transport.ritz)

`src/server.ritz` (line 88):
```ritz
if uri_val == null || text_val == null      # should be: or
```

`src/server.ritz` (line 117):
```ritz
if changes == null || changes.kind != JSON_ARRAY || changes.count == 0   # should be: or
```

`src/server.ritz` (line 232):
```ritz
if s.shutdown_requested != 0 && streq(msg.method, c"exit") != 0         # should be: and
```

`src/transport.ritz` (lines 81, 87):
```ritz
while i < line_buf.len && *(line_buf.data + i) == ' '    # should be: and
if c >= '0' && c <= '9'                                   # should be: and
```

## Major Issues

### 5. All Functions Use Standalone `fn Type.method()` Style Rather Than `impl` Blocks

None of the source files use `impl` blocks. All functions are free-standing with explicit receiver parameters or module-prefixed names. While tolerated as deprecated, the `impl` block form is strongly preferred:

```ritz
# Current (deprecated style):
pub fn server_drop(s: *Server)
pub fn server_run(s: *Server) -> i32

# Preferred:
impl Server
    pub fn drop(self:& Server)
    pub fn run(self:& Server) -> i32
```

### 6. No Use of `defer` for Resource Cleanup (`documents.ritz`, `transport.ritz`, `server.ritz`)

Resources are freed manually at multiple exit points. `defer` should be used immediately after acquisition.

`src/transport.ritz` - `read_headers()` frees `line_buf` at two separate points (lines 57 and 93) instead of using `defer`:
```ritz
# Current:
var line_buf: Vec<u8> = vec_with_cap<u8>(256)
loop
    ...
    if ch == -1
        vec_drop<u8>(&line_buf)   # manual early return cleanup
        return -1
    ...
vec_drop<u8>(&line_buf)           # manual normal-path cleanup
return content_length

# Preferred:
var line_buf: Vec<u8> = vec_with_cap<u8>(256)
defer vec_drop<u8>(@&line_buf)
...
```

`src/transport.ritz` - `read_message()` manually frees `buf` on error path (line 119):
```ritz
let buf: *u8 = malloc(content_length + 1)
if read_exact(buf, content_length) != 0
    free(buf)     # should use defer + Result
    return null
```

### 7. Error Handling: Null Returns Instead of `Result<T, E>` (`transport.ritz`, `documents.ritz`)

Functions return `null` or `-1` sentinel values for errors rather than `Result`. This suppresses the `?` propagation idiom entirely.

```ritz
# Current:
pub fn read_message() -> *u8       # returns null on error
pub fn document_find(...) -> i32   # returns -1 on error

# Preferred:
pub fn read_message() -> Result<String, LspError>
pub fn document_find(...) -> Result<i32, LspError>
```

### 8. `!=` Comparison Used as Boolean (`server.ritz`, `documents.ritz`)

Instead of checking boolean conditions directly, the code compares against 0 or null repeatedly:

```ritz
if s.shutdown_requested != 0   # should be: if s.shutdown_requested
if streq(msg.method, c"initialize") != 0  # acceptable if streq returns i32
if uri_val == null             # acceptable null check
```

Minor for the `!= 0` pattern on `i32` booleans - but worth making consistent.

## Minor Issues

### 9. Naming: `s` as Single-Letter Parameter for `Server` (`server.ritz`, `main.ritz`)

Single-letter variable names are acceptable in very tight contexts but `server` or `srv` would be clearer given the function sizes.

### 10. Missing Module-Level Documentation in `test.ritz`

`test.ritz` has no header comment describing its purpose. All other files have a brief module docstring.

### 11. No `[[test]]` Attribute on Test Functions

`test.ritz` defines what appears to be a test/demo `main()` function but does not use `[[test]]` attributes on any test functions. If this file is meant to contain proper unit tests, the individual test functions should be marked with `[[test]]`.

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | CRITICAL ISSUE | All aggregate params use `*T` raw pointers instead of `:&` or `:=` modifiers |
| Reference Types (@) | CRITICAL ISSUE | All address-of uses `&x` instead of `@x` or `@&x` throughout every file |
| Attributes ([[...]]) | OK | No `@test`/`@inline` old-style usage found; test file does not use `[[test]]` but does not use old syntax either |
| Logical Operators | CRITICAL ISSUE | `&&` and `\|\|` used in server.ritz and transport.ritz instead of `and`/`or` |
| String Types | CRITICAL ISSUE | `c"..."` prefix used pervasively in all files (20+ occurrences) |
| Error Handling | MAJOR ISSUE | Null/sentinel returns used throughout; no `Result<T,E>` or `?` operator anywhere |
| Naming Conventions | OK | snake_case functions, PascalCase types, SCREAMING_SNAKE constants all correct |
| Code Organization | OK | File structure is reasonable; imports grouped correctly; section comments used |

## Files Needing Attention

All files require attention. Priority order:

1. **`src/server.ritz`** - Most violations: raw pointers, `&x` refs, `c"..."` strings, `&&`/`||` operators, no `defer`
2. **`src/transport.ritz`** - Raw pointers, `&x` refs, `c"..."` strings, `&&` operators, missing `defer`, null return instead of `Result`
3. **`src/documents.ritz`** - Raw pointers, `&x` refs, null/sentinel error returns, no `defer`
4. **`src/protocol.ritz`** - Raw pointers, `&x` refs, `c"..."` strings throughout
5. **`src/main.ritz`** - `&s` refs, `c"..."` literal
6. **`test.ritz`** - `c"..."` literal, no `[[test]]` attribute usage

## Recommendations

1. **[CRITICAL] Replace all `*T` function parameters with ownership modifiers.** Any parameter being mutated should use `:&`, any that transfers ownership should use `:=`, and const borrows use `: T` (no sigil). This is the most pervasive issue and affects every function signature in the project.

2. **[CRITICAL] Replace all `&x` address-of expressions with `@x` (immutable) or `@&x` (mutable).** Mechanically search for `(&` and `= &` patterns across all files.

3. **[CRITICAL] Replace all `c"..."` literals with `"...".as_cstr()`.** This is a mechanical substitution. Note: since this is application-layer LSP code, not low-level kernel code, the exemption for `c"..."` in FFI contexts does not broadly apply here.

4. **[CRITICAL] Replace `&&` with `and` and `\|\|` with `or` in all conditional expressions.** Found in `server.ritz` (lines 88, 117, 232) and `transport.ritz` (lines 81, 87).

5. **[MAJOR] Migrate error returns to `Result<T, E>`.** Define an `LspError` enum and use `?` propagation. Functions like `read_message()`, `document_find()`, `document_open()` are the primary candidates.

6. **[MAJOR] Add `defer` for all resource cleanup.** Replace the dual free-site pattern in `read_headers()` and `read_message()` with `defer` immediately after allocation.

7. **[MAJOR] Consider migrating to `impl` blocks** for `Server`, `DocumentStore`, `Transport`, and `LspMessage`. Not required immediately but reduces naming clutter and follows the preferred idiom.
