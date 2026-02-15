# Harland: A Ritz Microkernel

> *"Ritzy from bare metal to user space"*

## Vision

Harland is a microkernel operating system written in Ritz, designed to showcase the language's ownership semantics, compile-time safety, and performance characteristics in the most demanding environment: bare metal x86-64.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Target** | Both QEMU/KVM and real hardware | Primary iteration on QEMU, validated on EC2/bare metal |
| **Bootloader** | Written in Ritz | Dogfood from Stage 1, inspired by BOOTBOOT |
| **Paging** | 4-level (PML4) | 256TB address space is plenty; LA57 as future enhancement |
| **Inline ASM** | `asm x86_64:` block syntax | Indented assembly with Ritz variable interpolation |
| **Architecture** | Microkernel | IPC-based, drivers in user space |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Space                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │  Shell  │  │   VFS   │  │  NetD   │  │ Drivers │            │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘            │
│       │            │            │            │                  │
│       └────────────┴─────┬──────┴────────────┘                  │
│                          │ IPC (message passing)                │
├──────────────────────────┼──────────────────────────────────────┤
│  ┌───────────────────────┴───────────────────────────────────┐  │
│  │                    HARLAND MICROKERNEL                    │  │
│  │                                                           │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │  │
│  │  │ Scheduler│ │  IPC     │ │  VMM     │ │ Interrupts   │  │  │
│  │  │ (preempt)│ │ (async)  │ │ (4-level)│ │ (APIC/IOAPIC)│  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Core Microkernel Components

### 1. Virtual Memory Manager (VMM)
- 4-level page tables (PML4 → PDPT → PD → PT)
- LA57 (5-level) support as optional enhancement
- Physical frame allocator (buddy or bitmap)
- Copy-on-write for `fork()`-like semantics

### 2. Scheduler
- Preemptive, priority-based
- SMP-aware (per-CPU run queues)
- O(1) scheduling with priority queues

### 3. IPC
- Synchronous message passing (L4-style)
- Async channels for bulk data
- Capability-based security

### 4. Interrupt Handling
- Local APIC configuration
- IOAPIC for device interrupts
- MSI-X support for modern devices

## Boot Sequence

### qcow2 Image Layout

```
Sector 0         │ GPT Header
Partition 1      │ EFI System Partition (FAT32)
                 │   └─ EFI/BOOT/BOOTX64.EFI  (Stage 1 Ritz)
Partition 2      │ Harland Boot Partition
                 │   ├─ harland.elf           (Kernel)
                 │   └─ initrd.tar            (Initial ramdisk)
```

### Boot Stages

| Stage | Mode | Responsibility |
|-------|------|----------------|
| **Stage 0** | UEFI Firmware | Load BOOTX64.EFI |
| **Stage 1** | 64-bit UEFI App | Get memory map, load kernel, exit boot services |
| **Stage 2** | 64-bit Kernel | Setup paging, GDT, IDT, APIC |
| **Running** | 64-bit | Full microkernel operation |

## Ritz Language Extensions for Kernel

### Already Available
- Ownership/borrowing (`ref`, `mut`, move)
- `@class` with typed fields
- Operator overloading
- `ptr[T]` typed pointers
- `alloc`/`free`/`load_int`/`store_int`

### Need to Add

#### 1. Inline Assembly (`asm` blocks)

The `asm` keyword introduces an indented block of raw assembly. Variables from the surrounding Ritz scope can be interpolated using `{varname}` syntax. The compiler handles register allocation automatically.

```ritz
# Simple single instruction
load_cr3(pml4: u64):
    asm x86_64:
        mov cr3, {pml4}

# Multi-line with variable interpolation
outb(port: u16, value: u8):
    asm x86_64:
        mov dx, {port}
        mov al, {value}
        out dx, al

# Return values via named outputs
inb(port: u16) -> u8:
    result: u8
    asm x86_64:
        mov dx, {port}
        in al, dx
        mov {result}, al
    return result

# Complex example: GDT load
load_gdt(gdt_ptr: ptr[GDTDescriptor]):
    asm x86_64:
        lgdt [{gdt_ptr}]
        # Reload segments
        mov ax, 0x10        # Kernel data segment
        mov ds, ax
        mov es, ax
        mov fs, ax
        mov gs, ax
        mov ss, ax
        # Far jump to reload CS
        push 0x08           # Kernel code segment
        lea rax, [rip + .reload_cs]
        push rax
        retfq
    .reload_cs:
        # Now running with new GDT
```

**Compiler behavior:**
- `{varname}` → compiler picks register or memory reference
- Local labels with `.name` syntax
- Clobber analysis automatic (compiler tracks which registers are modified)
- Intel syntax by default (can specify `asm x86_64 att:` for AT&T)

#### 2. Naked Functions

Functions with `@naked` have no compiler-generated prologue/epilogue. You're responsible for everything.

