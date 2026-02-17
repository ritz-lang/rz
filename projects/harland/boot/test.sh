#!/bin/bash
# Test the Harland UEFI bootloader with QEMU + OVMF
#
# This boots the full system: UEFI bootloader loads kernel.elf from filesystem.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARLAND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$SCRIPT_DIR"

# Build if needed using workspace rz CLI
# Use debug/ path directly - always copy fresh build to avoid stale cache
BOOT_EFI="$HARLAND_DIR/build/BOOTX64.EFI"
KERNEL_ELF="$HARLAND_DIR/build/harland.elf"
DEBUG_EFI="$HARLAND_DIR/build/debug/BOOTX64.EFI"
DEBUG_ELF="$HARLAND_DIR/build/debug/harland.elf"
RZ_CLI="$HARLAND_DIR/../../rz"

if [ ! -f "$DEBUG_ELF" ]; then
    echo "Building harland..."
    cd "$HARLAND_DIR/../.."
    ./rz build harland
    cd "$SCRIPT_DIR"
fi

# Always copy from debug/ to avoid stale cached builds
if [ -f "$DEBUG_EFI" ]; then
    cp "$DEBUG_EFI" "$BOOT_EFI"
fi
if [ -f "$DEBUG_ELF" ]; then
    cp "$DEBUG_ELF" "$KERNEL_ELF"
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

# Create VirtIO test disks (matching BIOS test)
INITRAMFS="$HARLAND_DIR/build/initramfs.qcow2"
STORAGE="$HARLAND_DIR/build/storage.qcow2"

# User init binary
INIT_ELF="$HARLAND_DIR/build/debug/init.elf"

# Create storage disk if needed
if [ ! -f "$STORAGE" ]; then
    echo "Creating storage disk (512MB)..."
    qemu-img create -f qcow2 "$STORAGE" 512M >/dev/null
fi

# Always rebuild initramfs with latest init.elf
echo "Creating initramfs TAR archive..."

# Create temporary directory for initramfs contents
INITRAMFS_TMP=$(mktemp -d)
mkdir -p "$INITRAMFS_TMP/bin"
mkdir -p "$INITRAMFS_TMP/etc"
mkdir -p "$INITRAMFS_TMP/var/log"

# Copy init.elf if it exists
if [ -f "$INIT_ELF" ]; then
    cp "$INIT_ELF" "$INITRAMFS_TMP/bin/init"
    echo "  Added /bin/init ($INIT_ELF)"
else
    echo "  WARNING: init.elf not found at $INIT_ELF"
fi

# Copy tier1 test binaries
for binary in hello true false exitcode hello_tier1; do
    ELF="$HARLAND_DIR/build/debug/${binary}.elf"
    if [ -f "$ELF" ]; then
        cp "$ELF" "$INITRAMFS_TMP/bin/$binary"
        echo "  Added /bin/$binary"
    fi
done

# Create /etc/hostname
echo "harland" > "$INITRAMFS_TMP/etc/hostname"
echo "  Added /etc/hostname"

# Create /etc/motd
cat > "$INITRAMFS_TMP/etc/motd" << 'MOTD'
Welcome to Harland!
Loaded from initramfs TAR archive.
MOTD
echo "  Added /etc/motd"

# Create /var/log/boot.log
echo "Harland kernel booted successfully." > "$INITRAMFS_TMP/var/log/boot.log"
echo "  Added /var/log/boot.log"

# Create TAR archive (POSIX ustar format)
# Use --format=ustar for compatibility, --numeric-owner to avoid user lookup
TAR_FILE="$HARLAND_DIR/build/initramfs.tar"
(cd "$INITRAMFS_TMP" && tar --format=ustar --numeric-owner -cf "$TAR_FILE" .)
echo "  Created TAR archive: $(du -h "$TAR_FILE" | cut -f1)"

# Clean up temp directory
rm -rf "$INITRAMFS_TMP"

# Create a raw disk image with the TAR at the beginning
# The kernel reads this directly without partition table
RAW_INITRAMFS="$HARLAND_DIR/build/initramfs.raw"

# Calculate size: TAR + padding to 64MB (or at least 1MB larger than TAR)
TAR_SIZE=$(stat -c%s "$TAR_FILE")
DISK_SIZE=$((64 * 1024 * 1024))  # 64 MB
if [ "$TAR_SIZE" -gt "$((DISK_SIZE - 1024 * 1024))" ]; then
    DISK_SIZE=$((TAR_SIZE + 1024 * 1024))
fi

# Create raw disk with TAR at the beginning
dd if=/dev/zero of="$RAW_INITRAMFS" bs=1M count=$((DISK_SIZE / 1024 / 1024)) 2>/dev/null
dd if="$TAR_FILE" of="$RAW_INITRAMFS" conv=notrunc 2>/dev/null
echo "  Created raw disk: $(du -h "$RAW_INITRAMFS" | cut -f1)"

