# POSIX Compatibility Strategy for Harland

> **Guiding Principle**: POSIX compatibility where it serves us, Ritz-native design where it doesn't.

---

## Overview

POSIX (Portable Operating System Interface) defines a standard API for Unix-like operating systems. While Harland is a microkernel designed for Ritz, strategic POSIX compatibility enables:

1. **Ecosystem Access**: Run existing tools during development
2. **Developer Familiarity**: Lower learning curve for new contributors
3. **Testing**: Validate Ritz programs on Linux before deploying to Harland
4. **Portability**: Ritz programs work across platforms via `ritzlib.sys`

However, we reject blind POSIX compliance. Where POSIX design decisions are outdated, unsafe, or conflict with Ritz's values, we design something better.

---

## Compatibility Tiers

### Tier 1: Full Compatibility (Stable API)

These interfaces match POSIX semantics exactly. Code using these works identically on Linux and Harland.

| Category | Functions | Status |
|----------|-----------|--------|
| **Basic I/O** | `read`, `write`, `open`, `close` | Planned |
| **File Info** | `stat`, `fstat`, `lstat` | Planned |
| **Directory** | `opendir`, `readdir`, `closedir` | Planned |
| **Memory** | `mmap`, `munmap`, `mprotect` | Planned |
| **Process** | `getpid`, `exit`, `_exit` | Planned |
| **Time** | `clock_gettime`, `nanosleep` | Planned |

### Tier 2: Semantic Compatibility (Same behavior, different mechanism)

These provide POSIX-like functionality but may use different underlying mechanisms.

| Category | POSIX | Harland | Notes |
|----------|-------|---------|-------|
| **Process Creation** | `fork()` | `spawn()` | No fork - cleaner design |
| **Exec** | `execve()` | Part of `spawn()` | Combined spawn+exec |
| **Pipes** | `pipe()` | `channel_create()` | IPC channels instead |
| **Signals** | `signal()`, `kill()` | IPC messages | No async signals |
| **Wait** | `waitpid()` | `process_wait()` | Capability-based |

### Tier 3: Intentionally Different (Ritz-native)

These areas intentionally diverge from POSIX to provide better safety, performance, or ergonomics.

| Area | POSIX Approach | Harland Approach | Rationale |
|------|----------------|------------------|-----------|
| **Error Handling** | errno global | `Result<T, E>` return | Thread-safe, explicit |
| **Strings** | NUL-terminated | Length-prefixed `StrView` | No buffer overflows |
| **Ownership** | Implicit | Explicit borrows | Compile-time safety |
| **Capabilities** | uid/gid bits | Object capabilities | Fine-grained control |
| **IPC** | Varied (pipes, sockets, SysV) | Unified channels | Simpler, faster |
| **Async I/O** | Multiple models | Unified async | io_uring-inspired |

---

## File Descriptor Abstraction

### The Problem

POSIX file descriptors are integers. This causes:
- Type confusion (is fd 3 a file, socket, or pipe?)
- No compile-time safety
- No ownership semantics

### Harland Solution: Typed Handles

```ritz
# Typed handles - can't accidentally use a Socket as a File
pub struct FileHandle { fd: i32 }
pub struct SocketHandle { fd: i32 }
pub struct ChannelHandle { fd: i32 }

# Each has its own methods
impl FileHandle
    fn read(self:&, buf: []u8) -> Result<usize, IoError>
    fn write(self:&, data: StrView) -> Result<usize, IoError>
    fn seek(self:&, offset: i64, whence: SeekFrom) -> Result<i64, IoError>
    fn close(self:=)  # Consumes the handle - can't use after close

impl SocketHandle
    fn recv(self:&, buf: []u8) -> Result<usize, IoError>
    fn send(self:&, data: StrView) -> Result<usize, IoError>
    fn connect(self:&, addr: SocketAddr) -> Result<(), IoError>
    # No seek - type system prevents it!
```

### Compatibility Layer

For POSIX compatibility, we provide raw fd functions:

```ritz
# ritzlib/sys/compat.ritz - Raw POSIX-style functions

pub fn read(fd: i32, buf: *u8, count: usize) -> i64
pub fn write(fd: i32, buf: *u8, count: usize) -> i64
pub fn close(fd: i32) -> i32

# But we recommend the typed API
pub fn file_open(path: StrView, flags: OpenFlags) -> Result<FileHandle, IoError>
```

---

## Error Handling Strategy

### POSIX: Global errno

```c
// C/POSIX style
int fd = open("/tmp/foo", O_RDONLY);
if (fd < 0) {
    perror("open failed");  // Reads global errno
}
```

**Problems:**
- Thread-unsafe (without thread-local storage)
- Easy to forget to check
- Errno can be clobbered between calls

### Harland: Result Type

```ritz
# Ritz/Harland style
match file_open("/tmp/foo", OpenFlags.ReadOnly)
    Ok(handle) => process(handle)
    Err(e) =>
        eprints("open failed: ")
        eprints(e.message())
        eprints("\n")
```

**Benefits:**
- Compile-time enforcement
- Thread-safe
- Clear ownership of error

