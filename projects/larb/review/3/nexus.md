# LARB Review: Nexus

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

Nexus is a wiki application (knowledge base) built on the Ritz ecosystem, providing HTTP serving, wiki page CRUD, a cache-aside layer backed by Tome, and storage via Mausoleum. The project is well-structured across models/repos/services/presenters layers with solid error type hierarchy. However, there is a systematic and critical inconsistency in attribute syntax: most test files use the old `@test` annotation while `test_simple.ritz` correctly uses `[[test]]`, and the source files contain widespread use of raw pointers (`*T`) for mutable parameters where `:&` borrows are idiomatic, plus persistent use of old `s"..."` and `c"..."` string prefixes throughout.

## Statistics

- **Files Reviewed:** 19
- **Total SLOC:** ~750
- **Issues Found:** 28 (Critical: 2, Major: 18, Minor: 8)

## Critical Issues

### 1. Mixed Attribute Syntax - `@test` vs `[[test]]`

The majority of test files use the deprecated `@test` syntax. `test_simple.ritz` correctly uses `[[test]]`, proving the team knows the correct syntax, yet it was not applied consistently.

**Files affected:** `test/test_models.ritz`, `test/test_services.ritz`, `test/test_errors.ritz`

**`test/test_models.ritz` lines 23, 37, 54, 71, 94, 107:**
```ritz
# WRONG:
@test
fn test_wiki_page_new() -> i32

# CORRECT:
[[test]]
fn test_wiki_page_new() -> i32
```

All 17 test functions across these three files use `@test`. This is a critical regression because `@test` conflicts with the `@` address-of operator and will not compile correctly under the finalized spec.

### 2. Raw Pointers Used for Mutable Parameters in Application Code

`*WikiPage`, `*WikiPageRepository`, `*PageCache`, `*WikiService`, `*PageLink`, and `*Response` are used extensively as mutable parameter types throughout all layers. In application code, raw pointers should only appear in FFI/unsafe contexts. Mutable borrows (`:& T`) are the correct idiom.

**Files affected:** `src/models/wiki_page.ritz`, `src/models/page_link.ritz`, `src/repos/wiki_page_repo.ritz`, `src/repos/page_cache.ritz`, `src/services/wiki_service.ritz`, `src/presenters/page_presenter.ritz`

**`src/models/wiki_page.ritz` lines 60, 67, 74, 79, 84, 93:**
```ritz
# WRONG:
pub fn wiki_page_update_content(page: *WikiPage, new_content:= String)
pub fn wiki_page_is_root(page: *WikiPage) -> bool

# CORRECT:
pub fn wiki_page_update_content(page:& WikiPage, new_content:= String)
pub fn wiki_page_is_root(page: WikiPage) -> bool
```

**`src/repos/wiki_page_repo.ritz` lines 47, 66, 75, 80, 99, 110, 128, 148, 162:**
```ritz
# WRONG:
pub fn wiki_page_repo_connect(repo: *WikiPageRepository, host: *u8, port: i32) -> Result<(), RepoError>
pub fn wiki_page_repo_insert(repo: *WikiPageRepository, page: *WikiPage) -> Result<DocumentId, RepoError>

# CORRECT:
pub fn wiki_page_repo_connect(repo:& WikiPageRepository, host: StrView, port: i32) -> Result<(), RepoError>
pub fn wiki_page_repo_insert(repo:& WikiPageRepository, page:& WikiPage) -> Result<DocumentId, RepoError>
```

Note: `*u8` as a host parameter (line 47) is also wrong; it should be `StrView` or `@u8` in application code.

---

## Major Issues

### 3. Pervasive `s"..."` String Prefix Usage

The `s"..."` prefix is deprecated. Plain `"hello"` is `StrView` by default. The `s"..."` prefix appears ~60 times across almost every file.

**Files affected:** All source and test files.

