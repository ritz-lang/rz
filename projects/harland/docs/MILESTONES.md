# Harland Development Milestones

## Goal: Working TCP/IP Stack with Web Client

Split into 10 logical chunks, each independently testable.

---

## ✅ Completed Milestones

### M1: Hello Kernel World
- [x] Multiboot2 boot
- [x] Serial output
- [x] Inline assembly

### M2: GDT/IDT/Exceptions
- [x] GDT with TSS
- [x] IDT with exception handlers
- [x] PIC remapping

### M3: Physical Memory
- [x] Multiboot2 memory map parsing
- [x] Bitmap allocator
- [x] Page allocation/free

### M4: Virtual Memory
- [x] 4-level page table walking
- [x] Map/unmap pages
- [x] virt_to_phys translation

### M5: Kernel Heap
- [x] kalloc/kfree
- [x] First-fit free list
- [x] Dynamic expansion

---

## Upcoming Milestones

### M6: APIC & Multi-core
**Goal**: Boot 2 CPUs, handle interrupts via APIC

**Tasks**:
1. Parse ACPI tables (MADT) for APIC info
2. Initialize Local APIC
3. Initialize I/O APIC
4. Disable legacy PIC (mask all, remap done)
5. Route interrupts through I/O APIC
6. Send INIT/SIPI to wake AP (2nd core)
7. Per-CPU kernel stacks
8. Basic spinlock primitive
9. AP reaches idle loop

**Test**: Both cores print to serial with CPU ID

**QEMU**: `-smp 2 -m 1G`

---

### M7: Scheduler & Context Switching
**Goal**: Preemptive multitasking, kernel threads

**Tasks**:
1. Thread control block (TCB) structure
2. Kernel thread creation
3. Context switch (save/restore regs)
4. APIC timer for preemption
5. Run queue (per-CPU)
6. Round-robin scheduling
7. Thread sleep/wake primitives
8. Idle thread per CPU

**Test**: Multiple kernel threads printing interleaved output

---

### M8: User Space & Syscalls
**Goal**: Ring 3 execution, syscall interface

**Tasks**:
1. User-mode page tables (PTE_USER flag)
2. SYSCALL/SYSRET MSR setup
3. Syscall dispatcher
4. Basic syscalls: exit, write, yield
5. User stack allocation
6. First user process (embedded ELF)
7. Ring 0 → Ring 3 transition

**Test**: User program prints "Hello from Ring 3!"

---

### M9: IPC & Ring Buffers
**Goal**: Zero-copy communication between rings

**Tasks**:
1. Ring buffer data structure
2. Shared memory region allocation
3. Capability token system (simple handles)
4. Channel create/destroy syscalls
5. send/recv syscalls (pointer + length)
6. Page permission flipping for ring transitions
7. Async notification (futex-style)
8. Ring 2 service framework

**Test**: Ring 3 app ↔ Ring 2 service ping-pong benchmark

---

### M10: Device Driver Framework
**Goal**: Isolated drivers in Ring 1

**Tasks**:
1. Ring 1 page table setup
2. Driver process structure
3. MMIO region mapping to driver
4. Port I/O permission bitmap (IOPB in TSS)
5. Interrupt delegation (kernel → driver notification)
6. DMA buffer allocation (contiguous physical)
7. Driver ↔ kernel protocol
8. virtio-net driver skeleton

**Test**: Driver receives interrupt, prints packet count

---

### M11: virtio-net Driver
**Goal**: Send and receive Ethernet frames

**Tasks**:
1. virtio PCI device enumeration
2. virtqueue setup (descriptor tables)
3. DMA buffer pool
4. TX path: queue packet, kick device
5. RX path: handle used buffers
6. Interrupt handling for completion
7. Frame delivery to TCP/IP service
8. Basic stats (packets in/out)

**Test**: Receive broadcast packets, print MACs

---

### M12: Network Stack - Link/IP Layer
**Goal**: ARP and IPv4

**Tasks**:
1. Ethernet frame parsing
2. ARP request/response
3. ARP cache
4. IPv4 header parsing
5. IPv4 checksum
6. ICMP echo (ping) request/response
7. IP routing (single default gateway)
8. Ring buffer interface to driver

**Test**: `ping` from host to VM works

---

### M13: Network Stack - TCP
**Goal**: TCP connections

**Tasks**:
1. TCP header parsing
2. Connection state machine
3. Sequence number handling
4. SYN/SYN-ACK/ACK handshake
5. Data transmission
6. ACK handling
7. Retransmission (simple timeout)
8. Connection teardown (FIN)
9. Socket-like API for apps

**Test**: TCP echo server, connect from host with netcat

---

### M14: HTTP Client
**Goal**: Fetch a web page!

**Tasks**:
1. DNS resolution (UDP to 8.8.8.8)
2. HTTP/1.1 GET request
3. Response parsing
4. Chunked transfer handling
5. Connection reuse
6. User-space application
7. Print page content to serial

**Test**: Fetch http://example.com and print HTML

**Stretch**:
- TLS using cryptosec
- Fetch Wikipedia page

---

## Milestone Dependencies

```
M1-M5 (done)
    │
    ▼
   M6 ──────────────────┐
 (APIC)                 │
    │                   │
    ▼                   │
   M7                   │
(Scheduler)             │
    │                   │
    ▼                   │
   M8 ◄─────────────────┤
(User Space)            │
    │                   │
    ▼                   │
   M9 ◄─────────────────┘
  (IPC)
    │
    ├────────┐
    ▼        ▼
  M10       M12
(Drivers) (Net Stack)
    │        │
    ▼        │
  M11       │
(virtio)    │
    │        │
    └────┬───┘
         ▼
       M13
      (TCP)
         │
         ▼
       M14
     (HTTP)
```

---

## Quick Reference: Ring Assignments

| Component | Ring | Why |
|-----------|------|-----|
| Memory allocator | 0 | Page tables are ring 0 only |
| Interrupt dispatch | 0 | IDT requires ring 0 |
| IPC primitives | 0 | Permission bit flipping |
| Context switch | 0 | TSS/segment manipulation |
| NIC driver | 1 | Direct hardware access |
| Storage driver | 1 | Direct hardware access |
| TCP/IP stack | 2 | Shared buffers, no hardware |
| Filesystem | 2 | Coordinates storage access |
| Applications | 3 | Fully isolated |

---

## QEMU Test Configuration

```bash
# Development (2 cores, 1GB, virtio-net)
qemu-system-x86_64 \
    -enable-kvm \
    -cpu host \
    -smp 2 \
    -m 1G \
    -netdev user,id=n0,hostfwd=tcp::8080-:80 \
    -device virtio-net-pci,netdev=n0 \
    -cdrom build/harland.iso \
    -serial stdio \
    -display none

# Debug (with GDB)
qemu-system-x86_64 \
    -enable-kvm \
    -cpu host \
    -smp 2 \
    -m 1G \
    -netdev user,id=n0 \
    -device virtio-net-pci,netdev=n0 \
    -cdrom build/harland.iso \
    -serial stdio \
    -display none \
    -s -S  # GDB on :1234
```
