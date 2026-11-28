#!/bin/bash
# Boot Harland with the indium userspace under OVMF and check init's Tier-1
# suite (#2132). Every Tier-1 test spawns a child that prints and exits, so
# this covers the blocking spawn -> child exit -> parent resume path.
#
# Two boots, both with the initramfs on a virtio-blk disk and a modern-only
# virtio-keyboard-pci (no I/O BAR, AGAST #3438):
#   native  OVMF -> Harland's own BOOTX64.EFI -> kernel.elf. The suite must
#           report ALL TESTS PASSED. Its virtio-blk is modern-only
#           (disable-legacy=on, AGAST #3576), so the initramfs is read over
#           the MMIO transport, and offers 1024-entry queues: the driver must
#           cap the queue at the 256 its rings hold ("queue 256").
#   grub    OVMF -> standalone GRUB-EFI -> multiboot2 harland.elf. The
#           kernel takes its framebuffer from the multiboot2 framebuffer tag
#           (#2143). The display driver must come up and the suite must also
#           report ALL TESTS PASSED. Its virtio-blk is QEMU's default
#           transitional device, so the legacy I/O-port path stays covered.
# Each boot's suite also runs two busy children side by side (#3629): their
# progress lines must interleave, which only timer preemption does.
# Each boot also injects `sendkey a` through the QEMU monitor once the kernel
# logs "[OK] VirtIO input device"; the key must reach the kernel's input queue
# ("[virtio-input] event type=1 code=30 value=1") and init's input check.
# init's exit powers the machine off (#2755): after the verdict QEMU must
# exit by itself, with status 0, instead of hanging until it is stopped.
#
# The native boot's second virtio-blk disk (the persistent store) answers every
# request 100 ms late. A spin-count poll gave up after ~40 ms of TCG time, and
# far less on a loaded host (AGAST #4078), so the store must still come up.
#
# The native ESP also carries \harland\klog-dump (AGAST #1885): the kernel
# then writes its crash ring buffer to serial just before it starts init. The
# dump must be exactly the kernel's serial output up to that point, starting
# at its first banner: every boot message, numbers included, reached the ring.
#
# Every boot runs in the kernel's boot-test mode (AGAST #1887): the native
# ESP carries \harland\boot-test and the grub boots pass `boot-test` on the
# multiboot2 cmdline. The kernel then runs its self-tests before init, one
# "[boot-test] PASS|FAIL <name>" line each and a "[boot-test] N passed, M
# failed" summary. Each boot must report every name in BOOT_TESTS passed and
# none failed. Boots without the option (every other boot test, and real
# hardware) run no self-tests.
#
# The grub boot's second virtio-blk disk is a real, blank qcow2 that a third
# boot, grub-reboot, boots again (AGAST #1881): the kernel's namespace is
# goliath, restored from that disk's goliath image at boot, and each boot
# counts itself in /var/boots and saves the image. The first boot must log
# "boot 1" and the reboot "boot 2": what one boot saved, the next one loaded.
#
# A boot fails as a hang when its serial log stops growing for BOOT_STALL
# seconds, not after a fixed time: on a host at load ~100 a TCG boot ran 10x
# slower and overran a fixed 60 s, though it was still making progress
# (AGAST #4078). A hung boot prints the vCPUs' state from the QEMU monitor.
#
# Each ESP is a QEMU vvfat directory, so the only tools needed are
# qemu-system-x86_64, OVMF, grub-mkstandalone (x86_64-efi) and python3.
# mtools, mkfs.vfat and xorriso are not needed.
#
# Usage: tools/test_tier1_boot.sh [native|grub|kvm|all]   (default: all)
#        kvm: only the native ESP, under KVM (-accel kvm -cpu host). It
#             requires the "sysret" self-test's non-canonical return RIP to
#             fault in ring 0 ("... CS 8"): only an IRETQ that checks the RIP
#             (KVM, hardware) takes #4610's syscall_exit_iret fixup, and TCG
#             never does (AGAST #4612). Skipped (exit 0, "SKIP (kvm): <why>")
#             where /dev/kvm is absent, can't be opened read-write, or QEMU's
#             KVM accelerator fails to start; never part of `all`.
#        SKIP_BUILD=1   use the existing build/debug outputs
#        BOOT_STALL=N   fail a boot whose serial log is idle N seconds (default 90;
#                       OVMF + GRUB print nothing for 20 s at a tenth of a core)
#        BOOT_TIMEOUT=N cap on each boot, however busy its log (default 600)
#        KEEP_WORK=DIR  copy each boot's serial log (NAME.log) into DIR
#        OVMF_CODE=F    OVMF firmware to use (default: search the usual paths)
#        POWEROFF_WAIT=N seconds QEMU gets to power off after the verdict
#                       (default 15)
#        QEMU_MEM=SIZE  guest RAM (default 2G; 512M puts every pmm page under
#                       the low 1 GiB identity map, AGAST #3530; above 4G each
#                       boot must also pass high_memory, AGAST #4183)
#        QEMU_SMP=SPEC  QEMU -smp (default 4). The kernel's per-CPU syscall
#                       stack self-test (AGAST #4192) must see every CPU, so
#                       `QEMU_SMP=2` runs the acceptance boot at two CPUs.
#                       Every AP must also answer the mailbox ping round
#                       trip (AGAST #4879); at 1 CPU the kernel says it has
#                       no AP to ping. Every AP must also serve the
#                       owner-side unmap and the kernel-half one (AGAST
#                       #4880); at 1 CPU the kernel says it has no AP for it.
#        COMPILER=NAME  ritz0, ritz1 or ritz1_selfhosted (AGAST #1848): build
#                       with `./rz build PKG --compiler NAME`, and require
#                       every binary the boot loads (kernel, BOOTX64.EFI,
#                       initramfs ELFs) to have a build manifest naming NAME,
#                       so a stale build from another compiler can't pass as
#                       NAME's image. Unset: rz's default, no manifest check.
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
TIMEOUT="${BOOT_TIMEOUT:-600}"
STALL="${BOOT_STALL:-90}"
MEM="${QEMU_MEM:-2G}"
SMP="${QEMU_SMP:-4}"
# The leading number of QEMU's -smp spec: how many CPUs must reach the
# per-CPU syscall self-test.
SMP_NCPUS="$(printf '%s\n' "$SMP" | sed -nE 's/^([0-9]+).*/\1/p' | head -1)"
[ -n "$SMP_NCPUS" ] || SMP_NCPUS=4
MODE="${1:-all}"

EXIT_SETUP=3
setup_error() { echo "SETUP ERROR: $*" >&2; exit "$EXIT_SETUP"; }

