#!/bin/bash
# test_etag.sh - ETag / If-None-Match on a static file
#
# Tests:
#   1  GET              -> 200 with an ETag
#   2  If-None-Match: that ETag    -> 304, no body
#   3  If-None-Match: "wrong-etag" -> 200 with the body
#   4  Range: bytes=0-4 -> 206 carrying the same ETag
#
# Until AGAST #1403 this printed the responses and exited 0 whatever they
# were, wrote into the repo's public/, and ran nowhere. run_all.sh runs it now.
#
# Usage: bash projects/valet/test/test_etag.sh  (after ./rz build valet)
# Exit only 0 or 1.

VALET="${VALET:-$(dirname "$0")/../build/debug/valet}"
# A free port, never a fixed one: valet's SO_REUSEPORT would share it (#3694).
. "$(dirname "${BASH_SOURCE[0]}")/lib_ports.sh"
PORT="${PORT:-$(pick_port)}"
require_free_port "$PORT" || exit 1

FAILED=0
SERVER_PID=""
WORK="$(mktemp -d)"
cleanup() {
    [ -n "$SERVER_PID" ] && kill -9 "$SERVER_PID" 2>/dev/null
    wait 2>/dev/null
    rm -rf "$WORK"
}
trap cleanup EXIT

VALET="$(realpath "$VALET")"
mkdir -p "$WORK/public"
echo "ETag test content" > "$WORK/public/etag_test.txt"

echo '{ "static": { "prefix": "/static/", "root": "./public" } }' > "$WORK/valet.json"
(cd "$WORK" && exec "$VALET" -c valet.json -p "$PORT") > "$WORK/server.log" 2>&1 &
SERVER_PID=$!
for _ in $(seq 1 50); do
    (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null && break
    kill -0 "$SERVER_PID" 2>/dev/null || break   # it exited: no point waiting
    sleep 0.1
done

URL="http://127.0.0.1:$PORT/static/etag_test.txt"
fail() { echo "FAIL: $1"; FAILED=1; }
# status <header file>: the status code; header <file> <name>: its value
status() { head -1 "$1" 2>/dev/null | awk '{print $2}'; }
header() { tr -d '\r' < "$1" | grep -i "^$2:" | head -1 | cut -d' ' -f2-; }

curl -s --max-time 5 -D "$WORK/h1" -o "$WORK/b1" "$URL"
ETAG=$(header "$WORK/h1" ETag)
if [ "$(status "$WORK/h1")" = 200 ] && [ -n "$ETAG" ]; then
    echo "PASS: 200 with ETag $ETAG"
else
    fail "GET: status '$(status "$WORK/h1")', ETag '$ETAG' (want 200 and an ETag)"
fi

if [ -n "$ETAG" ]; then
    curl -s --max-time 5 -D "$WORK/h2" -o "$WORK/b2" -H "If-None-Match: $ETAG" "$URL"
    if [ "$(status "$WORK/h2")" = 304 ] && [ ! -s "$WORK/b2" ]; then
        echo "PASS: matching If-None-Match -> 304"
    else
        fail "matching If-None-Match: status '$(status "$WORK/h2")' (want 304, no body)"
    fi
fi

curl -s --max-time 5 -D "$WORK/h3" -o "$WORK/b3" -H 'If-None-Match: "wrong-etag"' "$URL"
if [ "$(status "$WORK/h3")" = 200 ] && [ "$(cat "$WORK/b3")" = "ETag test content" ]; then
    echo "PASS: non-matching If-None-Match -> 200"
else
    fail "non-matching If-None-Match: status '$(status "$WORK/h3")' body '$(cat "$WORK/b3" 2>/dev/null)'"
fi

curl -s --max-time 5 -D "$WORK/h4" -o "$WORK/b4" -H "Range: bytes=0-4" "$URL"
if [ "$(status "$WORK/h4")" = 206 ] && [ -n "$ETAG" ] && [ "$(header "$WORK/h4" ETag)" = "$ETAG" ]; then
    echo "PASS: 206 keeps the ETag"
else
    fail "Range: status '$(status "$WORK/h4")', ETag '$(header "$WORK/h4" ETag)' (want 206, $ETAG)"
fi

if [ "$FAILED" -ne 0 ]; then
    echo "--- server log ---"; cat "$WORK/server.log"
    exit 1
fi
echo "All ETag tests passed"
exit 0
