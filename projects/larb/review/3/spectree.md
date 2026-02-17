# LARB Review: spectree

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

spectree is an in-memory specification tree library providing MCP (Model Context Protocol) server functionality for managing hierarchical nodes, links, agent ownership, and conversation history. The library core (`lib/`) shows good use of the `@` and `:&` ownership idioms overall, but has systematic violations in the `c"..."` string prefix (should be `.as_cstr()`), `&&`/`||` logical operators (should be `and`/`or`), and old Rust-style `&x` address-of in both `lib/uuid.ritz` and throughout all five test files.

## Statistics

- **Files Reviewed:** 10 (5 lib, 5 test)
- **Total SLOC:** ~900
- **Issues Found:** 28 (Critical: 0, Major: 22, Minor: 6)

## Critical Issues

None. No code uses old Rust-style `&T` or `&mut T` in function parameter type position. No dangerous memory safety patterns identified beyond the normal raw pointer null-check pattern used consistently throughout.

## Major Issues

### 1. Old `c"..."` String Prefix (MAJOR) - `lib/types.ritz`

The `c"..."` prefix is used in every name-returning function across `lib/types.ritz`. Per spec, application-layer code should use `"...".as_cstr()` instead.

**Files:** `lib/types.ritz` (lines 24, 26, 28, 30, 44, 46, 48, 50, 52, 54, 66, 68, 70, 72, 177, 179, 181, 183)

```ritz
# WRONG - current code:
return span_from_cstr(c"Org")
return span_from_cstr(c"Draft")

# CORRECT:
return span_from_cstr("Org".as_cstr())
return span_from_cstr("Draft".as_cstr())
```

18 occurrences in `types.ritz` alone. This is a systematic pattern across every string-returning function in the file.

---

### 2. `&&` Logical Operator (MAJOR) - `lib/types.ritz`, `lib/uuid.ritz`, `lib/store.ritz`

Symbol `&&` is used instead of keyword `and`. Appears in three lib files.

**`lib/types.ritz` line 89:**
```ritz
# WRONG:
if a.high == b.high && a.low == b.low

# CORRECT:
if a.high == b.high and a.low == b.low
```

**`lib/uuid.ritz` lines 127, 129, 131:**
```ritz
# WRONG:
if c >= '0' && c <= '9'
if c >= 'a' && c <= 'f'
if c >= 'A' && c <= 'F'

# CORRECT:
if c >= '0' and c <= '9'
if c >= 'a' and c <= 'f'
if c >= 'A' and c <= 'F'
```

4 occurrences total in lib files.

---

### 3. `||` Logical Operator (MAJOR) - `lib/store.ritz`

Symbol `||` is used instead of keyword `or`.

**`lib/store.ritz` lines 320 and 353:**
```ritz
# WRONG:
if idx < 0 || idx >= links_len(@entry.links)
if idx < 0 || idx >= agents_len(@entry.agents)

# CORRECT:
if idx < 0 or idx >= links_len(@entry.links)
if idx < 0 or idx >= agents_len(@entry.agents)
```

2 occurrences.

---

### 4. Old Rust-Style `&x` Address-Of in Tests (MAJOR) - All 5 test files

The test files use `&var` for address-of instead of the finalized `@var` syntax. This is a pervasive pattern across all test files.

**`test/test_types.ritz`** - 9 occurrences:
```ritz
# WRONG (lines 36-39, 63-67, 87-89, 113, 126, 134, 169, 173):
assert span_get<u8>(&org, 0) == 'O'
assert uuid_eq(&a, &b) == 1
assert node_is_root(&n) == 1

# CORRECT:
assert span_get<u8>(@org, 0) == 'O'
assert uuid_eq(@a, @b) == 1
assert node_is_root(@n) == 1
```

**`test/test_uuid.ritz`** - 14 occurrences:
```ritz
# WRONG (lines 26, 35, 73-74, 85-86, 99, 116-117, 122-128, 133-134, 144-145, 151-152, 170, 175-176):
assert uuid_eq(&u, &z) == 0
let len: i32 = uuid_format(&u, &buf[0])
uuid_parse(&s, &u)
uuid_parse(&original, &parsed)
uuid_format(&parsed, &formatted[0])
if formatted[i] != span_get<u8>(&original, i)
assert uuid_eq(&u, &z) == 1

# CORRECT:
assert uuid_eq(@u, @z) == 0
let len: i32 = uuid_format(@u, @buf[0])
uuid_parse(@s, @u)
```

