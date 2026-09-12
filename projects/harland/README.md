# Harland

A microkernel operating system written in Ritz, designed for portability and clean syscall abstraction.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

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
# Install dependencies. `lld` is required: the UEFI bootloader target
# (bootx64) links with lld-link, and without it the build fails with
# "Cannot link UEFI target 'bootx64': lld-link not found".
sudo apt install qemu-system-x86 grub-efi ovmf clang lld

# Build the kernel (run from the monorepo root)
./rz build harland
# or, from this directory, kernel only:
make -C projects/harland kernel
```

`make -C projects/harland` targets (`make help` prints this list):

```
kernel          Build the kernel (default)
iso             Create test ISO with GRUB
test            Run kernel boot test
test-boot       Run kernel boot test (GRUB/BIOS)
test-uefi-boot  Test UEFI bootloader (headless)
test-uefi-gui   Test UEFI bootloader with display
run-gui         Interactive run (no timeout, kill QEMU manually)
clean           Remove build artifacts
help            Show this help
```

There is **no `run` target and no `debug` target here** — `make run` and
`make debug` both exit 2 with `No rule to make target`. The interactive target is
`run-gui`. For booting a full system with userspace, and for the GDB server, use
indium:

```bash
make -C projects/indium run      # boot in QEMU (UEFI)
make -C projects/indium debug    # boot with GDB server on :1234
```

## Usage

```bash
# Boot Harland with Indium distribution in QEMU
make -C ../indium run-iso

# Connect GDB debugger (note the path — the ELF is under build/debug/)
gdb projects/harland/build/debug/harland.elf
(gdb) target remote :1234
```

```ritz
# kernel/src/main.ritz - kernel entry point
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
- Build tools: clang, LLVM, `lld` (for the UEFI `bootx64` target), QEMU,
  GRUB (for ISO builds)

## Status

**Active development.** Serial output, the GOP framebuffer display driver, basic
syscalls (exit, getpid, mmap, write) and the UEFI bootloader are implemented.
Multi-process scheduling, full IPC, and the driver framework are in progress.

Build status measured 2026-09-12: `./rz build harland` **fails at exit 1** on
this machine because `lld` is not installed —
`Cannot link UEFI target 'bootx64': lld-link not found`. The kernel half
(`harland.elf`) links fine; only `bootx64` needs lld. This is an environment
gap, not a code defect, which is why harland is deliberately *not* listed in
`rz.toml`'s `[ci.known_failing.build]` — CI installs lld and expects harland to
pass. Install `lld` and the build goes green.

## License

MIT License - see LICENSE file
