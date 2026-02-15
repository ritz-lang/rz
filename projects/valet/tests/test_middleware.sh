#!/bin/bash
# Test middleware and catch-all route functionality
set -e

# Find valet relative to test script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VALET_BIN="$SCRIPT_DIR/../valet"
PORT=8099

echo "=== Middleware & Catch-all Tests ==="

# Start server in background
$VALET_BIN -p $PORT 2>&1 &
SERVER_PID=$!
sleep 0.5

cleanup() {
    kill $SERVER_PID 2>/dev/null || true
}
trap cleanup EXIT

# Test 1: Basic request with middleware logging
echo ""
echo "Test 1: Basic request (middleware runs)"
RESPONSE=$(curl -s http://127.0.0.1:$PORT/)
if echo "$RESPONSE" | grep -q "Hello"; then
    echo "PASS: Basic request works"
else
    echo "FAIL: Expected Hello response"
    echo "Got: $RESPONSE"
    exit 1
fi

# Test 2: JSON route
echo ""
echo "Test 2: JSON route"
RESPONSE=$(curl -s http://127.0.0.1:$PORT/json)
if echo "$RESPONSE" | grep -q "msg"; then
    echo "PASS: JSON route works"
else
    echo "FAIL: Expected JSON response"
    echo "Got: $RESPONSE"
    exit 1
fi

# Test 3: Param route
echo ""
echo "Test 3: Param route /users/:id"
RESPONSE=$(curl -s http://127.0.0.1:$PORT/users/42)
if echo "$RESPONSE" | grep -q "User ID: 42"; then
    echo "PASS: Param route works"
else
    echo "FAIL: Expected 'User ID: 42'"
    echo "Got: $RESPONSE"
    exit 1
fi

# Test 4: Catch-all nested path
echo ""
echo "Test 4: Catch-all /api/v1/users/123"
RESPONSE=$(curl -s http://127.0.0.1:$PORT/api/v1/users/123)
if echo "$RESPONSE" | grep -q "API path: v1/users/123"; then
    echo "PASS: Catch-all nested path works"
else
    echo "FAIL: Expected 'API path: v1/users/123'"
    echo "Got: $RESPONSE"
    exit 1
fi

# Test 5: Catch-all exact prefix
echo ""
echo "Test 5: Catch-all exact prefix /api"
RESPONSE=$(curl -s http://127.0.0.1:$PORT/api)
if echo "$RESPONSE" | grep -q "API path:"; then
    echo "PASS: Catch-all exact prefix works"
else
    echo "FAIL: Expected 'API path:' response"
    echo "Got: $RESPONSE"
    exit 1
fi

# Test 6: Catch-all with trailing slash
echo ""
echo "Test 6: Catch-all with trailing slash /api/"
RESPONSE=$(curl -s http://127.0.0.1:$PORT/api/)
if echo "$RESPONSE" | grep -q "API path:"; then
    echo "PASS: Catch-all trailing slash works"
else
    echo "FAIL: Expected 'API path:' response"
    echo "Got: $RESPONSE"
    exit 1
fi

# Test 7: 404 for unknown routes
echo ""
echo "Test 7: 404 for unknown route"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$PORT/nonexistent)
if [ "$STATUS" = "404" ]; then
    echo "PASS: 404 for unknown route"
else
    echo "FAIL: Expected 404, got $STATUS"
    exit 1
fi

echo ""
echo "=== All middleware & catch-all tests passed ==="
