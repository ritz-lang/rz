#!/bin/bash
# Boot Harland under OVMF on a machine with a CPU whose APIC ID is 256 and
# check where device interrupts go (AGAST #4233).
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
# Passes only if:
#   - the LAPIC runs in x2APIC mode and the AP started ("(1 APs started)");
#   - the I/O APIC's IRQ 1 and IRQ 4 read back as the BSP's APIC ID
#     ("I/O APIC: IRQ 1 -> APIC ID B, IRQ 4 -> APIC ID B", B from "BSP APIC
#     ID: B");
#   - with 8-bit destinations, APIC ID 256 is logged as rerouted to the BSP,
#     with the BSP's MSI address and the reason ("[irq] APIC ID 256: device
#     interrupts -> APIC ID B (MSI addr FEE0B000): beyond the 8-bit ...");
#     with the extended destination ID, it is not rerouted at all;
#   - an NVMe controller still comes up on MSI-X and its interrupts arrive
#     ("[msix] nvme interrupts: N, ... completions without one: 0", N > 0);
#   - the kernel took no exception and init's Tier-1 suite reports ALL
#     TESTS PASSED.
#
# Usage: tools/test_irq_dest_boot.sh
#        SKIP_BUILD=1   use the existing build/debug outputs
#        BOOT_TIMEOUT=N seconds for the boot (default 240)
#        KEEP_WORK=DIR  copy the serial log (irq-dest.log) into DIR
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

vars=()
if [ -n "$OVMF_VARS" ]; then
    cp "$OVMF_VARS" "$WORK/vars.fd"
    vars=(-drive "if=pflash,format=raw,file=$WORK/vars.fd")
fi
SERIAL="$WORK/irq-dest.log"
: > "$SERIAL"
timeout "$TIMEOUT" qemu-system-x86_64 -machine q35 -cpu Haswell-v1,+x2apic \
    -smp 1,sockets=2,cores=200,maxcpus=400 \
    -device Haswell-v1-x86_64-cpu,socket-id=1,core-id=0,thread-id=0 \
    -m 2G -display none -no-reboot -monitor none \
    -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
    -drive "format=raw,file=fat:rw:$WORK/esp" \
    -device virtio-blk-pci,drive=initramfs \
    -drive "file=$WORK/initramfs.qcow2,format=qcow2,if=none,id=initramfs" \
    -device nvme,serial=harland-irq,drive=nvme0 \
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

echo "----- irq-dest boot: APIC and interrupt routing lines -----"
grep -aE "LAPIC mode|Device interrupt destinations|I/O APIC:|BSP APIC ID|APs started|\[irq\]|\[msix\] (nvme|vector|no CPU)" "$SERIAL" | head -20
echo "-----------------------------------------------------------"

rc=0
if grep -aqE "EXCEPTION|KERNEL PANIC" "$SERIAL"; then
    sed -n '/EXCEPTION/,/CR2/p' "$SERIAL" | head -20
    echo "FAIL: kernel exception during boot"
    rc=1
fi
if grep -aqF "LAPIC mode: x2APIC" "$SERIAL"; then
    echo "PASS: LAPIC in x2APIC mode"
else
    echo "FAIL: LAPIC not in x2APIC mode (APIC ID $AP_APIC_ID needs it)"
    rc=1
fi
if grep -aqF "(1 APs started)" "$SERIAL"; then
    echo "PASS: the AP (APIC ID $AP_APIC_ID) started"
else
    grep -aE "Boot APs|TIMEOUT|skipped" "$SERIAL" | head -5
    echo "FAIL: the AP with APIC ID $AP_APIC_ID did not start: no \"(1 APs started)\""
    rc=1
fi
bsp=$(grep -aoE "BSP APIC ID: [0-9]+" "$SERIAL" | head -1 | grep -oE "[0-9]+$")
route=$(grep -aoE "I/O APIC: IRQ 1 -> APIC ID [0-9]+, IRQ 4 -> APIC ID [0-9]+" "$SERIAL" | head -1)
irq1=$(echo "$route" | sed -nE 's/.*IRQ 1 -> APIC ID ([0-9]+),.*/\1/p')
irq4=$(echo "$route" | sed -nE 's/.*IRQ 4 -> APIC ID ([0-9]+)$/\1/p')
if [ -z "$bsp" ]; then
    echo "FAIL: no \"BSP APIC ID: N\" in the log"
    rc=1
elif [ -z "$route" ]; then
    echo "FAIL: no I/O APIC routing read back (I/O APIC: IRQ 1 -> APIC ID N, IRQ 4 -> APIC ID N)"
    rc=1
elif [ "$irq1" != "$bsp" ] || [ "$irq4" != "$bsp" ]; then
    echo "FAIL: I/O APIC sends IRQ 1 to APIC ID $irq1 and IRQ 4 to $irq4, not to the BSP ($bsp)"
    rc=1
else
    echo "PASS: I/O APIC sends IRQ 1 and IRQ 4 to the BSP (APIC ID $bsp)"
fi
if grep -aqF "Device interrupt destinations: extended destination ID" "$SERIAL"; then
    if grep -aqF "[irq] APIC ID $AP_APIC_ID:" "$SERIAL"; then
        echo "FAIL: APIC ID $AP_APIC_ID was rerouted though the extended destination ID reaches it"
        rc=1
    else
        echo "PASS: APIC ID $AP_APIC_ID takes its own device interrupts (extended destination ID)"
    fi
elif [ -n "$bsp" ]; then
    want_addr=$(printf '%X' $((0xFEE00000 | ((bsp & 0xFF) << 12))))
    want="[irq] APIC ID $AP_APIC_ID: device interrupts -> APIC ID $bsp (MSI addr $want_addr): beyond the 8-bit"
    if grep -aqF "$want" "$SERIAL"; then
        echo "PASS: APIC ID $AP_APIC_ID's device interrupts go to the BSP (APIC ID $bsp, MSI addr $want_addr)"
    else
        grep -a "\[irq\]" "$SERIAL" | head -5
        echo "FAIL: no \"$want ...\" in the log"
        rc=1
    fi
fi
nirq=$(grep -aoE "\[msix\] nvme interrupts: [0-9]+, commands waited: [0-9]+, completions without one: [0-9]+" "$SERIAL" | tail -1)
n_count=$(echo "$nirq" | sed -nE 's/.*interrupts: ([0-9]+),.*/\1/p')
n_missed=$(echo "$nirq" | sed -nE 's/.*without one: ([0-9]+)$/\1/p')
if ! grep -aqE "\[msix\] nvme [^ ]+: MSI-X on" "$SERIAL"; then
    echo "FAIL: NVMe did not come up in MSI-X mode"
    rc=1
elif [ -z "$n_count" ] || [ "$n_count" -eq 0 ]; then
    echo "FAIL: NVMe MSI-X interrupt counter is ${n_count:-missing}, want > 0"
    rc=1
elif [ "$n_missed" -ne 0 ]; then
    echo "FAIL: $n_missed NVMe completions arrived without an interrupt ($n_count delivered)"
    rc=1
else
    echo "PASS: NVMe delivered $n_count MSI-X interrupts, none missed"
fi
if grep -aq "ALL TESTS PASSED" "$SERIAL"; then
    echo "PASS: init Tier-1 suite: ALL TESTS PASSED"
else
    [ "$timed_out" = 1 ] && echo "FAIL: no verdict within ${TIMEOUT}s (BOOT_TIMEOUT)"
    echo "FAIL: init's Tier-1 suite did not report ALL TESTS PASSED"
    rc=1
fi
exit $rc
