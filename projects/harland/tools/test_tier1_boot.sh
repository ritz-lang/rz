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
# A boot fails as a hang when its serial log stops growing for BOOT_STALL
# seconds, not after a fixed time: on a host at load ~100 a TCG boot ran 10x
# slower and overran a fixed 60 s, though it was still making progress
# (AGAST #4078). A hung boot prints the vCPUs' state from the QEMU monitor.
#
# Each ESP is a QEMU vvfat directory, so the only tools needed are
# qemu-system-x86_64, OVMF, grub-mkstandalone (x86_64-efi) and python3.
# mtools, mkfs.vfat and xorriso are not needed.
#
# Usage: tools/test_tier1_boot.sh [native|grub|all]   (default: all)
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
MODE="${1:-all}"

EXIT_SETUP=3
setup_error() { echo "SETUP ERROR: $*" >&2; exit "$EXIT_SETUP"; }

case "$MODE" in native|grub|all) ;; *) echo "usage: $0 [native|grub|all]" >&2; exit 2 ;; esac
COMPILER="${COMPILER:-}"
case "$COMPILER" in
    ""|ritz0|ritz1|ritz1_selfhosted) ;;
    *) echo "usage: COMPILER must be ritz0, ritz1 or ritz1_selfhosted, not '$COMPILER'" >&2; exit 2 ;;
esac

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

# The packages in the initramfs, read after the tool checks so a missing
# tool is still a SETUP ERROR: indium/initramfs.pkgs, the one list shared
# with indium's Makefile and tools/mkiso.sh (AGAST #2759). init's suite spawns
# rzsh and prism's hello_gfx as well as indium's binaries.
USER_PKGS="$(sed -e 's/#.*//' "$PROJECTS_DIR/indium/initramfs.pkgs" | xargs)"
[ -n "$USER_PKGS" ] || { echo "FAIL: no packages in $PROJECTS_DIR/indium/initramfs.pkgs"; exit 1; }

if [ "${SKIP_BUILD:-0}" != "1" ]; then
    for pkg in harland $USER_PKGS; do
        (cd "$ROOT_DIR" && ./rz build "$pkg" ${COMPILER:+--compiler "$COMPILER"})
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

# AGAST #4308: no kernel function may keep data below %rsp. An interrupt or
# exception on the current stack (IST 0) would clobber it.
python3 "$HARLAND_DIR/tools/check_no_red_zone.py" "$KERNEL_ELF" || exit 1

