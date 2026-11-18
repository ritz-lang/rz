#!/bin/bash
# test_tls_socket.sh - HTTPS over a real socket, against OpenSSL s_client
#
# test_tls_e2e and the RFC 8448 tests call tls_server_process directly, so they
# cannot see valet_handle_tls_connection: its recv/send submission, or how it
# reads completions. Only a real client on a real socket exercises that layer
# (AGAST #2190).
#
# Tests:
#   - Handshake completes with -groups X25519
#   - Handshake completes with OpenSSL's default hybrid ClientHello
#   - A GET over the established session returns the response
#   - Sequential connections each complete
#   - CCS, Finished and the first request arriving in one write
#   - A request whose headers span two records (AGAST #2201)
#   - A body in a later record than its headers, then a keep-alive GET
#   - Two pipelined requests in one record both answered
#   - One record split across two TCP writes (AGAST #2197 item 1)
#   - A request's two records in one TCP write (AGAST #2197 item 2)
#   - Headers over the 8 KiB request limit get a 413, not a silent close
#   - A chunked body across records, then a keep-alive GET; Content-Length
#     with Transfer-Encoding is a 400 (AGAST #1865)
#   - A client hanging up mid-handshake does not spin the server
#   - A client's close_notify is a clean close, not "decrypt failed"
#     (AGAST #2197 item 4)
#   - A client's KeyUpdate, update_requested, is honoured and answered
#     (AGAST #3679)
#   - Responses sent in short sends, under a small SO_SNDBUF, arrive intact
#     (AGAST #2197 item 5)
#   - A handshake flight sent in short sends, a big cert chain under a small
#     SO_SNDBUF, completes (AGAST #3677)
#   - Every connection valet closes ends with its close_notify, not a bare
#     EOF (AGAST #2196)
#
# Usage: bash projects/valet/test/test_tls_socket.sh  (after ./rz build valet)
# PORT, SPORT and HPORT pin the three servers' ports; by default each run picks its own
# (see "Ports" below; projects/ritz/tools/test_tls_socket_ports.py).
#
# A step in main.yml's build-all job. Exit only 0 or 1: ci_local reads 3 as
# SETUP ERROR, a verdict-free missing tool, and a red run here must stay red.

VALET="${VALET:-$(dirname "$0")/../build/debug/valet}"
# Bounds every client so a server that stalls fails the test, not the run.
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

for tool in openssl python3 timeout; do
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

# Ports. valet sets SO_REUSEPORT, so a second valet on the same port binds
# without error and the kernel splits connections between the two. With fixed
# ports, a gate's client once finished its handshake with a room's mutated
# valet on the same port (AGAST #3685). Two copies of this script at once, in
# two gate slots or a gate and a room, must never share a port, so each picks
# random unused ones below the kernel's ephemeral range (32768 on), where no
# client socket's local port can be (lib_ports.sh, shared since #3694). PORT,
# SPORT and HPORT can still be given by hand, but a port that already has a
# listener is refused, not shared.
. "$(dirname "${BASH_SOURCE[0]}")/lib_ports.sh"
PORT="${PORT:-$(pick_port)}"
SPORT="${SPORT:-$(pick_port "$PORT")}"
HPORT="${HPORT:-$(pick_port "$PORT" "$SPORT")}"
require_free_port "$PORT" "$SPORT" "$HPORT" || exit 1

openssl genpkey -algorithm ed25519 -out "$WORK/key.pem" 2>/dev/null
openssl req -new -x509 -key "$WORK/key.pem" -out "$WORK/cert.pem" -days 2 \
    -subj /CN=localhost 2>/dev/null

cat > "$WORK/valet.json" <<EOF
{"server":{"port":$PORT},"tls":{"enabled":true,"cert":"$WORK/cert.pem","key":"$WORK/key.pem"}}
EOF

(cd "$WORK" && exec "$VALET" -c valet.json) > "$WORK/server.log" 2>&1 &
SERVER_PID=$!

