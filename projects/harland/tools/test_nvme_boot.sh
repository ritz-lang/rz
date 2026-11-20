#!/bin/bash
# Boot Harland under OVMF with NVMe disks only, no virtio-blk (AGAST #1850).
#
# Two QEMU NVMe controllers, in this PCI order:
#   harland-root  the initramfs (a TAR in a qcow2), block device 0;
#   harland-data  a 4 MiB raw disk whose sector N holds a known pattern,
#                 block device 1 (persistent storage).
#
# drivers/nvme resets each controller, sets up its admin queue, identifies
# it and its namespaces, creates one I/O queue pair and registers each
# namespace behind the block interface virtio-blk uses (drivers/virtio/blk),
# after the virtio disks. When a namespace comes up it reads 512-byte
# sectors 1-200 in one call (100 KiB: more than one command moves, so it
# splits, each part through a PRP list) and logs
#   [nvme] <serial> nsid <N>: <sectors> sectors, LBA 1-200 fnv1a=<decimal>, <B>-byte LBAs
#
# NVME_LBA_SIZE=4096 (AGAST #4088) gives both controllers 4 KiB logical
# blocks (QEMU logical_block_size=4096): the driver translates 512-byte
# sectors to native LBAs and read-modify-writes unaligned writes (persist
# writes single sectors). It must log "4096-byte LBAs", so this variant
# cannot pass on a QEMU that ignored the option. It also sets mdts=2 (16 KiB
# per command), so long transfers split at the controller's limit.
#
# Passes only if:
#   - harland-data reports 8192 sectors, the FNV-1a of LBAs 1-200 this
#     script wrote (read path: identify, LBA addressing, multi-page reads)
#     and NVME_LBA_SIZE as its LBA size;
#   - the initramfs loaded from harland-root and init's Tier-1 suite reports
#     ALL TESTS PASSED (the fs layer mounted from NVMe, unchanged);
#   - persistent storage came up on harland-data and its superblock magic
#     "\0HARBLOB" is in sector 0 of the image after the boot (write path);
#   - sectors 65-71 still hold the pattern: persist's format writes sectors
#     0-64 one at a time, and on 4 KiB LBAs sector 64 shares an LBA with
#     them, so a write that skipped read-modify-write would clobber them;
#   - the kernel took no exception;
#   - this ESP has no \harland\net-selftest boot option, so the kernel
#     skipped the pre-init network self-tests and never probed a NIC
#     (AGAST #4335: a broken driver on real hardware must not keep init
#     from starting).
#
# Usage: tools/test_nvme_boot.sh
#        SKIP_BUILD=1   use the existing build/debug outputs
#        BOOT_TIMEOUT=N seconds for the boot (default 120)
#        KEEP_WORK=DIR  copy the serial log (nvme.log) into DIR
#        OVMF_CODE=F    OVMF firmware to use (default: search the usual paths)
#        NVME_LBA_SIZE  512 (default) or 4096: the NVMe logical block size
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
DATA_SECTORS=8192
LBA_SIZE="${NVME_LBA_SIZE:-512}"
case "$LBA_SIZE" in
    512) NVME_OPTS=""; LOG_NAME=nvme.log ;;
    4096) NVME_OPTS=",logical_block_size=4096,physical_block_size=4096,mdts=2"; LOG_NAME=nvme-4k.log ;;
    *) echo "FAIL: NVME_LBA_SIZE must be 512 or 4096, not '$LBA_SIZE'"; exit 1 ;;
esac

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

# The data disk: sector N is "LBA" + N as u32 LE + "!", 64 times. Every
# sector differs, and so does every 8-byte slot from its neighbours' slots.
# Prints the FNV-1a (32-bit) of LBAs 1-200, the bytes the kernel hashes.
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

vars=()
if [ -n "$OVMF_VARS" ]; then
    cp "$OVMF_VARS" "$WORK/vars.fd"
    vars=(-drive "if=pflash,format=raw,file=$WORK/vars.fd")
