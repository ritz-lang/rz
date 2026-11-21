# Harland Kernel Contract for Filesystem Drivers

This document defines the stable interface that Harland provides to filesystem drivers like Goliath. Implementing against this contract ensures forward compatibility.

---

## Contract Version

**Version**: 1.0.0-draft
**Status**: Proposal
**Last Updated**: 2024

---

## Overview

Goliath runs as a Ring 2 service and communicates with:
1. **Applications** (Ring 3) - via IPC channels
2. **Block drivers** (Ring 2) - via IPC channels
3. **Kernel** (Ring 0) - via syscalls

This contract specifies the syscall interface Goliath depends on.

---

## System Call Contract

### Conventions

- **Syscall ABI**: AMD64 SYSCALL instruction
  - RAX = syscall number
  - RDI, RSI, RDX, R10, R8, R9 = arguments 1-6
  - RAX = return value (negative = error)
- **Errors**: Negative return values are negated errno codes
- **Pointers**: Must be in caller's valid address space

### Core Syscalls

#### SYS_EXIT (20)

```ritz
# Terminate the calling process
fn sys_exit(code: i32) -> !
```

- **code**: Exit code (0 = success)
- **Returns**: Never returns

#### SYS_YIELD (24)

```ritz
# Yield CPU to scheduler
fn sys_yield() -> i32
```

- The next runnable process runs; the caller runs again when its turn
  comes round (at once if nothing else can run). Processes are also
  preempted: a 100 Hz LAPIC tick, calibrated against the TSC, round-robins
  the runnable processes whenever it interrupts ring 3 (AGAST #3629).
- **Returns**: 0 on success

#### SYS_SPAWN_BG (28)

```ritz
# Start a program without waiting for it (AGAST #3629)
fn sys_spawn_bg(path: *u8, argv: **u8, argc: i32) -> i64
```

- Like SYS_SPAWN_ARGS (25), which blocks until the child exits; here the
  caller and the child both run. `sys_wait(pid)` (22) sleeps until the child
  exits and returns its exit code. A child whose parent exits first is
  detached: nobody can wait for it, and its exit frees its slot.
- **Returns**: the child's pid, or a negative errno (ENOENT, ENOEXEC,
  ENOMEM, EAGAIN with 8 processes live, E2BIG, EFAULT)

#### SYS_GETPID (23)

```ritz
# Get current process ID
fn sys_getpid() -> i32
```

- **Returns**: Current process ID

#### SYS_TTY_GETATTR (18), SYS_TTY_SETATTR (19)

```ritz
# The serial console's terminal flags (AGAST #4254)
fn sys_tty_getattr(fd: i32, attrs: *TtyAttrs) -> i32
fn sys_tty_setattr(fd: i32, attrs: *TtyAttrs) -> i32
```

- **attrs**: `{ flags: u32 }`: TTY_ECHO (1) echoes input, TTY_ICANON (2)
  edits a line in the kernel (DEL/BS rub out, CR reads as NL, Ctrl-D ends
  input) and `read(0)` returns one line, TTY_ISIG (4) makes Ctrl-C kill the
  foreground process (exit status 130; init is never killed). All three are
  set at boot. `read(0)` blocks until there is input.
- **fd**: 0, 1 or 2 when it is not an open file
- **Returns**: 0, ENOTTY for any other fd, EFAULT for a bad `attrs`

#### SYS_TTY_SETFG (16)

```ritz
# The console's foreground: whose Ctrl-C it is (tcsetpgrp, AGAST #4276)
fn sys_tty_setfg(fd: i32, mode: u64, pid: u64) -> i32
```

- **mode**: TTY_FG_NONE (0), the boot default: Ctrl-C kills the running
  process. TTY_FG_CHILDREN (1): the caller's descendants, not the caller.
  Spawn blocks, so a shell can't name its command's pid in advance. rzsh sets
  this before it turns ISIG back on, so a Ctrl-C typed before spawn starts
  the command is dropped instead of killing rzsh. TTY_FG_PID (2): `pid` and
  its descendants. A pid that is not running matches nothing.
- A Ctrl-C for a process outside the foreground only drops the line. init is
  never the foreground.
- **fd**: 0, 1 or 2 when it is not an open file
- **Returns**: 0, ENOTTY for any other fd, EINVAL for an unknown mode, for
  TTY_FG_PID with pid 0, or for TTY_FG_CHILDREN before init starts

---

### IPC Syscalls

#### SYS_CHANNEL_CREATE (100)

```ritz
# Create a new IPC channel pair
fn sys_channel_create() -> ChannelPair

pub struct ChannelPair
    send: CapHandle      # Capability to send on channel
    recv: CapHandle      # Capability to receive on channel
```

