# Indium

**Indium** is the distribution built on the Harland microkernel.

## Architecture

The Ritz ecosystem separates the **kernel** from the **distribution**:

- **Harland** — The microkernel. Just the kernel, nothing else.
- **Indium** — The distribution. Builds the kernel, userspace, and creates bootable images.

This separation allows:
- Multiple distributions built on Harland
- Clean testing of kernel vs userspace
- Proper packaging and image creation

## Current Status

**Work in Progress** — Indium is being extracted from the harland project.

Currently, harland contains embedded userspace programs (init, hello, true, false, etc.)
and QEMU run scripts. These will migrate here.

## Planned Structure

```
indium/
├── build.py              # Main build script
├── config/               # Distribution configuration
│   └── default.toml      # Default config
├── initramfs/            # Initramfs staging
│   ├── bin/              # Userspace binaries
│   ├── etc/              # Configuration files
│   └── ...
├── image/                # Image creation
│   └── iso.py            # ISO image builder
└── run/                  # QEMU run scripts
    └── qemu.py           # QEMU launcher
```

## Build Process (Planned)

```bash
# Build everything
./indium build

# This will:
# 1. Build harland kernel
# 2. Build userspace (init, rzsh, utilities)
# 3. Create initramfs TAR archive
# 4. Create bootable ISO
# 5. (Optional) Create disk image

# Run in QEMU
./indium run
```

## Migration Plan

1. [x] Create indium project stub
2. [ ] Move QEMU scripts from harland/boot/ to indium/run/
3. [ ] Move initramfs creation from kernel to indium
4. [ ] Remove embedded ELFs from kernel (use disk/TAR instead)
5. [ ] Create proper build orchestration
6. [ ] Support multiple configurations (test, release, etc.)

## Why "Indium"?

Indium is a soft, malleable metal. Like the distribution that wraps around the hard kernel.
