# LARB Review: Tome

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

Tome is a Redis-compatible in-memory key-value store implementing the RESP wire protocol with support for strings, lists, sets, sorted sets, and hashes. The codebase is a low-level systems project that makes heavy use of raw pointers throughout, which is architecturally appropriate for its goals, but it has pervasive violations of the finalized Ritz syntax spec — most critically, widespread use of `c"..."` string literals in test and application code, use of `&&`/`||` instead of `and`/`or` in several files, a single instance of old `&buf[0]` address-of syntax in test code, and inconsistent application of ownership modifier idioms. The library code (`lib/`) is generally cleaner and more idiomatically correct than the test and binary files.

## Statistics

- **Files Reviewed:** 16
- **Total SLOC:** ~3,500 (estimated)
- **Issues Found:** 34 (Critical: 1, Major: 23, Minor: 10)

## Critical Issues

### C-1: Old `&T` address-of syntax in test_resp.ritz (line 311)

`test/test_resp.ritz` line 311 uses the old Rust-style address-of operator:

```ritz
let len: i32 = resp_arg_copy(@arg, &buf[0], 32)
```

This should be `@buf[0]`. Every other address-of site in the project correctly uses `@`, making this a lone regression. It is a critical syntax error that will not compile with the new parser.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/tome/test/test_resp.ritz`, line 311

---

## Major Issues

### M-1: Pervasive `c"..."` prefix in test files (MAJOR — string type violation)

All test files (`test_resp.ritz`, `test_store.ritz`, `test_commands.ritz`, `run_tests.ritz`, `test_server_auth.ritz`) and both bin files use the old `c"..."` C-string prefix extensively. Per the spec, application and test code should use `"hello".as_cstr()` for FFI/C-string contexts, or plain `"hello"` (StrView) where zero-copy is sufficient.

The library files (`lib/`) correctly avoid this, preferring `StrView` literals and the `@`-based address-of approach. The inconsistency is stark:

**Wrong (test/bin files — hundreds of occurrences):**
```ritz
let input: *u8 = c"*2\r\n$3\r\nGET\r\n$3\r\nfoo\r\n"
store_set_cstr(@store, c"hello", c"world")
resp_parser_init(@parser, c"*1\r\n$4\r\nPING\r\n", 14)
```

**Correct:**
```ritz
let input: *u8 = "*2\r\n$3\r\nGET\r\n$3\r\nfoo\r\n".as_cstr()
store_set_cstr(@store, "hello".as_cstr(), "world".as_cstr())
```

**Files affected:**
- `/home/aaron/dev/ritz-lang/rz/projects/tome/test/test_resp.ritz` (dozens of uses)
- `/home/aaron/dev/ritz-lang/rz/projects/tome/test/test_store.ritz` (hundreds of uses)
- `/home/aaron/dev/ritz-lang/rz/projects/tome/test/test_commands.ritz` (dozens of uses)
- `/home/aaron/dev/ritz-lang/rz/projects/tome/test/run_tests.ritz` (dozens of uses)
- `/home/aaron/dev/ritz-lang/rz/projects/tome/test/test_server_auth.ritz` (several uses)
- `/home/aaron/dev/ritz-lang/rz/projects/tome/bin/tome_server_blocking.ritz` (several uses)
- `/home/aaron/dev/ritz-lang/rz/projects/tome/bin/tome_cli.ritz` (several uses)
- `/home/aaron/dev/ritz-lang/rz/projects/tome/bin/tome_server.ritz` (several uses)

### M-2: Symbol logical operators `&&` and `||` used instead of keywords (MAJOR)

Several files use `&&` and `||` instead of the required `and` and `or` keywords. The `or`/`and` keyword forms are used correctly in `bin/tome_server.ritz` (lines 198–224), but the symbol forms appear elsewhere:

**Wrong:**
```ritz
if c1 == 13 && c2 == 10          # resp.ritz line 114
if a >= 97 && a <= 122            # resp.ritz lines 579, 583, 599, 603
if c < 48 || c > 57               # resp.ritz line 143, 654
if len < 0 || len > RESP_MAX_BULK_LEN  # resp.ritz line 190
if cmd.argc < 4 || (cmd.argc - 2) % 2 != 0  # commands.ritz line 605
if strcmp(arg, c"-h") == 0 || strcmp(arg, c"--help") == 0  # tome_server_blocking.ritz line 61
```

**Correct:**
```ritz
if c1 == 13 and c2 == 10
if a >= 97 and a <= 122
if c < 48 or c > 57
```

**Files affected:**
- `/home/aaron/dev/ritz-lang/rz/projects/tome/lib/resp.ritz` (many occurrences)
- `/home/aaron/dev/ritz-lang/rz/projects/tome/lib/commands.ritz` (line 605)
- `/home/aaron/dev/ritz-lang/rz/projects/tome/bin/tome_server_blocking.ritz` (lines 44, 61, 65)
- `/home/aaron/dev/ritz-lang/rz/projects/tome/bin/tome_cli.ritz` (lines 45, 61, 240, 247, 254)

Note: `bin/tome_server.ritz` correctly uses `or` (lines 198–224), creating an inconsistency between bin files.

### M-3: Function parameters use `*T` instead of ownership modifiers for non-FFI code (MAJOR)

The entire codebase uses `*T` raw pointer parameters for nearly all functions that take mutable access to structs. While this is explicitly acceptable for FFI/kernel/low-level code, tome is an application-level project (in-memory store). The high-level API functions in `lib/commands.ritz`, `lib/server.ritz`, `lib/blocking_server.ritz` etc. should use `:&` for mutable borrows and plain `T` for const borrows where appropriate.

**Examples from lib/commands.ritz:**
```ritz
# Wrong - raw pointer where ownership modifier is appropriate
fn cmd_ping(ctx: *CommandContext, cmd: *RespCommand) -> i32
fn cmd_ctx_init(ctx: *CommandContext, store: *Store, buf: *u8, cap: i32)

