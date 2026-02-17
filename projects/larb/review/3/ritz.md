# LARB Review: Ritz Compiler (ritz project)

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

The ritz project (compiler + ritzlib standard library) shows strong adoption of v0.2.0 syntax in the core standard library: ownership modifiers (`@`, `:&`, `:=`) are used correctly throughout ritzlib, logical operators use keywords (`and`, `or`, `not`), and `[[test]]` attributes are used correctly in all active test files. However, there is a pervasive and systematic issue: the old `c"..."` C-string prefix syntax is used in 168 locations across ritzlib (including the gold-standard library modules) instead of the specified `"..."` StrView literals. Additionally, `testing.ritz` uses the deprecated `*i8` type for string parameters instead of `StrView`, and the examples (including the self-described "GOLD STANDARD" `75_async_reference`) use `&variable` Rust-style address-of instead of `@variable` in several places.

## Statistics

- **Files Reviewed:** 348 (non-archive .ritz files)
- **Total SLOC:** ~72,900
- **Issues Found:** 52+ (Critical: 0, Major: 47+, Minor: 5+)

---

## Critical Issues

None identified in active (non-archive) code. The `@test` syntax violations are all in `docs/archive/` which is explicitly historical. No dangerous memory safety or security issues found.

---

## Major Issues

### MAJOR-1: Pervasive `c"..."` prefix in ritzlib (168 occurrences across 16 files)

The old `c"..."` C-string prefix syntax is used throughout ritzlib instead of the modern `"..."` (StrView) literals. Per the spec, `c"..."` should only appear in FFI/low-level contexts; string literals default to `StrView`.

**Files affected (by occurrence count):**
- `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/tests/test_strview.ritz` - 60 occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/meta.ritz` - 37 occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/span.ritz` - 13 occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/json.ritz` - 18 occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/process.ritz` - 9 occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/args.ritz` - 7 occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/tests/test_buf.ritz` - 6 occurrences
- `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/tests/test_string_methods.ritz` - 5 occurrences
- And more...

**Examples from `ritzlib/json.ritz`:**
```ritz
# WRONG - current code:
if jp_match_str(p, c"true") != 0
if jp_match_str(p, c"false") != 0
result.error = c"JSON parse error"
return c"unexpected character"
vec_push_str(buf, c"null")
vec_push_str(buf, c", ")

# CORRECT:
if jp_match_str(p, "true") != 0
if jp_match_str(p, "false") != 0
result.error = "JSON parse error"
return "unexpected character"
```

**Examples from `ritzlib/string.ritz`:**
```ritz
# WRONG:
string_push_str(@s, c"0x0")
string_push_str(@s, c"0x")

# CORRECT:
string_push_str(@s, "0x0")
string_push_str(@s, "0x")
```

**Examples from `ritzlib/span.ritz`:**
```ritz
# WRONG:
return span_literal(c"HTTP/1.1 200 OK\r\n", 17)
return span_literal(c"Content-Length: ", 16)
return span_literal(c"\r\n", 2)

# CORRECT:
return span_literal("HTTP/1.1 200 OK\r\n", 17)
return span_literal("Content-Length: ", 16)
return span_literal("\r\n", 2)
```

**Context:** The `c"..."` usage in these modules is NOT for FFI purposes (they are not being passed to C functions). These are plain string comparisons and string pushes within pure Ritz logic. The `meta.ritz` module uses `c"..."` to pass strings to `json_get_field()` which is a pure Ritz function. This is the most prevalent violation in the codebase and is especially problematic because ritzlib is the gold standard.

**Note on `testing.ritz`:** The inline assembly test call area in `testing.ritz` does use `c"..."` in a comment-embedded example (`@test` usage in comment at line 23 - this is purely documentation, not active code).

---

### MAJOR-2: `*i8` type used in `testing.ritz` instead of `StrView` or `*u8`

`ritzlib/testing.ritz` uses `*i8` for string parameters in the `TestEntry` struct and assertion helpers. This is not a defined Ritz string type and should use `StrView` (for modern idiom) or at minimum `*u8`.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/testing.ritz`

```ritz
# WRONG - current code:
struct TestEntry
    name: *i8           # Should be *u8 or StrView
    func: *u8

fn register_test(name: *i8, func: *u8)   # Should be name: *u8 or StrView
fn assert_msg(condition: i32, msg: *i8)   # Should be StrView
fn assert_eq_i64(actual: i64, expected: i64, msg: *i8)  # Should be StrView
fn assert_eq_i32(actual: i32, expected: i32, msg: *i8)  # Should be StrView
fn assert_not_null(ptr: *u8, msg: *i8)    # Should be StrView
fn assert_null(ptr: *u8, msg: *i8)        # Should be StrView

