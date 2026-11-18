#!/bin/bash
# test_short_send.sh - plain-HTTP responses that go out in short sends
#
# valet_handle_connection's SEND state resumed short sends only for BigBuf
# responses. A response built in task.write_buf (up to 8 KiB) that the kernel
# took only part of moved on to keep-alive with its tail unsent, so the next
# response followed a truncated one (AGAST #3678). The HTTPS twin of this test
# is Test 13 in test_tls_socket.sh (AGAST #2197 item 5).
#
# Tests:
#   - write_buf responses under a small SO_SNDBUF arrive intact, one after
#     another on a keep-alive connection
#   - A single response, with Connection: close, arrives intact
#
# Usage: bash projects/valet/test/test_short_send.sh  (after ./rz build valet)
# PORT pins the server's port; by default each run picks its own (see
# test_tls_socket.sh, "Ports", AGAST #3685).
#
# A step in main.yml's build-all job. Exit only 0 or 1 (see test_tls_socket.sh).

VALET="${VALET:-$(dirname "$0")/../build/debug/valet}"
CLIENT_TIMEOUT="${CLIENT_TIMEOUT:-5}"

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

# valet sets SO_REUSEPORT: a fixed port could share a listener with another
# copy of this script (a gate and a room's mutant), so pick an unused one
# below the ephemeral range (lib_ports.sh, AGAST #3685, #3694).
. "$(dirname "${BASH_SOURCE[0]}")/lib_ports.sh"
PORT="${PORT:-$(pick_port)}"
require_free_port "$PORT" || exit 1

# The smallest send buffer (the kernel raises 1024 to its 4608 minimum): a
# 3500-byte response no longer fits in one send once the client stops reading.
cat > "$WORK/valet.json" <<EOF
{"server":{"port":$PORT,"sndbuf":1024}}
EOF
(cd "$WORK" && exec "$VALET" -c valet.json) > "$WORK/server.log" 2>&1 &
SERVER_PID=$!

for _ in $(seq 1 50); do
    port_taken "$PORT" && break
    sleep 0.1
done

# Send N GET /bytes/SIZE requests on one keep-alive connection (the last one
# closing), one at a time: each is sent while the client is not reading, so
# the server's send backs up and goes out short; then the client reads that
# response slowly and checks it arrived whole before sending the next.
# Not pipelined: plain-HTTP valet treats one recv as one request (AGAST #1865).
short_send_client() {
    timeout "$CLIENT_TIMEOUT" python3 - "$PORT" "$1" "$2" <<'EOF2'
import socket, sys, time

port, N, SIZE = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
sock = socket.socket()
# A small receive window too, so the server's sends back up behind it.
sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2048)
sock.connect(("127.0.0.1", port))
# A response that stops short never completes: give up on it after 1 s.
sock.settimeout(1.0)
body = bytes(b"0123456789"[i % 10] for i in range(SIZE))
got = 0
for i in range(N):
    close = b"Connection: close\r\n" if i == N - 1 else b""
    sock.sendall(b"GET /bytes/%d HTTP/1.1\r\nHost: localhost\r\n%s\r\n" % (SIZE, close))
    time.sleep(0.3)
    reply = b""
    while True:
        head, sep, rest = reply.partition(b"\r\n\r\n")
        if sep and len(rest) >= SIZE:
            break
        try:
            data = sock.recv(2048)
        except (socket.timeout, ConnectionResetError):
            break
        if not data:
            break
        reply += data
        time.sleep(0.002)
    if not head.startswith(b"HTTP/1.1 200") or rest != body:
        print("response %d: %d bytes, not the %d-byte body" % (i + 1, len(reply), SIZE))
        break
    got += 1
print("intact responses: %d of %d" % (got, N))
EOF2
}

expect_intact() {
    local name="$1" n="$2" out="$3"
    if grep -q "^intact responses: $n of $n$" <<<"$out"; then
        pass "$name: $n responses arrived intact"
    else
        fail "$name: responses truncated or missing"
        echo "--- client"; tail -3 <<<"$out"
        echo "--- server"; grep "WARN\|ERROR" "$WORK/server.log" | tail -3
    fi
}

echo "=== Test 1: keep-alive responses under a small SO_SNDBUF ==="
OUT="$(short_send_client 6 3500 2>&1)"
expect_intact "keep-alive" 6 "$OUT"

echo "=== Test 2: one response under a small SO_SNDBUF ==="
OUT="$(short_send_client 1 3500 2>&1)"
expect_intact "single" 1 "$OUT"

if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    fail "server exited during the run"
fi

if [ "$FAILED" -ne 0 ]; then
    echo -e "${RED}short send tests failed${NC}"
    exit 1
fi
echo -e "${GREEN}All short send tests passed${NC}"
