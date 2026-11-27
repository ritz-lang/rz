#!/bin/bash
# Boot Harland under OVMF on q35 and exercise the AHCI driver (AGAST #4882, #4884).
#
# The ESP is a USB disk (qemu-xhci). The payload disks are ide-hd on ich9-ahci:
#   ide.0  harland-root, the initramfs qcow2 (block device 0)
#   ide.1  harland-data, 4 MiB raw, sector N is a known pattern (block device 1)
# AHCI_EMPTY=1 attaches no ide-hd. The empty controller must log "0 disks"
# and no per-port line. That mode keeps the initramfs on the ESP and does
# not build user packages.
#
# The default mode reads the initramfs from ide.0 (the ESP has no tar) and
# the data disk through READ DMA EXT. It passes only if both IDENTIFY lines
# name the serial and the sector count, the FNV-1a of LBAs 1-200 on
# harland-data matches the pattern (a 200-sector read, split across the
# 128-sector bounce window), init's Tier-1 suite passes, /var/boots is 1
# and a second boot of the same disks reports 2, and the sectors around
# goliath's image still hold the pattern. A later save can leave an older
# image past the two live ones; the pattern must resume and hold through
# sector 15, which a 4 KiB DMA of a 512-byte write would wipe. The ESP sets
# \harland\storage-format: the patterned disk is not blank, and without it
# kfs would leave it alone (AGAST #4883).
#
# MSI (#4885): both boots switch the HBA to its one MSI message and read
# harland-data polled and then on the vector; each must log commands that
# waited and interrupts counted, the same data, and no completion without
# its interrupt. Boot 2 is q35,kernel-irqchip=split with
# -device intel-iommu,intremap=on,eim=on, so the message goes through
# interrupt remapping (its MSI line names an IRTE).
#
# Usage: tools/test_ahci_boot.sh
#        AHCI_EMPTY=1   empty controller
#        SKIP_BUILD=1   use the existing build/debug outputs
#        BOOT_TIMEOUT=N seconds for each qemu (default 240)
#        KEEP_WORK=DIR  copy the serial logs into DIR
#        OVMF_CODE=F    OVMF firmware (default: search the usual paths)
#        ACCEL=kvm      run under KVM
#
# Exit: 0 = pass; 1 = the boot or a check failed; 3 = a required tool is
#       missing: a SETUP ERROR, not a regression.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARLAND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECTS_DIR="$(dirname "$HARLAND_DIR")"
ROOT_DIR="$(dirname "$PROJECTS_DIR")"
TIMEOUT="${BOOT_TIMEOUT:-240}"
DATA_SECTORS=8192
EMPTY="${AHCI_EMPTY:-0}"
USER_PKGS="indium rzsh prism"

EXIT_SETUP=3
setup_error() { echo "SETUP ERROR: $*" >&2; exit "$EXIT_SETUP"; }

command -v qemu-system-x86_64 >/dev/null || setup_error "qemu-system-x86_64 not found"
command -v python3 >/dev/null || setup_error "python3 not found"
if [ "$EMPTY" != "1" ]; then
    command -v qemu-img >/dev/null || setup_error "qemu-img not found (qemu-utils)"
fi
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
    pkgs="harland"
    if [ "$EMPTY" != "1" ]; then
        pkgs="harland $USER_PKGS"
    fi
    for pkg in $pkgs; do
        (cd "$ROOT_DIR" && ./rz build "$pkg")
        brc=$?
        [ "$brc" -eq "$EXIT_SETUP" ] && setup_error "build of $pkg: a toolchain binary is missing"
        [ "$brc" -eq 0 ] || { echo "FAIL: build of $pkg failed"; exit 1; }
    done
fi

KERNEL_ELF="$HARLAND_DIR/build/debug/harland.elf"
LOADER_EFI="$HARLAND_DIR/build/debug/BOOTX64.EFI"
for f in "$KERNEL_ELF" "$LOADER_EFI"; do
    [ -f "$f" ] || { echo "FAIL: not built: $f"; exit 1; }