fi
SERIAL="$WORK/$LOG_NAME"
: > "$SERIAL"
timeout "$TIMEOUT" qemu-system-x86_64 -cpu Haswell-v1 -smp 4 -m 2G \
    -display none -no-reboot -monitor none \
    -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
    -drive "format=raw,file=fat:rw:$WORK/esp" \
    -drive "file=$WORK/initramfs.qcow2,format=qcow2,if=none,id=root" \
    -device "nvme,serial=harland-root,drive=root$NVME_OPTS" \
    -drive "file=$WORK/data.img,format=raw,if=none,id=data" \
    -device "nvme,serial=harland-data,drive=data$NVME_OPTS" \
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

echo "----- nvme boot ($LBA_SIZE-byte LBAs): NVMe lines -----"
grep -aE "\[nvme\]|\[initramfs\] Loaded|Persistent storage" "$SERIAL" | head -20
echo "---------------------------------"

rc=0
if grep -aqE "EXCEPTION|KERNEL PANIC" "$SERIAL"; then
    sed -n '/EXCEPTION/,/CR2/p' "$SERIAL" | head -20
    echo "FAIL: kernel exception during boot"
    rc=1
fi
# This ESP has no \harland\net-selftest marker, so the kernel must skip the
# pre-init network self-tests and leave the NIC (and its driver probes:
# netdev_init tries virtio-net, then the ENA path that panicked on EC2
# Nitro) alone until init is up (AGAST #4335).
if grep -aqF "[net] Network self-tests skipped" "$SERIAL"; then
    echo "PASS: network self-tests skipped without the boot option"
else
    echo "FAIL: boot did not skip the network self-tests without the boot option"
    rc=1
fi
if grep -aqE "\[net\] Initializing network stack|\[ena\]|\[virtio-net\] Initializing" "$SERIAL"; then
    echo "FAIL: boot initialized the network without the boot option"
    rc=1
fi
want="[nvme] harland-data nsid 1: $DATA_SECTORS sectors, LBA 1-200 fnv1a=$want_fnv, $LBA_SIZE-byte LBAs"
got=$(grep -aoE "\[nvme\] harland-data nsid [0-9]+: [0-9]+ sectors, LBA 1-200 fnv1a=[0-9]+, [0-9]+-byte LBAs" "$SERIAL" | head -1)
if [ "$got" = "$want" ]; then
    echo "PASS: harland-data read back the pattern (fnv1a=$want_fnv, $LBA_SIZE-byte LBAs)"
else
    echo "FAIL: harland-data: want '$want', got '${got:-nothing}'"
    rc=1
fi
if grep -aqE "\[initramfs\] Loaded [1-9]" "$SERIAL"; then
    echo "PASS: initramfs loaded from harland-root"
else
    echo "FAIL: the initramfs did not load from harland-root"
    rc=1
fi
magic=$(python3 -c 'import sys; print(open(sys.argv[1], "rb").read(8).hex())' "$WORK/data.img" 2>/dev/null)
if grep -aq "\[OK\] Persistent storage" "$SERIAL" && [ "$magic" = "00484152424c4f42" ]; then
    echo "PASS: persistent storage formatted harland-data over NVMe writes"
else
    echo "FAIL: persistent storage did not come up on harland-data (sector 0 starts ${magic:-?})"
    rc=1
fi
# Sectors 65-71: unchanged pattern, or the sector numbers that differ.
bad=$(python3 - "$WORK/data.img" <<'EOF2'
import struct, sys
data = open(sys.argv[1], "rb").read()
print(" ".join(str(n) for n in range(65, 72)
               if data[n * 512:(n + 1) * 512] != (b"LBA" + struct.pack("<I", n) + b"!") * 64))
EOF2
) || bad="?"
if [ -z "$bad" ]; then
    echo "PASS: sectors 65-71 kept the pattern (writes beside them read-modify-wrote)"
else
    echo "FAIL: sectors beside persist's writes were clobbered: ${bad}"
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