**Representative examples (`src/models/wiki_page.ritz` line 80, `src/repos/wiki_page_repo.ritz` line 53, `src/services/wiki_service.ritz` line 191):**
```ritz
# WRONG:
page.slug.as_view().split(s"/")
return Err(RepoError.DatabaseError(str_from_view(s"Failed to create client")))
if not (is_letter(c) or is_digit(c) or c == '-' as u8 or c == '/' as u8)

# CORRECT:
page.slug.as_view().split("/")
return Err(RepoError.DatabaseError(str_from_view("Failed to create client")))
```

### 4. `c"..."` Prefix in Application Code

`c"..."` prefixes appear in application-layer code. This prefix is only acceptable in low-level/FFI contexts. `src/repos/wiki_page_repo.ritz`, `src/repos/page_cache.ritz`, and `src/presenters/page_presenter.ritz` use it for response bodies and cache command strings that are passed to internal APIs, not extern C functions.

**`src/repos/wiki_page_repo.ritz` line 28:**
```ritz
# WRONG (constant defined as raw C string in application code):
const PAGES_COLLECTION: *u8 = c"nexus_pages"

# PREFERRED:
const PAGES_COLLECTION: StrView = "nexus_pages"
```

**`src/presenters/page_presenter.ritz` lines 108, 137, 166, 174, 189, 200:**
```ritz
# WRONG:
response_body(ctx.res, c"Missing slug parameter", 22)
response_body(ctx.res, c"OK", 2)

# CORRECT (if response_body takes StrView):
response_body(ctx.res, "Missing slug parameter")
```

**`src/repos/page_cache.ritz` lines 87, 125:**
```ritz
# WRONG:
client_send_cmd1(@cache.client, c"GET", @key_buf as *u8)
client_send_cmd1(@cache.client, c"DEL", @key_buf as *u8)
```
These command strings should use `"GET".as_cstr()` if the API requires a C string, or the API should be updated to accept `StrView`.

**`test/test_simple.ritz` line 27:**
```ritz
# WRONG - c"..." used in a test, not FFI:
let msg = c"hello"

# CORRECT:
let msg = "hello"
# or if testing null-check specifically:
let msg = "hello".as_cstr()
```

### 5. `wiki_page_new_child` Uses Raw Pointer Parameter in Model Code

**`src/models/wiki_page.ritz` line 43-44:**
```ritz
# WRONG:
pub fn wiki_page_new_child(slug:= String, title:= String, content:= String,
                           parent: *WikiPage) -> WikiPage

# CORRECT:
pub fn wiki_page_new_child(slug:= String, title:= String, content:= String,
                           parent: WikiPage) -> WikiPage
```
This is read-only access to `parent.id`, so a const borrow (no sigil) is correct.

### 6. Closure Syntax in `map_err` Uses Rust-Style Lambda

**`src/services/wiki_service.ritz` lines 68, 98, 113, 120, 134, 139, 150, 154:**
```ritz
# WRONG (Rust-style closure):
.map_err(|e| service_error_from_repo(e))?

# Should use Ritz closure syntax (if supported) or be restructured.
```
The `|e|` closure syntax appears to be Rust syntax carried over. This should be verified against the Ritz spec; if closures are not yet specified, using `.map_err` with a named function reference or rewriting as explicit match is preferred.

### 7. `page_link_same_target` Uses C-style Return Value Comparison

**`src/models/page_link.ritz` line 49:**
```ritz
# MINOR ISSUE (non-idiomatic, though works):
pub fn page_link_same_target(a: *PageLink, b: *PageLink) -> bool
    doc_id_eq(@a.target_id, @b.target_id) == 1
```
If `doc_id_eq` is supposed to return `bool`, comparing to `== 1` is non-idiomatic. If it returns `i32` (C-style), the FFI binding itself may need a wrapper. This should be audited.

### 8. `wiki_page_repo_disconnect` Missing `defer` for Early Cleanup

**`src/repos/wiki_page_repo.ritz` lines 65-72:** The disconnect function manually nulls `repo.client` after calling `client_free`. While this is a cleanup function itself (not a resource-acquiring function), the pattern for multi-step manual cleanup throughout the repo layer should use `defer` where applicable.

