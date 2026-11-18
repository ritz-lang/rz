#!/bin/bash
# Test JSON builder functionality
# Exit only 0 or 1: no set -e, whose curl exit 7 leaked out as the status.

# The valet under test: $VALET, else ./rz build valet's debug binary (#1403)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VALET="${VALET:-$SCRIPT_DIR/../build/debug/valet}"
# A free port, never a fixed one: valet's SO_REUSEPORT would share it (#3694).
. "$(dirname "${BASH_SOURCE[0]}")/lib_ports.sh"
PORT="${PORT:-$(pick_port)}"
require_free_port "$PORT" || exit 1

echo "=== JSON Builder Tests ==="

# Start server in background
"$VALET" -p "$PORT" 2>&1 &
SERVER_PID=$!
for _ in $(seq 1 50); do
    (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null && break
    kill -0 "$SERVER_PID" 2>/dev/null || break   # it exited: no point waiting
    sleep 0.1
done

cleanup() {
    kill $SERVER_PID 2>/dev/null || true
}
trap cleanup EXIT

# Test 1: JSON endpoint returns valid JSON
echo ""
echo "Test 1: JSON response structure"
RESPONSE=$(curl -s --max-time 5 http://127.0.0.1:$PORT/json)
if echo "$RESPONSE" | grep -q '"msg":"Hello Valet"'; then
    echo "PASS: msg field correct"
else
    echo "FAIL: Expected msg field"
    echo "Got: $RESPONSE"
    exit 1
fi

if echo "$RESPONSE" | grep -q '"version":1'; then
    echo "PASS: version field correct"
else
    echo "FAIL: Expected version field"
    echo "Got: $RESPONSE"
    exit 1
fi

if echo "$RESPONSE" | grep -q '"active":true'; then
    echo "PASS: active field correct"
else
    echo "FAIL: Expected active field"
    echo "Got: $RESPONSE"
    exit 1
fi

# Test 2: Content-Type header (use -D - instead of -I to avoid HEAD request issues)
echo ""
echo "Test 2: Content-Type header"
CONTENT_TYPE=$(curl -s --max-time 5 -D - http://127.0.0.1:$PORT/json -o /dev/null | grep -i "Content-Type" | tr -d '\r')
if echo "$CONTENT_TYPE" | grep -q "application/json"; then
    echo "PASS: Content-Type is application/json"
else
    echo "FAIL: Expected Content-Type: application/json"
    echo "Got: $CONTENT_TYPE"
    exit 1
fi

# Test 3: Valid JSON (can be parsed)
echo ""
echo "Test 3: Valid JSON syntax"
if python3 -c "import json; json.loads('$RESPONSE')" 2>/dev/null; then
    echo "PASS: Response is valid JSON"
else
    echo "FAIL: Response is not valid JSON"
    echo "Got: $RESPONSE"
    exit 1
fi

echo ""
echo "=== All JSON builder tests passed ==="
