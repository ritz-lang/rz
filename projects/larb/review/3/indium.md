# LARB Review: Indium

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

Indium is the Harland userspace distribution: a collection of small utility programs (hello, echo, wc, ping, seq10, cat_motd, args_test, mmap_test, etc.) plus a libharland compatibility shim and an init process that functions as a test harness. The codebase is largely low-level syscall code targeting the Harland OS, which grants some latitude for raw pointer usage, but it shows a pervasive and systematic use of the old `c"..."` string literal prefix that should be migrated to `"...".as_cstr()`. There are no critical ownership-modifier violations, but the string type issue is present in virtually every file and warrants a NEEDS WORK verdict.

## Statistics

- **Files Reviewed:** 17
- **Total SLOC:** ~450
- **Issues Found:** 22 (Critical: 0, Major: 20, Minor: 2)

## Critical Issues

None. No Rust-style `&T`/`&mut T` parameters, no old `@test`/`@inline` attribute syntax detected.

## Major Issues

### 1. Pervasive `c"..."` String Literal Prefix (String Types - MAJOR)

Every file that does any I/O uses `c"..."` syntax for C string literals. Per the specification, this should be `"...".as_cstr()`. This is the single largest issue in the project and is entirely systematic - it appears in **every** file except `false.ritz`, `true.ritz`, `exitcode.ritz`, and `minimal_syscall.ritz` (which have no string literals at all).

Affected files and representative lines:

- `hello.ritz:10` - `let msg: *u8 = c"Hello, Harland!\n"`
- `hello_tier1.ritz:10` - `print_str(c"Hello, Ritz!\n")`
- `echo.ritz:21` - `sys_write(STDOUT, c" ", 1)`
- `echo.ritz:26` - `sys_write(STDOUT, c"\n", 1)`
- `seq10.ritz:12` - `print_str(c"\n")`
- `args_test.ritz:26` - `puts(c"args_test: received ")`
- `ping.ritz:36` - `println(c"Usage: ping <host>")`
- `cat_motd.ritz:10` - `let fd: i32 = sys_open(c"/etc/motd", O_RDONLY)`
- `wc.ritz:14` - `print_str(c"Usage: wc <filename>\n")`
- `init.ritz:21` - `print_str(c"[test] ")`
- `mmap_test.ritz:9` - `print_str(c"mmap test: allocating 4KB...\n")`
- `portable_hello.ritz:69` - `let msg: *u8 = c"Hello from portable Ritz!\n"`
- `portable_getpid.ritz:87` - `let msg1: *u8 = c"Hello from PID "`

The specification notes that `c"..."` may be tolerated internally in low-level code, but the sheer volume here still warrants attention. All call sites where the literal is passed to a `*u8` parameter should use `"...".as_cstr()`.

### 2. `mmap_test.ritz` - Missing `pub` on `main`

`mmap_test.ritz:8` declares `fn main() -> i32` without the `pub` visibility modifier. All other entry-point `main` functions in the project correctly use `pub fn main`. This is inconsistent and may affect linking.

```ritz
# WRONG (mmap_test.ritz:8):
fn main() -> i32

# CORRECT (as in every other file):
pub fn main() -> i32
```

### 3. `cat_motd.ritz` - Missing `defer` for File Descriptor Cleanup

`cat_motd.ritz` opens a file descriptor but does not use `defer` for cleanup. The `sys_close(fd)` call only appears on the happy path; if a future code path exits early, the fd will leak. Using `defer` immediately after a successful open is the idiomatic pattern.

```ritz
# CURRENT (non-idiomatic):
let fd: i32 = sys_open(c"/etc/motd", O_RDONLY)
if fd < 0
    return 1
# ... work ...
sys_close(fd)

# IDIOMATIC:
let fd: i32 = sys_open("/etc/motd".as_cstr(), O_RDONLY)
if fd < 0
    return 1
defer sys_close(fd)
# ... work ...
```

The same applies to `wc.ritz:20-50`, where `sys_close(fd)` is called explicitly rather than via `defer`.

### 4. `libharland.ritz` - Deprecated Library with Raw Pointer Parameters

`libharland.ritz` is explicitly marked deprecated in its own header comment. However, it is still imported by 8 of the 17 files. The migration path (using `ritzlib.sys` directly) is documented in the file itself. All files importing `libharland` should be migrated to `ritzlib.sys` imports.

Files still importing `libharland`:
- `echo.ritz`
- `hello_tier1.ritz`
- `seq10.ritz`
- `cat_motd.ritz`
- `init.ritz`
- `mmap_test.ritz`
- `wc.ritz`

