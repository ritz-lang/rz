# LARB Review: Zeus

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

Zeus is the process manager / application server for Ritz, managing shared memory ring buffers and worker processes. The project is well-structured and comprehensive (33 files, ~10,600 SLOC), with thorough test coverage. However it has two pervasive systemic issues: `c"..."` string literal syntax used throughout application code (97 occurrences) where `"...".as_cstr()` is required, and raw pointer parameters `*T` used across nearly every function signature instead of the finalized ownership modifier syntax (`x: T` for const borrow, `x:& T` for mutable borrow). Symbol logical operators `||` and `&&` also appear across 11 and 9 files respectively instead of the required `or`/`and` keywords.

## Statistics

- **Files Reviewed:** 33 (15 lib, 17 test, 1 src)
- **Total SLOC:** ~10,627
- **Issues Found:** 375+ (Critical: 0, Major: 375+, Minor: 5)

## Critical Issues

None. No old `@test`/`@inline` attribute syntax found - all tests correctly use `[[test]]`. No dangerous memory safety patterns beyond what is expected for low-level systems code. No security vulnerabilities identified.

## Major Issues

### 1. `c"..."` String Literal Prefix (97 occurrences, 7 files) - WRONG SYNTAX

All application-level C string usage must migrate from the old `c"..."` prefix to `"...".as_cstr()`. The spec notes that the compiler itself may use `c"..."` internally for FFI, but application code must use the new form.

**Files affected:**
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/src/main.ritz` (49 occurrences) - the worst offender
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/main_helpers.ritz` (10 occurrences)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/test/test_main.ritz` (26 occurrences)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/test/test_daemon.ritz` (4 occurrences)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/test/test_hotreload.ritz` (4 occurrences)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/test/test_runtime.ritz` (3 occurrences)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/shm.ritz` (1 occurrence)

**Example from `src/main.ritz`:**
```ritz
# WRONG:
print_str(c"zeus: starting\n")
opts.socket_path = c"/run/zeus/zeus.sock"
sys_write(1, c"-", 1)

# CORRECT:
print_str("zeus: starting\n".as_cstr())
opts.socket_path = "/run/zeus/zeus.sock".as_cstr()
sys_write(1, "-".as_cstr(), 1)
```

---

### 2. Raw Pointer Parameters Instead of Ownership Modifiers (249 occurrences, 18 files) - WRONG SYNTAX

Every function that takes a pointer parameter (`fn foo(x: *SomeType)`) must be updated to use the finalized ownership modifier syntax. Raw pointers (`*T`) are for FFI/unsafe contexts only. For application code:
- Pass-by-const-borrow: `x: SomeType` (no sigil)
- Pass-by-mutable-borrow: `x:& SomeType`
- Pass-by-move: `x:= SomeType`

**All 18 source files are affected.** Representative examples:

**`lib/daemon.ritz`** (18 occurrences):
```ritz
# WRONG:
pub fn daemon_init(ctx: *DaemonContext, cfg: *DaemonConfig) -> i32
pub fn daemon_destroy(ctx: *DaemonContext)
pub fn daemon_alloc_worker_slot(ctx: *DaemonContext) -> i32

# CORRECT:
pub fn daemon_init(ctx:& DaemonContext, cfg: DaemonConfig) -> i32
pub fn daemon_destroy(ctx:& DaemonContext)
pub fn daemon_alloc_worker_slot(ctx:& DaemonContext) -> i32
```

**`lib/shm.ritz`** (12 occurrences):
```ritz
# WRONG:
pub fn shm_create(region: *ShmRegion, cfg: *ShmConfig) -> i32

# CORRECT:
pub fn shm_create(region:& ShmRegion, cfg: ShmConfig) -> i32
```

**`lib/ring.ritz`** (12 occurrences):
```ritz
# WRONG:
pub fn request_slot_init(slot: *RequestSlot)
pub fn request_slot_set_method(slot: *RequestSlot, method: u8)

# CORRECT:
pub fn request_slot_init(slot:& RequestSlot)
pub fn request_slot_set_method(slot:& RequestSlot, method: u8)
```

The pattern is consistent across all files: every function taking a struct pointer for mutation should use `:&`, and every function taking a struct pointer for read-only should use no sigil (const borrow).

---

### 3. Logical Operators: `||` and `&&` Used Instead of `or`/`and` (29 + 19 = 48 occurrences, 11+9 files)

All uses of `||`, `&&`, and `!` (as logical operators) must be replaced with `or`, `and`, and `not`.

**Files affected by `||` (29 occurrences):**
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/daemon.ritz` (7)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/valet.ritz` (6)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/main_helpers.ritz` (1)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/worksteal.ritz` (3)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/hotreload.ritz` (2)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/zeus_client.ritz` (1)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/src/main.ritz` (2)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/test/test_daemon.ritz` (1)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/test/test_hotreload.ritz` (4)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/test/test_memory.ritz` (1)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/test/test_streaming.ritz` (1)

