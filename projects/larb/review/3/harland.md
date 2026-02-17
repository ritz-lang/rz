# LARB Review: Harland Microkernel

**Reviewed:** 2026-02-17
**Reviewer:** Claude (LARB Agent)
**Status:** NEEDS WORK

## Summary

Harland is a well-structured x86-64 microkernel with clear module boundaries across memory management, IPC, capabilities, filesystems, networking, and device drivers. The codebase follows most Ritz idioms correctly (ownership modifiers, `@` reference syntax, `[[packed]]` attributes, naming conventions), but has two systematic issues: pervasive use of the old `c"..."` string prefix that should be migrated to `"..."` (StrView) or `"...".as_cstr()` for FFI paths, and recurring use of `&&`/`||` logical operator symbols instead of the `and`/`or` keywords. These issues span multiple files and need a sweep to bring the codebase into compliance.

## Statistics

- **Files Reviewed:** 53 (across kernel/src, boot/src; docs/old_designs excluded from compliance scoring)
- **Total SLOC:** ~20,100 (kernel/src ~17,400; boot/src ~2,700)
- **Issues Found:** 17 (Critical: 0, Major: 14, Minor: 3)

## Critical Issues

None. Raw pointers (`*T`) are used extensively and appropriately throughout the kernel for hardware interfacing, page table manipulation, and low-level memory management. All `@` reference operations are correctly used for taking addresses of stack variables and struct fields. No Rust-style `&T`/`&mut T` parameters found anywhere.

## Major Issues

### 1. `c"..."` String Prefix - Widespread Usage (MAJOR)

**Files affected:** 9 kernel source files + 1 boot file
**Total occurrences:** ~242 in active source (excluding docs/old_designs)

The old `c"..."` prefix for null-terminated strings is used pervasively. Per the spec, string literals default to `StrView` (`"..."`), and FFI/null-terminated strings should use `"...".as_cstr()`.

The instructions acknowledge that `c"..."` may be acceptable in low-level kernel code for FFI, but the current usage goes beyond strict FFI contexts - it is used for all serial logging, string constants returned from functions, and embedded path strings.

Worst offenders:
- `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/arch/x86_64/interrupts.ritz` - 89 occurrences (all serial print calls, exception name returns)
- `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/main.ritz` - 70 occurrences (klog calls, boot status messages, IPC test strings)
- `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/arch/x86_64/idt.ritz` - 22 occurrences (exception name string returns)
- `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/fs/initramfs.ritz` - 20 occurrences (filesystem path literals)
- `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/cap/types.ritz` - 12 occurrences (capability type name returns)

Example of the pattern found:
```ritz
# CURRENT (wrong for logging/string returns):
klog(c"Harland kernel starting...\n")
return c"Divide Error"
serial_print(c"\n!!! EXCEPTION !!!\n")

# CORRECT:
klog("Harland kernel starting...\n")
return "Divide Error"
serial_print("!!! EXCEPTION !!!\n")
# (or .as_cstr() where the called function truly requires *u8)
```

Note: the `serial_print(s: *u8)` function is explicitly labeled "Legacy: null-terminated C string" in `serial.ritz`. The preferred path is `prints(s: StrView)` which accepts the modern `"..."` literals directly. Most call sites passing `c"..."` to `serial_print` should migrate to `prints("...")`.

### 2. `&&` and `||` Logical Operators (MAJOR)

**Files affected:** 5 files
**Total occurrences:** 12

The spec requires `and`/`or` keywords. Symbol operators `&&` and `||` are used in:

- `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/main.ritz` (3 occurrences):
  - Line 1730: `while ap_started[apic_id as i32] == 0 && timeout > 0`
  - Line 2008: `while i < 15 && *src != 0`
  - Line 3585: `if old_task_idx != 0xFFFFFFFF && old_task_idx != (*cpu).idle_task`

- `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/mm/vmm.ritz` (3 occurrences):
  - Lines 228, 251, 274: `if need_user != 0 && (pml4_entry & PTE_USER) == 0`