```ritz
@naked
interrupt_handler_common():
    asm x86_64:
        # Save all registers
        push rax
        push rbx
        push rcx
        push rdx
        push rsi
        push rdi
        push rbp
        push r8
        push r9
        push r10
        push r11
        push r12
        push r13
        push r14
        push r15

        # Call Ritz handler with pointer to saved state
        mov rdi, rsp
        call handle_interrupt

        # Restore all registers
        pop r15
        pop r14
        pop r13
        pop r12
        pop r11
        pop r10
        pop r9
        pop r8
        pop rbp
        pop rdi
        pop rsi
        pop rdx
        pop rcx
        pop rbx
        pop rax

        iretq
```

#### 3. Volatile MMIO

The `@volatile` attribute ensures reads/writes are never optimized away or reordered.

```ritz
@volatile
mmio_read32(addr: ptr[u32]) -> u32:
    return *addr

@volatile
mmio_write32(addr: ptr[u32], value: u32):
    *addr = value

# Example: APIC register access
LAPIC_BASE: u64 = 0xFEE0_0000

lapic_read(reg: u32) -> u32:
    addr = (LAPIC_BASE + reg) as ptr[u32]
    return mmio_read32(addr)

lapic_write(reg: u32, value: u32):
    addr = (LAPIC_BASE + reg) as ptr[u32]
    mmio_write32(addr, value)
```

#### 4. Extended Integer Types

```ritz
# Unsigned integers
u8      # 8-bit unsigned (0 to 255)
u16     # 16-bit unsigned
u32     # 32-bit unsigned
u64     # 64-bit unsigned

# Signed integers
i8      # 8-bit signed (-128 to 127)
i16     # 16-bit signed
i32     # 32-bit signed
i64     # 64-bit signed

# Pointer-sized (64-bit on x86-64)
usize   # Unsigned pointer-sized
isize   # Signed pointer-sized

# Explicit casts required for narrowing
x: u64 = 0x1234_5678_9ABC_DEF0
y: u32 = x as u32              # 0x9ABC_DEF0 (truncated)
z: u8 = (x & 0xFF) as u8       # 0xF0
```

#### 5. Packed Structs

`@packed` removes all padding—fields are laid out exactly as specified.

```ritz
@packed @class
GDTEntry:
    limit_low: u16      # Offset 0
    base_low: u16       # Offset 2
    base_mid: u8        # Offset 4
    access: u8          # Offset 5
    flags_limit: u8     # Offset 6
    base_high: u8       # Offset 7
    # Total: 8 bytes, no padding

@packed @class
GDTDescriptor:
    size: u16           # Offset 0
    offset: u64         # Offset 2 (NOT aligned!)
    # Total: 10 bytes

@packed @class
IDTEntry:
    offset_low: u16     # Offset 0
    selector: u16       # Offset 2
    ist: u8             # Offset 4
    type_attr: u8       # Offset 5
    offset_mid: u16     # Offset 6
    offset_high: u32    # Offset 8
    zero: u32           # Offset 12
    # Total: 16 bytes
```

#### 6. Bitfield Support (Nice to Have)

For hardware registers with bit-level fields:

```ritz
@bitfield @class
PageTableEntry:
    present: bool @ 0           # Bit 0
    writable: bool @ 1          # Bit 1
    user: bool @ 2              # Bit 2
    write_through: bool @ 3     # Bit 3
    cache_disable: bool @ 4     # Bit 4
    accessed: bool @ 5          # Bit 5
    dirty: bool @ 6             # Bit 6
    huge: bool @ 7              # Bit 7
    global_: bool @ 8           # Bit 8
    _reserved: u3 @ 9           # Bits 9-11
    addr: u40 @ 12              # Bits 12-51 (physical address >> 12)
    _reserved2: u11 @ 52        # Bits 52-62
    no_execute: bool @ 63       # Bit 63
```

## Example: Page Table Entry in Ritz

```ritz
@class
PageTableEntry:
    raw: u64 = 0

    @property
    present() -> bool:
        return (raw & 1) != 0

    @property
    physical_addr() -> u64:
        return raw & 0x000F_FFFF_FFFF_F000

    set_addr(addr: u64, flags: PageFlags):
        raw = (addr & 0x000F_FFFF_FFFF_F000) | flags.bits
```

## Example: 4-Level Page Walk

```ritz
translate(pml4: ptr[PageTable], virtual: u64) -> u64:
    pml4_idx = (virtual >> 39) & 0x1FF
    pdpt_idx = (virtual >> 30) & 0x1FF
    pd_idx = (virtual >> 21) & 0x1FF
    pt_idx = (virtual >> 12) & 0x1FF
    offset = virtual & 0xFFF

    pdpt = pml4[pml4_idx].physical_addr()
    pd = pdpt[pdpt_idx].physical_addr()
    pt = pd[pd_idx].physical_addr()
    page = pt[pt_idx].physical_addr()

    return page | offset
```

