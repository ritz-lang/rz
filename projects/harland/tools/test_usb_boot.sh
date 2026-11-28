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
# configuration descriptors, SET_CONFIGURATION. With no boot option a
# controller with MSI-X never polls (#4891's fallback is for one with no
# working vector), so every step proves an MSI-X interrupt reached the BSP.
#
# Two controllers (AGAST #4889, docs/USB.md "Hot-plug"). The first, hc0,
# has two keyboards: usb-kbd at its default high speed, and one with
# usb_version=1 at full speed (EP0's size read from the device descriptor's
# first 8 bytes before the rest). The second, hc1, has one keyboard, and the
# boot option \harland\fault-usb forces one controller error on it once
# that keyboard is ready. Passes only if:
#   - both controllers are found, each running on its own MSI-X vector
#     aimed at the BSP;
#   - two of hc0's root ports report a keyboard connected (once each) and
#     enabled, one at high speed and one at full speed;
#   - hc0's slots 1 and 2 are addressed, their device descriptors read
#     (0627:0001);
#   - each configuration is read (interface 0 HID boot keyboard, endpoint
#     0x81 interrupt IN) and SET_CONFIGURATION completes;
#   - hc1 sees the error, resets alone and re-enumerates: its keyboard is
#     ready twice, before the error and after the reset;
#   - hc0 is never reset, and each of its keyboards is ready exactly once;
#   - no enumeration step failed;
#   - init's Tier-1 suite reports ALL TESTS PASSED;
#   - the kernel took no exception and did not panic.
#
# keyboard (AGAST #4888, docs/USB.md "Data path"): one usb-kbd on q35 with
# the PS/2 controller off and `-serial none`, so the USB keyboard is the
# only way in and the framebuffer the only way out. There are two
# controllers and the keyboard is on the second (AGAST #4889: chungus's
# keyboard can be on any of its three). init_interactive runs rzsh;
# tools/fbcon_screen.py reads the screen over QMP and types with send-key
# once each step's text is on screen. Passes only if:
#   - the keyboard is driven on the second controller (SET_PROTOCOL,
#     SET_IDLE, Configure Endpoint): "hc1 slot 1: keyboard ready" in the
#     boot log on screen;
#   - `echo hi` + Enter at rzsh's prompt shows `hi` under it;
#   - Ctrl-C kills `spin` (ring 3, no syscalls: the kill is the xHCI
#     interrupt's) and `echo $?` then shows 130;
#   - Caps Lock (with its LED report) types `echo ABc` as typed;
#   - a key held 1.2 s repeats (the BSP tick's typematic repeat);
#   - hot-plug (AGAST #4889): after QMP device_del of the keyboard its keys
#     are released and its port is detached (endpoints stopped, Disable
#     Slot completed), and after device_add it is ready again and
#     `echo back` types;
#   - no panic or exception on screen.
#
# keyboard-msi and keyboard-poll (AGAST #4891, docs/USB.md "Polling
# fallback"): the keyboard boot with the boot option \harland\usb-no-msix
# (each controller on plain MSI, as the X99's MSI-only Intel xHCI) or
# \harland\usb-poll (no vector: the BSP's tick polls each controller).
# QEMU's qemu-xhci offers plain MSI only with msi=on, which the MSI boot
# sets on both controllers. Passes only if hc1's keyboard is ready on that source (its ready line
# names it: "MSI" or "polled"; the keyboard boot's says "MSI-X"), no
# controller is seen running any other way, `echo hi` types, and Ctrl-C
# kills `spin` ($? = 130: on the poll, the kill is the tick's).
#
# Usage: tools/test_usb_boot.sh [enumerate|keyboard|keyboard-msi|keyboard-poll]
#                                                       (default enumerate)
#        SKIP_BUILD=1   use the existing build/debug outputs
#        BOOT_TIMEOUT=N seconds for the boot (default 120)
#        KEEP_WORK=DIR  copy the serial log (usb.log), or the keyboard boot's
#                       screens (usb-kbd-screens.txt), into DIR
#        OVMF_CODE=F    OVMF firmware to use (default: search the usual paths)
#
# Exit: 0 = pass; 1 = the boot or a check failed; 3 = a required tool is
#       missing: a SETUP ERROR (rz's and ci_local.py's EXIT_SETUP), not a
#       regression.

set -u

MODE="${1:-enumerate}"
case "$MODE" in
    enumerate|keyboard|keyboard-msi|keyboard-poll) ;;
    *) echo "usage: $0 [enumerate|keyboard|keyboard-msi|keyboard-poll]" >&2; exit 2 ;;
