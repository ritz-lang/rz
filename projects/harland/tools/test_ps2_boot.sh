#!/bin/bash
# q35 PS/2 keyboard into rzsh (AGAST #4869).
#
# present: the default i8042 (no virtio-keyboard). Once rzsh is up, the QEMU
# monitor sendkey's "psok" one letter at a time. The serial log must show
# those characters after the prompt, and the kernel must have claimed IRQ 1.
# absent: -machine q35,i8042=off. The boot must still reach rzsh and log
# that no keyboard was claimed.
#
#   tools/test_ps2_boot.sh present|absent
#
# SKIP_BUILD=1    use the existing build/debug outputs
# BOOT_TIMEOUT=N  seconds to wait for the prompt and for the keys (default 180)
# KEEP_WORK=DIR   copy serial.log into DIR
# OVMF_CODE=F     OVMF firmware (default: the usual paths)
#
# Exit: 0 pass, 1 a check failed, 3 a required tool or the build is missing.

set -u

MODE="${1:-present}"
if [ "$MODE" != "present" ] && [ "$MODE" != "absent" ]; then
    echo "usage: $0 present|absent" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARLAND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECTS_DIR="$(dirname "$HARLAND_DIR")"
ROOT_DIR="$(dirname "$PROJECTS_DIR")"
TIMEOUT="${BOOT_TIMEOUT:-300}"
SHELL_INIT="${SHELL_INIT:-init_interactive}"
KEYS="${PS2_KEYS:-psok}"

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

# TCG. A /dev/kvm node on this host does not mean the module works, and the
# other Harland boot scripts do not require KVM either.
CPU="Haswell-v1"
if [ "$MODE" = "absent" ]; then
    MACHINE="q35,accel=tcg,i8042=off"
else
    MACHINE="q35,accel=tcg"
fi

python3 - "$WORK/serial.log" "$TIMEOUT" "$MODE" "$KEYS" -- \
    qemu-system-x86_64 -cpu "$CPU" -smp 1 -m 512M \
    -machine "$MACHINE" \
    -display none -no-reboot \
    -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE" "${vars[@]}" \
    -drive "format=raw,file=fat:rw:$WORK/esp" \
    -device virtio-blk-pci,drive=initramfs \
    -drive "file=$WORK/initramfs.qcow2,format=qcow2,if=none,id=initramfs" \
    <<'PY'
import os, socket, subprocess, sys, tempfile, time

log_path, timeout_s, mode, keys = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4]
qemu = sys.argv[6:]
prompt = b"rzsh> "
fatal = b"KERNEL PANIC"

sock_dir = tempfile.mkdtemp(prefix="rz_ps2_", dir=os.environ.get("SOCK_DIR", "/tmp"))
con_path = os.path.join(sock_dir, "con.sock")
mon_path = os.path.join(sock_dir, "mon.sock")
srv = socket.socket(socket.AF_UNIX)
srv.bind(con_path)
srv.listen(1)
srv.settimeout(30)
qemu += [
    "-chardev", "socket,id=con,path=%s" % con_path, "-serial", "chardev:con",
    "-monitor", "unix:%s,server,nowait" % mon_path,
]
try:
    proc = subprocess.Popen(qemu, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
except OSError as e:
    print("SETUP ERROR: could not start QEMU: %s" % e, file=sys.stderr)
    sys.exit(3)

def fail(msg):
    err = b""
    if proc.poll() is None:
        proc.terminate()
    try:
        err = proc.stderr.read() if proc.stderr is not None else b""
    except Exception:
        err = b""
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    if err:
        sys.stderr.write(err.decode(errors="replace"))
    print("FAIL: %s" % msg)
    sys.exit(1)

try:
    try:
        conn, _ = srv.accept()
    except TimeoutError:
        err = b""
        if proc.poll() is not None and proc.stderr is not None:
            err = proc.stderr.read()
        fail("QEMU never connected its serial port %s" % err.decode(errors="replace").strip())
    conn.settimeout(0.5)
    data = b""
    deadline = time.monotonic() + timeout_s
    with open(log_path, "wb") as log:
        while prompt not in data:
            if time.monotonic() > deadline:
                fail("no rzsh prompt within %ds" % int(timeout_s))
            if fatal in data:
                fail("kernel panic before the prompt")
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                if proc.poll() is not None:
                    fail("QEMU exited before the prompt")
                continue
            if not chunk:
                fail("serial closed before the prompt")
            data += chunk
            log.write(chunk)
            log.flush()
        print("PASS: rzsh prompt on the serial console")
        mark = data.rfind(prompt) + len(prompt)
        if mode == "absent":
            if b"[i8042] no keyboard" not in data:
                fail("absent controller did not log [i8042] no keyboard")
            print("PASS: no keyboard claimed, rzsh is up")
        else:
            if b"[i8042] keyboard on IRQ 1 GSI " not in data:
                fail("present controller did not log IRQ 1 / GSI")
            print("PASS: keyboard claimed on IRQ 1")
            mon = socket.socket(socket.AF_UNIX)
            mon.settimeout(5)
            try:
                mon.connect(mon_path)
            except OSError as e:
                fail("monitor socket: %s" % e)
            try:
                mon.recv(4096)
            except socket.timeout:
                pass
            for ch in keys:
                mon.sendall(("sendkey %s\n" % ch).encode())
                time.sleep(0.15)
            mon.close()
            end = time.monotonic() + timeout_s
            while keys.encode() not in data[mark:]:
                if time.monotonic() > end:
                    fail("sendkey %s did not show up after the prompt" % keys)
                if fatal in data:
                    fail("kernel panic after sendkey")
                try:
                    chunk = conn.recv(4096)
                except socket.timeout:
                    if proc.poll() is not None:
                        fail("QEMU exited before the keys echoed")
                    continue
                if not chunk:
                    fail("serial closed before the keys echoed")
                data += chunk
                log.write(chunk)
                log.flush()
            print("PASS: sendkey %s echoed after rzsh>" % keys)
finally:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    srv.close()
PY
rc=$?
if [ "$rc" -ne 0 ]; then
    echo "----- serial tail -----"
    tail -c 1500 "$WORK/serial.log" 2>/dev/null | tr -d '\r'
    echo
    echo "-----------------------"
fi
exit "$rc"