- **Returns**: Two capabilities (send and receive endpoints)
- **Errors**: -ENOMEM if out of resources

#### SYS_IPC_SEND (30)

```ritz
# Send a message on a channel
fn sys_ipc_send(
    channel: CapHandle,  # Channel send capability
    msg: *MsgHeader,     # Message to send
    caps: *CapHandle,    # Capabilities to transfer (may be null)
    cap_count: u32       # Number of capabilities
) -> i32
```

- **Blocking**: Blocks if receiver buffer full
- **Returns**: 0 on success, negative on error
- **Errors**:
  - -EINVAL: Invalid capability or message
  - -EPERM: Capability doesn't have send rights
  - -EAGAIN: Would block (if non-blocking)

#### SYS_IPC_RECV (31)

```ritz
# Receive a message from a channel
fn sys_ipc_recv(
    channel: CapHandle,  # Channel receive capability
    msg_buf: *u8,        # Buffer for message
    msg_buf_len: u64,    # Buffer size
    caps: *CapHandle,    # Buffer for received capabilities
    cap_count: *u32      # In: cap buffer size, Out: caps received
) -> i64
```

- **Blocking**: Blocks until message available
- **Returns**: Message size on success, negative on error
- **Errors**:
  - -EINVAL: Invalid capability or buffer
  - -EPERM: Capability doesn't have receive rights
  - -EMSGSIZE: Message too large for buffer

#### SYS_IPC_CALL (32)

```ritz
# Send request and wait for reply (RPC pattern)
fn sys_ipc_call(
    channel: CapHandle,  # Channel capability
    request: *MsgHeader, # Request message
    reply_buf: *u8,      # Buffer for reply
    reply_len: u64       # Reply buffer size
) -> i64
```

- **Returns**: Reply size on success, negative on error
- **Atomic**: Combines send + receive atomically

---

### Capability Syscalls

#### SYS_CAP_GRANT (40)

```ritz
# Grant a capability to another process
fn sys_cap_grant(
    cap: CapHandle,      # Capability to grant
    target_pid: u32,     # Target process ID
    rights: u32          # Rights to grant (must be subset of owned rights)
) -> CapHandle
```

- **Returns**: New capability handle in target's table
- **Errors**:
  - -EINVAL: Invalid capability
  - -EPERM: Insufficient rights to grant
  - -ESRCH: Target process not found

#### SYS_CAP_REVOKE (41)

```ritz
# Revoke a previously granted capability
fn sys_cap_revoke(cap: CapHandle) -> i32
```

- **Cascading**: Revokes all capabilities derived from this one
- **Returns**: 0 on success

#### SYS_CAP_DERIVE (42)

```ritz
# Create a derived capability with reduced rights
fn sys_cap_derive(
    cap: CapHandle,      # Original capability
    rights_mask: u32     # Rights to keep (ANDed with original)
) -> CapHandle
```

- **Returns**: New capability with reduced rights
- **Errors**: -EINVAL if rights_mask exceeds original rights

#### SYS_CAP_INFO (43)

```ritz
# Query capability information
fn sys_cap_info(cap: CapHandle, info: *CapInfo) -> i32

pub struct CapInfo
    cap_type: u8         # Type (memory, channel, irq, etc.)
    rights: u32          # Current rights
    object_id: u64       # Object identifier
```

- **Returns**: 0 on success

---

### Memory Syscalls

#### SYS_SHM_CREATE (50)

```ritz
# Create a shared memory region
fn sys_shm_create(
    size: u64,           # Size in bytes (rounded up to page)
    flags: u32           # Flags (SHM_READ, SHM_WRITE, SHM_EXEC)
) -> CapHandle
```

- **Returns**: Capability for shared memory
- **Errors**: -ENOMEM if out of memory

#### SYS_SHM_MAP (51)

```ritz
# Map shared memory into address space
fn sys_shm_map(
    shm_cap: CapHandle,  # Shared memory capability
    addr_hint: *u8,      # Desired address (null for any)
    flags: u32           # MAP_FIXED, etc.
) -> *u8
```

- **Returns**: Mapped address on success
- **Errors**: -ENOMEM, -EINVAL

#### SYS_SHM_UNMAP (52)

```ritz
# Unmap shared memory
fn sys_shm_unmap(addr: *u8, size: u64) -> i32
```

- **Returns**: 0 on success

#### SYS_DMA_ALLOC (61)

```ritz
# Allocate DMA-capable memory (for drivers only)
fn sys_dma_alloc(size: u64) -> DmaRegion

pub struct DmaRegion
    virt: *u8            # Virtual address
    phys: u64            # Physical address (for hardware)
    size: u64            # Actual size allocated
```

