#!/bin/bash
# Integration test for the Tier 1 echo server (this package, 74_async_tiers).
# Usage: ./test_tier1_integration.sh
#
# Port: RITZ_EXAMPLE_PORT if set, else a free port the kernel picks.  A fixed
# port (it was 9001) collided with any concurrent gate on the same host, since
# regression.sh hands the server examples per-run ports from the same range
# (AGAST #1535, #1542).  The server reads RITZ_EXAMPLE_PORT itself, so the
# script exports the one it chose.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RITZ_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SERVER_PID=""

free_port() {
    python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()'
}
PORT="${RITZ_EXAMPLE_PORT:-$(free_port)}"
export RITZ_EXAMPLE_PORT="$PORT"

cleanup() {
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

echo "=== Tier 1 Echo Server Integration Test (port $PORT) ==="

# Build the server
echo "Building server..."
cd "$RITZ_ROOT"
RITZ_PATH="$RITZ_ROOT" python3 build.py build examples/74_async_tiers >/dev/null
"$SCRIPT_DIR/build/debug/tier1_echo" &
SERVER_PID=$!

# Wait for the server to listen (up to ~5s)
for _ in $(seq 50); do
    nc -z localhost "$PORT" 2>/dev/null && break
    sleep 0.1
done

# Test 1: Simple echo
echo "Test 1: Simple echo..."
RESULT=$(echo "Hello, World!" | nc -q1 localhost "$PORT")
if [ "$RESULT" = "Hello, World!" ]; then
    echo "  PASS: Simple echo"
else
    echo "  FAIL: Expected 'Hello, World!' but got '$RESULT'"
    exit 1
fi

# Test 2: Multi-line echo
echo "Test 2: Multi-line echo..."
RESULT=$(printf "line1\nline2\nline3" | nc -q1 localhost "$PORT")
EXPECTED=$(printf "line1\nline2\nline3")
if [ "$RESULT" = "$EXPECTED" ]; then
    echo "  PASS: Multi-line echo"
else
    echo "  FAIL: Multi-line echo mismatch"
    exit 1
fi

# Test 3: Binary data
echo "Test 3: Binary data echo..."
RESULT=$(printf '\x00\x01\x02\x03\x04' | nc -q1 localhost "$PORT" | xxd -p)
EXPECTED="0001020304"
if [ "$RESULT" = "$EXPECTED" ]; then
    echo "  PASS: Binary echo"
else
    echo "  FAIL: Binary echo mismatch"
    exit 1
fi

echo ""
echo "=== All Tier 1 tests passed! ==="
