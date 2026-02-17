# LARB Review: ritzunit

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

ritzunit is a self-discovering test framework that reads the binary's ELF symbol table at runtime to find and execute `test_*` functions with fork isolation, timing, filtering, and multiple output formats (human, JSON, JUnit). The core library (`src/`) is largely well-structured and uses modern `[[test]]` attribute syntax and `@` reference syntax consistently; however, multiple files contain legacy `&x` address-of expressions (should be `@x`) and `&&` / `||` logical operators (should be `and` / `or`), plus widespread use of the `c"..."` C-string prefix in application-level code. The legacy test scaffolding files (`runner_test.ritz`, `runner_test_v2.ritz`, `simple_test.ritz`) predate the `[[test]]` attribute and skip it entirely, making them non-compliant with current idioms.

## Statistics

- **Files Reviewed:** 18
- **Total SLOC:** ~1,850
- **Issues Found:** 22 (Critical: 0, Major: 16, Minor: 6)

---

## Critical Issues

None. The code does not contain patterns that would fail to compile under the new syntax, as the compiler currently still accepts both old and new forms.

---

## Major Issues

### M1 - `&x` address-of used instead of `@x` (multiple files)

The `@` operator is the finalized address-of syntax. `&x` expressions appear throughout the codebase:

**`src/reporter.ritz` line 37:**
```ritz
let ret: i64 = syscall3(SYS_IOCTL, fd as i64, TIOCGWINSZ, &winsize as i64)
```
Should be:
```ritz
let ret: i64 = syscall3(SYS_IOCTL, fd as i64, TIOCGWINSZ, @winsize as i64)
```

**`src/reporter.ritz` line 77:**
```ritz
prints_cstr(&buf[0])
```
Should be `@buf[0]`.

**`src/json_reporter.ritz` line 91, 158:**
```ritz
prints_cstr(&buf[0])
let r: *JsonTestResult = &g_json_results[i]
```

**`src/junit_reporter.ritz` lines 81, 139:**
```ritz
prints_cstr(&buf[0])
let r: *JunitTestResult = &g_junit_results[i]
```

**`test/runner_test.ritz` lines 80, 84, 94, 142:**
```ritz
if elf_init(&reader, data, size) != 0
if elf_parse_sections(&reader) != 0
let info: u8 = elf_get_symbol_info(&reader, i)
let entry: *TestEntry = &g_tests[i]
```

**`test/runner_test_v2.ritz` lines 49, 129, 134, 143, 199:**
```ritz
let n: i64 = sys_read(fd, &buf as *u8, 4096)
if elf_init(&reader, data, size) != 0
if elf_parse_sections(&reader) != 0
let info: u8 = elf_get_symbol_info(&reader, i)
let entry: *TestEntry = &g_tests[i]
```

**`inventory/src/lib.ritz` lines 41, 55, 67, 76, 88, 119:**
Multiple `&inv.items`, `&item.name`, `vec_get_ptr<Item>(&inv.items, i)`, etc.

**`inventory/test/test_inventory.ritz`:** Pervasive use of `&inv`, `&inv.items`, `&buf`, `&new_item.name[0]` throughout all test functions (approx. 40+ occurrences).

**`known_issues/test_vec_string.ritz` lines 13, 30, 31, 59-61, 102-119:**
```ritz
fn str_eq_ptr(v:&Vec<u8>, s: *u8) -> i32
let eq: i32 = str_eq_ptr(&v, "hello")
```

**`test/test_sizeof.ritz` lines 32-34:**
```ritz
let base: i64 = &item as i64
let name_addr: i64 = &item.name[0] as i64
let name_len_addr: i64 = &item.name_len as i64
```

### M2 - `&&` and `||` logical operators instead of `and` / `or`

**`src/runner.ritz` lines 56, 96 (WIFSIGNALED), 123 (detect_base_address), 375, 381, 621, 633, 638, 643:**

```ritz
# runner.ritz line 56:
let sig: i32 = status & 127
return (sig != 0 && sig != 127) as i32
```
(The `&&` here is a logical AND, not bitwise - should be `and`.)

