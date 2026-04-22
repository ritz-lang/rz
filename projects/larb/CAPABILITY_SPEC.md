# Harland Capability Model Specification

> LARB-0012: Mechanism/Policy Security Architecture for the Harland Microkernel
>
> Status: DRAFT
> Author: Aaron Sinclair / Adele
> Date: 2026-04-22

## 1. Design Philosophy

**Mechanisms are forever. Policies are for Tuesday.**

The Harland kernel provides a minimal set of **mechanism primitives** — stable,
rarely-changing kernel objects that enable isolation, communication, and resource
accounting. All security **policies** (access control, identity, scheduling
priorities, filesystem layout) live in userspace and can be changed without
touching the kernel.

This is the inverse of Linux, where security is bolted on (DAC + MAC via
SELinux/AppArmor) and file descriptors conflate naming, access, and identity
into a single leaky abstraction.

### 1.1. Principles

1. **No ambient authority.** A process has exactly the capabilities it was
   explicitly granted. No global namespaces, no implicit access.
2. **Unforgeable handles.** Capabilities are kernel-managed tokens. Userspace
   cannot fabricate, guess, or corrupt them.
3. **Least privilege by construction.** New processes start with zero
   capabilities. Parents explicitly delegate what children need.
4. **Revocable delegation.** Any capability can be revoked by its grantor,
   propagating transitively through the delegation tree.
5. **Composable mechanisms.** Complex policies emerge from combining simple
   primitives — the kernel doesn't need to understand "files" or "sockets".

### 1.2. What's a Mechanism vs. a Policy?

| Mechanism (Kernel, Stable) | Policy (Userspace, Changeable) |
|---|---|
| Capability handle creation/transfer/revocation | Access control lists, role-based access |
| Memory region grant/map/unmap | Filesystem layout, directory structure |
| Channel create/send/receive | Service discovery, DNS, routing |
| Execution context create/schedule/kill | Process supervision, restart policies |
| Interrupt routing to capability holders | Device driver selection, hotplug rules |
| Namespace scoping (hierarchical isolation) | User identity, authentication, login |

## 2. Mechanism Primitives

Harland has exactly **6 kernel object types**. Everything else is userspace.

### 2.1. Capability Handle (`Cap`)

The fundamental unit of authority. A `Cap` is an unforgeable reference to a
kernel object with an embedded permission mask.

```ritz
# Kernel-internal representation (NOT exposed to userspace)
struct Cap
    object_id: u64       # Kernel object table index
    rights: CapRights    # Permission bitmask
    generation: u32      # Revocation generation counter
    owner: u16           # Owning CSpace index
    _pad: u16

# Rights bitmask — what operations this handle allows
struct CapRights
    bits: u32

const CAP_READ: u32       = 0x0001  # Read data from object
const CAP_WRITE: u32      = 0x0002  # Write data to object
const CAP_EXEC: u32       = 0x0004  # Execute (for code regions)
const CAP_MAP: u32        = 0x0008  # Map into address space
const CAP_GRANT: u32      = 0x0010  # Delegate to another process
const CAP_REVOKE: u32     = 0x0020  # Revoke delegated caps
const CAP_DESTROY: u32    = 0x0040  # Destroy the underlying object
const CAP_DUP: u32        = 0x0080  # Duplicate this handle (same rights)
const CAP_REDUCE: u32     = 0x0100  # Create handle with fewer rights
const CAP_WAIT: u32       = 0x0200  # Wait for events on this object
const CAP_SIGNAL: u32     = 0x0400  # Signal events on this object
const CAP_INSPECT: u32    = 0x0800  # Query object metadata
```

**Key properties:**
- Handles are **indices into a per-process capability space (CSpace)**, not
  pointers. Userspace sees small integers (like file descriptors) but cannot
  forge them — the kernel validates every access.
- Rights can only be **reduced**, never amplified. `cap_reduce(cap, mask)` →
  new handle with `rights & mask`.
- **Generation counter** enables O(1) revocation — bump the generation, all
  stale handles become invalid on next use.

### 2.2. Memory Region (`MemRegion`)

