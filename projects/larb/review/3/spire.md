# LARB Review: Spire

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

Spire is a MVRSPT web framework for Ritz providing HTTP, routing, model types, service layer, repositories, presenters, CLI, and testing utilities. The library code (19 files, ~4946 SLOC) is largely well-structured with consistent use of `[[test]]`, `@` for address-of, and keyword logical operators. However, the codebase has two systemic issues: pervasive use of raw pointer `*T` parameters where borrow-style parameters should be used, and widespread use of the deprecated `c"..."` string prefix in application-level library code. The test suite additionally uses old-style `&x` address-of syntax throughout instead of `@x`.

## Statistics

- **Files Reviewed:** 30 (19 lib + 11 test, excluding httplib vendored/copied ritzlib)
- **Total SLOC:** ~7714 (lib ~4946, test ~2768)
- **Issues Found:** 71+ (Critical: 0, Major: 3 categories with ~60+ instances, Minor: several)

## Critical Issues

None. No code that will fail to compile with new syntax, no memory safety violations, no security vulnerabilities were found.

## Major Issues

### 1. Pervasive Raw Pointer Parameters Instead of Borrow Modifiers

Across all 13 lib files, function parameters use `*T` (raw pointer) where the Ritz spec mandates ownership modifier syntax. This is the most systemic issue in the project.

**Examples from `lib/http/request.ritz`:**
```ritz
# WRONG - raw pointer parameters
pub fn request_method(self: *Request) -> i32
pub fn request_path(self: *Request) -> Span<u8>
pub fn request_param(self: *Request, name: *Span<u8>, out_value: *Span<u8>) -> i32
pub fn request_with(method: i32, path: *Span<u8>) -> Request
```

**Should be:**
```ritz
# CORRECT - ownership modifier syntax
pub fn request_method(self: Request) -> i32           # const borrow (copy for i32 return)
pub fn request_path(self: Request) -> Span<u8>
pub fn request_param(self: Request, name: Span<u8>, out_value:& Span<u8>) -> i32
pub fn request_with(method: i32, path: Span<u8>) -> Request
```

**Files affected (all lib files):**
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/http/request.ritz` - ~20 functions with `*T` params
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/http/response.ritz` - ~10 functions with `*T` params
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/http/headers.ritz` - ~6 functions with `*T` params
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/router/mod.ritz` - ~8 functions with `*T` params
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/middleware/mod.ritz` - ~12 functions with `*T` params
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/service/mod.ritz` - ~10 functions with `*T` params
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/presenter/mod.ritz` - ~8 functions with `*T` params
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/form/mod.ritz` - ~6 functions with `*T` params
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/repo/mod.ritz` - ~4 functions with `*T` params
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/model/uuid.ritz` - ~5 functions with `*T` params
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/model/timestamp.ritz` - ~8 functions with `*T` params
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/test/mod.ritz` - ~6 functions with `*T` params
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/json/mod.ritz` - ~6 functions with `*T` params

Note: A limited number of `*T` usages are legitimate (FFI calls, low-level pointer arithmetic in inner loops), but the majority of `self: *Type` and parameter usages should be converted.

### 2. Old `c"..."` String Prefix in Application Library Code

The library modules use the deprecated `c"..."` prefix for C string literals in application-level code (content type strings, HTTP header names). Per the spec, these should use `"...".as_cstr()` for FFI contexts, or simply `"..."` (StrView) for application code.

**Examples from `lib/http/headers.ritz`:**
```ritz
# WRONG - old c"..." prefix in application library code
pub fn header_content_type() -> Span<u8>
    return span_from_cstr(c"Content-Type")

pub fn content_type_html() -> Span<u8>
    return span_from_cstr(c"text/html; charset=utf-8")
