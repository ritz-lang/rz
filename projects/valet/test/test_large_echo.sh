#!/bin/bash
# test_large_echo.sh - a >8 KB request answered with a >8 KB response
#
# A request bigger than the 8 KB read buffer is read into a per-task heap
# buffer, and a response bigger than the 8 KB write buffer is built in one.
# Both used the same per-task slot, and acquiring the response buffer
# unmapped the request the handler was still reading (AGAST #3900): the
# zeus proxy, sizing its reply before copying a large POST body, read freed
# memory. POST /mirror (stand-alone mode) acquires its response buffer
# first, then copies the request body into it.
#
# Tests:
#   1  a 20000-byte Content-Length body comes back byte for byte
#   2  the same with a chunked body
#   3  keep-alive: a large mirror, GET /, another large mirror
#      on one connection, all answered correctly and in order
#
# Usage: bash projects/valet/test/test_large_echo.sh  (after ./rz build valet)
# No ab/wrk needed. Exit only 0 or 1.

VALET="${VALET:-$(dirname "$0")/../build/debug/valet}"
PORT="${PORT:-9194}"
CLIENT_TIMEOUT="${CLIENT_TIMEOUT:-10}"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

FAILED=0
SERVER_PID=""
WORK="$(mktemp -d)"

pass() {
    echo -e "${GREEN}PASS${NC}: $1"
}

fail() {
    echo -e "${RED}FAIL${NC}: $1"
    FAILED=1
}

cleanup() {
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill -9 "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    rm -rf "$WORK"
}

trap cleanup EXIT

for tool in python3 timeout; do
    if ! command -v "$tool" >/dev/null; then
        echo "FAIL: $tool not found"
        exit 1
    fi
done

VALET="$(realpath "$VALET")"
if [ ! -x "$VALET" ]; then
    echo "FAIL: no valet binary at $VALET (run ./rz build valet)"
    exit 1
fi

(cd "$WORK" && exec "$VALET" -p "$PORT") > "$WORK/server.log" 2>&1 &
SERVER_PID=$!

for _ in $(seq 1 50); do
    (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null && break
    sleep 0.1
done

# mirror_client <mode> <size>...: on one connection, for each size send
# POST /mirror with a <size>-byte body (a pattern that differs at every
# offset mod 251, so a shifted or zeroed copy shows), then GET / between
# them. mode is "cl" or "chunked". The last request asks Connection: close.
# Prints "OK" or what went wrong.
mirror_client() {
    timeout "$CLIENT_TIMEOUT" python3 - "$PORT" "$@" <<'EOF'
import socket, sys, time

port, mode, sizes = int(sys.argv[1]), sys.argv[2], [int(s) for s in sys.argv[3:]]
sock = socket.create_connection(("127.0.0.1", port))
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
f = sock.makefile("rb")

def body_of(n, seed):
    return bytes((i * 7 + seed) % 251 + 1 for i in range(n))

def read_response():
    status = f.readline()
    if not status:
        return None, None
    length = None
    while True:
        line = f.readline()
        if line in (b"\r\n", b""):
            break
        k, _, v = line.decode("latin-1").partition(":")
        if k.strip().lower() == "content-length":
            length = int(v.strip())
    return status, f.read(length) if length is not None else b""

for i, n in enumerate(sizes):
    last = i == len(sizes) - 1
    body = body_of(n, i)
    head = b"POST /mirror HTTP/1.1\r\nHost: x\r\n"
    if mode == "chunked":
        head += b"Transfer-Encoding: chunked\r\n\r\n"
        data = b""
        for off in range(0, n, 1000):
            piece = body[off:off + 1000]
            data += b"%x\r\n" % len(piece) + piece + b"\r\n"
        data += b"0\r\n\r\n"
    else:
        head += b"Content-Length: %d\r\n\r\n" % n
        data = body
    # Headers first, body in a later write: the body must not fit the
    # first recv, so the request goes through the heap buffer.
    sock.sendall(head)
    time.sleep(0.02)
    sock.sendall(data)
    status, got = read_response()
    if status is None:
        print("request %d (%d bytes): connection closed, no response" % (i, n))
        sys.exit(0)
    if not status.startswith(b"HTTP/1.1 200 "):
        print("request %d: status %r" % (i, status))
        sys.exit(0)
    if got != body:
        bad = next((j for j in range(min(len(got), n)) if got[j] != body[j]), min(len(got), n))
        print("request %d (%d bytes): body differs at byte %d (got %d bytes)" % (i, n, bad, len(got)))
        sys.exit(0)
    if not last:
        sock.sendall(b"GET / HTTP/1.1\r\nHost: x\r\n\r\n")
        status, got = read_response()
        if status is None or b"Hello, World!" not in got:
            print("GET / after request %d: %r %r" % (i, status, got))
            sys.exit(0)
print("OK")
EOF
}

check() {
    local name="$1" out="$2"
    if [ "$out" = "OK" ]; then
        pass "$name"
    else
        fail "$name: ${out:-no output (client timed out or crashed)}"
        echo "--- server"; tail -5 "$WORK/server.log"
    fi
}

echo "=== Test 1: 20000-byte Content-Length body mirrored ==="
check "large CL body mirrored" "$(mirror_client cl 20000)"

echo "=== Test 2: 20000-byte chunked body mirrored ==="
check "large chunked body mirrored" "$(mirror_client chunked 20000)"

echo "=== Test 3: keep-alive, large mirror / GET / / large mirror ==="
check "keep-alive large mirrors" "$(mirror_client cl 30000 12000)"

if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    fail "server exited during the run"
    tail -5 "$WORK/server.log"
fi

if [ "$FAILED" -ne 0 ]; then
    echo -e "${RED}large echo tests failed${NC}"
    exit 1
fi
echo -e "${GREEN}All large echo tests passed${NC}"
