#!/bin/bash
# test_framing.sh - plain-HTTP request framing against a live valet (AGAST #1865)
#
# valet decides where a request ends with http's lib/h1_framing.ritz, the
# same code projects/http uses. Before it:
#   - bytes behind a request in the same recv (a pipelined next request)
#     were dropped,
#   - Content-Length was parsed into an i32 and an invalid one meant "no
#     body", so the body was read as the next request,
#   - Transfer-Encoding was ignored, so a chunked body was too,
#   - "Range: bytes=N-" past the end of a file answered 206 with a negative
#     Content-Length.
#
# Tests:
#   1-4  CL+TE, duplicate CL, invalid CL -> 400; unsupported TE -> 501
#   5-6  a Content-Length / chunked body split across writes is read whole
#   7    four pipelined requests in one write get four responses, in order
#   8-9  a body bigger than the 8 KB read buffer (CL and chunked) followed
#        by a pipelined request
#   10   Range past the end of the file -> 416; in-range Ranges still 206
#
# Usage: bash projects/valet/test/test_framing.sh  (after ./rz build valet)
# Exit only 0 or 1.

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

mkdir -p "$WORK/public"
printf '0123456789ABCDEFGHIJ' > "$WORK/public/range.txt"   # 20 bytes
cat > "$WORK/valet.json" <<EOF
{
  "server": { "port": $PORT, "workers": 1 },
  "static": { "prefix": "/static/", "root": "./public" }
}
EOF

(cd "$WORK" && exec "$VALET" -c valet.json -p "$PORT") > "$WORK/server.log" 2>&1 &
SERVER_PID=$!

