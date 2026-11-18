#!/bin/bash
# test_split_request.sh - plain-HTTP requests that arrive over several reads
#
# valet_handle_connection parsed whatever the first recv returned. A request
# whose headers had not all arrived parsed as incomplete, and valet closed the
# connection with no response and no log line (AGAST #2201). The HTTPS twin of
# this test is Test 5 in test_tls_socket.sh.
#
# Tests:
#   - Headers split across two writes get the response
#   - Headers split across many small writes get the response
#   - A malformed request still closes at once, not after a wait for more
#   - Headers that fill the read buffer without ending get a 413
#
# Usage: bash projects/valet/test/test_split_request.sh  (after ./rz build valet)
#
# A step in main.yml's build-all job. Exit only 0 or 1 (see test_tls_socket.sh).

VALET="${VALET:-$(dirname "$0")/../build/debug/valet}"
# A free port, never a fixed one: valet's SO_REUSEPORT would share it (#3694).
. "$(dirname "${BASH_SOURCE[0]}")/lib_ports.sh"
PORT="${PORT:-$(pick_port)}"
require_free_port "$PORT" || exit 1
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

(cd "$WORK" && exec "$VALET" -p "$PORT") > "$WORK/server.log" 2>&1 &
SERVER_PID=$!

for _ in $(seq 1 50); do
    (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null && break
    sleep 0.1
done

# Send each argument as its own write, 20 ms apart so each lands in its own
# recv, then print everything the server sends until it closes. Prints
# "ELAPSED <seconds>" last.
split_client() {
    timeout "$CLIENT_TIMEOUT" python3 - "$PORT" "$@" <<'EOF'
import socket, sys, time

port, pieces = int(sys.argv[1]), sys.argv[2:]
sock = socket.create_connection(("127.0.0.1", port))
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
start = time.monotonic()
for i, piece in enumerate(pieces):
    if i:
        time.sleep(0.02)
    data = piece.encode("latin-1").decode("unicode_escape").encode("latin-1")
    sock.sendall(data)
reply = b""
while True:
    try:
        data = sock.recv(16384)
    except ConnectionResetError:
        break
    if not data:
        break
    reply += data
sys.stdout.write(reply.decode("latin-1"))
print("\nELAPSED %.2f" % (time.monotonic() - start))
EOF
}

expect_hello() {
    local name="$1" out="$2"
    if grep -q "HTTP/1.1 200" <<<"$out" && grep -q "Hello, World!" <<<"$out"; then
        pass "$name: got the response"
    else
        fail "$name: no response"
        echo "--- client"; tail -5 <<<"$out"
        echo "--- server"; tail -5 "$WORK/server.log"
    fi
}

echo "=== Test 1: headers split across two writes ==="
OUT="$(split_client 'GET / HTTP/1.1\r\n' 'Host: localhost\r\nConnection: close\r\n\r\n' 2>&1)"
expect_hello "two writes" "$OUT"

echo "=== Test 2: headers split across many writes ==="
OUT="$(split_client 'GE' 'T / HT' 'TP/1.1\r' '\nHost: local' 'host\r\nConnection: close\r' '\n' '\r\n' 2>&1)"
expect_hello "many writes" "$OUT"

# Waiting for more is right only for an incomplete request: a malformed one
# can never complete, so it must still close straight away.
echo "=== Test 3: malformed request closes at once ==="
OUT="$(split_client 'hello there\r\n\r\n' 2>&1)"
SECS="$(sed -n 's/^ELAPSED //p' <<<"$OUT")"
if [ -n "$SECS" ] && awk "BEGIN{exit !($SECS < 1)}"; then
    pass "malformed: closed in ${SECS}s"
else
    fail "malformed: not closed promptly (${SECS:-timed out})"
fi

echo "=== Test 4: headers fill the read buffer without ending ==="
# Exactly fills read_buf (16 + 8176 bytes): unread bytes would make the
# server's close a reset, which can discard the 413 before the client reads it.
FILL="$(printf 'X-Fill: %08168d' 0)"
OUT="$(split_client 'GET / HTTP/1.1\r\n' "$FILL" 2>&1)"
if grep -q "HTTP/1.1 413" <<<"$OUT"; then
    pass "oversized headers: 413"
else
    fail "oversized headers: no 413"
    echo "--- client"; tail -5 <<<"$OUT"
fi

if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    fail "server exited during the run"
fi

if [ "$FAILED" -ne 0 ]; then
    echo -e "${RED}split request tests failed${NC}"
    exit 1
fi
echo -e "${GREEN}All split request tests passed${NC}"