- `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/arch/x86_64/syscall.ritz` (1 occurrence):
  - Line 271: `if fd == 1 || fd == 2`

- `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/arch/x86_64/apic.ritz` (1 occurrence):
  - Line 601: `while ap_started[apic_id as i32] == 0 && timeout > 0`

- `/home/aaron/dev/ritz-lang/rz/projects/harland/boot/src/main.ritz` (4 occurrences):
  - Lines 493, 1015, 1135, 1311

All instances should use `and`/`or`:
```ritz
# WRONG:
while ap_started[apic_id as i32] == 0 && timeout > 0

# CORRECT:
while ap_started[apic_id as i32] == 0 and timeout > 0
```

### 3. No `impl` Blocks (MAJOR - Architectural)

All methods are defined as free functions. No `impl` blocks are used anywhere in the project. While the deprecated `fn Type.method()` syntax is also not used (which is correct), the preferred modern idiom is `impl` blocks for organizing type-related functions. This is a significant structural gap across all 53 files.

Example from `cap/types.ritz`:
```ritz
# CURRENT (acceptable but not preferred):
pub fn cap_handle_init(index: u32, generation: u32) -> CapHandle
pub fn cap_handle_invalid() -> CapHandle
pub fn cap_handle_is_valid(handle: CapHandle) -> bool

# PREFERRED:
impl CapHandle
    pub fn init(index: u32, generation: u32) -> CapHandle
    pub fn invalid() -> CapHandle
    pub fn is_valid(self: CapHandle) -> bool
```

Given that this is kernel code with a large number of types and associated functions, migrating to `impl` blocks would greatly improve readability and discoverability.

### 4. No `defer` for Resource Cleanup (MAJOR)

No `defer` statements are found anywhere in the kernel. Functions that allocate resources use early-return patterns, which means cleanup can be missed in error paths. Example in `channel_send` in `ipc/channel.ritz`:

```ritz
# Current: if kalloc succeeds but queue operations fail, no cleanup path
let entry: *QueuedMessage = kalloc(4096) as *QueuedMessage
if entry == 0 as *QueuedMessage
    return -5

# Preferred idiom (if error handling is added):
let entry: *QueuedMessage = kalloc(4096) as *QueuedMessage
if entry == 0 as *QueuedMessage
    return -5
defer kfree(entry as *u8)
```

For kernel code the impact is limited since most functions are infallible after initial checks, but `defer` would prevent future bugs during maintenance.

### 5. No `Result<T, E>` Error Handling (MAJOR)

All functions return integer error codes (`i32`, `i64`) instead of `Result<T, E>`. While this is understandable in kernel code given the lack of allocator guarantees in early boot, the `Result` type is available and would make error propagation explicit and composable. The `?` operator would eliminate many redundant error check patterns like:

```ritz
# Current (repeated ~50+ times):
let result: i32 = vmm_map_page(virt, phys, PTE_WRITABLE)
if result != 0
    pmm_free_page(phys)
    return -1

# Preferred:
vmm_map_page(virt, phys, PTE_WRITABLE)?
```

This is a pervasive pattern across `mm/heap.ritz`, `mm/vmm.ritz`, `fs/` subsystem, and `drivers/`.

### 6. Code Duplication in `process.ritz` (MAJOR)

`/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/process.ritz` redefines `outb`, `inb`, `serial_write_byte`, `serial_print`, `serial_print_hex`, `prints`, and `StrView` locally with a comment "Serial Output (duplicate for now - TODO: import from main)". The module should import these from `serial` and `io` as all other kernel modules do.

## Minor Issues

### 7. Missing Module Documentation in Some Files (MINOR)

Most files have good header comments (e.g., `serial.ritz`, `channel.ritz`, `heap.ritz`). A few files are lighter:
- `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/cap/table.ritz` - functional but sparse header
- `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/ipc/message.ritz` - struct doc could be expanded

### 8. Section Organization Inconsistency (MINOR)

Most files use `# ===...===` section separators cleanly. However, `process.ritz` interleaves type definitions, constants, and function implementations without following the canonical ordering (imports, constants, types, impl, functions, tests).

