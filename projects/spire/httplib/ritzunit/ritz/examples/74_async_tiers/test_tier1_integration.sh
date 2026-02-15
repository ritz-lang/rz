#!/bin/bash
# Integration test for Tier 1 echo server
# Usage: ./test_tier1_integration.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT=9001
SERVER_PID=""

cleanup() {
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

echo "=== Tier 1 Echo Server Integration Test ==="

# Build the server
echo "Building server..."
cd "$SCRIPT_DIR/.."
python3 build.py run examples/74_async_tiers/tier1_echo_blocking.ritz &
SERVER_PID=$!

# Wait for server to start
sleep 1

# Test 1: Simple echo
echo "Test 1: Simple echo..."
RESULT=$(echo "Hello, World!" | nc -q1 localhost $PORT)
if [ "$RESULT" = "Hello, World!" ]; then
    echo "  PASS: Simple echo"
else
    echo "  FAIL: Expected 'Hello, World!' but got '$RESULT'"
    exit 1
fi

# Test 2: Multi-line echo
echo "Test 2: Multi-line echo..."
RESULT=$(printf "line1\nline2\nline3" | nc -q1 localhost $PORT)
EXPECTED=$(printf "line1\nline2\nline3")
if [ "$RESULT" = "$EXPECTED" ]; then
    echo "  PASS: Multi-line echo"
else
    echo "  FAIL: Multi-line echo mismatch"
    exit 1
fi

# Test 3: Binary data
echo "Test 3: Binary data echo..."
BINARY=$(printf '\x00\x01\x02\x03\x04')
RESULT=$(printf '\x00\x01\x02\x03\x04' | nc -q1 localhost $PORT | xxd -p)
EXPECTED="0001020304"
if [ "$RESULT" = "$EXPECTED" ]; then
    echo "  PASS: Binary echo"
else
    echo "  FAIL: Binary echo mismatch"
    exit 1
fi

echo ""
echo "=== All Tier 1 tests passed! ==="
