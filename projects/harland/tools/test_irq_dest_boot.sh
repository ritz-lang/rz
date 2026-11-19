#!/bin/bash
# Boot Harland under OVMF on a machine with a CPU whose APIC ID is 256 and
# check where device interrupts go (AGAST #4233), without and with VT-d
# interrupt remapping (#4316).
#
# An MSI address and an I/O APIC redirection entry carry an 8-bit APIC ID
# (0xFF is broadcast). msix_set_entry used to write `lapic_id() & 0xFF`,
# so an entry set up on APIC ID 256 went to APIC ID 0, 257 to 1, and so
# on; ioapic_init sent the keyboard (IRQ 1) and COM1 (IRQ 4) to the literal
# APIC ID 0 rather than the BSP's. Now arch/x86_64/irq_dest.ritz picks a CPU
# an interrupt message can reach: the CPU itself if its ID is below 255 (or
# up to 0x7FFF with KVM's extended destination ID), else the BSP, else the
# first CPU that can be reached, and the kernel logs every CPU it reroutes.
#
# The machine: q35, -smp 1,sockets=2,cores=200,maxcpus=400 and one more CPU
# cold-plugged at socket 1, core 0: the BSP is APIC ID 0 and the AP APIC ID
# 256, which only x2APIC reaches (#4184). TCG advertises no extended
# destination ID, so APIC ID 256's device interrupts must go to the BSP.
# QEMU always gives CPU 0 APIC ID 0, so a BSP that isn't APIC ID 0 can't be
# booted; projects/ritz/ritz0/test_harland_irq_dest.py covers that in
# irq_dest's logic and pins ioapic_init to the BSP's ID.
#
# The second boot ("vtd") adds -device intel-iommu,intremap=on,eim=on:
# QEMU's DMAR table lists a remapping unit, the kernel turns interrupt
# remapping on in extended interrupt mode (drivers/iommu/vtd.ritz), and
# MSI-X entries and redirection entries carry IRT handles whose entries hold
# 32-bit destinations, so APIC ID 256 is no longer rerouted. Under KVM the
# IOMMU needs kernel-irqchip=split (ACCEL=kvm); TCG takes it as is.
# QEMU validates each IRTE's source ID (a wrong requester ID loses the NVMe
# interrupts), but passes compatibility-format MSIs through whatever CFI
# says, so "nothing bypasses the table" is pinned at source level only
# (projects/ritz/ritz0/test_harland_vtd.py).
#
# Each boot passes only if:
#   - the LAPIC runs in x2APIC mode and the AP started ("(1 APs started)");
#   - the I/O APIC's IRQ 1 and IRQ 4 read back as the BSP's APIC ID
#     ("I/O APIC: IRQ 1 -> APIC ID B, IRQ 4 -> APIC ID B", B from "BSP APIC
#     ID: B");
#   - with 8-bit destinations, APIC ID 256 is logged as rerouted to the BSP,
#     with the BSP's MSI address and the reason ("[irq] APIC ID 256: device
#     interrupts -> APIC ID B (MSI addr FEE0B000): beyond the 8-bit ...");
#     with the extended destination ID, it is not rerouted at all;
#   - vtd boot: "Interrupt remapping: VT-d on ... (EIM)", destinations
#     "interrupt remapping (32-bit APIC IDs)", APIC ID 256 not rerouted, the
#     I/O APIC's IRQ 1 and 4 remapped (IRTE 1, 4) to the BSP, and the NVMe
#     vectors set through IRTEs aimed at the BSP;
#   - an NVMe controller still comes up on MSI-X and its interrupts arrive
#     ("[msix] nvme interrupts: N, ... completions without one: 0", N > 0);
#   - the kernel took no exception and init's Tier-1 suite reports ALL
#     TESTS PASSED.
#
# Usage: tools/test_irq_dest_boot.sh
#        IRQ_DEST_BOOTS="plain vtd"  which boots to run (default both)
#        ACCEL=kvm      boot under KVM (default TCG)
#        SKIP_BUILD=1   use the existing build/debug outputs
#        BOOT_TIMEOUT=N seconds for the boot (default 240)
#        KEEP_WORK=DIR  copy the serial logs (irq-dest.log, irq-dest-vtd.log) into DIR
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
TIMEOUT="${BOOT_TIMEOUT:-240}"
# Same packages as test_tier1_boot.sh: init's suite spawns all of them.
USER_PKGS="indium rzsh prism"
# The CPU the AP gets: APIC ID = socket 1 << 8 (core IDs take 8 bits).
AP_APIC_ID=256
BOOTS="${IRQ_DEST_BOOTS:-plain vtd}"

