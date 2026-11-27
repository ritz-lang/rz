# Harland Microkernel Architecture

## Design Philosophy

**Ultra-thin kernel, maximum delegation.**

Ring 0 should do the absolute minimum:
- Memory allocation (PMM)
- Page table management (VMM)
- Interrupt dispatch
- Ring transitions
- IPC primitives

Everything else runs outside ring 0, in user-mode processes at CPL 3.

## Ring Model

```
┌─────────────────────────────────────────────────────────────┐
│ Ring 0 - Microkernel (harland)                              │
│   • Physical memory allocator                               │
│   • Page table management                                   │
│   • Interrupt handlers (dispatch only)                      │
│   • IPC: ring buffers, capability tokens                    │
│   • Ring transitions (syscall interface)                    │
│   └─ ~5KB code, deterministic latency                       │
├─────────────────────────────────────────────────────────────┤
│ Ring 1 - Device Drivers                                     │
│   • Direct hardware access (MMIO; port I/O not granted)     │
│   • Interrupt handling (delegated from ring 0)              │
│   • NIC driver, storage drivers, etc.                       │
│   • Can modify ring buffers shared with ring 2/3            │
│   └─ Isolated per-driver, crash doesn't kill kernel         │
├─────────────────────────────────────────────────────────────┤
│ Ring 2 - System Services                                    │
│   • TCP/IP stack                                            │
│   • Filesystem                                              │
│   • Process manager                                         │
│   • Shared ring buffer access for IPC                       │
│   └─ Protected but fast transitions from ring 3             │
├─────────────────────────────────────────────────────────────┤
│ Ring 3 - User Applications                                  │
│   • Web client, shells, apps                                │
│   • Communicates via ring buffers to services               │
│   └─ Full isolation, capability-based access                │
└─────────────────────────────────────────────────────────────┘
```