# Wait for the listener rather than sleeping a fixed time.
for _ in $(seq 1 50); do
    (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null && break
    sleep 0.1
done

# Send one GET through s_client; prints everything s_client printed. The sleep
# holds stdin open so s_client does not hang up before the response arrives.
# cat, not printf: bash's printf writes line by line, so s_client could send
# the request as several records. valet must handle that (#2201, Test 5), but
# these tests are about the handshake, so they send it in one.
printf 'GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n' \
    > "$WORK/request"
https_get() {
    {
        sleep 0.5
        cat "$WORK/request"
        sleep 0.5
    } | timeout "$CLIENT_TIMEOUT" openssl s_client -connect "127.0.0.1:$PORT" \
        -tls1_3 -ign_eof "$@" 2>&1
}

check_get() {
    local name="$1"
    shift
    local out
    out="$(https_get "$@")"
    if ! grep -q "^New, TLSv1.3" <<<"$out"; then
        fail "$name: handshake did not complete"
        echo "--- client"; tail -5 <<<"$out"
        echo "--- server"; tail -5 "$WORK/server.log"
        return
    fi
    pass "$name: handshake completed"
    if grep -q "HTTP/1.1 200" <<<"$out" && grep -q "Hello, World!" <<<"$out"; then
        pass "$name: GET returned the response"
    else
        fail "$name: no HTTP response over the session"
        echo "--- client"; tail -5 <<<"$out"
        echo "--- server"; tail -5 "$WORK/server.log"
    fi
}

echo "=== Test 1: X25519 ClientHello ==="
check_get "X25519" -groups X25519

echo "=== Test 2: default hybrid ClientHello ==="
check_get "default groups"

echo "=== Test 3: sequential connections ==="
check_get "second connection" -groups X25519
check_get "third connection" -groups X25519

# s_client cannot choose how its records land on the wire, so these use
# Python's memory-BIO TLS, where the test owns every byte it writes.
raw_client() {
    timeout "$CLIENT_TIMEOUT" python3 - "$PORT" "$1" <<'EOF'
import socket, ssl, sys, time

port, mode = int(sys.argv[1]), sys.argv[2]
PAUSE = 0.15
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
ctx.minimum_version = ssl.TLSVersion.TLSv1_3
inc, outg = ssl.MemoryBIO(), ssl.MemoryBIO()
tls = ctx.wrap_bio(inc, outg, server_hostname="localhost")
sock = socket.create_connection(("127.0.0.1", port))

try:
    tls.do_handshake()
except ssl.SSLWantReadError:
    pass
sock.sendall(outg.read())  # ClientHello

if mode == "hangup":
    sock.recv(16384)  # the server flight: it now waits on our Finished
    sock.close()
    sys.exit(0)

while True:
    try:
        tls.do_handshake()
        break
    except ssl.SSLWantReadError:
        inc.write(sock.recv(16384))

def send_record(data):
    # One tls.write is one record. The pause keeps the next out of this
    # recv: at 20 ms valet (debug build, logging) still read two at once.
    tls.write(data)
    sock.sendall(outg.read())
    time.sleep(PAUSE)

if mode == "coalesced":
    # outg now holds CCS + Finished. Queue the request behind them, one write.
    tls.write(b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
    sock.sendall(outg.read())
elif mode == "split":
    sock.sendall(outg.read())  # CCS + Finished alone
    time.sleep(PAUSE)
    send_record(b"GET / HTTP/1.1\r\n")
    send_record(b"Host: localhost\r\nConnection: close\r\n\r\n")
elif mode == "splitbody":
    sock.sendall(outg.read())
    time.sleep(PAUSE)
    send_record(b"POST /nowhere HTTP/1.1\r\nHost: localhost\r\nContent-Length: 5\r\n\r\n")
    send_record(b"hello")
    send_record(b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
elif mode == "pipelined":
    sock.sendall(outg.read())
    time.sleep(PAUSE)
    send_record(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
                b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
elif mode == "splitrecord":
    sock.sendall(outg.read())
    time.sleep(PAUSE)
    tls.write(b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
    rec = outg.read()
    sock.sendall(rec[:10])  # the header and a little ciphertext
    time.sleep(PAUSE)
    sock.sendall(rec[10:])
elif mode == "tworecords":
    sock.sendall(outg.read())
    time.sleep(PAUSE)
    tls.write(b"GET / HTTP/1.1\r\n")
    tls.write(b"Host: localhost\r\nConnection: close\r\n\r\n")
    sock.sendall(outg.read())  # both records, one write
elif mode == "closenotify":
    # A keep-alive GET, its response, then close_notify: how a
    # well-behaved client ends a session.
    sock.sendall(outg.read())
    time.sleep(PAUSE)
    send_record(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
    reply = b""
    while b"Hello, World!" not in reply:
        try:
            reply += tls.read(16384)
        except ssl.SSLWantReadError:
            data = sock.recv(16384)
            if not data:
                break
            inc.write(data)
    try:
        tls.unwrap()  # queues close_notify, then wants the server's
    except ssl.SSLWantReadError:
        pass
    sock.sendall(outg.read())
    # The client is done; the server must not wait on it. Its close, not
    # ours, ends the connection.
    sock.settimeout(2)
    try:
        while sock.recv(16384):
            pass
        reply += b"\nSERVER CLOSED\n"
    except socket.timeout:
        pass
    sock.close()
    sys.stdout.write(reply.decode("latin-1"))
    sys.exit(0)
elif mode == "chunkedbody":
    sock.sendall(outg.read())
    time.sleep(PAUSE)
    send_record(b"POST /nowhere HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nhel")
    send_record(b"lo\r\n0\r\n\r\n")
    send_record(b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
elif mode == "clte":
    sock.sendall(outg.read())
    time.sleep(PAUSE)
    send_record(b"POST /nowhere HTTP/1.1\r\nHost: localhost\r\nContent-Length: 5\r\n"
                b"Transfer-Encoding: chunked\r\n\r\n0\r\n\r\nGET / HTTP/1.1\r\n\r\n")
elif mode == "oversized":
    sock.sendall(outg.read())
    time.sleep(PAUSE)
    send_record(b"GET / HTTP/1.1\r\n")
    for _ in range(3):
        send_record(b"X-Fill: " + b"a" * 4000 + b"\r\n")

reply = b""
while True:
    try:
        chunk = tls.read(16384)
        if not chunk:  # SSLObject.read's answer to close_notify
            reply += b"\nTLS: close_notify\n"
            break
        reply += chunk
    except ssl.SSLWantReadError:
        data = sock.recv(16384)
        if data:
            inc.write(data)
        else:
            inc.write_eof()  # tls.read now tells close_notify from a bare EOF
    except ssl.SSLZeroReturnError:
        reply += b"\nTLS: close_notify\n"
        break
    except ssl.SSLEOFError:
        # suppress_ragged_eofs=False semantics: a strict client calls the
        # stream truncated (AGAST #2196).
        reply += b"\nTLS: EOF without close_notify\n"
        break
sys.stdout.write(reply.decode("latin-1"))
EOF
}

# Every connection valet closes ends with its close_notify: a client that
# demands one (Python's suppress_ragged_eofs=False) sees anything else as a
# truncated stream. valet queued the alert, then shut down and freed the
# task before the send completed (AGAST #2196).
check_close_notify() {
    if grep -q "^TLS: close_notify$" <<<"$2"; then
        pass "$1: ended with close_notify"
    else
        fail "$1: connection ended without close_notify"
        echo "--- client"; tail -8 <<<"$2"
    fi
}

echo "=== Test 4: CCS, Finished and request in one write ==="
OUT="$(raw_client coalesced 2>&1)"
check_close_notify "coalesced flight" "$OUT"
if grep -q "HTTP/1.1 200" <<<"$OUT" && grep -q "Hello, World!" <<<"$OUT"; then
    pass "coalesced flight: GET returned the response"
else
    fail "coalesced flight: no HTTP response"
    echo "--- client"; tail -5 <<<"$OUT"
    echo "--- server"; tail -5 "$WORK/server.log"
fi

# utime + stime, in clock ticks. Fields 14 and 15, counted past the ")" that
# ends the command name.
cpu_ticks() {
    sed 's/.*) //' "/proc/$SERVER_PID/stat" | cut -d' ' -f12,13 | awk '{print $1 + $2}'
}

# A request split across records used to be parsed one record at a time: the
# first was incomplete, and valet closed without a response (AGAST #2201).
echo "=== Test 5: request headers split across two records ==="
OUT="$(raw_client split 2>&1)"
check_close_notify "split headers" "$OUT"
if grep -q "HTTP/1.1 200" <<<"$OUT" && grep -q "Hello, World!" <<<"$OUT"; then
    pass "split headers: GET returned the response"
else
    fail "split headers: no HTTP response"
    echo "--- client"; tail -5 <<<"$OUT"
    echo "--- server"; tail -5 "$WORK/server.log"
fi

# The body must be read as part of its request, not parsed as the next one:
# the GET behind it is answered only if the connection survives.
echo "=== Test 6: body in a later record, then a keep-alive GET ==="
OUT="$(raw_client splitbody 2>&1)"
check_close_notify "split body" "$OUT"
NRESP="$(grep -o "HTTP/1.1 [0-9]" <<<"$OUT" | wc -l)"
if [ "$NRESP" -eq 2 ] && grep -q "HTTP/1.1 404" <<<"$OUT" && grep -q "Hello, World!" <<<"$OUT"; then
    pass "split body: POST and the GET behind it both answered"
else
    fail "split body: expected 404 then 200, got $NRESP responses"
    echo "--- client"; tail -8 <<<"$OUT"
    echo "--- server"; tail -5 "$WORK/server.log"
fi

echo "=== Test 7: two pipelined requests in one record ==="
OUT="$(raw_client pipelined 2>&1)"
check_close_notify "pipelined" "$OUT"
NOK="$(grep -o "HTTP/1.1 200" <<<"$OUT" | wc -l)"
if [ "$NOK" -eq 2 ]; then
    pass "pipelined: both requests answered"
else
    fail "pipelined: expected 2 responses, got $NOK"
    echo "--- client"; tail -8 <<<"$OUT"
    echo "--- server"; tail -5 "$WORK/server.log"
fi

echo "=== Test 8: one record split across two TCP writes ==="
OUT="$(raw_client splitrecord 2>&1)"
check_close_notify "split record" "$OUT"
if grep -q "HTTP/1.1 200" <<<"$OUT" && grep -q "Hello, World!" <<<"$OUT"; then
    pass "split record: GET returned the response"
else
    fail "split record: no HTTP response"
    echo "--- client"; tail -5 <<<"$OUT"
    echo "--- server"; tail -5 "$WORK/server.log"
fi

echo "=== Test 9: a request's two records in one TCP write ==="
OUT="$(raw_client tworecords 2>&1)"
check_close_notify "two records, one write" "$OUT"
if grep -q "HTTP/1.1 200" <<<"$OUT" && grep -q "Hello, World!" <<<"$OUT"; then
    pass "two records, one write: GET returned the response"
else
    fail "two records, one write: no HTTP response"
    echo "--- client"; tail -5 <<<"$OUT"
    echo "--- server"; tail -5 "$WORK/server.log"
fi

echo "=== Test 10: headers over the request limit ==="
OUT="$(raw_client oversized 2>&1)"
check_close_notify "oversized headers" "$OUT"
if grep -q "^HTTP/1.1 413" <<<"$OUT"; then
    pass "oversized headers: 413"
else
    fail "oversized headers: no 413"
    echo "--- client"; tail -5 <<<"$OUT"
    echo "--- server"; tail -5 "$WORK/server.log"
fi

# The framing a plain request gets, from http's lib/h1_framing.ritz
# (AGAST #1865): a chunked body is read as part of its request.
echo "=== Test 10a: chunked body across records, then a keep-alive GET ==="
OUT="$(raw_client chunkedbody 2>&1)"
NRESP="$(grep -o "HTTP/1.1 [0-9]" <<<"$OUT" | wc -l)"
if [ "$NRESP" -eq 2 ] && grep -q "HTTP/1.1 404" <<<"$OUT" && grep -q "Hello, World!" <<<"$OUT"; then
    pass "chunked body: POST and the GET behind it both answered"
else
    fail "chunked body: expected 404 then 200, got $NRESP responses"
    echo "--- client"; tail -8 <<<"$OUT"
    echo "--- server"; tail -5 "$WORK/server.log"
fi

echo "=== Test 10b: Content-Length with Transfer-Encoding ==="
OUT="$(raw_client clte 2>&1)"
NRESP="$(grep -o "HTTP/1.1 [0-9]" <<<"$OUT" | wc -l)"
if grep -q "^HTTP/1.1 400" <<<"$OUT" && [ "$NRESP" -eq 1 ]; then
    pass "CL+TE: 400, and nothing behind it served"
else
    fail "CL+TE: expected one 400, got $NRESP responses"
    echo "--- client"; tail -5 <<<"$OUT"
    echo "--- server"; tail -5 "$WORK/server.log"
fi

echo "=== Test 11: client hangs up mid-handshake ==="
raw_client hangup 2>&1 | tail -3
sleep 0.2
BEFORE="$(cpu_ticks)"
sleep 1
SPENT=$(( $(cpu_ticks) - BEFORE ))
# A spinning worker burns ~100 ticks in that second; an idle one, none.
if [ "$SPENT" -lt 20 ]; then
    pass "hangup: server idle afterwards ($SPENT ticks)"
else
    fail "hangup: server spinning ($SPENT ticks in 1s)"
fi

# A client's close_notify came back from tls_server_read as -1, so every
# normal hangup logged a warning (AGAST #2197 item 4).
echo "=== Test 12: client sends close_notify, then hangs up ==="
BEFORE="$(grep -c "TLS decrypt failed" "$WORK/server.log")"
OUT="$(raw_client closenotify 2>&1)"
sleep 0.3
AFTER="$(grep -c "TLS decrypt failed" "$WORK/server.log")"
if ! grep -q "Hello, World!" <<<"$OUT"; then
    fail "close_notify: no HTTP response before the close"
    echo "--- client"; tail -5 <<<"$OUT"
elif ! grep -q "^SERVER CLOSED$" <<<"$OUT"; then
    fail "close_notify: server kept the connection open"
elif [ "$AFTER" -ne "$BEFORE" ]; then
    fail "close_notify: logged \"TLS decrypt failed\""
    echo "--- server"; grep "WARN\|ERROR" "$WORK/server.log" | tail -3
else
    pass "close_notify: clean close, no decrypt warning"
fi

# A client's KeyUpdate (RFC 8446 4.6.3) came back from tls_server_read as -1:
# the connection died with "TLS decrypt failed" (AGAST #3679). s_client's K
# command sends KeyUpdate(update_requested), so valet must rekey its reads
# and send its own KeyUpdate before the next response. Without -ign_eof,
# which turns s_client's commands off; the sleeps keep stdin open instead.
echo "=== Test 12b: client KeyUpdate between two requests ==="
BEFORE="$(grep -c "TLS decrypt failed" "$WORK/server.log")"
OUT="$({
    sleep 0.5
    printf 'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n'
    sleep 0.5
    printf 'K\n'
    sleep 0.5
    cat "$WORK/request"
    sleep 0.7
} | timeout "$CLIENT_TIMEOUT" openssl s_client -connect "127.0.0.1:$PORT" \
    -tls1_3 -msg 2>&1)"
AFTER="$(grep -c "TLS decrypt failed" "$WORK/server.log")"
if [ "$(grep -c "Hello, World!" <<<"$OUT")" -ne 2 ]; then
    fail "KeyUpdate: the request after it was not answered"
    echo "--- client"; grep -E "KeyUpdate|HTTP/1.1|Hello" <<<"$OUT" | tail -6
elif ! grep -q "^<<< TLS 1.3, Handshake \[length 0005\], KeyUpdate" <<<"$OUT"; then
    fail "KeyUpdate: update_requested got no KeyUpdate back"
elif [ "$AFTER" -ne "$BEFORE" ]; then
    fail "KeyUpdate: logged \"TLS decrypt failed\""
else
    pass "KeyUpdate: both requests answered, keys updated both ways"
fi

if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    fail "server exited during the run"
fi

# A second server with the smallest send buffer: a 3500-byte response no
# longer fits in one send while the client is not reading, so it goes out in
# pieces. The TLS SEND state took the first piece for the whole record and
# moved on, so the rest of the record never followed (AGAST #2197 item 5).
echo "=== Test 13: short sends under a small SO_SNDBUF ==="
cat > "$WORK/valet_sndbuf.json" <<EOF2
{"server":{"port":$SPORT,"sndbuf":1024},"tls":{"enabled":true,"cert":"$WORK/cert.pem","key":"$WORK/key.pem"}}
EOF2
(cd "$WORK" && exec "$VALET" -c valet_sndbuf.json) > "$WORK/server_sndbuf.log" 2>&1 &
SNDBUF_PID=$!
for _ in $(seq 1 50); do
    (exec 3<>"/dev/tcp/127.0.0.1/$SPORT") 2>/dev/null && break
    sleep 0.1
done
OUT="$(timeout "$CLIENT_TIMEOUT" python3 - "$SPORT" <<'EOF2' 2>&1
import socket, ssl, sys, time

port = int(sys.argv[1])
N, SIZE = 12, 3500
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
ctx.minimum_version = ssl.TLSVersion.TLSv1_3
inc, outg = ssl.MemoryBIO(), ssl.MemoryBIO()
tls = ctx.wrap_bio(inc, outg, server_hostname="localhost")
sock = socket.socket()
# A small receive window too, so the server's sends back up behind it.
sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2048)
sock.connect(("127.0.0.1", port))
while True:
    try:
        tls.do_handshake()
        break
    except ssl.SSLWantReadError:
        sock.sendall(outg.read())
        inc.write(sock.recv(16384))
sock.sendall(outg.read())
# N pipelined requests, the last closing; then not reading for a while.
reqs = b"GET /bytes/%d HTTP/1.1\r\nHost: localhost\r\n\r\n" % SIZE * (N - 1)
reqs += b"GET /bytes/%d HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n" % SIZE
tls.write(reqs)
sock.sendall(outg.read())
time.sleep(0.5)
reply = b""
try:
    while True:
        try:
            chunk = tls.read(16384)
            if not chunk:  # SSLObject.read's answer to close_notify
                print("TLS: close_notify")
                break
            reply += chunk
        except ssl.SSLWantReadError:
            data = sock.recv(2048)
            if data:
                inc.write(data)
                time.sleep(0.002)
            else:
                inc.write_eof()
        except ssl.SSLZeroReturnError:
            print("TLS: close_notify")
            break
        except ssl.SSLEOFError:
            print("TLS: EOF without close_notify")
            break
except ssl.SSLError as e:
    print("TLS error after %d bytes: %s" % (len(reply), e))
body = bytes(b"0123456789"[i % 10] for i in range(SIZE))
head, sep, rest = reply.partition(b"\r\n\r\n")
got = 0
while sep:
    if not head.startswith(b"HTTP/1.1 200") or not rest.startswith(body):
        break
    got += 1
    head, sep, rest = rest[SIZE:].partition(b"\r\n\r\n")
print("intact responses: %d of %d" % (got, N))
EOF2
)"
check_close_notify "short sends" "$OUT"
if grep -q "^intact responses: 12 of 12$" <<<"$OUT"; then
    pass "short sends: 12 responses of 3500 bytes arrived intact"
else
    fail "short sends: responses corrupted or missing"
    echo "--- client"; tail -3 <<<"$OUT"
    echo "--- server"; grep "WARN\|ERROR" "$WORK/server_sndbuf.log" | tail -3
fi
{ kill -9 "$SNDBUF_PID"; wait "$SNDBUF_PID"; } 2>/dev/null

# The handshake flight goes out in short sends too, once the certificate chain
# outgrows the send buffer. HANDSHAKE_SEND closed the connection on the first
# short send instead of sending the rest from write_pos (AGAST #3677). Three
# filler certificates behind the leaf make a ~5.7 KB chain; valet reads at most
# 8 KiB of PEM, and the chain is 7.9 KB of it.
echo "=== Test 14: handshake flight in short sends (big cert chain) ==="
SAN="$(python3 -c "print(','.join('DNS:pad%02d.chain-filler.example.invalid' % i for i in range(40)))")"
cp "$WORK/cert.pem" "$WORK/chain.pem"
for i in 1 2 3; do
    openssl req -new -x509 -key "$WORK/key.pem" -out "$WORK/filler$i.pem" -days 2 \
        -subj "/CN=Filler CA $i" -addext "subjectAltName=$SAN" 2>/dev/null
    cat "$WORK/filler$i.pem" >> "$WORK/chain.pem"
done
cat > "$WORK/valet_chain.json" <<EOF2
{"server":{"port":$HPORT,"sndbuf":1024},"tls":{"enabled":true,"cert":"$WORK/chain.pem","key":"$WORK/key.pem"}}
EOF2
(cd "$WORK" && exec "$VALET" -c valet_chain.json) > "$WORK/server_chain.log" 2>&1 &
CHAIN_PID=$!
for _ in $(seq 1 50); do
    (exec 3<>"/dev/tcp/127.0.0.1/$HPORT") 2>/dev/null && break
    sleep 0.1
done
OUT="$(timeout "$CLIENT_TIMEOUT" python3 - "$HPORT" <<'EOF2' 2>&1
import socket, ssl, sys, time

port = int(sys.argv[1])
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
ctx.minimum_version = ssl.TLSVersion.TLSv1_3
inc, outg = ssl.MemoryBIO(), ssl.MemoryBIO()
tls = ctx.wrap_bio(inc, outg, server_hostname="localhost")
sock = socket.socket()
# A small receive window, and no reading for a while after the ClientHello:
# the flight backs up behind it and the server's send comes back short.
sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2048)
sock.connect(("127.0.0.1", port))
try:
    tls.do_handshake()
except ssl.SSLWantReadError:
    pass
sock.sendall(outg.read())  # ClientHello
time.sleep(0.5)
flight = 0
try:
    while True:
        try:
            tls.do_handshake()
            break
        except ssl.SSLWantReadError:
            data = sock.recv(2048)
            if not data:
                print("server closed after %d flight bytes" % flight)
                sys.exit(0)
            flight += len(data)
            inc.write(data)
            time.sleep(0.002)
except ssl.SSLError as e:
    print("TLS error after %d flight bytes: %s" % (flight, e))
    sys.exit(0)
print("flight bytes: %d" % flight)
tls.write(b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
sock.sendall(outg.read())
reply = b""
while True:
    try:
        chunk = tls.read(16384)
        if not chunk:  # SSLObject.read's answer to close_notify
            reply += b"\nTLS: close_notify\n"
            break
        reply += chunk
    except ssl.SSLWantReadError:
        data = sock.recv(16384)
        if data:
            inc.write(data)
        else:
            inc.write_eof()  # tls.read now tells close_notify from a bare EOF
    except ssl.SSLZeroReturnError:
        reply += b"\nTLS: close_notify\n"
        break
    except ssl.SSLEOFError:
        # suppress_ragged_eofs=False semantics: a strict client calls the
        # stream truncated (AGAST #2196).
        reply += b"\nTLS: EOF without close_notify\n"
        break
sys.stdout.write(reply.decode("latin-1"))
EOF2
)"
check_close_notify "big cert chain" "$OUT"
if grep -q "HTTP/1.1 200" <<<"$OUT" && grep -q "Hello, World!" <<<"$OUT"; then
    pass "big cert chain: handshake completed and GET answered ($(grep -o 'flight bytes: [0-9]*' <<<"$OUT"))"
else
    fail "big cert chain: handshake did not complete"
    echo "--- client"; tail -3 <<<"$OUT"
    echo "--- server"; grep "WARN\|ERROR" "$WORK/server_chain.log" | tail -3
fi
{ kill -9 "$CHAIN_PID"; wait "$CHAIN_PID"; } 2>/dev/null

if [ "$FAILED" -ne 0 ]; then
    echo -e "${RED}TLS socket tests failed${NC}"
    exit 1
fi
echo -e "${GREEN}All TLS socket tests passed${NC}"