done
if [ "$EMPTY" != "1" ]; then
    [ -f "$PROJECTS_DIR/indium/build/debug/init.elf" ] || {
        echo "FAIL: not built: $PROJECTS_DIR/indium/build/debug/init.elf"
        exit 1
    }
fi

WORK="$(mktemp -d)"
trap '[ -n "${KEEP_WORK:-}" ] && cp "$WORK"/*.log "$KEEP_WORK"/ 2>/dev/null; rm -rf "$WORK"' EXIT
mkdir -p "$WORK/bin" "$WORK/esp/EFI/BOOT" "$WORK/esp/harland"
cp "$LOADER_EFI" "$WORK/esp/EFI/BOOT/BOOTX64.EFI"
cp "$KERNEL_ELF" "$WORK/esp/harland/kernel.elf"
: > "$WORK/esp/harland/storage-format"

ROOT_SECTORS=0
want_fnv=""
if [ "$EMPTY" = "1" ]; then
    python3 "$HARLAND_DIR/tools/mkinitramfs.py" --bin-dir "$WORK/bin" \
        --output "$WORK/esp/harland/initramfs.tar" >/dev/null || {
        echo "FAIL: mkinitramfs failed"
        exit 1
    }
else
    for pkg in $USER_PKGS; do
        cp "$PROJECTS_DIR/$pkg"/build/debug/*.elf "$WORK/bin/" 2>/dev/null || true
    done
    python3 "$HARLAND_DIR/tools/mkinitramfs.py" --bin-dir "$WORK/bin" \
        --output "$WORK/initramfs.qcow2" >/dev/null || {
        echo "FAIL: mkinitramfs failed"
        exit 1
    }
    root_bytes=$(qemu-img info --output=json "$WORK/initramfs.qcow2" | python3 -c 'import json,sys; print(json.load(sys.stdin)["virtual-size"])') || {
        echo "FAIL: qemu-img info on the root disk failed"
        exit 1
    }
    if [ $((root_bytes % 512)) -ne 0 ] || [ "$root_bytes" -le 0 ]; then
        echo "FAIL: root image is not a whole number of 512-byte sectors ($root_bytes)"
        exit 1
    fi
    ROOT_SECTORS=$((root_bytes / 512))
    # Sector N is "LBA" + N as u32 LE + "!", 64 times. Prints the FNV-1a of LBAs 1-200.
    want_fnv=$(python3 - "$WORK/data.img" "$DATA_SECTORS" <<'EOF'
import struct, sys
path, sectors = sys.argv[1], int(sys.argv[2])
def sector(n):
    return (b"LBA" + struct.pack("<I", n) + b"!") * 64
with open(path, "wb") as f:
    for n in range(sectors):
        f.write(sector(n))
h = 0x811C9DC5
for b in b"".join(sector(n) for n in range(1, 201)):
    h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
print(h)
EOF
    ) || { echo "FAIL: could not write the data disk"; exit 1; }
fi

vars=()
if [ -n "$OVMF_VARS" ]; then
    cp "$OVMF_VARS" "$WORK/vars.fd"
    vars=(-drive "if=pflash,format=raw,file=$WORK/vars.fd")
fi

disks=()
if [ "$EMPTY" != "1" ]; then
    disks=(
        -drive "file=$WORK/initramfs.qcow2,format=qcow2,if=none,id=root"
        -device "ide-hd,drive=root,bus=ide.0,serial=harland-root"
        -drive "file=$WORK/data.img,format=raw,if=none,id=data"
        -device "ide-hd,drive=data,bus=ide.1,serial=harland-data"
    )
fi

# One qemu. AHCI_WHICH selects which fake serial a CI stub writes.
# -nodefaults drops QEMU's default ide-cd, which would show up as ATAPI.
# AHCI_IR=1: the interrupt-remapping machine (the IOMMU before the devices).
run_qemu() {
    local which="$1"
    local serial="$2"
    local stop_re="$3"
    local machine=q35 iommu=() accel=()
    [ "${ACCEL:-}" = kvm ] && accel=(-accel kvm)
    if [ "${AHCI_IR:-0}" = 1 ]; then
        machine=q35,kernel-irqchip=split
        iommu=(-device intel-iommu,intremap=on,eim=on)
    fi
    export AHCI_WHICH="$which"
    : > "$serial"
    timeout "$TIMEOUT" qemu-system-x86_64 -machine "$machine" "${accel[@]}" -cpu Haswell-v1 -smp 1 -m "$MEM" \
        "${iommu[@]}" \
        -nodefaults -display none -vga std -no-reboot -monitor none \
        -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
        -device qemu-xhci,id=xhci \
        -drive "if=none,id=esp,format=raw,file=fat:rw:$WORK/esp" \
        -device usb-storage,drive=esp,bus=xhci.0,bootindex=0 \
        "${disks[@]}" \
        -serial "file:$serial" >/dev/null 2>&1 &
    local pid=$!
    timed_out=1
    local _i
    for _i in $(seq 1 "$TIMEOUT"); do
        sleep 1
        grep -aqE "$stop_re" "$serial" && { sleep 1; timed_out=0; break; }
        kill -0 "$pid" 2>/dev/null || { timed_out=0; break; }
    done
    kill "$pid" 2>/dev/null
    wait "$pid" 2>/dev/null
}

rc=0
note() { echo "$1"; }

if [ "$EMPTY" = "1" ]; then
    MEM=512M
    SERIAL="$WORK/ahci-empty.log"
    run_qemu 1 "$SERIAL" "0 disks|KERNEL PANIC|EXCEPTION"
    echo "----- ahci boot (empty=1) -----"
    grep -aE "\[ahci\]" "$SERIAL" | head -20
    echo "---------------------------------"
    if [ "$timed_out" = "1" ]; then
        note "FAIL: boot timed out before the AHCI summary"
        rc=1
    fi
    if grep -aqE "EXCEPTION|KERNEL PANIC" "$SERIAL"; then
        sed -n '/EXCEPTION\|KERNEL PANIC/,+8p' "$SERIAL" | head -24
        note "FAIL: kernel exception during boot"
        rc=1
    fi
    if grep -aqE "\[ahci\] [0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f]: 0 disks" "$SERIAL"; then
        note "PASS: empty ich9-ahci logged one summary line"
    else
        note "FAIL: empty controller did not log '0 disks'"
        rc=1
    fi
    if grep -aqE "\[ahci\] .* port " "$SERIAL"; then
        note "FAIL: empty controller logged a port line"
        rc=1
    else
        note "PASS: empty controller logged no per-port line"
    fi
    if [ "$rc" -eq 0 ]; then
        note "PASS: ahci boot empty=1"
    fi
    exit "$rc"
fi

MEM=2G
check_identify() {
    local serial="$1"
    local root_re data_re
    root_re="\[ahci\] [0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f] port 0: .*harland-root, ${ROOT_SECTORS} sectors, 512-byte sectors"
    data_re="\[ahci\] [0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f] port 1: .*harland-data, ${DATA_SECTORS} sectors, 512-byte sectors"
    if grep -aqE "EXCEPTION|KERNEL PANIC" "$serial"; then
        sed -n '/EXCEPTION\|KERNEL PANIC/,+8p' "$serial" | head -24
        note "FAIL: kernel exception during boot"
        rc=1
    fi
    if grep -aqE "$root_re" "$serial"; then
        note "PASS: port 0 identified harland-root ($ROOT_SECTORS sectors)"
    else
        note "FAIL: port 0 IDENTIFY line missing or wrong sector count"
        rc=1
    fi
    if grep -aqE "$data_re" "$serial"; then
        note "PASS: port 1 identified harland-data ($DATA_SECTORS sectors)"
    else
        note "FAIL: port 1 IDENTIFY line missing or wrong sector count"
        rc=1
    fi
    if grep -aqE "\[ahci\] [0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f]: 2 disks" "$serial"; then
        note "PASS: controller summary is 2 disks"
    else
        note "FAIL: summary is not '2 disks'"
        rc=1
    fi
}

check_persist() {
    local serial="$1"
    local which="$2"
    local fnv_re
    fnv_re="\[ahci\] [0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f] port 1: LBA 1-200 fnv1a=${want_fnv}([^0-9]|$)"
    if grep -aqE "$fnv_re" "$serial"; then
        note "PASS: harland-data read back the pattern (fnv1a=$want_fnv)"
    else
        note "FAIL: harland-data fingerprint missing (want fnv1a=$want_fnv)"
        rc=1
    fi
    if grep -aqE "\[initramfs\] Loaded [1-9]" "$serial"; then
        note "PASS: initramfs loaded from harland-root"
    else
        note "FAIL: the initramfs did not load from harland-root"
        rc=1
    fi
    if grep -aqE "Persistent storage \(goliath image: boot ${which}," "$serial"; then
        note "PASS: /var/boots is $which"
    else
        note "FAIL: persistent storage did not report boot $which"
        rc=1
    fi
    if grep -aq "ALL TESTS PASSED" "$serial"; then
        note "PASS: init Tier-1 suite: ALL TESTS PASSED"
    else
        [ "$timed_out" = 1 ] && note "FAIL: no verdict within ${TIMEOUT}s (BOOT_TIMEOUT)"
        note "FAIL: init's Tier-1 suite did not report ALL TESTS PASSED"
        rc=1
    fi
}

# check_msi SERIAL IR: the MSI read waited on the vector and was counted;
# IR=1 also wants the message through an IRTE.
check_msi() {
    local serial="$1" ir="$2" bdf="[0-9a-f]{2}:[0-9a-f]{2}\\.[0-9a-f]"
    if [ "$ir" = 1 ]; then
        if grep -aqE "\[ahci\] $bdf: MSI on, vector [0-9]+, IRTE [0-9]+ -> APIC ID [0-9]+" "$serial"; then
            note "PASS: AHCI MSI goes through an IRTE (interrupt remapping)"
        else
            note "FAIL: no 'MSI on, vector V, IRTE h' line on the intremap boot"
            rc=1
        fi
    elif grep -aqE "\[ahci\] $bdf: MSI on, vector [0-9]+$" "$serial"; then
        note "PASS: AHCI MSI on, not remapped"
    else
        note "FAIL: no 'MSI on, vector V' line"
        rc=1
    fi
    if grep -aqE "\[ahci\] $bdf port 1: MSI read LBA 1-200 waited=[1-9][0-9]*, interrupted=[1-9][0-9]*, data: same" "$serial"; then
        note "PASS: harland-data read on the vector: waited, interrupted, same data"
    else
        note "FAIL: harland-data MSI read did not wait, was not interrupted, or differed"
        rc=1
    fi
    if grep -aqE "\[ahci\] msi interrupts: [1-9][0-9]*, commands waited: [1-9][0-9]*, completions without one: 0$" "$serial"; then
        note "PASS: AHCI interrupts counted, commands waited, none missed"
    else
        note "FAIL: AHCI msi summary wants interrupts > 0, waited > 0, 0 without one"
        rc=1
    fi
}

SERIAL1="$WORK/ahci-persist-1.log"
run_qemu 1 "$SERIAL1" "ALL TESTS PASSED|TESTS FAILED|KERNEL PANIC|EXCEPTION"
echo "----- ahci persist boot 1 -----"
grep -aE "\[ahci\]|\[initramfs\] Loaded|Persistent storage|ALL TESTS PASSED|TESTS FAILED" "$SERIAL1" | head -30
echo "---------------------------------"
if [ "$timed_out" = "1" ]; then
    note "FAIL: boot 1 timed out"
    rc=1
fi
check_identify "$SERIAL1"
check_persist "$SERIAL1" 1
check_msi "$SERIAL1" 0
if [ "$rc" -ne 0 ]; then
    exit "$rc"
fi

SERIAL2="$WORK/ahci-persist-2.log"
AHCI_IR=1 run_qemu 2 "$SERIAL2" "ALL TESTS PASSED|TESTS FAILED|KERNEL PANIC|EXCEPTION"
echo "----- ahci persist boot 2 -----"
grep -aE "\[ahci\]|\[initramfs\] Loaded|Persistent storage|ALL TESTS PASSED|TESTS FAILED" "$SERIAL2" | head -30
echo "---------------------------------"
check_msi "$SERIAL2" 1
if [ "$timed_out" = "1" ]; then
    note "FAIL: boot 2 timed out"
    rc=1
fi
if grep -aqE "EXCEPTION|KERNEL PANIC" "$SERIAL2"; then
    sed -n '/EXCEPTION\|KERNEL PANIC/,+8p' "$SERIAL2" | head -24
    note "FAIL: kernel exception during boot"
    rc=1
fi
if grep -aqE "Persistent storage \(goliath image: boot 2," "$SERIAL2"; then
    note "PASS: /var/boots is 2"
else
    note "FAIL: persistent storage did not report boot 2"
    rc=1
fi
if grep -aq "ALL TESTS PASSED" "$SERIAL2"; then
    note "PASS: second boot Tier-1 suite: ALL TESTS PASSED"
else
    [ "$timed_out" = 1 ] && note "FAIL: no verdict within ${TIMEOUT}s (BOOT_TIMEOUT)"
    note "FAIL: second boot did not report ALL TESTS PASSED"
    rc=1
fi

layout=$(python3 - "$WORK/data.img" <<'EOF2'
import struct, sys
data = open(sys.argv[1], "rb").read()
covered = set()
for idx in (0, 1):
    sb = data[idx * 512:(idx + 1) * 512]
    if len(sb) < 512 or sb[:8] != b"GOLIATHB":
        continue
    version, sector = struct.unpack_from("<II", sb, 8)
    lba, length = struct.unpack_from("<QQ", sb, 24)
    if (version, sector) != (2, 512) or lba < 2 or length == 0:
        print("header %d names a bad image (lba %d, len %d)" % (idx, lba, length)); sys.exit()
    if data[lba * 512:lba * 512 + 8] != b"GOLIATHS":
        print("header %d names an image at sector %d, which is not a goliath image" % (idx, lba)); sys.exit()
    covered.update(range(lba, lba + (length + 511) // 512))
if not covered:
    print("no goliath slot header on the disk"); sys.exit()
print("ok " + " ".join(str(n) for n in sorted(covered)))
EOF2
) || layout="unreadable"
if grep -aq "Persistent storage" "$SERIAL2" && [ "${layout%% *}" = ok ]; then
    note "PASS: persistent storage saved a goliath image to harland-data"
else
    note "FAIL: persistent storage did not save a goliath image on harland-data (${layout})"
    rc=1
fi
covered="${layout#ok }"
case "$covered" in ''|*[!0-9\ ]*) covered="" ;; esac
# block_store_save appends, then a smaller image can fit back at LBA 2 and
# leave the previous image's tail behind the two live slots. That tail is
# stale image. A 512-byte write that DMAs a whole 4 KiB page dirties the
# rest of that page, so once the pattern resumes it must hold through
# sector 15. Sector 1 stays pattern unless a slot header landed there.
bad=$(python3 - "$WORK/data.img" "$covered" <<'EOF2'
import struct, sys
data = open(sys.argv[1], "rb").read()
covered = {int(n) for n in sys.argv[2].split() if n}
def sector(n):
    return (b"LBA" + struct.pack("<I", n) + b"!") * 64
bad = []
if data[512:520] != b"GOLIATHB" and data[512:1024] != sector(1):
    bad.append(1)
rest = list(range((max(covered) + 1) if covered else 2, 16))
seen = False
for n in rest:
    if data[n * 512:(n + 1) * 512] == sector(n):
        seen = True
    elif seen:
        bad.append(n)
if rest and not seen:
    bad.extend(rest)
print(" ".join(str(n) for n in bad))
EOF2
) || bad="?"
if [ -z "$bad" ]; then
    note "PASS: sectors beside goliath's writes kept the pattern"
else
    note "FAIL: sectors beside goliath's writes were clobbered: ${bad}"
    rc=1
fi

if [ "$rc" -eq 0 ]; then
    note "PASS: ahci persist boot 1 then 2"
fi
exit "$rc"