- **Requires**: Driver privilege (Ring 2)
- **Properties**: Physically contiguous, not pageable
- **Errors**: -ENOMEM, -EPERM if not a driver

#### SYS_DMA_FREE (62)

```ritz
# Free DMA memory
fn sys_dma_free(virt: *u8) -> i32
```

- **Returns**: 0 on success

---

### Device Syscalls (Ring 2 Drivers Only)

#### SYS_MMIO_MAP (63)

```ritz
# Map device MMIO region
fn sys_mmio_map(
    mmio_cap: CapHandle, # MMIO capability (granted by kernel)
    size: u64            # Size to map
) -> *u8
```

- **Requires**: MMIO capability for specific device
- **Properties**: Uncached, device memory
- **Returns**: Virtual address of mapped region

#### SYS_IRQ_WAIT (60)

```ritz
# Wait for interrupt
fn sys_irq_wait(
    irq_cap: CapHandle,  # IRQ capability (granted by kernel)
    timeout_ms: i64      # Timeout (-1 = infinite)
) -> i32
```

- **Blocking**: Until interrupt fires or timeout
- **Returns**: 0 on interrupt, -ETIMEDOUT on timeout

#### SYS_IRQ_ACK (64)

```ritz
# Acknowledge interrupt (re-enable)
fn sys_irq_ack(irq_cap: CapHandle) -> i32
```

- **Must call**: After handling interrupt
- **Returns**: 0 on success

---

### Service Registration

#### SYS_SERVICE_REGISTER (70)

```ritz
# Register as a named service
fn sys_service_register(
    name: *u8,           # Service name (e.g., "goliath", "virtio-blk")
    name_len: u64,
    channel: CapHandle   # Channel to receive requests
) -> i32
```

- **Returns**: 0 on success
- **Errors**: -EEXIST if name taken

#### SYS_SERVICE_LOOKUP (71)

```ritz
# Look up a registered service
fn sys_service_lookup(
    name: *u8,
    name_len: u64
) -> CapHandle
```

- **Returns**: Channel capability to service
- **Errors**: -ENOENT if not found

---

## Message Format

### Standard Header

All IPC messages begin with:

```ritz
pub struct MsgHeader
    msg_type: u32        # Application-defined message type
    flags: u32           # MSG_NEEDS_REPLY, MSG_URGENT, etc.
    seq: u32             # Sequence number (for replies)
    payload_len: u32     # Bytes following header
```

### Message Flags

```ritz
pub const MSG_NEEDS_REPLY: u32 = 1 << 0
pub const MSG_URGENT: u32 = 1 << 1
pub const MSG_CAPS_FOLLOW: u32 = 1 << 2  # Capabilities attached
```

---

## Error Codes

A failing syscall returns a negative errno in rax, numbered as on Linux. The
kernel's one source for them is `pub enum Errno: i64` in
`kernel/src/syscall/errno.ritz` (each discriminant is the negated number);
this table lists exactly its variants (checked by
`projects/ritz/ritz0/test_harland_errno.py`).

| Code | Name | `Errno` | Description |
|------|------|---------|-------------|
| -1 | EPERM | Perm | Operation not permitted |
| -2 | ENOENT | NoEnt | No such file or directory |
| -3 | ESRCH | Srch | No such process |
| -5 | EIO | Io | I/O error |
| -7 | E2BIG | TooBig | Argument list too long |
| -8 | ENOEXEC | NoExec | Not a loadable executable |
| -9 | EBADF | BadF | Bad file descriptor or handle |
| -10 | ECHILD | Child | No child to wait for |
| -11 | EAGAIN | Again | Try again (nothing pending) |
| -12 | ENOMEM | NoMem | Out of memory |
| -13 | EACCES | Acces | Access denied |
| -14 | EFAULT | Fault | Bad address |
| -17 | EEXIST | Exist | Already exists |
| -19 | ENODEV | NoDev | No such device |
| -20 | ENOTDIR | NotDir | Not a directory |
| -21 | EISDIR | IsDir | Is a directory |
| -22 | EINVAL | Inval | Invalid argument |
| -23 | ENFILE | NFile | Too many open files |
| -25 | ENOTTY | NotTy | Not a terminal |
| -28 | ENOSPC | NoSpc | No space left |
| -32 | EPIPE | Pipe | Broken pipe (peer closed) |
| -34 | ERANGE | Range | Buffer too small |
| -36 | ENAMETOOLONG | NameTooLong | Name too long |
| -38 | ENOSYS | NoSys | Syscall not implemented |
| -39 | ENOTEMPTY | NotEmpty | Directory not empty |

The ELF loader's failures are not errnos: `loader/elf.ritz` returns an
`ElfStatus`, which a failed spawn reports as ENOMEM or ENOEXEC.

