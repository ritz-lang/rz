#!/bin/bash
# Boot Harland under OVMF on q35 and check the polled AHCI probe (AGAST #4882).
#
# The ESP is a USB disk (qemu-xhci) so the boot has no virtio-blk and no
# NVMe, and the ESP does not occupy an ich9-ahci port. The two AHCI disks
# are ide-hd units:
#   ide.0  harland-root, ROOT_SECTORS 512-byte sectors
#   ide.1  harland-data, DATA_SECTORS 512-byte sectors
# The initramfs is \harland\initramfs.tar on the ESP, so the kernel reaches
# init without reading those SATA disks. This ticket only identifies them.
# Read/write and /var/boots land in #4884.
#
# AHCI_EMPTY=1 attaches no ide-hd. The empty ich9-ahci must log one summary
# line, "0 disks", and no per-port line.
#
# Passes only if both IDENTIFY lines name the serial and the sector count
# this script created, the summary says 2 disks (or 0 in the empty boot),
# and the kernel did not take an exception before that summary.
#
# Usage: tools/test_ahci_boot.sh
#        AHCI_EMPTY=1   empty controller
#        SKIP_BUILD=1   use the existing build/debug outputs
#        BOOT_TIMEOUT=N seconds (default 180)
#        KEEP_WORK=DIR  copy the serial log into DIR
#        OVMF_CODE=F    OVMF firmware (default: search the usual paths)

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARLAND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECTS_DIR="$(dirname "$HARLAND_DIR")"
ROOT_DIR="$(dirname "$PROJECTS_DIR")"
TIMEOUT="${BOOT_TIMEOUT:-180}"
ROOT_SECTORS=2048
DATA_SECTORS=8192
EMPTY="${AHCI_EMPTY:-0}"

EXIT_SETUP=3
setup_error() { echo "SETUP ERROR: $*" >&2; exit "$EXIT_SETUP"; }

command -v qemu-system-x86_64 >/dev/null || setup_error "qemu-system-x86_64 not found"
command -v python3 >/dev/null || setup_error "python3 not found"
if [ -n "${OVMF_CODE:-}" ]; then
    [ -f "$OVMF_CODE" ] || setup_error "OVMF firmware not found: $OVMF_CODE"
else
    for p in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd \
             /usr/share/edk2/x64/OVMF_CODE.4m.fd /usr/share/ovmf/OVMF.fd; do
        if [ -f "$p" ]; then OVMF_CODE="$p"; break; fi
    done
    [ -n "${OVMF_CODE:-}" ] || setup_error "OVMF firmware not found"
fi
OVMF_VARS=""
for p in "${OVMF_CODE/CODE/VARS}" /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd; do
    if [ -f "$p" ]; then OVMF_VARS="$p"; break; fi
done

if [ "${SKIP_BUILD:-0}" != "1" ]; then
    (cd "$ROOT_DIR" && ./rz build harland)
    brc=$?
    [ "$brc" -eq "$EXIT_SETUP" ] && setup_error "build of harland: a toolchain binary is missing"
    [ "$brc" -eq 0 ] || { echo "FAIL: build of harland failed"; exit 1; }
fi

KERNEL_ELF="$HARLAND_DIR/build/debug/harland.elf"
LOADER_EFI="$HARLAND_DIR/build/debug/BOOTX64.EFI"
for f in "$KERNEL_ELF" "$LOADER_EFI"; do
    [ -f "$f" ] || { echo "FAIL: not built: $f"; exit 1; }
done

WORK="$(mktemp -d)"
trap '[ -n "${KEEP_WORK:-}" ] && cp "$WORK"/*.log "$KEEP_WORK"/ 2>/dev/null; rm -rf "$WORK"' EXIT
mkdir -p "$WORK/bin" "$WORK/esp/EFI/BOOT" "$WORK/esp/harland"
python3 "$HARLAND_DIR/tools/mkinitramfs.py" --bin-dir "$WORK/bin" \
    --output "$WORK/esp/harland/initramfs.tar" >/dev/null || { echo "FAIL: mkinitramfs failed"; exit 1; }
cp "$LOADER_EFI" "$WORK/esp/EFI/BOOT/BOOTX64.EFI"
cp "$KERNEL_ELF" "$WORK/esp/harland/kernel.elf"

if [ "$EMPTY" != "1" ]; then
    dd if=/dev/zero of="$WORK/root.img" bs=512 count="$ROOT_SECTORS" status=none
    dd if=/dev/zero of="$WORK/data.img" bs=512 count="$DATA_SECTORS" status=none
