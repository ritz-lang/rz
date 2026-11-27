#!/bin/bash
# Boot Harland under OVMF with an xHCI controller and a USB keyboard
# (QEMU -device qemu-xhci -device usb-kbd), AGAST #4887, docs/USB.md
# "Tests": the xHCI bring-up boot.
#
# The initramfs is on the ESP beside the kernel (as test_esp_initramfs_boot.sh
# boots it), so the boot needs no block device. The kernel brings the
# controller up in kernel_main (BIOS handoff, reset, rings, interrupter 0 on
# an MSI-X vector aimed at the BSP); the keyboard then enumerates on events
# alone: port reset, Enable Slot, Address Device, the device and
# configuration descriptors, SET_CONFIGURATION. There is no polled fallback
# yet (#4891), so every step proves an MSI-X interrupt reached the BSP.
#
# Two keyboards: usb-kbd at its default high speed, and one with
# usb_version=1 at full speed (EP0's size read from the device descriptor's
# first 8 bytes before the rest). Passes only if:
#   - the controller is found and running on an MSI-X vector aimed at the
#     BSP;
#   - two root ports report a keyboard connected (once each) and enabled,
#     one at high speed and one at full speed;
#   - slots 1 and 2 are addressed, their device descriptors read (0627:0001);
#   - each configuration is read (interface 0 HID boot keyboard, endpoint
#     0x81 interrupt IN) and SET_CONFIGURATION completes;
#   - no enumeration step failed;
#   - init's Tier-1 suite reports ALL TESTS PASSED;
#   - the kernel took no exception and did not panic.
#
# Usage: tools/test_usb_boot.sh
#        SKIP_BUILD=1   use the existing build/debug outputs
#        BOOT_TIMEOUT=N seconds for the boot (default 120)
#        KEEP_WORK=DIR  copy the serial log (usb.log) into DIR
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
qemu-system-x86_64 -device help 2>/dev/null | grep -q '"qemu-xhci"' || setup_error "this QEMU has no qemu-xhci device"

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

WORK="$(mktemp -d)" || setup_error "mktemp -d failed (is TMPDIR full?)"
trap '[ -n "${KEEP_WORK:-}" ] && cp "$WORK"/*.log "$KEEP_WORK"/ 2>/dev/null; rm -rf "$WORK"' EXIT
mkdir -p "$WORK/bin"
for pkg in $USER_PKGS; do
    cp "$PROJECTS_DIR/$pkg"/build/debug/*.elf "$WORK/bin/" 2>/dev/null || true
done
ESP="$WORK/esp"
mkdir -p "$ESP/EFI/BOOT" "$ESP/harland"
python3 "$HARLAND_DIR/tools/mkinitramfs.py" --bin-dir "$WORK/bin" \
    --output "$ESP/harland/initramfs.tar" >/dev/null || { echo "FAIL: mkinitramfs failed"; exit 1; }
cp "$LOADER_EFI" "$ESP/EFI/BOOT/BOOTX64.EFI"
cp "$KERNEL_ELF" "$ESP/harland/kernel.elf"

vars=()
if [ -n "$OVMF_VARS" ]; then
    cp "$OVMF_VARS" "$WORK/vars.fd"
    vars=(-drive "if=pflash,format=raw,file=$WORK/vars.fd")
fi
SERIAL="$WORK/usb.log"
: > "$SERIAL"
timeout "$TIMEOUT" qemu-system-x86_64 -cpu Haswell-v1 -smp 2 -m 2G \
    -display none -no-reboot -monitor none \
    -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
    -drive "format=raw,file=fat:rw:$ESP" \
    -device qemu-xhci,id=xhci -device usb-kbd,bus=xhci.0 \
    -device usb-kbd,bus=xhci.0,usb_version=1 \
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

echo "----- usb boot: xHCI and USB lines -----"
grep -aE "\[xhci\]|\[usb\]|USB \(|KERNEL PANIC" "$SERIAL" | head -40
echo "----------------------------------------"

rc=0
# need PATTERN WHAT: PASS when the serial log has an extended-regex match.
need() {
    if grep -aqE "$1" "$SERIAL"; then
        echo "PASS: $2"
    else
        echo "FAIL: $2 (no line matching: $1)"
        rc=1
    fi
}

if grep -aqE "EXCEPTION|KERNEL PANIC" "$SERIAL"; then
    sed -n '/EXCEPTION/,/CR2/p' "$SERIAL" | head -20
    grep -aA4 "KERNEL PANIC" "$SERIAL" | head -6
    echo "FAIL: kernel panic or exception during boot"
    rc=1
fi
need '^\[xhci\] [0-9A-F]{2}:[0-9A-F]{2}\.[0-7] 1B36:000D v1\.00: ' "the controller is found and its capabilities read (qemu-xhci, xHCI 1.0)"
need '^\[xhci\] running: MSI-X vector [0-9]+ -> BSP$' "the xHCI controller is running on an MSI-X vector aimed at the BSP"
# Two keyboards: usb-kbd at its default high speed, and one with
# usb_version=1 at full speed, whose EP0 size is learned from the first 8
# bytes of its device descriptor.
connected=$(grep -acE '^\[usb\] port [0-9]+: connected \(USB 2\)$' "$SERIAL")
ports=$(grep -aoE '^\[usb\] port [0-9]+: connected' "$SERIAL" | sort -u | wc -l)
if [ "$connected" -eq 2 ] && [ "$ports" -eq 2 ]; then
    echo "PASS: two root ports report a keyboard connected, once each"
else
    echo "FAIL: want 2 'connected' lines on 2 ports, got $connected on $ports"
    rc=1
fi
need '^\[usb\] port [0-9]+: enabled, high speed$' "a port reset enabled the high-speed keyboard"
need '^\[usb\] port [0-9]+: enabled, full speed$' "a port reset enabled the full-speed keyboard"
need '^\[usb\] slot [12]: EP0 max packet 8 \(from the device descriptor\)$' "the full-speed keyboard's EP0 size came from its first 8 bytes"
for slot in 1 2; do
    need "^\\[usb\\] slot $slot addressed: port [0-9]+, address [1-9][0-9]*, EP0 (8|64) bytes$" "slot $slot is addressed"
    need "^\\[usb\\] slot $slot: device 0627:0001, USB [12]\\.[01], class 0, 1 configuration\\(s\\)$" "slot $slot: the device descriptor is read (QEMU's usb-kbd, 0627:0001)"
    need "^\\[usb\\] slot $slot: config 1, 34 bytes$" "slot $slot: the configuration is read"
    need "^\\[usb\\] slot $slot:   interface 0 class 3/1/1, 1 endpoint\\(s\\)$" "slot $slot: its HID boot keyboard interface is parsed"
    need "^\\[usb\\] slot $slot:   endpoint 0x81, 8 bytes, interval [0-9]+$" "slot $slot: its interrupt IN endpoint is parsed"
    need "^\\[usb\\] slot $slot: configured \\(configuration 1\\)$" "slot $slot: SET_CONFIGURATION completed"
done
if grep -aqE '^\[usb\] port [0-9]+: .*device left unconfigured' "$SERIAL"; then
    grep -aE 'device left unconfigured' "$SERIAL"
    echo "FAIL: a device's enumeration failed"
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
