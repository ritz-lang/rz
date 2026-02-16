# Harland Namespace & Storage Architecture

## Overview

Harland separates two distinct concerns that traditional Unix conflates:

1. **Resource Namespace** - How resources are organized and accessed (paths, visibility)
2. **Storage Backends** - How data is persisted (Goliath, memory, devices)

This separation enables:
- Ephemeral objects (pipes, sockets) without disk overhead
- Capability-controlled visibility independent of storage
- Clean hypervisor-level resource sharing
- No setuid - privilege via capability delegation

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Processes                           │
├─────────────────────────────────────────────────────────────────┤
│                     Syscall Interface                            │
│              (open, read, write, close, stat)                    │
├─────────────────────────────────────────────────────────────────┤
│                    VFS / FD Table Layer                          │
│         (file descriptors, current position, flags)              │
├─────────────────────────────────────────────────────────────────┤
│                   Resource Namespace Layer                       │
│    (knamespace: path resolution, visibility, capabilities)       │
├────────────────────┬────────────────────┬───────────────────────┤
│   Goliath Backend  │  Memory Backend    │   Device Backend      │
│  (persistent files)│ (pipes, tmpfs)     │ (block, char devs)    │
├────────────────────┴────────────────────┴───────────────────────┤
│                      Block / DMA Layer                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Resource Namespace (knamespace)

The namespace is an **in-memory tree** that maps paths to resources. Each node has:

```ritz
struct NamespaceNode
    name: [64]u8              # Node name (file/directory name)
    name_len: u32             # Length of name

    # Tree structure
    parent: *NamespaceNode
    first_child: *NamespaceNode
    next_sibling: *NamespaceNode

    # Node type and backend
    node_type: NodeType       # Directory, File, Device, Pipe, Socket, Symlink
    backend: BackendType      # Goliath, Memory, Device, None

    # Backend-specific handle
    backend_handle: u64       # Blob hash for Goliath, device ID, pipe ID, etc.

    # Metadata
    size: u64
    created: u64
    modified: u64

    # Capability-based access control
    visibility: Visibility
    required_caps: u64        # Capability mask for access
    owner_pid: u32            # Creator process (for cleanup)
```

### Node Types

| Type | Description | Typical Backend |
|------|-------------|-----------------|
| `Directory` | Contains other nodes | None (namespace-only) |
| `File` | Regular file | Goliath or Memory |
| `Device` | Block or character device | Device |
| `Pipe` | Anonymous pipe | Memory |
| `Socket` | Unix domain socket | Memory |
| `Symlink` | Symbolic link | None (stores path) |
| `Mount` | Mount point overlay | Delegates to mounted namespace |

### Backend Types

| Backend | Description | Persistence |
|---------|-------------|-------------|
| `Goliath` | Content-addressed blob store | Persistent |
| `Memory` | Kernel heap allocation | Volatile |
| `Device` | Driver-managed resource | N/A |
| `None` | Pure namespace node | N/A |

---

## Visibility Model

Unlike Unix's simple permission bits, Harland has explicit visibility levels:

```ritz
enum Visibility
    # Everyone can see AND access
    Public = 0

    # Everyone can see it exists, but needs capabilities to access
    Visible = 1

    # Only processes with specific capabilities can even see it
    Hidden = 2

    # Only the kernel can see it
    KernelOnly = 3
```

### Example: /dev/ Directory

```
/dev/
  ├── null      [Public]     - anyone can read/write
  ├── zero      [Public]     - anyone can read
  ├── random    [Public]     - anyone can read
  ├── disk0     [Visible]    - visible to all, accessible to CAP_BLOCK_DEVICE
  ├── disk1     [Visible]    - visible to all, accessible to CAP_BLOCK_DEVICE
  ├── kmem      [Hidden]     - only kernel drivers see this
  └── port      [KernelOnly] - truly hidden from userspace
```

### Behavior

| Visibility | `ls /dev/` shows? | `stat /dev/disk0` returns? | `open()` returns? |
|------------|-------------------|----------------------------|-------------------|
| Public | Yes | Full info | Success |
| Visible | Yes | Limited info (exists, type) | EPERM if no cap |
| Hidden | No (unless has cap) | ENOENT (unless has cap) | ENOENT or EPERM |
| KernelOnly | Never | ENOENT | ENOENT |

---

## Storage Backends

### Goliath (Persistent Storage)

Content-addressed blob storage for persistent files.

```ritz
# Store data, get hash back
fn goliath_store(data: *u8, len: u64) -> BlobHash

# Retrieve data by hash
fn goliath_load(hash: BlobHash, buf: *u8, len: u64) -> i64

# Reference counting for GC
fn goliath_ref(hash: BlobHash)
fn goliath_unref(hash: BlobHash)
```

**Key insight**: The namespace stores the hash, Goliath stores the data. Multiple paths can point to the same hash (deduplication for free).

### Memory Backend (Ephemeral)

For pipes, sockets, tmpfs:

```ritz
struct MemoryFile
    data: *u8
    capacity: u64
    size: u64

    # For pipes
    read_pos: u64
    write_pos: u64
    readers: u32
    writers: u32
```

**Cleanup**: When `owner_pid` exits, all Memory-backed nodes it created are removed (unless transferred).

### Device Backend

Delegates to device drivers:

```ritz
struct DeviceOps
    read: fn(dev: *Device, buf: *u8, len: u64, offset: u64) -> i64
    write: fn(dev: *Device, buf: *u8, len: u64, offset: u64) -> i64
    ioctl: fn(dev: *Device, cmd: u64, arg: u64) -> i64
    mmap: fn(dev: *Device, offset: u64, len: u64) -> *u8
```