EXIT_SETUP=3
setup_error() { echo "SETUP ERROR: $*" >&2; exit "$EXIT_SETUP"; }
for b in $BOOTS; do
    case "$b" in plain|vtd) ;; *) setup_error "unknown boot in IRQ_DEST_BOOTS: $b";; esac
done

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
# A blank 16 MiB NVMe disk: the driver's MSI-X reads only need sectors.
python3 -c 'import sys; open(sys.argv[1], "wb").truncate(16 << 20)' "$WORK/nvme.img" \
    || { echo "FAIL: could not write the NVMe disk"; exit 1; }

# boot NAME SERIAL: boot the machine, NAME "vtd" with the IOMMU.
boot() {
    local name="$1" serial="$2" machine="q35" accel=() iommu=() vars=()
    if [ "${ACCEL:-}" = kvm ]; then
        accel=(-accel kvm)
        [ "$name" = vtd ] && machine="q35,kernel-irqchip=split"
    fi
    # The IOMMU first: it must exist before the PCI devices it remaps.
    [ "$name" = vtd ] && iommu=(-device intel-iommu,intremap=on,eim=on)
    if [ -n "$OVMF_VARS" ]; then
        cp "$OVMF_VARS" "$WORK/vars-$name.fd"
        vars=(-drive "if=pflash,format=raw,file=$WORK/vars-$name.fd")
    fi
    : > "$serial"
    timeout "$TIMEOUT" qemu-system-x86_64 -machine "$machine" "${accel[@]}" -cpu Haswell-v1,+x2apic \
        -smp 1,sockets=2,cores=200,maxcpus=400 \
        -device Haswell-v1-x86_64-cpu,socket-id=1,core-id=0,thread-id=0 \
        "${iommu[@]}" \
        -m 2G -display none -no-reboot -monitor none \
        -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
        -drive "format=raw,file=fat:rw:$WORK/esp" \
        -device virtio-blk-pci,drive=initramfs \
        -drive "file=$WORK/initramfs.qcow2,format=qcow2,if=none,id=initramfs" \
        -device nvme,serial=harland-irq,drive=nvme0 \
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

# check NAME SERIAL: the verdicts for one boot; sets rc=1 on any failure.
check() {
    local name="$1" SERIAL="$2"
    echo "----- irq-dest boot ($name): APIC and interrupt routing lines -----"
    grep -aE "LAPIC mode|Device interrupt destinations|Interrupt remapping|DMAR at|\[vtd\]|I/O APIC:|BSP APIC ID|APs started|\[irq\]|\[msix\] (nvme|vector|no CPU)" "$SERIAL" | head -24
    echo "-----------------------------------------------------------"
    local P="[$name]"

    if grep -aqE "EXCEPTION|KERNEL PANIC" "$SERIAL"; then
        sed -n '/EXCEPTION/,/CR2/p' "$SERIAL" | head -20
        echo "FAIL: $P kernel exception during boot"
        rc=1
    fi
    if grep -aqF "LAPIC mode: x2APIC" "$SERIAL"; then
        echo "PASS: $P LAPIC in x2APIC mode"
    else
        echo "FAIL: $P LAPIC not in x2APIC mode (APIC ID $AP_APIC_ID needs it)"
        rc=1
    fi
    if grep -aqF "(1 APs started)" "$SERIAL"; then
        echo "PASS: $P the AP (APIC ID $AP_APIC_ID) started"
    else
        grep -aE "Boot APs|TIMEOUT|skipped" "$SERIAL" | head -5
        echo "FAIL: $P the AP with APIC ID $AP_APIC_ID did not start: no \"(1 APs started)\""
        rc=1
    fi
    local bsp route irq1 irq4 want want_addr nirq n_count n_missed
    bsp=$(grep -aoE "BSP APIC ID: [0-9]+" "$SERIAL" | head -1 | grep -oE "[0-9]+$")
    route=$(grep -aoE "I/O APIC: IRQ 1 -> APIC ID [0-9]+, IRQ 4 -> APIC ID [0-9]+" "$SERIAL" | head -1)
    irq1=$(echo "$route" | sed -nE 's/.*IRQ 1 -> APIC ID ([0-9]+),.*/\1/p')
    irq4=$(echo "$route" | sed -nE 's/.*IRQ 4 -> APIC ID ([0-9]+)$/\1/p')
    if [ -z "$bsp" ]; then
        echo "FAIL: $P no \"BSP APIC ID: N\" in the log"
        rc=1
    elif [ -z "$route" ]; then
        echo "FAIL: $P no I/O APIC routing read back (I/O APIC: IRQ 1 -> APIC ID N, IRQ 4 -> APIC ID N)"
        rc=1
    elif [ "$irq1" != "$bsp" ] || [ "$irq4" != "$bsp" ]; then
        echo "FAIL: $P I/O APIC sends IRQ 1 to APIC ID $irq1 and IRQ 4 to $irq4, not to the BSP ($bsp)"
        rc=1
    else
        echo "PASS: $P I/O APIC sends IRQ 1 and IRQ 4 to the BSP (APIC ID $bsp)"
    fi
    if [ "$name" = vtd ]; then
        if grep -aqE "Interrupt remapping: VT-d on, [0-9]+ unit\(s\), table at [0-9A-Fa-fx]+, 32-bit x2APIC destinations \(EIM\)" "$SERIAL"; then
            echo "PASS: $P VT-d interrupt remapping on with 32-bit destinations (EIM)"
        else
            grep -aE "Interrupt remapping|DMAR|\[vtd\]" "$SERIAL" | head -5
            echo "FAIL: $P interrupt remapping is not on in extended interrupt mode"
            rc=1
        fi
        if ! grep -aqF "Device interrupt destinations: interrupt remapping (32-bit APIC IDs)" "$SERIAL"; then
            echo "FAIL: $P device interrupt destinations are not 32-bit through remapping"
            rc=1
        elif grep -aqF "[irq] APIC ID $AP_APIC_ID:" "$SERIAL"; then
            echo "FAIL: $P APIC ID $AP_APIC_ID was rerouted though interrupt remapping reaches it"
            rc=1
        else
            echo "PASS: $P APIC ID $AP_APIC_ID takes its own device interrupts (interrupt remapping)"
        fi
        if [ -n "$route" ] && grep -aqF "$route (remapped: IRTE 1, 4)" "$SERIAL"; then
            echo "PASS: $P I/O APIC IRQ 1 and IRQ 4 go through IRTEs 1 and 4"
        else
            echo "FAIL: $P I/O APIC IRQ 1 and IRQ 4 are not in the remappable format (no \"(remapped: IRTE 1, 4)\")"
            rc=1
        fi
        # "MSI-X on, vectors admin=A io=I (IRTE a, i -> APIC ID d, d)":
        # the table entries read back as remappable, IRTEs 128 + vector,
        # each aimed at the BSP.
        local m want_irte
        m=$(grep -aoE "\[msix\] nvme [^ ]+: MSI-X on, vectors admin=[0-9]+ io=[0-9]+ \(IRTE [0-9]+, [0-9]+ -> APIC ID [0-9]+, [0-9]+\)" "$SERIAL" | head -1)
        local va vi
        va=$(echo "$m" | sed -nE 's/.*admin=([0-9]+) io=.*/\1/p')
        vi=$(echo "$m" | sed -nE 's/.* io=([0-9]+) .*/\1/p')
        want_irte="(IRTE $((128 + (${va:-0} & 127))), $((128 + (${vi:-0} & 127))) -> APIC ID $bsp, $bsp)"
        if [ -z "$m" ]; then
            echo "FAIL: $P NVMe MSI-X entries are not in the remappable format (no \"(IRTE a, i -> APIC ID ...)\")"
            rc=1
        elif [ "${m##*vectors admin=$va io=$vi }" != "$want_irte" ]; then
            echo "FAIL: $P NVMe MSI-X entries: \"${m##*io=$vi }\", want \"$want_irte\""
            rc=1
        else
            echo "PASS: $P NVMe MSI-X vectors $va and $vi go through IRTEs to the BSP $want_irte"
        fi
    elif grep -aqF "Device interrupt destinations: extended destination ID" "$SERIAL"; then
        if grep -aqF "[irq] APIC ID $AP_APIC_ID:" "$SERIAL"; then
            echo "FAIL: $P APIC ID $AP_APIC_ID was rerouted though the extended destination ID reaches it"
            rc=1
        else
            echo "PASS: $P APIC ID $AP_APIC_ID takes its own device interrupts (extended destination ID)"
        fi
    elif [ -n "$bsp" ]; then
        want_addr=$(printf '%X' $((0xFEE00000 | ((bsp & 0xFF) << 12))))
        want="[irq] APIC ID $AP_APIC_ID: device interrupts -> APIC ID $bsp (MSI addr $want_addr): beyond the 8-bit"
        if grep -aqF "$want" "$SERIAL"; then
            echo "PASS: $P APIC ID $AP_APIC_ID's device interrupts go to the BSP (APIC ID $bsp, MSI addr $want_addr)"
        else
            grep -a "\[irq\]" "$SERIAL" | head -5
            echo "FAIL: $P no \"$want ...\" in the log"
            rc=1
        fi
    fi
    nirq=$(grep -aoE "\[msix\] nvme interrupts: [0-9]+, commands waited: [0-9]+, completions without one: [0-9]+" "$SERIAL" | tail -1)
    n_count=$(echo "$nirq" | sed -nE 's/.*interrupts: ([0-9]+),.*/\1/p')
    n_missed=$(echo "$nirq" | sed -nE 's/.*without one: ([0-9]+)$/\1/p')
    if ! grep -aqE "\[msix\] nvme [^ ]+: MSI-X on" "$SERIAL"; then
        echo "FAIL: $P NVMe did not come up in MSI-X mode"
        rc=1
    elif [ -z "$n_count" ] || [ "$n_count" -eq 0 ]; then
        echo "FAIL: $P NVMe MSI-X interrupt counter is ${n_count:-missing}, want > 0"
        rc=1
    elif [ "$n_missed" -ne 0 ]; then
        echo "FAIL: $P $n_missed NVMe completions arrived without an interrupt ($n_count delivered)"
        rc=1
    else
        echo "PASS: $P NVMe delivered $n_count MSI-X interrupts, none missed"
    fi
    if grep -aq "ALL TESTS PASSED" "$SERIAL"; then
        echo "PASS: $P init Tier-1 suite: ALL TESTS PASSED"
    else
        [ "$timed_out" = 1 ] && echo "FAIL: $P no verdict within ${TIMEOUT}s (BOOT_TIMEOUT)"
        echo "FAIL: $P init's Tier-1 suite did not report ALL TESTS PASSED"
        rc=1
    fi
}

rc=0
for b in $BOOTS; do
    log="$WORK/irq-dest.log"
    [ "$b" = vtd ] && log="$WORK/irq-dest-vtd.log"
    boot "$b" "$log"
    check "$b" "$log"
done
exit $rc