> **Rings 1 and 2 are tiers, not CPU privilege levels** (decision D8 in
> [`RING1_DRIVER.md`](RING1_DRIVER.md)). Every non-kernel process, drivers and
> system services included, runs at CPL 3 in its own address space, with the
> kernel half mapped `U/S = 0`. What separates the tiers is the capabilities the
> kernel grants at spawn: a ring-1 driver gets its device's MMIO, IRQ and DMA
> capabilities, with device DMA fenced by an IOMMU domain; a ring-2 service gets
> the shared rings it serves. The reason is the hardware: every access at
> CPL < 3 is a supervisor-mode access (Intel SDM Vol 3 §4.6), and long mode has
> no segment limits, so a process below CPL 3 that shares the kernel half is
> not isolated from the kernel, and fencing it costs more than CPL 3 for the same
> result. seL4, QNX, MINIX 3 and Fuchsia run drivers and services the same way:
> user-mode processes with explicit grants. Harland adds no DPL-1/DPL-2
> descriptors; every process returns with `sysretq`.
>
> A tier is a set of grants, so one process may hold two. Network drivers
> live inside netd (decision D9): `/bin/netd` holds its NIC's ring-1 grants
> and the ring-2 service's, with the driver linked in as a library, because a
> separate driver process cost two extra switches per packet (#4768).

## IPC: Ring Buffers (Zeus/Valet Style)

Each connection/channel uses a **shared ring buffer**:

```
┌──────────────────────────────────────────┐
│ Ring Buffer (shared memory region)       │
│                                          │
│  ┌─────┬─────┬─────┬─────┬─────┬─────┐  │
│  │ msg │ msg │     │     │ msg │ msg │  │
│  └─────┴─────┴─────┴─────┴─────┴─────┘  │
│     ↑                       ↑            │
│   read_idx                write_idx      │
│                                          │
│  • Lock-free SPSC (single producer/      │
│    single consumer)                      │
│  • Ring transition just flips access bit │
│  • Zero-copy for large payloads          │
└──────────────────────────────────────────┘
```

**Ring transition for IPC:**
- Ring 3 app writes to buffer, triggers `syscall`
- Kernel flips page table bits (ring 3 → ring 2 readable)
- Ring 2 service processes, writes response
- Kernel flips bits back, returns to ring 3
- **No data copying**, just permission changes

> **Superseded.** The per-call page-table flip above is not the design.
> [`RING1_DRIVER.md`](RING1_DRIVER.md) uses persistent SPSC rings in
> `CAP_TYPE_SHM` regions, mapped once by `ShmMap` (227), so a message neither
> edits page tables nor shoots down the TLB.

## Networking Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Application                        │
│                     (Ring 3 - e.g., web client)             │
│                              │                              │
│                    ┌─────────▼─────────┐                    │
│                    │   Ring Buffer     │                    │
│                    │   (TX/RX queues)  │                    │
│                    └─────────┬─────────┘                    │
├──────────────────────────────┼──────────────────────────────┤
│                     TCP/IP Stack                            │
│                     (Ring 2 - system service)               │
│                              │                              │
│  • Connection state machine  │  • Retransmission            │
│  • Congestion control        │  • Checksum validation       │
│                    ┌─────────▼─────────┐                    │
│                    │   Ring Buffer     │                    │
│                    │   (packet queues) │                    │
│                    └─────────┬─────────┘                    │
├──────────────────────────────┼──────────────────────────────┤
│                     NIC Driver                              │
│                     (Ring 1 - device driver)                │
│                              │                              │
│  • DMA setup                 │  • Interrupt handling        │
│  • Descriptor rings          │  • MMIO access               │
│                              ▼                              │
│                    ┌───────────────────┐                    │
│                    │   virtio-net      │                    │
│                    │   (or e1000)      │                    │
│                    └───────────────────┘                    │
├─────────────────────────────────────────────────────────────┤
│                     Microkernel (Ring 0)                    │
│  • Interrupt dispatch to NIC driver                         │
│  • Page table updates for ring buffer sharing               │
│  • DMA buffer allocation                                    │
└─────────────────────────────────────────────────────────────┘
```

## Milestone Roadmap to TCP/IP

> **Historical.** Phases 1–4 below are the original plan. Much of that work now
> exists, all of it in ring 0: LAPIC, I/O APIC, AP startup, per-CPU data,
> preemptive scheduling (AGAST #3629), ring-3 syscalls (`syscall` entry,
> `iretq` return, not SYSRET), capabilities, and an in-kernel virtio-net
> driver. Ring-1 drivers are designed in [`RING1_DRIVER.md`](RING1_DRIVER.md).
> That design grants MMIO, DMA and IRQ wait but not port I/O. User processes
> on the APs (pinned first), the big kernel lock and TLB shootdown are
> designed in [`SMP_USER.md`](SMP_USER.md).

### Phase 1: Multi-core & APIC
1. **Local APIC initialization**
2. **I/O APIC for interrupt routing**
3. **AP (Application Processor) startup**
4. **Per-CPU data structures**
5. **Basic spinlocks**

### Phase 2: Scheduler & Processes
1. **Process/thread structures**
2. **Context switching**
3. **Round-robin scheduler**
4. **Ring 3 transitions (SYSRET/SYSCALL)**
5. **Basic syscall interface**

### Phase 3: IPC & Ring Buffers
1. **Ring buffer primitive**
2. **Capability tokens**
3. **Ring 1/2/3 transitions** (superseded: every process is CPL 3, and the tiers
   are capabilities; see the ring model note)
4. **Shared memory regions**
5. **Async notification (signal/wait)**

### Phase 4: Device Driver Framework
1. **Driver isolation model**
2. **MMIO access from ring 1** (port I/O is not granted)
3. **Interrupt delegation**
4. **DMA buffer management**
5. **virtio-net driver (QEMU)**

### Phase 5: TCP/IP Stack (Ring 2 Service)
1. **Ethernet frame handling**
2. **ARP**
3. **IPv4**
4. **ICMP (ping)**
5. **UDP**
6. **TCP**

### Phase 6: User Application
1. **Simple HTTP client**
2. **DNS resolution**
3. **TLS (using cryptosec)**
4. **Fetch a web page!**

## QEMU Configuration

```bash
qemu-system-x86_64 \
    -cpu host -enable-kvm \
    -smp 2 \                          # 2 cores for SMP testing
    -m 1G \                           # 1GB RAM
    -netdev user,id=net0,hostfwd=tcp::8080-:80 \
    -device virtio-net-pci,netdev=net0 \
    -serial stdio \
    -cdrom harland.iso
```

## Security Model

**Capability-based access control:**
- No global namespaces
- Resources accessed via unforgeable tokens
- Tokens passed via IPC
- Revocation through kernel

**Isolation guarantees:**
- Ring 1 driver crash → restart driver, not kernel
- Ring 2 service crash → restart service
- Ring 3 app crash → just that app
- Only ring 0 crash is fatal

## Performance Targets

- **Syscall latency**: < 100 cycles (ring transition)
- **IPC latency**: < 500 cycles (ring buffer notify)
- **Interrupt latency**: < 1µs (APIC dispatch)
- **Context switch**: < 2µs

## Code Size Targets

- Ring 0 kernel: < 10KB
- Per-driver overhead: < 1KB
- TCP/IP stack: < 50KB
- Total system (to TCP): < 100KB