esac
# Every keyboard boot types into rzsh on the screen; keyboard-msi and
# keyboard-poll differ only in the boot option and what they type.
KBD=0
case "$MODE" in keyboard*) KBD=1 ;; esac

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
# indium/tools/stage_initramfs.sh is initramfs.pkgs' one reader: it builds
# each package with the compiler its entry names and stages the ELFs
# (AGAST #2759, #4834).
STAGE="$PROJECTS_DIR/indium/tools/stage_initramfs.sh"

if [ "${SKIP_BUILD:-0}" != "1" ]; then
    for pkg in harland; do
        (cd "$ROOT_DIR" && ./rz build "$pkg")
        brc=$?
        [ "$brc" -eq "$EXIT_SETUP" ] && setup_error "build of $pkg: a toolchain binary is missing"
        [ "$brc" -eq 0 ] || { echo "FAIL: build of $pkg failed"; exit 1; }
    done
    bash "$STAGE" --build-only
    brc=$?
    [ "$brc" -eq 3 ] && { echo "SETUP ERROR: building the initramfs packages: a toolchain binary or docker is missing" >&2; exit 3; }
    [ "$brc" -eq 0 ] || { echo "FAIL: building the initramfs packages failed"; exit 1; }
fi

KERNEL_ELF="$HARLAND_DIR/build/debug/harland.elf"
LOADER_EFI="$HARLAND_DIR/build/debug/BOOTX64.EFI"
INIT=init
[ "$KBD" = 1 ] && INIT=init_interactive
need_built=("$KERNEL_ELF" "$LOADER_EFI" "$PROJECTS_DIR/indium/build/debug/$INIT.elf")
[ "$KBD" = 1 ] && need_built+=("$PROJECTS_DIR/rzsh/build/debug/rzsh.elf")
for f in "${need_built[@]}"; do
    [ -f "$f" ] || { echo "FAIL: not built: $f"; exit 1; }
done

WORK="$(mktemp -d)" || setup_error "mktemp -d failed (is TMPDIR full?)"
trap '[ -n "${KEEP_WORK:-}" ] && { cp "$WORK"/*.log "$KEEP_WORK"/ 2>/dev/null; cp "$WORK/kbd/screens.txt" "$KEEP_WORK/usb-kbd-screens.txt" 2>/dev/null; }; rm -rf "$WORK"' EXIT
mkdir -p "$WORK/bin"
bash "$STAGE" --no-build "$WORK/bin" || { echo "FAIL: staging the initramfs packages failed"; exit 1; }
ESP="$WORK/esp"
mkdir -p "$ESP/EFI/BOOT" "$ESP/harland"
init_arg=()
[ "$KBD" = 1 ] && init_arg=(--init "$INIT")
python3 "$HARLAND_DIR/tools/mkinitramfs.py" --bin-dir "$WORK/bin" "${init_arg[@]}" \
    --output "$ESP/harland/initramfs.tar" >/dev/null || { echo "FAIL: mkinitramfs failed"; exit 1; }
cp "$LOADER_EFI" "$ESP/EFI/BOOT/BOOTX64.EFI"
cp "$KERNEL_ELF" "$ESP/harland/kernel.elf"
# The enumerate boot fails its second controller once (AGAST #4889).
[ "$MODE" = enumerate ] && : > "$ESP/harland/fault-usb"
# The fallback boots (AGAST #4891): plain MSI, or the BSP tick's poll.
[ "$MODE" = keyboard-msi ] && : > "$ESP/harland/usb-no-msix"
[ "$MODE" = keyboard-poll ] && : > "$ESP/harland/usb-poll"

vars=()
if [ -n "$OVMF_VARS" ]; then
    cp "$OVMF_VARS" "$WORK/vars.fd"
    vars=(-drive "if=pflash,format=raw,file=$WORK/vars.fd")
fi