A contiguous range of physical memory with explicit permissions. Replaces
`mmap`/`munmap`/`mprotect` with capability-gated operations.

```ritz
# Create a memory region (anonymous)
#   Returns: Cap to the new region with full rights
fn sys_mem_create(size: u64, flags: u32) -> CapResult

# Map a region into current address space
#   cap: Must have CAP_MAP right
#   vaddr: Suggested virtual address (0 = kernel picks)
#   Returns: Actual mapped virtual address
fn sys_mem_map(cap: u32, vaddr: u64, offset: u64, size: u64) -> AddrResult

# Unmap a region
fn sys_mem_unmap(vaddr: u64, size: u64) -> SysResult

# Grant a sub-view of a region to another process
#   cap: Must have CAP_GRANT right
#   target: Cap to target process's CSpace
#   offset, size: Sub-range within the region
#   rights: Must be subset of cap's rights
fn sys_mem_grant(cap: u32, target: u32, offset: u64, size: u64,
                 rights: u32) -> CapResult
```

**Design notes:**
- No `MAP_SHARED` / `MAP_PRIVATE` distinction. Sharing is explicit via
  `sys_mem_grant`. The recipient gets a capability with exactly the rights
  you specify.
- **Zero-copy IPC**: Grant a region with `CAP_READ` to a service. The service
  maps it, reads the data, unmaps. No copying.
- DMA buffers: Drivers get `MemRegion` caps from the kernel with physical
  address access rights. Only Ring 1 drivers can request physically-contiguous
  regions.

### 2.3. Channel (`Chan`)

Typed, bidirectional IPC endpoint. Channels are the only way processes
communicate. Replaces pipes, sockets, signals, and shared memory notifications.

```ritz
# Create a channel pair
#   Returns: Two capabilities — one for each endpoint
fn sys_chan_create() -> ChanPairResult

# Send a message on a channel
#   chan: Must have CAP_WRITE right
#   msg: Message header (inline data + optional cap transfers)
fn sys_chan_send(chan: u32, msg: *Message) -> SysResult

# Receive a message from a channel
#   chan: Must have CAP_READ right
#   msg: Buffer for received message
fn sys_chan_recv(chan: u32, msg: *Message) -> SysResult

# Synchronous call (send + recv, like an RPC)
#   chan: Must have CAP_WRITE | CAP_READ rights
fn sys_chan_call(chan: u32, request: *Message, reply: *Message) -> SysResult

# Message structure
struct Message
    # Inline data (small messages, no allocation)
    data: [64]u8         # 64 bytes inline payload
    data_len: u32        # Actual data length (0..64)

    # Capability transfer (send caps to the other endpoint)
    caps: [4]u32         # Up to 4 capability handles to transfer
    cap_count: u32       # Number of caps being transferred (0..4)

    # Large payload (optional, via MemRegion)
    payload_cap: u32     # Cap to MemRegion for large data (0 = none)
    payload_offset: u64  # Offset within the region
    payload_len: u64     # Length of payload data
```

**Design notes:**
- Channels carry **both data and capabilities**. This is how authority flows
  through the system — a parent sends a child the capabilities it needs via
  channel messages.
- The 64-byte inline payload avoids allocation for small messages (most IPC).
  For large transfers, attach a `MemRegion` capability.
- **No global channel namespace.** You can only send to a channel you hold a
  cap to. Service discovery is a userspace policy.

### 2.4. Execution Context (`Exec`)

A schedulable unit of computation with its own address space, CSpace, and
thread state. Replaces processes, threads, and thread groups.

