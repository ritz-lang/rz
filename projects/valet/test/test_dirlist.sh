#!/bin/bash
# test_dirlist.sh - directory listing for a static directory
#
# GET /static/ on a root holding subdir/ and test.txt answers 200 with an
# HTML index linking both.
#
# Until AGAST #1403 this printed the response and exited 0 whatever it was,
# and ran nowhere. run_all.sh runs it now.
#
# Usage: bash projects/valet/test/test_dirlist.sh  (after ./rz build valet)
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
mkdir -p "$WORK/public/subdir"; echo hi > "$WORK/public/test.txt"

echo '{ "static": { "prefix": "/static/", "root": "./public" } }' > "$WORK/valet.json"
(cd "$WORK" && exec "$VALET" -c valet.json -p "$PORT") > "$WORK/server.log" 2>&1 &
SERVER_PID=$!
for _ in $(seq 1 50); do
    (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null && break
    kill -0 "$SERVER_PID" 2>/dev/null || break   # it exited: no point waiting
    sleep 0.1
done

BODY=$(curl -s --max-time 5 -D "$WORK/h" "http://127.0.0.1:$PORT/static/")
CODE=$(head -1 "$WORK/h" 2>/dev/null | awk '{print $2}')
for want in "Index of /static/" 'href="subdir/"' 'href="test.txt"'; do
    if [ "$CODE" = 200 ] && [[ "$BODY" == *"$want"* ]]; then
        echo "PASS: listing has $want"
    else
        echo "FAIL: listing: status '$CODE', no '$want' in: $BODY"
        FAILED=1
    fi
done
if ! tr -d '\r' < "$WORK/h" | grep -qi '^Content-Type: text/html'; then
    echo "FAIL: listing is not text/html"; cat "$WORK/h"
    FAILED=1
fi

if [ "$FAILED" -ne 0 ]; then
    echo "--- server log ---"; cat "$WORK/server.log"
    exit 1
fi
echo "All directory listing tests passed"
exit 0