```ritz
# runner.ritz line 375:
while i < reader.symtab_count && g_test_count < MAX_TESTS
```
Should be `and`.

```ritz
# runner.ritz line 381:
if name != null && is_test_name(name) != 0
```
Should be `and`.

```ritz
# runner.ritz line 621:
if force_color != 0 && no_color != 0
```
Should be `and`.

```ritz
# runner.ritz line 633:
if g_verbose != 0 && g_quiet != 0
```
Should be `and`.

```ritz
# runner.ritz line 638:
if g_json != 0 && g_junit != 0
```
Should be `and`.

```ritz
# runner.ritz line 643:
if g_json != 0 || g_junit != 0
```
Should be `or`.

**`src/filter.ritz` lines 45, 125:**
```ritz
return (c == ' ' || c == '\t') as i32
```
Should be `or`.

```ritz
if strview_get(pattern, pos) == ':' && strview_get(pattern, pos + 1) == ':'
```
Should be `and`.

**`src/filter.ritz` line 158:**
```ritz
if strview_starts_with_cstr(@trimmed, c"ignore") != 0 || strview_starts_with_cstr(@trimmed, c"skip") != 0
```
Should be `or`.

**`test/runner_test.ritz` line 96:**
```ritz
if elf_is_function(info) != 0 && elf_is_global(info) != 0
```
Should be `and`.

**`test/runner_test_v2.ritz` lines 64, 145:**
```ritz
if c >= '0' && c <= '9'
...
if elf_is_function(info) != 0 && elf_is_global(info) != 0
```
Both should be `and`.

**`src/runner.ritz` line 123 (detect_base_address):**
```ritz
if c >= '0' && c <= '9'
else if c >= 'a' && c <= 'f'
```
Should be `and`.

### M3 - `c"..."` C-string prefix in application-level code

The `c"..."` prefix should be replaced with `"...".as_cstr()` in application code. This is pervasive throughout the codebase. Examples (not exhaustive):

**`src/runner.ritz`:**
```ritz
let fd: i32 = sys_open(c"/proc/self/exe", O_RDONLY)
...
args_init(@parser, c"ritzunit", c"Unit test framework for Ritz")
args_flag(@parser, 'v', c"verbose", c"Show detailed output")
```

**`src/filter.ritz`:**
```ritz
var kw: StrView = strview_from_cstr(c"and")
var kw: StrView = strview_from_cstr(c"or")
```

**`src/json_reporter.ritz`:**
```ritz
fn status_pass() -> StrView
    return strview_from_cstr(c"pass")
```

**`src/junit_reporter.ritz`:**
```ritz
var msg: StrView = strview_from_cstr(c"Test assertion failed")
```

**`inventory/test/test_inventory.ritz`:** Approximately 40 `c"..."` literals used as item name arguments to inventory functions.

Note: `c"..."` in `sys_open` calls and FFI boundaries is explicitly permitted by the spec. However, the volume of `c"..."` usage in filter.ritz, json_reporter.ritz, and junit_reporter.ritz for constructing StrViews from string constants is non-idiomatic - those should just use `"..."` directly since string literals are `StrView` by default.

### M4 - Test functions in legacy files missing `[[test]]` attribute

**`test/runner_test.ritz` lines 170-189:** Four test functions (`test_simple_pass`, `test_addition`, `test_comparison`, `test_memory_ops`) lack the `[[test]]` attribute entirely. These files predate the attribute syntax and rely on the `test_` name prefix for discovery, which is the runtime discovery mechanism not the compile-time annotation.

**`test/runner_test_v2.ritz` lines 227-246:** Same issue - same four test functions without `[[test]]`.

**`test/simple_test.ritz` lines 9-31:** All four functions (`test_passes`, `test_also_passes`, `test_addition`, `test_comparison`) lack `[[test]]`.

### M5 - Inconsistent ownership modifier spacing

The spec shows `:&` (mutable borrow) and `:=` (move) with no space before the type. In `inventory/src/lib.ritz` and `inventory/test/test_inventory.ritz`, mutable borrow parameters use `:&` correctly:

