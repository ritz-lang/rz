#!/bin/bash
# Classify a Harland UEFI boot's serial log: exit 0 on the most advanced
# milestone reached, 1 on a kernel panic / CPU exception or no milestone.
# boot/test.sh calls this; it is separate so the verdict is testable on a
# canned log without QEMU (AGAST #2749).
#
# Usage: uefi_verdict.sh SERIAL_LOG

SERIAL_LOG="$1"
if [ -z "$SERIAL_LOG" ] || [ ! -f "$SERIAL_LOG" ]; then
    echo "usage: $0 SERIAL_LOG (file not found: '$SERIAL_LOG')"
    exit 2
fi

# Check for expected output - most advanced first (matching BIOS test milestones)
if grep -aqE "KERNEL PANIC|!!! EXCEPTION !!!" "$SERIAL_LOG"; then
    # A later milestone line does not excuse a panic or CPU exception (#2749).
    echo "========================================="
    echo "  FAIL: Kernel panic/exception detected"
    echo "========================================="
    grep -aE -A4 "KERNEL PANIC|!!! EXCEPTION !!!" "$SERIAL_LOG" | head -20
    exit 1
elif grep -q "ALL TESTS PASSED" "$SERIAL_LOG"; then
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
