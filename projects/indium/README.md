# Indium

Distribution built on the Harland microkernel - userspace programs, init system, and bootable image tooling.

**Part of the [Ritz Ecosystem](../ritz/docs/ECOSYSTEM.md)**

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
- GPU framebuffer support with prism_demo
- EC2-compatible GPT disk image builder (`make ec2-disk`)

## Installation

```bash
# Prerequisites. `lld` is required: indium builds harland, whose UEFI
# bootloader target links with lld-link. Without it the build fails at
# exit 1 with "Cannot link UEFI target 'bootx64': lld-link not found".
sudo apt install qemu-system-x86 grub-efi mtools clang lld

cd projects/indium

# Build everything and create bootable ISO
make

# Boot in QEMU (BIOS/GRUB mode)
make run-iso

# Boot in QEMU (UEFI mode)
make run

# Boot with GUI display (shows framebuffer)
make test-uefi-gui

# Build with GDB debug server
make debug
# Then: gdb -ex "target remote :1234" ../harland/build/debug/harland.elf
```

## Usage

```bash
# Available make targets
make              # Build ISO (default)
make kernel       # Build Harland kernel only
make userspace    # Build all userspace programs
make iso          # Create bootable ISO with GRUB
make ec2-disk     # Create EC2-compatible GPT disk image
make run          # Boot in QEMU (UEFI)
make run-iso      # Boot in QEMU (BIOS/GRUB)
make test-uefi-gui # Boot with display (shows graphics)
make debug        # Boot with GDB server on :1234
make clean        # Remove build artifacts
```

## AWS EC2 Deployment — NOT IMPLEMENTED

**There is no deployment tooling in this project.** `projects/indium/deploy/`
does not exist, so neither does `deploy/terraform`. Every `terraform init`,
`terraform apply`, `terraform output` and `terraform destroy` command this
section used to document would fail immediately on a missing directory. (The
only `deploy/` directory in the monorepo belongs to `projects/nexus`, and it is
unrelated.)

What does exist is the disk image itself:

```bash
make ec2-disk        # builds build/ec2-boot.img
```

### Disk Image Format

`build/ec2-boot.img` is shaped for UEFI boot on EC2:

- **GPT partition table** (required for UEFI boot)
- **EFI System Partition (ESP)** — FAT32, type code `EF00`
- Sectors 2048-131038 (~63MB ESP), containing
  `/EFI/BOOT/BOOTX64.EFI` (bootloader) and `/harland/kernel.elf` (kernel)

### Hardware Support (Nitro Instances)

EC2 Nitro instances (t3, c5, m5, etc.) use NVMe for storage (EBS appears as
`/dev/nvme*`), ENA for networking, and UEFI firmware. Driver status in the
harland kernel:

- **NVMe** — implemented
- **ENA** — in progress
- **Serial console** — implemented (readable via `aws ec2 get-console-output`)

None of the above has been re-validated against live EC2 hardware recently; treat
it as a design target. Actually deploying would mean writing the Terraform (or
equivalent) that this section previously described as already present: a builder
instance to `dd` the image onto an EBS volume, a snapshot registered as a
UEFI-bootable AMI with `ena_support`, and an instance booted from it.

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
| `cwd_test` | Test working-directory syscalls |
| `hello_tier1` | Minimal hello (tier-1 language subset) |
| `minimal_syscall` | Smallest possible syscall program |
| `portable_getpid` | getpid via the portable libharland interface |

All of the above appear as `*.elf` in `projects/indium/build/debug/` after
`./rz build indium` (exit 0, measured 2026-09-12).

Two entries that are **not** built by indium, despite earlier revisions of this
table listing them here:

| Program | Where it actually comes from |
|---------|------------------------------|
| `rzsh` | `projects/rzsh` → `build/debug/rzsh.elf`; indium's `make rzsh` target pulls it in |
| `prism_demo` | `projects/prism` → `build/debug/prism_demo.elf` |

## Dependencies

- `harland` - Microkernel (kernel must be built first)

## Status

**Active development.** `./rz build indium` is green (exit 0, measured
2026-09-12) and produces all 17 userspace `.elf` binaries. Init, the basic
utilities (hello, true, false, echo, wc, seq10) and the rzsh shell run on
Harland; mmap and argument passing work; UEFI and BIOS bootable images are
buildable. Multi-process support and more utilities are in progress.

Two caveats this README previously omitted:

- Booting requires `lld` for harland's `bootx64` target — see Installation.
- There is no AWS deployment tooling; `make ec2-disk` builds an image, nothing
  ships it. See the EC2 section above.

QEMU boot targets (`make run`, `make run-iso`, `make test-uefi-gui`,
`make debug`) all resolve as real Make targets, but none of them were executed
as part of this documentation pass — they need QEMU and a display/serial session.
Treat their behaviour as unverified here.

## License

MIT License - see LICENSE file
