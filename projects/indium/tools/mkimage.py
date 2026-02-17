#!/usr/bin/env python3
"""
Indium qcow2 Image Builder

Creates a bootable UEFI disk image with:
- GPT partition table
- EFI System Partition (FAT32) with bootloader
- Boot partition with kernel and initrd

Usage:
    python3 mkimage.py --kernel ../harland/build/debug/harland.elf \
                       --bootloader ../harland/build/debug/BOOTX64.EFI \
                       --output build/indium.qcow2

Requirements:
    - qemu-img
    - guestfish (libguestfs-tools)
"""

import argparse
import subprocess
import sys
import tempfile
import os


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def create_image(
    kernel_path: str,
    bootloader_path: str,
    output_path: str,
    initrd_path: str | None = None,
    size_mb: int = 512
):
    """Create a bootable qcow2 image."""
    print(f"Creating {size_mb}MB qcow2 image: {output_path}")

    # Verify input files exist
    for path, name in [(kernel_path, "kernel"), (bootloader_path, "bootloader")]:
        if not os.path.exists(path):
            print(f"Error: {name} not found: {path}")
            sys.exit(1)

    if initrd_path and not os.path.exists(initrd_path):
        print(f"Error: initrd not found: {initrd_path}")
        sys.exit(1)

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Create empty qcow2 image
    run(["qemu-img", "create", "-f", "qcow2", output_path, f"{size_mb}M"])

    # Use guestfish to partition and populate the image
    # EFI partition: 200MB
    # Boot partition: rest
    efi_end_sector = 2048 + (200 * 1024 * 1024 // 512)  # 200MB in sectors
    boot_start_sector = efi_end_sector + 1

    guestfish_script = f"""
run
part-init /dev/sda gpt
part-add /dev/sda p 2048 {efi_end_sector}
part-add /dev/sda p {boot_start_sector} -1
part-set-gpt-type /dev/sda 1 C12A7328-F81F-11D2-BA4B-00A0C93EC93B
part-set-name /dev/sda 1 "EFI System"
part-set-name /dev/sda 2 "Indium Boot"
mkfs fat /dev/sda1
mkfs ext4 /dev/sda2
mount /dev/sda1 /
mkdir-p /EFI/BOOT
upload {bootloader_path} /EFI/BOOT/BOOTX64.EFI
umount /
mount /dev/sda2 /
upload {kernel_path} /harland.elf
"""

    if initrd_path:
        guestfish_script += f"upload {initrd_path} /initrd.tar\n"

    guestfish_script += "umount /\n"

    print("Partitioning and populating image with guestfish...")

    # Write script to temp file and run guestfish
    with tempfile.NamedTemporaryFile(mode='w', suffix='.gf', delete=False) as f:
        f.write(guestfish_script)
        script_path = f.name

    try:
        result = subprocess.run(
            ["guestfish", "-a", output_path, "-f", script_path],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running guestfish: {e.stderr}")
        sys.exit(1)
    finally:
        os.unlink(script_path)

    print(f"\nImage created: {output_path}")
    print(f"  Size: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
    print("\nTo boot:")
    print("  make run")


def main():
    parser = argparse.ArgumentParser(
        description="Create a bootable Indium qcow2 image"
    )
    parser.add_argument(
        "--kernel", "-k",
        required=True,
        help="Path to kernel ELF (harland.elf)"
    )
    parser.add_argument(
        "--bootloader", "-b",
        required=True,
        help="Path to UEFI bootloader (BOOTX64.EFI)"
    )
    parser.add_argument(
        "--initrd", "-i",
        help="Path to initial ramdisk (optional)"
    )
    parser.add_argument(
        "--output", "-o",
        default="build/indium.qcow2",
        help="Output image path (default: build/indium.qcow2)"
    )
    parser.add_argument(
        "--size", "-s",
        type=int,
        default=512,
        help="Image size in MB (default: 512)"
    )

    args = parser.parse_args()

    create_image(
        kernel_path=args.kernel,
        bootloader_path=args.bootloader,
        output_path=args.output,
        initrd_path=args.initrd,
        size_mb=args.size
    )


if __name__ == "__main__":
    main()