### Syscall Layer Translation

```ritz
# Internal: syscalls return i64 (negative = error)
fn sys_open(path: *u8, path_len: u64, flags: u32) -> i64

# Public API wraps in Result
pub fn file_open(path: StrView, flags: OpenFlags) -> Result<FileHandle, IoError>
    let result = sys_open(path.ptr, path.len as u64, flags.bits())
    if result < 0
        Err(IoError.from_errno(-result as i32))
    else
        Ok(FileHandle { fd: result as i32 })
```

---

## Process Model

### POSIX: fork() + exec()

```c
pid_t pid = fork();  // Clone entire process
if (pid == 0) {
    // Child
    execve("/bin/ls", args, env);  // Replace with new program
} else {
    // Parent
    waitpid(pid, &status, 0);
}
```

**Problems:**
- `fork()` is expensive (copy-on-write helps but still)
- Fork + exec is a two-step dance
- Inherited file descriptors cause security issues
- No explicit capability passing

### Harland: spawn()

```ritz
# Create new process with explicit capabilities
let child = process_spawn(SpawnConfig {
    program: "/bin/ls",
    args: ["ls", "-la"],
    env: inherit_env(),
    stdin: channel_create().recv,   # Explicit stdin
    stdout: my_channel.send,        # Explicit stdout
    stderr: inherit_stderr(),
    capabilities: [
        cap_derive(fs_cap, CAP_READ)  # Read-only filesystem
    ]
})?

# Wait for completion
let status = process_wait(child)?
```

**Benefits:**
- Single operation (no fork+exec race)
- Explicit capability transfer
- No accidental fd inheritance
- Cleaner semantics

### POSIX Compatibility Layer

```ritz
# For porting POSIX code - not recommended for new code
pub fn fork() -> i64
    # Emulated via spawn() + shared memory
    # Or: return -ENOSYS and require spawn()
    return -38  # ENOSYS - not implemented

pub fn execve(path: *u8, argv: **u8, envp: **u8) -> i32
    # Only valid immediately after fork() in child
    # Otherwise: -ENOSYS
```

---

## Signal Handling

### POSIX: Async Signals

```c
signal(SIGINT, handler);  // Register handler
// ... handler can interrupt any code at any time ...
void handler(int sig) {
    // Very limited safe operations (async-signal-safe)
}
```

**Problems:**
- Interrupts at arbitrary points
- Race conditions everywhere
- Very few functions are async-signal-safe
- Complex interaction with threads

### Harland: Event Messages

```ritz
# Create an event channel
let events = event_channel_create()?

# Register interest
event_subscribe(events, EventKind.Interrupt)?  # Ctrl+C
event_subscribe(events, EventKind.ChildExit)?  # Child processes
event_subscribe(events, EventKind.Timer)?      # Periodic timer

# Poll for events - happens at controlled points
loop
    match event_recv(events, timeout: 100)
        Ok(Event.Interrupt) =>
            prints("Caught Ctrl+C, cleaning up...\n")
            break
        Ok(Event.ChildExit(pid, status)) =>
            prints("Child exited\n")
        Ok(Event.Timer) =>
            do_periodic_work()
        Err(IoError.WouldBlock) =>
            continue  # No events, continue work
        Err(e) =>
            return Err(e)
```

**Benefits:**
- Events arrive at controlled points (no arbitrary interruption)
- Full language features available in handlers
- No race conditions
- Simpler mental model

---

## String Handling

### POSIX: NUL-terminated C strings

```c
char *s = "hello";  // 5 chars + NUL
strlen(s);          // O(n) scan to find NUL
strncpy(dst, src, n);  // Confusing semantics
```

**Problems:**
- O(n) length calculation
- Buffer overflow vulnerabilities
- NUL can't appear in string content

### Harland: Length-prefixed StrView

```ritz
# String literals are StrView
let s: StrView = "hello"  # ptr + len, no NUL needed

# Length is O(1)
s.len  # => 5

# Safe slicing
let sub = s.slice(0, 3)  # "hel" - bounds checked

# Can contain any bytes including NUL
let binary: StrView = "foo\x00bar"  # len = 7, works fine
```

### Syscall Interface

```ritz
# Syscalls take pointer + length (no NUL dependency)
fn sys_write(fd: i32, buf: *u8, len: u64) -> i64
fn sys_open(path: *u8, path_len: u64, flags: u32) -> i64

# StrView integrates naturally
pub fn prints(s: StrView) -> i64
    sys_write(1, s.ptr, s.len as u64)
```

---

## Implementation Phases

### Phase 1: Core Syscalls (Current Focus)

**Goal**: Enough POSIX for basic I/O and process management.

```ritz
# File I/O
sys_open(path, len, flags) -> i64
sys_close(fd) -> i32
sys_read(fd, buf, len) -> i64
sys_write(fd, buf, len) -> i64
sys_lseek(fd, offset, whence) -> i64
sys_fstat(fd, stat_buf) -> i32

# Process
sys_exit(code) -> !
sys_getpid() -> i32
sys_spawn(config) -> i64

# Memory
sys_mmap(addr, len, prot, flags, fd, offset) -> *u8
sys_munmap(addr, len) -> i32
```

