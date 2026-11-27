#!/bin/bash
# Buddhafinger's Harland acceptance test (AGAST #4833; docs/
# BUDDHAFINGER_PROPOSAL.md, "Harland acceptance"): the editor, built by
# ritz1_selfhosted, run from rzsh on the serial console under QEMU.
#
# The image is the packaged Indium image (AGAST #4834): every package in
# indium/initramfs.pkgs, built and staged by indium/tools/stage_initramfs.sh
# as indium's Makefile stages them, with init_interactive as /bin/init (the
# interactive shell's, tools/test_shell_boot.sh in harland). The editor is
# initramfs.pkgs' buddhafinger entry: the builder image's ritz1_selfhosted
# builds it, and its Harland ELF is /bin/buddhafinger. tools/harland_console.py plays
# one session per boot; the storage disk (the second virtio-blk: /var's
# goliath image) is the same qcow2 throughout, so each boot is a reboot of
# the one before:
#
#   first          edit, bare Escape, :w, :q, the shell's terminal state,
#                  reopen, an empty save, kills before and after the write
#   reboot         every file persisted
#   fault-persist  \harland\fault-persist: the persistent update fails
#   fault-sync     \harland\fault-sync: the sync fails
#   after-faults   the file is what it was before both failed saves
#   ram-only       no storage disk: RAM-only and /var saves
#
# Boots use KVM where /dev/kvm opens and QEMU's KVM accelerator starts
# (the probe is test_tier1_boot.sh's), else TCG, said once up front.
#
# Usage: tools/test_harland_console.sh
#        SKIP_BUILD=1    stage the existing outputs (build/debug; the
#                        editor's build/builder) without building
#        BOOT_TIMEOUT=N  seconds to wait for each prompt or frame (default 120)
#        KEEP_WORK=DIR   copy the serial transcripts (*.log) into DIR
#        OVMF_CODE=F     OVMF firmware (default: search the usual paths)
#
# Exit: 0 = pass; 1 = a check failed or a build failed; 3 = a required tool
# is missing (SETUP ERROR, as test_shell_boot.sh).

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_DIR="$(dirname "$SCRIPT_DIR")"
PROJECTS_DIR="$(dirname "$PKG_DIR")"
ROOT_DIR="$(dirname "$PROJECTS_DIR")"
HARLAND_DIR="$PROJECTS_DIR/harland"
TIMEOUT="${BOOT_TIMEOUT:-120}"

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

ACCEL=(-cpu Haswell-v1)
if ( exec 3<>/dev/kvm ) 2>/dev/null \
    && printf 'quit\n' | timeout 60 qemu-system-x86_64 -accel kvm -machine none \
        -display none -nodefaults -monitor stdio >/dev/null 2>&1; then
    ACCEL=(-accel kvm -cpu host)
    echo "boots: KVM"
else
    echo "boots: TCG (KVM unavailable)"
fi

# The kernel with rz's default compiler, as the shell boot builds it; the
# initramfs packages through indium's stager, each with the compiler its
# entry names (the editor: the builder image's ritz1_selfhosted, #4813).
STAGE="$PROJECTS_DIR/indium/tools/stage_initramfs.sh"
if [ "${SKIP_BUILD:-0}" != "1" ]; then
    (cd "$ROOT_DIR" && ./rz build harland)
    brc=$?
    [ "$brc" -eq "$EXIT_SETUP" ] && setup_error "build of harland: a toolchain binary is missing"
    [ "$brc" -eq 0 ] || { echo "FAIL: build of harland failed"; exit 1; }
    bash "$STAGE" --build-only
    brc=$?
    [ "$brc" -eq "$EXIT_SETUP" ] && setup_error "building the initramfs packages: a toolchain binary or docker is missing"
    [ "$brc" -eq 0 ] || { echo "FAIL: building the initramfs packages failed"; exit 1; }
fi

KERNEL_ELF="$HARLAND_DIR/build/debug/harland.elf"
LOADER_EFI="$HARLAND_DIR/build/debug/BOOTX64.EFI"
for f in "$KERNEL_ELF" "$LOADER_EFI"; do
    [ -f "$f" ] || { echo "FAIL: not built: $f"; exit 1; }
done

