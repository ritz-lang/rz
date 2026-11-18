#!/bin/bash
# test_range.sh - Range requests on a static file
#
# Tests (a 20-byte file "0123456789ABCDEFGHIJ"):
#   1  no Range        -> 200, the whole file
#   2  bytes=0-4       -> 206 "01234",      Content-Range: bytes 0-4/20
#   3  bytes=5-9       -> 206 "56789",      Content-Range: bytes 5-9/20
#   4  bytes=10-       -> 206 "ABCDEFGHIJ", Content-Range: bytes 10-19/20
#   5  bytes=-5        -> 206 "FGHIJ",      Content-Range: bytes 15-19/20
#
# Until AGAST #1403 this printed the responses and exited 0 whatever they
# were, and ran nowhere. run_all.sh runs it now.
#
# Usage: bash projects/valet/test/test_range.sh  (after ./rz build valet)
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
printf '0123456789ABCDEFGHIJ' > "$WORK/public/range_test.txt"

echo '{ "static": { "prefix": "/static/", "root": "./public" } }' > "$WORK/valet.json"
(cd "$WORK" && exec "$VALET" -c valet.json -p "$PORT") > "$WORK/server.log" 2>&1 &
SERVER_PID=$!
for _ in $(seq 1 50); do
    (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null && break
    kill -0 "$SERVER_PID" 2>/dev/null || break   # it exited: no point waiting
    sleep 0.1
done

# expect <name> <status> <body> <content-range or ""> [curl args...]
expect() {
    local name=$1 status=$2 body=$3 crange=$4
    shift 4
    local hdr="$WORK/hdr" got
    got=$(curl -s --max-time 5 -D "$hdr" "$@" "http://127.0.0.1:$PORT/static/range_test.txt")
    local code
    code=$(head -1 "$hdr" 2>/dev/null | awk '{print $2}')
    if [ "$code" != "$status" ] || [ "$got" != "$body" ]; then
        echo "FAIL: $name: got status '$code' body '$got', want $status '$body'"
        FAILED=1
    elif [ -n "$crange" ] && ! tr -d '\r' < "$hdr" | grep -qix "Content-Range: $crange"; then
        echo "FAIL: $name: no 'Content-Range: $crange' in"; cat "$hdr"
        FAILED=1
    else
        echo "PASS: $name"
    fi
}

expect "full file" 200 0123456789ABCDEFGHIJ ""
expect "bytes=0-4" 206 01234 "bytes 0-4/20" -H "Range: bytes=0-4"
expect "bytes=5-9" 206 56789 "bytes 5-9/20" -H "Range: bytes=5-9"
expect "bytes=10-" 206 ABCDEFGHIJ "bytes 10-19/20" -H "Range: bytes=10-"
expect "bytes=-5" 206 FGHIJ "bytes 15-19/20" -H "Range: bytes=-5"

if [ "$FAILED" -ne 0 ]; then
    echo "--- server log ---"; cat "$WORK/server.log"
    exit 1
fi
echo "All range tests passed"
exit 0
