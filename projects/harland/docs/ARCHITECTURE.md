# Harland Microkernel Architecture

## Design Philosophy

**Ultra-thin kernel, maximum delegation.**

Ring 0 should do the absolute minimum:
- Memory allocation (PMM)
- Page table management (VMM)
- Interrupt dispatch
- Ring transitions
- IPC primitives

Everything else runs in lower privilege rings.

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
│   • Direct hardware access (MMIO, port I/O)                 │
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

### Phase 1: Multi-core & APIC (Current Focus)
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
3. **Ring 1/2/3 transitions**
4. **Shared memory regions**
5. **Async notification (signal/wait)**

### Phase 4: Device Driver Framework
1. **Driver isolation model**
2. **MMIO/port access from ring 1**
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