if [ "$KBD" = 1 ]; then
    # Each --send waits for its text on screen, then types. `spin` prints
    # one line and computes in ring 3 until killed; the prompt after its ^C
    # is the one `echo $?` is typed at.
    # The keyboard-ready line names how its controller is serviced: the
    # line that proves the boot option took. (Each controller's "running"
    # line comes earlier and can scroll by between screenshots.)
    # qemu-xhci has no MSI capability unless asked (msi=on): the MSI boot's
    # controllers get one, as the X99's Intel xHCI has.
    XHCI_OPT=""
    [ "$MODE" = keyboard-msi ] && XHCI_OPT=",msi=on"
    case "$MODE" in
        keyboard) VIA=MSI-X ;;
        keyboard-msi) VIA=MSI ;;
        keyboard-poll) VIA=polled ;;
    esac
    common=(
        --expect "\\[usb\\] hc1 slot 1: keyboard ready \\(endpoint 0x81, interval [0-9]+, $VIA\\)"
        --send '(?m)^rzsh>$' 'e c h o spc h i ret'
        --expect '(?m)^rzsh> echo hi\nhi$'
        --send '(?m)^hi\nrzsh>$' 's p i n ret'
        --send '(?m)^spin: running, Ctrl-C stops me$' 'ctrl-c'
        --send '(?m)^\^C\nrzsh>$' 'e c h o spc shift-4 shift-slash ret'
        --expect '(?m)^rzsh> echo \$\?\n130$'
    )
    case "$MODE" in
    keyboard)
        steps=(
            "${common[@]}"
            --send '(?m)^130\nrzsh>$' 'e c h o spc caps_lock a b caps_lock c ret'
            --expect '(?m)^rzsh> echo ABc\nABc$'
            --send '(?m)^ABc\nrzsh>$' 'e c h o spc x@1200 ret'
            --expect '(?m)^rzsh> echo xxxx+\nxxxx+$'
            --qmp-do '(?m)^xxxx+\nrzsh>$' 'device_del id=kbd'
            --expect '\[usb\] hc1 slot [0-9]+: keyboard gone, keys released'
            --qmp-do '\[usb\] hc1 port [0-9]+: detached \(slot [0-9]+ disabled\)' 'device_add driver=usb-kbd id=kbd bus=xhci1.0'
            --send '(?s)hc1 port [0-9]+: detached \(slot [0-9]+ disabled\).*\[usb\] hc1 slot [0-9]+: keyboard ready[^\n]*\n' 'e c h o spc b a c k ret'
            --expect '(?m)^echo back\nback$'
        )
        how="a USB keyboard" ;;
    keyboard-msi)
        steps=("${common[@]}" --absent '\[xhci\] hc[01] running: (MSI-X vector|no vector)')
        how="a USB keyboard on plain MSI (MSI-X off)" ;;
    keyboard-poll)
        steps=("${common[@]}" --absent '\[xhci\] hc[01] running: MSI(-X)? vector')
        how="a USB keyboard polled from the BSP tick (no vector)" ;;
    esac
    python3 "$SCRIPT_DIR/fbcon_screen.py" watch --qmp "$WORK/qmp.sock" --shots "$WORK/kbd" \
        --timeout "$TIMEOUT" "${steps[@]}" \
        --absent 'KERNEL PANIC|!!! EXCEPTION !!!' -- \
        qemu-system-x86_64 -cpu Haswell-v1 -smp 1 -m 2G \
        -machine q35,i8042=off -serial none -display none -vga std -no-reboot -monitor none \
        -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
        -drive "format=raw,file=fat:rw:$ESP" \
        -device "qemu-xhci,id=xhci0$XHCI_OPT" -device "qemu-xhci,id=xhci1$XHCI_OPT" -device usb-kbd,id=kbd,bus=xhci1.0
    rc=$?
    [ "$rc" -eq "$EXIT_SETUP" ] && setup_error "QEMU could not be started"
    if [ "$rc" -ne 0 ]; then
        echo "----- usb keyboard boot: last screen -----"
        cat "$WORK/kbd/screen.txt" 2>/dev/null
        echo "------------------------------------------"
    else
        echo "PASS: typed into rzsh on $how (no COM1, framebuffer console)"
    fi
    exit "$rc"
fi
SERIAL="$WORK/usb.log"
: > "$SERIAL"
timeout "$TIMEOUT" qemu-system-x86_64 -cpu Haswell-v1 -smp 2 -m 2G \
    -display none -no-reboot -monitor none \
    -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
    -drive "format=raw,file=fat:rw:$ESP" \
    -device qemu-xhci,id=xhci0 -device usb-kbd,bus=xhci0.0 \
    -device usb-kbd,bus=xhci0.0,usb_version=1 \
    -device qemu-xhci,id=xhci1 -device usb-kbd,bus=xhci1.0 \
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
grep -aE "\[xhci\]|\[usb\]|USB \(|fault-usb|KERNEL PANIC" "$SERIAL" | head -80
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
for hc in 0 1; do
    need "^\\[xhci\\] hc$hc [0-9A-F]{2}:[0-9A-F]{2}\\.[0-7] 1B36:000D v1\\.00: " "hc$hc is found and its capabilities read (qemu-xhci, xHCI 1.0)"