# CORRECT:
struct TestEntry
    name: StrView
    func: *u8

fn register_test(name: StrView, func: *u8)
fn assert_msg(condition: i32, msg: StrView)
```

Additionally at line 80, `prints(entry.name)` is called where `name: *i8`, but `prints()` takes `StrView`. This is a type inconsistency in the gold-standard testing framework.

---

### MAJOR-3: `c"..."` usage in ritz1 compiler source (non-FFI contexts)

The ritz1 compiler source (`ritz1/src/emitter.ritz`) uses `c"..."` extensively for LLVM IR string fragments that are emitted. While this is technically the compiler internals (which have some latitude), the emitter is using `c"..."` to pass string data to `emit_str()` which is a Ritz-level function, not an FFI function.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritz1/src/emitter.ritz` (and other ritz1/src/ files)

```ritz
# Examples from ritz1/src/emitter.ritz:
emit_str(s, c") {\n")
emit_str(s, c"}\n\n")
emit_str(s, c" = type {")
emit_str(s, c"}\n")
emit_str(s, c"%Vec$u8 = type { ptr, i64, i64 }\n")
```

Per the instructions, the compiler has "some latitude for legacy patterns" but should modernize over time. Given the density of usage in the emitter, this is flagged as major.

---

### MAJOR-4: `&variable` Rust-style address-of in examples (including "GOLD STANDARD")

The example `75_async_reference` (self-described as the gold standard for async Ritz code) uses `&future` (Rust-style address-of) instead of the spec-required `@future`.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/ritz/examples/tier5_async/75_async_reference/src/main.ritz`

```ritz
# WRONG - from the "GOLD STANDARD" example:
let result: i32 = add_values_poll(&future)

# CORRECT:
let result: i32 = add_values_poll(@future)
```

Additional examples using `&array[0]` pattern in tier3/tier4 examples:

**File:** `/home/aaron/dev/ritz-lang/rz/projects/ritz/examples/37_xargs/src/main.ritz`
```ritz
# WRONG:
args[0] = &cmd_path[0]
arg = read_arg_null(&input_buf[0], total_read, &pos)
let result: i32 = run_command(&cmd_path[0], &args[0], envp)

# CORRECT:
args[0] = @cmd_path[0]
arg = read_arg_null(@input_buf[0], total_read, @pos)
let result: i32 = run_command(@cmd_path[0], @args[0], envp)
```

This pattern of `&variable` appears across many example files in the tier3/tier4 applications.

---

### MAJOR-5: `string_from(c"...")` - mixing `c"..."` with StrView-accepting function

In `ritzlib/tests/test_string_methods.ritz`, `string_from()` is called with `c"..."` arguments. `string_from()` accepts `StrView`, so the `c"..."` is being implicitly coerced. This should use plain `"..."` literals to match the StrView-based API contract.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/tests/test_string_methods.ritz`

```ritz
# WRONG:
var expected: String = string_from(c"hello")
var expected: String = string_from(c"hel")

# CORRECT:
var expected: String = string_from("hello")
var expected: String = string_from("hel")
```

---

### MAJOR-6: `@test` usage in `testing.ritz` comment example

The `testing.ritz` module documentation shows `@test` as the usage example at line 23, which contradicts the modern `[[test]]` syntax. While this is a comment, it is the primary documentation that users see when writing tests.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/testing.ritz`

```ritz
# WRONG - documentation example at line 23:
# @test
# fn test_addition() -> i32
#     assert 1 + 1 == 2
#     0

# CORRECT documentation should show:
# [[test]]
# fn test_addition() -> i32
#     assert 1 + 1 == 2
#     0
```

---

### MAJOR-7: Commented-out `impl` blocks in `string.ritz` and `gvec.ritz`

Both `string.ritz` and `gvec.ritz` have large sections of commented-out `impl` blocks with comments like "NOTE: ritz1 doesn't support impl blocks yet". This represents technical debt that needs to be resolved. The `StrView` impl block in `strview.ritz` is active and working (good), but `String` and `Vec<T>` lack active impl blocks.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/string.ritz` (lines 39-133)
**File:** `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/gvec.ritz` (lines 40-110)

This is a compiler limitation note, but it means the standard library's method syntax support is inconsistent (StrView has impl, String does not).

---

## Minor Issues

### MINOR-1: Naming - `g_alloc`, `g_tests` global variables using underscore prefix convention

`memory.ritz` uses `g_alloc` and `testing.ritz` uses `g_tests` for global state. The `g_` prefix for globals is reasonable but not standardized in the naming conventions doc. Consistent module-level approach is worth standardizing.

### MINOR-2: `strview_from_cstr(c"...")` in `test_strview.ritz` is redundant double-conversion

