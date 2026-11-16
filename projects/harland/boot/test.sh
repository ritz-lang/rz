#!/bin/bash
# Test the Harland UEFI bootloader with QEMU + OVMF
#
# This boots the full system: UEFI bootloader loads kernel.elf from filesystem.
#
# Usage:
#   ./test.sh         # Headless mode (for CI/automated testing)
#   ./test.sh --gui   # With display window (to see framebuffer graphics)
#
# The ESP is a QEMU vvfat directory (as tools/test_tier1_boot.sh does), so no
# mkfs.vfat (dosfstools: /usr/sbin, off a non-login shell's PATH) and no
# mtools are needed (AGAST #2200).
#
# Knobs:
#   UEFI_MIN_MILESTONE=N  lowest milestone that passes (default 12: init's
#                         Tier-1 suite reports ALL TESTS PASSED; numbering in
#                         uefi_verdict.sh)
#   BOOT_TIMEOUT=N        seconds QEMU may run (default 60 headless, 120 GUI).
#                         Only the boot counts: every build finishes before
#                         the clock starts, and a headless run stops QEMU as
#                         soon as a verdict line (ALL TESTS PASSED, TESTS
#                         FAILED, a panic or exception) appears.
#   SKIP_BUILD=1          use the existing build outputs; build nothing
#   OVMF_CODE=F           OVMF firmware to use (default: search the usual paths)
#
# Exit: 0 = pass; 1 = the boot failed or stopped below UEFI_MIN_MILESTONE;
#       3 = a required tool is missing: a SETUP ERROR, as test_tier1_boot.sh.

set -e

EXIT_SETUP=3
setup_error() { echo "SETUP ERROR: $*" >&2; exit "$EXIT_SETUP"; }

# Parse arguments
GUI_MODE=false
INTERACTIVE=false
for arg in "$@"; do
    case $arg in
        --gui)
            GUI_MODE=true
            ;;
        --interactive)
            INTERACTIVE=true
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARLAND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$SCRIPT_DIR"

command -v qemu-system-x86_64 >/dev/null || setup_error "qemu-system-x86_64 not found (qemu-system-x86)"
command -v qemu-img >/dev/null || setup_error "qemu-img not found (qemu-utils)"

# Build if needed using workspace rz CLI
# Use debug/ path directly - always copy fresh build to avoid stale cache
BOOT_EFI="$HARLAND_DIR/build/BOOTX64.EFI"
KERNEL_ELF="$HARLAND_DIR/build/harland.elf"
DEBUG_EFI="$HARLAND_DIR/build/debug/BOOTX64.EFI"
DEBUG_ELF="$HARLAND_DIR/build/debug/harland.elf"

if [ ! -f "$DEBUG_ELF" ] && [ "${SKIP_BUILD:-}" != 1 ]; then
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
if [ -n "${OVMF_CODE:-}" ]; then
    [ -f "$OVMF_CODE" ] || setup_error "OVMF firmware not found: $OVMF_CODE"
else
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
    [ -n "$OVMF_CODE" ] || setup_error "OVMF not found. Install the ovmf package."
fi

echo "=== Testing UEFI Boot (Full System) ==="
echo "  OVMF:   $OVMF_CODE"
echo "  EFI:    $BOOT_EFI"
echo "  Kernel: $KERNEL_ELF"
echo ""

# The ESP: a directory QEMU presents as a FAT disk (vvfat, `fat:rw:DIR`)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
ESP="$WORK/esp"
mkdir -p "$ESP/EFI/BOOT" "$ESP/harland"
cp "$BOOT_EFI" "$ESP/EFI/BOOT/BOOTX64.EFI"
cp "$KERNEL_ELF" "$ESP/harland/kernel.elf"

# startup.nsh auto-runs our EFI app
cat > "$ESP/startup.nsh" << 'NSH'
@echo -off
FS0:\EFI\BOOT\BOOTX64.EFI
NSH

# Serial output file
SERIAL_LOG="$WORK/serial.log"

# Create VirtIO test disks
# Tests use separate disk images that get reformatted each run
# This keeps `make run` disks pristine for interactive use
INITRAMFS="$HARLAND_DIR/build/initramfs.qcow2"
STORAGE="$HARLAND_DIR/build/storage-test.qcow2"