```ritz
# Create a new execution context
#   Returns: Cap to the new context (suspended, no caps, empty address space)
fn sys_exec_create() -> CapResult

# Start execution
#   exec: Must have CAP_EXEC right
#   entry: Virtual address of entry point (within context's address space)
#   stack: Virtual address of stack top
#   arg: Cap to pass as initial argument (typically a channel)
fn sys_exec_start(exec: u32, entry: u64, stack: u64, arg: u32) -> SysResult

# Stop execution
#   exec: Must have CAP_SIGNAL right
fn sys_exec_stop(exec: u32) -> SysResult

# Wait for context to exit
#   exec: Must have CAP_WAIT right
fn sys_exec_wait(exec: u32) -> ExecResult

# Grant a capability to another context's CSpace
#   exec: Must have CAP_GRANT right on the target context
#   cap: The capability to grant
#   rights: Subset of cap's current rights
fn sys_exec_grant(exec: u32, cap: u32, rights: u32) -> CapResult

# Set resource budget (CPU time, memory pages)
#   exec: Must have CAP_WRITE right
fn sys_exec_set_budget(exec: u32, budget: *Budget) -> SysResult

struct Budget
    cpu_us: u64          # CPU microseconds per scheduling period
    period_us: u64       # Scheduling period length
    mem_pages: u64       # Maximum physical pages
    chan_count: u32       # Maximum channel endpoints
    cap_count: u32       # Maximum CSpace entries
```

**Design notes:**
- A new `Exec` starts with **nothing** — empty address space, empty CSpace.
  The parent must explicitly grant everything: memory regions for code/data/stack,
  channel endpoints for communication, any other capabilities needed.
- **This is least privilege by construction.** You cannot accidentally give a
  process access to something — you have to explicitly grant each capability.
- Resource budgets enable **deterministic scheduling** — no process can starve
  others beyond its budget.

### 2.5. Interrupt Object (`Irq`)

Kernel-managed interrupt routing. Interrupts are delivered as messages on
channels, not as signals or callbacks.

```ritz
# Bind a hardware interrupt to a channel
#   irq_num: Hardware IRQ number
#   chan: Channel to receive interrupt notifications on
#   Returns: Cap to the IRQ object (for unbinding)
fn sys_irq_bind(irq_num: u32, chan: u32) -> CapResult

# Acknowledge an interrupt (allows next delivery)
fn sys_irq_ack(irq: u32) -> SysResult

# Unbind
fn sys_irq_unbind(irq: u32) -> SysResult
```

**Design notes:**
- Only Ring 1 (driver) contexts can bind interrupts. The kernel enforces this.
- Interrupt delivery is a **message on a channel**, not a signal. This means
  drivers use the same IPC mechanism for interrupts and normal messages.
- No shared interrupt lines — each IRQ is bound to exactly one channel.

### 2.6. IO Port / MMIO Object (`IoPort`)

Grants access to hardware I/O ports or memory-mapped I/O regions.

```ritz
# Grant I/O port access to a context
#   port_base: Starting I/O port
#   port_count: Number of consecutive ports
#   Returns: Cap with port access rights
fn sys_ioport_create(port_base: u16, port_count: u16) -> CapResult

# Grant MMIO region access
#   phys_addr: Physical address of MMIO region
#   size: Size in bytes
#   Returns: Cap to a MemRegion backed by physical MMIO
fn sys_mmio_create(phys_addr: u64, size: u64) -> CapResult
```

**Design notes:**
- Only the kernel can create `IoPort` and MMIO objects. They are granted to
  Ring 1 driver contexts during device initialization.
- This replaces Linux's `iopl()`/`ioperm()` with capability-gated access.

## 3. Capability Operations (Cross-cutting)

These syscalls work on any capability regardless of object type:

```ritz
# Reduce rights on a capability (create a less-powerful copy)
fn sys_cap_reduce(cap: u32, new_rights: u32) -> CapResult

# Duplicate a capability (same rights, new CSpace slot)
fn sys_cap_dup(cap: u32) -> CapResult

# Revoke all capabilities derived from this one
#   cap: Must have CAP_REVOKE right
#   This is TRANSITIVE — revokes all delegations recursively
fn sys_cap_revoke(cap: u32) -> SysResult

# Destroy a capability (release CSpace slot)
fn sys_cap_close(cap: u32) -> SysResult

# Inspect a capability (query rights and object type)
fn sys_cap_inspect(cap: u32, info: *CapInfo) -> SysResult

struct CapInfo
    object_type: u32     # OBJ_MEM, OBJ_CHAN, OBJ_EXEC, OBJ_IRQ, OBJ_IOPORT
    rights: u32          # Current rights bitmask
    generation: u32      # Revocation generation
    _reserved: u32

const OBJ_MEM: u32    = 1
const OBJ_CHAN: u32    = 2
const OBJ_EXEC: u32   = 3
const OBJ_IRQ: u32    = 4
const OBJ_IOPORT: u32 = 5

# Result types
struct CapResult
    cap: u32             # New capability handle (0 on error)
    error: u32           # Error code (0 = success)

struct AddrResult
    addr: u64            # Virtual address (0 on error)
    error: u32           # Error code

struct SysResult
    error: u32           # Error code (0 = success)

struct ExecResult
    exit_code: i32       # Context's exit code
    error: u32           # Error code

struct ChanPairResult
    end_a: u32           # First endpoint capability
    end_b: u32           # Second endpoint capability
    error: u32           # Error code
```

