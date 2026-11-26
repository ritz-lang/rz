#!/bin/bash
# Boot Harland under OVMF with a virtio-net NIC and an NVMe controller and
# check that PCI devices interrupt the kernel through MSI-X (AGAST #1852,
# NVMe: #3630).
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
#   - virtio-net came up over the modern (MMIO) transport: the NIC is
#     modern-only (disable-legacy=on, AGAST #3576), so MSI-X and the DHCP
#     traffic go through the virtio 1.x common config and notify regions;
#   - its RX queue, offered at 1024 entries (rx_queue_size=1024), was capped
#     to the 256 the driver's rings hold ("Queue 0: size=256 (device max
#     1024)");
#   - frames really crossed the modern NIC: DHCP got a lease ("[dhcp]
#     Configured!"), which needs the virtio 1.x 12-byte net header both ways;
#   - the NIC kept sending past its 256-entry TX ring: after DHCP the kernel
#     pings the gateway 300 times in back-to-back groups of 4 and logs
#     "[net] TX burst: sent=S/300 replies=R". S must be 300 (a driver that
#     never reclaims used TX descriptors fails every send after 256) and
#     R > 256 (R counts distinct reply seqs; one that reuses a TX buffer the
#     device is still reading loses a group's earlier requests) (AGAST #4073);
#   - virtio-net came up in MSI-X mode ("[msix] virtio-net: MSI-X on");
#   - N > 0: interrupts were really delivered through the table, not polled;
#   - NVMe came up in MSI-X mode too ("[msix] nvme <serial>: MSI-X on"), its
#     admin and I/O completion queues on their own vectors (AGAST #3630);
#   - with interrupts on, it read the last 200 512-byte sectors of its disk,
#     which this script fills with a known pattern, and logged their FNV-1a
#     ("[msix] nvme <serial> nsid 1: LBA 32568-32767 fnv1a=H"), matching
#     the pattern's (100 KiB: two commands, one through a PRP list; the end
#     of the disk, as persistent storage formats its start during boot);
#   - "[msix] nvme interrupts: N, commands waited: W, completions without
#     one: M" has N > 0, W > 0 and M = 0: the driver waited for its MSI-X
#     vector on every command (W) and every one of them fired (M);
#   - "[msix] nvme idle wait halted: P" has 0 < P <= 64: with no command
#     outstanding, the kernel ran the commands' interrupt wait on the I/O
#     vector for one watchdog round (~0.27 s). The vector cannot fire, so a
#     wait that sleeps in hlt (cli/check/sti;hlt, so the wakeup cannot be
#     missed) halts at least once and wakes only for the few interrupts of
#     that window; one that spins on the vector's counter halts 0 times, or
#     a huge number if it still counts its rounds (AGAST #4212). The
#     commands' own "[msix] nvme waits halted: H" is only logged: QEMU often
#     raises the interrupt before the wait checks, so H = 0 is legal
#     (AGAST #4246);
#   - virtio-blk and virtio-input are modern-only too (disable-legacy=on;
#     QEMU's virtio-keyboard-pci always is), so their MSI-X goes through
#     common_cfg msix_config and queue_msix_vector (AGAST #3631): both log
#     "[msix] virtio-blk: MSI-X on" / "[msix] virtio-input: MSI-X on";
#   - "[msix] virtio-blk interrupts: N, requests waited: W, halted: H,
#     data: D" has N > 0, W > 0 and D = same: with interrupts on, disk reads
#     slept on the disk's vector and returned what polled reads did (H is
#     only logged: QEMU often completes a request before its wait checks);
#   - "[msix] virtio-net rx waits: W, halted: H" has W > 0 and H > 0: the
#     DHCP window slept on the NIC's RX vector between polls instead of
#     spinning a fixed delay (AGAST #3631);
#   - the kernel took no exception, and init's Tier-1 suite still reports
#     ALL TESTS PASSED with the NIC and NVMe attached.
#
# It boots twice, with the same devices and the same checks (AGAST #4723,
# docs/RING1_DRIVER.md "DMA domain", PR 5b):
#   - "pc": the pc machine, no IOMMU. PCI stays on port I/O ("[pci] no
#     MCFG: segment 0 only, port I/O"), and DMA is not translated;
#   - "vtd", the translating boot: q35 with kernel-irqchip=split and
#     -device intel-iommu,intremap=on,eim=on, the NIC with iommu_platform=on so
#     QEMU puts its DMA behind the IOMMU. The kernel turns interrupt
#     remapping on ("Interrupt remapping: VT-d on"), gives every requester
#     an identity context and sets TE ("[vtd] translation on"), and
#     virtio-net negotiates VIRTIO_F_ACCESS_PLATFORM, bit 33 ("[virtio-net]
#     VIRTIO_F_ACCESS_PLATFORM negotiated"). Every storage, NVMe and NIC
#     check above must still pass with translation on: the disks and the
#     NIC were bus-mastering through identity contexts, halted > 0 included.
#   - the NIC's private DMA domain (AGAST #4724), on the vtd run only: TE
#     comes on with the NIC's requester held out of the identity domain
#     ("1 requester(s) held"), the NIC gets its own domain before its bus
#     master ("[nic-dma] private domain D for SID ... bus master on"), a
#     TX buffer at an unmapped IOVA faults with the NIC's source ID ("fault
#     probe: the NIC's DMA to unmapped IOVA ... faulted with its source ID
#     SID", and the unit's record for it), a received frame lands in a
#     granted IOVA of domain D above every RAM address ("device DMA"), and
#     net_ring1_allowed holds ("ring-1 owner allowed"). Every NIC check
#     above then passed with the in-kernel driver on IOVAs. The pc run must
#     give the NIC no domain and refuse a ring-1 owner.
#
# The NIC uses QEMU's user-mode network (slirp): its built-in DHCP server
# answers inside QEMU, so this needs no root and no host network.
#
# The kernel's pre-init network self-tests are a boot option (AGAST #4335):
# this ESP carries the empty \harland\net-selftest marker, so the kernel
# runs DHCP, the gateway ping and the TX burst before init. Without it the
# kernel leaves the NIC alone until init is up, so a misbehaving driver
# cannot keep rzsh from starting (EC2 Nitro's ENA path did).
#
# Usage: tools/test_msix_boot.sh
#        SKIP_BUILD=1   use the existing build/debug outputs
#        BOOT_TIMEOUT=N seconds for the boot (default 120)
#        KEEP_WORK=DIR  copy the serial logs (msix.log, msix-vtd.log) into DIR
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
# This ESP asks for the kernel's pre-init network self-tests (AGAST #4335):
# the boot option is the presence of this marker on the boot volume. Every
# other boot script leaves it out, so a misbehaving NIC can't keep rzsh from
# starting there; here the NIC coverage below runs.
: > "$WORK/esp/harland/net-selftest"
# The NVMe disk (16 MiB, 32768 sectors): sector N holds the pattern
# test_nvme_boot.sh uses, ("LBA" + N as u32 LE + "!") * 64. Prints the
# FNV-1a (32-bit) of sectors 32568-32767, the bytes the kernel reads under
# MSI-X.
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

