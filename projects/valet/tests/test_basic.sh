#!/bin/bash
# test_basic.sh - Basic HTTP server tests for Valet
#
# Tests:
#   - Server starts and responds
#   - GET / returns 200 OK with "Hello, World!"
#   - GET /hello returns 200 OK with "Hello from Valet!"
#   - GET /nonexistent returns 404 Not Found
#   - Headers are correct

set -e

VALET="${VALET:-./valet}"
PORT="${PORT:-9100}"
TIMEOUT=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

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

# Start server
echo "Starting Valet on port $PORT..."
$VALET -p $PORT &
SERVER_PID=$!
sleep 0.5

FAILED=0

# Test 1: GET /
echo ""
echo "=== Test 1: GET / ==="
RESP=$(curl -s http://localhost:$PORT/)
if [ "$RESP" = "Hello, World!" ]; then
    pass "GET / returns Hello, World!"
else
    fail "GET / returned: $RESP"
fi

# Test 2: GET /hello
echo ""
echo "=== Test 2: GET /hello ==="
RESP=$(curl -s http://localhost:$PORT/hello)
if [ "$RESP" = "Hello from Valet!" ]; then
    pass "GET /hello returns Hello from Valet!"
else
    fail "GET /hello returned: $RESP"
fi

# Test 3: GET /nonexistent
echo ""
echo "=== Test 3: GET /nonexistent ==="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/nonexistent)
if [ "$HTTP_CODE" = "404" ]; then
    pass "GET /nonexistent returns 404"
else
    fail "GET /nonexistent returned HTTP $HTTP_CODE"
fi

# Test 4: Check Content-Length header
echo ""
echo "=== Test 4: Content-Length header ==="
# Use -si (include headers in GET) instead of -sI (HEAD request)
# because HEAD requires explicit route support
HEADERS=$(curl -si http://localhost:$PORT/)
if echo "$HEADERS" | grep -qi "Content-Length: 13"; then
    pass "Content-Length header is correct"
else
    fail "Content-Length header missing or wrong"
fi

# Test 5: Check HTTP status
echo ""
echo "=== Test 5: HTTP status ==="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/)
if [ "$HTTP_CODE" = "200" ]; then
    pass "GET / returns 200 OK"
else
    fail "GET / returned HTTP $HTTP_CODE"
fi

# Test 6: Concurrent requests
echo ""
echo "=== Test 6: Concurrent requests ==="
# Use -k for keep-alive mode (server defaults to keep-alive)
timeout 10 ab -q -k -n 100 -c 10 http://localhost:$PORT/ 2>&1 | grep -q "Failed requests:        0"
if [ $? -eq 0 ]; then
    pass "100 concurrent requests completed with 0 failures"
else
    fail "Some concurrent requests failed"
fi

# Test 7: Keep-alive (two requests on same connection)
echo ""
echo "=== Test 7: Keep-alive ==="
RESP=$(curl -s http://localhost:$PORT/ http://localhost:$PORT/)
if [ "$RESP" = "Hello, World!Hello, World!" ]; then
    pass "Two requests on same connection succeeded"
else
    fail "Keep-alive returned: $RESP (expected 'Hello, World!Hello, World!')"
fi

# Test 8: Keep-alive with wrk (verifies high throughput)
echo ""
echo "=== Test 8: Keep-alive stress test ==="
WRK_OUT=$(wrk -t1 -c5 -d1s http://localhost:$PORT/ 2>&1)
# Check for successful requests (some read errors are expected from keep-alive limit)
if echo "$WRK_OUT" | grep -q "Requests/sec"; then
    # Extract requests per second
    RPS=$(echo "$WRK_OUT" | grep "Requests/sec" | awk '{print $2}' | cut -d'.' -f1)
    if [ "$RPS" -gt 10000 ]; then
        pass "wrk achieved $RPS req/s"
    else
        fail "wrk throughput too low: $RPS req/s"
    fi
else
    fail "wrk failed to report results"
fi

# Summary
echo ""
echo "========================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