## 4. Syscall Table

The complete Harland syscall ABI. This is the **entire kernel surface**.

```
# Memory
0x00  sys_mem_create      (size, flags)              -> CapResult
0x01  sys_mem_map         (cap, vaddr, offset, size) -> AddrResult
0x02  sys_mem_unmap       (vaddr, size)              -> SysResult
0x03  sys_mem_grant       (cap, target, off, sz, r)  -> CapResult

# Channels
0x10  sys_chan_create      ()                         -> ChanPairResult
0x11  sys_chan_send        (chan, msg)                 -> SysResult
0x12  sys_chan_recv        (chan, msg)                 -> SysResult
0x13  sys_chan_call        (chan, req, reply)          -> SysResult

# Execution
0x20  sys_exec_create     ()                         -> CapResult
0x21  sys_exec_start      (exec, entry, stack, arg)  -> SysResult
0x22  sys_exec_stop       (exec)                     -> SysResult
0x23  sys_exec_wait       (exec)                     -> ExecResult
0x24  sys_exec_grant      (exec, cap, rights)        -> CapResult
0x25  sys_exec_set_budget (exec, budget)             -> SysResult

# Hardware (Ring 1 only)
0x30  sys_irq_bind        (irq_num, chan)             -> CapResult
0x31  sys_irq_ack         (irq)                      -> SysResult
0x32  sys_irq_unbind      (irq)                      -> SysResult
0x33  sys_ioport_create   (port_base, port_count)    -> CapResult
0x34  sys_mmio_create     (phys_addr, size)           -> CapResult

# Capability management
0x40  sys_cap_reduce      (cap, new_rights)           -> CapResult
0x41  sys_cap_dup         (cap)                       -> CapResult
0x42  sys_cap_revoke      (cap)                       -> SysResult
0x43  sys_cap_close       (cap)                       -> SysResult
0x44  sys_cap_inspect     (cap, info)                 -> SysResult

# Event loop
0x50  sys_wait_any        (caps, count, timeout)      -> WaitResult

# Debug (temporary, removed in production)
0xFF  sys_debug_print     (buf, len)                  -> SysResult
```

**Total: 22 syscalls.** Linux has 450+. seL4 has ~12.

### 4.1. Event Loop (`sys_wait_any`)

The missing piece — how does a process wait for events from multiple channels,
IRQs, or timers?

```ritz
# Wait for any of the given capabilities to become ready
#   caps: Array of capability handles to wait on
#   count: Number of capabilities in array
#   timeout_us: Timeout in microseconds (0 = no wait, -1 = forever)
fn sys_wait_any(caps: *u32, count: u32, timeout_us: i64) -> WaitResult

struct WaitResult
    ready_index: u32     # Index into caps[] that fired
    event_type: u32      # What happened (EVENT_READABLE, EVENT_WRITABLE, etc.)
    error: u32           # Error code

const EVENT_READABLE: u32  = 1  # Data available to read
const EVENT_WRITABLE: u32  = 2  # Space available to write
const EVENT_CLOSED: u32    = 4  # Remote endpoint closed
const EVENT_ERROR: u32     = 8  # Error on object
const EVENT_SIGNAL: u32    = 16 # Object was signaled
```

This is the equivalent of `epoll`/`kqueue`/`io_uring` — but operating on
capabilities, not file descriptors.

## 5. Boot Sequence with Capabilities

When Harland boots, the **init process** receives the initial set of
capabilities from the kernel:

