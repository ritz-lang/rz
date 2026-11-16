#!/bin/bash
# Classify a Harland UEFI boot's serial log. boot/test.sh calls this; it is
# separate so the verdict is testable on a canned log without QEMU (AGAST
# #2749; tests in projects/ritz/ritz0/test_harland_uefi_boot_script.py).
#
# Usage: uefi_verdict.sh SERIAL_LOG [MIN_MILESTONE]
#
# Exit 0 only when the most advanced milestone reached is at least
# MIN_MILESTONE (default 12: init's Tier-1 suite reports ALL TESTS PASSED).
# A boot that stops lower -- a timeout, a hang, a regression -- exits 1
# (#2200: a cold run that stopped at MILESTONE 9 used to pass). A kernel
# panic or CPU exception exits 1 whatever the milestone. Bad usage exits 2.
#
# Milestones (highest first; the numbering matches the BIOS test's):
#   12 ALL TESTS PASSED         init's Tier-1 suite
#   11 ACPI S5 shutdown         init ran and powered off
#   10 [userspace] exit         ring 3 ELF ran and exited
#    9 virtio-blk sector 0 OK   VirtIO block device
#    7 Task ... done            scheduler
#    6 AP ... started           APIC and multi-core
#    2 exit(0)                  kernel ran to completion
#    1 Hello from Harland       kernel entered
#    0 Harland UEFI Bootloader  bootloader only

SERIAL_LOG="$1"
MIN_MILESTONE="${2:-12}"
if [ -z "$SERIAL_LOG" ] || [ ! -f "$SERIAL_LOG" ]; then
    echo "usage: $0 SERIAL_LOG [MIN_MILESTONE] (file not found: '$SERIAL_LOG')"
    exit 2
fi
case "$MIN_MILESTONE" in
    ''|*[!0-9]*)
        echo "usage: $0 SERIAL_LOG [MIN_MILESTONE] (not a milestone number: '$MIN_MILESTONE')"
        exit 2
        ;;
esac

banner() {
    echo "========================================="
    echo "  $1"
    echo "========================================="
}

# A later milestone line does not excuse a panic or CPU exception (#2749).
if grep -aqE "KERNEL PANIC|!!! EXCEPTION !!!" "$SERIAL_LOG"; then
    banner "FAIL: Kernel panic/exception detected"
    grep -aE -A4 "KERNEL PANIC|!!! EXCEPTION !!!" "$SERIAL_LOG" | head -20
    exit 1
fi

# The most advanced milestone reached.
if grep -aq "ALL TESTS PASSED" "$SERIAL_LOG"; then
    REACHED=12
    banner "UEFI: MILESTONE 12 COMPLETE: Tier 1 Test Suite!"
    echo "  - Init userspace process running"
    echo "  - All Tier 1 programs executed correctly"
    echo "  - Exit codes verified"
    echo "  - Full test suite passed!"
elif grep -aq "ACPI.*Initiating S5 shutdown" "$SERIAL_LOG"; then
    REACHED=11
    banner "UEFI: MILESTONE 11 COMPLETE: Init + ACPI Shutdown!"
    echo "  - Init userspace process running"
    echo "  - sys_acpi_poweroff syscall working"
    echo "  - ACPI S5 shutdown via FADT PM1a register"
elif grep -aq "\[userspace\] exit" "$SERIAL_LOG"; then
    REACHED=10
    banner "UEFI: MILESTONE 10 COMPLETE: Userspace Execution!"
    echo "  - Ring 0 -> Ring 3 transition"
    echo "  - ELF loading and execution"
    echo "  - SYSCALL mechanism working"
elif grep -aq "virtio-blk.*Read sector 0 OK" "$SERIAL_LOG"; then
    REACHED=9
    banner "UEFI: MILESTONE 9 COMPLETE: VirtIO Block Device!"
    echo "  - VirtIO-blk driver initialization"
    echo "  - Sector read/write operations"
elif grep -aq "Task.*done" "$SERIAL_LOG"; then
    REACHED=7
    banner "UEFI: MILESTONE 7 COMPLETE: Scheduler!"
    echo "  - $(grep -ac "Task.*done" "$SERIAL_LOG") tasks completed"
elif grep -aq "AP.*started" "$SERIAL_LOG"; then
    REACHED=6
    banner "UEFI: MILESTONE 6 COMPLETE: APIC & Multi-core!"
    echo "  - $(grep -ac "AP.*started" "$SERIAL_LOG") Application Processor(s) started"
elif grep -aq "exit(0)" "$SERIAL_LOG"; then
    REACHED=2
    banner "UEFI: MILESTONE 2: kernel ran to exit(0)"
elif grep -aq "Hello from Harland" "$SERIAL_LOG"; then
    REACHED=1
    banner "UEFI: MILESTONE 1: Kernel loaded and running"
elif grep -aq "Harland UEFI Bootloader" "$SERIAL_LOG"; then
    REACHED=0
    banner "PARTIAL: Bootloader ran but kernel didn't start"
else
    echo "FAIL: Expected output not found"
    exit 1
fi

if [ "$REACHED" -lt "$MIN_MILESTONE" ]; then
    echo ""
    echo "FAIL: the boot stopped at milestone $REACHED, below the required milestone $MIN_MILESTONE"
    exit 1
fi
echo "PASS: milestone $REACHED (required: $MIN_MILESTONE)"
exit 0