### Phase 2: Filesystem Semantics

**Goal**: POSIX path semantics, directory operations.

```ritz
# Directory operations
sys_opendir(path, len) -> i64
sys_readdir(dirfd, entry_buf) -> i32
sys_closedir(dirfd) -> i32
sys_mkdir(path, len, mode) -> i32
sys_rmdir(path, len) -> i32

# Path operations
sys_getcwd(buf, len) -> i32
sys_chdir(path, len) -> i32
sys_unlink(path, len) -> i32
sys_rename(old, old_len, new, new_len) -> i32
sys_stat(path, len, stat_buf) -> i32
sys_lstat(path, len, stat_buf) -> i32
```

### Phase 3: Process Management

**Goal**: Full process lifecycle, waiting, environment.

```ritz
sys_spawn(config) -> i64
sys_wait(pid, status, options) -> i64
sys_getenv(name, len, buf, buf_len) -> i32
sys_setenv(name, len, value, val_len) -> i32
```

### Phase 4: IPC and Events

**Goal**: Replace signals with event channels, add pipes.

```ritz
sys_channel_create() -> ChannelPair
sys_event_subscribe(channel, events) -> i32
sys_event_recv(channel, buf, timeout) -> i64
sys_pipe(fds: *i32) -> i32  # POSIX compat - creates channel pair
```

### Phase 5: Compatibility Shims

**Goal**: Run more POSIX programs with minimal changes.

- `fork()` emulation (if feasible) or clear ENOSYS
- Signal emulation via events
- pthreads over Harland threads
- Socket API over IPC channels

---

## Testing Strategy

### Cross-Platform Test Suite

Tests should pass on both Linux and Harland:

```ritz
[[test]]
fn test_file_roundtrip() -> i32
    let handle = file_open("/tmp/test.txt", OpenFlags.Create | OpenFlags.Write)?
    file_write(handle, "hello world")?
    file_close(handle)

    let handle = file_open("/tmp/test.txt", OpenFlags.Read)?
    let buf = [0u8; 256]
    let n = file_read(handle:&, buf)?
    assert buf[0..n] == "hello world"
    file_close(handle)
    0
```

### Platform-Specific Tests

```ritz
[[test]]
[[cfg(target_os = "harland")]]
fn test_capability_derivation() -> i32
    # Harland-specific capability test
    ...
```

### Compatibility Validation

Maintain a list of POSIX behaviors we intentionally differ from:

| Behavior | POSIX | Harland | Test |
|----------|-------|---------|------|
| fork() | Clones process | Returns ENOSYS | `test_fork_not_supported` |
| errno | Global variable | Not used | `test_no_errno_global` |
| signals | Async delivery | Event channel | `test_sigint_via_events` |

---

## Migration Guide for POSIX Code

### Simple Cases (Direct Mapping)

```ritz
# POSIX C:
# int fd = open("/etc/hosts", O_RDONLY);
# read(fd, buf, sizeof(buf));
# close(fd);

# Ritz (POSIX compat layer):
let fd = sys_open(c"/etc/hosts", 0)
sys_read(fd, buf.ptr, buf.len as u64)
sys_close(fd)

# Ritz (idiomatic):
let handle = file_open("/etc/hosts", OpenFlags.Read)?
file_read(handle:&, buf)?
# handle closed automatically at scope end via Drop
```

### fork() Replacement

```ritz
# POSIX C:
# pid_t pid = fork();
# if (pid == 0) {
#     execve("/bin/ls", args, env);
# } else {
#     waitpid(pid, &status, 0);
# }

# Ritz:
let child = process_spawn(SpawnConfig {
    program: "/bin/ls",
    args: args,
    env: inherit_env()
})?
let status = process_wait(child)?
```

### Signal Handler Replacement

```ritz
# POSIX C:
# void handler(int sig) { cleanup(); exit(0); }
# signal(SIGINT, handler);

# Ritz:
let events = event_channel_create()?
event_subscribe(events, EventKind.Interrupt)?

# In main loop:
match event_try_recv(events)
    Ok(Event.Interrupt) =>
        cleanup()
        return 0
    _ => ()
```

---

## Non-Goals

We explicitly do NOT aim to support:

1. **Complete POSIX compliance certification** - Too much legacy cruft
2. **fork() semantics** - Fundamentally incompatible with our design
3. **Async signals** - Unsafe by design
4. **POSIX threads (pthreads)** - Will have native threading API
5. **System V IPC** - Obsolete, use channels
6. **uid/gid permission model** - Use capabilities instead

---

## References

- [POSIX.1-2024 Specification](https://pubs.opengroup.org/onlinepubs/9799919799/)
- [Harland Syscall Abstraction](./SYSCALL_ABSTRACTION.md)
- [Harland Kernel Contract](./KERNEL_CONTRACT.md)
- [seL4 Capability Model](https://sel4.systems/)
- [Fuchsia Zircon Syscalls](https://fuchsia.dev/fuchsia-src/reference/syscalls)

---

*This document guides POSIX compatibility decisions. Update as implementation proceeds.*
