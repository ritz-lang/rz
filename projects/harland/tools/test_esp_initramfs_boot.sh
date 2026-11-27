#!/bin/bash
# Boot Harland under OVMF with no block device at all, two ways:
#
#   esp   the initramfs is \harland\initramfs.tar on the ESP, beside the
#         kernel; BOOTX64.EFI hands it over in BootInfo (AGAST #4253).
#   grub  OVMF -> standalone GRUB-EFI -> multiboot2 harland.elf, with the
#         initramfs loaded by `module2 /boot/initramfs.tar`; the kernel finds
#         the multiboot2 module tag (type 3) and unpacks it (AGAST #4258).
#
# This is the EC2 Nitro / laptop case: no virtio-blk, so the kernel cannot
# read a raw TAR disk. BOOTX64.EFI reads the TAR with the UEFI file protocol
# into loader memory and passes its base and size in BootInfo (version 2);
# the kernel unpacks it from memory and only falls back to virtio-blk when
# BootInfo carries no initramfs.
#
# The ESP is a QEMU vvfat directory (EFI/BOOT/BOOTX64.EFI, harland/kernel.elf,
# harland/initramfs.tar). QEMU gets no -drive besides the ESP and the OVMF
# flash, and no virtio-blk, NVMe or other disk device.
#
# Passes only if, for each mode run:
#   - esp: the loader logged that it read harland\initramfs.tar (its size in
#     bytes, the same as the file's);
#   - grub: the kernel booted over multiboot2;
#   - the kernel loaded the initramfs from boot memory, not from a disk;
#   - init's Tier-1 suite reports ALL TESTS PASSED;
#   - the kernel took no exception and did not panic.
#
# Usage: tools/test_esp_initramfs_boot.sh [esp|grub|all]   (default: all)
#        SKIP_BUILD=1   use the existing build/debug outputs
#        BOOT_TIMEOUT=N seconds for the boot (default 120)
#        KEEP_WORK=DIR  copy the serial logs (esp-initramfs.log,
#                       grub-initramfs.log) into DIR
#        OVMF_CODE=F    OVMF firmware to use (default: search the usual paths)
#
# Exit: 0 = pass; 1 = the boot or a check failed; 2 = bad usage;
#       3 = a required tool is
#       missing: a SETUP ERROR (rz's and ci_local.py's EXIT_SETUP), not a
#       regression.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARLAND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECTS_DIR="$(dirname "$HARLAND_DIR")"
ROOT_DIR="$(dirname "$PROJECTS_DIR")"
TIMEOUT="${BOOT_TIMEOUT:-120}"

MODE="${1:-all}"

EXIT_SETUP=3
setup_error() { echo "SETUP ERROR: $*" >&2; exit "$EXIT_SETUP"; }

case "$MODE" in esp|grub|all) ;; *) echo "usage: $0 [esp|grub|all]" >&2; exit 2 ;; esac

command -v qemu-system-x86_64 >/dev/null || setup_error "qemu-system-x86_64 not found"
command -v python3 >/dev/null || setup_error "python3 not found"
if [ "$MODE" != esp ]; then
    command -v grub-mkstandalone >/dev/null || setup_error "grub-mkstandalone not found"
    [ -d "${GRUB_EFI_DIR:-/usr/lib/grub/x86_64-efi}" ] || setup_error "GRUB x86_64-efi modules not found (grub-efi-amd64-bin)"
fi
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
NEED=("$KERNEL_ELF" "$PROJECTS_DIR/indium/build/debug/init.elf")
[ "$MODE" != grub ] && NEED+=("$LOADER_EFI")
for f in "${NEED[@]}"; do
    [ -f "$f" ] || { echo "FAIL: not built: $f"; exit 1; }
done

WORK="$(mktemp -d)" || setup_error "mktemp -d failed (is TMPDIR full?)"
trap '[ -n "${KEEP_WORK:-}" ] && cp "$WORK"/*.log "$KEEP_WORK"/ 2>/dev/null; rm -rf "$WORK"' EXIT
mkdir -p "$WORK/bin"
bash "$STAGE" --no-build "$WORK/bin" || { echo "FAIL: staging the initramfs packages failed"; exit 1; }
TAR="$WORK/initramfs.tar"
python3 "$HARLAND_DIR/tools/mkinitramfs.py" --bin-dir "$WORK/bin" \
    --output "$TAR" >/dev/null || { echo "FAIL: mkinitramfs failed"; exit 1; }
TAR_SIZE=$(stat -c %s "$TAR")