## TDD Strategy

### Testing Pyramid

| Level | Environment | Focus |
|-------|-------------|-------|
| **Unit** | Host Linux | Pure functions, data structures |
| **Integration** | QEMU headless | Page tables, interrupts, drivers |
| **System** | QEMU full | Boot, IPC, user processes |

### Example Unit Test

```ritz
@test
test_page_table_entry_flags():
    entry = PageTableEntry()
    entry.set_addr(0x1000, PRESENT | WRITABLE | USER)

    assert entry.present() == true
    assert entry.writable() == true
    assert entry.user_accessible() == true
    assert entry.physical_addr() == 0x1000
```

### Example Integration Test

```ritz
@test @integration
test_page_fault_handler():
    # Map read-only page
    map_page(0xDEAD_0000, 0x1000, READ_ONLY)

    # Install test handler
    old_handler = install_fault_handler(test_handler)

    # Trigger fault
    @asm("mov dword ptr [0xDEAD_0000], 42")

    # Verify
    assert fault_count == 1
    assert fault_was_write == true
```

## SIMD/AVX Opportunities

| Operation | Instruction Set | Use Case |
|-----------|-----------------|----------|
| Page zeroing | AVX-512 | 64 bytes/instruction |
| Memory copy | AVX2 + NT stores | DMA buffers |
| Checksum | AVX2 | TCP/IP |
| Crypto | AES-NI | Disk encryption |

```ritz
@simd @target("avx512f")
zero_page(page: ptr[u8]):
    zero = @asm("vpxorq zmm0, zmm0, zmm0")
    for offset in range(0, 4096, 64):
        @asm("vmovntdq [{page} + {offset}], zmm0")
    @asm("sfence")
```

## Non-Requirements

- **Not POSIX compliant** (custom syscall ABI)
- **Not Linux compatible** (no /proc, no systemd)
- **No legacy hardware** (no BIOS, no 32-bit)
- **No dynamic linking** (static only)
- **No self-hosting** (compiler stays on host)

## Directory Structure

```
harland/
├── boot/
│   ├── stage1.ritz          # UEFI bootloader
│   └── linker.ld             # Stage 1 linker script
├── kernel/
│   ├── main.ritz             # Kernel entry point
│   ├── mm/
│   │   ├── page_table.ritz   # Page table management
│   │   ├── frame.ritz        # Physical frame allocator
│   │   └── heap.ritz         # Kernel heap
│   ├── sched/
│   │   ├── scheduler.ritz    # Task scheduling
│   │   └── process.ritz      # Process management
│   ├── ipc/
│   │   └── message.ritz      # IPC primitives
│   ├── arch/
│   │   └── x86_64/
│   │       ├── gdt.ritz      # Global Descriptor Table
│   │       ├── idt.ritz      # Interrupt Descriptor Table
│   │       ├── apic.ritz     # APIC drivers
│   │       └── cpu.ritz      # CPU feature detection
│   └── linker.ld             # Kernel linker script
├── user/
│   └── init/
│       └── main.ritz         # First user process
├── tests/
│   ├── unit/
│   └── integration/
├── tools/
│   └── mkimage.py            # qcow2 builder
├── Makefile
├── DESIGN.md                 # This file
├── TODO.md                   # Current work items
└── DONE.md                   # Completed work
```

## Build System

```makefile
# Key targets
make build        # Compile all Ritz → LLVM IR → objects → ELF
make qcow2        # Create bootable qcow2 image
make run          # Boot in QEMU
make test         # Run all tests
make test-unit    # Host-only unit tests
make test-qemu    # QEMU integration tests
```

## Roadmap

### Phase 1: Foundation
- [ ] Ritz x86-64 backend (LLVM target)
- [ ] Inline assembly support
- [ ] Extended integer types (u8..u64)
- [ ] Packed struct support
- [ ] UEFI Stage 1 bootloader

### Phase 2: Kernel Core
- [ ] GDT/IDT setup
- [ ] Page table implementation
- [ ] Physical frame allocator
- [ ] Kernel heap
- [ ] Serial console output

### Phase 3: Interrupts & Scheduling
- [ ] Local APIC setup
- [ ] Timer interrupt
- [ ] Basic scheduler
- [ ] Context switching

### Phase 4: User Space
- [ ] Ring 3 transitions
- [ ] Syscall interface
- [ ] Init process
- [ ] Basic IPC

### Phase 5: Drivers
- [ ] VirtIO block
- [ ] VirtIO network
- [ ] PS/2 keyboard

## References

- [OSDev Wiki](https://wiki.osdev.org/)
- [Intel SDM](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)
- [UEFI Specification](https://uefi.org/specifications)
- [L4 Microkernel](https://en.wikipedia.org/wiki/L4_microkernel_family)
- [seL4 Reference](https://sel4.systems/)