for _ in $(seq 1 50); do
    (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null && break
    sleep 0.1
done

# Send each argument as its own write, 20 ms apart so each lands in its own
# recv, then print everything the server sends until it closes. An argument
# "@BIG:<n>" is n bytes of 'x'; "@CHUNKS:<n>" is n bytes of 'y' as chunked
# body chunks of 1000 bytes and the last chunk.
client() {
    timeout "$CLIENT_TIMEOUT" python3 - "$PORT" "$@" <<'EOF'
import socket, sys, time

port, pieces = int(sys.argv[1]), sys.argv[2:]
sock = socket.create_connection(("127.0.0.1", port))
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
for i, piece in enumerate(pieces):
    if i:
        time.sleep(0.02)
    if piece.startswith("@BIG:"):
        data = b"x" * int(piece[5:])
    elif piece.startswith("@CHUNKS:"):
        n, data = int(piece[8:]), b""
        while n > 0:
            k = min(n, 1000)
            data += b"%x\r\n" % k + b"y" * k + b"\r\n"
            n -= k
        data += b"0\r\n\r\n"
    else:
        data = piece.encode("latin-1").decode("unicode_escape").encode("latin-1")
    sock.sendall(data)
reply = b""
while True:
    try:
        data = sock.recv(65536)
    except ConnectionResetError:
        break
    if not data:
        break
    reply += data
sys.stdout.write(reply.decode("latin-1"))
EOF
}

# expect <name> <output> <grep -E pattern>...: every pattern matches.
expect() {
    local name="$1" out="$2"
    shift 2
    for pat in "$@"; do
        if ! grep -qE -- "$pat" <<<"$out"; then
            fail "$name: no match for '$pat'"
            echo "--- client"; head -c 600 <<<"$out"; echo
            echo "--- server"; tail -5 "$WORK/server.log"
            return
        fi
    done
    pass "$name"
}

# Number of responses (status lines) in the output.
responses() {
    grep -c "^HTTP/1.1 " <<<"$1"
}

echo "=== Test 1: Content-Length with Transfer-Encoding ==="
OUT="$(client 'POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 5\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\nGET / HTTP/1.1\r\n\r\n')"
expect "CL+TE is 400" "$OUT" "^HTTP/1.1 400 " "Connection: close"
[ "$(responses "$OUT")" = 1 ] || fail "CL+TE: answered more than once"

echo "=== Test 2: duplicate Content-Length ==="
OUT="$(client 'POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 3\r\nContent-Length: 3\r\n\r\nabc')"
expect "duplicate CL is 400" "$OUT" "^HTTP/1.1 400 "

echo "=== Test 3: invalid Content-Length ==="
OUT="$(client 'POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 3x\r\n\r\nGET / HTTP/1.1\r\n\r\n')"
expect "invalid CL is 400" "$OUT" "^HTTP/1.1 400 "
[ "$(responses "$OUT")" = 1 ] || fail "invalid CL: body was served as a request"
OUT="$(client 'POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 99999999999999999999\r\n\r\n')"
expect "overflowing CL is 400" "$OUT" "^HTTP/1.1 400 "

echo "=== Test 4: unsupported Transfer-Encoding ==="
OUT="$(client 'POST /echo HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: gzip, chunked\r\n\r\n')"
expect "TE gzip is 501" "$OUT" "^HTTP/1.1 501 "

echo "=== Test 5: Content-Length body split across writes ==="
OUT="$(client 'POST /echo HTTP/1.1\r\nHost: x\r\nConnection: close\r\nContent-Length: 11\r\n\r\nhel' 'lo w' 'orld')"
expect "split CL body" "$OUT" "^HTTP/1.1 200 " "^11 hello world"

echo "=== Test 6: chunked body split across writes ==="
OUT="$(client 'POST /echo HTTP/1.1\r\nHost: x\r\nConnection: close\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nhel' 'lo\r\n6;x=y\r\n world\r' '\n0\r\n' 'Trailer: t\r\n\r\n')"
expect "split chunked body" "$OUT" "^HTTP/1.1 200 " "^11 hello world"

echo "=== Test 7: pipelined requests in one write ==="
OUT="$(client 'POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 3\r\n\r\nabcGET /hello HTTP/1.1\r\nHost: x\r\n\r\nPOST /echo HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n\r\n3\r\nxyz\r\n0\r\n\r\nGET / HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n')"
ORDER="$(grep -oE '^3 abc|Hello from Valet!|^3 xyz|Hello, World!' <<<"$OUT" | tr '\n' '|')"
if [ "$(responses "$OUT")" = 4 ] && [ "$ORDER" = "3 abc|Hello from Valet!|3 xyz|Hello, World!|" ]; then
    pass "pipelined: four responses in order"
else
    fail "pipelined: got $(responses "$OUT") responses, order '$ORDER'"
    echo "--- server"; tail -5 "$WORK/server.log"
fi

echo "=== Test 8: large Content-Length body, then a pipelined request ==="
OUT="$(client 'POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 20000\r\n\r\n' '@BIG:20000' 'GET / HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n')"
expect "large CL body" "$OUT" "^20000 xxxx" "Hello, World!"

echo "=== Test 9: large chunked body, then a pipelined request ==="
OUT="$(client 'POST /echo HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n\r\n' '@CHUNKS:20000' 'GET / HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n')"
expect "large chunked body" "$OUT" "^20000 yyyy" "Hello, World!"

echo "=== Test 10: Range ==="
OUT="$(client 'GET /static/range.txt HTTP/1.1\r\nHost: x\r\nRange: bytes=100-\r\nConnection: close\r\n\r\n')"
expect "open-ended Range past the end is 416" "$OUT" "^HTTP/1.1 416 " "Content-Range: bytes \*/20"
if grep -q "Content-Length: -" <<<"$OUT"; then
    fail "Range: negative Content-Length"
fi
OUT="$(client 'GET /static/range.txt HTTP/1.1\r\nHost: x\r\nRange: bytes=20-25\r\nConnection: close\r\n\r\n')"
expect "Range starting at the end is 416" "$OUT" "^HTTP/1.1 416 "
OUT="$(client 'GET /static/range.txt HTTP/1.1\r\nHost: x\r\nRange: bytes=15-\r\nConnection: close\r\n\r\n')"
expect "open-ended Range in the file is 206" "$OUT" "^HTTP/1.1 206 " "Content-Length: 5" "Content-Range: bytes 15-19/20" "FGHIJ"
OUT="$(client 'GET /static/range.txt HTTP/1.1\r\nHost: x\r\nRange: bytes=10-1000\r\nConnection: close\r\n\r\n')"
expect "Range end clamped to the file" "$OUT" "^HTTP/1.1 206 " "Content-Length: 10" "Content-Range: bytes 10-19/20"

if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    fail "server exited during the run"
fi

if [ "$FAILED" -ne 0 ]; then
    echo -e "${RED}framing tests failed${NC}"
    exit 1
fi
echo -e "${GREEN}All framing tests passed${NC}"
