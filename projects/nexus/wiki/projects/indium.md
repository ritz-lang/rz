# Indium

Distribution layer for the Harland microkernel. Active development.

*Named after indium — a soft, malleable metal that wraps around the hard kernel.*

---

## Overview

Indium is the OS distribution that sits on top of Harland. While Harland provides only the kernel and UEFI bootloader, Indium provides everything needed for a bootable, usable system: an init process, basic userspace utilities, the rzsh shell, and tooling to build bootable disk images.

---

## Where It Fits

```
Bootable ISO or qcow2 image
    ├── GRUB (BIOS) or UEFI bootloader
    ├── Harland kernel
    └── Indium userspace
            ├── init (PID 1)
            ├── rzsh (shell)
            └── Basic utilities
```

---

## Features

- **Init process** — PID 1, the first userspace process. Starts the system.
- **Basic utilities** — echo, cat, wc, seq, true, false, exit, hello
- **rzsh shell** — Interactive shell, cross-platform (Linux + Harland)
- **libharland** — Syscall wrapper library (Harland's ABI → portable interface)
- **PIE userspace** — All binaries are position-independent executables
- **Bootable ISO** — GRUB/BIOS bootable image builder
- **Bootable qcow2** — UEFI disk image builder for QEMU

---

## Userspace Programs

| Program | Description |
|---------|-------------|
| `init` | Init process — PID 1, starts the system |
| `rzsh` | Interactive shell |
| `hello` | Print "Hello from Harland!" |
| `echo` | Print command-line arguments |
| `wc` | Count words, lines, and bytes |
| `seq10` | Print numbers 1 through 10 |
| `cat_motd` | Display message of the day |
| `ping` | Network connectivity test |
| `true` | Exit with status 0 |
| `false` | Exit with status 1 |
| `exitcode` | Exit with a specific code |
| `mmap_test` | Test mmap syscall |
| `args_test` | Test argument passing |

---

## Build and Run

```bash
cd projects/indium

# Build everything and create bootable ISO
make

# Boot in QEMU (BIOS/GRUB mode)
make run-iso

# Boot in QEMU (UEFI mode)
make run

# Debug with GDB
make debug
# Then: gdb -ex "target remote :1234" ../harland/build/harland.elf

# Clean
make clean
```

---

## libharland

Indium programs use `libharland` — a Ritz library that wraps Harland's syscall ABI into a portable interface. This abstracts the kernel ABI so userspace code doesn't hardcode syscall numbers directly.

All Indium binaries are compiled as freestanding Ritz programs that link the Harland runtime (no libc, no Linux compatibility layer).

---

## Relationship to Harland and rzsh

- **Harland** — The microkernel. Provides process isolation, memory management, IPC, interrupts.
- **Indium** — The distribution. Provides userspace, init, utilities, bootable images.
- **rzsh** — The shell. Lives in `projects/rzsh/` but is distributed via Indium. Cross-platform.

Keeping these separate means:
- Harland stays focused on kernel concerns
- Multiple distributions could theoretically build on Harland
- rzsh runs on both Linux (for development) and Harland (for production)

---

## Current Status

Active development. Init, basic utilities, and rzsh all run on Harland. UEFI and BIOS bootable images build successfully. Multi-process support and more utilities are in progress.

---

## Related Projects

- [Harland](harland.md) — The microkernel Indium runs on
- [rzsh](rzsh.md) — The shell distributed by Indium
- [Goliath](goliath.md) — Filesystem server (future Indium component)
- [Prism](prism.md) — Display server (future Indium component)
- [Kernel Subsystem](../subsystems/kernel.md)
