#!/bin/bash
# Boot the hardware-inventory stick image headless under QEMU + OVMF and
# check the dump it writes back to itself (AGAST #3406).
#
#   1. build HWINV.EFI (rz build harland) unless SKIP_BUILD=1;
#   2. esp_image.py builds the stick image: GPT + FAT32 ESP with
#      \EFI\BOOT\BOOTX64.EFI, exactly what `dd` would write to a USB stick;
#   3. QEMU (q35, OVMF) boots it from a USB mass-storage device on an xHCI
#      controller, writable, with no NVRAM boot entry: firmware finds the
#      removable-media default path itself, as on real hardware;
#   4. once the app logs "HWINV: DONE" (or fails, or the timeout passes)
#      QEMU is stopped, fsck.fat (when installed) checks the firmware's
#      writes left the FAT consistent, and the files are read back;
#   5. check_dump.py validates them against what this script told QEMU:
#      -smp (MADT CPUs), -m (SMBIOS type 17 and the memory map),
#      -smbios type=1 strings, the q35 host bridge, the xHCI controller and a
#      virtio-rng device, and the ACPI tables q35 always has.
#
# Steps 2-5 run twice, each on a fresh image: QEMU's SMBIOS entry point
# 64-bit (SMBIOS3, "_SM3_") and 32-bit (2.x, "_SM_"), so both of the app's
# SMBIOS paths are booted. ~12 s for both under TCG.
#
# Knobs:
#   SKIP_BUILD=1    use projects/harland/build/debug/HWINV.EFI as it is
#   BOOT_TIMEOUT=N  seconds QEMU may run (default 120)
#   KEEP_WORK=DIR   copy the image, serial log and extracted dump into DIR
#   OVMF_CODE=F     OVMF firmware (default: search the usual paths)
#
# Exit: 0 = pass; 1 = the boot or a check failed; 3 = a tool is missing or
#       the build failed: a SETUP ERROR (ci_local.py's EXIT_SETUP).

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARLAND_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(cd "$HARLAND_DIR/../.." && pwd)"
TIMEOUT="${BOOT_TIMEOUT:-120}"
EFI="$HARLAND_DIR/build/debug/HWINV.EFI"

EXIT_SETUP=3
setup_error() { echo "SETUP ERROR: $*" >&2; exit "$EXIT_SETUP"; }

command -v qemu-system-x86_64 >/dev/null || setup_error "qemu-system-x86_64 not found (qemu-system-x86)"
command -v python3 >/dev/null || setup_error "python3 not found"

if [ -z "${OVMF_CODE:-}" ]; then
    for path in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd \
                /usr/share/edk2/x64/OVMF_CODE.4m.fd /usr/share/edk2-ovmf/x64/OVMF_CODE.4m.fd; do
        [ -f "$path" ] && { OVMF_CODE="$path"; break; }
    done
fi
[ -n "${OVMF_CODE:-}" ] && [ -f "$OVMF_CODE" ] || setup_error "OVMF not found (ovmf package)"

if [ "${SKIP_BUILD:-}" != 1 ]; then
    (cd "$ROOT_DIR" && ./rz build harland) >/dev/null 2>&1 \
        || { (cd "$ROOT_DIR" && ./rz build harland) 2>&1 | tail -20; setup_error "build of harland failed"; }
fi
[ -f "$EFI" ] || setup_error "no $EFI (build harland: ./rz build harland)"

WORK=$(mktemp -d "${TMPDIR:-/tmp}/hwinv-test.XXXXXX")
cleanup() {
    if [ -n "${KEEP_WORK:-}" ]; then
        mkdir -p "$KEEP_WORK"
        cp -r "$WORK"/. "$KEEP_WORK"/ 2>/dev/null || true
    fi
    rm -rf "$WORK"
}
trap cleanup EXIT

# What the dump must show. -m and -smp are the machine; the SMBIOS strings
# are ours, so a match proves the table came from this QEMU, not a constant.
CPUS=2
MEM_MIB=512
SMBIOS_MFR="RitzInventoryTest"
SMBIOS_PRODUCT="QEMU-HWINV"
SMBIOS_SERIAL="HWINV-3406"

FSCK_FAT=$(command -v fsck.fat || ls /usr/sbin/fsck.fat /sbin/fsck.fat 2>/dev/null | head -1)