# Correct
fn cmd_ping(ctx:& CommandContext, cmd: RespCommand) -> i32
fn cmd_ctx_init(ctx:& CommandContext, store:& Store, buf: *u8, cap: i32)
```

This is a systemic issue across all `lib/` files. The `buf: *u8` for raw byte buffers is acceptable (FFI boundary), but structs like `CommandContext`, `Store`, `RespParser`, `TomeServer` etc. should use Ritz ownership syntax.

**Files affected:** `lib/server.ritz`, `lib/resp.ritz`, `lib/commands.ritz`, `lib/master.ritz`, `lib/client.ritz`, `lib/blocking_server.ritz`, `lib/server_blocking.ritz`

### M-4: `blocking_server.ritz` uses `@T` as parameter type (inconsistent with rest of codebase)

`lib/blocking_server.ritz` uses a different parameter style from all other files — it uses `@BlockingTomeServer` as a function parameter type instead of `*BlockingTomeServer` (as used consistently elsewhere) or the preferred `:&` modifier:

```ritz
fn blk_conn_state_init(state: @BlockingConnectionState)   # line 44
pub fn blocking_server_init(srv: @BlockingTomeServer, port: i32) -> i32   # line 129
pub fn blocking_server_run(srv: @BlockingTomeServer) -> i32   # line 161
pub fn blocking_server_stop(srv: @BlockingTomeServer)   # line 186
pub fn blocking_server_destroy(srv: @BlockingTomeServer)   # line 190
```

This is inconsistent with the rest of the codebase and with the spec. `@T` is the type for an immutable reference (analogous to `&T`), while these functions clearly need mutable access. Should be `@&T` (mutable reference type) or ideally `:& T` in the parameter modifier style.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/tome/lib/blocking_server.ritz`

### M-5: Test functions in `test_resp.ritz` and `test_store.ritz` lack `[[test]]` attribute

`test/test_resp.ritz` and `test/test_store.ritz` define test functions without the `[[test]]` attribute. Only `test/test_server_auth.ritz` correctly uses `[[test]]`. The other test files omit it entirely.

**Wrong (test_resp.ritz, test_store.ritz, test_commands.ritz):**
```ritz
fn test_parse_array_simple() -> i32
    ...
```

**Correct (test_server_auth.ritz):**
```ritz
[[test]]
fn test_conn_state_init() -> i32
    ...
```

**Files affected:**
- `/home/aaron/dev/ritz-lang/rz/projects/tome/test/test_resp.ritz` (all test functions)
- `/home/aaron/dev/ritz-lang/rz/projects/tome/test/test_store.ritz` (all test functions)
- `/home/aaron/dev/ritz-lang/rz/projects/tome/test/test_commands.ritz` (all test functions)
- `/home/aaron/dev/ritz-lang/rz/projects/tome/test/run_tests.ritz` (test functions)

### M-6: Mixed `or`/`||` usage within `bin/tome_server.ritz` (MAJOR — inconsistency)

`bin/tome_server.ritz` uses `or` correctly in the argument parsing section (lines 198–224), but this is the only file doing so. The `&&` vs `and` inconsistency across the codebase suggests this was partially modernized but not completed. The `or` uses in `tome_server.ritz` are actually correct — it's the other files that need fixing.