case "$MODE" in native|grub|kvm|all) ;; *) echo "usage: $0 [native|grub|kvm|all]" >&2; exit 2 ;; esac
COMPILER="${COMPILER:-}"
case "$COMPILER" in
    ""|ritz0|ritz1|ritz1_selfhosted) ;;
    *) echo "usage: COMPILER must be ritz0, ritz1 or ritz1_selfhosted, not '$COMPILER'" >&2; exit 2 ;;
esac

command -v qemu-system-x86_64 >/dev/null || setup_error "qemu-system-x86_64 not found"
# kvm mode runs only where KVM really works, and SKIPs (exit 0, saying why)
# elsewhere. [ -r ] / [ -w ] are not enough: as root in a user namespace they
# pass on a /dev/kvm owned by an unmapped nobody:nogroup that open() refuses
# (WSL2's gate, AGAST #4612), and that boot printed nothing. So really open the
# device read-write, then have QEMU itself bring up its KVM accelerator.
# KVM_DEV overrides the device path for the tests. Past this point a boot that
# fails under working KVM is a FAIL like any other.
skip_kvm() { echo "SKIP (kvm): $*; the KVM boot did not run"; exit 0; }
if [ "$MODE" = kvm ]; then
    KVM_DEV="${KVM_DEV:-/dev/kvm}"
    [ -e "$KVM_DEV" ] || skip_kvm "$KVM_DEV is absent"
    ( exec 3<>"$KVM_DEV" ) 2>/dev/null || skip_kvm "$KVM_DEV can't be opened read-write"
    kvm_probe=$(printf 'quit\n' | timeout 60 qemu-system-x86_64 -accel kvm -machine none \
        -display none -nodefaults -monitor stdio 2>&1 >/dev/null) \
        || skip_kvm "QEMU's KVM accelerator failed to start ($(printf '%s' "$kvm_probe" | tr '\n' ' ' | cut -c1-200))"
fi
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

# The packages in the initramfs, read after the tool checks so a missing
# tool is still a SETUP ERROR: indium/initramfs.pkgs, the one list shared
# with indium's Makefile and tools/mkiso.sh (AGAST #2759). init's suite spawns
# rzsh and prism's hello_gfx as well as indium's binaries.
# indium/tools/stage_initramfs.sh is initramfs.pkgs' one reader: it builds
# each package with the compiler its entry names and stages the ELFs
# (AGAST #2759, #4834).
STAGE="$PROJECTS_DIR/indium/tools/stage_initramfs.sh"

if [ "${SKIP_BUILD:-0}" != "1" ]; then
    for pkg in harland; do
        (cd "$ROOT_DIR" && ./rz build "$pkg" ${COMPILER:+--compiler "$COMPILER"})
        brc=$?
        # rz exits EXIT_SETUP when a toolchain binary is missing (lld-link
        # for BOOTX64.EFI): the host's fault, not the code's.
        [ "$brc" -eq "$EXIT_SETUP" ] && setup_error "build of $pkg: a toolchain binary is missing"
        [ "$brc" -eq 0 ] || { echo "FAIL: build of $pkg failed"; exit 1; }
    done
    COMPILER="$COMPILER" bash "$STAGE" --build-only
    brc=$?
    [ "$brc" -eq 3 ] && { echo "SETUP ERROR: building the initramfs packages: a toolchain binary or docker is missing" >&2; exit 3; }
    [ "$brc" -eq 0 ] || { echo "FAIL: building the initramfs packages failed"; exit 1; }
fi

KERNEL_ELF="$HARLAND_DIR/build/debug/harland.elf"
LOADER_EFI="$HARLAND_DIR/build/debug/BOOTX64.EFI"
for f in "$KERNEL_ELF" "$LOADER_EFI" "$PROJECTS_DIR/indium/build/debug/init.elf"; do
    [ -f "$f" ] || { echo "FAIL: not built: $f"; exit 1; }
done

# AGAST #4308: no kernel function may keep data below %rsp. An interrupt or
# exception on the current stack (IST 0) would clobber it.
python3 "$HARLAND_DIR/tools/check_no_red_zone.py" "$KERNEL_ELF" || exit 1

# COMPILER set: every binary the boot loads must say COMPILER built it. The
# manifest (build.py writes BIN.manifest.json beside each output) records the
# compiler; the build directory does not, so without this SKIP_BUILD, or a
# build/debug a ritz0 build left behind, would boot and pass as ritz1's image.
# The initramfs ELFs are checked as they are staged (stage_initramfs.sh
# --check-compiler, below): a compiler= entry (Buddhafinger, the builder
# image's ritz1_selfhosted, AGAST #4834) must name its own compiler instead.
if [ -n "$COMPILER" ]; then
    BOOT_BINS=("$KERNEL_ELF" "$LOADER_EFI")
    for f in "${BOOT_BINS[@]}"; do
        m="$f.manifest.json"
        [ -f "$m" ] || { echo "FAIL: $(basename "$f") has no build manifest ($m)"; exit 1; }
        built_by="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("compiler", ""))' "$m" 2>/dev/null)"
        [ "$built_by" = "$COMPILER" ] || {
            echo "FAIL: $(basename "$f") was built by ${built_by:-an unknown compiler}, not $COMPILER"
            exit 1
        }
    done
fi