# Indium and Prism directories
INDIUM_DIR="$HARLAND_DIR/../indium"
PRISM_DIR="$HARLAND_DIR/../prism"

# Always recreate test storage disk (fresh for each test run)
echo "Creating test storage disk (512MB)..."
rm -f "$STORAGE"
qemu-img create -f qcow2 "$STORAGE" 512M >/dev/null

if [ "${SKIP_BUILD:-}" != 1 ]; then
    # Build the Ritz runtime (required for harland userspace binaries)
    echo "Building ritz runtime..."
    make -C "$HARLAND_DIR/../ritz/runtime" >/dev/null 2>&1 || {
        echo "  Building runtime..."
        make -C "$HARLAND_DIR/../ritz/runtime"
    }

    # Build indium userspace (init, hello, true, false, etc.)
    echo "Building indium userspace..."
    cd "$HARLAND_DIR/../.."
    ./rz build indium 2>&1 | grep -v "^  Compiling\|^  Assembling\|^  ⚡" || true
    cd "$SCRIPT_DIR"

    # Build prism (includes prism_demo)
    echo "Building prism..."
    cd "$HARLAND_DIR/../.."
    ./rz build prism 2>&1 | grep -v "^  Compiling\|^  Assembling\|^  ⚡" || true

    # Build rzsh (Ritz shell)
    echo "Building rzsh..."
    ./rz build rzsh 2>&1 | grep -v "^  Compiling\|^  Assembling\|^  ⚡" || true
    cd "$SCRIPT_DIR"
fi

# Always rebuild initramfs with all binaries
echo "Creating initramfs TAR archive..."

# Create temporary directory for initramfs contents
INITRAMFS_TMP=$(mktemp -d)
mkdir -p "$INITRAMFS_TMP/bin"
mkdir -p "$INITRAMFS_TMP/etc"
mkdir -p "$INITRAMFS_TMP/var/log"