### 9. Struct Fields Use Raw Pointer Types for Owned Connections

**`src/repos/wiki_page_repo.ritz` line 34:**
```ritz
pub struct WikiPageRepository
    client: *Client           # Mausoleum client connection
```

**`src/presenters/page_presenter.ritz` line 47-48:**
```ritz
pub struct WikiService
    repo: *WikiPageRepository
    cache: *PageCache
```
Storing raw pointers to owned data in structs is unsafe. The ownership model should be expressed: if these are owned (moved in), use `:=` fields or owned values. If borrowed, the lifetime must be clear. This is a systemic design issue.

### 10. `handle_index` Uses `s"..."` for Multi-line HTML String Literal

**`src/presenters/page_presenter.ritz` line 59:**
```ritz
let html = s"<!DOCTYPE html>..."
```
Should be plain `"..."`. Additionally the `html.ptr() as *u8` cast and manual length passing (`html.len() as i32`) suggests `response_body_html` should accept `StrView` directly, avoiding the cast.

### 11. Enum Variant Matching Uses Qualified Names Inconsistently

Some match arms use `LinkKind.Reference` (qualified) while the spec uses bare variant names for patterns. Check consistency against language spec.

**`src/models/page_link.ritz` lines 54-56:**
```ritz
match link.kind
    LinkKind.Reference => true
    _ => false
```
Per the spec's error handling section, bare variant names (`Reference => true`) are preferred in match patterns. This is minor but should be consistent.

---

## Minor Issues

### 12. `wiki_page_slug_parts` Return Type Uses Unimported `Span<u8>`

**`src/models/wiki_page.ritz` line 79:**
`Vec<Span<u8>>` - `Span` does not appear in the imports. The import section brings in `Vec` from `ritzlib.vec`, but `Span` is used without an explicit import. This may be a built-in, but it should be verified and documented.

### 13. Missing Module Documentation in Several Files

Per code organization guidelines, files should begin with a module documentation comment. `src/models/mod.ritz`, `src/repos/mod.ritz`, `src/services/mod.ritz`, and `src/presenters/mod.ritz` have single-line header comments, which is acceptable, but `src/errors/mod.ritz` is the best example; all mod files should follow that style.

### 14. Import at Bottom of File

**`src/presenters/page_presenter.ritz` line 353:**
```ritz
# Import WikiPage for render functions
import models { WikiPage }
```
An import appears at the bottom of the file, after all function definitions. All imports must be at the top of the file per code organization guidelines.

### 15. `wiki_page_repo_connect` `host` Parameter Is Raw `*u8`

**`src/repos/wiki_page_repo.ritz` line 47:**
```ritz
pub fn wiki_page_repo_connect(repo: *WikiPageRepository, host: *u8, port: i32) -> Result<(), RepoError>
```
The `host` parameter should be `StrView`, not a raw C string pointer, since this is application-layer code.

### 16. Constants `PAGES_COLLECTION_LEN` Is Fragile

**`src/repos/wiki_page_repo.ritz` lines 28-29:**
```ritz
const PAGES_COLLECTION: *u8 = c"nexus_pages"
const PAGES_COLLECTION_LEN: i32 = 11
```
Manually tracking string length as a separate constant is error-prone. This should either use a `StrView` constant or the string length should be computed at compile time.

### 17. `build_cache_key` Bound Check Uses `255` but Buffer Is `[256]u8`

**`src/repos/page_cache.ritz` line 159:**
```ritz
while i < slug.len() and pos < 255
```
The null terminator is written at `pos` after the loop, so the maximum usable data length is 254 bytes (prefix + slug), leaving 1 byte for the null. This is correct but deserves a comment explaining the off-by-one relationship.

### 18. `g_wiki_service` Global Uses `i64` as Pointer Storage

**`src/presenters/page_presenter.ritz` lines 36, 40, 45:**
```ritz
var g_wiki_service: i64 = 0
pub fn page_presenter_init(svc: *WikiService)
    g_wiki_service = svc as i64
fn get_service() -> *WikiService
    g_wiki_service as *WikiService
```
Using `i64` to store a pointer is a portability concern. A typed `Option<*WikiService>` or a direct `*WikiService` global (initialized to null) would be more idiomatic and safer.