`test_strview.ritz` repeatedly calls `strview_from_cstr(c"hello")`. This is semantically: create a C string literal, then convert it to StrView. The correct idiom is to use a StrView literal directly: `let s: StrView = "hello"`.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/tests/test_strview.ritz` (60 occurrences)

### MINOR-3: Missing module header documentation in several ritzlib files

Some ritzlib files lack proper header documentation. `result.ritz` lacks a module description comment. `option.ritz`, `eq.ritz`, `hash.ritz` may similarly be sparse.

### MINOR-4: `tests/test_elf.ritz` uses `**i8` for argv

**File:** `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/tests/test_elf.ritz`

```ritz
# WRONG:
fn main(argc: i32, argv: **i8) -> i32
    let filename: *i8 = *(argv + 1)

# CORRECT:
fn main(argc: i32, argv: **u8) -> i32
    let filename: *u8 = *(argv + 1)
```

### MINOR-5: `ritz0/test/test_level29.ritz` has commented `@test` attributes

Three instances of `# @test` (commented out) appear in `test_level29.ritz`. These should either be uncommented as `[[test]]` or removed.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritz0/test/test_level29.ritz` (lines 53, 61, 70, 77)

---

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | OK | `@`, `:&`, `:=` used correctly throughout ritzlib and compiler sources |
| Reference Types (@) | ISSUE | `&variable` used in examples including "gold standard" 75_async_reference |
| Attributes ([[...]]) | OK | All active test files use `[[test]]`; `@test` only in archive/comments |
| Logical Operators | OK | No `&&`/`\|\|` as operators; ritzlib uses `and`/`or`/`not` |
| String Types | ISSUE | 168 uses of `c"..."` in ritzlib; should use `"..."` (StrView) in non-FFI code |
| Error Handling | OK | Result/Option types used correctly; `?` operator in appropriate places |
| Naming Conventions | OK | snake_case functions, PascalCase types, SCREAMING_SNAKE_CASE constants throughout |
| Code Organization | OK | Module structure is clean; imports grouped; sections documented |

---

## Files Needing Attention

### High Priority (ritzlib - gold standard violations):
1. `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/tests/test_strview.ritz` - 60 `c"..."` uses
2. `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/meta.ritz` - 37 `c"..."` uses
3. `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/json.ritz` - 18 `c"..."` uses
4. `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/span.ritz` - 13 `c"..."` uses
5. `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/testing.ritz` - `*i8` type, `@test` in docs
6. `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/process.ritz` - 9 `c"..."` uses
7. `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/args.ritz` - 7 `c"..."` uses
8. `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/string.ritz` - 2 `c"..."` uses, commented-out impl block
9. `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritzlib/gvec.ritz` - commented-out impl block

### Medium Priority (examples):
10. `/home/aaron/dev/ritz-lang/rz/projects/ritz/examples/tier5_async/75_async_reference/src/main.ritz` - `&variable` usage in gold standard
11. `/home/aaron/dev/ritz-lang/rz/projects/ritz/examples/37_xargs/src/main.ritz` - `&array[0]` patterns
12. Multiple tier3/tier4 examples - `&variable` address-of usage

### Lower Priority (compiler internals):
13. `/home/aaron/dev/ritz-lang/rz/projects/ritz/ritz1/src/emitter.ritz` - `c"..."` usage in emit_str calls

---

## Recommendations

### Priority 1 - Fix ritzlib string literal syntax (MAJOR-1)
Replace all `c"..."` in ritzlib with `"..."` in non-FFI contexts. This is the most impactful change since ritzlib is the gold standard. The primary affected functions are:
- `strview_from_cstr(c"...")` → `strview_from_cstr("...")` or just create StrView directly
- `json_get_field(item, c"name")` → `json_get_field(item, "name")`
- `jp_match_str(p, c"true")` → `jp_match_str(p, "true")`
- `span_literal(c"HTTP/1.1 ...", n)` → `span_literal("HTTP/1.1 ...", n)`

### Priority 2 - Fix `testing.ritz` string types (MAJOR-2)
Update `testing.ritz` to use `StrView` for all string parameters and update the documentation comment from `@test` to `[[test]]`.

### Priority 3 - Fix gold-standard example address-of (MAJOR-4)
Update `75_async_reference` and other example files to use `@variable` instead of `&variable` for address-of operations. The "gold standard" example is especially visible to developers learning the language.

### Priority 4 - Resolve commented-out impl blocks (MAJOR-7)
Either implement `impl String` and `impl Vec<T>` in ritz1, or document explicitly that method syntax for these types is pending compiler support. The current state creates confusion about the idiomatic API.

### Priority 5 - Update ritz1 compiler source `c"..."` usage (MAJOR-3)
Once ritzlib is updated, update the compiler source files to use `"..."` consistently.

---

*LARB Review by Claude (LARB Agent) - February 2026*