### 9. Magic Numbers Without Constants (MINOR)

Some values in `main.ritz` use magic numbers that could be named constants:
- `4096` used as allocation size in several places (should be `PAGE_SIZE`)
- `0xFFFFFFFF` used for "invalid index" in task code (could be `INVALID_TASK_IDX`)
- Boot status spinners use raw bytes for progress display

## Compliance Matrix

| Category | Status | Notes |
|----------|--------|-------|
| Ownership Modifiers | OK | No Rust-style `&T`/`&mut T` found; `x: T`, `:&`, `:=` used correctly |
| Reference Types (@) | OK | `@x`, `@T`, `@&T` used correctly throughout; `*T` confined to raw pointer contexts |
| Attributes ([[...]]) | OK | `[[packed]]`, `[[test]]` (none present) used correctly; no old `@packed` found |
| Logical Operators | ISSUE | 12 occurrences of `&&`/`\|\|` across 5 files; should be `and`/`or` |
| String Types | ISSUE | 242 occurrences of `c"..."` in active source; most should be `"..."` with migration to `prints()` |
| Error Handling | ISSUE | No `Result<T,E>` or `?` operator; integer return codes used exclusively |
| Naming Conventions | OK | snake_case functions, PascalCase types, SCREAMING_SNAKE_CASE constants - all consistent |
| Code Organization | ISSUE | No `impl` blocks anywhere; `process.ritz` has code duplication; `defer` never used |

## Files Needing Attention

1. `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/arch/x86_64/interrupts.ritz` - 89 `c"..."` occurrences
2. `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/main.ritz` - 70 `c"..."` + 3 `&&` occurrences
3. `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/arch/x86_64/idt.ritz` - 22 `c"..."` occurrences
4. `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/fs/initramfs.ritz` - 20 `c"..."` occurrences
5. `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/cap/types.ritz` - 12 `c"..."` occurrences
6. `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/mm/vmm.ritz` - 3 `&&` occurrences
7. `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/arch/x86_64/syscall.ritz` - 1 `||` occurrence
8. `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/arch/x86_64/apic.ritz` - 1 `&&` occurrence
9. `/home/aaron/dev/ritz-lang/rz/projects/harland/kernel/src/process.ritz` - duplicated serial/IO code
10. `/home/aaron/dev/ritz-lang/rz/projects/harland/boot/src/main.ritz` - 4 `||` occurrences + 1 `c"..."`

## Recommendations

Prioritized by impact:

1. **(Quick win) Fix `&&`/`||` operators** - Only 12 occurrences in 5 files. Simple mechanical substitution: `&&` -> `and`, `||` -> `or`. Start with `syscall.ritz` and `apic.ritz` (one each), then `vmm.ritz` (3), then `main.ritz` (3), then `boot/main.ritz` (4).

2. **(Sweep) Migrate `c"..."` in logging paths** - The bulk of the `c"..."` usage is passing strings to `serial_print(s: *u8)`. Since `prints(s: StrView)` already exists and accepts `"..."` literals directly, most call sites can be updated as: `serial_print(c"foo")` -> `prints("foo")`. The `c"..."` form may remain in the handful of places that genuinely need `*u8` (e.g., passing to `klog(s: *u8)` which could also be updated to accept `StrView`).

3. **(Fix) Remove code duplication in `process.ritz`** - Replace the locally-defined serial/IO functions with `import serial { ... }` and `import io { ... }` to match the rest of the codebase.

4. **(Architectural) Introduce `impl` blocks** - Start with the most obvious candidates: `CapHandle` and `CapEntry` in `cap/types.ritz`, `ChannelEndpoint` in `ipc/channel.ritz`, and `SimpleFramebuffer` in `drivers/display/framebuffer.ritz`. This can be incremental.

5. **(Long-term) Consider `Result<T,E>` for subsystems** - The filesystem (`fs/`) and IPC subsystems are the most natural candidates for Result-based error handling, since they have well-defined error conditions. The hardware-level (`io.ritz`, `mm/pmm.ritz`) code is fine with integer returns.