---

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | ISSUE | `*T` used pervasively for mutable params; should be `:& T` in application code |
| Reference Types (@) | OK | `@x` and `@&x` used correctly for address-of and mutable references |
| Attributes ([[...]]) | ISSUE | `@test` used in 3 of 4 test files; only `test_simple.ritz` uses `[[test]]` |
| Logical Operators | OK | `and`, `or`, `not` used correctly throughout; no `&&`/`\|\|`/`!` found |
| String Types | ISSUE | `s"..."` prefix used ~60 times; `c"..."` used in application (non-FFI) code |
| Error Handling | OK | `?` operator used, `Result<T,E>` types throughout; minor lambda syntax question |
| Naming Conventions | OK | snake_case functions, PascalCase types, SCREAMING_SNAKE constants all consistent |
| Code Organization | ISSUE | Import at bottom of `page_presenter.ritz`; some minor grouping issues |

---

## Files Needing Attention

| File | Severity | Issues |
|------|----------|--------|
| `test/test_models.ritz` | CRITICAL | All 6 tests use `@test` instead of `[[test]]` |
| `test/test_services.ritz` | CRITICAL | All 13 tests use `@test` instead of `[[test]]` |
| `test/test_errors.ritz` | CRITICAL | All 13 tests use `@test` instead of `[[test]]` |
| `src/models/wiki_page.ritz` | CRITICAL/MAJOR | Raw `*WikiPage` params; `s"..."` prefix; raw pointer in `wiki_page_new_child` |
| `src/models/page_link.ritz` | CRITICAL/MAJOR | Raw `*PageLink` params; `s"..."` prefix |
| `src/repos/wiki_page_repo.ritz` | CRITICAL/MAJOR | Raw `*T` params; `c"..."` constants; `s"..."` prefix; `*u8` host param |
| `src/repos/page_cache.ritz` | MAJOR | `c"..."` for command strings; `s"..."` prefix |
| `src/services/wiki_service.ritz` | MAJOR | Raw `*T` params; `s"..."` prefix; Rust-style `|e|` closures |
| `src/presenters/page_presenter.ritz` | MAJOR | Raw `*T` params; `c"..."` response bodies; `s"..."` prefix; import at bottom |
| `test/test_simple.ritz` | MINOR | `c"hello"` in non-FFI test |

---

## Recommendations

**Priority 1 (Critical - fix immediately):**
1. Replace all `@test` annotations with `[[test]]` in `test/test_models.ritz`, `test/test_services.ritz`, and `test/test_errors.ritz`.
2. Replace raw pointer mutable parameters (`*WikiPage`, `*WikiPageRepository`, `*PageCache`, `*WikiService`, `*PageLink`, `*Response`) with `:& T` mutable borrows or plain `T` const borrows throughout all source files.

**Priority 2 (Major - fix before next merge):**
3. Replace all `s"..."` string prefixes with plain `"..."` throughout the entire codebase (~60 occurrences).
4. Replace `c"..."` usage in application-layer code (`page_presenter.ritz`, `page_cache.ritz`, `wiki_page_repo.ritz`) with `StrView` literals or `.as_cstr()` only at FFI call sites.
5. Audit and fix the `|e|` closure syntax in `wiki_service.ritz` map_err calls.
6. Move the stray `import models { WikiPage }` at the bottom of `page_presenter.ritz` to the top imports section.

**Priority 3 (Minor - clean up):**
7. Replace `PAGES_COLLECTION: *u8 = c"..."` with a `StrView` constant and remove the separate `PAGES_COLLECTION_LEN` constant.
8. Replace `g_wiki_service: i64` with a typed pointer global.
9. Document the `Span<u8>` type's import source in `wiki_page.ritz`.
10. Audit `doc_id_eq` return type and remove `== 1` comparison if it returns `bool`.
