#!/bin/bash
# Test kernel boot with QEMU
# Captures serial output and checks for expected messages

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

ISO="$PROJECT_DIR/build/harland.iso"
SERIAL_LOG="/tmp/harland_serial_$$.log"

# Find OVMF (4M variant is more commonly available)
OVMF_CODE=""
for f in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd; do
    if [[ -f "$f" ]]; then
        OVMF_CODE="$f"
        break
    fi
done

if [[ -z "$OVMF_CODE" ]]; then
    OVMF_CODE=$(find /usr -name "OVMF_CODE*.fd" -type f 2>/dev/null | head -1)
fi

if [[ -z "$OVMF_CODE" || ! -f "$OVMF_CODE" ]]; then
    echo "Error: OVMF firmware not found"
    echo "Install: sudo apt install ovmf"
    exit 1
fi

if [[ ! -f "$ISO" ]]; then
    echo "Error: ISO not found at $ISO"
    echo "Run: ./tools/mkiso.sh"
    exit 1
fi

echo "Testing kernel boot..."
echo "ISO: $ISO"
echo "OVMF: $OVMF_CODE"

# Run QEMU with timeout, capture serial output
# Use pflash for OVMF_CODE_4M variant
# -smp 2 for multi-core testing, -m 1G for full memory tests
timeout 10 qemu-system-x86_64 \
    -drive if=pflash,format=raw,readonly=on,file="$OVMF_CODE" \
    -cdrom "$ISO" \
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
if grep -q "\[syscall\] exit" "$SERIAL_LOG"; then
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
