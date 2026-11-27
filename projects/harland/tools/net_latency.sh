#!/bin/bash
# Harland's network latency gate (AGAST #4768, docs/RING2_NET.md "Rollout").
# Local only: not a CI step. Run it on a host with /dev/kvm (else TCG, and
# the report says so):
#
#   bash projects/harland/tools/net_latency.sh            # build, then measure
#   SKIP_BUILD=1 bash projects/harland/tools/net_latency.sh
#
# Measures ICMP echo RTT, host -> guest -> host, on each owner of the guest's
# network stack, and a UDP round trip on the ring path:
#   in-kernel    q35, no IOMMU: an untranslated boot, so virtio_net_init and
#                the kernel stack own the NIC;
#   kernel-ring  q35 + intel-iommu: the CPL-3 /bin/virtio-net owns the NIC,
#                and the kernel stack is still in the frame seat (the
#                self-test window, before the handoff);
#   netd         the same boot after the seat handoff: the CPL-3 driver and
#                /bin/netd.
#   netd-udp     the same boot after netd's window: the kernel spawns
#                /bin/udp-echo (port 7), and the wire sends UDP datagrams
#                to it and times each until its bytes come back: driver,
#                netd and an app, the whole ring path.
# Both boots are q35 with the split irqchip, the same CPU, memory and NIC
# (modern virtio-net, rx_queue_size=1024); the translating one adds the
# IOMMU and VIRTIO_F_ACCESS_PLATFORM, which a ring-1 driver needs.
#
# The ESP carries \harland\net-selftest and \harland\net-responder, so the
# kernel opens a fixed-length latency window on each owner
# (kernel/src/net/latency.ritz) and logs "[net-latency] ready owner=O
# ip=A ..." when it opens and "[net-latency] done owner=O switches=S cr3=C
# syscalls=N" when it closes. The NIC sits on a QEMU hub with slirp (DHCP) and a dgram
# netdev whose other end is tools/net_latency_wire.py: it sends WARMUP+COUNT
# echo requests to A (one at a time) and prints min / median / p99 RTT of
# the COUNT timed ones. S and C are the window's process switches and
# page-table loads; on the netd and netd-udp windows they are the round
# trips' alone (pid 1 sleeps through it), so S / COUNT+WARMUP is the
# switches per round trip, and the same for the window's syscalls (N on the
# done line). An idle run (COUNT=0 WARMUP=0) gives the baseline to subtract.
#
# The RTT is the host's (send to reply), so it carries QEMU's hub and dgram
# hops and the host's scheduling. "wire-floor" pings slirp's gateway over
# the same hub with no guest in the path, first on the pc boot: subtract it
# from an owner's numbers for the guest's share, and rerun on a loaded host.
#
# Env: COUNT (200), WARMUP (20), INTERVAL_MS (10), ACCEL (kvm if /dev/kvm is
# usable, else tcg), BOOT_TIMEOUT (300 s per boot), KEEP_WORK=DIR (keep the
# serial logs there).
# Exit: 0 = every owner measured; 1 = a boot or a window failed; 3 = a
# required tool is missing.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARLAND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECTS_DIR="$(dirname "$HARLAND_DIR")"
ROOT_DIR="$(dirname "$PROJECTS_DIR")"
TIMEOUT="${BOOT_TIMEOUT:-300}"
COUNT="${COUNT:-200}"
WARMUP="${WARMUP:-20}"
INTERVAL_MS="${INTERVAL_MS:-10}"
GUEST_MAC="52:54:00:12:34:56"
SLIRP_MAC="52:55:0a:00:02:02"   # slirp's gateway, 10.0.2.2
WIRE="$SCRIPT_DIR/net_latency_wire.py"

setup_error() { echo "SETUP ERROR: $*" >&2; exit 3; }
command -v qemu-system-x86_64 >/dev/null || setup_error "qemu-system-x86_64 not found"
command -v python3 >/dev/null || setup_error "python3 not found"
if [ -z "${OVMF_CODE:-}" ]; then
    for p in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd /usr/share/edk2/x64/OVMF_CODE.4m.fd; do
        if [ -f "$p" ]; then OVMF_CODE="$p"; break; fi
    done
fi
[ -f "${OVMF_CODE:-}" ] || setup_error "OVMF firmware not found"
OVMF_VARS=""
for p in "${OVMF_CODE/CODE/VARS}" /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd; do
    if [ -f "$p" ]; then OVMF_VARS="$p"; break; fi
done
if [ -z "${ACCEL:-}" ]; then
    if [ -r /dev/kvm ] && [ -w /dev/kvm ]; then ACCEL=kvm; else ACCEL=tcg; fi
fi

USER_PKGS="$(sed -e 's/#.*//' "$PROJECTS_DIR/indium/initramfs.pkgs" | xargs)"
if [ "${SKIP_BUILD:-0}" != "1" ]; then
    for pkg in harland $USER_PKGS; do
        (cd "$ROOT_DIR" && ./rz build "$pkg") || { echo "FAIL: build of $pkg failed"; exit 1; }
    done
fi
KERNEL_ELF="$HARLAND_DIR/build/debug/harland.elf"
LOADER_EFI="$HARLAND_DIR/build/debug/BOOTX64.EFI"
for f in "$KERNEL_ELF" "$LOADER_EFI"; do
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
: > "$WORK/esp/harland/net-selftest"
: > "$WORK/esp/harland/net-responder"

# Two free UDP ports on loopback: QEMU's end of the dgram netdev, and ours.
read -r QEMU_PORT WIRE_PORT < <(python3 -I -c '
import socket
s = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in range(2)]
for x in s: x.bind(("127.0.0.1", 0))
print(*(x.getsockname()[1] for x in s))')

rc=0
RESULTS="$WORK/results.jsonl"
: > "$RESULTS"