```ritz
# The init process entry point receives a bootstrap channel
fn _start(bootstrap: u32)
    # bootstrap is a Cap to a channel connected to the kernel
    # First message contains the initial capability set:

    var msg: Message
    sys_chan_recv(bootstrap, @msg)

    # msg contains caps for:
    # [0] = Physical memory allocator (to create MemRegions)
    # [1] = IRQ controller (to bind interrupts)
    # [2] = IO port namespace (to create IoPort caps)
    # [3] = Init's own Exec cap (self-reference)

    let phys_mem: u32 = msg.caps[0]
    let irq_ctl: u32 = msg.caps[1]
    let io_ctl: u32 = msg.caps[2]
    let self_exec: u32 = msg.caps[3]

    # Init is now the root of all authority.
    # It delegates capabilities to drivers and services.
    # The kernel has NO further role in policy decisions.
```

### 5.1. Example: Starting a Serial Driver

```ritz
# Init creates a serial driver context
fn start_serial_driver(io_ctl: u32, irq_ctl: u32)
    # 1. Create execution context
    let driver_result = sys_exec_create()
    let driver: u32 = driver_result.cap

    # 2. Create a channel pair for communication
    let chan = sys_chan_create()

    # 3. Create memory for driver code + stack
    let code_region = sys_mem_create(4096 * 16, 0)  # 64KB for code
    let stack_region = sys_mem_create(4096 * 4, 0)   # 16KB for stack
    # ... load driver binary into code_region ...

    # 4. Grant ONLY what the driver needs:
    #    - Its code region (read + exec)
    #    - Its stack region (read + write)
    #    - IO ports 0x3F8-0x3FF (COM1) — NOTHING ELSE
    #    - IRQ 4 (COM1 interrupt)
    #    - One end of the communication channel
    sys_exec_grant(driver, code_region.cap, CAP_MAP | CAP_READ | CAP_EXEC)
    sys_exec_grant(driver, stack_region.cap, CAP_MAP | CAP_READ | CAP_WRITE)

    # Create IO port cap for JUST COM1 ports
    let com1_ports = sys_ioport_create(0x3F8, 8)
    sys_exec_grant(driver, com1_ports.cap, CAP_READ | CAP_WRITE)

    # Bind IRQ 4 to the driver's channel
    let irq4 = sys_irq_bind(4, chan.end_b)
    sys_exec_grant(driver, irq4.cap, CAP_READ | CAP_SIGNAL)

    # Give driver its channel endpoint
    sys_exec_grant(driver, chan.end_b, CAP_READ | CAP_WRITE)

    # 5. Start the driver
    let entry: u64 = 0x1000  # Driver entry point in its address space
    let stack: u64 = 0x8000  # Stack top
    sys_exec_start(driver, entry, stack, chan.end_b)

    # Init keeps chan.end_a — it can now send/recv with the driver
    # The driver has EXACTLY: COM1 ports, IRQ4, one channel, its own memory.
    # It cannot access any other hardware, any other process, or any other
    # resource. If it crashes, revoke its caps and restart it.
```

### 5.2. Revocation Example

```ritz
# A misbehaving driver — revoke all its capabilities
fn kill_driver(driver_exec: u32, driver_chan: u32)
    # Stop execution
    sys_exec_stop(driver_exec)

    # Revoke ALL capabilities derived from what we granted
    # This transitively revokes anything the driver delegated further
    sys_cap_revoke(driver_exec)

    # Destroy the execution context
    sys_cap_close(driver_exec)
    sys_cap_close(driver_chan)

    # The driver is gone. Its memory is freed. Its IRQ is unbound.
    # No global state was corrupted. Start a new one.
```

## 6. Comparison with Linux File Descriptors

