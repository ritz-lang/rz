#!/bin/bash
# Boot Harland's GRUB ISO under legacy BIOS (SeaBIOS -> GRUB multiboot2) with
# the real initramfs, and check init's Tier-1 suite. `make test-boot` (and so
# `make test`) runs this; the Makefile builds the ISO first.
#
# This is the one boot path tools/test_tier1_boot.sh (OVMF only) does not
# cover. It also boots with -smp 4 and the virtio net/input devices attached.
#
# Until AGAST #3437 this attached a blank `qemu-img create` disk as the
# initramfs, so the kernel panicked right after its banner ("Failed to load
# initramfs") and the script still passed, because it only grepped for
# "Hello from Harland". The verdict is now test_tier1_boot.sh's: any
# KERNEL PANIC or EXCEPTION fails, and the suite must report ALL TESTS PASSED.
#
# Usage: tools/test_boot.sh
#        SKIP_BUILD=1   use the existing userspace build/debug outputs
#        BOOT_TIMEOUT=N seconds for the boot (default 120: TCG boots took
#                       16-39s at load average 26, and a pass stops early)
#        KEEP_WORK=DIR  copy the serial log (bios.log) into DIR
#        SMP=SPEC       QEMU -smp (default: 4 CPUs with sparse APIC IDs
#                       0,1,2,4; SMP=10,sockets=2,cores=9,maxcpus=18 gives
#                       APIC ID 16, past the old [16] arrays: #1883)
#        CPU=MODEL      QEMU -cpu (default Haswell-v1, which has x2APIC, so
#                       the kernel runs its LAPIC in x2APIC mode; append
#                       ,-x2apic for the MMIO xAPIC path). #4184's check:
#                       SMP=20,sockets=2,cores=10 CPU=Haswell-v1,+x2apic
#                       (20 CPUs, APIC IDs up to 25, past the old 16-CPU cap)
#        MACHINE=TYPE   QEMU -machine (default pc; i440fx stops at 255 CPUs).
#        PLUG_CPU=IDS   cold-plug one more CPU at socket/core/thread IDS.
#                       APIC IDs past 255 (MADT type 9, x2APIC only: #4184):
#                       MACHINE=q35 SMP=1,sockets=2,cores=200,maxcpus=400
#                       PLUG_CPU=socket-id=1,core-id=0,thread-id=0
#                       CPU=Haswell-v1,+x2apic boots an AP with APIC ID 256
#
# Every CPU -smp starts must come up: the log must say "(N-1 APs started)".
# The TSC must be calibrated: the log must say "[tsc] N.NNN MHz (source)" (#4181).
#
# Exit: 0 = pass; 1 = the boot failed (panic, exception, failed suite, no
#       verdict before the timeout, or a failed build); 3 = a required tool
#       is missing: a SETUP ERROR (rz's and ci_local.py's EXIT_SETUP), not a
#       regression.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARLAND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECTS_DIR="$(dirname "$HARLAND_DIR")"
ROOT_DIR="$(dirname "$PROJECTS_DIR")"
TIMEOUT="${BOOT_TIMEOUT:-120}"
ISO="$HARLAND_DIR/build/harland.iso"

EXIT_SETUP=3
setup_error() { echo "SETUP ERROR: $*" >&2; exit "$EXIT_SETUP"; }

command -v qemu-system-x86_64 >/dev/null || setup_error "qemu-system-x86_64 not found"
command -v qemu-img >/dev/null || setup_error "qemu-img not found (qemu-utils)"

[ -f "$ISO" ] || { echo "FAIL: ISO not found at $ISO (run: make -C projects/harland iso)"; exit 1; }

# The packages in the initramfs, read after the tool checks so a missing
# tool is still a SETUP ERROR: indium/initramfs.pkgs, the one list shared
# with test_tier1_boot.sh and indium's Makefile and mkiso.sh (AGAST #2759).
# init's suite spawns rzsh and prism's hello_gfx as well as indium's binaries.
USER_PKGS="$(sed -e 's/#.*//' "$PROJECTS_DIR/indium/initramfs.pkgs" | xargs)"
[ -n "$USER_PKGS" ] || { echo "FAIL: no packages in $PROJECTS_DIR/indium/initramfs.pkgs"; exit 1; }

if [ "${SKIP_BUILD:-0}" != "1" ]; then
    for pkg in $USER_PKGS; do
        (cd "$ROOT_DIR" && ./rz build "$pkg")
        brc=$?
        [ "$brc" -eq "$EXIT_SETUP" ] && setup_error "build of $pkg: a toolchain binary is missing"
        [ "$brc" -eq 0 ] || { echo "FAIL: build of $pkg failed"; exit 1; }
    done
fi
INIT_ELF="$PROJECTS_DIR/indium/build/debug/init.elf"
[ -f "$INIT_ELF" ] || { echo "FAIL: not built: $INIT_ELF"; exit 1; }

# Scratch is a `mktemp -d` removed on exit, so concurrent runs on one host
# never share a path (AGAST #3183), and no disk outlives the run to be booted
# by a later one (the blank initramfs lived in build/ for good, #3437).
T=$(mktemp -d)
trap '[ -n "${KEEP_WORK:-}" ] && cp "$T/bios.log" "$KEEP_WORK"/ 2>/dev/null; rm -rf "$T"' EXIT
SERIAL_LOG="$T/bios.log"