### 5. `libharland.ritz` - Raw Pointer in `print_str` and `sys_open` Signatures

```ritz
# libharland.ritz:40
pub fn sys_open(path: *u8, flags: i32) -> i32

# libharland.ritz:55
pub fn print_str(s: *u8)
```

These functions take `*u8` (raw pointer) where a proper Ritz type (`StrView` or `@u8`) would be expected in non-FFI code. Since this library is a compatibility shim bridging to actual kernel syscalls, the raw pointer is unavoidable at the lowest level, but the public-facing wrappers (`print_str`, `print_num`) could use `StrView` for the application-level API.

### 6. `portable_getpid.ritz` and `portable_hello.ritz` - Duplicate Inline Syscall Boilerplate

Both `portable_getpid.ritz` and `portable_hello.ritz` define their own local `syscall0`/`syscall1`/`syscall3` wrapper functions with inline assembly, duplicating what is available in `ritzlib.sys`. This is an artifact of them being standalone demo files, but it means these files will diverge from the canonical implementation. They should import from `ritzlib.sys`.

## Minor Issues

### 1. `wc.ritz:63` - Bare integer expression as implicit return

```ritz
    sys_exit(0)
    0
```

The trailing `0` after `sys_exit(0)` is used as an implicit return value. While the intent is clear (the program never reaches this line), using an explicit `return 0` would be clearer and consistent with every other `main` in the project.

### 2. Missing module-level documentation in some files

`args_test.ritz`, `ping.ritz`, and `wc.ritz` have good header comments. However `mmap_test.ritz`, `cat_motd.ritz`, and `seq10.ritz` have minimal or incomplete descriptions. Per the code organization guidelines, each file should include a brief module documentation header.

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | OK | No Rust-style `&T`/`&mut T` in parameters. Raw `*u8` is acceptable in this syscall-level context. |
| Reference Types (@) | OK | `@x` syntax used correctly (e.g., `@buf[0]`, `@digit`, `@newline`). No misuse of `&x` for address-of. |
| Attributes ([[...]]) | OK | `[[target_os = "..."]]` used correctly in `portable_hello.ritz`. No old `@test`/`@inline` found. |
| Logical Operators | OK | `wc.ritz` correctly uses `or` and `not` keywords. No `&&`, `\|\|`, or `!` found. |
| String Types | ISSUE | Pervasive `c"..."` prefix throughout all files with string literals. Should be `"...".as_cstr()`. |
| Error Handling | OK | No Result types used (appropriate for syscall-level code). Error paths handled via return codes. |
| Naming Conventions | OK | Functions are snake_case, constants are SCREAMING_SNAKE_CASE, types are PascalCase. |
| Code Organization | ISSUE | Missing `defer` for fd cleanup in `cat_motd.ritz` and `wc.ritz`. `mmap_test.ritz` missing `pub` on `main`. |

## Files Needing Attention

| File | Issues | Priority |
|------|--------|----------|
| All files with string I/O | `c"..."` prefix usage | Major - systematic |
| `mmap_test.ritz` | Missing `pub` on `main` | Major |
| `cat_motd.ritz` | No `defer` for fd cleanup; `c"..."` usage | Major |
| `wc.ritz` | No `defer` for fd cleanup; trailing bare `0`; `c"..."` usage | Major |
| `libharland.ritz` | Deprecated; `*u8` in public wrappers | Major |
| `portable_getpid.ritz` | Duplicates `ritzlib.sys` boilerplate | Major |
| `portable_hello.ritz` | Duplicates `ritzlib.sys` boilerplate | Major |

## Recommendations

1. **[Major - Systematic]** Do a project-wide replacement of `c"..."` with `"...".as_cstr()`. Given there are approximately 50+ instances across 13 files, this should be done as a single sweep. The NOTE in the spec that compilers may use `c"..."` internally does not apply here - these are application-level programs.

2. **[Major]** Add `pub` to `fn main()` in `mmap_test.ritz` to match every other entry point in the project.

3. **[Major]** Add `defer sys_close(fd)` immediately after the `fd < 0` guard in `cat_motd.ritz` and `wc.ritz`, and remove the manual `sys_close()` calls at the end of each function.

4. **[Major]** Migrate all 7 files still importing `libharland` to import directly from `ritzlib.sys`, following the migration guide already documented in `libharland.ritz` itself.

5. **[Major]** Consolidate `portable_getpid.ritz` and `portable_hello.ritz` to import syscall wrappers from `ritzlib.sys` rather than defining inline assembly locally.

6. **[Minor]** Replace the trailing bare `0` in `wc.ritz` with `return 0` for consistency.
