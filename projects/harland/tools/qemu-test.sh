#!/bin/bash
#
# Harland QEMU Test Script
#
# Boots the kernel in QEMU and captures serial output.
# Checks for "Hello from Harland!" to verify successful boot.
#
# Boot methods:
#   1. ISO with GRUB (Multiboot2) - recommended, requires grub-mkrescue
#   2. Direct ELF boot - simpler but requires kernel to handle CPU init
#
# Usage:
#   ./tools/qemu-test.sh              # Run test
#   ./tools/qemu-test.sh --verbose    # Show all output
#   ./tools/qemu-test.sh --debug      # Run with GDB server
#   ./tools/qemu-test.sh --iso        # Use ISO boot method

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_ROOT/build"
KERNEL_ELF="$BUILD_DIR/harland.elf"
ISO_FILE="$BUILD_DIR/harland.iso"
SERIAL_LOG="$BUILD_DIR/serial.log"
TIMEOUT=5

# Parse args
VERBOSE=0
DEBUG=0
USE_ISO=0
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose) VERBOSE=1; shift ;;
        -d|--debug)   DEBUG=1; shift ;;
        --iso)        USE_ISO=1; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Check kernel exists
if [ ! -f "$KERNEL_ELF" ]; then
    echo "Error: Kernel not found at $KERNEL_ELF"
    echo "Run: python3 build.py build kernel"
    exit 1
fi

# Check for QEMU
if ! command -v qemu-system-x86_64 &> /dev/null; then
    echo "Error: qemu-system-x86_64 not found"
    echo "Install with: sudo apt install qemu-system-x86"
    exit 1
fi

echo "=== Harland QEMU Boot Test ==="
echo "Kernel: $KERNEL_ELF"

# Build QEMU command
if [ "$USE_ISO" -eq 1 ]; then
    # Build ISO if needed
    if [ ! -f "$ISO_FILE" ] || [ "$KERNEL_ELF" -nt "$ISO_FILE" ]; then
        echo "Building ISO..."
        "$SCRIPT_DIR/mkiso.sh"
    fi
    echo "Boot method: ISO (Multiboot2)"
    QEMU_CMD=(
        qemu-system-x86_64
        -cdrom "$ISO_FILE"
        -m 128M
        -serial file:"$SERIAL_LOG"
        -display none
        -no-reboot
    )
else
    # Direct kernel boot with multiboot - QEMU recognizes the multiboot2 header
    echo "Boot method: Direct Multiboot"
    QEMU_CMD=(
        qemu-system-x86_64
        -kernel "$KERNEL_ELF"
        -m 128M
        -serial file:"$SERIAL_LOG"
        -display none
        -no-reboot
        -no-shutdown
        -d guest_errors
        -device isa-debug-exit,iobase=0xf4,iosize=0x04
    )
fi

echo ""

if [ "$DEBUG" -eq 1 ]; then
    QEMU_CMD+=(-S -s -serial stdio)
    # Remove file serial for debug mode
    QEMU_CMD=("${QEMU_CMD[@]/-serial file:$SERIAL_LOG/}")
    echo "GDB server listening on :1234"
    echo "Serial output to stdio"
    echo "Press Ctrl+C to exit"
    "${QEMU_CMD[@]}"
    exit 0
fi

# Remove old log
rm -f "$SERIAL_LOG"
touch "$SERIAL_LOG"

# Run QEMU in background
echo "Starting QEMU (timeout: ${TIMEOUT}s)..."
"${QEMU_CMD[@]}" &
QEMU_PID=$!

# Wait for boot
sleep "$TIMEOUT"

# Stop QEMU
kill $QEMU_PID 2>/dev/null || true
wait $QEMU_PID 2>/dev/null || true

# Check output
echo ""
echo "=== Serial Output ==="
if [ -s "$SERIAL_LOG" ]; then
    cat "$SERIAL_LOG"
else
    echo "(empty)"
fi
echo ""
echo "=== Test Result ==="

if grep -q "Hello from Harland!" "$SERIAL_LOG"; then
    echo "✓ SUCCESS: Kernel booted and printed hello message!"
    exit 0
else
    echo "✗ FAILED: Expected 'Hello from Harland!' not found in serial output"
    if [ "$VERBOSE" -eq 1 ]; then
        echo ""
        echo "Full serial log (hex):"
        xxd "$SERIAL_LOG" 2>/dev/null | head -50 || echo "(no output)"
    fi
    exit 1
fi
