#!/bin/bash
# test_multishot.sh - Tests for multishot accept mode
#
# Tests:
#   - Server starts in multishot mode
#   - Basic requests work in multishot mode
#   - Multiple concurrent connections work

set -e

VALET="${VALET:-./valet}"
PORT="${PORT:-9101}"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

pass() {
    echo -e "${GREEN}PASS${NC}: $1"
}

fail() {
    echo -e "${RED}FAIL${NC}: $1"
    FAILED=1
}

# Track server PID for safe cleanup (avoids killing unrelated processes)
SERVER_PID=""

cleanup() {
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill -9 "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}

trap cleanup EXIT

# Start server with multishot
echo "Starting Valet in multishot mode on port $PORT..."
$VALET -m -p $PORT &
SERVER_PID=$!
sleep 0.5

FAILED=0

# Test 1: Basic request works
echo ""
echo "=== Test 1: Basic request in multishot mode ==="
RESP=$(curl -s http://localhost:$PORT/)
if [ "$RESP" = "Hello, World!" ]; then
    pass "Basic request works in multishot mode"
else
    fail "Basic request returned: $RESP"
fi

# Test 2: Multiple sequential requests
echo ""
echo "=== Test 2: Multiple sequential requests ==="
for i in {1..5}; do
    RESP=$(curl -s http://localhost:$PORT/)
    if [ "$RESP" != "Hello, World!" ]; then
        fail "Request $i failed"
        break
    fi
done
if [ $FAILED -eq 0 ]; then
    pass "5 sequential requests completed"
fi

# Test 3: Concurrent requests
echo ""
echo "=== Test 3: 50 concurrent requests ==="
ab -q -n 100 -c 50 http://localhost:$PORT/ 2>&1 | grep -q "Failed requests:        0"
if [ $? -eq 0 ]; then
    pass "Concurrent requests completed with 0 failures"
else
    fail "Some concurrent requests failed"
fi

# Summary
echo ""
echo "========================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All multishot tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some multishot tests failed!${NC}"
    exit 1
fi
