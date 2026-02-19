#!/bin/bash
# Test kernel boot with QEMU (BIOS mode via GRUB)
# Captures serial output and checks for expected messages
#
# This test uses legacy BIOS boot with GRUB multiboot2.
# For UEFI testing, use: make test-uefi-boot

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

ISO="$PROJECT_DIR/build/harland.iso"
SERIAL_LOG="/tmp/harland_serial_$$.log"

if [[ ! -f "$ISO" ]]; then
    echo "Error: ISO not found at $ISO"
    echo "Run: ./tools/mkiso.sh"
    exit 1
fi

echo "Testing kernel boot (BIOS/GRUB mode)..."
echo "ISO: $ISO"

# Create test disks if they don't exist (for VirtIO testing)
INITRAMFS="$PROJECT_DIR/build/initramfs.qcow2"
STORAGE="$PROJECT_DIR/build/storage.qcow2"

if [[ ! -f "$INITRAMFS" ]]; then
    echo "Creating initramfs disk (64MB)..."
    qemu-img create -f qcow2 "$INITRAMFS" 64M >/dev/null
fi

if [[ ! -f "$STORAGE" ]]; then
    echo "Creating storage disk (512MB)..."
    qemu-img create -f qcow2 "$STORAGE" 512M >/dev/null
fi

# Run QEMU in BIOS mode (no OVMF) with GRUB ISO
# -smp 4 for multi-core testing, -m 2G for full memory tests
# VirtIO block, network, and input devices for driver testing
# -cpu Haswell-v1 enables BMI1/BMI2 instructions (bextr, etc.)
timeout 45 qemu-system-x86_64 \
    -cpu Haswell-v1 \
    -cdrom "$ISO" \
    -device virtio-blk-pci,drive=initramfs \
    -drive file="$INITRAMFS",format=qcow2,if=none,id=initramfs \
    -device virtio-blk-pci,drive=storage \
    -drive file="$STORAGE",format=qcow2,if=none,id=storage \
    -device virtio-net-pci,netdev=net0 \
    -netdev user,id=net0 \
    -device virtio-keyboard-pci \
    -device virtio-mouse-pci \
    -serial file:"$SERIAL_LOG" \
    -display none \
    -smp 4 \
    -m 2G \
    -no-reboot 2>&1 || true

echo ""
echo "=== Serial Output ==="
cat "$SERIAL_LOG"
echo ""

# Check for expected output - most advanced first
if grep -q "virtio-blk.*Read sector 0 OK" "$SERIAL_LOG"; then
    echo "========================================="
    echo "  MILESTONE 9 COMPLETE: VirtIO Block Device!"
    echo "========================================="
    echo "  - VirtIO-blk driver initialization"
    echo "  - Sector read/write operations"
    echo "  - DMA buffer management"
    echo "  - Ready for filesystem!"
    rm -f "$SERIAL_LOG"
    exit 0
elif grep -q "\[syscall\] exit" "$SERIAL_LOG"; then
    echo "========================================="
    echo "  MILESTONE 8 COMPLETE: Userspace + Syscalls!"
    echo "========================================="
    echo "  - Ring 0 -> Ring 3 transition"
    echo "  - User program execution"
    echo "  - SYSCALL/SYSRET mechanism"
    echo "  - First userspace syscall!"
    rm -f "$SERIAL_LOG"
    exit 0
elif grep -q "Task.*done" "$SERIAL_LOG"; then
    echo "========================================="
    echo "  MILESTONE 7 COMPLETE: Scheduler!"
    echo "========================================="
    echo "  - Task Control Blocks (TCB)"
    echo "  - Context switching"
    echo "  - Per-CPU ready queues"
    echo "  - Cooperative multitasking"
    TASK_COUNT=$(grep -c "Task.*done" "$SERIAL_LOG" || echo "0")
    echo "  - $TASK_COUNT tasks completed!"
    rm -f "$SERIAL_LOG"
    exit 0
elif grep -q "AP.*started" "$SERIAL_LOG"; then
    echo "========================================="
    echo "  MILESTONE 6 COMPLETE: APIC & Multi-core!"
    echo "========================================="
    echo "  - ACPI/MADT parsing for APIC discovery"
    echo "  - Local APIC and I/O APIC initialization"
    echo "  - AP bootstrap via INIT/SIPI sequence"
    AP_COUNT=$(grep -c "AP.*started" "$SERIAL_LOG" || echo "0")
    echo "  - $AP_COUNT Application Processor(s) started!"
    rm -f "$SERIAL_LOG"
    exit 0
elif grep -q "Hello from Harland" "$SERIAL_LOG"; then
    echo "========================================="
    echo "  Boot successful (single core)"
    echo "========================================="
    rm -f "$SERIAL_LOG"
    exit 0
else
    echo "FAIL: Kernel boot failed - expected output not found"
    rm -f "$SERIAL_LOG"
    exit 1
fi