Note: `uuid_format` takes `out: *u8` (raw pointer) as its second argument - passing `&buf[0]` here is arguably intentional for the raw pointer, but `&u` for the `Uuid` argument is wrong and should be `@u`.

**`test/test_store.ritz`** - 0 occurrences (this file correctly uses `@` throughout - well done).

**`test/test_mcp.ritz`** - 0 occurrences (correctly uses `@` throughout - well done).

**`test/test_conversation.ritz`** - 0 occurrences (correctly uses `@` throughout - well done).

The `&&` violations also appear in the test files:

**`test/test_uuid.ritz`** - indirectly via `span_get<u8>(&original, i)` within a loop condition, but this is an `&` address-of issue, not `&&`.

Total `&x` address-of violations in tests: approximately 23 across `test_types.ritz` and `test_uuid.ritz`.

---

### 5. Raw Pointer `&buf[0]` in `lib/uuid.ritz` (MAJOR)

`lib/uuid.ritz` line 22 passes `&buf[0]` as a syscall argument, which is the Rust-style address-of. Because this is going directly into a raw syscall (FFI), a raw pointer is appropriate - but the syntax should be `@buf[0] as *u8` to take the address using the `@` operator and then cast to raw pointer. Using `&buf[0]` is old syntax.

```ritz
# WRONG (line 22):
let n: i64 = syscall3(SYS_GETRANDOM, &buf[0] as i64, 16, 0)

# CORRECT:
let n: i64 = syscall3(SYS_GETRANDOM, @buf[0] as i64, 16, 0)
```

---

### 6. `uuid_parse` Mutable Parameter Modifier (MAJOR) - `lib/uuid.ritz`

`uuid_parse` at line 135 uses `out:& Uuid` which is correct `:&` mutable borrow syntax. However, the call sites in `test/test_uuid.ritz` pass `&u` (old syntax) instead of `@&u`. Since the function signature is correct, this is purely a call-site issue covered under item 4.

---

### 7. Missing `impl` Blocks - Methods as Free Functions (MAJOR)

All methods on types (`node_new`, `node_is_root`, `uuid_zero`, `uuid_eq`, `message_new`, `conversation_new`) are defined as free functions rather than in `impl` blocks. Per spec, the `impl Type` form is preferred.

**`lib/types.ritz` examples:**
```ritz
# DEPRECATED pattern (current):
pub fn node_new(kind: i32) -> Node
pub fn node_is_root(n: @Node) -> i32
pub fn uuid_zero() -> Uuid

# PREFERRED:
impl Node
    pub fn new(kind: i32) -> Node
    pub fn is_root(self: @Node) -> i32

impl Uuid
    pub fn zero() -> Uuid
```

This affects `lib/types.ritz`, `lib/uuid.ritz`, `lib/store.ritz`, and `lib/conversation.ritz`. This is a MAJOR but non-critical pattern - the deprecated form is tolerated for now per the instructions.

---

## Minor Issues

### 1. `conv_delete` is a Stub (MINOR) - `lib/conversation.ritz`

`conv_delete` (line 188) does not actually remove the conversation - it returns success if the conversation exists but leaves it in the store. The TODO comment acknowledges this. The test `test_conv_delete` passes vacuously as a result. This is a correctness issue but minor for a review of syntax/idioms.

### 2. `mcp_release_ownership` is a Stub (MINOR) - `lib/mcp.ritz`

`mcp_release_ownership` (line 176) always returns `MCP_OK` after finding the node, without actually removing the agent. Acknowledged by TODO comment.

### 3. Inconsistent `let` vs `var` Usage (MINOR)

Some bindings that are never reassigned use `var` (e.g., `var count: i64 = ...` in many places) when `let` would be more idiomatic and express immutability intent. The pattern is inconsistent.

### 4. No Module-Level Documentation Headers in Some Files (MINOR)

`lib/store.ritz` has a brief header but does not follow the recommended code organization section order (module docs, imports, constants, types, etc.) consistently. `lib/conversation.ritz` omits constants section entirely (none needed, but the ordering deviates).

