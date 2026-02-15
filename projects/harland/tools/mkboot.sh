#!/bin/bash
#
# Create a minimal bootable disk image using GRUB
# This creates a raw disk image with GRUB and our kernel
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_ROOT/build"
KERNEL_ELF="$BUILD_DIR/harland.elf"
DISK_IMG="$BUILD_DIR/harland.img"

# Check kernel exists
if [ ! -f "$KERNEL_ELF" ]; then
    echo "Error: Kernel not found at $KERNEL_ELF"
    exit 1
fi

echo "=== Creating Bootable Disk Image ==="

# Create a 32MB disk image
dd if=/dev/zero of="$DISK_IMG" bs=1M count=32 2>/dev/null

# Create partition table and partition
echo "Creating partition table..."
parted -s "$DISK_IMG" mklabel msdos
parted -s "$DISK_IMG" mkpart primary fat32 1MiB 100%
parted -s "$DISK_IMG" set 1 boot on

# Set up loop device
LOOP_DEV=$(sudo losetup --find --show --partscan "$DISK_IMG")
PART_DEV="${LOOP_DEV}p1"

# Wait for partition to appear
sleep 1

# Format the partition
echo "Formatting partition..."
sudo mkfs.fat -F 32 "$PART_DEV"

# Mount and install files
MOUNT_DIR=$(mktemp -d)
sudo mount "$PART_DEV" "$MOUNT_DIR"

# Create GRUB directory
sudo mkdir -p "$MOUNT_DIR/boot/grub"

# Copy kernel
sudo cp "$KERNEL_ELF" "$MOUNT_DIR/boot/harland.elf"

# Create GRUB config
sudo tee "$MOUNT_DIR/boot/grub/grub.cfg" > /dev/null << 'EOF'
set timeout=0
set default=0

menuentry "Harland" {
    multiboot2 /boot/harland.elf
    boot
}
EOF

# Install GRUB
echo "Installing GRUB..."
sudo grub-install --target=i386-pc --boot-directory="$MOUNT_DIR/boot" "$LOOP_DEV"

# Cleanup
sudo umount "$MOUNT_DIR"
rmdir "$MOUNT_DIR"
sudo losetup -d "$LOOP_DEV"

echo ""
echo "Disk image created: $DISK_IMG"
echo ""
echo "To boot:"
echo "  qemu-system-x86_64 -drive file=$DISK_IMG,format=raw -serial stdio -m 128M"