---

## Capability Types

| Type ID | Name | Description |
|---------|------|-------------|
| 0 | CAP_NONE | Invalid/null capability |
| 1 | CAP_MEMORY | Memory region |
| 2 | CAP_CHANNEL | IPC channel endpoint |
| 3 | CAP_IRQ | Interrupt handling |
| 4 | CAP_IOPORT | x86 I/O port |
| 5 | CAP_MMIO | Memory-mapped I/O |
| 6 | CAP_PROCESS | Process control |
| 7 | CAP_NAMESPACE | Filesystem namespace |
| 8 | CAP_FILE | Open file |
| 9 | CAP_SHM | Shared memory |
| 10 | CAP_SERVICE | Named service |
| 11 | CAP_POWER | ACPI power-off (AGAST #1888) |
| 12 | CAP_DISPLAY | Framebuffer mapping (AGAST #1888) |

### Capability Gate Policy

The syscall boundary checks a process-wide capability before a reserved
operation runs (`cap/table.ritz`, AGAST #1888 and #4472). A process with no
capability table, or no entry of that type with the required right, is
refused with `-EPERM`; the operation never reaches the subsystem.

| Syscall | Capability | Right |
|---------|------------|-------|
| SYS_ACPI_POWEROFF | CAP_POWER | EXECUTE |
| SYS_FB_MAP | CAP_DISPLAY | WRITE |
| SYS_IPC_SEND | CAP_CHANNEL | SEND |
| SYS_IPC_RECV | CAP_CHANNEL | RECV |
| SYS_IPC_CLOSE | CAP_CHANNEL | SEND or RECV |
| SYS_OPEN | CAP_NAMESPACE | READ; CREATE too for O_CREAT |
| SYS_READ (filesystem fd) | CAP_NAMESPACE | READ |
| SYS_WRITE (filesystem fd) | CAP_NAMESPACE | WRITE |
| SYS_LSEEK, SYS_CLOSE (filesystem fd) | CAP_NAMESPACE | READ or WRITE |
| SYS_READDIR | CAP_NAMESPACE | LIST |
| SYS_MKDIR | CAP_NAMESPACE | CREATE |
| SYS_SYNC | CAP_NAMESPACE | WRITE |

Console fds 0-2 stay ungated: a process denied the filesystem must still be
able to report why.

**Seeding and inheritance.** Init (pid 1) is seeded with POWER, DISPLAY,
CHANNEL and NAMESPACE with CAP_RIGHT_ALL. A spawned child starts with an
empty table and inherits DISPLAY, CHANNEL and NAMESPACE with its parent's
rights, never widened (`cap_inherit_ambient`). POWER is never inherited:
only init can power the machine off, so no child can.

**Granting.** Every other capability is granted explicitly. SYS_CAP_GRANT
copies an entry from the caller's table when the entry carries
CAP_RIGHT_GRANT; the recipient's rights are the source rights intersected
with the requested rights. SYS_CAP_DERIVE narrows a held capability, and
SYS_CAP_REVOKE removes one. A child that revokes an inherited CHANNEL or
NAMESPACE capability loses IPC or filesystem access from the next syscall
(the boot-gate children `cap_ipc_child` and `cap_fs_child` prove this).

---

## Stability Guarantees

### Stable

- Syscall numbers for documented calls
- MsgHeader structure layout
- Error code values
- Capability type IDs

### Unstable (May Change)

- Internal kernel structures
- Undocumented syscalls
- Performance characteristics
- Specific scheduling behavior

### Deprecated

When a syscall is deprecated:
1. It continues to work for 2 major versions
2. It returns -ENOSYS after deprecation period
3. Replacement syscall is documented

---

## Versioning

The kernel reports its contract version:

```ritz
# Get kernel contract version
fn sys_version(info: *VersionInfo) -> i32

pub struct VersionInfo
    major: u16           # Major version (breaking changes)
    minor: u16           # Minor version (new features)
    patch: u16           # Patch version (bug fixes)
    flags: u16           # Feature flags
```

Goliath should check version on startup and fail gracefully if incompatible.

---

## Implementation Notes for Harland

### Priority Order

1. **IPC channels** - Core communication mechanism
2. **Capability management** - Security foundation
3. **Shared memory** - Efficient data transfer
4. **Service registration** - Service discovery
5. **IRQ/MMIO** - Driver support

### Testing Strategy

Each syscall should have:
1. Unit tests in kernel
2. Integration tests from userspace
3. Stress tests for concurrency
4. Negative tests for error paths

---

## See Also

- Filesystem architecture: not yet written (this link pointed at a file that has never existed)
- [Goliath Design](../../goliath/docs/DESIGN.md)