WORK="$(mktemp -d)"
# sock_dir (tools/sock_dir.sh, shared with bench/run.sh, nexus's
# e2e_large_page.sh and smoke_stack): $TMPDIR if <dir>/<name> fits sun_path,
# else $XDG_RUNTIME_DIR, else /tmp; a full or unwritable one is skipped.
. "$ROOT_DIR/projects/ritz/tools/sock_dir.sh"
# The QEMU monitor sockets' dir (<name>-mon.sock): a socket path past
# sun_path's 107 bytes stops QEMU from starting at all (AGAST #4177).  Sized
# for a boot name of up to 15 bytes (native, grub).
SOCK_DIR="$(sock_dir rz_tier1_mon. 123456789012345-mon.sock)" || exit 1
trap '[ -n "${KEEP_WORK:-}" ] && cp "$WORK"/*.log "$KEEP_WORK"/ 2>/dev/null; rm -rf "$WORK" "$SOCK_DIR"' EXIT
mkdir -p "$WORK/bin"
bash "$STAGE" --no-build ${COMPILER:+--check-compiler "$COMPILER"} "$WORK/bin" || { echo "FAIL: staging the initramfs packages failed"; exit 1; }
if [ -n "$COMPILER" ]; then
    staged=("$WORK/bin"/*.elf)
    [ -f "${staged[0]}" ] || staged=()
    echo "PASS: $(( ${#BOOT_BINS[@]} + ${#staged[@]} )) boot binaries built by $COMPILER (or their initramfs.pkgs compiler=)"
fi
python3 "$HARLAND_DIR/tools/mkinitramfs.py" --bin-dir "$WORK/bin" \
    --output "$WORK/initramfs.qcow2" >/dev/null || { echo "FAIL: mkinitramfs failed"; exit 1; }

# boot NAME ESP_DIR BLK_OPTS [QEMU_ARG...]: boot one ESP with the initramfs
# disk on virtio-blk-pci,drive=initramfs<BLK_OPTS> and any extra QEMU_ARGs,
# leaving the serial log in $WORK/NAME.log. Fails (returns 1) if the boot
# reached no verdict: its log went idle for $STALL s, or it ran $TIMEOUT s.
boot() {
    local name="$1" esp="$2" blk_opts="$3" serial="$WORK/$1.log"
    shift 3
    local vars=()
    if [ -n "$OVMF_VARS" ]; then
        cp "$OVMF_VARS" "$WORK/$name-vars.fd"
        vars=(-drive "if=pflash,format=raw,file=$WORK/$name-vars.fd")
    fi
    : > "$serial"
    # A fresh qcow2 overlay per boot keeps each boot from seeing what the
    # other one wrote.
    qemu-img create -q -f qcow2 -F qcow2 -b "$WORK/initramfs.qcow2" "$WORK/$name-initramfs.qcow2"
    # The loop below enforces $TIMEOUT; this one only backs it up, late enough
    # that a hung guest's monitor is still there to report on.
    timeout "$((TIMEOUT + 30))" qemu-system-x86_64 -cpu "${QEMU_CPU:-Haswell-v1}" -smp "$SMP" -m "$MEM" \
        -display none -no-reboot -monitor "unix:$SOCK_DIR/$name-mon.sock,server,nowait" \
        -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
        -drive "format=raw,file=fat:rw:$esp" \
        -device "virtio-blk-pci,drive=initramfs$blk_opts" \
        -device virtio-keyboard-pci \
        -drive "file=$WORK/$name-initramfs.qcow2,format=qcow2,if=none,id=initramfs" \
        "$@" -serial "file:$serial" >/dev/null 2>&1 &
    local pid=$!
    local key_sent=0 verdict=0 stalled=0 size=0 last_size=-1
    local start=$SECONDS last_change=$SECONDS
    # Stop polling once a verdict line appears (QEMU then powers off, below).
    # $SECONDS, not a count of iterations: each one takes longer than 1 s on
    # a loaded host.
    while [ $((SECONDS - start)) -lt "$TIMEOUT" ]; do
        sleep 1
        size=$(stat -c %s "$serial")
        if [ "$size" != "$last_size" ]; then
            last_size=$size
            last_change=$SECONDS
        elif [ $((SECONDS - last_change)) -ge "$STALL" ]; then
            stalled=1
            break
        fi
        if [ "$key_sent" = 0 ] && grep -aq "\[OK\] VirtIO input device" "$serial"; then
            # A failed send (monitor not up yet) retries next second; a key
            # that never lands is reported by key_received.
            send_key "$SOCK_DIR/$name-mon.sock" a 2>/dev/null && key_sent=1
        fi
        grep -aqE "ALL TESTS PASSED|TESTS FAILED|KERNEL PANIC" "$serial" && { verdict=1; break; }
        # QEMU exited before a verdict: nothing to dump, the checks report it.
        kill -0 "$pid" 2>/dev/null || { verdict=1; break; }
    done
    local elapsed=$((SECONDS - start))
    # init's exit powers the machine off through ACPI (#2755), so after the
    # verdict QEMU should exit by itself; give it POWEROFF_WAIT seconds, then
    # stop it. Its exit status is 0 only for a guest power-off (124: timeout
    # stopped it, 143: we did); powered_off checks it.
    if [ "$verdict" = 1 ]; then
        for _ in $(seq 1 "${POWEROFF_WAIT:-15}"); do
            kill -0 "$pid" 2>/dev/null || break
            sleep 1
        done
    else
        # Where each vCPU is and whether it is halted (HLT=1) or spinning.
        echo "----- $name boot: no verdict; vCPU state from the QEMU monitor -----"
        monitor "$SOCK_DIR/$name-mon.sock" "info registers -a" 2>&1 \
            | grep -aE '^CPU#|IP=' | paste -d' ' - - | sed 's/^/      /'
    fi
    kill "$pid" 2>/dev/null
    wait "$pid" 2>/dev/null
    echo $? > "$WORK/$name.qemu-rc"
    echo "----- $name boot: Tier-1 suite output (tail) -----"
    sed -n '/Running Tier 1 Test Suite/,$p' "$serial" | grep -aE '^\[test\]|PASS|FAIL|Results|EXCEPTION|RIP|RSP' | tail -30
    [ "$verdict" = 1 ] && return 0
    echo "      serial tail: $(tail -c 200 "$serial" | tr -s '\r\n' '  ')"
    if [ "$stalled" = 1 ]; then
        echo "FAIL ($name): hung: serial output stopped for ${STALL}s (BOOT_STALL), ${elapsed}s into the boot"
    else
        echo "FAIL ($name): no verdict within ${TIMEOUT}s (BOOT_TIMEOUT), serial output still growing"
    fi
    return 1
}

# monitor SOCK CMD...: run each CMD on the QEMU monitor socket SOCK and print
# what it answers.
monitor() {
    python3 - "$@" <<'PY'
import socket, sys, time
s = socket.socket(socket.AF_UNIX)
s.settimeout(5)
s.connect(sys.argv[1])
for cmd in sys.argv[2:]:
    s.sendall((cmd + "\n").encode())
    time.sleep(1)
out = b""
try:
    while True:
        d = s.recv(65536)
        if not d:
            break
        out += d
except socket.timeout:
    pass
sys.stdout.write(out.decode(errors="replace"))
PY
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

# blk_transport NAME WANT: pass only if virtio-blk device 0 came up on the
# WANT transport (modern|legacy) with a 256-entry request queue.
blk_transport() {
    if grep -aqE "\[virtio-blk\] Device 0 initialized \([0-9]+ MB, $2, queue 256\)" "$WORK/$1.log"; then
        echo "PASS ($1): virtio-blk came up over the $2 transport with a 256-entry queue"
    else
        grep -a "\[virtio-blk\]" "$WORK/$1.log" | head -5
        echo "FAIL ($1): virtio-blk did not come up over the $2 transport with a 256-entry queue"
        return 1
    fi
}

# slow_disk NAME: pass only if the persistent store came up on the second
# virtio-blk disk, whose every request takes 100 ms (AGAST #4078).
slow_disk() {
    if grep -aq "\[OK\] Persistent storage" "$WORK/$1.log"; then
        echo "PASS ($1): persistent storage came up on a disk with 100 ms request latency"
    else
        grep -aE "\[virtio-blk\] (Read|Write) timeout|persist:|Persistent storage" "$WORK/$1.log" | head -5
        echo "FAIL ($1): persistent storage did not come up on a disk with 100 ms request latency"
        return 1
    fi
}

# ring_holds_boot NAME: pass only if the kernel's ring dump (the
# \harland\klog-dump boot option) holds its whole serial log up to the dump,
# byte for byte, from the first banner on (AGAST #1885).
ring_holds_boot() {
    python3 - "$WORK/$1.log" "$1" <<'PY'
import sys
log = open(sys.argv[1], "rb").read()
name = sys.argv[2]
start = b"\n=== RING BUFFER DUMP (kernel log) ===\n"
end = b"\n=== END RING BUFFER ===\n"
first = b"========================================\n    Hello from Harland!\n"
s = log.find(start)
if s < 0:
    sys.exit(f"FAIL ({name}): no ring buffer dump (\\harland\\klog-dump set)")
e = log.find(end, s)
if e < 0:
    sys.exit(f"FAIL ({name}): ring buffer dump never ended")
dump = log[s + len(start):e]
if first not in dump[:200]:
    sys.exit(f"FAIL ({name}): ring dump does not start at the kernel banner: {dump[:120]!r}")
if not log[:s].endswith(dump):
    k = 0
    pre = log[:s]
    while k < len(dump) and dump[-1 - k] == pre[-1 - k]:
        k += 1
    sys.exit(f"FAIL ({name}): serial and ring disagree {k} bytes before the dump: "
             f"serial {pre[-k - 60:-k]!r} vs ring {dump[-k - 60:len(dump) - k]!r}")
print(f"PASS ({name}): the crash ring holds all {len(dump)} bytes of the kernel's boot log")
PY
}

# The kernel self-tests every boot-test boot must pass (postinit.ritz's
# boot_self_tests and boot_process_tests). channel-close and
# channel-debug-print were skipped as page faults until AGAST #1887; the
# gate now requires both.
BOOT_TESTS="vmm higher-half heap ipc channel-close channel-debug-print munmap mmap-failure pmm-above-4g mmap-overlap mmap-cursor mmap-driver-window elf-loader sysret nmi-gs ist-nest nmi-nest cap-device shm-map virtio-blk-read proc-create-init driver-enter driver-fault driver-preempt driver-reap drv-irq-wait drv-mmio-map drv-dma-alloc drv-dma-free console-poll shm-wait net-attach net-info shm-retire net-addr frame-ring spawn-pages drv-quiesce smp-user"

# boot_tests_passed NAME: pass only if the kernel's boot-test summary is in
# the log (before any ring dump, which repeats it) with 0 failed, no test logged FAIL, and every BOOT_TESTS name
# logged PASS (AGAST #1887).
boot_tests_passed() {
    python3 - "$WORK/$1.log" "$1" $BOOT_TESTS <<'PY'
import re, sys
text = open(sys.argv[1], "rb").read().decode(errors="replace")
name, required = sys.argv[2], sys.argv[3:]
# The ring dump (\\harland\\klog-dump) repeats the log: read up to it only
text = text.split("\n=== RING BUFFER DUMP (kernel log) ===\n", 1)[0]
def fail(msg):
    print(msg)
    sys.exit(1)
results = re.findall(r"\[boot-test\] (PASS|FAIL) (\S+)", text)
passed = [t for v, t in results if v == "PASS"]
failed = [t for v, t in results if v == "FAIL"]
summary = re.search(r"\[boot-test\] (\d+) passed, (\d+) failed", text)
if failed:
    fail(f"FAIL ({name}): boot self-tests failed: {' '.join(failed)}")
if not summary:
    fail(f"FAIL ({name}): no boot-test summary (kernel ran no self-tests: \\harland\\boot-test / cmdline boot-test)")
missing = [t for t in required if t not in passed]
if missing:
    fail(f"FAIL ({name}): boot self-tests missing: {' '.join(missing)}")
n_pass, n_fail = map(int, summary.groups())
if n_fail != 0 or n_pass != len(passed):
    fail(f"FAIL ({name}): boot-test summary {n_pass} passed, {n_fail} failed disagrees with {len(passed)} PASS lines")
print(f"PASS ({name}): {n_pass} kernel boot self-tests passed")
PY
}

# no_exception NAME: fail if the kernel took an exception or panicked, and
# print the first one: the 20 boot lines before it and up to 40 after, the
# register dump or panic message included. A panic before init has no suite
# output for boot's tail to show, and its message is no EXCEPTION line:
# printing only an EXCEPTION..CR2 range left a grub-reboot panic as a bare
# FAIL line (AGAST #4856).
no_exception() {
    local log="$WORK/$1.log" first
    first="$(grep -anE "EXCEPTION|KERNEL PANIC" "$log" | head -1)"
    [ -n "$first" ] || return 0
    local n="${first%%:*}"
    local from=$((n > 20 ? n - 20 : 1))
    echo "----- $1 boot: serial lines $from-$((n + 40)), around the first EXCEPTION or KERNEL PANIC -----"
    sed -n "${from},$((n + 40))p" "$log" | tr -d '\r' | sed 's/^/      /'
    case "$first" in
        *EXCEPTION*) echo "FAIL ($1): kernel exception during boot" ;;
        *) echo "FAIL ($1): kernel panic during boot" ;;
    esac
    return 1
}

# powered_off NAME: pass only if init exited and QEMU then exited by itself
# (ACPI S5 power-off) instead of hanging until it was stopped (#2755).
powered_off() {
    local log="$WORK/$1.log" qrc
    qrc="$(cat "$WORK/$1.qemu-rc" 2>/dev/null)"
    if ! grep -aq "\[exit\] init exited with code" "$log"; then
        echo "FAIL ($1): init did not exit"
        return 1
    fi
    if [ "$qrc" != 0 ]; then
        echo "FAIL ($1): QEMU did not power off after init exited (exit status ${qrc:-none})"
        return 1
    fi
    echo "PASS ($1): init exited and QEMU powered off"
}

# preempted NAME: pass only if the kernel calibrated its LAPIC tick and init's
# two /bin/busy children (Tier-1 `preempt`, #3629) both ran side by side with
# their progress lines interleaved. Neither child makes a syscall between
# lines, so without timer preemption the first runs to its end before the
# second starts: A..A..B..B, exactly two runs.
#
# The bar is 6 runs, not 10 (AGAST #4438). The run count is a relative-speed
# measure: 16 lines alternating gives 16 runs, but a loaded host may give each
# child two steps per timeslice, pairing the lines ABBAABBA... for 9 runs
# (#4438's CI failure: 9 runs, preemption healthy). The genuine failure shapes
# are 2 runs (no preemption) and 4 (#4332's starved child, caught by the
# ratio below). 6 sits between them: two clear of 4, three below the measured
# CI tail of 9, seven below the 13..16 healthy pair (39 boots, load 2..23).
# The ratio check is the primary invariant: it measures preemption directly
# and is scale-invariant under host load.
preempted() {
    local log="$WORK/$1.log"
    if ! grep -aqE '\[timer\] LAPIC timer [0-9]+ Hz .*periodic [0-9]+ Hz tick' "$log"; then
        grep -a '\[timer\]' "$log" | head -3
        echo "FAIL ($1): no calibrated LAPIC timer tick"
        return 1
    fi
    python3 - "$log" "$1" <<'PY'
import re, sys
log, name = sys.argv[1], sys.argv[2]
text = open(log, "rb").read().decode(errors="replace")
lines = re.findall(r"\[busy ([AB])\] (\d+)/(\d+)", text)
seq = [tag for tag, _, _ in lines]
done = {tag for tag, n, total in lines if n == total}
runs = sum(1 for i, t in enumerate(seq) if i == 0 or seq[i - 1] != t)
order = "".join(seq)
if done != {"A", "B"}:
    print(f"FAIL ({name}): busy children did not both finish (progress: {order or 'none'})")
    sys.exit(1)
if runs < 6:
    print(f"FAIL ({name}): busy children barely interleaved, not preempted each step ({order}, {runs} runs)")
    sys.exit(1)
# The interleave count is timing-sensitive, so also read the scheduler's own
# counters (AGAST #4332). A healthy pair preempts on almost every timer tick
# that interrupts ring 3, so the tick:preemption ratio is ~1.1..1.5 whichever
# compiler built kernel and userland. The bug left one child running alone
# for hundreds of ticks (911 ticks, 195 preemptions, ratio 4.7) while the fix
# gives 356/233 (1.5). Measured over 39 boots at load 2..23 (AGAST #4438):
# 1.10..1.23. The ratio is scale-invariant: a loaded host slows the
# guest and inflates ticks and preemptions together. 3 leaves margin on both
# sides, and the run count above must pass as well, so neither a lone green
# boot nor a lucky preemption can wave the regression through.
# The ticks are the contended ones, those that found two or more processes
# runnable (proc/sched.ritz, AGAST #4832): the boot's total also counts
# every tick a Tier-1 program spends alone, waiting on the 100 ms disk say,
# which no scheduler can preempt on. Counted against all ticks, the ratio
# grew with the suite (2.96 once #4830's /var test joined it) until a test
# that changed nothing in the scheduler failed it.
sched = re.search(r"\[sched\] (\d+) ticks, (\d+) switches, (\d+) preemptions, (\d+) contended ticks", text)
if not sched:
    print(f"FAIL ({name}): no [sched] tick/preemption counters to check the preempt path")
    sys.exit(1)
ticks, switches, preemptions, contended = map(int, sched.groups())
if preemptions == 0 or contended > preemptions * 3:
    print(f"FAIL ({name}): one child ran alone: {contended} contended ticks but only {preemptions} preemptions (ratio {contended / max(preemptions, 1):.1f}; AGAST #4332)")
    sys.exit(1)
print(f"PASS ({name}): two busy children preempted each other: {order} ({runs} runs, {contended} contended of {ticks} ticks / {preemptions} preemptions)")
PY
}

# mem_mib SIZE: QEMU's -m SIZE (e.g. 512M, 6G, 6144) in MiB.
mem_mib() {
    case "$1" in
        *[gG]) echo $(( ${1%[gG]} * 1024 )) ;;
        *[mM]) echo "${1%[mM]}" ;;
        *) echo "$1" ;;
    esac
}

# high_memory NAME: with more than 4 GiB of guest RAM, pmm must count more
# than 4 GiB free and the kernel's above-4G self-test must pass: it takes
# pages from the top of RAM and touches them through the physmap (#4183).
high_memory() {
    local log="$WORK/$1.log" free_mb
    free_mb="$(grep -aoE 'Free pages: +[0-9]+ \([0-9]+ MB\)' "$log" | head -1 | sed -E 's/.*\(([0-9]+) MB\)/\1/')"
    if [ -z "$free_mb" ] || [ "$free_mb" -le 4096 ]; then
        echo "FAIL ($1): pmm reports ${free_mb:-no} MB free with $MEM of RAM (want > 4096)"
        return 1
    fi
    if ! grep -aqE '\[pmm\] above-4G self-test: [0-9]+ pages from 0x[0-9A-Fa-f]+ PASSED' "$log"; then
        grep -a '\[pmm\]' "$log" | head -5
        echo "FAIL ($1): above-4G self-test did not pass"
        return 1
    fi
    echo "PASS ($1): $free_mb MB free; pages above 4 GiB allocated and touched through the physmap"
}

# persisted NAME N: pass only if boot NAME restored the goliath image the
# boot before saved, so this is boot N of the storage disk (#1881).
persisted() {
    local got
    got="$(grep -aoE '\[OK\] Persistent storage \(goliath image: boot [0-9]+' "$WORK/$1.log" | head -1 | grep -oE '[0-9]+$')"
    if [ "$got" = "$2" ]; then
        echo "PASS ($1): goliath image on the storage disk: boot $2"
    else
        grep -aE "Persistent storage|kfs:" "$WORK/$1.log" | head -5
        echo "FAIL ($1): want boot $2 of the storage disk, got ${got:-no count}"
        return 1
    fi
}

# image_entries: print the keys of the goliath image the storage disk holds.
# The kernel saves only the persistent subtree (/var, #4321), so the image's
# root is that subtree's contents: no /bin, /etc or any other initramfs file.
# Reads the qcow2's slots and image with python3 (already a required tool).
image_entries() {
    local raw
    raw="$(mktemp)" || return 1
    qemu-img convert -f qcow2 -O raw "$WORK/storage.qcow2" "$raw" || { rm -f "$raw"; return 1; }
    python3 - "$raw" <<'PY'
import struct, sys

raw = open(sys.argv[1], "rb").read()

def fnv(b):
    h = 14695981039346656037
    for x in b[:504]:
        h = ((h ^ x) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h

best = None
for idx in (0, 1):
    sb = raw[idx * 512:(idx + 1) * 512]
    if len(sb) < 512 or sb[:8] != b"GOLIATHB":
        continue
    version, sector = struct.unpack_from("<II", sb, 8)
    gen, lba, ln = struct.unpack_from("<QQQ", sb, 16)
    if version != 2 or sector != 512 or struct.unpack_from("<Q", sb, 504)[0] != fnv(sb):
        continue
    if gen == 0 or ln == 0 or lba < 2 or lba * 512 + ln > len(raw):
        continue
    if best is None or gen > best[0]:
        best = (gen, lba, ln)
if best is None:
    print("no valid goliath image on the storage disk")
    sys.exit(1)
gen, lba, ln = best
img = raw[lba * 512:lba * 512 + ln]
magic, version, count = struct.unpack_from("<8sII", img, 0)
if magic != b"GOLIATHS" or version != 1:
    print("bad goliath image")
    sys.exit(1)
blobs = {}
off = 48
for _ in range(count):
    bid = img[off:off + 32]
    size = struct.unpack_from("<Q", img, off + 32)[0]
    off += 40
    blobs[bid] = img[off:off + size]
    off += size
print("goliath image: generation %d, %d bytes, %d blobs" % (gen, ln, count))

def walk(blob, path):
    n = struct.unpack_from("<I", blob, 0)[0]
    for i in range(n):
        e = blob[4 + i * 320:4 + (i + 1) * 320]
        name = e[:256].split(b"\0", 1)[0].decode(errors="replace")
        kind, bid = e[257], e[258:290]
        p = path + "/" + name
        print("  " + p + ("/" if kind == 1 else ""))
        if kind == 1 and bid in blobs:
            walk(blobs[bid], p)

walk(blobs.get(img[16:48], b"\0\0\0\0"), "")
PY
    rm -f "$raw"
}

# saved_subtree NAME: pass only if the image the boot saved holds the
# persistent /var subtree and no initramfs content (#4321). Boot 1 wrote
# /var/x, so the subtree's keys must be /boots and /x — no /bin.
saved_subtree() {
    local out
    if ! out="$(image_entries)"; then
        echo "FAIL ($1): no readable goliath image on the storage disk"
        return 1
    fi
    echo "$out" | sed "s/^/  ($1) /"
    local top
    top="$(echo "$out" | sed -n 's/^  \/\([^\/]*\)\/\{0,1\}$/\1/p' | sort | tr '\n' ' ')"
    if echo "$out" | grep -qE '^  /(bin|etc|initramfs)(/|$)'; then
        echo "FAIL ($1): initramfs content is in the saved image: $top"
        return 1
    fi
    if ! echo "$out" | grep -qx '  /boots' || ! echo "$out" | grep -qx '  /x'; then
        echo "FAIL ($1): saved subtree keys are '$top', want 'boots x'"
        return 1
    fi
    echo "PASS ($1): saved image holds only the /var subtree: $top"
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

# write_empty NAME: pass only if indium's write_empty_test checked /var as
# well as /tmp (AGAST #4830). Its exit code already fails the suite; this
# stops a boot whose storage disk came up from passing on the /tmp leg alone.
write_empty() {
    if grep -aq "\[write_empty_test\] PASS: /tmp and /var" "$WORK/$1.log"; then
        echo "PASS ($1): an empty write_file emptied the file on /tmp and /var"
        return 0
    fi
    grep -a "\[write_empty_test\]" "$WORK/$1.log" | head -3
    echo "FAIL ($1): write_empty_test did not pass on both /tmp and /var"
    return 1
}

# stat_ok NAME: pass only if indium's stat_test checked /var as well as /tmp
# (AGAST #4832): stat/fstat's size, mtime and mode, and open(O_CREAT)'s
# mode. Its exit code already fails the suite; this stops a boot whose
# storage disk came up from passing on the /tmp leg alone.
stat_ok() {
    if grep -aq "\[stat_test\] PASS: /tmp and /var" "$WORK/$1.log"; then
        echo "PASS ($1): stat and fstat reported size, mtime and mode on /tmp and /var"
        return 0
    fi
    grep -a "\[stat_test\]" "$WORK/$1.log" | head -3
    echo "FAIL ($1): stat_test did not pass on both /tmp and /var"
    return 1
}

# dir_ok NAME: pass only if indium's dir_test listed /var as well as /tmp
# (AGAST #4947): ritzlib.fs dir_open / DirIter over O_DIRECTORY and
# getdents64. As stat_ok: the /tmp leg alone doesn't pass a boot with storage.
dir_ok() {
    if grep -aq "\[dir_test\] PASS: /tmp and /var" "$WORK/$1.log"; then
        echo "PASS ($1): dir_open and DirIter listed directories on /tmp and /var"
        return 0
    fi
    grep -a "\[dir_test\]" "$WORK/$1.log" | head -3
    echo "FAIL ($1): dir_test did not pass on both /tmp and /var"
    return 1
}

# net_nodev NAME: pass only if init ran indium's ping, udp-send and
# udp-recv and each exited 19 (-Errno.NoDev): a Tier-1 boot runs no ring-2
# service, so NetAttach answers NoDev and each tool ends before it publishes
# a request (AGAST #4751, docs/RING2_NET.md "Ring-3 tools"). The kernel must
# also have declared all three net calls: an undeclared number logs
# "[syscall] unknown" and answers NoSys, which is not the spec's answer.
net_nodev() {
    local tool rc=0
    for tool in ping udp-send udp-recv; do
        # The tool's own stderr line lands between init's "[test] ... " and
        # its verdict on the one serial console.
        if ! grep -aPzq "\\[test\\] $tool nodev \\.\\.\\. $tool: NetAttach: Errno\\.NoDev [^\\n]*\\(-19\\)\\r?\\nPASS \\(exit=19\\)" "$WORK/$1.log"; then
            grep -a "\[test\] $tool nodev" "$WORK/$1.log" | head -1
            echo "FAIL ($1): $tool did not exit 19 (Errno.NoDev) without the net service"
            rc=1
        fi
    done
    if grep -aqE '\[syscall\] unknown: (224|225|227|228)\b' "$WORK/$1.log"; then
        echo "FAIL ($1): a net call reached the kernel undeclared (NoSys, not NoDev)"
        rc=1
    fi
    [ $rc = 0 ] && echo "PASS ($1): ping, udp-send and udp-recv exit 19 (Errno.NoDev) with no net service"
    return $rc
}

# smp_stacks NAME: pass only if the kernel proved (AGAST #4192) that every
# CPU -smp starts was inside a ring-3 SYSCALL at once, each on its own per-CPU
# stack and with its own saved user frame. The self-test runs after
# ap_boot_all and before init, so it is in every boot's log.
smp_stacks() {
    local line
    # One CPU: main.ritz init_smp runs the self-test only with an AP to run
    # it against, so there is no verdict to want, and any [smp] line is news.
    if [ "$SMP_NCPUS" -le 1 ]; then
        if grep -aq '\[smp\]' "$WORK/$1.log"; then
            grep -a '\[smp\]' "$WORK/$1.log" | head -5
            echo "FAIL ($1): one CPU, but the SMP self-test said something"
            return 1
        fi
        echo "PASS ($1): one CPU, no SMP syscall-stack self-test to run"
        return 0
    fi
    line="$(grep -aoE '\[smp\] syscall stacks OK: [0-9]+ CPUs' "$WORK/$1.log" | head -1)"
    if [ "$line" = "[smp] syscall stacks OK: $SMP_NCPUS CPUs" ]; then
        echo "PASS ($1): $SMP_NCPUS CPUs in ring-3 SYSCALL at once on per-CPU stacks"
    else
        grep -a '\[smp\]' "$WORK/$1.log" | head -5
        echo "FAIL ($1): no per-CPU syscall stack verdict for $SMP_NCPUS CPUs (got: ${line:-none})"
        return 1
    fi
}

# mbox_round_trip NAME: pass only if every AP -smp starts answered the BSP's
# pings over its mailbox from its idle loop (AGAST #4879, docs/SMP_USER.md
# §6): one "[mbox] round trip OK: cpu K answered 64 pings" line per AP, K
# distinct (the crash-ring dump repeats each line). At one CPU there is no
# AP, and the kernel must say "[mbox] no APs to ping" instead.
mbox_round_trip() {
    local want=$((SMP_NCPUS - 1)) got
    if grep -aq '\[mbox\] round trip FAIL' "$WORK/$1.log"; then
        grep -a '\[mbox\]' "$WORK/$1.log" | head -5
        echo "FAIL ($1): an AP did not answer the BSP's pings over its mailbox"
        return 1
    fi
    if [ "$want" -le 0 ]; then
        if grep -aq '\[mbox\] no APs to ping' "$WORK/$1.log"; then
            echo "PASS ($1): one CPU, no AP to ping over the mailbox"
            return 0
        fi
        echo "FAIL ($1): one CPU, but no \"[mbox] no APs to ping\" line"
        return 1
    fi
    got="$(grep -aoE '\[mbox\] round trip OK: cpu [0-9]+ answered 64 pings' "$WORK/$1.log" | sort -u | wc -l)"
    if [ "$got" = "$want" ]; then
        echo "PASS ($1): all $want APs answered 64 pings each over their mailboxes"
        return 0
    fi
    grep -a '\[mbox\]' "$WORK/$1.log" | head -5
    echo "FAIL ($1): $got of $want APs answered the mailbox round trip"
    return 1
}

# tlb_owner_unmap NAME: pass only if every AP -smp starts unmapped a page
# from a space it had loaded, on the BSP's UNMAP request, and saw a
# kernel-half unmap (AGAST #4880, docs/SMP_USER.md §3, §6): per AP one
# "[tlb] owner unmap OK: cpu K saw the unmap" and one "[tlb] kernel invlpg
# OK: cpu K saw the unmap" line, K distinct, and no FAIL. At one CPU the
# kernel must say "[tlb] no APs for the owner unmap" instead. At any count,
# vmm_free_pml4's lazy-CR3 assert ("[vmm] vmm_free_pml4: ... still loaded")
# must never fire: a CPU kept a space loaded that was being freed.
tlb_owner_unmap() {
    local want=$((SMP_NCPUS - 1)) owner kernel
    if grep -aq '\[vmm\] vmm_free_pml4: .* still loaded' "$WORK/$1.log"; then
        grep -a '\[vmm\] vmm_free_pml4' "$WORK/$1.log" | head -5
        echo "FAIL ($1): a PML4 was freed while a CPU still had it loaded"
        return 1
    fi
    if grep -aq '\[tlb\] .* FAIL' "$WORK/$1.log"; then
        grep -a '\[tlb\]' "$WORK/$1.log" | head -5
        echo "FAIL ($1): an AP missed an unmap (owner-side UNMAP or KERNEL_INVLPG)"
        return 1
    fi
    if [ "$want" -le 0 ]; then
        if grep -aq '\[tlb\] no APs for the owner unmap' "$WORK/$1.log"; then
            echo "PASS ($1): one CPU, no AP for the owner unmap"
            return 0
        fi
        echo "FAIL ($1): one CPU, but no \"[tlb] no APs for the owner unmap\" line"
        return 1
    fi
    owner="$(grep -aoE '\[tlb\] owner unmap OK: cpu [0-9]+ saw the unmap' "$WORK/$1.log" | sort -u | wc -l)"
    kernel="$(grep -aoE '\[tlb\] kernel invlpg OK: cpu [0-9]+ saw the unmap' "$WORK/$1.log" | sort -u | wc -l)"
    if [ "$owner" = "$want" ] && [ "$kernel" = "$want" ]; then
        echo "PASS ($1): all $want APs saw the owner-side unmap and the kernel-half one"
        return 0
    fi
    grep -a '\[tlb\]' "$WORK/$1.log" | head -5
    echo "FAIL ($1): $owner (owner) and $kernel (kernel) of $want APs saw the unmap"
    return 1
}

# smp_user NAME: pass only if user processes ran pinned to an AP (AGAST
# #4881, docs/SMP_USER.md §6; the boot carries \harland\smp-user or the
# `smp-user` word). With APs, one on the BSP and one on the last AP (index
# NCPUS - 1) each made 100000 forwarded and 100000 local test syscalls at
# once, every count exact: "[smp-user] concurrent syscalls OK: cpu0 100000
# cpuK 100000, forwarded F". At one CPU the pinned spawn must have fallen
# back to the BSP: "[smp-user] single CPU: pinned spawn ran on the BSP".
# With APs, a process parked on cpu K must also have been woken from the BSP
# and resumed on cpu K, and one parked on the BSP woken from cpu K (test
# (b)): "[smp-user] cross-CPU wake OK: woken on cpu K by cpu 0, on cpu 0 by
# cpu K".
smp_user() {
    local last=$((SMP_NCPUS - 1)) line wake
    if grep -aq '\[smp-user\] FAIL' "$WORK/$1.log"; then
        grep -a '\[smp-user\]' "$WORK/$1.log" | head -5
        echo "FAIL ($1): the smp-user boot test failed"
        return 1
    fi
    if [ "$last" -le 0 ]; then
        if grep -aq '\[smp-user\] single CPU: pinned spawn ran on the BSP' "$WORK/$1.log"; then
            echo "PASS ($1): one CPU, the pinned spawn ran on the BSP"
            return 0
        fi
        echo "FAIL ($1): one CPU, but no \"[smp-user] single CPU\" line"
        return 1
    fi
    line="$(grep -aoE '\[smp-user\] concurrent syscalls OK: cpu0 100000 cpu[0-9]+ 100000, forwarded [0-9]+' "$WORK/$1.log" | head -1)"
    if ! printf '%s\n' "$line" | grep -q " cpu$last 100000,"; then
        grep -a '\[smp-user\]' "$WORK/$1.log" | head -5
        echo "FAIL ($1): no concurrent-syscalls verdict for a process on cpu $last (got: ${line:-none})"
        return 1
    fi
    wake="$(grep -aoE '\[smp-user\] cross-CPU wake OK: woken on cpu [0-9]+ by cpu [0-9]+, on cpu [0-9]+ by cpu [0-9]+' "$WORK/$1.log" | head -1)"
    if [ "$wake" != "[smp-user] cross-CPU wake OK: woken on cpu $last by cpu 0, on cpu 0 by cpu $last" ]; then
        grep -a '\[smp-user\]' "$WORK/$1.log" | head -5
        echo "FAIL ($1): no cross-CPU wake verdict for a process on cpu $last (got: ${wake:-none})"
        return 1
    fi
    echo "PASS ($1): $line"
    echo "PASS ($1): $wake"
    return 0
}

# sysret_ring0 NAME: pass only if the "sysret" self-test's non-canonical
# return RIP faulted in ring 0 at syscall_exit_iret (CS 8), the path #4610's
# fixup covers and TCG never takes (AGAST #4612).
sysret_ring0() {
    local line
    line="$(grep -a '^\[sysret\] SYSRETQ fast path OK' "$WORK/$1.log" | head -1 | tr -d '\r')"
    if printf '%s\n' "$line" | grep -qE ' CS 8$'; then
        echo "PASS ($1): the non-canonical syscall return faulted in ring 0 and was the user's: $line"
    else
        echo "FAIL ($1): no ring-0 (CS 8) verdict from the sysret self-test (got: ${line:-none})"
        return 1
    fi
}

rc=0
HIGH_MEM=0
[ "$(mem_mib "$MEM")" -gt 4096 ] 2>/dev/null && HIGH_MEM=1

if [ "$MODE" != grub ]; then
    mkdir -p "$WORK/esp-native/EFI/BOOT" "$WORK/esp-native/harland"
    cp "$LOADER_EFI" "$WORK/esp-native/EFI/BOOT/BOOTX64.EFI"
    cp "$KERNEL_ELF" "$WORK/esp-native/harland/kernel.elf"
    : > "$WORK/esp-native/harland/klog-dump"
    : > "$WORK/esp-native/harland/boot-test"
    : > "$WORK/esp-native/harland/smp-user"
fi

if [ "$MODE" = kvm ]; then
    # The native ESP under KVM (AGAST #4612): the boot self-tests, with the
    # non-canonical return RIP's fault taken in ring 0 at syscall_exit_iret.
    QEMU_CPU=host boot kvm "$WORK/esp-native" ",disable-legacy=on,queue-size=1024" \
        -accel kvm \
        -drive "driver=null-co,size=1M,read-zeroes=on,latency-ns=100000000,if=none,id=persist" \
        -device "virtio-blk-pci,drive=persist,disable-legacy=on" || rc=1
    boot_tests_passed kvm || rc=1
    smp_user kvm || rc=1
    sysret_ring0 kvm || rc=1
    no_exception kvm || rc=1
    exit $rc
fi

if [ "$MODE" != grub ]; then
    boot native "$WORK/esp-native" ",disable-legacy=on,queue-size=1024" \
        -drive "driver=null-co,size=1M,read-zeroes=on,latency-ns=100000000,if=none,id=persist" \
        -device "virtio-blk-pci,drive=persist,disable-legacy=on" || rc=1
    all_passed native || rc=1
    net_nodev native || rc=1
    write_empty native || rc=1
    stat_ok native || rc=1
    dir_ok native || rc=1
    boot_tests_passed native || rc=1
    smp_stacks native || rc=1
    mbox_round_trip native || rc=1
    tlb_owner_unmap native || rc=1
    smp_user native || rc=1
    ring_holds_boot native || rc=1
    blk_transport native modern || rc=1
    slow_disk native || rc=1
    key_received native || rc=1
    preempted native || rc=1
    powered_off native || rc=1
    [ "$HIGH_MEM" = 1 ] && { high_memory native || rc=1; }
fi

if [ "$MODE" != native ]; then
    mkdir -p "$WORK/esp-grub/EFI/BOOT"
    # A standalone GRUB image loads no video driver by itself; without one
    # it can't honour the kernel's multiboot2 framebuffer request.
    cat > "$WORK/grub.cfg" <<'EOF'
set timeout=0
insmod all_video
menuentry "Harland" { multiboot2 /boot/harland.elf boot-test smp-user; boot; }
EOF
    grub-mkstandalone -O x86_64-efi -o "$WORK/esp-grub/EFI/BOOT/BOOTX64.EFI" \
        "boot/grub/grub.cfg=$WORK/grub.cfg" "boot/harland.elf=$KERNEL_ELF" \
        || setup_error "grub-mkstandalone failed"
    qemu-img create -q -f qcow2 "$WORK/storage.qcow2" 64M \
        || { echo "FAIL: qemu-img create failed"; exit 1; }
    STORAGE=(-drive "file=$WORK/storage.qcow2,format=qcow2,if=none,id=storage"
             -device "virtio-blk-pci,drive=storage")
    boot grub "$WORK/esp-grub" "" "${STORAGE[@]}" || rc=1
    # The framebuffer must come from the multiboot2 tag, not just be absent
    # and tolerated (#2143).
    if grep -aq "\[OK\] Display driver" "$WORK/grub.log"; then
        grep -aA1 "\[OK\] Display driver" "$WORK/grub.log" | grep -a "Resolution" | sed 's/^ */      grub framebuffer: /'
    else
        echo "FAIL (grub): display driver did not come up from the multiboot2 framebuffer tag"
        rc=1
    fi
    all_passed grub || rc=1
    net_nodev grub || rc=1
    write_empty grub || rc=1
    stat_ok grub || rc=1
    dir_ok grub || rc=1
    boot_tests_passed grub || rc=1
    smp_stacks grub || rc=1
    mbox_round_trip grub || rc=1
    tlb_owner_unmap grub || rc=1
    smp_user grub || rc=1
    blk_transport grub legacy || rc=1
    key_received grub || rc=1
    preempted grub || rc=1
    powered_off grub || rc=1
    persisted grub 1 || rc=1
    saved_subtree grub || rc=1
    [ "$HIGH_MEM" = 1 ] && { high_memory grub || rc=1; }
    # The same storage disk, booted again: the image survives the reboot
    boot grub-reboot "$WORK/esp-grub" "" "${STORAGE[@]}" || rc=1
    all_passed grub-reboot || rc=1
    boot_tests_passed grub-reboot || rc=1
    smp_stacks grub-reboot || rc=1
    mbox_round_trip grub-reboot || rc=1
    tlb_owner_unmap grub-reboot || rc=1
    smp_user grub-reboot || rc=1
    persisted grub-reboot 2 || rc=1
    saved_subtree grub-reboot || rc=1
fi

exit $rc