---

## Capability-Based Access (No setuid!)

### The Problem with setuid

Linux's setuid is dangerous because:
1. Binary runs with elevated privileges for its entire lifetime
2. Any vulnerability in the binary = root shell
3. Complex interactions with environment, file descriptors
4. Difficult to audit

### Harland's Solution: Capability Delegation

Instead of elevating a process, **delegate specific capabilities** via IPC:

```
┌─────────────────┐         IPC Request          ┌─────────────────┐
│  User Process   │  ─────────────────────────►  │  Gatekeeper     │
│                 │                              │  Service        │
│  Has: CAP_NET   │  "add user 'bob'"            │                 │
│                 │                              │  Has: CAP_ADMIN │
│                 │  ◄─────────────────────────  │                 │
└─────────────────┘     Result or Delegated Cap  └─────────────────┘
```

### Gatekeeper Services

Privileged services that mediate access:

| Service | Capabilities | Function |
|---------|--------------|----------|
| `userd` | `CAP_ADMIN_USERS` | User management |
| `netd` | `CAP_ADMIN_NET` | Network configuration |
| `mountd` | `CAP_ADMIN_MOUNT` | Mount operations |
| `cryptd` | `CAP_ADMIN_CRYPTO` | Key management |

### Delegation Types

```ritz
enum DelegationType
    # Service performs action, returns result
    Proxy = 0

    # Service grants time-limited capability token
    TimeToken = 1

    # Service grants scope-limited capability
    ScopedToken = 2
```

**Example: Changing password**

```ritz
# User process sends request to userd
let req = UserRequest {
    action: ChangePassword,
    user: "self",
    credential: current_password,
    new_value: new_password,
}

# userd verifies credential, makes change
let resp = ipc_call(USERD_CHANNEL, &req)

# User never had elevated privileges
```

### Audit Trail

Every capability delegation is logged:

```
[2024-01-15 10:23:45] userd: PID 1234 (uid=bob) requested ChangePassword
[2024-01-15 10:23:45] userd: Verified credential for bob
[2024-01-15 10:23:45] userd: Password changed for bob
```

---

## Mount Semantics

### Namespace Composition

Mounting overlays one namespace subtree onto another:

```ritz
struct Mount
    source: *NamespaceNode    # Root of mounted tree
    target: *NamespaceNode    # Mount point in parent namespace
    flags: MountFlags

    # Capability restrictions
    max_caps: u64             # Ceiling for capabilities in mount
```

### Mount Types

| Type | Description |
|------|-------------|
| `Bind` | Same namespace, different path |
| `Overlay` | Layer writable tree over read-only |
| `Remote` | Network filesystem (future) |
| `Virtio` | Hypervisor-shared volume |

### Per-Process Namespace Views

Each process has its own namespace view:

```ritz
struct ProcessNamespace
    root: *NamespaceNode      # Process sees this as /
    cwd: *NamespaceNode       # Current working directory
    mounts: []*Mount          # Active mounts for this process

    # Capability ceiling
    max_caps: u64             # Process cannot exceed these
```

**Containers**: Just processes with restricted namespace views and capability ceilings.

---

## Hypervisor Integration (Future)

### VirtIO Shared Volumes

```
┌─────────────────┐     VirtIO     ┌─────────────────┐
│  Harland Host   │  ◄──────────►  │  Harland Guest  │
│                 │                │                 │
│  /shared/       │    Shared      │  /mnt/host/     │
│    data.txt     │    Memory      │    data.txt     │
└─────────────────┘                └─────────────────┘
```

### Nested Harland

Capabilities compose hierarchically:

```
Host Harland
  └── Guest Harland (has subset of host capabilities)
       └── Container (has subset of guest capabilities)
```

The guest can never have more capabilities than the host granted it.

### Cross-Guest Sharing

```
Host Harland
  ├── Guest A (Linux)
  │     └── /mnt/shared → VirtIO channel 0
  ├── Guest B (Harland)
  │     └── /mnt/shared → VirtIO channel 0
  └── /hypervisor/shared/ → backing store
```

All guests see the same files via hypervisor-mediated VirtIO.

---

## Implementation Plan

### Phase 1: Separate Namespace from Storage
- [ ] Add `backend` field to `NamespaceNode`
- [ ] Add `visibility` field
- [ ] Refactor `knamespace_write` to use backend selection
- [ ] Memory backend for pipes/tmpfs

### Phase 2: Visibility Model
- [ ] Implement visibility checks in path resolution
- [ ] Limited `stat` for `Visible` nodes
- [ ] Capability-gated access

### Phase 3: Gatekeeper Services
- [ ] Design gatekeeper IPC protocol
- [ ] Implement `userd` as proof of concept
- [ ] Audit logging

### Phase 4: Mount Semantics
- [ ] Mount/unmount syscalls
- [ ] Bind mounts
- [ ] Per-process namespace views

### Phase 5: Hypervisor Support
- [ ] VirtIO shared memory device
- [ ] Shared volume backend
- [ ] Nested capability enforcement

---

## Summary

| Feature | Linux | Harland |
|---------|-------|---------|
| Ephemeral objects | tmpfs, pipes "feel" like files | First-class Memory backend |
| Visibility | File permissions only | Explicit Visibility levels |
| Privilege escalation | setuid (dangerous) | Capability delegation (safe) |
| Containers | namespaces + cgroups (complex) | Namespace views + cap ceilings |
| Cross-VM sharing | Network only | VirtIO shared memory |

**The key insight**: By separating "where things appear" from "how they're stored", we get clean abstractions that compose well for containers, VMs, and distributed systems.