```ritz
fn inventory_drop(inv:&Inventory)
fn inventory_add(inv:&Inventory, name: *u8, qty: i32) -> i32
```

However, `inventory/src/lib.ritz` line 85 mixes spacing styles - `inv: &Inventory` (space before `&`) vs `inv:&Inventory` (no space). Specifically:

```ritz
# lib.ritz line 85 - space before & (wrong):
fn inventory_count(inv: &Inventory, name: *u8) -> i32
# lib.ritz line 95 - same issue:
fn inventory_has(inv: &Inventory, name: *u8) -> i32
# lib.ritz line 101:
fn inventory_len(inv: &Inventory) -> i64
# lib.ritz line 119:
fn str_eq_ptr(v: &Vec<u8>, s: *u8) -> i32
# lib.ritz line 134:
fn inventory_total_quantity(inv: &Inventory) -> i32
```

These use `inv: &Inventory` (Rust-style space + ampersand) rather than `inv:&Inventory` (Ritz `:&` modifier). This is inconsistent with the other functions in the same file.

### M6 - `summary_merge` takes `*TestSummary` instead of borrow for `src`

**`src/types.ritz` line 73:**
```ritz
pub fn summary_merge(dest:&TestSummary, src: *TestSummary)
```

The `src` parameter is read-only and passed as a raw pointer. It should be a const borrow:
```ritz
pub fn summary_merge(dest:& TestSummary, src: TestSummary)
```
(or `src: @TestSummary` via reference). Using raw `*T` where a borrow is appropriate is flagged by the review spec.

---

## Minor Issues

### m1 - `runner_test.ritz` and `runner_test_v2.ritz` are development scaffolding, not proper tests

These files duplicate significant logic already present in `src/runner.ritz` and appear to be early prototypes. They should either be removed or refactored into proper tests using `[[test]]` and the full runner infrastructure.

### m2 - `simple_test.ritz` lacks file-level documentation header

`test/simple_test.ritz` has no module documentation comment explaining its purpose. All other source files begin with a header block.

### m3 - `test/test_sizeof.ritz` uses `&item` address-of expressions not wrapped in unsafe

```ritz
let base: i64 = &item as i64
let name_addr: i64 = &item.name[0] as i64
```
This is casting a stack address to `i64` for arithmetic - acceptable in a diagnostic tool but should be marked unsafe or placed in an `unsafe` block.

### m4 - Naming: `WIFEXITED`, `WEXITSTATUS`, `WIFSIGNALED`, `WTERMSIG` functions are SCREAMING_SNAKE_CASE

**`src/runner.ritz` lines 48-59:** These POSIX macro wrappers use SCREAMING_SNAKE_CASE, which the spec reserves for constants. They should be snake_case since they are functions:
```ritz
fn wif_exited(status: i32) -> i32
fn wex_itstatus(status: i32) -> i32
fn wif_signaled(status: i32) -> i32
fn wter_msig(status: i32) -> i32
```
(The naming is inherited from POSIX convention, so this is a judgment call, but per spec they are functions not constants.)

### m5 - `inventory/src/lib.ritz` not imported by test; inventory reimplements itself

`inventory/test/test_inventory.ritz` reimplements the entire inventory system inline rather than importing from `inventory/src/lib.ritz`. This means the actual library code is untested by these tests. The two implementations have different struct layouts (`Vec<u8>` name vs `[32]u8` fixed buffer). This is a structural issue worth noting.

### m6 - Code organization: imports appear mid-file in `src/runner.ritz`

**`src/runner.ritz` lines 402-406:** Import statements appear mid-file after function definitions:
```ritz
import src.reporter
import src.types
import src.filter
import src.json_reporter
import src.junit_reporter
```

Per the spec, imports should appear at the top of the file (section 2 of the organization checklist), before any function or type definitions.