```

**Examples from `lib/http/request.ritz`:**
```ritz
# WRONG
let accept_name: Span<u8> = span_from_cstr(c"Accept")
let json_type: Span<u8> = span_from_cstr(c"application/json")
```

**Examples from `lib/http/response.ritz`:**
```ritz
# WRONG
response_set_header(@res, span_from_cstr(c"Content-Type"), span_from_cstr(c"text/html; charset=utf-8"))
```

**Files affected:**
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/http/headers.ritz` - 12 occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/http/request.ritz` - 9 occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/http/response.ritz` - 5 occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/model/uuid.ritz` - 1 occurrence (FFI path - acceptable)

Note: The `uuid.ritz` usage (`c"/dev/urandom"`) is for a syscall path and is acceptable. The HTTP header/content-type usages are application-level and should be updated.

### 3. Old `&x` Address-Of Syntax in All Test Files

All 11 test files consistently use the old `&x` address-of syntax instead of `@x`. This is systematic and affects every test function.

**Examples from `test/test_router.ritz`:**
```ritz
# WRONG - old & address-of syntax
router_get(&r, &path, handler_ok)
var req: Request = request_with(GET, &req_path)
let resp: Response = router_handle(&r, &req)
assert response_status_code(&resp) == 200
match request_param(&req, &param_name)
```

**Should be:**
```ritz
# CORRECT - @ address-of syntax
router_get(@r, @path, handler_ok)
var req: Request = request_with(GET, @req_path)
let resp: Response = router_handle(@r, @req)
assert response_status_code(@resp) == 200
match request_param(@req, @param_name)
```

**Files affected (all test files):**
- `/home/aaron/dev/ritz-lang/rz/projects/spire/test/test_router.ritz` - ~60+ occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/spire/test/test_http_request.ritz` - ~40+ occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/spire/test/test_integration.ritz` - ~50+ occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/spire/test/test_app.ritz` - multiple occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/spire/test/test_http_response.ritz` - multiple occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/spire/test/test_http_headers.ritz` - multiple occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/spire/test/test_model_uuid.ritz` - multiple occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/spire/test/test_model_timestamp.ritz` - multiple occurrences
- And all remaining test files

## Minor Issues

### 1. Documentation Comments Use Old `@export`, `@model` Attribute Syntax

The documentation examples in `lib/app/mod.ritz`, `lib/mod.ritz`, and `lib/model/mod.ritz` show users how to write `@export` and `@model` attributes, but the spec mandates `[[export]]` and `[[model]]`. While these are only in comments, they will mislead application developers.

**Example from `lib/app/mod.ritz` (comment, line 14):**
```ritz
#   @export
#   fn app_create() -> *MyApp
```

**Should document:**
```ritz
#   [[export]]
#   fn app_create() -> *MyApp
```

**Files affected:**
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/app/mod.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/mod.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/model/mod.ritz`

### 2. Method Organization: Free Functions Instead of `impl` Blocks

All types use free function style (`fn request_method(self: *Request)`) rather than `impl` blocks. This is flagged as deprecated. It is a pervasive stylistic issue across the whole codebase.

**Example from `lib/http/request.ritz`:**
```ritz
# DEPRECATED STYLE
pub fn request_method(self: *Request) -> i32
    return self.method

pub fn request_path(self: *Request) -> Span<u8>
    ...
```

**Preferred:**
```ritz
impl Request
    pub fn method(self: Request) -> i32
        return self.method

    pub fn path(self: Request) -> Span<u8>
        ...
```

The instructions note this is "tolerated for now," so this is a low-priority issue.

### 3. No `defer` for Resource Cleanup in `uuid.ritz`

In `lib/model/uuid.ritz`, the file descriptor opened for `/dev/urandom` is closed manually, which is correct, but is not using `defer` immediately after acquisition:

```ritz
# Current - manual close (works but not idiomatic)
let fd: i64 = open(c"/dev/urandom", 0, 0)
if fd >= 0
    read(fd, @uuid.bytes[0], 16)
    close(fd)
```

**Preferred:**
```ritz
let fd: i64 = open("/dev/urandom".as_cstr(), 0, 0)
if fd >= 0
    defer close(fd)
    read(fd, @uuid.bytes[0], 16)
