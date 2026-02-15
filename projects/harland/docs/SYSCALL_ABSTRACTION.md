# Syscall Abstraction Layer Design

> **Goal**: Ritz programs run unchanged on Linux, Harland, and future platforms

## Overview

The syscall abstraction separates the **API** (what applications call) from the **backend** (platform-specific implementation). This allows:

1. **Code portability**: Same Ritz code runs on Linux and Harland
2. **Testing on host**: Develop kernel services using Linux, deploy on Harland
3. **Gradual migration**: Apps start on Linux, move to Harland without rewrite

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Application Code                              │
│                                                                      │
│   prints("Hello\n")                                                  │
│   let fd = open("/etc/hosts", O_RDONLY)                             │
│   let n = read(fd, buf, 1024)                                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        ritzlib.sys (Abstract API)                    │
│                                                                      │
│   pub fn write(fd: i32, buf: *u8, len: i64) -> i64                  │
│   pub fn read(fd: i32, buf: *u8, len: i64) -> i64                   │
│   pub fn open(path: *u8, flags: i32) -> i32                         │
│   pub fn close(fd: i32) -> i32                                      │
│   pub fn exit(code: i32) -> !                                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ sys/linux.ritz   │ │ sys/harland.ritz │ │ sys/macos.ritz   │
│                  │ │                  │ │                  │
│ Linux x86_64     │ │ Harland syscalls │ │ (future)         │
│ syscall ABI      │ │ via IPC/ring buf │ │                  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

## Implementation Strategy

### Option 1: Compile-time Selection (Recommended)

The compiler selects the backend based on `--target`:

```bash
# For Linux (current default)
ritz build --target x86_64-linux src/main.ritz

# For Harland (freestanding)
ritz build --target x86_64-harland src/main.ritz
```

**ritzlib/sys.ritz** becomes a facade:

```ritz
# ritzlib/sys.ritz - Platform-agnostic syscall interface

# Import the appropriate backend based on target
# (This is pseudo-code - actual implementation TBD)
@cfg(target_os = "linux")
import ritzlib.sys.linux as backend

@cfg(target_os = "harland")
import ritzlib.sys.harland as backend

# Export the common API
pub fn write(fd: i32, buf: *u8, len: i64) -> i64
    return backend.write(fd, buf, len)

pub fn read(fd: i32, buf: *u8, len: i64) -> i64
    return backend.read(fd, buf, len)

pub fn open(path: *u8, flags: i32) -> i32
    return backend.open(path, flags)

pub fn close(fd: i32) -> i32
    return backend.close(fd)

pub fn exit(code: i32) -> !
    backend.exit(code)
```

### Option 2: Runtime Dispatch (Not Recommended)

Function pointers set at startup. Higher overhead, more complexity.

### Option 3: Inline Backend (Current State)

Each backend module is self-contained. Applications import the specific one they need. Simple but not portable.

## Backend: Linux x86_64

**File**: `ritzlib/sys/linux.ritz`

Uses the Linux syscall ABI directly:

```ritz
# Linux syscall numbers
const SYS_READ: i64 = 0
const SYS_WRITE: i64 = 1
const SYS_OPEN: i64 = 2
const SYS_CLOSE: i64 = 3
const SYS_EXIT: i64 = 60
# ... etc

extern fn syscall3(n: i64, a1: i64, a2: i64, a3: i64) -> i64

pub fn write(fd: i32, buf: *u8, len: i64) -> i64
    return syscall3(SYS_WRITE, fd as i64, buf as i64, len)

pub fn read(fd: i32, buf: *u8, len: i64) -> i64
    return syscall3(SYS_READ, fd as i64, buf as i64, len)

pub fn exit(code: i32) -> !
    syscall1(SYS_EXIT, code as i64)
    # Never returns
```

## Backend: Harland

**File**: `ritzlib/sys/harland.ritz` or `kernel/sys/harland.ritz`

For user-space programs on Harland, syscalls use the kernel's IPC mechanism:

```ritz
# Harland syscall interface
# Ring 3 → Ring 0 via SYSCALL instruction
# Returns to ring 3 after kernel handles request

pub fn write(fd: i32, buf: *u8, len: i64) -> i64
    # Harland uses SYSCALL instruction similar to Linux
    # but with its own syscall number ABI
    return harland_syscall3(HARLAND_SYS_WRITE, fd as i64, buf as i64, len)

pub fn read(fd: i32, buf: *u8, len: i64) -> i64
    return harland_syscall3(HARLAND_SYS_READ, fd as i64, buf as i64, len)

# Assembly for Harland syscall ABI
fn harland_syscall3(n: i64, a1: i64, a2: i64, a3: i64) -> i64
    var result: i64 = 0
    asm x86_64:
        movq {n}, %rax
        movq {a1}, %rdi
        movq {a2}, %rsi
        movq {a3}, %rdx
        syscall
        movq %rax, {result}
    return result
```

