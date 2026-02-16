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

# Create VirtIO test disks (matching BIOS test)
INITRAMFS="$HARLAND_DIR/build/initramfs.qcow2"
STORAGE="$HARLAND_DIR/build/storage.qcow2"

if [ ! -f "$INITRAMFS" ]; then
    echo "Creating initramfs disk (64MB)..."
    qemu-img create -f qcow2 "$INITRAMFS" 64M >/dev/null
fi

if [ ! -f "$STORAGE" ]; then
    echo "Creating storage disk (512MB)..."
    qemu-img create -f qcow2 "$STORAGE" 512M >/dev/null
fi

echo "Starting QEMU..."
echo ""

# Run QEMU with UEFI (longer timeout for full boot)
# NOTE: Using 256M because UEFI bootloader only identity maps first 256MB.
# With more RAM, UEFI may allocate kernel buffers above 256MB which aren't mapped.
# TODO: Fix bootloader to dynamically map memory where kernel is loaded.
# VirtIO block and network devices for driver testing (matching BIOS test)
timeout 20 qemu-system-x86_64 \
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
if grep -q "\[userspace\] exit" "$SERIAL_LOG"; then
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