### M-7: `run_tests.ritz` uses old manual test runner pattern instead of `[[test]]` framework

`test/run_tests.ritz` hand-wires test execution in a `main()` function rather than using the `[[test]]` attribute system. This creates a second parallel testing mechanism and means tests won't be picked up by the standard test runner.

**File:** `/home/aaron/dev/ritz-lang/rz/projects/tome/test/run_tests.ritz`

### M-8: `conn_state_init` and `tome_server_set_password` take `*T` but `blocking_server.ritz` defines duplicate `ConnectionState` struct

`lib/server_blocking.ritz` (line 34) and `lib/blocking_server.ritz` (line 40) both define their own `ConnectionState`/`BlockingConnectionState` structs with `is_authenticated: i32`. This is code duplication that should be refactored into a shared definition. Additionally `lib/server.ritz` defines yet another `ConnectionState` (line 44). Three definitions of effectively the same struct.

---

## Minor Issues

### m-1: Naming convention — `g_` prefix for globals is non-standard

The codebase uses `g_password`, `g_store`, `g_blk_password`, `g_shutdown` etc. for global variables. While not explicitly forbidden, this is a C convention and there is no mention of it in the naming conventions section. Constants use `SCREAMING_SNAKE_CASE` (correct), but global vars should just use `snake_case` without a prefix per the conventions table.

### m-2: Module-level documentation comments present but inconsistent

Most files have a good module header comment. `lib/client.ritz` is missing a module description beyond the basic header, and `lib/blocking_server.ritz` duplicates content from `lib/server_blocking.ritz` without clearly distinguishing the two.

### m-3: Magic number ASCII values used instead of character literals

Throughout `lib/resp.ritz` and `lib/client.ritz`, ASCII values are used as magic numbers with comments:
```ritz
*ptr0 = 43  # '+'
if first == 43  # '+' Simple string
if c1 == 13 && c2 == 10  # \r\n
```
If the language supports character literals (`'\r'`, `'\n'`, `'+'`), these should be used for readability.

### m-4: `exec_cmd` helper in `test_commands.ritz` ignores command return value

`fn exec_cmd` (line 18 of `test_commands.ritz`) calls `cmd_dispatch` and assigns the result to `let result: i32`, but `result` is never used — only `ctx.resp_len` is returned. This silently discards dispatch errors.

### m-5: Fixed-size key/value buffers (256/8192 bytes) repeated across all command handlers

Every command handler in `lib/commands.ritz` declares `var key: [256]u8` and `var val: [8192]u8` inline. This is a minor code organization issue — define named constants `KEY_BUF_SIZE` and `VAL_BUF_SIZE` rather than repeating magic numbers.

### m-6: `fn is_tty()` in `bin/tome_cli.ritz` is a stub that always returns 1

```ritz
fn is_tty() -> i32
    # ...simplification...
    return 1
```

This function is misleading — it claims to check if stdin is a TTY but always returns 1. Either implement it properly or remove it and inline `1` at the call site with a TODO comment.

### m-7: Imports not grouped per code organization guidelines

The import order guideline is: ritzlib, external, local. Most files follow this (`ritzlib.*` before `lib.*`), but a few files mix the order or have minor deviations. This is a nitpick but worth standardizing.

### m-8: `test_store.ritz` and `test_commands.ritz` do not clean up Store allocations

Test functions allocate a `Store` with `store_new()` but never call any drop/destroy function on it. While this may be intentional (short-lived tests), it leaves heap memory unreleased. If tome has a `store_drop()` function in `lib/tome.ritz`, tests should call it.

### m-9: `BlockingTomeServer.listen_fd` not initialized to `-1` before use

`blocking_server.ritz` and `server_blocking.ritz` both call `blocking_server_destroy`/`tome_server_blocking_destroy` which check `srv.listen_fd >= 0`, but the struct fields are not explicitly initialized to `-1` in a constructor — they rely on whatever the stack contains prior to `blocking_server_init`. A constructor or explicit initialization would make this safer.

### m-10: `lib/commands.ritz` dispatcher uses linear scan instead of a dispatch table

The `cmd_dispatch` function (lines 890–1026) uses 30+ sequential `if resp_arg_eq_ci_sv(...)` comparisons. While this is a functional pattern, a dispatch table (array of `(StrView, fn)` pairs) would be more idiomatic for this scale and easier to maintain. Minor organizational concern.