# measure NAME OWNERS...: boot NAME ("pc": no IOMMU, "vtd": intel-iommu) and
# run the wire against each owner's window in turn.
measure() {
    local name="$1"; shift
    local serial="$WORK/$name.log" iommu=() platform="" vars=()
    if [ "$name" = vtd ]; then
        iommu=(-device intel-iommu,intremap=on,eim=on)
        platform=",iommu_platform=on"
    fi
    if [ -n "$OVMF_VARS" ]; then
        cp "$OVMF_VARS" "$WORK/vars-$name.fd"
        vars=(-drive "if=pflash,format=raw,file=$WORK/vars-$name.fd")
    fi
    : > "$serial"
    timeout "$TIMEOUT" qemu-system-x86_64 -machine q35,kernel-irqchip=split -accel "$ACCEL" \
        -cpu Haswell-v1 -smp 4 -m 2G "${iommu[@]}" \
        -display none -no-reboot -monitor none \
        -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
        -drive "format=raw,file=fat:rw:$WORK/esp" \
        -device virtio-blk-pci,drive=initramfs,disable-legacy=on \
        -drive "file=$WORK/initramfs.qcow2,format=qcow2,if=none,id=initramfs" \
        -netdev hubport,id=nic0,hubid=0 \
        -device "virtio-net-pci,netdev=nic0,mac=$GUEST_MAC,romfile=,disable-legacy=on,rx_queue_size=1024$platform" \
        -netdev user,id=slirp0 -netdev hubport,id=hp1,hubid=0,netdev=slirp0 \
        -netdev "dgram,id=wire0,local.type=inet,local.host=127.0.0.1,local.port=$QEMU_PORT,remote.type=inet,remote.host=127.0.0.1,remote.port=$WIRE_PORT" \
        -netdev hubport,id=hp2,hubid=0,netdev=wire0 \
        -serial "file:$serial" >"$WORK/qemu-$name.err" 2>&1 &
    local qemu=$!
    local owner out target
    for owner in "$@"; do
        # wire-floor: slirp's gateway, through the same hub, no guest.
        target=()
        [ "$owner" = wire-floor ] && target=(--target 10.0.2.2 --guest-mac "$SLIRP_MAC")
        [ "$owner" = netd-udp ] && target=(--udp 7)
        out=$(python3 -I "$WIRE" --serial "$serial" --owner "$owner" \
            --listen "$WIRE_PORT" --qemu "$QEMU_PORT" --guest-mac "$GUEST_MAC" \
            --count "$COUNT" --warmup "$WARMUP" --interval-ms "$INTERVAL_MS" \
            --ready-timeout "$TIMEOUT" --dump "$WORK/rtt-$owner.log" "${target[@]}")
        echo "$out" >> "$RESULTS"
        echo "$out"
        echo "$out" | grep -q '"error"' && rc=1
        # The done line comes when the window closes.
        [ "$owner" = wire-floor ] && continue
        for _ in $(seq 1 60); do
            grep -aqE "\[net-latency\] done owner=$owner " "$serial" && break
            sleep 1
        done
    done
    kill "$qemu" 2>/dev/null
    wait "$qemu" 2>/dev/null
    grep -a "\[net-latency\]" "$serial"
    # A window must be quiet: klog writes COM1 a VM exit per byte, so a log
    # line per echo would be measured as the stack's latency.
    local noisy
    noisy=$(awk '/\[net-latency\] ready /{w=1; next} /\[net-latency\] done /{w=0} w && /\[icmp\]/{n++} END{print n+0}' "$serial")
    if [ "$noisy" != 0 ]; then
        echo "FAIL: $noisy [icmp] log line(s) inside a latency window on the $name boot"
        rc=1
    fi
    if [ -s "$WORK/qemu-$name.err" ]; then cat "$WORK/qemu-$name.err"; fi
}

echo "=== net latency: accel=$ACCEL count=$COUNT warmup=$WARMUP interval=${INTERVAL_MS}ms ($(date -u +%Y-%m-%dT%H:%MZ), $(uname -n))"
[ "$ACCEL" = kvm ] || echo "NOTE: TCG, not KVM: the numbers are the emulator's as much as the guest's"
echo "--- pc: the wire floor, then in-kernel"
measure pc wire-floor in-kernel
echo "--- vtd: kernel-ring, then netd, then netd-udp"
measure vtd kernel-ring netd netd-udp

# The table: RTTs from the wire, switch counts from the serial logs.
python3 -I - "$RESULTS" "$WORK/pc.log" "$WORK/vtd.log" "$WIRE" <<'EOF'
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("wire", sys.argv[4])
wire = importlib.util.module_from_spec(spec); spec.loader.exec_module(wire)
counts = {}
for log in sys.argv[2:4]:
    with open(log, "rb") as f:
        counts.update(wire.done_counts(f.read()))
print()
print("| owner | received/sent | min us | median us | p99 us | >10 ms | switches/rt | cr3/rt | syscalls/rt |")
print("|---|---|---|---|---|---|---|---|---|")
for line in open(sys.argv[1]):
    r = json.loads(line)
    c = counts.get(r["owner"], {})
    if "error" in r:
        print(f"| {r['owner']} | {r['error']} | | | | | | | |")
        continue
    echoes = r["sent"] + r["warmup"]
    per = lambda k: f"{c[k] / echoes:.2f}" if k in c and echoes else "-"
    print(f"| {r['owner']} | {r['received']}/{r['sent']} | {r.get('min_us', 0):.0f} | {r.get('median_us', 0):.0f}"
          f" | {r.get('p99_us', 0):.0f} | {r.get('over_10ms', '-')} | {per('switches')} | {per('cr3')} | {per('syscalls')} |")
EOF
exit "$rc"
