#!/bin/bash
# Boot Harland under OVMF on two CPUs with an NVMe controller and check that
# an AP-issued NVMe command completes through that AP's own MSI-X vector
# (AGAST #4220).
#
# The kernel boots both CPUs ("AP <id> started!"), and once the APIC is up
# and the NVMe controllers are in MSI-X mode, the BSP calls the AP through an
# IPI. The AP reads the last 200 512-byte sectors of the disk with interrupts
# on, so its command must wait for an I/O completion interrupt delivered to
# that AP's Local APIC (a per-CPU I/O queue pair and MSI-X entry), and it logs
#   [msix] nvme AP <apic>: nsid <N>: LBA 32568-32767 fnv1a=H, waited=W, interrupted=I
# with W = 1 (the command waited for its vector) and I > 0 (the vector fired
# on the AP). A driver that polls from APs, or aims every I/O vector at the
# BSP, either logs no such line or logs waited=0/interrupted=0.
#
# No virtio-net: the NIC's MSI-X and the DHCP window are covered by
# test_msix_boot.sh, and this test is about a second CPU.
#
# Passes only if:
#   - both CPUs started ("2 APs started" is APs, so 1 AP plus the BSP);
#   - NVMe came up in MSI-X mode with a per-CPU I/O queue for the AP;
#   - the AP's read returned the pattern's FNV-1a, waited for its vector and
#     the vector fired on the AP;
#   - the kernel took no exception, and init's Tier-1 suite still reports
#     ALL TESTS PASSED with the second CPU up.
#
# Usage: tools/test_nvme_ap_boot.sh
#        SKIP_BUILD=1   use the existing build/debug outputs
#        BOOT_TIMEOUT=N seconds for the boot (default 120)
#        KEEP_WORK=DIR  copy the serial log (nvme-ap.log) into DIR
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
USER_PKGS="indium rzsh prism"

EXIT_SETUP=3
setup_error() { echo "SETUP ERROR: $*" >&2; exit "$EXIT_SETUP"; }

command -v qemu-system-x86_64 >/dev/null || setup_error "qemu-system-x86_64 not found"
command -v qemu-img >/dev/null || setup_error "qemu-img not found (qemu-utils)"
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

# The NVMe disk (16 MiB, 32768 sectors): sector N holds the pattern
# test_nvme_boot.sh uses. Prints the FNV-1a (32-bit) of sectors 32568-32767,
# the bytes the AP reads.
want_fnv=$(python3 - "$WORK/nvme.img" <<'EOF'
import struct, sys
def sector(n):
    return (b"LBA" + struct.pack("<I", n) + b"!") * 64
with open(sys.argv[1], "wb") as f:
    f.write(b"".join(sector(n) for n in range(32768)))
h = 0x811C9DC5
for b in b"".join(sector(n) for n in range(32568, 32768)):
    h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
print(h)
EOF
) || { echo "FAIL: could not write the NVMe disk"; exit 1; }

vars=()
if [ -n "$OVMF_VARS" ]; then
    cp "$OVMF_VARS" "$WORK/vars.fd"
    vars=(-drive "if=pflash,format=raw,file=$WORK/vars.fd")
fi
SERIAL="$WORK/nvme-ap.log"
: > "$SERIAL"
timeout "$TIMEOUT" qemu-system-x86_64 -cpu Haswell-v1 -smp 2 -m 2G \
    -display none -no-reboot -monitor none \
    -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
    -drive "format=raw,file=fat:rw:$WORK/esp" \
    -device virtio-blk-pci,drive=initramfs \
    -drive "file=$WORK/initramfs.qcow2,format=qcow2,if=none,id=initramfs" \
    -device nvme,serial=harland-ap,drive=nvme0 \
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

echo "----- nvme AP boot: AP/MSI-X lines -----"
grep -aE "AP [0-9]+ started|\[msix\] nvme" "$SERIAL" | head -20
echo "----------------------------------------"

rc=0
if grep -aqE "EXCEPTION|KERNEL PANIC" "$SERIAL"; then
    sed -n '/EXCEPTION/,/CR2/p' "$SERIAL" | head -20
    echo "FAIL: kernel exception during boot"
    rc=1
fi
if grep -aqE "AP [1-9][0-9]* started" "$SERIAL"; then
    echo "PASS: a second CPU started"
else
    echo "FAIL: no AP started (boot is not multi-CPU)"
    rc=1
fi
if grep -aqE "\[msix\] nvme [^ ]+: MSI-X on" "$SERIAL"; then
    echo "PASS: NVMe is in MSI-X mode"
else
    grep -a "\[msix\] nvme\|\[nvme\]" "$SERIAL" | head -5
    echo "FAIL: NVMe did not come up in MSI-X mode"
    rc=1
fi
ap_line=$(grep -aoE "\[msix\] nvme AP [0-9]+: nsid [0-9]+: LBA 32568-32767 fnv1a=[0-9]+, waited=[0-9]+, interrupted=[0-9]+" "$SERIAL" | tail -1)
if [ -z "$ap_line" ]; then
    grep -a "\[msix\] nvme AP" "$SERIAL" | head -3
    echo "FAIL: no AP-issued NVMe read logged ([msix] nvme AP <apic>: nsid <N>: LBA 32568-32767 fnv1a=H, waited=W, interrupted=I)"
    rc=1
else
    ap_apic=$(echo "$ap_line" | sed -nE 's/.* AP ([0-9]+):.*/\1/p')
    ap_fnv=$(echo "$ap_line" | sed -nE 's/.*fnv1a=([0-9]+),.*/\1/p')
    ap_waited=$(echo "$ap_line" | sed -nE 's/.*waited=([0-9]+),.*/\1/p')
    ap_intr=$(echo "$ap_line" | sed -nE 's/.*interrupted=([0-9]+)$/\1/p')
    if [ "$ap_fnv" != "$want_fnv" ]; then
        echo "FAIL: AP read returned fnv1a=$ap_fnv, want fnv1a=$want_fnv"
        rc=1
    else
        echo "PASS: AP $ap_apic read LBAs 32568-32767 (fnv1a=$want_fnv)"
    fi
    if [ "$ap_waited" -eq 0 ]; then
        echo "FAIL: the AP-issued command did not wait for its MSI-X vector (polled)"
        rc=1
    elif [ "$ap_intr" -eq 0 ]; then
        echo "FAIL: the AP's I/O vector never fired on the AP (waited=$ap_waited, interrupted=0)"
        rc=1
    else
        echo "PASS: the AP-issued command waited for its vector and the vector fired on AP $ap_apic"
    fi
fi
if grep -aq "ALL TESTS PASSED" "$SERIAL"; then
    echo "PASS: init Tier-1 suite: ALL TESTS PASSED"
else
    [ "$timed_out" = 1 ] && echo "FAIL: no verdict within ${TIMEOUT}s (BOOT_TIMEOUT)"
    echo "FAIL: init's Tier-1 suite did not report ALL TESTS PASSED"
    rc=1
fi
exit $rc
