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
- GPU framebuffer support with prism_demo
- **AWS EC2 deployment** via Terraform

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

# Boot with GUI display (shows framebuffer)
make test-uefi-gui

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
make ec2-disk     # Create EC2-compatible GPT disk image
make run          # Boot in QEMU (UEFI)
make run-iso      # Boot in QEMU (BIOS/GRUB)
make test-uefi-gui # Boot with display (shows graphics)
make debug        # Boot with GDB server on :1234
make clean        # Remove build artifacts
```

## AWS EC2 Deployment

Indium can run on real AWS EC2 hardware using UEFI boot. The deployment uses Terraform to automate the entire process.

### Architecture

The deployment works using a **builder pattern**:

1. **Builder Instance** - Ubuntu t3.micro that burns the disk image to EBS
2. **EBS Volume** - 1GB volume that holds the Harland OS
3. **Snapshot + AMI** - EBS snapshot registered as UEFI-bootable AMI
4. **Harland Instance** - t3.micro running Harland from the custom AMI

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Terraform Deployment Flow                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────┐     ┌─────────────┐     ┌──────────────┐                  │
│  │  Local   │ SCP │   Ubuntu    │ dd  │     EBS      │                  │
│  │ GPT Disk ├────▶│   Builder   ├────▶│    Volume    │                  │
│  │  Image   │     │  Instance   │     │   (1 GB)     │                  │
│  └──────────┘     └─────────────┘     └──────┬───────┘                  │
│       │                                       │                          │
│       │  make ec2-disk                        │ snapshot                 │
│       │                                       ▼                          │
│  ┌──────────┐                         ┌──────────────┐                  │
│  │  Harland │◀───────────────────────│    UEFI      │                  │
│  │ Instance │     boot from AMI       │     AMI      │                  │
│  │ (t3.micro)│                        │ (ena_support)│                  │
│  └──────────┘                         └──────────────┘                  │
│       │                                                                  │
│       │ serial output                                                    │
│       ▼                                                                  │
│  aws ec2 get-console-output                                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Prerequisites

```bash
# Install AWS CLI and Terraform
brew install awscli terraform    # macOS
sudo apt install awscli terraform  # Ubuntu

# Configure AWS credentials
aws configure

# Create S3 bucket for Terraform state (one-time)
aws s3 mb s3://ritz-harland-terraform-state --region us-west-2
```

### Deployment

```bash
# Build the EC2-compatible disk image
cd projects/indium
make ec2-disk

# Initialize Terraform (first time only)
cd deploy/terraform
terraform init

# Deploy to AWS
terraform apply

# View serial console output (boot log)
terraform output -raw get_console_output | sh

# Or manually:
aws ec2 get-console-output --instance-id $(terraform output -raw harland_instance_id) --region us-west-2 --output text
```

### Disk Image Format

The EC2 disk image (`build/ec2-boot.img`) uses:
- **GPT partition table** (required for UEFI boot)
- **EFI System Partition (ESP)** - FAT32, type code `EF00`
- **Partition layout:**
  - Sectors 2048-131038 (~63MB ESP)
  - Contains `/EFI/BOOT/BOOTX64.EFI` (bootloader)
  - Contains `/harland/kernel.elf` (kernel)

### Hardware Support (Nitro Instances)

EC2 Nitro instances (t3, c5, m5, etc.) use:
- **NVMe for storage** - Amazon EBS appears as `/dev/nvme*`
- **ENA for networking** - Elastic Network Adapter (VF device)
- **UEFI firmware** - Required for custom OS boot

Current driver status:
- ✅ **NVMe** - Working, reads/writes to EBS volumes
- 🔄 **ENA** - In progress, reset sequence being debugged
- ✅ **Serial Console** - Working via `aws ec2 get-console-output`

### Terraform Resources

| Resource | Purpose |
|----------|---------|
| `aws_instance.builder` | Ubuntu instance for burning images |
| `aws_ebs_volume.harland` | Target volume for OS image |
| `aws_ebs_snapshot.harland` | Snapshot for AMI creation |
| `aws_ami.harland` | UEFI-bootable AMI with ENA support |
| `aws_instance.harland` | Running Harland OS instance |

### Outputs

```bash
# Get all outputs
terraform output

# Specific outputs
terraform output harland_instance_id   # Instance ID
terraform output harland_ami_id        # AMI ID
terraform output get_console_output    # Command to view boot log
```

### Destroying Resources

```bash
cd deploy/terraform
terraform destroy
```

This will terminate instances, delete snapshots, deregister the AMI, and clean up all resources.

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
| `prism_demo` | GPU framebuffer graphics demo |

## Dependencies

- `harland` - Microkernel (kernel must be built first)

## Status

**Active development** - Init, basic utilities (hello, true, false, echo, wc, seq10), and rzsh shell all run on Harland. UEFI and BIOS bootable images are buildable. mmap and args passing work. GPU framebuffer support with prism_demo. Multi-process support and more utilities are in progress.

## License

MIT License - see LICENSE file