WORK="$(mktemp -d)"
trap '[ -n "${KEEP_WORK:-}" ] && cp "$WORK"/*.log "$KEEP_WORK"/ 2>/dev/null; rm -rf "$WORK"' EXIT
# --no-build: the packages were built above (or, SKIP_BUILD, before).
bash "$STAGE" --no-build "$WORK/bin" || { echo "FAIL: staging the initramfs packages failed"; exit 1; }
EDITOR_ELF="$WORK/bin/buddhafinger.elf"
for f in "$EDITOR_ELF" "$WORK/bin/rzsh.elf" "$WORK/bin/init_interactive.elf"; do
    [ -f "$f" ] || { echo "FAIL: not in the packaged image: /bin/$(basename "$f" .elf)"; exit 1; }
done
# The stager already refuses a compiler= entry built by anything else; this
# says so in the log, and fails if initramfs.pkgs ever drops the pin.
grep -q '"compiler": *"ritz1_selfhosted"' "$EDITOR_ELF.manifest.json" \
    || { echo "FAIL: the packaged /bin/buddhafinger was not built by ritz1_selfhosted"; exit 1; }
echo "packaged: /bin/buddhafinger built by ritz1_selfhosted"
python3 "$HARLAND_DIR/tools/mkinitramfs.py" --bin-dir "$WORK/bin" --init init_interactive \
    --output "$WORK/initramfs.qcow2" >/dev/null || { echo "FAIL: mkinitramfs failed"; exit 1; }
qemu-img create -q -f qcow2 "$WORK/storage.qcow2" 64M || { echo "FAIL: qemu-img create failed"; exit 1; }

# An ESP per boot option set: "" (none), fault-persist, fault-sync.
esp() {
    local dir="$WORK/esp-${1:-plain}"
    mkdir -p "$dir/EFI/BOOT" "$dir/harland"
    cp "$LOADER_EFI" "$dir/EFI/BOOT/BOOTX64.EFI"
    cp "$KERNEL_ELF" "$dir/harland/kernel.elf"
    [ -n "$1" ] && : > "$dir/harland/$1"
    echo "$dir"
}

# boot SESSION ESP_OPTION STORAGE(yes|no)
rc=0
boot() {
    local session="$1" dir vars=() storage=()
    dir="$(esp "$2")"
    for p in "${OVMF_CODE/CODE/VARS}" /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd; do
        if [ -f "$p" ]; then
            cp "$p" "$WORK/vars-$session.fd"
            vars=(-drive "if=pflash,format=raw,file=$WORK/vars-$session.fd")
            break
        fi
    done
    # Each boot gets a fresh overlay of the initramfs; the storage disk is shared.
    qemu-img create -q -f qcow2 -F qcow2 -b "$WORK/initramfs.qcow2" "$WORK/initramfs-$session.qcow2"
    [ "$3" = yes ] && storage=(-drive "file=$WORK/storage.qcow2,format=qcow2,if=none,id=storage"
                               -device virtio-blk-pci,drive=storage)
    echo "--- boot: $session"
    python3 "$SCRIPT_DIR/harland_console.py" "$session" "$WORK/$session.log" "$TIMEOUT" -- \
        qemu-system-x86_64 "${ACCEL[@]}" -smp 4 -m 2G \
        -display none -no-reboot -monitor none \
        -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
        -drive "format=raw,file=fat:rw:$dir" \
        -device virtio-blk-pci,drive=initramfs \
        -drive "file=$WORK/initramfs-$session.qcow2,format=qcow2,if=none,id=initramfs" \
        "${storage[@]}"
    local brc=$?
    [ "$brc" -eq "$EXIT_SETUP" ] && setup_error "QEMU could not be started"
    if grep -aqE "KERNEL PANIC|!!! EXCEPTION !!!" "$WORK/$session.log" 2>/dev/null; then
        echo "FAIL: [$session] kernel exception or panic on the serial console"
        brc=1
    fi
    if [ "$brc" -ne 0 ]; then
        echo "----- [$session] serial tail -----"
        tail -c 1500 "$WORK/$session.log" 2>/dev/null | tr -d '\r'
        echo
        echo "-----------------------"
        rc=1
    fi
}

boot first "" yes
boot reboot "" yes
boot fault-persist fault-persist yes
boot fault-sync fault-sync yes
boot after-faults "" yes
boot ram-only "" no

[ "$rc" -eq 0 ] && echo "PASS: Buddhafinger's Harland console acceptance"
exit "$rc"
