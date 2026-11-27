#!/bin/bash
# Boot harland with no serial port and read its framebuffer console (AGAST
# #4868): the Acer laptop has no UART, so the kernel log, rzsh and the panic
# screen must reach the screen, and a missing COM1 must not hang the boot.
#
# QEMU gets `-serial none` (no 16550 at 0x3F8: its ports read 0xFF, as on
# the Acer), `-display none` and std VGA under OVMF (a GOP framebuffer).
# tools/fbcon_screen.py takes a QMP screendump every second and decodes the
# console's text with the kernel's own font table. Two boots:
#
#   console  init_interactive as /bin/init. The screen must show the boot
#            banner (replayed from the klog ring when the console starts),
#            the kernel's "No COM1" line and rzsh's `rzsh> ` prompt, and
#            then CPU 0 must go idle (HLT=1): rzsh is blocked in read(0),
#            which before #4868 spun for ever on LSR's floating data-ready
#            bit, feeding 0xFF into the line discipline. No panic on screen.
#   panic    the same disk plus \harland\panic-test: the kernel raises #UD
#            once the console is up. The screen must show the KERNEL PANIC
#            banner, the exception ("Invalid Opcode"), the register dump and
#            the recent-log tail, drawn with interrupts off.
#
# Usage: tools/test_fbcon_boot.sh
#        SKIP_BUILD=1    use the existing build/debug outputs
#        BOOT_TIMEOUT=N  seconds each boot may take (default 300)
#        KEEP_WORK=DIR   copy each boot's screens (fbcon-*.txt) into DIR
#        OVMF_CODE=F     OVMF firmware to use (default: search the usual paths)
#
# Exit: 0 = pass; 1 = a check failed or a build failed; 3 = a required tool
#       is missing: a SETUP ERROR, as test_tier1_boot.sh.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARLAND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECTS_DIR="$(dirname "$HARLAND_DIR")"
ROOT_DIR="$(dirname "$PROJECTS_DIR")"
TIMEOUT="${BOOT_TIMEOUT:-300}"
SHELL_INIT=init_interactive

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
for f in "$KERNEL_ELF" "$LOADER_EFI" "$PROJECTS_DIR/indium/build/debug/$SHELL_INIT.elf" \
         "$PROJECTS_DIR/rzsh/build/debug/rzsh.elf"; do
    [ -f "$f" ] || { echo "FAIL: not built: $f"; exit 1; }
done

WORK="$(mktemp -d)"
trap '[ -n "${KEEP_WORK:-}" ] && mkdir -p "$KEEP_WORK" && for b in console panic; do cp "$WORK/$b/screens.txt" "$KEEP_WORK/fbcon-$b.txt" 2>/dev/null; done; rm -rf "$WORK"' EXIT
mkdir -p "$WORK/bin" "$WORK/esp/EFI/BOOT" "$WORK/esp/harland"
bash "$STAGE" --no-build "$WORK/bin" || { echo "FAIL: staging the initramfs packages failed"; exit 1; }
python3 "$HARLAND_DIR/tools/mkinitramfs.py" --bin-dir "$WORK/bin" --init "$SHELL_INIT" \
    --output "$WORK/initramfs.qcow2" >/dev/null || { echo "FAIL: mkinitramfs failed"; exit 1; }
cp "$LOADER_EFI" "$WORK/esp/EFI/BOOT/BOOTX64.EFI"
cp "$KERNEL_ELF" "$WORK/esp/harland/kernel.elf"

# One boot: name, then fbcon_screen.py watch's checks. Each boot gets its
# own OVMF vars and a snapshot of the disk.
boot() {
    local name="$1"; shift
    local dir="$WORK/$name"
    mkdir -p "$dir"
    local vars=()
    for p in "${OVMF_CODE/CODE/VARS}" /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd; do
        if [ -f "$p" ]; then
            cp "$p" "$dir/vars.fd"
            vars=(-drive "if=pflash,format=raw,file=$dir/vars.fd")
            break
        fi
    done
    python3 "$SCRIPT_DIR/fbcon_screen.py" watch --qmp "$dir/qmp.sock" --shots "$dir" \
        --timeout "$TIMEOUT" "$@" -- \
        qemu-system-x86_64 -cpu Haswell-v1 -smp 1 -m 2G \
        -serial none -display none -vga std -no-reboot -monitor none \
        -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
        -drive "format=raw,file=fat:rw:$WORK/esp" \
        -device virtio-blk-pci,drive=initramfs \
        -drive "file=$WORK/initramfs.qcow2,format=qcow2,if=none,id=initramfs,snapshot=on"
    local rc=$?
    [ "$rc" -eq "$EXIT_SETUP" ] && setup_error "QEMU could not be started"
    if [ "$rc" -ne 0 ]; then
        echo "----- $name: last screen -----"
        cat "$dir/screen.txt" 2>/dev/null
        echo "------------------------------"
    else
        echo "PASS: $name boot (no COM1, framebuffer console)"
    fi
    return "$rc"
}

rc=0
boot console \
    --expect 'Hello from Harland!' \
    --expect 'No COM1 \(serial probe\)' \
    --expect 'Console: framebuffer text console on' \
    --expect '(?m)^rzsh>' \
    --idle-after '(?m)^rzsh>' \
    --absent 'KERNEL PANIC|!!! EXCEPTION !!!' || rc=1

touch "$WORK/esp/harland/panic-test"
boot panic \
    --expect '\*\*\* KERNEL PANIC \*\*\*  Harland has stopped\.' \
    --expect 'Vector: 6 \(Invalid Opcode\)' \
    --expect 'RIP: ' \
    --expect '--- recent kernel log ---' \
    --expect '\[panic-test\] raising #UD' || rc=1

[ "$rc" -eq 0 ] && echo "PASS: harland's framebuffer console with no COM1"
exit "$rc"