# COMPILER set: every binary the boot loads must say COMPILER built it. The
# manifest (build.py writes BIN.manifest.json beside each output) records the
# compiler; the build directory does not, so without this SKIP_BUILD, or a
# build/debug a ritz0 build left behind, would boot and pass as ritz1's image.
if [ -n "$COMPILER" ]; then
    BOOT_BINS=("$KERNEL_ELF" "$LOADER_EFI")
    for pkg in $USER_PKGS; do
        for f in "$PROJECTS_DIR/$pkg"/build/debug/*.elf; do
            [ -f "$f" ] && BOOT_BINS+=("$f")
        done
    done
    for f in "${BOOT_BINS[@]}"; do
        m="$f.manifest.json"
        [ -f "$m" ] || { echo "FAIL: $(basename "$f") has no build manifest ($m)"; exit 1; }
        built_by="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("compiler", ""))' "$m" 2>/dev/null)"
        [ "$built_by" = "$COMPILER" ] || {
            echo "FAIL: $(basename "$f") was built by ${built_by:-an unknown compiler}, not $COMPILER"
            exit 1
        }
    done
    echo "PASS: ${#BOOT_BINS[@]} boot binaries built by $COMPILER"
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
for pkg in $USER_PKGS; do
    cp "$PROJECTS_DIR/$pkg"/build/debug/*.elf "$WORK/bin/" 2>/dev/null || true
done
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
    timeout "$((TIMEOUT + 30))" qemu-system-x86_64 -cpu Haswell-v1 -smp 4 -m "$MEM" \
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

# no_exception NAME: fail if the kernel took an exception or panicked.
no_exception() {
    if grep -aqE "EXCEPTION|KERNEL PANIC" "$WORK/$1.log"; then
        sed -n '/EXCEPTION/,/CR2/p' "$WORK/$1.log"
        echo "FAIL ($1): kernel exception during boot"
        return 1
    fi
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
# two /bin/busy children (Tier-1 `preempt`, #3629) both finished all their
# steps with their progress lines interleaved: the run of one child's lines
# broken by the other's at least twice (A..B..A or B..A..B). Neither child
# makes a syscall between lines, so without timer preemption the first runs
# to its end before the second starts: exactly two runs.
#
# The bar is 10 runs, not 3 (AGAST #4332). A healthy pair alternates almost
# every step (14..16 runs); the two runs of an un-preempted pair (or of the
# ritz1/ritz1 bug that made one child ~14x slower, BBBBBBBABAAAAAAA) are 2..4.
# A threshold of 3 let that regression pass as 4 runs; 10 is far above both
# failure shapes and below every measured healthy pairing.
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
if runs < 10:
    print(f"FAIL ({name}): busy children barely interleaved, not preempted each step ({order}, {runs} runs)")
    sys.exit(1)
# The interleave count is timing-sensitive, so also read the scheduler's own
# counters (AGAST #4332). A healthy pair preempts on almost every timer tick
# that interrupts ring 3, so the tick:preemption ratio is ~1.1..1.5 whichever
# compiler built kernel and userland. The bug left one child running alone
# for hundreds of ticks (911 ticks, 195 preemptions, ratio 4.7) while the fix
# gives 356/233 (1.5). The ratio is scale-invariant: a loaded host slows the
# guest and inflates ticks and preemptions together. 3 leaves margin on both
# sides, and the run count above must pass as well, so neither a lone green
# boot nor a lucky preemption can wave the regression through.
sched = re.search(r"\[sched\] (\d+) ticks, (\d+) switches, (\d+) preemptions", text)
if not sched:
    print(f"FAIL ({name}): no [sched] tick/preemption counters to check the preempt path")
    sys.exit(1)
ticks, switches, preemptions = map(int, sched.groups())
if preemptions == 0 or ticks > preemptions * 3:
    print(f"FAIL ({name}): one child ran alone: {ticks} ticks but only {preemptions} preemptions (ratio {ticks / max(preemptions, 1):.1f}; AGAST #4332)")
    sys.exit(1)
print(f"PASS ({name}): two busy children preempted each other: {order} ({runs} runs, {ticks} ticks / {preemptions} preemptions)")
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
HIGH_MEM=0
[ "$(mem_mib "$MEM")" -gt 4096 ] 2>/dev/null && HIGH_MEM=1

if [ "$MODE" != grub ]; then
    mkdir -p "$WORK/esp-native/EFI/BOOT" "$WORK/esp-native/harland"
    cp "$LOADER_EFI" "$WORK/esp-native/EFI/BOOT/BOOTX64.EFI"
    cp "$KERNEL_ELF" "$WORK/esp-native/harland/kernel.elf"
    boot native "$WORK/esp-native" ",disable-legacy=on,queue-size=1024" \
        -drive "driver=null-co,size=1M,read-zeroes=on,latency-ns=100000000,if=none,id=persist" \
        -device "virtio-blk-pci,drive=persist,disable-legacy=on" || rc=1
    all_passed native || rc=1
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
menuentry "Harland" { multiboot2 /boot/harland.elf; boot; }
EOF
    grub-mkstandalone -O x86_64-efi -o "$WORK/esp-grub/EFI/BOOT/BOOTX64.EFI" \
        "boot/grub/grub.cfg=$WORK/grub.cfg" "boot/harland.elf=$KERNEL_ELF" \
        || setup_error "grub-mkstandalone failed"
    boot grub "$WORK/esp-grub" "" || rc=1
    # The framebuffer must come from the multiboot2 tag, not just be absent
    # and tolerated (#2143).
    if grep -aq "\[OK\] Display driver" "$WORK/grub.log"; then
        grep -aA1 "\[OK\] Display driver" "$WORK/grub.log" | grep -a "Resolution" | sed 's/^ */      grub framebuffer: /'
    else
        echo "FAIL (grub): display driver did not come up from the multiboot2 framebuffer tag"
        rc=1
    fi
    all_passed grub || rc=1
    blk_transport grub legacy || rc=1
    key_received grub || rc=1
    preempted grub || rc=1
    powered_off grub || rc=1
    [ "$HIGH_MEM" = 1 ] && { high_memory grub || rc=1; }
fi

exit $rc