---

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | ISSUE | Pervasive use of `*T` raw pointers for non-FFI struct parameters; `:&` and `:=` modifiers not used in function signatures |
| Reference Types (@) | ISSUE | One regression: `&buf[0]` in `test_resp.ritz:311`; `blocking_server.ritz` uses `@T` as a parameter type (should be `@&T` or `:&`) |
| Attributes ([[...]]) | ISSUE | `[[test]]` attribute only used in `test_server_auth.ritz`; the other 4 test files omit it entirely |
| Logical Operators | ISSUE | `&&` and `||` used in `resp.ritz`, `commands.ritz`, `tome_server_blocking.ritz`, `tome_cli.ritz`; `tome_server.ritz` correctly uses `or` |
| String Types | ISSUE | `c"..."` prefix used pervasively in all test and bin files; library files are correct |
| Error Handling | OK | No deeply nested match chains; error codes propagated via return values consistently |
| Naming Conventions | OK | Functions snake_case, types PascalCase, constants SCREAMING_SNAKE_CASE — all correct. Minor: `g_` prefix on globals |
| Code Organization | OK | Files have module headers, imports grouped correctly, logical section grouping with dividers |

---

## Files Needing Attention

**Critical:**
- `/home/aaron/dev/ritz-lang/rz/projects/tome/test/test_resp.ritz` — `&buf[0]` on line 311 (critical regression)

**High priority (Major):**
- `/home/aaron/dev/ritz-lang/rz/projects/tome/lib/resp.ritz` — pervasive `&&`/`||`, string type OK but internal logic operators wrong
- `/home/aaron/dev/ritz-lang/rz/projects/tome/lib/blocking_server.ritz` — `@T` parameter type misuse
- `/home/aaron/dev/ritz-lang/rz/projects/tome/test/test_resp.ritz` — no `[[test]]`, `c"..."` strings, old `&` sigil
- `/home/aaron/dev/ritz-lang/rz/projects/tome/test/test_store.ritz` — no `[[test]]`, `c"..."` strings throughout (largest offender)
- `/home/aaron/dev/ritz-lang/rz/projects/tome/test/test_commands.ritz` — no `[[test]]`, `c"..."` strings, `&buf[0]` style
- `/home/aaron/dev/ritz-lang/rz/projects/tome/test/run_tests.ritz` — no `[[test]]`, manual test runner pattern
- `/home/aaron/dev/ritz-lang/rz/projects/tome/bin/tome_server_blocking.ritz` — `&&`/`||`, `c"..."` strings
- `/home/aaron/dev/ritz-lang/rz/projects/tome/bin/tome_cli.ritz` — `&&`/`||`, `c"..."` strings
- `/home/aaron/dev/ritz-lang/rz/projects/tome/lib/commands.ritz` — `*T` parameters, one `||` instance

**Lower priority (Major — systemic ownership modifiers):**
- All `lib/` files need ownership modifier review for non-FFI struct parameters

---

## Recommendations

1. **[CRITICAL] Fix `&buf[0]` to `@buf[0]`** in `test/test_resp.ritz` line 311 — this is the only compile-breaking regression.

2. **[HIGH] Replace `&&`/`||` with `and`/`or`** throughout `lib/resp.ritz`, `lib/commands.ritz`, `bin/tome_server_blocking.ritz`, and `bin/tome_cli.ritz`. The pattern is widespread in resp.ritz especially — do a bulk find-replace.

3. **[HIGH] Replace `c"..."` with `"...".as_cstr()`** in all test and bin files. The library files are already clean. This is the highest-volume change needed (~200+ occurrences in test files alone).

4. **[HIGH] Add `[[test]]` attribute** to all test functions in `test_resp.ritz`, `test_store.ritz`, `test_commands.ritz`, and `run_tests.ritz`.

5. **[MEDIUM] Fix `@T` parameter type** in `lib/blocking_server.ritz` — replace `@BlockingTomeServer` with `@&BlockingTomeServer` (mutable reference type) or migrate to `:&` modifier style.

6. **[MEDIUM] Adopt `:&` and `:=` ownership modifiers** for struct parameters across the library files. This is a larger refactor — start with the public API functions in `commands.ritz` and `server.ritz`.

7. **[LOW] Consolidate `ConnectionState` struct** — three files define essentially the same `is_authenticated: i32` struct. Extract to a shared `lib/auth.ritz` or `lib/tome.ritz`.

8. **[LOW] Define `KEY_BUF_SIZE` and `VAL_BUF_SIZE` constants** in `commands.ritz` to replace the repeated `256`/`8192` magic numbers.