# Convert to QCOW2 for QEMU
rm -f "$INITRAMFS"
qemu-img convert -f raw -O qcow2 "$RAW_INITRAMFS" "$INITRAMFS"
echo "  Converted to QCOW2: $(du -h "$INITRAMFS" | cut -f1)"

# Clean up intermediate files
rm -f "$TAR_FILE" "$RAW_INITRAMFS"

echo "Starting QEMU..."
echo ""

# Run QEMU with UEFI (longer timeout for full boot)
# NOTE: Using 256M because UEFI bootloader only identity maps first 256MB.
# With more RAM, UEFI may allocate kernel buffers above 256MB which aren't mapped.
# TODO: Fix bootloader to dynamically map memory where kernel is loaded.
# VirtIO block and network devices for driver testing (matching BIOS test)
timeout 30 qemu-system-x86_64 \
    -drive if=pflash,format=raw,readonly=on,file="$OVMF_CODE" \
    -drive format=raw,file="$TMPDIR/disk.img" \
    -device virtio-blk-pci,drive=initramfs \
    -drive file="$INITRAMFS",format=qcow2,if=none,id=initramfs \
    -device virtio-blk-pci,drive=storage \
    -drive file="$STORAGE",format=qcow2,if=none,id=storage \
    -device virtio-net-pci,netdev=net0 \
    -netdev user,id=net0 \
    -serial file:"$SERIAL_LOG" \
    -display none \
    -smp 4 \
    -m 256M \
    -no-reboot 2>&1 || true

echo "=== Serial Output ==="
cat "$SERIAL_LOG"
echo ""

# Check for expected output - most advanced first (matching BIOS test milestones)
if grep -q "ALL TESTS PASSED" "$SERIAL_LOG"; then
    echo "========================================="
    echo "  UEFI: MILESTONE 12 COMPLETE: Tier 1 Test Suite!"
    echo "========================================="
    echo "  - Init userspace process running"
    echo "  - All Tier 1 programs executed correctly"
    echo "  - Exit codes verified"
    echo "  - Full test suite passed!"
    exit 0
elif grep -q "ACPI.*Initiating S5 shutdown" "$SERIAL_LOG"; then
    echo "========================================="
    echo "  UEFI: MILESTONE 11 COMPLETE: Init + ACPI Shutdown!"
    echo "========================================="
    echo "  - Init userspace process running"
    echo "  - All userspace tests passed"
    echo "  - sys_acpi_poweroff syscall working"
    echo "  - ACPI S5 shutdown via FADT PM1a register"
    echo "  - Clean system shutdown!"
    exit 0
elif grep -q "\[userspace\] exit" "$SERIAL_LOG"; then
    echo "========================================="
    echo "  UEFI: MILESTONE 10 COMPLETE: Userspace Execution!"
    echo "========================================="
    echo "  - Ring 0 -> Ring 3 transition"
    echo "  - ELF loading and execution"
    echo "  - SYSCALL mechanism working"
    echo "  - sys_write, sys_getpid, sys_yield, sys_exit"
    exit 0
elif grep -q "virtio-blk.*Read sector 0 OK" "$SERIAL_LOG"; then
    echo "========================================="
    echo "  UEFI: MILESTONE 9 COMPLETE: VirtIO Block Device!"
    echo "========================================="
    echo "  - VirtIO-blk driver initialization"
    echo "  - Sector read/write operations"
    echo "  - DMA buffer management"
    echo "  - Ready for filesystem!"
    exit 0
elif grep -q "Task.*done" "$SERIAL_LOG"; then
    echo "========================================="
    echo "  UEFI: MILESTONE 7 COMPLETE: Scheduler!"
    echo "========================================="
    echo "  - Task Control Blocks (TCB)"
    echo "  - Context switching"
    echo "  - Per-CPU ready queues"
    echo "  - Cooperative multitasking"
    TASK_COUNT=$(grep -c "Task.*done" "$SERIAL_LOG" || echo "0")
    echo "  - $TASK_COUNT tasks completed!"
    exit 0
elif grep -q "AP.*started" "$SERIAL_LOG"; then
    echo "========================================="
    echo "  UEFI: MILESTONE 6 COMPLETE: APIC & Multi-core!"
    echo "========================================="
    echo "  - ACPI/MADT parsing for APIC discovery"
    echo "  - Local APIC and I/O APIC initialization"
    echo "  - AP bootstrap via INIT/SIPI sequence"
    AP_COUNT=$(grep -c "AP.*started" "$SERIAL_LOG" || echo "0")
    echo "  - $AP_COUNT Application Processor(s) started!"
    exit 0
elif grep -q "exit(0)" "$SERIAL_LOG"; then
    echo "========================================="
    echo "  UEFI BOOT TEST PASSED (FULL KERNEL)!"
    echo "========================================="
    exit 0
elif grep -q "Hello from Harland" "$SERIAL_LOG"; then
    echo "========================================="
    echo "  UEFI BOOT: Kernel loaded and running!"
    echo "========================================="
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
