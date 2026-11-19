#!/bin/bash
# Boot the `make shell` image and drive a scripted rzsh session over its
# serial console (AGAST #4252): the first interactive Indium prompt.
#
# The image is the one `make -C projects/indium shell` boots: every package in
# indium/initramfs.pkgs, with init_interactive installed as /bin/init
# (mkinitramfs.py --init), on a virtio-blk disk; harland's own BOOTX64.EFI
# under OVMF. tools/shell_session.py connects COM1 to a unix socket and plays:
#
#   wait for `rzsh> `, then type
#     echo hi          -> hi
#     pwd              -> /
#     ls /bin          -> lists rzsh, cat and init
#     cat /etc/motd    -> Welcome to Harland! (a spawned program)
#     echo after-cat   -> after-cat (the shell survives a child's exit)
#     exit             -> Goodbye!, "[init] Shell exited", "[exit] init
#                         exited with code 0, powering off", in that order,
#                         and QEMU exits by itself with status 0.
#
# rzsh is init_interactive's child, so its exit wakes init's sys_wait (#1882's
# per-process table); init_interactive reports it and returns, and init's own
# exit is an ACPI power-off (#2755). Before #1882 the kernel took rzsh's exit
# as init's and "[init] Shell exited" never appeared: that now fails.
#
# Usage: tools/test_shell_boot.sh
#        SKIP_BUILD=1    use the existing build/debug outputs
#        BOOT_TIMEOUT=N  seconds to wait for each prompt (default 300: OVMF
#                        and the boot come first, under TCG)
#        KEEP_WORK=DIR   copy the serial transcript (shell.log) into DIR
#        OVMF_CODE=F     OVMF firmware to use (default: search the usual paths)
#        SHELL_INIT=NAME the ELF installed as /bin/init (default
#                        init_interactive; `init` boots the Tier-1 suite, which
#                        never prompts: the test then fails, as it did before
#                        `make shell` existed)
#
# Exit: 0 = pass; 1 = a check failed (no prompt, wrong output, a panic, no
#       power-off) or a build failed; 3 = a required tool is missing: a
#       SETUP ERROR, as test_tier1_boot.sh.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARLAND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECTS_DIR="$(dirname "$HARLAND_DIR")"
ROOT_DIR="$(dirname "$PROJECTS_DIR")"
TIMEOUT="${BOOT_TIMEOUT:-300}"
SHELL_INIT="${SHELL_INIT:-init_interactive}"

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
for f in "$KERNEL_ELF" "$LOADER_EFI" "$PROJECTS_DIR/indium/build/debug/$SHELL_INIT.elf" \
         "$PROJECTS_DIR/rzsh/build/debug/rzsh.elf"; do
    [ -f "$f" ] || { echo "FAIL: not built: $f"; exit 1; }
done

WORK="$(mktemp -d)"
trap '[ -n "${KEEP_WORK:-}" ] && cp "$WORK"/*.log "$KEEP_WORK"/ 2>/dev/null; rm -rf "$WORK"' EXIT
mkdir -p "$WORK/bin" "$WORK/esp/EFI/BOOT" "$WORK/esp/harland"
for pkg in $USER_PKGS; do
    cp "$PROJECTS_DIR/$pkg"/build/debug/*.elf "$WORK/bin/" 2>/dev/null || true
done
python3 "$HARLAND_DIR/tools/mkinitramfs.py" --bin-dir "$WORK/bin" --init "$SHELL_INIT" \
    --output "$WORK/initramfs.qcow2" >/dev/null || { echo "FAIL: mkinitramfs failed"; exit 1; }
cp "$LOADER_EFI" "$WORK/esp/EFI/BOOT/BOOTX64.EFI"
cp "$KERNEL_ELF" "$WORK/esp/harland/kernel.elf"

vars=()
for p in "${OVMF_CODE/CODE/VARS}" /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd; do
    if [ -f "$p" ]; then
        cp "$p" "$WORK/vars.fd"
        vars=(-drive "if=pflash,format=raw,file=$WORK/vars.fd")
        break
    fi
done

# shell_session.py adds the serial port (a unix socket it listens on). The
# rest matches `make -C projects/indium shell`.
python3 "$SCRIPT_DIR/shell_session.py" "$WORK/shell.log" "$TIMEOUT" -- \
    qemu-system-x86_64 -cpu Haswell-v1 -smp 4 -m 2G \
    -display none -no-reboot -monitor none \
    -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
    -drive "format=raw,file=fat:rw:$WORK/esp" \
    -device virtio-blk-pci,drive=initramfs \
    -drive "file=$WORK/initramfs.qcow2,format=qcow2,if=none,id=initramfs"
rc=$?
[ "$rc" -eq "$EXIT_SETUP" ] && setup_error "QEMU could not be started"

if grep -aqE "KERNEL PANIC|!!! EXCEPTION !!!" "$WORK/shell.log" 2>/dev/null; then
    sed -n '/EXCEPTION/,/CR2/p' "$WORK/shell.log" | head -20
    echo "FAIL: kernel exception or panic on the serial console"
    rc=1
fi
if [ "$rc" -ne 0 ]; then
    echo "----- serial tail -----"
    tail -c 1500 "$WORK/shell.log" 2>/dev/null | tr -d '\r'
    echo
    echo "-----------------------"
fi
[ "$rc" -eq 0 ] && echo "PASS: scripted rzsh session on the serial console"
exit "$rc"
