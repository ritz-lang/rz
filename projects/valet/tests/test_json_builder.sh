#!/bin/bash
# Test JSON builder functionality
set -e

# Find valet relative to test script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VALET_BIN="$SCRIPT_DIR/../valet"
PORT=8098

echo "=== JSON Builder Tests ==="

# Start server in background
$VALET_BIN -p $PORT 2>&1 &
SERVER_PID=$!
sleep 0.5

cleanup() {
    kill $SERVER_PID 2>/dev/null || true
}
trap cleanup EXIT

# Test 1: JSON endpoint returns valid JSON
echo ""
echo "Test 1: JSON response structure"
RESPONSE=$(curl -s http://127.0.0.1:$PORT/json)
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
CONTENT_TYPE=$(curl -s -D - http://127.0.0.1:$PORT/json -o /dev/null | grep -i "Content-Type" | tr -d '\r')
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
