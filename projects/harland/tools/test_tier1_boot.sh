#!/bin/bash
# Boot Harland with the indium userspace under OVMF and check init's Tier-1
# suite (#2132). Every Tier-1 test spawns a child that prints and exits, so
# this covers the blocking spawn -> child exit -> parent resume path.
#
# Two boots, both with the initramfs on a virtio-blk disk and a modern-only
# virtio-keyboard-pci (no I/O BAR, AGAST #3438):
#   native  OVMF -> Harland's own BOOTX64.EFI -> kernel.elf. The suite must
#           report ALL TESTS PASSED.
#   grub    OVMF -> standalone GRUB-EFI -> multiboot2 harland.elf. The
#           kernel takes its framebuffer from the multiboot2 framebuffer tag
#           (#2143). The display driver must come up and the suite must also
#           report ALL TESTS PASSED.
# Each boot also injects `sendkey a` through the QEMU monitor once the kernel
# logs "[OK] VirtIO input device"; the key must reach the kernel's input queue
# ("[virtio-input] event type=1 code=30 value=1") and init's input check.
#
# Each ESP is a QEMU vvfat directory, so the only tools needed are
# qemu-system-x86_64, OVMF, grub-mkstandalone (x86_64-efi) and python3.
# mtools, mkfs.vfat and xorriso are not needed.
#
# Usage: tools/test_tier1_boot.sh [native|grub|all]   (default: all)
#        SKIP_BUILD=1   use the existing build/debug outputs
#        BOOT_TIMEOUT=N seconds per boot (default 60)
#        KEEP_WORK=DIR  copy each boot's serial log (NAME.log) into DIR
#        OVMF_CODE=F    OVMF firmware to use (default: search the usual paths)
#        QEMU_MEM=SIZE  guest RAM (default 2G; 512M puts every pmm page under
#                       the low 1 GiB identity map, AGAST #3530)
#
# Exit: 0 = pass; 1 = a boot failed (panic, exception, failed suite, no
#       verdict before the timeout, or a failed build); 2 = bad usage;
#       3 = a required tool is missing: a SETUP ERROR, not a regression.
#       3 is rz's and ci_local.py's EXIT_SETUP (AGAST #1845): CI runs this
#       in main.yml's build-all job, and ci_local must read a host without
#       QEMU as "not verified here", never as a pass or a regression.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARLAND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECTS_DIR="$(dirname "$HARLAND_DIR")"
ROOT_DIR="$(dirname "$PROJECTS_DIR")"
TIMEOUT="${BOOT_TIMEOUT:-60}"
MEM="${QEMU_MEM:-2G}"
MODE="${1:-all}"
# Same packages indium/tools/mkiso.sh puts in the initramfs. init's suite
# spawns rzsh and prism's hello_gfx as well as indium's binaries.
USER_PKGS="indium rzsh ritzutils prism"

EXIT_SETUP=3
setup_error() { echo "SETUP ERROR: $*" >&2; exit "$EXIT_SETUP"; }

case "$MODE" in native|grub|all) ;; *) echo "usage: $0 [native|grub|all]" >&2; exit 2 ;; esac

command -v qemu-system-x86_64 >/dev/null || setup_error "qemu-system-x86_64 not found"
# Each boot writes a qcow2 overlay; without qemu-img that read as a boot
# that never reported a verdict (a FAIL) rather than a missing tool.
command -v qemu-img >/dev/null || setup_error "qemu-img not found (qemu-utils)"
if [ -n "${OVMF_CODE:-}" ]; then
    [ -f "$OVMF_CODE" ] || setup_error "OVMF firmware not found: $OVMF_CODE"
else
    for p in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd /usr/share/edk2/x64/OVMF_CODE.4m.fd; do
        if [ -f "$p" ]; then OVMF_CODE="$p"; break; fi
    done
    [ -n "$OVMF_CODE" ] || setup_error "OVMF firmware not found"