| Aspect | Linux FDs | Harland Caps |
|--------|-----------|-------------|
| **What it represents** | Entry in per-process fd table | Entry in per-process CSpace |
| **Permissions** | Coarse (O_RDONLY/O_WRONLY/O_RDWR) at open time | Fine-grained rights bitmask, reducible at any time |
| **Delegation** | `sendmsg` SCM_RIGHTS (clunky) | `sys_chan_send` with cap transfer (first-class) |
| **Revocation** | Cannot revoke a sent fd | `sys_cap_revoke` — transitive, immediate |
| **Naming** | Global filesystem namespace | No global namespace — caps obtained via channels |
| **Ambient authority** | Yes (open("/etc/passwd") works if uid allows) | None — must hold a cap to access anything |
| **Privilege escalation** | setuid, capabilities(7), namespaces | Impossible — rights only reduce |
| **TOCTOU attacks** | `access()` + `open()` race | Atomic — cap check and operation are one step |

## 7. Interaction with Ritz Ownership Model

Capabilities have natural synergy with Ritz's ownership semantics:

```ritz
# A capability handle is a move-only type (like a Rust Box)
# Sending it on a channel MOVES it — the sender no longer has it
fn delegate_to_child(chan: u32, cap: u32)
    var msg: Message
    msg.caps[0] = cap       # cap moves into message
    msg.cap_count = 1
    sys_chan_send(chan, @msg)
    # `cap` is now invalid in this scope — ownership transferred

# To keep a copy, explicitly duplicate first
fn share_with_child(chan: u32, cap: u32)
    let copy = sys_cap_dup(cap)      # Explicit duplication
    var msg: Message
    msg.caps[0] = copy.cap           # Send the copy
    msg.cap_count = 1
    sys_chan_send(chan, @msg)
    # `cap` is still valid — we sent a duplicate
```

This means **capability leaks are prevented by the type system**. If you send
a cap on a channel, you can't accidentally use it afterward. The compiler
catches use-after-move at compile time.

## 8. What This Replaces

### 8.1. Gone (Linux concepts that don't exist in Harland)

- File descriptors → **Capability handles**
- open()/close() → **Caps granted via channels**
- read()/write() → **`sys_chan_send`/`sys_chan_recv`**
- mmap()/mprotect() → **`sys_mem_create`/`sys_mem_map`/`sys_mem_grant`**
- fork() → **`sys_exec_create` + explicit cap delegation**
- signals → **Channel messages**
- pipes → **Channels**
- sockets → **Channels** (network stack is a userspace service)
- ioctl() → **Channel-specific messages to device drivers**
- /dev, /proc, /sys → **Caps granted by init to those who need them**
- setuid/setgid → **Doesn't exist. Authority = held caps, nothing else.**
- SELinux/AppArmor → **Doesn't exist. The capability model IS the security.**
- namespaces/cgroups → **Exec budgets + hierarchical cap delegation**

### 8.2. Userspace Policy Layer

These are NOT kernel mechanisms. They're libraries/services built ON the
mechanisms:

```
# Userspace file service (like a VFS)
# Implements open/read/write/close as an IPC protocol over channels
# The kernel knows nothing about "files"

# Userspace network service
# Implements TCP/IP as an IPC protocol over channels
# The kernel knows nothing about "sockets" or "ports"

# Userspace process manager
# Implements supervision, restart policies, logging
# The kernel just provides Exec creation and cap delegation
```

## 9. Design Alternatives (from capability OS research)

### 9.1. Single Entry Point vs. Per-Object Syscalls

This spec uses per-object syscalls (`sys_mem_create`, `sys_chan_send`, etc.).
An alternative (closer to seL4) is a **single `handle_invoke(cap, op, args)`**
syscall where the kernel dispatches based on object type + op code. This is
more minimal (fewer syscalls) but less ergonomic for userspace.

**Recommendation**: Per-object syscalls for now. They're clearer, and the
syscall table is small enough (22) that the overhead of separate numbers is
negligible. Can unify later if needed.

### 9.2. Process vs. Thread Separation

This spec has `Exec` (execution context) as a single abstraction. Zircon
separates Process (address space + handle table) from Thread (execution within
a process). seL4 separates TCB from VSpace from CSpace.

**Recommendation**: Start with unified `Exec`. Split into Process + Thread
when SMP requires multiple threads sharing an address space. The split is
additive — it doesn't break the capability model.

### 9.3. Event Objects

Zircon has lightweight `Event` objects for signaling without full message
passing. seL4 has `Notification` objects (bit-ORing semantics). These avoid
the overhead of a full channel message for simple "wake up" signals.

