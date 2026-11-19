#!/bin/bash
# Boot Harland under OVMF with no block device at all: the initramfs is
# \harland\initramfs.tar on the ESP, beside the kernel (AGAST #4253).
#
# This is the EC2 Nitro / laptop case: no virtio-blk, so the kernel cannot
# read a raw TAR disk. BOOTX64.EFI reads the TAR with the UEFI file protocol
# into loader memory and passes its base and size in BootInfo (version 2);
# the kernel unpacks it from memory and only falls back to virtio-blk when
# BootInfo carries no initramfs.
#
# The ESP is a QEMU vvfat directory (EFI/BOOT/BOOTX64.EFI, harland/kernel.elf,
# harland/initramfs.tar). QEMU gets no -drive besides the ESP and the OVMF
# flash, and no virtio-blk, NVMe or other disk device.
#
# Passes only if:
#   - the loader logged that it read harland\initramfs.tar (its size in bytes,
#     the same as the file's);
#   - the kernel loaded the initramfs from boot memory, not from a disk;
#   - init's Tier-1 suite reports ALL TESTS PASSED;
#   - the kernel took no exception and did not panic.
#
# Usage: tools/test_esp_initramfs_boot.sh
#        SKIP_BUILD=1   use the existing build/debug outputs
#        BOOT_TIMEOUT=N seconds for the boot (default 120)
#        KEEP_WORK=DIR  copy the serial log (esp-initramfs.log) into DIR
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

EXIT_SETUP=3
setup_error() { echo "SETUP ERROR: $*" >&2; exit "$EXIT_SETUP"; }

command -v qemu-system-x86_64 >/dev/null || setup_error "qemu-system-x86_64 not found"
command -v python3 >/dev/null || setup_error "python3 not found"
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

# The initramfs packages: indium/initramfs.pkgs, the list test_tier1_boot.sh
# and indium's Makefile share (AGAST #2759).
USER_PKGS="$(sed -e 's/#.*//' "$PROJECTS_DIR/indium/initramfs.pkgs" | xargs)"
[ -n "$USER_PKGS" ] || { echo "FAIL: no packages in $PROJECTS_DIR/indium/initramfs.pkgs"; exit 1; }

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
ESP="$WORK/esp"
mkdir -p "$WORK/bin" "$ESP/EFI/BOOT" "$ESP/harland"
for pkg in $USER_PKGS; do
    cp "$PROJECTS_DIR/$pkg"/build/debug/*.elf "$WORK/bin/" 2>/dev/null || true
done
python3 "$HARLAND_DIR/tools/mkinitramfs.py" --bin-dir "$WORK/bin" \
    --output "$ESP/harland/initramfs.tar" >/dev/null || { echo "FAIL: mkinitramfs failed"; exit 1; }
cp "$LOADER_EFI" "$ESP/EFI/BOOT/BOOTX64.EFI"
cp "$KERNEL_ELF" "$ESP/harland/kernel.elf"
TAR_SIZE=$(stat -c %s "$ESP/harland/initramfs.tar")

vars=()
if [ -n "$OVMF_VARS" ]; then
    cp "$OVMF_VARS" "$WORK/vars.fd"
    vars=(-drive "if=pflash,format=raw,file=$WORK/vars.fd")
fi
SERIAL="$WORK/esp-initramfs.log"
: > "$SERIAL"
# The ESP is the only disk: no virtio-blk, no NVMe.
timeout "$TIMEOUT" qemu-system-x86_64 -cpu Haswell-v1 -smp 4 -m 2G \
    -display none -no-reboot -monitor none \
    -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
    -drive "format=raw,file=fat:rw:$ESP" \
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

echo "----- ESP-initramfs boot: initramfs lines -----"
grep -aE "initramfs|Initramfs|VirtIO block|KERNEL PANIC" "$SERIAL" | head -20
echo "-----------------------------------------------"

rc=0
if grep -aqE "EXCEPTION|KERNEL PANIC" "$SERIAL"; then
    sed -n '/EXCEPTION/,/CR2/p' "$SERIAL" | head -20
    grep -aA4 "KERNEL PANIC" "$SERIAL" | head -6
    echo "FAIL: kernel panic or exception during boot"
    rc=1
fi
if grep -aqF "Read initramfs: $TAR_SIZE bytes" "$SERIAL"; then
    echo "PASS: BOOTX64.EFI read harland\\initramfs.tar ($TAR_SIZE bytes) from the ESP"
else
    echo "FAIL: BOOTX64.EFI did not log 'Read initramfs: $TAR_SIZE bytes'"
    rc=1
fi
if grep -aqE "\[initramfs\] Loading from boot memory" "$SERIAL" \
        && grep -aqE "\[initramfs\] Loaded [1-9][0-9]* files from boot memory" "$SERIAL"; then
    echo "PASS: the kernel loaded the initramfs from the BootInfo hand-off"
else
    echo "FAIL: the kernel did not load the initramfs from boot memory"
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