### 5. Magic Number `0` for Null Pointer Comparisons (MINOR)

Throughout `lib/store.ritz` and `lib/mcp.ritz`, null pointer checks use `0 as *Node`, `0 as *NodeEntry`, etc. A named constant `NULL_PTR` or using a `null` keyword (as `lib/conversation.ritz` does via `return null`) would be more consistent. `conversation.ritz` correctly uses `null`; `store.ritz` and `mcp.ritz` use `0 as *Type` casts. Pick one style.

### 6. Test Files Lack `[[test]]` on Some Helper Setup (MINOR)

All test functions are correctly decorated with `[[test]]` - this is well done. No missing or wrong attribute syntax. The `@test` old syntax is not present anywhere.

---

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | OK | `:&` and `@&` used correctly in lib files; test files have `&x` address-of violations |
| Reference Types (@) | ISSUE | `&x` old address-of used in `test_types.ritz` (~9) and `test_uuid.ritz` (~14); `&buf[0]` in `lib/uuid.ritz` syscall |
| Attributes ([[...]]) | OK | `[[test]]` used correctly throughout; no old `@test` found |
| Logical Operators | ISSUE | `&&` in `types.ritz` (1), `uuid.ritz` (3), `store.ritz` (2); `\|\|` in `store.ritz` (2) |
| String Types | ISSUE | `c"..."` prefix used 18 times in `types.ritz`; should be `"...".as_cstr()` |
| Error Handling | OK | Consistent i32 return codes with early returns; no nested match chains |
| Naming Conventions | OK | snake_case functions, PascalCase types, SCREAMING_SNAKE_CASE constants throughout |
| Code Organization | OK | Files have clear section headers; import grouping is consistent |

---

## Files Needing Attention

| File | Issues | Priority |
|------|--------|----------|
| `test/test_uuid.ritz` | ~14 `&x` address-of violations, `c"..."` in span_from_cstr calls | HIGH |
| `test/test_types.ritz` | ~9 `&x` address-of violations | HIGH |
| `lib/types.ritz` | 18 `c"..."` literals, 1 `&&` operator | HIGH |
| `lib/uuid.ritz` | 3 `&&` operators, 1 `&buf[0]` address-of | MEDIUM |
| `lib/store.ritz` | 2 `\|\|` operators | MEDIUM |
| `lib/mcp.ritz` | No syntax violations; stub implementations only | LOW |
| `lib/conversation.ritz` | No syntax violations; stub `conv_delete` | LOW |
| `test/test_store.ritz` | No issues found | - |
| `test/test_mcp.ritz` | No issues found | - |
| `test/test_conversation.ritz` | No issues found | - |

---

## Recommendations

1. **[HIGH]** Fix all `&x` address-of to `@x` in `test/test_types.ritz` and `test/test_uuid.ritz` - approximately 23 violations. These files were clearly written before the `@` syntax was finalized.

2. **[HIGH]** Replace all `c"..."` string literals in `lib/types.ritz` with `"...".as_cstr()` - 18 occurrences across the name-returning functions (`node_kind_name`, `status_name`, `link_kind_name`, `role_name`).

3. **[MEDIUM]** Replace `&&` with `and` in `lib/types.ritz` (line 89), `lib/uuid.ritz` (lines 127, 129, 131), and `||` with `or` in `lib/store.ritz` (lines 320, 353).

4. **[MEDIUM]** Fix `&buf[0]` in `lib/uuid.ritz` line 22 to `@buf[0]`.

5. **[LOW]** Migrate type-associated functions to `impl` blocks over time, starting with `Uuid` (small, self-contained) as a model.

6. **[LOW]** Standardize null pointer handling: either use `null` keyword consistently (as `conversation.ritz` does) or `0 as *T` (as `store.ritz` and `mcp.ritz` do) - not both.

7. **[LOW]** Implement `conv_delete` and `mcp_release_ownership` properly - the stubs mean tests pass vacuously and callers cannot rely on the contracts.

Note: `test/test_store.ritz`, `test/test_mcp.ritz`, and `test/test_conversation.ritz` are exemplary - they correctly use `@` and `@&` throughout with no syntax violations. These three files should be used as style references when updating `test_types.ritz` and `test_uuid.ritz`.