fi
OVMF_VARS=""
for p in "${OVMF_CODE/CODE/VARS}" /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd; do
    if [ -f "$p" ]; then OVMF_VARS="$p"; break; fi
done
if [ "$MODE" != native ]; then
    command -v grub-mkstandalone >/dev/null || setup_error "grub-mkstandalone not found"
    [ -d /usr/lib/grub/x86_64-efi ] || setup_error "GRUB x86_64-efi modules not found (grub-efi-amd64-bin)"
fi

if [ "${SKIP_BUILD:-0}" != "1" ]; then
    for pkg in harland $USER_PKGS; do
        (cd "$ROOT_DIR" && ./rz build "$pkg")
        brc=$?
        # rz exits EXIT_SETUP when a toolchain binary is missing (lld-link
        # for BOOTX64.EFI): the host's fault, not the code's.
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
mkdir -p "$WORK/bin"
for pkg in $USER_PKGS; do
    cp "$PROJECTS_DIR/$pkg"/build/debug/*.elf "$WORK/bin/" 2>/dev/null || true
done
python3 "$HARLAND_DIR/tools/mkinitramfs.py" --bin-dir "$WORK/bin" \
    --output "$WORK/initramfs.qcow2" >/dev/null || { echo "FAIL: mkinitramfs failed"; exit 1; }

# boot NAME ESP_DIR: boot one ESP, leaving the serial log in $WORK/NAME.log.
boot() {
    local name="$1" esp="$2" serial="$WORK/$1.log"
    local vars=()
    if [ -n "$OVMF_VARS" ]; then
        cp "$OVMF_VARS" "$WORK/$name-vars.fd"
        vars=(-drive "if=pflash,format=raw,file=$WORK/$name-vars.fd")
    fi
    : > "$serial"
    # A fresh qcow2 overlay per boot keeps each boot from seeing what the
    # other one wrote.
    qemu-img create -q -f qcow2 -F qcow2 -b "$WORK/initramfs.qcow2" "$WORK/$name-initramfs.qcow2"
    timeout "$TIMEOUT" qemu-system-x86_64 -cpu Haswell-v1 -smp 4 -m "$MEM" \
        -display none -no-reboot -monitor "unix:$WORK/$name-mon.sock,server,nowait" \
        -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
        -drive "format=raw,file=fat:rw:$esp" \
        -device virtio-blk-pci,drive=initramfs \
        -device virtio-keyboard-pci \
        -drive "file=$WORK/$name-initramfs.qcow2,format=qcow2,if=none,id=initramfs" \
        -serial "file:$serial" >/dev/null 2>&1 &
    local pid=$!
    local key_sent=0
    # init halts after the suite, so stop QEMU once a verdict line appears.
    for _ in $(seq 1 "$TIMEOUT"); do
        sleep 1
        if [ "$key_sent" = 0 ] && grep -aq "\[OK\] VirtIO input device" "$serial"; then
            # A failed send (monitor not up yet) retries next second; a key
            # that never lands is reported by key_received.
            send_key "$WORK/$name-mon.sock" a 2>/dev/null && key_sent=1
        fi
        grep -aqE "ALL TESTS PASSED|TESTS FAILED|KERNEL PANIC" "$serial" && { sleep 1; break; }
        kill -0 "$pid" 2>/dev/null || break
    done
    kill "$pid" 2>/dev/null
    wait "$pid" 2>/dev/null
    echo "----- $name boot: Tier-1 suite output (tail) -----"
    sed -n '/Running Tier 1 Test Suite/,$p' "$serial" | grep -aE '^\[test\]|PASS|FAIL|Results|EXCEPTION|RIP|RSP' | tail -30
}

# send_key SOCK KEY: type KEY on the guest's keyboard through the QEMU
# monitor socket SOCK (python3, so no socat is needed).
send_key() {
    python3 - "$1" "$2" <<'PY'
import socket, sys, time
s = socket.socket(socket.AF_UNIX)
s.settimeout(5)
s.connect(sys.argv[1])
s.recv(4096)  # monitor banner
s.sendall(("sendkey %s\n" % sys.argv[2]).encode())
time.sleep(0.5)
s.close()
PY
}

# key_received NAME: pass only if the injected key reached the kernel's input
# queue and init read it back (AGAST #3438).
key_received() {
    local log="$WORK/$1.log" ok=0
    grep -aq "\[OK\] VirtIO input device" "$log" || { echo "FAIL ($1): virtio-keyboard-pci did not come up"; ok=1; }
    grep -aq "\[virtio-input\] event type=1 code=30 value=1" "$log" || { echo "FAIL ($1): injected key A never reached the kernel input queue"; ok=1; }
    # Not anchored to "[test] input ...": the kernel's event lines land on the
    # same serial port between that prefix and init's verdict.
    grep -aq "key event code=30 value=1" "$log" || { echo "FAIL ($1): init did not read the injected key"; ok=1; }
    [ "$ok" = 0 ] && echo "PASS ($1): sendkey a reached the kernel input queue"
    return $ok
}

# no_exception NAME: fail if the kernel took an exception or panicked.
no_exception() {
    if grep -aqE "EXCEPTION|KERNEL PANIC" "$WORK/$1.log"; then
        sed -n '/EXCEPTION/,/CR2/p' "$WORK/$1.log"
        echo "FAIL ($1): kernel exception during boot"
        return 1
    fi
}

# all_passed NAME: pass only if the kernel took no exception and the suite
# reported ALL TESTS PASSED.
all_passed() {
    if no_exception "$1" && grep -aq "ALL TESTS PASSED" "$WORK/$1.log"; then
        echo "PASS ($1): init Tier-1 suite: ALL TESTS PASSED"
    else
        grep -aq "ALL TESTS PASSED" "$WORK/$1.log" || echo "FAIL ($1): suite did not report ALL TESTS PASSED"
        return 1
    fi
}

rc=0

if [ "$MODE" != grub ]; then
    mkdir -p "$WORK/esp-native/EFI/BOOT" "$WORK/esp-native/harland"
    cp "$LOADER_EFI" "$WORK/esp-native/EFI/BOOT/BOOTX64.EFI"
    cp "$KERNEL_ELF" "$WORK/esp-native/harland/kernel.elf"
    boot native "$WORK/esp-native"
    all_passed native || rc=1
    key_received native || rc=1
fi

if [ "$MODE" != native ]; then
    mkdir -p "$WORK/esp-grub/EFI/BOOT"
    # A standalone GRUB image loads no video driver by itself; without one
    # it can't honour the kernel's multiboot2 framebuffer request.
    cat > "$WORK/grub.cfg" <<'EOF'
set timeout=0
insmod all_video
menuentry "Harland" { multiboot2 /boot/harland.elf; boot; }
EOF
    grub-mkstandalone -O x86_64-efi -o "$WORK/esp-grub/EFI/BOOT/BOOTX64.EFI" \
        "boot/grub/grub.cfg=$WORK/grub.cfg" "boot/harland.elf=$KERNEL_ELF" \
        || setup_error "grub-mkstandalone failed"
    boot grub "$WORK/esp-grub"
    # The framebuffer must come from the multiboot2 tag, not just be absent
    # and tolerated (#2143).
    if grep -aq "\[OK\] Display driver" "$WORK/grub.log"; then
        grep -aA1 "\[OK\] Display driver" "$WORK/grub.log" | grep -a "Resolution" | sed 's/^ */      grub framebuffer: /'
    else
        echo "FAIL (grub): display driver did not come up from the multiboot2 framebuffer tag"
        rc=1
    fi
    all_passed grub || rc=1
    key_received grub || rc=1
fi

exit $rc
