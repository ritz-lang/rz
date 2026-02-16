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

- **Returns**: 0 on success

#### SYS_GETPID (23)

```ritz
# Get current process ID
fn sys_getpid() -> i32
```

- **Returns**: Current process ID

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

Standard POSIX-compatible error codes:

| Code | Name | Description |
|------|------|-------------|
| -1 | EPERM | Permission denied |
| -2 | ENOENT | No such file or directory |
| -3 | ESRCH | No such process |
| -4 | EINTR | Interrupted syscall |
| -9 | EBADF | Bad file descriptor |
| -11 | EAGAIN | Try again |
| -12 | ENOMEM | Out of memory |
| -13 | EACCES | Access denied |
| -14 | EFAULT | Bad address |
| -17 | EEXIST | Already exists |
| -19 | ENODEV | No such device |
| -20 | ENOTDIR | Not a directory |
| -21 | EISDIR | Is a directory |
| -22 | EINVAL | Invalid argument |
| -28 | ENOSPC | No space left |
| -36 | ENAMETOOLONG | Name too long |
| -38 | ENOSYS | Syscall not implemented |
| -40 | ELOOP | Too many symlinks |
| -90 | EMSGSIZE | Message too long |
| -110 | ETIMEDOUT | Timed out |

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

- [Filesystem Architecture](./FILESYSTEM_ARCHITECTURE.md)
- [Goliath Design](../../goliath/docs/DESIGN.md)