**Recommendation**: Add if needed. `sys_wait_any` on channels covers most
cases. If profiling shows IPC overhead for simple signals, add an `Event`
primitive later.

## 10. Open Questions

1. **CSpace size**: Fixed-size (256 slots?) or dynamic? Fixed is simpler and
   deterministic. Dynamic allows more flexibility.

2. **Revocation strategy**: Three options from research:
   - **Generation counter** (O(1) but lazy — stale caps fail on next use)
   - **CDT walk** (seL4 — O(n), complete, needs preemption handling)
   - **Ref-counted + derived tracking** (Zircon-like — simple, handles most cases)
   Recommend: Generation counter for simplicity. seL4's CDT is beautiful but
   complex. Ref-counting misses transitive revocation.

3. **Channel buffering**: seL4 is synchronous (0 buffering — sender blocks
   until receiver reads). Zircon uses bounded queues. Recommend: configurable
   per-channel, default 16 messages. Sync IPC (seL4-style) is fastest but
   requires careful programming to avoid deadlocks.

4. **Large messages**: The 64-byte inline limit means large data needs a
   MemRegion cap. Zircon allows up to 64KB per channel message. Should we
   support larger inline payloads (256 bytes? 1 page?) or is MemRegion-based
   transfer always the answer for large data?

5. **Kernel memory accounting**: Who "pays" for kernel objects (CSpace entries,
   channel buffers, page tables)? seL4 solves this elegantly: all memory
   starts as Untyped caps, and creating objects consumes Untyped. Zircon
   tracks per-job. Recommend: Charged against the creating context's Budget.

6. **Multi-core**: Per-CPU CSpace caches? Lock-free channel queues? This needs
   careful design but doesn't change the mechanism primitives.

7. **Capability persistence**: EROS persists capabilities across reboots
   via periodic checkpointing. This adds significant kernel complexity (dirty
   page tracking, crash recovery). **Recommendation: No.** Persistence is a
   userspace concern (filesystem). Re-bootstrap from init on reboot.

8. **MMIO/IoPort as separate object?** seL4 treats MMIO as just Frames with
   uncacheable attributes. Zircon has Resource objects. We have both IoPort
   and MMIO as separate types. Consider unifying into a single `HwRegion`
   type with flags for port-I/O vs. memory-mapped.

9. **Address space hierarchy**: Zircon's VMAR model (hierarchical address
   space regions, delegatable) is more flexible than flat `sys_mem_map`.
   Consider whether Exec contexts need sub-region delegation for sandboxing.

---

## 10. Summary

**22 syscalls. 6 object types. Zero ambient authority.**

The kernel is a capability machine. It creates objects, manages handles,
transfers authority, and schedules computation. Everything else — files,
networks, devices, users, security policies — is userspace code built on
these primitives.

This is mechanism/policy separation taken to its logical conclusion.

## 12. Prior Art & References

| System | Key Insight Borrowed | What We Avoid |
|--------|---------------------|---------------|
| **seL4** | Complete policy separation. Untyped memory model. All operations are cap invocations. | CDT complexity. CSpace tree indirection overhead. |
| **Zircon (Fuchsia)** | Channel-pair IPC with handle move semantics. VMO/VMAR separation. Production-proven. | 300K LoC kernel. No forcible revocation of duplicated handles. |
| **FreeBSD Capsicum** | `cap_enter()` as one-way ambient authority removal. Monotonic right reduction. | POSIX-centric. No cap transfer. No revocation. Coarse-grained. |
| **EROS/CapROS** | Constructor pattern for controlled process creation. Forwarder-based revocation. | Persistence complexity. Fixed 16-slot nodes. No SMP. |
| **L4** | IPC-based everything. Map/grant/flush memory semantics. ~10KB kernel. | Thread-ID IPC (forgeable). Incomplete transitive revocation. |

**Harland combines:**
- Zircon's channel+handle model (best fit for Ritz ownership)
- seL4's policy-freedom principle (kernel never decides who gets what)
- L4's size discipline (target: <10KB kernel)
- EROS's insight that process creation is a delegation pattern, not a syscall
