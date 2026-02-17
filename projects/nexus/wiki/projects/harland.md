# Harland

*"Ritzy from bare metal to user space."*

IPC-based microkernel for x86-64, written in Ritz. Active development.

---

## Overview

Harland is an operating system kernel built from scratch in Ritz. It demonstrates that Ritz's ownership semantics, compile-time safety, and performance are sufficient for the most demanding environment: bare metal x86-64 with no C runtime.

Harland follows the microkernel philosophy: the kernel provides only the minimal set of services needed for isolation and communication. Filesystems, device drivers, and network stacks all run as user-space processes communicating via IPC.

---

## Where It Fits

```
User Space Applications
    ├── rzsh (shell)
    ├── Goliath (filesystem server)
    ├── Prism (display server)
    └── Network daemon
         │
         │ IPC (capability-based message passing)
         ▼
┌────────────────────────────────────┐
│          HARLAND MICROKERNEL       │
│                                    │
│  Scheduler │ IPC │ VMM │ Interrupts│
└────────────────────────────────────┘
         │
   x86-64 Hardware
```

---

## Core Components

### Virtual Memory Manager (VMM)

Harland uses 4-level x86-64 page tables (PML4 → PDPT → PD → PT), supporting a 256TB virtual address space per process.

- Physical frame allocator (bitmap-based)
- Copy-on-write page semantics
- Demand paging
- LA57 (5-level paging for 128PB) as future enhancement

### Preemptive Scheduler

- Priority-based with O(1) run queue operations
- SMP-aware with per-CPU run queues
- Work-stealing for load balancing across cores
- Cooperative yield available for latency-sensitive tasks

### IPC Subsystem

Harland uses L4-style synchronous message passing as the primary IPC mechanism:

- **Synchronous calls** — Caller blocks until reply, enabling direct stack switch optimization
- **Async channels** — Ring buffer channels for high-throughput bulk data transfer
- **Capabilities** — Every IPC endpoint is a capability. Untrusted code cannot forge capabilities.

### Interrupt Handling

- Local APIC configuration and timer interrupts
- IOAPIC for legacy device interrupts
- MSI-X for modern PCIe devices
- IST (Interrupt Stack Table) for safe NMI and double-fault handling

---

## Boot Sequence

### Boot Media Layout

```
Disk (qcow2 or NVMe)
├── EFI System Partition (FAT32)
│   └── EFI/BOOT/BOOTX64.EFI    # UEFI bootloader (Stage 1)
└── Harland Boot Partition
    ├── harland.elf               # Kernel ELF
    └── initrd.tar                # Initial ramdisk
```

### Boot Stages

| Stage | Mode | Responsibility |
|-------|------|----------------|
| **Stage 0** | UEFI firmware | Loads BOOTX64.EFI from EFI partition |
| **Stage 1** | UEFI app (64-bit) | Gets memory map, loads kernel, exits boot services |
| **Stage 2** | Kernel entry | Sets up GDT, IDT, paging, APIC, serial |
| **Running** | Kernel mode | Full microkernel operation |

---

## Ritz Language Extensions for Kernel Programming

Harland requires features beyond standard Ritz. These have been added to the language:

### Inline Assembly

```ritz
fn load_cr3(pml4: u64)
    asm x86_64:
        mov cr3, {pml4}

fn outb(port: u16, value: u8)
    asm x86_64:
        mov dx, {port}
        mov al, {value}
        out dx, al

fn inb(port: u16) -> u8
    var result: u8
    asm x86_64:
        mov dx, {port}
        in al, dx
        mov {result}, al
    result
```

### Naked Functions (No Prologue/Epilogue)

```ritz
@naked
fn interrupt_handler_common()
    asm x86_64:
        push rax
        push rbx
        # ... save all registers
        mov rdi, rsp
        call handle_interrupt
        # ... restore all registers
        iretq
```

### Volatile MMIO

```ritz
@volatile
fn mmio_write32(addr: *u32, value: u32)
    *addr = value
```

### Packed Structs

```ritz
@packed
struct GDTEntry
    limit_low: u16
    base_low: u16
    base_mid: u8
    access: u8
    flags_limit: u8
    base_high: u8
    # Exactly 8 bytes — no compiler padding
```

---

## Page Table Example

```ritz
fn translate(pml4: *PageTable, virtual: u64) -> u64
    let pml4_idx = (virtual >> 39) and 0x1FF
    let pdpt_idx = (virtual >> 30) and 0x1FF
    let pd_idx   = (virtual >> 21) and 0x1FF
    let pt_idx   = (virtual >> 12) and 0x1FF
    let offset   = virtual and 0xFFF

    let pdpt = pml4[pml4_idx].physical_addr()
    let pd   = pdpt[pdpt_idx].physical_addr()
    let pt   = pd[pd_idx].physical_addr()
    let page = pt[pt_idx].physical_addr()

    page or offset
```

---

## Development Strategy

### Testing Pyramid

| Level | Environment | Scope |
|-------|-------------|-------|
| Unit tests | Host Linux | Pure functions, data structures |
| Integration tests | QEMU headless | Page tables, interrupts |
| System tests | QEMU full | Full boot, IPC, user processes |

Unit tests run on the host — no QEMU needed. This makes the TDD cycle fast.

### Build Targets

```bash
make build        # Compile all Ritz sources
make qcow2        # Create bootable disk image
make run          # Boot in QEMU
make test         # Run all tests
make test-unit    # Host-only unit tests (fast)
make test-qemu    # QEMU integration tests
```

---

## Non-Goals

Harland is not:

- POSIX compatible — custom syscall ABI
- Linux compatible — no /proc, no systemd, no ELF dynamic linking
- Backwards compatible with legacy hardware — requires UEFI, no BIOS boot
- Supporting 32-bit — 64-bit x86 only

---

## Roadmap

| Phase | Focus |
|-------|-------|
| 1 | UEFI bootloader, basic paging, serial output |
| 2 | GDT/IDT, physical frame allocator, kernel heap |
| 3 | APIC, timer interrupt, scheduler, context switching |
| 4 | Ring 3, syscall interface, init process, basic IPC |
| 5 | VirtIO block, VirtIO network, PS/2 keyboard |

---

## Current Status

Active development. New Ritz syntax (`--syntax reritz`) migration in progress.

---

## Related Projects

- [Goliath](goliath.md) — Content-addressable filesystem running on Harland
- [Prism](prism.md) — Display server running as a Harland user process
- [rzsh](rzsh.md) — Shell running on Harland
- [Kernel Subsystem](../subsystems/kernel.md)
