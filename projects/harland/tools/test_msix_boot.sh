#!/bin/bash
# Boot Harland under OVMF with a virtio-net NIC and an NVMe controller and
# check that PCI devices interrupt the kernel through MSI-X (AGAST #1852).
#
# The kernel walks every PCI device's capability list at boot and logs each
# MSI-X table it finds ("[msix] BB:DD.F VVVV:DDDD: N vectors ..."). The
# virtio-net driver then takes vectors for its config and RX/TX queues,
# programs the MSI-X table and runs its DHCP window with interrupts enabled.
# After that window it logs how many MSI-X interrupts the NIC delivered:
#   [msix] virtio-net interrupts: N
#
# Passes only if:
#   - the NVMe controller (QEMU 1b36:0010) was found to have an MSI-X table;
#   - virtio-net came up in MSI-X mode ("[msix] virtio-net: MSI-X on");
#   - N > 0: interrupts were really delivered through the table, not polled;
#   - the kernel took no exception, and init's Tier-1 suite still reports
#     ALL TESTS PASSED with the NIC and NVMe attached.
#
# The NIC uses QEMU's user-mode network (slirp): its built-in DHCP server
# answers inside QEMU, so this needs no root and no host network.
#
# Usage: tools/test_msix_boot.sh
#        SKIP_BUILD=1   use the existing build/debug outputs
#        BOOT_TIMEOUT=N seconds for the boot (default 120)
#        KEEP_WORK=DIR  copy the serial log (msix.log) into DIR
#        OVMF_CODE=F    OVMF firmware to use (default: search the usual paths)
#
# Exit: 0 = pass; 1 = the boot or a check failed; 3 = a required tool is
#       missing: a SETUP ERROR (rz's and ci_local.py's EXIT_SETUP), not a
#       regression.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARLAND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECTS_DIR="$(dirname "$HARLAND_DIR")"
ROOT_DIR="$(dirname "$PROJECTS_DIR")"
TIMEOUT="${BOOT_TIMEOUT:-120}"
# Same packages as test_tier1_boot.sh: init's suite spawns all of them.
USER_PKGS="indium rzsh ritzutils prism"

EXIT_SETUP=3
setup_error() { echo "SETUP ERROR: $*" >&2; exit "$EXIT_SETUP"; }

command -v qemu-system-x86_64 >/dev/null || setup_error "qemu-system-x86_64 not found"
command -v qemu-img >/dev/null || setup_error "qemu-img not found (qemu-utils)"
if [ -n "${OVMF_CODE:-}" ]; then
    [ -f "$OVMF_CODE" ] || setup_error "OVMF firmware not found: $OVMF_CODE"
else
    for p in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd /usr/share/edk2/x64/OVMF_CODE.4m.fd; do
        if [ -f "$p" ]; then OVMF_CODE="$p"; break; fi
    done
    [ -n "${OVMF_CODE:-}" ] || setup_error "OVMF firmware not found"
fi
OVMF_VARS=""
for p in "${OVMF_CODE/CODE/VARS}" /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd; do
    if [ -f "$p" ]; then OVMF_VARS="$p"; break; fi
done

if [ "${SKIP_BUILD:-0}" != "1" ]; then
    for pkg in harland $USER_PKGS; do
        (cd "$ROOT_DIR" && ./rz build "$pkg")
        brc=$?
        [ "$brc" -eq "$EXIT_SETUP" ] && setup_error "build of $pkg: a toolchain binary is missing"
        [ "$brc" -eq 0 ] || { echo "FAIL: build of $pkg failed"; exit 1; }
    done
fi

KERNEL_ELF="$HARLAND_DIR/build/debug/harland.elf"
LOADER_EFI="$HARLAND_DIR/build/debug/BOOTX64.EFI"
for f in "$KERNEL_ELF" "$LOADER_EFI" "$PROJECTS_DIR/indium/build/debug/init.elf"; do
    [ -f "$f" ] || { echo "FAIL: not built: $f"; exit 1; }
done