done
vectors=$(grep -aoE '^\[xhci\] hc[01] running: MSI-X vector [0-9]+ -> BSP$' "$SERIAL" | sort -u | grep -oE 'vector [0-9]+' | sort -u | wc -l)
if [ "$vectors" -eq 2 ]; then
    echo "PASS: each controller is running on its own MSI-X vector aimed at the BSP"
else
    echo "FAIL: want hc0 and hc1 running on two distinct MSI-X vectors -> BSP, got $vectors"
    rc=1
fi
# hc0: usb-kbd at its default high speed, and one with usb_version=1 at
# full speed, whose EP0 size is learned from the first 8 bytes of its
# device descriptor.
connected=$(grep -acE '^\[usb\] hc0 port [0-9]+: connected \(USB 2\)$' "$SERIAL")
ports=$(grep -aoE '^\[usb\] hc0 port [0-9]+: connected' "$SERIAL" | sort -u | wc -l)
if [ "$connected" -eq 2 ] && [ "$ports" -eq 2 ]; then
    echo "PASS: two of hc0's root ports report a keyboard connected, once each"
else
    echo "FAIL: want 2 'hc0 ... connected' lines on 2 ports, got $connected on $ports"
    rc=1
fi
need '^\[usb\] hc0 port [0-9]+: enabled, high speed$' "a port reset enabled the high-speed keyboard"
need '^\[usb\] hc0 port [0-9]+: enabled, full speed$' "a port reset enabled the full-speed keyboard"
need '^\[usb\] hc0 slot [12]: EP0 max packet 8 \(from the device descriptor\)$' "the full-speed keyboard's EP0 size came from its first 8 bytes"
for slot in 1 2; do
    need "^\\[usb\\] hc0 slot $slot addressed: port [0-9]+, address [1-9][0-9]*, EP0 (8|64) bytes$" "hc0 slot $slot is addressed"
    need "^\\[usb\\] hc0 slot $slot: device 0627:0001, USB [12]\\.[01], class 0, 1 configuration\\(s\\)$" "hc0 slot $slot: the device descriptor is read (QEMU's usb-kbd, 0627:0001)"
    need "^\\[usb\\] hc0 slot $slot: config 1, 34 bytes$" "hc0 slot $slot: the configuration is read"
    need "^\\[usb\\] hc0 slot $slot:   interface 0 class 3/1/1, 1 endpoint\\(s\\)$" "hc0 slot $slot: its HID boot keyboard interface is parsed"
    need "^\\[usb\\] hc0 slot $slot:   endpoint 0x81, 8 bytes, interval [0-9]+$" "hc0 slot $slot: its interrupt IN endpoint is parsed"
    need "^\\[usb\\] hc0 slot $slot: configured \\(configuration 1\\)$" "hc0 slot $slot: SET_CONFIGURATION completed"
done
# hc1: the forced error, a reset of hc1 alone, and its keyboard again.
# These run while init's suite prints, so a line may start mid-line.
need '\[xhci\] hc1: fault-usb: forcing a controller error$' "the fault-usb boot option fails hc1 once its keyboard is ready"
need '\[xhci\] hc1: controller error \(USBSTS 0x[0-9A-F]+\): resetting it alone$' "hc1's error is seen and only hc1 is reset"
need '\[xhci\] hc1: reset done, ports re-enumerating$' "hc1 comes back from its reset"
ready() { grep -acE "\\[usb\\] hc$1 slot [0-9]+: keyboard ready \\(endpoint 0x81, interval [0-9]+, MSI-X\\)$" "$SERIAL"; }
if [ "$(ready 1)" -eq 2 ]; then
    echo "PASS: hc1's keyboard is ready before the error and again after the reset"
else
    echo "FAIL: want hc1's keyboard ready twice (before and after its reset), got $(ready 1)"
    rc=1
fi
if [ "$(ready 0)" -eq 2 ] && ! grep -aqE '\[xhci\] hc0: (controller error|reset)' "$SERIAL"; then
    echo "PASS: hc0 kept running through hc1's reset (never reset, each keyboard ready once)"
else
    echo "FAIL: hc0 was disturbed by hc1's error (keyboards ready: $(ready 0), want 2; or hc0 reset)"
    rc=1
fi
if grep -aqE '^\[usb\] hc[0-9] port [0-9]+: .*device left unconfigured' "$SERIAL"; then
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