mkdir -p "$T/bin"
for pkg in $USER_PKGS; do
    cp "$PROJECTS_DIR/$pkg"/build/debug/*.elf "$T/bin/" 2>/dev/null || true
done
python3 "$HARLAND_DIR/tools/mkinitramfs.py" --bin-dir "$T/bin" \
    --output "$T/initramfs-base.qcow2" >/dev/null || { echo "FAIL: mkinitramfs failed"; exit 1; }
# The boot writes to its disks; an overlay keeps the built image pristine.
qemu-img create -q -f qcow2 -F qcow2 -b "$T/initramfs-base.qcow2" "$T/initramfs.qcow2" \
    || { echo "FAIL: qemu-img overlay failed"; exit 1; }
# A blank scratch disk for the virtio-blk storage driver.
qemu-img create -q -f qcow2 "$T/storage.qcow2" 512M \
    || { echo "FAIL: qemu-img create failed"; exit 1; }

echo "Testing kernel boot (BIOS/GRUB, real initramfs)..."
echo "ISO: $ISO"

# -cpu Haswell-v1 enables BMI1/BMI2 (bextr etc.); -smp starts the APs.
# 2 sockets x 3 cores: core IDs take 2 bits, so the 4 CPUs' APIC IDs are
# 0,1,2,4, not 0..3; per-CPU state must be indexed by CPU, not APIC ID (#1883).
SMP="${SMP:-4,sockets=2,cores=3,threads=1,maxcpus=6}"
CPU="${CPU:-Haswell-v1}"
MACHINE="${MACHINE:-pc}"
# The CPU count is SMP's leading number (or its cpus= key).
NCPUS="$(printf '%s\n' "$SMP" | sed -nE 's/^([0-9]+).*/\1/p; s/^.*(^|,)cpus=([0-9]+).*/\2/p' | head -1)"
PLUG_ARGS=()
if [ -n "${PLUG_CPU:-}" ]; then
    PLUG_ARGS=(-device "${CPU%%,*}-x86_64-cpu,$PLUG_CPU")
    [ -n "$NCPUS" ] && NCPUS=$((NCPUS + 1))
fi
: > "$SERIAL_LOG"
timeout "$TIMEOUT" qemu-system-x86_64 \
    -machine "$MACHINE" \
    -cpu "$CPU" \
    -cdrom "$ISO" \
    -device virtio-blk-pci,drive=initramfs \
    -drive file="$T/initramfs.qcow2",format=qcow2,if=none,id=initramfs \
    -device virtio-blk-pci,drive=storage \
    -drive file="$T/storage.qcow2",format=qcow2,if=none,id=storage \
    -device virtio-net-pci,netdev=net0 \
    -netdev user,id=net0 \
    -device virtio-keyboard-pci \
    -device virtio-mouse-pci \
    -serial file:"$SERIAL_LOG" \
    -display none \
    -monitor none \
    -smp "$SMP" "${PLUG_ARGS[@]}" \
    -m 2G \
    -no-reboot >/dev/null 2>&1 &
pid=$!
# init halts after the suite, so stop QEMU once a verdict line appears.
timed_out=1
for _ in $(seq 1 "$TIMEOUT"); do
    sleep 1
    grep -aqE "ALL TESTS PASSED|TESTS FAILED|KERNEL PANIC" "$SERIAL_LOG" && { sleep 1; timed_out=0; break; }
    kill -0 "$pid" 2>/dev/null || { timed_out=0; break; }
done
kill "$pid" 2>/dev/null
wait "$pid" 2>/dev/null
# 124: `timeout` stopped QEMU just as the loop saw it gone.
[ $? -eq 124 ] && timed_out=1

echo "----- BIOS boot: serial output (tail) -----"
tail -40 "$SERIAL_LOG"
echo "-------------------------------------------"

if grep -aqE "EXCEPTION|KERNEL PANIC" "$SERIAL_LOG"; then
    grep -aE "EXCEPTION|KERNEL PANIC" "$SERIAL_LOG" | head -5
    echo "FAIL (bios): kernel panic or exception during boot"
    exit 1
fi
if ! grep -aq "ALL TESTS PASSED" "$SERIAL_LOG"; then
    [ "$timed_out" = 1 ] && echo "FAIL (bios): no verdict within ${TIMEOUT}s (BOOT_TIMEOUT)"
    echo "FAIL (bios): init's Tier-1 suite did not report ALL TESTS PASSED"
    exit 1
fi
if [ -n "$NCPUS" ]; then
    want="($((NCPUS - 1)) APs started)"
    if ! grep -aqF "$want" "$SERIAL_LOG"; then
        grep -aE "Boot APs|TIMEOUT|skipped" "$SERIAL_LOG" | head -5
        echo "FAIL (bios): -smp $SMP should start $((NCPUS - 1)) APs: no \"$want\" in the log"
        exit 1
    fi
    echo "PASS (bios): all $((NCPUS - 1)) APs started (-smp $SMP, -cpu $CPU)"
fi
# Every kernel wait is a deadline on the calibrated TSC (#4181): the boot must
# log a measured frequency, not the uncalibrated fallback guess.
tsc=$(grep -aoE "\[tsc\] [0-9]+\.[0-9]{3} MHz \([^)]*\)" "$SERIAL_LOG" | head -1)
if [ -z "$tsc" ] || [[ "$tsc" == *uncalibrated* ]]; then
    echo "FAIL (bios): no calibrated TSC frequency in the log (got: ${tsc:-nothing})"
    exit 1
fi
echo "PASS (bios): $tsc"
echo "PASS (bios): init Tier-1 suite: ALL TESTS PASSED"
exit 0