**Files affected by `&&` (19 occurrences):**
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/zeus_client.ritz` (6)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/valet.ritz` (2)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/daemon.ritz` (1)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/shm.ritz` (2)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/main_helpers.ritz` (2)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/arena.ritz` (1)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/streaming.ritz` (1)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/hotreload.ritz` (2)
- `/home/aaron/dev/ritz-lang/rz/projects/zeus/src/main.ritz` (2)

**Examples:**

**`src/main.ritz` line 124:**
```ritz
# WRONG:
if sig == SIGTERM || sig == SIGINT

# CORRECT:
if sig == SIGTERM or sig == SIGINT
```

**`lib/daemon.ritz` (multiple):**
```ritz
# WRONG:
if slot_idx < 0 || slot_idx >= MAX_WORKERS
if slot.state != WORKER_SLOT_FREE

# CORRECT:
if slot_idx < 0 or slot_idx >= MAX_WORKERS
```

**`src/main.ritz` lines 191, 223:**
```ritz
# WRONG:
if n != 8 || hello.msg_type != CLIENT_MSG_HELLO
if slot != null && slot.state == WORKER_SLOT_RUNNING

# CORRECT:
if n != 8 or hello.msg_type != CLIENT_MSG_HELLO
if slot != null and slot.state == WORKER_SLOT_RUNNING
```

**`lib/main_helpers.ritz` line 93:**
```ritz
# WRONG:
else if str_eq_cstr(arg, c"-h") || str_eq_cstr(arg, c"--help")

# CORRECT:
else if str_eq_cstr(arg, "-h".as_cstr()) or str_eq_cstr(arg, "--help".as_cstr())
```

---

### 4. Raw Pointer Types Used as Function Parameters for Non-FFI Code

Related to issue 2 but distinct: function return types that return `*T` for application structs should also use reference types (`@T` / `@&T`) where appropriate. For example:

**`lib/daemon.ritz`:**
```ritz
# WRONG (returns raw pointer for application use):
pub fn daemon_get_worker_slot(ctx: *DaemonContext, slot_idx: i32) -> *WorkerSlot

# CORRECT:
pub fn daemon_get_worker_slot(ctx: DaemonContext, slot_idx: i32) -> @WorkerSlot
```

This applies to all the `*_get_*` accessor functions across lib files.

---

### 5. Method Organization: Free Functions Instead of `impl` Blocks

All modules define methods as free functions with type-prefixed names (e.g. `daemon_init`, `daemon_destroy`, `shm_create`) instead of using `impl` blocks. While the spec notes this is deprecated but tolerated, all 15 lib files should migrate to `impl` blocks.

**Example from `lib/control.ritz`:**
```ritz
# DEPRECATED (tolerated):
pub fn control_block_init(cb: *ControlBlock)
pub fn control_block_set_state(cb: *ControlBlock, state: i32)
pub fn control_block_req_write_inc(cb: *ControlBlock) -> i64

# PREFERRED:
impl ControlBlock
    pub fn init(self:& ControlBlock)
    pub fn set_state(self:& ControlBlock, state: i32)
    pub fn req_write_inc(self:& ControlBlock) -> i64
```

---

### 6. Missing `defer` for Resource Cleanup

Several functions acquire resources and close them at multiple exit points rather than using `defer`. This is a correctness risk if new code paths are added.

**`lib/shm.ritz` `shm_create`:**
```ritz
# Current pattern - multiple manual closes:
let fd: i32 = sys_memfd_create(...)
if fd < 0
    return fd
let ret: i32 = sys_ftruncate(fd, total_size)
if ret < 0
    sys_close(fd)    # must remember to close manually
    return ret

# Preferred pattern with defer:
let fd: i32 = sys_memfd_create(...)?
defer sys_close(fd)
let ret: i32 = sys_ftruncate(fd, total_size)?
```

This pattern appears in `lib/shm.ritz`, `lib/valet.ritz`, `lib/daemon.ritz`, and `lib/zeus_client.ritz`.

---

### 7. Missing Error Propagation with `?` Operator

Several functions use manual error checking (`if result < 0 { return result }`) that could use the `?` operator for cleaner code.

**`lib/zeus_client.ritz` `zeus_client_connect`:**
```ritz
# Current:
let fd: i32 = syscall3(SYS_SOCKET, ...) as i32
if fd < 0
    client.state = ZEUS_CLIENT_STATE_ERROR
    return fd

# Could use ? with proper Result types:
let fd: i32 = syscall3(SYS_SOCKET, ...)?
```

Note: full adoption of `?` requires return types to be `Result<T, E>`, which is a larger refactor.

## Minor Issues

### 1. Documentation Headers

Files like `lib/ring.ritz`, `lib/arena.ritz`, and `lib/control.ritz` have module documentation headers, which is good. However several test files (e.g. `test/test_memory.ritz`) lack a description of what module they test beyond the filename. Minor.

### 2. Magic Numbers Without Constants

`src/main.ritz` uses several raw syscall numbers and magic values inline:
```ritz
syscall2(35, @tv[0] as i64, 0)  # SYS_NANOSLEEP
syscall2(96, @tv[0] as i64, 0)  # SYS_GETTIMEOFDAY
```
These should be named constants, as done in some other files like `lib/daemon.ritz` which properly declares `const SYS_SOCKET`, etc.