## Backend: Kernel (Freestanding)

**For kernel code itself** (not user-space), there are no syscalls - the kernel IS the syscall handler. Instead:

```ritz
# kernel/sys/kernel.ritz - Kernel-internal "syscalls"

# These map directly to kernel functions, no ring transition

pub fn write(fd: i32, buf: *u8, len: i64) -> i64
    # fd 1 = serial console (stdout equivalent)
    if fd == 1
        serial_write(buf, len)
        return len
    # Other fds would go to VFS
    return -1

pub fn read(fd: i32, buf: *u8, len: i64) -> i64
    # Kernel read from VFS or device
    return vfs_read(fd, buf, len)

pub fn exit(code: i32) -> !
    # Kernel panic or halt
    panic("exit() called in kernel")
```

## StrView Integration

The API should use StrView for string parameters:

```ritz
# Higher-level API with StrView
pub fn prints(s: StrView) -> i64
    return write(1, s.ptr, s.len)

pub fn eprints(s: StrView) -> i64
    return write(2, s.ptr, s.len)

# Usage - clean!
prints("Hello, World!\n")  # StrView literal with compile-time length
```

## Phased Implementation

### Phase 1: Kernel Basics (Current)

- [x] `StrView` struct in kernel
- [x] `serial_write(buf, len)`
- [x] `prints(s: StrView)`
- [ ] Rename to match ritzlib API conventions

### Phase 2: Factor Out sys Module

- [ ] Create `kernel/sys/` directory
- [ ] Move serial I/O to `kernel/sys/io.ritz`
- [ ] Create `kernel/sys/strview.ritz` (or inline in io)

### Phase 3: Harland Syscall ABI

- [ ] Design Harland syscall numbers
- [ ] Implement SYSCALL/SYSRET in kernel
- [ ] Create `ritzlib/sys/harland.ritz` for user-space

### Phase 4: Conditional Compilation

- [ ] Add `@cfg(target_os = "...")` attribute support to ritz0
- [ ] Create `ritzlib/sys.ritz` facade
- [ ] Test same code on Linux and Harland

## Harland Syscall Numbers (Draft)

```ritz
# Core I/O
const HARLAND_SYS_READ: i64 = 0
const HARLAND_SYS_WRITE: i64 = 1
const HARLAND_SYS_OPEN: i64 = 2
const HARLAND_SYS_CLOSE: i64 = 3

# Memory
const HARLAND_SYS_MMAP: i64 = 10
const HARLAND_SYS_MUNMAP: i64 = 11
const HARLAND_SYS_MPROTECT: i64 = 12

# Process
const HARLAND_SYS_EXIT: i64 = 20
const HARLAND_SYS_SPAWN: i64 = 21  # Not fork - spawn new process
const HARLAND_SYS_WAIT: i64 = 22

# IPC (Harland-specific)
const HARLAND_SYS_IPC_SEND: i64 = 30
const HARLAND_SYS_IPC_RECV: i64 = 31
const HARLAND_SYS_IPC_CALL: i64 = 32  # Send + recv (synchronous RPC)

# Capability
const HARLAND_SYS_CAP_GRANT: i64 = 40
const HARLAND_SYS_CAP_REVOKE: i64 = 41
```

## File Structure (Proposed)

```
ritzlib/
├── sys.ritz                    # Facade - exports platform-agnostic API
├── sys/
│   ├── linux.ritz              # Linux x86_64 backend
│   ├── harland.ritz            # Harland user-space backend (future)
│   └── types.ritz              # Shared types (StrView, etc.)
└── io.ritz                     # Higher-level I/O (uses sys)

kernel/
├── src/
│   └── main.ritz               # Main kernel with inline StrView/serial
└── sys/                        # (Future) kernel-internal modules
    ├── io.ritz
    └── strview.ritz
```

## Open Questions

1. **Conditional compilation syntax**: `@cfg(...)` or `[[cfg(...)]]`?
2. **Error handling**: Result<T, E> vs raw i64 with negative = error?
3. **Async I/O**: How does io_uring integrate with abstraction?
4. **Harland IPC**: Ring buffer vs message passing for syscall args?

---

*This document guides the syscall abstraction implementation. Update as decisions are made.*
