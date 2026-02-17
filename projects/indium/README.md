# Indium

Distribution built on the Harland microkernel - userspace programs, init system, and bootable image tooling.

**Part of the [Ritz Ecosystem](../larb/docs/ECOSYSTEM.md)**

## Overview

Indium is the distribution layer that builds on top of the Harland microkernel. While Harland provides only the kernel and UEFI bootloader, Indium provides everything needed for a bootable, usable system: an init process, basic Unix utilities, shell, and the tooling to build bootable ISO and disk images.

This separation keeps the kernel repository clean and focused, allowing multiple distributions to potentially build on Harland in the future. Indium programs use `libharland` - a Ritz library that wraps Harland's syscall ABI into a portable interface. All userspace binaries are position-independent executables (PIE) compiled as freestanding Ritz programs that link the Harland runtime.

Named after Indium, a soft malleable metal - the distribution that wraps around the hard kernel.

## Features

- Init process (PID 1) for system initialization
- Basic Unix utilities written in Ritz for Harland
- rzsh shell (cross-platform, runs on both Harland and Linux)
- libharland syscall wrapper library
- Position-independent executable (PIE) userspace binaries
- Bootable ISO image builder (GRUB/BIOS mode)
- UEFI disk image builder (qcow2 format)
- QEMU launch targets for both UEFI and BIOS boot

## Installation

```bash
# Prerequisites: qemu-system-x86, grub-efi, mtools
cd projects/indium

# Build everything and create bootable ISO
make

# Boot in QEMU (BIOS/GRUB mode)
make run-iso

# Boot in QEMU (UEFI mode)
make run

# Build with GDB debug server
make debug
# Then: gdb -ex "target remote :1234" ../harland/build/harland.elf
```

## Usage

```bash
# Available make targets
make              # Build ISO (default)
make kernel       # Build Harland kernel only
make userspace    # Build all userspace programs
make iso          # Create bootable ISO with GRUB
make image        # Create qcow2 disk image (UEFI)
make run          # Boot in QEMU (UEFI)
make run-iso      # Boot in QEMU (BIOS/GRUB)
make debug        # Boot with GDB server on :1234
make clean        # Remove build artifacts
```

## Userspace Programs

| Program | Description |
|---------|-------------|
| `init` | Init process - PID 1, starts the system |
| `rzsh` | Interactive shell |
| `hello` | Print "Hello from Harland!" |
| `true` | Exit with status 0 |
| `false` | Exit with status 1 |
| `exitcode` | Exit with a specific code |
| `echo` | Print command-line arguments |
| `wc` | Count words, lines, and bytes |
| `seq10` | Print numbers 1 through 10 |
| `cat_motd` | Display the message of the day |
| `ping` | Network connectivity test |
| `args_test` | Test argument passing |
| `mmap_test` | Test mmap syscall |

## Dependencies

- `harland` - Microkernel (kernel must be built first)

## Status

**Active development** - Init, basic utilities (hello, true, false, echo, wc, seq10), and rzsh shell all run on Harland. UEFI and BIOS bootable images are buildable. mmap and args passing work. Multi-process support and more utilities are in progress.

## License

MIT License - see LICENSE file