### 3. Duplicate Constant Definitions

`SIGTERM`, `SIGHUP`, `SIGCHLD`, `SIGINT` are defined in both `lib/daemon.ritz` and `lib/main_helpers.ritz`. These should live in one place (likely `lib/main_helpers.ritz` since it exports them as `pub`).

Similarly `DEFAULT_WORKER_COUNT`, `DEFAULT_SHM_SIZE`, `DEFAULT_RING_CAPACITY` are declared in both `lib/daemon.ritz` and `lib/main_helpers.ritz`.

### 4. Hardcoded sizeof Estimates

Several places hardcode struct sizes with comments:
```ritz
let slot_size: i64 = (MAX_WORKERS as i64) * 72  # sizeof(WorkerSlot) ~ 72
let slot_size: i64 = 64  # sizeof(WorkerSlot) - approximate
```
These are fragile. A `sizeof()` intrinsic or a dedicated size function would be safer.

### 5. Test File Naming Convention

`test/helpers.ritz` is not prefixed with `test_` but is a test support file. Consider renaming to `test/test_helpers.ritz` for consistency, or documenting the convention.

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | ISSUE | All 18 source files use `*T` raw pointer params instead of `: T` / `:& T` / `:= T`. 249 occurrences. |
| Reference Types (@) | ISSUE | Return types use `*T` instead of `@T` / `@&T` for non-FFI application accessors. |
| Attributes ([[...]]) | OK | All `[[test]]` attributes correctly used. No old `@test`/`@inline` syntax found. |
| Logical Operators | ISSUE | 48 occurrences of `\|\|`/`&&` across 15 files. Should be `or`/`and`. |
| String Types | ISSUE | 97 occurrences of `c"..."` prefix in application code across 7 files. |
| Error Handling | PARTIAL | Manual error returns are consistent but `?` operator and `Result` types not used. |
| Naming Conventions | OK | snake_case functions, PascalCase types, SCREAMING_SNAKE constants all correct. |
| Code Organization | PARTIAL | Good module structure, but all methods as free functions instead of `impl` blocks. |

## Files Needing Attention

Ranked by number and severity of issues:

1. **`/home/aaron/dev/ritz-lang/rz/projects/zeus/src/main.ritz`** - 49 c-string usages, 2 `||`, 2 `&&`, 12 raw pointer params, no `defer`
2. **`/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/zeus_client.ritz`** - 27 raw pointer params, 6 `&&`, 1 `||`
3. **`/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/daemon.ritz`** - 18 raw pointer params, 7 `||`, 1 `&&`, no `defer`
4. **`/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/valet.ritz`** - 16 raw pointer params, 6 `||`, 2 `&&`
5. **`/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/main_helpers.ritz`** - 10 c-strings, 12 raw pointer params, 2 `&&`, 1 `||`
6. **`/home/aaron/dev/ritz-lang/rz/projects/zeus/test/test_main.ritz`** - 26 c-strings (test file)
7. **`/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/hotreload.ritz`** - 17 raw pointer params, 2 `||`, 2 `&&`
8. **`/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/runtime.ritz`** - 15 raw pointer params
9. **`/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/worksteal.ritz`** - 15 raw pointer params, 3 `||`
10. **`/home/aaron/dev/ritz-lang/rz/projects/zeus/lib/limits.ritz`** - 24 raw pointer params

## Recommendations

Prioritized list for what to fix, in order:

1. **[MAJOR] Migrate all `||`/`&&` to `or`/`and`** - This is a mechanical find-and-replace. 48 occurrences across 15 files. Do this first as it has the smallest blast radius.

2. **[MAJOR] Migrate `c"..."` to `"...".as_cstr()`** - Also largely mechanical. 97 occurrences in 7 files. The test files (`test/test_main.ritz` alone has 26) should be especially easy to update.

3. **[MAJOR] Migrate raw pointer parameters to ownership modifiers** - This is the largest change. 249 occurrences across 18 files. A strategy:
   - Functions that mutate their argument: change `x: *T` to `x:& T`
   - Functions that only read their argument: change `x: *T` to `x: T`
   - Functions that take ownership: change `x: *T` to `x:= T`
   - Call sites: change `&var` to `@&var` (mutable ref) or `@var` (immutable ref)

4. **[MAJOR] Update accessor return types** - After (3), change `-> *T` return types for application accessors to `-> @T` or `-> @&T` as appropriate.

5. **[MAJOR] Add `defer` for resource cleanup** - After (3)/(4), audit `lib/shm.ritz`, `lib/daemon.ritz`, `lib/valet.ritz`, `lib/zeus_client.ritz` for multi-exit resource acquisition patterns.

6. **[MINOR] Migrate free functions to `impl` blocks** - Lower priority, but should be done before the codebase grows further. Can be done incrementally module by module.

7. **[MINOR] Deduplicate constants** - Remove duplicate signal and config constant declarations between `lib/daemon.ritz` and `lib/main_helpers.ritz`.

---

*LARB Review v3.0 - Zeus Application Server - February 2026*
