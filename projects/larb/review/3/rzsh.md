# LARB Review: rzsh (Ritz Shell)

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

rzsh is a cross-platform interactive shell targeting both Linux and Harland, with clean OS abstraction via `[[target_os]]` conditional compilation. The code is well-structured and readable, and uses several modern Ritz idioms correctly (keyword logical operators, `[[...]]` attributes, `@` address-of syntax). However, the project has pervasive use of the `c"..."` string prefix for all string literals, which should be replaced with `"...".as_cstr()` in application code, and all function parameters use raw `*u8` pointer types where ownership modifiers with `StrView` would be more idiomatic.

## Statistics

- **Files Reviewed:** 3 (`main.ritz`, `common.ritz`, `os.ritz`)
- **Total SLOC:** ~280
- **Issues Found:** 35+ (Critical: 0, Major: 31+, Minor: 4)

## Critical Issues

None. The code compiles under the current syntax and has no memory safety violations beyond what is expected in this low-level shell context.

## Major Issues

### 1. Pervasive `c"..."` String Prefix (MAJOR) - all 3 files

Every string literal in the project uses the old `c"..."` prefix. Per the spec, the modern form is `"...".as_cstr()` for FFI/syscall strings. The `c"..."` form is noted as acceptable in low-level compiler internals, but rzsh is an application and should use the modern syntax.

Affected: every `puts(c"...")`, `println(c"...")`, `strcmp(cmd, c"...")` call site.

Examples in `main.ritz`:
```ritz
# WRONG (current)
println(c"rzsh - Ritz Shell v0.1 (linux)")
puts(c"ls: cannot access '")
strcmp(cmd, c"help")

# CORRECT
println("rzsh - Ritz Shell v0.1 (linux)".as_cstr())
puts("ls: cannot access '".as_cstr())
strcmp(cmd, "help".as_cstr())
```

Examples in `common.ritz`:
```ritz
# WRONG (current)
println(c"rzsh - Ritz Shell")
puts(c"rzsh> ")

# CORRECT
println("rzsh - Ritz Shell".as_cstr())
puts("rzsh> ".as_cstr())
```

Examples in `os.ritz`:
```ritz
# WRONG (current)
return c"."
return c"/usr/bin/"

# CORRECT
return ".".as_cstr()
return "/usr/bin/".as_cstr()
```

Count: approximately 30+ occurrences across all three files.

### 2. Function Signatures Using `*u8` Instead of Idiomatic String Types (MAJOR)

All string-handling functions use raw `*u8` as parameter and return types. For functions that accept read-only string data, `StrView` should be preferred. The `*u8` type is appropriate for FFI output buffers and pointer arithmetic, but the public API of `puts`, `println`, `print_prompt`, `cmd_help`, etc. should accept `StrView`.

Examples in `common.ritz`:
```ritz
# CURRENT - raw pointer, no ownership signal
pub fn puts(s: *u8) -> i64
pub fn println(s: *u8) -> i64

# PREFERRED - const borrow of StrView
pub fn puts(s: StrView) -> i64
pub fn println(s: StrView) -> i64
```

Examples in `os.ritz`:
```ritz
# CURRENT
pub fn os_readdir(path: *u8, buf: *u8, buf_size: i64) -> i64
pub fn os_spawn_and_wait(path: *u8, argv: **u8, argc: i32) -> i32

# PREFERRED (at minimum for path param)
pub fn os_readdir(path: StrView, buf: *u8, buf_size: i64) -> i64
```

Note: `buf: *u8` for output buffers and `argv: **u8` for exec argv arrays are acceptable as raw pointers given the FFI/syscall context.

### 3. Return Types `-> *u8` for String-Returning Functions (MAJOR) - `main.ritz`, `os.ritz`

Functions returning static string literals use `-> *u8`. These should return `StrView` or `@u8` (immutable reference) to convey intent.

```ritz
# WRONG (current) - main.ritz
fn version_string() -> *u8
    return c"rzsh - Ritz Shell v0.1 (linux)"

# PREFERRED
fn version_string() -> StrView
    return "rzsh - Ritz Shell v0.1 (linux)"
```

Affected functions: `version_string()`, `os_default_ls_path()`, `os_bin_path_1()`, `os_bin_path_2()`.

### 4. `parse_args` Mutates Through Raw Pointer Without Ownership Signal (MAJOR) - `common.ritz`

`parse_args` takes `line: *u8` and writes null bytes into it (in-place tokenization). This mutation is invisible in the function signature. The parameter should be `line:& *u8` or the design should be documented clearly, since callers cannot tell from the signature that their buffer will be modified.

```ritz
# CURRENT - silent mutation
pub fn parse_args(line: *u8) -> i32

# PREFERRED - signals mutation intent
pub fn parse_args(line:& *u8) -> i32
```

### 5. `cmd_ls` Parameter `argc: i32` Passed by Value but `g_argv` Accessed as Global (MAJOR) - `main.ritz`

Minor design concern: `cmd_ls` and all command functions receive `argc` but then read arguments from the global `g_argv`. This pattern is functional but non-idiomatic for Ritz. A struct carrying `(argc, argv)` passed by const borrow would be cleaner and would allow proper use of ownership modifiers.