fi

vars=()
if [ -n "$OVMF_VARS" ]; then
    cp "$OVMF_VARS" "$WORK/vars.fd"
    vars=(-drive "if=pflash,format=raw,file=$WORK/vars.fd")
fi
if [ "$EMPTY" = "1" ]; then
    LOG_NAME=ahci-empty.log
else
    LOG_NAME=ahci-identify.log
fi
SERIAL="$WORK/$LOG_NAME"
: > "$SERIAL"

disks=()
if [ "$EMPTY" != "1" ]; then
    disks=(
        -drive "file=$WORK/root.img,format=raw,if=none,id=root"
        -device "ide-hd,drive=root,bus=ide.0,serial=harland-root"
        -drive "file=$WORK/data.img,format=raw,if=none,id=data"
        -device "ide-hd,drive=data,bus=ide.1,serial=harland-data"
    )
fi

# -nodefaults drops QEMU's default ide-cd. On an otherwise empty ich9-ahci
# that CD is a present ATAPI device, and the empty-controller check would
# see a port line for it.
timeout "$TIMEOUT" qemu-system-x86_64 -machine q35 -cpu Haswell-v1 -smp 1 -m 512M \
    -nodefaults -display none -vga std -no-reboot -monitor none \
    -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
    -device qemu-xhci,id=xhci \
    -drive "if=none,id=esp,format=raw,file=fat:rw:$WORK/esp" \
    -device usb-storage,drive=esp,bus=xhci.0,bootindex=0 \
    "${disks[@]}" \
    -serial "file:$SERIAL" >/dev/null 2>&1 &
pid=$!
timed_out=1
for _ in $(seq 1 "$TIMEOUT"); do
    sleep 1
    if [ "$EMPTY" = "1" ]; then
        grep -aqE "0 disks|KERNEL PANIC|EXCEPTION" "$SERIAL" && { sleep 1; timed_out=0; break; }
    else
        grep -aqE "2 disks|KERNEL PANIC|EXCEPTION" "$SERIAL" && { sleep 1; timed_out=0; break; }
    fi
    kill -0 "$pid" 2>/dev/null || { timed_out=0; break; }
done
kill "$pid" 2>/dev/null
wait "$pid" 2>/dev/null

echo "----- ahci boot (empty=$EMPTY) -----"
grep -aE "\[ahci\]" "$SERIAL" | head -20
echo "---------------------------------"

rc=0
if [ "$timed_out" = "1" ]; then
    echo "FAIL: boot timed out before the AHCI summary"
    rc=1
fi
if grep -aqE "EXCEPTION|KERNEL PANIC" "$SERIAL"; then
    sed -n '/EXCEPTION\|KERNEL PANIC/,+8p' "$SERIAL" | head -24
    echo "FAIL: kernel exception during boot"
    rc=1
fi

if [ "$EMPTY" = "1" ]; then
    if grep -aqE "\[ahci\] [0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f]: 0 disks" "$SERIAL"; then
        echo "PASS: empty ich9-ahci logged one summary line"
    else
        echo "FAIL: empty controller did not log '0 disks'"
        rc=1
    fi
    if grep -aqE "\[ahci\] .* port " "$SERIAL"; then
        echo "FAIL: empty controller logged a port line"
        rc=1
    else
        echo "PASS: empty controller logged no per-port line"
    fi
else
    root_re="\[ahci\] [0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f] port 0: .*harland-root, ${ROOT_SECTORS} sectors, 512-byte sectors"
    data_re="\[ahci\] [0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f] port 1: .*harland-data, ${DATA_SECTORS} sectors, 512-byte sectors"
    if grep -aqE "$root_re" "$SERIAL"; then
        echo "PASS: port 0 identified harland-root ($ROOT_SECTORS sectors)"
    else
        echo "FAIL: port 0 IDENTIFY line missing or wrong sector count"
        rc=1
    fi
    if grep -aqE "$data_re" "$SERIAL"; then
        echo "PASS: port 1 identified harland-data ($DATA_SECTORS sectors)"
    else
        echo "FAIL: port 1 IDENTIFY line missing or wrong sector count"
        rc=1
    fi
    if grep -aqE "\[ahci\] [0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f]: 2 disks" "$SERIAL"; then
        echo "PASS: controller summary is 2 disks"
    else
        echo "FAIL: summary is not '2 disks'"
        rc=1
    fi
fi

if [ "$rc" -eq 0 ]; then
    echo "PASS: ahci boot empty=$EMPTY"
fi
exit "$rc"
