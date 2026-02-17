# LARB Review: Tempest

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

Tempest is a browser project implementing a multi-process architecture with a browser process and isolated tab processes. The codebase is largely well-structured and follows modern Ritz idioms, but contains a handful of issues: one instance of old `c"..."` FFI string prefix in application-level code, one use of `@&` (mutable address-of) applied directly to a vec push argument in document.ritz that is inconsistent with usage elsewhere, and a struct field declared with a reference type (`channel:& IpcChannel`) inside a struct definition rather than in a function parameter. Overall compliance is good with no critical breaking issues, but several patterns need correction.

## Statistics

- **Files Reviewed:** 15
- **Total SLOC:** ~950
- **Issues Found:** 6 (Critical: 0, Major: 4, Minor: 2)

## Critical Issues

None. All syntax appears compatible with the current compiler, and no unsafe memory hazards were found in application-level code.

## Major Issues

### 1. Reference type stored in struct field (Major) — `lib/tab_renderer.ritz:24`

```ritz
pub struct TabRenderer
    channel:& IpcChannel   # <-- reference type in struct field
```

Storing a borrow (`:& IpcChannel`) as a struct field is a structural ownership problem. A struct should own its data or hold a raw pointer in FFI contexts. This should either be owned (`channel: IpcChannel`) or restructured so the channel reference is threaded through each method call rather than stored. This pattern will cause lifetime issues.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/tempest/lib/tab_renderer.ritz`, line 24

---

### 2. Old `c"..."` string prefix in application code (Major) — `lib/tab.ritz:62`

```ritz
# sys_execve(c"tempest-tab", args, env)
```

Although this line is commented out, `c"..."` prefix syntax is explicitly deprecated per the spec (should be `"tempest-tab".as_cstr()`). Commented-out code that will be uncommented later should use the correct idiom now to avoid introducing old syntax at activation time.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/tempest/lib/tab.ritz`, line 62

---

### 3. Inconsistent `@&` usage in `document_new` (Major) — `lib/document.ritz:133`

```ritz
vec_push<Node>(@&doc.nodes, root)
```

All other call sites in the codebase use `@` (immutable address-of) for mutable vec operations (e.g., `@doc.nodes`, `@browser.tabs`, etc.). The `@&` form is used here and in `document_create_element` (line 166), but not uniformly. If `vec_push` requires a mutable reference, all call sites should use `@&`; if `@` suffices (because the borrow modifier is on the parameter), then `@&` is unnecessary. Pick one and apply it consistently.

**Files:** `/home/aaron/dev/ritz-lang/rz/projects/tempest/lib/document.ritz`, lines 133, 166

---

### 4. `@*history` dereference-then-address pattern (Major) — `lib/history.ritz:73,82`

```ritz
if tab_history_can_go_back(@*history) == 0
    ...
if tab_history_can_go_forward(@*history) == 0
```

`history` is already a `TabHistory` reference parameter (`history:& TabHistory`). Passing `@*history` (dereference then take address) is roundabout and should simply be `@history` or just `history` if the callee takes a const borrow. This pattern obscures intent and is non-idiomatic.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/tempest/lib/history.ritz`, lines 73, 82

---

## Minor Issues

### 5. `string_from_strview` called with `@url` and `@title` in `history_visit` (Minor) — `lib/history.ritz:119-120`

```ritz
entry.url = string_from_strview(@url)
entry.title = string_from_strview(@title)
```

The function signature is `history_visit(history:& History, url: StrView, title: StrView)`. `url` and `title` are already `StrView` values (passed by copy/const borrow). Taking `@url` gives a reference to a local `StrView`, which is unnecessary — call `string_from_strview(url)` directly as every other call site in the project does.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/tempest/lib/history.ritz`, lines 119, 120

---

### 6. `network_manager_new` takes `Config` by value but only inspects it (Minor) — `lib/network.ritz:93`

```ritz
pub fn network_manager_new(config: Config) -> NetworkManager
```

`config` is passed by value (move or copy) but the function body does not use any fields from `config` — the struct is constructed from scratch. The parameter is either unused dead code or will eventually be used. If it will be used, it should take `config: Config` as a const borrow (no sigil change needed since that is the default). If it will never be used, remove the parameter. Low severity since `Config` is likely cheap to copy, but worth noting.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/tempest/lib/network.ritz`, line 93

---

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | OK | Consistent use of `:&` for mutation, no Rust-style `&T` / `&mut T` parameters |
| Reference Types (@) | ISSUE | `@&` used inconsistently in `document.ritz`; `@*history` pattern in `history.ritz` |
| Attributes ([[...]]) | OK | `[[test]]` used correctly throughout `tests/test_document.ritz`; no old `@test` found |
| Logical Operators | OK | No `&&`, `\|\|`, or `!` operators found; no logical operators used in this codebase |
| String Types | ISSUE | Deprecated `c"..."` prefix present (commented) in `tab.ritz` line 62 |
| Error Handling | OK | No nested match chains that need `?`; stubs return `None`/`0` appropriately |
| Naming Conventions | OK | `snake_case` functions, `PascalCase` types, `SCREAMING_SNAKE_CASE` constants throughout |
| Code Organization | OK | Files have header comments, imports grouped, type definitions before functions |

## Files Needing Attention

| File | Issue |
|------|-------|
| `/home/aaron/dev/ritz-lang/rz/projects/tempest/lib/tab_renderer.ritz` | Reference stored as struct field (`channel:& IpcChannel`) |
| `/home/aaron/dev/ritz-lang/rz/projects/tempest/lib/document.ritz` | Inconsistent `@&` vs `@` for vec_push calls |
| `/home/aaron/dev/ritz-lang/rz/projects/tempest/lib/history.ritz` | `@*history` dereference pattern; unnecessary `@url`/`@title` in `history_visit` |
| `/home/aaron/dev/ritz-lang/rz/projects/tempest/lib/tab.ritz` | Deprecated `c"..."` in commented-out code |

## Recommendations

1. **(Major, fix before landing)** Resolve the `channel:& IpcChannel` struct field in `TabRenderer` — either store it as an owned value or restructure the API to pass the channel reference through each method that needs it.

2. **(Major)** Standardize `vec_push` call style in `document.ritz` — audit all `vec_push` / `vec_get` call sites project-wide and pick either `@` or `@&` based on what the function signature requires.

3. **(Major)** Replace `@*history` with the direct idiomatic form in `history.ritz`; these are `history:& TabHistory` parameters so the callee already has a reference.

4. **(Major)** Update the commented-out `sys_execve` call in `tab.ritz` to use `"tempest-tab".as_cstr()` before it gets uncommented.

5. **(Minor)** Remove the spurious `@url`/`@title` address-of operators in `history_visit`.

6. **(Minor)** Decide whether `network_manager_new`'s `config` parameter is intentional scaffolding or dead code and act accordingly.