## Minor Issues

### 1. Missing Module Documentation Header in `main.ritz` (MINOR)

`main.ritz` has a comment block at the top, but `common.ritz` and `os.ritz` headers reference old design ("platform between rzsh.harland.ritz and rzsh.linux.ritz") that predates the unified single-file design. These should be updated.

`common.ritz` line 3:
```
# This module contains platform-agnostic code shared between
# rzsh.harland.ritz and rzsh.linux.ritz
```
The referenced files no longer exist; the comment is stale.

### 2. Magic Number Literals Without Named Constants (MINOR) - `common.ritz`, `main.ritz`

Several ASCII values are used directly without named constants, making the code harder to read:

```ritz
# common.ritz - line 44
return c == 32 or c == 9 or c == 10 or c == 13

# main.ritz - line 224
if c == 13 or c == 10      # CR/LF
else if c == 127 or c == 8  # DEL/BS
else if c == 3              # ETX / Ctrl-C
else if c == 4              # EOT / Ctrl-D
else if c >= 32 and c < 127 # printable range
```

These would be clearer as named constants:
```ritz
const ASCII_CR:  u8 = 13
const ASCII_LF:  u8 = 10
const ASCII_DEL: u8 = 127
const ASCII_BS:  u8 = 8
const ASCII_ETX: u8 = 3
const ASCII_EOT: u8 = 4
```

### 3. `g_argv` Array Length Hardcoded as 32 Instead of Using `MAX_ARGS` (MINOR) - `common.ritz`

```ritz
# Line 83 - CURRENT
pub var g_argv: [32]*u8

# PREFERRED
pub var g_argv: [MAX_ARGS]*u8
```

`MAX_ARGS` is defined as `32` on line 18; the array declaration should reference it.

### 4. No `defer` for `sys_close(fd)` in `os_readdir` Linux Implementation (MINOR) - `os.ritz`

The Linux `os_readdir` implementation opens a file descriptor and closes it manually at the end. While the function has a single exit path (so it is not unsafe), using `defer` would follow the idiomatic Ritz pattern:

```ritz
# CURRENT
let fd: i32 = sys_open(path, O_RDONLY | O_DIRECTORY)
if fd < 0
    return -1
# ... long loop ...
sys_close(fd)
return out_pos

# PREFERRED
let fd: i32 = sys_open(path, O_RDONLY | O_DIRECTORY)
if fd < 0
    return -1
defer sys_close(fd)
# ... long loop ...
return out_pos
```

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | ISSUE | Function params use raw `*u8` throughout; no `:&` or `:=` modifiers used where appropriate; `parse_args` mutates silently |
| Reference Types (@) | OK | `@x` address-of syntax used correctly and consistently; no old `&x` forms found |
| Attributes ([[...]]) | OK | `[[target_os = "...]]` used correctly in all conditional compilation blocks; no old `@attr` forms found |
| Logical Operators | OK | `and`, `or`, `not` used correctly throughout; no `&&`, `||`, `!` found |
| String Types | ISSUE | Pervasive `c"..."` prefix (30+ occurrences); no `StrView` usage; all strings passed as `*u8` |
| Error Handling | OK | Low-level code returns i32/i64 status codes as expected for syscall wrappers; pattern is appropriate for this layer |
| Naming Conventions | OK | snake_case functions/variables, SCREAMING_SNAKE_CASE constants, correct throughout |
| Code Organization | OK | Files are logically separated; imports grouped; constants at top; minor stale comment in common.ritz |

## Files Needing Attention

1. **`/home/aaron/dev/ritz-lang/rz/projects/rzsh/src/common.ritz`** - Highest priority: all string literals use `c"..."`, `puts`/`println` signatures use `*u8`, stale header comment, `g_argv` hardcoded size, magic ASCII constants.

2. **`/home/aaron/dev/ritz-lang/rz/projects/rzsh/src/main.ritz`** - `version_string()` return type, all `c"..."` string literals, magic ASCII constants in main loop.

3. **`/home/aaron/dev/ritz-lang/rz/projects/rzsh/src/os.ritz`** - `c"..."` return literals in path functions, `os_readdir`/`os_spawn_and_wait` path parameter types, missing `defer` for fd cleanup.

## Recommendations

1. **(High)** Replace all `c"..."` literals with `"...".as_cstr()` across all three files. This is the largest surface area of non-compliance (~30+ sites) and the most systematic fix.

2. **(High)** Update public API string parameter types from `*u8` to `StrView` for all functions that accept read-only string data (`puts`, `println`, `os_readdir` path, `os_spawn_and_wait` path, `os_default_ls_path`, `os_bin_path_1`, `os_bin_path_2` return types).

3. **(Medium)** Add `:&` modifier to `parse_args` parameter to signal in-place mutation, or refactor to avoid mutating the caller's buffer.

4. **(Low)** Extract magic ASCII constants to named `const` declarations in `common.ritz`.

5. **(Low)** Fix `g_argv` array size to reference `MAX_ARGS` instead of the hardcoded `32`.

6. **(Low)** Add `defer sys_close(fd)` in the Linux `os_readdir` implementation.

7. **(Low)** Update stale header comment in `common.ritz` to reflect the current unified architecture.
