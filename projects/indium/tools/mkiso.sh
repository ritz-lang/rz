#!/bin/bash
#
# Indium ISO Creation Script
#
# Creates a bootable ISO with GRUB2 and the Harland kernel.
# Also builds userspace programs and creates the initramfs.
#
# Usage:
#   ./tools/mkiso.sh              # Create ISO
#   ./tools/mkiso.sh --clean      # Remove ISO build files
#
# Every package in initramfs.pkgs must build and produce an ELF: a missing
# binary (rzsh, say) fails the build instead of leaving a thinner image
# (AGAST #1871). RZ_CLI, PKGS_ROOT, KERNEL_ELF and BUILD_DIR may be set in the
# environment; projects/ritz/tools/test_harland_userland.py uses them to run
# this script against fake packages.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HARLAND_DIR="$PROJECT_ROOT/../harland"
BUILD_DIR="${BUILD_DIR:-$PROJECT_ROOT/build}"
RZ_CLI="${RZ_CLI:-$PROJECT_ROOT/../../rz}"
PKGS_ROOT="${PKGS_ROOT:-$PROJECT_ROOT/..}"

# Kernel is built by harland project
KERNEL_ELF="${KERNEL_ELF:-$HARLAND_DIR/build/debug/harland.elf}"
ISO_DIR="$BUILD_DIR/isodir"
ISO_FILE="$BUILD_DIR/indium.iso"
INITRAMFS="$BUILD_DIR/initramfs.qcow2"

# Parse args
if [ "$1" == "--clean" ]; then
    rm -rf "$ISO_DIR" "$ISO_FILE" "$INITRAMFS"
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

# ============================================================================
# Build userspace programs
# ============================================================================

# The packages in initramfs.pkgs, the one list, staged by
# tools/stage_initramfs.sh as the Makefile and harland's boot scripts stage
# them (AGAST #2759, #4834). Staged apart from indium's own build/debug so
# another package's ELFs never land in it. RZ_CLI and PKGS_ROOT pass through.
INITRAMFS_BIN="$BUILD_DIR/initramfs-bin"
RZ_CLI="$RZ_CLI" PKGS_ROOT="$PKGS_ROOT" bash "$SCRIPT_DIR/stage_initramfs.sh" "$INITRAMFS_BIN" \
    || { echo "Error: staging the initramfs packages failed"; exit 1; }

# List what we're including
echo ""
echo "=== Userspace binaries ==="
ls -la "$INITRAMFS_BIN/"*.elf
echo ""

# ============================================================================
# Create initramfs
# ============================================================================

echo "=== Creating initramfs ==="
python3 "$HARLAND_DIR/tools/mkinitramfs.py" \
    --bin-dir "$INITRAMFS_BIN" \
    --output "$INITRAMFS"

# ============================================================================
# Create ISO
# ============================================================================

# Create ISO directory structure
mkdir -p "$ISO_DIR/boot/grub"

# Copy kernel
cp "$KERNEL_ELF" "$ISO_DIR/boot/harland.elf"

# The initramfs as a multiboot2 module (AGAST #4258): GRUB loads the raw TAR
# into RAM and the kernel unpacks it from the module tag, so the ISO boots
# with no virtio-blk disk. initramfs.qcow2 stays for `make run-iso`.
python3 "$HARLAND_DIR/tools/mkinitramfs.py" \
    --bin-dir "$INITRAMFS_BIN" \
    --output "$ISO_DIR/boot/initramfs.tar"

# Create GRUB configuration
cat > "$ISO_DIR/boot/grub/grub.cfg" << 'EOF'
# Indium GRUB Configuration

set timeout=0
set default=0

# Load GOP/VBE drivers so GRUB can honour the kernel's multiboot2
# framebuffer request (#2143)
insmod all_video

menuentry "Indium (Harland Kernel)" {
    multiboot2 /boot/harland.elf
    module2 /boot/initramfs.tar
    boot
}
EOF

# Create ISO (force both BIOS and UEFI boot modes)
echo ""
echo "=== Building ISO ==="
grub-mkrescue -o "$ISO_FILE" "$ISO_DIR" -- -volid "INDIUM"

if [ -f "$ISO_FILE" ]; then
    echo ""
    echo "=========================================="
    echo "  Indium build complete!"
    echo "=========================================="
    echo ""
    echo "ISO:       $ISO_FILE"
    ls -lh "$ISO_FILE"
    echo ""
    echo "Initramfs: $INITRAMFS"
    ls -lh "$INITRAMFS"
    echo ""
    echo "To boot in QEMU:"
    echo "  make run-iso"
else
    echo "Error: ISO creation failed"
    exit 1
fi
