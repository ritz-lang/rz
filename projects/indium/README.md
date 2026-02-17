# Indium

**Indium** is the distribution built on the Harland microkernel.

## Architecture

The Ritz ecosystem separates the **kernel** from the **distribution**:

- **Harland** — The microkernel. Just the kernel and UEFI bootloader.
- **Indium** — The distribution. Builds userspace, creates images, runs QEMU.

This separation allows:
- Clean testing of kernel vs userspace
- Proper packaging and image creation
- Multiple distributions built on Harland (future)

## Quick Start

```bash
# Build everything and create bootable ISO
make

# Boot in QEMU (BIOS mode via GRUB)
make run-iso

# Boot in QEMU (UEFI mode)
make run

# Build with debugging (GDB server on :1234)
make debug
```

## Structure

```
indium/
├── ritz.toml             # Userspace program build config
├── Makefile              # Distribution build orchestration
├── tools/
│   ├── mkiso.sh          # ISO image builder
│   ├── mkimage.py        # qcow2 disk image builder
│   └── mkboot.sh         # Raw disk image builder
├── user/                 # Userspace programs
│   ├── libharland.ritz   # Syscall library
│   ├── linker_pie.ld     # Position-independent linker
│   ├── init.ritz         # Init process (PID 1)
│   ├── hello.ritz        # Hello world
│   ├── true.ritz         # Exit 0
│   ├── false.ritz        # Exit 1
│   ├── echo.ritz         # Echo arguments
│   ├── wc.ritz           # Word count
│   └── ...               # Other utilities
└── config/               # Future: distribution configs
```

## Build Targets

| Target | Description |
|--------|-------------|
| `make` | Build ISO (default) |
| `make kernel` | Build Harland kernel |
| `make userspace` | Build userspace programs |
| `make iso` | Create bootable ISO with GRUB |
| `make image` | Create qcow2 disk image (UEFI) |
| `make run` | Boot in QEMU (UEFI mode) |
| `make run-iso` | Boot in QEMU (BIOS/GRUB mode) |
| `make debug` | Boot with GDB server on :1234 |
| `make clean` | Remove build artifacts |

## Userspace Programs

### Tier 1 - Basic Utilities
- `hello` - Print "Hello from Harland!"
- `true` - Exit with status 0
- `false` - Exit with status 1
- `exitcode` - Exit with specific code
- `echo` - Print arguments
- `wc` - Count words/lines/bytes
- `seq10` - Print 1-10
- `cat_motd` - Print message of the day

### System Programs
- `init` - Init process (PID 1)
- `ping` - Network connectivity test

### Test Programs
- `args_test` - Test argument passing
- `minimal_syscall` - Minimal syscall test
- `portable_getpid` - getpid() test

## Why "Indium"?

Indium is a soft, malleable metal. Like the distribution that wraps around the hard kernel.
