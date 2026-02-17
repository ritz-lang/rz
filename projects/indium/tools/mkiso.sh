#!/bin/bash
#
# Indium ISO Creation Script
#
# Creates a bootable ISO with GRUB2 and the Harland kernel.
# This allows booting via Multiboot2 protocol.
#
# Usage:
#   ./tools/mkiso.sh              # Create ISO
#   ./tools/mkiso.sh --clean      # Remove ISO build files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HARLAND_DIR="$PROJECT_ROOT/../harland"
BUILD_DIR="$PROJECT_ROOT/build"

# Kernel is built by harland project
KERNEL_ELF="$HARLAND_DIR/build/debug/harland.elf"
ISO_DIR="$BUILD_DIR/isodir"
ISO_FILE="$BUILD_DIR/indium.iso"

# Parse args
if [ "$1" == "--clean" ]; then
    rm -rf "$ISO_DIR" "$ISO_FILE"
    echo "Cleaned ISO build files"
    exit 0
fi

# Check kernel exists
if [ ! -f "$KERNEL_ELF" ]; then
    echo "Error: Kernel not found at $KERNEL_ELF"
    echo "Build the kernel first: make -C ../harland kernel"
    exit 1
fi

# Check for required tools
if ! command -v grub-mkrescue &> /dev/null; then
    echo "Error: grub-mkrescue not found"
    echo "Install with: sudo apt install grub-pc-bin grub-common xorriso"
    exit 1
fi

echo "=== Creating Indium ISO ==="
echo "Kernel: $KERNEL_ELF"
echo ""

# Create build directory
mkdir -p "$BUILD_DIR"

# Create ISO directory structure
mkdir -p "$ISO_DIR/boot/grub"

# Copy kernel
cp "$KERNEL_ELF" "$ISO_DIR/boot/harland.elf"

# Create GRUB configuration
cat > "$ISO_DIR/boot/grub/grub.cfg" << 'EOF'
# Indium GRUB Configuration

set timeout=0
set default=0

menuentry "Indium (Harland Kernel)" {
    multiboot2 /boot/harland.elf
    boot
}
EOF

# Create ISO (force both BIOS and UEFI boot modes)
echo "Building ISO..."
grub-mkrescue -o "$ISO_FILE" "$ISO_DIR" -- -volid "INDIUM"

if [ -f "$ISO_FILE" ]; then
    echo ""
    echo "ISO created: $ISO_FILE"
    ls -lh "$ISO_FILE"
    echo ""
    echo "To boot in QEMU:"
    echo "  make run-iso"
    echo "  # or:"
    echo "  qemu-system-x86_64 -cdrom $ISO_FILE -serial stdio -m 128M"
else
    echo "Error: ISO creation failed"
    exit 1
fi
