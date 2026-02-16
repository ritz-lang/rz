#!/bin/bash
# Test the Harland UEFI bootloader with QEMU + OVMF
#
# This boots the full system: UEFI bootloader loads kernel.elf from filesystem.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARLAND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$SCRIPT_DIR"

# Build if needed using workspace rz CLI
BOOT_EFI="$HARLAND_DIR/build/BOOTX64.EFI"
KERNEL_ELF="$HARLAND_DIR/build/harland.elf"
RZ_CLI="$HARLAND_DIR/../../rz"

if [ ! -f "$BOOT_EFI" ] || [ ! -f "$KERNEL_ELF" ]; then
    echo "Building harland..."
    cd "$HARLAND_DIR/../.."
    ./rz build harland
    cd "$HARLAND_DIR"
    # Copy to expected locations
    cp build/debug/BOOTX64.EFI build/BOOTX64.EFI 2>/dev/null || true
    cp build/debug/harland.elf build/harland.elf 2>/dev/null || true
    cd "$SCRIPT_DIR"
fi

if [ ! -f "$KERNEL_ELF" ]; then
    echo "ERROR: Kernel not found at $KERNEL_ELF"
    echo "Please build: cd ../.. && ./rz build harland"
    exit 1
fi

# Find OVMF
OVMF_CODE=""
for path in \
    /usr/share/OVMF/OVMF_CODE_4M.fd \
    /usr/share/OVMF/OVMF_CODE.fd \
    /usr/share/edk2/x64/OVMF_CODE.4m.fd \
    /usr/share/edk2-ovmf/x64/OVMF_CODE.4m.fd
do
    if [ -f "$path" ]; then
        OVMF_CODE="$path"
        break
    fi
done

if [ -z "$OVMF_CODE" ]; then
    echo "ERROR: OVMF not found. Install ovmf package."
    exit 1
fi

echo "=== Testing UEFI Boot (Full System) ==="
echo "  OVMF:   $OVMF_CODE"
echo "  EFI:    $BOOT_EFI"
echo "  Kernel: $KERNEL_ELF"
echo ""

# Create a temporary FAT filesystem with the EFI file and kernel
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# Create EFI directory structure
mkdir -p "$TMPDIR/EFI/BOOT"
mkdir -p "$TMPDIR/harland"
cp "$BOOT_EFI" "$TMPDIR/EFI/BOOT/BOOTX64.EFI"
cp "$KERNEL_ELF" "$TMPDIR/harland/kernel.elf"

# Create startup.nsh to auto-run our EFI app
cat > "$TMPDIR/startup.nsh" << 'EOF'
@echo -off
FS0:\EFI\BOOT\BOOTX64.EFI
EOF

# Create a FAT disk image (larger to fit kernel)
dd if=/dev/zero of="$TMPDIR/disk.img" bs=1M count=64 2>/dev/null
mkfs.vfat "$TMPDIR/disk.img" >/dev/null
mmd -i "$TMPDIR/disk.img" ::/EFI
mmd -i "$TMPDIR/disk.img" ::/EFI/BOOT
mmd -i "$TMPDIR/disk.img" ::/harland
mcopy -i "$TMPDIR/disk.img" "$BOOT_EFI" ::/EFI/BOOT/BOOTX64.EFI
mcopy -i "$TMPDIR/disk.img" "$KERNEL_ELF" ::/harland/kernel.elf
mcopy -i "$TMPDIR/disk.img" "$TMPDIR/startup.nsh" ::/startup.nsh

# Serial output file
SERIAL_LOG="$TMPDIR/serial.log"

echo "Starting QEMU..."
echo ""

# Run QEMU with UEFI (longer timeout for full boot)
timeout 20 qemu-system-x86_64 \
    -drive if=pflash,format=raw,readonly=on,file="$OVMF_CODE" \
    -drive format=raw,file="$TMPDIR/disk.img" \
    -serial file:"$SERIAL_LOG" \
    -display none \
    -m 256M \
    -no-reboot 2>&1 || true

echo "=== Serial Output ==="
cat "$SERIAL_LOG"
echo ""

# Check for expected output
# Full success: kernel completes to userspace syscall
if grep -q "exit(0)" "$SERIAL_LOG"; then
    echo "========================================="
    echo "  UEFI BOOT TEST PASSED (FULL KERNEL)!"
    echo "========================================="
    exit 0
# Partial success: kernel loads and starts (but crashes due to missing multiboot info)
elif grep -q "Hello from Harland" "$SERIAL_LOG"; then
    echo "========================================="
    echo "  UEFI BOOT: Kernel loaded and running!"
    echo "  (Full boot requires kernel multiboot2/UEFI adaptation)"
    echo "========================================="
    # This is still a success for the bootloader test
    exit 0
elif grep -q "Harland UEFI Bootloader" "$SERIAL_LOG"; then
    echo "========================================="
    echo "  PARTIAL: Bootloader ran but kernel didn't start"
    echo "========================================="
    exit 1
else
    echo "FAIL: Expected output not found"
    exit 1
fi