# One boot per SMBIOS entry point: 64 (SMBIOS3, _SM3_) and 32 (2.x, _SM_).
# Each on a fresh image, so each dump is the only one on its stick.
boot_and_check() {
    local ep="$1"
    local img="$WORK/hwinv-$ep.img" serial="$WORK/serial-$ep.log" out="$WORK/esp-$ep"
    python3 "$SCRIPT_DIR/esp_image.py" build "$img" --efi "$EFI" || { echo "FAIL: esp_image.py build"; return 1; }
    echo "=== Boot: q35 + OVMF, USB stick, SMBIOS entry point $ep-bit (${TIMEOUT}s max) ==="
    : > "$serial"
    # Haswell, as boot/test.sh: LLVM may emit BMI1 instructions qemu64 lacks.
    timeout "$TIMEOUT" qemu-system-x86_64 \
        -machine "q35,smbios-entry-point-type=$ep" -cpu Haswell -smp "$CPUS" -m "${MEM_MIB}M" \
        -drive if=pflash,format=raw,readonly=on,file="$OVMF_CODE" \
        -smbios "type=1,manufacturer=$SMBIOS_MFR,product=$SMBIOS_PRODUCT,serial=$SMBIOS_SERIAL" \
        -device qemu-xhci,id=xhci \
        -drive if=none,id=stick,format=raw,file="$img" \
        -device usb-storage,bus=xhci.0,drive=stick,removable=on \
        -device virtio-rng-pci \
        -vga std \
        -display none -serial file:"$serial" -monitor none \
        -no-reboot 2>"$WORK/qemu-$ep.err" &
    local qemu=$!
    # The app powers off 15 s after DONE (or at a key); don't wait for that.
    # `timeout` passes the TERM on to QEMU.
    while kill -0 "$qemu" 2>/dev/null; do
        if grep -aqE "HWINV: (DONE|FAIL)" "$serial"; then
            sleep 2
            kill "$qemu" 2>/dev/null
            break
        fi
        sleep 1
    done
    wait "$qemu" 2>/dev/null
    grep -v "TCG doesn't support requested feature\|terminating on signal" "$WORK/qemu-$ep.err"

    echo "--- serial (HWINV lines) ---"
    grep -a "HWINV\|^  [a-z]*:" "$serial" | tr -d '\r' | sed 's/\x1b\[[0-9;]*[A-Za-z]//g'
    if ! grep -aq "HWINV: DONE" "$serial"; then
        echo "--- last 40 serial lines ---"
        tail -40 "$serial" | tr -d '\r' | sed 's/\x1b\[[0-9;]*[A-Za-z]//g'
        echo "FAIL: the app did not report HWINV: DONE within ${TIMEOUT}s"
        return 1
    fi
    if [ -n "$FSCK_FAT" ]; then
        python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import esp_image; open(sys.argv[3], "wb").write(esp_image.partition_bytes(sys.argv[2]))' \
            "$SCRIPT_DIR" "$img" "$WORK/esp-$ep.part"
        "$FSCK_FAT" -n "$WORK/esp-$ep.part" >"$WORK/fsck-$ep.log" 2>&1 \
            || { cat "$WORK/fsck-$ep.log"; echo "FAIL: fsck.fat: the firmware left the ESP inconsistent"; return 1; }
        rm -f "$WORK/esp-$ep.part"
        echo "fsck.fat: ESP clean after the firmware's writes"
    fi
    python3 "$SCRIPT_DIR/esp_image.py" extract "$img" "$out" || { echo "FAIL: cannot read the image back"; return 1; }
    local anchor="_SM3_"
    [ "$ep" = 32 ] && anchor="_SM_"
    local dump
    dump=$(ls -d "$out"/INVENTORY/*/ 2>/dev/null | head -1)
    if [ -z "$dump" ] || ! head -c 5 "$dump/smbios/smbios_entry_point" | grep -aq "^$anchor"; then
        echo "FAIL: smbios_entry_point is not the $ep-bit ($anchor) entry point QEMU was asked for"
        return 1
    fi
    python3 "$SCRIPT_DIR/check_dump.py" "$out" \
        --expect-cpus "$CPUS" --expect-mem-mib "$MEM_MIB" \
        --expect-smbios "manufacturer=$SMBIOS_MFR" \
        --expect-smbios "product=$SMBIOS_PRODUCT" \
        --expect-smbios "serial=$SMBIOS_SERIAL" \
        --expect-acpi FACP,APIC,HPET,MCFG,DSDT,FACS \
        --expect-pci 8086:29c0 --expect-pci 1af4:1005 --expect-pci 1b36:000d
}

status=0
for ep in 64 32; do
    boot_and_check "$ep" || status=1
done
[ "$status" = 0 ] && echo "PASS: the inventory stick booted and dumped (SMBIOS3 and 2.x)"
exit "$status"