WORK="$(mktemp -d)"
trap '[ -n "${KEEP_WORK:-}" ] && cp "$WORK"/*.log "$KEEP_WORK"/ 2>/dev/null; rm -rf "$WORK"' EXIT
mkdir -p "$WORK/bin" "$WORK/esp/EFI/BOOT" "$WORK/esp/harland"
for pkg in $USER_PKGS; do
    cp "$PROJECTS_DIR/$pkg"/build/debug/*.elf "$WORK/bin/" 2>/dev/null || true
done
python3 "$HARLAND_DIR/tools/mkinitramfs.py" --bin-dir "$WORK/bin" \
    --output "$WORK/initramfs.qcow2" >/dev/null || { echo "FAIL: mkinitramfs failed"; exit 1; }
cp "$LOADER_EFI" "$WORK/esp/EFI/BOOT/BOOTX64.EFI"
cp "$KERNEL_ELF" "$WORK/esp/harland/kernel.elf"
# A blank namespace for the NVMe controller: the kernel only needs to find
# its MSI-X capability, not read it.
truncate -s 16M "$WORK/nvme.img"

vars=()
if [ -n "$OVMF_VARS" ]; then
    cp "$OVMF_VARS" "$WORK/vars.fd"
    vars=(-drive "if=pflash,format=raw,file=$WORK/vars.fd")
fi
SERIAL="$WORK/msix.log"
: > "$SERIAL"
# romfile= drops the NIC's iPXE option ROM, so OVMF never tries a network
# boot before the ESP.
timeout "$TIMEOUT" qemu-system-x86_64 -cpu Haswell-v1 -smp 4 -m 2G \
    -display none -no-reboot -monitor none \
    -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
    -drive "format=raw,file=fat:rw:$WORK/esp" \
    -device virtio-blk-pci,drive=initramfs \
    -drive "file=$WORK/initramfs.qcow2,format=qcow2,if=none,id=initramfs" \
    -device virtio-net-pci,netdev=net0,romfile= \
    -netdev user,id=net0 \
    -device nvme,serial=harland-msix,drive=nvme0 \
    -drive "file=$WORK/nvme.img,format=raw,if=none,id=nvme0" \
    -serial "file:$SERIAL" >/dev/null 2>&1 &
pid=$!
timed_out=1
for _ in $(seq 1 "$TIMEOUT"); do
    sleep 1
    grep -aqE "ALL TESTS PASSED|TESTS FAILED|KERNEL PANIC" "$SERIAL" && { sleep 1; timed_out=0; break; }
    kill -0 "$pid" 2>/dev/null || { timed_out=0; break; }
done
kill "$pid" 2>/dev/null
wait "$pid" 2>/dev/null

echo "----- msix boot: MSI-X lines -----"
grep -a "\[msix\]" "$SERIAL" | head -20
echo "----------------------------------"

rc=0
if grep -aqE "EXCEPTION|KERNEL PANIC" "$SERIAL"; then
    sed -n '/EXCEPTION/,/CR2/p' "$SERIAL" | head -20
    echo "FAIL: kernel exception during boot"
    rc=1
fi
# QEMU's NVMe controller is PCI 1b36:0010.
if grep -aiqE "\[msix\] [0-9a-f:.]+ 1b36:0010: [1-9][0-9]* vectors" "$SERIAL"; then
    echo "PASS: NVMe controller's MSI-X table found"
else
    echo "FAIL: no MSI-X table found on the NVMe controller (1b36:0010)"
    rc=1
fi
if grep -aq "\[msix\] virtio-net: MSI-X on" "$SERIAL"; then
    echo "PASS: virtio-net is in MSI-X mode"
else
    echo "FAIL: virtio-net did not come up in MSI-X mode"
    rc=1
fi
count=$(grep -aoE "\[msix\] virtio-net interrupts: [0-9]+" "$SERIAL" | tail -1 | grep -oE "[0-9]+$")
if [ -n "$count" ] && [ "$count" -gt 0 ]; then
    echo "PASS: virtio-net delivered $count MSI-X interrupts"
else
    echo "FAIL: virtio-net MSI-X interrupt counter is ${count:-missing}, want > 0"
    rc=1
fi
if grep -aq "ALL TESTS PASSED" "$SERIAL"; then
    echo "PASS: init Tier-1 suite: ALL TESTS PASSED"
else
    [ "$timed_out" = 1 ] && echo "FAIL: no verdict within ${TIMEOUT}s (BOOT_TIMEOUT)"
    echo "FAIL: init's Tier-1 suite did not report ALL TESTS PASSED"
    rc=1
fi
exit $rc