```

### 4. `or` Used Correctly Except One Case in Test File

The `test/test_router.ritz` line 223 uses `or` correctly in an expression:
```ritz
assert response_status_code(&resp) == 200 or response_status_code(&resp) == 201
```
This is idiomatic. All logical operator usage in lib files was checked and found to be correct (`and`, `or`, `not` keywords used throughout).

### 5. Duplicate Helper Function Definitions

`push_strview`, `push_i64`, `push_u64` are defined independently in multiple files (`lib/middleware/mod.ritz`, `lib/test/mod.ritz`, `lib/presenter/mod.ritz`). These should be consolidated into `lib/utils.ritz` and re-exported.

### 6. Missing `return` Keywords (Style)

Some functions use implicit returns (last expression is the return value), others use explicit `return`. The codebase is inconsistent:
```ritz
# Implicit (ok in Ritz)
fn handler_ok(req: *Request) -> Response
    response_ok()

# Explicit (also ok)
pub fn response_ok() -> Response
    return response_with_status(STATUS_OK)
```
Pick one style and be consistent.

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | ISSUE | `*T` raw pointers used for all `self` and reference params; should use `: T` (const borrow), `:& T` (mut borrow), or `:= T` (move) |
| Reference Types (@) | ISSUE | Lib code uses `@x` correctly; all 11 test files use old `&x` syntax throughout |
| Attributes ([[...]]) | OK | `[[test]]` used correctly in all test files; `@export`/`@model` only appear in documentation comments (see minor issues) |
| Logical Operators | OK | `and`, `or`, `not` used correctly throughout lib and test files |
| String Types | ISSUE | 26 uses of deprecated `c"..."` prefix in application-level HTTP library code; acceptable in `uuid.ritz` FFI context |
| Error Handling | OK | `Result<T, E>` and `Option<T>` used correctly; `match` used appropriately; `?` operator not yet used but acceptable given language maturity |
| Naming Conventions | OK | PascalCase types, snake_case functions/variables, SCREAMING_SNAKE_CASE constants - all correct |
| Code Organization | OK | Files well-organized with sections; imports grouped; constants before types; helpers at end |

## Files Needing Attention

**Priority 1 (Major - address-of syntax):**
- `/home/aaron/dev/ritz-lang/rz/projects/spire/test/test_router.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/spire/test/test_http_request.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/spire/test/test_integration.ritz`
- All other files in `/home/aaron/dev/ritz-lang/rz/projects/spire/test/`

**Priority 2 (Major - c"..." strings):**
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/http/headers.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/http/request.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/http/response.ritz`

**Priority 3 (Major - ownership modifiers, longer effort):**
- All 19 files in `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/`

**Priority 4 (Minor - docs, consolidation):**
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/app/mod.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/model/mod.ritz`
- `/home/aaron/dev/ritz-lang/rz/projects/spire/lib/utils.ritz`

## Recommendations

1. **Immediate: Fix `&x` -> `@x` in all test files.** This is a straightforward mechanical change (search/replace `&` address-of uses). ~100+ occurrences across 11 files.

2. **Short-term: Replace `c"..."` with `"..."` (StrView) in HTTP lib.** The header name constants and content-type strings in `headers.ritz`, `request.ritz`, and `response.ritz` are application-level strings that can be plain `StrView` literals. Replace `span_from_cstr(c"Content-Type")` with `"Content-Type"` (or an appropriate StrView binding).

3. **Medium-term: Convert `*T` params to ownership modifier syntax.** This requires careful analysis of each function to determine if the intent is const borrow (`: T`), mutable borrow (`:& T`), or move (`:= T`). Given the breadth (~60+ functions), prioritize the public API surface first: `request.*`, `response.*`, `router.*`.

4. **Minor: Update documentation comments** in `app/mod.ritz` and `model/mod.ritz` to show `[[export]]` and `[[model]]` instead of `@export` and `@model`.

5. **Minor: Consolidate helper functions** (`push_strview`, `push_i64`, etc.) into `lib/utils.ritz` to eliminate duplication across middleware, test, and presenter modules.

---

*LARB Review 3 - Spire - February 2026*
