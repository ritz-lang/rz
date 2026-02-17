# Harland

A microkernel operating system written in Ritz, designed for portability and clean syscall abstraction.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Harland is a microkernel written entirely in Ritz, designed to demonstrate the language's suitability for the most demanding systems programming tasks: bare metal x86-64 kernel development. The kernel handles virtual memory management, process scheduling, IPC message passing, interrupt handling, and syscall dispatch.

The project includes a UEFI bootloader also written in Ritz, making the entire boot chain from firmware to kernel a Ritz-only codebase. The kernel targets QEMU/KVM for development iteration and real hardware (EC2, bare metal) for validation.

Harland uses a capability-based microkernel architecture inspired by L4. Drivers and most system services run in user space and communicate via IPC. The Indium distribution builds on Harland, providing the init system, shell, and basic utilities.

## Features

- x86-64 microkernel with 4-level page tables (PML4)
- UEFI bootloader written in Ritz
- Preemptive priority-based scheduler with SMP support
- L4-style synchronous IPC with async bulk channels
- Capability-based security model
- Local APIC and IOAPIC interrupt handling
- Virtual memory manager with copy-on-write
- GOP framebuffer driver for UEFI graphics
- Syscall abstraction layer for multi-platform portability
- Assembly integration via `asm x86_64:` block syntax with Ritz variable interpolation

## Installation

```bash
# Install dependencies
apt-get install qemu-system-x86 grub-efi ovmf clang

# Build kernel and bootloader
cd projects/harland
make

# Run in QEMU (UEFI mode)
make run

# Run with debugging (GDB server on :1234)
make debug
```

## Usage

```bash
# Boot Harland with Indium distribution in QEMU
make -C ../indium run-iso

# Connect GDB debugger
gdb harland.elf
(gdb) target remote :1234
```

```ritz
# kernel/main.ritz - kernel entry point
fn kernel_main(boot_info: *BootInfo) -> void
    serial_init()
    serial_print("Hello from Harland!\n")
    gdt_init()
    idt_init()
    vmm_init(boot_info)
    scheduler_init()
    syscall_init()
    # Transfer to first userspace process
    jump_to_user(boot_info.initrd)
```

## Architecture

```
User Space
  Shell | VFS | NetD | Drivers
        | IPC (message passing)
  Harland Microkernel
    Scheduler | IPC | VMM | Interrupts
  Hardware (x86-64)
```

## Dependencies

- No runtime dependencies (freestanding kernel)
- Build tools: clang, LLVM, QEMU, GRUB (for ISO builds)

## Status

**Active development** - Kernel boots in QEMU and UEFI mode. Serial output, GOP framebuffer display driver, basic syscalls (exit, getpid, mmap, write), and the UEFI bootloader are all working. Multi-process scheduling, full IPC, and driver framework are in progress.

## License

MIT License - see LICENSE file