---

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | ISSUE | `inv: &Inventory` (Rust-style space) in lib.ritz; `*TestSummary` where borrow should be used in types.ritz |
| Reference Types (@) | ISSUE | Pervasive `&x` address-of in runner_test.ritz, runner_test_v2.ritz, inventory files, reporter.ritz, json/junit reporters |
| Attributes ([[...]]) | ISSUE | runner_test.ritz, runner_test_v2.ritz, simple_test.ritz lack `[[test]]` on test functions |
| Logical Operators | ISSUE | `&&` and `\|\|` used throughout runner.ritz, filter.ritz, runner_test.ritz, runner_test_v2.ritz |
| String Types | ISSUE | `c"..."` prefix overused in application logic (filter, reporters, test data); should use plain `"..."` or `.as_cstr()` at FFI boundaries only |
| Error Handling | OK | No nested match pyramids; errors propagated via return codes as appropriate for this low-level project |
| Naming Conventions | ISSUE | POSIX macro wrappers (`WIFEXITED` etc.) are functions named as constants |
| Code Organization | ISSUE | Import block split across file in runner.ritz; legacy test scaffolding files mixed with proper test files |

---

## Files Needing Attention

| File | Issues | Priority |
|------|--------|----------|
| `src/runner.ritz` | `&&`/`\|\|` operators (7 occurrences), `c"..."` in CLI arg setup, mid-file imports | HIGH |
| `src/filter.ritz` | `&&`/`\|\|` operators (3 occurrences), `c"..."` for StrView construction | HIGH |
| `inventory/test/test_inventory.ritz` | 40+ `&x` address-of, `c"..."` for all string literals, reimplements library | HIGH |
| `inventory/src/lib.ritz` | Mixed `:&` vs `: &` modifier style, `&x` address-of in vec calls | HIGH |
| `test/runner_test.ritz` | No `[[test]]`, `&x` address-of, `&&` operators - legacy file | MEDIUM |
| `test/runner_test_v2.ritz` | No `[[test]]`, `&x` address-of, `&&` operators - legacy file | MEDIUM |
| `src/reporter.ritz` | `&winsize`, `&buf[0]` address-of | MEDIUM |
| `src/json_reporter.ritz` | `&buf[0]`, `&g_json_results[i]`, `c"..."` status strings | MEDIUM |
| `src/junit_reporter.ritz` | `&buf[0]`, `&g_junit_results[i]`, `c"..."` message strings | MEDIUM |
| `src/types.ritz` | `*TestSummary` parameter should be const borrow | LOW |
| `test/simple_test.ritz` | No `[[test]]`, no doc header | LOW |
| `test/test_sizeof.ritz` | `&item` address casts outside unsafe | LOW |

---

## Recommendations

Prioritized by severity:

1. **[HIGH] Replace all `&&` / `||` with `and` / `or`** across `src/runner.ritz`, `src/filter.ritz`, `test/runner_test.ritz`, and `test/runner_test_v2.ritz`. This is a systematic find-and-replace but requires care to distinguish bitwise `&` (correct) from logical `&&` (wrong).

2. **[HIGH] Replace `&x` address-of with `@x`** throughout the inventory files and the legacy runner tests. The src/ files have isolated occurrences; the inventory test file is the worst offender with 40+ instances.

3. **[HIGH] Audit `c"..."` usage** - retain it only at true FFI call sites (`sys_open`, `args_init` etc.); replace uses where a `StrView` is being constructed from a string constant with plain `"..."` literals.

4. **[MEDIUM] Add `[[test]]` attributes** to all test functions in `runner_test.ritz`, `runner_test_v2.ritz`, and `simple_test.ritz`, or (preferred) retire these legacy scaffolding files and migrate their tests into the proper `[[test]]`-annotated style.

5. **[MEDIUM] Fix `:&` modifier consistency** in `inventory/src/lib.ritz` - all mutable borrow parameters should use `fn foo(x:& T)` not `fn foo(x: &T)`.

6. **[LOW] Move imports to top of `src/runner.ritz`** (before function definitions).

7. **[LOW] Rename POSIX macro wrappers** from SCREAMING_SNAKE to snake_case.

8. **[LOW] Have `inventory/test/test_inventory.ritz` import from `inventory/src/lib.ritz`** rather than re-implementing the inventory system with a different struct layout.
