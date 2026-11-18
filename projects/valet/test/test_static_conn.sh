#!/bin/bash
# test_static_conn.sh - static 416/403 say what valet does with the
# connection (AGAST #3899)
#
# static_send_416 and static_send_403 hard-coded "Connection: close", but
# valet_try_static_raw kept the connection alive after them, so a pipelining
# client's next request was still read and answered: the header lied
# (RFC 9112 9.6: a server that sends "close" must close after it).  Both now
# take valet's keep-alive decision, like the 404 (#2117).
#
# Tests, each one connection with everything pipelined in a single write:
#   1  416, then a GET: both answered, the 416 says keep-alive
#   2  403, then a GET: both answered, the 403 says keep-alive
#   3  keepalive_requests=2; a GET, then a 416 as the last request, then a
#      GET: the 416 says close, valet closes, the third is never answered
#   4  the same with a 403 as the last request
#
# Usage: bash projects/valet/test/test_static_conn.sh  (after ./rz build valet)
# Exit only 0 or 1.

VALET="${VALET:-$(dirname "$0")/../build/debug/valet}"
# A free port, never a fixed one: valet's SO_REUSEPORT would share it (#3694).
. "$(dirname "${BASH_SOURCE[0]}")/lib_ports.sh"
PORT="${PORT:-$(pick_port)}"
require_free_port "$PORT" || exit 1
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

stop_server() {
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill -9 "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    SERVER_PID=""
}

cleanup() {
    stop_server
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

# start_server <keepalive_requests>
start_server() {
    stop_server
    cat > "$WORK/valet.json" <<EOF
{
  "server": { "port": $PORT, "workers": 1 },
  "limits": { "keepalive_requests": $1 },
  "static": { "prefix": "/static/", "root": "./public" }
}
EOF
    (cd "$WORK" && exec "$VALET" -c valet.json -p "$PORT") > "$WORK/server.log" 2>&1 &
    SERVER_PID=$!
    for _ in $(seq 1 50); do
        (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null && break
        sleep 0.1
    done
}

# Send the argument in one write and print everything the server sends,
# then "<<EOF>>" if the server closed the connection or "<<OPEN>>" if it
# was still open 3 s after the last byte.
client() {
    timeout "$CLIENT_TIMEOUT" python3 - "$PORT" "$1" <<'EOF'
import socket, sys

port, piece = int(sys.argv[1]), sys.argv[2]
sock = socket.create_connection(("127.0.0.1", port))
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.sendall(piece.encode("latin-1").decode("unicode_escape").encode("latin-1"))
sock.settimeout(3)
reply, end = b"", "<<OPEN>>"
while True:
    try:
        data = sock.recv(65536)
    except socket.timeout:
        break
    except ConnectionResetError:
        end = "<<EOF>>"
        break
    if not data:
        end = "<<EOF>>"
        break
    reply += data
sys.stdout.write(reply.decode("latin-1") + "\n" + end + "\n")
EOF
}

# The block of response headers that starts at status line `status`.
headers_of() {
    awk -v s="$2" 'index($0, s) == 1 { on = 1 } on && /^\r?$/ { exit } on' <<<"$1"
}

# check <name> <output> <status> <want-connection> <want-responses> <want-end>
check() {
    local name="$1" out="$2" status="$3" conn="$4" n="$5" end="$6" hdr got
    hdr="$(headers_of "$out" "HTTP/1.1 $status ")"
    got="$(grep -c '^HTTP/1.1 ' <<<"$out")"
    if [ -z "$hdr" ]; then
        fail "$name: no $status response"
    elif ! grep -q "^Connection: $conn" <<<"$hdr"; then
        fail "$name: $status says '$(grep '^Connection:' <<<"$hdr" | tr -d '\r')', want '$conn'"
    elif [ "$got" != "$n" ]; then
        fail "$name: $got responses, want $n"
    elif ! grep -qx -- "$end" <<<"$out"; then
        fail "$name: connection $(tail -1 <<<"$out"), want $end"
    else
        pass "$name"
        return
    fi
    echo "--- client"; head -c 1200 <<<"$out"; echo
    echo "--- server"; tail -5 "$WORK/server.log"
}

GET_LAST='GET /hello HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n'
GET='GET /hello HTTP/1.1\r\nHost: x\r\n\r\n'
R416='GET /static/range.txt HTTP/1.1\r\nHost: x\r\nRange: bytes=100-\r\n\r\n'
R403='GET /static/../etc/passwd HTTP/1.1\r\nHost: x\r\n\r\n'

start_server 100

echo "=== Test 1: 416 then a request on the same connection ==="
OUT="$(client "$R416$GET_LAST")"
check "416 keeps the connection alive" "$OUT" 416 keep-alive 2 "<<EOF>>"
grep -q "Hello from Valet!" <<<"$OUT" || fail "416: the next request was not served"

echo "=== Test 2: 403 then a request on the same connection ==="
OUT="$(client "$R403$GET_LAST")"
check "403 keeps the connection alive" "$OUT" 403 keep-alive 2 "<<EOF>>"
grep -q "Hello from Valet!" <<<"$OUT" || fail "403: the next request was not served"

start_server 2

echo "=== Test 3: 416 as the keepalive_requests-th request ==="
OUT="$(client "$GET$R416$GET")"
check "last-request 416 says close and closes" "$OUT" 416 close 2 "<<EOF>>"

echo "=== Test 4: 403 as the keepalive_requests-th request ==="
OUT="$(client "$GET$R403$GET")"
check "last-request 403 says close and closes" "$OUT" 403 close 2 "<<EOF>>"

if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    fail "server exited during the run"
fi

if [ "$FAILED" -ne 0 ]; then
    echo -e "${RED}static connection tests failed${NC}"
    exit 1
fi
echo -e "${GREEN}All static connection tests passed${NC}"