# boot NAME ESP_DIR: boot OVMF from the vvfat ESP_DIR, the only disk (no
# virtio-blk, no NVMe), with serial to $WORK/NAME-initramfs.log, until a
# verdict, a panic, QEMU's exit or BOOT_TIMEOUT. Sets timed_out.
boot() {
    local vars=()
    if [ -n "$OVMF_VARS" ]; then
        cp "$OVMF_VARS" "$WORK/$1-vars.fd"
        vars=(-drive "if=pflash,format=raw,file=$WORK/$1-vars.fd")
    fi
    local serial="$WORK/$1-initramfs.log"
    : > "$serial"
    timeout "$TIMEOUT" qemu-system-x86_64 -cpu Haswell-v1 -smp 4 -m 2G \
        -display none -no-reboot -monitor none \
        -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
        -drive "format=raw,file=fat:rw:$2" \
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

    echo "----- $1 boot: initramfs lines -----"
    grep -aE "Boot protocol|initramfs|Initramfs|VirtIO block|KERNEL PANIC" "$serial" | head -20
    echo "-----------------------------------------------"
}

# check NAME: the checks every mode shares. Returns 1 if any failed.
check() {
    local serial="$WORK/$1-initramfs.log" r=0
    if grep -aqE "EXCEPTION|KERNEL PANIC" "$serial"; then
        sed -n '/EXCEPTION/,/CR2/p' "$serial" | head -20
        grep -aA4 "KERNEL PANIC" "$serial" | head -6
        echo "FAIL ($1): kernel panic or exception during boot"
        r=1
    fi
    if grep -aqF "[initramfs] Loading from boot memory ($TAR_SIZE bytes)" "$serial" \
            && grep -aqE "\[initramfs\] Loaded [1-9][0-9]* files from boot memory" "$serial"; then
        echo "PASS ($1): the kernel loaded the initramfs ($TAR_SIZE bytes) from boot memory"
    else
        echo "FAIL ($1): the kernel did not load the initramfs from boot memory"
        r=1
    fi
    if grep -aq "ALL TESTS PASSED" "$serial"; then
        echo "PASS ($1): init Tier-1 suite: ALL TESTS PASSED"
    else
        [ "$timed_out" = 1 ] && echo "FAIL ($1): no verdict within ${TIMEOUT}s (BOOT_TIMEOUT)"
        echo "FAIL ($1): init's Tier-1 suite did not report ALL TESTS PASSED"
        r=1
    fi
    return $r
}

rc=0

if [ "$MODE" != grub ]; then
    ESP="$WORK/esp"
    mkdir -p "$ESP/EFI/BOOT" "$ESP/harland"
    cp "$TAR" "$ESP/harland/initramfs.tar"
    cp "$LOADER_EFI" "$ESP/EFI/BOOT/BOOTX64.EFI"
    cp "$KERNEL_ELF" "$ESP/harland/kernel.elf"
    boot esp "$ESP"
    check esp || rc=1
    if grep -aqF "Read initramfs: $TAR_SIZE bytes" "$WORK/esp-initramfs.log"; then
        echo "PASS (esp): BOOTX64.EFI read harland\\initramfs.tar ($TAR_SIZE bytes) from the ESP"
    else
        echo "FAIL (esp): BOOTX64.EFI did not log 'Read initramfs: $TAR_SIZE bytes'"
        rc=1
    fi
fi

if [ "$MODE" != esp ]; then
    ESP="$WORK/esp-grub"
    mkdir -p "$ESP/EFI/BOOT"
    # The grub.cfg indium's mkiso.sh writes: the kernel plus the initramfs as
    # a multiboot2 module. A standalone GRUB image loads no video driver by
    # itself; without one it can't honour the framebuffer request.
    cat > "$WORK/grub.cfg" <<'GRUBCFG'
set timeout=0
insmod all_video
menuentry "Harland" { multiboot2 /boot/harland.elf; module2 /boot/initramfs.tar; boot; }
GRUBCFG
    grub-mkstandalone -O x86_64-efi -o "$ESP/EFI/BOOT/BOOTX64.EFI" \
        "boot/grub/grub.cfg=$WORK/grub.cfg" "boot/harland.elf=$KERNEL_ELF" \
        "boot/initramfs.tar=$TAR" || setup_error "grub-mkstandalone failed"
    boot grub "$ESP"
    check grub || rc=1
    if grep -aq "Boot protocol: Multiboot2" "$WORK/grub-initramfs.log"; then
        echo "PASS (grub): GRUB booted the kernel over multiboot2"
    else
        echo "FAIL (grub): the kernel did not boot over multiboot2"
        rc=1
    fi
fi

exit $rc