# boot NAME SERIAL: boot the machine; NAME "vtd" is q35 with intel-iommu
# and the NIC behind it, "pc" has no IOMMU.
boot() {
    local name="$1" serial="$2" machine=(-machine pc) iommu=() platform="" vars=()
    if [ "$name" = vtd ]; then
        # intremap=on wants the split irqchip; eim=on because the kernel
        # runs the LAPIC in x2APIC mode (32-bit IRTE destinations). The
        # IOMMU goes before the PCI devices it translates.
        machine=(-machine q35,kernel-irqchip=split)
        iommu=(-device intel-iommu,intremap=on,eim=on)
        platform=",iommu_platform=on"
    fi
    if [ -n "$OVMF_VARS" ]; then
        cp "$OVMF_VARS" "$WORK/vars-$name.fd"
        vars=(-drive "if=pflash,format=raw,file=$WORK/vars-$name.fd")
    fi
    : > "$serial"
    # romfile= drops the NIC's iPXE option ROM, so OVMF never tries a network
    # boot before the ESP. The legacy virtio-net path is covered by
    # tools/test_tier1_boot.sh's grub boot, whose NIC is QEMU's transitional
    # default.
    timeout "$TIMEOUT" qemu-system-x86_64 "${machine[@]}" -cpu Haswell-v1 -smp 4 -m 2G \
        "${iommu[@]}" \
        -display none -no-reboot -monitor none \
        -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
        -drive "format=raw,file=fat:rw:$WORK/esp" \
        -device virtio-blk-pci,drive=initramfs,disable-legacy=on \
        -device virtio-keyboard-pci \
        -drive "file=$WORK/initramfs.qcow2,format=qcow2,if=none,id=initramfs" \
        -device "virtio-net-pci,netdev=net0,romfile=,disable-legacy=on,rx_queue_size=1024$platform" \
        -netdev user,id=net0 \
        -device nvme,serial=harland-msix,drive=nvme0 \
        -drive "file=$WORK/nvme.img,format=raw,if=none,id=nvme0" \
        -serial "file:$serial" >/dev/null 2>&1 &
    local pid=$!
    timed_out=1
    for _ in $(seq 1 "$TIMEOUT"); do
        sleep 1
        grep -aqE "ALL TESTS PASSED|TESTS FAILED|KERNEL PANIC" "$serial" && { sleep 1; timed_out=0; break; }
        kill -0 "$pid" 2>/dev/null || { timed_out=0; break; }
    done
    kill "$pid" 2>/dev/null
    wait "$pid" 2>/dev/null
}