# Copy all indium binaries
echo "  Copying indium binaries..."
for elf in "$INDIUM_DIR/build/debug"/*.elf; do
    if [ -f "$elf" ]; then
        name=$(basename "$elf" .elf)
        cp "$elf" "$INITRAMFS_TMP/bin/$name"
        echo "    /bin/$name"
    fi
done

# For interactive mode, replace init with init_interactive
if [ "$INTERACTIVE" = true ]; then
    if [ -f "$INITRAMFS_TMP/bin/init_interactive" ]; then
        echo "  Using init_interactive for interactive mode"
        cp "$INITRAMFS_TMP/bin/init_interactive" "$INITRAMFS_TMP/bin/init"
    fi
fi

# Copy prism binaries
if [ -f "$PRISM_DIR/build/debug/prism_demo.elf" ]; then
    cp "$PRISM_DIR/build/debug/prism_demo.elf" "$INITRAMFS_TMP/bin/prism_demo"
    echo "    /bin/prism_demo"
fi

if [ -f "$PRISM_DIR/build/debug/hello_gfx.elf" ]; then
    cp "$PRISM_DIR/build/debug/hello_gfx.elf" "$INITRAMFS_TMP/bin/hello_gfx"
    echo "    /bin/hello_gfx"
fi

# Copy rzsh
RZSH_DIR="$HARLAND_DIR/../rzsh"
if [ -f "$RZSH_DIR/build/debug/rzsh.elf" ]; then
    cp "$RZSH_DIR/build/debug/rzsh.elf" "$INITRAMFS_TMP/bin/rzsh"
    echo "    /bin/rzsh"
fi

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

# Create raw disk with TAR at the beginning (copy TAR, then extend with zeros;
# dd hung here, AGAST #2748)
cp "$TAR_FILE" "$RAW_INITRAMFS"
truncate -s "$DISK_SIZE" "$RAW_INITRAMFS"
echo "  Created raw disk: $(du -h "$RAW_INITRAMFS" | cut -f1)"

# Convert to QCOW2 for QEMU
rm -f "$INITRAMFS"
qemu-img convert -f raw -O qcow2 "$RAW_INITRAMFS" "$INITRAMFS"
echo "  Converted to QCOW2: $(du -h "$INITRAMFS" | cut -f1)"

# Clean up intermediate files
rm -f "$TAR_FILE" "$RAW_INITRAMFS"

echo "Starting QEMU..."
echo ""

# Set display mode based on --gui flag. BOOT_TIMEOUT covers QEMU only: every
# build above has finished before the clock starts (#2200).
if [ "$GUI_MODE" = true ]; then
    DISPLAY_OPT="-display gtk"
    TIMEOUT_SECS=${BOOT_TIMEOUT:-120}  # Longer timeout for interactive use
    echo "  Display: GUI mode (gtk)"
else
    DISPLAY_OPT="-display none"
    TIMEOUT_SECS=${BOOT_TIMEOUT:-60}
    echo "  Display: headless"
fi

# Interactive mode disables timeout. init_interactive runs no Tier-1 suite,
# so any milestone from the kernel up counts unless one is asked for.
if [ "$INTERACTIVE" = true ]; then
    TIMEOUT_SECS=0
    UEFI_MIN_MILESTONE=${UEFI_MIN_MILESTONE:-1}
    echo "  Mode: interactive (no timeout, Ctrl+C to quit)"
fi
UEFI_MIN_MILESTONE=${UEFI_MIN_MILESTONE:-12}
echo "  Boot timeout: ${TIMEOUT_SECS}s; required milestone: $UEFI_MIN_MILESTONE"

# Run QEMU with UEFI (longer timeout for full boot)
# NOTE: Using 256M because UEFI bootloader only identity maps first 256MB.
# With more RAM, UEFI may allocate kernel buffers above 256MB which aren't mapped.
# TODO: Fix bootloader to dynamically map memory where kernel is loaded.
# VirtIO block, network, and input devices for driver testing (matching BIOS test)
# NOTE: Using Haswell CPU because LLVM may generate BMI1 instructions (like bextr)
# that the default qemu64 CPU doesn't support.
QEMU_CMD="qemu-system-x86_64 \
    -cpu Haswell \
    -drive if=pflash,format=raw,readonly=on,file=$OVMF_CODE \
    -drive format=raw,file=fat:rw:$ESP \
    -device virtio-blk-pci,drive=initramfs \
    -drive file=$INITRAMFS,format=qcow2,if=none,id=initramfs \
    -device virtio-blk-pci,drive=storage \
    -drive file=$STORAGE,format=qcow2,if=none,id=storage \
    -device virtio-net-pci,netdev=net0 \
    -netdev user,id=net0 \
    -device virtio-keyboard-pci \
    -device virtio-mouse-pci \
    -serial file:$SERIAL_LOG \
    $DISPLAY_OPT \
    -smp 4 \
    -m 256M \
    -no-reboot"

if [ "$TIMEOUT_SECS" -gt 0 ] && [ "$GUI_MODE" != true ]; then
    # init halts after its suite: stop QEMU once a verdict line appears
    # instead of idling out the rest of the timeout.
    timeout "$TIMEOUT_SECS" $QEMU_CMD 2>&1 &
    QEMU_PID=$!
    while kill -0 "$QEMU_PID" 2>/dev/null; do
        if grep -aqE "ALL TESTS PASSED|TESTS FAILED|KERNEL PANIC|!!! EXCEPTION !!!" "$SERIAL_LOG" 2>/dev/null; then
            sleep 1
            kill "$QEMU_PID" 2>/dev/null || true
            break
        fi
        sleep 1
    done
    wait "$QEMU_PID" 2>/dev/null || true
elif [ "$TIMEOUT_SECS" -gt 0 ]; then
    timeout $TIMEOUT_SECS $QEMU_CMD 2>&1 || true
else
    $QEMU_CMD 2>&1 || true
fi

echo "=== Serial Output ==="
cat "$SERIAL_LOG"
echo ""

# Classify the boot: boot/uefi_verdict.sh fails on a panic or exception
# before looking for milestones, and on any milestone below the required one.
"$SCRIPT_DIR/uefi_verdict.sh" "$SERIAL_LOG" "$UEFI_MIN_MILESTONE"