# nic_dma_checks SERIAL: the NIC's private DMA domain on the translating
# boot (AGAST #4724); sets rc=1 on any failure.
nic_dma_checks() {
    local SERIAL="$1" line sid dom hole dma iova ddom
    line=$(grep -aoE "\[nic-dma\] private domain [0-9]+ for [0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7] and [0-9]+ alias\(es\), never in the identity map; bus master on" "$SERIAL" | head -1)
    dom=$(echo "$line" | sed -nE 's/.*private domain ([0-9]+) for.*/\1/p')
    sid=$(echo "$line" | sed -nE 's/.* for ([0-9a-f:.]+) and .*/\1/p')
    if [ -z "$line" ]; then
        grep -a "\[nic-dma\]" "$SERIAL" | head -3
        echo "FAIL: the NIC got no private DMA domain before its bus master"
        rc=1
        return
    fi
    echo "PASS: the NIC ($sid) is in private DMA domain $dom, held out of the identity map, bus master set after"
    if grep -aqF "1 requester(s) held for a private domain" "$SERIAL"; then
        echo "PASS: TE came on with the NIC's requester held out of the identity domain"
    else
        echo "FAIL: the NIC's requester was not held out of the identity domain when TE came on"
        rc=1
    fi
    hole=$(grep -aoE "\[nic-dma\] fault probe: the NIC's DMA to unmapped IOVA 0x[0-9A-Fa-f]+ faulted with its source ID $sid" "$SERIAL" | head -1 | sed -nE 's/.*IOVA 0x([0-9A-Fa-f]+) faulted.*/\1/p')
    if [ -z "$hole" ]; then
        grep -a "\[nic-dma\] fault" "$SERIAL" | head -3
        echo "FAIL: no fault record with the NIC's source ID ($sid) for an unmapped IOVA"
        rc=1
    elif ! grep -aqE "\[nic-dma\] fault record: source $sid IOVA 0x$hole reason [0-9]+" "$SERIAL"; then
        echo "FAIL: the fault probe's record (IOVA 0x$hole) was not logged from the unit"
        rc=1
    else
        echo "PASS: the NIC's DMA to unmapped IOVA 0x$hole faulted with its source ID $sid"
    fi
    dma=$(grep -aoE "\[nic-dma\] device DMA: [0-9]+ bytes received into granted IOVA 0x[0-9A-Fa-f]+ -> physical 0x[0-9A-Fa-f]+ in domain [0-9]+" "$SERIAL" | head -1)
    iova=$(echo "$dma" | sed -nE 's/.*granted IOVA 0x([0-9A-Fa-f]+) .*/\1/p')
    ddom=$(echo "$dma" | sed -nE 's/.*in domain ([0-9]+)$/\1/p')
    if [ -z "$dma" ]; then
        grep -a "\[nic-dma\] device DMA" "$SERIAL" | head -3
        echo "FAIL: no device DMA into a granted page of the NIC's domain"
        rc=1
    elif [ "$ddom" != "$dom" ]; then
        echo "FAIL: the NIC's DMA went through domain $ddom, not its private domain $dom"
        rc=1
    elif [ $((16#$iova)) -lt $((16#1000000000)) ]; then
        echo "FAIL: the NIC was given IOVA 0x$iova, below the private IOVA base 0x1000000000 (a RAM address)"
        rc=1
    else
        echo "PASS: the NIC DMA'd a frame into granted IOVA 0x$iova (domain $dom), above every RAM address"
    fi
    if grep -aqF "[nic-dma] ring-1 owner allowed: translation on, remapping on, compatibility format blocked (read from the unit), NIC isolated" "$SERIAL"; then
        echo "PASS: net_ring1_allowed: translation, remapping and blocked compatibility format read from the unit"
    else
        grep -a "\[nic-dma\] ring-1" "$SERIAL" | head -3
        echo "FAIL: net_ring1_allowed is false on the translating boot"
        rc=1
    fi
}

# check NAME SERIAL: the verdicts for one boot; sets rc=1 on any failure.
check() {
    local name="$1" SERIAL="$2"
    echo "===== msix boot ($name) ====="
    echo "----- msix boot ($name): MSI-X and IOMMU lines -----"
    grep -aE "\[msix\]|Interrupt remapping|\[vtd\]|ACCESS_PLATFORM|\[nic-dma\]" "$SERIAL" | head -42
    echo "----------------------------------"

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
    if grep -aq "\[virtio-net\] Transport: modern (MMIO)" "$SERIAL"; then
        echo "PASS: virtio-net is driven over the modern (MMIO) transport"
    else
        grep -a "\[virtio-net\]" "$SERIAL" | head -5
        echo "FAIL: virtio-net was not driven over the modern (MMIO) transport"
        rc=1
    fi
    if grep -aqF "[virtio-net] Queue 0: size=256 (device max 1024)" "$SERIAL"; then
        echo "PASS: virtio-net's 1024-entry RX queue was capped to 256"
    else
        echo "FAIL: virtio-net's RX queue was not capped from 1024 to 256"
        rc=1
    fi
    if grep -aqF "[dhcp] Configured!" "$SERIAL"; then
        echo "PASS: DHCP got a lease over the modern virtio-net"
    else
        grep -a "\[dhcp\]\|DHCP" "$SERIAL" | head -5
        echo "FAIL: DHCP got no lease over the modern virtio-net"
        rc=1
    fi
    burst=$(grep -aoE "\[net\] TX burst: sent=[0-9]+/[0-9]+ replies=[0-9]+" "$SERIAL" | tail -1)
    b_sent=$(echo "$burst" | sed -nE 's/.*sent=([0-9]+)\/.*/\1/p')
    b_total=$(echo "$burst" | sed -nE 's/.*sent=[0-9]+\/([0-9]+) .*/\1/p')
    b_replies=$(echo "$burst" | sed -nE 's/.*replies=([0-9]+)$/\1/p')
    if [ -z "$burst" ]; then
        grep -a "\[net\] TX burst" "$SERIAL" | head -3
        echo "FAIL: no TX burst result ([net] TX burst: sent=S/N replies=R)"
        rc=1
    elif [ "$b_total" -le 256 ] || [ "$b_sent" -ne "$b_total" ]; then
        echo "FAIL: TX burst sent $b_sent of $b_total frames, want all of more than 256"
        rc=1
    elif [ "$b_replies" -le 256 ]; then
        echo "FAIL: TX burst got $b_replies distinct replies to $b_sent pings, want > 256"
        rc=1
    else
        echo "PASS: TX burst sent $b_sent/$b_total frames, $b_replies distinct replies"
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
    if grep -aqE "\[msix\] nvme [^ ]+: MSI-X on" "$SERIAL"; then
        echo "PASS: NVMe is in MSI-X mode"
    else
        grep -a "\[msix\] nvme\|\[nvme\]" "$SERIAL" | head -5
        echo "FAIL: NVMe did not come up in MSI-X mode"
        rc=1
    fi
    nread=$(grep -aoE "\[msix\] nvme [^ ]+ nsid 1: LBA 32568-32767 fnv1a=[0-9]+" "$SERIAL" | head -1 | sed -nE 's/.*fnv1a=([0-9]+)$/\1/p')
    if [ -z "$nread" ]; then
        grep -a "\[msix\] nvme .* nsid" "$SERIAL" | head -3
        echo "FAIL: no NVMe read under MSI-X ([msix] nvme <serial> nsid 1: LBA 32568-32767 fnv1a=H)"
        rc=1
    elif [ "$nread" != "$want_fnv" ]; then
        echo "FAIL: NVMe read under MSI-X returned fnv1a=$nread, want fnv1a=$want_fnv"
        rc=1
    else
        echo "PASS: NVMe read LBAs 32568-32767 under MSI-X (fnv1a=$want_fnv)"
    fi
    nirq=$(grep -aoE "\[msix\] nvme interrupts: [0-9]+, commands waited: [0-9]+, completions without one: [0-9]+" "$SERIAL" | tail -1)
    n_count=$(echo "$nirq" | sed -nE 's/.*interrupts: ([0-9]+),.*/\1/p')
    n_waited=$(echo "$nirq" | sed -nE 's/.*commands waited: ([0-9]+),.*/\1/p')
    n_missed=$(echo "$nirq" | sed -nE 's/.*without one: ([0-9]+)$/\1/p')
    if [ -z "$n_count" ] || [ "$n_count" -eq 0 ]; then
        echo "FAIL: NVMe MSI-X interrupt counter is ${n_count:-missing}, want > 0"
        rc=1
    elif [ "$n_waited" -eq 0 ]; then
        echo "FAIL: no NVMe command waited for its MSI-X interrupt (polled with $n_count delivered)"
        rc=1
    elif [ "$n_missed" -ne 0 ]; then
        echo "FAIL: $n_missed NVMe completions arrived without an interrupt ($n_count delivered)"
        rc=1
    else
        echo "PASS: NVMe delivered $n_count MSI-X interrupts, $n_waited commands waited for theirs, none missed"
    fi
    # An idle sleeping wait wakes only for the watchdog and the odd other
    # interrupt; a spinning one that counts its rounds runs thousands of them.
    IDLE_HALTS_MAX=64
    n_idle=$(grep -aoE "\[msix\] nvme idle wait halted: [0-9]+" "$SERIAL" | tail -1 | sed -nE 's/.*halted: ([0-9]+)$/\1/p')
    if [ -z "$n_idle" ]; then
        echo "FAIL: no NVMe idle interrupt wait logged ([msix] nvme idle wait halted: P)"
        rc=1
    elif [ "$n_idle" -eq 0 ]; then
        echo "FAIL: NVMe idle interrupt wait never halted: it spins instead of sleeping"
        rc=1
    elif [ "$n_idle" -gt "$IDLE_HALTS_MAX" ]; then
        echo "FAIL: NVMe idle interrupt wait halted $n_idle times (> $IDLE_HALTS_MAX): it spins instead of sleeping"
        rc=1
    else
        echo "PASS: NVMe idle interrupt wait slept: halted $n_idle times in one watchdog round"
    fi
    if grep -aqE "\[virtio-blk\] Device 0 initialized \([0-9]+ MB, modern" "$SERIAL"; then
        echo "PASS: virtio-blk is driven over the modern (MMIO) transport"
    else
        grep -a "\[virtio-blk\]" "$SERIAL" | head -5
        echo "FAIL: virtio-blk was not driven over the modern (MMIO) transport"
        rc=1
    fi
    if grep -aq "\[msix\] virtio-blk: MSI-X on" "$SERIAL"; then
        echo "PASS: virtio-blk is in MSI-X mode"
    else
        grep -a "\[msix\] virtio-blk" "$SERIAL" | head -3
        echo "FAIL: virtio-blk did not come up in MSI-X mode"
        rc=1
    fi
    birq=$(grep -aoE "\[msix\] virtio-blk interrupts: [0-9]+, requests waited: [0-9]+, halted: [0-9]+, data: [A-Za-z]+" "$SERIAL" | tail -1)
    bk_count=$(echo "$birq" | sed -nE 's/.*interrupts: ([0-9]+),.*/\1/p')
    bk_waited=$(echo "$birq" | sed -nE 's/.*requests waited: ([0-9]+),.*/\1/p')
    bk_data=$(echo "$birq" | sed -nE 's/.*data: ([A-Za-z]+)$/\1/p')
    if [ -z "$birq" ]; then
        echo "FAIL: no virtio-blk MSI-X read check logged ([msix] virtio-blk interrupts: N, requests waited: W, ...)"
        rc=1
    elif [ "$bk_count" -eq 0 ]; then
        echo "FAIL: virtio-blk MSI-X interrupt counter is 0, want > 0"
        rc=1
    elif [ "$bk_waited" -eq 0 ]; then
        echo "FAIL: no virtio-blk request waited for its MSI-X interrupt (polled with $bk_count delivered)"
        rc=1
    elif [ "$bk_data" != "same" ]; then
        echo "FAIL: virtio-blk reads under MSI-X returned data: $bk_data, want the polled reads' (same)"
        rc=1
    else
        echo "PASS: virtio-blk delivered $bk_count MSI-X interrupts, $bk_waited requests waited for theirs, same data as polled"
    fi
    if grep -aq "\[msix\] virtio-input: MSI-X on" "$SERIAL"; then
        echo "PASS: virtio-input is in MSI-X mode"
    else
        grep -a "\[msix\] virtio-input\|\[virtio-input\]" "$SERIAL" | head -3
        echo "FAIL: virtio-input did not come up in MSI-X mode"
        rc=1
    fi
    nrx=$(grep -aoE "\[msix\] virtio-net rx waits: [0-9]+, halted: [0-9]+" "$SERIAL" | tail -1)
    nrx_waits=$(echo "$nrx" | sed -nE 's/.*rx waits: ([0-9]+),.*/\1/p')
    nrx_halts=$(echo "$nrx" | sed -nE 's/.*halted: ([0-9]+)$/\1/p')
    if [ -z "$nrx" ]; then
        echo "FAIL: no virtio-net RX wait count logged ([msix] virtio-net rx waits: W, halted: H)"
        rc=1
    elif [ "$nrx_waits" -eq 0 ]; then
        echo "FAIL: the DHCP window never waited on the RX vector: it busy-polls"
        rc=1
    elif [ "$nrx_halts" -eq 0 ]; then
        echo "FAIL: virtio-net RX waits ($nrx_waits) never halted: they spin instead of sleeping"
        rc=1
    else
        echo "PASS: virtio-net RX waited on its vector $nrx_waits times, halted $nrx_halts"
    fi
    if [ "$name" = pc ]; then
        # QEMU's pc machine has no MCFG: PCI stays on port I/O, segment 0 only
        # (AGAST #4582; tools/test_irq_dest_boot.sh boots q35 through ECAM).
        if grep -aqF "[pci] no MCFG: segment 0 only, port I/O" "$SERIAL"; then
            echo "PASS: no MCFG on pc: PCI config access stays on port I/O"
        else
            grep -a "\[pci\]" "$SERIAL" | head -5
            echo "FAIL: no \"[pci] no MCFG: segment 0 only, port I/O\" on the pc machine"
            rc=1
        fi
        # No IOMMU on pc: nothing may claim DMA is translated
        if grep -aqF "[vtd] translation on" "$SERIAL"; then
            echo "FAIL: \"[vtd] translation on\" on the pc machine, which has no IOMMU"
            rc=1
        fi
        # ... nor give the NIC a domain, nor allow a ring-1 owner (AGAST #4724)
        if grep -aqF "[nic-dma] private domain" "$SERIAL"; then
            echo "FAIL: a private NIC DMA domain on the pc machine, which has no IOMMU"
            rc=1
        elif grep -aqF "[nic-dma] ring-1 owner refused" "$SERIAL"; then
            echo "PASS: no IOMMU: the NIC stays on physical addresses and a ring-1 owner is refused"
        else
            grep -a "\[nic-dma\]" "$SERIAL" | head -3
            echo "FAIL: no \"[nic-dma] ring-1 owner refused\" on the pc machine"
            rc=1
        fi
    else
        # The translating boot (AGAST #4723): interrupt remapping, then TE
        # with an identity context for every requester, and the NIC's DMA
        # through it
        if grep -aq "Interrupt remapping: VT-d on" "$SERIAL"; then
            echo "PASS: VT-d interrupt remapping is on"
        else
            grep -a "Interrupt remapping\|DMAR" "$SERIAL" | head -3
            echo "FAIL: VT-d interrupt remapping did not come on"
            rc=1
        fi
        if grep -aqF "[vtd] translation on" "$SERIAL"; then
            echo "PASS: VT-d DMA translation is on: identity contexts, TE set"
        else
            grep -a "\[vtd\]" "$SERIAL" | head -3
            echo "FAIL: no \"[vtd] translation on\": DMA was not translated"
            rc=1
        fi
        if grep -aqF "[virtio-net] VIRTIO_F_ACCESS_PLATFORM negotiated" "$SERIAL"; then
            echo "PASS: virtio-net negotiated VIRTIO_F_ACCESS_PLATFORM: its DMA goes through the IOMMU"
        else
            echo "FAIL: virtio-net did not negotiate VIRTIO_F_ACCESS_PLATFORM (bit 33) on the translating boot"
            rc=1
        fi
        nic_dma_checks "$SERIAL"
    fi
    if grep -aq "ALL TESTS PASSED" "$SERIAL"; then
        echo "PASS: init Tier-1 suite: ALL TESTS PASSED"
    else
        [ "$timed_out" = 1 ] && echo "FAIL: no verdict within ${TIMEOUT}s (BOOT_TIMEOUT)"
        echo "FAIL: init's Tier-1 suite did not report ALL TESTS PASSED"
        rc=1
    fi
}

rc=0
boot pc "$WORK/msix.log"
check pc "$WORK/msix.log"
boot vtd "$WORK/msix-vtd.log"
check vtd "$WORK/msix-vtd.log"
exit $rc
